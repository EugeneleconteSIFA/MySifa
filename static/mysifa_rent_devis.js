/* MySifa — lecture d'un devis, le résultat d'abord.
 *
 * La fenêtre de devis alignait quinze cases de même poids : un « 0 couleur »
 * pesait autant que le temps de production, et rien ne disait si le devis
 * gagnait de l'argent. Ici, dans l'ordre où l'œil doit passer :
 *   1. ce qui cloche dans le classeur (alertes) ;
 *   2. le résultat : prix de vente, marge brute, coût horaire ;
 *   3. où part le prix de vente ;
 *   4. la chaîne du classeur : étiquette → métrage → matière → temps ;
 *   5. ce qui ferait passer le devis sous un seuil en production.
 * Les valeurs lues case par case restent dessous, repliées.
 *
 * Sobriété : un libellé et une valeur à l'écran ; la cellule d'origine, les
 * montants et les explications passent dans l'infobulle du Pilotage
 * (MySifaRentFiche.infobulle).
 *
 * Données : `GET /api/rentabilite/devis/{id}/chiffrage`. textContent partout.
 * API : MySifaRentDevis.monter(conteneur, devisId, {surSansChiffrage})
 */
(function () {
  'use strict';

  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = String(txt);
    return e;
  }
  function nb(v, dec) {
    if (v === null || v === undefined || v === '' || !isFinite(Number(v))) return '—';
    return Number(v).toLocaleString('fr-FR', {minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0});
  }
  function bulle(cible, c) {
    var F = window.MySifaRentFiche;
    if (F && F.infobulle) F.infobulle(cible, c);
    return cible;
  }
  function api(path, opts) {
    var core = window.__prodCore;
    if (core && typeof core.api === 'function') return core.api(path, opts);
    return fetch(path, Object.assign({credentials: 'same-origin'}, opts || {})).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }
  function src(d, cle) { return (d.sources || {})[cle] || ''; }

  // ── 1. Alertes ─────────────────────────────────────────────────────
  function alertes(d) {
    var liste = d.alertes || [];
    if (!liste.length) return null;
    var w = el('div', 'rd-alertes');
    liste.forEach(function (a) {
      var l = el('div', 'rd-alerte rd-alerte-' + (a.niveau || 'info'), a.message);
      if (a.detail) bulle(l, {note: a.detail});
      w.appendChild(l);
    });
    return w;
  }

  // ── 2. Résultat ────────────────────────────────────────────────────
  function resultat(d) {
    var c = d.calcul || {}, v = d.chiffrage || {}, s = d.seuils || {};
    var ind = d.indicateurs || {};
    var w = el('div', 'rd-resultat');
    function tuile(k, val, ton, info) {
      var t = el('div', 'rd-tuile' + (ton ? ' rd-' + ton : ''));
      t.appendChild(el('span', 'rd-tuile-k', k));
      t.appendChild(el('span', 'rd-tuile-v', val));
      bulle(t, info);
      w.appendChild(t);
    }
    var pm = (ind['Prix au mille'] || {}).valeur;
    tuile('Prix de vente', nb(c.prix_vente) + ' €', '', {titre: 'Prix de vente', lignes: [
      ['Prix au mille', pm != null ? nb(pm, 2) + ' €' : ''],
      ['Prix de revient', nb(v.prix_revient) + ' €'],
      ['Surmarge', v.surmarge_taux != null ? nb(v.surmarge_taux * 100, 1) + ' %' : ''],
      ['Cellule', src(d, 'prix_vente')]]});
    var mbTon = c.mb_pct == null ? '' : (c.mb_pct >= s.mb_pct ? 'ok' : 'bad');
    var marge = c.mb_pct == null ? null : c.mb_pct - s.mb_pct;
    tuile('Marge brute', nb(c.mb_pct, 1) + ' %', mbTon, {titre: 'Marge brute', lignes: [
      ['Montant', nb(c.marge_brute) + ' €'],
      ['Seuil', nb(s.mb_pct) + ' %'],
      ['Marge au-dessus', marge != null ? (marge >= 0 ? '+' : '−') + nb(Math.abs(marge), 1) + ' pt' : ''],
      ['Cellule', src(d, 'marge_brute')]],
      note: 'Prix de vente moins matière, encre, cliché, outil, emballage et transport.'});
    var ehTon = c.cout_horaire == null ? '' : (c.cout_horaire >= s.cout_horaire ? 'ok' : 'bad');
    tuile('Coût horaire', nb(c.cout_horaire) + ' €/h', ehTon, {titre: 'Coût horaire', lignes: [
      ['Heures machine', nb(c.heures, 1) + ' h'],
      ['Taux machine du devis', nb(v.taux_horaire) + ' €/h'],
      ['Seuil', nb(s.cout_horaire) + ' €/h'],
      ['Cellule', src(d, 'cout_horaire')]],
      note: 'Marge brute par heure machine.'});
    return w;
  }

  // ── 3. Où part le prix de vente ────────────────────────────────────
  function repartition(d) {
    var v = d.chiffrage || {}, pv = Number((d.calcul || {}).prix_vente) || 0;
    if (!pv) return null;
    var autres = ['cout_outil', 'cout_emballage', 'cout_transport', 'cout_encre', 'cout_cliche',
      'cout_conditionnement', 'cout_manutention'].reduce(function (a, k) { return a + (Number(v[k]) || 0); }, 0);
    var parts = [
      ['Matière', Number(v.cout_matiere) || 0, 'rd-s-matiere'],
      ['Production', Number(v.cout_production) || 0, 'rd-s-prod'],
      ['Outil, emballage, transport', autres, 'rd-s-autres'],
    ];
    var reste = pv - parts.reduce(function (a, p) { return a + p[1]; }, 0);
    parts.push(['Surmarge', reste, 'rd-s-surmarge']);
    var w = el('div', 'rd-repart');
    var barre = el('div', 'rd-barre');
    var leg = el('div', 'rd-legende');
    parts.forEach(function (p) {
      if (p[1] <= 0) return;
      var pc = p[1] / pv * 100;
      var seg = el('span', p[2]);
      seg.style.width = pc + '%';
      bulle(seg, {titre: p[0], lignes: [['Montant', nb(p[1]) + ' €'], ['Part du prix', nb(pc, 1) + ' %']]});
      barre.appendChild(seg);
      var l = el('span', 'rd-leg');
      l.appendChild(el('i', p[2]));
      l.appendChild(document.createTextNode(p[0] + ' ' + nb(pc, 0) + ' %'));
      leg.appendChild(l);
    });
    w.appendChild(barre);
    w.appendChild(leg);
    return w;
  }

  // ── 4. La chaîne du classeur ───────────────────────────────────────
  function etape(titre, lignes, total) {
    var e = el('div', 'rd-etape');
    e.appendChild(el('div', 'rd-etape-t', titre));
    var dl = el('dl');
    lignes.forEach(function (l) {
      if (l[1] == null || l[1] === '') return;
      var dt = el('dt', '', l[0]), dd = el('dd', '', l[1]);
      var info = [l[3], l[2] ? 'Cellule ' + l[2] : ''].filter(Boolean).join(' · ');
      if (info) { bulle(dt, {note: info}); bulle(dd, {note: info}); }
      dl.appendChild(dt);
      dl.appendChild(dd);
    });
    e.appendChild(dl);
    if (total) {
      var t = el('div', 'rd-etape-tot');
      t.appendChild(el('span', '', total[0]));
      t.appendChild(el('span', '', total[1]));
      if (total[2]) bulle(t, {note: 'Cellule ' + total[2]});
      e.appendChild(t);
    }
    return e;
  }

  function chaine(d) {
    var v = d.chiffrage || {}, so = d.socle || {}, ind = d.indicateurs || {}, c = d.calcul || {};
    var laize = Number(so.laize) || 0;
    var mlProd = Number(so.metrage_production_ml) || 0;
    var mlCal = (Number(so.metrage_calage_ml) || 0) + (Number(so.metrage_calage_impression_ml) || 0);
    var mlTot = Number(v.metrage_total_ml) || 0;
    var gacheMl = mlTot ? Math.max(0, mlTot - mlProd - mlCal) : null;
    var prix = Number(v.prix_m2_corrige) || Number(v.prix_m2_base) || 0;
    var fronts = (ind['Nombre de fronts'] || {}).valeur, poses = (ind['Nombre total de poses'] || {}).valeur;
    var pas = (ind['Pas développé'] || {}).valeur;
    var w = el('div', 'rd-chaine');
    w.appendChild(etape('Étiquette', [
      ['Format', so.format_v && so.format_h ? nb(so.format_v, 1) + ' × ' + nb(so.format_h, 1) + ' mm' : ''],
      ['Fronts', fronts != null ? nb(fronts) + (poses && fronts ? ' × ' + nb(poses / fronts) : '') : '',
        (ind['Nombre de fronts'] || {}).source],
      ['Pas développé', pas != null ? nb(pas, 2) + ' mm' : '', (ind['Pas développé'] || {}).source],
      ['Laize', laize ? nb(laize) + ' mm' : ''],
      ['Matière', v.num_matiere ? 'n° ' + v.num_matiere : '', src(d, 'num_matiere')]],
      ['Quantité', nb(so.qte_etiquettes)]));
    w.appendChild(etape('Métrage', [
      ['Production', nb(mlProd) + ' ml'],
      ['Calage', nb(mlCal) + ' ml'],
      ['Gâche', gacheMl != null ? nb(gacheMl) + ' ml' : '', null,
        so.gache ? nb(so.gache * 100, 1) + ' % du métrage (production + calage)' : '']],
      ['Total', nb(mlTot) + ' ml', src(d, 'metrage_total_ml')]));
    w.appendChild(etape('Matière', [
      ['Surface', laize && mlTot ? nb(mlTot * laize / 1000) + ' m²' : ''],
      ['Prix', prix ? nb(prix, 3) + ' €/m²' : '', src(d, v.prix_m2_corrige ? 'prix_m2_corrige' : 'prix_m2_base')],
      ['Au mille', (ind['Prix au mille'] || {}).valeur != null && so.qte_etiquettes
        ? nb((Number(v.cout_matiere) || 0) / so.qte_etiquettes * 1000, 2) + ' €' : '']],
      ['Coût', nb(v.cout_matiere) + ' €', src(d, 'cout_matiere')]));
    w.appendChild(etape('Temps', [
      ['Calage', nb((Number(so.temps_calage_mn) || 0) + (Number(so.temps_calage_impression_mn) || 0)) + ' mn'],
      ['Production', nb(so.temps_production_mn) + ' mn'],
      ['Vitesse', so.vitesse_theorique ? nb(so.vitesse_theorique) + ' m/mn' : ''],
      ['Taux machine', v.taux_horaire ? nb(v.taux_horaire) + ' €/h' : '', src(d, 'taux_horaire')]],
      ['Heures', nb(c.heures, 1) + ' h', src(d, 'temps_total_mn')]));
    return w;
  }

  // ── 5. Sensibilité ─────────────────────────────────────────────────
  function sensibilite(d) {
    var liste = d.sensibilite || [];
    if (!liste.length) return null;
    var w = el('div', 'rd-sens');
    var tete = el('div', 'rd-sens-l rd-sens-tete');
    tete.appendChild(bulle(el('span', '', 'Si en production'), {note:
      'Un paramètre à la fois, à prix de vente constant : le devis est signé.'}));
    tete.appendChild(el('span', '', 'Marge brute'));
    tete.appendChild(el('span', '', 'Coût horaire'));
    w.appendChild(tete);
    liste.forEach(function (l) {
      var r = el('div', 'rd-sens-l');
      var lib = el('span', 'rd-sens-lib', l.libelle);
      if (l.detail || l.delta_mb) bulle(lib, {titre: l.libelle, lignes: [['Hypothèse', l.detail],
        ['Effet sur la marge', l.delta_mb ? '−' + nb(Math.abs(l.delta_mb)) + ' €' : 'aucun']]});
      r.appendChild(lib);
      r.appendChild(el('span', l.sous_seuil_mb ? 'rd-bad' : '', nb(l.mb_pct, 1) + ' %'));
      r.appendChild(el('span', l.sous_seuil_cout_horaire ? 'rd-bad' : '', nb(l.cout_horaire) + ' €/h'));
      w.appendChild(r);
    });
    return w;
  }

  function dessiner(d) {
    var r = el('div', 'rd-lecture');
    [alertes(d), resultat(d), repartition(d), chaine(d), sensibilite(d)].forEach(function (x) {
      if (x) r.appendChild(x);
    });
    return r;
  }

  function sansChiffrage(conteneur, devisId, message, o) {
    conteneur.textContent = '';
    var w = el('div', 'rd-vide');
    w.appendChild(el('span', '', message || 'Montants du devis non lus.'));
    var b = el('button', 'btn-sec', 'Relire le classeur');
    b.type = 'button';
    b.addEventListener('click', function () {
      b.disabled = true;
      api('/api/rentabilite/devis/' + Number(devisId) + '/chiffrage/relire', {method: 'POST'})
        .then(function (d) { conteneur.textContent = ''; conteneur.appendChild(dessiner(d)); })
        .catch(function () { b.disabled = false; b.textContent = 'Fichier d\'origine introuvable'; });
    });
    w.appendChild(b);
    conteneur.appendChild(w);
    if (o && o.surSansChiffrage) o.surSansChiffrage();
  }

  function monter(conteneur, devisId, o) {
    if (!conteneur) return;
    conteneur.textContent = '';
    conteneur.appendChild(el('div', 'rd-attente', 'Lecture des montants…'));
    api('/api/rentabilite/devis/' + Number(devisId) + '/chiffrage').then(function (d) {
      if (!conteneur.isConnected) return;
      if (!d || !d.chiffrage || d.chiffrage.prix_vente == null) {
        sansChiffrage(conteneur, devisId, d && d.message, o);
        return;
      }
      conteneur.textContent = '';
      conteneur.appendChild(dessiner(d));
    }).catch(function () {
      if (conteneur.isConnected) sansChiffrage(conteneur, devisId, 'Montants du devis indisponibles.', o);
    });
  }

  window.MySifaRentDevis = {monter: monter, dessiner: dessiner};
})();

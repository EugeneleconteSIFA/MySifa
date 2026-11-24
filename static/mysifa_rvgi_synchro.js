/* MySifa — date des données RVGI et bouton « Mettre à jour maintenant ».
 *
 * Partagé par l'ERP (/erp) et l'ADV (/adv). Le VPS ne voit pas RVGI : le bouton
 * DÉPOSE une demande (POST /api/erp/miroir/actualiser), que le poste du réseau
 * SIFA relève toutes les deux minutes avant d'exporter et d'envoyer le miroir.
 * Ce module affiche où en est la demande et, quand le miroir a été reconstruit,
 * prévient la page (`surMiseAJour`) pour qu'elle recharge ses données.
 *
 *   MySifaRvgiSynchro.monter(hote, {peutDemander: true, surMiseAJour: fn})
 *
 * `monter` peut être rappelé à chaque rendu de la page : l'état et le relevé
 * périodique vivent ici, une seule fois.
 */
(function () {
  'use strict';
  if (window.MySifaRvgiSynchro) return;

  var etat = null;            // dernière réponse de /api/erp/miroir/etat
  var importeAuDepart = null; // date du miroir quand la demande a été suivie
  var minuteur = null;
  var opts = {};
  var hotes = [];

  function css() {
    if (document.getElementById('rvgi-synchro-css')) return;
    var s = document.createElement('style');
    s.id = 'rvgi-synchro-css';
    s.textContent =
      '.rvgi-sync{display:inline-flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:12px;color:var(--muted)}' +
      '.rvgi-sync b{color:var(--text2);font-weight:700}' +
      '.rvgi-sync .rs-vieux b{color:var(--warn)}' +
      '.rvgi-sync button{display:inline-flex;align-items:center;gap:5px;padding:4px 10px;border-radius:8px;border:1px solid var(--border);' +
      'background:var(--card);color:var(--text);font:inherit;font-size:12px;font-weight:700;cursor:pointer}' +
      '.rvgi-sync button:hover{background:var(--bg)}' +
      '.rvgi-sync button:disabled{opacity:.6;cursor:default}' +
      '.rvgi-sync .rs-etat{font-weight:600}' +
      '.rvgi-sync .rs-etat.encours{color:var(--accent)}' +
      '.rvgi-sync .rs-etat.ok{color:var(--success)}' +
      '.rvgi-sync .rs-etat.ko{color:var(--danger)}' +
      '@keyframes rs-tourne{to{transform:rotate(360deg)}}' +
      '.rvgi-sync .rs-tourne{display:inline-block;animation:rs-tourne 1s linear infinite}' +
      'html.reduce-anim .rvgi-sync .rs-tourne{animation:none}';
    document.head.appendChild(s);
  }

  function dateHeure(s) {
    if (!s) return '';
    var v = String(s).replace('T', ' ');
    var d = v.slice(0, 10).split('-');
    return (d.length === 3 ? d[2] + '/' + d[1] + '/' + d[0] : v.slice(0, 10)) + (v.length >= 16 ? ' à ' + v.slice(11, 16) : '');
  }
  function heure(s) { return s && String(s).length >= 16 ? String(s).replace('T', ' ').slice(11, 16) : ''; }

  function el(tag, cls, txt) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (txt != null) e.textContent = txt;
    return e;
  }

  function enCours() {
    var d = etat && etat.demande;
    return !!(d && (d.statut === 'en_attente' || d.statut === 'prise'));
  }

  function dessiner(hote) {
    hote.textContent = '';
    var bloc = el('span', 'rvgi-sync');
    if (!etat) { bloc.appendChild(el('span', null, 'Données RVGI…')); hote.appendChild(bloc); return; }
    if (!etat.present) {
      bloc.appendChild(el('span', 'rs-vieux', null)).appendChild(el('b', null, 'Miroir RVGI absent'));
    } else if (!etat.importe_le) {
      bloc.appendChild(el('span', null, 'Données RVGI · date d’import inconnue'));
    } else {
      var age = (new Date() - new Date(String(etat.importe_le || '').replace(' ', 'T'))) / 3600000;
      var date = el('span', isFinite(age) && age > 3 ? 'rs-vieux' : null, 'Données RVGI du ');
      date.appendChild(el('b', null, dateHeure(etat.importe_le)));
      bloc.appendChild(date);
    }
    var d = etat.demande;
    if (d && enCours()) {
      var t = d.statut === 'prise'
        ? 'Mise à jour en cours depuis ' + heure(d.prise_le)
        : 'Demande envoyée à ' + heure(d.demande_le) + ' · en attente du poste SIFA';
      var e = el('span', 'rs-etat encours');
      e.appendChild(el('span', 'rs-tourne', '↻'));
      e.appendChild(document.createTextNode(' ' + t));
      bloc.appendChild(e);
      if (d.alerte) bloc.appendChild(el('span', 'rs-etat ko', d.alerte));
    } else if (d && d.statut === 'echec' && d.fin_le && (new Date() - new Date(String(d.fin_le).replace(' ', 'T'))) < 6 * 3600000) {
      bloc.appendChild(el('span', 'rs-etat ko', 'Dernière demande en échec' + (d.message ? ' : ' + d.message : '')));
    }
    if (opts.peutDemander) {
      var b = el('button', null, enCours() ? 'Demandée' : 'Mettre à jour');
      b.type = 'button';
      b.disabled = enCours();
      b.title = 'Demande au poste SIFA un export de RVGI, maintenant (relevé en 2 minutes, puis quelques minutes d’export)';
      b.addEventListener('click', demander);
      bloc.appendChild(b);
    }
    hote.appendChild(bloc);
  }

  function redessiner() {
    hotes = hotes.filter(function (h) { return document.body.contains(h); });
    hotes.forEach(dessiner);
  }

  async function lire() {
    try {
      var r = await fetch('/api/erp/miroir/etat', {credentials: 'include'});
      if (!r.ok) return;
      var avant = etat && etat.importe_le;
      etat = await r.json();
      // Le miroir vient d'être reconstruit pendant qu'on suivait une demande :
      // la page recharge ses données.
      if (importeAuDepart !== null && etat.importe_le && etat.importe_le !== importeAuDepart) {
        importeAuDepart = null;
        if (typeof opts.surMiseAJour === 'function') { try { opts.surMiseAJour(etat); } catch (e) {} }
      } else if (avant && etat.importe_le && avant !== etat.importe_le && typeof opts.surMiseAJour === 'function') {
        try { opts.surMiseAJour(etat); } catch (e) {}
      }
    } catch (e) { /* l'affichage garde le dernier état connu */ }
    redessiner();
    planifier();
  }

  function planifier() {
    clearTimeout(minuteur);
    // Toutes les 20 s tant qu'une demande court, sinon toutes les 5 min : un
    // passage horaire du poste est vu sans recharger la page.
    minuteur = setTimeout(lire, enCours() ? 20000 : 300000);
  }

  async function demander() {
    try {
      importeAuDepart = (etat && etat.importe_le) || '';
      var r = await fetch('/api/erp/miroir/actualiser', {method: 'POST', credentials: 'include'});
      if (!r.ok) {
        var j = null; try { j = await r.json(); } catch (e) {}
        throw new Error((j && j.detail) || ('Erreur ' + r.status));
      }
    } catch (e) {
      importeAuDepart = null;
      if (typeof opts.surErreur === 'function') opts.surErreur(e.message);
    }
    lire();
  }

  window.MySifaRvgiSynchro = {
    monter: function (hote, o) {
      if (!hote) return;
      css();
      opts = o || opts || {};
      if (hotes.indexOf(hote) === -1) hotes.push(hote);
      dessiner(hote);
      if (!etat && !minuteur) lire();
      else if (!minuteur) planifier();
    },
    actualiser: lire
  };
})();

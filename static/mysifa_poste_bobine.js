/* Poste de déroulement d'une bobine au scan — Frontal · Complexe · Glassine.
 *
 * Posé dans les modales de scan de MyProd. Le serveur a déjà tenté de
 * reconnaître la nature de la bobine (app/services/poste_bobine.py) et renvoie
 * `poste` dans la réponse de /api/fabrication/receptions/lookup :
 *
 *   null                         la machine n'a pas de poste → rien à afficher
 *   {trouve:true, categorie, …}  nature reconnue → bouton présélectionné
 *   {trouve:true, categorie:null, poste:'frontal'}
 *                                le poste est sûr, pas la nature exacte
 *   {trouve:false, …}            rien de sûr → choix OBLIGATOIRE
 *
 * Raccourcis clavier F / C / G quand le focus n'est pas dans un champ : le
 * geste de l'atelier reste douchette puis Entrée.
 */
(function () {
  'use strict';

  var CATS = [
    { code: 'frontal', label: 'Frontal', touche: 'f', poste: 'frontal' },
    { code: 'complexe', label: 'Complexe', touche: 'c', poste: 'frontal' },
    { code: 'glassine', label: 'Glassine', touche: 'g', poste: 'glassine' },
  ];
  var CONF_MOT = { certain: 'Reconnu', probable: 'Détecté', suggere: 'Probablement' };

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function html(poste) {
    if (!poste) return '';
    var detecte = poste.trouve ? (CONF_MOT[poste.confiance] || 'Détecté') : '';
    var tete = poste.trouve
      ? detecte + ' · poste ' + String(poste.poste_label || poste.poste || '').toLowerCase()
      : 'Sur quel poste va cette bobine ? (obligatoire)';
    var boutons = CATS.map(function (c) {
      return '<button type="button" class="mpb-btn" data-cat="' + c.code + '"' +
        ' style="flex:1;min-width:0;padding:10px 8px;border-radius:10px;cursor:pointer;' +
        'font:inherit;font-size:13px;font-weight:700;background:var(--bg);' +
        'border:1px solid var(--border);color:var(--text)">' +
        esc(c.label) + ' <span style="color:var(--muted);font-weight:600;font-size:11px">' +
        c.touche.toUpperCase() + '</span></button>';
    }).join('');
    return '' +
      '<div class="mpb" style="margin-bottom:16px">' +
      '  <div style="font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;' +
      '       color:var(--muted);margin-bottom:6px">Poste de déroulement</div>' +
      '  <div class="mpb-tete" style="font-size:13px;font-weight:700;color:' +
      (poste.trouve ? 'var(--accent)' : 'var(--text)') + ';margin-bottom:4px">' + esc(tete) + '</div>' +
      (poste.explication && poste.trouve
        ? '  <div style="font-size:12px;color:var(--text2);line-height:1.5;margin-bottom:8px">' +
          esc(poste.explication) + '</div>'
        : '') +
      '  <div style="display:flex;gap:6px">' + boutons + '</div>' +
      '</div>';
  }

  function bind(root, poste) {
    if (!root || !poste) {
      return { get: function () { return {}; }, manque: function () { return false; }, detach: function () {} };
    }
    var choix = poste.categorie || null;
    // L'écran a proposé une nature : tant que l'opérateur ne la change pas,
    // la source reste celle de la détection. Dès qu'il clique ailleurs, c'est
    // une saisie — même logique que pour le fournisseur.
    var source = choix ? (poste.source || 'saisie') : null;
    var confiance = choix ? (poste.confiance || 'aucune') : null;
    var btns = root.querySelectorAll('.mpb-btn');

    function peindre() {
      for (var i = 0; i < btns.length; i++) {
        var b = btns[i];
        var actif = b.getAttribute('data-cat') === choix;
        var cat = CATS.filter(function (c) { return c.code === b.getAttribute('data-cat'); })[0];
        var surPoste = !choix && poste.trouve && cat && cat.poste === poste.poste;
        b.style.background = actif ? 'var(--accent-bg)' : 'var(--bg)';
        b.style.borderColor = actif || surPoste ? 'var(--accent)' : 'var(--border)';
        b.style.color = actif ? 'var(--accent)' : 'var(--text)';
      }
    }
    function choisir(cat) {
      if (cat === choix) return;
      choix = cat;
      source = 'saisie';
      confiance = 'certain';
      peindre();
    }
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener('click', function (e) {
        choisir(e.currentTarget.getAttribute('data-cat'));
      });
    }
    function clavier(e) {
      var t = e.target;
      if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.isContentEditable)) return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      var k = String(e.key || '').toLowerCase();
      var c = CATS.filter(function (x) { return x.touche === k; })[0];
      if (c) { e.preventDefault(); choisir(c.code); }
    }
    document.addEventListener('keydown', clavier, true);
    peindre();

    return {
      // Champs à joindre au POST /api/fabrication/matieres.
      get: function () {
        return choix ? { categorie_bobine: choix, poste_source: source, poste_confiance: confiance } : {};
      },
      // Vrai quand la nature est inconnue ET que le poste l'est aussi.
      manque: function () { return !choix && !poste.trouve; },
      detach: function () { document.removeEventListener('keydown', clavier, true); },
    };
  }

  window.MysPosteBobine = { html: html, bind: bind };
})();

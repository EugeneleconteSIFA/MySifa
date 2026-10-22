/* Fiche d'une note de frais : la même consultation dans Mon coffre (/coffre)
 * et dans Coffre RH (/rh/coffre).
 *
 *   const f = MySifaNdfFiche.ouvrir(note, {
 *     salarie: true,                 // affiche le nom du salarié (Coffre RH)
 *     actions: [{cle:'valider', label:'Valider', style:'primaire'|'secondaire'|'danger'}],
 *     surAction: async (cle) => true,   // true = fermer la fiche après l'action
 *     surFermer: () => {},              // fermeture par l'utilisateur
 *   });
 *   f.fermer(true);                     // fermeture technique, sans surFermer
 *
 * `note` est une ligne des API /api/coffre/notes-frais ou /api/rh-coffre/ndf.
 * Le justificatif s'ouvre par data-preview-url : chaque page a déjà son aperçu.
 * Le badge de statut reprend les classes .statut de la page.
 *
 *   MySifaNdfFiche.cartes(notes, {salarie: true, ouvrir: 'ouvrirNoteRh'})
 *
 * rend la liste en cartes regroupées par mois (téléphone). La page enveloppe
 * son tableau dans .ndf-tableau : sous 640 px, le tableau se masque et les
 * cartes prennent sa place. `ouvrir` est le nom de la fonction de la page qui
 * ouvre la fiche d'une note.
 */
(function () {
  'use strict';

  var STATUTS = { brouillon: 'Brouillon', soumise: 'Soumise', validee: 'Validée', payee: 'Payée', refusee: 'Refusée' };
  var MOIS = ['', 'Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'];

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function montant(n) {
    return (Number(n) || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' €';
  }
  function nombre(n) {
    return (Number(n) || 0).toLocaleString('fr-FR', { maximumFractionDigits: 3 });
  }
  function date(s) {
    if (!s) return '';
    var d = new Date(String(s).substr(0, 10));
    return isNaN(d) ? s : d.toLocaleDateString('fr-FR');
  }
  function taux(t) { return t ? String(t).replace('.', ',') + ' %' : 'Sans TVA'; }

  function injecterStyle() {
    if (document.getElementById('nf-style')) return;
    var st = document.createElement('style');
    st.id = 'nf-style';
    st.textContent = [
      '.nf-back{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:400;display:flex;align-items:center;justify-content:center;padding:16px}',
      '.nf-modal{background:var(--card);border:1px solid var(--border);border-radius:14px;max-width:520px;width:100%;max-height:90vh;overflow:auto;box-shadow:0 24px 64px rgba(0,0,0,.35);color:var(--text)}',
      '.nf-head{display:flex;align-items:center;gap:12px;padding:18px 22px 14px;border-bottom:1px solid var(--border)}',
      '.nf-ico{width:34px;height:34px;flex-shrink:0;border-radius:9px;background:var(--bg);border:1px solid var(--border);color:var(--text2);display:flex;align-items:center;justify-content:center}',
      '.nf-head h3{margin:0;font-size:16px;font-weight:700}',
      '.nf-sub{font-size:12px;color:var(--muted);margin-top:2px}',
      '.nf-head .statut{margin-left:auto}',
      '.nf-close{width:32px;height:32px;flex-shrink:0;border-radius:8px;border:1px solid var(--border);background:var(--bg);color:var(--text2);cursor:pointer;font-size:18px;line-height:1;font-family:inherit}',
      '.nf-close:hover{background:var(--card);color:var(--accent);border-color:var(--accent)}',
      '.nf-body{padding:18px 22px 2px}',
      '.nf-section+.nf-section{border-top:1px solid var(--border);padding-top:16px}',
      '.nf-titre{font-size:13px;font-weight:700;margin-bottom:12px}',
      '.nf-dl{display:grid;grid-template-columns:140px 1fr;gap:8px 14px;font-size:13px;margin:0 0 16px}',
      '.nf-dl dt{color:var(--muted);font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;padding-top:2px}',
      '.nf-dl dd{margin:0;white-space:pre-wrap;word-break:break-word}',
      '.nf-total{font-weight:700;font-variant-numeric:tabular-nums}',
      '.nf-vide{font-size:12px;color:var(--muted);margin:0 0 16px}',
      '.nf-resume{padding:4px 0 18px;margin-bottom:16px;border-bottom:1px solid var(--border)}',
      '.nf-montant{font-size:28px;font-weight:800;letter-spacing:-.5px;font-variant-numeric:tabular-nums;line-height:1.1}',
      '.nf-montant span{font-size:12px;font-weight:600;color:var(--muted);margin-left:6px;letter-spacing:0}',
      '.nf-puces{display:flex;flex-wrap:wrap;gap:6px;margin-top:10px}',
      '.nf-puce{display:inline-flex;align-items:center;padding:4px 10px;border-radius:999px;border:1px solid var(--border);background:var(--bg);font-size:12px;font-weight:600;color:var(--text2);font-variant-numeric:tabular-nums}',
      '.nf-puce:first-child{color:var(--text)}',
      '.nf-frise{list-style:none;margin:0 0 14px;padding:0;display:grid;grid-template-columns:repeat(4,1fr);position:relative}',
      '.nf-frise li{display:flex;flex-direction:column;align-items:center;text-align:center;gap:4px;position:relative;font-size:12px}',
      '.nf-frise li::before{content:"";position:absolute;top:6px;left:-50%;width:100%;height:2px;background:var(--border);z-index:0}',
      '.nf-frise li:first-child::before{display:none}',
      '.nf-frise li.fait::before,.nf-frise li.refus::before{background:var(--accent)}',
      '.nf-point{width:14px;height:14px;border-radius:50%;border:2px solid var(--border);background:var(--card);position:relative;z-index:1}',
      '.nf-frise li.fait .nf-point{background:var(--accent);border-color:var(--accent)}',
      '.nf-frise li.courante .nf-point{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}',
      '.nf-frise li.refus .nf-point{background:var(--danger);border-color:var(--danger)}',
      '.nf-etape{font-weight:600;color:var(--muted)}',
      '.nf-frise li.fait .nf-etape,.nf-frise li.courante .nf-etape{color:var(--text)}',
      '.nf-frise li.refus .nf-etape{color:var(--danger)}',
      '.nf-date{font-size:11px;color:var(--muted);min-height:14px}',
      '.nf-refus{margin:0 0 14px;padding:10px 12px;border-radius:8px;border:1px solid color-mix(in srgb,var(--danger) 35%,var(--border));font-size:13px;color:var(--text)}',
      '.nf-refus strong{display:block;font-size:11px;text-transform:uppercase;letter-spacing:.5px;color:var(--danger);margin-bottom:2px}',
      '.nf-par{font-size:12px;color:var(--muted);margin:-6px 0 14px;text-align:center}',
      '.nf-justif{display:flex;align-items:center;gap:12px;padding:8px;margin-bottom:16px;border:1px solid var(--border);border-radius:10px;background:var(--bg);color:var(--text);text-decoration:none}',
      '.nf-justif:hover{border-color:var(--accent)}',
      '.nf-justif img,.nf-justif-doc{width:56px;height:56px;flex-shrink:0;border-radius:6px;border:1px solid var(--border);object-fit:cover;background:var(--card)}',
      '.nf-justif-doc{display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--muted)}',
      '.nf-justif-nom{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}',
      '.nf-justif-nom strong{font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}',
      '.nf-justif-nom span{font-size:11px;color:var(--muted)}',
      '.nf-justif-voir{font-size:12px;font-weight:700;color:var(--accent);padding:0 6px}',
      '.nf-foot{display:flex;gap:8px;align-items:center;flex-wrap:wrap;padding:14px 22px;border-top:1px solid var(--border);position:sticky;bottom:0;background:var(--card)}',
      '.nf-foot .nf-sep{flex:1}',
      '.nf-btn{padding:9px 16px;border-radius:10px;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s,background .15s}',
      '.nf-btn.primaire{border:none;background:var(--accent);color:white}',
      '.nf-btn.primaire:hover{filter:brightness(1.08)}',
      '.nf-btn.secondaire{border:1px solid var(--border);background:var(--bg);color:var(--text2)}',
      '.nf-btn.secondaire:hover{background:var(--card);border-color:var(--accent);color:var(--accent)}',
      '.nf-btn.danger{border:1px solid var(--border);background:var(--bg);color:var(--danger)}',
      '.nf-btn.danger:hover{border-color:var(--danger);background:var(--card)}',
      '.nf-btn:disabled{opacity:.5;cursor:default}',
      '.nf-modal{overflow-x:hidden;overscroll-behavior:contain}.nf-modal *{box-sizing:border-box}',
      '.ndf-cartes{display:none}',
      '.ndf-mois+.ndf-mois{margin-top:16px}',
      '.ndf-mois-tete{display:flex;justify-content:space-between;gap:8px;padding:0 2px 6px;font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}',
      '.ndf-carte{display:flex;flex-direction:column;gap:6px;width:100%;text-align:left;padding:12px;margin-bottom:8px;border:1px solid var(--border);border-radius:10px;background:var(--bg);color:var(--text);font-family:inherit;cursor:pointer;box-sizing:border-box}',
      '.ndf-carte:active{border-color:var(--accent)}',
      '.ndf-carte-l1,.ndf-carte-l2{display:flex;justify-content:space-between;align-items:center;gap:10px}',
      '.ndf-carte-cat{font-size:14px;font-weight:600;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      '.ndf-carte-mt{font-size:14px;font-weight:700;font-variant-numeric:tabular-nums;white-space:nowrap}',
      '.ndf-carte-l2{font-size:12px;color:var(--muted)}',
      '.ndf-carte-l2>span:first-child{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
      '.ndf-carte-refus{font-size:12px;color:var(--danger)}',
      '@media(max-width:640px){.ndf-tableau{display:none}.ndf-cartes{display:block}}',
      'html:has(.nf-back),html:has(.nf-back) body{overflow:hidden}',
      '@media(max-width:640px){.nf-back{padding:10px}.nf-head,.nf-body,.nf-foot{padding-left:16px;padding-right:16px}' +
        '.nf-dl{grid-template-columns:1fr;gap:2px}.nf-dl dd{margin-bottom:8px}' +
        '.nf-foot{display:grid;grid-template-columns:1fr 1fr;gap:8px}.nf-foot .nf-sep{display:none}.nf-foot .nf-btn{width:100%;white-space:nowrap;padding:11px 8px}' +
        '.nf-foot .nf-btn.primaire{grid-column:1/-1;order:-1}}'
    ].join('\n');
    document.head.appendChild(st);
  }

  // Frise de suivi : Créée → Soumise → Validée (ou Refusée) → Payée.
  function frise(n) {
    var refusee = n.statut === 'refusee';
    // Le statut fait foi : une note payée a forcément été soumise et validée.
    var rang = { brouillon: 0, soumise: 1, refusee: 1, validee: 2, payee: 3 }[n.statut] || 0;
    var etapes = [
      { lib: 'Créée', date: n.created_at, fait: true },
      { lib: 'Soumise', date: n.soumise_at, fait: rang >= 1 },
      refusee
        ? { lib: 'Refusée', date: null, fait: true, refus: true }
        : { lib: 'Validée', date: n.validee_at, fait: rang >= 2 },
      { lib: 'Payée', date: n.payee_at, fait: rang >= 3 }
    ];
    var courante = refusee ? -1 : etapes.findIndex(function (x) { return !x.fait; });
    return '<ol class="nf-frise">' + etapes.map(function (x, i) {
      var cls = x.refus ? 'refus' : (x.fait ? 'fait' : (i === courante ? 'courante' : ''));
      return '<li class="' + cls + '"><span class="nf-point"></span><span class="nf-etape">' + esc(x.lib) + '</span>' +
        '<span class="nf-date">' + (x.date ? esc(date(x.date)) : (i === courante ? 'en attente' : '')) + '</span></li>';
    }).join('') + '</ol>' +
      (refusee && n.motif_refus ? '<div class="nf-refus"><strong>Motif du refus</strong>' + esc(n.motif_refus) + '</div>' : '') +
      (n.validee_by_nom && n.validee_at ? '<div class="nf-par">Validée par ' + esc(n.validee_by_nom) + '</div>' : '');
  }

  function corps(n, opts) {
    var km = n.distance_km != null;
    var puces = [esc(n.categorie || 'Note de frais')];
    if (km) {
      puces.push(esc(nombre(n.distance_km)) + ' km × ' + esc(nombre(n.taux_km)) + ' €');
      puces.push('Sans TVA');
    } else {
      puces.push(n.taux_tva ? 'TVA ' + esc(taux(n.taux_tva)) + ' · ' + montant(n.montant_tva) : 'Sans TVA');
      if (n.montant_ht != null) puces.push('HT ' + montant(n.montant_ht));
    }
    var just = '/api/coffre/notes-frais/' + encodeURIComponent(n.id) + '/justificatif';
    var image = /\.(png|jpe?g|gif|webp|heic)$/i.test(n.justificatif_nom || '');
    var details =
      (opts.salarie ? '<dt>Salarié</dt><dd>' + esc(n.employe_nom || '—') + (n.matricule ? ' · ' + esc(n.matricule) : '') + '</dd>' : '') +
      '<dt>Date du frais</dt><dd>' + esc(date(n.date_frais)) + '</dd>' +
      (n.ville ? '<dt>Ville</dt><dd>' + esc(n.ville) + '</dd>' : '') +
      (n.description ? '<dt>Description</dt><dd>' + esc(n.description) + '</dd>' : '');
    return '' +
      '<div class="nf-resume">' +
        '<div class="nf-montant">' + montant(n.montant_ttc) + '<span>TTC</span></div>' +
        '<div class="nf-puces">' + puces.map(function (p) { return '<span class="nf-puce">' + p + '</span>'; }).join('') + '</div>' +
      '</div>' +
      '<div class="nf-section"><div class="nf-titre">Suivi</div>' + frise(n) + '</div>' +
      '<div class="nf-section"><div class="nf-titre">Détails</div><dl class="nf-dl">' + details + '</dl></div>' +
      '<div class="nf-section"><div class="nf-titre">Justificatif</div>' +
        (n.justificatif_nom
          ? '<a class="nf-justif" href="' + esc(just) + '" data-preview-url="' + esc(just) + '" data-preview-name="' + esc(n.justificatif_nom) + '">' +
              (image ? '<img alt="" src="' + esc(just) + '?inline=1">' : '<span class="nf-justif-doc">PDF</span>') +
              '<span class="nf-justif-nom"><strong>' + esc(n.justificatif_nom) + '</strong><span>Justificatif joint à la note</span></span>' +
              '<span class="nf-justif-voir">Voir</span>' +
            '</a>'
          : '<p class="nf-vide">Aucun justificatif joint.</p>') +
      '</div>';
  }

  function ouvrir(n, opts) {
    opts = opts || {};
    injecterStyle();
    var actions = opts.actions || [];
    var back = document.createElement('div');
    back.className = 'nf-back';
    var titre = n.categorie || 'Note de frais';
    var sous = [date(n.date_frais), opts.salarie ? n.employe_nom : n.ville].filter(Boolean).join(' · ');
    var gauche = actions.filter(function (a) { return a.style === 'danger'; });
    var droite = actions.filter(function (a) { return a.style !== 'danger'; });
    function bouton(a) {
      return '<button type="button" class="nf-btn ' + esc(a.style || 'secondaire') + '" data-nf="' + esc(a.cle) + '">' + esc(a.label) + '</button>';
    }
    back.innerHTML =
      '<div class="nf-modal" role="dialog" aria-modal="true" aria-label="Note de frais">' +
        '<div class="nf-head">' +
          '<div class="nf-ico"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="5" width="20" height="14" rx="2"/><line x1="2" y1="10" x2="22" y2="10"/></svg></div>' +
          '<div><h3>' + esc(titre) + '</h3><div class="nf-sub">' + esc(sous) + '</div></div>' +
          '<span class="statut ' + esc(n.statut) + '">' + esc(STATUTS[n.statut] || n.statut) + '</span>' +
          '<button type="button" class="nf-close" data-nf="fermer" aria-label="Fermer">×</button>' +
        '</div>' +
        '<div class="nf-body">' + corps(n, opts) + '</div>' +
        (actions.length
          ? '<div class="nf-foot">' + gauche.map(bouton).join('') + '<span class="nf-sep"></span>' + droite.map(bouton).join('') + '</div>'
          : '') +
      '</div>';
    document.body.appendChild(back);

    var clos = false;
    function fermer(technique) {
      if (clos) return;
      clos = true;
      back.remove();
      document.removeEventListener('keydown', surTouche);
      if (!technique && typeof opts.surFermer === 'function') opts.surFermer();
    }
    function surTouche(e) {
      // Une confirmation ou un aperçu ouvert par-dessus garde la main sur Échap.
      if (e.key === 'Escape' && !document.querySelector('.mysifa-cfm-ov, .preview-back')) fermer(false);
    }
    document.addEventListener('keydown', surTouche);
    back.addEventListener('click', async function (e) {
      if (e.target === back) { fermer(false); return; }
      var b = e.target.closest('[data-nf]');
      if (!b) return;
      var cle = b.getAttribute('data-nf');
      if (cle === 'fermer') { fermer(false); return; }
      if (typeof opts.surAction !== 'function') return;
      b.disabled = true;
      try {
        if (await opts.surAction(cle)) fermer(false);
      } finally {
        if (!clos) b.disabled = false;
      }
    });
    return { fermer: fermer, element: back };
  }

  function cartes(liste, opts) {
    opts = opts || {};
    injecterStyle();
    var ouvrirFn = /^[A-Za-z_$][\w$]*$/.test(opts.ouvrir || '') ? opts.ouvrir : 'void';
    var groupes = [];
    (liste || []).forEach(function (n) {
      var cle = String(n.date_frais || '').slice(0, 7);
      var g = groupes.find(function (x) { return x.cle === cle; });
      if (!g) { g = { cle: cle, lignes: [], total: 0 }; groupes.push(g); }
      g.lignes.push(n);
      g.total += Number(n.montant_ttc) || 0;
    });
    return '<div class="ndf-cartes">' + groupes.map(function (g) {
      var am = g.cle.split('-');
      var titre = am[1] ? (MOIS[Number(am[1])] || am[1]) + ' ' + am[0] : 'Sans date';
      var resume = g.lignes.length + (g.lignes.length > 1 ? ' notes · ' : ' note · ') + montant(g.total);
      return '<div class="ndf-mois"><div class="ndf-mois-tete"><span>' + esc(titre) + '</span><span>' + esc(resume) + '</span></div>' +
        g.lignes.map(function (n) {
          // Coffre RH : le salarié d'abord (c'est lui que la compta cherche),
          // Mon coffre : la catégorie.
          var titreCarte = opts.salarie ? (n.employe_nom || '—') : (n.categorie || 'Note de frais');
          var sous = opts.salarie
            ? [n.categorie, date(n.date_frais)]
            : [date(n.date_frais), n.ville];
          return '<button type="button" class="ndf-carte" onclick="' + ouvrirFn + '(' + Number(n.id) + ')">' +
            '<span class="ndf-carte-l1"><span class="ndf-carte-cat">' + esc(titreCarte) + '</span><span class="ndf-carte-mt">' + montant(n.montant_ttc) + '</span></span>' +
            '<span class="ndf-carte-l2"><span>' + esc(sous.filter(Boolean).join(' · ')) + '</span>' +
              '<span class="statut ' + esc(n.statut) + '">' + esc(STATUTS[n.statut] || n.statut) + '</span></span>' +
            (n.motif_refus ? '<span class="ndf-carte-refus">Refus : ' + esc(n.motif_refus) + '</span>' : '') +
          '</button>';
        }).join('') + '</div>';
    }).join('') + '</div>';
  }

  window.MySifaNdfFiche = { ouvrir: ouvrir, cartes: cartes, STATUTS: STATUTS };
})();

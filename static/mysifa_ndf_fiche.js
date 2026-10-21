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
 */
(function () {
  'use strict';

  var STATUTS = { brouillon: 'Brouillon', soumise: 'Soumise', validee: 'Validée', payee: 'Payée', refusee: 'Refusée' };

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
      '.nf-suivi{list-style:none;margin:0 0 12px;padding:0;font-size:13px}',
      '.nf-suivi li{display:flex;gap:10px;padding:6px 0;color:var(--text2)}',
      '.nf-suivi li::before{content:"";width:7px;height:7px;border-radius:50%;background:var(--border);margin-top:6px;flex-shrink:0}',
      '.nf-suivi li.fait::before{background:var(--accent)}',
      '.nf-suivi li.refus{color:var(--danger)}',
      '.nf-suivi li.refus::before{background:var(--danger)}',
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
      '.nf-lien{display:inline-flex;align-items:center;gap:6px;padding:6px 10px;border-radius:7px;border:1px solid var(--border);background:var(--bg);color:var(--text2);font-size:12px;font-weight:600;text-decoration:none}',
      '.nf-lien:hover{border-color:var(--accent);color:var(--accent)}',
      '@media(max-width:640px){.nf-dl{grid-template-columns:1fr;gap:2px}.nf-dl dd{margin-bottom:8px}}'
    ].join('\n');
    document.head.appendChild(st);
  }

  function corps(n, opts) {
    var km = n.distance_km != null;
    var lignesMontant = km
      ? '<dt>Distance</dt><dd>' + esc(nombre(n.distance_km)) + ' km × ' + esc(nombre(n.taux_km)) + ' €</dd>' +
        '<dt>Montant</dt><dd class="nf-total">' + montant(n.montant_ttc) + '</dd>'
      : '<dt>Montant TTC</dt><dd class="nf-total">' + montant(n.montant_ttc) + '</dd>' +
        '<dt>TVA</dt><dd>' + (n.taux_tva != null ? esc(taux(n.taux_tva)) + ' · ' : '') + montant(n.montant_tva) + '</dd>' +
        (n.montant_ht != null ? '<dt>Montant HT</dt><dd>' + montant(n.montant_ht) + '</dd>' : '');
    var just = '/api/coffre/notes-frais/' + encodeURIComponent(n.id) + '/justificatif';
    var suivi = [
      '<li class="fait">Créée le ' + esc(date(n.created_at)) + '</li>',
      n.soumise_at ? '<li class="fait">Soumise à la comptabilité le ' + esc(date(n.soumise_at)) + '</li>'
        : (n.statut === 'brouillon' ? '<li>Pas encore soumise</li>' : ''),
      n.statut === 'refusee' ? '<li class="refus">Refusée' + (n.motif_refus ? ' : ' + esc(n.motif_refus) : '') + '</li>' : '',
      n.validee_at ? '<li class="fait">Validée le ' + esc(date(n.validee_at)) + (n.validee_by_nom ? ' par ' + esc(n.validee_by_nom) : '') + '</li>' : '',
      n.payee_at ? '<li class="fait">Payée le ' + esc(date(n.payee_at)) + (n.payee_by_nom && opts.salarie ? ' par ' + esc(n.payee_by_nom) : '') + '</li>' : ''
    ].join('');
    return '' +
      '<div class="nf-section"><div class="nf-titre">Le frais</div><dl class="nf-dl">' +
        (opts.salarie ? '<dt>Salarié</dt><dd>' + esc(n.employe_nom || '—') + (n.matricule ? ' · ' + esc(n.matricule) : '') + '</dd>' : '') +
        '<dt>Catégorie</dt><dd>' + esc(n.categorie || '—') + '</dd>' +
        '<dt>Date</dt><dd>' + esc(date(n.date_frais)) + '</dd>' +
        '<dt>Ville</dt><dd>' + esc(n.ville || '—') + '</dd>' +
        '<dt>Description</dt><dd>' + esc(n.description || '—') + '</dd>' +
      '</dl></div>' +
      '<div class="nf-section"><div class="nf-titre">Montant</div><dl class="nf-dl">' + lignesMontant + '</dl></div>' +
      '<div class="nf-section"><div class="nf-titre">Justificatif</div>' +
        (n.justificatif_nom
          ? '<div style="margin-bottom:16px"><a class="nf-lien" href="' + esc(just) + '" data-preview-url="' + esc(just) +
            '" data-preview-name="' + esc(n.justificatif_nom) + '">Voir ' + esc(n.justificatif_nom) + '</a></div>'
          : '<p class="nf-vide">Aucun justificatif joint.</p>') +
      '</div>' +
      '<div class="nf-section"><div class="nf-titre">Suivi</div><ul class="nf-suivi">' + suivi + '</ul></div>';
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

  window.MySifaNdfFiche = { ouvrir: ouvrir, STATUTS: STATUTS };
})();

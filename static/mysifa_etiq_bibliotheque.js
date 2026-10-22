/* MyTools › Étiquettes spécifiques — bibliothèque (EtiqSpec.biblio).
 *
 * Catégories par client et par usage (bobine, palette, carton, échantillon,
 * expédition), versions (historique, revenir à une version), validation des
 * modèles (soumettre, approuver par un rôle qualité, refuser avec motif —
 * la production imprime la version approuvée), compteurs mémorisés.
 *
 * Expose aussi, pour l'impression et le kiosque :
 *   EtiqSpec.modeleProduction(id)        → GET /modeles/{id}/production
 *   EtiqSpec.rendu(id, {enregistrement, source, index})  → POST /modeles/{id}/rendu
 *   EtiqSpec.modelesPourDossier(ref, usage)  → GET /production/pour-dossier
 */
(function () {
  'use strict';
  const X = () => window.EtiqSpec._;
  const E = () => window.EtiqSpec.editeur.api;

  function usageLibelle(id) { return ((X().ES.boot.referentiel.usages || []).find(u => u.id === id) || {}).libelle || ''; }

  // ── Filtres de la liste ─────────────────────────────────────────────
  function filtrer(liste) {
    const ES = X().ES;
    return liste.filter(m => (!ES.usage || m.usage === ES.usage) && (!ES.client || (m.client || '').toLowerCase() === ES.client.toLowerCase()));
  }
  function barreFiltres() {
    const { h, ES, rendre } = X();
    const usages = ES.boot.referentiel.usages || [];
    const clients = [...new Set(ES.boot.modeles.map(m => m.client).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'fr'));
    const cl = h('select', { cls: 'es-input es-court-l', 'aria-label': 'Client', 'data-bulle': 'Client' }, h('option', { value: '', text: 'Tous les clients' }), ...clients.map(c => h('option', { value: c, text: c })));
    cl.value = ES.client || '';
    cl.addEventListener('change', () => { ES.client = cl.value || null; rendre(); });
    return h('div', { cls: 'es-filtres' },
      h('div', { cls: 'es-puces' },
        h('button', { cls: 'es-puce' + (!ES.usage ? ' actif' : ''), type: 'button', text: 'Tous usages', onclick: () => { ES.usage = null; rendre(); } }),
        ...usages.map(u => h('button', { cls: 'es-puce' + (ES.usage === u.id ? ' actif' : ''), type: 'button', text: u.libelle, 'data-bulle': 'Filtrer',
          onclick: () => { ES.usage = ES.usage === u.id ? null : u.id; rendre(); } }))),
      clients.length ? cl : null);
  }
  function infosCarte(m) {
    const { h } = X();
    const st = m.statut_validation || 'brouillon';
    return h('div', { cls: 'es-carte-tags' },
      m.usage ? h('span', { cls: 'es-tag', text: usageLibelle(m.usage) }) : null,
      m.client ? h('span', { cls: 'es-tag', text: m.client }) : null,
      h('span', { cls: 'es-statut es-valid-' + st, text: (X().ES.boot.referentiel.statuts_validation || {})[st] || st }),
      h('span', { cls: 'es-aide', text: 'v' + (m.version || 1) + (m.version_approuvee && m.version_approuvee !== m.version ? ' · production v' + m.version_approuvee : '') }));
  }

  // ── Validation ──────────────────────────────────────────────────────
  function badgeValidation(m) {
    const { h } = X();
    const st = m.statut_validation || 'brouillon';
    const lib = (X().ES.boot.referentiel.statuts_validation || {})[st] || st;
    return h('button', { cls: 'es-statut es-valid-' + st + ' es-statut-btn', type: 'button', 'data-bulle': 'Validation',
      'aria-label': 'Validation : ' + lib, onclick: () => modaleApprobation(m) },
      lib + (m.version_approuvee ? (m.version_approuvee === m.version ? ' · v' + m.version : ` · production v${m.version_approuvee}`) : ' · jamais approuvée'));
  }
  function boutonsEditeur(m) {
    const { bouton } = X();
    return [bouton('Versions', () => modaleVersions(m), '', 'clock')];
  }
  async function modaleApprobation(m) {
    const { h, api, modale, fermerModale, bouton, toast, champ, fmtDate } = X();
    let d;
    try { d = await api('/modeles/' + m.id + '/approbations'); } catch (e) { toast(e.message, 'danger'); return; }
    const com = h('textarea', { cls: 'es-input', rows: 2, maxlength: 1000, placeholder: 'Commentaire (obligatoire pour un refus)' });
    const agir = (chemin, msg) => async () => {
      if (E().ED.m && E().ED.m.id === m.id && E().ED.dirty) { toast('Enregistrer avant de soumettre ou d\'approuver.', 'info'); return; }
      try {
        const r = await api('/modeles/' + m.id + '/' + chemin, { method: 'POST', body: { commentaire: com.value } });
        if (E().ED.m && E().ED.m.id === m.id) Object.assign(E().ED.m, { statut_validation: r.statut_validation, version_approuvee: r.version_approuvee });
        fermerModale(); toast(msg); await X().charger(); X().rendre();
      } catch (e) { toast(e.message, 'danger'); }
    };
    const ACTION = { demande: 'Soumise', approuve: 'Approuvée', refuse: 'Refusée' };
    const actions = [bouton('Fermer', fermerModale)];
    if (d.statut_validation !== 'approuve' && d.statut_validation !== 'a_approuver') actions.push(bouton('Soumettre à approbation', agir('soumettre', 'Version soumise à la qualité.'), '', 'send'));
    if (d.peut_approuver && d.statut_validation !== 'approuve') {
      actions.push(bouton('Refuser', agir('refuser', 'Version refusée.'), 'danger', 'x'), bouton('Approuver la version ' + d.version, agir('approuver', 'Version approuvée : c\'est elle que la production imprime.'), 'accent', 'check'));
    }
    X().ES.adresseModale = { cle: 'approbation', id: m.id };
    modale('Validation — ' + m.nom, h('div', { cls: 'es-form' },
      h('p', { cls: 'es-texte', text: d.version_approuvee
        ? `La production imprime la version ${d.version_approuvee}${d.approuve_par ? ', approuvée par ' + d.approuve_par.split('@')[0] + ' le ' + fmtDate(d.approuve_le) : ''}. Version en cours : ${d.version} (${d.statut_libelle.toLowerCase()}).`
        : `Jamais approuvée : impossible à imprimer. Version en cours : ${d.version}.` }),
      d.peut_approuver ? null : h('p', { cls: 'es-aide', text: 'L\'approbation est réservée aux rôles qualité ; elle se fait par une autre personne que l\'auteur de la modification.' }),
      champ('Commentaire', com),
      h('div', { cls: 'es-table-wrap' }, d.historique.length ? h('table', { cls: 'es-table' },
        h('thead', {}, h('tr', {}, ...['Date', 'Version', 'Action', 'Par', 'Commentaire'].map(t => h('th', { text: t })))),
        h('tbody', {}, ...d.historique.map(r => h('tr', {}, h('td', { text: fmtDate(r.le) }), h('td', { text: 'v' + r.version }),
          h('td', { text: ACTION[r.action] || r.action }), h('td', { text: (r.par || '').split('@')[0] }), h('td', { text: r.commentaire || '' })))))
        : h('div', { cls: 'es-aide', text: 'Aucun historique.' }))), actions, true);
  }

  // ── Versions ────────────────────────────────────────────────────────
  async function modaleVersions(m) {
    const { h, api, modale, fermerModale, bouton, toast, fmtDate, confirmer } = X();
    let d;
    try { d = await api('/modeles/' + m.id + '/versions'); } catch (e) { toast(e.message, 'danger'); return; }
    const apercu = h('div', { cls: 'es-version-apercu' }, h('div', { cls: 'es-aide', text: 'Choisir une version pour la voir.' }));
    const voir = async (v) => {
      try {
        const r = v.actuelle ? await api('/modeles/' + m.id) : await api('/modeles/' + m.id + '/versions/' + v.version);
        const lay = E().completerLayout(r.layout);
        const vals = window.EtiqMoteur.valeurs(lay, { systeme: { fsc_licence: X().ES.boot.referentiel.fsc_licence } });
        apercu.replaceChildren(E().construireSvg({ largeur_mm: r.largeur_mm, hauteur_mm: r.hauteur_mm }, lay, false, vals),
          h('div', { cls: 'es-aide', text: `Version ${v.version} · ${X().fmtNum(r.largeur_mm)} × ${X().fmtNum(r.hauteur_mm)} mm` }));
      } catch (e) { toast(e.message, 'danger'); }
    };
    const restaurer = (v) => confirmer(`Revenir à la version ${v.version} ? Elle devient une nouvelle version, à faire approuver ; l'historique est conservé.`, 'Revenir', async () => {
      const r = await api('/modeles/' + m.id + '/versions/' + v.version + '/restaurer', { method: 'POST', body: {} });
      toast(`Version ${v.version} rétablie (nouvelle version ${r.version}).`);
      await X().charger();
      if (E().ED.m && E().ED.m.id === m.id) { await window.EtiqSpec.editeur.ouvrir(r); }
      X().rendre();
    });
    X().ES.adresseModale = { cle: 'versions_etiq', id: m.id };
    modale('Versions — ' + m.nom, h('div', { cls: 'es-versions' },
      h('div', { cls: 'es-table-wrap' }, h('table', { cls: 'es-table' },
        h('thead', {}, h('tr', {}, ...['Version', 'Date', 'Par', 'Objets', ''].map(t => h('th', { text: t })))),
        h('tbody', {}, ...d.versions.map(v => h('tr', { cls: 'es-ligne-cliquable', onclick: () => voir(v) },
          h('td', {}, 'v' + v.version, v.actuelle ? h('span', { cls: 'es-tag', text: 'en cours' }) : null, v.version === m.version_approuvee ? h('span', { cls: 'es-tag es-tag-ok', text: 'production' }) : null),
          h('td', { text: fmtDate(v.created_at) }), h('td', { text: (v.created_by || '').split('@')[0] }),
          h('td', { text: `${v.nb_elements} obj. · ${v.nb_variables} var.` }),
          h('td', {}, v.actuelle ? null : bouton('Revenir', (ev) => { ev.stopPropagation(); restaurer(v); }, '', 'rotate-ccw'))))))),
      apercu), [bouton('Fermer', fermerModale)], true);
    voir(d.versions[0]);
  }

  // ── Compteurs mémorisés ─────────────────────────────────────────────
  async function modaleCompteurs(m) {
    const { h, api, modale, fermerModale, bouton, toast, fmtDate } = X();
    let d;
    try { d = await api('/modeles/' + m.id + '/compteurs'); } catch (e) { toast(e.message, 'danger'); return; }
    X().ES.adresseModale = { cle: 'compteurs', id: m.id };
    modale('Numérotation — ' + m.nom, h('div', { cls: 'es-form' },
      ...(d.compteurs.length ? d.compteurs.map(c => {
        const i = h('input', { cls: 'es-input es-court-l', type: 'number', min: 0, value: c.dernier ?? '' });
        return h('div', { cls: 'es-encart' }, h('div', { cls: 'es-encart-titre', text: c.libelle + (c.type === 'sscc' ? ' (SSCC)' : '') }),
          h('div', { cls: 'es-aide', text: (c.dernier == null ? 'Jamais imprimé.' : `Dernier numéro émis : ${c.dernier}` + (c.maj_le ? ` (${fmtDate(c.maj_le)}, ${(c.maj_par || '').split('@')[0]})` : '')) + ` · Prochain : ${c.prochain || '—'}` + (c.reprise === false ? ' · repart du départ à chaque impression' : '') }),
          c.type === 'compteur' ? h('div', { cls: 'es-ligne-champ' }, i, bouton('Corriger', async () => {
            try { await api('/modeles/' + m.id + '/compteurs/' + encodeURIComponent(c.nom), { method: 'POST', body: { dernier: parseInt(i.value, 10) } }); toast('Compteur corrigé.'); modaleCompteurs(m); }
            catch (e) { toast(e.message, 'danger'); }
          }, '', 'save')) : h('div', { cls: 'es-aide', text: 'Un SSCC ne se corrige pas : revenir en arrière réémettrait un numéro déjà sorti.' }));
      }) : [h('div', { cls: 'es-aide', text: 'Aucun compteur ni SSCC sur cette étiquette.' })])), [bouton('Fermer', fermerModale)]);
  }

  // ── Accès publics (impression, kiosque) ─────────────────────────────
  const modeleProduction = (id) => X().api('/modeles/' + id + '/production');
  const rendu = (id, o) => X().api('/modeles/' + id + '/rendu', { method: 'POST', body: Object.assign({ enregistrement: {}, index: 0 }, o || {}) });
  const modelesPourDossier = (ref, usage) => X().api('/production/pour-dossier?dossier=' + encodeURIComponent(ref || '') + '&usage=' + encodeURIComponent(usage || ''));

  window.EtiqSpec = Object.assign(window.EtiqSpec || {}, {
    biblio: { filtrer, barreFiltres, infosCarte, badgeValidation, boutonsEditeur, modaleApprobation, modaleVersions, modaleCompteurs },
    modeleProduction, rendu, modelesPourDossier,
  });
})();

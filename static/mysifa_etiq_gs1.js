/* MyTools › Étiquettes spécifiques — GS1 et pictogrammes (EtiqSpec.gs1).
 *
 * - Étiquette logistique palette conforme GS1 (SSCC en bas, données en clair
 *   au milieu, AI 00, 02, 37, 10, 11, 15, 310x) : EtiqMoteur.etiquetteLogistique,
 *   SSCC fourni par le client (saisie contrôlée) ou calculé sur la plage qu'il a confiée.
 * - Aide à la saisie des AI d'un code GS1-128 / GS1 DataMatrix, contrôle des
 *   longueurs, dates et clés en direct.
 * - Bibliothèque de pictogrammes réglementaires (SVG inline, primitives
 *   servies par /bootstrap).
 */
(function () {
  'use strict';
  const X = () => window.EtiqSpec._;
  const E = () => window.EtiqSpec.editeur.api;
  const MO = () => window.EtiqMoteur;
  const SVGNS = 'http://www.w3.org/2000/svg';

  function vignettePicto(nom, coul) {
    const ref = (X().ES.boot.referentiel.pictos || {})[nom];
    const svg = document.createElementNS(SVGNS, 'svg');
    svg.setAttribute('viewBox', '0 0 24 24'); svg.setAttribute('width', '48'); svg.setAttribute('height', '48');
    for (const p of (ref ? ref.primitives : [])) {
      const pts = (p.p || []).map(q => q.join(',')).join(' ');
      let n;
      if (p.t === 'ligne') { n = document.createElementNS(SVGNS, 'polyline'); n.setAttribute('points', pts); n.setAttribute('fill', 'none'); n.setAttribute('stroke', coul); n.setAttribute('stroke-width', p.e || 1); n.setAttribute('stroke-linecap', 'round'); }
      else if (p.t === 'poly') { n = document.createElementNS(SVGNS, 'polygon'); n.setAttribute('points', pts); n.setAttribute('fill', coul); }
      else if (p.t === 'cercle') { n = document.createElementNS(SVGNS, 'circle'); n.setAttribute('cx', p.c[0]); n.setAttribute('cy', p.c[1]); n.setAttribute('r', p.r); n.setAttribute('fill', p.e ? 'none' : coul); if (p.e) { n.setAttribute('stroke', coul); n.setAttribute('stroke-width', p.e); } }
      else if (p.t === 'texte') { n = document.createElementNS(SVGNS, 'text'); n.setAttribute('x', p.x); n.setAttribute('y', p.y); n.setAttribute('font-size', p.s); n.setAttribute('text-anchor', 'middle'); n.setAttribute('font-weight', '700'); n.setAttribute('fill', coul); n.textContent = p.v; }
      if (n) svg.appendChild(n);
    }
    return svg;
  }

  function modalePictos() {
    const { h, modale, fermerModale, bouton, ES } = X();
    const pictos = ES.boot.referentiel.pictos || {};
    ES.adresseModale = { cle: 'pictos', id: E().ED.m.id };
    modale('Pictogrammes réglementaires', h('div', { cls: 'es-form' },
      h('div', { cls: 'es-pictos' }, ...Object.entries(pictos).map(([k, p]) => h('button', { cls: 'es-picto-choix', type: 'button', 'data-bulle': 'Ajouter',
        'aria-label': 'Ajouter le pictogramme ' + p.libelle,
        onclick: () => { fermerModale(); E().ajouter('picto', { picto: k, legende: p.legende || '', hauteur: p.legende ? 15 : 12, nom: p.libelle }); } },
        vignettePicto(k, 'currentColor'), h('span', { text: p.libelle })))),
      h('p', { cls: 'es-aide', text: 'Manutention d\'après l\'ISO 780. Le logo FSC n\'est pas reproduit (marque déposée) : l\'objet réserve l\'emplacement et porte le numéro de licence. Le remplacer par l\'illustration officielle validée par l\'outil de marquage FSC.' })),
    [bouton('Fermer', fermerModale)]);
  }

  // Aide AI sous le champ « Données » d'un code GS1.
  function aideAi(e, ctx) {
    const { h } = X();
    const ai = (X().ES.boot.referentiel.gs1 || {}).ai || {};
    const vals = E().valeursApercu(E().layout());
    const erreurs = MO().controlerGs1(MO().substituer(e.valeur, vals));
    const ajout = (code) => {
      if (E().fige(e)) return;
      ctx.memoriser();
      const ex = { '00': '{{sscc}}', '01': '', '02': '', '10': '{{lot}}', '15': '', '17': '', '37': '{{quantite}}' }[code];
      e.valeur = (e.valeur || '') + '(' + code + ')' + (ex == null ? '' : ex);
      ctx.salir(); ctx.majPanneauElement(); ctx.dessiner();
    };
    return h('div', { cls: 'es-form' },
      h('div', { cls: 'es-puces' }, ...['00', '01', '02', '10', '11', '15', '17', '37', '3102', '400'].filter(k => ai[k]).map(k => h('button', {
        cls: 'es-puce', type: 'button', 'data-bulle': ai[k].libelle, 'aria-label': 'Ajouter l\'AI ' + k + ' ' + ai[k].libelle, text: '(' + k + ')', onclick: () => ajout(k) }))),
      erreurs.length ? h('ul', { cls: 'es-propo-remarques es-erreur' }, ...erreurs.map(m => h('li', { text: m }))) : h('div', { cls: 'es-aide es-ok', text: 'Données GS1 conformes (avec les valeurs de l\'aperçu).' }));
  }

  function modaleLogistique(mActuel) {
    const { h, champ, bouton, modale, fermerModale, api, toast, ES, selectDossiers } = X();
    const ref = ES.boot.referentiel;
    const AIS = [['02', 'GTIN du contenu (02)'], ['37', 'Nombre d\'unités (37)'], ['10', 'Lot (10)'], ['11', 'Date de fabrication (11)'],
      ['15', 'Date de durabilité minimale (15)'], ['3102', 'Poids net en kg (3102)']];
    const coches = {};
    const cases = AIS.map(([k, l]) => { const c = h('input', { type: 'checkbox', checked: ['02', '37', '10', '15'].includes(k) }); coches[k] = c; return h('label', { cls: 'es-case' }, c, h('span', { text: l })); });
    // D'où viennent les SSCC : le client les fournit (cas courant), ou il a
    // confié son préfixe GS1 et une plage de numéros.
    const origine = h('select', { cls: 'es-input' },
      h('option', { value: 'fourni', text: 'Le client fournit les numéros SSCC' }),
      h('option', { value: 'plage', text: 'Le client a confié son préfixe et une plage' }));
    const prefixe = h('input', { cls: 'es-input es-mono', maxlength: 10, value: '' });
    const ext = h('input', { cls: 'es-input', maxlength: 1, value: '0' });
    const debut = h('input', { cls: 'es-input', type: 'number', min: 0, value: '' });
    const fin = h('input', { cls: 'es-input', type: 'number', min: 0, value: '' });
    const zonePlage = h('div', { cls: 'es-form', hidden: true },
      h('div', { cls: 'es-ligne2' }, champ('Préfixe GS1 du client', prefixe, '7 à 10 chiffres'), champ('Extension SSCC', ext, '1 chiffre')),
      h('div', { cls: 'es-ligne2' }, champ('Première série', debut, 'Plage attribuée par le client'), champ('Dernière série', fin, 'Vide = sans borne')));
    const aideFourni = h('div', { cls: 'es-aide', text: 'Le SSCC est demandé à chaque impression : saisi, scanné ou repris d\'une série importée (liste du client). Il est contrôlé : 18 chiffres et clé de contrôle exacte.' });
    origine.addEventListener('change', () => { const pl = origine.value === 'plage'; zonePlage.hidden = !pl; aideFourni.hidden = pl; });
    const format = h('select', { cls: 'es-input' }, h('option', { value: '105x148', text: 'A6 · 105 × 148 mm' }), h('option', { value: '148x210', text: 'A5 · 148 × 210 mm' }), h('option', { value: '100x150', text: '100 × 150 mm' }));
    const nom = h('input', { cls: 'es-input', maxlength: 120, value: 'Palette SSCC' + (mActuel && mActuel.client ? ' ' + mActuel.client : '') });
    const dossier = selectDossiers((mActuel && mActuel.dossier_id) || (ES.boot.dossiers[0] || {}).id);
    const ok = bouton('Créer l\'étiquette', async () => {
      const fourni = origine.value === 'fourni';
      const pre = prefixe.value.replace(/\D/g, '');
      if (!fourni && (pre.length < 7 || pre.length > 10)) { toast('Préfixe GS1 du client : 7 à 10 chiffres.', 'danger'); return; }
      const [L, H] = format.value.split('x').map(Number);
      const g = MO().etiquetteLogistique({ largeur: L, hauteur: H, fourni, prefixe: pre, extension: ext.value.replace(/\D/g, '') || '0',
        serie_debut: parseInt(debut.value, 10) || 0, serie_fin: parseInt(fin.value, 10) || 0,
        ai: AIS.map(a => a[0]).filter(k => coches[k].checked) });
      ok.disabled = true;
      try {
        const r = await api('/modeles', { method: 'POST', body: { dossier_id: parseInt(dossier.value, 10), nom: nom.value, usage: 'palette',
          client: (mActuel && mActuel.client) || '', largeur_mm: g.largeur_mm, hauteur_mm: g.hauteur_mm, dpi: 203, layout: g.layout,
          description: 'Étiquette logistique palette GS1 : SSCC (00) en bas, données en clair au-dessus.' } });
        fermerModale(); toast('Étiquette logistique créée — à relire puis faire approuver.');
        await X().charger();
        await X().ouvrirEditeur(r.id);
      } catch (e) { toast(e.message, 'danger'); ok.disabled = false; }
    }, 'accent', 'check');
    if (!ES.boot.dossiers.length) { toast('Créer d\'abord un dossier.', 'info'); return; }
    ES.adresseModale = { cle: 'gs1_palette', id: (mActuel && mActuel.id) || 'nouvelle' };
    modale('Étiquette logistique palette (GS1)', h('div', { cls: 'es-form' },
      h('p', { cls: 'es-aide', text: 'Disposition des spécifications GS1 : expéditeur et destinataire en haut, données en clair au milieu, codes GS1-128 en bas, le SSCC toujours le plus bas (dimension X 0,5 mm, barres de 32 mm).' }),
      h('div', { cls: 'es-ligne2' }, champ('Nom', nom), champ('Dossier', dossier)),
      h('div', { cls: 'es-ligne2' }, champ('Format', format), champ('Numéros SSCC', origine)),
      aideFourni, zonePlage,
      h('div', { cls: 'es-champ' }, h('span', { cls: 'es-champ-label', text: 'Identifiants (AI)' }), ...cases)),
    [bouton('Annuler', fermerModale), ok]);
  }

  window.EtiqSpec = Object.assign(window.EtiqSpec || {}, { gs1: { modalePictos, modaleLogistique, aideAi, vignettePicto } });
})();

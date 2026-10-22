/* MyTools › Étiquettes spécifiques — contrôle avant impression (EtiqSpec.controle).
 *
 * Trois niveaux :
 *  1. Lisibilité des codes (EtiqMoteur.lisibilite) : module en points à la
 *     résolution de l'étiquette, dimension X conseillée, hauteur, zone de
 *     silence, distance aux bords, données GS1.
 *  2. Contrôles mécaniques (EtiqMoteur.controleLocal) : texte coupé, objet qui
 *     dépasse, texte blanc hors aplat, variable non remplacée, SSCC d'une
 *     palette, licence d'une mention FSC.
 *  3. Relecture par l'IA (violet, tracée dans ia_usage) : rendu PNG +
 *     mise en page → POST /ia/controler.
 * Et la comparaison avec l'étiquette de référence du client (image ou PDF
 * déposé) : superposition et écarts visuels surlignés, calculés dans le
 * navigateur.
 */
(function () {
  'use strict';
  const X = () => window.EtiqSpec._;
  const E = () => window.EtiqSpec.editeur.api;
  const MO = () => window.EtiqMoteur;
  const SVGNS = 'http://www.w3.org/2000/svg';
  const C = { ia: null, iaBusy: false, ref: null, refUrl: null, opacite: 0.5, ecarts: null, refVue: false };

  function alertesLocales() {
    const ED = E().ED, lay = E().layout(), m = ED.m;
    const vals = E().valeursApercu(lay);
    const boites = ED.boites || {};
    const out = MO().controleLocal(lay, vals, { L: m.largeur_mm, H: m.hauteur_mm, usage: m.usage }, boites);
    const visibles = lay.elements.filter(e => MO().visible(e, vals));
    for (const e of visibles.filter(x => x.type === 'code_barre')) {
      const b = boites[e.id];
      if (!b) continue;
      const voisins = visibles.filter(o => o !== e && boites[o.id]).map(o => Object.assign({ nom: o.nom || o.id }, boites[o.id]));
      const taille = { w: b.cw || b.w, h: b.ch || b.h };
      for (const a of MO().lisibilite(e, taille, { dpi: m.dpi, L: m.largeur_mm, H: m.hauteur_mm, voisins }, MO().substituer(e.valeur, vals))) out.push(Object.assign({ element_id: e.id }, a));
    }
    const rang = { bloquant: 0, attention: 1, info: 2 };
    return out.sort((a, b) => rang[a.gravite] - rang[b.gravite]);
  }

  function ligneAlerte(a) {
    const { h } = X();
    return h('div', { cls: 'es-alerte es-alerte-' + a.gravite, onclick: a.element_id ? () => { E().ED.sel = a.element_id; X().rendre(); } : null },
      h('span', { cls: 'es-alerte-g', text: { bloquant: 'Bloquant', attention: 'Attention', info: 'Info' }[a.gravite] }), h('span', { text: a.message }));
  }

  // Rendu PNG de l'étiquette (valeurs de l'aperçu), pour l'IA et la comparaison.
  function rendrePng(pxParMm) {
    return new Promise((ok, ko) => {
      const ED = E().ED, m = ED.m, lay = E().layout();
      const svg = E().construireSvg(m, lay, false, E().valeursApercu(lay));
      svg.setAttribute('viewBox', `0 0 ${m.largeur_mm} ${m.hauteur_mm}`);
      const w = Math.round(m.largeur_mm * pxParMm), hh = Math.round(m.hauteur_mm * pxParMm);
      svg.setAttribute('width', w); svg.setAttribute('height', hh);
      svg.setAttribute('xmlns', SVGNS);
      const url = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(new XMLSerializer().serializeToString(svg));
      const img = new Image();
      img.onload = () => { const c = document.createElement('canvas'); c.width = w; c.height = hh; const x = c.getContext('2d'); x.fillStyle = 'white'; x.fillRect(0, 0, w, hh); x.drawImage(img, 0, 0, w, hh); ok(c); };
      img.onerror = () => ko(new Error('Rendu de l\'étiquette impossible.'));
      img.src = url;
    });
  }

  async function controlerIa(btn, apres) {
    const { api, toast, selectModeleIa } = X();
    const ED = E().ED, m = ED.m, lay = E().layout();
    C.iaBusy = true;
    if (btn) { btn.disabled = true; btn.textContent = 'Claude relit l\'étiquette…'; btn.classList.add('ia-travail'); }
    try {
      const canvas = await rendrePng(8);
      const png = canvas.toDataURL('image/png');
      const vals = E().valeursApercu(lay);
      const modeleIa = selectModeleIa();
      C.ia = await api('/ia/controler', { method: 'POST', body: { modele_id: m.id, largeur_mm: m.largeur_mm, hauteur_mm: m.hauteur_mm, dpi: m.dpi,
        layout: E().nettoyer(lay), valeurs: Object.fromEntries(Object.entries(vals).filter(([k]) => !k.startsWith('_'))), usage: m.usage || '',
        alertes: alertesLocales().map(a => a.message), image_png: png, modele: modeleIa.select.value } });
    } catch (e) { toast(e.message, 'danger'); }
    C.iaBusy = false;
    if (apres) apres();
  }

  function blocIa(rerendre) {
    const { h, bouton } = X();
    const go = bouton(C.ia ? 'Relancer le contrôle' : 'Contrôler avec Claude', () => controlerIa(go, rerendre), 'ia', 'zap');
    const blocs = [h('div', { cls: 'es-panneau-titre' }, 'Relecture ', h('span', { cls: 'ia-badge', text: 'IA' })),
      h('div', { cls: 'ia-texte', text: 'Claude relit le rendu : mention obligatoire manquante, texte coupé, code illisible, contraste.' })];
    if (C.ia) {
      const v = { ok: 'Aucun défaut relevé.', a_corriger: 'À corriger avant impression.', bloquant: 'Impression déconseillée en l\'état.' }[C.ia.verdict];
      blocs.push(h('div', { cls: 'es-propo' }, h('div', { cls: 'es-propo-resume', text: v }), C.ia.resume ? h('div', { cls: 'es-aide', text: C.ia.resume }) : null,
        ...C.ia.points.map(ligneAlerte), h('div', { cls: 'es-aide', text: 'Relu par ' + C.ia.modele_libelle })));
    }
    blocs.push(h('div', { cls: 'es-ligne-actions' }, go));
    return h('div', { cls: 'es-form ia-zone es-encart' }, ...blocs);
  }

  // ── Comparaison avec l'étiquette de référence du client ────────────
  async function chargerReference() {
    const m = E().ED.m;
    C.ref = null; C.ecarts = null;
    try {
      const r = await fetch(X().API + '/modeles/' + m.id + '/reference.png', { credentials: 'include', cache: 'no-store' });
      if (!r.ok) return null;
      const blob = await r.blob();
      if (C.refUrl) URL.revokeObjectURL(C.refUrl);
      C.refUrl = URL.createObjectURL(blob);
      C.ref = await new Promise((ok, ko) => { const i = new Image(); i.onload = () => ok(i); i.onerror = ko; i.src = C.refUrl; });
      return C.ref;
    } catch (e) { return null; }
  }
  function recadrer(img) {
    // Rogne le blanc autour de l'étiquette photographiée ou scannée.
    const c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
    const x = c.getContext('2d'); x.drawImage(img, 0, 0);
    const d = x.getImageData(0, 0, c.width, c.height).data;
    let x0 = c.width, y0 = c.height, x1 = 0, y1 = 0;
    for (let y = 0; y < c.height; y += 2) for (let i = 0; i < c.width; i += 2) {
      const k = (y * c.width + i) * 4;
      if (d[k] + d[k + 1] + d[k + 2] < 600) { if (i < x0) x0 = i; if (i > x1) x1 = i; if (y < y0) y0 = y; if (y > y1) y1 = y; }
    }
    if (x1 <= x0 || y1 <= y0) return { x: 0, y: 0, w: c.width, h: c.height };
    return { x: x0, y: y0, w: x1 - x0 + 1, h: y1 - y0 + 1 };
  }
  async function calculerEcarts() {
    const m = E().ED.m;
    if (!C.ref) return;
    const k = 6, w = Math.round(m.largeur_mm * k), hh = Math.round(m.hauteur_mm * k);
    const rendu = await rendrePng(k);
    const ref = document.createElement('canvas'); ref.width = w; ref.height = hh;
    const rx = ref.getContext('2d'); rx.fillStyle = 'white'; rx.fillRect(0, 0, w, hh);
    const b = recadrer(C.ref);
    rx.drawImage(C.ref, b.x, b.y, b.w, b.h, 0, 0, w, hh);
    const a = rendu.getContext('2d').getImageData(0, 0, w, hh).data, r = rx.getImageData(0, 0, w, hh).data;
    const bloc = Math.round(2 * k), zones = [];
    let diffTot = 0, n = 0;
    for (let by = 0; by < hh; by += bloc) for (let bx = 0; bx < w; bx += bloc) {
      let d = 0, t = 0;
      for (let y = by; y < Math.min(hh, by + bloc); y++) for (let x = bx; x < Math.min(w, bx + bloc); x++) {
        const i = (y * w + x) * 4;
        const na = a[i] + a[i + 1] + a[i + 2] < 384, nr = r[i] + r[i + 1] + r[i + 2] < 384;
        if (na !== nr) d++;
        t++;
      }
      diffTot += d; n += t;
      if (d / t > 0.12) zones.push({ x: bx / k, y: by / k, w: bloc / k, h: bloc / k });
    }
    C.ecarts = { zones, taux: n ? diffTot / n : 0 };
  }
  // Superposition sur l'aperçu : image de référence + zones d'écart.
  function superposer() {
    const zone = document.querySelector('#es-canevas svg');
    if (!zone || !C.refVue) return;
    const m = E().ED.m;
    zone.querySelectorAll('.es-ref-calque').forEach(n => n.remove());
    const g = document.createElementNS(SVGNS, 'g'); g.setAttribute('class', 'es-ref-calque'); g.setAttribute('pointer-events', 'none');
    if (C.ref) {
      const b = recadrer(C.ref);
      const c = document.createElement('canvas'); c.width = b.w; c.height = b.h; c.getContext('2d').drawImage(C.ref, b.x, b.y, b.w, b.h, 0, 0, b.w, b.h);
      const im = document.createElementNS(SVGNS, 'image');
      im.setAttribute('href', c.toDataURL('image/png')); im.setAttribute('x', 0); im.setAttribute('y', 0);
      im.setAttribute('width', m.largeur_mm); im.setAttribute('height', m.hauteur_mm); im.setAttribute('preserveAspectRatio', 'none');
      im.setAttribute('opacity', C.opacite);
      g.appendChild(im);
    }
    for (const z of (C.ecarts && C.ecarts.zones) || []) {
      const r = document.createElementNS(SVGNS, 'rect');
      for (const [k, v] of Object.entries({ x: z.x, y: z.y, width: z.w, height: z.h, class: 'es-ecart' })) r.setAttribute(k, v);
      g.appendChild(r);
    }
    zone.appendChild(g);
  }

  function blocReference(rerendre) {
    const { h, bouton, toast, champ } = X();
    const m = E().ED.m;
    const fichier = h('input', { type: 'file', accept: 'image/png,image/jpeg,image/webp,application/pdf', hidden: true });
    fichier.addEventListener('change', async () => {
      const f = fichier.files[0];
      if (!f) return;
      const fd = new FormData(); fd.append('fichier', f, f.name);
      try { await X().api('/modeles/' + m.id + '/reference', { method: 'POST', form: fd }); toast('Étiquette de référence déposée.'); await chargerReference(); await calculerEcarts(); C.refVue = true; rerendre(); }
      catch (e) { toast(e.message, 'danger'); }
    });
    const op = h('input', { type: 'range', min: 0, max: 100, value: Math.round(C.opacite * 100), 'aria-label': 'Opacité de la référence' });
    op.addEventListener('input', () => { C.opacite = op.value / 100; superposer(); });
    const blocs = [h('div', { cls: 'es-panneau-titre', text: 'Référence client' }),
      h('div', { cls: 'es-aide', text: 'Déposer l\'étiquette fournie par le client (photo, scan ou PDF) : elle se superpose à l\'aperçu, les écarts sont surlignés.' })];
    if (C.ref) {
      blocs.push(h('label', { cls: 'es-case' }, (() => { const c = h('input', { type: 'checkbox', checked: C.refVue }); c.addEventListener('change', () => { C.refVue = c.checked; E().dessiner(); }); return c; })(), h('span', { text: 'Superposer à l\'aperçu' })),
        champ('Opacité', op),
        C.ecarts ? h('div', { cls: C.ecarts.zones.length ? 'es-aide es-erreur' : 'es-aide es-ok', text: C.ecarts.zones.length ? `${C.ecarts.zones.length} zone(s) d'écart · ${Math.round(C.ecarts.taux * 1000) / 10} % des points diffèrent.` : 'Aucun écart visuel notable.' }) : null,
        bouton('Recalculer les écarts', async () => { await calculerEcarts(); rerendre(); }, '', 'refresh-cw'));
    }
    blocs.push(h('div', { cls: 'es-ligne-actions' }, bouton(C.ref ? 'Remplacer la référence' : 'Déposer la référence', () => fichier.click(), '', 'paperclip')), fichier);
    return h('div', { cls: 'es-form es-encart' }, ...blocs);
  }

  function panneau() {
    const { h } = X();
    const racine = h('div', { cls: 'es-panneau', id: 'es-controle' });
    const rerendre = () => { const n = remplir(); racine.replaceChildren(...n); if (C.refVue) superposer(); };
    const remplir = () => {
      const al = alertesLocales();
      const m = E().ED.m;
      return [h('div', { cls: 'es-panneau-titre', text: `Contrôle à ${m.dpi} dpi` }),
        h('div', { cls: 'es-form', id: 'es-controle-liste' }, ...(al.length ? al.map(ligneAlerte) : [h('div', { cls: 'es-aide es-ok', text: 'Aucune alerte : codes lisibles, textes entiers, mentions présentes.' })])),
        blocIa(rerendre), blocReference(rerendre)];
    };
    racine.replaceChildren(...remplir());
    if (E().ED.m && C.ref === null && !C._charge) { C._charge = true; chargerReference().then(async (r) => { if (r) { await calculerEcarts(); rerendre(); } }); }
    return racine;
  }
  function majResume() {
    const zone = document.getElementById('es-controle-liste');
    if (zone) {
      const al = alertesLocales();
      zone.replaceChildren(...(al.length ? al.map(ligneAlerte) : [X().h('div', { cls: 'es-aide es-ok', text: 'Aucune alerte : codes lisibles, textes entiers, mentions présentes.' })]));
    }
    if (C.refVue) superposer();
  }
  // Mode opérateur : même contrôle dans une fenêtre, avant d'imprimer.
  function modaleControle() {
    const { h, modale, bouton, fermerModale } = X();
    const corps = h('div', { cls: 'es-form' });
    const remplir = () => { const al = alertesLocales(); corps.replaceChildren(...(al.length ? al.map(ligneAlerte) : [h('div', { cls: 'es-aide es-ok', text: 'Aucune alerte.' })]), blocIa(remplir)); };
    remplir();
    X().ES.adresseModale = { cle: 'controle', id: E().ED.m.id };
    modale('Contrôle avant impression', corps, [bouton('Fermer', fermerModale)]);
  }

  window.EtiqSpec = Object.assign(window.EtiqSpec || {}, {
    controle: { panneau, majResume, alertesLocales, modaleControle, rendrePng, _C: C,
      reinitialiser: () => { C.ia = null; C.ref = null; C.ecarts = null; C._charge = false; C.refVue = false; } },
  });
})();

/* MyTools › Étiquettes spécifiques — mise en page (EtiqSpec.miseEnPage).
 *
 * Grille, règles et guides en mm, magnétisme (grille, guides, bords et
 * centres des autres objets, bords de l'étiquette), aligner / distribuer une
 * sélection multiple, forme d'étiquette (coins arrondis, ronde, ovale,
 * découpe libre), planche (rouleau multi-poses, A4 multi-étiquettes),
 * propriétés de texte (ajusté au cadre, en arc, miroir), couleurs (quadri,
 * tons directs du référentiel des encres), langues et traduction des
 * mentions (/api/translate, DeepL).
 *
 * Réglages d'affichage (grille, pas, magnétisme, règles) : préférence du
 * poste en localStorage, pas une donnée de l'étiquette. Les guides, eux,
 * sont enregistrés dans le modèle (layout.guides).
 */
(function () {
  'use strict';
  const X = () => window.EtiqSpec._;
  const E = () => window.EtiqSpec.editeur.api;
  const SVGNS = 'http://www.w3.org/2000/svg';
  const LS = 'mysifa_etiq_mise_en_page';
  const P = { grille: true, pas: 1, aimant: true, regles: true };
  try { Object.assign(P, JSON.parse(localStorage.getItem(LS) || '{}')); } catch (e) { /* préférences par défaut */ }
  const garder = () => { try { localStorage.setItem(LS, JSON.stringify(P)); } catch (e) { /* navigation privée */ } };
  const SEUIL = 1;   // mm : distance d'accroche
  let reperesActifs = [];
  let encres = null;

  function s(tag, attrs) {
    const n = document.createElementNS(SVGNS, tag);
    for (const [k, v] of Object.entries(attrs || {})) if (v !== null && v !== undefined) n.setAttribute(k, v);
    return n;
  }
  const lay = () => E().layout();
  const ED = () => E().ED;

  // ── Fond : grille, règles, guides ───────────────────────────────────
  function dessinerFond(svg, m) {
    const L = m.largeur_mm, H = m.hauteur_mm;
    if (P.grille) {
      const g = s('g', { class: 'es-grille' });
      const pas = Math.max(0.5, P.pas);
      for (let x = pas; x < L; x += pas) g.appendChild(s('line', { x1: x, y1: 0, x2: x, y2: H, class: Math.abs(x % 10) < 1e-6 ? 'fort' : null }));
      for (let y = pas; y < H; y += pas) g.appendChild(s('line', { x1: 0, y1: y, x2: L, y2: y, class: Math.abs(y % 10) < 1e-6 ? 'fort' : null }));
      svg.appendChild(g);
    }
    if (P.regles) {
      const g = s('g', { class: 'es-regle' });
      for (let x = 0; x <= L + 1e-6; x += 1) {
        const long = x % 10 === 0 ? 2.2 : (x % 5 === 0 ? 1.4 : 0.7);
        g.appendChild(s('line', { x1: x, y1: -long, x2: x, y2: 0 }));
        if (x % 10 === 0 && x) { const t = s('text', { x, y: -2.8, 'text-anchor': 'middle' }); t.textContent = x; g.appendChild(t); }
      }
      for (let y = 0; y <= H + 1e-6; y += 1) {
        const long = y % 10 === 0 ? 2.2 : (y % 5 === 0 ? 1.4 : 0.7);
        g.appendChild(s('line', { x1: -long, y1: y, x2: 0, y2: y }));
        if (y % 10 === 0 && y) { const t = s('text', { x: -2.9, y: y + 0.8, 'text-anchor': 'end' }); t.textContent = y; g.appendChild(t); }
      }
      svg.appendChild(g);
    }
  }
  function dessinerDessus(svg, m) {
    const g = s('g', { class: 'es-guides' });
    for (const gd of lay().guides || []) {
      g.appendChild(gd.o === 'v' ? s('line', { x1: gd.pos, y1: -5, x2: gd.pos, y2: m.hauteur_mm + 5 }) : s('line', { x1: -5, y1: gd.pos, x2: m.largeur_mm + 5, y2: gd.pos }));
    }
    // Bord de pose d'une planche multi-poses : où commence la pose suivante.
    const pl = lay().planche || {};
    if ((pl.poses || 1) > 1) g.appendChild(s('line', { x1: m.largeur_mm + (pl.espace_h_mm || 0), y1: 0, x2: m.largeur_mm + (pl.espace_h_mm || 0), y2: m.hauteur_mm, class: 'es-pose' }));
    svg.appendChild(g);
  }

  // ── Magnétisme ──────────────────────────────────────────────────────
  function cibles(e) {
    const m = ED().m, xs = [0, m.largeur_mm / 2, m.largeur_mm], ys = [0, m.hauteur_mm / 2, m.hauteur_mm];
    for (const gd of lay().guides || []) (gd.o === 'v' ? xs : ys).push(gd.pos);
    for (const o of lay().elements) {
      if (o === e || ED().multi.has(o.id)) continue;
      const b = E().bboxElement(o);
      xs.push(b.x, b.x + b.w / 2, b.x + b.w); ys.push(b.y, b.y + b.h / 2, b.y + b.h);
    }
    return { xs, ys };
  }
  function accroche(valeurs, candidats) {
    let mieux = null;
    for (const [v, dec] of valeurs) for (const c of candidats) { const d = Math.abs(v - c); if (d <= SEUIL && (!mieux || d < mieux.d)) mieux = { d, delta: c - v, c }; }
    return mieux;
  }
  function aimanter(e, nx, ny, b) {
    reperesActifs = [];
    if (!P.aimant) return [nx, ny];
    const dx = nx - e.x, dy = ny - e.y;
    const x0 = b.x + dx, y0 = b.y + dy;
    const { xs, ys } = cibles(e);
    const ax = accroche([[x0], [x0 + b.w / 2], [x0 + b.w]], xs);
    const ay = accroche([[y0], [y0 + b.h / 2], [y0 + b.h]], ys);
    if (ax) { nx += ax.delta; reperesActifs.push({ o: 'v', pos: ax.c }); }
    else if (P.grille) nx = Math.round(nx / P.pas) * P.pas;
    if (ay) { ny += ay.delta; reperesActifs.push({ o: 'h', pos: ay.c }); }
    else if (P.grille) ny = Math.round(ny / P.pas) * P.pas;
    return [Math.max(0, Math.round(nx * 100) / 100), Math.max(0, Math.round(ny * 100) / 100)];
  }
  function reperes(svg) {
    svg.querySelectorAll('.es-repere').forEach(n => n.remove());
    const m = ED().m;
    for (const r of reperesActifs) {
      svg.appendChild(r.o === 'v' ? s('line', { x1: r.pos, y1: -5, x2: r.pos, y2: m.hauteur_mm + 5, class: 'es-repere' })
        : s('line', { x1: -5, y1: r.pos, x2: m.largeur_mm + 5, y2: r.pos, class: 'es-repere' }));
    }
  }

  // ── Aligner / distribuer ────────────────────────────────────────────
  function selection() {
    const ids = ED().multi.size ? [...ED().multi] : (ED().sel ? [ED().sel] : []);
    return ids.map(id => lay().elements.find(e => e.id === id)).filter(e => e && !E().fige(e));
  }
  function aligner(mode) {
    const els = selection();
    if (!els.length) return;
    const bs = els.map(e => [e, E().bboxElement(e)]);
    const seul = els.length === 1;
    const m = ED().m;
    const x0 = seul ? 0 : Math.min(...bs.map(([, b]) => b.x)), x1 = seul ? m.largeur_mm : Math.max(...bs.map(([, b]) => b.x + b.w));
    const y0 = seul ? 0 : Math.min(...bs.map(([, b]) => b.y)), y1 = seul ? m.hauteur_mm : Math.max(...bs.map(([, b]) => b.y + b.h));
    E().memoriser();
    for (const [e, b] of bs) {
      const ox = e.x - b.x, oy = e.y - b.y;
      if (mode === 'gauche') e.x = x0 + ox;
      if (mode === 'centre_h') e.x = (x0 + x1) / 2 - b.w / 2 + ox;
      if (mode === 'droite') e.x = x1 - b.w + ox;
      if (mode === 'haut') e.y = y0 + oy;
      if (mode === 'centre_v') e.y = (y0 + y1) / 2 - b.h / 2 + oy;
      if (mode === 'bas') e.y = y1 - b.h + oy;
      e.x = Math.max(0, Math.round(e.x * 10) / 10); e.y = Math.max(0, Math.round(e.y * 10) / 10);
    }
    E().salir(); X().rendre();
  }
  function distribuer(axe) {
    const els = selection();
    if (els.length < 3) { X().toast('Distribuer : trois objets au moins.', 'info'); return; }
    const bs = els.map(e => [e, E().bboxElement(e)]).sort((a, b) => axe === 'h' ? a[1].x - b[1].x : a[1].y - b[1].y);
    const debut = axe === 'h' ? bs[0][1].x : bs[0][1].y;
    const fin = axe === 'h' ? bs[bs.length - 1][1].x + bs[bs.length - 1][1].w : bs[bs.length - 1][1].y + bs[bs.length - 1][1].h;
    const total = bs.reduce((t, [, b]) => t + (axe === 'h' ? b.w : b.h), 0);
    const ecart = (fin - debut - total) / (bs.length - 1);
    E().memoriser();
    let pos = debut;
    for (const [e, b] of bs) {
      if (axe === 'h') { e.x = Math.round((pos + (e.x - b.x)) * 10) / 10; pos += b.w + ecart; }
      else { e.y = Math.round((pos + (e.y - b.y)) * 10) / 10; pos += b.h + ecart; }
    }
    E().salir(); X().rendre();
  }
  const ICO = {
    gauche: '<line x1="4" y1="3" x2="4" y2="21"/><rect x="7" y="6" width="12" height="4"/><rect x="7" y="14" width="7" height="4"/>',
    centre_h: '<line x1="12" y1="3" x2="12" y2="21"/><rect x="5" y="6" width="14" height="4"/><rect x="8" y="14" width="8" height="4"/>',
    droite: '<line x1="20" y1="3" x2="20" y2="21"/><rect x="5" y="6" width="12" height="4"/><rect x="10" y="14" width="7" height="4"/>',
    haut: '<line x1="3" y1="4" x2="21" y2="4"/><rect x="6" y="7" width="4" height="12"/><rect x="14" y="7" width="4" height="7"/>',
    centre_v: '<line x1="3" y1="12" x2="21" y2="12"/><rect x="6" y="5" width="4" height="14"/><rect x="14" y="8" width="4" height="8"/>',
    bas: '<line x1="3" y1="20" x2="21" y2="20"/><rect x="6" y="5" width="4" height="12"/><rect x="14" y="10" width="4" height="7"/>',
    dist_h: '<line x1="3" y1="4" x2="3" y2="20"/><line x1="21" y1="4" x2="21" y2="20"/><rect x="9" y="7" width="6" height="10"/>',
    dist_v: '<line x1="4" y1="3" x2="20" y2="3"/><line x1="4" y1="21" x2="20" y2="21"/><rect x="7" y="9" width="10" height="6"/>',
  };
  function icone(nom) {
    const t = document.createElement('template');
    t.innerHTML = `<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICO[nom]}</svg>`;
    return t.content.firstChild;
  }
  function barreAlignement() {
    const { h } = X();
    const b = (nom, bulle, fn) => h('button', { cls: 'es-btn es-btn-icone', type: 'button', 'data-bulle': bulle, 'aria-label': bulle, onclick: fn }, icone(nom));
    return h('div', { cls: 'es-barre-align' },
      b('gauche', 'Gauche', () => aligner('gauche')), b('centre_h', 'Centrer', () => aligner('centre_h')), b('droite', 'Droite', () => aligner('droite')),
      b('haut', 'Haut', () => aligner('haut')), b('centre_v', 'Milieu', () => aligner('centre_v')), b('bas', 'Bas', () => aligner('bas')),
      b('dist_h', 'Distribuer', () => distribuer('h')), b('dist_v', 'Répartir', () => distribuer('v')));
  }
  function barreOutils() {
    const { h } = X();
    const bascule = (cle, libelle, bulle) => h('button', { cls: 'es-puce' + (P[cle] ? ' actif' : ''), type: 'button', text: libelle, 'data-bulle': bulle,
      onclick: () => { P[cle] = !P[cle]; garder(); X().rendre(); } });
    const pas = h('select', { cls: 'es-input es-court', 'data-bulle': 'Pas', 'aria-label': 'Pas de la grille' },
      ...[0.5, 1, 2, 5].map(v => h('option', { value: v, text: String(v).replace('.', ',') + ' mm' })));
    pas.value = String(P.pas);
    pas.addEventListener('change', () => { P.pas = parseFloat(pas.value); garder(); E().dessiner(); });
    const guide = (o) => h('button', { cls: 'es-puce', type: 'button', text: o === 'v' ? '+ Guide |' : '+ Guide —', 'data-bulle': 'Guide',
      onclick: () => { E().memoriser(); const m = ED().m; lay().guides.push({ o, pos: Math.round((o === 'v' ? m.largeur_mm : m.hauteur_mm) / 2) }); E().salir(); E().dessiner(); } });
    return h('div', { cls: 'es-outils-canevas' }, bascule('grille', 'Grille', 'Grille'), pas, bascule('aimant', 'Magnétisme', 'Aimanter'),
      bascule('regles', 'Règles', 'Règles'), guide('v'), guide('h'), barreAlignement());
  }

  // ── Propriétés : texte, couleur ─────────────────────────────────────
  function proprietesTexte(e, ctx) {
    const { h, champ, api, toast } = X();
    const dis = ctx.fige ? true : null;
    const cas = (label, cle) => {
      const i = h('input', { type: 'checkbox', checked: !!e[cle], disabled: dis });
      i.addEventListener('change', () => { ctx.memoriser(); e[cle] = i.checked; ctx.salir(); ctx.dessiner(); });
      return h('label', { cls: 'es-case' }, i, h('span', { text: label }));
    };
    const arcOn = h('input', { type: 'checkbox', checked: !!e.arc, disabled: dis });
    const rayon = h('input', { cls: 'es-input', type: 'number', step: '1', min: 2, value: e.arc ? e.arc.rayon_mm : 20, disabled: dis });
    const sens = h('select', { cls: 'es-input', disabled: dis }, h('option', { value: 'haut', text: 'Arc vers le haut' }), h('option', { value: 'bas', text: 'Arc vers le bas' }));
    sens.value = e.arc ? e.arc.sens : 'haut';
    const majArc = () => { ctx.memoriser(); e.arc = arcOn.checked ? { rayon_mm: parseFloat(rayon.value) || 20, sens: sens.value } : null; if (!e.arc) delete e.arc; ctx.salir(); ctx.dessiner(); };
    [arcOn, sens].forEach(i => i.addEventListener('change', majArc));
    rayon.addEventListener('input', majArc);
    const blocs = [h('div', { cls: 'es-ligne2' }, cas('Ajuster au cadre', 'ajuster'), cas('Miroir', 'miroir')),
      h('label', { cls: 'es-case' }, arcOn, h('span', { text: 'Texte en arc' })),
      e.arc ? h('div', { cls: 'es-ligne2' }, champ('Rayon (mm)', rayon), champ('Sens', sens)) : null];
    // Variantes par langue
    const langues = (lay().langues || ['fr']).filter(l => l !== (lay().langue_defaut || lay().langues[0]));
    if (langues.length) {
      e.traductions = e.traductions || {};
      for (const l of langues) {
        const i = h('textarea', { cls: 'es-input', rows: 1, value: e.traductions[l] || '', placeholder: 'Texte en ' + l.toUpperCase(), disabled: dis });
        i.addEventListener('focus', ctx.memoriser, { once: true });
        i.addEventListener('input', () => { e.traductions[l] = i.value; ctx.salir(); ctx.dessiner(); });
        const tr = h('button', { cls: 'es-btn es-btn-icone', type: 'button', 'data-bulle': 'Traduire', 'aria-label': 'Traduire en ' + l.toUpperCase(), disabled: dis,
          onclick: async () => {
            const brut = e.valeur || '';
            if (!brut.trim()) return;
            // Les {{variables}} ne se traduisent pas : protégées le temps de l'appel.
            const vars = []; const prot = brut.replace(/\{\{[^}]+\}\}/g, m => { vars.push(m); return '[[' + (vars.length - 1) + ']]'; });
            tr.disabled = true;
            try {
              const r = await api('/api/translate', { brut: true, method: 'POST', body: { text: prot, target_lang: cibleDeepl(l) } });
              i.value = String(r.translated || '').replace(/\[\[(\d+)\]\]/g, (_, n) => vars[+n] || '');
              i.dispatchEvent(new Event('input'));
            } catch (err) { toast(err.message, 'danger'); }
            tr.disabled = false;
          } }, X().ic('globe', 14));
        blocs.push(champ('Texte ' + l.toUpperCase(), h('div', { cls: 'es-ligne-champ' }, i, tr)));
      }
    }
    return h('div', { cls: 'es-form' }, ...blocs);
  }
  function cibleDeepl(l) { return ({ en: 'EN-GB', pt: 'PT-PT' })[l] || l.toUpperCase(); }

  async function chargerEncres() {
    if (encres) return encres;
    try { encres = (await X().api('/api/encres/palette', { brut: true })).encres || []; } catch (e) { encres = []; }
    return encres;
  }
  function proprieteCouleur(e, ctx) {
    const { h, champ } = X();
    const dis = ctx.fige ? true : null;
    const c = e.couleur || null;
    const mode = h('select', { cls: 'es-input', disabled: dis }, h('option', { value: '', text: 'Noir (thermique)' }),
      h('option', { value: 'cmjn', text: 'Quadri (CMJN)' }), h('option', { value: 'ton_direct', text: 'Ton direct (Pantone)' }));
    mode.value = c ? c.mode : '';
    mode.addEventListener('change', () => {
      ctx.memoriser();
      e.couleur = mode.value ? Object.assign({ mode: mode.value, c: 0, m: 0, j: 0, n: 100, nom: '', hex: '' }, e.couleur || {}, { mode: mode.value }) : null;
      if (!e.couleur) delete e.couleur;
      ctx.salir(); E().majPanneauElement(); ctx.dessiner();
    });
    const blocs = [champ('Couleur', mode, 'Les imprimantes thermiques impriment en noir ; la couleur sert au PDF et à l\'aperçu.')];
    if (c && c.mode === 'cmjn') {
      const ch = (k) => { const i = h('input', { cls: 'es-input', type: 'number', min: 0, max: 100, value: c[k] || 0, disabled: dis });
        i.addEventListener('input', () => { c[k] = Math.max(0, Math.min(100, parseFloat(i.value) || 0)); c.hex = ''; ctx.salir(); ctx.dessiner(); }); return champ(k.toUpperCase() + ' %', i); };
      blocs.push(h('div', { cls: 'es-ligne4' }, ch('c'), ch('m'), ch('j'), ch('n')));
    }
    if (c && c.mode === 'ton_direct') {
      const liste = 'es-encres-' + e.id;
      const i = h('input', { cls: 'es-input', value: c.nom || '', list: liste, placeholder: 'Ex. PANTONE 185 C', disabled: dis });
      const dl = h('datalist', { id: liste });
      chargerEncres().then(lst => { dl.replaceChildren(...lst.slice(0, 4000).map(([cle, lib]) => h('option', { value: cle, text: lib }))); });
      i.addEventListener('change', async () => {
        ctx.memoriser();
        const lst = await chargerEncres();
        const t = lst.find(x => x[0].toLowerCase() === i.value.trim().toLowerCase());
        c.nom = i.value.trim(); c.hex = t ? t[2] : '';
        ctx.salir(); ctx.dessiner();
      });
      blocs.push(champ('Ton direct', h('div', {}, i, dl), 'Référentiel des encres de MySifa.'));
    }
    return h('div', { cls: 'es-form' }, ...blocs);
  }

  // ── Onglet Page : forme, planche, langues, guides ───────────────────
  function panneau() {
    const { h, champ, bouton } = X();
    const l = lay();
    const sel = (opts, val, fn) => { const x = h('select', { cls: 'es-input' }, ...Object.entries(opts).map(([k, v]) => h('option', { value: k, text: v }))); x.value = val; x.addEventListener('change', () => { E().memoriser(); fn(x.value); E().salir(); X().rendre(); }); return x; };
    const nb = (obj, cle, pas, apres) => { const x = h('input', { cls: 'es-input', type: 'number', step: pas || '0.5', min: 0, value: obj[cle] ?? 0 }); x.addEventListener('focus', E().memoriser, { once: true }); x.addEventListener('input', () => { obj[cle] = parseFloat(x.value) || 0; E().salir(); E().dessiner(); if (apres) apres(); }); return x; };
    const f = l.forme, pl = l.planche;
    const forme = [champ('Forme', sel({ rectangle: 'Rectangle', arrondi: 'Coins arrondis', ronde: 'Ronde', ovale: 'Ovale', libre: 'Découpe libre' }, f.type, v => { f.type = v; if (v === 'ronde') ED().m.hauteur_mm = ED().m.largeur_mm; }))];
    if (f.type === 'arrondi') forme.push(champ('Rayon des coins (mm)', nb(f, 'rayon_mm')));
    if (f.type === 'libre') {
      const ch = h('textarea', { cls: 'es-input es-mono', rows: 3, value: f.chemin || '', placeholder: 'M 0 0 L 100 0 L 100 60 L 50 80 L 0 60 Z' });
      ch.addEventListener('input', () => { f.chemin = ch.value.replace(/[^MmLlHhVvCcSsQqTtAaZz0-9 ,.\-eE]/g, ''); E().salir(); E().dessiner(); });
      forme.push(champ('Contour (chemin SVG en mm)', ch, 'Commandes M, L, A, C, Z en millimètres depuis le coin haut gauche.'));
    }
    const resume = h('div', { cls: 'es-aide' });
    const majResume = () => {
      const m = ED().m;
      if (pl.type === 'a4') {
        const cols = Math.max(1, Math.floor((210 - 2 * (pl.marge_gauche_mm ?? 5) + (pl.espace_h_mm ?? 2)) / (m.largeur_mm + (pl.espace_h_mm ?? 2))));
        const rangs = Math.max(1, Math.floor((297 - 2 * (pl.marge_haut_mm ?? 5) + (pl.espace_v_mm ?? 2)) / (m.hauteur_mm + (pl.espace_v_mm ?? 2))));
        const c = pl.poses > 1 ? Math.min(cols, pl.poses) : cols, r = pl.rangees ? Math.min(rangs, pl.rangees) : rangs;
        resume.textContent = `${c} × ${r} = ${c * r} étiquettes par feuille A4.`;
      } else {
        resume.textContent = (pl.poses || 1) > 1 ? `${pl.poses} poses de front : laize utile ${X().fmtNum((pl.marge_gauche_mm || 0) + pl.poses * m.largeur_mm + (pl.poses - 1) * (pl.espace_h_mm || 0))} mm. Les étiquettes de la série se posent côte à côte.` : 'Une étiquette de front.';
      }
    };
    const planche = [champ('Support', sel({ rouleau: 'Rouleau', a4: 'Feuille A4 (bureau)' }, pl.type, v => { pl.type = v; })),
      h('div', { cls: 'es-ligne2' }, champ(pl.type === 'a4' ? 'Colonnes max' : 'Poses de front', nb(pl, 'poses', '1', majResume)), pl.type === 'a4' ? champ('Rangées max (0 = auto)', nb(pl, 'rangees', '1', majResume)) : h('span')),
      h('div', { cls: 'es-ligne2' }, champ('Marge gauche (mm)', nb(pl, 'marge_gauche_mm', '0.5', majResume)), champ('Marge haut (mm)', nb(pl, 'marge_haut_mm', '0.5', majResume))),
      h('div', { cls: 'es-ligne2' }, champ('Espace horizontal (mm)', nb(pl, 'espace_h_mm', '0.5', majResume)), champ('Espace vertical (mm)', nb(pl, 'espace_v_mm', '0.5', majResume))),
      resume];
    majResume();
    // Langues
    const nouvelle = h('input', { cls: 'es-input es-court', maxlength: 5, placeholder: 'en' });
    const langues = [h('div', { cls: 'es-puces' }, ...l.langues.map(code => h('span', { cls: 'es-puce' + (code === l.langue_defaut ? ' actif' : '') },
      h('button', { cls: 'es-lien', type: 'button', text: code.toUpperCase(), 'data-bulle': 'Par défaut', onclick: () => { E().memoriser(); l.langue_defaut = code; E().salir(); X().rendre(); } }),
      l.langues.length > 1 ? h('button', { cls: 'es-lien', type: 'button', text: '×', 'data-bulle': 'Retirer', 'aria-label': 'Retirer la langue ' + code,
        onclick: () => { E().memoriser(); l.langues = l.langues.filter(x => x !== code); if (l.langue_defaut === code) l.langue_defaut = l.langues[0]; E().salir(); X().rendre(); } }) : null))),
      h('div', { cls: 'es-ligne-champ' }, nouvelle, bouton('Langue', () => {
        const c = nouvelle.value.trim().toLowerCase();
        if (!/^[a-z]{2}(-[a-z]{2})?$/.test(c)) { X().toast('Code de langue sur deux lettres (en, de, es…).', 'danger'); return; }
        if (!l.langues.includes(c)) { E().memoriser(); l.langues.push(c); E().salir(); X().rendre(); }
      }, '', 'plus')),
      l.langues.length > 1 ? bouton('Traduire toutes les mentions', traduireTout, '', 'globe') : null,
      h('div', { cls: 'es-aide', text: 'Une variante de texte par langue sur chaque texte (réglages du texte). La langue se choisit à l\'impression.' })];
    const guides = (l.guides || []).map((g, i) => h('div', { cls: 'es-ligne-champ' },
      h('span', { cls: 'es-aide', text: g.o === 'v' ? 'Vertical à x =' : 'Horizontal à y =' }), nb(g, 'pos', '0.5'),
      h('button', { cls: 'es-btn es-btn-icone', type: 'button', 'data-bulle': 'Retirer', 'aria-label': 'Retirer le guide', onclick: () => { E().memoriser(); l.guides.splice(i, 1); E().salir(); X().rendre(); } }, '×')));
    return h('div', { cls: 'es-panneau' },
      h('div', { cls: 'es-panneau-titre', text: 'Forme' }), ...forme,
      h('div', { cls: 'es-panneau-titre', text: 'Planche' }), ...planche,
      h('div', { cls: 'es-panneau-titre', text: 'Langues' }), ...langues,
      h('div', { cls: 'es-panneau-titre', text: 'Guides' }), ...(guides.length ? guides : [h('div', { cls: 'es-aide', text: 'Ajouter un guide depuis la barre au-dessus de l\'aperçu.' })]));
  }

  async function traduireTout() {
    const { api, toast } = X();
    const l = lay();
    const cibles = l.langues.filter(x => x !== l.langue_defaut);
    const textes = l.elements.filter(e => e.type === 'texte' && (e.valeur || '').replace(/\{\{[^}]+\}\}/g, '').trim() && !E().fige(e));
    if (!textes.length) { toast('Aucune mention à traduire.', 'info'); return; }
    E().memoriser();
    let n = 0;
    for (const c of cibles) for (const e of textes) {
      e.traductions = e.traductions || {};
      if (e.traductions[c]) continue;
      const vars = []; const prot = e.valeur.replace(/\{\{[^}]+\}\}/g, m => { vars.push(m); return '[[' + (vars.length - 1) + ']]'; });
      try {
        const r = await api('/api/translate', { brut: true, method: 'POST', body: { text: prot, target_lang: cibleDeepl(c) } });
        e.traductions[c] = String(r.translated || '').replace(/\[\[(\d+)\]\]/g, (_, k) => vars[+k] || '');
        n++;
      } catch (err) { toast(err.message, 'danger'); break; }
    }
    E().salir(); X().rendre();
    toast(n + ' mention' + (n > 1 ? 's' : '') + ' traduite' + (n > 1 ? 's' : '') + ' — à relire.');
  }

  function majBarre() { /* la barre d'alignement agit sur la sélection courante : rien à redessiner */ }

  window.EtiqSpec = Object.assign(window.EtiqSpec || {}, {
    miseEnPage: { dessinerFond, dessinerDessus, aimanter, reperes, barreAlignement, barreOutils, majBarre, proprietesTexte, proprieteCouleur,
      panneau, aligner, distribuer, _P: P },
  });
})();

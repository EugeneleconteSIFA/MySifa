/* MyTools › Utilitaires › Unités et couleurs — conversions d'atelier.
 *
 *   longueur   µm, mm, cm, m, pouces, points, picas
 *   grammage   g/m² = épaisseur (µm) × densité (g/cm³) : deux valeurs → la troisième
 *   laize      mètres linéaires ↔ m² pour une laize, et masse si le grammage est connu
 *   couleur    HEX ↔ RVB ↔ CMJN, Pantone le plus proche (table indicative,
 *              static/mysifa_tools_pantone.js)
 *   contraste  ratio WCAG 2.1 de deux couleurs, seuils AA et AAA
 *
 * Le CMJN est une conversion naïve sans profil ICC : il dépend en réalité du
 * papier, de l'encre et de la machine. L'écran le dit. Le Pantone proposé est
 * calculé par écart ΔE 2000 sur des valeurs sRGB approchées : indicatif.
 *
 * Adresse : conv (longueur par défaut). Les valeurs saisies n'y vont pas.
 */
(function () {
  'use strict';
  if (window.MyToolsUtil_unites) return;

  const CONVS = [
    ['longueur', 'Longueurs', 'mm, pouces'],
    ['grammage', 'Grammage', 'g/m², µm'],
    ['laize', 'Laize ↔ m²', 'Surface'],
    ['couleur', 'Couleur', 'CMJN, Pantone'],
    ['contraste', 'Contraste', 'WCAG'],
  ];
  const IDS = CONVS.map(c => c[0]);

  // ── Logique pure (tests/test_tools_utilitaires.js) ────────────────
  const num = v => { const x = parseFloat(String(v == null ? '' : v).replace(/\s/g, '').replace(',', '.')); return isFinite(x) ? x : NaN; };
  // Valeur d'une unité, en millimètres.
  const LONGUEURS = { um: 0.001, mm: 1, cm: 10, m: 1000, po: 25.4, pt: 25.4 / 72, pica: 25.4 / 6 };
  const LIB_LONG = { um: 'µm', mm: 'mm', cm: 'cm', m: 'm', po: 'pouces', pt: 'points', pica: 'picas' };
  function longueur(v, de) {
    const x = num(v);
    if (!isFinite(x) || !LONGUEURS[de]) return null;
    const mm = x * LONGUEURS[de], r = {};
    Object.keys(LONGUEURS).forEach(k => { r[k] = mm / LONGUEURS[k]; });
    return r;
  }
  // g/m² = µm × g/cm³ (1 µm d'une matière de densité 1 pèse 1 g/m²).
  function grammage(g, ep, dens) {
    const G = num(g), E = num(ep), D = num(dens);
    const a = [G > 0, E > 0, D > 0].filter(Boolean).length;
    if (a < 2) return { vide: true };
    // Trois valeurs saisies : la densité est recalculée.
    if (!(E > 0)) return { calcule: 'ep', g: G, ep: G / D, dens: D };
    if (!(G > 0)) return { calcule: 'g', g: E * D, ep: E, dens: D };
    return { calcule: 'dens', g: G, ep: E, dens: G / E };
  }
  // Laize (mm) et métrage (m) ou surface (m²) ; masse (kg) si grammage (g/m²).
  function laize(lz, metres, m2, gsm) {
    const L = num(lz), M = num(metres), S = num(m2), G = num(gsm);
    if (!(L > 0)) return { vide: true };
    let r;
    if (M > 0) r = { calcule: 'm2', metres: M, m2: M * L / 1000 };
    else if (S > 0) r = { calcule: 'metres', metres: S * 1000 / L, m2: S };
    else return { vide: true };
    if (G > 0) r.kg = r.m2 * G / 1000;
    return r;
  }

  // Couleurs : rvb = [0..255]×3.
  function lireCouleur(t) {
    const s = String(t == null ? '' : t).trim().toLowerCase();
    let m = s.match(/^#?([0-9a-f]{3})$/);
    if (m) return m[1].split('').map(c => parseInt(c + c, 16));
    m = s.match(/^#?([0-9a-f]{6})$/);
    if (m) return [0, 2, 4].map(i => parseInt(m[1].slice(i, i + 2), 16));
    m = s.replace(/^rgba?\(|\)$/g, '').split(/[\s,;]+/).filter(Boolean);
    if (m.length === 3 && m.every(x => /^\d{1,3}$/.test(x) && Number(x) <= 255)) return m.map(Number);
    return null;
  }
  const hex = rvb => rvb.map(v => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, '0')).join('').toUpperCase();
  // Conversion naïve, sans profil : c = (1 − r − k) ÷ (1 − k), en %.
  function rvbVersCmjn(rvb) {
    const [r, g, b] = rvb.map(v => v / 255);
    const k = 1 - Math.max(r, g, b);
    if (k >= 1) return [0, 0, 0, 100];
    return [(1 - r - k) / (1 - k), (1 - g - k) / (1 - k), (1 - b - k) / (1 - k), k].map(v => Math.round(v * 100));
  }
  function cmjnVersRvb(cmjn) {
    const [c, m, j, k] = cmjn.map(v => Math.max(0, Math.min(100, num(v) || 0)) / 100);
    return [c, m, j].map(v => Math.round(255 * (1 - v) * (1 - k)));
  }
  const lineaire = v => { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
  const luminance = rvb => 0.2126 * lineaire(rvb[0]) + 0.7152 * lineaire(rvb[1]) + 0.0722 * lineaire(rvb[2]);
  function contraste(a, b) {
    const la = luminance(a), lb = luminance(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  }
  function verdicts(ratio) {
    return { aaNormal: ratio >= 4.5, aaGrand: ratio >= 3, aaaNormal: ratio >= 7, aaaGrand: ratio >= 4.5 };
  }
  function lab(rvb) {
    const [R, G, B] = rvb.map(lineaire);
    const X = (R * 0.4124564 + G * 0.3575761 + B * 0.1804375) / 0.95047;
    const Y = (R * 0.2126729 + G * 0.7151522 + B * 0.072175);
    const Z = (R * 0.0193339 + G * 0.119192 + B * 0.9503041) / 1.08883;
    const f = t => (t > 216 / 24389 ? Math.cbrt(t) : (24389 / 27 * t + 16) / 116);
    const fx = f(X), fy = f(Y), fz = f(Z);
    return [116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)];
  }
  // ΔE 2000 (Sharma, Wu, Dalal 2005).
  function deltaE(l1, l2) {
    const rad = Math.PI / 180;
    const [L1, a1, b1] = l1, [L2, a2, b2] = l2;
    const C1 = Math.hypot(a1, b1), C2 = Math.hypot(a2, b2), Cm = (C1 + C2) / 2;
    const G = 0.5 * (1 - Math.sqrt(Math.pow(Cm, 7) / (Math.pow(Cm, 7) + Math.pow(25, 7))));
    const a1p = a1 * (1 + G), a2p = a2 * (1 + G);
    const C1p = Math.hypot(a1p, b1), C2p = Math.hypot(a2p, b2);
    const h = (b, a) => { if (b === 0 && a === 0) return 0; const x = Math.atan2(b, a) / rad; return x < 0 ? x + 360 : x; };
    const h1 = h(b1, a1p), h2 = h(b2, a2p);
    const dL = L2 - L1, dC = C2p - C1p;
    let dh = 0;
    if (C1p * C2p !== 0) { dh = h2 - h1; if (dh > 180) dh -= 360; else if (dh < -180) dh += 360; }
    const dH = 2 * Math.sqrt(C1p * C2p) * Math.sin(dh * rad / 2);
    const Lm = (L1 + L2) / 2, Cmp = (C1p + C2p) / 2;
    let hm = h1 + h2;
    if (C1p * C2p !== 0) { if (Math.abs(h1 - h2) > 180) hm += (h1 + h2 < 360 ? 360 : -360); hm /= 2; }
    const T = 1 - 0.17 * Math.cos((hm - 30) * rad) + 0.24 * Math.cos(2 * hm * rad) + 0.32 * Math.cos((3 * hm + 6) * rad) - 0.2 * Math.cos((4 * hm - 63) * rad);
    const dTheta = 30 * Math.exp(-Math.pow((hm - 275) / 25, 2));
    const Rc = 2 * Math.sqrt(Math.pow(Cmp, 7) / (Math.pow(Cmp, 7) + Math.pow(25, 7)));
    const Sl = 1 + 0.015 * Math.pow(Lm - 50, 2) / Math.sqrt(20 + Math.pow(Lm - 50, 2));
    const Sc = 1 + 0.045 * Cmp, Sh = 1 + 0.015 * Cmp * T;
    const Rt = -Math.sin(2 * dTheta * rad) * Rc;
    return Math.sqrt(Math.pow(dL / Sl, 2) + Math.pow(dC / Sc, 2) + Math.pow(dH / Sh, 2) + Rt * (dC / Sc) * (dH / Sh));
  }
  function pantoneProches(rvb, table, n) {
    const l = lab(rvb);
    return (table || []).map(p => { const c = lireCouleur(p[1]); return { nom: p[0], hex: hex(c), de: deltaE(l, lab(c)) }; })
      .sort((a, b) => a.de - b.de).slice(0, n || 3);
  }

  // ── Interface ──────────────────────────────────────────────────────
  let U = null;
  const V = { host: null, conv: 'longueur', panneaux: {} };
  const fmt = (x, d) => (isFinite(x) ? Number(x).toLocaleString('fr-FR', { maximumFractionDigits: d == null ? 3 : d }) : '—');
  const fmtSig = x => { if (!isFinite(x)) return '—'; const a = Math.abs(x); return fmt(x, a >= 1000 ? 1 : a >= 1 ? 3 : a >= 0.01 ? 4 : 6); };

  function champ(id, libelle, attrs) {
    const lab = U.el('label', 'tut-champ');
    lab.appendChild(U.el('span', null, libelle));
    const i = U.el('input', 'tut-in');
    i.id = 'tut-u-' + id;
    Object.assign(i, Object.assign({ type: 'text', inputMode: 'decimal', autocomplete: 'off' }, attrs || {}));
    lab.appendChild(i);
    return lab;
  }
  const val = id => { const e = V.host.querySelector('#tut-u-' + id); return e ? e.value : ''; };
  function tuile(valeur, libelle, copie) {
    const b = U.el('button', 'tut-tuile');
    b.type = 'button'; b.setAttribute('data-bulle', 'Copier');
    b.appendChild(U.el('b', null, valeur));
    b.appendChild(U.el('small', null, libelle));
    b.addEventListener('click', async () => { const ok = await U.copierTexte(copie != null ? copie : valeur); U.toast(ok ? 'Copié.' : 'Copie refusée.', ok ? 'success' : 'danger'); });
    return b;
  }
  function pastilleCouleur(rvb) { const s = U.el('span', 'tut-pastille-c'); s.style.background = '#' + hex(rvb); return s; }

  function panneau(id) {
    const p = U.el('section', 'tut-carte');
    p.setAttribute('data-conv', id);
    V.panneaux[id] = p;
    return p;
  }

  function construire() {
    const h = V.host;
    h.appendChild(U.tete('unites'));
    V.choix = U.pastilles(CONVS, V.conv, v => { V.conv = v; afficher(); U.signaler(); }, 'tut-pastilles--grandes');
    h.appendChild(V.choix);

    // Longueurs
    let p = panneau('longueur');
    let g = U.el('div', 'tut-grille');
    g.appendChild(champ('lv', 'Valeur', { placeholder: '210' }));
    const ls = U.el('label', 'tut-champ'); ls.appendChild(U.el('span', null, 'Unité'));
    const sel = U.el('select', 'tut-in'); sel.id = 'tut-u-lu';
    Object.keys(LONGUEURS).forEach(k => { const o = U.el('option', null, LIB_LONG[k]); o.value = k; if (k === 'mm') o.selected = true; sel.appendChild(o); });
    ls.appendChild(sel); g.appendChild(ls); p.appendChild(g);
    p.appendChild(U.el('div', 'tut-tuiles', '')).id = 'tut-u-lr';
    p.appendChild(U.el('p', 'tut-aide', '1 pouce = 25,4 mm · 1 point typographique (PostScript) = 1/72 pouce ≈ 0,353 mm · 1 pica = 12 points.'));

    // Grammage
    p = panneau('grammage');
    p.appendChild(U.el('p', 'tut-consigne', 'Renseigner deux valeurs : la troisième est calculée.'));
    g = U.el('div', 'tut-grille');
    g.append(champ('gg', 'Grammage (g/m²)', { placeholder: '80' }), champ('ge', 'Épaisseur (µm)', { placeholder: '100' }), champ('gd', 'Densité (g/cm³)', { placeholder: '0,8' }));
    p.appendChild(g);
    p.appendChild(U.el('div', 'tut-res tut-res--vide')).id = 'tut-u-gr';
    p.appendChild(U.el('p', 'tut-aide', 'Grammage = épaisseur × densité. Ordres de grandeur : papier couché 1,0 à 1,3 g/cm³, PP 0,9, PET 1,4, PE 0,92.'));

    // Laize
    p = panneau('laize');
    p.appendChild(U.el('p', 'tut-consigne', 'Laize, puis le métrage ou la surface. Le grammage, facultatif, donne la masse.'));
    g = U.el('div', 'tut-grille');
    g.append(champ('zl', 'Laize (mm)', { placeholder: '330' }), champ('zm', 'Métrage (m)', { placeholder: '2000' }),
      champ('zs', 'Surface (m²)', { placeholder: '660' }), champ('zg', 'Grammage (g/m²)', { placeholder: 'facultatif' }));
    p.appendChild(g);
    p.appendChild(U.el('div', 'tut-res tut-res--vide')).id = 'tut-u-zr';

    // Couleur
    p = panneau('couleur');
    g = U.el('div', 'tut-grille');
    const lc = champ('ch', 'HEX ou RVB', { placeholder: '#0085CA ou 0, 133, 202', inputMode: 'text' });
    const pick = U.el('input', 'tut-pick'); pick.type = 'color'; pick.id = 'tut-u-cp'; pick.setAttribute('data-bulle', 'Nuancier');
    lc.appendChild(pick);
    g.appendChild(lc);
    const cm = U.el('div', 'tut-champ');
    cm.appendChild(U.el('span', null, 'Ou CMJN (%)'));
    const q = U.el('div', 'tut-quatre');
    ['c', 'm', 'j', 'k'].forEach(k => { const i = U.el('input', 'tut-in'); i.id = 'tut-u-k' + k; i.inputMode = 'numeric'; i.placeholder = k.toUpperCase(); i.setAttribute('aria-label', k.toUpperCase()); q.appendChild(i); });
    cm.appendChild(q); g.appendChild(cm);
    p.appendChild(g);
    p.appendChild(U.el('div', 'tut-couleur', '')).id = 'tut-u-cr';
    p.appendChild(U.el('p', 'tut-aide', 'CMJN approximatif : conversion mathématique sans profil ICC. Le rendu réel dépend du papier, de l\'encre et de la machine. Pantone : table embarquée de valeurs écran approchées, indicatif — toujours valider sur nuancier imprimé.'));

    // Contraste
    p = panneau('contraste');
    g = U.el('div', 'tut-grille');
    const c1 = champ('t1', 'Texte', { placeholder: '#FFFFFF', inputMode: 'text' });
    const p1 = U.el('input', 'tut-pick'); p1.type = 'color'; p1.id = 'tut-u-p1'; p1.setAttribute('data-bulle', 'Nuancier'); c1.appendChild(p1);
    const c2 = champ('t2', 'Fond', { placeholder: '#0085CA', inputMode: 'text' });
    const p2 = U.el('input', 'tut-pick'); p2.type = 'color'; p2.id = 'tut-u-p2'; p2.setAttribute('data-bulle', 'Nuancier'); c2.appendChild(p2);
    const inv = U.bouton('tut-btn tut-btn--icone', 'inverser', '', 'Inverser');
    inv.addEventListener('click', () => { const a = val('t1'); V.host.querySelector('#tut-u-t1').value = val('t2'); V.host.querySelector('#tut-u-t2').value = a; maj(); });
    g.append(c1, c2, inv);
    p.appendChild(g);
    p.appendChild(U.el('div', 'tut-contraste', '')).id = 'tut-u-tr';
    p.appendChild(U.el('p', 'tut-aide', 'Ratio WCAG 2.1 : 4,5 pour un texte courant (AA), 3 pour un grand texte (≥ 18 pt, ou 14 pt gras), 7 et 4,5 pour le niveau AAA.'));

    Object.values(V.panneaux).forEach(x => h.appendChild(x));

    // Le nuancier et le CMJN alimentent le champ texte.
    pick.addEventListener('input', () => { V.host.querySelector('#tut-u-ch').value = pick.value.toUpperCase(); videCmjn(); maj(); });
    p1.addEventListener('input', () => { V.host.querySelector('#tut-u-t1').value = p1.value.toUpperCase(); maj(); });
    p2.addEventListener('input', () => { V.host.querySelector('#tut-u-t2').value = p2.value.toUpperCase(); maj(); });
    q.addEventListener('input', () => {
      const v = ['c', 'm', 'j', 'k'].map(k => val('k' + k));
      if (v.some(x => x !== '')) V.host.querySelector('#tut-u-ch').value = '#' + hex(cmjnVersRvb(v));
      maj();
    });
    V.host.querySelector('#tut-u-ch').addEventListener('input', videCmjn);
    h.addEventListener('input', e => { if (!q.contains(e.target)) maj(); });
    h.addEventListener('change', () => maj());
    afficher();
  }
  function videCmjn() { ['c', 'm', 'j', 'k'].forEach(k => { V.host.querySelector('#tut-u-k' + k).value = ''; }); }

  function afficher() {
    if (V.choix) V.choix.choisir(V.conv);
    Object.keys(V.panneaux).forEach(k => { V.panneaux[k].hidden = k !== V.conv; });
    maj();
  }

  function maj() {
    if (!V.host) return;
    // Longueurs
    const lr = V.host.querySelector('#tut-u-lr');
    lr.textContent = '';
    const L = longueur(val('lv'), V.host.querySelector('#tut-u-lu').value);
    if (L) Object.keys(L).forEach(k => lr.appendChild(tuile(fmtSig(L[k]), LIB_LONG[k], String(Math.round(L[k] * 1e6) / 1e6).replace('.', ','))));
    else lr.appendChild(U.el('div', 'tut-vide-l', 'Saisir une valeur.'));

    // Grammage
    const G = grammage(val('gg'), val('ge'), val('gd'));
    const gr = V.host.querySelector('#tut-u-gr');
    gr.classList.toggle('tut-res--vide', !!G.vide);
    gr.textContent = '';
    if (G.vide) gr.appendChild(U.el('div', 'tut-res-l', 'Deux valeurs à renseigner.'));
    else {
      const lib = { g: ['Grammage', fmt(G.g, 1) + ' g/m²'], ep: ['Épaisseur', fmt(G.ep, 1) + ' µm'], dens: ['Densité', fmt(G.dens, 3) + ' g/cm³'] }[G.calcule];
      gr.appendChild(U.el('div', 'tut-res-v', lib[1]));
      gr.appendChild(U.el('div', 'tut-res-l', lib[0] + (lib[0] === 'Grammage' ? ' calculé' : ' calculée') + ' à partir des deux autres valeurs.'));
    }

    // Laize
    const Z = laize(val('zl'), val('zm'), val('zs'), val('zg'));
    const zr = V.host.querySelector('#tut-u-zr');
    zr.classList.toggle('tut-res--vide', !!Z.vide);
    zr.textContent = '';
    if (Z.vide) zr.appendChild(U.el('div', 'tut-res-l', 'Laize et métrage, ou laize et surface.'));
    else {
      zr.appendChild(U.el('div', 'tut-res-v', Z.calcule === 'm2' ? fmt(Z.m2, 2) + ' m²' : fmt(Z.metres, 1) + ' m'));
      zr.appendChild(U.el('div', 'tut-res-l', (Z.calcule === 'm2' ? 'pour ' + fmt(Z.metres, 1) + ' m linéaires' : 'linéaires pour ' + fmt(Z.m2, 2) + ' m²')
        + ' en laize ' + fmt(num(val('zl')), 1) + ' mm' + (Z.kg != null ? ' · masse ≈ ' + fmt(Z.kg, Z.kg < 10 ? 2 : 1) + ' kg' : '')));
    }

    // Couleur
    const cr = V.host.querySelector('#tut-u-cr');
    cr.textContent = '';
    const rvb = lireCouleur(val('ch'));
    if (!rvb) cr.appendChild(U.el('div', 'tut-vide-l', val('ch') ? 'Couleur illisible : #RRVVBB, #RVB ou trois nombres de 0 à 255.' : 'Saisir une couleur, ou la choisir au nuancier.'));
    else {
      V.host.querySelector('#tut-u-cp').value = '#' + hex(rvb).toLowerCase();
      const ap = U.el('div', 'tut-couleur-ap'); ap.appendChild(pastilleCouleur(rvb));
      const t = U.el('div', 'tut-tuiles');
      const k = rvbVersCmjn(rvb);
      t.append(tuile('#' + hex(rvb), 'HEX'), tuile(rvb.join(', '), 'RVB'), tuile(k.join(' / '), 'CMJN approximatif', 'C' + k[0] + ' M' + k[1] + ' J' + k[2] + ' N' + k[3]));
      ap.appendChild(t);
      cr.appendChild(ap);
      const pt = window.MyToolsPantone;
      const zp = U.el('div', 'tut-pantone');
      zp.appendChild(U.el('div', 'tut-titre', 'Pantone le plus proche — indicatif'));
      if (!pt) zp.appendChild(U.el('div', 'tut-vide-l', 'Table Pantone en cours de chargement…'));
      else pantoneProches(rvb, pt, 3).forEach((x, i) => {
        const l = U.el('div', 'tut-pantone-l');
        l.appendChild(pastilleCouleur(lireCouleur(x.hex)));
        l.appendChild(U.el('b', null, 'PANTONE ' + x.nom));
        l.appendChild(U.el('small', null, 'ΔE ' + fmt(x.de, 1) + (x.de < 2 ? ' · très proche' : x.de < 5 ? ' · proche' : ' · éloigné') + (i ? '' : ' · le plus proche')));
        zp.appendChild(l);
      });
      cr.appendChild(zp);
    }

    // Contraste
    const tr = V.host.querySelector('#tut-u-tr');
    tr.textContent = '';
    const a = lireCouleur(val('t1')), b = lireCouleur(val('t2'));
    if (a) V.host.querySelector('#tut-u-p1').value = '#' + hex(a).toLowerCase();
    if (b) V.host.querySelector('#tut-u-p2').value = '#' + hex(b).toLowerCase();
    if (!a || !b) tr.appendChild(U.el('div', 'tut-vide-l', 'Deux couleurs à renseigner : texte et fond.'));
    else {
      const r = contraste(a, b), v = verdicts(r);
      const ex = U.el('div', 'tut-contraste-ex', 'Exemple de texte · Aa');
      ex.style.color = '#' + hex(a); ex.style.background = '#' + hex(b);
      const big = U.el('div', 'tut-res');
      big.appendChild(U.el('div', 'tut-res-v', fmt(r, 2) + ' : 1'));
      big.appendChild(U.el('div', 'tut-res-l', 'ratio de contraste'));
      const bd = U.el('div', 'tut-badges');
      [['AA texte courant', v.aaNormal], ['AA grand texte', v.aaGrand], ['AAA texte courant', v.aaaNormal], ['AAA grand texte', v.aaaGrand]].forEach(x => {
        bd.appendChild(U.el('span', 'tut-badge ' + (x[1] ? 'tut-badge--ok' : 'tut-badge--ko'), (x[1] ? '✓ ' : '× ') + x[0]));
      });
      tr.append(ex, big, bd);
    }
  }

  function chargerPantone() {
    if (window.MyToolsPantone) return;
    const T = window.__MYTOOLS__ || {};
    U.chargerScript('/static/mysifa_tools_pantone.js' + (T.version ? '?v=' + encodeURIComponent(T.version) : '')).then(() => maj(), () => {});
  }

  window.MyToolsUtil_unites = {
    cles: ['conv'],
    mount(host, outils) { U = outils; V.host = host; construire(); chargerPantone(); },
    etat: () => (V.conv !== 'longueur' ? { conv: V.conv } : {}),
    aller(p) { V.conv = p && IDS.indexOf(p.conv) !== -1 ? p.conv : 'longueur'; if (V.host) afficher(); },
    _interne: { longueur, grammage, laize, lireCouleur, hex, rvbVersCmjn, cmjnVersRvb, luminance, contraste, verdicts, lab, deltaE, pantoneProches },
  };
})();

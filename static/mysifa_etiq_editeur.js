/* MyTools › Étiquettes spécifiques — éditeur.
 *
 * ════════════════════════════════════════════════════════════════════════
 * FORMAT DU MODÈLE — le contrat lu par l'impression (ZPL, EPL, TSPL, PDF)
 * ════════════════════════════════════════════════════════════════════════
 * Unités : millimètres. Origine en haut à gauche, x vers la droite, y vers le
 * bas. Rotation en degrés, sens horaire : 0, 90, 180, 270. Normalisé côté
 * serveur par app/services/etiq_specifiques.py → normaliser_layout().
 *
 * modele = { id, nom, dossier_id, usage, client, largeur_mm, hauteur_mm, dpi,
 *            version, statut_validation, version_approuvee, layout }
 * layout = {
 *   elements:  [objet…]                    ordre = ordre de dessin
 *   variables: [variable…]                 référencées par {{nom}}
 *   calques:   [{id, nom, verrou}]         « fond » (figé), « donnees »…
 *   forme:     {type: rectangle|arrondi|ronde|ovale|libre, rayon_mm,
 *               chemin (path SVG en mm, découpe libre)}
 *   planche:   {type: rouleau|a4, poses (étiquettes de front), rangees (A4,
 *               0 = autant qu'il en tient), marge_gauche_mm, marge_haut_mm,
 *               espace_h_mm, espace_v_mm}
 *   langues:   ['fr', 'en', …], langue_defaut   (variantes de texte)
 *   guides:    [{o: 'h'|'v', pos}]             (édition seulement)
 * }
 * Champs communs à tout objet : id, type, nom, x, y, rotation, calque, verrou,
 *   condition (expression : imprimé seulement si vraie), masquer_si_vide,
 *   couleur {mode: cmjn|ton_direct, c, m, j, n (0-100), nom, hex (aperçu)}
 *   — les thermiques impriment en noir et ignorent la couleur.
 * texte       valeur, taille (hauteur de cellule), gras, largeur (bloc, 0 =
 *             sans), lignes, align (gauche|centre|droite), inverse, ajuster
 *             (réduit la taille pour tenir dans largeur × lignes), arc
 *             {rayon_mm, sens: haut|bas}, miroir, police, traductions {en: …}
 * code_barre  symbologie (code128 [auto], gs1_128, ean13, ean8, upca, code39,
 *             itf14, datamatrix, gs1_datamatrix, qrcode, pdf417), valeur (AI
 *             GS1 entre parenthèses), hauteur, module (largeur du plus petit
 *             module), lisible, colonnes / securite (PDF417), correction (QR)
 * cadre       largeur, hauteur, epaisseur, arrondi (0-8), plein
 * ellipse     largeur, hauteur, epaisseur, plein
 * ligne       orientation (h|v), longueur, epaisseur
 * picto       picto (recyclage, fsc, deroulage, fragile, haut, humidite),
 *             largeur, hauteur, legende, taille_legende — primitives dans
 *             /bootstrap (referentiel.pictos), trame ZPL : etiq_pictos.py
 * image       src (data:image/png;base64,…), largeur, hauteur, seuil,
 *             tramage, inverse
 * Variables : {nom, libelle, type, …}
 *   fixe {valeur} · saisie {valeur, obligatoire, controle {type: texte|entier|
 *   nombre|date|motif, motif, min, max, longueur_max}, choix [..], pesee,
 *   balance_id} · source {champ: « dossier.reference »…, valeur, obligatoire}
 *   · compteur {debut, pas, longueur, prefixe, suffixe, reprise} · sscc
 *   {extension, prefixe_gs1} · date {base: impression|<variable>,
 *   decalage_jours, decalage_mois, format} · formule {expression}
 *   Fournies sans déclaration : {{fsc_licence}}, {{gs1_prefixe}}.
 *
 * Calcul des valeurs (serveur, à appeler par l'impression) :
 *   es.plan_serie() + es.reserver_serie()  numéros réservés
 *   es.valeurs_etiquette(layout, plan, i, enregistrement)  toutes les variables
 *   es.element_visible(e, valeurs) · es.texte_element(e, langue)
 *   etiq_validation.modele_production(conn, id)  version APPROUVÉE à imprimer
 * Routes (préfixe /api/print/specifiques, app/routers/etiq_avance.py) :
 *   GET  /modeles/{id}/production              modèle approuvé (à imprimer)
 *   GET  /production/pour-dossier?dossier=&usage=   modèles approuvés d'un dossier
 *   POST /modeles/{id}/rendu {enregistrement | source {type, id}, index}
 *        → {modele, valeurs, elements visibles (texte substitué), zpl}
 * Côté page : EtiqSpec.rendu(modeleId, {enregistrement, source}) et
 *   EtiqSpec.modeleProduction(modeleId) appellent ces routes.
 * Impression : window.MySifaEtiqImpression.imprimer({modele, enregistrements,
 *   quantite}) — modele = version approuvée ci-dessus, enregistrements =
 *   [{nom_variable: valeur, _langue}] (saisies + sources ; compteurs, SSCC,
 *   dates et formules restent au serveur), quantite = étiquettes par
 *   enregistrement. Sans ce module : chemin intégré (ZPL ou PDF A4).
 * ════════════════════════════════════════════════════════════════════════
 *
 * Trois colonnes : objets (liste, calques, réglages de l'objet choisi),
 * aperçu SVG à l'échelle, onglets (variables, données, page, contrôle,
 * assistant IA). Mode opérateur : seul le formulaire de saisie reste
 * modifiable, l'aperçu suit. Panneaux externes : EtiqSpec.miseEnPage,
 * EtiqSpec.donnees, EtiqSpec.controle, EtiqSpec.biblio, EtiqSpec.gs1.
 *
 * Saisie dans un champ : seul l'aperçu est redessiné, jamais le formulaire.
 */
(function () {
  'use strict';
  const X = () => window.EtiqSpec._;
  const MO = () => window.EtiqMoteur;
  const ext = (n) => (window.EtiqSpec && window.EtiqSpec[n]) || null;
  const BWIP_URL = 'https://cdn.jsdelivr.net/npm/bwip-js@4.5.1/dist/bwip-js-min.js';
  const BCID = { code128: 'code128', gs1_128: 'gs1-128', ean13: 'ean13', ean8: 'ean8', upca: 'upca', code39: 'code39',
    itf14: 'itf14', datamatrix: 'datamatrix', gs1_datamatrix: 'gs1datamatrix', qrcode: 'qrcode', pdf417: 'pdf417' };
  const DEUX_D = ['datamatrix', 'gs1_datamatrix', 'qrcode'];
  const SVGNS = 'http://www.w3.org/2000/svg';
  const PANNEAUX = ['variables', 'donnees', 'page', 'controle', 'ia'];

  const ED = { m: null, sel: null, multi: new Set(), dirty: false, pile: [], propo: null, iaBusy: false, voirPropo: true,
    mode: 'conception', panneau: 'variables', langue: '', saisies: {}, source: null, calquesMasques: new Set(),
    plan: null, boites: {} };
  let bwipEtat = 'absent';
  const cacheCodes = new Map();

  // ── Outils ──────────────────────────────────────────────────────────
  function $id(id) { const host = X().ES.host; return host ? host.querySelector('#' + id) : document.getElementById(id); }
  function s(tag, attrs) {
    const n = document.createElementNS(SVGNS, tag);
    for (const [k, v] of Object.entries(attrs || {})) if (v !== null && v !== undefined) n.setAttribute(k, v);
    return n;
  }
  function num(v, d) { const f = parseFloat(String(v).replace(',', '.')); return Number.isFinite(f) ? f : d; }
  function cloner(o) { return JSON.parse(JSON.stringify(o)); }
  function layout() { return ED.m.layout; }
  function elSel() { return layout().elements.find(e => e.id === ED.sel) || null; }
  function concepteur() { return !!(X().ES.boot.referentiel.concepteur); }
  function fige(e) { return MO().verrouille(e, layout()) && !concepteur(); }
  function nouvelId() {
    const ids = new Set(layout().elements.map(e => e.id));
    let i = layout().elements.length + 1;
    while (ids.has('e' + i)) i++;
    return 'e' + i;
  }
  function memoriser() {
    ED.pile.push(JSON.stringify({ layout: ED.m.layout, l: ED.m.largeur_mm, h: ED.m.hauteur_mm }));
    if (ED.pile.length > 60) ED.pile.shift();
  }
  function annuler() {
    const p = ED.pile.pop();
    if (!p) { X().toast('Rien à annuler.', 'info'); return; }
    const o = JSON.parse(p);
    ED.m.layout = o.layout; ED.m.largeur_mm = o.l; ED.m.hauteur_mm = o.h;
    if (!elSel()) ED.sel = null;
    salir(); X().rendre();
  }
  function salir() {
    ED.dirty = true;
    const b = $id('es-enregistrer');
    if (b) b.disabled = false;
  }
  function completerLayout(lay) {
    lay.elements = lay.elements || []; lay.variables = lay.variables || [];
    if (!lay.calques || !lay.calques.length) lay.calques = cloner(X().ES.boot.referentiel.calques_defaut || []);
    lay.forme = lay.forme || { type: 'rectangle', rayon_mm: 3, chemin: '' };
    lay.planche = lay.planche || { type: 'rouleau', poses: 1 };
    lay.langues = lay.langues && lay.langues.length ? lay.langues : ['fr'];
    lay.guides = lay.guides || [];
    return lay;
  }

  // ── Valeurs d'aperçu ────────────────────────────────────────────────
  function systeme() {
    const r = X().ES.boot.referentiel;
    return { fsc_licence: r.fsc_licence || '', gs1_prefixe: (r.gs1 && r.gs1.prefixe) || '' };
  }
  function valeursApercu(lay, index) {
    const sa = Object.assign({}, ED.saisies);
    if (ED.langue) sa._langue = ED.langue;
    const v = MO().valeurs(lay, { saisies: sa, plan: ED.plan || {}, index: index || 0, systeme: systeme() });
    v._langue = ED.langue && (lay.langues || []).includes(ED.langue) ? ED.langue : '';
    return v;
  }
  function texteDe(e, vals) {
    const t = (vals._langue && e.traductions && e.traductions[vals._langue]) || e.valeur;
    return MO().substituer(t, vals);
  }
  function avertissements(lay, vals) {
    const decl = new Set(lay.variables.map(v => v.nom).concat(['fsc_licence', 'gs1_prefixe']));
    const out = [], vus = new Set();
    for (const e of lay.elements) {
      for (const m of String((e.valeur || '') + ' ' + (e.legende || '')).matchAll(/\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}/g)) {
        const n = m[1].toLowerCase();
        if (!decl.has(n) && !vus.has(n)) { vus.add(n); out.push(`{{${n}}} est utilisé mais aucune variable « ${n} » n'est déclarée.`); }
      }
    }
    for (const v of lay.variables) {
      if (v.type === 'sscc') { const l = String(v.prefixe_gs1 || '').replace(/\D/g, '').length; if (l < 7 || l > 10) out.push(`Variable « ${v.nom} » : le préfixe GS1 doit compter 7 à 10 chiffres.`); }
      if (v.type === 'formule') { const r = MO().evaluer(v.expression || '', vals); if (r.erreur) out.push(`Formule « ${v.nom} » : ${r.erreur}`); }
      if (v.type === 'source' && !v.champ) out.push(`Variable « ${v.nom} » : choisir la donnée MySifa à lire.`);
    }
    for (const e of lay.elements) if (e.x > ED.m.largeur_mm || e.y > ED.m.hauteur_mm) out.push(`« ${e.nom || e.id} » est hors de l'étiquette.`);
    return out;
  }

  // ── Codes-barres (bwip-js) ──────────────────────────────────────────
  function chargerBwip() {
    if (bwipEtat !== 'absent') return;
    bwipEtat = 'charge';
    const sc = document.createElement('script');
    sc.src = BWIP_URL;
    sc.onload = () => { bwipEtat = window.bwipjs ? 'pret' : 'erreur'; dessiner(); document.dispatchEvent(new Event('etiq-bwip-pret')); };
    sc.onerror = () => { bwipEtat = 'erreur'; dessiner(); };
    document.head.appendChild(sc);
  }
  function donneesCode(sym, v) {
    if (sym === 'ean13') return String(v).replace(/\D/g, '').slice(0, 12);
    if (sym === 'ean8') return String(v).replace(/\D/g, '').slice(0, 7);
    if (sym === 'upca') return String(v).replace(/\D/g, '').slice(0, 11);
    if (sym === 'itf14') return String(v).replace(/\D/g, '').slice(0, 13);
    if (sym === 'gs1_128' || sym === 'gs1_datamatrix') return String(v).replace(/\s+/g, '');
    if (sym === 'code39') return String(v).toUpperCase();
    return String(v);
  }
  function code(sym, texte, e) {
    const cle = sym + '|' + texte + '|' + (e.colonnes || '') + (e.correction || '');
    if (cacheCodes.has(cle)) return cacheCodes.get(cle);
    let r;
    try {
      if (!texte) throw new Error('vide');
      const opts = { bcid: BCID[sym], text: texte, scale: 1, height: 10, includetext: false, paddingwidth: 0, paddingheight: 0 };
      if (sym === 'ean13') opts.text = texte.padEnd(12, '0');
      if (sym === 'pdf417' && e.colonnes) opts.columns = e.colonnes;
      if (sym === 'qrcode' && e.correction) opts.eclevel = e.correction;
      const raw = window.bwipjs.raw(Object.assign({}, opts))[0];
      let mx, my;
      if (raw.pixx) { mx = raw.pixx; my = raw.pixy; } else { mx = (raw.sbs || []).reduce((a, b) => a + b, 0); my = null; }
      const svg = window.bwipjs.toSVG(opts);
      r = { url: 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg), mx, my };
    } catch (err) {
      r = { erreur: String(err.message || err).replace(/^bwipp\.\w+#\d+:\s*/, '').slice(0, 80) };
    }
    if (cacheCodes.size > 300) cacheCodes.clear();
    cacheCodes.set(cle, r);
    return r;
  }

  // ── Dessin SVG ──────────────────────────────────────────────────────
  function encre(e) {
    const c = e.couleur;
    if (!c) return 'black';
    if (c.hex) return c.hex;
    const k = x => Math.round(255 * (1 - (x || 0) / 100) * (1 - (c.n || 0) / 100));
    return `rgb(${k(c.c)},${k(c.m)},${k(c.j)})`;
  }
  function dessinerElement(g, e, vals) {
    const rot = e.rotation ? `rotate(${e.rotation} ${e.x} ${e.y})` : null;
    const coul = encre(e);
    if (e.type === 'texte') {
      const t = texteDe(e, vals);
      const larg = e.largeur || 0;
      let taille = e.taille;
      if (e.ajuster && larg && t) { const besoin = t.length * taille * 0.55, place = larg * (e.lignes || 1); if (besoin > place) taille = Math.max(1, taille * place / besoin); }
      const police = "'Arial Narrow', Arial, sans-serif", poids = e.gras ? 700 : 500;
      const fill = e.inverse ? 'white' : coul;
      let tr = rot;
      if (e.miroir) tr = (tr ? tr + ' ' : '') + `translate(${2 * e.x + (larg || t.length * taille * 0.5)} 0) scale(-1 1)`;
      if (e.arc && e.arc.rayon_mm) {
        const r = e.arc.rayon_mm, bas = e.arc.sens === 'bas';
        const cx = e.x + r, cy = e.y + r;
        const pid = 'arc-' + e.id + '-' + Math.random().toString(36).slice(2, 7);
        const d = bas ? `M ${cx - r} ${cy} A ${r} ${r} 0 0 0 ${cx + r} ${cy}` : `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
        const defs = s('defs'); defs.appendChild(s('path', { id: pid, d })); g.appendChild(defs);
        const tx = s('text', { 'font-size': taille, 'font-family': police, 'font-weight': poids, fill, transform: tr });
        const tp = s('textPath', { href: '#' + pid, startOffset: '50%', 'text-anchor': 'middle' });
        tp.textContent = t; tx.appendChild(tp); g.appendChild(tx);
        return;
      }
      let ax = e.x, anchor = 'start';
      if (larg && e.align === 'centre') { ax = e.x + larg / 2; anchor = 'middle'; }
      if (larg && e.align === 'droite') { ax = e.x + larg; anchor = 'end'; }
      const toutes = larg ? decouper(t, larg, taille, 99) : String(t).split('\n');
      const lignes = larg ? toutes.slice(0, e.lignes || 1) : toutes;
      g.dataset.coupe = larg && toutes.length > (e.lignes || 1) ? '1' : '';
      const txt = s('text', { x: ax, y: e.y + taille * 0.82, 'font-size': taille, 'text-anchor': anchor,
        'font-family': police, 'font-weight': poids, fill, transform: tr });
      lignes.forEach((l, i) => { const ts = s('tspan', { x: ax, dy: i ? taille * 1.05 : 0 }); ts.textContent = l; txt.appendChild(ts); });
      g.appendChild(txt);
      return;
    }
    if (e.type === 'cadre') {
      const t = e.epaisseur, r = (e.arrondi || 0) / 8 * Math.min(e.largeur, e.hauteur) / 2;
      g.appendChild(e.plein
        ? s('rect', { x: e.x, y: e.y, width: e.largeur, height: e.hauteur, rx: r, fill: coul, transform: rot })
        : s('rect', { x: e.x + t / 2, y: e.y + t / 2, width: Math.max(0.1, e.largeur - t), height: Math.max(0.1, e.hauteur - t),
          rx: r, fill: 'none', stroke: coul, 'stroke-width': t, transform: rot }));
      return;
    }
    if (e.type === 'ellipse') {
      const t = e.epaisseur;
      g.appendChild(s('ellipse', { cx: e.x + e.largeur / 2, cy: e.y + e.hauteur / 2, rx: Math.max(0.1, (e.largeur - (e.plein ? 0 : t)) / 2),
        ry: Math.max(0.1, (e.hauteur - (e.plein ? 0 : t)) / 2), fill: e.plein ? coul : 'none', stroke: e.plein ? null : coul, 'stroke-width': e.plein ? null : t, transform: rot }));
      return;
    }
    if (e.type === 'ligne') {
      g.appendChild(e.orientation === 'v'
        ? s('rect', { x: e.x, y: e.y, width: e.epaisseur, height: e.longueur, fill: coul })
        : s('rect', { x: e.x, y: e.y, width: e.longueur, height: e.epaisseur, fill: coul }));
      return;
    }
    if (e.type === 'image') {
      g.appendChild(s('image', { href: e.src, x: e.x, y: e.y, width: e.largeur, height: e.hauteur, transform: rot, style: 'filter:grayscale(1)' }));
      return;
    }
    if (e.type === 'picto') { dessinerPicto(g, e, vals, coul, rot); return; }
    if (e.type === 'code_barre') {
      const texte = donneesCode(e.symbologie, texteDe(e, vals));
      const deuxD = DEUX_D.includes(e.symbologie);
      if (bwipEtat !== 'pret') {
        chargerBwip();
        g.appendChild(s('rect', { x: e.x, y: e.y, width: deuxD ? 15 : 40, height: deuxD ? 15 : e.hauteur, fill: 'none', stroke: 'black', 'stroke-dasharray': '1 1', 'stroke-width': 0.3 }));
        return;
      }
      const c = code(e.symbologie, texte, e);
      if (c.erreur) {
        const w = deuxD ? 15 : 40, ht = deuxD ? 15 : e.hauteur;
        g.appendChild(s('rect', { x: e.x, y: e.y, width: w, height: ht, fill: 'none', stroke: 'crimson', 'stroke-width': 0.4, 'stroke-dasharray': '1.5 1' }));
        const t = s('text', { x: e.x + 1, y: e.y + 3.5, 'font-size': 2.6, fill: 'crimson', 'font-family': 'Arial, sans-serif' });
        t.textContent = 'Code invalide : ' + c.erreur;
        g.appendChild(t);
        return;
      }
      const w = c.mx * e.module;
      const ht = deuxD ? (c.my || c.mx) * e.module : (e.symbologie === 'pdf417' ? (c.my || 10) * e.module * 3 : e.hauteur);
      g.appendChild(s('image', { href: c.url, x: e.x, y: e.y, width: w, height: ht, preserveAspectRatio: 'none', transform: rot }));
      g.dataset.w = w; g.dataset.h = ht;
      if (e.lisible && !deuxD && e.symbologie !== 'pdf417') {
        let lisible = texte;
        if (e.symbologie === 'ean13') lisible = texte.padEnd(12, '0') + MO().cleGs1(texte.padEnd(12, '0'));
        const t = s('text', { x: e.x + w / 2, y: e.y + ht + 2.6, 'font-size': 2.4, 'text-anchor': 'middle',
          'font-family': "'Arial Narrow', Arial, sans-serif", fill: 'black', transform: rot });
        t.textContent = lisible;
        g.appendChild(t);
      }
    }
  }
  function dessinerPicto(g, e, vals, coul, rot) {
    const ref = (X().ES.boot.referentiel.pictos || {})[e.picto];
    const leg = MO().substituer(e.legende || '', vals).trim();
    const hl = leg ? (e.taille_legende || 2.2) + 0.5 : 0;
    const k = Math.min(e.largeur, e.hauteur - hl) / 24;
    const ox = e.x + (e.largeur - 24 * k) / 2, oy = e.y;
    const gg = s('g', { transform: (rot ? rot + ' ' : '') + `translate(${ox} ${oy}) scale(${k})` });
    for (const p of (ref ? ref.primitives : [])) {
      const pts = (p.p || []).map(q => q.join(',')).join(' ');
      if (p.t === 'ligne') gg.appendChild(s('polyline', { points: pts, fill: 'none', stroke: coul, 'stroke-width': p.e || 1, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }));
      else if (p.t === 'poly') gg.appendChild(s('polygon', { points: pts, fill: coul }));
      else if (p.t === 'cercle') gg.appendChild(s('circle', { cx: p.c[0], cy: p.c[1], r: p.r, fill: p.e ? 'none' : coul, stroke: p.e ? coul : null, 'stroke-width': p.e || null }));
      else if (p.t === 'texte') { const t = s('text', { x: p.x, y: p.y, 'font-size': p.s, 'text-anchor': 'middle', 'font-weight': 700, 'font-family': 'Arial, sans-serif', fill: coul }); t.textContent = p.v; gg.appendChild(t); }
    }
    g.appendChild(gg);
    if (leg) {
      const t = s('text', { x: e.x + e.largeur / 2, y: e.y + e.hauteur - 0.3, 'font-size': e.taille_legende || 2.2, 'text-anchor': 'middle', 'font-family': 'Arial, sans-serif', fill: coul });
      t.textContent = leg; g.appendChild(t);
    }
  }
  function decouper(t, larg, taille, max) {
    const parCar = Math.max(1, Math.floor(larg / (taille * 0.5)));
    const lignes = [];
    for (const para of String(t).split('\n')) {
      let cur = '';
      for (const m of para.split(/\s+/)) {
        if ((cur + ' ' + m).trim().length > parCar && cur) { lignes.push(cur); cur = m; } else cur = (cur + ' ' + m).trim();
      }
      lignes.push(cur);
    }
    return lignes.slice(0, max);
  }
  function bboxElement(e) {
    if (e.type === 'texte') return { x: e.x, y: e.y, w: e.largeur || Math.max(4, String(e.valeur || '').length * e.taille * 0.5), h: e.taille * (e.largeur ? (e.lignes || 1) : 1) * 1.05 };
    if (e.type === 'cadre' || e.type === 'ellipse' || e.type === 'picto' || e.type === 'image') return { x: e.x, y: e.y, w: e.largeur, h: e.hauteur };
    if (e.type === 'ligne') return e.orientation === 'v' ? { x: e.x - 0.5, y: e.y, w: e.epaisseur + 1, h: e.longueur } : { x: e.x, y: e.y - 0.5, w: e.longueur, h: e.epaisseur + 1 };
    return { x: e.x, y: e.y, w: 20, h: e.hauteur || 15 };
  }
  function cheminForme(m, lay) {
    const L = m.largeur_mm, H = m.hauteur_mm, f = lay.forme || {};
    if (f.type === 'ronde' || f.type === 'ovale') return s('ellipse', { cx: L / 2, cy: H / 2, rx: L / 2, ry: H / 2 });
    if (f.type === 'libre' && f.chemin) return s('path', { d: f.chemin });
    return s('rect', { x: 0, y: 0, width: L, height: H, rx: f.type === 'arrondi' ? (f.rayon_mm || 3) : 1.2 });
  }

  function construireSvg(m, lay, interactif, vals) {
    const L = m.largeur_mm, H = m.hauteur_mm, marge = 5;
    vals = vals || valeursApercu(lay);
    const svg = s('svg', { viewBox: `${-marge} ${-marge} ${L + 2 * marge} ${H + 2 * marge}`, class: 'es-svg', tabindex: interactif ? 0 : null });
    const idc = 'clip-' + Math.random().toString(36).slice(2, 8);
    const defs = s('defs'), clip = s('clipPath', { id: idc });
    clip.appendChild(cheminForme(m, lay)); defs.appendChild(clip); svg.appendChild(defs);
    const papier = cheminForme(m, lay); papier.setAttribute('fill', 'white'); papier.setAttribute('class', 'es-papier');
    svg.appendChild(papier);
    const mp = ext('miseEnPage');
    if (interactif && mp && mp.dessinerFond) mp.dessinerFond(svg, m, lay);
    const corps = s('g', { 'clip-path': `url(#${idc})` });
    svg.appendChild(corps);
    for (const e of lay.elements) {
      if (ED.calquesMasques.has(e.calque)) continue;
      const vis = MO().visible(e, vals);
      if (!vis && !interactif) continue;
      const g = s('g', { 'data-id': e.id, class: 'es-el' + (interactif && (e.id === ED.sel || ED.multi.has(e.id)) ? ' sel' : '')
        + (interactif && MO().verrouille(e, lay) ? ' es-fige' : '') + (vis ? '' : ' es-masque') });
      dessinerElement(g, e, vals);
      if (interactif) {
        const b = bboxElement(e);
        if (e.type === 'code_barre' && g.dataset.w) { b.w = +g.dataset.w; b.h = +g.dataset.h + (e.lisible && !DEUX_D.includes(e.symbologie) ? 3 : 0); }
        g.appendChild(s('rect', { x: b.x, y: b.y, width: Math.max(1, b.w), height: Math.max(1, b.h), class: 'es-poignee' }));
      }
      corps.appendChild(g);
    }
    if (interactif && mp && mp.dessinerDessus) mp.dessinerDessus(svg, m, lay);
    return svg;
  }

  // Boîtes réelles (mm) des objets, mesurées sur l'aperçu — pour les contrôles.
  function mesurer(svg) {
    const out = {};
    svg.querySelectorAll('.es-el').forEach(g => {
      try {
        const e = layout().elements.find(x => x.id === g.dataset.id);
        if (!e) return;
        const kids = [...g.children].filter(c => !c.classList.contains('es-poignee') && c.tagName !== 'defs');
        let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
        // Boîte de chaque enfant ramenée au repère de l'étiquette (un picto est
        // dessiné dans un groupe mis à l'échelle).
        const inv = g.getCTM().inverse();
        for (const c of kids) {
          const b = c.getBBox(), mtx = inv.multiply(c.getCTM());
          for (const [px, py] of [[b.x, b.y], [b.x + b.width, b.y], [b.x, b.y + b.height], [b.x + b.width, b.y + b.height]]) {
            const q = new DOMPoint(px, py).matrixTransform(mtx);
            x0 = Math.min(x0, q.x); y0 = Math.min(y0, q.y); x1 = Math.max(x1, q.x); y1 = Math.max(y1, q.y);
          }
        }
        if (x0 === Infinity) return;
        out[e.id] = { x: x0, y: y0, w: x1 - x0, h: y1 - y0, coupe: g.dataset.coupe === '1', cw: +g.dataset.w || 0, ch: +g.dataset.h || 0 };
      } catch (err) { /* élément pas encore rendu */ }
    });
    return out;
  }

  function dessiner() {
    const zone = $id('es-canevas');
    if (!zone || !ED.m) return;
    const montrer = ED.propo && ED.voirPropo;
    const m = montrer ? Object.assign({}, ED.m, { largeur_mm: ED.propo.largeur_mm, hauteur_mm: ED.propo.hauteur_mm }) : ED.m;
    const lay = montrer ? completerLayout(cloner(ED.propo.layout)) : layout();
    const vals = valeursApercu(lay);
    const interactif = !montrer && ED.mode === 'conception';
    const svg = construireSvg(m, lay, interactif, vals);
    zone.replaceChildren(svg);
    if (interactif) brancherSouris(svg);
    ED.boites = mesurer(svg);
    const av = $id('es-avert');
    if (av) av.replaceChildren(...avertissements(lay, vals).map(t => X().h('div', { cls: 'es-avert-ligne', text: t })));
    const dim = $id('es-dim');
    if (dim) dim.textContent = `${X().fmtNum(m.largeur_mm)} × ${X().fmtNum(m.hauteur_mm)} mm · ${ED.m.dpi} dpi` + (montrer ? ' · proposition de Claude' : '')
      + (ED.mode === 'operateur' ? ' · mode opérateur' : '') + (vals._langue ? ' · ' + vals._langue.toUpperCase() : '');
    const ctl = ext('controle');
    if (ctl && ctl.majResume) ctl.majResume();
  }

  // ── Souris / clavier ────────────────────────────────────────────────
  function brancherSouris(svg) {
    let glisse = null;
    const enMm = (ev) => { const pt = svg.createSVGPoint(); pt.x = ev.clientX; pt.y = ev.clientY; return pt.matrixTransform(svg.getScreenCTM().inverse()); };
    svg.addEventListener('pointerdown', (ev) => {
      const g = ev.target.closest('.es-el');
      if (!g) { if (ED.sel || ED.multi.size) { ED.sel = null; ED.multi.clear(); majPanneauElement(); dessiner(); } return; }
      const e = layout().elements.find(x => x.id === g.dataset.id);
      if (!e) return;
      if (ev.shiftKey) {   // sélection multiple (aligner, distribuer)
        if (ED.sel && !ED.multi.size) ED.multi.add(ED.sel);
        ED.multi.has(e.id) ? ED.multi.delete(e.id) : ED.multi.add(e.id);
        ED.sel = e.id; majListe(); majPanneauElement(); dessinerSel();
        return;
      }
      if (!ED.multi.has(e.id)) ED.multi.clear();
      const p = enMm(ev);
      const groupe = (ED.multi.size ? [...ED.multi] : [e.id]).map(id => layout().elements.find(x => x.id === id)).filter(x => x && !fige(x));
      glisse = fige(e) ? null : { e, dx: p.x - e.x, dy: p.y - e.y, bouge: false, groupe: groupe.map(x => ({ x, ox: x.x - e.x, oy: x.y - e.y })) };
      if (ED.sel !== e.id) { ED.sel = e.id; majPanneauElement(); majListe(); }
      svg.setPointerCapture(ev.pointerId);
      svg.focus({ preventScroll: true });
      dessinerSel();
    });
    svg.addEventListener('pointermove', (ev) => {
      if (!glisse) return;
      const p = enMm(ev);
      let nx = Math.max(0, Math.round((p.x - glisse.dx) * 2) / 2);
      let ny = Math.max(0, Math.round((p.y - glisse.dy) * 2) / 2);
      const mpa = ext('miseEnPage');
      if (mpa && mpa.aimanter && !ev.altKey) [nx, ny] = mpa.aimanter(glisse.e, nx, ny, bboxElement(glisse.e));
      if (nx === glisse.e.x && ny === glisse.e.y) return;
      if (!glisse.bouge) { memoriser(); glisse.bouge = true; }
      for (const o of glisse.groupe) { o.x.x = Math.max(0, nx + o.ox); o.x.y = Math.max(0, ny + o.oy); }
      salir();
      // Pendant le glisser, seuls les groupes déplacés sont redessinés : remplacer
      // le SVG ferait perdre la capture du pointeur.
      const vals = valeursApercu(layout());
      for (const o of glisse.groupe) {
        const g = svg.querySelector(`.es-el[data-id="${CSS.escape(o.x.id)}"]`);
        if (!g) continue;
        g.replaceChildren();
        dessinerElement(g, o.x, vals);
        const b = bboxElement(o.x);
        if (o.x.type === 'code_barre' && g.dataset.w) { b.w = +g.dataset.w; b.h = +g.dataset.h; }
        g.appendChild(s('rect', { x: b.x, y: b.y, width: Math.max(1, b.w), height: Math.max(1, b.h), class: 'es-poignee' }));
      }
      const mp = ext('miseEnPage');
      if (mp && mp.reperes) mp.reperes(svg, glisse.e, bboxElement(glisse.e));
    });
    const fin = () => { if (glisse && glisse.bouge) { majChampsPosition(); dessiner(); } glisse = null; };
    svg.addEventListener('pointerup', fin);
    svg.addEventListener('pointercancel', fin);
    svg.addEventListener('keydown', (ev) => {
      const e = elSel();
      if (!e || fige(e)) return;
      const pas = ev.shiftKey ? 5 : 0.5;
      const d = { ArrowLeft: [-pas, 0], ArrowRight: [pas, 0], ArrowUp: [0, -pas], ArrowDown: [0, pas] }[ev.key];
      if (d) {
        ev.preventDefault(); memoriser();
        const cibles = ED.multi.size ? [...ED.multi].map(id => layout().elements.find(x => x.id === id)).filter(x => x && !fige(x)) : [e];
        for (const c of cibles) { c.x = Math.max(0, Math.round((c.x + d[0]) * 2) / 2); c.y = Math.max(0, Math.round((c.y + d[1]) * 2) / 2); }
        salir(); majChampsPosition(); dessiner();
        requestAnimationFrame(() => $id('es-canevas')?.querySelector('svg')?.focus({ preventScroll: true }));
      } else if (ev.key === 'Delete' || ev.key === 'Backspace') { ev.preventDefault(); supprimerElement(e); }
    });
  }
  function dessinerSel() {
    ($id('es-canevas')?.querySelectorAll('.es-el') || []).forEach(g => g.classList.toggle('sel', g.dataset.id === ED.sel || ED.multi.has(g.dataset.id)));
    const mp = ext('miseEnPage');
    if (mp && mp.majBarre) mp.majBarre();
  }
  function majChampsPosition() {
    const e = elSel();
    if (!e) return;
    const fx = $id('es-f-x'), fy = $id('es-f-y');
    if (fx) fx.value = e.x;
    if (fy) fy.value = e.y;
  }

  // ── Panneau objets ──────────────────────────────────────────────────
  const LIBELLE_TYPE = { texte: 'Texte', code_barre: 'Code-barres', cadre: 'Cadre', ellipse: 'Ellipse', ligne: 'Ligne', picto: 'Pictogramme', image: 'Image' };
  const ICONE_TYPE = { texte: 'type', code_barre: 'barcode', cadre: 'square', ellipse: 'circle', ligne: 'minus', picto: 'shield', image: 'image' };

  function ajouter(type, extra) {
    memoriser();
    const L = ED.m.largeur_mm, H = ED.m.hauteur_mm;
    const base = { id: nouvelId(), type, nom: '', x: 5, y: Math.min(H - 10, 5 + layout().elements.length * 4), calque: 'donnees', verrou: false, condition: '', masquer_si_vide: false };
    const par = {
      texte: { valeur: 'Texte', taille: 4, gras: false, largeur: 0, lignes: 1, align: 'gauche', rotation: 0, inverse: false },
      code_barre: { symbologie: 'code128', valeur: '123456789', hauteur: 15, module: 0.375, lisible: true, rotation: 0 },
      cadre: { x: 2, y: 2, largeur: Math.max(5, L - 4), hauteur: Math.max(5, Math.min(30, H - 4)), epaisseur: 0.5, arrondi: 0, plein: false },
      ellipse: { largeur: 20, hauteur: 12, epaisseur: 0.5, plein: false },
      ligne: { orientation: 'h', longueur: Math.max(5, L - 10), epaisseur: 0.5 },
      picto: { picto: 'recyclage', largeur: 12, hauteur: 12, legende: '', taille_legende: 2.2, rotation: 0, calque: 'fond' },
      image: { largeur: 20, hauteur: 12, seuil: 128, tramage: 'seuil', inverse: false, calque: 'fond' },
    }[type];
    const e = Object.assign(base, par, extra || {});
    layout().elements.push(e);
    ED.sel = e.id; ED.multi.clear();
    salir(); X().rendre();
    return e;
  }
  function choisirImage() {
    const i = document.createElement('input');
    i.type = 'file'; i.accept = 'image/png,image/jpeg,image/webp';
    i.onchange = () => {
      const f = i.files[0];
      if (!f) return;
      if (f.size > 600 * 1024) { X().toast('Logo de plus de 600 Ko — le réduire avant de l\'ajouter.', 'danger'); return; }
      const r = new FileReader();
      r.onload = () => {
        const img = new Image();
        img.onload = () => { const w = 25; ajouter('image', { src: r.result, largeur: w, hauteur: Math.round(w * img.naturalHeight / Math.max(1, img.naturalWidth) * 10) / 10, nom: 'Logo' }); };
        img.src = r.result;
      };
      r.readAsDataURL(f);
    };
    i.click();
  }
  function supprimerElement(e) {
    if (fige(e)) { X().toast('Objet figé — seul un concepteur le retire.', 'info'); return; }
    memoriser();
    ED.m.layout.elements = layout().elements.filter(x => x !== e);
    ED.sel = null; ED.multi.delete(e.id); salir(); X().rendre();
  }
  function deplacerOrdre(e, sens) {
    const arr = layout().elements, i = arr.indexOf(e), j = i + sens;
    if (j < 0 || j >= arr.length) return;
    memoriser(); arr.splice(i, 1); arr.splice(j, 0, e); salir(); X().rendre();
  }

  function majListe() {
    const zone = $id('es-liste-el');
    if (!zone) return;
    const { h, ic } = X();
    zone.replaceChildren(...layout().elements.map(e => h('div', {
      cls: 'es-el-ligne' + (e.id === ED.sel || ED.multi.has(e.id) ? ' actif' : '') + (ED.calquesMasques.has(e.calque) ? ' es-el-masque' : ''),
      onclick: (ev) => {
        if (ev.shiftKey) { if (ED.sel && !ED.multi.size) ED.multi.add(ED.sel); ED.multi.has(e.id) ? ED.multi.delete(e.id) : ED.multi.add(e.id); }
        else ED.multi.clear();
        ED.sel = e.id; majListe(); majPanneauElement(); dessinerSel();
      } },
      ic(ICONE_TYPE[e.type], 14),
      h('span', { cls: 'es-el-nom', text: e.nom || resume(e) }),
      MO().verrouille(e, layout()) ? h('span', { cls: 'es-cadenas', 'data-bulle': 'Figé', 'aria-label': 'Objet figé' }, ic('lock', 12)) : null,
      h('span', { cls: 'es-aide', text: LIBELLE_TYPE[e.type] }))));
    if (!layout().elements.length) zone.appendChild(h('div', { cls: 'es-aide', text: 'Étiquette vide. Ajouter un objet ou décrire l\'étiquette à l\'assistant.' }));
  }
  function resume(e) {
    if (e.type === 'texte') return (e.valeur || '').slice(0, 30) || 'Texte';
    if (e.type === 'code_barre') return (X().ES.boot.referentiel.symbologies[e.symbologie] || e.symbologie) + ' ' + (e.valeur || '').slice(0, 20);
    if (e.type === 'picto') return ((X().ES.boot.referentiel.pictos || {})[e.picto] || {}).libelle || 'Pictogramme';
    return LIBELLE_TYPE[e.type];
  }

  function panneauCalques() {
    const { h, ic } = X();
    const lay = layout();
    return h('div', { cls: 'es-panneau' },
      h('div', { cls: 'es-panneau-titre', text: 'Calques' }),
      ...lay.calques.map(c => h('div', { cls: 'es-calque' },
        h('button', { cls: 'es-btn es-btn-icone' + (ED.calquesMasques.has(c.id) ? '' : ' es-btn-actif'), type: 'button',
          'data-bulle': ED.calquesMasques.has(c.id) ? 'Afficher' : 'Masquer', 'aria-label': 'Afficher ou masquer le calque ' + c.nom,
          onclick: () => { ED.calquesMasques.has(c.id) ? ED.calquesMasques.delete(c.id) : ED.calquesMasques.add(c.id); majListe(); dessiner(); } }, ic('eye', 13)),
        h('span', { cls: 'es-el-nom', text: c.nom }),
        h('button', { cls: 'es-btn es-btn-icone' + (c.verrou ? ' es-btn-actif' : ''), type: 'button', disabled: concepteur() ? null : true,
          'data-bulle': c.verrou ? 'Déverrouiller' : 'Verrouiller', 'aria-label': (c.verrou ? 'Déverrouiller' : 'Verrouiller') + ' le calque ' + c.nom,
          onclick: () => { memoriser(); c.verrou = !c.verrou; salir(); X().rendre(); } }, ic('lock', 13)))));
  }

  function champNum(id, label, e, cle, pas, aide) {
    const { h, champ } = X();
    const i = h('input', { cls: 'es-input', id, type: 'number', step: pas || '0.5', value: e[cle], disabled: fige(e) ? true : null });
    i.addEventListener('focus', memoriser, { once: true });
    i.addEventListener('input', () => { e[cle] = num(i.value, e[cle]); salir(); dessiner(); });
    return champ(label, i, aide);
  }
  function champCase(label, e, cle, apres) {
    const { h } = X();
    const i = h('input', { type: 'checkbox', checked: !!e[cle], disabled: fige(e) ? true : null });
    i.addEventListener('change', () => { memoriser(); e[cle] = i.checked; salir(); dessiner(); majListe(); if (apres) apres(); });
    return h('label', { cls: 'es-case' }, i, h('span', { text: label }));
  }
  function champChoix(label, e, cle, options, apres) {
    const { h, champ } = X();
    const sel = h('select', { cls: 'es-input', disabled: fige(e) ? true : null }, ...Object.entries(options).map(([k, l]) => h('option', { value: k, text: l })));
    sel.value = String(e[cle]);
    sel.addEventListener('change', () => {
      memoriser();
      e[cle] = /^\d+$/.test(sel.value) && typeof e[cle] === 'number' ? parseInt(sel.value, 10) : sel.value;
      salir(); dessiner(); majListe(); if (apres) apres();
    });
    return champ(label, sel);
  }
  function champTexte(label, e, cle, multi, aide) {
    const { h, champ } = X();
    const i = multi ? h('textarea', { cls: 'es-input', rows: 2, value: e[cle] || '' }) : h('input', { cls: 'es-input', value: e[cle] || '' });
    if (fige(e)) i.disabled = true;
    i.addEventListener('focus', memoriser, { once: true });
    i.addEventListener('input', () => { e[cle] = i.value; salir(); dessiner(); majListe(); });
    const blocs = [i];
    if ((cle === 'valeur' || cle === 'legende' || cle === 'condition') && layout().variables.length && !fige(e)) {
      blocs.push(h('div', { cls: 'es-puces' }, ...layout().variables.map(v => h('button', {
        cls: 'es-puce', type: 'button', 'data-bulle': 'Insérer', 'aria-label': 'Insérer ' + v.libelle, text: cle === 'condition' ? v.nom : '{{' + v.nom + '}}',
        onclick: () => {
          const ins = cle === 'condition' ? v.nom : '{{' + v.nom + '}}';
          const pos = i.selectionStart ?? i.value.length;
          i.value = i.value.slice(0, pos) + ins + i.value.slice(i.selectionEnd ?? pos);
          i.dispatchEvent(new Event('input')); i.focus();
        } }))));
    }
    return champ(label, h('div', { cls: 'es-pile' }, ...blocs), aide);
  }

  function majPanneauElement() {
    const zone = $id('es-panneau-el');
    if (!zone) return;
    const { h, bouton, ES } = X();
    const e = elSel();
    const mp = ext('miseEnPage');
    if (ED.multi.size > 1) {
      zone.replaceChildren(h('div', { cls: 'es-form' }, h('div', { cls: 'es-panneau-titre', text: ED.multi.size + ' objets sélectionnés' }),
        mp && mp.barreAlignement ? mp.barreAlignement() : null,
        h('div', { cls: 'es-aide', text: 'Maj + clic : ajouter ou retirer un objet. Flèches : déplacer l\'ensemble.' })));
      return;
    }
    if (!e) { zone.replaceChildren(h('div', { cls: 'es-aide', text: 'Cliquer un objet sur l\'aperçu ou dans la liste. Maj + clic : sélection multiple (aligner, distribuer). Flèches : 0,5 mm (Maj : 5 mm). Alt pendant le glisser : sans magnétisme.' })); return; }
    const rot = { 0: '0°', 90: '90°', 180: '180°', 270: '270°' };
    const f = [];
    if (fige(e)) f.push(h('div', { cls: 'es-encart es-fige-encart' }, X().ic('lock', 14), h('span', { text: 'Objet figé : seul un concepteur le modifie.' })));
    f.push(champTexte('Nom (repère)', e, 'nom'));
    f.push(h('div', { cls: 'es-ligne2' }, champNum('es-f-x', 'X (mm)', e, 'x'), champNum('es-f-y', 'Y (mm)', e, 'y')));
    if (e.type === 'texte') {
      f.push(champTexte('Texte', e, 'valeur', true, 'Variables : {{nom}}'));
      f.push(h('div', { cls: 'es-ligne2' }, champNum('es-f-t', 'Hauteur car. (mm)', e, 'taille'), champChoix('Rotation', e, 'rotation', rot)));
      f.push(h('div', { cls: 'es-ligne2' }, champNum('es-f-l', 'Largeur bloc (mm)', e, 'largeur', '0.5', '0 = sans bloc'), champNum('es-f-n', 'Lignes max', e, 'lignes', '1')));
      f.push(champChoix('Alignement', e, 'align', { gauche: 'Gauche', centre: 'Centré', droite: 'Droite' }));
      f.push(h('div', { cls: 'es-ligne2' }, champCase('Gras', e, 'gras'), champCase('Inversé (blanc)', e, 'inverse')));
      if (mp && mp.proprietesTexte) f.push(mp.proprietesTexte(e, { memoriser, salir, dessiner, fige: fige(e) }));
    } else if (e.type === 'code_barre') {
      f.push(champChoix('Symbologie', e, 'symbologie', ES.boot.referentiel.symbologies, majPanneauElement));
      const gs1 = e.symbologie === 'gs1_128' || e.symbologie === 'gs1_datamatrix';
      f.push(champTexte('Données', e, 'valeur', false, gs1 ? 'AI entre parenthèses : (00){{sscc}}, (02)…(37)…' : (e.symbologie === 'ean13' ? '12 chiffres, la clé est calculée.' : (e.symbologie === 'qrcode' ? 'Lien vers la fiche : {{lien_fiche}} (variable source « produit.lien_fiche »).' : null))));
      const deuxD = DEUX_D.includes(e.symbologie);
      f.push(h('div', { cls: 'es-ligne2' }, deuxD ? h('span') : champNum('es-f-h', 'Hauteur (mm)', e, 'hauteur'),
        champNum('es-f-m', 'Module (mm)', e, 'module', '0.025', 'Plus petit module')));
      f.push(h('div', { cls: 'es-ligne2' }, champChoix('Rotation', e, 'rotation', rot), deuxD || e.symbologie === 'pdf417' ? h('span') : champCase('Texte en clair', e, 'lisible')));
      if (e.symbologie === 'pdf417') f.push(champNum('es-f-col', 'Colonnes (0 = auto)', e, 'colonnes', '1'));
      if (e.symbologie === 'qrcode') f.push(champChoix('Correction', e, 'correction', { L: 'L (7 %)', M: 'M (15 %)', Q: 'Q (25 %)', H: 'H (30 %)' }));
      if (gs1 && ext('gs1') && ext('gs1').aideAi) f.push(ext('gs1').aideAi(e, { memoriser, salir, dessiner, majPanneauElement }));
    } else if (e.type === 'cadre') {
      f.push(h('div', { cls: 'es-ligne2' }, champNum('es-f-w', 'Largeur (mm)', e, 'largeur'), champNum('es-f-hh', 'Hauteur (mm)', e, 'hauteur')));
      f.push(h('div', { cls: 'es-ligne2' }, champNum('es-f-e', 'Épaisseur (mm)', e, 'epaisseur', '0.1'), champNum('es-f-a', 'Arrondi (0–8)', e, 'arrondi', '1')));
      f.push(champCase('Plein', e, 'plein'));
    } else if (e.type === 'ellipse') {
      f.push(h('div', { cls: 'es-ligne2' }, champNum('es-f-w', 'Largeur (mm)', e, 'largeur'), champNum('es-f-hh', 'Hauteur (mm)', e, 'hauteur')));
      f.push(h('div', { cls: 'es-ligne2' }, champNum('es-f-e', 'Épaisseur (mm)', e, 'epaisseur', '0.1'), champCase('Pleine', e, 'plein')));
    } else if (e.type === 'ligne') {
      f.push(champChoix('Orientation', e, 'orientation', { h: 'Horizontale', v: 'Verticale' }));
      f.push(h('div', { cls: 'es-ligne2' }, champNum('es-f-lg', 'Longueur (mm)', e, 'longueur'), champNum('es-f-e', 'Épaisseur (mm)', e, 'epaisseur', '0.1')));
    } else if (e.type === 'picto') {
      const pics = Object.fromEntries(Object.entries(ES.boot.referentiel.pictos || {}).map(([k, v]) => [k, v.libelle]));
      f.push(champChoix('Pictogramme', e, 'picto', pics, () => { const p = ES.boot.referentiel.pictos[e.picto]; if (p && p.legende && !e.legende) { e.legende = p.legende; majPanneauElement(); dessiner(); } }));
      f.push(h('div', { cls: 'es-ligne2' }, champNum('es-f-w', 'Largeur (mm)', e, 'largeur'), champNum('es-f-hh', 'Hauteur (mm)', e, 'hauteur')));
      f.push(champTexte('Légende', e, 'legende', false, e.picto === 'fsc' ? '{{fsc_licence}} : licence lue dans la configuration (MyQualité).' : 'Facultatif.'));
      f.push(h('div', { cls: 'es-ligne2' }, champNum('es-f-tl', 'Taille légende (mm)', e, 'taille_legende', '0.1'), champChoix('Rotation', e, 'rotation', rot)));
    } else if (e.type === 'image') {
      f.push(h('div', { cls: 'es-ligne2' }, champNum('es-f-w', 'Largeur (mm)', e, 'largeur'), champNum('es-f-hh', 'Hauteur (mm)', e, 'hauteur')));
      f.push(h('div', { cls: 'es-ligne2' }, champNum('es-f-s', 'Seuil noir (0–255)', e, 'seuil', '1'), champCase('Inversée', e, 'inverse')));
    }
    if (mp && mp.proprieteCouleur && e.type !== 'image') f.push(mp.proprieteCouleur(e, { memoriser, salir, dessiner, fige: fige(e) }));
    // Calque, verrou, conditions d'affichage
    f.push(champChoix('Calque', e, 'calque', Object.fromEntries(layout().calques.map(c => [c.id, c.nom]))));
    if (concepteur()) f.push(champCase('Figé (logo, mention imposée)', e, 'verrou'));
    if (e.type === 'texte' || e.type === 'code_barre') f.push(champCase('Masquer si vide', e, 'masquer_si_vide'));
    f.push(champTexte('Afficher si', e, 'condition', false, 'Expression, ex. NON(VIDE(lot)) ou qte > 100. Vide = toujours.'));
    f.push(h('div', { cls: 'es-ligne-actions' },
      bouton('Monter', () => deplacerOrdre(e, -1), '', 'arrow-up'),
      bouton('Descendre', () => deplacerOrdre(e, 1), '', 'arrow-down'),
      bouton('Dupliquer', () => { memoriser(); const c = cloner(e); c.id = nouvelId(); c.x += 2; c.y += 2; c.verrou = false; layout().elements.push(c); ED.sel = c.id; salir(); X().rendre(); }, '', 'copy'),
      fige(e) ? null : bouton('Retirer', () => supprimerElement(e), 'danger', 'trash-2')));
    zone.replaceChildren(h('div', { cls: 'es-form' }, ...f));
  }

  // ── Variables ───────────────────────────────────────────────────────
  function panneauVariables() {
    const { h, champ, bouton, ES } = X();
    const ref = ES.boot.referentiel, types = ref.types_variable;
    const lignes = layout().variables.map((v, idx) => {
      const corps = [];
      const nom = h('input', { cls: 'es-input es-mono', value: v.nom, maxlength: 40 });
      nom.addEventListener('focus', memoriser, { once: true });
      nom.addEventListener('change', () => {
        const nv = nom.value.trim().toLowerCase().replace(/[^a-z0-9_]/g, '_').replace(/^[^a-z]+/, '');
        if (!nv) { nom.value = v.nom; return; }
        const re = new RegExp('\\{\\{\\s*' + v.nom + '\\s*\\}\\}', 'g');
        layout().elements.forEach(e => { if (e.valeur) e.valeur = e.valeur.replace(re, '{{' + nv + '}}'); if (e.legende) e.legende = e.legende.replace(re, '{{' + nv + '}}'); });
        v.nom = nv; salir(); X().rendre();
      });
      const lib = h('input', { cls: 'es-input', value: v.libelle, maxlength: 80 });
      lib.addEventListener('input', () => { v.libelle = lib.value; salir(); });
      const typ = h('select', { cls: 'es-input' }, ...Object.entries(types).map(([k, l]) => h('option', { value: k, text: l })));
      typ.value = v.type;
      typ.addEventListener('change', () => { memoriser(); Object.assign(v, defautsVar(typ.value), { nom: v.nom, libelle: v.libelle, type: typ.value }); salir(); X().rendre(); });
      corps.push(h('div', { cls: 'es-ligne2' }, champ('Nom', nom), champ('Libellé', lib)), champ('Type', typ));
      const ch = (label, cle, attrs, aide) => {
        const i = h('input', Object.assign({ cls: 'es-input', value: v[cle] ?? '' }, attrs || {}));
        i.addEventListener('focus', memoriser, { once: true });
        i.addEventListener(attrs && attrs.type === 'checkbox' ? 'change' : 'input', () => {
          v[cle] = attrs && attrs.type === 'checkbox' ? i.checked : (attrs && attrs.type === 'number' ? (parseInt(i.value, 10) || 0) : i.value);
          salir(); dessiner();
        });
        if (attrs && attrs.type === 'checkbox') { i.checked = !!v[cle]; return h('label', { cls: 'es-case' }, i, h('span', { text: label })); }
        return champ(label, i, aide);
      };
      if (v.type === 'fixe') corps.push(ch('Valeur', 'valeur'));
      if (v.type === 'saisie') {
        corps.push(ch('Valeur par défaut', 'valeur'), ch('Obligatoire', 'obligatoire', { type: 'checkbox' }));
        const dn = ext('donnees');
        if (dn && dn.reglagesSaisie) corps.push(dn.reglagesSaisie(v, { memoriser, salir, dessiner }));
      }
      if (v.type === 'source') {
        const sel = h('select', { cls: 'es-input' }, h('option', { value: '', text: '— Choisir la donnée —' }),
          ...Object.entries(ref.sources || {}).map(([t, src]) => h('optgroup', { label: src.libelle }, ...src.champs.map(c => h('option', { value: c.cle, text: c.libelle })))));
        sel.value = v.champ || '';
        sel.addEventListener('change', () => { memoriser(); v.champ = sel.value; salir(); X().rendre(); });
        corps.push(champ('Donnée MySifa', sel), ch('Valeur d\'exemple', 'valeur', null, 'Affichée dans l\'aperçu, remplacée à l\'impression.'), ch('Obligatoire', 'obligatoire', { type: 'checkbox' }));
      }
      if (v.type === 'formule') corps.push(ch('Expression', 'expression', { cls: 'es-input es-mono' }, 'Ex. MAJUSCULE(client) & " - " & lot · SI(VIDE(lot); "-"; lot) · ZEROS(num; 6). Fonctions : ' + (ref.fonctions || []).join(', ')),
        h('div', { cls: 'es-aide es-mono', text: '= ' + (MO().evaluer(v.expression || '', valeursApercu(layout())).valeur || '—') }));
      if (v.type === 'compteur') {
        corps.push(
          h('div', { cls: 'es-ligne2' }, ch('Départ', 'debut', { type: 'number', min: 0 }), ch('Pas', 'pas', { type: 'number', min: 1 })),
          h('div', { cls: 'es-ligne3' }, ch('Préfixe', 'prefixe'), ch('Chiffres', 'longueur', { type: 'number', min: 0, max: 20 }), ch('Suffixe', 'suffixe')),
          ch('Reprendre au dernier numéro mémorisé', 'reprise', { type: 'checkbox' }));
        if (ED.m.id) corps.push(h('div', { cls: 'es-ligne-actions' }, bouton('Numéros', () => ext('biblio') && ext('biblio').modaleCompteurs(ED.m), '', 'hash')));
      }
      if (v.type === 'sscc') corps.push(
        h('div', { cls: 'es-aide', text: 'À utiliser seulement si le client vous a confié son préfixe GS1 et une plage de numéros. S\'il fournit lui-même ses SSCC, prendre une variable « Saisie » avec le contrôle « SSCC fourni par le client ».' }),
        h('div', { cls: 'es-ligne2' }, ch('Extension', 'extension', { maxlength: 1 }, '1 chiffre'), ch('Préfixe GS1 du client', 'prefixe_gs1', { maxlength: 10 }, '7 à 10 chiffres')),
        h('div', { cls: 'es-ligne2' }, ch('Première série', 'serie_debut', { type: 'number', min: 0 }, 'Plage attribuée par le client'), ch('Dernière série', 'serie_fin', { type: 'number', min: 0 }, '0 = sans borne')),
        h('div', { cls: 'es-aide', text: 'Série et clé calculées. Le compteur est commun à toutes les étiquettes de ce préfixe : un SSCC ne sort jamais deux fois.' }));
      if (v.type === 'date') {
        const fmt = h('select', { cls: 'es-input' }, ...(ref.formats_date || []).map(f => h('option', { value: f.format, text: f.libelle })), h('option', { value: '__libre', text: 'Autre format…' }));
        fmt.value = (ref.formats_date || []).some(f => f.format === v.format) ? v.format : '__libre';
        fmt.addEventListener('change', () => { if (fmt.value !== '__libre') { memoriser(); v.format = fmt.value; salir(); X().rendre(); } });
        const base = h('select', { cls: 'es-input' }, h('option', { value: 'impression', text: 'Jour de l\'impression' }),
          ...layout().variables.filter(x => x !== v && ['saisie', 'source', 'date'].includes(x.type)).map(x => h('option', { value: x.nom, text: x.libelle })));
        base.value = v.base || 'impression';
        base.addEventListener('change', () => { memoriser(); v.base = base.value; salir(); X().rendre(); });
        corps.push(champ('À partir de', base, 'Ex. date de fabrication saisie, pour une DLUO.'),
          h('div', { cls: 'es-ligne2' }, ch('+ mois', 'decalage_mois', { type: 'number' }), ch('+ jours', 'decalage_jours', { type: 'number' })),
          champ('Format', fmt), ch('Format (codes)', 'format', { cls: 'es-input es-mono' }, '%d %m %Y %y %j (jour de l\'année) %V (semaine ISO) %G %b'),
          h('div', { cls: 'es-aide es-mono', text: '= ' + (valeursApercu(layout())[v.nom] || '—') }));
      }
      corps.push(h('div', { cls: 'es-ligne-actions' }, bouton('Retirer', () => { memoriser(); layout().variables.splice(idx, 1); salir(); X().rendre(); }, 'danger', 'trash-2')));
      return h('details', { cls: 'es-var', open: v._ouvert ? true : null, ontoggle: (ev) => { v._ouvert = ev.target.open; } },
        h('summary', {}, h('code', { text: '{{' + v.nom + '}}' }), h('span', { cls: 'es-aide', text: types[v.type] + (v.type === 'source' && v.champ ? ' · ' + v.champ : '') })),
        h('div', { cls: 'es-form' }, ...corps));
    });
    return h('div', { cls: 'es-panneau' },
      h('div', { cls: 'es-panneau-titre' }, 'Variables',
        h('button', { cls: 'es-btn es-btn-icone', type: 'button', 'data-bulle': 'Variable', 'aria-label': 'Ajouter une variable', onclick: () => {
          memoriser();
          const noms = new Set(layout().variables.map(v => v.nom));
          let i = 1; while (noms.has('champ' + i)) i++;
          layout().variables.push(Object.assign({ nom: 'champ' + i, libelle: 'Champ ' + i, type: 'saisie', _ouvert: true }, defautsVar('saisie')));
          salir(); X().rendre();
        } }, X().ic('plus', 14))),
      layout().variables.length ? null : h('div', { cls: 'es-aide', text: 'Une variable remplace {{nom}} dans les textes et codes : saisie, donnée MySifa, compteur, SSCC, date calculée, formule.' }),
      ...lignes);
  }
  function defautsVar(type) {
    return { fixe: { valeur: '' }, saisie: { valeur: '', obligatoire: true }, source: { champ: '', valeur: '', obligatoire: false },
      compteur: { debut: 1, pas: 1, longueur: 6, prefixe: '', suffixe: '', reprise: true },
      sscc: { extension: '0', prefixe_gs1: '', serie_debut: 0, serie_fin: 0 },
      date: { base: 'impression', format: '%d/%m/%Y', decalage_jours: 0, decalage_mois: 0 }, formule: { expression: '' } }[type] || {};
  }

  // ── Assistant IA ────────────────────────────────────────────────────
  function panneauIa() {
    const { h, bouton, api, toast, selectModeleIa } = X();
    const modeleIa = selectModeleIa();
    const consigne = h('textarea', { cls: 'es-input', id: 'es-ia-consigne', rows: 4, maxlength: 4000,
      placeholder: 'Ex. Ajoute un SSCC en GS1-128 sous le code produit, avec le numéro en clair au-dessus.' });
    const go = bouton('Proposer', async () => {
      if (!consigne.value.trim()) { toast('Décrire la modification souhaitée.', 'danger'); return; }
      ED.iaBusy = true; go.disabled = true; go.textContent = 'Claude travaille…'; go.classList.add('ia-travail');
      try {
        const r = await api('/ia/proposer', { method: 'POST', body: {
          consigne: consigne.value, modele: modeleIa.select.value, largeur_mm: ED.m.largeur_mm, hauteur_mm: ED.m.hauteur_mm, dpi: ED.m.dpi, layout: nettoyer(layout()) } });
        ED.propo = r; ED.voirPropo = true; X().rendre();
      } catch (e) { toast(e.message, 'danger'); go.disabled = false; go.textContent = 'Proposer'; go.classList.remove('ia-travail'); }
      ED.iaBusy = false;
    }, 'ia', 'zap');
    consigne.addEventListener('keydown', (e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) go.click(); });
    const blocs = [h('div', { cls: 'es-panneau-titre' }, 'Assistant ', h('span', { cls: 'ia-badge', text: 'IA' })),
      h('div', { cls: 'es-aide', text: 'Décrire la modification. Claude propose une nouvelle mise en page, rien n\'est enregistré avant « Appliquer ».' })];
    if (ED.propo) {
      const p = ED.propo;
      blocs.push(h('div', { cls: 'es-propo' },
        h('div', { cls: 'es-propo-resume', text: p.resume || 'Proposition prête.' }),
        h('div', { cls: 'es-aide', text: 'Proposé par ' + (p.modele_libelle || p.modele) + (p.modele_reel && !String(p.modele_reel).startsWith(p.modele) ? ` (relayé par ${p.modele_reel})` : '') }),
        p.remarques.length ? h('ul', { cls: 'es-propo-remarques' }, ...p.remarques.map(r => h('li', { text: r }))) : null,
        h('div', { cls: 'es-bascule' },
          h('button', { cls: 'es-puce' + (!ED.voirPropo ? ' actif' : ''), type: 'button', text: 'Avant', onclick: () => { ED.voirPropo = false; X().rendre(); } }),
          h('button', { cls: 'es-puce' + (ED.voirPropo ? ' actif' : ''), type: 'button', text: 'Proposition', onclick: () => { ED.voirPropo = true; X().rendre(); } })),
        h('div', { cls: 'es-ligne-actions' },
          bouton('Écarter', () => { ED.propo = null; X().rendre(); }),
          bouton('Appliquer', () => {
            memoriser();
            const garde = layout().elements.filter(e => fige(e));
            const nouveau = completerLayout(cloner(p.layout));
            // Un objet figé ne se laisse pas remplacer par la proposition.
            for (const g of garde) { const i = nouveau.elements.findIndex(e => e.id === g.id); if (i >= 0) nouveau.elements[i] = g; else nouveau.elements.unshift(g); }
            nouveau.calques = layout().calques;
            ED.m.layout = nouveau; ED.m.largeur_mm = p.largeur_mm; ED.m.hauteur_mm = p.hauteur_mm;
            ED.propo = null; ED.sel = null; salir(); X().rendre();
            X().toast('Proposition appliquée — enregistrer pour la garder.');
          }, 'accent', 'check'))));
    }
    blocs.push(modeleIa.bloc, consigne, h('div', { cls: 'es-ligne-actions' }, go));
    return h('div', { cls: 'es-panneau es-ia ia-zone' }, ...blocs);
  }

  function nettoyer(lay) { return JSON.parse(JSON.stringify(lay, (k, v) => (k.startsWith('_') ? undefined : v))); }

  // ── Barre du haut, enregistrement, aperçu exact, impression ────────
  async function enregistrer() {
    const { api, toast } = X();
    const b = $id('es-enregistrer');
    if (b) { b.disabled = true; b.textContent = 'Enregistrement…'; }
    try {
      const r = await api('/modeles/' + ED.m.id, { method: 'PATCH', body: {
        nom: ED.m.nom, description: ED.m.description, dossier_id: ED.m.dossier_id, usage: ED.m.usage || '', client: ED.m.client || '',
        largeur_mm: ED.m.largeur_mm, hauteur_mm: ED.m.hauteur_mm, dpi: ED.m.dpi, layout: nettoyer(layout()) } });
      Object.assign(ED.m, { largeur_mm: r.largeur_mm, hauteur_mm: r.hauteur_mm, dpi: r.dpi, updated_at: r.updated_at, version: r.version,
        statut_validation: r.statut_validation, version_approuvee: r.version_approuvee });
      ED.dirty = false;
      toast(r.statut_validation === 'brouillon' && r.version_approuvee ? `Étiquette enregistrée (version ${r.version}). La production imprime la version ${r.version_approuvee} jusqu'à approbation.` : 'Étiquette enregistrée.');
      await X().charger();
      X().rendre();
    } catch (e) { toast(e.message, 'danger'); }
    if (b) { b.textContent = 'Enregistrer'; b.disabled = !ED.dirty; }
  }

  async function apercuExact() {
    const { api, h, modale, bouton, fermerModale } = X();
    const corps = { modele_id: ED.m.id, largeur_mm: ED.m.largeur_mm, hauteur_mm: ED.m.hauteur_mm, dpi: ED.m.dpi, layout: nettoyer(layout()),
      saisies: Object.assign({}, ED.saisies, ED.langue ? { _langue: ED.langue } : {}) };
    const zone = h('div', { cls: 'es-apercu-exact' }, h('div', { cls: 'es-vide', text: 'Rendu du ZPL…' }));
    const zplPre = h('pre', { cls: 'es-zpl', hidden: true });
    modale('Aperçu imprimante — ' + ED.m.nom, h('div', {}, zone,
      h('p', { cls: 'es-aide', text: 'Rendu exact du ZPL envoyé à l\'imprimante, avec les valeurs de l\'aperçu. Rien n\'est consommé.' }),
      zplPre), [bouton('Voir le ZPL', () => { zplPre.hidden = !zplPre.hidden; }), bouton('Fermer', fermerModale)], true);
    try {
      const [z, png] = await Promise.all([
        api('/apercu', { method: 'POST', body: corps }),
        fetch(X().API + '/apercu.png', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corps) })
          .then(async r => { if (!r.ok) { const e = await r.json().catch(() => ({})); throw new Error(e.detail || 'Rendu indisponible.'); } return r.blob(); }),
      ]);
      zplPre.textContent = z.zpl;
      zone.replaceChildren(h('img', { alt: 'Aperçu de l\'étiquette', src: URL.createObjectURL(png) }));
    } catch (e) {
      zone.replaceChildren(h('div', { cls: 'es-vide es-erreur', text: e.message }));
      api('/apercu', { method: 'POST', body: corps }).then(z => { zplPre.textContent = z.zpl; zplPre.hidden = false; }).catch(() => {});
    }
  }

  // Impression : module d'impression s'il est chargé (version approuvée,
  // une étiquette avec les valeurs saisies), sinon la fenêtre intégrée.
  async function imprimer() {
    const { toast, api } = X();
    if (ED.dirty) { toast('Enregistrer avant d\'imprimer.', 'info'); return; }
    if (!ED.m.version_approuvee) { toast('Étiquette jamais approuvée — la faire valider avant d\'imprimer.', 'danger'); return; }
    const imp = window.MySifaEtiqImpression;
    if (imp && typeof imp.imprimer === 'function') {
      try {
        const modele = await api('/modeles/' + ED.m.id + '/production');
        const enr = Object.assign({}, ED.saisies, ED.langue ? { _langue: ED.langue } : {});
        await imp.imprimer({ modele, enregistrements: [enr], quantite: 1 });
      } catch (e) { toast(e.message, 'danger'); }
      return;
    }
    X().modaleImpression(ED.m, { saisies: ED.saisies });
  }

  function quitter() {
    const { confirmer, ES } = X();
    const sortir = async () => { ED.m = null; ED.propo = null; ED.dirty = false; ED.mode = 'conception'; ED.saisies = {}; ED.source = null; ES.view = 'liste'; await X().charger(); X().rendre(); };
    if (ED.dirty) confirmer('Des modifications ne sont pas enregistrées. Quitter sans enregistrer ?', 'Quitter', sortir);
    else sortir();
  }

  function barreHaut() {
    const { h, bouton, selectDossiers, ES, ic } = X();
    const ref = ES.boot.referentiel;
    const nom = h('input', { cls: 'es-input es-nom', value: ED.m.nom, maxlength: 120, 'data-bulle': 'Nom', 'aria-label': 'Nom de l\'étiquette' });
    nom.addEventListener('input', () => { ED.m.nom = nom.value; salir(); });
    const desc = h('input', { cls: 'es-input', value: ED.m.description || '', maxlength: 1000, placeholder: 'Description (ce qui la distingue)' });
    desc.addEventListener('input', () => { ED.m.description = desc.value; salir(); });
    const dossier = selectDossiers(ED.m.dossier_id);
    dossier.addEventListener('change', () => { ED.m.dossier_id = parseInt(dossier.value, 10); salir(); });
    const usage = h('select', { cls: 'es-input', 'data-bulle': 'Usage', 'aria-label': 'Usage de l\'étiquette' }, h('option', { value: '', text: '— Usage —' }),
      ...(ref.usages || []).map(u => h('option', { value: u.id, text: u.libelle })));
    usage.value = ED.m.usage || '';
    usage.addEventListener('change', () => { ED.m.usage = usage.value; salir(); });
    const client = h('input', { cls: 'es-input es-court-l', value: ED.m.client || '', maxlength: 120, placeholder: 'Client', 'aria-label': 'Client' });
    client.addEventListener('input', () => { ED.m.client = client.value; salir(); });
    const fmt = (cle, pas) => {
      const i = h('input', { cls: 'es-input es-court', type: 'number', step: pas, value: ED.m[cle] });
      i.addEventListener('focus', memoriser, { once: true });
      i.addEventListener('input', () => { ED.m[cle] = num(i.value, ED.m[cle]); salir(); dessiner(); });
      return i;
    };
    const dpi = h('select', { cls: 'es-input es-court' }, ...ref.dpi.map(x => h('option', { value: x, text: x + ' dpi' })));
    dpi.value = String(ED.m.dpi);
    dpi.addEventListener('change', () => { ED.m.dpi = parseInt(dpi.value, 10); salir(); dessiner(); });
    const enr = bouton('Enregistrer', enregistrer, 'accent', 'save');
    enr.id = 'es-enregistrer'; enr.disabled = !ED.dirty;
    const langues = layout().langues || ['fr'];
    const selLangue = langues.length > 1 ? h('select', { cls: 'es-input es-court', 'data-bulle': 'Langue', 'aria-label': 'Langue de l\'aperçu' },
      ...langues.map(l => h('option', { value: l, text: l.toUpperCase() }))) : null;
    if (selLangue) { selLangue.value = ED.langue || layout().langue_defaut || langues[0]; selLangue.addEventListener('change', () => { ED.langue = selLangue.value; dessiner(); X().rendre(); }); }
    const operateur = ED.mode === 'operateur';
    const bib = ext('biblio');
    return h('div', { cls: 'es-ed-haut' },
      h('div', { cls: 'es-ed-ligne' },
        h('button', { cls: 'es-btn', type: 'button', onclick: quitter, 'data-bulle': 'Liste' }, ic('arrow-left', 15), 'Étiquettes'),
        operateur ? h('div', { cls: 'es-titre', text: ED.m.nom }) : nom, operateur ? null : dossier,
        bib && bib.badgeValidation ? bib.badgeValidation(ED.m) : null,
        h('div', { cls: 'es-actions' },
          h('div', { cls: 'es-bascule', role: 'group', 'aria-label': 'Mode' },
            h('button', { cls: 'es-puce' + (!operateur ? ' actif' : ''), type: 'button', text: 'Conception', 'data-bulle': 'Concevoir', onclick: () => { ED.mode = 'conception'; X().rendre(); } }),
            h('button', { cls: 'es-puce' + (operateur ? ' actif' : ''), type: 'button', text: 'Opérateur', 'data-bulle': 'Remplir', onclick: () => { ED.mode = 'operateur'; ED.sel = null; ED.multi.clear(); X().rendre(); } })),
          selLangue,
          operateur ? null : bouton('Annuler', annuler, '', 'rotate-ccw'),
          bouton('Aperçu imprimante', apercuExact, '', 'eye'),
          bib && bib.boutonsEditeur ? bib.boutonsEditeur(ED.m) : null,
          ext('donnees') ? bouton('Série', () => ext('donnees').modaleSerie(ED.m), '', 'layers') : null,
          bouton('Imprimer', imprimer, operateur ? 'accent' : '', 'printer'),
          operateur ? null : enr)),
      operateur ? null : h('div', { cls: 'es-ed-ligne' }, desc, usage, client,
        h('span', { cls: 'es-aide', text: 'Format' }), fmt('largeur_mm', '0.5'), h('span', { text: '×' }), fmt('hauteur_mm', '0.5'),
        h('span', { cls: 'es-aide', text: 'mm' }), dpi));
  }

  // ── Vue ─────────────────────────────────────────────────────────────
  function ongletsDroite() {
    const { h } = X();
    const libelles = { variables: 'Variables', donnees: 'Données', page: 'Page', controle: 'Contrôle', ia: 'Assistant' };
    const dispo = PANNEAUX.filter(p => p === 'variables' || p === 'ia' || ext({ donnees: 'donnees', page: 'miseEnPage', controle: 'controle' }[p]));
    if (!dispo.includes(ED.panneau)) ED.panneau = 'variables';
    const tete = h('div', { cls: 'es-onglets', role: 'tablist' }, ...dispo.map(p => h('button', {
      cls: 'es-onglet' + (ED.panneau === p ? ' actif' : '') + (p === 'ia' ? ' es-onglet-ia' : ''), type: 'button', role: 'tab',
      'data-bulle': libelles[p], text: libelles[p], onclick: () => { ED.panneau = p; X().rendre(); } })));
    let corps;
    if (ED.panneau === 'ia') corps = panneauIa();
    else if (ED.panneau === 'donnees') corps = ext('donnees').panneau();
    else if (ED.panneau === 'page') corps = ext('miseEnPage').panneau();
    else if (ED.panneau === 'controle') corps = ext('controle').panneau();
    else corps = panneauVariables();
    return [tete, corps];
  }
  function vue() {
    const { h, bouton } = X();
    if (!ED.m) return h('div', { cls: 'es-vide', text: 'Aucune étiquette ouverte.' });
    completerLayout(layout());
    const centre = h('div', { cls: 'es-ed-centre' },
      h('div', { cls: 'es-dim', id: 'es-dim' }),
      ext('miseEnPage') && ED.mode === 'conception' && ext('miseEnPage').barreOutils ? ext('miseEnPage').barreOutils() : null,
      h('div', { cls: 'es-canevas' + (ED.propo && ED.voirPropo ? ' es-canevas-propo' : ''), id: 'es-canevas' }),
      h('div', { cls: 'es-avert', id: 'es-avert' }));
    if (ED.mode === 'operateur') {
      const dn = ext('donnees');
      const gauche = h('div', { cls: 'es-ed-gauche' }, dn ? dn.panneauOperateur() : panneauVariables());
      return h('div', { cls: 'es-editeur es-editeur-operateur' }, barreHaut(), h('div', { cls: 'es-ed-corps es-ed-corps-op' }, gauche, centre));
    }
    const gs1 = ext('gs1');
    const gauche = h('div', { cls: 'es-ed-gauche' },
      h('div', { cls: 'es-panneau' },
        h('div', { cls: 'es-panneau-titre', text: 'Objets' }),
        h('div', { cls: 'es-ajouts' },
          bouton('Texte', () => ajouter('texte'), '', 'type'),
          bouton('Code-barres', () => ajouter('code_barre'), '', 'barcode'),
          bouton('Cadre', () => ajouter('cadre'), '', 'square'),
          bouton('Ellipse', () => ajouter('ellipse'), '', 'circle'),
          bouton('Ligne', () => ajouter('ligne'), '', 'minus'),
          bouton('Image', choisirImage, '', 'image'),
          bouton('Picto', () => (gs1 && gs1.modalePictos ? gs1.modalePictos() : ajouter('picto')), '', 'shield'),
          gs1 && gs1.modaleLogistique ? bouton('Palette GS1', () => gs1.modaleLogistique(ED.m), '', 'truck') : null),
        h('div', { cls: 'es-liste-el', id: 'es-liste-el' })),
      panneauCalques(),
      h('div', { cls: 'es-panneau', id: 'es-panneau-el' }));
    const droite = h('div', { cls: 'es-ed-droite' }, ...ongletsDroite());
    return h('div', { cls: 'es-editeur' }, barreHaut(), h('div', { cls: 'es-ed-corps' }, gauche, centre, droite));
  }
  function apres() {
    if (!ED.m) return;
    if (ED.mode === 'conception') { majListe(); majPanneauElement(); }
    dessiner();
  }

  async function ouvrir(m) {
    ED.m = cloner(m); completerLayout(ED.m.layout);
    ED.sel = null; ED.multi.clear(); ED.dirty = false; ED.pile = []; ED.propo = null; ED.saisies = {}; ED.source = null; ED.plan = null;
    ED.langue = ED.m.layout.langue_defaut || '';
    if (ext('controle') && ext('controle').reinitialiser) ext('controle').reinitialiser();
    chargerBwip();
    // Prochains numéros réels des compteurs, pour un aperçu fidèle.
    try { const r = await X().api('/modeles/' + m.id + '/compteurs'); ED.plan = Object.fromEntries(r.compteurs.map(c => [c.nom, { premier: c.prochain_numero, pas: (m.layout.variables.find(v => v.nom === c.nom) || {}).pas || 1 }])); dessiner(); }
    catch (e) { /* aperçu sur les valeurs de départ */ }
  }

  document.addEventListener('keydown', (ev) => {
    if (!ED.m || !document.querySelector('.es-editeur') || document.getElementById('es-modale')) return;
    if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 's') { ev.preventDefault(); if (ED.dirty) enregistrer(); }
    else if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 'z' && !/INPUT|TEXTAREA/.test(document.activeElement?.tagName || '')) { ev.preventDefault(); annuler(); }
  });
  window.addEventListener('beforeunload', (ev) => { if (ED.m && ED.dirty) { ev.preventDefault(); ev.returnValue = ''; } });

  window.EtiqSpec = Object.assign(window.EtiqSpec || {}, {
    editeur: {
      vue, apres, ouvrir, _ED: ED, PANNEAUX,
      api: { ED, layout, memoriser, salir, dessiner, construireSvg, valeursApercu, ajouter, nettoyer, completerLayout,
        bboxElement, elSel, fige, concepteur, majPanneauElement, majListe, cloner, mesurer, imprimer, enregistrer, chargerBwip },
    },
  });
})();

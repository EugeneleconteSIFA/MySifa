/* MyTools › Utilitaires › Codes — un texte → QR, Code 128, EAN-13 ou DataMatrix.
 *
 * Rendu par bwip-js (même version que l'éditeur d'étiquettes, déjà en cache
 * chez qui l'a ouvert). L'aperçu est une image SVG (data:), jamais du SVG
 * injecté dans la page. Copier = l'image PNG dans le presse-papiers (le SVG en
 * texte si le navigateur refuse les images). Rien n'est envoyé au serveur.
 *
 * Adresse : format (qr par défaut, code128, ean13, datamatrix). Le texte saisi
 * n'y va pas.
 */
(function () {
  'use strict';
  if (window.MyToolsUtil_qr) return;

  const URL_BWIP = 'https://cdn.jsdelivr.net/npm/bwip-js@4.5.1/dist/bwip-js-min.js';
  // [id, libellé, bulle, id bwip-js, linéaire]
  const FORMATS = [
    ['qr', 'QR code', 'QR', 'qrcode', false],
    ['code128', 'Code 128', 'Linéaire', 'code128', true],
    ['ean13', 'EAN-13', 'Produit', 'ean13', true],
    ['datamatrix', 'DataMatrix', 'Compact', 'datamatrix', false],
  ];
  const IDS = FORMATS.map(f => f[0]);

  // ── Logique pure (tests/test_tools_utilitaires.js) ────────────────
  // Clé de contrôle EAN-13 de 12 chiffres.
  function ean13Cle(douze) {
    const s = String(douze);
    if (!/^\d{12}$/.test(s)) return null;
    let t = 0;
    for (let i = 0; i < 12; i++) t += Number(s[i]) * (i % 2 ? 3 : 1);
    return (10 - (t % 10)) % 10;
  }
  // Contrôle de la saisie avant rendu : { ok, texte, info } ou { erreur }.
  function verifier(format, brut) {
    const t = String(brut == null ? '' : brut);
    if (!t.trim()) return { vide: true };
    if (format === 'ean13') {
      const d = t.replace(/[\s-]/g, '');
      if (!/^\d+$/.test(d)) return { erreur: 'EAN-13 : chiffres uniquement.' };
      if (d.length === 12) { const k = ean13Cle(d); return { ok: true, texte: d + k, info: 'Clé de contrôle calculée : ' + k }; }
      if (d.length === 13) {
        const k = ean13Cle(d.slice(0, 12));
        if (k !== Number(d[12])) return { erreur: 'Clé de contrôle fausse : le 13e chiffre devrait être ' + k + '.' };
        return { ok: true, texte: d, info: 'Clé de contrôle correcte.' };
      }
      return { erreur: 'EAN-13 : 12 chiffres (la clé est calculée) ou 13 chiffres — ' + d.length + ' saisis.' };
    }
    if (format === 'code128') {
      if (/[^\x20-\x7e]/.test(t)) return { erreur: 'Code 128 : caractères ASCII imprimables uniquement (pas d\'accents ni de retour à la ligne).' };
      if (t.length > 80) return { erreur: 'Code 128 : 80 caractères au plus — le code deviendrait illisible.' };
      return { ok: true, texte: t };
    }
    if (format === 'qr' && new TextEncoder().encode(t).length > 2900) return { erreur: 'QR : texte trop long (2 900 octets au plus).' };
    if (format === 'datamatrix' && new TextEncoder().encode(t).length > 1500) return { erreur: 'DataMatrix : texte trop long (1 500 octets au plus).' };
    return { ok: true, texte: t };
  }
  function optionsBwip(format, texte, echelle) {
    const f = FORMATS.find(x => x[0] === format) || FORMATS[0];
    const o = { bcid: f[3], text: texte, scale: echelle || 3, paddingwidth: 4, paddingheight: 4, backgroundcolor: 'FFFFFF' };
    if (f[4]) { o.height = 14; o.includetext = true; o.textxalign = 'center'; }
    if (format === 'qr') o.eclevel = 'M';
    // Les caractères hors ASCII d'un QR ou d'un DataMatrix passent en UTF-8.
    if ((format === 'qr' || format === 'datamatrix') && /[^\x00-\x7f]/.test(texte)) {
      o.text = Array.from(new TextEncoder().encode(texte)).map(b => String.fromCharCode(b)).join('');
      o.binarytext = true;
    }
    return o;
  }

  // ── Interface ──────────────────────────────────────────────────────
  let U = null;
  const Q = { host: null, format: 'qr', svg: '', texte: '' };
  const $ = s => Q.host.querySelector(s);

  function construire() {
    const h = Q.host;
    h.appendChild(U.tete('qr'));
    const carte = U.el('section', 'tut-carte');
    const l1 = U.el('div', 'tut-ligne');
    l1.appendChild(U.el('span', 'tut-lib', 'Format'));
    Q.choix = U.pastilles(FORMATS.map(f => [f[0], f[1], f[2]]), Q.format, v => { Q.format = v; maj(); U.signaler(); });
    l1.appendChild(Q.choix);
    carte.appendChild(l1);
    const lab = U.el('label', 'tut-champ');
    lab.appendChild(U.el('span', null, 'Contenu'));
    const ta = U.el('textarea', 'tut-in tut-in--texte');
    ta.id = 'tut-qr-texte'; ta.rows = 3; ta.spellcheck = false;
    ta.placeholder = 'Texte, adresse web, référence, numéro de lot…';
    lab.appendChild(ta);
    carte.appendChild(lab);
    carte.appendChild(U.el('div', 'tut-info', ''));
    carte.appendChild(U.el('div', 'tut-err', ''));
    const res = U.el('div', 'tut-qr-res');
    res.innerHTML = '<div class="tut-qr-apercu"><img alt="Code généré"></div><div class="tut-actions"></div>';
    const act = res.querySelector('.tut-actions');
    const bC = U.bouton('tut-btn tut-btn--plein', 'copier', 'Copier', 'Copier');
    const bS = U.bouton('tut-btn', 'telecharger', 'SVG', 'Vectoriel');
    const bP = U.bouton('tut-btn', 'telecharger', 'PNG', 'Image');
    bC.addEventListener('click', copier);
    bS.addEventListener('click', () => { if (Q.svg) U.telecharger(new Blob([Q.svg], { type: 'image/svg+xml' }), nomFichier('svg')); });
    bP.addEventListener('click', async () => { const b = await png(); if (b) U.telecharger(b, nomFichier('png')); });
    act.append(bC, bS, bP);
    carte.appendChild(res);
    h.appendChild(carte);
    let t = 0;
    ta.addEventListener('input', () => { clearTimeout(t); t = setTimeout(maj, 120); });
    maj();
  }
  const nomFichier = ext => Q.format + '-' + (Q.texte.replace(/[^A-Za-z0-9_-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 30) || 'code') + '.' + ext;

  async function maj() {
    if (!Q.host) return;
    if (Q.choix) Q.choix.choisir(Q.format);
    const r = verifier(Q.format, $('#tut-qr-texte').value);
    const info = $('.tut-info'), err = $('.tut-err'), res = $('.tut-qr-res');
    info.textContent = r.info || ''; err.textContent = r.erreur || '';
    Q.svg = ''; Q.texte = '';
    if (!r.ok) { res.hidden = true; return; }
    try { await U.chargerScript(URL_BWIP); }
    catch (e) { err.textContent = e.message; res.hidden = true; return; }
    try {
      Q.svg = window.bwipjs.toSVG(optionsBwip(Q.format, r.texte, 3));
      Q.texte = r.texte;
      res.querySelector('img').src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(Q.svg);
      res.classList.toggle('tut-qr-res--lineaire', !!(FORMATS.find(f => f[0] === Q.format) || [])[4]);
      res.hidden = false;
    } catch (e) {
      res.hidden = true;
      err.textContent = 'Code impossible à générer : ' + String(e && e.message || e).replace(/^bwipp?\.\w+#?\d*:?\s*/i, '');
    }
  }
  function png() {
    if (!Q.texte) return Promise.resolve(null);
    const c = document.createElement('canvas');
    try { window.bwipjs.toCanvas(c, optionsBwip(Q.format, Q.texte, 8)); }
    catch (e) { U.toast('Image impossible à produire.', 'danger'); return Promise.resolve(null); }
    return new Promise(ok => c.toBlob(b => ok(b), 'image/png'));
  }
  async function copier() {
    if (!Q.texte) return;
    try {
      if (!window.ClipboardItem || !navigator.clipboard || !navigator.clipboard.write) throw new Error('img');
      await navigator.clipboard.write([new ClipboardItem({ 'image/png': png() })]);
      U.toast('Image copiée.', 'success');
    } catch (e) {
      const ok = await U.copierTexte(Q.svg);
      U.toast(ok ? 'SVG copié (texte).' : 'Copie refusée par le navigateur.', ok ? 'success' : 'danger');
    }
  }

  window.MyToolsUtil_qr = {
    cles: ['format'],
    mount(host, outils) { U = outils; Q.host = host; construire(); },
    etat: () => (Q.format !== 'qr' ? { format: Q.format } : {}),
    aller(p) { Q.format = p && IDS.indexOf(p.format) !== -1 ? p.format : 'qr'; if (Q.host) maj(); },
    _interne: { ean13Cle, verifier, optionsBwip },
  };
})();

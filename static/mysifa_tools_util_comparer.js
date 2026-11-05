/* MyTools › Utilitaires › Comparer — deux textes, deux listes, deux tableaux CSV.
 *
 *   texte   différences ligne à ligne (Myers), et mot à mot dans les lignes modifiées
 *   listes  une valeur par ligne : présentes d'un seul côté, ou des deux
 *   csv     deux tableaux rapprochés par une colonne clé : lignes ajoutées,
 *           retirées, cellules modifiées, colonnes propres à un seul fichier
 *
 * Tout reste dans le navigateur. Export : texte annoté (.txt) ou CSV au point-virgule
 * (lisible par Excel). Adresse : comparaison (texte par défaut, listes, csv), niveau
 * (ligne par défaut, mot), casse=ignorer, espaces=ignorer. Les textes collés
 * et la colonne clé n'y vont pas.
 */
(function () {
  'use strict';
  if (window.MyToolsUtil_comparer) return;

  const MODES = [['texte', 'Texte', 'Ligne à ligne'], ['listes', 'Listes', 'Présents ou absents'], ['csv', 'Tableaux CSV', 'Par colonne clé']];
  const MAX_D = 2500;

  // ── Logique pure (tests/test_tools_utilitaires.js) ────────────────
  // Myers O((N+M)·D). Rend [{t:'=',i,j} | {t:'-',i} | {t:'+',j}] ; au-delà de
  // MAX_D différences, le cœur est rendu en bloc retiré puis ajouté.
  function diffSeq(a, b, eq) {
    eq = eq || ((x, y) => x === y);
    let s = 0;
    while (s < a.length && s < b.length && eq(a[s], b[s])) s++;
    let e = 0;
    while (e < a.length - s && e < b.length - s && eq(a[a.length - 1 - e], b[b.length - 1 - e])) e++;
    const A = a.slice(s, a.length - e), B = b.slice(s, b.length - e);
    const ops = [];
    for (let i = 0; i < s; i++) ops.push({ t: '=', i, j: i });
    let mid = myers(A, B, eq);
    if (!mid) { mid = []; A.forEach((x, i) => mid.push({ t: '-', i })); B.forEach((x, j) => mid.push({ t: '+', j })); }
    mid.forEach(o => ops.push(o.t === '=' ? { t: '=', i: o.i + s, j: o.j + s } : o.t === '-' ? { t: '-', i: o.i + s } : { t: '+', j: o.j + s }));
    for (let k = 0; k < e; k++) ops.push({ t: '=', i: a.length - e + k, j: b.length - e + k });
    return ops;
  }
  function myers(A, B, eq) {
    const N = A.length, M = B.length, max = N + M;
    if (!max) return [];
    const off = max + 1, V = new Int32Array(2 * max + 3), trace = [];
    for (let d = 0; d <= max; d++) {
      if (d > MAX_D) return null;
      const snap = new Int32Array(2 * d + 3);
      for (let k = -d - 1; k <= d + 1; k++) snap[k + d + 1] = V[k + off];
      trace.push(snap);
      for (let k = -d; k <= d; k += 2) {
        let x = (k === -d || (k !== d && V[k - 1 + off] < V[k + 1 + off])) ? V[k + 1 + off] : V[k - 1 + off] + 1;
        let y = x - k;
        while (x < N && y < M && eq(A[x], B[y])) { x++; y++; }
        V[k + off] = x;
        if (x >= N && y >= M) return remonter(trace, N, M);
      }
    }
    return null;
  }
  function remonter(trace, N, M) {
    const ops = [];
    let x = N, y = M;
    for (let d = trace.length - 1; d >= 0; d--) {
      const T = trace[d], get = k => T[k + d + 1], k = x - y;
      const pk = (k === -d || (k !== d && get(k - 1) < get(k + 1))) ? k + 1 : k - 1;
      const px = get(pk), py = px - pk;
      while (x > px && y > py) { ops.push({ t: '=', i: x - 1, j: y - 1 }); x--; y--; }
      if (d > 0) { if (x === px) ops.push({ t: '+', j: y - 1 }); else ops.push({ t: '-', i: x - 1 }); }
      x = px; y = py;
    }
    return ops.reverse();
  }
  const lignes = t => { const l = String(t == null ? '' : t).replace(/\r\n?/g, '\n').split('\n'); if (l.length && l[l.length - 1] === '') l.pop(); return l; };
  function normaliseur(o) {
    o = o || {};
    return s => { let v = String(s); if (o.espaces) v = v.replace(/\s+/g, ' ').trim(); if (o.casse) v = v.toLocaleLowerCase('fr'); return v; };
  }
  // Différences de deux textes : ops ligne + appariement des blocs retirés/ajoutés.
  function diffTextes(ta, tb, o) {
    const A = lignes(ta), B = lignes(tb), nz = normaliseur(o);
    const nA = A.map(nz), nB = B.map(nz);
    const ops = diffSeq(nA, nB);
    const st = { egales: 0, retirees: 0, ajoutees: 0 };
    ops.forEach(x => { if (x.t === '=') st.egales++; else if (x.t === '-') st.retirees++; else st.ajoutees++; });
    return { A, B, ops, stats: st };
  }
  const mots = s => String(s).match(/\s+|[\p{L}\p{N}_]+|[^\s\p{L}\p{N}_]/gu) || [];
  // Mot à mot : [{t:'='|'-'|'+', v}] pour chaque côté.
  function diffMots(a, b, o) {
    const ta = mots(a), tb = mots(b), nz = normaliseur(o);
    const ops = diffSeq(ta.map(nz), tb.map(nz));
    const ga = [], gb = [];
    ops.forEach(x => {
      if (x.t === '=') { ga.push({ t: '=', v: ta[x.i] }); gb.push({ t: '=', v: tb[x.j] }); }
      else if (x.t === '-') ga.push({ t: '-', v: ta[x.i] });
      else gb.push({ t: '+', v: tb[x.j] });
    });
    const fusion = l => l.reduce((r, x) => { const d = r[r.length - 1]; if (d && d.t === x.t) d.v += x.v; else r.push({ t: x.t, v: x.v }); return r; }, []);
    return { a: fusion(ga), b: fusion(gb) };
  }
  // Blocs : suites de « - » suivies de « + » appariées ligne à ligne.
  function blocs(ops) {
    const r = [];
    let i = 0;
    while (i < ops.length) {
      if (ops[i].t === '=') { r.push({ t: '=', ops: [ops[i]] }); i++; continue; }
      const moins = [], plus = [];
      while (i < ops.length && ops[i].t === '-') moins.push(ops[i++]);
      while (i < ops.length && ops[i].t === '+') plus.push(ops[i++]);
      r.push({ t: 'x', moins, plus });
    }
    return r;
  }
  function texteAnnote(d) {
    return d.ops.map(x => (x.t === '=' ? '  ' + d.A[x.i] : x.t === '-' ? '- ' + d.A[x.i] : '+ ' + d.B[x.j])).join('\n') + '\n';
  }

  // Listes : une valeur par ligne, lignes vides ignorées.
  function diffListes(ta, tb, o) {
    const nz = normaliseur(Object.assign({}, o, { espaces: true }));
    const lire = t => {
      const m = new Map(); let doublons = 0;
      lignes(t).forEach(l => { const v = l.trim(); if (!v) return; const k = nz(v); if (m.has(k)) doublons++; else m.set(k, v); });
      return { m, doublons };
    };
    const a = lire(ta), b = lire(tb);
    const seulA = [], seulB = [], communs = [];
    a.m.forEach((v, k) => { (b.m.has(k) ? communs : seulA).push(v); });
    b.m.forEach((v, k) => { if (!a.m.has(k)) seulB.push(v); });
    return { seulA, seulB, communs, doublonsA: a.doublons, doublonsB: b.doublons };
  }

  // CSV : séparateur deviné sur la première ligne (; , tabulation |), guillemets RFC 4180.
  function separateur(t) {
    const l = String(t).split(/\r?\n/)[0] || '';
    let mieux = ',', n = -1;
    [';', ',', '\t', '|'].forEach(s => {
      let c = 0, q = false;
      for (const ch of l) { if (ch === '"') q = !q; else if (ch === s && !q) c++; }
      if (c > n) { n = c; mieux = s; }
    });
    return mieux;
  }
  function lireCsv(t, sep) {
    const s = String(t == null ? '' : t).replace(/^﻿/, '');
    sep = sep || separateur(s);
    const rows = []; let row = [], cell = '', q = false;
    for (let i = 0; i < s.length; i++) {
      const c = s[i];
      if (q) {
        if (c === '"') { if (s[i + 1] === '"') { cell += '"'; i++; } else q = false; }
        else cell += c;
      } else if (c === '"' && cell === '') q = true;
      else if (c === sep) { row.push(cell); cell = ''; }
      else if (c === '\n' || c === '\r') {
        if (c === '\r' && s[i + 1] === '\n') i++;
        row.push(cell); cell = '';
        if (row.length > 1 || row[0] !== '') rows.push(row);
        row = [];
      } else cell += c;
    }
    row.push(cell);
    if (row.length > 1 || row[0] !== '') rows.push(row);
    return rows;
  }
  function diffCsv(ta, tb, cle, o) {
    const A = lireCsv(ta), B = lireCsv(tb);
    if (!A.length || !B.length) return { vide: true };
    const hA = A[0].map(x => x.trim()), hB = B[0].map(x => x.trim());
    const communes = hA.filter(h => hB.indexOf(h) !== -1);
    if (!communes.length) return { erreur: 'Aucune colonne commune : les en-têtes (première ligne) doivent porter les mêmes noms.' };
    const c = communes.indexOf(cle) !== -1 ? cle : communes[0];
    const nz = normaliseur(o);
    const ia = hA.indexOf(c), ib = hB.indexOf(c);
    const index = (rows, k) => {
      const m = new Map(); let doublons = 0;
      rows.slice(1).forEach(r => { const v = nz(r[k] == null ? '' : r[k]); if (m.has(v)) doublons++; else m.set(v, r); });
      return { m, doublons };
    };
    const xa = index(A, ia), xb = index(B, ib);
    const ajoutees = [], retirees = [], modifiees = [];
    let identiques = 0;
    xa.m.forEach((ra, k) => {
      const rb = xb.m.get(k);
      if (!rb) { retirees.push(ra); return; }
      const diffs = [];
      communes.forEach(h => {
        const va = ra[hA.indexOf(h)] == null ? '' : ra[hA.indexOf(h)], vb = rb[hB.indexOf(h)] == null ? '' : rb[hB.indexOf(h)];
        if (nz(va) !== nz(vb)) diffs.push({ col: h, a: va, b: vb });
      });
      if (diffs.length) modifiees.push({ cle: ra[ia], diffs }); else identiques++;
    });
    xb.m.forEach((rb, k) => { if (!xa.m.has(k)) ajoutees.push(rb); });
    return {
      cle: c, communes, hA, hB, ajoutees, retirees, modifiees, identiques,
      seulColA: hA.filter(h => hB.indexOf(h) === -1), seulColB: hB.filter(h => hA.indexOf(h) === -1),
      doublonsA: xa.doublons, doublonsB: xb.doublons, ia, ib,
    };
  }
  const celluleCsv = v => { const s = String(v == null ? '' : v); return /[";\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
  const ecrireCsv = rows => '﻿' + rows.map(r => r.map(celluleCsv).join(';')).join('\r\n') + '\r\n';
  function exportCsvDiff(r) {
    const rows = [['Clé (' + r.cle + ')', 'Écart', 'Colonne', 'Fichier A', 'Fichier B']];
    r.retirees.forEach(x => rows.push([x[r.ia], 'Seulement dans A', '', '', '']));
    r.ajoutees.forEach(x => rows.push([x[r.ib], 'Seulement dans B', '', '', '']));
    r.modifiees.forEach(m => m.diffs.forEach(d => rows.push([m.cle, 'Modifiée', d.col, d.a, d.b])));
    return ecrireCsv(rows);
  }
  function exportListes(r) {
    const rows = [['Valeur', 'Présence']];
    r.seulA.forEach(v => rows.push([v, 'Seulement dans A']));
    r.seulB.forEach(v => rows.push([v, 'Seulement dans B']));
    r.communs.forEach(v => rows.push([v, 'Les deux']));
    return ecrireCsv(rows);
  }

  // ── Interface ──────────────────────────────────────────────────────
  let U = null;
  const D = { host: null, mode: 'texte', niveau: 'ligne', casse: false, espaces: false, cle: '', ouverts: {} };
  const $ = s => D.host.querySelector(s);
  const fmt = n => Number(n).toLocaleString('fr-FR');

  function cote(id, titre) {
    const z = U.el('div', 'tut-cote');
    const t = U.el('div', 'tut-cote-t');
    t.appendChild(U.el('span', 'tut-cote-l', titre));
    const inp = U.el('input'); inp.type = 'file'; inp.hidden = true; inp.accept = '.txt,.csv,.tsv,.md,.json,.xml,.log,text/*';
    const b = U.bouton('tut-btn tut-btn--petit', 'fichier', 'Ouvrir', 'Fichier');
    b.addEventListener('click', () => inp.click());
    inp.addEventListener('change', () => { if (inp.files[0]) lireFichier(inp.files[0], id); inp.value = ''; });
    t.append(b, inp);
    z.appendChild(t);
    const ta = U.el('textarea', 'tut-in tut-in--code');
    ta.id = 'tut-c-' + id; ta.rows = 12; ta.spellcheck = false; ta.wrap = 'off';
    ta.placeholder = 'Coller le texte, ou déposer un fichier ici';
    ta.addEventListener('dragover', e => { e.preventDefault(); ta.classList.add('tut-survol'); });
    ta.addEventListener('dragleave', () => ta.classList.remove('tut-survol'));
    ta.addEventListener('drop', e => { e.preventDefault(); ta.classList.remove('tut-survol'); const f = e.dataTransfer && e.dataTransfer.files[0]; if (f) lireFichier(f, id); });
    z.appendChild(ta);
    return z;
  }
  function lireFichier(f, id) {
    if (f.size > 20e6) { U.toast('Fichier trop lourd pour une comparaison (20 Mo au plus).', 'danger'); return; }
    const r = new FileReader();
    r.onload = () => { $('#tut-c-' + id).value = String(r.result || ''); maj(); };
    r.onerror = () => U.toast('Lecture du fichier impossible.', 'danger');
    r.readAsText(f);
  }

  function construire() {
    const h = D.host;
    h.appendChild(U.tete('comparer'));
    const carte = U.el('section', 'tut-carte');
    const l1 = U.el('div', 'tut-ligne');
    D.choixMode = U.pastilles(MODES, D.mode, v => { D.mode = v; maj(); U.signaler(); });
    l1.appendChild(D.choixMode);
    D.choixNiveau = U.pastilles([['ligne', 'Lignes', 'Par ligne'], ['mot', 'Mots', 'Par mot']], D.niveau, v => { D.niveau = v; maj(); U.signaler(); });
    D.choixNiveau.classList.add('tut-si-texte');
    l1.appendChild(D.choixNiveau);
    const cases = U.el('div', 'tut-cases');
    [['casse', 'Ignorer la casse', 'Majuscules'], ['espaces', 'Ignorer les espaces', 'Espaces']].forEach(c => {
      const l = U.el('label', 'tut-case'); l.setAttribute('data-bulle', c[2]);
      const i = U.el('input'); i.type = 'checkbox'; i.id = 'tut-c-' + c[0];
      i.addEventListener('change', () => { D[c[0]] = i.checked; maj(); U.signaler(); });
      l.append(i, document.createTextNode(' ' + c[1]));
      cases.appendChild(l);
    });
    l1.appendChild(cases);
    carte.appendChild(l1);
    const deux = U.el('div', 'tut-deux');
    deux.append(cote('a', 'A — référence'), cote('b', 'B — à comparer'));
    carte.appendChild(deux);
    const l2 = U.el('div', 'tut-ligne tut-si-csv');
    const lc = U.el('label', 'tut-champ tut-champ--ligne');
    lc.appendChild(U.el('span', null, 'Colonne clé'));
    const sel = U.el('select', 'tut-in'); sel.id = 'tut-c-cle';
    sel.addEventListener('change', () => { D.cle = sel.value; maj(); });
    lc.appendChild(sel); l2.appendChild(lc);
    l2.appendChild(U.el('span', 'tut-aide', 'Les lignes des deux fichiers sont rapprochées par cette colonne (référence, numéro…).'));
    carte.appendChild(l2);
    const actions = U.el('div', 'tut-actions');
    const inv = U.bouton('tut-btn', 'inverser', 'Inverser', 'A ↔ B');
    inv.addEventListener('click', () => { const a = $('#tut-c-a').value; $('#tut-c-a').value = $('#tut-c-b').value; $('#tut-c-b').value = a; maj(); });
    const vid = U.bouton('tut-btn', 'vider', 'Vider', 'Effacer');
    vid.addEventListener('click', () => { $('#tut-c-a').value = ''; $('#tut-c-b').value = ''; maj(); });
    const exp = U.bouton('tut-btn tut-btn--plein', 'telecharger', 'Exporter', 'Exporter');
    exp.id = 'tut-c-exp';
    exp.addEventListener('click', exporter);
    actions.append(inv, vid, exp);
    carte.appendChild(actions);
    h.appendChild(carte);
    const res = U.el('section', 'tut-carte tut-c-res'); res.id = 'tut-c-res';
    h.appendChild(res);
    let t = 0;
    carte.addEventListener('input', e => { if (e.target.tagName === 'TEXTAREA') { clearTimeout(t); t = setTimeout(maj, 250); } });
    maj();
  }

  function stat(cls, n, lib) { const s = U.el('span', 'tut-stat ' + cls); s.appendChild(U.el('b', null, fmt(n))); s.appendChild(document.createTextNode(' ' + lib)); return s; }
  function majOptions() {
    D.choixMode.choisir(D.mode); D.choixNiveau.choisir(D.niveau);
    $('#tut-c-casse').checked = D.casse; $('#tut-c-espaces').checked = D.espaces;
    D.host.querySelectorAll('.tut-si-texte').forEach(e => { e.hidden = D.mode !== 'texte'; });
    D.host.querySelectorAll('.tut-si-csv').forEach(e => { e.hidden = D.mode !== 'csv'; });
    $('#tut-c-a').wrap = D.mode === 'texte' ? 'soft' : 'off';
    $('#tut-c-b').wrap = $('#tut-c-a').wrap;
  }

  function maj() {
    if (!D.host) return;
    majOptions();
    const res = $('#tut-c-res'), ta = $('#tut-c-a').value, tb = $('#tut-c-b').value, o = { casse: D.casse, espaces: D.espaces };
    res.textContent = '';
    D.resultat = null;
    $('#tut-c-exp').disabled = true;
    if (!ta.trim() && !tb.trim()) { res.appendChild(U.el('div', 'tut-vide-l', 'Coller ou ouvrir les deux versions à comparer.')); return; }
    if (D.mode === 'texte') rendreTexte(res, diffTextes(ta, tb, o), o);
    else if (D.mode === 'listes') rendreListes(res, diffListes(ta, tb, o));
    else rendreCsv(res, ta, tb, o);
  }

  function rendreTexte(res, d, o) {
    D.resultat = { type: 'texte', d };
    $('#tut-c-exp').disabled = false;
    const s = U.el('div', 'tut-stats');
    s.append(stat('tut-stat--moins', d.stats.retirees, 'retirée' + (d.stats.retirees > 1 ? 's' : '')), stat('tut-stat--plus', d.stats.ajoutees, 'ajoutée' + (d.stats.ajoutees > 1 ? 's' : '')), stat('', d.stats.egales, 'identique' + (d.stats.egales > 1 ? 's' : '')));
    res.appendChild(s);
    if (!d.stats.retirees && !d.stats.ajoutees) { res.appendChild(U.el('div', 'tut-res', 'Les deux textes sont identiques' + (o.casse || o.espaces ? ' (aux options près).' : '.'))); return; }
    const tab = U.el('div', 'tut-diff');
    const ligne = (t, na, nb, contenu) => {
      const l = U.el('div', 'tut-diff-l tut-diff-l--' + (t === '=' ? 'eg' : t === '-' ? 'moins' : 'plus'));
      l.appendChild(U.el('span', 'tut-diff-n', na == null ? '' : String(na + 1)));
      l.appendChild(U.el('span', 'tut-diff-n', nb == null ? '' : String(nb + 1)));
      l.appendChild(U.el('span', 'tut-diff-s', t === '=' ? '' : t));
      const c = U.el('span', 'tut-diff-c');
      if (typeof contenu === 'string') c.textContent = contenu || ' ';
      else contenu.forEach(x => { const sp = U.el('span', x.t === '=' ? null : 'tut-diff-m', x.v); c.appendChild(sp); });
      l.appendChild(c);
      tab.appendChild(l);
    };
    const B = blocs(d.ops);
    // Contexte : trois lignes autour de chaque écart, le reste replié.
    const garder = new Set();
    B.forEach((b, bi) => { if (b.t !== '=') for (let k = bi - 3; k <= bi + 3; k++) garder.add(k); });
    let replie = [];
    const vider = () => {
      if (!replie.length) return;
      const lot = replie; replie = [];
      const cleR = lot[0].ops[0].i;
      if (D.ouverts[cleR]) { lot.forEach(b => ligne('=', b.ops[0].i, b.ops[0].j, d.A[b.ops[0].i])); return; }
      const btn = U.el('button', 'tut-diff-replie', fmt(lot.length) + ' ligne' + (lot.length > 1 ? 's identiques' : ' identique'));
      btn.type = 'button'; btn.setAttribute('data-bulle', 'Déplier');
      btn.addEventListener('click', () => { D.ouverts[cleR] = true; maj(); });
      tab.appendChild(btn);
    };
    B.forEach((b, bi) => {
      if (b.t === '=') { if (garder.has(bi)) { vider(); ligne('=', b.ops[0].i, b.ops[0].j, d.A[b.ops[0].i]); } else replie.push(b); return; }
      vider();
      const paires = D.niveau === 'mot' ? Math.min(b.moins.length, b.plus.length) : 0;
      const mm = [];
      for (let k = 0; k < paires; k++) mm.push(diffMots(d.A[b.moins[k].i], d.B[b.plus[k].j], o));
      b.moins.forEach((x, k) => ligne('-', x.i, null, k < paires ? mm[k].a : d.A[x.i]));
      b.plus.forEach((x, k) => ligne('+', null, x.j, k < paires ? mm[k].b : d.B[x.j]));
    });
    vider();
    res.appendChild(tab);
  }

  function colonne(titre, cls, liste) {
    const c = U.el('div', 'tut-liste ' + cls);
    const t = U.el('div', 'tut-liste-t');
    t.appendChild(U.el('b', null, fmt(liste.length)));
    t.appendChild(U.el('span', null, titre));
    const cp = U.bouton('tut-btn tut-btn--icone', 'copier', '', 'Copier');
    cp.disabled = !liste.length;
    cp.addEventListener('click', async () => { const ok = await U.copierTexte(liste.join('\n')); U.toast(ok ? fmt(liste.length) + ' valeurs copiées.' : 'Copie refusée.', ok ? 'success' : 'danger'); });
    t.appendChild(cp);
    c.appendChild(t);
    const ul = U.el('ul');
    liste.slice(0, 2000).forEach(v => ul.appendChild(U.el('li', null, v)));
    if (liste.length > 2000) ul.appendChild(U.el('li', 'tut-plus', '… ' + fmt(liste.length - 2000) + ' de plus (export complet)'));
    c.appendChild(ul);
    return c;
  }
  function rendreListes(res, r) {
    D.resultat = { type: 'listes', r };
    $('#tut-c-exp').disabled = false;
    const g = U.el('div', 'tut-listes');
    g.append(colonne('seulement dans A', 'tut-liste--moins', r.seulA), colonne('seulement dans B', 'tut-liste--plus', r.seulB), colonne('dans les deux', '', r.communs));
    res.appendChild(g);
    if (r.doublonsA || r.doublonsB) res.appendChild(U.el('p', 'tut-aide', 'Doublons ignorés : ' + fmt(r.doublonsA) + ' dans A, ' + fmt(r.doublonsB) + ' dans B.'));
  }
  function rendreCsv(res, ta, tb, o) {
    const r = diffCsv(ta, tb, D.cle, o);
    const sel = $('#tut-c-cle');
    if (r.communes) {
      const actuel = Array.from(sel.options).map(x => x.value).join('\u0001');
      if (actuel !== r.communes.join('\u0001')) { sel.textContent = ''; r.communes.forEach(c => { const op = U.el('option', null, c); op.value = c; sel.appendChild(op); }); }
      sel.value = r.cle; D.cle = r.cle;
    }
    if (r.vide) { res.appendChild(U.el('div', 'tut-vide-l', 'Deux tableaux à renseigner, avec une ligne d\'en-têtes.')); return; }
    if (r.erreur) { res.appendChild(U.el('div', 'tut-err', r.erreur)); return; }
    D.resultat = { type: 'csv', r };
    $('#tut-c-exp').disabled = false;
    const s = U.el('div', 'tut-stats');
    s.append(stat('tut-stat--moins', r.retirees.length, 'seulement dans A'), stat('tut-stat--plus', r.ajoutees.length, 'seulement dans B'),
      stat('tut-stat--modif', r.modifiees.length, 'modifiée' + (r.modifiees.length > 1 ? 's' : '')), stat('', r.identiques, 'identique' + (r.identiques > 1 ? 's' : '')));
    res.appendChild(s);
    const notes = [];
    if (r.seulColA.length) notes.push('Colonnes seulement dans A : ' + r.seulColA.join(', ') + '.');
    if (r.seulColB.length) notes.push('Colonnes seulement dans B : ' + r.seulColB.join(', ') + '.');
    if (r.doublonsA || r.doublonsB) notes.push('Clés en double ignorées : ' + fmt(r.doublonsA) + ' dans A, ' + fmt(r.doublonsB) + ' dans B.');
    notes.forEach(n => res.appendChild(U.el('p', 'tut-aide', n)));
    const t = U.el('table', 'tut-table');
    const th = U.el('tr');
    [r.cle, 'Écart', 'Colonne', 'A', 'B'].forEach(x => th.appendChild(U.el('th', null, x)));
    t.appendChild(th);
    let n = 0;
    const ajout = (cells, cls) => { if (n++ > 3000) return; const tr = U.el('tr', cls); cells.forEach(x => tr.appendChild(U.el('td', null, x))); t.appendChild(tr); };
    r.retirees.forEach(x => ajout([x[r.ia], 'Seulement dans A', '', '', ''], 'tut-tr--moins'));
    r.ajoutees.forEach(x => ajout([x[r.ib], 'Seulement dans B', '', '', ''], 'tut-tr--plus'));
    r.modifiees.forEach(m => m.diffs.forEach((dd, k) => ajout([k ? '' : m.cle, k ? '' : 'Modifiée', dd.col, dd.a, dd.b], 'tut-tr--modif')));
    if (n) { const w = U.el('div', 'tut-table-w'); w.appendChild(t); res.appendChild(w); }
    else res.appendChild(U.el('div', 'tut-res', 'Aucun écart sur les colonnes communes.'));
    if (n > 3000) res.appendChild(U.el('p', 'tut-aide', 'Affichage limité à 3 000 lignes : l\'export contient tout.'));
  }

  function exporter() {
    const x = D.resultat;
    if (!x) return;
    const date = new Date().toISOString().slice(0, 10);
    if (x.type === 'texte') U.telecharger(new Blob([texteAnnote(x.d)], { type: 'text/plain;charset=utf-8' }), 'comparaison-' + date + '.txt');
    else if (x.type === 'listes') U.telecharger(new Blob([exportListes(x.r)], { type: 'text/csv;charset=utf-8' }), 'comparaison-listes-' + date + '.csv');
    else U.telecharger(new Blob([exportCsvDiff(x.r)], { type: 'text/csv;charset=utf-8' }), 'comparaison-tableaux-' + date + '.csv');
  }

  window.MyToolsUtil_comparer = {
    cles: ['comparaison', 'niveau', 'casse', 'espaces'],
    mount(host, outils) { U = outils; D.host = host; construire(); },
    etat: () => {
      const e = {};
      if (D.mode !== 'texte') e.comparaison = D.mode;
      if (D.mode === 'texte' && D.niveau !== 'ligne') e.niveau = D.niveau;
      if (D.casse) e.casse = 'ignorer';
      if (D.espaces) e.espaces = 'ignorer';
      return e;
    },
    aller(p) {
      p = p || {};
      D.mode = MODES.some(m => m[0] === p.comparaison) ? p.comparaison : 'texte';
      D.niveau = p.niveau === 'mot' ? 'mot' : 'ligne';
      D.casse = p.casse === 'ignorer';
      D.espaces = p.espaces === 'ignorer';
      if (D.host) maj();
    },
    _interne: { diffSeq, diffTextes, diffMots, blocs, texteAnnote, diffListes, separateur, lireCsv, diffCsv, exportCsvDiff, exportListes, ecrireCsv },
  };
})();

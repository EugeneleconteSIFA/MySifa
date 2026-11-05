/*
 * MyTools — éditeur PDF : fonctions IA (menu « IA », camaïeu violet).
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 * Seules ces fonctions font sortir le document du poste :
 *   résumer, poser une question, extraire des données en tableau (CSV),
 *   détecter les champs d'un PDF à plat → envoi du PDF produit à
 *     /api/tools/pdf/ia/* (Claude, suivi dans ia_usage) ;
 *   traduire en gardant la mise en page → chaque bloc de texte est envoyé à
 *     /api/translate (DeepL), puis posé à la place du texte d'origine avec le
 *     moteur de « Modifier le texte ».
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  /* ── Fonctions pures (tests/test_tools_pdf.js) ────────────────────── */
  // Champ détecté (coordonnées 0–1000, origine haut-gauche) -> boîte en points.
  function boiteDetectee(c, W, H) {
    return { x: c.x / 1000 * W, y: c.y / 1000 * H, w: Math.max(8, c.l / 1000 * W), h: Math.max(8, c.h / 1000 * H) };
  }
  // Un bloc qui mérite traduction : au moins deux lettres, pas qu'un code ou un nombre.
  function aTraduire(t) { return /\p{L}{2,}/u.test(String(t || '')) && !/^[\p{Lu}\d\s._\/-]{1,6}$/u.test(String(t).trim()); }
  // Taille réduite pour qu'un texte traduit tienne dans la largeur d'origine (60 % au plus bas).
  function tailleAjustee(taille, largeurCible, largeurTexte) {
    if (!(largeurTexte > largeurCible * 1.02) || !(largeurCible > 0)) return taille;
    return Math.max(taille * 0.6, taille * largeurCible / largeurTexte);
  }

  /* ── Modification assistée : fonctions pures ─────────────────────── */
  var MODIF_MAX_BLOCS = 1500, MODIF_MAX_CARACTERES = 60000;
  var MODIF_TYPES = { remplacer: 1, masquer: 1, inserer: 1 };
  // Identifiant d'un bloc envoyé à l'IA : « page.élément », page à partir de 1.
  function idBloc(page, premier) { return (page + 1) + '.' + premier; }
  // Bloc (ligne de base x, y en points depuis le haut) à l'intérieur d'un cadre.
  function dansZone(b, z) { return b.x >= z.x - 2 && b.x <= z.x + z.w && b.y >= z.y && b.y <= z.y + z.h + 4; }
  // Ce qui part au serveur : texte et position arrondie, rien d'autre.
  function blocsPourIa(entrees) {
    var blocs = [], car = 0;
    (entrees || []).forEach(function (e) {
      if (!e || !String(e.texte || '').trim()) return;
      var t = String(e.texte).slice(0, 2000); car += t.length;
      blocs.push({ id: e.id, page: e.page + 1, texte: t, x: Math.round(e.x), y: Math.round(e.y) });
    });
    return { blocs: blocs, caracteres: car, trop: blocs.length > MODIF_MAX_BLOCS || car > MODIF_MAX_CARACTERES };
  }
  function remplacerTout(texte, ancien, nouveau) { return ancien ? String(texte).split(ancien).join(nouveau) : String(texte); }
  // Mêmes règles que le serveur (pdf_ia.valider_operations) : id connu,
  // « ancien » présent dans le bloc, insertion non vide ; doublons retirés.
  function validerOps(ops, textes) {
    var valides = [], ecartees = 0, vus = {};
    (Array.isArray(ops) ? ops : []).forEach(function (o) {
      if (!o || !MODIF_TYPES[o.type] || !Object.prototype.hasOwnProperty.call(textes, o.id)) { ecartees++; return; }
      var t = textes[o.id], ancien = String(o.ancien || ''), nouveau = String(o.nouveau || '');
      if (o.type === 'remplacer' && (!ancien || t.indexOf(ancien) < 0 || ancien === nouveau)) { ecartees++; return; }
      if (o.type === 'masquer') { ancien = t; nouveau = ''; }
      if (o.type === 'inserer') { nouveau = nouveau.trim(); ancien = ''; if (!nouveau) { ecartees++; return; } }
      var cle = [o.type, o.id, ancien, nouveau].join('\u0001');
      if (vus[cle]) return; vus[cle] = 1;
      valides.push({ type: o.type, id: o.id, ancien: ancien, nouveau: nouveau,
        position: o.position === 'droite' ? 'droite' : 'dessous', motif: String(o.motif || '') });
    });
    return { valides: valides, ecartees: ecartees };
  }
  // Texte d'un bloc après une seule opération (aperçu de la proposition).
  function apres(o, texte) {
    if (o.type === 'masquer') return '';
    if (o.type === 'inserer') return o.nouveau;
    return remplacerTout(texte, o.ancien, o.nouveau);
  }
  // Lot coché -> état final : {blocs: {id: texte final ('' = masqué)}, insertions, sansEffet}.
  // Les remplacements d'un même bloc s'enchaînent dans l'ordre de la liste.
  function planLot(ops, textes) {
    var blocs = {}, insertions = [], sansEffet = 0, masques = {};
    (ops || []).forEach(function (o) {
      if (!Object.prototype.hasOwnProperty.call(textes, o.id)) { sansEffet++; return; }
      if (o.type === 'inserer') { insertions.push({ id: o.id, texte: o.nouveau, position: o.position }); return; }
      if (o.type === 'masquer') { masques[o.id] = 1; blocs[o.id] = ''; return; }
      if (masques[o.id]) { sansEffet++; return; }
      var cur = Object.prototype.hasOwnProperty.call(blocs, o.id) ? blocs[o.id] : textes[o.id];
      if (cur.indexOf(o.ancien) < 0) { sansEffet++; return; }
      blocs[o.id] = remplacerTout(cur, o.ancien, o.nouveau);
    });
    Object.keys(blocs).forEach(function (id) { if (!masques[id] && blocs[id] === textes[id]) delete blocs[id]; });
    return { blocs: blocs, insertions: insertions, sansEffet: sansEffet };
  }
  // Différence mot à mot : [['=', 'Date : '], ['-', '12/10'], ['+', '14/11']].
  function diffMots(a, b) {
    var x = String(a || '').match(/\s+|[^\s]+/g) || [], y = String(b || '').match(/\s+|[^\s]+/g) || [], out = [];
    function pousser(op, t) { if (out.length && out[out.length - 1][0] === op) out[out.length - 1][1] += t; else out.push([op, t]); }
    if (x.length * y.length > 160000) { if (a) pousser('-', a); if (b) pousser('+', b); return out; }
    var n = x.length, m = y.length, L = [], i, j;
    for (i = 0; i <= n; i++) { L.push(new Array(m + 1).fill(0)); }
    for (i = n - 1; i >= 0; i--) for (j = m - 1; j >= 0; j--) L[i][j] = x[i] === y[j] ? L[i + 1][j + 1] + 1 : Math.max(L[i + 1][j], L[i][j + 1]);
    i = 0; j = 0;
    while (i < n && j < m) {
      if (x[i] === y[j]) { pousser('=', x[i]); i++; j++; }
      else if (L[i + 1][j] >= L[i][j + 1]) { pousser('-', x[i]); i++; }
      else { pousser('+', y[j]); j++; }
    }
    while (i < n) pousser('-', x[i++]);
    while (j < m) pousser('+', y[j++]);
    return out;
  }

  /* ── Place libre d'un texte inséré ─────────────────────────────────── */
  // Occupation de la page, en cases d'un point : l'encre du rendu (tout pixel
  // qui n'est pas blanc, fond coloré compris : prudent) et des rectangles
  // (annotations, insertions déjà réservées).
  function grilleVide(w, h) {
    var nx = Math.ceil(w), ny = Math.ceil(h);
    return { w: w, h: h, nx: nx, ny: ny, cases: new Uint8Array(nx * ny), rects: [] };
  }
  function grilleEncre(data, W, H, k, w, h) {
    var g = grilleVide(w, h);
    for (var y = 0; y < H; y++) {
      var cy = Math.floor(y / k); if (cy >= g.ny) break;
      for (var x = 0; x < W; x++) {
        var i = (y * W + x) * 4;
        if (765 - data[i] - data[i + 1] - data[i + 2] > 60) { var cx = Math.floor(x / k); if (cx < g.nx) g.cases[cy * g.nx + cx] = 1; }
      }
    }
    return g;
  }
  function marquer(g, r) {
    for (var y = Math.max(0, Math.floor(r.y)); y < Math.min(g.ny, Math.ceil(r.y + r.h)); y++)
      for (var x = Math.max(0, Math.floor(r.x)); x < Math.min(g.nx, Math.ceil(r.x + r.w)); x++) g.cases[y * g.nx + x] = 1;
  }
  function croise(a, b) { return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h; }
  // Libre = dans la page, sans encre ni rectangle occupé. `ignorer` : la ligne
  // de référence elle-même (rect, et id de sa correction).
  function estLibre(g, r, ignorer) {
    if (r.x < 0 || r.y < 0 || r.x + r.w > g.w || r.y + r.h > g.h) return false;
    var ir = ignorer && ignorer.rect;
    for (var j = 0; j < g.rects.length; j++) {
      var q = g.rects[j];
      if (ignorer && ignorer.id && q.id === ignorer.id) continue;
      if (croise(r, q)) return false;
    }
    for (var y = Math.floor(r.y); y < Math.ceil(r.y + r.h); y++) {
      for (var x = Math.floor(r.x); x < Math.ceil(r.x + r.w); x++) {
        if (!g.cases[y * g.nx + x]) continue;
        if (ir && x + 1 > ir.x && x < ir.x + ir.w && y + 1 > ir.y && y < ir.y + ir.h) continue;
        return false;
      }
    }
    return true;
  }
  // Place d'un texte inséré près d'une ligne. Ordre : position demandée
  // (dessous : si l'espace jusqu'à la ligne suivante suffit ; droite : dans la
  // marge), l'autre position, les mêmes réduites jusqu'à 80 %, puis l'espace
  // libre le plus proche dans la même colonne ; sinon position demandée,
  // marquée « chevauche ». Rend {x, y, w, h, taille, mode, chevauche}.
  function placerInsertion(o) {
    var L = o.ligne, g = o.grille, ig = o.ignorer || { rect: L };
    function essai(mode, k) {
      var t = o.taille * k, m = o.mesure(t), e = 0.15 * o.taille;
      // À droite : même ligne de base que la ligne (ou centré sans elle), et seule la
      // bande des lettres (capitale -> ligne de base) doit être libre : l'interligne du
      // cadre texte déborde sans encre. Dessous : cadre entier + marge.
      var base = L.base != null ? L.base : null, asc = o.asc || 0.78, r, marge;
      if (mode === 'droite') {
        r = { x: L.x + L.w + 0.5 * o.taille, y: base != null ? base - asc * t : L.y + (L.h - m.h) / 2, w: m.w, h: m.h };
        marge = base != null ? { x: r.x - e, y: base - 0.8 * t, w: r.w + 2 * e, h: 0.8 * t }
          : { x: r.x - e, y: Math.min(L.y, r.y), w: r.w + 2 * e, h: Math.max(L.h, m.h) };
      } else {
        r = { x: L.x, y: L.y + L.h + e, w: m.w, h: m.h };
        marge = { x: r.x - e, y: r.y - e, w: r.w + 2 * e, h: r.h + 2 * e };
      }
      var dedans = r.x >= 0 && r.y >= 0 && r.x + r.w <= g.w && r.y + r.h <= g.h;
      return { r: r, t: t, ok: dedans && estLibre(g, marge, ig) };
    }
    function rendre(x, mode, chev) { return { x: x.r.x, y: x.r.y, w: x.r.w, h: x.r.h, taille: x.t, mode: mode, chevauche: !!chev }; }
    var ordre = o.position === 'droite' ? ['droite', 'dessous'] : ['dessous', 'droite'];
    var ks = [1, 0.9, 0.8];
    for (var a = 0; a < ks.length; a++) for (var b = 0; b < 2; b++) {
      var x = essai(ordre[b], ks[a]);
      if (x.ok) return rendre(x, ks[a] < 1 ? 'reduit' : ordre[b]);
    }
    // Même colonne : on s'écarte d'un point à la fois, dessous d'abord.
    for (var c = 0; c < 2; c++) {
      var k = c ? 0.8 : 1, t = o.taille * k, m = o.mesure(t), e = 0.15 * o.taille, y0 = L.y + L.h + e;
      for (var d = 1; d < g.h; d++) {
        for (var sgn = 1; sgn >= -1; sgn -= 2) {
          var y = sgn > 0 ? y0 + d : L.y - e - m.h - d;
          var r = { x: L.x, y: y, w: m.w, h: m.h };
          if (estLibre(g, { x: r.x - e, y: r.y - e, w: r.w + 2 * e, h: r.h + 2 * e }, ig)) return { x: r.x, y: r.y, w: r.w, h: r.h, taille: t, mode: 'colonne', chevauche: false };
        }
        if (y0 + d > g.h && L.y - d < 0) break;
      }
    }
    var dem = essai(ordre[0], 1), p = dem.r;
    // Jamais hors de la page, même en chevauchement.
    p.x = Math.max(0, Math.min(g.w - p.w, p.x)); p.y = Math.max(0, Math.min(g.h - p.h, p.y));
    return rendre(dem, ordre[0], true);
  }
  // L'insertion placée se réserve sa place (les suivantes du lot l'évitent).
  function reserver(g, pl, id) { g.rects.push({ x: pl.x, y: pl.y, w: pl.w, h: pl.h, id: id || null }); }

  M._interne = M._interne || {};
  M._interne.ia = { boiteDetectee: boiteDetectee, aTraduire: aTraduire, tailleAjustee: tailleAjustee,
    modif: { idBloc: idBloc, dansZone: dansZone, blocsPourIa: blocsPourIa, validerOps: validerOps, apres: apres,
      planLot: planLot, diffMots: diffMots, grilleVide: grilleVide, grilleEncre: grilleEncre, marquer: marquer, estLibre: estLibre, placerInsertion: placerInsertion, reserver: reserver, remplacerTout: remplacerTout, MAX_BLOCS: MODIF_MAX_BLOCS, MAX_CARACTERES: MODIF_MAX_CARACTERES } };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    var MENTION = 'Le PDF est envoyé à l\'assistant IA (Claude) pour cette demande ; rien n\'est conservé par l\'outil.';

    Object.assign(api.IC, {
      ia: '<path d="M12 3l1.9 5.4L19.5 10l-5.6 1.6L12 17l-1.9-5.4L4.5 10l5.6-1.6z"/><path d="M18.5 15.5l.8 1.9 1.9.8-1.9.8-.8 1.9-.8-1.9-1.9-.8 1.9-.8z"/>',
      resumer: '<path d="M5 6h14M5 10h14M5 14h9M5 18h6"/>',
      question: '<path d="M4.5 5.5h15v10h-8l-4 3.5v-3.5h-3z"/><path d="M10 9a2 2 0 1 1 2.5 1.9c-.4.1-.5.4-.5.8v.3M12 14h.01"/>',
      traduire: '<path d="M4 6h8M8 4v2M5.5 6c.5 3 2.5 5 5 6"/><path d="M10.5 6c-.5 3-2.5 5.5-6 6.5"/><path d="M12.5 20l3.5-9 3.5 9M13.8 17h4.4"/>',
      extraireIa: '<rect x="3.5" y="4.5" width="17" height="15" rx="1.5"/><path d="M3.5 9.5h17M9 9.5v10M15 9.5v10"/>',
      champsIa: '<rect x="3.5" y="6.5" width="17" height="11" rx="2"/><path d="M7 10v4M6 10h2M6 14h2M11 12h6"/>'
    });
    EXT.menus.ia = { libelle: 'IA', icone: 'ia', ordre: 9, ia: true, items: [
      { act: 'iaResumer', icone: 'resumer', libelle: 'Résumer le document', bulle: 'Résumer', doc: 1 },
      { act: 'iaQuestion', icone: 'question', libelle: 'Poser une question au document', bulle: 'Question', doc: 1 },
      { act: 'iaExtraire', icone: 'extraireIa', libelle: 'Extraire des données (CSV)', bulle: 'Extraire', doc: 1 },
      { act: 'iaTraduire', icone: 'traduire', libelle: 'Traduire en gardant la mise en page', bulle: 'Traduire', doc: 1 },
      { act: 'iaChamps', icone: 'champsIa', libelle: 'Détecter les champs (PDF à plat)', bulle: 'Champs', doc: 1 }
    ] };

    async function envoyer(route, champs) {
      var b = await api.construire(), fd = new FormData();
      fd.append('pdf', new Blob([b], { type: 'application/pdf' }), api.nomBase() + '.pdf');
      Object.keys(champs || {}).forEach(function (k) { fd.append(k, champs[k]); });
      var r = await fetch('/api/tools/pdf/ia/' + route, { method: 'POST', body: fd, credentials: 'same-origin' });
      var j = null; try { j = await r.json(); } catch (e) { j = null; }
      if (!r.ok) throw new Error((j && j.detail) || ('service IA indisponible (' + r.status + ')'));
      return j;
    }
    // Bouton IA qui pulse pendant l'appel ; erreurs en toast.
    function lancer(bouton, zone, fn) {
      return async function () {
        if (bouton.disabled) return;
        bouton.disabled = true; bouton.classList.add('ia-travail'); zone.classList.add('ia-travail');
        try { await fn(); }
        catch (e) { api.toast(e && e.message ? e.message.replace(/^Opération impossible — /, '') : 'Erreur IA.', 'danger'); }
        finally { bouton.disabled = false; bouton.classList.remove('ia-travail'); zone.classList.remove('ia-travail'); }
      };
    }
    function boutonIa(txt, bulle) { var b = el('button', 'tpdf-b ia-btn', txt); b.type = 'button'; b.setAttribute('data-bulle', bulle || txt); return b; }
    function copier(txt) {
      try { navigator.clipboard.writeText(txt); api.toast('Copié.', 'success'); } catch (e) { api.toast('Copie impossible dans ce navigateur.', 'danger'); }
    }

    /* ── Résumer ──────────────────────────────────────────────────────── */
    function panneauResumer() {
      var corps = el('div'), go = boutonIa('Résumer', 'Résumer'), out = el('div', 'tpdf-ia-sortie');
      corps.appendChild(el('p', 'ia-texte', MENTION)); corps.appendChild(go); corps.appendChild(out);
      go.addEventListener('click', lancer(go, out, async function () {
        out.textContent = 'Lecture du document…';
        var r = await envoyer('resumer');
        out.textContent = r.texte;
      }));
      api.ouvrirModale('Résumer le document', corps, [
        { txt: 'Copier', bulle: 'Copier', fn: function () { if (out.textContent) copier(out.textContent); } },
        { txt: 'Fermer', plein: true, fn: api.fermerModale }
      ], { cle: 'ia-resumer', ia: true });
    }
    EXT.actions.iaResumer = { fn: panneauResumer }; EXT.panneaux['ia-resumer'] = panneauResumer;

    /* ── Question ─────────────────────────────────────────────────────── */
    function panneauQuestion() {
      var corps = el('div'), fil = el('div', 'tpdf-ia-fil'), q = el('textarea', 'tpdf-champ'), go = boutonIa('Demander', 'Demander');
      q.rows = 2; q.placeholder = 'Ex. Quelle est la date d\'échéance ? Quelles pénalités en cas de retard ?';
      corps.appendChild(el('p', 'ia-texte', MENTION)); corps.appendChild(fil); corps.appendChild(q); corps.appendChild(go);
      var envoi = lancer(go, fil, async function () {
        var v = q.value.trim(); if (!v) { q.focus(); return; }
        fil.appendChild(el('div', 'tpdf-ia-q', v)); q.value = '';
        var att = el('div', 'tpdf-ia-r', '…'); fil.appendChild(att);
        try { var r = await envoyer('question', { question: v }); att.textContent = r.reponse; }
        catch (e) { att.remove(); throw e; }
        fil.scrollTop = fil.scrollHeight;
      });
      go.addEventListener('click', envoi);
      q.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' && !ev.shiftKey) { ev.preventDefault(); envoi(); } });
      api.ouvrirModale('Poser une question au document', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'ia-question', ia: true });
      requestAnimationFrame(function () { q.focus(); });
    }
    EXT.actions.iaQuestion = { fn: panneauQuestion }; EXT.panneaux['ia-question'] = panneauQuestion;

    /* ── Extraire des données ─────────────────────────────────────────── */
    function panneauExtraire() {
      var corps = el('div'), nat = el('select', 'tpdf-champ'), cons = el('textarea', 'tpdf-champ'), go = boutonIa('Extraire', 'Extraire'), out = el('div', 'tpdf-ia-sortie');
      [['facture', 'Facture'], ['bl', 'Bon de livraison'], ['fiche', 'Fiche technique'], ['libre', 'Autre (préciser)']].forEach(function (x) { var o = el('option', null, x[1]); o.value = x[0]; nat.appendChild(o); });
      cons.rows = 2; cons.placeholder = 'Facultatif : colonnes voulues, pages à lire…';
      corps.appendChild(el('p', 'ia-texte', MENTION));
      corps.appendChild(api.champ('Type de document', nat)); corps.appendChild(api.champ('Consigne', cons));
      corps.appendChild(go); corps.appendChild(out);
      var donnees = null;
      go.addEventListener('click', lancer(go, out, async function () {
        out.textContent = 'Lecture du document…';
        donnees = await envoyer('extraire', { nature: nat.value, consigne: cons.value });
        out.textContent = '';
        var t = el('table', 'tpdf-ia-table'), th = el('tr');
        donnees.colonnes.forEach(function (c) { th.appendChild(el('th', null, c)); }); t.appendChild(th);
        donnees.lignes.forEach(function (l) { var tr = el('tr'); l.forEach(function (c) { tr.appendChild(el('td', null, c)); }); t.appendChild(tr); });
        var w = el('div', 'tpdf-ia-tablewrap'); w.appendChild(t); out.appendChild(w);
        out.appendChild(el('p', 'tpdf-aide', donnees.lignes.length + ' ligne' + (donnees.lignes.length > 1 ? 's' : '') + (donnees.remarques ? ' · ' + donnees.remarques : '')));
      }));
      api.ouvrirModale('Extraire des données', corps, [
        { txt: 'Télécharger le CSV', bulle: 'CSV', fn: function () {
          if (!donnees) { api.toast('Lancer l\'extraction d\'abord.', 'info'); return; }
          var csv = (M._interne.revision && M._interne.revision.csv) ? M._interne.revision.csv([donnees.colonnes].concat(donnees.lignes)) : '';
          var u = api.urlObjet(new Blob([csv], { type: 'text/csv;charset=utf-8' })), a = el('a'); a.href = u; a.download = api.nomBase() + '-donnees.csv'; a.style.display = 'none';
          S().el.appendChild(a); a.click(); a.remove();
        } },
        { txt: 'Fermer', plein: true, fn: api.fermerModale }
      ], { cle: 'ia-extraire', ia: true, large: true });
    }
    EXT.actions.iaExtraire = { fn: panneauExtraire }; EXT.panneaux['ia-extraire'] = panneauExtraire;

    /* ── Détecter les champs ──────────────────────────────────────────── */
    function panneauChamps() {
      var corps = el('div'), go = boutonIa('Détecter les champs', 'Détecter'), out = el('div', 'tpdf-ia-sortie');
      corps.appendChild(el('p', 'ia-texte', MENTION));
      corps.appendChild(el('p', 'tpdf-aide', 'Les zones à remplir (lignes, cases, cadres) deviennent des champs remplissables, à vérifier et ajuster comme les autres (outil Champ).'));
      corps.appendChild(go); corps.appendChild(out);
      go.addEventListener('click', lancer(go, out, async function () {
        if (!EXT.types.champ) throw new Error('Module formulaires indisponible.');
        out.textContent = 'Lecture du document…';
        var r = await envoyer('champs'), s = S(), avant = api.snapshot(), n = 0;
        var pris = [];
        Object.keys(s.sources).forEach(function (k) { s.sources[k].champs.forEach(function (c) { pris.push(c.nom); }); });
        s.pages.forEach(function (p) { p.annots.forEach(function (a) { if (a.t === 'champ') pris.push(a.nom); }); });
        r.champs.forEach(function (c) {
          var p = s.pages[c.page - 1]; if (!p) return;
          var d = api.dims(p), b = boiteDetectee(c, d.w, d.h);
          var nom = c.nom && pris.indexOf(c.nom) < 0 ? c.nom : M._interne.formulaires.nomUnique(c.nom || 'Champ', pris);
          pris.push(nom);
          var genre = c.type === 'case' ? 'case' : c.type;
          var a = { id: api.nid('n'), t: 'champ', genre: genre, nom: nom, requis: false, defaut: genre === 'case' ? false : '',
            options: c.options || [], taille: 0, x: b.x, y: b.y, w: b.w, h: b.h };
          if (genre === 'case') { var cote = Math.max(10, Math.min(b.w, b.h)); a.w = a.h = cote; }
          p.annots.push(a); n++;
        });
        if (n) { api.pushHist(avant); api.dessinerCalque(); api.rendreVignettes(); api.rendreBarre(); }
        out.textContent = n ? n + ' champ' + (n > 1 ? 's posés' : ' posé') + ' — vérifier les positions, puis enregistrer.' : 'Aucune zone à remplir trouvée.';
        if (n) api.toast(out.textContent, 'success');
      }));
      api.ouvrirModale('Détecter les champs', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'ia-champs', ia: true });
    }
    EXT.actions.iaChamps = { fn: panneauChamps }; EXT.panneaux['ia-champs'] = panneauChamps;

    /* ── Traduire en gardant la mise en page ──────────────────────────── */
    function panneauTraduire() {
      var s = S(), corps = el('div'), langue = el('select', 'tpdf-champ'), pages = el('select', 'tpdf-champ'), go = boutonIa('Traduire', 'Traduire'), out = el('div', 'tpdf-ia-sortie');
      [['courante', 'Page courante'], ['toutes', 'Toutes les pages']].forEach(function (x) { var o = el('option', null, x[1]); o.value = x[0]; pages.appendChild(o); });
      fetch('/api/translate/langs', { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (j) {
        (j.langs || []).forEach(function (l) { var o = el('option', null, l.label); o.value = l.code; langue.appendChild(o); });
        langue.value = (j.langs || []).some(function (l) { return l.code === 'EN-GB'; }) ? 'EN-GB' : ((j.langs || [])[0] || {}).code || '';
      }).catch(function () { var o = el('option', null, 'Anglais'); o.value = 'EN-GB'; langue.appendChild(o); });
      corps.appendChild(el('p', 'ia-texte', 'Chaque bloc de texte est envoyé au service de traduction (DeepL), puis posé à la place de l\'original avec la même police, taille réduite si la traduction est plus longue.'));
      corps.appendChild(api.champ('Traduire vers', langue)); corps.appendChild(api.champ('Pages', pages));
      corps.appendChild(el('p', 'tpdf-aide tpdf-avert', (EXT.texte && EXT.texte.AVERTISSEMENT) || ''));
      corps.appendChild(el('p', 'tpdf-aide', 'Pages pivotées, recadrées ou scannées ignorées. Chaque bloc traduit reste modifiable ; Ctrl+Z annule tout.'));
      corps.appendChild(go); corps.appendChild(out);
      go.addEventListener('click', lancer(go, out, async function () {
        if (!EXT.texte) throw new Error('Module « Modifier le texte » indisponible.');
        var l = pages.value === 'toutes' ? s.pages.slice() : [api.pageCourante()], avant = api.snapshot(), n = 0, ign = 0, erreurs = 0;
        api.occuper('Traduction…');
        try {
          for (var i = 0; i < l.length; i++) {
            var p = l[i], info = await EXT.texte.blocsPage(p);
            if (!info) { ign++; continue; }
            var blocs = info.blocs.filter(function (b) { return aTraduire(b.str); });
            for (var k = 0; k < blocs.length; k += 4) {
              out.textContent = 'Page ' + (s.pages.indexOf(p) + 1) + ' — blocs ' + (k + 1) + ' à ' + Math.min(blocs.length, k + 4) + ' sur ' + blocs.length + '…';
              await Promise.all(blocs.slice(k, k + 4).map(async function (bl) {
                var r = await fetch('/api/translate', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ text: bl.str, target_lang: langue.value }) });
                if (!r.ok) { erreurs++; return; }
                var tr = ((await r.json()) || {}).translated;
                if (!tr || tr === bl.str) return;
                var a = EXT.texte.trouverRemplace(p, bl.premier);
                if (!a) { a = await EXT.texte.preparer(p, info.d, bl, info.tc, info.bornes[info.blocs.indexOf(bl)]); p.annots.push(a); }
                var taille0 = a.tailleOrig || a.taille; a.tailleOrig = taille0;
                a.texte = tr; a.esp = 0; a.largeur = null;
                a.taille = tailleAjustee(taille0, a.w, EXT.texte.mesure(tr, Object.assign({}, a, { taille: taille0 })));
                n++;
              }));
            }
          }
        } finally { api.liberer(); }
        if (n) { api.pushHist(avant); api.dessinerCalque(); api.rendreVignettes(); api.rendreBarre(); }
        out.textContent = n + ' bloc' + (n > 1 ? 's traduits' : ' traduit') + (ign ? ' · ' + ign + ' page(s) ignorée(s)' : '') + (erreurs ? ' · ' + erreurs + ' bloc(s) en échec' : '') + '.';
        if (n) api.toast(out.textContent, 'success'); else if (erreurs) throw new Error('Service de traduction indisponible.');
      }));
      api.ouvrirModale('Traduire en gardant la mise en page', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'ia-traduire', ia: true });
    }
    EXT.actions.iaTraduire = { fn: panneauTraduire }; EXT.panneaux['ia-traduire'] = panneauTraduire;

    /* ── Lot 4 : sélection, contrats, BAT, génération ─────────────────── */
    Object.assign(api.IC, {
      iaZone: '<path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16"/><path d="M12 8l1 2.6 2.6 1-2.6 1L12 15l-1-2.4-2.6-1 2.6-1z"/>',
      contrats: '<path d="M13.5 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M13.5 3.5V9H19"/><path d="M8.5 13h7M8.5 16.5h4"/>',
      batIa: '<rect x="3.5" y="5" width="11" height="14" rx="1.5"/><path d="M6.5 9h5M6.5 12h5"/><path d="M15.5 13.5l2 2 4-4.5"/>',
      generer: '<path d="M13.5 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M13.5 3.5V9H19"/><path d="M12 11v6M9 14h6"/>'
    });
    api.LIBELLES.iaZone = 'Sélection pour l\'IA';
    api.AIDE_OUTIL.iaZone = 'Tracer un cadre autour du passage à expliquer ou reformuler.';
    EXT.menus.ia.items.push({ separe: true },
      { act: 'iaSelection', icone: 'iaZone', libelle: 'Expliquer ou reformuler un passage', bulle: 'Passage', doc: 1 },
      { act: 'iaContrats', icone: 'contrats', libelle: 'Comparer deux contrats', bulle: 'Contrats', doc: 1 },
      { act: 'iaBat', icone: 'batIa', libelle: 'Vérifier le BAT contre la fiche technique', bulle: 'Vérifier', doc: 1 },
      { act: 'iaGenerer', icone: 'generer', libelle: 'Remplir le modèle à partir de données', bulle: 'Générer', doc: 1 });

    EXT.actions.iaSelection = { fn: function () { api.choisirOutil('iaZone'); } };
    EXT.outils.iaZone = { down: function (pt) { return { t: 'iazone', x: pt.x, y: pt.y, w: 0, h: 0 }; } };
    EXT.types.iazone = {
      boiteTournante: true,
      tailleDefaut: function () { return [200, 60]; },
      dessiner: function (a, g, z) { api.sv('rect', { x: a.x, y: a.y, width: a.w, height: a.h, 'class': 'tpdf-iazone', 'stroke-width': 1.5 / z }, g); },
      apresCreation: function (a) {
        var s = S(), p = api.pageCourante(), d = api.dims(p);
        setTimeout(async function () {
          var pour = s._iaZonePour; s._iaZonePour = null;
          p.annots = p.annots.filter(function (x) { return x !== a; }); s.annSel = null; api.choisirOutil('select'); api.dessinerCalque(); api.majBadges();
          var items = await api.texteDe(p), dedans = items.filter(function (it) {
            if (!it.transform || !it.str || !it.str.trim()) return false;
            var q = api.versVue(d.meta.view, d.R, it.transform[4], it.transform[5]);
            return q[0] >= a.x - 2 && q[0] <= a.x + a.w && q[1] >= a.y && q[1] <= a.y + a.h + 4;
          });
          var texte = dedans.map(function (it) { return it.str + (it.hasEOL ? '\n' : ' '); }).join('').replace(/[ \t]+\n/g, '\n').trim();
          s._iaZone = { uid: p.uid, x: a.x, y: a.y, w: a.w, h: a.h };
          if (pour === 'modifier') { panneauModifier({ portee: 'zone' }); return; }
          panneauSelection(texte);
        }, 0);
      },
      exporter: async function () { /* cadre de travail */ }
    };
    function panneauSelection(texte) {
      var corps = el('div'), src = el('textarea', 'tpdf-champ'), out = el('div', 'tpdf-ia-sortie'), lg = el('div', 'tpdf-ligne');
      src.rows = 5; src.value = texte || '';
      corps.appendChild(el('p', 'ia-texte', 'Seul le passage ci-dessous est envoyé à l\'assistant IA.'));
      corps.appendChild(api.champ('Passage', src));
      if (!texte) corps.appendChild(el('p', 'tpdf-aide', 'Aucun texte dans ce cadre (scan ?) : coller le passage ou lancer l\'OCR.'));
      [['expliquer', 'Expliquer'], ['reformuler', 'Reformuler'], ['resumer', 'Résumer']].forEach(function (x) {
        var b = boutonIa(x[1], x[1]);
        b.addEventListener('click', lancer(b, out, async function () {
          if (!src.value.trim()) throw new Error('Aucun texte sélectionné.');
          var fd = new FormData(); fd.append('texte', src.value); fd.append('mode', x[0]);
          var r = await fetch('/api/tools/pdf/ia/selection', { method: 'POST', body: fd, credentials: 'same-origin' });
          var j = null; try { j = await r.json(); } catch (e) { j = null; }
          if (!r.ok) throw new Error((j && j.detail) || 'Service IA indisponible.');
          out.textContent = j.texte;
        }));
        lg.appendChild(b);
      });
      var modif = boutonIa('Modifier avec l\'IA', 'Modifier');
      modif.addEventListener('click', function () { panneauModifier({ portee: 'zone' }); });
      lg.appendChild(modif);
      corps.appendChild(lg); corps.appendChild(out);
      api.ouvrirModale('Passage sélectionné', corps, [
        { txt: 'Copier le résultat', bulle: 'Copier', fn: function () { if (out.textContent) copier(out.textContent); } },
        { txt: 'Fermer', plein: true, fn: api.fermerModale }
      ], { ia: true });
    }

    function panneauContrats() {
      var corps = el('div'), fic = el('input', 'tpdf-champ'), go = boutonIa('Comparer les clauses', 'Comparer'), out = el('div', 'tpdf-ia-sortie');
      fic.type = 'file'; fic.accept = '.pdf,application/pdf';
      corps.appendChild(el('p', 'ia-texte', 'Les deux PDF sont envoyés à l\'assistant IA (Claude) pour cette demande.'));
      corps.appendChild(api.champ('Autre version du contrat (le document ouvert sert de référence)', fic));
      corps.appendChild(go); corps.appendChild(out);
      go.addEventListener('click', lancer(go, out, async function () {
        var f = fic.files && fic.files[0]; if (!f) throw new Error('Choisir l\'autre version.');
        out.textContent = 'Lecture des deux versions…';
        var r = await envoyer('contrats', { pdf2: new File([await f.arrayBuffer()], f.name, { type: 'application/pdf' }) });
        out.textContent = r.texte;
      }));
      api.ouvrirModale('Comparer deux contrats', corps, [
        { txt: 'Copier', bulle: 'Copier', fn: function () { if (out.textContent) copier(out.textContent); } },
        { txt: 'Fermer', plein: true, fn: api.fermerModale }
      ], { cle: 'ia-contrats', ia: true, large: true });
    }
    EXT.actions.iaContrats = { fn: panneauContrats }; EXT.panneaux['ia-contrats'] = panneauContrats;

    function panneauBat() {
      var corps = el('div'), q = el('input', 'tpdf-champ'), fiches = el('select', 'tpdf-champ'), go = boutonIa('Vérifier le BAT', 'Vérifier'), out = el('div', 'tpdf-lc');
      q.type = 'search'; q.placeholder = 'Rechercher une fiche (référence, format, support…)';
      corps.appendChild(el('p', 'ia-texte', 'Le BAT (document ouvert) et la fiche technique choisie sont envoyés à l\'assistant IA.'));
      corps.appendChild(api.champ('Fiche technique', q)); corps.appendChild(fiches); corps.appendChild(go); corps.appendChild(out);
      var minuteur = null;
      async function chercher() {
        try {
          var r = await fetch('/api/fiches-techniques/list?limit=50&q=' + encodeURIComponent(q.value.trim()), { credentials: 'same-origin' });
          var j = await r.json(); if (!r.ok) throw new Error((j && j.detail) || 'Fiches techniques inaccessibles.');
          fiches.textContent = '';
          (j.rows || []).forEach(function (f) { var o = el('option', null, [f.reference, f.designation || f.format, f.client].filter(Boolean).join(' — ')); o.value = f.id; fiches.appendChild(o); });
          if (!(j.rows || []).length) { var o0 = el('option', null, 'Aucun résultat pour « ' + q.value + ' »'); o0.value = ''; fiches.appendChild(o0); }
        } catch (e) { api.toast(api.msgErreur(e), 'danger'); }
      }
      q.addEventListener('input', function () { clearTimeout(minuteur); minuteur = setTimeout(chercher, 250); });
      chercher();
      go.addEventListener('click', lancer(go, out, async function () {
        if (!fiches.value) throw new Error('Choisir une fiche technique.');
        out.textContent = '';
        var r = await envoyer('bat', { fiche_id: fiches.value });
        out.appendChild(el('p', 'tpdf-resultat', r.synthese));
        var lib = { conforme: 'Conforme', ecart: 'Écart', a_verifier: 'À vérifier' };
        r.points.forEach(function (pt) {
          var b = el('button', 'tpdf-lc-item tpdf-bat-' + pt.statut); b.type = 'button';
          b.appendChild(el('span', 'tpdf-lc-nom', pt.sujet)); b.appendChild(el('span', 'tpdf-lc-type', lib[pt.statut] || pt.statut));
          b.appendChild(el('span', 'tpdf-lc-val', 'Attendu : ' + pt.attendu + ' · Constaté : ' + pt.constate));
          b.addEventListener('click', function () { api.fermerModale(); api.allerPage(Math.max(0, (pt.page || 1) - 1), true); });
          out.appendChild(b);
        });
      }));
      api.ouvrirModale('Vérifier le BAT', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'ia-bat', ia: true, large: true });
    }
    EXT.actions.iaBat = { fn: panneauBat }; EXT.panneaux['ia-bat'] = panneauBat;

    function panneauGenerer() {
      var corps = el('div'), don = el('textarea', 'tpdf-champ'), go = boutonIa('Remplir le modèle', 'Remplir'), out = el('div', 'tpdf-ia-sortie');
      var champs = EXT.formulaire ? EXT.formulaire.champsDuDocument() : [];
      don.rows = 6; don.placeholder = 'Coller les données : texte libre, courriel, ligne de tableau…';
      corps.appendChild(el('p', 'ia-texte', 'Le modèle (document ouvert) et les données sont envoyés à l\'assistant IA, qui remplit les champs.'));
      corps.appendChild(el('p', 'tpdf-aide', champs.length ? champs.length + ' champ(s) dans le modèle. Pour un CSV d\'une ligne par document, sans IA : Réviser › Réponses du formulaire.' : 'Ce document n\'a pas de champ : en créer (outil Champ) ou les détecter (IA › Détecter les champs).'));
      corps.appendChild(api.champ('Données', don)); corps.appendChild(go); corps.appendChild(out);
      go.addEventListener('click', lancer(go, out, async function () {
        if (!champs.length) throw new Error('Ce modèle n\'a pas de champ à remplir.');
        out.textContent = 'Remplissage…';
        var r = await envoyer('remplir', { champs: JSON.stringify(champs.map(function (f) { return { nom: f.nom, type: f.cree ? f.cree.genre : (f.c && f.c.type), options: (f.cree ? f.cree.options : f.c && f.c.options) || [] }; })), donnees: don.value });
        var noms = Object.keys(r.valeurs || {});
        var avant = api.snapshot(), n = EXT.formulaire.appliquer(noms, noms.map(function (k) { return r.valeurs[k]; }));
        api.pushHist(avant); api.rendrePage(); api.rendreProps(); api.dessinerCalque();
        out.textContent = n + ' champ(s) rempli(s). Vérifier, puis enregistrer.';
      }));
      api.ouvrirModale('Remplir le modèle à partir de données', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'ia-generer', ia: true });
    }
    EXT.actions.iaGenerer = { fn: panneauGenerer }; EXT.panneaux['ia-generer'] = panneauGenerer;

    /* ── Modifier avec l'IA ───────────────────────────────────────────── */
    // L'utilisateur décrit la modification ; seuls les blocs de texte de la
    // portée partent au serveur. Les propositions se relisent (avant/après,
    // aperçu sur la page) et s'appliquent avec le moteur de « Modifier le
    // texte », en une seule étape d'annulation.
    var MD = M._interne.ia.modif;
    api.IC.iaCreer = '<path d="M13.5 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M13.5 3.5V9H19"/><path d="M12 11.5l.9 2.3 2.3.9-2.3.9-.9 2.3-.9-2.3-2.3-.9 2.3-.9z"/>';
    api.IC.iaModif = '<path d="M4 20h4L18.5 9.5a2.1 2.1 0 0 0-3-3L5 17z"/><path d="M14 8l3 3"/><path d="M19 14l.7 1.8 1.8.7-1.8.7-.7 1.8-.7-1.8-1.8-.7 1.8-.7z"/>';
    EXT.menus.ia.items.unshift(
      { act: 'iaModifier', icone: 'iaModif', libelle: 'Modifier avec l\'IA', bulle: 'Modifier', doc: 1, badge: 'IA' },
      // Action dans mysifa_tools_pdf_iacreer.js ; disponible sans document ouvert.
      { act: 'iaCreer', icone: 'iaCreer', libelle: 'Créer avec l\'IA', bulle: 'Créer', badge: 'IA' },
      { separe: true });
    var _modif = null; // {props: [...], reg: {id: {uid, premier, texte, x, y, h, w}}, remarque, ecartees}

    function pageParUid(uid) { var s = S(); for (var i = 0; i < s.pages.length; i++) if (s.pages[i].uid === uid) return i; return -1; }
    // Blocs de la portée, avec le texte courant (correction déjà posée comprise).
    async function collecter(portee) {
      var s = S(), zone = s._iaZone, liste;
      if (portee === 'zone') { var iz = zone ? pageParUid(zone.uid) : -1; liste = iz >= 0 ? [s.pages[iz]] : []; }
      else liste = portee === 'page' ? [api.pageCourante()] : s.pages.slice();
      var entrees = [], reg = {}, ignorees = 0, vues = 0;
      for (var i = 0; i < liste.length; i++) {
        var p = liste[i], info = await EXT.texte.blocsPage(p);
        if (!info) { ignorees++; continue; }
        vues++;
        var view = info.d.meta.view, ip = s.pages.indexOf(p);
        info.blocs.forEach(function (bl) {
          var deja = EXT.texte.trouverRemplace(p, bl.premier), texte = deja ? deja.texte : bl.str;
          if (!texte || !texte.trim()) return;
          var b = { x: bl.X0 - view[0], y: view[3] - bl.Y };
          if (portee === 'zone' && !MD.dansZone(b, zone)) return;
          var id = MD.idBloc(ip, bl.premier);
          reg[id] = { uid: p.uid, premier: bl.premier, texte: texte, x: b.x, y: b.y, h: bl.h, w: bl.X1 - bl.X0 };
          entrees.push({ id: id, page: ip, texte: texte, x: b.x, y: b.y });
        });
      }
      return { entrees: entrees, reg: reg, ignorees: ignorees, vues: vues };
    }

    function ancrerCote(o) { o.fond.classList.add('tpdf-fond-cote'); }
    function surFermeture(fond, fn) {
      var obs = new MutationObserver(function () { if (!fond.isConnected) { obs.disconnect(); fn(); } });
      obs.observe(S().el, { childList: true });
    }

    /* Aperçu en surimpression sur la page */
    var _apercu = null; // {id, texte}
    function retirerApercu() { var s = S(); if (s && s.html) s.html.querySelectorAll('.tpdf-ia-apercu').forEach(function (e) { e.remove(); }); }
    function dessinerApercu() {
      retirerApercu();
      var s = S(); if (!_apercu || !_modif || !s) return;
      var r = _modif.reg[_apercu.id], p = api.pageCourante();
      if (!r || !p || p.uid !== r.uid) return;
      var z = s.zoomCourant || 1, d = el('div', 'tpdf-ia-apercu', _apercu.texte || 'Ligne supprimée');
      if (!_apercu.texte) d.classList.add('tpdf-ia-apercu-vide');
      var pl = _apercu.place;
      if (pl) {
        d.style.left = (pl.x * z) + 'px'; d.style.top = (pl.y * z) + 'px';
        d.style.fontSize = (pl.taille * z) + 'px'; d.style.lineHeight = (pl.h * z) + 'px';
        if (pl.chevauche) { d.classList.add('tpdf-ia-apercu-chev'); d.appendChild(el('span', 'tpdf-ia-chev', 'Chevauche — à déplacer')); }
      } else {
        d.style.left = (r.x * z) + 'px'; d.style.top = ((r.y - r.h * 0.95) * z) + 'px'; d.style.minWidth = (r.w * z) + 'px';
        d.style.fontSize = (r.h * z) + 'px'; d.style.lineHeight = (r.h * 1.2 * z) + 'px';
      }
      s.html.appendChild(d);
      if (d.scrollIntoView) d.scrollIntoView({ block: 'center', inline: 'nearest', behavior: 'smooth' });
    }
    EXT.hooks.page = (EXT.hooks.page || []).concat(function () { if (_apercu) setTimeout(dessinerApercu, 0); });
    function montrer(o) {
      if (!_modif) return;
      var r = _modif.reg[o.id]; if (!r) return;
      var i = pageParUid(r.uid); if (i < 0) { api.toast('Page retirée du document.', 'info'); return; }
      _apercu = { op: o, id: o.id, texte: o.type === 'inserer' ? o.nouveau : MD.apres(o, r.texte),
        place: o.type === 'inserer' && _modif.places ? _modif.places.get(o) || null : null };
      if (S().cur !== i) api.allerPage(i, true); else dessinerApercu();
    }

    function diffEl(a, b) {
      var d = el('div', 'tpdf-diff');
      MD.diffMots(a, b).forEach(function (x) {
        d.appendChild(el(x[0] === '-' ? 'del' : x[0] === '+' ? 'ins' : 'span', x[0] === '-' ? 'tpdf-diff-moins' : x[0] === '+' ? 'tpdf-diff-plus' : null, x[1]));
      });
      return d;
    }
    var LIB_OP = { remplacer: 'Remplacer', masquer: 'Supprimer la ligne', inserer: 'Ajouter' };
    var LIB_PLACE = { dessous: 'sous la ligne', droite: 'à droite de la ligne', reduit: 'taille réduite pour tenir', colonne: 'plus loin dans la colonne' };

    // Ligne de référence d'une insertion : sa correction si elle existe, sinon
    // la mesure du moteur « Modifier le texte » (sans la poser).
    async function refPour(p, info, id) {
      var r = _modif.reg[id], k = -1;
      info.blocs.forEach(function (bl, i) { if (bl.premier === r.premier) k = i; });
      if (k < 0) return null;
      return EXT.texte.trouverRemplace(p, r.premier) || await EXT.texte.preparer(p, info.d, info.blocs[k], info.tc, info.bornes[k]);
    }
    // Place des insertions d'une page, dans l'ordre : encre du rendu + annotations
    // existantes occupées, chaque insertion placée se réserve sa place.
    async function placerPage(p, info, items) {
      var g;
      try { var px = await EXT.texte.rendu(p); g = MD.grilleEncre(px.data, px.W, px.H, px.k, info.d.w, info.d.h); }
      catch (e) { g = MD.grilleVide(info.d.w, info.d.h); }
      p.annots.forEach(function (a) {
        if (a.t === 'iazone') return;
        var b = null; try { b = api.boite(a); } catch (e) { b = null; }
        if (b && b.w > 0 && b.h > 0) g.rects.push({ x: b.x, y: b.y, w: b.w, h: b.h, id: a.id });
      });
      var out = [];
      for (var i = 0; i < items.length; i++) {
        var x = items[i], ref = await refPour(p, info, x.id);
        if (!ref) { out.push(null); continue; }
        var lg = { x: ref.x + (ref.dx || 0), y: ref.y + (ref.dy || 0), w: Math.max(ref.w, EXT.texte.mesure(ref.texte || ref.orig, ref)), h: ref.h,
          base: ref.by + (ref.dy || 0) };
        var txt = x.texte;
        var pl = MD.placerInsertion({ ligne: lg, taille: Math.round(ref.taille * 10) / 10, position: x.position, grille: g,
          asc: api.ASC, mesure: function (t) { return api.mesureTexte(txt, t); }, ignorer: { rect: lg, id: ref.id } });
        pl.taille = Math.round(pl.taille * 10) / 10; pl.couleur = ref.couleur;
        MD.reserver(g, pl); out.push(pl);
      }
      return out;
    }
    // Places des insertions cochées (relecture) : Map proposition -> place.
    async function placerTout(ops) {
      var parPage = {}, res = new Map();
      ops.forEach(function (o) { var u = _modif.reg[o.id].uid; (parPage[u] = parPage[u] || []).push(o); });
      for (var u in parPage) {
        var ip = pageParUid(u); if (ip < 0) continue;
        var p = S().pages[ip], info = await EXT.texte.blocsPage(p); if (!info) continue;
        var pls = await placerPage(p, info, parPage[u].map(function (o) { return { id: o.id, texte: o.nouveau, position: o.position }; }));
        parPage[u].forEach(function (o, i) { if (pls[i]) res.set(o, pls[i]); });
      }
      return res;
    }

    async function appliquer(choisies) {
      var s = S(), avant = api.snapshot(), textes = {}, n = 0, sansEffet = 0, chev = 0;
      // Texte courant au moment d'appliquer (une correction a pu être faite entre-temps).
      Object.keys(_modif.reg).forEach(function (id) {
        var r = _modif.reg[id], ip = pageParUid(r.uid); if (ip < 0) return;
        var deja = EXT.texte.trouverRemplace(s.pages[ip], r.premier);
        textes[id] = deja ? deja.texte : r.texte;
      });
      var plan = MD.planLot(choisies, textes);
      sansEffet = plan.sansEffet;
      var parPage = {};
      Object.keys(plan.blocs).forEach(function (id) { var u = _modif.reg[id].uid; (parPage[u] = parPage[u] || { blocs: [], ins: [] }).blocs.push(id); });
      plan.insertions.forEach(function (x) { var u = _modif.reg[x.id].uid; (parPage[u] = parPage[u] || { blocs: [], ins: [] }).ins.push(x); });
      api.occuper('Application…');
      try {
        for (var u in parPage) {
          var ip = pageParUid(u); if (ip < 0) { sansEffet += parPage[u].blocs.length + parPage[u].ins.length; continue; }
          var p = s.pages[ip], info = await EXT.texte.blocsPage(p);
          if (!info) { sansEffet += parPage[u].blocs.length + parPage[u].ins.length; continue; }
          var parPremier = {};
          info.blocs.forEach(function (bl, k) { parPremier[bl.premier] = k; });
          var correction = async function (id, poser) {
            var r = _modif.reg[id], k = parPremier[r.premier]; if (k == null) return null;
            var a = EXT.texte.trouverRemplace(p, r.premier);
            if (a) return a;
            a = await EXT.texte.preparer(p, info.d, info.blocs[k], info.tc, info.bornes[k]);
            if (poser) p.annots.push(a);
            return a;
          };
          for (var b = 0; b < parPage[u].blocs.length; b++) {
            var id = parPage[u].blocs[b], a = await correction(id, true);
            if (!a) { sansEffet++; continue; }
            a.texte = plan.blocs[id]; n++;
          }
          // Après les corrections de la page : elles comptent comme occupées.
          var ins = parPage[u].ins, pls = await placerPage(p, info, ins);
          for (var j = 0; j < ins.length; j++) {
            var pl = pls[j]; if (!pl) { sansEffet++; continue; }
            p.annots.push({ id: api.nid('n'), t: 'texte', texte: ins[j].texte, taille: pl.taille, couleur: pl.couleur, x: pl.x, y: pl.y });
            if (pl.chevauche) chev++;
            n++;
          }
        }
      } finally { api.liberer(); }
      if (n) { api.pushHist(avant); s.annSel = null; api.dessinerCalque(); api.rendreVignettes(); api.rendreBarre(); api.majBadges(); }
      return { n: n, sansEffet: sansEffet, chev: chev };
    }

    function panneauModifier(opts) {
      opts = opts || {};
      var s = S(), corps = el('div'), cons = el('textarea', 'tpdf-champ'), portee = el('select', 'tpdf-champ');
      var go = boutonIa('Préparer les modifications', 'Préparer'), out = el('div', 'tpdf-ia-sortie');
      cons.rows = 3; cons.maxLength = 2000; cons.value = opts.consigne || '';
      cons.placeholder = 'Ex. Remplace la date du 12/10 par le 14/11 partout · Corrige les fautes de la page 2 · Supprime la ligne Téléphone';
      var zoneOk = !!(s._iaZone && pageParUid(s._iaZone.uid) >= 0);
      [['document', 'Tout le document'], ['page', 'Page courante'], ['zone', zoneOk ? 'Zone encadrée (page ' + (pageParUid(s._iaZone.uid) + 1) + ')' : 'Zone encadrée (aucune)']].forEach(function (x) {
        var o = el('option', null, x[1]); o.value = x[0]; if (x[0] === 'zone' && !zoneOk) o.disabled = true; portee.appendChild(o);
      });
      portee.value = opts.portee === 'zone' && zoneOk ? 'zone' : (opts.portee || (s.pages.length > 20 ? 'page' : 'document'));
      var encadrer = el('button', 'tpdf-b', 'Encadrer une zone'); encadrer.type = 'button'; encadrer.setAttribute('data-bulle', 'Encadrer');
      encadrer.addEventListener('click', function () { S()._iaZonePour = 'modifier'; api.fermerModale(); api.choisirOutil('iaZone'); api.toast('Tracer un cadre autour du passage à modifier.', 'info'); });
      var lg = el('div', 'tpdf-ligne'); lg.appendChild(portee); lg.appendChild(encadrer);
      corps.appendChild(el('p', 'ia-texte', 'Seul le texte de la portée choisie est envoyé à l\'assistant IA (Claude), sans le PDF ni les images. Rien ne s\'applique avant relecture.'));
      corps.appendChild(api.champ('Consigne', cons));
      var lab = el('div', 'tpdf-prop'); lab.appendChild(el('span', 'tpdf-lab', 'Portée')); lab.appendChild(lg); corps.appendChild(lab);
      corps.appendChild(el('p', 'tpdf-aide', 'Pages pivotées, recadrées ou scannées ignorées. Document long : choisir la page courante ou une zone.'));
      corps.appendChild(go); corps.appendChild(out);
      var envoi = lancer(go, out, async function () {
        if (!EXT.texte) throw new Error('Module « Modifier le texte » indisponible.');
        var v = cons.value.trim(); if (!v) { cons.focus(); throw new Error('Décrire la modification voulue.'); }
        out.textContent = 'Lecture du texte…';
        var c = await collecter(portee.value);
        if (!c.entrees.length) {
          out.textContent = '';
          if (portee.value === 'zone') throw new Error('Aucun texte dans la zone encadrée.');
          var vide = el('div', 'tpdf-lc');
          vide.appendChild(el('p', 'tpdf-aide', c.vues ? 'Pas de texte lisible dans la portée choisie : PDF scanné ? Lancer l\'OCR d\'abord, puis recommencer.'
            : 'Pages pivotées ou recadrées : les remettre à l\'endroit, ou lancer l\'OCR si le document est scanné.'));
          if (EXT.actions.ocr) { var ocr = el('button', 'tpdf-b', 'Lancer l\'OCR'); ocr.type = 'button'; ocr.setAttribute('data-bulle', 'OCR'); ocr.addEventListener('click', function () { api.fermerModale(); EXT.actions.ocr.fn(); }); vide.appendChild(ocr); }
          out.appendChild(vide);
          return;
        }
        var env = MD.blocsPourIa(c.entrees);
        if (env.trop) throw new Error('Document trop long pour un seul passage (' + env.blocs.length + ' lignes) — choisir la page courante ou une zone.');
        out.textContent = 'Préparation des modifications…';
        var fd = new FormData(); fd.append('consigne', v); fd.append('blocs', JSON.stringify(env.blocs));
        var r = await fetch('/api/tools/pdf/ia/modifier', { method: 'POST', body: fd, credentials: 'same-origin' });
        var j = null; try { j = await r.json(); } catch (e) { j = null; }
        if (!r.ok) throw new Error((j && j.detail) || ('Service IA indisponible (' + r.status + ').'));
        var textes = {}; Object.keys(c.reg).forEach(function (id) { textes[id] = c.reg[id].texte; });
        var vo = MD.validerOps(j.operations, textes);
        _modif = { props: vo.valides, reg: c.reg, remarque: j.remarque || '', ecartees: (j.ecartees || 0) + vo.ecartees, consigne: v, portee: portee.value };
        out.textContent = '';
        panneauRelecture();
      });
      go.addEventListener('click', envoi);
      cons.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' && (ev.metaKey || ev.ctrlKey)) { ev.preventDefault(); envoi(); } });
      var o = api.ouvrirModale('Modifier avec l\'IA', corps, [{ txt: 'Fermer', bulle: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'ia-modifier', ia: true });
      ancrerCote(o);
      requestAnimationFrame(function () { cons.focus(); });
    }

    function panneauRelecture() {
      var m = _modif, corps = el('div'), liste = el('div', 'tpdf-ia-props'), coches = [], placesEl = new Map();
      var tete = el('p', 'tpdf-aide', m.props.length
        ? m.props.length + ' proposition' + (m.props.length > 1 ? 's' : '') + ' — cliquer pour voir l\'endroit, décocher pour écarter.'
        : 'Aucune modification proposée.');
      corps.appendChild(el('p', 'ia-texte', 'Consigne : ' + m.consigne));
      corps.appendChild(tete);
      if (m.remarque) corps.appendChild(el('p', 'tpdf-resultat', m.remarque));
      if (m.ecartees) corps.appendChild(el('p', 'tpdf-aide tpdf-avert', m.ecartees + ' proposition' + (m.ecartees > 1 ? 's écartées' : ' écartée') + ' : texte introuvable dans le document.'));
      m.props.forEach(function (o, i) {
        var r = m.reg[o.id], ligne = el('div', 'tpdf-ia-prop'), cb = el('input');
        cb.type = 'checkbox'; cb.checked = true; cb.setAttribute('aria-label', 'Retenir la proposition ' + (i + 1));
        cb.addEventListener('change', function () { ligne.classList.toggle('tpdf-ia-prop-off', !cb.checked); majBouton(); majPlaces(); });
        coches.push(cb);
        var txt = el('button', 'tpdf-ia-prop-corps'); txt.type = 'button'; txt.setAttribute('data-bulle', 'Voir');
        txt.appendChild(el('span', 'tpdf-ia-prop-tete', 'Page ' + (pageParUid(r.uid) + 1) + ' · ' + LIB_OP[o.type] + (o.motif ? ' · ' + o.motif : '')));
        if (o.type === 'inserer') { var d0 = el('div', 'tpdf-diff'); d0.appendChild(el('span', 'tpdf-diff-ctx', (o.position === 'droite' ? 'À droite de « ' : 'Sous « ') + r.texte + ' »')); txt.appendChild(d0); txt.appendChild(diffEl('', o.nouveau));
          var pe = el('span', 'tpdf-ia-place'); txt.appendChild(pe); placesEl.set(o, pe); }
        else txt.appendChild(diffEl(r.texte, MD.apres(o, r.texte)));
        txt.addEventListener('click', function () { liste.querySelectorAll('.tpdf-ia-prop-actif').forEach(function (e) { e.classList.remove('tpdf-ia-prop-actif'); }); ligne.classList.add('tpdf-ia-prop-actif'); montrer(o); });
        ligne.appendChild(cb); ligne.appendChild(txt); liste.appendChild(ligne);
      });
      corps.appendChild(liste);
      var tout = el('button', 'tpdf-b', 'Tout décocher'); tout.type = 'button'; tout.setAttribute('data-bulle', 'Basculer');
      tout.addEventListener('click', function () { var on = !coches.every(function (c) { return c.checked; }); coches.forEach(function (c) { c.checked = on; c.dispatchEvent(new Event('change')); }); });
      if (m.props.length > 1) corps.insertBefore(tout, liste);
      var o = api.ouvrirModale('Modifier avec l\'IA — relecture', corps, [
        { txt: 'Nouvelle consigne', bulle: 'Recommencer', fn: function () { _apercu = null; retirerApercu(); panneauModifier({ consigne: m.consigne, portee: m.portee }); } },
        { txt: 'Appliquer la sélection', bulle: 'Appliquer', plein: true, cle: 'appliquer', fn: async function () {
          var choisies = m.props.filter(function (x, i) { return coches[i].checked; });
          if (!choisies.length) { api.toast('Aucune proposition cochée.', 'info'); return; }
          var r = await appliquer(choisies);
          _apercu = null; retirerApercu(); api.fermerModale();
          api.toast(r.n ? r.n + ' modification' + (r.n > 1 ? 's appliquées' : ' appliquée') + (r.sansEffet ? ' · ' + r.sansEffet + ' sans effet' : '') + (r.chev ? ' · ' + r.chev + ' insertion' + (r.chev > 1 ? 's' : '') + ' à déplacer (chevauche)' : '') + '. Ctrl+Z annule tout le lot.' : 'Rien à appliquer : le texte a changé depuis.', r.n ? 'success' : 'info');
        } }
      ], { cle: 'ia-modifier', ia: true });
      ancrerCote(o);
      var bAppl = o.pied.querySelector('[data-cle="appliquer"]');
      function majBouton() { var k = coches.filter(function (c) { return c.checked; }).length; bAppl.disabled = !k; bAppl.textContent = k ? 'Appliquer la sélection (' + k + ')' : 'Appliquer la sélection'; tout.textContent = coches.every(function (c) { return c.checked; }) ? 'Tout décocher' : 'Tout cocher'; }
      majBouton();
      // Place des insertions cochées, recalculée quand la sélection change
      // (les insertions du lot se réservent leur place les unes après les autres).
      var jeton = 0;
      async function majPlaces() {
        var j0 = ++jeton, ops = m.props.filter(function (x, i) { return x.type === 'inserer' && coches[i].checked; });
        if (!placesEl.size) return;
        var places;
        try { places = await placerTout(ops); } catch (e) { return; }
        if (j0 !== jeton) return;
        m.places = places;
        placesEl.forEach(function (pe, op) {
          var pl = places.get(op); pe.textContent = '';
          if (!pl) return;
          if (pl.chevauche) pe.appendChild(el('span', 'tpdf-ia-chev', 'Chevauche — à déplacer'));
          else pe.appendChild(el('span', 'tpdf-aide', 'Place : ' + LIB_PLACE[pl.mode] + (pl.mode === 'reduit' ? ' (' + String(pl.taille).replace('.', ',') + ' pt)' : '')));
        });
        if (_apercu && _apercu.op && _apercu.op.type === 'inserer') { _apercu.place = places.get(_apercu.op) || null; dessinerApercu(); }
      }
      majPlaces();
      surFermeture(o.fond, function () { _apercu = null; retirerApercu(); });
    }
    EXT.actions.iaModifier = { fn: function () { panneauModifier(); } };
    // Cadre demandé pour la modification puis abandonné (Échap, autre outil) : on oublie.
    EXT.hooks.barre = (EXT.hooks.barre || []).concat(function () { var s = S(); if (s && s._iaZonePour && s.outil !== 'iaZone') s._iaZonePour = null; });
    EXT.panneaux['ia-modifier'] = function () { panneauModifier(); };
  });
})();

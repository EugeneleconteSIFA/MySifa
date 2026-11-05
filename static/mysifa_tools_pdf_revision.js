/*
 * MyTools — éditeur PDF : réviser (menu « Réviser »).
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 *   comparer deux PDF (texte mot à mot, pixels), commentaires en fil sur une
 *   zone (réponses, résolu), liste des remarques exportée en CSV ou PDF,
 *   tampons personnalisés, rechercher et remplacer dans tout le document.
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  /* ── Fonctions pures (tests/test_tools_pdf.js) ────────────────────── */
  function mots(t) { return String(t || '').split(/\s+/).filter(Boolean); }
  // Différences mot à mot (plus longue sous-suite commune).
  // Rend [{t: '=' | '-' | '+', m: [mots]}] ; '-' = seulement dans A, '+' = seulement dans B.
  function diffMots(a, b) {
    var n = a.length, m = b.length, ops = [];
    function pousser(t, w) { var d = ops[ops.length - 1]; if (d && d.t === t) d.m.push(w); else ops.push({ t: t, m: [w] }); }
    // Préfixe et suffixe communs : ramènent le tableau à la zone modifiée.
    var deb = 0; while (deb < n && deb < m && a[deb] === b[deb]) deb++;
    var fa = n, fb = m; while (fa > deb && fb > deb && a[fa - 1] === b[fb - 1]) { fa--; fb--; }
    for (var i0 = 0; i0 < deb; i0++) pousser('=', a[i0]);
    var A = a.slice(deb, fa), B = b.slice(deb, fb), na = A.length, nb = B.length;
    if (na * nb > 4e6) { A.forEach(function (w) { pousser('-', w); }); B.forEach(function (w) { pousser('+', w); }); }
    else {
      var L = new Uint32Array((na + 1) * (nb + 1)), i, j;
      for (i = na - 1; i >= 0; i--) for (j = nb - 1; j >= 0; j--)
        L[i * (nb + 1) + j] = A[i] === B[j] ? L[(i + 1) * (nb + 1) + j + 1] + 1 : Math.max(L[(i + 1) * (nb + 1) + j], L[i * (nb + 1) + j + 1]);
      i = 0; j = 0;
      while (i < na && j < nb) {
        if (A[i] === B[j]) { pousser('=', A[i]); i++; j++; }
        else if (L[(i + 1) * (nb + 1) + j] >= L[i * (nb + 1) + j + 1]) { pousser('-', A[i]); i++; }
        else { pousser('+', B[j]); j++; }
      }
      while (i < na) pousser('-', A[i++]);
      while (j < nb) pousser('+', B[j++]);
    }
    for (var k = fa; k < n; k++) pousser('=', a[k]);
    return ops;
  }
  // Zones de pixels différents : grille de cellules, cellules voisines réunies.
  function zonesDiff(da, db, W, H, seuil, cellule) {
    var c = cellule || 8, gw = Math.ceil(W / c), gh = Math.ceil(H / c), g = new Uint8Array(gw * gh), s2 = (seuil || 60) * 3;
    for (var y = 0; y < H; y++) for (var x = 0; x < W; x++) {
      var i = (y * W + x) * 4;
      if (Math.abs(da[i] - db[i]) + Math.abs(da[i + 1] - db[i + 1]) + Math.abs(da[i + 2] - db[i + 2]) > s2) g[Math.floor(y / c) * gw + Math.floor(x / c)] = 1;
    }
    var vu = new Uint8Array(gw * gh), zones = [];
    for (var k = 0; k < g.length; k++) {
      if (!g[k] || vu[k]) continue;
      var pile = [k], x0 = gw, y0 = gh, x1 = 0, y1 = 0; vu[k] = 1;
      while (pile.length) {
        var q = pile.pop(), qx = q % gw, qy = (q / gw) | 0;
        x0 = Math.min(x0, qx); x1 = Math.max(x1, qx); y0 = Math.min(y0, qy); y1 = Math.max(y1, qy);
        for (var dy = -1; dy <= 1; dy++) for (var dx = -1; dx <= 1; dx++) {
          var nx = qx + dx, ny = qy + dy, r = ny * gw + nx;
          if (nx >= 0 && ny >= 0 && nx < gw && ny < gh && g[r] && !vu[r]) { vu[r] = 1; pile.push(r); }
        }
      }
      zones.push({ x: x0 * c, y: y0 * c, w: Math.min(W, (x1 + 1) * c) - x0 * c, h: Math.min(H, (y1 + 1) * c) - y0 * c });
    }
    return zones;
  }
  function champCsv(v) { v = String(v == null ? '' : v); return /[;"\n\r]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }
  function csv(lignes) { return '﻿' + lignes.map(function (l) { return l.map(champCsv).join(';'); }).join('\r\n'); }

  M._interne = M._interne || {};
  M._interne.revision = { diffMots: diffMots, zonesDiff: zonesDiff, csv: csv, mots: mots };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function bouton(txt, cls, bulle) { var b = el('button', 'tpdf-b' + (cls ? ' ' + cls : ''), txt); b.type = 'button'; if (bulle) b.setAttribute('data-bulle', bulle); return b; }
    function telechargerBlob(blob, nom) { var u = api.urlObjet(blob), a = el('a'); a.href = u; a.download = nom; a.style.display = 'none'; S().el.appendChild(a); a.click(); a.remove(); }

    Object.assign(api.IC, {
      reviser: '<path d="M4 19.5h4l10.5-10.5a2.1 2.1 0 0 0-3-3L5 16.5z"/><path d="M13.5 8l3 3"/>',
      comparer: '<rect x="3" y="4" width="7.5" height="16" rx="1.5"/><rect x="13.5" y="4" width="7.5" height="16" rx="1.5"/><path d="M5.5 9h2.5M16 9h2.5M5.5 13h2.5M16 13h2.5"/>',
      note: '<path d="M4.5 5.5h15v10h-8l-4 3.5v-3.5h-3z"/><path d="M8 9.5h8M8 12.5h5"/>',
      remarques: '<path d="M8 6.5h12M8 12h12M8 17.5h12"/><circle cx="4.5" cy="6.5" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="17.5" r="1"/>',
      remplacer: '<circle cx="10" cy="10" r="5.5"/><path d="M14 14l6 6"/><path d="M7.5 10h5M10.5 8l2 2-2 2"/>'
    });
    api.LIBELLES.note = 'Commentaire';
    api.AIDE_OUTIL.note = 'Cliquer ou tracer la zone commentée, puis écrire dans le panneau.';
    api.BULLES.note = 'Commenter';
    EXT.boutons.push({ groupe: 'outils', html: api.outilBtn('note', 'note', 'Commenter une zone') });
    EXT.menus.reviser = { libelle: 'Réviser', icone: 'reviser', ordre: 2, items: [
      { act: 'comparer', icone: 'comparer', libelle: 'Comparer avec un autre PDF…', bulle: 'Comparer', doc: 1 },
      { act: 'remarques', icone: 'remarques', libelle: 'Commentaires du document…', bulle: 'Commentaires', doc: 1 },
      { act: 'remplacer', icone: 'remplacer', libelle: 'Rechercher et remplacer…', bulle: 'Remplacer', doc: 1 },
      { act: 'formulaire', icone: 'formulaire', libelle: 'Champs du formulaire', bulle: 'Formulaire', doc: 1 }
    ] };

    /* ── Commentaires en fil ──────────────────────────────────────────── */
    function auteur() { return api.nomUtilisateur() || 'Moi'; }
    function maintenant() { var d = new Date(); return api.dateDuJour() + ' ' + ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2); }
    EXT.outils.note = {
      down: function (pt) { return { t: 'note', x: pt.x, y: pt.y, w: 0, h: 0, fil: [], resolu: false }; }
    };
    EXT.types.note = {
      boiteTournante: true,
      tailleDefaut: function () { return [22, 22]; },
      apresCreation: function () {
        api.choisirOutil('select', true);
        requestAnimationFrame(function () { var t = S().props.querySelector('textarea[data-prop="reponse"]'); S().el.classList.add('tpdf-props-ouvert'); if (t) t.focus(); });
      },
      dessiner: function (a, g, z) {
        var cls = 'tpdf-note' + (a.resolu ? ' tpdf-note-resolue' : '');
        if (a.w > 26 || a.h > 26) api.sv('rect', { x: a.x, y: a.y, width: a.w, height: a.h, fill: 'transparent', 'class': cls + ' tpdf-note-zone', 'stroke-width': 1.2 / z }, g);
        var t = 18 / z, bx = a.x, by = a.y;
        api.sv('rect', { x: bx, y: by, width: Math.max(t, 1), height: Math.max(t, 1) * 0.85, rx: 3 / z, 'class': cls + ' tpdf-note-bulle' }, g);
        var n = api.sv('text', { x: bx + t / 2, y: by + t * 0.6, 'font-size': 10 / z, 'text-anchor': 'middle', 'font-family': api.POLICE, 'class': 'tpdf-note-nb' }, g);
        n.textContent = a.fil.length || '+';
      },
      props: function (sec, a) {
        if (!a) return;
        var fil = el('div', 'tpdf-fil');
        a.fil.forEach(function (m, i) {
          var b = el('div', 'tpdf-fil-msg');
          var t = el('div', 'tpdf-fil-tete'); t.appendChild(el('b', null, m.auteur)); t.appendChild(el('span', null, ' · ' + m.date));
          b.appendChild(t); b.appendChild(el('div', 'tpdf-fil-txt', m.texte));
          if (m.auteur === auteur()) {
            var x = el('button', 'tpdf-btn tpdf-btn-mini'); x.type = 'button'; x.setAttribute('data-bulle', 'Retirer'); x.setAttribute('aria-label', 'Retirer ce message');
            x.innerHTML = api.ico('fermer', 12);
            x.addEventListener('click', function () { var av = api.snapshot(); a.fil.splice(i, 1); api.pushHist(av); api.dessinerCalque(); api.rendreProps(); });
            t.appendChild(x);
          }
          fil.appendChild(b);
        });
        if (a.fil.length) sec.appendChild(fil);
        var ta = el('textarea', 'tpdf-champ'); ta.rows = 3; ta.setAttribute('data-prop', 'reponse');
        ta.placeholder = a.fil.length ? 'Répondre…' : 'Commentaire…';
        sec.appendChild(ta);
        var lg = el('div', 'tpdf-ligne');
        var env = bouton(a.fil.length ? 'Répondre' : 'Ajouter', 'tpdf-b-plein', 'Publier');
        function publier() {
          var v = ta.value.trim(); if (!v) { ta.focus(); return; }
          var av = api.snapshot(); a.fil.push({ auteur: auteur(), date: maintenant(), texte: v });
          api.pushHist(av); api.dessinerCalque(); api.rendreBarre(); api.rendreProps();
        }
        env.addEventListener('click', publier);
        ta.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' && (ev.metaKey || ev.ctrlKey)) { ev.preventDefault(); publier(); } });
        var res = bouton(a.resolu ? 'Rouvrir' : 'Marquer résolu', '', a.resolu ? 'Rouvrir' : 'Résolu');
        res.addEventListener('click', function () { var av = api.snapshot(); a.resolu = !a.resolu; api.pushHist(av); api.dessinerCalque(); api.rendreProps(); });
        lg.appendChild(env); lg.appendChild(res);
        sec.appendChild(lg);
      },
      // Exporté en vraie note PDF (icône commentaire) : le fil est dans son contenu.
      exporter: async function (a, c) {
        if (!a.fil.length) return;
        var L = c.L, q = c.P(a.x, a.y), ctx = c.out.context;
        var texte = a.fil.map(function (m) { return m.auteur + ' (' + m.date + ') : ' + m.texte; }).join('\n\n') + (a.resolu ? '\n\n[Résolu]' : '');
        var annot = ctx.obj({
          Type: 'Annot', Subtype: 'Text', Name: 'Comment', Open: false,
          Rect: [q[0], q[1] - 20, q[0] + 20, q[1]],
          Contents: L.PDFHexString.fromText(texte), T: L.PDFHexString.fromText(a.fil[0].auteur),
          C: a.resolu ? [0.18, 0.62, 0.27] : [0.98, 0.75, 0.14], F: 4
        });
        c.pg.node.addAnnot(ctx.register(annot));
      }
    };

    function toutesLesNotes() {
      var l = [];
      S().pages.forEach(function (p, i) { p.annots.forEach(function (a) { if (a.t === 'note' && a.fil.length) l.push({ p: p, i: i, a: a }); }); });
      return l;
    }
    function panneauRemarques() {
      var s = S(), corps = el('div'), filtre = 'toutes';
      var seg = el('div', 'tpdf-seg');
      [['toutes', 'Toutes'], ['ouvertes', 'Ouvertes'], ['resolues', 'Résolues']].forEach(function (x) {
        var b = el('button', 'tpdf-btn' + (x[0] === filtre ? ' tpdf-actif' : ''), x[1]); b.type = 'button'; b.setAttribute('data-bulle', x[1]);
        b.addEventListener('click', function () { filtre = x[0]; seg.querySelectorAll('button').forEach(function (y) { y.classList.toggle('tpdf-actif', y === b); }); liste(); });
        seg.appendChild(b);
      });
      corps.appendChild(seg);
      var zone = el('div', 'tpdf-lc'); corps.appendChild(zone);
      function liste() {
        zone.textContent = '';
        var l = toutesLesNotes().filter(function (n) { return filtre === 'toutes' || (filtre === 'resolues') === !!n.a.resolu; });
        if (!l.length) { zone.appendChild(el('p', 'tpdf-aide', 'Aucun commentaire.')); return; }
        l.forEach(function (n) {
          var b = el('button', 'tpdf-lc-item'); b.type = 'button';
          b.appendChild(el('span', 'tpdf-lc-nom', 'Page ' + (n.i + 1) + ' · ' + n.a.fil[0].auteur));
          b.appendChild(el('span', 'tpdf-lc-type', (n.a.resolu ? 'Résolu' : 'Ouvert') + ' · ' + n.a.fil.length + ' message' + (n.a.fil.length > 1 ? 's' : '')));
          b.appendChild(el('span', 'tpdf-lc-val', n.a.fil[0].texte));
          b.addEventListener('click', function () { api.fermerModale(); api.allerPage(n.i, true); s.annSel = n.a.id; api.choisirOutil('select', true); s.el.classList.add('tpdf-props-ouvert'); });
          zone.appendChild(b);
        });
      }
      liste();
      api.ouvrirModale('Commentaires', corps, [
        { txt: 'Exporter en CSV', fn: exporterCsv },
        { txt: 'Exporter en PDF', fn: exporterPdf },
        { txt: 'Fermer', plein: true, fn: api.fermerModale }
      ], { cle: 'remarques' });
    }
    function lignesRemarques() {
      var l = [['Page', 'Statut', 'Auteur', 'Date', 'Commentaire']];
      toutesLesNotes().forEach(function (n) {
        n.a.fil.forEach(function (m, k) { l.push([n.i + 1, n.a.resolu ? 'Résolu' : 'Ouvert', m.auteur, m.date, (k ? '↳ ' : '') + m.texte]); });
      });
      return l;
    }
    function exporterCsv() {
      var l = lignesRemarques();
      if (l.length < 2) { api.toast('Aucun commentaire à exporter.', 'info'); return; }
      telechargerBlob(new Blob([csv(l)], { type: 'text/csv;charset=utf-8' }), api.nomBase() + '-commentaires.csv');
      api.toast((l.length - 1) + ' message' + (l.length > 2 ? 's exportés.' : ' exporté.'), 'success');
    }
    async function exporterPdf() {
      var l = lignesRemarques();
      if (l.length < 2) { api.toast('Aucun commentaire à exporter.', 'info'); return; }
      var L = await api.pdflib(), d = await L.PDFDocument.create();
      var fN = await d.embedFont(L.StandardFonts.Helvetica), fG = await d.embedFont(L.StandardFonts.HelveticaBold);
      var couper = (M._interne.creation && M._interne.creation.couperLignes) || function (t) { return [t]; };
      var pg = d.addPage([595.28, 841.89]), y = 790;
      function ecrire(t, f, taille, x, largeur, coul) {
        t = api.nettoyerTexte(f, String(t));
        couper(t, largeur, function (u) { return f.widthOfTextAtSize(u, taille); }).forEach(function (ligne) {
          if (y < 50) { pg = d.addPage([595.28, 841.89]); y = 790; }
          pg.drawText(ligne, { x: x, y: y, size: taille, font: f, color: coul || L.rgb(0.1, 0.1, 0.1) }); y -= taille * 1.35;
        });
      }
      ecrire('Commentaires — ' + api.nomBase(), fG, 15, 50, 495);
      ecrire('Exporté le ' + api.dateDuJour() + (api.nomUtilisateur() ? ' par ' + api.nomUtilisateur() : ''), fN, 9, 50, 495, L.rgb(0.4, 0.4, 0.4));
      y -= 8;
      l.slice(1).forEach(function (r) {
        y -= 4;
        ecrire('Page ' + r[0] + ' · ' + r[1] + ' · ' + r[2] + ' · ' + r[3], fG, 9.5, 50, 495);
        ecrire(r[4], fN, 10, 62, 483);
      });
      api.telecharger(await d.save(), api.nomBase() + '-commentaires.pdf');
      api.toast('Liste des commentaires téléchargée.', 'success');
    }
    EXT.actions.remarques = { fn: panneauRemarques };
    EXT.panneaux.remarques = panneauRemarques;

    /* ── Tampons personnalisés ────────────────────────────────────────── */
    var CLE_TAMPONS = 'mytools_pdf_tampons';
    function lirePerso() { try { return JSON.parse(localStorage.getItem(CLE_TAMPONS) || '[]') || []; } catch (e) { return []; } }
    function ecrirePerso(l) { try { localStorage.setItem(CLE_TAMPONS, JSON.stringify(l)); } catch (e) { /* stockage indisponible */ } }
    function chargerPerso() {
      lirePerso().forEach(function (t) {
        if (!t || !t.libelle) return;
        if (api.TAMPONS.indexOf(t.libelle) < 0) api.TAMPONS.push(t.libelle);
        api.COULEUR_TAMPON[t.libelle] = t.couleur || api.COULEURS[4];
      });
    }
    chargerPerso();
    EXT.hooks.props = (EXT.hooks.props || []).concat(function (box) {
      var s = S(), a = api.trouverAnnot(s.annSel);
      if (s.outil !== 'tampon' && !(a && a.t === 'tampon')) return;
      var sec = api.section('Tampons personnalisés'), perso = lirePerso();
      perso.forEach(function (t, i) {
        var lg = el('div', 'tpdf-ligne tpdf-ligne-esp');
        var nom = el('span', null, t.libelle); nom.style.color = t.couleur;
        var x = el('button', 'tpdf-btn tpdf-btn-mini'); x.type = 'button'; x.setAttribute('data-bulle', 'Retirer'); x.setAttribute('aria-label', 'Retirer « ' + t.libelle + ' »');
        x.innerHTML = api.ico('fermer', 12);
        x.addEventListener('click', function () {
          perso.splice(i, 1); ecrirePerso(perso);
          var k = api.TAMPONS.indexOf(t.libelle); if (k >= 0) api.TAMPONS.splice(k, 1);
          api.rendreProps();
        });
        lg.appendChild(nom); lg.appendChild(x); sec.appendChild(lg);
      });
      var lib = el('input', 'tpdf-champ'); lib.type = 'text'; lib.placeholder = 'Ex. Validé production'; lib.maxLength = 30;
      var coul = el('select', 'tpdf-champ');
      api.COULEURS.slice(0, 7).forEach(function (c) { var o = el('option', null, api.NOMS_COULEURS[c] || c); o.value = c; coul.appendChild(o); });
      coul.value = api.COULEURS[4];
      var ajout = bouton('Ajouter', '', 'Ajouter');
      ajout.addEventListener('click', function () {
        var v = lib.value.trim();
        if (!v) { api.toast('Libellé obligatoire.', 'danger'); lib.focus(); return; }
        if (api.TAMPONS.indexOf(v) >= 0) { api.toast('Ce tampon existe déjà.', 'danger'); return; }
        perso.push({ libelle: v, couleur: coul.value }); ecrirePerso(perso); chargerPerso();
        s.style.tampon = v; api.rendreProps();
        api.toast('Tampon « ' + v + ' » ajouté sur ce poste.', 'success');
      });
      var lg2 = el('div', 'tpdf-ligne tpdf-ligne-esp');
      lg2.appendChild(api.champ('Libellé', lib)); lg2.appendChild(api.champ('Couleur', coul));
      sec.appendChild(lg2); sec.appendChild(ajout);
      box.appendChild(sec);
    });

    /* ── Rechercher et remplacer ──────────────────────────────────────── */
    function panneauRemplacer() {
      var corps = el('div');
      if (!EXT.texte) { corps.appendChild(el('p', 'tpdf-aide', 'Module « Modifier le texte » indisponible.')); }
      var q = el('input', 'tpdf-champ'); q.type = 'text';
      var r = el('input', 'tpdf-champ'); r.type = 'text';
      corps.appendChild(api.champ('Rechercher', q)); corps.appendChild(api.champ('Remplacer par', r));
      var c1 = el('label', 'tpdf-case'), i1 = el('input'); i1.type = 'checkbox'; c1.appendChild(i1); c1.appendChild(document.createTextNode(' Respecter les majuscules'));
      var c2 = el('label', 'tpdf-case'), i2 = el('input'); i2.type = 'checkbox'; c2.appendChild(i2); c2.appendChild(document.createTextNode(' Mot entier'));
      corps.appendChild(c1); corps.appendChild(c2);
      corps.appendChild(el('p', 'tpdf-aide tpdf-avert', (EXT.texte && EXT.texte.AVERTISSEMENT) || ''));
      corps.appendChild(el('p', 'tpdf-aide', 'Pages pivotées ou recadrées ignorées. Chaque remplacement reste modifiable et annulable (Ctrl+Z).'));
      var res = el('div', 'tpdf-resultat'); corps.appendChild(res);
      var m = api.ouvrirModale('Rechercher et remplacer', corps, [
        { txt: 'Fermer', fn: api.fermerModale },
        { txt: 'Remplacer partout', plein: true, cle: 'go', fn: async function () {
          if (!q.value) { api.toast('Texte à rechercher obligatoire.', 'danger'); q.focus(); return; }
          var go = m.pied.querySelector('[data-cle="go"]'); go.disabled = true; res.textContent = 'Recherche…'; api.occuper('Remplacement…');
          try {
            var x = await EXT.texte.remplacerPartout(q.value, r.value, { casse: i1.checked, mot: i2.checked });
            res.textContent = x.n ? x.n + ' occurrence' + (x.n > 1 ? 's remplacées' : ' remplacée') + ' dans ' + x.blocs + ' bloc' + (x.blocs > 1 ? 's' : '') + '.' : 'Aucun résultat pour « ' + q.value + ' ».';
            if (x.ignorees) res.textContent += ' ' + x.ignorees + ' page' + (x.ignorees > 1 ? 's ignorées.' : ' ignorée.');
            if (x.n) api.toast(res.textContent, 'success');
          } catch (e) { res.textContent = ''; api.toast(api.msgErreur(e), 'danger'); }
          finally { api.liberer(); go.disabled = false; }
        } }
      ], { cle: 'remplacer' });
      requestAnimationFrame(function () { q.focus(); });
    }
    EXT.actions.remplacer = { fn: panneauRemplacer };
    EXT.panneaux.remplacer = panneauRemplacer;

    /* ── Comparer deux PDF ────────────────────────────────────────────── */
    async function rendreCanvas(pg, scale, R, pc) {
      var vpp = pc ? api.viewportPour(pg, pc, scale, R) : (function () { var v = pg.getViewport({ scale: scale, rotation: R }); return { vp: v, w: v.width, h: v.height }; })();
      var cv = el('canvas'); cv.width = Math.ceil(vpp.w); cv.height = Math.ceil(vpp.h);
      var c = cv.getContext('2d', { willReadFrequently: true }); c.fillStyle = 'white'; c.fillRect(0, 0, cv.width, cv.height);
      await pg.render({ canvasContext: c, viewport: vpp.vp, intent: 'print' }).promise;
      return cv;
    }
    function panneauComparer() {
      var s = S(), corps = el('div', 'tpdf-cmp'), etat = { res: [], i: 0, z: 0, vue: 'cote' };
      var haut = el('div', 'tpdf-ligne tpdf-ligne-esp');
      var fic = el('input', 'tpdf-champ'); fic.type = 'file'; fic.accept = '.pdf,application/pdf';
      haut.appendChild(api.champ('PDF à comparer avec le document ouvert', fic));
      var seg = el('div', 'tpdf-seg');
      [['cote', 'Côte à côte'], ['superpose', 'Superposé'], ['texte', 'Texte']].forEach(function (x) {
        var b = el('button', 'tpdf-btn' + (x[0] === etat.vue ? ' tpdf-actif' : ''), x[1]); b.type = 'button'; b.setAttribute('data-bulle', x[1]);
        b.addEventListener('click', function () { etat.vue = x[0]; seg.querySelectorAll('button').forEach(function (y) { y.classList.toggle('tpdf-actif', y === b); }); afficher(); });
        seg.appendChild(b);
      });
      haut.appendChild(api.champ('Affichage', seg));
      corps.appendChild(haut);
      var nav = el('div', 'tpdf-ligne'), prec = bouton('Écart précédent', '', 'Précédent'), suiv = bouton('Écart suivant', '', 'Suivant'), info = el('span', 'tpdf-aide');
      nav.appendChild(prec); nav.appendChild(suiv); nav.appendChild(info); corps.appendChild(nav);
      var scene = el('div', 'tpdf-cmp-scene'); corps.appendChild(scene);
      var ecarts = [];
      function listerEcarts() {
        ecarts = [];
        etat.res.forEach(function (r, i) {
          r.zones.forEach(function (z, k) { ecarts.push({ i: i, k: k }); });
          if (!r.zones.length && r.texteDiff) ecarts.push({ i: i, k: -1 });
        });
      }
      function aller(sens) {
        if (!ecarts.length) return;
        var cur = ecarts.findIndex(function (e) { return e.i === etat.i && e.k === etat.z; });
        cur = (cur + sens + ecarts.length) % ecarts.length;
        etat.i = ecarts[cur].i; etat.z = ecarts[cur].k; afficher();
      }
      prec.addEventListener('click', function () { aller(-1); });
      suiv.addEventListener('click', function () { aller(1); });
      function cadres(cv, zones, actif) {
        var c = el('canvas'); c.width = cv.width; c.height = cv.height; var x = c.getContext('2d');
        x.drawImage(cv, 0, 0);
        zones.forEach(function (z, k) {
          x.lineWidth = k === actif ? 3 : 1.5; x.strokeStyle = k === actif ? 'rgb(220,38,38)' : 'rgba(220,38,38,.7)';
          x.fillStyle = 'rgba(220,38,38,.12)'; x.fillRect(z.x, z.y, z.w, z.h); x.strokeRect(z.x - 1, z.y - 1, z.w + 2, z.h + 2);
        });
        return c;
      }
      function afficher() {
        scene.textContent = '';
        var r = etat.res[etat.i];
        if (!r) { info.textContent = ''; return; }
        var nbZ = etat.res.reduce(function (t, x) { return t + x.zones.length; }, 0);
        info.textContent = 'Page ' + (etat.i + 1) + ' / ' + etat.res.length + ' · ' + r.zones.length + ' zone' + (r.zones.length > 1 ? 's' : '') + ' différente' + (r.zones.length > 1 ? 's' : '') +
          ' · ' + r.nMots + ' mot' + (r.nMots > 1 ? 's' : '') + ' changé' + (r.nMots > 1 ? 's' : '') + ' — ' + nbZ + ' zones et ' + etat.res.filter(function (x) { return x.texteDiff; }).length + ' page(s) au texte différent au total';
        if (etat.vue === 'texte') {
          var t = el('div', 'tpdf-cmp-texte');
          if (!r.ops.length) t.appendChild(el('p', 'tpdf-aide', 'Pas de texte sur cette page.'));
          r.ops.forEach(function (o) {
            var sp = el(o.t === '-' ? 'del' : o.t === '+' ? 'ins' : 'span', null, o.m.join(' ') + ' ');
            t.appendChild(sp);
          });
          scene.appendChild(t);
          return;
        }
        if (etat.vue === 'cote') {
          var g = el('div', 'tpdf-cmp-cote');
          [['Document ouvert', r.a], ['Comparé', r.b]].forEach(function (x) {
            var f = el('figure'); f.appendChild(el('figcaption', null, x[0]));
            f.appendChild(x[1] ? cadres(x[1], r.zones, etat.z) : el('p', 'tpdf-aide', 'Page absente.'));
            g.appendChild(f);
          });
          scene.appendChild(g);
        } else {
          var c = el('canvas'), base = r.a || r.b; c.width = base.width; c.height = base.height;
          var x2 = c.getContext('2d');
          if (r.a) x2.drawImage(r.a, 0, 0);
          if (r.b) { x2.globalCompositeOperation = 'difference'; x2.drawImage(r.b, 0, 0, c.width, c.height); x2.globalCompositeOperation = 'source-over'; }
          var f2 = el('figure'); f2.appendChild(el('figcaption', null, 'Superposition : ce qui diffère ressort en clair sur fond noir'));
          f2.appendChild(cadres(c, r.zones, etat.z)); scene.appendChild(f2);
        }
        var actif = scene.querySelector('canvas');
        if (actif && r.zones[etat.z]) {
          var z = r.zones[etat.z], k = actif.clientWidth / actif.width;
          scene.scrollTop = Math.max(0, actif.offsetTop + z.y * k - 80);
        }
      }
      fic.addEventListener('change', async function () {
        var f = fic.files && fic.files[0]; if (!f) return;
        scene.textContent = ''; info.textContent = 'Comparaison en cours…'; api.occuper('Comparaison…');
        try {
          var pj = await api.pdfjs(), doc;
          try { doc = await pj.getDocument({ data: new Uint8Array(await f.arrayBuffer()), isEvalSupported: false }).promise; }
          catch (e) { throw new Error(e && e.name === 'PasswordException' ? 'chiffre' : 'invalide'); }
          var n = Math.max(s.pages.length, doc.numPages), res = [];
          for (var i = 0; i < n; i++) {
            info.textContent = 'Page ' + (i + 1) + ' / ' + n + '…';
            var p = s.pages[i], ca = null, cb = null, ta = [], tb = [];
            if (p) {
              var src = s.sources[p.src], pa = await src.pdf.getPage(p.idx + 1), d = api.dims(p), k = 640 / Math.max(d.w, d.h);
              ca = await rendreCanvas(pa, k, d.R, p);
              ta = mots((await api.texteDe(p)).map(function (it) { return it.str; }).join(' '));
            }
            if (i < doc.numPages) {
              var pb = await doc.getPage(i + 1), v1 = pb.getViewport({ scale: 1 });
              var kb = ca ? Math.min(ca.width / v1.width, ca.height / v1.height) : 640 / Math.max(v1.width, v1.height);
              cb = await rendreCanvas(pb, kb, pb.rotate || 0, null);
              tb = mots((await pb.getTextContent()).items.map(function (it) { return it.str || ''; }).join(' '));
            }
            var zones = [];
            if (ca && cb) {
              var W = ca.width, H = ca.height, c2 = el('canvas'); c2.width = W; c2.height = H;
              var x2 = c2.getContext('2d', { willReadFrequently: true }); x2.fillStyle = 'white'; x2.fillRect(0, 0, W, H); x2.drawImage(cb, 0, 0);
              zones = zonesDiff(ca.getContext('2d').getImageData(0, 0, W, H).data, x2.getImageData(0, 0, W, H).data, W, H, 40, 6);
            } else zones = [{ x: 0, y: 0, w: (ca || cb).width, h: (ca || cb).height }];
            var ops = diffMots(ta, tb), nm = ops.reduce(function (t, o) { return t + (o.t !== '=' ? o.m.length : 0); }, 0);
            res.push({ a: ca, b: cb, zones: zones, ops: ops, nMots: nm, texteDiff: nm > 0 });
          }
          try { doc.destroy(); } catch (e) { /* libéré */ }
          etat.res = res; listerEcarts();
          etat.i = ecarts.length ? ecarts[0].i : 0; etat.z = ecarts.length ? ecarts[0].k : 0;
          afficher();
          api.toast(ecarts.length ? ecarts.length + ' écart' + (ecarts.length > 1 ? 's trouvés.' : ' trouvé.') : 'Aucune différence trouvée.', ecarts.length ? 'info' : 'success');
        } catch (e) { info.textContent = ''; api.toast(api.msgErreur(e), 'danger'); }
        finally { api.liberer(); }
      });
      api.ouvrirModale('Comparer deux PDF', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'comparer', large: true });
    }
    EXT.actions.comparer = { fn: panneauComparer };
    EXT.panneaux.comparer = panneauComparer;
  });
})();

/*
 * MyTools — éditeur PDF : formulaires avancés.
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 *   champs créés : calcul (somme, produit, TVA, date du jour), format
 *     (nombre, montant, date) et validation (plage, e-mail) — écrits en
 *     actions JavaScript AcroForm, exécutées par Acrobat, Foxit et la plupart
 *     des lecteurs complets (pas par les aperçus simples des navigateurs) ;
 *   réponses : export et import CSV, collecte de plusieurs PDF remplis en un
 *     CSV, génération d'un PDF par ligne d'un CSV (publipostage).
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  /* ── Fonctions pures (tests) ──────────────────────────────────────── */
  // CSV (séparateur ; ou , détecté sur la première ligne), guillemets gérés.
  function lireCsv(texte) {
    var t = String(texte || '').replace(/^﻿/, ''), sep = (t.split(/\r?\n/)[0].match(/;/g) || []).length >= (t.split(/\r?\n/)[0].match(/,/g) || []).length ? ';' : ',';
    var lignes = [], l = [], c = '', q = false;
    for (var i = 0; i < t.length; i++) {
      var ch = t[i];
      if (q) { if (ch === '"') { if (t[i + 1] === '"') { c += '"'; i++; } else q = false; } else c += ch; continue; }
      if (ch === '"') q = true;
      else if (ch === sep) { l.push(c); c = ''; }
      else if (ch === '\n' || ch === '\r') { if (ch === '\r' && t[i + 1] === '\n') i++; l.push(c); c = ''; if (l.some(function (x) { return x !== ''; })) lignes.push(l); l = []; }
      else c += ch;
    }
    l.push(c); if (l.some(function (x) { return x !== ''; })) lignes.push(l);
    return lignes;
  }
  function noms(liste) { return String(liste || '').split(/[,;]+/).map(function (x) { return x.trim(); }).filter(Boolean); }
  function js(t) { return t; }
  // Scripts AcroForm d'un champ : {C, F, K, V} (chaînes JavaScript) ou absents.
  function scripts(a) {
    var o = {}, f = a.format || 'texte', c = a.calcul || {}, v = a.validation || {};
    function liste(n) { return 'new Array(' + noms(n).map(function (x) { return JSON.stringify(x); }).join(', ') + ')'; }
    if (f === 'nombre') { o.F = 'AFNumber_Format(2, 3, 0, 0, "", false);'; o.K = 'AFNumber_Keystroke(2, 3, 0, 0, "", false);'; }
    if (f === 'montant') { o.F = 'AFNumber_Format(2, 3, 0, 0, " \\u20ac", false);'; o.K = 'AFNumber_Keystroke(2, 3, 0, 0, " \\u20ac", false);'; }
    if (f === 'date') { o.F = 'AFDate_FormatEx("dd/mm/yyyy");'; o.K = 'AFDate_KeystrokeEx("dd/mm/yyyy");'; }
    if (c.type === 'somme' && noms(c.champs).length) o.C = 'AFSimple_Calculate("SUM", ' + liste(c.champs) + ');';
    if (c.type === 'produit' && noms(c.champs).length) o.C = 'AFSimple_Calculate("PRD", ' + liste(c.champs) + ');';
    if (c.type === 'tva' && noms(c.champs).length) o.C = 'event.value = (Number(this.getField(' + JSON.stringify(noms(c.champs)[0]) + ').value) || 0) * ' + (Number(c.taux) || 0) / 100 + ';';
    if (c.type === 'date') o.C = 'if (!event.value) event.value = util.printd("dd/mm/yyyy", new Date());';
    if (v.min !== '' && v.min != null || v.max !== '' && v.max != null) {
      var hasMin = v.min !== '' && v.min != null, hasMax = v.max !== '' && v.max != null;
      o.V = 'AFRange_Validate(' + hasMin + ', ' + (hasMin ? Number(v.min) : 0) + ', ' + hasMax + ', ' + (hasMax ? Number(v.max) : 0) + ');';
    }
    if (v.motif === 'email') o.V = 'if (event.value && !/^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$/.test(event.value)) { app.alert("Adresse e-mail invalide."); event.rc = false; }';
    if (v.motif === 'chiffres') o.V = 'if (event.value && !/^[0-9 ]+$/.test(event.value)) { app.alert("Chiffres seulement."); event.rc = false; }';
    return o;
  }

  M._interne = M._interne || {};
  M._interne.formavance = { lireCsv: lireCsv, scripts: scripts, noms: noms, js: js };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function choix(opts, v) { var s = el('select', 'tpdf-champ'); opts.forEach(function (o) { var x = el('option', null, o[1]); x.value = o[0]; s.appendChild(x); }); if (v != null) s.value = v; return s; }
    function telechargerTexte(t, nom) { var u = api.urlObjet(new Blob([t], { type: 'text/csv;charset=utf-8' })), a = el('a'); a.href = u; a.download = nom; a.style.display = 'none'; S().el.appendChild(a); a.click(); a.remove(); }
    var csv = function (l) { return M._interne.revision ? M._interne.revision.csv(l) : l.map(function (r) { return r.join(';'); }).join('\r\n'); };

    api.IC.formdonnees = '<rect x="4" y="3.5" width="16" height="17" rx="2"/><path d="M8 8h8M8 12h4M14 15.5l2 2 3-3.5"/>';
    var mr = EXT.menus.reviser || (EXT.menus.reviser = { libelle: 'Réviser', icone: 'reviser', ordre: 2, items: [] });
    mr.items.push({ act: 'formdonnees', icone: 'formdonnees', libelle: 'Réponses du formulaire (CSV, publipostage)…', bulle: 'Réponses', doc: 1 });

    /* ── Calcul, format, validation des champs créés ──────────────────── */
    EXT.hooks.propsChamp = (EXT.hooks.propsChamp || []).concat(function (sec, a) {
      if (!a || a.genre === 'case' || a.genre === 'signature') return;
      var s2 = el('div', 'tpdf-section'); s2.appendChild(el('h3', null, 'Calcul et contrôle'));
      var fmt = choix([['texte', 'Texte libre'], ['nombre', 'Nombre (1234,56)'], ['montant', 'Montant (€)'], ['date', 'Date JJ/MM/AAAA']], a.format || 'texte');
      fmt.addEventListener('change', function () { api.majProp('format', fmt.value, a); api.validerProp(); });
      s2.appendChild(api.champ('Format', fmt));
      var c = a.calcul || {};
      var typ = choix([['', 'Aucun'], ['somme', 'Somme de champs'], ['produit', 'Produit de champs'], ['tva', 'TVA d\'un montant HT'], ['date', 'Date du jour']], c.type || '');
      var src = el('input', 'tpdf-champ'); src.type = 'text'; src.placeholder = 'Noms des champs, séparés par des virgules'; src.value = c.champs || '';
      var taux = el('input', 'tpdf-champ'); taux.type = 'number'; taux.step = 'any'; taux.value = c.taux != null ? c.taux : 20;
      var ls = api.champ('Champs sources', src), lt = api.champ('Taux de TVA (%)', taux);
      function majCalc() {
        ls.hidden = !/somme|produit|tva/.test(typ.value); lt.hidden = typ.value !== 'tva';
        api.majProp('calcul', typ.value ? { type: typ.value, champs: src.value, taux: parseFloat(taux.value) || 0 } : null, a); api.validerProp();
      }
      [typ, src, taux].forEach(function (x) { x.addEventListener('change', majCalc); });
      s2.appendChild(api.champ('Calcul', typ)); s2.appendChild(ls); s2.appendChild(lt);
      ls.hidden = !/somme|produit|tva/.test(typ.value); lt.hidden = typ.value !== 'tva';
      var v = a.validation || {};
      var mot = choix([['', 'Aucun'], ['email', 'Adresse e-mail'], ['chiffres', 'Chiffres seulement']], v.motif || '');
      var mn = el('input', 'tpdf-champ'); mn.type = 'number'; mn.step = 'any'; mn.value = v.min != null ? v.min : '';
      var mx = el('input', 'tpdf-champ'); mx.type = 'number'; mx.step = 'any'; mx.value = v.max != null ? v.max : '';
      function majVal() { api.majProp('validation', { motif: mot.value, min: mn.value === '' ? null : parseFloat(mn.value), max: mx.value === '' ? null : parseFloat(mx.value) }, a); api.validerProp(); }
      [mot, mn, mx].forEach(function (x) { x.addEventListener('change', majVal); });
      s2.appendChild(api.champ('Contrôle de saisie', mot));
      var lg = el('div', 'tpdf-ligne tpdf-ligne-esp'); lg.appendChild(api.champ('Minimum', mn)); lg.appendChild(api.champ('Maximum', mx)); s2.appendChild(lg);
      s2.appendChild(el('p', 'tpdf-aide', 'Exécuté par Acrobat, Foxit et les lecteurs PDF complets ; ignoré par les aperçus simples (navigateur, Aperçu macOS).'));
      sec.appendChild(s2);
    });
    EXT.apresChamp = async function (a, champ, c) {
      var o = scripts(a), cles = Object.keys(o);
      if (a.calcul && a.calcul.type === 'date' && champ.setText && !a.defaut) {
        try { champ.setText(api.dateDuJour()); champ.updateAppearances(await c.pol.police('0', {})); } catch (e) { /* date facultative */ }
      }
      if (!cles.length) return;
      var L = c.L, ctx = c.out.context, aa = {};
      cles.forEach(function (k) { aa[k] = { S: 'JavaScript', JS: L.PDFHexString.fromText(o[k]) }; });
      var dict = champ.acroField.dict, deja = ctx.lookup(dict.get(L.PDFName.of('AA')));
      if (deja instanceof L.PDFDict) cles.forEach(function (k) { deja.set(L.PDFName.of(k), ctx.obj(aa[k])); });
      else dict.set(L.PDFName.of('AA'), ctx.obj(aa));
      if (o.C) { c.out.__calculs = c.out.__calculs || []; c.out.__calculs.push(champ.ref); }
    };
    // Ordre de calcul (/CO) : sans lui, Acrobat ne recalcule pas les champs.
    EXT.hooks.export = (EXT.hooks.export || []).concat(function (ctx) {
      var l = ctx.out.__calculs; if (!l || !l.length) return;
      var acro = ctx.out.catalog.getOrCreateAcroForm();
      acro.dict.set(ctx.L.PDFName.of('CO'), ctx.out.context.obj(l));
    });

    /* ── Réponses : CSV, collecte, publipostage ───────────────────────── */
    function champsDuDocument() {
      var s = S(), l = [], vus = {};
      s.pages.forEach(function (p) {
        var src = s.sources[p.src];
        if (!vus[src.id]) { vus[src.id] = 1; src.champs.forEach(function (c) { l.push({ nom: c.nom, valeur: Object.prototype.hasOwnProperty.call(src.valeurs, c.nom) ? src.valeurs[c.nom] : c.valeur, src: src, c: c }); }); }
        p.annots.forEach(function (a) { if (a.t === 'champ') l.push({ nom: a.nom, valeur: a.defaut, cree: a }); });
      });
      return l;
    }
    function valeurTexte(v) { return v === true ? 'Oui' : v === false ? 'Non' : v == null ? '' : String(v); }
    function appliquer(entete, ligne) {
      var n = 0;
      champsDuDocument().forEach(function (f) {
        var i = entete.indexOf(f.nom); if (i < 0) return;
        var v = ligne[i] != null ? ligne[i] : '';
        var bool = /^(oui|vrai|true|x|1|yes)$/i.test(v.trim());
        if (f.cree) f.cree.defaut = f.cree.genre === 'case' ? bool : v;
        else f.src.valeurs[f.nom] = f.c.type === 'case' ? bool : v;
        n++;
      });
      return n;
    }
    function lireFichierTexte(accept) {
      return new Promise(function (ok) {
        var i = el('input'); i.type = 'file'; i.accept = accept || '.csv,text/csv'; i.hidden = true; S().el.appendChild(i);
        i.addEventListener('change', async function () { var f = i.files && i.files[0]; i.remove(); ok(f ? await f.text() : null); });
        i.click();
      });
    }
    async function collecter() {
      var i = el('input'); i.type = 'file'; i.multiple = true; i.accept = '.pdf,application/pdf'; i.hidden = true; S().el.appendChild(i);
      var fichiers = await new Promise(function (ok) { i.addEventListener('change', function () { ok(Array.prototype.slice.call(i.files || [])); i.remove(); }); i.click(); });
      if (!fichiers.length) return;
      var L = await api.pdflib(), lignes = [], nomsCols = [];
      for (var k = 0; k < fichiers.length; k++) {
        var f = fichiers[k], r = { Fichier: f.name };
        try {
          var d = await L.PDFDocument.load(new Uint8Array(await f.arrayBuffer()), { updateMetadata: false });
          d.getForm().getFields().forEach(function (x) {
            var v = '';
            try {
              if (x instanceof L.PDFTextField) v = x.getText() || '';
              else if (x instanceof L.PDFCheckBox) v = x.isChecked() ? 'Oui' : 'Non';
              else if (x instanceof L.PDFDropdown || x instanceof L.PDFOptionList) v = (x.getSelected() || []).join(', ');
              else if (x instanceof L.PDFRadioGroup) v = x.getSelected() || '';
            } catch (e) { v = ''; }
            r[x.getName()] = v; if (nomsCols.indexOf(x.getName()) < 0) nomsCols.push(x.getName());
          });
        } catch (e) { r.Fichier += ' (illisible)'; }
        lignes.push(r);
      }
      var entete = ['Fichier'].concat(nomsCols);
      telechargerTexte(csv([entete].concat(lignes.map(function (r) { return entete.map(function (c) { return r[c] != null ? r[c] : ''; }); }))), 'reponses-' + api.dateDuJour().replace(/\//g, '-') + '.csv');
      api.toast(fichiers.length + ' PDF collecté(s), ' + nomsCols.length + ' champ(s).', 'success');
    }
    async function publipostage(colNom) {
      var t = await lireFichierTexte(); if (!t) return;
      var rows = lireCsv(t); if (rows.length < 2) { api.toast('CSV vide — une ligne d\'en-tête puis une ligne par document.', 'danger'); return; }
      var entete = rows[0].map(function (x) { return x.trim(); }), s = S();
      var sauve = champsDuDocument().map(function (f) { return f.cree ? { a: f.cree, v: f.cree.defaut } : { src: f.src, nom: f.nom, v: f.src.valeurs[f.nom], aVal: Object.prototype.hasOwnProperty.call(f.src.valeurs, f.nom) }; });
      api.occuper('Génération…');
      try {
        for (var i = 1; i < rows.length; i++) {
          if (!appliquer(entete, rows[i])) continue;
          var b = await api.construire(s.pages), ci = entete.indexOf(colNom);
          var nom = ci >= 0 && rows[i][ci] ? String(rows[i][ci]).replace(/[\\/:*?"<>|]+/g, '-').slice(0, 60) : String(i);
          api.telecharger(b, api.nomBase() + '-' + nom + '.pdf');
          await new Promise(function (r) { setTimeout(r, 300); });
        }
        api.toast((rows.length - 1) + ' PDF générés.', 'success');
      } catch (e) { api.toast(api.msgErreur(e), 'danger'); }
      finally {
        sauve.forEach(function (x) { if (x.a) x.a.defaut = x.v; else if (x.aVal) x.src.valeurs[x.nom] = x.v; else delete x.src.valeurs[x.nom]; });
        api.liberer(); api.rendrePage(); api.rendreProps();
      }
    }
    function panneauDonnees() {
      var corps = el('div'), l = champsDuDocument();
      corps.appendChild(el('p', 'tpdf-aide', l.length + ' champ(s) dans le document. La première ligne d\'un CSV porte les noms des champs.'));
      var col = el('select', 'tpdf-champ'); var o0 = el('option', null, 'Numéro de ligne'); o0.value = ''; col.appendChild(o0);
      l.forEach(function (f) { var o = el('option', null, f.nom); o.value = f.nom; col.appendChild(o); });
      function action(t, bulle, fn, aide) {
        var b = el('button', 'tpdf-b', t); b.type = 'button'; b.setAttribute('data-bulle', bulle); b.addEventListener('click', fn);
        var lg = el('div', 'tpdf-ligne tpdf-ligne-esp'); lg.appendChild(b); lg.appendChild(el('span', 'tpdf-aide', aide)); corps.appendChild(lg);
      }
      action('Exporter les réponses', 'Exporter', function () {
        if (!l.length) { api.toast('Aucun champ dans ce document.', 'info'); return; }
        telechargerTexte(csv([l.map(function (f) { return f.nom; }), l.map(function (f) { return valeurTexte(f.valeur); })]), api.nomBase() + '-reponses.csv');
      }, 'Valeurs actuelles des champs, une ligne.');
      action('Importer des réponses', 'Importer', async function () {
        var t = await lireFichierTexte(); if (!t) return;
        var r = lireCsv(t); if (r.length < 2) { api.toast('CSV vide.', 'danger'); return; }
        var n = appliquer(r[0].map(function (x) { return x.trim(); }), r[1]);
        api.rendrePage(); api.rendreProps(); api.dessinerCalque();
        api.toast(n ? n + ' champ(s) rempli(s) depuis la première ligne.' : 'Aucun nom de colonne ne correspond aux champs.', n ? 'success' : 'info');
      }, 'Remplit les champs depuis la première ligne.');
      action('Collecter des PDF remplis', 'Collecter', collecter, 'Plusieurs exemplaires remplis → un CSV, une ligne par PDF.');
      corps.appendChild(api.champ('Nom des fichiers générés', col));
      action('Générer un PDF par ligne', 'Générer', function () { publipostage(col.value); }, 'Publipostage : un CSV, un PDF rempli par ligne.');
      api.ouvrirModale('Réponses du formulaire', corps, [{ txt: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'formdonnees' });
    }
    EXT.actions.formdonnees = { fn: panneauDonnees }; EXT.panneaux.formdonnees = panneauDonnees;
    EXT.formulaire = { champsDuDocument: champsDuDocument, appliquer: appliquer };
  });
})();

/*
 * MyTools — éditeur PDF : protéger (menu « Protéger »).
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 *   mot de passe d'ouverture et restrictions (impression, copie, modification)
 *     — chiffrement AES-256 dans le navigateur par @cantoo/pdf-lib (fork de
 *     pdf-lib qui sait chiffrer), chargé à la demande en module ES ;
 *   nettoyage des métadonnées (informations, XMP, pièces jointes, JavaScript) ;
 *   détection des données sensibles (e-mails, téléphones, IBAN, n° de sécurité
 *     sociale, SIRET) et masquage d'un clic par la vraie suppression du
 *     floutage (pages enregistrées en image).
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  var URL_CHIFFRE = 'https://cdn.jsdelivr.net/npm/@cantoo/pdf-lib@2.11.1/dist/pdf-lib.esm.min.js';

  /* ── Fonctions pures (tests/test_tools_pdf.js) ────────────────────── */
  function chiffres(s) { return String(s).replace(/\D/g, ''); }
  function luhn(n) {
    var s = 0, double = false;
    for (var i = n.length - 1; i >= 0; i--) {
      var c = +n[i]; if (double) { c *= 2; if (c > 9) c -= 9; }
      s += c; double = !double;
    }
    return s % 10 === 0;
  }
  function ibanValide(v) {
    var x = String(v).replace(/\s/g, '').toUpperCase();
    if (!/^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$/.test(x)) return false;
    var r = x.slice(4) + x.slice(0, 4), reste = 0;
    for (var i = 0; i < r.length; i++) {
      var c = r[i], v2 = c >= 'A' ? String(c.charCodeAt(0) - 55) : c;
      for (var k = 0; k < v2.length; k++) reste = (reste * 10 + +v2[k]) % 97;
    }
    return reste === 1;
  }
  function nirValide(v) {
    var x = String(v).replace(/\s/g, '').toUpperCase();
    if (!/^[12]\d{4}(\d{2}|2A|2B)\d{6}(\d{2})?$/.test(x)) return false;
    if (x.length === 13) return true;
    var corps = x.slice(0, 13).replace('2A', '19').replace('2B', '18');
    var cle = +x.slice(13), reste = 0;
    for (var i = 0; i < corps.length; i++) reste = (reste * 10 + +corps[i]) % 97;
    return 97 - reste === cle;
  }
  var MOTIFS = [
    ['iban', 'IBAN', /\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]){11,30}\b/g, ibanValide],
    ['nir', 'N° de sécurité sociale', /\b[12] ?\d{2} ?\d{2} ?(?:\d{2}|2[AB]) ?\d{3} ?\d{3}(?: ?\d{2})?\b/g, nirValide],
    ['siret', 'SIRET', /\b\d{3} ?\d{3} ?\d{3} ?\d{5}\b/g, function (v) { return luhn(chiffres(v)); }],
    ['email', 'E-mail', /[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, null],
    ['tel', 'Téléphone', /(?:\+\d{2,3}[ .-]?(?:\(0\)[ .-]?)?[1-9]|\b0[1-9])(?:[ .-]?\d{2}){4}\b/g, null]
  ];
  // [{type, libelle, debut, fin, valeur}] sans chevauchement (ordre de MOTIFS = priorité).
  function detecterSensibles(texte) {
    var t = String(texte || ''), pris = [], out = [];
    MOTIFS.forEach(function (m) {
      m[2].lastIndex = 0;
      var r;
      while ((r = m[2].exec(t))) {
        var v = r[0].replace(/\s+$/, ''), d = r.index, f = d + v.length;
        if (m[3] && !m[3](v)) continue;
        if (pris.some(function (x) { return d < x[1] && f > x[0]; })) continue;
        pris.push([d, f]); out.push({ type: m[0], libelle: m[1], debut: d, fin: f, valeur: v });
      }
    });
    return out.sort(function (a, b) { return a.debut - b.debut; });
  }
  // Valeur à demi masquée pour la liste (on ne réaffiche pas la donnée en clair).
  function masquerValeur(v) {
    v = String(v);
    if (v.length <= 4) return '••••';
    var garde = Math.max(2, Math.floor(v.length / 5));
    return v.slice(0, garde) + '•'.repeat(Math.max(3, v.length - 2 * garde)) + v.slice(-garde);
  }

  M._interne = M._interne || {};
  M._interne.securite = { detecterSensibles: detecterSensibles, ibanValide: ibanValide, nirValide: nirValide, luhn: luhn, masquerValeur: masquerValeur };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function coche(lib, val) { var l = el('label', 'tpdf-case'), i = el('input'); i.type = 'checkbox'; i.checked = !!val; l.appendChild(i); l.appendChild(document.createTextNode(' ' + lib)); l.input = i; return l; }

    Object.assign(api.IC, {
      proteger: '<path d="M12 3l7.5 3v5.5c0 4.5-3.2 8-7.5 9.5-4.3-1.5-7.5-5-7.5-9.5V6z"/>',
      cadenas: '<rect x="5" y="10.5" width="14" height="10" rx="2"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/><path d="M12 14.5v2.5"/>',
      nettoyer: '<path d="M14.5 3.5l-3 7"/><path d="M6 13h11l1.5 7.5h-14z"/><path d="M10 16.5v4M13.5 16.5v4"/>',
      sensibles: '<path d="M2.5 12s3.5-6.5 9.5-6.5S21.5 12 21.5 12s-3.5 6.5-9.5 6.5S2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.5"/><path d="M4 20L20 4"/>'
    });
    EXT.menus.proteger = { libelle: 'Protéger', icone: 'proteger', ordre: 3, items: [
      { act: 'protection', icone: 'cadenas', libelle: 'Mot de passe et restrictions…', bulle: 'Protéger', doc: 1 },
      { act: 'sensibles', icone: 'sensibles', libelle: 'Masquer les données sensibles…', bulle: 'Masquer', doc: 1 },
      { act: 'nettoyer', icone: 'nettoyer', libelle: 'Nettoyer les métadonnées…', bulle: 'Nettoyer', doc: 1 }
    ] };

    /* ── Mot de passe et restrictions ─────────────────────────────────── */
    var _chiffre = null;
    function libChiffre() {
      if (!_chiffre) _chiffre = import(URL_CHIFFRE).catch(function () { _chiffre = null; throw new Error('bibli'); });
      return _chiffre;
    }
    function aleatoire() {
      var a = new Uint8Array(18); crypto.getRandomValues(a);
      return Array.prototype.map.call(a, function (x) { return ('0' + x.toString(16)).slice(-2); }).join('');
    }
    function panneauProtection() {
      var corps = el('div');
      var mdp = el('input', 'tpdf-champ'), mdp2 = el('input', 'tpdf-champ'), prop = el('input', 'tpdf-champ');
      [mdp, mdp2, prop].forEach(function (x) { x.type = 'password'; x.autocomplete = 'new-password'; });
      corps.appendChild(api.champ('Mot de passe d\'ouverture (facultatif)', mdp));
      corps.appendChild(api.champ('Confirmation', mdp2));
      corps.appendChild(api.champ('Mot de passe pour lever les restrictions (facultatif)', prop));
      var impr = el('select', 'tpdf-champ');
      [['highResolution', 'Autorisée'], ['lowResolution', 'Basse qualité seulement'], ['', 'Interdite']].forEach(function (x) { var o = el('option', null, x[1]); o.value = x[0]; impr.appendChild(o); });
      corps.appendChild(api.champ('Impression', impr));
      var cop = coche('Copier le texte et les images', false), mod = coche('Modifier le document (pages, contenu)', false), ann = coche('Annoter et remplir les formulaires', true);
      corps.appendChild(cop); corps.appendChild(mod); corps.appendChild(ann);
      corps.appendChild(el('p', 'tpdf-aide', 'Chiffrement AES-256 fait sur ce poste. Aucun mot de passe n\'est conservé : le noter. Sans mot de passe propriétaire, les restrictions ne pourront plus être levées. Les restrictions sont respectées par les lecteurs PDF, pas garanties contre un outil qui les ignore.'));
      api.ouvrirModale('Mot de passe et restrictions', corps, [
        { txt: 'Annuler', fn: api.fermerModale },
        { txt: 'Protéger et télécharger', plein: true, fn: async function () {
          if (mdp.value !== mdp2.value) { api.toast('Les deux mots de passe d\'ouverture diffèrent.', 'danger'); mdp2.focus(); return; }
          if (mdp.value && mdp.value.length < 4) { api.toast('Mot de passe trop court — 4 caractères au moins.', 'danger'); mdp.focus(); return; }
          var perm = { printing: impr.value || false, copying: cop.input.checked, modifying: mod.input.checked, documentAssembly: mod.input.checked,
            annotating: ann.input.checked, fillingForms: ann.input.checked, contentAccessibility: true };
          var u = mdp.value, o = prop.value || aleatoire();
          mdp.value = mdp2.value = prop.value = '';
          api.fermerModale(); api.occuper('Chiffrement…');
          try {
            var b = await api.construire(), C = await libChiffre();
            var doc = await C.PDFDocument.load(b, { updateMetadata: false });
            doc.encrypt({ userPassword: u, ownerPassword: o, permissions: perm });
            api.telecharger(await doc.save(), api.nomBase() + '-protege.pdf');
            api.toast(u ? 'PDF protégé par mot de passe téléchargé.' : 'PDF avec restrictions téléchargé.', 'success');
          } catch (e) { api.toast(api.msgErreur(e), 'danger'); }
          finally { api.liberer(); }
        } }
      ], { cle: 'protection' });
      requestAnimationFrame(function () { mdp.focus(); });
    }
    EXT.actions.protection = { fn: panneauProtection };
    EXT.panneaux.protection = panneauProtection;

    /* ── Nettoyage des métadonnées ────────────────────────────────────── */
    function analyser(L, lib) {
      var N = L.PDFName, ctx = lib.context, cat = lib.catalog, r = { infos: [], xmp: false, pj: 0, js: 0, calques: 0, actions: 0 };
      var info = ctx.trailerInfo.Info && ctx.lookup(ctx.trailerInfo.Info);
      if (info instanceof L.PDFDict) info.keys().forEach(function (k) { r.infos.push(String(k).slice(1)); });
      r.xmp = !!cat.get(N.of('Metadata'));
      var noms = ctx.lookup(cat.get(N.of('Names')));
      if (noms instanceof L.PDFDict) { if (noms.get(N.of('EmbeddedFiles'))) r.pj++; if (noms.get(N.of('JavaScript'))) r.js++; }
      if (cat.get(N.of('OpenAction')) || cat.get(N.of('AA'))) r.actions++;
      var oc = ctx.lookup(cat.get(N.of('OCProperties')));
      if (oc instanceof L.PDFDict) { var dd = ctx.lookup(oc.get(N.of('D'))), off = dd instanceof L.PDFDict ? ctx.lookup(dd.get(N.of('OFF'))) : null; if (off instanceof L.PDFArray) r.calques = off.size(); }
      lib.getPages().forEach(function (pg) {
        var an = pg.node.Annots(); if (!an) return;
        for (var i = 0; i < an.size(); i++) {
          var a = ctx.lookup(an.get(i)); if (!(a instanceof L.PDFDict)) continue;
          if (String(a.get(N.of('Subtype'))) === '/FileAttachment') r.pj++;
          var act = ctx.lookup(a.get(N.of('A'))); if (act instanceof L.PDFDict && String(act.get(N.of('S'))) === '/JavaScript') r.js++;
        }
      });
      return r;
    }
    function nettoyer(L, doc) {
      var N = L.PDFName, ctx = doc.context, cat = doc.catalog, n = 0;
      if (ctx.trailerInfo.Info) { ctx.trailerInfo.Info = undefined; n++; }
      ['Metadata', 'Names', 'OpenAction', 'AA', 'PieceInfo', 'SpiderInfo', 'Threads'].forEach(function (k) { if (cat.get(N.of(k))) { cat.delete(N.of(k)); n++; } });
      doc.getPages().forEach(function (pg) {
        ['AA', 'Metadata', 'PieceInfo', 'Thumb'].forEach(function (k) { if (pg.node.get(N.of(k))) { pg.node.delete(N.of(k)); n++; } });
        var an = pg.node.Annots(); if (!an) return;
        for (var i = an.size() - 1; i >= 0; i--) {
          var a = ctx.lookup(an.get(i)); if (!(a instanceof L.PDFDict)) continue;
          if (String(a.get(N.of('Subtype'))) === '/FileAttachment') { an.remove(i); n++; continue; }
          var act = ctx.lookup(a.get(N.of('A')));
          if (act instanceof L.PDFDict && /JavaScript|Launch|SubmitForm|ImportData/.test(String(act.get(N.of('S'))))) { a.delete(N.of('A')); n++; }
          if (a.get(N.of('AA'))) { a.delete(N.of('AA')); n++; }
        }
      });
      return n;
    }
    EXT.hooks.exportApres = (EXT.hooks.exportApres || []).concat(function (ctx) {
      if (!S().nettoyer) return;
      var doc = ctx.final || ctx.out;
      ctx.nettoyes = nettoyer(ctx.L, doc);
      // Le titre choisi pour l'accessibilité reste (Pages › Accessibilité).
      var a = S().a11y; if (a && a.titre) doc.setTitle(a.titre, { showInWindowTitleBar: true });
    });
    async function panneauNettoyer() {
      var s = S(), L = await api.pdflib(), corps = el('div');
      var ids = {}; s.pages.forEach(function (p) { ids[p.src] = 1; });
      var tab = el('div', 'tpdf-lc'), total = { infos: {}, xmp: 0, pj: 0, js: 0, calques: 0, actions: 0 };
      Object.keys(ids).forEach(function (id) {
        var src = s.sources[id], r = analyser(L, src.lib);
        r.infos.forEach(function (k) { total.infos[k] = 1; });
        total.xmp += r.xmp ? 1 : 0; total.pj += r.pj; total.js += r.js; total.calques += r.calques; total.actions += r.actions;
        var it = el('div', 'tpdf-lc-item');
        it.appendChild(el('span', 'tpdf-lc-nom', src.nom));
        it.appendChild(el('span', 'tpdf-lc-val', [r.infos.length ? 'Informations : ' + r.infos.join(', ') : 'Pas d\'informations',
          r.xmp ? 'métadonnées XMP' : '', r.pj ? r.pj + ' pièce(s) jointe(s)' : '', r.js ? r.js + ' script(s)' : '', r.actions ? 'action à l\'ouverture' : '',
          r.calques ? r.calques + ' calque(s) masqué(s)' : ''].filter(Boolean).join(' · ')));
        tab.appendChild(it);
      });
      corps.appendChild(el('p', 'tpdf-aide', 'Trouvé dans les fichiers ouverts :'));
      corps.appendChild(tab);
      var ch = coche('Nettoyer à chaque enregistrement (informations, XMP, pièces jointes, scripts, actions)', !!s.nettoyer);
      ch.input.addEventListener('change', function () { s.nettoyer = ch.input.checked; });
      corps.appendChild(ch);
      corps.appendChild(el('p', 'tpdf-aide', 'Le document produit ne recopie déjà ni les pièces jointes ni les scripts du document : le nettoyage retire en plus les informations (auteur, logiciel, dates), le XMP et les actions restantes des pages.'));
      if (total.calques) corps.appendChild(el('p', 'tpdf-aide tpdf-avert', total.calques + ' calque(s) masqué(s) : leur contenu n\'est pas supprimé et peut redevenir visible dans le PDF produit. Pour l\'effacer, flouter ou masquer la zone (page enregistrée en image).'));
      api.ouvrirModale('Nettoyer les métadonnées', corps, [{ txt: 'Fermer', plein: true, fn: function () {
        api.fermerModale(); if (s.nettoyer) api.toast('Nettoyage actif pour les prochains enregistrements.', 'success');
      } }], { cle: 'nettoyer' });
    }
    EXT.actions.nettoyer = { fn: panneauNettoyer };
    EXT.panneaux.nettoyer = panneauNettoyer;

    /* ── Données sensibles ────────────────────────────────────────────── */
    // Éléments de texte d'une page : ceux de pdf.js, plus les mots de l'OCR s'il y en a.
    async function itemsPage(p) {
      var items = (await api.texteDe(p)).slice();
      if (p.ocr && p.ocr.mots && p.ocr.mots.length) {
        var v = api.dims(p).meta.view;
        p.ocr.mots.forEach(function (m) { items.push({ str: m.t, width: m.w, transform: [m.h, 0, 0, m.h, v[0] + m.x, v[3] - (m.y + m.h * 0.8)], ocr: true }); items.push({ str: ' ', width: 0, transform: [m.h, 0, 0, m.h, v[0] + m.x + m.w, v[3] - (m.y + m.h * 0.8)] }); });
      }
      return items;
    }
    async function analyserSensibles(progres) {
      var s = S(), TX = M._interne.texte, FL = M._interne.flou, trouves = [], sansTexte = 0;
      for (var i = 0; i < s.pages.length; i++) {
        if (progres) progres(i + 1, s.pages.length);
        var p = s.pages[i], d = api.dims(p), items = await itemsPage(p);
        if (!items.some(function (it) { return it.str && it.str.trim(); })) { sansTexte++; continue; }
        TX.grouperItems(items).forEach(function (bl) {
          detecterSensibles(bl.str).forEach(function (r) {
            var b = FL.boiteTexte([bl.h, 0, 0, bl.h, bl.X0, bl.Y], bl.X1 - bl.X0, r.debut, r.fin - r.debut, bl.str.length, d.meta.view, d.R, api.versVue);
            trouves.push({ page: i, p: p, type: r.type, libelle: r.libelle, valeur: r.valeur, boite: b });
          });
        });
      }
      return { trouves: trouves, sansTexte: sansTexte };
    }
    async function panneauSensibles() {
      var s = S(), corps = el('div'), res = el('div', 'tpdf-resultat'), liste = el('div', 'tpdf-lc');
      corps.appendChild(res); corps.appendChild(liste);
      var effet = el('select', 'tpdf-champ');
      [['masquer', 'Masquer (aplat noir)'], ['flou', 'Flouter'], ['pixeliser', 'Pixeliser']].forEach(function (x) { var o = el('option', null, x[1]); o.value = x[0]; effet.appendChild(o); });
      corps.appendChild(api.champ('Effet', effet));
      corps.appendChild(el('p', 'tpdf-aide tpdf-avert', 'Les pages masquées sont enregistrées en image : le texte caché est réellement supprimé, et le reste de la page n\'est plus sélectionnable.'));
      var donnees = [];
      var m = api.ouvrirModale('Masquer les données sensibles', corps, [
        { txt: 'Annuler', fn: api.fermerModale },
        { txt: 'Masquer la sélection', plein: true, cle: 'go', fn: function () {
          var choisis = donnees.filter(function (x) { return x.coche.checked; });
          if (!choisis.length) { api.toast('Rien de coché.', 'info'); return; }
          if (!EXT.types.flou) { api.toast('Module de floutage indisponible.', 'danger'); return; }
          var avant = api.snapshot(), pages = {};
          choisis.forEach(function (x) {
            var b = x.boite, mg = 1;
            x.p.annots.push({ id: api.nid('n'), t: 'flou', effet: effet.value, rayon: 10, bloc: 8, masque: 'noir', x: b.x - mg, y: b.y - mg, w: b.w + 2 * mg, h: b.h + 2 * mg });
            pages[x.page] = 1;
          });
          api.pushHist(avant); api.fermerModale(); api.dessinerCalque(); api.rendreVignettes(); api.rendreBarre();
          var np = Object.keys(pages).length;
          api.toast(choisis.length + ' zone' + (choisis.length > 1 ? 's posées' : ' posée') + ' sur ' + np + ' page' + (np > 1 ? 's' : '') + ' — vérifier, puis enregistrer.', 'success');
        } }
      ], { cle: 'sensibles' });
      var go = m.pied.querySelector('[data-cle="go"]'); go.disabled = true;
      res.textContent = 'Analyse du texte…';
      try {
        var r = await analyserSensibles(function (i, n) { res.textContent = 'Analyse — page ' + i + ' / ' + n + '…'; });
        if (S() !== s) return;
        res.textContent = r.trouves.length ? r.trouves.length + ' donnée' + (r.trouves.length > 1 ? 's trouvées' : ' trouvée') + '. Décocher ce qui doit rester visible.' : 'Aucune donnée sensible trouvée dans le texte.';
        if (r.sansTexte) res.textContent += ' ' + r.sansTexte + ' page' + (r.sansTexte > 1 ? 's' : '') + ' sans texte (scan ?) non analysée' + (r.sansTexte > 1 ? 's' : '') + ' : lancer l\'OCR d\'abord.';
        r.trouves.forEach(function (x) {
          var l = el('label', 'tpdf-lc-item tpdf-case'), c = el('input'); c.type = 'checkbox'; c.checked = true;
          l.appendChild(c);
          l.appendChild(el('span', 'tpdf-lc-nom', 'Page ' + (x.page + 1) + ' · ' + x.libelle));
          l.appendChild(el('span', 'tpdf-lc-val', masquerValeur(x.valeur)));
          liste.appendChild(l); x.coche = c; donnees.push(x);
        });
        go.disabled = !r.trouves.length;
      } catch (e) { res.textContent = ''; api.toast(api.msgErreur(e), 'danger'); }
    }
    EXT.actions.sensibles = { fn: panneauSensibles };
    EXT.panneaux.sensibles = panneauSensibles;
  });
})();

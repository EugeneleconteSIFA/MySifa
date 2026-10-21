/*
 * MyTools — éditeur PDF : formulaires.
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 *   - champs AcroForm existants : contrôles HTML posés sur la page, valeurs
 *     écrites à l'enregistrement (pdf-lib), aplatis ou laissés modifiables ;
 *   - outil « Champ » : création de champs remplissables (texte, multiligne,
 *     case, liste, date, zone de signature), jamais aplatis ;
 *   - document fusionné : le formulaire est reconstruit dans le fichier produit.
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  /* ── Fonctions pures (tests/test_tools_pdf.js) ────────────────────── */
  // « Champ » + premier numéro libre parmi les noms pris.
  function nomUnique(base, pris) {
    var set = {}; (pris || []).forEach(function (n) { set[n] = 1; });
    for (var i = 1; i < 10000; i++) if (!set[base + ' ' + i]) return base + ' ' + i;
    return base + ' ' + Date.now();
  }
  // Rectangle PDF [x1, y1, x2, y2] -> boîte affichée {x, y, w, h} (points).
  function boiteChamp(rect, view, R, versVue) {
    var a = versVue(view, R, rect[0], rect[1]), b = versVue(view, R, rect[2], rect[3]);
    return { x: Math.min(a[0], b[0]), y: Math.min(a[1], b[1]), w: Math.abs(b[0] - a[0]), h: Math.abs(b[1] - a[1]) };
  }
  // Boîte affichée -> options x, y, width, height de pdf-lib.
  function rectPdf(a, P) {
    var p1 = P(a.x, a.y), p2 = P(a.x + a.w, a.y + a.h);
    return { x: Math.min(p1[0], p2[0]), y: Math.min(p1[1], p2[1]), width: Math.abs(p2[0] - p1[0]), height: Math.abs(p2[1] - p1[1]) };
  }
  // Annotation pdf.js (widget) -> genre de contrôle à afficher.
  function genreWidget(an) {
    if (an.fieldType === 'Tx') return an.multiLine ? 'multi' : 'texte';
    if (an.fieldType === 'Btn') return an.checkBox ? 'case' : an.radioButton ? 'radio' : null;
    if (an.fieldType === 'Ch') return an.combo ? 'liste' : 'listeOuverte';
    return null;
  }
  // État d'apparence d'un bouton radio -> libellé de l'option (pdf-lib : index dans /Opt).
  function optionRadio(c, etat) {
    var e = String(etat == null ? '' : etat), o = c && c.options;
    if (o && o.indexOf(e) >= 0) return e;
    if (o && /^\d+$/.test(e) && o[+e] != null) return o[+e];
    return e;
  }
  var TAILLES = { texte: [160, 22], multi: [220, 60], case: [14, 14], liste: [140, 22], date: [100, 22], signature: [180, 50] };
  var GENRES = [['texte', 'Texte une ligne'], ['multi', 'Texte multiligne'], ['case', 'Case à cocher'], ['liste', 'Liste déroulante'], ['date', 'Date'], ['signature', 'Zone de signature']];
  var NOM_GENRE = { texte: 'Texte', multi: 'Texte multiligne', case: 'Case', radio: 'Boutons radio', liste: 'Liste', listeOuverte: 'Liste', date: 'Date', signature: 'Signature' };

  M._interne = M._interne || {};
  M._interne.formulaires = { nomUnique: nomUnique, boiteChamp: boiteChamp, rectPdf: rectPdf, genreWidget: genreWidget, optionRadio: optionRadio, TAILLES: TAILLES };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };

    api.IC.champ = '<rect x="3.5" y="7" width="17" height="10" rx="2"/><path d="M7 10v4M6 10h2M6 14h2"/>';
    api.LIBELLES.champ = 'Champ de formulaire';
    api.AIDE_OUTIL.champ = 'Cliquer-glisser sur la page pour poser le champ.';
    EXT.boutons.push({ groupe: 'outils', html: api.outilBtn('champ', 'champ', 'Créer un champ de formulaire') });
    EXT.boutons.push({ groupe: 'export', html: api.bouton('formulaire', 'formulaire', 'Champs du formulaire', { doc: 1 }) });

    /* ── Lecture des champs d'une source ──────────────────────────────── */
    function lireChamps(L, lib) {
      var out = [], fields = [];
      try { fields = lib.getForm().getFields(); } catch (e) { return out; }
      fields.forEach(function (f) {
        var c = { nom: f.getName(), lectureSeule: false };
        try {
          c.lectureSeule = f.isReadOnly();
          if (f instanceof L.PDFTextField) { c.type = f.isMultiline() ? 'multi' : 'texte'; c.valeur = f.getText() || ''; }
          else if (f instanceof L.PDFCheckBox) { c.type = 'case'; c.valeur = f.isChecked(); }
          else if (f instanceof L.PDFDropdown) { c.type = 'liste'; c.options = f.getOptions(); c.valeur = (f.getSelected() || [])[0] || ''; }
          else if (f instanceof L.PDFOptionList) { c.type = 'listeOuverte'; c.options = f.getOptions(); c.valeur = (f.getSelected() || [])[0] || ''; }
          else if (f instanceof L.PDFRadioGroup) { c.type = 'radio'; c.options = f.getOptions(); c.valeur = f.getSelected() || ''; }
          else return;
        } catch (e) { return; }
        out.push(c);
      });
      return out;
    }
    EXT.hooks.source = (EXT.hooks.source || []).concat(function (src, L, lib) {
      src.champs = lireChamps(L, lib);
      if (!src.champs.length) return;
      // Où vit chaque champ (page, pour « aller au champ »).
      src.ouChamps = {};
      src.pdf.getFieldObjects().then(function (fo) {
        Object.keys(fo || {}).forEach(function (nom) {
          var w = (fo[nom] || []).filter(function (x) { return x.page != null && x.page >= 0; })[0];
          if (w) src.ouChamps[nom] = w.page;
        });
      }).catch(function () { /* positions inconnues : le saut au champ ne marchera pas */ });
      // Les contrôles HTML remplacent l'apparence des champs dans l'aperçu.
      api.pdfjs().then(function (pj) { EXT.modeAnnot = pj.AnnotationMode.ENABLE_FORMS; });
    });

    function valeurCourante(src, nom, defaut) {
      return Object.prototype.hasOwnProperty.call(src.valeurs, nom) ? src.valeurs[nom] : defaut;
    }
    function champParNom(src, nom) {
      for (var i = 0; i < src.champs.length; i++) if (src.champs[i].nom === nom) return src.champs[i];
      return null;
    }

    /* ── Contrôles HTML sur la page ───────────────────────────────────── */
    var _focusChamp = null;
    function rendreControles(p, d, z) {
      var s = S(); if (!s) return;
      s.html.querySelectorAll('.tpdf-fc').forEach(function (e) { e.remove(); });
      var src = s.sources[p.src];
      if (!src || !src.champs.length) return;
      var jeton = s.jeton;
      src.pdf.getPage(p.idx + 1).then(function (pg) { return pg.getAnnotations({ intent: 'display' }); }).then(function (anns) {
        if (S() !== s || s.jeton !== jeton || api.pageCourante() !== p) return;
        anns.forEach(function (an) {
          if (an.annotationType !== 20 || !an.fieldName || an.hidden) return;
          var genre = genreWidget(an); if (!genre) return;
          var c = champParNom(src, an.fieldName);
          var b = boiteChamp(an.rect, d.meta.view, d.R, api.versVue);
          var el = controle(an, genre, c, src, b, z);
          if (!el) return;
          el.classList.add('tpdf-fc');
          el.style.left = (b.x * z) + 'px'; el.style.top = (b.y * z) + 'px';
          el.style.width = Math.max(8, b.w * z) + 'px'; el.style.height = Math.max(8, b.h * z) + 'px';
          el.setAttribute('data-champ', an.fieldName);
          el.setAttribute('data-bulle', an.readOnly || (c && c.lectureSeule) ? 'Lecture seule' : an.fieldName);
          el.setAttribute('aria-label', an.fieldName);
          s.html.appendChild(el);
        });
        if (_focusChamp) {
          var f = s.html.querySelector('[data-champ="' + CSS.escape(_focusChamp) + '"]');
          _focusChamp = null;
          if (f) { var i = f.matches('input,select,textarea') ? f : f.querySelector('input,select,textarea'); if (i) i.focus(); f.classList.add('tpdf-fc-vu'); setTimeout(function () { f.classList.remove('tpdf-fc-vu'); }, 1200); }
        }
      }).catch(function () { /* page sans annotations lisibles */ });
    }

    function controle(an, genre, c, src, b, z) {
      var nom = an.fieldName, ro = !!(an.readOnly || (c && c.lectureSeule));
      var taille = (an.defaultAppearanceData && an.defaultAppearanceData.fontSize) || 0;
      var fs = (taille > 0 ? taille : Math.max(6, Math.min(12, b.h * 0.62))) * z;
      if (an.fieldType !== 'Tx' || !an.multiLine) fs = Math.min(fs, b.h * z * 0.78);
      var el;
      function noter(v) { src.valeurs[nom] = v; majListe(nom); }
      // Lecture seule : pdf.js dessine déjà sa valeur ; on ne pose qu'un cadre.
      if (ro) { el = document.createElement('div'); el.className = 'tpdf-fc-ro'; return el; }
      if (genre === 'texte' || genre === 'multi') {
        el = document.createElement(genre === 'multi' ? 'textarea' : 'input');
        if (genre === 'texte') el.type = 'text';
        el.value = String(valeurCourante(src, nom, c ? c.valeur : (an.fieldValue || '')) || '');
        if (an.maxLen) el.maxLength = an.maxLen;
        if (an.textAlignment === 1) el.style.textAlign = 'center'; else if (an.textAlignment === 2) el.style.textAlign = 'right';
        el.style.fontSize = fs + 'px';
        el.addEventListener('input', function () { noter(el.value); });
      } else if (genre === 'case' || genre === 'radio') {
        el = document.createElement('label');
        el.className = 'tpdf-fc-coche';
        var i = document.createElement('input');
        i.type = genre === 'case' ? 'checkbox' : 'radio';
        if (genre === 'case') {
          var defaut = c ? c.valeur : (an.fieldValue && an.fieldValue !== 'Off');
          i.checked = !!valeurCourante(src, nom, defaut);
          i.addEventListener('change', function () { noter(i.checked); });
        } else {
          i.name = 'tpdf-r-' + src.id + '-' + nom;
          // pdf-lib nomme les états « 0 », « 1 »… et range les libellés dans /Opt.
          var lib = optionRadio(c, an.buttonValue);
          var cur = valeurCourante(src, nom, c ? c.valeur : optionRadio(c, an.fieldValue));
          i.checked = cur != null && cur !== '' && String(cur) === lib;
          i.addEventListener('change', function () { if (i.checked) noter(lib); });
        }
        i.disabled = ro;
        el.appendChild(i);
        if (ro) el.classList.add('tpdf-fc-ro');
        return el;
      } else {
        el = document.createElement('select');
        if (genre === 'listeOuverte') el.size = Math.max(2, Math.floor(b.h / 14));
        var opts = an.options || [], v0 = Array.isArray(an.fieldValue) ? an.fieldValue[0] : an.fieldValue;
        var vide = document.createElement('option'); vide.value = ''; vide.textContent = ''; el.appendChild(vide);
        var initial = '';
        opts.forEach(function (o) {
          var lib = o.displayValue != null ? o.displayValue : o.exportValue;
          var op = document.createElement('option'); op.value = lib; op.textContent = lib; el.appendChild(op);
          if (o.exportValue === v0 || lib === v0) initial = lib;
        });
        el.value = String(valeurCourante(src, nom, c ? c.valeur || initial : initial) || '');
        el.style.fontSize = fs + 'px';
        el.addEventListener('change', function () { noter(el.value); });
      }
      el.disabled = ro;
      if (ro) el.classList.add('tpdf-fc-ro');
      return el;
    }
    EXT.hooks.page = (EXT.hooks.page || []).concat(rendreControles);

    /* ── Panneau : liste des champs ───────────────────────────────────── */
    function sourcesAvecChamps() {
      var s = S(), vus = {}, l = [];
      s.pages.forEach(function (p) {
        var src = s.sources[p.src];
        if (!vus[src.id] && src.champs.length) { vus[src.id] = 1; l.push(src); }
      });
      return l;
    }
    function texteValeur(c, v) {
      if (c.type === 'case') return v ? 'cochée' : 'non cochée';
      return v === '' || v == null ? '—' : String(v);
    }
    function majListe(nom) {
      var s = S(); if (!s) return;
      s.props.querySelectorAll('.tpdf-lc-item[data-nom="' + CSS.escape(nom) + '"] .tpdf-lc-val').forEach(function (e) {
        var src = s.sources[e.getAttribute('data-src')], c = src && champParNom(src, nom);
        if (c) e.textContent = texteValeur(c, valeurCourante(src, nom, c.valeur));
      });
    }
    function allerAuChamp(src, nom) {
      var s = S(), pi = src.ouChamps && src.ouChamps[nom];
      var i = pi == null ? -1 : s.pages.findIndex(function (p) { return p.src === src.id && p.idx === pi; });
      if (i < 0) { api.toast('Champ « ' + nom + ' » introuvable dans les pages du document.', 'info'); return; }
      _focusChamp = nom;
      if (i !== s.cur) api.allerPage(i, true);
      else { var f = s.html.querySelector('[data-champ="' + CSS.escape(nom) + '"]'); if (f) { _focusChamp = null; var x = f.matches('input,select,textarea') ? f : f.querySelector('input'); if (x) x.focus(); } }
      s.el.classList.remove('tpdf-props-ouvert');
    }
    function nbChampsCrees() {
      var n = 0; S().pages.forEach(function (p) { p.annots.forEach(function (a) { if (a.t === 'champ') n++; }); });
      return n;
    }
    EXT.hooks.props = (EXT.hooks.props || []).concat(function (box) {
      var s = S(), srcs = sourcesAvecChamps(), crees = nbChampsCrees();
      if (!srcs.length && !crees) return;
      var sec = api.section('Formulaire');
      sec.classList.add('tpdf-section-form');
      if (srcs.length) {
        var ap = document.createElement('label'); ap.className = 'tpdf-case';
        var ac = document.createElement('input'); ac.type = 'checkbox'; ac.checked = s.aplatir;
        ac.addEventListener('change', function () { s.aplatir = ac.checked; });
        ap.appendChild(ac); ap.appendChild(document.createTextNode(' Aplatir les champs existants à l\'enregistrement'));
        sec.appendChild(ap);
      }
      if (crees) {
        var nc = document.createElement('p'); nc.className = 'tpdf-aide';
        nc.textContent = crees + ' champ' + (crees > 1 ? 's créés restent remplissables' : ' créé reste remplissable') + ' : « Aplatir » ne s\'applique qu\'aux champs existants.';
        sec.appendChild(nc);
      }
      srcs.forEach(function (src) {
        if (srcs.length > 1) { var h = document.createElement('div'); h.className = 'tpdf-lab'; h.textContent = src.nom; sec.appendChild(h); }
        var ul = document.createElement('div'); ul.className = 'tpdf-lc';
        src.champs.forEach(function (c) {
          var it = document.createElement('button'); it.type = 'button'; it.className = 'tpdf-lc-item';
          it.setAttribute('data-nom', c.nom);
          var n = document.createElement('span'); n.className = 'tpdf-lc-nom'; n.textContent = c.nom;
          var t = document.createElement('span'); t.className = 'tpdf-lc-type'; t.textContent = (NOM_GENRE[c.type] || c.type) + (c.lectureSeule ? ' · lecture seule' : '');
          var v = document.createElement('span'); v.className = 'tpdf-lc-val'; v.setAttribute('data-src', src.id);
          v.textContent = texteValeur(c, valeurCourante(src, c.nom, c.valeur));
          it.appendChild(n); it.appendChild(t); it.appendChild(v);
          it.addEventListener('click', function () { allerAuChamp(src, c.nom); });
          ul.appendChild(it);
        });
        sec.appendChild(ul);
      });
      box.appendChild(sec);
    });
    EXT.actions.formulaire = { fn: function () {
      var s = S();
      if (!sourcesAvecChamps().length && !nbChampsCrees()) {
        api.toast('Aucun champ de formulaire dans ce document — l\'outil Champ en crée.', 'info');
        return;
      }
      s.el.classList.add('tpdf-props-ouvert');
      requestAnimationFrame(function () { var f = s.props.querySelector('.tpdf-section-form'); if (f) f.scrollIntoView({ block: 'start' }); });
    } };

    /* ── Export des champs existants ──────────────────────────────────── */
    EXT.docPourExport = async function (src, L) {
      var s = S();
      var modif = Object.keys(src.valeurs).length > 0, aplat = s.aplatir && src.champs.length > 0;
      if (!modif && !aplat) return src.lib;
      var d = await L.PDFDocument.load(src.bytes, { updateMetadata: false });
      var form = d.getForm();
      Object.keys(src.valeurs).forEach(function (nom) {
        var v = src.valeurs[nom], c = champParNom(src, nom);
        if (c && c.lectureSeule) return;
        try {
          var f = form.getField(nom);
          if (f instanceof L.PDFTextField) f.setText(String(v || ''));
          else if (f instanceof L.PDFCheckBox) { if (v) f.check(); else f.uncheck(); }
          else if (f instanceof L.PDFDropdown || f instanceof L.PDFOptionList || f instanceof L.PDFRadioGroup) { if (v) f.select(v); else f.clear(); }
        } catch (e) { /* champ non modifiable : valeur ignorée */ }
      });
      try { form.updateFieldAppearances(); }
      catch (e) {
        // Valeur hors WinAnsi : apparences refaites avec une police Unicode.
        try {
          d.registerFontkit(await api.fontkit());
          form.updateFieldAppearances(await d.embedFont(await api.octetsNoto(false), { subset: false }));
        } catch (e2) { /* apparences d'origine conservées */ }
      }
      if (aplat) {
        try { form.flatten({ updateFieldAppearances: false }); }
        catch (e) { api.toast('Aplatissement impossible sur « ' + src.nom + ' » — champs conservés.', 'info'); }
      }
      return d;
    };

    // Document produit : pdf-lib recopie les widgets des pages, pas le formulaire.
    // On rattache chaque champ au formulaire du fichier produit pour qu'il reste
    // remplissable après fusion, découpage ou réordonnancement.
    // Rattache au formulaire du document chaque champ dont un widget est sur
    // une de ses pages. Réutilisée par le floutage sur son document refait.
    function reconstruire(out, L) {
      var P = L.PDFName, tops = [], vus = {};
      out.getPages().forEach(function (pg) {
        var annots = pg.node.Annots(); if (!annots) return;
        for (var i = 0; i < annots.size(); i++) {
          var ref = annots.get(i), dict = out.context.lookup(ref);
          if (!(dict instanceof L.PDFDict) || String(dict.get(P.of('Subtype'))) !== '/Widget') continue;
          var top = ref, cur = dict, par;
          while ((par = cur.get(P.of('Parent')))) { top = par; cur = out.context.lookup(par); }
          if (!(top instanceof L.PDFRef) || vus[top.toString()]) continue;
          vus[top.toString()] = 1; tops.push(top);
        }
      });
      if (!tops.length) return false;
      var acro = out.catalog.getOrCreateAcroForm(), deja = {};
      try { acro.getAllFields().forEach(function (f) { deja[f[1].toString()] = 1; }); } catch (e) { /* formulaire vide */ }
      tops.forEach(function (t) { if (!deja[t.toString()]) acro.addField(t); });
      if (!acro.dict.get(P.of('DA'))) acro.dict.set(P.of('DA'), L.PDFString.of('/Helv 0 Tf 0 g'));
      acro.dict.set(P.of('NeedAppearances'), L.PDFBool.True);
      return true;
    }
    EXT.reconstruireFormulaire = reconstruire;
    EXT.hooks.export = (EXT.hooks.export || []).concat(async function (ctx) {
      var s = S(), L = ctx.L, out = ctx.out;
      var ids = {}; ctx.pages.forEach(function (p) { ids[p.src] = 1; });
      var srcs = Object.keys(ids).map(function (k) { return s.sources[k]; }).filter(function (x) { return x.champs.length; });
      var crees = ctx.pages.some(function (p) { return p.annots.some(function (a) { return a.t === 'champ'; }); });
      if (crees) ctx.optionsSave = { updateFieldAppearances: false };
      if (s.aplatir || !srcs.length) return;
      if (srcs.length > 1) {
        var vus = {}, doublon = null;
        srcs.forEach(function (src) { src.champs.forEach(function (c) { if (vus[c.nom] && vus[c.nom] !== src.id) doublon = c.nom; vus[c.nom] = src.id; }); });
        if (doublon) api.toast('Deux fichiers fusionnés ont un champ « ' + doublon + ' » : ils partageront leur valeur. Cocher « Aplatir » pour l\'éviter.', 'info');
      }
      reconstruire(out, L);
      ctx.optionsSave = { updateFieldAppearances: false };
    });

    /* ── Outil « Champ » : champs créés ───────────────────────────────── */
    function nomsPris() {
      var s = S(), l = [];
      Object.keys(s.sources).forEach(function (k) { s.sources[k].champs.forEach(function (c) { l.push(c.nom); }); });
      s.pages.forEach(function (p) { p.annots.forEach(function (a) { if (a.t === 'champ' && a.nom) l.push(a.nom); }); });
      return l;
    }
    EXT.outils.champ = {
      down: function (pt) {
        var g = S().style.genreChamp || 'texte';
        return { t: 'champ', genre: g, nom: '', requis: false, defaut: g === 'case' ? false : '',
          options: g === 'liste' ? ['Option 1', 'Option 2'] : [], taille: 0, x: pt.x, y: pt.y, w: 0, h: 0 };
      },
      props: function (sec) { propsChamp(sec, null); }
    };
    EXT.types.champ = {
      tailleDefaut: function (a) { return TAILLES[a.genre] || [160, 22]; },
      apresCreation: function (a) {
        if (a.genre === 'case') { var c = Math.max(10, Math.min(a.w, a.h)); a.w = a.h = c; }
        if (!a.nom) a.nom = nomUnique('Champ', nomsPris().filter(function (n) { return n !== a.nom; }));
      },
      dessiner: function (a, g, z) {
        var sv = api.sv;
        if (a.genre === 'signature') sv('rect', { x: a.x, y: a.y, width: a.w, height: a.h, 'class': 'tpdf-chp-cadre' }, g);
        sv('rect', { x: a.x, y: a.y, width: a.w, height: a.h, rx: a.genre === 'case' ? 1.5 : 2, 'class': 'tpdf-chp' }, g);
        var fs = Math.max(5, Math.min(a.taille || 10, a.h * 0.55));
        var lib = a.genre === 'case' ? (a.defaut ? '✓' : '') :
          a.genre === 'date' ? (a.defaut || 'JJ/MM/AAAA') :
          a.genre === 'liste' ? (a.defaut || (a.options[0] || '')) :
          a.genre === 'signature' ? 'Signature' : (a.defaut || a.nom);
        if (lib) {
          var t = sv('text', { x: a.genre === 'case' ? a.x + a.w / 2 : a.x + 3, y: a.genre === 'multi' || a.genre === 'signature' ? a.y + fs + 2 : a.y + a.h / 2 + fs * 0.35,
            'font-size': a.genre === 'case' ? a.h * 0.8 : fs, 'font-family': api.POLICE, 'text-anchor': a.genre === 'case' ? 'middle' : 'start', 'class': 'tpdf-chp-txt' }, g);
          t.textContent = lib;
        }
        if (a.genre === 'liste') {
          var cx = a.x + a.w - 7, cy = a.y + a.h / 2;
          sv('path', { d: 'M' + (cx - 3) + ' ' + (cy - 1.5) + ' L' + cx + ' ' + (cy + 1.5) + ' L' + (cx + 3) + ' ' + (cy - 1.5), 'class': 'tpdf-chp-fl', 'stroke-width': 1 }, g);
        }
        if (a.genre !== 'case') {
          var tn = sv('text', { x: a.x, y: a.y - 2, 'font-size': Math.max(6, 7), 'font-family': api.POLICE, 'class': 'tpdf-chp-nom' }, g);
          tn.textContent = a.nom + (a.requis ? ' *' : '');
        }
      },
      props: function (sec, a) { propsChamp(sec, a); },
      exporter: async function (a, c) {
        var L = c.L, form = c.out.getForm(), nom = a.nom || 'Champ';
        for (var k = 2; ; k++) { var existe = null; try { existe = form.getField(nom); } catch (e) { existe = null; } if (!existe) break; nom = (a.nom || 'Champ') + ' (' + k + ')'; }
        var r = rectPdf(a, c.P);
        var o = { x: r.x, y: r.y, width: r.width, height: r.height, rotate: c.rot, borderWidth: 0.75,
          borderColor: L.rgb(0.6, 0.64, 0.7), backgroundColor: L.rgb(0.93, 0.96, 1) };
        if (a.genre === 'case') {
          var cb = form.createCheckBox(nom);
          cb.addToPage(c.pg, o);
          if (a.defaut) cb.check();
          if (a.requis) cb.enableRequired();
          return;
        }
        var textes = String(a.defaut || '') + (a.options || []).join('');
        var font = await c.pol.police(textes, {});
        o.font = font;
        if (a.genre === 'liste') {
          var dd = form.createDropdown(nom);
          var opts = (a.options || []).filter(Boolean);
          if (opts.length) dd.setOptions(opts);
          if (a.defaut && opts.indexOf(a.defaut) >= 0) dd.select(a.defaut);
          dd.addToPage(c.pg, o);
          if (a.taille) { try { dd.setFontSize(a.taille); dd.updateAppearances(font); } catch (e) { /* taille auto */ } }
          if (a.requis) dd.enableRequired();
          return;
        }
        if (a.genre === 'signature') {
          c.pg.drawRectangle({ x: r.x - 2, y: r.y - 2, width: r.width + 4, height: r.height + 4, borderColor: L.rgb(0.35, 0.38, 0.42), borderWidth: 0.75 });
          o.backgroundColor = L.rgb(1, 1, 1); o.borderWidth = 0;
        }
        var tf = form.createTextField(nom);
        if (a.genre === 'multi' || a.genre === 'signature') tf.enableMultiline();
        if (a.defaut) tf.setText(String(a.defaut));
        tf.addToPage(c.pg, o);
        if (a.taille) { try { tf.setFontSize(a.taille); tf.updateAppearances(font); } catch (e) { /* taille auto */ } }
        if (a.requis) tf.enableRequired();
        if (a.genre === 'date') {
          try {
            var dict = tf.acroField.dict, ctxp = c.out.context;
            dict.set(L.PDFName.of('TU'), L.PDFHexString.fromText('Date (JJ/MM/AAAA)'));
            dict.set(L.PDFName.of('AA'), ctxp.obj({
              K: { S: 'JavaScript', JS: L.PDFString.of('AFDate_KeystrokeEx("dd/mm/yyyy");') },
              F: { S: 'JavaScript', JS: L.PDFString.of('AFDate_FormatEx("dd/mm/yyyy");') }
            }));
          } catch (e) { /* format de date facultatif */ }
        }
        if (a.genre === 'signature') {
          try { tf.acroField.dict.set(L.PDFName.of('TU'), L.PDFHexString.fromText('Signature')); } catch (e) { /* infobulle facultative */ }
        }
      }
    };

    function propsChamp(sec, a) {
      var s = S();
      var g = document.createElement('select'); g.className = 'tpdf-champ';
      GENRES.forEach(function (x) { var o = document.createElement('option'); o.value = x[0]; o.textContent = x[1]; g.appendChild(o); });
      g.value = a ? a.genre : (s.style.genreChamp || 'texte');
      g.addEventListener('change', function () {
        s.style.genreChamp = g.value;
        if (a) {
          var avant = api.snapshot();
          a.genre = g.value;
          if (a.genre === 'case') { a.defaut = !!a.defaut && a.defaut !== ''; var c = Math.max(10, Math.min(a.w, a.h)); a.w = a.h = c; }
          else { if (typeof a.defaut !== 'string') a.defaut = ''; var t = TAILLES[a.genre]; if (a.w < t[0] / 2 || a.h < 12) { a.w = t[0]; a.h = t[1]; } }
          if (a.genre === 'liste' && !a.options.length) a.options = ['Option 1', 'Option 2'];
          api.pushHist(avant); api.dessinerCalque(); api.rendreBarre(); api.rendreProps();
        }
      });
      sec.appendChild(api.champ('Type de champ', g));
      var note = document.createElement('p'); note.className = 'tpdf-aide';
      note.textContent = 'Les champs créés restent remplissables : « Aplatir » ne s\'applique qu\'aux champs existants.';
      if (!a) { sec.appendChild(note); return; }

      var nm = document.createElement('input'); nm.type = 'text'; nm.className = 'tpdf-champ'; nm.value = a.nom;
      nm.addEventListener('change', function () {
        var v = nm.value.trim();
        var pris = nomsPris(); var idx = pris.indexOf(a.nom); if (idx >= 0) pris.splice(idx, 1);
        if (!v) { api.toast('Nom obligatoire.', 'danger'); nm.value = a.nom; return; }
        if (pris.indexOf(v) >= 0) { api.toast('Nom déjà utilisé — « ' + v + ' » existe dans ce document.', 'danger'); nm.value = a.nom; return; }
        if (/\./.test(v)) { api.toast('Nom invalide — le point est réservé aux champs hiérarchiques.', 'danger'); nm.value = a.nom; return; }
        var avant = api.snapshot(); a.nom = v; api.pushHist(avant); api.dessinerCalque(); api.rendreBarre();
      });
      sec.appendChild(api.champ('Nom', nm));

      var rq = document.createElement('label'); rq.className = 'tpdf-case';
      var rqi = document.createElement('input'); rqi.type = 'checkbox'; rqi.checked = !!a.requis;
      rqi.addEventListener('change', function () { api.majProp('requis', rqi.checked, a); api.validerProp(); });
      rq.appendChild(rqi); rq.appendChild(document.createTextNode(' Obligatoire'));
      sec.appendChild(rq);

      if (a.genre === 'case') {
        var dl = document.createElement('label'); dl.className = 'tpdf-case';
        var di = document.createElement('input'); di.type = 'checkbox'; di.checked = !!a.defaut;
        di.addEventListener('change', function () { api.majProp('defaut', di.checked, a); api.validerProp(); });
        dl.appendChild(di); dl.appendChild(document.createTextNode(' Cochée par défaut'));
        sec.appendChild(dl);
      } else if (a.genre === 'liste') {
        var op = document.createElement('textarea'); op.className = 'tpdf-champ'; op.rows = 4; op.value = a.options.join('\n');
        op.addEventListener('input', function () {
          api.majProp('options', op.value.split('\n').map(function (x) { return x.trim(); }).filter(Boolean), a);
        });
        op.addEventListener('change', function () { api.validerProp(); api.rendreProps(); });
        sec.appendChild(api.champ('Options (une par ligne)', op));
        var ds = document.createElement('select'); ds.className = 'tpdf-champ';
        [''].concat(a.options).forEach(function (x) { var o = document.createElement('option'); o.value = x; o.textContent = x || '—'; ds.appendChild(o); });
        ds.value = a.defaut || '';
        ds.addEventListener('change', function () { api.majProp('defaut', ds.value, a); api.validerProp(); });
        sec.appendChild(api.champ('Valeur par défaut', ds));
      } else if (a.genre !== 'signature') {
        var dv = document.createElement(a.genre === 'multi' ? 'textarea' : 'input'); dv.className = 'tpdf-champ';
        if (a.genre !== 'multi') dv.type = 'text'; else dv.rows = 3;
        if (a.genre === 'date') dv.placeholder = 'JJ/MM/AAAA';
        dv.value = a.defaut || '';
        dv.addEventListener('input', function () { api.majProp('defaut', dv.value, a); });
        dv.addEventListener('change', api.validerProp);
        sec.appendChild(api.champ('Valeur par défaut', dv));
      }
      if (a.genre !== 'case') {
        var tp = document.createElement('input'); tp.type = 'number'; tp.min = 0; tp.max = 72; tp.className = 'tpdf-champ'; tp.value = a.taille || 0;
        tp.addEventListener('input', function () { var v = parseFloat(tp.value); if (v >= 0 && v <= 72) api.majProp('taille', v, a); });
        tp.addEventListener('change', api.validerProp);
        sec.appendChild(api.champ('Taille de police (0 = auto)', tp));
      }
      sec.appendChild(note);
    }
  });
})();

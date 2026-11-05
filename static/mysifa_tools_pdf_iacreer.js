/*
 * MyTools — éditeur PDF : « Créer avec l'IA » (menu IA et écran d'accueil).
 * Chargé par static/mysifa_tools_pdf.js (point d'extension MyToolsPDF.etendre).
 *
 * L'utilisateur décrit le document (au clavier ou en dictée) ; le serveur
 * (/api/tools/pdf/ia/creer, Claude) rend une structure : titre + blocs typés
 * (titre de section, paragraphe, liste, tableau, adresse, signature,
 * séparateur), jamais de HTML. Le PDF est composé ici avec pdf-lib (Noto pour
 * les accents), pagination automatique, numéros de page ; puis il s'ouvre dans
 * l'éditeur comme un document ordinaire.
 */
(function () {
  'use strict';
  var M = window.MyToolsPDF;
  if (!M || !M.etendre) return;

  /* ── Fonctions pures (tests/test_tools_pdf_iacreer.js) ────────────── */
  var FORMATS = { a4: [595.28, 841.89], a4p: [841.89, 595.28], a5: [419.53, 595.28] };

  // Découpe en lignes qui tiennent dans `largeur` ; un mot trop long est coupé.
  function couper(texte, largeur, mes) {
    var out = [];
    String(texte == null ? '' : texte).split('\n').forEach(function (para) {
      var mots = para.split(/\s+/).filter(Boolean), cur = '';
      if (!mots.length) { out.push(''); return; }
      mots.forEach(function (mot) {
        var essai = cur ? cur + ' ' + mot : mot;
        if (mes(essai) <= largeur) { cur = essai; return; }
        if (cur) out.push(cur);
        cur = '';
        while (mes(mot) > largeur && mot.length > 1) {
          var n = mot.length - 1;
          while (n > 1 && mes(mot.slice(0, n)) > largeur) n--;
          out.push(mot.slice(0, n)); mot = mot.slice(n);
        }
        cur = mot;
      });
      out.push(cur);
    });
    return out;
  }

  // Largeur des colonnes d'un tableau : au contenu (bornée), puis ramenée à la largeur utile.
  function largeursColonnes(colonnes, lignes, largeur, mes) {
    var poids = colonnes.map(function (c, i) {
      var m = mes(c, true);
      lignes.slice(0, 200).forEach(function (l) { m = Math.max(m, mes(l[i] || '', false)); });
      return Math.max(30, Math.min(largeur * 0.6, m + 8));
    });
    var t = poids.reduce(function (s, v) { return s + v; }, 0) || 1;
    return poids.map(function (p) { return p / t * largeur; });
  }

  // Structure -> pages d'opérations de dessin (repère : origine en haut à gauche).
  // o = {format, mesure(str, taille, gras), entete: {nom, adresse[], logo: {w, h}|null}|null}
  function mettreEnPage(doc, o) {
    var dim = FORMATS[o.format] || FORMATS.a4, W = dim[0], H = dim[1], petit = o.format === 'a5';
    var marge = petit ? 40 : 56, corps = petit ? 9.5 : 10.5, IL = 1.4, larg = W - 2 * marge, bas = H - marge - 14;
    var pages = [], ops = null, y = 0;
    function mes(s, t, g) { return o.mesure(String(s), t, !!g); }
    function nouvelle() { ops = []; pages.push(ops); y = marge; }
    function place(h) { if (y + h > bas && y > marge + 0.5) nouvelle(); }
    function ligne(str, x, taille, gras, couleur) {
      ops.push({ t: 'texte', x: x, y: y + taille * 0.8, str: str, taille: taille, gras: !!gras, couleur: couleur || 'texte' });
      y += taille * IL;
    }
    function paragraphe(texte, x, l, taille, gras, couleur) {
      couper(texte, l, function (s) { return mes(s, taille, gras); }).forEach(function (s) { place(taille * IL); ligne(s, x, taille, gras, couleur); });
    }
    nouvelle();

    // En-tête de l'entreprise (première page).
    var e = o.entete;
    if (e && (e.nom || e.logo)) {
      var x0 = marge, haut = marge, fond = marge;
      if (e.logo) { var lh = 34, lw = e.logo.w * lh / e.logo.h; if (lw > 140) { lw = 140; lh = e.logo.h * lw / e.logo.w; } ops.push({ t: 'image', x: marge, y: marge, w: lw, h: lh }); x0 = marge + lw + 12; fond = marge + lh; }
      y = haut;
      if (e.nom) ligne(e.nom, x0, petit ? 12 : 14, true, 'texte');
      (e.adresse || []).forEach(function (a) { ligne(a, x0, 8.5, false, 'doux'); });
      y = Math.max(y, fond) + 6;
      ops.push({ t: 'trait', x1: marge, y1: y, x2: W - marge, y2: y, ep: 0.75, couleur: 'trait' });
      y += 18;
    }
    if (doc.titre) { paragraphe(doc.titre, marge, larg, petit ? 15 : 18, true, 'texte'); y += corps * 0.8; }

    (doc.blocs || []).forEach(function (b) {
      var tl;
      switch (b.type) {
        case 'titre':
          tl = petit ? 11.5 : 13;
          if (y > marge + 0.5) y += corps * 0.6;
          place(tl * IL + 2 * corps * IL); // jamais seul en bas de page
          paragraphe(b.texte, marge, larg, tl, true, 'texte'); y += 2;
          break;
        case 'paragraphe':
          paragraphe(b.texte, marge, larg, corps, false); y += corps * 0.6;
          break;
        case 'liste':
          (b.elements || []).forEach(function (el) {
            couper(el, larg - 14, function (s) { return mes(s, corps, false); }).forEach(function (s, i) {
              place(corps * IL);
              if (!i) ops.push({ t: 'texte', x: marge + 3, y: y + corps * 0.8, str: '•', taille: corps, gras: false, couleur: 'texte' });
              ligne(s, marge + 14, corps, false);
            });
            y += corps * 0.2;
          });
          y += corps * 0.5;
          break;
        case 'adresse':
          var la = Math.min(230, larg * 0.48), xa = W - marge - la;
          place((b.elements || []).length * corps * IL);
          (b.elements || []).forEach(function (el) { paragraphe(el, xa, la, corps, false); });
          y += corps * 1.5;
          break;
        case 'signature':
          var ls = larg * 0.42, xs = W - marge - ls;
          var lt = b.texte ? couper(b.texte, ls, function (s) { return mes(s, corps, false); }) : [], ln = [];
          (b.elements || []).forEach(function (el, i) { couper(el, ls, function (s) { return mes(s, corps, !i); }).forEach(function (s) { ln.push([s, !i]); }); });
          y += corps;
          place((lt.length + ln.length) * corps * IL + (lt.length ? corps * 1.2 : 0) + 36); // bloc gardé entier
          lt.forEach(function (s) { ligne(s, xs, corps, false); });
          if (lt.length && ln.length) y += corps * 1.2;
          ln.forEach(function (l) { ligne(l[0], xs, corps, l[1]); });
          y += corps;
          break;
        case 'separateur':
          place(14); y += 6;
          ops.push({ t: 'trait', x1: marge, y1: y, x2: W - marge, y2: y, ep: 0.5, couleur: 'trait' });
          y += 8;
          break;
        case 'tableau':
          tableau(b);
          break;
      }
    });

    function tableau(b) {
      var tc = corps - 1, pad = 4, cols = b.colonnes || [], n = cols.length;
      if (!n) return;
      var ws = largeursColonnes(cols, b.lignes || [], larg, function (s, g) { return mes(s, tc, g); });
      function cellules(row, gras) {
        return row.map(function (c, i) { return couper(c, ws[i] - 2 * pad, function (s) { return mes(s, tc, gras); }); });
      }
      function hauteur(cs) { return Math.max.apply(null, cs.map(function (l) { return l.length; }).concat([1])) * tc * 1.3 + 2 * pad; }
      var tete = cellules(cols, true), hTete = hauteur(tete), maxCorps = bas - marge - hTete;
      function rangee(cs, gras, h) {
        var x = marge;
        if (gras) ops.push({ t: 'rect', x: marge, y: y, w: larg, h: h, couleur: 'fond' });
        cs.forEach(function (lignes, i) {
          ops.push({ t: 'cadre', x: x, y: y, w: ws[i], h: h, couleur: 'trait' });
          lignes.forEach(function (s, k) {
            if ((k + 1) * tc * 1.3 + 2 * pad > h + 0.01) return; // rangée plus haute qu'une page : coupée
            ops.push({ t: 'texte', x: x + pad, y: y + pad + k * tc * 1.3 + tc * 0.85, str: s, taille: tc, gras: gras, couleur: 'texte' });
          });
          x += ws[i];
        });
        y += h;
      }
      y += corps * 0.3;
      place(hTete + tc * 1.3 + 2 * pad); // en-tête jamais seul en bas de page
      rangee(tete, true, hTete);
      (b.lignes || []).forEach(function (row) {
        var cs = cellules(row, false), h = Math.min(hauteur(cs), maxCorps);
        if (y + h > bas) { nouvelle(); rangee(tete, true, hTete); } // en-tête répété
        rangee(cs, false, h);
      });
      y += corps;
    }

    // Numéros de page.
    var N = pages.length;
    pages.forEach(function (p, i) {
      var s = 'Page ' + (i + 1) + ' / ' + N;
      p.push({ t: 'texte', x: (W - mes(s, 8, false)) / 2, y: H - marge / 2 - 2, str: s, taille: 8, gras: false, couleur: 'doux' });
    });
    return { w: W, h: H, pages: pages };
  }
  function nomFichier(titre) {
    var s = String(titre || '').normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^A-Za-z0-9]+/g, '-').replace(/^-+|-+$/g, '').toLowerCase().slice(0, 60);
    return s || 'document';
  }

  M._interne = M._interne || {};
  M._interne.iacreer = { couper: couper, largeursColonnes: largeursColonnes, mettreEnPage: mettreEnPage, nomFichier: nomFichier, FORMATS: FORMATS };

  M.etendre(function (api) {
    var EXT = api.ext;
    var S = function () { return api.etat(); };
    function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
    function option(sel, v, t) { var o = el('option', null, t); o.value = v; sel.appendChild(o); }

    api.IC.iaCreer = api.IC.iaCreer || '<path d="M13.5 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V9z"/><path d="M13.5 3.5V9H19"/><path d="M12 11.5l.9 2.3 2.3.9-2.3.9-.9 2.3-.9-2.3-2.3-.9 2.3-.9z"/>';
    api.IC.micro = '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v2.5M9 20.5h6"/>';
    EXT.boutons.push({ groupe: 'vide', html: '<button type="button" class="tpdf-b ia-btn tpdf-ia-creer" data-act="iaCreer" data-bulle="Créer">' +
      api.ico('iaCreer', 16) + '<span>Créer avec l\'IA</span><span class="ia-badge">IA</span></button>' });

    var COULEURS_PDF = { texte: [0.1, 0.1, 0.12], doux: [0.42, 0.44, 0.48], trait: [0.6, 0.62, 0.66], fond: [0.93, 0.94, 0.96] };
    var _creer = { consigne: '', format: 'a4', ton: 'neutre', langue: 'fr', entete: true, structure: null, bytes: null };
    var _identite = null;
    function identite() {
      if (!_identite) {
        _identite = fetch('/api/tools/pdf/ia/entete', { credentials: 'same-origin' }).then(function (r) { return r.ok ? r.json() : null; })
          .catch(function () { return null; }).then(function (j) {
            var org = String((S() && S().ctx && S().ctx.org) || '').trim();
            return { nom: (j && j.nom) || org, adresse: (j && j.adresse) || [], logo: (j && j.logo) || '' };
          });
      }
      return _identite;
    }

    /* ── Composition du PDF (pdf-lib) ─────────────────────────────────── */
    async function composer(doc, opts) {
      var L = await api.pdflib(), d = await L.PDFDocument.create(), reg, gras, standard = false;
      try {
        d.registerFontkit(await api.fontkit());
        // Polices complètes : le sous-ensemble de pdf-lib perd des glyphes dès que le
        // document contient deux polices (vérifié au rendu), d'où ~600 Ko par document.
        reg = await d.embedFont(await api.octetsNoto(false), { subset: false });
        gras = await d.embedFont(await api.octetsNoto(true), { subset: false });
      } catch (e) {
        // Polices Noto injoignables : Helvetica, caractères hors WinAnsi remplacés.
        reg = await d.embedFont(L.StandardFonts.Helvetica); gras = await d.embedFont(L.StandardFonts.HelveticaBold); standard = true;
      }
      function propre(f, s) { return standard ? api.nettoyerTexte(f, s) : s; }
      var ent = null, img = null;
      if (opts.entete) {
        var id = await identite();
        ent = { nom: id.nom, adresse: id.adresse, logo: null };
        if (id.logo) {
          try {
            var b = new Uint8Array(await (await fetch(id.logo, { credentials: 'same-origin' })).arrayBuffer());
            img = b[0] === 0x89 ? await d.embedPng(b) : await d.embedJpg(b);
            ent.logo = { w: img.width, h: img.height };
          } catch (e) { img = null; }
        }
      }
      var plan = mettreEnPage(doc, { format: opts.format, entete: ent,
        mesure: function (s, t, g) { var f = g ? gras : reg; return f.widthOfTextAtSize(propre(f, s), t); } });
      plan.pages.forEach(function (ops) {
        var pg = d.addPage([plan.w, plan.h]), H = plan.h;
        ops.forEach(function (op) {
          var c = COULEURS_PDF[op.couleur] || COULEURS_PDF.texte, col = L.rgb(c[0], c[1], c[2]);
          if (op.t === 'texte') { var f = op.gras ? gras : reg; if (op.str) pg.drawText(propre(f, op.str), { x: op.x, y: H - op.y, size: op.taille, font: f, color: col }); }
          else if (op.t === 'trait') pg.drawLine({ start: { x: op.x1, y: H - op.y1 }, end: { x: op.x2, y: H - op.y2 }, thickness: op.ep, color: col });
          else if (op.t === 'rect') pg.drawRectangle({ x: op.x, y: H - op.y - op.h, width: op.w, height: op.h, color: col });
          else if (op.t === 'cadre') pg.drawRectangle({ x: op.x, y: H - op.y - op.h, width: op.w, height: op.h, borderColor: col, borderWidth: 0.5 });
          else if (op.t === 'image' && img) pg.drawImage(img, { x: op.x, y: H - op.y - op.h, width: op.w, height: op.h });
        });
      });
      if (doc.titre) d.setTitle(doc.titre);
      return d.save();
    }

    /* ── Dictée (reconnaissance vocale du navigateur) ─────────────────── */
    function micro(champ) {
      var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      var enveloppe = el('span', 'tpdf-bw'), b = el('button', 'tpdf-btn tpdf-micro');
      b.type = 'button'; b.innerHTML = api.ico('micro', 18); b.setAttribute('aria-label', 'Dicter la consigne');
      enveloppe.appendChild(b);
      if (!SR) {
        b.disabled = true;
        enveloppe.setAttribute('data-bulle', 'Dictée indisponible dans ce navigateur — Chrome, Edge ou Safari');
        return { el: enveloppe, dispo: false, arreter: function () {} };
      }
      enveloppe.setAttribute('data-bulle', 'Dicter');
      var rec = null;
      function arreter() { if (rec) { try { rec.stop(); } catch (e) { /* déjà arrêtée */ } } }
      function etat(on) { b.classList.toggle('tpdf-micro-ecoute', on); b.setAttribute('aria-pressed', on ? 'true' : 'false'); enveloppe.setAttribute('data-bulle', on ? 'Arrêter' : 'Dicter'); }
      b.addEventListener('click', function () {
        if (rec) { arreter(); return; }
        if (location.protocol !== 'https:' && !/^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname)) { api.toast('Le micro nécessite une connexion HTTPS.', 'danger'); return; }
        var base = champ.value.replace(/\s+$/, ''), fixe = '';
        rec = new SR(); rec.lang = 'fr-FR'; rec.interimResults = true; rec.continuous = true; rec.maxAlternatives = 1;
        rec.onresult = function (ev) {
          var provisoire = '';
          for (var i = ev.resultIndex; i < ev.results.length; i++) {
            var t = ev.results[i][0].transcript;
            if (ev.results[i].isFinal) fixe += (fixe && !/^\s/.test(t) ? ' ' : '') + t.trim(); else provisoire += t;
          }
          var ajout = (fixe + (provisoire ? (fixe ? ' ' : '') + provisoire.trim() : '')).trim();
          champ.value = base + (base && ajout ? ' ' : '') + ajout;
          champ.scrollTop = champ.scrollHeight;
        };
        rec.onerror = function (ev) { if (ev && ev.error === 'not-allowed') api.toast('Micro refusé par le navigateur.', 'danger'); };
        rec.onend = function () { rec = null; etat(false); };
        try { rec.start(); etat(true); } catch (e) { rec = null; etat(false); api.toast('Dictée impossible : ' + (e.message || 'micro occupé') + '.', 'danger'); }
      });
      return { el: enveloppe, dispo: true, arreter: arreter };
    }

    /* ── Panneau ──────────────────────────────────────────────────────── */
    function occupe(bouton, zone, actif) { bouton.disabled = actif; bouton.classList.toggle('ia-travail', actif); zone.classList.toggle('ia-travail', actif); }
    async function demander(champs) {
      var fd = new FormData();
      Object.keys(champs).forEach(function (k) { fd.append(k, champs[k]); });
      var r = await fetch('/api/tools/pdf/ia/creer', { method: 'POST', body: fd, credentials: 'same-origin' });
      var j = null; try { j = await r.json(); } catch (e) { j = null; }
      if (!r.ok) throw new Error((j && j.detail) || ('Service IA indisponible (' + r.status + ').'));
      return j;
    }

    function panneauCreer() {
      var corps = el('div'), cons = el('textarea', 'tpdf-champ'), fmt = el('select', 'tpdf-champ'), ton = el('select', 'tpdf-champ'), lang = el('select', 'tpdf-champ');
      var go = el('button', 'tpdf-b ia-btn', 'Créer le document'), out = el('div', 'tpdf-ia-sortie');
      go.type = 'button'; go.setAttribute('data-bulle', 'Créer');
      cons.rows = 5; cons.maxLength = 4000; cons.value = _creer.consigne;
      cons.placeholder = 'Ex. Courrier de relance au client X pour la facture 123, ton ferme mais poli · Fiche de consignes sécurité, 1 page, avec un tableau des EPI';
      [['a4', 'A4 portrait'], ['a4p', 'A4 paysage'], ['a5', 'A5 portrait']].forEach(function (x) { option(fmt, x[0], x[1]); });
      [['neutre', 'Neutre'], ['formel', 'Formel'], ['ferme', 'Ferme mais poli'], ['chaleureux', 'Chaleureux'], ['concis', 'Concis']].forEach(function (x) { option(ton, x[0], x[1]); });
      [['fr', 'Français'], ['en', 'Anglais'], ['de', 'Allemand'], ['es', 'Espagnol'], ['it', 'Italien'], ['nl', 'Néerlandais']].forEach(function (x) { option(lang, x[0], x[1]); });
      fmt.value = _creer.format; ton.value = _creer.ton; lang.value = _creer.langue;
      var mic = micro(cons);
      corps.appendChild(el('p', 'ia-texte', 'La consigne est envoyée à l\'assistant IA (Claude) ; aucun document n\'est envoyé.'));
      var lc = el('div', 'tpdf-prop'), ligneCons = el('div', 'tpdf-ia-consigne');
      lc.appendChild(el('span', 'tpdf-lab', 'Ce que doit contenir le document'));
      ligneCons.appendChild(cons); ligneCons.appendChild(mic.el); lc.appendChild(ligneCons);
      corps.appendChild(lc);
      if (mic.dispo) corps.appendChild(el('p', 'tpdf-aide', 'La dictée passe par le service de reconnaissance vocale du navigateur.'));
      var lg = el('div', 'tpdf-ligne tpdf-ligne-esp');
      lg.appendChild(api.champ('Format', fmt)); lg.appendChild(api.champ('Ton', ton)); lg.appendChild(api.champ('Langue', lang));
      corps.appendChild(lg);
      var ent = el('input'); ent.type = 'checkbox'; ent.checked = _creer.entete;
      var lEnt = el('label', 'tpdf-case'); lEnt.appendChild(ent); var tEnt = document.createTextNode(' À l\'en-tête de l\'entreprise'); lEnt.appendChild(tEnt);
      corps.appendChild(lEnt);
      identite().then(function (id) {
        if (!id.nom && !id.logo) { lEnt.hidden = true; ent.checked = false; return; }
        tEnt.textContent = ' À l\'en-tête de l\'entreprise (« ' + (id.nom || 'logo') + ' »)';
      });
      corps.appendChild(go); corps.appendChild(out);
      async function lancer() {
        var v = cons.value.trim();
        if (!v) { cons.focus(); api.toast('Décrire le document voulu.', 'info'); return; }
        mic.arreter();
        Object.assign(_creer, { consigne: v, format: fmt.value, ton: ton.value, langue: lang.value, entete: ent.checked && !lEnt.hidden });
        occupe(go, out, true); out.textContent = 'Rédaction du document…';
        try {
          var st = await demander({ consigne: v, format: fmt.value, ton: ton.value, langue: lang.value, entete: _creer.entete ? '1' : '0' });
          out.textContent = 'Mise en page…';
          _creer.structure = st;
          _creer.bytes = await composer(st, _creer);
          panneauResultat();
        } catch (e) { out.textContent = ''; api.toast(api.msgErreur ? api.msgErreur(e) : (e.message || 'Erreur IA.'), 'danger'); }
        finally { occupe(go, out, false); }
      }
      go.addEventListener('click', lancer);
      cons.addEventListener('keydown', function (ev) { if (ev.key === 'Enter' && (ev.metaKey || ev.ctrlKey)) { ev.preventDefault(); lancer(); } });
      var o = api.ouvrirModale('Créer avec l\'IA', corps, [{ txt: 'Fermer', bulle: 'Fermer', plein: true, fn: api.fermerModale }], { cle: 'ia-creer', ia: true, large: true });
      var obs = new MutationObserver(function () { if (!o.fond.isConnected) { obs.disconnect(); mic.arreter(); } });
      obs.observe(S().el, { childList: true });
      requestAnimationFrame(function () { cons.focus(); });
    }

    async function apercu(zone, bytes) {
      zone.textContent = '';
      var pj = await api.pdfjs(), doc = await pj.getDocument({ data: bytes.slice(), isEvalSupported: false }).promise;
      var n = Math.min(doc.numPages, 12);
      for (var i = 1; i <= n; i++) {
        var pg = await doc.getPage(i), vp0 = pg.getViewport({ scale: 1 }), k = 300 / vp0.width * Math.min(window.devicePixelRatio || 1, 2);
        var vp = pg.getViewport({ scale: k }), cv = el('canvas', 'tpdf-ia-page');
        cv.width = Math.floor(vp.width); cv.height = Math.floor(vp.height);
        await pg.render({ canvasContext: cv.getContext('2d'), viewport: vp, intent: 'print' }).promise;
        zone.appendChild(cv);
      }
      if (doc.numPages > n) zone.appendChild(el('p', 'tpdf-aide', '… et ' + (doc.numPages - n) + ' page(s) de plus.'));
      var total = doc.numPages; doc.destroy();
      return total;
    }

    function panneauResultat() {
      var s = S(), st = _creer.structure, corps = el('div'), vue = el('div', 'tpdf-ia-apercu-doc'), info = el('p', 'tpdf-aide');
      corps.appendChild(info);
      if (st.remarque) corps.appendChild(el('p', 'tpdf-aide tpdf-avert', st.remarque));
      corps.appendChild(vue);
      // Affiner : consigne complémentaire, structure précédente renvoyée au serveur.
      var aff = el('textarea', 'tpdf-champ'), bAff = el('button', 'tpdf-b ia-btn', 'Affiner'), outAff = el('div', 'tpdf-ia-sortie');
      aff.rows = 2; aff.maxLength = 4000; aff.placeholder = 'Ex. Plus court · Ajoute un tableau des factures · Ton plus cordial';
      bAff.type = 'button'; bAff.setAttribute('data-bulle', 'Affiner');
      var micA = micro(aff), lAff = el('div', 'tpdf-ia-consigne'); lAff.appendChild(aff); lAff.appendChild(micA.el);
      var pAff = el('div', 'tpdf-prop'); pAff.appendChild(el('span', 'tpdf-lab', 'Affiner')); pAff.appendChild(lAff);
      corps.appendChild(pAff); corps.appendChild(bAff); corps.appendChild(outAff);
      var rempl = null;
      if (s.pages.length) {
        var r1 = el('label', 'tpdf-case'); rempl = el('input'); rempl.type = 'radio'; rempl.name = 'tpdf-iacreer'; rempl.checked = true;
        r1.appendChild(rempl); r1.appendChild(document.createTextNode(' Remplacer le document ouvert (Ctrl+Z pour revenir)'));
        var r2 = el('label', 'tpdf-case'), aj = el('input'); aj.type = 'radio'; aj.name = 'tpdf-iacreer';
        r2.appendChild(aj); r2.appendChild(document.createTextNode(' Ajouter les pages à la fin'));
        corps.appendChild(r1); corps.appendChild(r2);
      }
      function montrer() {
        vue.textContent = 'Aperçu…';
        apercu(vue, _creer.bytes).then(function (n) { info.textContent = (st.titre ? '« ' + st.titre + ' » · ' : '') + n + ' page' + (n > 1 ? 's' : '') + '. Relire avant usage : les informations absentes de la consigne sont entre crochets.'; })
          .catch(function () { vue.textContent = 'Aperçu indisponible.'; });
      }
      montrer();
      bAff.addEventListener('click', async function () {
        var v = aff.value.trim(); if (!v) { aff.focus(); return; }
        micA.arreter(); occupe(bAff, outAff, true); outAff.textContent = 'Modification du document…';
        try {
          var nst = await demander({ consigne: _creer.consigne, format: _creer.format, ton: _creer.ton, langue: _creer.langue,
            entete: _creer.entete ? '1' : '0', precedent: JSON.stringify(st), affiner: v });
          _creer.structure = st = nst; _creer.bytes = await composer(nst, _creer);
          aff.value = ''; outAff.textContent = '';
          panneauResultat();
        } catch (e) { outAff.textContent = ''; api.toast(api.msgErreur ? api.msgErreur(e) : e.message, 'danger'); }
        finally { occupe(bAff, outAff, false); }
      });
      var o = api.ouvrirModale('Créer avec l\'IA — aperçu', corps, [
        { txt: 'Recommencer', bulle: 'Recommencer', fn: function () { micA.arreter(); panneauCreer(); } },
        { txt: 'Ouvrir dans l\'éditeur', bulle: 'Ouvrir', plein: true, fn: function () { micA.arreter(); ouvrir(!rempl || rempl.checked); } }
      ], { cle: 'ia-creer', ia: true, large: true });
      var obs = new MutationObserver(function () { if (!o.fond.isConnected) { obs.disconnect(); micA.arreter(); } });
      obs.observe(S().el, { childList: true });
    }

    async function ouvrir(remplacer) {
      var s = S();
      try {
        var nom = nomFichier(_creer.structure && _creer.structure.titre);
        var src = await api.ajouterSource(nom + '.pdf', _creer.bytes), avant = api.snapshot(), pages = [];
        for (var i = 0; i < src.metas.length; i++) pages.push(api.nouvellePage(src.id, i));
        if (remplacer || !s.pages.length) { s.pages = pages; s.cur = 0; s.nom = nom; }
        else { s.cur = s.pages.length; s.pages = s.pages.concat(pages); }
        s.sel = {}; s.sel[s.pages[s.cur].uid] = 1; s.ancre = s.pages[s.cur].uid; s.annSel = null;
        api.pushHist(avant);
        api.fermerModale();
        api.toutRendre(); api.notifier();
        api.toast('Document créé : ' + pages.length + ' page' + (pages.length > 1 ? 's' : '') + '.', 'success');
      } catch (e) { api.toast(api.msgErreur ? api.msgErreur(e) : e.message, 'danger'); }
    }

    EXT.actions.iaCreer = { sansDoc: true, fn: function () { panneauCreer(); } };
    EXT.panneaux['ia-creer'] = function () { panneauCreer(); };
    EXT.panneaux['ia-creer'].sansDoc = true; // s'ouvre sans document, adresse comprise
  });
})();

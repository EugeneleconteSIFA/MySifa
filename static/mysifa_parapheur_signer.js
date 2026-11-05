/*
 * Parapheur — noyau de signature, commun à MyTools et à l'Espace SIFA.
 *
 *   ParapheurCore.rendrePages(conteneur, octets, opts)  pages du PDF (pdf.js),
 *       chacune avec un calque `.ppx-calque` où poser des zones en fractions
 *       de la page affichée (rotation comprise, origine en haut à gauche) ;
 *   ParapheurCore.pad(conteneur, opts)   capture d'une signature : tracée,
 *       saisie au clavier ou réutilisée ; rend une image PNG ;
 *   ParapheurCore.vueSignature(racine, ctx)  document + zones du signataire +
 *       fenêtres « Signer » et « Refuser » ;
 *   ParapheurEspace   branchement dans la page de l'Espace SIFA
 *       (app/web/portail_espace_page.py) : carte de la liste, adresse
 *       `?signature=<id>`, lien de l'email `#signer=<jeton>`.
 *
 * Le jeton de signature d'un externe arrive dans le FRAGMENT de l'adresse
 * (jamais envoyé au serveur ni journalisé), est gardé pour l'onglet dans
 * sessionStorage et part dans l'en-tête X-Parapheur-Jeton.
 */
(function () {
  'use strict';
  if (window.ParapheurCore) return;

  var CDN_PDFJS = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.4.168/';
  /* Encres proposées : ce sont des données (elles finissent dans le PDF). */
  var ENCRES = [['rgb(26,26,26)', 'Noir'], ['rgb(28,63,148)', 'Bleu']];
  var POLICE_MANUSCRITE = "'Segoe Script','Bradley Hand','Brush Script MT','Lucida Handwriting',cursive";
  var CLE_EDITEUR = 'mytools_pdf_signature';
  var LIB_ZONE = { signature: 'Signature', paraphe: 'Paraphe', date: 'Date', nom: 'Nom' };

  var IC = {
    signer: '<path d="M3.5 16.5c2.8 0 3.8-9 6-9s-.2 8.5 2 8.5c1.6 0 2.2-3 3.6-3 1.2 0 .9 2.2 2.4 2.2 1 0 1.6-.8 3-1.6"/><path d="M3.5 20h17"/>',
    refuser: '<circle cx="12" cy="12" r="8.5"/><path d="M6 6l12 12"/>',
    fermer: '<path d="M6 6l12 12M18 6L6 18"/>',
    suivant: '<path d="M12 5v14"/><path d="M6 13l6 6 6-6"/>',
    effacer: '<path d="M4 20h16"/><path d="M14.5 4.5l5 5-8.5 8.5H6v-5z"/>',
    doc: '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/><path d="M8.5 16.5c1.4 0 1.9-3.5 3-3.5s-.1 3.3 1 3.3c.8 0 1.1-1.2 1.8-1.2.6 0 .5.9 1.2.9"/>',
    telecharger: '<path d="M12 4v10.5"/><path d="M7.5 10.5L12 15l4.5-4.5"/><path d="M5 19.5h14"/>',
    lien: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>'
  };
  function svg(n, t) {
    return '<svg width="' + (t || 16) + '" height="' + (t || 16) + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (IC[n] || '') + '</svg>';
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; });
  }
  function dateFr(s) { if (!s) return ''; var p = String(s).slice(0, 10).split('-'); return p.length === 3 ? p[2] + '/' + p[1] + '/' + p[0] : String(s); }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }
  function initiales(nom) {
    return String(nom || '').split(/[\s-]+/).filter(Boolean).map(function (m) { return m[0].toUpperCase(); }).join('').slice(0, 4) || '';
  }

  /* ── pdf.js, chargé à la demande ───────────────────────────────────── */
  var _pdfjs = null;
  function pdfjs() {
    if (!_pdfjs) {
      _pdfjs = import(CDN_PDFJS + 'pdf.min.mjs').then(function (m) {
        m.GlobalWorkerOptions.workerSrc = CDN_PDFJS + 'pdf.worker.min.mjs';
        return m;
      }, function () { _pdfjs = null; throw new Error('Lecteur PDF indisponible — vérifier la connexion.'); });
    }
    return _pdfjs;
  }

  // Rend chaque page dans `conteneur`. Rend [{num, w, h, el, calque}] (w, h en
  // points de la page affichée).
  async function rendrePages(conteneur, octets, opts) {
    opts = opts || {};
    var pj = await pdfjs();
    var doc = await pj.getDocument({ data: octets.slice(0) }).promise;
    var largeur = Math.max(280, (opts.largeur || conteneur.clientWidth || 800) - 4);
    var dpr = Math.min(window.devicePixelRatio || 1, 2);
    var pages = [];
    conteneur.innerHTML = '';
    for (var i = 1; i <= doc.numPages; i++) {
      var page = await doc.getPage(i);
      var vp1 = page.getViewport({ scale: 1 });
      var k = Math.min(opts.echelleMax || 1.5, largeur / vp1.width);
      var vp = page.getViewport({ scale: k * dpr });
      var bloc = el('div', 'ppx-page');
      bloc.style.width = Math.round(vp1.width * k) + 'px';
      bloc.style.height = Math.round(vp1.height * k) + 'px';
      bloc.setAttribute('data-page', String(i));
      var cv = el('canvas', 'ppx-page-cv');
      cv.width = Math.round(vp.width); cv.height = Math.round(vp.height);
      var calque = el('div', 'ppx-calque');
      var num = el('div', 'ppx-page-num'); num.textContent = 'Page ' + i + ' / ' + doc.numPages;
      bloc.appendChild(cv); bloc.appendChild(calque); bloc.appendChild(num);
      conteneur.appendChild(bloc);
      await page.render({ canvasContext: cv.getContext('2d'), viewport: vp }).promise;
      pages.push({ num: i, w: vp1.width, h: vp1.height, el: bloc, calque: calque });
    }
    return pages;
  }

  /* ── Image PNG d'une signature ─────────────────────────────────────── */
  // Recadre un canvas sur son tracé (boîte bx en pixels) et rend un data URL.
  function recadrer(cv, bx) {
    var x0 = Math.max(0, Math.floor(bx[0])), y0 = Math.max(0, Math.floor(bx[1]));
    var w = Math.min(cv.width, Math.ceil(bx[2])) - x0, h = Math.min(cv.height, Math.ceil(bx[3])) - y0;
    if (w < 4 || h < 4) return null;
    var c2 = document.createElement('canvas'); c2.width = w; c2.height = h;
    c2.getContext('2d').drawImage(cv, x0, y0, w, h, 0, 0, w, h);
    return c2.toDataURL('image/png');
  }
  function texteEnPng(texte, encre, taille) {
    texte = String(texte || '').trim();
    if (!texte) return null;
    var t = taille || 64;
    var c = document.createElement('canvas'), g = c.getContext('2d');
    g.font = 'italic ' + t + 'px ' + POLICE_MANUSCRITE;
    var w = Math.ceil(g.measureText(texte).width) + t;
    c.width = Math.min(w, 2400); c.height = Math.round(t * 1.6);
    g = c.getContext('2d');
    g.font = 'italic ' + t + 'px ' + POLICE_MANUSCRITE;
    g.fillStyle = encre || ENCRES[0][0];
    g.textBaseline = 'middle';
    g.fillText(texte, t / 2, c.height / 2);
    return c.toDataURL('image/png');
  }

  /* ── Capture d'une signature ───────────────────────────────────────── */
  // opts : {nom, reutilisables: [dataUrl], petit (paraphe), titre}
  // Rend {lire(): {png, mode} | null}
  function pad(conteneur, opts) {
    opts = opts || {};
    var reut = (opts.reutilisables || []).filter(Boolean);
    var modes = [['dessin', 'Tracer'], ['texte', 'Saisir']];
    if (reut.length) modes.push(['reutilise', 'Réutiliser']);
    var etat = { mode: opts.petit ? 'texte' : 'dessin', encre: ENCRES[0][0], vide: true, bx: null, choix: 0 };
    var racine = el('div', 'ppx-pad' + (opts.petit ? ' ppx-pad-petit' : ''));
    var onglets = el('div', 'ppx-onglets');
    modes.forEach(function (m) {
      var b = el('button', 'ppx-onglet', esc(m[1])); b.type = 'button'; b.setAttribute('data-mode', m[0]);
      b.setAttribute('data-bulle', m[1]);
      b.addEventListener('click', function () { etat.mode = m[0]; maj(); });
      onglets.appendChild(b);
    });
    var corps = el('div', 'ppx-pad-corps');
    // Tracé
    var zoneDessin = el('div', 'ppx-pad-dessin');
    var cv = el('canvas', 'ppx-pad-cv');
    var outils = el('div', 'ppx-pad-outils');
    ENCRES.forEach(function (e, i) {
      var b = el('button', 'ppx-encre' + (i ? '' : ' actif')); b.type = 'button';
      b.style.background = e[0]; b.setAttribute('aria-label', 'Encre ' + e[1].toLowerCase()); b.setAttribute('data-bulle', e[1]);
      b.addEventListener('click', function () {
        etat.encre = e[0];
        outils.querySelectorAll('.ppx-encre').forEach(function (x) { x.classList.toggle('actif', x === b); });
        if (etat.mode === 'texte') apercu();
      });
      outils.appendChild(b);
    });
    var bEff = el('button', 'ppx-btn ppx-btn-sm', svg('effacer', 14) + 'Effacer'); bEff.type = 'button'; bEff.setAttribute('data-bulle', 'Effacer');
    bEff.addEventListener('click', function () { effacer(); });
    outils.appendChild(bEff);
    zoneDessin.appendChild(cv);
    // Saisie
    var zoneTexte = el('div', 'ppx-pad-texte');
    var inp = el('input', 'ppx-champ'); inp.type = 'text'; inp.maxLength = 80;
    inp.value = opts.petit ? initiales(opts.nom) : (opts.nom || '');
    inp.setAttribute('aria-label', opts.petit ? 'Initiales' : 'Nom');
    var ap = el('div', 'ppx-pad-apercu');
    zoneTexte.appendChild(inp); zoneTexte.appendChild(ap);
    inp.addEventListener('input', apercu);
    // Réutiliser
    var zoneReut = el('div', 'ppx-pad-reut');
    reut.forEach(function (u, i) {
      var b = el('button', 'ppx-reut' + (i ? '' : ' actif')); b.type = 'button'; b.setAttribute('data-bulle', 'Choisir');
      var im = el('img'); im.src = u; im.alt = 'Signature enregistrée'; b.appendChild(im);
      b.addEventListener('click', function () { etat.choix = i; zoneReut.querySelectorAll('.ppx-reut').forEach(function (x) { x.classList.toggle('actif', x === b); }); });
      zoneReut.appendChild(b);
    });
    corps.appendChild(zoneDessin); corps.appendChild(zoneTexte); corps.appendChild(zoneReut);
    if (opts.titre) racine.appendChild(el('div', 'ppx-pad-titre', esc(opts.titre)));
    racine.appendChild(onglets); racine.appendChild(corps); racine.appendChild(outils);
    conteneur.appendChild(racine);

    var g = cv.getContext('2d'), dpr = Math.min(window.devicePixelRatio || 1, 2), der = null;
    function taille() {
      var w = cv.clientWidth, h = cv.clientHeight;
      if (w && h && (cv.width !== Math.round(w * dpr))) { cv.width = Math.round(w * dpr); cv.height = Math.round(h * dpr); effacer(); }
    }
    function effacer() { g.clearRect(0, 0, cv.width, cv.height); etat.vide = true; etat.bx = null; }
    function pos(ev) { var r = cv.getBoundingClientRect(); return [(ev.clientX - r.left) * dpr, (ev.clientY - r.top) * dpr]; }
    function etendre(q) {
      var r = 3 * dpr;
      if (!etat.bx) etat.bx = [q[0] - r, q[1] - r, q[0] + r, q[1] + r];
      else { etat.bx[0] = Math.min(etat.bx[0], q[0] - r); etat.bx[1] = Math.min(etat.bx[1], q[1] - r); etat.bx[2] = Math.max(etat.bx[2], q[0] + r); etat.bx[3] = Math.max(etat.bx[3], q[1] + r); }
    }
    cv.addEventListener('pointerdown', function (ev) {
      ev.preventDefault(); try { cv.setPointerCapture(ev.pointerId); } catch (e) { /* ignoré */ }
      der = pos(ev); etendre(der);
      g.fillStyle = etat.encre; g.beginPath(); g.arc(der[0], der[1], 1.2 * dpr, 0, Math.PI * 2); g.fill();
      etat.vide = false;
    });
    cv.addEventListener('pointermove', function (ev) {
      if (!der) return;
      var q = pos(ev);
      g.strokeStyle = etat.encre; g.lineWidth = (opts.petit ? 2 : 2.6) * dpr; g.lineCap = 'round'; g.lineJoin = 'round';
      g.beginPath(); g.moveTo(der[0], der[1]); g.lineTo(q[0], q[1]); g.stroke();
      der = q; etendre(q);
    });
    function lever() { der = null; }
    cv.addEventListener('pointerup', lever); cv.addEventListener('pointercancel', lever);

    function apercu() {
      var u = texteEnPng(inp.value, etat.encre, 56);
      ap.innerHTML = '';
      if (u) { var im = el('img'); im.src = u; im.alt = 'Aperçu'; ap.appendChild(im); }
      else ap.textContent = opts.petit ? 'Saisir vos initiales' : 'Saisir votre nom';
    }
    function maj() {
      onglets.querySelectorAll('.ppx-onglet').forEach(function (b) { b.classList.toggle('actif', b.getAttribute('data-mode') === etat.mode); });
      zoneDessin.hidden = etat.mode !== 'dessin';
      zoneTexte.hidden = etat.mode !== 'texte';
      zoneReut.hidden = etat.mode !== 'reutilise';
      bEff.hidden = etat.mode !== 'dessin';
      outils.hidden = etat.mode === 'reutilise';
      if (etat.mode === 'dessin') requestAnimationFrame(taille);
      if (etat.mode === 'texte') apercu();
    }
    maj();
    return {
      lire: function () {
        if (etat.mode === 'reutilise') return reut[etat.choix] ? { png: reut[etat.choix], mode: 'reutilise' } : null;
        if (etat.mode === 'texte') { var u = texteEnPng(inp.value, etat.encre, 72); return u ? { png: u, mode: 'texte', texte: inp.value.trim() } : null; }
        if (etat.vide || !etat.bx) return null;
        var d = recadrer(cv, etat.bx);
        return d ? { png: d, mode: 'dessin' } : null;
      }
    };
  }

  /* ── Fenêtre interne (dans la vue de signature) ────────────────────── */
  function fenetre(titre, corps, actions) {
    var fond = el('div', 'ppx-modale-fond');
    var m = el('div', 'ppx-modale');
    m.setAttribute('role', 'dialog'); m.setAttribute('aria-modal', 'true');
    var hd = el('div', 'ppx-modale-hd', '<h3></h3>');
    hd.querySelector('h3').textContent = titre;
    var x = el('button', 'ppx-x', svg('fermer', 16)); x.type = 'button'; x.setAttribute('aria-label', 'Fermer'); x.setAttribute('data-bulle', 'Fermer');
    hd.appendChild(x);
    var ft = el('div', 'ppx-modale-ft');
    m.appendChild(hd); m.appendChild(corps); m.appendChild(ft);
    fond.appendChild(m);
    document.body.appendChild(fond);
    function fermer() { fond.remove(); document.removeEventListener('keydown', clavier); }
    function clavier(ev) { if (ev.key === 'Escape') fermer(); }
    document.addEventListener('keydown', clavier);
    x.addEventListener('click', fermer);
    fond.addEventListener('pointerdown', function (ev) { if (ev.target === fond) fermer(); });
    (actions || []).forEach(function (a) {
      var b = el('button', 'ppx-btn' + (a.plein ? ' ppx-btn-plein' : '') + (a.danger ? ' ppx-btn-danger' : ''), esc(a.txt));
      b.type = 'button'; b.setAttribute('data-bulle', a.bulle || a.txt.split(' ')[0]);
      b.addEventListener('click', function () { a.fn(b, fermer); });
      ft.appendChild(b);
    });
    return { fermer: fermer, el: m };
  }

  /* ── Vue de signature ──────────────────────────────────────────────── */
  // ctx : {octets, zones, nom, titre, detail, circuit, reutilisables,
  //        consentement (texte), surSigner(data) -> Promise, surRefuser(motif) -> Promise, toast(msg, type)}
  function vueSignature(racine, ctx) {
    var toast = ctx.toast || function () {};
    var aParaphe = (ctx.zones || []).some(function (z) { return z.type === 'paraphe'; });
    racine.innerHTML = '';
    var barre = el('div', 'ppx-sig-barre');
    var info = el('div', 'ppx-sig-info');
    var t = el('div', 'ppx-sig-titre'); t.textContent = ctx.titre || '';
    var d = el('div', 'ppx-sig-detail'); d.textContent = ctx.detail || '';
    info.appendChild(t); info.appendChild(d);
    var actions = el('div', 'ppx-sig-actions');
    var bSuiv = el('button', 'ppx-btn', svg('suivant', 16) + 'Zone suivante'); bSuiv.type = 'button'; bSuiv.setAttribute('data-bulle', 'Suivante');
    var bRef = el('button', 'ppx-btn ppx-btn-danger-l', svg('refuser', 16) + 'Refuser'); bRef.type = 'button'; bRef.setAttribute('data-bulle', 'Refuser');
    var bSig = el('button', 'ppx-btn ppx-btn-plein', svg('signer', 16) + 'Signer'); bSig.type = 'button'; bSig.setAttribute('data-bulle', 'Signer');
    actions.appendChild(bSuiv); actions.appendChild(bRef); actions.appendChild(bSig);
    barre.appendChild(info); barre.appendChild(actions);
    racine.appendChild(barre);
    if (ctx.message) { var msg = el('div', 'ppx-sig-message'); msg.textContent = ctx.message; racine.appendChild(msg); }
    if (ctx.circuit && ctx.circuit.length > 1) {
      var circ = el('div', 'ppx-circuit');
      ctx.circuit.forEach(function (c) {
        var p = el('span', 'ppx-circuit-pas ppx-st-' + esc(c.statut) + (c.moi ? ' moi' : ''));
        p.textContent = c.ordre + '. ' + (c.moi ? 'Vous' : c.nom);
        circ.appendChild(p);
      });
      racine.appendChild(circ);
    }
    var docs = el('div', 'ppx-docs', '<div class="ppx-attente"><span class="ppx-spin"></span> Chargement du document…</div>');
    racine.appendChild(docs);
    var zonesEl = [], courant = -1;
    rendrePages(docs, ctx.octets, { largeur: Math.min(980, racine.clientWidth || 900) }).then(function (pages) {
      (ctx.zones || []).forEach(function (z) {
        var p = pages[z.page - 1]; if (!p) return;
        var e = el('div', 'ppx-zone ppx-zone-moi ppx-zone-' + z.type);
        e.style.left = (z.x * 100) + '%'; e.style.top = (z.y * 100) + '%';
        e.style.width = (z.w * 100) + '%'; e.style.height = (z.h * 100) + '%';
        e.innerHTML = '<span class="ppx-zone-lib">' + esc(LIB_ZONE[z.type] || z.type) + '</span>';
        e.setAttribute('data-bulle', 'Signer');
        e.addEventListener('click', function () { if (z.type === 'date' || z.type === 'nom') return; ouvrirSigner(); });
        p.calque.appendChild(e);
        zonesEl.push(e);
      });
      if (zonesEl.length) setTimeout(function () { allerZone(0); }, 60);
    }).catch(function (e) { docs.innerHTML = '<div class="ppx-vide">' + esc(e.message || 'Document illisible.') + '</div>'; });

    function allerZone(i) {
      if (!zonesEl.length) return;
      courant = (i + zonesEl.length) % zonesEl.length;
      zonesEl.forEach(function (z, k) { z.classList.toggle('ppx-zone-active', k === courant); });
      zonesEl[courant].scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    bSuiv.addEventListener('click', function () { allerZone(courant + 1); });

    function ouvrirSigner() {
      var corps = el('div', 'ppx-modale-bd');
      var pSig = pad(corps, { nom: ctx.nom, reutilisables: ctx.reutilisables, titre: 'Signature' });
      var pPar = aParaphe ? pad(corps, { nom: ctx.nom, petit: true, titre: 'Paraphe' }) : null;
      var lab = el('label', 'ppx-consent');
      lab.innerHTML = '<input type="checkbox"> <span></span>';
      lab.querySelector('span').textContent = ctx.consentement || "J'ai lu le document et je le signe.";
      corps.appendChild(lab);
      var f = fenetre('Signer « ' + (ctx.titre || 'le document') + ' »', corps, [
        { txt: 'Annuler', fn: function (b, fermer) { fermer(); } },
        { txt: 'Signer le document', bulle: 'Signer', plein: true, fn: async function (b, fermer) {
          var s = pSig.lire();
          if (!s) { toast('Signature vide — tracez-la, saisissez-la ou choisissez-en une.', 'danger'); return; }
          var p = pPar ? pPar.lire() : null;
          if (pPar && !p) { toast('Paraphe vide — saisissez vos initiales ou tracez-les.', 'danger'); return; }
          if (!lab.querySelector('input').checked) { toast('Cochez la case pour confirmer la signature.', 'danger'); return; }
          b.disabled = true; b.textContent = 'Signature…';
          try {
            await ctx.surSigner({ signature: s.png, paraphe: p ? p.png : null, mode: s.mode,
                                  nom: s.texte || ctx.nom || '', consentement: true });
            fermer();
          } catch (e) { toast(e.message || 'Signature non enregistrée.', 'danger'); b.disabled = false; b.textContent = 'Signer le document'; }
        } }
      ]);
      return f;
    }
    bSig.addEventListener('click', ouvrirSigner);
    bRef.addEventListener('click', function () {
      var corps = el('div', 'ppx-modale-bd');
      corps.appendChild(el('p', 'ppx-aide', 'Le refus arrête la demande. Il est transmis à l\'émetteur avec son motif.'));
      var ta = el('textarea', 'ppx-champ'); ta.rows = 4; ta.maxLength = 1000; ta.setAttribute('aria-label', 'Motif du refus');
      ta.placeholder = 'Motif du refus';
      corps.appendChild(ta);
      fenetre('Refuser de signer', corps, [
        { txt: 'Annuler', fn: function (b, fermer) { fermer(); } },
        { txt: 'Confirmer le refus', bulle: 'Refuser', danger: true, fn: async function (b, fermer) {
          if (ta.value.trim().length < 3) { toast('Motif du refus obligatoire.', 'danger'); return; }
          b.disabled = true;
          try { await ctx.surRefuser(ta.value.trim()); fermer(); }
          catch (e) { toast(e.message || 'Refus non enregistré.', 'danger'); b.disabled = false; }
        } }
      ]);
      requestAnimationFrame(function () { ta.focus(); });
    });
    return { signer: ouvrirSigner };
  }

  function signaturesReutilisables(serveur) {
    var out = [];
    if (serveur) out.push(serveur);
    try { var l = localStorage.getItem(CLE_EDITEUR); if (l && l.indexOf('data:image/png') === 0 && out.indexOf(l) === -1) out.push(l); } catch (e) { /* stockage indisponible */ }
    return out;
  }

  window.ParapheurCore = {
    pdfjs: pdfjs, rendrePages: rendrePages, pad: pad, vueSignature: vueSignature, fenetre: fenetre,
    texteEnPng: texteEnPng, initiales: initiales, esc: esc, svg: svg, dateFr: dateFr,
    signaturesReutilisables: signaturesReutilisables, LIB_ZONE: LIB_ZONE
  };

  /* ══ Espace SIFA ════════════════════════════════════════════════════ */
  var X = { ctx: null };
  var CLE_JETON = 'ppx_jeton:';

  function jetonDe(sid) { try { return sessionStorage.getItem(CLE_JETON + sid) || ''; } catch (e) { return ''; } }
  function garderJeton(sid, j) { try { sessionStorage.setItem(CLE_JETON + sid, j); } catch (e) { /* onglet privé */ } }
  function oublierJeton(sid) { try { sessionStorage.removeItem(CLE_JETON + sid); } catch (e) { /* ignoré */ } }

  async function appelX(chemin, jeton, opts) {
    opts = opts || {};
    var h = Object.assign({}, opts.headers || {});
    if (jeton) h['X-Parapheur-Jeton'] = jeton;
    if (opts.body) h['Content-Type'] = 'application/json';
    var r = await fetch(X.ctx.api + chemin, { method: opts.method || 'GET', headers: h, body: opts.body, credentials: 'same-origin' });
    if (opts.binaire && r.ok) return new Uint8Array(await r.arrayBuffer());
    var j = null; try { j = await r.json(); } catch (e) { /* vide */ }
    if (!r.ok) {
      var d = j && j.detail, err = new Error(typeof d === 'string' ? d : (d && d.message) || ('Erreur ' + r.status));
      err.status = r.status; err.detail = d; throw err;
    }
    return j;
  }
  function toastX(m) { if (typeof window.toast === 'function') window.toast(m); }

  function vueMessage(texte, sid) {
    var m = X.ctx.main;
    m.innerHTML = '<button type="button" class="es-retour">← Votre espace</button><div class="es-form ppx-x-msg"><p></p></div>';
    m.querySelector('.es-retour').addEventListener('click', function () { X.ctx.retour(); });
    m.querySelector('p').textContent = texte;
    if (sid) {
      var b = el('button', 'es-btn', 'Recevoir un nouveau lien par email'); b.type = 'button'; b.setAttribute('data-bulle', 'Recevoir');
      b.addEventListener('click', function () { demanderLien(sid, b); });
      m.querySelector('.es-form').appendChild(b);
    }
  }
  async function demanderLien(sid, b) {
    if (b) { b.disabled = true; b.textContent = 'Envoi…'; }
    try {
      await appelX('/signatures/' + sid + '/lien', '', { method: 'POST' });
      if (b) b.textContent = 'Lien envoyé — consultez votre messagerie.';
    } catch (e) { toastX(e.message); if (b) { b.disabled = false; b.textContent = 'Recevoir un nouveau lien par email'; } }
  }

  async function afficherSignature(sid, jeton) {
    var m = X.ctx.main;
    m.innerHTML = '<div class="es-intro"><span class="ppx-spin"></span> Chargement…</div>';
    var info;
    try { info = await appelX('/signature', jeton); }
    catch (e) {
      var ds = e.detail && typeof e.detail === 'object' ? e.detail : {};
      if (ds.raison === 'traite' || ds.raison === 'inconnu') oublierJeton(sid);
      vueMessage(e.message, ds.raison === 'traite' || ds.raison === 'inconnu' ? null : (ds.signataire_id || sid));
      return;
    }
    sid = info.signataire.id;
    garderJeton(sid, jeton);
    if (new URLSearchParams(location.search).get('signature') !== String(sid) || location.hash) {
      // Garde l'état de l'entrée : arrivée directe (lien de l'email) = null,
      // et « Votre espace » ne recule pas hors de l'Espace.
      history.replaceState(history.state, '', location.pathname + '?signature=' + sid);
    }
    var octets;
    try { octets = await appelX('/signature/document', jeton, { binaire: true }); }
    catch (e) { vueMessage(e.message, sid); return; }
    m.innerHTML = '<button type="button" class="es-retour">← Votre espace</button><div class="ppx-x-vue"></div>';
    m.querySelector('.es-retour').addEventListener('click', function () { X.ctx.retour(); });
    var dm = info.demande;
    document.title = dm.titre + ' — à signer';
    vueSignature(m.querySelector('.ppx-x-vue'), {
      octets: octets, zones: info.zones, nom: info.signataire.nom, titre: dm.titre, message: dm.message,
      detail: [dm.nom_fichier, dm.cree_par_nom ? 'envoyé par ' + dm.cree_par_nom : '', dm.echeance ? 'à signer avant le ' + dateFr(dm.echeance) : ''].filter(Boolean).join(' · '),
      circuit: info.circuit, reutilisables: signaturesReutilisables(null),
      consentement: "J'ai lu le document « " + dm.titre + " » et je le signe électroniquement. Mon nom, mon adresse email, la date et mon adresse IP figureront sur le certificat de signature.",
      toast: function (msg) { toastX(msg); },
      surSigner: async function (data) {
        await appelX('/signature/signer', jeton, { method: 'POST', body: JSON.stringify(data) });
        oublierJeton(sid);
        await fin('Signature enregistrée.', 'Merci. Vous recevrez le document signé par email dès que tous les signataires auront signé ; il restera disponible dans votre espace.');
      },
      surRefuser: async function (motif) {
        await appelX('/signature/refuser', jeton, { method: 'POST', body: JSON.stringify({ motif: motif }) });
        oublierJeton(sid);
        await fin('Refus enregistré.', "L'émetteur du document en est informé.");
      }
    });
  }
  async function fin(titre, texte) {
    try { if (X.ctx.recharger) await X.ctx.recharger(); } catch (e) { /* liste rechargée au retour */ }
    var m = X.ctx.main;
    m.innerHTML = '<div class="es-merci"><h2></h2><p style="margin:0 0 16px;color:var(--text2)"></p><button type="button" class="es-retour" style="margin:0">← Votre espace</button></div>';
    m.querySelector('h2').textContent = titre;
    m.querySelector('p').textContent = texte;
    m.querySelector('.es-retour').addEventListener('click', function () { X.ctx.retour(); });
    window.scrollTo(0, 0);
  }

  window.ParapheurEspace = {
    // Appelé par suivreAdresse() de la page : rend true si l'adresse désigne
    // une signature (et l'affiche).
    suivre: async function (ctx) {
      X.ctx = ctx;
      var h = /[#&]signer=([A-Za-z0-9_-]{20,100})/.exec(location.hash || '');
      if (h) { await afficherSignature(null, h[1]); return true; }
      var sid = new URLSearchParams(location.search).get('signature');
      if (sid && /^\d+$/.test(sid)) {
        var j = jetonDe(sid);
        if (j) await afficherSignature(Number(sid), j);
        else vueMessage('Pour signer ce document, ouvrez le lien de l\'email reçu, ou recevez-en un nouveau.', Number(sid));
        return true;
      }
      return false;
    },
    carte: function (e) {
      var badge, action = '';
      if (e.a_traiter) {
        badge = '<span class="es-badge attente">À signer' + (e.echeance ? ' avant le ' + esc(dateFr(e.echeance)) : '') + '</span>';
      } else if (e.statut === 'signe') {
        badge = '<span class="es-badge ok">Signé le ' + esc(dateFr(e.signe_le)) + '</span>';
      } else {
        badge = '<span class="es-badge">' + esc({ refuse: 'Refusé', expire: 'Expiré', annule: 'Annulé' }[e.statut] || 'Clos') + '</span>';
      }
      var detail = [e.detail, e.de ? 'de ' + e.de : '', e.envoye_le ? 'envoyé le ' + dateFr(e.envoye_le) : ''].filter(Boolean).join(' · ');
      var corps = '<span class="es-ico">' + svg('doc', 20) + '</span><span class="es-carte-main"><span class="es-carte-titre">' + esc(e.titre)
        + '</span><span class="es-carte-detail" style="display:block">' + esc(detail) + '</span></span>' + badge;
      if (e.final && X.ctx) {
        return '<a class="es-carte" data-bulle="Télécharger" href="' + esc(X.ctx.api + '/signatures/' + Number(e.id) + '/final') + '">' + corps + '</a>';
      }
      if (e.a_traiter) return '<button type="button" class="es-carte" data-bulle="Signer" onclick="ParapheurEspace.ouvrir(' + Number(e.id) + ')">' + corps + '</button>';
      return '<div class="es-carte" style="cursor:default">' + corps + '</div>';
    },
    ouvrir: function (sid) {
      history.pushState({ signature: sid }, '', location.pathname + '?signature=' + sid);
      window.ParapheurEspace.suivre(X.ctx);
      window.scrollTo(0, 0);
    }
  };
})();

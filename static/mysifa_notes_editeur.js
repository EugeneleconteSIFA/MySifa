/**
 * MySifa — Éditeur de notes en blocs, commun aux post-its et à Mes notes (/note).
 *
 * Une note est une suite de blocs { uid, type, texte, html, coche, retrait, ref,
 * legende, largeur }. Chaque bloc de texte est un élément `contenteditable`
 * dont le HTML est réduit à la mise en forme en ligne (gras, italique,
 * souligné, barré, code, lien, retour à la ligne) — le serveur assainit de
 * nouveau à la réception (app/services/notes.py).
 *
 * Synchronisation : l'éditeur ne renvoie jamais la note entière. Il compare
 * le contenu à ce qu'il a déjà envoyé et en tire des opérations par bloc
 * (ins, set, del, mov), envoyées par paquets. Avec `flux`, il suit les
 * opérations des autres éditeurs et la présence (qui écrit dans quel bloc) ;
 * deux personnes dans le même bloc : le texte de l'autre est fusionné dans le
 * sien avant le prochain envoi.
 *
 *   var ed = MySifaNotesEditeur.monter(conteneur, note, {
 *     noteId,                         // obligatoire pour enregistrer
 *     flux: true,                     // suivre les autres éditeurs
 *     lectureSeule: false,
 *     surChange(ed), surPresences(liste), surTitre(titre), recharger(),
 *     creerSousPage(ed) → Promise<{id, title}>, ouvrirPage(id), titrePage(ref),
 *     lienPage(ref), poignees: true, placeholder: '…', signaler(msg),
 *   });
 */
(function () {
  'use strict';
  if (window.MySifaNotesEditeur) return;

  var TYPES = {
    p: { libelle: 'Texte', aide: 'Paragraphe simple', icone: 'Aa', ph: 'Écrire, ou « / » pour les commandes', mots: 'texte paragraphe normal' },
    h1: { libelle: 'Titre 1', aide: 'Grand titre', icone: 'H1', ph: 'Titre 1', mots: 'titre grand h1 #' },
    h2: { libelle: 'Titre 2', aide: 'Titre de section', icone: 'H2', ph: 'Titre 2', mots: 'titre moyen h2 ##' },
    h3: { libelle: 'Titre 3', aide: 'Petit titre', icone: 'H3', ph: 'Titre 3', mots: 'titre petit h3 ###' },
    todo: { libelle: 'Case à cocher', aide: 'Tâche à cocher', icone: '✓', ph: 'À faire', mots: 'tache case cocher todo checkbox liste []' },
    puce: { libelle: 'Liste à puces', aide: 'Liste simple', icone: '•', ph: 'Élément', mots: 'liste puce puces bullet -' },
    num: { libelle: 'Liste numérotée', aide: 'Liste 1, 2, 3', icone: '1.', ph: 'Élément', mots: 'liste numerotee numero ordonnee 1.' },
    citation: { libelle: 'Citation', aide: 'Propos rapporté', icone: '“', ph: 'Citation', mots: 'citation quote >' },
    encadre: { libelle: 'Encadré', aide: 'Texte mis en avant', icone: '!', ph: 'À retenir', mots: 'encadre important callout attention note !' },
    code: { libelle: 'Code', aide: 'Texte à chasse fixe', icone: '</>', ph: 'Code', mots: 'code mono commande ```' },
    sep: { libelle: 'Séparateur', aide: 'Ligne de séparation', icone: '—', ph: '', mots: 'separateur ligne trait diviseur ---' },
    page: { libelle: 'Page', aide: 'Sous-note rangée dans celle-ci', icone: '▤', ph: '', mots: 'page sous-page sous note lien' },
    image: { libelle: 'Image', aide: 'Depuis votre ordinateur', icone: '▣', ph: '', mots: 'image photo capture illustration' },
    bascule: { libelle: 'Bloc repliable', aide: 'Titre qui cache son contenu', icone: '▸', ph: 'Titre repliable', mots: 'repliable bascule toggle replier deplier details' },
    tableau: { libelle: 'Tableau', aide: 'Lignes et colonnes', icone: '▦', ph: '', mots: 'tableau table grille colonnes lignes excel' },
  };
  var LISTES = { todo: 1, puce: 1, num: 1 };
  var OBJETS = { sep: 1, page: 1, image: 1 };
  /* Blocs sans texte propre : on ne fusionne pas de texte avec eux. */
  var NON_TEXTE = { sep: 1, page: 1, image: 1, tableau: 1 };
  var TAB_LIGNES_MAX = 60;
  var TAB_COLONNES_MAX = 12;

  /* Blocs repliables fermés : préférence de chacun, dans son navigateur. */
  var _plies = {};
  try { _plies = JSON.parse(localStorage.getItem('mysifa_notes_plies') || '{}') || {}; } catch (e) { _plies = {}; }
  function memoriserPlies() {
    try { localStorage.setItem('mysifa_notes_plies', JSON.stringify(_plies)); } catch (e) {}
  }
  var RETRAIT_MAX = 3;
  var BLOCS_MAX = 400;
  var IMAGE_MAX = 10 * 1024 * 1024;
  var COMMANDES = Object.keys(TYPES)
    .map(function (t) {
      var d = TYPES[t];
      return { cle: t, type: t, libelle: d.libelle, aide: d.aide, icone: d.icone, mots: d.mots };
    })
    .concat([
      { cle: 'lien', action: 'lien', libelle: 'Lien', aide: 'Adresse web (Cmd/Ctrl + K)', icone: '↗', mots: 'lien url adresse web' },
      { cle: 'mysifa', action: 'mysifa', libelle: 'Lien MySifa', aide: 'Dossier, machine, client, note (ou tapez @)', icone: '@', mots: 'mysifa dossier machine client note arobase reference' },
      { cle: 'modele', action: 'modele', libelle: 'Modèle', aide: 'Insérer un modèle de note', icone: '❏', mots: 'modele gabarit template trame' },
      { cle: 'date', action: 'date', libelle: 'Date du jour', aide: 'Insère la date', icone: 'J', mots: 'date jour aujourdhui' },
      { cle: 'heure', action: 'heure', libelle: 'Heure', aide: 'Insère l\'heure', icone: 'h', mots: 'heure maintenant' },
      { cle: 'dupliquer', action: 'dupliquer', libelle: 'Dupliquer le bloc', aide: 'Copie juste en dessous', icone: '⧉', mots: 'dupliquer copier' },
      { cle: 'supprimer', action: 'supprimer', libelle: 'Supprimer le bloc', aide: 'Retire ce bloc', icone: '×', mots: 'supprimer effacer retirer' },
    ]);
  var RACCOURCIS = {
    '#': 'h1', '##': 'h2', '###': 'h3', '-': 'puce', '*': 'puce', '1.': 'num',
    '[]': 'todo', '[ ]': 'todo', '>': 'citation', '!': 'encadre',
  };
  /* Remplacements à la frappe ; retour arrière juste après rend le texte tapé. */
  var REMPLACEMENTS = [
    ['←>', '↔'], ['-->', '→'], ['<--', '←'], ['==>', '⇒'], ['->', '→'], ['=>', '⇒'],
    ['!=', '≠'], ['>=', '≥'], ['<=', '≤'], ['...', '…'], ['(c)', '©'], ['+-', '±'],
  ];
  /* Couleurs des autres éditeurs : variables du thème, jamais en dur. */
  var COULEURS = ['var(--c1, var(--accent))', 'var(--c2, var(--success))', 'var(--c3, var(--warn))', 'var(--c4, var(--danger))', 'var(--accent)'];

  var ICONE_POIGNEE =
    '<svg width="10" height="14" viewBox="0 0 10 14" fill="currentColor" aria-hidden="true">' +
    '<circle cx="2.5" cy="2.5" r="1.3"/><circle cx="7.5" cy="2.5" r="1.3"/>' +
    '<circle cx="2.5" cy="7" r="1.3"/><circle cx="7.5" cy="7" r="1.3"/>' +
    '<circle cx="2.5" cy="11.5" r="1.3"/><circle cx="7.5" cy="11.5" r="1.3"/></svg>';
  var ICONE_PAGE =
    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
    '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><path d="M9 12h6M9 16h4"/></svg>';

  var _editeurs = [];
  var _slash = null;
  var _drag = null;
  var _remp = null;
  var _interne = 0;
  var _barre = null;
  var _bulleLien = null;
  var _client = 'c' + Math.random().toString(36).slice(2, 10) + Date.now().toString(36);

  try { document.execCommand('styleWithCSS', false, false); } catch (e) {}

  /* ── Outils ─────────────────────────────────────────────────────────── */

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function sansAccent(s) {
    return String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }
  function uid() {
    return Math.random().toString(36).slice(2, 8) + Date.now().toString(36).slice(-6);
  }
  function copie(b) {
    return JSON.parse(JSON.stringify(b));
  }
  function signature(b) {
    return JSON.stringify([b.type, b.html || '', b.html ? '' : (b.texte || ''), !!b.coche, b.retrait || 0, b.ref || 0, b.legende || '', b.largeur || 0,
      b.lignes || null, !!b.entete]);
  }

  /* ── Texte riche : assainissement (miroir de app/services/notes.py) ── */

  var BALISES = { B: 'b', STRONG: 'b', I: 'i', EM: 'i', U: 'u', S: 's', STRIKE: 's', DEL: 's', CODE: 'code', A: 'a' };
  var LIEN_OK = /^(https?:\/\/|mailto:|\/)[^\s"'<>]*$/i;

  function assainirNoeud(n, out) {
    if (n.nodeType === 3) { out.push(esc(n.data).replace(/&#39;/g, "'").replace(/&quot;/g, '"')); return; }
    if (n.nodeType !== 1) return;
    var tag = n.tagName;
    if (tag === 'BR') { out.push('<br>'); return; }
    if ((tag === 'DIV' || tag === 'P') && out.length) out.push('<br>');
    var nom = BALISES[tag];
    /* Gras / italique posés en style par certains collages. */
    if (!nom && tag === 'SPAN' && n.style) {
      if (/^(bold|[6-9]00)$/.test(n.style.fontWeight)) nom = 'b';
      else if (n.style.fontStyle === 'italic') nom = 'i';
    }
    var ouvre = '';
    if (nom === 'a') {
      var href = (n.getAttribute('href') || '').trim();
      if (LIEN_OK.test(href)) ouvre = '<a href="' + esc(href) + '">';
      else nom = null;
    } else if (nom) ouvre = '<' + nom + '>';
    if (ouvre) out.push(ouvre);
    for (var c = n.firstChild; c; c = c.nextSibling) assainirNoeud(c, out);
    if (ouvre) out.push('</' + nom + '>');
  }

  function assainir(html) {
    var d = document.createElement('div');
    d.innerHTML = String(html || '');
    var out = [];
    for (var c = d.firstChild; c; c = c.nextSibling) assainirNoeud(c, out);
    return out.join('').replace(/(<br>)+$/, '');
  }

  function aMiseEnForme(html) {
    return /<(b|i|u|s|code|a)[ >]/.test(html || '');
  }

  function htmlDe(b) {
    if (b.html) return b.html;
    return esc(b.texte || '').replace(/\n/g, '<br>');
  }

  /* ── Positions dans un bloc (texte brut, <br> compte pour un caractère) ── */

  function texteDe(el) {
    var t = '';
    (function parcourir(n) {
      for (var c = n.firstChild; c; c = c.nextSibling) {
        if (c.nodeType === 3) t += c.data;
        else if (c.nodeName === 'BR') t += '\n';
        else parcourir(c);
      }
    })(el);
    return t;
  }

  function longueurJusqua(el, noeud, offset) {
    var r = document.createRange();
    r.setStart(el, 0);
    try { r.setEnd(noeud, offset); } catch (e) { return 0; }
    var d = document.createElement('div');
    d.appendChild(r.cloneContents());
    return texteDe(d).length;
  }

  function curseur(el) {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return { debut: 0, fin: 0 };
    var r = sel.getRangeAt(0);
    if (!el.contains(r.startContainer)) return { debut: 0, fin: 0 };
    var a = longueurJusqua(el, r.startContainer, r.startOffset);
    var b = r.collapsed ? a : longueurJusqua(el, r.endContainer, r.endOffset);
    return { debut: a, fin: b };
  }

  function point(el, pos) {
    var reste = pos;
    var trouve = null;
    (function parcourir(n) {
      for (var c = n.firstChild; c && !trouve; c = c.nextSibling) {
        if (c.nodeType === 3) {
          if (reste <= c.data.length) { trouve = { n: c, o: reste }; return; }
          reste -= c.data.length;
        } else if (c.nodeName === 'BR') {
          if (reste === 0) { trouve = { n: n, o: Array.prototype.indexOf.call(n.childNodes, c) }; return; }
          reste -= 1;
        } else parcourir(c);
      }
    })(el);
    return trouve || { n: el, o: el.childNodes.length };
  }

  function plage(el, a, b) {
    var r = document.createRange();
    var p1 = point(el, a);
    var p2 = b === a ? p1 : point(el, b);
    r.setStart(p1.n, p1.o);
    r.setEnd(p2.n, p2.o);
    return r;
  }

  function placer(el, a, b) {
    var sel = window.getSelection();
    if (!sel) return;
    var n = texteDe(el).length;
    a = a == null || a < 0 || a > n ? n : a;
    b = b == null ? a : Math.min(b, n);
    sel.removeAllRanges();
    sel.addRange(plage(el, a, b));
  }

  /* Remplace le texte [a, b[ du bloc focalisé, en gardant l'annulation native. */
  function remplacerTexte(el, a, b, txt) {
    placer(el, a, b);
    /* execCommand déclenche son propre « input » : on ne le retraite pas. */
    _interne++;
    try {
      if (txt) document.execCommand('insertText', false, txt);
      else if (b > a) document.execCommand('delete', false);
    } finally {
      _interne--;
    }
  }

  function rectCurseur() {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return null;
    var r = sel.getRangeAt(0).cloneRange();
    r.collapse(true);
    var rects = r.getClientRects();
    if (rects.length) return rects[0];
    var span = document.createElement('span');
    span.textContent = '​';
    r.insertNode(span);
    var rect = span.getBoundingClientRect();
    var parent = span.parentNode;
    parent.removeChild(span);
    parent.normalize();
    return rect;
  }

  function premiereLigne(el) {
    if (!texteDe(el)) return true;
    var rc = rectCurseur();
    if (!rc) return true;
    var lh = parseFloat(getComputedStyle(el).lineHeight) || 20;
    return rc.top - el.getBoundingClientRect().top < lh * 0.8;
  }

  function derniereLigne(el) {
    if (!texteDe(el)) return true;
    var rc = rectCurseur();
    if (!rc) return true;
    var lh = parseFloat(getComputedStyle(el).lineHeight) || 20;
    return el.getBoundingClientRect().bottom - rc.bottom < lh * 0.8;
  }

  /* HTML d'un bloc découpé au curseur : [avant, après]. */
  function couper(el) {
    var sel = window.getSelection();
    var r = sel.getRangeAt(0);
    var fin = document.createRange();
    fin.setStart(r.endContainer, r.endOffset);
    fin.setEnd(el, el.childNodes.length);
    var apres = document.createElement('div');
    apres.appendChild(fin.extractContents());
    if (!r.collapsed) r.deleteContents();
    return [assainir(el.innerHTML), assainir(apres.innerHTML)];
  }

  /* Fusion de trois versions d'un même texte : base commune, la mienne, l'autre. */
  function fusion3(base, moi, autre) {
    if (moi === base || moi === autre) return autre;
    if (autre === base) return moi;
    function zone(a, b) {
      var p = 0;
      while (p < a.length && p < b.length && a[p] === b[p]) p++;
      var s = 0;
      while (s < a.length - p && s < b.length - p && a[a.length - 1 - s] === b[b.length - 1 - s]) s++;
      return { debut: p, finBase: a.length - s, insere: b.slice(p, b.length - s) };
    }
    var zm = zone(base, moi);
    var za = zone(base, autre);
    if (za.finBase <= zm.debut) {
      return autre.slice(0, za.debut) + za.insere + base.slice(za.finBase, zm.debut) + zm.insere + base.slice(zm.finBase);
    }
    if (zm.finBase <= za.debut) {
      return base.slice(0, zm.debut) + zm.insere + base.slice(zm.finBase, za.debut) + za.insere + base.slice(za.finBase);
    }
    return moi;
  }

  /* ── Instance ─────────────────────────────────────────────────────────── */

  function Editeur(corps, note, opts) {
    this.corps = corps;
    this.note = note;
    this.opts = opts || {};
    this.lecture = !!this.opts.lectureSeule;
    this._timer = null;
    this._envoi = null;
    this._actif = true;
    this._pres = [];
    this._sig = '';
    this._blocFocus = null;
    this.rev = Number(note.revision || 0);
    corps.classList.add('nted');
    corps.classList.toggle('nted-lecture', this.lecture);
    if (this.opts.poignees && !this.lecture) corps.classList.add('nted-poignees');
    /* Référence = ce que le serveur a vraiment : sans le bloc vide ajouté ici. */
    this.envoye = (Array.isArray(note.blocs) ? note.blocs : []).map(copie);
    /* Des blocs sans identifiant ne viennent pas d'un serveur à jour (page
       chargée pendant une mise à jour) : on n'envoie rien tant que la note
       n'a pas été relue. Sinon tout le contenu repartirait comme « nouveau »
       et serait doublé (incident du 12/11/2026). */
    this._fiable = this.envoye.every(function (b) { return !!b.uid; });
    this.blocs();
    brancher(this);
    if (!this._fiable && this.opts.noteId && this.opts.recharger) {
      var moi = this;
      setTimeout(function () { if (!moi._fiable) moi.opts.recharger(); }, 0);
    }
    this.redessiner();
    _editeurs.push(this);
    if (this.opts.flux && this.opts.noteId) this.suivre();
  }

  var P = Editeur.prototype;

  P.blocs = function () {
    var n = this.note;
    if (!Array.isArray(n.blocs)) n.blocs = [];
    if (!n.blocs.length && !this.lecture) n.blocs.push({ uid: uid(), type: 'p', texte: '' });
    n.blocs.forEach(function (b) { if (!b.uid) b.uid = uid(); });
    return n.blocs;
  };

  /* Ce que le serveur a (ou aura dès l'envoi en cours) : base des différences. */
  P.prendreReference = function () {
    this.envoye = this.blocs().map(copie);
  };

  P.indexUid = function (u) {
    var bl = this.blocs();
    for (var i = 0; i < bl.length; i++) if (bl[i].uid === u) return i;
    return -1;
  };

  P.aCoche = function () {
    return this.blocs().some(function (b) { return b.type === 'todo' && b.coche; });
  };

  P.numero = function (blocs, i) {
    var r = blocs[i].retrait || 0;
    var n = 1;
    for (var j = i - 1; j >= 0; j--) {
      var rj = blocs[j].retrait || 0;
      if (rj > r) continue;
      if (rj < r || blocs[j].type !== 'num') break;
      n++;
    }
    return n;
  };

  P.blocHtml = function (blocs, i) {
    var b = blocs[i];
    var t = TYPES[b.type] ? b.type : 'p';
    var r = Math.max(0, Math.min(RETRAIT_MAX, b.retrait || 0));
    var edit = this.lecture ? 'false' : 'true';
    var cache = this._caches && this._caches[i];
    var h = '<div class="pb pb-' + t + (t === 'todo' && b.coche ? ' coche' : '') + (cache ? ' pb-cache' : '') +
      (t === 'bascule' && _plies[b.uid] ? ' ferme' : '') + '" data-i="' + i + '" data-uid="' + esc(b.uid) + '" style="--pb-r:' + r + '">';
    if (this.opts.poignees && !this.lecture) {
      h += '<span class="pb-poignee" draggable="true" title="Glisser pour déplacer" aria-hidden="true">' + ICONE_POIGNEE + '</span>';
    }
    h += '<span class="pb-presence" aria-hidden="true"></span>';
    if (t === 'sep') return h + '<div class="pb-sep pb-focusable" tabindex="0" aria-label="Séparateur"></div></div>';
    if (t === 'page') {
      var titre = (this.opts.titrePage && this.opts.titrePage(b.ref)) || b.texte || 'Sans titre';
      var url = this.opts.lienPage ? this.opts.lienPage(b.ref) : '/note?note=' + encodeURIComponent(b.ref || '');
      return h + '<a class="pb-lien pb-focusable" href="' + esc(url) + '" data-ref="' + esc(b.ref || '') + '">' +
        ICONE_PAGE + '<span>' + esc(titre) + '</span></a></div>';
    }
    if (t === 'image') {
      var l = Math.max(20, Math.min(100, b.largeur || 100));
      return h + '<figure class="pb-figure pb-focusable" tabindex="0">' +
        '<img src="/api/postits/images/' + Number(b.ref || 0) + '" alt="' + esc(b.legende || 'Image') + '" style="width:' + l + '%" loading="lazy" draggable="false">' +
        (this.lecture ? '' : '<span class="pb-taille" role="group" aria-label="Largeur">' +
          [25, 50, 75, 100].map(function (x) { return '<button type="button" data-largeur="' + x + '"' + (x === l ? ' class="sel"' : '') + '>' + x + ' %</button>'; }).join('') + '</span>') +
        '<figcaption class="pb-legende" contenteditable="' + edit + '" data-ph="Légende">' + esc(b.legende || '') + '</figcaption></figure></div>';
    }
    if (t === 'tableau') return h + this.tableauHtml(b) + '</div>';
    if (t === 'bascule') {
      var ouvert = !_plies[b.uid];
      h += '<button type="button" class="pb-chevron" data-basculer tabindex="-1" aria-expanded="' + ouvert + '" title="' + (ouvert ? 'Replier' : 'Déplier') + '">' +
        '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 6 15 12 9 18"/></svg></button>';
    }
    if (t === 'todo') h += '<input type="checkbox" class="pb-case" tabindex="-1"' + (b.coche ? ' checked' : '') + (this.lecture ? ' disabled' : '') + '>';
    else if (t === 'puce') h += '<span class="pb-marque" aria-hidden="true">' + (r % 2 ? '◦' : '•') + '</span>';
    else if (t === 'num') h += '<span class="pb-marque pb-marque-num" aria-hidden="true">' + this.numero(blocs, i) + '.</span>';
    var ph = blocs.length === 1 && t === 'p' && this.opts.placeholder ? this.opts.placeholder : TYPES[t].ph;
    return h + '<div class="pb-txt" contenteditable="' + edit + '" spellcheck="true" data-ph="' + esc(this.lecture ? '' : ph) + '">' + htmlDe(b) + '</div></div>';
  };

  P.tableauHtml = function (b) {
    var edit = this.lecture ? 'false' : 'true';
    var lignes = Array.isArray(b.lignes) && b.lignes.length ? b.lignes : [['', ''], ['', '']];
    var h = '<div class="pb-tableau-zone"><table class="pb-grille' + (b.entete ? ' entete' : '') + '"><tbody>';
    lignes.forEach(function (ligne, r) {
      h += '<tr>';
      ligne.forEach(function (cell, c) {
        h += '<td><div class="pb-cellule" contenteditable="' + edit + '" spellcheck="true" data-r="' + r + '" data-c="' + c + '">' + assainir(cell || '') + '</div></td>';
      });
      h += '</tr>';
    });
    h += '</tbody></table></div>';
    if (!this.lecture) {
      h += '<div class="pb-tableau-outils" role="group" aria-label="Tableau">' +
        '<button type="button" data-tab="ligne">+ Ligne</button><button type="button" data-tab="colonne">+ Colonne</button>' +
        '<button type="button" data-tab="moins-ligne">− Ligne</button><button type="button" data-tab="moins-colonne">− Colonne</button>' +
        '<button type="button" data-tab="entete"' + (b.entete ? ' class="sel"' : '') + '>En-tête</button></div>';
    }
    return h;
  };

  function texteTableau(lignes) {
    var d = document.createElement('div');
    return (lignes || []).map(function (l) {
      return l.map(function (c) { d.innerHTML = c || ''; return texteDe(d).replace(/\n/g, ' '); }).join(' · ');
    }).join('\n');
  }

  /* Redessine tout ; sans consigne, le curseur reste où il était (même bloc, même position). */
  P.redessiner = function (focusI, pos) {
    var garde = null;
    if (focusI == null) {
      var ae = document.activeElement;
      if (ae && this.corps.contains(ae) && (ae.classList.contains('pb-txt') || ae.classList.contains('pb-cellule'))) {
        var row = ae.closest('.pb');
        garde = { uid: row && row.dataset.uid, c: curseur(ae), r: ae.dataset.r, col: ae.dataset.c };
      }
    }
    var blocs = this.blocs();
    /* Blocs rangés sous un bloc repliable fermé : présents, mais cachés. */
    this._caches = {};
    var pile = [];
    var vides = {};
    for (var j = 0; j < blocs.length; j++) {
      var rj = blocs[j].retrait || 0;
      while (pile.length && rj <= pile[pile.length - 1].r) pile.pop();
      if (pile.some(function (x) { return x.ferme; })) this._caches[j] = 1;
      if (blocs[j].type === 'bascule') {
        pile.push({ r: rj, ferme: !!_plies[blocs[j].uid] });
        var suivant = blocs[j + 1];
        if (!_plies[blocs[j].uid] && !(suivant && (suivant.retrait || 0) > rj) && !this._caches[j]) vides[j] = rj;
      }
    }
    var out = '';
    for (var i = 0; i < blocs.length; i++) {
      out += this.blocHtml(blocs, i);
      if (vides[i] != null && !this.lecture) {
        out += '<div class="pb-bascule-vide" data-apres="' + i + '" style="--pb-r:' + (vides[i] + 1) + '">Vide — cliquez pour écrire dedans</div>';
      }
    }
    if (!blocs.length) out = '<div class="nted-vide">Note vide</div>';
    this.corps.innerHTML = out;
    this.peindrePresences();
    if (focusI != null) this.focus(focusI, pos);
    else if (garde && garde.uid) {
      var k = this.indexUid(garde.uid);
      if (k >= 0 && garde.r != null) this.focusCellule(k, Number(garde.r), Number(garde.col), garde.c.debut);
      else if (k >= 0) this.focus(k, garde.c.debut, garde.c.fin);
    }
  };

  P.ajuster = function () {};

  P.elTexte = function (i) {
    var row = this.corps.querySelector('.pb[data-i="' + i + '"]');
    return row ? row.querySelector('.pb-txt') : null;
  };

  P.focus = function (i, pos, fin) {
    var row = this.corps.querySelector('.pb[data-i="' + i + '"]');
    if (!row) return;
    var el = row.querySelector('.pb-txt');
    if (!el && row.querySelector('.pb-cellule')) return this.focusCellule(i, 0, 0, pos);
    if (!el) {
      var f = row.querySelector('.pb-focusable');
      if (f) f.focus();
      return;
    }
    el.focus();
    placer(el, pos == null ? -1 : pos, fin == null ? undefined : fin);
  };

  P.focusCellule = function (i, r, c, pos) {
    var row = this.corps.querySelector('.pb[data-i="' + i + '"]');
    var cell = row && row.querySelector('.pb-cellule[data-r="' + r + '"][data-c="' + c + '"]');
    if (!cell) return;
    cell.focus();
    placer(cell, pos == null ? -1 : pos);
  };

  /* Une cellule a changé : on relit sa valeur dans le bloc tableau. */
  P.lireCellule = function (b, cell) {
    var r = Number(cell.dataset.r);
    var c = Number(cell.dataset.c);
    if (!Array.isArray(b.lignes) || !b.lignes[r]) return;
    var html = assainir(cell.innerHTML);
    if (!texteDe(cell).replace(/\n/g, '') && cell.innerHTML !== '') { cell.innerHTML = ''; html = ''; }
    b.lignes[r][c] = html;
    b.texte = texteTableau(b.lignes);
  };

  P.ctx = function (node) {
    var row = node && node.closest && node.closest('.pb');
    if (!row || !this.corps.contains(row)) return null;
    var i = Number(row.dataset.i);
    var blocs = this.blocs();
    if (!blocs[i]) return null;
    return { i: i, blocs: blocs, b: blocs[i], row: row };
  };

  /* Le bloc lit son élément : HTML assaini, texte brut. */
  P.lire = function (b, el) {
    var html = assainir(el.innerHTML);
    var txt = texteDe(el);
    if (!txt.replace(/\n/g, '') && el.innerHTML !== '') { el.innerHTML = ''; txt = ''; html = ''; }
    b.texte = txt;
    if (aMiseEnForme(html) && b.type !== 'code') b.html = html;
    else delete b.html;
  };

  /* ── Enregistrement : différences → opérations ── */

  P.modifie = function (immediat) {
    var self = this;
    if (this.opts.surChange) { try { this.opts.surChange(this); } catch (e) {} }
    if (this.lecture || !this.opts.noteId) return;
    if (this._timer) clearTimeout(this._timer);
    if (immediat) this.envoyer(true);
    else this._timer = setTimeout(function () { self._timer = null; self.envoyer(false); }, 400);
  };

  P.restructure = function (focusI, pos) {
    this.redessiner(focusI, pos);
    this.modifie();
  };

  P.ops = function () {
    var cur = this.blocs();
    var ref = this.envoye;
    var ops = [];
    var vivants = {};
    cur.forEach(function (b) { vivants[b.uid] = 1; });
    var sim = [];
    var parUid = {};
    ref.forEach(function (b) {
      if (!vivants[b.uid]) ops.push({ t: 'del', uid: b.uid });
      else { sim.push(b.uid); parUid[b.uid] = b; }
    });
    for (var k = 0; k < cur.length; k++) {
      var b = cur[k];
      var apres = k ? cur[k - 1].uid : null;
      if (!parUid[b.uid]) {
        ops.push({ t: 'ins', apres: apres, bloc: copie(b) });
        sim.splice(k, 0, b.uid);
        continue;
      }
      if (sim[k] !== b.uid) {
        ops.push({ t: 'mov', uid: b.uid, apres: apres });
        sim.splice(sim.indexOf(b.uid), 1);
        sim.splice(k, 0, b.uid);
      }
      if (signature(parUid[b.uid]) !== signature(b)) ops.push({ t: 'set', bloc: copie(b) });
    }
    return ops;
  };

  P.envoyer = function (immediat) {
    var self = this;
    if (!this._fiable || this._bloque) return Promise.resolve();
    if (this._envoi) { this._relancer = true; return this._envoi; }
    var ops = this.ops();
    if (!ops.length) return Promise.resolve();
    var avant = this.envoye;
    this.envoye = this.blocs().map(copie);
    this._envoi = fetch('/api/postits/' + this.opts.noteId + '/frappe', {
      method: 'POST',
      credentials: 'include',
      keepalive: !!immediat,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ client: _client, ops: ops }),
    }).then(function (r) {
      if (!r.ok) {
        return r.json().catch(function () { return {}; }).then(function (j) {
          var err = new Error((j && j.detail) || 'Note non enregistrée.');
          err.statut = r.status;
          throw err;
        });
      }
      return r.json();
    }).then(function (res) {
      self._erreurEnvoi = 0;
      if (self.opts.surEnregistre) { try { self.opts.surEnregistre(res); } catch (e) {} }
    }).catch(function (e) {
      /* Échec : on repartira de l'état d'avant pour renvoyer ces changements. */
      self.envoye = avant;
      var definitif = e.statut === 403 || (e.statut === 404 && e.message !== 'Not Found');
      if (definitif) {
        /* Note retirée ou devenue en lecture seule : on arrête d'envoyer. */
        self._bloque = true;
        if (self.opts.signaler) self.opts.signaler(e.message);
        return;
      }
      /* Serveur injoignable ou en cours de mise à jour (route encore absente) :
         un seul message, puis on réessaie sans bruit. */
      self._erreurEnvoi = (self._erreurEnvoi || 0) + 1;
      if (self._erreurEnvoi === 1 && self.opts.signaler) {
        self.opts.signaler('Connexion au serveur interrompue — vos modifications seront renvoyées.', 'info');
      }
      clearTimeout(self._reessai);
      self._reessai = setTimeout(function () { self.envoyer(false); }, Math.min(30000, 3000 * self._erreurEnvoi));
    }).then(function () {
      self._envoi = null;
      if (self._relancer) { self._relancer = false; self.envoyer(false); }
    });
    return this._envoi;
  };

  P.vider = function () {
    if (this._timer) { clearTimeout(this._timer); this._timer = null; }
    if (!this.lecture && this.opts.noteId) this.envoyer(true);
  };

  /* ── Flux des autres éditeurs ── */

  P.suivre = function () {
    var self = this;
    if (!this._actif) return;
    var ctrl = window.AbortController ? new AbortController() : null;
    this._ctrl = ctrl;
    var url = '/api/postits/' + this.opts.noteId + '/flux?depuis=' + this.rev + '&client=' + encodeURIComponent(_client) +
      '&bloc=' + encodeURIComponent(this._blocFocus || '') + '&sig=' + encodeURIComponent(this._sig);
    fetch(url, { credentials: 'include', signal: ctrl ? ctrl.signal : undefined })
      .then(function (r) {
        if (r.status === 404 || r.status === 403) { self._actif = false; if (self.opts.recharger) self.opts.recharger(); return null; }
        if (!r.ok) throw new Error('flux');
        return r.json();
      })
      .then(function (d) {
        if (!d || !self._actif) return;
        self._erreurs = 0;
        if (d.reset) {
          self.rev = d.revision;
          if (self.opts.recharger) self.opts.recharger();
        } else {
          (d.ops || []).forEach(function (o) { self.appliquerDistant(o); });
          self.rev = Math.max(self.rev, d.revision);
        }
        self._sig = d.sig || '';
        self._pres = d.presences || [];
        self.peindrePresences();
        if (self.opts.surPresences) { try { self.opts.surPresences(self._pres); } catch (e) {} }
        self.suivre();
      })
      .catch(function (e) {
        if (!self._actif) return;
        if (e && e.name === 'AbortError') return self.suivre();
        self._erreurs = (self._erreurs || 0) + 1;
        setTimeout(function () { self.suivre(); }, Math.min(15000, 1500 * self._erreurs));
      });
  };

  P.relancerFlux = function () {
    if (this._ctrl) { try { this._ctrl.abort(); } catch (e) {} }
  };

  P.signalerFocus = function (u) {
    if (u === this._blocFocus) return;
    this._blocFocus = u;
    var self = this;
    if (!this.opts.flux) return;
    clearTimeout(this._focusTimer);
    this._focusTimer = setTimeout(function () { self.relancerFlux(); }, 250);
  };

  P.appliquerDistant = function (o) {
    if (o.client === _client) return;
    var op = o.op || {};
    var blocs = this.blocs();
    var ref = this.envoye;
    function indice(liste, u) {
      for (var k = 0; k < liste.length; k++) if (liste[k].uid === u) return k;
      return -1;
    }
    if (op.t === 'titre') {
      if (this.opts.surTitre) this.opts.surTitre(op.titre);
      return;
    }
    if (op.t === 'com') {
      if (this.opts.surCommentaires) this.opts.surCommentaires();
      return;
    }
    if (op.t === 'set' || op.t === 'ins') {
      var b = op.bloc;
      var i = indice(blocs, b.uid);
      var j = indice(ref, b.uid);
      if (op.t === 'ins' && i < 0) {
        var a = op.apres ? indice(blocs, op.apres) : -1;
        blocs.splice(a + 1, 0, copie(b));
        var ar = op.apres ? indice(ref, op.apres) : -1;
        ref.splice(ar + 1, 0, copie(b));
        return this.redessiner();
      }
      if (i < 0) return;
      var local = blocs[i];
      var base = j >= 0 ? ref[j] : null;
      var differe = base && signature(local) !== signature(base);
      var nouveau = copie(b);
      if (differe && b.type === 'tableau' && local.type === 'tableau' && base && Array.isArray(base.lignes) &&
          JSON.stringify(dims(base)) === JSON.stringify(dims(local)) && JSON.stringify(dims(local)) === JSON.stringify(dims(b))) {
        /* Tableau modifié des deux côtés : fusion cellule par cellule. */
        nouveau.lignes = b.lignes.map(function (l, r) {
          return l.map(function (cell, c) { return fusion3(base.lignes[r][c] || '', local.lignes[r][c] || '', cell || ''); });
        });
        nouveau.texte = texteTableau(nouveau.lignes);
      } else if (differe && local.type === b.type && !OBJETS[b.type] && b.type !== 'tableau') {
        /* Les deux ont écrit dans ce bloc : on garde les deux textes. */
        var h = fusion3(htmlDe(base), htmlDe(local), htmlDe(b));
        var d = document.createElement('div');
        d.innerHTML = assainir(h);
        nouveau.texte = texteDe(d);
        if (aMiseEnForme(d.innerHTML)) nouveau.html = d.innerHTML; else delete nouveau.html;
      }
      if (j >= 0) ref[j] = copie(b);
      blocs[i] = nouveau;
      this.repeindreBloc(i, local);
      if (differe) this.modifie();
      return;
    }
    if (op.t === 'del') {
      var k1 = indice(blocs, op.uid);
      var k2 = indice(ref, op.uid);
      if (k2 >= 0) ref.splice(k2, 1);
      if (k1 < 0) return;
      /* Bloc supprimé par l'autre pendant que j'y écrivais : il revient. */
      if (k2 >= 0 && signature(blocs[k1]) !== signature(this.envoye[k2] || {})) { this.modifie(); return; }
      blocs.splice(k1, 1);
      if (!blocs.length) blocs.push({ uid: uid(), type: 'p', texte: '' });
      return this.redessiner();
    }
    if (op.t === 'mov') {
      [blocs, ref].forEach(function (liste) {
        var k = indice(liste, op.uid);
        if (k < 0) return;
        var x = liste.splice(k, 1)[0];
        var a2 = op.apres ? indice(liste, op.apres) : -1;
        liste.splice(a2 + 1, 0, x);
      });
      return this.redessiner();
    }
  };

  function dims(b) {
    return (b.lignes || []).map(function (l) { return l.length; });
  }

  /* Un seul bloc a changé : on ne touche qu'à lui (le curseur ailleurs ne bouge pas). */
  P.repeindreBloc = function (i, avant) {
    var blocs = this.blocs();
    var b = blocs[i];
    var row = this.corps.querySelector('.pb[data-uid="' + b.uid + '"]');
    if (!row || !avant || avant.type !== b.type || (avant.retrait || 0) !== (b.retrait || 0) || b.type === 'tableau') return this.redessiner();
    var el = row.querySelector('.pb-txt');
    if (b.type === 'todo') {
      var cb = row.querySelector('.pb-case');
      if (cb) cb.checked = !!b.coche;
      row.classList.toggle('coche', !!b.coche);
    }
    if (!el) return this.redessiner();
    var actif = document.activeElement === el;
    var c = actif ? curseur(el) : null;
    var ancien = texteDe(el);
    el.innerHTML = htmlDe(b);
    if (actif) {
      var neuf = texteDe(el);
      var p = 0;
      while (p < ancien.length && p < neuf.length && ancien[p] === neuf[p]) p++;
      var delta = neuf.length - ancien.length;
      var dbt = c.debut > p ? c.debut + delta : c.debut;
      var fn = c.fin > p ? c.fin + delta : c.fin;
      placer(el, Math.max(0, dbt), Math.max(0, fn));
    }
    this.peindrePresences();
  };

  /* La note entière a changé ailleurs (contenu remplacé, restauration). */
  P.remplacer = function (note) {
    this.note.blocs = note.blocs || [];
    this.note.revision = note.revision;
    this.rev = Number(note.revision || 0);
    this.envoye = this.note.blocs.map(copie);
    this._fiable = this.envoye.every(function (b) { return !!b.uid; });
    this.blocs();
    this.redessiner();
  };

  P.peindrePresences = function () {
    var corps = this.corps;
    if (this._coms) this.peindreCommentaires();
    corps.querySelectorAll('.pb.pb-autre').forEach(function (r) {
      r.classList.remove('pb-autre');
      r.style.removeProperty('--pb-autre');
      var m = r.querySelector('.pb-presence');
      if (m) { m.textContent = ''; m.removeAttribute('title'); }
    });
    var vus = {};
    (this._pres || []).forEach(function (p) {
      if (!p.bloc || vus[p.bloc]) return;
      vus[p.bloc] = 1;
      var row = corps.querySelector('.pb[data-uid="' + String(p.bloc).replace(/[^A-Za-z0-9_-]/g, '') + '"]');
      if (!row) return;
      row.classList.add('pb-autre');
      row.style.setProperty('--pb-autre', couleurDe(p.user_id));
      var m = row.querySelector('.pb-presence');
      if (m) { m.textContent = initiales(p.nom); m.title = p.nom + ' écrit ici'; }
    });
  };

  /* Insère des blocs (modèle, collage) après l'index donné ; nouveaux identifiants. */
  P.insererBlocs = function (liste, apres) {
    var blocs = this.blocs();
    var neufs = (liste || []).map(function (b) { var x = copie(b); x.uid = uid(); return x; });
    if (!neufs.length) return;
    var at = apres == null || apres < 0 ? blocs.length - 1 : apres;
    var cible = blocs[at];
    if (cible && cible.type === 'p' && !cible.texte && !cible.html) blocs.splice(at, 1, ...neufs);
    else blocs.splice(at + 1, 0, ...neufs);
    this.restructure(Math.min(blocs.length - 1, (cible && !cible.texte ? at : at + 1)), -1);
  };

  /* Commentaires ouverts par bloc : {uid: nombre}, repeints à chaque dessin. */
  P.marquerCommentaires = function (parUid) {
    this._coms = parUid || {};
    this.peindreCommentaires();
  };

  P.peindreCommentaires = function () {
    var coms = this._coms || {};
    this.corps.querySelectorAll('.pb-com').forEach(function (x) { x.remove(); });
    var corps = this.corps;
    Object.keys(coms).forEach(function (u) {
      var row = corps.querySelector('.pb[data-uid="' + String(u).replace(/[^A-Za-z0-9_-]/g, '') + '"]');
      if (!row || !coms[u]) return;
      var b = document.createElement('button');
      b.type = 'button';
      b.className = 'pb-com';
      b.dataset.comUid = u;
      b.title = coms[u] + ' commentaire' + (coms[u] > 1 ? 's' : '');
      b.textContent = String(coms[u]);
      row.appendChild(b);
    });
  };

  P.effacerCochees = function () {
    this.note.blocs = this.blocs().filter(function (b) { return !(b.type === 'todo' && b.coche); });
    this.redessiner();
    this.modifie(true);
  };

  P.ouvrirCommandes = function () {
    if (this.lecture) return;
    var blocs = this.blocs();
    var der = blocs[blocs.length - 1];
    if (!(der && der.type === 'p' && !der.texte)) blocs.push({ uid: uid(), type: 'p', texte: '' });
    var i = blocs.length - 1;
    blocs[i].texte = '/';
    delete blocs[i].html;
    this.redessiner(i, 1);
    var el = this.elTexte(i);
    if (el) ouvrirSlash(this, el, 0);
  };

  /* Bloc où agit le panneau d'actions : celui qui a le curseur, sinon le
     dernier visité, sinon une ligne vide en bas de la note. */
  P.cible = function () {
    var ae = document.activeElement;
    if (ae && this.corps.contains(ae) && (ae.classList.contains('pb-txt') || ae.classList.contains('pb-cellule'))) return ae;
    var k = this._dernierUid ? this.indexUid(this._dernierUid) : -1;
    if (k >= 0 && this.elTexte(k)) {
      var pos = this._dernierPos == null ? -1 : this._dernierPos;
      this.focus(k, pos);
      return this.elTexte(k);
    }
    this.focusFin();
    var bl = this.blocs();
    return this.elTexte(bl.length - 1);
  };

  /* Commande lancée depuis le panneau d'actions de /note. */
  P.commande = function (cle) {
    if (this.lecture) return;
    var fmt = { gras: 'bold', italique: 'italic', souligne: 'underline', barre: 'strikeThrough', code_ligne: 'code', lien_texte: 'lien' }[cle];
    var el = this.cible();
    if (!el) return;
    if (fmt) {
      var sel = window.getSelection();
      if (fmt !== 'lien' && (!sel || sel.isCollapsed)) {
        if (this.opts.signaler) this.opts.signaler('Sélectionnez d\'abord le texte à mettre en forme.', 'info');
        return;
      }
      return formater(this, el, fmt);
    }
    var cmd = null;
    commandesDe(this).forEach(function (x) { if (x.cle === cle) cmd = x; });
    var c = this.ctx(el);
    if (!cmd || !c) return;
    relire(this, c.b, el);
    executer(this, el, c, cmd, curseur(el).debut, true);
  };

  P.focusFin = function () {
    if (this.lecture) return;
    var blocs = this.blocs();
    var der = blocs[blocs.length - 1];
    if (der && der.type === 'p' && !der.texte) return this.focus(blocs.length - 1, 0);
    blocs.push({ uid: uid(), type: 'p', texte: '' });
    this.restructure(blocs.length - 1, 0);
  };

  P.detruire = function () {
    this.vider();
    this._actif = false;
    this.relancerFlux();
    if (this.opts.noteId && this.opts.flux) {
      try {
        var corps = JSON.stringify({ client: _client });
        if (navigator.sendBeacon) navigator.sendBeacon('/api/postits/' + this.opts.noteId + '/presence-fin', new Blob([corps], { type: 'application/json' }));
      } catch (e) {}
    }
    if (_slash && _slash.ed === this) fermerSlash();
    var k = _editeurs.indexOf(this);
    if (k >= 0) _editeurs.splice(k, 1);
  };

  /* ── Images ── */

  P.insererImages = function (fichiers, apresIndex) {
    var self = this;
    if (!this.opts.noteId) return;
    var liste = Array.prototype.filter.call(fichiers || [], function (f) { return /^image\//.test(f.type); });
    if (!liste.length) return;
    var pos = apresIndex == null ? this.blocs().length - 1 : apresIndex;
    liste.reduce(function (prom, f) {
      return prom.then(function () {
        if (f.size > IMAGE_MAX) { if (self.opts.signaler) self.opts.signaler('Image trop lourde — 10 Mo au plus.'); return; }
        var fd = new FormData();
        fd.append('fichier', f, f.name || 'image.png');
        if (self.opts.signaler) self.opts.signaler('Envoi de l\'image…', 'info');
        return fetch('/api/postits/' + self.opts.noteId + '/images', { method: 'POST', credentials: 'include', body: fd })
          .then(function (r) { return r.json().then(function (j) { if (!r.ok) throw new Error(j.detail || 'Image refusée.'); return j; }); })
          .then(function (img) {
            var blocs = self.blocs();
            var b = { uid: uid(), type: 'image', texte: '', ref: img.id, largeur: 100 };
            var cible = blocs[pos];
            if (cible && cible.type === 'p' && !cible.texte) blocs[pos] = b;
            else { pos += 1; blocs.splice(pos, 0, b); }
            self.redessiner();
            self.modifie(true);
          })
          .catch(function (e) { if (self.opts.signaler) self.opts.signaler(e.message || 'Image refusée.'); });
      });
    }, Promise.resolve());
  };

  P.choisirImage = function (apresIndex) {
    var self = this;
    var inp = document.createElement('input');
    inp.type = 'file';
    inp.accept = 'image/png,image/jpeg,image/gif,image/webp';
    inp.multiple = true;
    inp.onchange = function () { self.insererImages(inp.files, apresIndex); };
    inp.click();
  };

  /* ── Présence : initiales et couleur ── */

  function initiales(nom) {
    var m = String(nom || '?').trim().split(/\s+/);
    return ((m[0] || '?')[0] + (m.length > 1 ? m[m.length - 1][0] : '')).toUpperCase();
  }
  function couleurDe(id) {
    return COULEURS[Math.abs(Number(id) || 0) % COULEURS.length];
  }

  /* ── Événements ───────────────────────────────────────────────────────── */

  function blocDepuisLigne(ligne) {
    var m = /^(\s*)(#{1,3}|[-*•]|\d+[.)]|\[[ xX]?\]|>)\s+(.*)$/.exec(ligne);
    if (!m) return { uid: uid(), type: 'p', texte: ligne };
    var r = Math.min(RETRAIT_MAX, Math.floor(m[1].replace(/\t/g, '  ').length / 2));
    var k = m[2];
    var b = { uid: uid(), texte: m[3] };
    if (k.charAt(0) === '#') b.type = 'h' + k.length;
    else if (/^[-*•]$/.test(k)) b.type = 'puce';
    else if (/^\d/.test(k)) b.type = 'num';
    else if (k === '>') b.type = 'citation';
    else { b.type = 'todo'; b.coche = /x/i.test(k); }
    if (r) b.retrait = r;
    return b;
  }

  function normaliserLien(u) {
    u = String(u || '').trim();
    if (!u) return '';
    if (/^[\w.+-]+@[\w-]+\.[\w.-]+$/.test(u)) return 'mailto:' + u;
    if (!/^(https?:\/\/|mailto:|\/)/i.test(u)) u = 'https://' + u;
    return LIEN_OK.test(u) ? u : '';
  }

  function surCollage(ed, e) {
    if (ed.lecture) return;
    if (e.target.classList && e.target.classList.contains('pb-cellule')) {
      var cc = ed.ctx(e.target);
      if (cc) collerCellule(ed, e, cc);
      return;
    }
    var cd = e.clipboardData;
    var fichiers = cd && cd.files && cd.files.length ? cd.files : null;
    var cible = e.target.closest && e.target.closest('.pb');
    if (fichiers && Array.prototype.some.call(fichiers, function (f) { return /^image\//.test(f.type); })) {
      e.preventDefault();
      var c0 = ed.ctx(e.target);
      ed.insererImages(fichiers, c0 ? c0.i : null);
      return;
    }
    var el = e.target.closest && e.target.closest('.pb-txt');
    if (!el) {
      if (e.target.classList && e.target.classList.contains('pb-legende')) {
        e.preventDefault();
        document.execCommand('insertText', false, ((cd && cd.getData('text/plain')) || '').replace(/\s+/g, ' '));
      }
      return;
    }
    var c = ed.ctx(el);
    if (!c) return;
    var txt = (cd && cd.getData('text/plain')) || '';
    var html = (cd && cd.getData('text/html')) || '';
    e.preventDefault();
    /* Une adresse collée sur du texte sélectionné en fait un lien. */
    var sel = window.getSelection();
    var url = normaliserLien(txt);
    if (url && /^\S+$/.test(txt.trim()) && /^(https?:|www\.)/i.test(txt.trim()) && sel && !sel.isCollapsed && c.b.type !== 'code') {
      document.execCommand('createLink', false, url);
      ed.lire(c.b, el);
      ed.modifie();
      return;
    }
    if (c.b.type === 'code' || txt.indexOf('\n') < 0) {
      if (html && c.b.type !== 'code' && txt.indexOf('\n') < 0) {
        var propre = assainir(html);
        if (aMiseEnForme(propre)) document.execCommand('insertHTML', false, propre);
        else document.execCommand('insertText', false, txt);
      } else {
        document.execCommand('insertText', false, txt);
      }
      ed.lire(c.b, el);
      ed.modifie();
      return;
    }
    var lignes = txt.replace(/\r\n?/g, '\n').split('\n');
    while (lignes.length && !lignes[lignes.length - 1].trim()) lignes.pop();
    if (!lignes.length) return;
    var nouveaux = lignes.slice(1).map(blocDepuisLigne);
    if (nouveaux.length + c.blocs.length > BLOCS_MAX) {
      if (ed.opts.signaler) ed.opts.signaler('Note trop longue — ' + BLOCS_MAX + ' blocs au plus.');
      return;
    }
    var parts = couper(el);
    var avantVide = !texteDe(el);
    if (avantVide && c.b.type === 'p') {
      var tete = blocDepuisLigne(lignes[0]);
      c.b.type = tete.type;
      c.b.texte = tete.texte;
      delete c.b.html;
      if (tete.coche != null) c.b.coche = tete.coche;
      if (tete.retrait) c.b.retrait = tete.retrait;
    } else {
      var d = document.createElement('div');
      d.innerHTML = parts[0] + esc(lignes[0]);
      c.b.texte = texteDe(d);
      if (aMiseEnForme(d.innerHTML)) c.b.html = d.innerHTML; else delete c.b.html;
    }
    var dernier = nouveaux.length ? nouveaux[nouveaux.length - 1] : c.b;
    var pos = (dernier.texte || '').length;
    if (parts[1]) {
      var d2 = document.createElement('div');
      d2.innerHTML = htmlDe(dernier) + parts[1];
      dernier.texte = texteDe(d2);
      if (aMiseEnForme(d2.innerHTML)) dernier.html = d2.innerHTML; else delete dernier.html;
    }
    Array.prototype.splice.apply(c.blocs, [c.i + 1, 0].concat(nouveaux));
    ed.restructure(c.i + nouveaux.length, pos);
    void cible;
  }

  function surSaisie(ed, e) {
    if (_interne) return;
    var el = e.target;
    if (el.classList && el.classList.contains('pb-legende')) {
      var cl = ed.ctx(el);
      if (cl) { cl.b.legende = el.textContent.replace(/\s+/g, ' ').trim(); ed.modifie(); }
      return;
    }
    if (el.classList && el.classList.contains('pb-cellule')) {
      var ct = ed.ctx(el);
      if (ct) { ed.lireCellule(ct.b, el); ed.modifie(); }
      return;
    }
    if (!el.classList || !el.classList.contains('pb-txt')) return;
    var c = ed.ctx(el);
    if (!c) return;
    var cur = curseur(el);
    var pos = cur.debut;
    _remp = null;
    var txt = texteDe(el);
    if (e.inputType === 'insertText' && c.b.type !== 'code' && cur.debut === cur.fin) {
      var avant = txt.slice(0, pos);
      for (var k = 0; k < REMPLACEMENTS.length; k++) {
        var seq = REMPLACEMENTS[k][0];
        if (avant.slice(-seq.length) !== seq) continue;
        var signe = REMPLACEMENTS[k][1];
        remplacerTexte(el, pos - seq.length, pos, signe);
        pos = pos - seq.length + signe.length;
        _remp = { el: el, pos: pos, tape: seq === '←>' ? '<-->' : seq, signe: signe };
        txt = texteDe(el);
        break;
      }
    }
    if (e.inputType === 'insertText' && e.data === ' ' && c.b.type === 'p') {
      var t = RACCOURCIS[txt.slice(0, pos - 1)];
      if (t) {
        remplacerTexte(el, 0, pos, '');
        ed.lire(c.b, el);
        c.b.type = t;
        if (t === 'todo') c.b.coche = false;
        fermerSlash();
        ed.restructure(c.i, 0);
        return;
      }
    }
    if (c.b.type === 'p' && (txt === '---' || txt === '```')) {
      if (txt === '---') {
        c.b.type = 'sep'; c.b.texte = ''; delete c.b.html;
        c.blocs.splice(c.i + 1, 0, { uid: uid(), type: 'p', texte: '' });
        ed.restructure(c.i + 1, 0);
      } else {
        c.b.type = 'code'; c.b.texte = ''; delete c.b.html;
        ed.restructure(c.i, 0);
      }
      return;
    }
    ed.lire(c.b, el);
    if (_ref && _ref.el === el) majRef();
    else if (e.data === '@' && c.b.type !== 'code' && ed.opts.noteId) {
      var prec0 = txt.charAt(pos - 2);
      if (pos === 1 || /\s|\(/.test(prec0)) ouvrirRef(ed, el, pos - 1);
    }
    if (_slash && _slash.el === el) majSlash();
    else if (e.data === '/' && c.b.type !== 'code') {
      var precedent = txt.charAt(pos - 2);
      if (pos === 1 || /\s/.test(precedent)) ouvrirSlash(ed, el, pos - 1);
    }
    ed.modifie();
  }

  function surChangement(ed, e) {
    var cb = e.target;
    if (!cb.classList || !cb.classList.contains('pb-case')) return;
    var c = ed.ctx(cb);
    if (!c) return;
    c.b.coche = !!cb.checked;
    c.row.classList.toggle('coche', c.b.coche);
    ed.modifie();
  }

  function surToucheObjet(ed, e, c) {
    var k = e.key;
    if (ed.lecture) return;
    if (e.target.classList.contains('pb-legende')) {
      if (k === 'Enter') {
        e.preventDefault();
        c.blocs.splice(c.i + 1, 0, { uid: uid(), type: 'p', texte: '' });
        ed.restructure(c.i + 1, 0);
      }
      return;
    }
    if (k === 'Backspace' || k === 'Delete') {
      e.preventDefault();
      c.blocs.splice(c.i, 1);
      if (!c.blocs.length) c.blocs.push({ uid: uid(), type: 'p', texte: '' });
      ed.restructure(Math.max(0, c.i - (k === 'Backspace' ? 1 : 0)), k === 'Backspace' ? -1 : 0);
    } else if (k === 'Enter') {
      e.preventDefault();
      if (c.b.type === 'page' && e.target.href) { location.href = e.target.href; return; }
      c.blocs.splice(c.i + 1, 0, { uid: uid(), type: 'p', texte: '' });
      ed.restructure(c.i + 1, 0);
    } else if (k === 'ArrowUp' && c.i > 0) {
      e.preventDefault();
      ed.focus(c.i - 1, -1);
    } else if (k === 'ArrowDown' && c.i < c.blocs.length - 1) {
      e.preventDefault();
      ed.focus(c.i + 1, 0);
    }
  }

  function basculerCode() {
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount || sel.isCollapsed) return;
    var r = sel.getRangeAt(0);
    var anc = r.commonAncestorContainer;
    var code = (anc.nodeType === 1 ? anc : anc.parentNode).closest('code');
    if (code) {
      var parent = code.parentNode;
      while (code.firstChild) parent.insertBefore(code.firstChild, code);
      parent.removeChild(code);
      return;
    }
    var txt = r.toString();
    document.execCommand('insertHTML', false, '<code>' + esc(txt) + '</code>');
  }

  function formater(ed, el, commande) {
    if (commande === 'code') basculerCode();
    else if (commande === 'lien') return ouvrirLien(ed, el);
    else document.execCommand(commande, false);
    var c = ed.ctx(el);
    if (c && el.classList.contains('pb-cellule')) ed.lireCellule(c.b, el);
    else if (c) ed.lire(c.b, el);
    if (c) ed.modifie();
    majBarre();
  }

  /* Relit un bloc ou une cellule de tableau après une modification. */
  function relire(ed, b, el) {
    if (el.classList.contains('pb-cellule')) ed.lireCellule(b, el);
    else ed.lire(b, el);
  }

  function basculer(ed, b) {
    if (_plies[b.uid]) delete _plies[b.uid]; else _plies[b.uid] = 1;
    memoriserPlies();
    ed.redessiner();
  }

  /* ── Tableau : clavier, collage, outils ── */

  function changerTableau(ed, c, action, r, col) {
    var b = c.b;
    var L = b.lignes;
    var nbCol = L[0] ? L[0].length : 1;
    if (action === 'ligne') {
      if (L.length >= TAB_LIGNES_MAX) return ed.opts.signaler && ed.opts.signaler('Tableau limité à ' + TAB_LIGNES_MAX + ' lignes.');
      var at = r == null ? L.length : r + 1;
      L.splice(at, 0, new Array(nbCol).fill(''));
      r = at;
    } else if (action === 'colonne') {
      if (nbCol >= TAB_COLONNES_MAX) return ed.opts.signaler && ed.opts.signaler('Tableau limité à ' + TAB_COLONNES_MAX + ' colonnes.');
      var atc = col == null ? nbCol : col + 1;
      L.forEach(function (l) { l.splice(atc, 0, ''); });
      col = atc;
    } else if (action === 'moins-ligne') {
      if (L.length <= 1) return;
      L.splice(r == null ? L.length - 1 : r, 1);
      r = Math.min(r == null ? 0 : r, L.length - 1);
    } else if (action === 'moins-colonne') {
      if (nbCol <= 1) return;
      L.forEach(function (l) { l.splice(col == null ? nbCol - 1 : col, 1); });
      col = Math.min(col == null ? 0 : col, nbCol - 2);
    } else if (action === 'entete') {
      b.entete = !b.entete;
    }
    b.texte = texteTableau(L);
    ed.redessiner();
    ed.focusCellule(c.i, r || 0, col || 0, -1);
    ed.modifie();
  }

  function surToucheCellule(ed, e, c) {
    var cell = e.target;
    var r = Number(cell.dataset.r);
    var col = Number(cell.dataset.c);
    var L = c.b.lignes;
    var nbCol = L[0].length;
    var mod = e.metaKey || e.ctrlKey;
    if (mod && !e.altKey) {
      var touche = e.key.toLowerCase();
      var cmd = !e.shiftKey && touche === 'b' ? 'bold' : !e.shiftKey && touche === 'i' ? 'italic'
        : !e.shiftKey && touche === 'u' ? 'underline' : e.shiftKey && (touche === 's' || touche === 'x') ? 'strikeThrough'
        : !e.shiftKey && touche === 'e' ? 'code' : !e.shiftKey && touche === 'k' ? 'lien' : null;
      if (cmd) { e.preventDefault(); e.stopPropagation(); formater(ed, cell, cmd); return; }
    }
    if (e.key === 'Tab') {
      e.preventDefault();
      var k = r * nbCol + col + (e.shiftKey ? -1 : 1);
      if (k < 0) return;
      if (k >= L.length * nbCol) return changerTableau(ed, c, 'ligne', L.length - 1, 0);
      ed.focusCellule(c.i, Math.floor(k / nbCol), k % nbCol, -1);
      return;
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (r + 1 >= L.length) return changerTableau(ed, c, 'ligne', r, col);
      ed.focusCellule(c.i, r + 1, col, -1);
      return;
    }
    if (e.key === 'Enter' && e.shiftKey) {
      e.preventDefault();
      document.execCommand('insertLineBreak') || document.execCommand('insertHTML', false, '<br><br>');
      ed.lireCellule(c.b, cell);
      ed.modifie();
      return;
    }
    if (e.key === 'ArrowUp' && premiereLigne(cell)) {
      e.preventDefault();
      if (r > 0) ed.focusCellule(c.i, r - 1, col, -1); else if (c.i > 0) ed.focus(c.i - 1, -1);
      return;
    }
    if (e.key === 'ArrowDown' && derniereLigne(cell)) {
      e.preventDefault();
      if (r + 1 < L.length) ed.focusCellule(c.i, r + 1, col, 0);
      else if (c.i + 1 < c.blocs.length) ed.focus(c.i + 1, 0);
      else { c.blocs.push({ uid: uid(), type: 'p', texte: '' }); ed.restructure(c.i + 1, 0); }
      return;
    }
    if (e.key === 'Escape') cell.blur();
  }

  /* Coller une grille (Excel, tableur) : elle remplit le tableau depuis la cellule. */
  function collerCellule(ed, e, c) {
    var cd = e.clipboardData;
    var txt = (cd && cd.getData('text/plain')) || '';
    e.preventDefault();
    if (txt.indexOf('\t') < 0 && txt.replace(/\r?\n$/, '').indexOf('\n') < 0) {
      document.execCommand('insertText', false, txt.replace(/\r?\n$/, ''));
      ed.lireCellule(c.b, e.target);
      ed.modifie();
      return;
    }
    var grille = txt.replace(/\r\n?/g, '\n').replace(/\n$/, '').split('\n').map(function (l) { return l.split('\t'); });
    var r0 = Number(e.target.dataset.r);
    var c0 = Number(e.target.dataset.c);
    var L = c.b.lignes;
    grille.forEach(function (ligne, dr) {
      var r = r0 + dr;
      if (r >= TAB_LIGNES_MAX) return;
      while (L.length <= r) L.push(new Array(L[0].length).fill(''));
      ligne.forEach(function (val, dc) {
        var col = c0 + dc;
        if (col >= TAB_COLONNES_MAX) return;
        while (L[0].length <= col) L.forEach(function (l) { l.push(''); });
        L[r][col] = esc(val).replace(/&#39;/g, "'").replace(/&quot;/g, '"');
      });
    });
    c.b.texte = texteTableau(L);
    ed.redessiner();
    ed.focusCellule(c.i, r0, c0, -1);
    ed.modifie();
  }

  function surTouche(ed, e) {
    if (e.isComposing) return;
    var t = e.target;
    var c = ed.ctx(t);
    if (!c) return;
    if (t.classList.contains('pb-focusable') || t.classList.contains('pb-legende')) return surToucheObjet(ed, e, c);
    if (t.classList.contains('pb-cellule')) { if (!ed.lecture) surToucheCellule(ed, e, c); return; }
    if (!t.classList.contains('pb-txt') || ed.lecture) return;
    if (_slash && _slash.el === t && toucheSlash(e)) return;
    if (_ref && _ref.el === t && toucheRef(e)) return;
    var el = t;
    var v = texteDe(el);
    var cur = curseur(el);
    var s = cur.debut;
    var f = cur.fin;
    var b = c.b;
    var mod = e.metaKey || e.ctrlKey;
    var r0 = _remp;
    _remp = null;

    /* Mise en forme : Cmd (Mac) ou Ctrl (Windows). */
    if (mod && !e.altKey && b.type !== 'code') {
      var touche = e.key.toLowerCase();
      var cmd = !e.shiftKey && touche === 'b' ? 'bold'
        : !e.shiftKey && touche === 'i' ? 'italic'
        : !e.shiftKey && touche === 'u' ? 'underline'
        : e.shiftKey && (touche === 's' || touche === 'x') ? 'strikeThrough'
        : !e.shiftKey && touche === 'e' ? 'code'
        : !e.shiftKey && touche === 'k' ? 'lien' : null;
      if (cmd) {
        e.preventDefault();
        e.stopPropagation();
        formater(ed, el, cmd);
        return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey && b.type === 'bascule') {
      e.preventDefault();
      if (mod) { basculer(ed, c.b); return; }
      /* Entrée sur un titre repliable : on écrit dedans (bloc décalé dessous). */
      var p2 = couper(el);
      var d0 = document.createElement('div');
      d0.innerHTML = p2[0];
      b.texte = texteDe(d0);
      if (aMiseEnForme(p2[0])) b.html = p2[0]; else delete b.html;
      var enfant = { uid: uid(), type: 'p', texte: '', retrait: Math.min(RETRAIT_MAX, (b.retrait || 0) + 1) };
      var d3 = document.createElement('div');
      d3.innerHTML = p2[1];
      enfant.texte = texteDe(d3);
      if (aMiseEnForme(p2[1])) enfant.html = p2[1];
      delete _plies[b.uid];
      memoriserPlies();
      c.blocs.splice(c.i + 1, 0, enfant);
      ed.restructure(c.i + 1, 0);
      return;
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      if (mod && b.type === 'todo') {
        e.preventDefault();
        b.coche = !b.coche;
        ed.restructure(c.i, s);
        return;
      }
      if (b.type === 'code' && !mod) {
        e.preventDefault();
        document.execCommand('insertLineBreak') || document.execCommand('insertHTML', false, '<br>');
        ed.lire(b, el);
        ed.modifie();
        return;
      }
      e.preventDefault();
      if (v === '' && LISTES[b.type]) {
        if (b.retrait) b.retrait--;
        else b.type = 'p';
        ed.restructure(c.i, 0);
        return;
      }
      var parts = couper(el);
      var suite = { uid: uid(), type: LISTES[b.type] ? b.type : 'p', texte: '' };
      if (b.retrait) suite.retrait = b.retrait;
      if (suite.type === 'todo') suite.coche = false;
      if (s === 0 && v !== '') {
        /* Entrée en début de bloc : une ligne vide au-dessus, le bloc ne bouge pas. */
        var vide = { uid: uid(), type: suite.type, texte: '' };
        if (b.retrait) vide.retrait = b.retrait;
        el.innerHTML = parts[1];
        ed.lire(b, el);
        c.blocs.splice(c.i, 0, vide);
        ed.restructure(c.i + 1, 0);
        return;
      }
      var d1 = document.createElement('div');
      d1.innerHTML = parts[0];
      b.texte = texteDe(d1);
      if (aMiseEnForme(parts[0])) b.html = parts[0]; else delete b.html;
      var d2 = document.createElement('div');
      d2.innerHTML = parts[1];
      suite.texte = texteDe(d2);
      if (aMiseEnForme(parts[1])) suite.html = parts[1];
      c.blocs.splice(c.i + 1, 0, suite);
      ed.restructure(c.i + 1, 0);
      return;
    }

    if (e.key === 'Enter' && e.shiftKey) {
      e.preventDefault();
      document.execCommand('insertLineBreak') || document.execCommand('insertHTML', false, '<br><br>');
      ed.lire(b, el);
      ed.modifie();
      return;
    }

    if (e.key === 'Backspace' && r0 && r0.el === el && s === f && s === r0.pos && v.slice(s - r0.signe.length, s) === r0.signe) {
      e.preventDefault();
      remplacerTexte(el, s - r0.signe.length, s, r0.tape);
      ed.lire(b, el);
      ed.modifie();
      return;
    }

    if (e.key === 'Backspace' && s === 0 && f === 0) {
      if (b.type !== 'p') {
        e.preventDefault();
        b.type = 'p';
        delete b.coche;
        ed.restructure(c.i, 0);
        return;
      }
      if (b.retrait) {
        e.preventDefault();
        b.retrait--;
        ed.restructure(c.i, 0);
        return;
      }
      if (c.i === 0) return;
      e.preventDefault();
      var prec = c.blocs[c.i - 1];
      if (NON_TEXTE[prec.type]) {
        if (v === '') { c.blocs.splice(c.i, 1); ed.restructure(c.i - 1, 0); }
        else ed.focus(c.i - 1, 0);
        return;
      }
      var pos = (prec.texte || '').length;
      var dm = document.createElement('div');
      dm.innerHTML = assainir(htmlDe(prec) + el.innerHTML);
      prec.texte = texteDe(dm);
      if (aMiseEnForme(dm.innerHTML)) prec.html = dm.innerHTML; else delete prec.html;
      c.blocs.splice(c.i, 1);
      ed.restructure(c.i - 1, pos);
      return;
    }

    if (e.key === 'Delete' && s === v.length && f === s && c.i < c.blocs.length - 1) {
      var suiv = c.blocs[c.i + 1];
      if (suiv.type === 'page' || suiv.type === 'image' || suiv.type === 'tableau') return;
      e.preventDefault();
      if (suiv.type !== 'sep') {
        var dd = document.createElement('div');
        dd.innerHTML = assainir(el.innerHTML + htmlDe(suiv));
        b.texte = texteDe(dd);
        if (aMiseEnForme(dd.innerHTML)) b.html = dd.innerHTML; else delete b.html;
      }
      c.blocs.splice(c.i + 1, 1);
      ed.restructure(c.i, s);
      return;
    }

    if (e.key === 'Tab') {
      e.preventDefault();
      var r = Math.max(0, Math.min(RETRAIT_MAX, (b.retrait || 0) + (e.shiftKey ? -1 : 1)));
      if (r === (b.retrait || 0)) return;
      if (r) b.retrait = r; else delete b.retrait;
      ed.lire(b, el);
      ed.restructure(c.i, s);
      return;
    }

    if (e.key === 'ArrowUp' && !e.shiftKey && s === f && c.i > 0 && premiereLigne(el)) {
      e.preventDefault();
      ed.focus(c.i - 1, -1);
      return;
    }
    if (e.key === 'ArrowDown' && !e.shiftKey && s === f && c.i < c.blocs.length - 1 && derniereLigne(el)) {
      e.preventDefault();
      ed.focus(c.i + 1, 0);
      return;
    }
    if (e.key === 'Escape') el.blur();
  }

  /* Glisser-déposer d'un bloc par sa poignée ; dépôt d'images depuis l'ordinateur. */
  function brancherGlisser(ed) {
    var corps = ed.corps;
    function nettoyer() {
      corps.querySelectorAll('.pb-drop-avant, .pb-drop-apres, .pb-glisse').forEach(function (el) {
        el.classList.remove('pb-drop-avant', 'pb-drop-apres', 'pb-glisse');
      });
    }
    corps.addEventListener('dragstart', function (e) {
      var poignee = e.target.closest && e.target.closest('.pb-poignee');
      if (!poignee) return;
      var c = ed.ctx(poignee);
      if (!c) return;
      _drag = { ed: ed, i: c.i };
      c.row.classList.add('pb-glisse');
      try {
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/plain', String(c.b.texte || ''));
        e.dataTransfer.setDragImage(c.row, 12, 12);
      } catch (err) {}
    });
    corps.addEventListener('dragover', function (e) {
      var fichiers = e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types || [], 'Files') >= 0;
      if (!(_drag && _drag.ed === ed) && !fichiers) return;
      var row = e.target.closest && e.target.closest('.pb');
      if (!row) return;
      e.preventDefault();
      var rect = row.getBoundingClientRect();
      var apres = e.clientY > rect.top + rect.height / 2;
      corps.querySelectorAll('.pb-drop-avant, .pb-drop-apres').forEach(function (el) {
        el.classList.remove('pb-drop-avant', 'pb-drop-apres');
      });
      row.classList.add(apres ? 'pb-drop-apres' : 'pb-drop-avant');
    });
    corps.addEventListener('drop', function (e) {
      var row = e.target.closest && e.target.closest('.pb');
      var fichiers = e.dataTransfer && e.dataTransfer.files;
      if (!(_drag && _drag.ed === ed) && fichiers && fichiers.length && !ed.lecture) {
        e.preventDefault();
        var at = row ? Number(row.dataset.i) - (row.classList.contains('pb-drop-apres') ? 0 : 1) : null;
        nettoyer();
        ed.insererImages(fichiers, at);
        return;
      }
      if (!_drag || _drag.ed !== ed) return;
      e.preventDefault();
      var de = _drag.i;
      _drag = null;
      if (!row) return nettoyer();
      var vers = Number(row.dataset.i) + (row.classList.contains('pb-drop-apres') ? 1 : 0);
      nettoyer();
      if (vers === de || vers === de + 1) return;
      var blocs = ed.blocs();
      var b = blocs.splice(de, 1)[0];
      if (vers > de) vers--;
      blocs.splice(vers, 0, b);
      ed.restructure(vers, -1);
    });
    corps.addEventListener('dragend', function () {
      _drag = null;
      nettoyer();
    });
  }

  function brancher(ed) {
    var corps = ed.corps;
    corps.addEventListener('input', function (e) { surSaisie(ed, e); });
    corps.addEventListener('keydown', function (e) { surTouche(ed, e); });
    corps.addEventListener('change', function (e) { surChangement(ed, e); });
    corps.addEventListener('paste', function (e) { surCollage(ed, e); });
    corps.addEventListener('mousedown', function (e) {
      if (e.target.closest && e.target.closest('[data-tab], [data-basculer]')) { e.preventDefault(); return; }
      if (e.target !== corps) return;
      e.preventDefault();
      ed.focusFin();
    });
    corps.addEventListener('click', function (e) {
      var com = e.target.closest && e.target.closest('.pb-com');
      if (com) {
        if (ed.opts.ouvrirCommentaires) ed.opts.ouvrirCommentaires(com.dataset.comUid);
        return;
      }
      var chevron = e.target.closest && e.target.closest('[data-basculer]');
      if (chevron) {
        var cb0 = ed.ctx(chevron);
        if (cb0) basculer(ed, cb0.b);
        return;
      }
      var vide = e.target.closest && e.target.closest('.pb-bascule-vide');
      if (vide && !ed.lecture) {
        var at = Number(vide.dataset.apres);
        var parent = ed.blocs()[at];
        if (parent) {
          ed.blocs().splice(at + 1, 0, { uid: uid(), type: 'p', texte: '', retrait: Math.min(RETRAIT_MAX, (parent.retrait || 0) + 1) });
          ed.restructure(at + 1, 0);
        }
        return;
      }
      var outil = e.target.closest && e.target.closest('[data-tab]');
      if (outil && !ed.lecture) {
        var ct = ed.ctx(outil);
        if (!ct) return;
        var dern = ed._celluleActive && ed._celluleActive.uid === ct.b.uid ? ed._celluleActive : { r: null, c: null };
        changerTableau(ed, ct, outil.dataset.tab, dern.r, dern.c);
        return;
      }
      var largeur = e.target.closest && e.target.closest('[data-largeur]');
      if (largeur && !ed.lecture) {
        var c = ed.ctx(largeur);
        if (c) { c.b.largeur = Number(largeur.dataset.largeur); ed.redessiner(); ed.modifie(); }
        return;
      }
      var a = e.target.closest && e.target.closest('.pb-txt a[href]');
      if (!a) return;
      e.preventDefault();
      /* Dans le texte : Cmd/Ctrl + clic ou lecture seule ouvre ; un clic simple propose. */
      if (e.metaKey || e.ctrlKey || ed.lecture) {
        window.open(a.getAttribute('href'), '_blank', 'noopener');
        return;
      }
      ouvrirBulleLien(ed, a);
    });
    corps.addEventListener('focusin', function (e) {
      var row = e.target.closest && e.target.closest('.pb');
      ed.signalerFocus(row ? row.dataset.uid : null);
      if (row && e.target.classList.contains('pb-txt')) ed._dernierUid = row.dataset.uid;
      if (row && e.target.classList.contains('pb-cellule')) {
        ed._celluleActive = { uid: row.dataset.uid, r: Number(e.target.dataset.r), c: Number(e.target.dataset.c) };
      }
    });
    corps.addEventListener('focusout', function (e) {
      if (e.target.classList && e.target.classList.contains('pb-txt')) ed._dernierPos = curseur(e.target).fin;
      var vers = e.relatedTarget;
      if (vers && corps.contains(vers)) return;
      if (_slash && _slash.ed === ed) fermerSlash();
      if (_ref && _ref.ed === ed) fermerRef();
      ed.signalerFocus(null);
      ed.vider();
    });
    if (!ed.lecture) brancherGlisser(ed);
  }

  /* ── Barre de mise en forme (au-dessus d'une sélection) ── */

  var BOUTONS_BARRE = [
    ['bold', '<b>G</b>', 'Gras (Cmd/Ctrl + B)'],
    ['italic', '<i>I</i>', 'Italique (Cmd/Ctrl + I)'],
    ['underline', '<u>S</u>', 'Souligné (Cmd/Ctrl + U)'],
    ['strikeThrough', '<s>B</s>', 'Barré (Cmd/Ctrl + Maj + S)'],
    ['code', '<code>&lt;/&gt;</code>', 'Code (Cmd/Ctrl + E)'],
    ['lien', '↗ Lien', 'Lien (Cmd/Ctrl + K)'],
  ];

  function barre() {
    if (_barre) return _barre;
    _barre = document.createElement('div');
    _barre.id = 'nted-barre';
    _barre.setAttribute('role', 'toolbar');
    _barre.setAttribute('aria-label', 'Mise en forme');
    _barre.innerHTML = BOUTONS_BARRE.map(function (b) {
      return '<button type="button" class="nted-fmt" data-cmd="' + b[0] + '" title="' + esc(b[2]) + '">' + b[1] + '</button>';
    }).join('') + '<button type="button" class="nted-commenter" data-cmd="commenter" title="Commenter ce passage">Commenter</button>';
    _barre.addEventListener('mousedown', function (e) {
      e.preventDefault();
      var btn = e.target.closest('[data-cmd]');
      if (!btn || !_barre._ed) return;
      if (btn.dataset.cmd === 'commenter') {
        var sel = window.getSelection();
        var row = _barre._el.closest('.pb');
        var citation = sel ? sel.toString() : '';
        _barre.classList.remove('open');
        if (_barre._ed.opts.surCommenter) _barre._ed.opts.surCommenter({ bloc_uid: row ? row.dataset.uid : null, citation: citation });
        return;
      }
      formater(_barre._ed, _barre._el, btn.dataset.cmd);
    });
    document.body.appendChild(_barre);
    return _barre;
  }

  function majBarre() {
    var sel = window.getSelection();
    var b = barre();
    if (!sel || !sel.rangeCount || sel.isCollapsed) { b.classList.remove('open'); return; }
    var n = sel.anchorNode;
    var el = n && (n.nodeType === 1 ? n : n.parentNode).closest && (n.nodeType === 1 ? n : n.parentNode).closest('.pb-txt, .pb-cellule');
    var ed = null;
    _editeurs.forEach(function (x) { if (el && x.corps.contains(el)) ed = x; });
    var c = ed && ed.ctx(el);
    var commenter = !!(ed && ed.opts.surCommenter);
    if (!ed || !c || (ed.lecture && !commenter)) { b.classList.remove('open'); return; }
    var formats = !ed.lecture && c.b.type !== 'code';
    if (!formats && !commenter) { b.classList.remove('open'); return; }
    b.querySelectorAll('.nted-fmt').forEach(function (x) { x.hidden = !formats; });
    var bc = b.querySelector('.nted-commenter');
    if (bc) bc.hidden = !commenter;
    b._ed = ed;
    b._el = el;
    ['bold', 'italic', 'underline', 'strikeThrough'].forEach(function (k) {
      var btn = b.querySelector('[data-cmd="' + k + '"]');
      var actif = false;
      try { actif = document.queryCommandState(k); } catch (e) {}
      if (btn) btn.classList.toggle('actif', !!actif);
    });
    var rect = sel.getRangeAt(0).getBoundingClientRect();
    b.classList.add('open');
    var w = b.offsetWidth || 240;
    var left = Math.max(8, Math.min(window.innerWidth - w - 8, rect.left + rect.width / 2 - w / 2));
    var top = rect.top - b.offsetHeight - 8;
    if (top < 8) top = rect.bottom + 8;
    b.style.left = left + 'px';
    b.style.top = top + 'px';
  }

  document.addEventListener('selectionchange', function () {
    clearTimeout(majBarre._t);
    majBarre._t = setTimeout(majBarre, 60);
  });

  /* ── Liens : saisie de l'adresse, bulle sur un lien existant ── */

  function fermerBulle() {
    if (_bulleLien) { _bulleLien.remove(); _bulleLien = null; }
  }

  function poserBulle(rect) {
    var w = _bulleLien.offsetWidth || 300;
    _bulleLien.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, rect.left)) + 'px';
    var top = rect.bottom + 6;
    if (top + 60 > window.innerHeight) top = rect.top - 56;
    _bulleLien.style.top = top + 'px';
  }

  function ouvrirLien(ed, el, lienExistant) {
    fermerBulle();
    var sel = window.getSelection();
    if (!sel || !sel.rangeCount) return;
    var plageSauvee = sel.getRangeAt(0).cloneRange();
    if (lienExistant) {
      plageSauvee = document.createRange();
      plageSauvee.selectNodeContents(lienExistant);
    }
    var rect = plageSauvee.getBoundingClientRect();
    _bulleLien = document.createElement('div');
    _bulleLien.className = 'nted-bulle';
    _bulleLien.innerHTML =
      '<input type="text" placeholder="Coller ou taper une adresse (https://…)" spellcheck="false" value="' +
      esc(lienExistant ? lienExistant.getAttribute('href') : '') + '">' +
      '<button type="button" class="nted-bulle-ok">Lier</button>';
    document.body.appendChild(_bulleLien);
    poserBulle(rect);
    var inp = _bulleLien.querySelector('input');
    function valider() {
      var url = normaliserLien(inp.value);
      fermerBulle();
      el.focus();
      var s2 = window.getSelection();
      s2.removeAllRanges();
      s2.addRange(plageSauvee);
      if (!url) { if (inp.value.trim() && ed.opts.signaler) ed.opts.signaler('Adresse invalide.'); return; }
      if (plageSauvee.collapsed) document.execCommand('insertHTML', false, '<a href="' + esc(url) + '">' + esc(inp.value.trim()) + '</a>');
      else document.execCommand('createLink', false, url);
      var c = ed.ctx(el);
      if (c) { relire(ed, c.b, el); ed.modifie(); }
    }
    inp.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); valider(); }
      if (e.key === 'Escape') { e.preventDefault(); fermerBulle(); el.focus(); }
    });
    _bulleLien.querySelector('.nted-bulle-ok').addEventListener('mousedown', function (e) { e.preventDefault(); valider(); });
    requestAnimationFrame(function () { inp.focus(); inp.select(); });
  }

  function ouvrirBulleLien(ed, a) {
    fermerBulle();
    var el = a.closest('.pb-txt');
    _bulleLien = document.createElement('div');
    _bulleLien.className = 'nted-bulle';
    var href = a.getAttribute('href') || '';
    _bulleLien.innerHTML =
      '<span class="nted-bulle-url" title="' + esc(href) + '">' + esc(href) + '</span>' +
      '<button type="button" data-a="ouvrir">Ouvrir</button>' +
      '<button type="button" data-a="modifier">Modifier</button>' +
      '<button type="button" data-a="retirer">Retirer</button>';
    document.body.appendChild(_bulleLien);
    poserBulle(a.getBoundingClientRect());
    _bulleLien.addEventListener('mousedown', function (e) {
      var b = e.target.closest('[data-a]');
      if (!b) return;
      e.preventDefault();
      if (b.dataset.a === 'ouvrir') { fermerBulle(); window.open(href, '_blank', 'noopener'); return; }
      if (b.dataset.a === 'modifier') { ouvrirLien(ed, el, a); return; }
      fermerBulle();
      var parent = a.parentNode;
      while (a.firstChild) parent.insertBefore(a.firstChild, a);
      parent.removeChild(a);
      var c = ed.ctx(el);
      if (c) { relire(ed, c.b, el); ed.modifie(); }
    });
  }

  document.addEventListener('mousedown', function (e) {
    if (_bulleLien && !_bulleLien.contains(e.target)) fermerBulle();
  }, true);

  /* ── Menu « / » ───────────────────────────────────────────────────────── */

  function menuSlash() {
    var m = document.getElementById('nted-slash');
    if (!m) {
      m = document.createElement('div');
      m.id = 'nted-slash';
      m.setAttribute('role', 'listbox');
      m.setAttribute('aria-label', 'Insérer un bloc');
      m.addEventListener('mousedown', function (e) {
        e.preventDefault();
        e.stopPropagation();
        var item = e.target.closest('.nted-slash-item');
        if (item && _slash) appliquerSlash(_slash.items[Number(item.dataset.k)]);
      });
      m.addEventListener('mousemove', function (e) {
        var item = e.target.closest('.nted-slash-item');
        if (!item || !_slash) return;
        var k = Number(item.dataset.k);
        if (k !== _slash.sel) { _slash.sel = k; dessinerSlash(false); }
      });
      document.body.appendChild(m);
    }
    return m;
  }

  function commandesDe(ed) {
    return COMMANDES.filter(function (cmd) {
      if (cmd.type === 'page') return !!ed.opts.creerSousPage;
      if (cmd.type === 'image') return !!ed.opts.noteId;
      if (cmd.action === 'mysifa') return !!ed.opts.noteId;
      if (cmd.action === 'modele') return !!ed.opts.choisirModele;
      return true;
    });
  }

  function ouvrirSlash(ed, el, debut) {
    _slash = { ed: ed, el: el, debut: debut, sel: 0, items: commandesDe(ed), q: '' };
    majSlash();
  }

  function fermerSlash() {
    _slash = null;
    var m = document.getElementById('nted-slash');
    if (m) m.classList.remove('open');
  }

  function majSlash() {
    var st = _slash;
    if (!st) return;
    var el = st.el;
    var v = texteDe(el);
    var pos = curseur(el).debut;
    if (!document.body.contains(el) || v.charAt(st.debut) !== '/' || pos <= st.debut) return fermerSlash();
    var q = v.slice(st.debut + 1, pos);
    if (q.length > 24 || /\n/.test(q) || /\s\s/.test(q)) return fermerSlash();
    var nq = sansAccent(q.trim());
    st.q = q;
    st.items = commandesDe(st.ed).filter(function (cmd) {
      return !nq || sansAccent(cmd.libelle + ' ' + cmd.mots).indexOf(nq) >= 0;
    });
    if (!st.items.length && / $/.test(q)) return fermerSlash();
    if (st.sel >= st.items.length) st.sel = 0;
    dessinerSlash(true);
  }

  function dessinerSlash(placerMenu) {
    var st = _slash;
    var m = menuSlash();
    if (!st) return;
    if (!st.items.length) {
      m.innerHTML = '<div class="nted-slash-vide">Aucune commande pour « ' + esc(st.q.trim()) + ' »</div>';
    } else {
      m.innerHTML = '<div class="nted-slash-titre">Insérer</div>' + st.items.map(function (cmd, k) {
        return '<div class="nted-slash-item' + (k === st.sel ? ' sel' : '') + '" role="option" data-k="' + k + '"' +
          (k === st.sel ? ' aria-selected="true"' : '') + '><span class="nted-slash-ico">' + esc(cmd.icone) + '</span>' +
          '<span class="nted-slash-txt"><b>' + esc(cmd.libelle) + '</b><small>' + esc(cmd.aide) + '</small></span></div>';
      }).join('');
    }
    m.classList.add('open');
    var sel = m.querySelector('.nted-slash-item.sel');
    if (sel && sel.scrollIntoView) sel.scrollIntoView({ block: 'nearest' });
    if (!placerMenu) return;
    var rect = rectCurseur() || st.el.getBoundingClientRect();
    var w = 250;
    var h = Math.min(300, m.scrollHeight || 300);
    var left = Math.min(rect.left, window.innerWidth - w - 12);
    var top = rect.bottom + 6;
    if (top + h > window.innerHeight - 12) top = Math.max(12, rect.top - h - 6);
    m.style.left = Math.max(12, left) + 'px';
    m.style.top = top + 'px';
  }

  function toucheSlash(e) {
    var st = _slash;
    if (!st) return false;
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      if (!st.items.length) return false;
      e.preventDefault();
      var n = st.items.length;
      st.sel = (st.sel + (e.key === 'ArrowDown' ? 1 : -1) + n) % n;
      dessinerSlash(false);
      return true;
    }
    if (e.key === 'Enter' || e.key === 'Tab') {
      if (!st.items.length) { fermerSlash(); return false; }
      e.preventDefault();
      appliquerSlash(st.items[st.sel]);
      return true;
    }
    if (e.key === 'Escape') { e.preventDefault(); fermerSlash(); return true; }
    return false;
  }

  function appliquerSlash(cmd) {
    var st = _slash;
    if (!st || !cmd) return;
    var ed = st.ed;
    var el = st.el;
    var c = ed.ctx(el);
    fermerSlash();
    if (!c) return;
    var debut = st.debut;
    var fin = Math.max(debut + 1, curseur(el).debut);
    remplacerTexte(el, debut, fin, '');
    ed.lire(c.b, el);
    executer(ed, el, c, cmd, debut, false);
  }

  /* Exécute une commande sur le bloc `el` : depuis le menu « / » (le bloc prend
     le type demandé) ou depuis le panneau d'actions (un bloc non vide reste tel
     quel, le nouveau bloc s'insère dessous). */
  function executer(ed, el, c, cmd, debut, depuisPanneau) {
    var b = c.b;
    var vide = !b.texte.trim() && b.type !== 'tableau';
    if (cmd.type === 'tableau') {
      var tab = { uid: uid(), type: 'tableau', texte: '', entete: true, lignes: [['', '', ''], ['', '', ''], ['', '', '']] };
      if (vide && b.type === 'p') c.blocs[c.i] = tab;
      else c.blocs.splice(c.i + 1, 0, tab);
      var at = vide && b.type === 'p' ? c.i : c.i + 1;
      if (at === c.blocs.length - 1) c.blocs.push({ uid: uid(), type: 'p', texte: '' });
      ed.redessiner();
      ed.focusCellule(at, 0, 0, 0);
      ed.modifie();
      return;
    }
    if (b.type === 'tableau' && cmd.type) {
      var neuf0 = { uid: uid(), type: cmd.type, texte: '' };
      c.blocs.splice(c.i + 1, 0, neuf0);
      ed.restructure(c.i + 1, 0);
      return;
    }
    if (depuisPanneau && cmd.type && !vide && !OBJETS[cmd.type] && cmd.type !== 'page' && cmd.type !== 'image') {
      var neuf = { uid: uid(), type: cmd.type, texte: '' };
      if (cmd.type === 'todo') neuf.coche = false;
      if (b.retrait && LISTES[cmd.type]) neuf.retrait = b.retrait;
      c.blocs.splice(c.i + 1, 0, neuf);
      ed.restructure(c.i + 1, 0);
      return;
    }
    if (cmd.action === 'date' || cmd.action === 'heure') {
      var d = new Date();
      var ins = cmd.action === 'date'
        ? d.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
        : d.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
      document.execCommand('insertText', false, ins);
      relire(ed, b, el);
      ed.modifie();
    } else if (cmd.action === 'mysifa') {
      document.execCommand('insertText', false, '@');
      relire(ed, b, el);
      ouvrirRef(ed, el, curseur(el).debut - 1);
    } else if (cmd.action === 'modele') {
      var choix = ed.opts.choisirModele();
      if (choix && choix.then) choix.then(function (blocs) { if (blocs && blocs.length) ed.insererBlocs(blocs, ed.indexUid(b.uid)); });
    } else if (cmd.action === 'lien') {
      ouvrirLien(ed, el);
    } else if (cmd.action === 'dupliquer') {
      var cp = copie(b);
      cp.uid = uid();
      c.blocs.splice(c.i + 1, 0, cp);
      ed.restructure(c.i + 1, -1);
    } else if (cmd.action === 'supprimer') {
      c.blocs.splice(c.i, 1);
      if (!c.blocs.length) c.blocs.push({ uid: uid(), type: 'p', texte: '' });
      ed.restructure(Math.max(0, c.i - 1), -1);
    } else if (cmd.type === 'image') {
      ed.modifie();
      ed.choisirImage(vide ? c.i : c.i);
    } else if (cmd.type === 'page') {
      var cree = ed.opts.creerSousPage(ed);
      if (!cree || !cree.then) return;
      cree.then(function (page) {
        if (!page || !page.id) return;
        var lien = { uid: uid(), type: 'page', texte: page.title || 'Sans titre', ref: page.id };
        var blocs = ed.blocs();
        var at = ed.indexUid(b.uid);
        if (at >= 0 && !blocs[at].texte) blocs[at] = lien;
        else blocs.splice(at + 1, 0, lien);
        ed.redessiner();
        ed.modifie(true);
        if (ed.opts.ouvrirPage) ed.opts.ouvrirPage(page.id);
      });
    } else if (cmd.type === 'sep') {
      if (vide) {
        b.type = 'sep'; b.texte = ''; delete b.html; delete b.coche;
        c.blocs.splice(c.i + 1, 0, { uid: uid(), type: 'p', texte: '' });
        ed.restructure(c.i + 1, 0);
      } else {
        c.blocs.splice(c.i + 1, 0, { uid: uid(), type: 'sep', texte: '' }, { uid: uid(), type: 'p', texte: '' });
        ed.restructure(c.i + 2, 0);
      }
    } else {
      b.type = cmd.type;
      if (cmd.type === 'todo') b.coche = !!b.coche; else delete b.coche;
      if (cmd.type === 'code') delete b.html;
      ed.restructure(c.i, debut);
    }
  }

  /* ── Menu « @ » : lier un objet MySifa (dossier, machine, client, note) ── */

  var _ref = null;
  var ICONES_REF = { note: '▤', dossier: 'D', machine: 'M', client: 'C' };

  function ouvrirRef(ed, el, debut) {
    _ref = { ed: ed, el: el, debut: debut, sel: 0, items: [], q: '', attente: null, jeton: 0 };
    majRef();
  }

  function fermerRef() {
    _ref = null;
    var m = document.getElementById('nted-slash');
    if (m && m.classList.contains('nted-ref')) { m.classList.remove('open', 'nted-ref'); }
  }

  function majRef() {
    var st = _ref;
    if (!st) return;
    var v = texteDe(st.el);
    var pos = curseur(st.el).debut;
    if (!document.body.contains(st.el) || v.charAt(st.debut) !== '@' || pos <= st.debut) return fermerRef();
    var q = v.slice(st.debut + 1, pos);
    if (q.length > 40 || /\n/.test(q) || /\s\s/.test(q)) return fermerRef();
    st.q = q;
    clearTimeout(st.attente);
    var jeton = ++st.jeton;
    dessinerRef(true, true);
    st.attente = setTimeout(function () {
      fetch('/api/postits/references?q=' + encodeURIComponent(q.trim()), { credentials: 'include' })
        .then(function (r) { return r.ok ? r.json() : { resultats: [] }; })
        .then(function (d) {
          if (!_ref || _ref !== st || jeton !== st.jeton) return;
          st.items = d.resultats || [];
          st.sel = 0;
          dessinerRef(false, true);
        })
        .catch(function () {});
    }, 180);
  }

  function dessinerRef(chargement, placerMenu) {
    var st = _ref;
    var m = menuSlash();
    if (!st) return;
    m.classList.add('nted-ref');
    if (!st.items.length) {
      m.innerHTML = '<div class="nted-slash-titre">Lier dans MySifa</div><div class="nted-slash-vide">' +
        (chargement ? 'Recherche…' : (st.q.trim() ? 'Aucun résultat pour « ' + esc(st.q.trim()) + ' »' : 'Tapez une référence de dossier, une machine, un client, une note')) + '</div>';
    } else {
      m.innerHTML = '<div class="nted-slash-titre">Lier dans MySifa</div>' + st.items.map(function (it, k) {
        return '<div class="nted-slash-item' + (k === st.sel ? ' sel' : '') + '" role="option" data-ref="' + k + '">' +
          '<span class="nted-slash-ico">' + esc(ICONES_REF[it.type] || '•') + '</span>' +
          '<span class="nted-slash-txt"><b>' + esc(it.libelle) + '</b><small>' + esc(it.detail || '') + '</small></span></div>';
      }).join('');
    }
    m.classList.add('open');
    if (placerMenu) {
      var rect = rectCurseur() || st.el.getBoundingClientRect();
      var h = Math.min(300, m.scrollHeight || 300);
      var top = rect.bottom + 6;
      if (top + h > window.innerHeight - 12) top = Math.max(12, rect.top - h - 6);
      m.style.left = Math.max(12, Math.min(rect.left, window.innerWidth - 262)) + 'px';
      m.style.top = top + 'px';
    }
    var sel = m.querySelector('.nted-slash-item.sel');
    if (sel && sel.scrollIntoView) sel.scrollIntoView({ block: 'nearest' });
  }

  function choisirRef(it) {
    var st = _ref;
    if (!st || !it) return;
    var el = st.el;
    var ed = st.ed;
    var fin = Math.max(st.debut + 1, curseur(el).debut);
    fermerRef();
    placer(el, st.debut, fin);
    _interne++;
    try {
      document.execCommand('insertHTML', false, '<a href="' + esc(it.url) + '">' + esc(it.libelle) + '</a>\u00a0');
    } finally { _interne--; }
    var c = ed.ctx(el);
    if (c) { relire(ed, c.b, el); ed.modifie(); }
  }

  function toucheRef(e) {
    var st = _ref;
    if (!st) return false;
    if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && st.items.length) {
      e.preventDefault();
      var n = st.items.length;
      st.sel = (st.sel + (e.key === 'ArrowDown' ? 1 : -1) + n) % n;
      dessinerRef(false, false);
      return true;
    }
    if ((e.key === 'Enter' || e.key === 'Tab') && st.items.length) {
      e.preventDefault();
      choisirRef(st.items[st.sel]);
      return true;
    }
    if (e.key === 'Escape') { e.preventDefault(); fermerRef(); return true; }
    return false;
  }

  document.addEventListener('mousedown', function (e) {
    var m = document.getElementById('nted-slash');
    if (!_ref || !m || !m.contains(e.target)) return;
    e.preventDefault();
    e.stopPropagation();
    var item = e.target.closest('[data-ref]');
    if (item) choisirRef(_ref.items[Number(item.dataset.ref)]);
  }, true);

  function toutVider() {
    _editeurs.forEach(function (ed) { ed.vider(); });
  }

  window.addEventListener('pagehide', function () {
    _editeurs.slice().forEach(function (ed) { ed.detruire(); });
  });
  document.addEventListener('visibilitychange', function () {
    if (document.visibilityState === 'hidden') toutVider();
  });
  window.addEventListener('scroll', function (e) {
    if (_slash && !(e.target && e.target.id === 'nted-slash')) fermerSlash();
    if (_ref && !(e.target && e.target.id === 'nted-slash')) fermerRef();
    if (_barre) _barre.classList.remove('open');
  }, true);

  function texteBlocs(blocs) {
    return (Array.isArray(blocs) ? blocs : [])
      .map(function (b) { return b && (b.texte || b.legende) ? (b.texte || b.legende) : ''; })
      .filter(Boolean)
      .join('\n');
  }

  window.MySifaNotesEditeur = {
    monter: function (corps, note, opts) { return new Editeur(corps, note, opts); },
    /* Commandes d'insertion proposées à cet éditeur (menu « / » et panneau d'actions). */
    commandes: function (ed) {
      return commandesDe(ed).map(function (c) { return { cle: c.cle, libelle: c.libelle, aide: c.aide, icone: c.icone }; });
    },
    types: TYPES,
    texte: texteBlocs,
    toutVider: toutVider,
    client: _client,
    initiales: initiales,
    couleur: couleurDe,
    _fusion3: fusion3,
    _assainir: assainir,
  };
})();

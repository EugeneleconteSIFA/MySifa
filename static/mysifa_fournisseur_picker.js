/* ============================================================
   MySifa — Picker fournisseur partagé  (v1.0)
   ------------------------------------------------------------
   Remplace partout les <select> et <datalist> de fournisseurs par
   une recherche qui filtre à la frappe.

   Pourquoi : l'annuaire compte plusieurs centaines de fiches. Une
   liste déroulante à 300 entrées oblige à connaître l'orthographe
   exacte et à scroller ; elle ne sait rien chercher sur la ville,
   le code postal ou le numéro de licence.

   Ce composant :
     - filtre dès le 1er caractère, sur nom, ville, code postal,
       pays, groupe, branche, licence, certificat, e-mail et tags ;
     - met en avant les fournisseurs de la CATÉGORIE attendue par
       l'écran appelant (« Fournisseurs adhésif » en tête), le
       reste de l'annuaire dessous ;
     - navigue au clavier (flèches, Entrée, Origine/Fin, Échap) ;
     - se positionne en position:fixed dans <body> pour ne jamais
       être rogné par l'overflow d'un .modal-body scrollable ;
     - ne reconstruit JAMAIS le champ de saisie, seulement la liste
       de résultats — le focus et le curseur ne bougent pas ;
     - charge l'annuaire UNE fois par page (promesse partagée).

   Valeur portée : `input[type=hidden]` (l'id du fournisseur, ou
   son nom si valueMode:'nom'). Le champ texte visible ne porte que
   le libellé — ne jamais le lire pour récupérer une valeur.

   ── API ────────────────────────────────────────────────────────
   MysFournisseurPicker.fromSelect(selectEl, opts) -> instance
       Remplace un <select> en place. Reprend son id, son name, sa
       valeur courante et son onchange inline.

   MysFournisseurPicker.attach(inputEl, opts) -> instance
       Remplace un <input type="text"> déjà dans le DOM.

   MysFournisseurPicker.create(opts) -> instance
       Construit le markup ; `instance.el` est à insérer où l'on veut.

   MysFournisseurPicker.autoInit(root)
       Enrichit les [data-mys-fp-auto] trouvés sous `root`.

   opts :
     valueMode      'id' (défaut) | 'nom'
     value          valeur initiale (id ou nom selon valueMode)
     categories     ['adhesif','frontal'] — favoris câblés par l'écran
     resolveCategories  () => ['adhesif'] — favoris déduits du contexte ;
                    prime sur `categories` quand elle renvoie non-vide
     placeholder    défaut « Rechercher un fournisseur… »
     activeOnly     true (défaut) — masque les fiches archivées
     fscOnly        false — ne garde que les fournisseurs certifiés FSC
     allowEmpty     true — propose « — Aucun — »
     emptyLabel     défaut « — Aucun — »
     allowFree      false — accepte un nom hors annuaire (id null)
     filter         (f) => bool — filtre supplémentaire
     hiddenName     name du champ caché
     hiddenId       id du champ caché
     inputId        id du champ texte visible
     className      classe ajoutée au conteneur ('mys-fp-sm' = compact)
     required       true — marque le champ comme requis
     onSelect       (fournisseur|null) => void
     onClear        () => void

   instance :
     el, input, hidden
     getId() -> Number|null      getNom() -> String
     get() -> fournisseur|null   set(idOrNom, silent)
     clear(silent)               setCategories(codes)
     refresh()                   focus()                destroy()
   ============================================================ */
(function () {
  'use strict';
  if (window.MysFournisseurPicker) return;

  var ENDPOINT = '/api/fournisseurs/picker';
  var CSS_HREF = '/static/mysifa_fournisseur_picker.css';
  var MAX_RENDER = 60;          // au-delà, la liste n'est plus lisible
  var MAX_PAR_GROUPE = 40;

  var _pop = null;              // popover unique, réutilisé
  var _active = null;           // instance actuellement ouverte
  var _rafId = 0;
  var _seq = 0;                 // compteur d'ids uniques
  var _cache = null;            // Array des fournisseurs
  var _cacheCats = null;        // Array {code,label}
  var _loading = null;          // promesse en cours (partagée)

  /* Le composant est appelé depuis six pages différentes. Oublier le <link>
     dans l'une d'elles donnerait un champ sans style — visuellement cassé,
     mais fonctionnel, donc facile à laisser passer en revue. On s'assure de
     la feuille plutôt que de compter sur six déclarations. */
  function assurerCss() {
    if (!document.head) return;
    var liens = document.head.querySelectorAll('link[rel="stylesheet"]');
    for (var i = 0; i < liens.length; i++) {
      if ((liens[i].getAttribute('href') || '').indexOf('mysifa_fournisseur_picker.css') !== -1) return;
    }
    var l = document.createElement('link');
    l.rel = 'stylesheet';
    l.href = CSS_HREF + '?v=1.0';
    document.head.appendChild(l);
  }

  /* ── Utilitaires ──────────────────────────────────────────── */

  function escHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  /* Minuscule, sans accent, ponctuation ramenée à des espaces.
     « Sté ÉTIQ-PLUS (Lille) » → « ste etiq plus lille ».
     Diacritiques en échappements \u0300-\u036f et non en caractères
     combinants nus : ces derniers survivent mal à un changement d'encodage
     du fichier, et la recherche cesserait alors de tolérer les accents. */
  function norm(s) {
    s = String(s == null ? '' : s);
    if (s.normalize) s = s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');
    return s.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
  }

  function tokens(q) {
    var n = norm(q);
    return n ? n.split(' ').filter(Boolean) : [];
  }

  /* ── Chargement de l'annuaire ─────────────────────────────── */

  function load(force) {
    if (_cache && !force) return Promise.resolve(_cache);
    if (_loading && !force) return _loading;
    _loading = fetch(ENDPOINT, { credentials: 'same-origin' })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (data) {
        var list = Array.isArray(data) ? data : (data.fournisseurs || []);
        _cacheCats = (data && data.categories) || _cacheCats || [];
        _cache = list.map(prepare);
        _loading = null;
        return _cache;
      })
      .catch(function (e) {
        // Pas de cache vide mémorisé : un réseau qui hoquette ne doit pas
        // condamner la page à un annuaire vide jusqu'au rechargement.
        _loading = null;
        throw e;
      });
    return _loading;
  }

  /* Pré-calcule la botte de foin une fois pour toutes : refaire la
     normalisation à chaque frappe sur 300 fiches × 10 champs se voit. */
  function prepare(f) {
    var o = {};
    for (var k in f) if (Object.prototype.hasOwnProperty.call(f, k)) o[k] = f[k];
    o.id = o.id == null ? null : Number(o.id);
    o.nom = String(o.nom || '');
    o.categories = Array.isArray(o.categories) ? o.categories : [];
    var tags = Array.isArray(o.tags) ? o.tags.join(' ') : (o.tags || '');
    o._nomNorm = norm(o.nom);
    o._hay = norm([
      o.nom, o.ville, o.code_postal, o.pays, o.groupe, o.branche,
      o.licence, o.certificat, o.email, tags
    ].filter(Boolean).join(' '));
    return o;
  }

  function catLabel(code) {
    var list = _cacheCats || [];
    for (var i = 0; i < list.length; i++) if (list[i].code === code) return list[i].label;
    return code;
  }

  /* ── Popover unique ───────────────────────────────────────── */

  function ensurePop() {
    if (_pop) return _pop;
    assurerCss();
    _pop = document.createElement('div');
    _pop.className = 'mys-fp-pop';
    _pop.id = 'mys-fp-pop';
    _pop.setAttribute('role', 'listbox');
    _pop.style.display = 'none';
    // mousedown et non click : le blur du champ part avant le click et
    // refermerait le popover sous le curseur.
    _pop.addEventListener('mousedown', function (e) {
      var it = e.target.closest ? e.target.closest('.mys-fp-item') : null;
      if (!it || !_active) return;
      e.preventDefault();
      choose(_active, it.getAttribute('data-fid'));
    });
    _pop.addEventListener('mousemove', function (e) {
      var it = e.target.closest ? e.target.closest('.mys-fp-item') : null;
      if (!it || !_active) return;
      var idx = Number(it.getAttribute('data-idx'));
      if (idx !== _active._hi) { _active._hi = idx; paintHi(_active); }
    });
    document.body.appendChild(_pop);
    return _pop;
  }

  function place() {
    if (!_active || !_pop) return;
    var r = _active.input.getBoundingClientRect();
    var vh = window.innerHeight || 600;
    var vw = window.innerWidth || 800;
    var mobile = vw < 640;
    var w = mobile ? Math.min(vw - 20, 460) : Math.max(r.width, 300);
    var dessous = vh - r.bottom - 10;
    var dessus = r.top - 10;
    // Champ en bas d'écran (dernière ligne d'un tableau, pied de modale) :
    // le popover s'ouvre vers le haut plutôt que de sortir du cadre.
    var vers_le_haut = dessous < 200 && dessus > dessous;
    var hMax = Math.max(160, Math.min(360, vers_le_haut ? dessus : dessous));

    _pop.style.width = w + 'px';
    _pop.style.maxHeight = hMax + 'px';
    var left = mobile ? Math.max(10, (vw - w) / 2) : r.left;
    if (left + w > vw - 8) left = Math.max(8, vw - w - 8);
    _pop.style.left = left + 'px';
    if (vers_le_haut) {
      _pop.style.top = 'auto';
      _pop.style.bottom = (vh - r.top + 4) + 'px';
    } else {
      _pop.style.bottom = 'auto';
      _pop.style.top = (r.bottom + 4) + 'px';
    }
  }

  function schedulePlace() {
    if (!_active || _rafId) return;
    _rafId = requestAnimationFrame(function () { _rafId = 0; place(); });
  }

  /* ── Filtrage et rendu de la liste ────────────────────────── */

  function candidats(inst) {
    var list = _cache || [];
    var opts = inst.opts;
    var out = [];
    for (var i = 0; i < list.length; i++) {
      var f = list[i];
      if (opts.activeOnly !== false && f.actif === 0) {
        // Une fiche archivée reste visible si c'est la valeur courante :
        // masquer la valeur qu'on est en train d'éditer donnerait un champ
        // qui paraît vide alors qu'il porte une donnée.
        if (f.id !== inst._selId) continue;
      }
      if (opts.fscOnly && !f.has_fsc) continue;
      if (typeof opts.filter === 'function' && !opts.filter(f)) continue;
      out.push(f);
    }
    return out;
  }

  function score(f, toks) {
    if (!toks.length) return 0;
    // Tous les mots doivent être présents (recherche « et »), sinon taper
    // un deuxième mot élargit le résultat au lieu de le resserrer.
    for (var i = 0; i < toks.length; i++) {
      if (f._hay.indexOf(toks[i]) === -1) return -1;
    }
    var t0 = toks[0];
    if (f._nomNorm.indexOf(t0) === 0) return 3;                  // le nom commence par
    if ((' ' + f._nomNorm).indexOf(' ' + t0) !== -1) return 2;   // un mot du nom
    if (f._nomNorm.indexOf(t0) !== -1) return 1;                 // ailleurs dans le nom
    return 0;                                                    // ville, licence…
  }

  function activeCats(inst) {
    var dyn = null;
    if (typeof inst.opts.resolveCategories === 'function') {
      try { dyn = inst.opts.resolveCategories(); } catch (_) { dyn = null; }
    }
    // Le contexte prime sur le câblage : l'écran déclare ce qu'il attend en
    // général, la matière en cours d'édition sait mieux.
    var cats = (dyn && dyn.length) ? dyn : (inst.opts.categories || []);
    return (cats || []).filter(Boolean);
  }

  function buildGroups(inst, q) {
    var toks = tokens(q);
    var cats = activeCats(inst);
    var favSet = {};
    for (var c = 0; c < cats.length; c++) favSet[cats[c]] = 1;

    var fav = [], reste = [];
    var pool = candidats(inst);
    for (var i = 0; i < pool.length; i++) {
      var f = pool[i];
      var s = score(f, toks);
      if (s < 0) continue;
      var estFav = false;
      for (var j = 0; j < f.categories.length; j++) {
        if (favSet[f.categories[j]]) { estFav = true; break; }
      }
      (estFav ? fav : reste).push({ f: f, s: s });
    }

    function tri(a, b) {
      if (b.s !== a.s) return b.s - a.s;
      return a.f.nom.localeCompare(b.f.nom, 'fr', { sensitivity: 'base' });
    }
    fav.sort(tri); reste.sort(tri);

    var groups = [];
    if (fav.length) {
      groups.push({
        titre: cats.length === 1
          ? 'Fournisseurs ' + catLabel(cats[0]).toLowerCase()
          : 'Catégories attendues',
        fav: true,
        items: fav.slice(0, MAX_PAR_GROUPE),
        tronque: Math.max(0, fav.length - MAX_PAR_GROUPE)
      });
    }
    if (reste.length) {
      var budget = fav.length
        ? Math.max(10, MAX_RENDER - Math.min(fav.length, MAX_PAR_GROUPE))
        : MAX_RENDER;
      groups.push({
        titre: fav.length ? 'Autres fournisseurs' : '',
        fav: false,
        items: reste.slice(0, budget),
        tronque: Math.max(0, reste.length - budget)
      });
    }
    return { groups: groups, total: fav.length + reste.length };
  }

  /* Met en gras la portion qui correspond à la frappe — l'utilisateur voit
     POURQUOI une ligne est là, y compris quand le match porte sur la ville. */
  function surligne(texte, toks) {
    var s = String(texte || '');
    if (!toks.length) return escHtml(s);
    var n = norm(s);
    var t = toks[0];
    var at = n.indexOf(t);
    if (at === -1) return escHtml(s);
    // La normalisation peut changer la longueur (« Œ » → « oe », ponctuation
    // multiple ramenée à un espace). Quand les longueurs divergent, l'index
    // n'est plus fiable : on renonce au surlignage plutôt que de couper le
    // nom au mauvais endroit.
    if (n.length !== s.length) return escHtml(s);
    return escHtml(s.slice(0, at)) + '<b>' + escHtml(s.slice(at, at + t.length)) +
           '</b>' + escHtml(s.slice(at + t.length));
  }

  function metaLigne(f) {
    var bouts = [];
    var lieu = [f.code_postal, f.ville].filter(Boolean).join(' ');
    if (lieu) bouts.push(escHtml(lieu));
    if (f.pays && String(f.pays).toUpperCase() !== 'FR') {
      bouts.push(escHtml(String(f.pays).toUpperCase()));
    }
    if (f.groupe) bouts.push('groupe ' + escHtml(f.groupe));
    return bouts.join(' · ');
  }

  function badges(f) {
    var out = '';
    if (f.has_fsc) {
      out += '<span class="mys-fp-badge mys-fp-fsc" title="' +
        escHtml(f.licence || 'Certifié FSC') + '">FSC</span>';
    }
    if (f.actif === 0) out += '<span class="mys-fp-badge mys-fp-archive">archivé</span>';
    return out;
  }

  function renderList(inst) {
    var pop = ensurePop();
    // Le libellé de la valeur retenue n'est pas une recherche : on ne filtre
    // que sur ce que l'utilisateur a réellement tapé.
    var q = inst.input.value === inst._selLabel ? '' : inst.input.value;
    var res = buildGroups(inst, q);
    var toks = tokens(q);
    var html = '';
    var flat = [];
    var idx = 0;

    if (inst.opts.allowEmpty !== false && !toks.length) {
      html += '<div class="mys-fp-item mys-fp-item-vide" role="option" data-fid="" data-idx="' +
        idx + '" id="mys-fp-opt-' + inst._uid + '-' + idx + '"><span class="mys-fp-nom">' +
        escHtml(inst.opts.emptyLabel || '— Aucun —') + '</span></div>';
      flat.push(null);
      idx++;
    }

    for (var g = 0; g < res.groups.length; g++) {
      var grp = res.groups[g];
      if (grp.titre) {
        html += '<div class="mys-fp-groupe' + (grp.fav ? ' mys-fp-groupe-fav' : '') +
          '" role="presentation">' + escHtml(grp.titre) + '</div>';
      }
      for (var i = 0; i < grp.items.length; i++) {
        var f = grp.items[i].f;
        var meta = metaLigne(f);
        html += '<div class="mys-fp-item" role="option" aria-selected="false" data-fid="' +
          f.id + '" data-idx="' + idx + '" id="mys-fp-opt-' + inst._uid + '-' + idx + '">' +
          '<span class="mys-fp-nom">' + surligne(f.nom, toks) + badges(f) + '</span>' +
          (meta ? '<span class="mys-fp-meta">' + meta + '</span>' : '') +
          '</div>';
        flat.push(f);
        idx++;
      }
      if (grp.tronque) {
        html += '<div class="mys-fp-plus" role="presentation">+ ' + grp.tronque +
          ' autre' + (grp.tronque > 1 ? 's' : '') + ' — précisez la recherche</div>';
      }
    }

    if (!res.total) {
      html += '<div class="mys-fp-empty">' + (
        toks.length
          ? 'Aucun résultat pour « ' + escHtml(q.trim()) + ' »'
          : 'Annuaire fournisseurs vide.'
      ) + '</div>';
      if (toks.length && inst.opts.allowFree) {
        html += '<div class="mys-fp-item mys-fp-item-libre" role="option" data-fid="__libre__" data-idx="' +
          idx + '" id="mys-fp-opt-' + inst._uid + '-' + idx +
          '"><span class="mys-fp-nom">Utiliser « ' + escHtml(q.trim()) +
          ' »</span><span class="mys-fp-meta">hors annuaire</span></div>';
        flat.push({ id: null, nom: q.trim(), _libre: true });
        idx++;
      }
    }

    pop.innerHTML = html;
    inst._flat = flat;
    if (inst._hi >= flat.length) inst._hi = flat.length ? 0 : -1;
    if (inst._hi < 0 && flat.length) inst._hi = toks.length ? 0 : firstReal(flat);
    paintHi(inst);
    place();
  }

  /* Sans frappe, on préfère surligner un vrai fournisseur plutôt que
     « — Aucun — » : Entrée à l'aveugle ne doit pas vider le champ. */
  function firstReal(flat) {
    for (var i = 0; i < flat.length; i++) if (flat[i]) return i;
    return flat.length ? 0 : -1;
  }

  function paintHi(inst) {
    if (!_pop) return;
    var items = _pop.querySelectorAll('.mys-fp-item');
    for (var i = 0; i < items.length; i++) {
      var on = Number(items[i].getAttribute('data-idx')) === inst._hi;
      items[i].classList.toggle('hi', on);
      items[i].setAttribute('aria-selected', on ? 'true' : 'false');
      if (on) {
        inst.input.setAttribute('aria-activedescendant', items[i].id || '');
        var it = items[i];
        var top = it.offsetTop, bot = top + it.offsetHeight;
        if (top < _pop.scrollTop) _pop.scrollTop = top;
        else if (bot > _pop.scrollTop + _pop.clientHeight) _pop.scrollTop = bot - _pop.clientHeight;
      }
    }
    if (inst._hi < 0) inst.input.removeAttribute('aria-activedescendant');
  }

  /* ── Ouverture / fermeture ────────────────────────────────── */

  function open(inst) {
    if (_active === inst && _pop && _pop.style.display !== 'none') return;
    if (_active && _active !== inst) close();
    _active = inst;
    var pop = ensurePop();
    pop.style.display = 'block';
    inst.input.setAttribute('aria-expanded', 'true');
    inst.input.setAttribute('aria-controls', 'mys-fp-pop');
    inst.el.classList.add('mys-fp-open');
    if (!_cache) {
      pop.innerHTML = '<div class="mys-fp-empty">Chargement de l\'annuaire…</div>';
      place();
      load().then(function () {
        if (_active === inst) { inst._syncLabel(); renderList(inst); }
      }).catch(function () {
        if (_active === inst) {
          pop.innerHTML = '<div class="mys-fp-empty mys-fp-err">Annuaire indisponible. ' +
            'Réessayez dans un instant.</div>';
          place();
        }
      });
      return;
    }
    inst._hi = -1;
    renderList(inst);
  }

  function close() {
    if (_pop) { _pop.style.display = 'none'; _pop.innerHTML = ''; }
    if (_active) {
      _active.input.setAttribute('aria-expanded', 'false');
      _active.input.removeAttribute('aria-activedescendant');
      _active.el.classList.remove('mys-fp-open');
      _active._hi = -1;
    }
    _active = null;
  }

  function choose(inst, fid) {
    if (fid === '') { inst.clear(); close(); inst.input.focus(); return; }
    var f = null;
    if (fid === '__libre__') {
      f = { id: null, nom: inst.input.value.trim(), _libre: true };
    } else {
      var n = Number(fid);
      for (var i = 0; i < (_cache || []).length; i++) {
        if (_cache[i].id === n) { f = _cache[i]; break; }
      }
    }
    if (!f) return;
    applyValue(inst, f, false);
    close();
    inst.input.focus();
  }

  function applyValue(inst, f, silent) {
    inst._selId = f ? f.id : null;
    inst._selNom = f ? f.nom : '';
    inst._selObj = f || null;
    inst._selLabel = f ? f.nom : '';
    inst.input.value = inst._selLabel;
    inst.input.placeholder = inst.opts.placeholder || 'Rechercher un fournisseur…';
    var v = '';
    if (f) v = (inst.opts.valueMode === 'nom') ? f.nom : (f.id == null ? '' : String(f.id));
    inst.hidden.value = v;
    inst.el.classList.toggle('mys-fp-filled', !!f);
    inst.el.classList.toggle('mys-fp-vide', !f);
    if (!silent) {
      // On notifie comme l'aurait fait un <select> : le code appelant qui
      // écoutait 'change' continue de fonctionner sans une ligne de plus.
      fire(inst.hidden, 'input');
      fire(inst.hidden, 'change');
      if (typeof inst.opts.onSelect === 'function') inst.opts.onSelect(f);
    }
  }

  function fire(el, type) {
    var ev;
    try { ev = new Event(type, { bubbles: true }); }
    catch (_) { ev = document.createEvent('Event'); ev.initEvent(type, true, true); }
    el.dispatchEvent(ev);
  }

  /* ── Construction d'une instance ──────────────────────────── */

  function create(opts) {
    opts = opts || {};
    assurerCss();
    var uid = ++_seq;

    var el = document.createElement('div');
    el.className = 'mys-fp' + (opts.className ? ' ' + opts.className : '');
    el.setAttribute('data-mys-fp', '1');

    var hidden = document.createElement('input');
    hidden.type = 'hidden';
    if (opts.hiddenName) hidden.name = opts.hiddenName;
    if (opts.hiddenId) hidden.id = opts.hiddenId;

    var input = document.createElement('input');
    input.type = 'text';
    input.className = 'mys-fp-input';
    if (opts.inputId) input.id = opts.inputId;
    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('autocomplete', 'off');
    input.setAttribute('spellcheck', 'false');
    input.placeholder = opts.placeholder || 'Rechercher un fournisseur…';
    if (opts.required) input.setAttribute('aria-required', 'true');

    var clear = document.createElement('button');
    clear.type = 'button';
    clear.className = 'mys-fp-clear';
    clear.setAttribute('aria-label', 'Vider le champ fournisseur');
    clear.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>';

    // Loupe et non chevron : elle dit « on tape pour chercher » là où le
    // chevron d'un <select> disait « on déroule ».
    var loupe = document.createElement('span');
    loupe.className = 'mys-fp-caret';
    loupe.setAttribute('aria-hidden', 'true');
    loupe.innerHTML = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<circle cx="11" cy="11" r="7"/><path d="M20 20l-4.5-4.5"/></svg>';

    el.appendChild(hidden);
    el.appendChild(loupe);
    el.appendChild(input);
    el.appendChild(clear);

    var inst = {
      el: el, input: input, hidden: hidden, opts: opts, _uid: uid,
      _hi: -1, _flat: [], _selId: null, _selNom: '', _selObj: null, _selLabel: ''
    };

    inst.getId = function () { return inst._selId; };
    inst.getNom = function () { return inst._selNom; };
    inst.get = function () { return inst._selObj; };

    inst.set = function (v, silent) {
      if (v == null || v === '') { inst.clear(true); if (!silent) fire(hidden, 'change'); return; }
      var apply = function () {
        var f = null, list = _cache || [];
        if (opts.valueMode === 'nom') {
          var n = norm(v);
          for (var i = 0; i < list.length; i++) if (list[i]._nomNorm === n) { f = list[i]; break; }
          // Nom absent de l'annuaire : c'est le cas des réceptions anciennes,
          // saisies en texte libre. On l'affiche tel quel plutôt que de vider
          // le champ — la donnée existe, elle n'est simplement pas rattachée.
          if (!f) f = { id: null, nom: String(v), _libre: true };
        } else {
          var num = Number(v);
          for (var j = 0; j < list.length; j++) if (list[j].id === num) { f = list[j]; break; }
        }
        if (f) { applyValue(inst, f, silent !== false); return; }
        // Id inconnu (fiche supprimée ou fusionnée) : on garde la valeur brute
        // dans le champ caché et on le dit. L'effacer en silence ferait
        // enregistrer un champ vide au prochain « Enregistrer ».
        inst.hidden.value = String(v);
        inst._selId = Number(v) || null;
        inst._selLabel = '';
        inst.input.value = '';
        inst.input.placeholder = 'Fournisseur introuvable (#' + String(v) + ')';
        inst.el.classList.add('mys-fp-orphelin');
      };
      if (_cache) apply(); else load().then(apply).catch(function () {});
    };

    inst.clear = function (silent) {
      inst.el.classList.remove('mys-fp-orphelin');
      applyValue(inst, null, silent !== false);
      if (!silent && typeof opts.onClear === 'function') opts.onClear();
    };

    inst.setCategories = function (codes) {
      opts.categories = (codes || []).filter(Boolean);
      if (_active === inst) renderList(inst);
    };

    inst.refresh = function () {
      return load(true).then(function () {
        if (inst._selId != null) {
          inst.set(opts.valueMode === 'nom' ? inst._selNom : inst._selId, true);
        }
        if (_active === inst) renderList(inst);
      });
    };

    inst.focus = function () { input.focus(); };

    inst._syncLabel = function () {
      if (inst._selId != null || inst._selNom) {
        inst.set(opts.valueMode === 'nom' ? inst._selNom : inst._selId, true);
      }
    };

    inst.destroy = function () {
      if (_active === inst) close();
      if (el.parentNode) el.parentNode.removeChild(el);
    };

    /* ── Écouteurs ─────────────────────────────────────────── */

    input.addEventListener('focus', function () { open(inst); });
    input.addEventListener('click', function () { open(inst); });

    input.addEventListener('input', function () {
      // Le conteneur du champ n'est jamais reconstruit : seule la liste du
      // popover l'est. Focus et curseur restent donc intacts, sans avoir à
      // sauvegarder selectionStart / selectionEnd autour du rendu.
      if (_active !== inst) open(inst);
      inst._hi = -1;
      renderList(inst);
    });

    input.addEventListener('keydown', function (e) {
      var ouvert = _active === inst && _pop && _pop.style.display !== 'none';
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (!ouvert) { open(inst); return; }
        var n = inst._flat.length;
        if (!n) return;
        inst._hi = e.key === 'ArrowDown'
          ? (inst._hi + 1 >= n ? 0 : inst._hi + 1)
          : (inst._hi - 1 < 0 ? n - 1 : inst._hi - 1);
        paintHi(inst);
        return;
      }
      if (e.key === 'Home' && ouvert) { e.preventDefault(); inst._hi = 0; paintHi(inst); return; }
      if (e.key === 'End' && ouvert) {
        e.preventDefault(); inst._hi = inst._flat.length - 1; paintHi(inst); return;
      }
      if (e.key === 'Enter') {
        // Entrée valide la ligne surlignée et ne soumet JAMAIS le formulaire
        // autour (règle searchbar : naviguer sans soumettre).
        if (ouvert && inst._hi >= 0 && inst._hi < inst._flat.length) {
          e.preventDefault(); e.stopPropagation();
          var f = inst._flat[inst._hi];
          if (f === null) { inst.clear(); close(); }
          else if (f._libre) { applyValue(inst, f, false); close(); }
          else { choose(inst, String(f.id)); }
        } else if (ouvert) {
          e.preventDefault();
        }
        return;
      }
      if (e.key === 'Escape') {
        // Échap vide d'abord la frappe et restaure la liste complète ; un
        // second Échap referme. stopPropagation pour que la modale derrière
        // ne se ferme pas tant que le popover est ouvert.
        if (ouvert) {
          e.stopPropagation();
          e.preventDefault();
          if (input.value && input.value !== inst._selLabel) {
            input.value = inst._selLabel;
            inst._hi = -1;
            renderList(inst);
          } else {
            close();
          }
        }
        return;
      }
      if (e.key === 'Tab') { if (ouvert) close(); }
    });

    input.addEventListener('blur', function () {
      // Le champ visible n'est qu'un libellé : ce que l'utilisateur a tapé
      // sans valider ne doit pas rester à l'écran comme si c'était retenu.
      setTimeout(function () {
        if (_active === inst) return;      // clic dans le popover en cours
        if (input.value === inst._selLabel) return;
        if (!input.value.trim() && inst._selId != null && opts.allowEmpty !== false) {
          inst.clear();
        } else {
          input.value = inst._selLabel;
        }
      }, 0);
    });

    clear.addEventListener('click', function (e) {
      e.preventDefault(); e.stopPropagation();
      inst.clear();
      input.focus();
      open(inst);
    });

    applyValue(inst, null, true);
    if (opts.value != null && opts.value !== '') inst.set(opts.value, true);
    else load().catch(function () {});   // préchauffe le cache sans bloquer

    return inst;
  }

  /* ── Remplacement d'un <select> existant ──────────────────── */

  function fromSelect(sel, opts) {
    if (!sel || sel.tagName !== 'SELECT') return null;
    if (sel.getAttribute('data-mys-fp-done')) return sel._mysFp || null;
    opts = opts || {};

    var o = {};
    for (var k in opts) if (Object.prototype.hasOwnProperty.call(opts, k)) o[k] = opts[k];
    if (!o.hiddenId && sel.id) o.hiddenId = sel.id;
    if (!o.hiddenName && sel.name) o.hiddenName = sel.name;
    if (!o.inputId && sel.id) o.inputId = sel.id + '-search';
    if (o.value == null && sel.value) o.value = sel.value;

    var inst = create(o);
    // Le champ caché reprend l'id ET le onchange inline du select : un
    // `onchange="foo(this.value)"` posé dans le HTML continue de partir, et
    // `document.getElementById(<id>).value` lit toujours la bonne valeur.
    //
    // Ce qui NE survit pas : un addEventListener('change') posé en JS sur le
    // nœud <select> lui-même, puisque ce nœud quitte le DOM. Les appelants
    // concernés passent par opts.onSelect, ou reposent le handler sur
    // `instance.hidden` — c'est explicite plutôt que silencieusement cassé.
    var inlineChange = sel.getAttribute('onchange');
    if (inlineChange) inst.hidden.setAttribute('onchange', inlineChange);
    if (sel.disabled) { inst.input.disabled = true; inst.el.classList.add('mys-fp-disabled'); }
    if (sel.parentNode) sel.parentNode.replaceChild(inst.el, sel);
    sel.setAttribute('data-mys-fp-done', '1');
    sel._mysFp = inst;
    return inst;
  }

  function attach(input, opts) {
    if (!input || input.tagName !== 'INPUT') return null;
    if (input.getAttribute('data-mys-fp-done')) return input._mysFp || null;
    opts = opts || {};
    var o = {};
    for (var k in opts) if (Object.prototype.hasOwnProperty.call(opts, k)) o[k] = opts[k];
    if (!o.inputId && input.id) o.inputId = input.id;
    if (!o.hiddenName && input.name) o.hiddenName = input.name;
    if (!o.placeholder && input.placeholder) o.placeholder = input.placeholder;
    if (o.value == null && input.value) o.value = input.value;
    var inst = create(o);
    if (input.parentNode) input.parentNode.replaceChild(inst.el, input);
    input.setAttribute('data-mys-fp-done', '1');
    input._mysFp = inst;
    return inst;
  }

  /* Enrichit les champs déclarés en HTML :
       <div data-mys-fp-auto data-fp-categories="adhesif,frontal"
            data-fp-name="fournisseur_id" data-fp-value="12"></div>  */
  function autoInit(root) {
    var scope = root || document;
    if (!scope.querySelectorAll) return;
    var nodes = scope.querySelectorAll('[data-mys-fp-auto]:not([data-mys-fp-done])');
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      n.setAttribute('data-mys-fp-done', '1');
      var cats = (n.getAttribute('data-fp-categories') || '')
        .split(',').map(function (s) { return s.trim(); }).filter(Boolean);
      var requis = n.getAttribute('data-fp-required') === '1';
      var inst = create({
        categories: cats,
        hiddenName: n.getAttribute('data-fp-name') || '',
        hiddenId: n.getAttribute('data-fp-id') || '',
        inputId: n.getAttribute('data-fp-input-id') || '',
        value: n.getAttribute('data-fp-value') || '',
        valueMode: n.getAttribute('data-fp-value-mode') || 'id',
        placeholder: n.getAttribute('data-fp-placeholder') || '',
        allowEmpty: !requis,
        required: requis,
        fscOnly: n.getAttribute('data-fp-fsc-only') === '1',
        allowFree: n.getAttribute('data-fp-allow-free') === '1'
      });
      n.appendChild(inst.el);
      n._mysFp = inst;
    }
  }

  /* ── Handlers globaux ─────────────────────────────────────── */

  document.addEventListener('mousedown', function (e) {
    if (!_active) return;
    if (_pop && _pop.contains(e.target)) return;
    if (e.target.closest && e.target.closest('.mys-fp')) return;
    close();
  }, true);

  window.addEventListener('scroll', schedulePlace, true);
  window.addEventListener('resize', schedulePlace);

  function boot() { assurerCss(); autoInit(document); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();

  window.MysFournisseurPicker = {
    create: create,
    attach: attach,
    fromSelect: fromSelect,
    autoInit: autoInit,
    load: load,
    list: function () { return _cache ? _cache.slice() : []; },
    invalidate: function () { _cache = null; _loading = null; },
    categories: function () { return (_cacheCats || []).slice(); },
    byId: function (id) {
      var n = Number(id), l = _cache || [];
      for (var i = 0; i < l.length; i++) if (l[i].id === n) return l[i];
      return null;
    },
    byNom: function (nom) {
      var n = norm(nom), l = _cache || [];
      for (var i = 0; i < l.length; i++) if (l[i]._nomNorm === n) return l[i];
      return null;
    },
    norm: norm,
    close: close,
    setEndpoint: function (url) { if (url) { ENDPOINT = url; _cache = null; _loading = null; } },
    version: '1.0'
  };
})();

/* ============================================================
   MySifa — Recherche d'encre à la saisie  (v1.0)
   ------------------------------------------------------------
   Branche le référentiel des encres (Paramètres › Fabrication ›
   Impression) sur tous les champs où l'on saisit une couleur :
   fiche technique (Tête n — Pantone / Couleur), fiche produit MyAO
   (couleur de chaque passage).

   Le champ reste un champ texte libre : on peut toujours taper une
   désignation hors référentiel. Le composant ajoute :
     - une liste de suggestions dès le 1er caractère (« 485 », « p.485c »,
       « warm red », « rose ») — flèches, Entrée, Échap ;
     - une pastille de la teinte dans le champ, calculée par le serveur
       exactement comme sur le BAT (/api/encres/resoudre).

   Il ne reconstruit jamais le champ : la pastille est un fond CSS,
   la liste vit dans <body> en position:fixed. Les champs créés après
   coup (modales, lignes ajoutées) sont pris en charge par un
   MutationObserver — l'écran appelant n'a rien à appeler.

   Champs concernés : [data-encre], plus les champs Pantone/Couleur
   des fiches techniques (#fce-tN-pantone, #fce-tN-couleur).
   data-encre="libelle" insère le libellé (« Pantone 485 C ») au lieu
   de la clé (« 485 C ») — utile quand le texte part chez un fournisseur.
   ============================================================ */
(function () {
  'use strict';
  if (window.MysEncrePicker) return;

  var SELECTEUR = '[data-encre], input[id^="fce-t"][id$="-pantone"], input[id^="fce-t"][id$="-couleur"]';
  var MAX = 40;
  var palette = null;       // promesse partagée
  var teintes = {};         // désignation → hex | null
  var enAttente = {};       // désignation → [input]
  var lotTimer = null;
  var liste = null;         // élément de la liste ouverte
  var cible = null;         // input actif
  var resultats = [];
  var actif = -1;

  function esc(v) {
    return String(v == null ? '' : v).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function norm(s) {
    s = String(s || '').normalize('NFKD').replace(/[̀-ͯ]/g, '').toUpperCase();
    s = s.replace(/[().,\/\-]/g, ' ').replace(/\b(PANTONE|PMS)\b/g, ' ');
    s = s.replace(/\bPROC\b/g, 'PROCESS').replace(/\bRUB\b/g, 'RUBINE').replace(/\bREFL\b/g, 'REFLEX');
    s = s.replace(/\s+/g, ' ').trim();
    s = s.replace(/^P(?:\s+|(?=\d))/, '');
    return s;
  }

  function chargerPalette() {
    if (!palette) {
      palette = fetch('/api/encres/palette', { credentials: 'include' })
        .then(function (r) { return r.ok ? r.json() : { encres: [] }; })
        .then(function (d) {
          return (d.encres || []).map(function (e) {
            return { cle: e[0], lib: e[1], hex: e[2], c: e[0].replace(/\s+/g, ''), l: norm(e[1]) };
          });
        })
        .catch(function () { return []; });
    }
    return palette;
  }

  /* ── Pastille ───────────────────────────────────────────── */
  function peindre(input, hex) {
    if (!input.dataset.encPad) {
      input.dataset.encPad = getComputedStyle(input).paddingLeft || '';
    }
    if (hex) {
      input.style.backgroundImage = 'linear-gradient(' + hex + ',' + hex + ')';
      input.style.backgroundRepeat = 'no-repeat';
      input.style.backgroundSize = '14px 14px';
      input.style.backgroundPosition = '10px center';
      input.style.paddingLeft = '32px';
      input.title = 'Teinte BAT : ' + hex;
    } else {
      input.style.backgroundImage = '';
      input.style.paddingLeft = '';
      if (input.title && input.title.indexOf('Teinte BAT') === 0) input.title = '';
    }
  }

  function demanderTeinte(input) {
    var v = (input.value || '').trim();
    if (!v) { peindre(input, null); return; }
    if (Object.prototype.hasOwnProperty.call(teintes, v)) { peindre(input, teintes[v]); return; }
    (enAttente[v] = enAttente[v] || []).push(input);
    clearTimeout(lotTimer);
    lotTimer = setTimeout(envoyerLot, 200);
  }

  function envoyerLot() {
    var cles = Object.keys(enAttente);
    if (!cles.length) return;
    var lot = enAttente;
    enAttente = {};
    var qs = cles.slice(0, 200).map(function (k) { return 'd=' + encodeURIComponent(k); }).join('&');
    fetch('/api/encres/resoudre?' + qs, { credentials: 'include' })
      .then(function (r) { return r.ok ? r.json() : { teintes: {} }; })
      .then(function (d) {
        var t = d.teintes || {};
        cles.forEach(function (k) {
          teintes[k] = Object.prototype.hasOwnProperty.call(t, k) ? t[k] : null;
          (lot[k] || []).forEach(function (inp) {
            if ((inp.value || '').trim() === k) peindre(inp, teintes[k]);
          });
        });
      })
      .catch(function () {});
  }

  /* ── Liste de suggestions ───────────────────────────────── */
  function filtrer(q, rows) {
    var n = norm(q);
    if (!n) return [];
    var nc = n.replace(/\s+/g, '');
    var out = [];
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i], score = -1;
      if (r.c === nc) score = 0;
      else if (r.c.indexOf(nc) === 0) score = 1;
      else if (r.l.indexOf(n) >= 0) score = 2;
      else if (r.c.indexOf(nc) > 0) score = 3;
      if (score >= 0) out.push({ r: r, s: score });
    }
    out.sort(function (a, b) {
      return (a.s - b.s) || (a.r.c.length - b.r.c.length) || (a.r.c < b.r.c ? -1 : 1);
    });
    return out.map(function (x) { return x.r; });
  }

  function placer() {
    if (!liste || !cible) return;
    var b = cible.getBoundingClientRect();
    var larg = Math.max(b.width, 260);
    var gauche = Math.min(b.left, window.innerWidth - larg - 8);
    liste.style.left = Math.max(8, gauche) + 'px';
    liste.style.width = larg + 'px';
    var bas = window.innerHeight - b.bottom;
    if (bas < 200 && b.top > bas) {
      liste.style.top = '';
      liste.style.bottom = (window.innerHeight - b.top + 4) + 'px';
    } else {
      liste.style.bottom = '';
      liste.style.top = (b.bottom + 4) + 'px';
    }
  }

  function fermer() {
    if (liste) liste.remove();
    liste = null; resultats = []; actif = -1;
  }

  function dessiner(q, total) {
    if (!liste) {
      liste = document.createElement('div');
      liste.className = 'mys-enc-list';
      liste.setAttribute('role', 'listbox');
      liste.addEventListener('mousedown', function (e) {
        e.preventDefault();  // garder le focus dans le champ
        var it = e.target.closest('.mys-enc-item');
        if (it) choisir(parseInt(it.dataset.i, 10));
      });
      document.body.appendChild(liste);
    }
    if (!resultats.length) {
      liste.innerHTML = '<div class="mys-enc-vide">Aucun résultat pour « ' + esc(q) + ' » — texte libre conservé.</div>';
    } else {
      liste.innerHTML = resultats.map(function (r, i) {
        return '<div class="mys-enc-item' + (i === actif ? ' is-active' : '') + '" role="option" data-i="' + i + '">'
          + '<span class="mys-enc-sw" style="background:' + esc(r.hex) + '"></span>'
          + '<span class="mys-enc-cle">' + esc(r.cle) + '</span>'
          + '<span class="mys-enc-lib">' + esc(r.lib) + '</span></div>';
      }).join('')
        + (total > resultats.length ? '<div class="mys-enc-pied">' + total + ' encres — précisez la saisie</div>' : '');
    }
    placer();
  }

  function ouvrir(input) {
    cible = input;
    var q = input.value;
    if (!norm(q)) { fermer(); return; }
    chargerPalette().then(function (rows) {
      if (cible !== input || document.activeElement !== input) return;
      var tous = filtrer(q, rows);
      resultats = tous.slice(0, MAX);
      actif = resultats.length ? 0 : -1;
      dessiner(q, tous.length);
    });
  }

  function choisir(i) {
    var r = resultats[i];
    if (!r || !cible) return;
    var mode = cible.getAttribute('data-encre');
    cible.value = mode === 'libelle' ? r.lib : r.cle;
    teintes[cible.value] = r.hex;
    peindre(cible, r.hex);
    cible.dispatchEvent(new Event('input', { bubbles: true }));
    cible.dispatchEvent(new Event('change', { bubbles: true }));
    fermer();
  }

  function surligner(i) {
    if (!liste || !resultats.length) return;
    actif = (i + resultats.length) % resultats.length;
    var items = liste.querySelectorAll('.mys-enc-item');
    items.forEach(function (el, k) { el.classList.toggle('is-active', k === actif); });
    if (items[actif]) items[actif].scrollIntoView({ block: 'nearest' });
  }

  /* ── Délégation ─────────────────────────────────────────── */
  function estCible(el) {
    return el && el.matches && el.tagName === 'INPUT' && el.matches(SELECTEUR);
  }

  document.addEventListener('input', function (e) {
    if (!estCible(e.target) || !e.isTrusted) return;
    ouvrir(e.target);
    demanderTeinte(e.target);
  }, true);

  document.addEventListener('focusin', function (e) {
    if (estCible(e.target)) { chargerPalette(); demanderTeinte(e.target); }
  });

  // Valeur posée par le code (pré-remplissage depuis RVGI, OF…) : l'écran
  // appelant déclenche en général un change ; on repeint à ce moment-là.
  document.addEventListener('change', function (e) {
    if (estCible(e.target)) demanderTeinte(e.target);
  }, true);

  document.addEventListener('focusout', function (e) {
    // On ne ferme que si le champ quitté est toujours la cible : passer
    // directement d'un champ encre à un autre ne doit pas fermer la
    // nouvelle liste.
    var quitte = e.target;
    if (quitte === cible) setTimeout(function () { if (cible === quitte && document.activeElement !== quitte) fermer(); }, 120);
  });

  document.addEventListener('keydown', function (e) {
    if (!liste || e.target !== cible) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); surligner(actif + 1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); surligner(actif - 1); }
    else if (e.key === 'Enter' && actif >= 0 && resultats.length) { e.preventDefault(); e.stopPropagation(); choisir(actif); }
    else if (e.key === 'Escape') { e.stopPropagation(); fermer(); }
  }, true);

  window.addEventListener('scroll', function () { if (liste) placer(); }, true);
  window.addEventListener('resize', function () { if (liste) placer(); });

  /* ── Champs présents ou ajoutés plus tard ───────────────── */
  function scanner(root) {
    var els = [];
    if (estCible(root)) els.push(root);
    if (root.querySelectorAll) els = els.concat(Array.prototype.slice.call(root.querySelectorAll(SELECTEUR)));
    els.forEach(function (inp) {
      if (inp.tagName !== 'INPUT' || inp.dataset.encOk) return;
      inp.dataset.encOk = '1';
      inp.setAttribute('autocomplete', 'off');
      demanderTeinte(inp);
    });
  }

  function demarrer() {
    scanner(document.body);
    new MutationObserver(function (muts) {
      muts.forEach(function (m) {
        m.addedNodes.forEach(function (n) { if (n.nodeType === 1) scanner(n); });
      });
    }).observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrer);
  else demarrer();

  window.MysEncrePicker = { scanner: scanner, rafraichir: function (inp) { delete inp.dataset.encOk; scanner(inp); } };
})();

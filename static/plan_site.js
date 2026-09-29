/* Plan du site — rendu SVG partagé par MyStock (Plan entrepôt) et
 * Paramètres (Emplacements).
 *
 * Les éléments viennent de `plan_site_elements` : rien du site n'est écrit
 * ici. Le cadre se calcule sur le contenu, l'origine des coordonnées n'a
 * donc pas d'importance.
 *
 *   const plan = MysPlanSite.monter(conteneur, elements, {
 *     mode: 'lecture' | 'edition',
 *     batiment: el | null,       // lecture : vue zoomée sur ce bâtiment
 *     zoomDepuisSite: true,      // anime le passage de la vue site au bâtiment
 *     statut: el => ({vert, jaune, orange, rouge}) | null,  // barre d'inventaire
 *     cellules: el => [{rangee, couleur, codes}] | null,     // vue bâtiment : rack découpé par rangée
 *     compte: el => nombre | null,                           // pastille de comptage
 *     onBatiment: bat => {},     // lecture, vue site : clic sur un bâtiment
 *     onSelect: el => {},        // clic sur un élément (null = clic dans le vide)
 *     onChange: el => {},        // édition : fin d'un déplacement / redimensionnement
 *   });
 *   plan.selectionner(id); plan.redessiner(elements);
 *
 * Un « batiment » est une zone polygonale : en vue site, c'est elle qu'on
 * clique ; en vue bâtiment, elle fixe le cadre et trie les éléments affichés
 * (ceux dont le centre tombe dedans).
 */
(function () {
  'use strict';

  const NS = 'http://www.w3.org/2000/svg';
  const TYPES_POINTS = ['contour', 'limite', 'entree', 'batiment'];
  const TYPES_LIENS = ['rack', 'sol', 'zone', 'allee', 'divers'];
  const MARGE = 14;
  const COULEURS = ['vert', 'jaune', 'orange', 'rouge'];

  const LIBELLES_TYPES = {
    rack: 'Rack de rangement',
    sol: 'Matière première au sol',
    zone: 'Zone Z0 / Z1',
    allee: 'Allée / couloir',
    machine: 'Machine',
    divers: 'Rangement divers',
    locaux: 'Bureaux · locaux',
    titre: 'Nom de bâtiment',
    batiment: 'Bâtiment (zone cliquable)',
    contour: 'Contour des bâtiments',
    limite: 'Limite entre bâtiments',
    entree: "Sens d'entrée",
  };

  function mk(tag, attrs, parent) {
    const n = document.createElementNS(NS, tag);
    if (attrs) for (const k in attrs) if (attrs[k] != null) n.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(n);
    return n;
  }

  function cadre(elements) {
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    const pousser = (x, y) => {
      x0 = Math.min(x0, x); y0 = Math.min(y0, y);
      x1 = Math.max(x1, x); y1 = Math.max(y1, y);
    };
    elements.forEach(e => {
      if (TYPES_POINTS.includes(e.type)) (e.points || []).forEach(p => pousser(p[0], p[1]));
      else { pousser(e.x, e.y); pousser(e.x + e.w, e.y + e.h); }
    });
    if (!isFinite(x0)) return { x: 0, y: 0, w: 600, h: 400 };
    return { x: x0 - MARGE, y: y0 - MARGE, w: (x1 - x0) + 2 * MARGE, h: (y1 - y0) + 2 * MARGE };
  }

  // ── Géométrie ────────────────────────────────────────────────────
  function dedans(pt, poly) {
    let c = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const xi = poly[i][0], yi = poly[i][1], xj = poly[j][0], yj = poly[j][1];
      if (((yi > pt[1]) !== (yj > pt[1])) && (pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi)) c = !c;
    }
    return c;
  }

  function centreEl(e) {
    if (TYPES_POINTS.includes(e.type)) {
      const pts = e.points || [];
      if (!pts.length) return [0, 0];
      const s = pts.reduce((a, p) => [a[0] + p[0], a[1] + p[1]], [0, 0]);
      return [s[0] / pts.length, s[1] / pts.length];
    }
    return [e.x + e.w / 2, e.y + e.h / 2];
  }

  // Éléments d'un bâtiment : ceux dont le centre tombe dans sa zone.
  // Les traits (limites, contour) n'appartiennent à aucun bâtiment.
  function elementsDuBatiment(bat, elements) {
    const poly = (bat && bat.points) || [];
    if (poly.length < 3) return [];
    return (elements || []).filter(e =>
      !['batiment', 'contour', 'limite'].includes(e.type) && dedans(centreEl(e), poly));
  }

  // Code d'emplacement = préfixe + rangée (2 chiffres) + niveau (1 chiffre).
  // Tout autre format n'a pas de place dans une grille : null.
  function decouperCode(code, prefixe) {
    const reste = String(code || '').toUpperCase().slice((prefixe || '').length);
    const m = reste.match(/^(\d{2})(\d)$/);
    return m ? { rangee: m[1], niveau: m[2] } : null;
  }

  // Taille de police qui fait tenir `txt` dans une largeur donnée.
  function taillePolice(txt, largeur, hauteur, max) {
    const n = Math.max(1, (txt || '').length);
    let fs = Math.min(max, hauteur * 0.62);
    fs = Math.min(fs, (largeur - 4) / (n * 0.56));
    return Math.max(3.2, fs);
  }

  function texte(g, txt, cx, cy, fs, cls, rot) {
    const t = mk('text', {
      x: cx, y: cy, 'font-size': fs.toFixed(2), class: cls,
      'text-anchor': 'middle', 'dominant-baseline': 'central',
      transform: rot ? `rotate(-90 ${cx} ${cy})` : null,
    }, g);
    t.textContent = txt;
    return t;
  }

  function dessinerRect(g, e, opts) {
    mk('rect', { x: e.x, y: e.y, width: e.w, height: e.h, rx: e.type === 'rack' ? 1 : 1.5, class: 'ps-forme' }, g);
    if (e.type === 'machine') {
      mk('line', { x1: e.x, y1: e.y, x2: e.x + e.w, y2: e.y + e.h, class: 'ps-croix' }, g);
      mk('line', { x1: e.x + e.w, y1: e.y, x2: e.x, y2: e.y + e.h, class: 'ps-croix' }, g);
    }
    const cx = e.x + e.w / 2, cy = e.y + e.h / 2;
    const long = e.vertical ? e.h : e.w, court = e.vertical ? e.w : e.h;

    // Vue bâtiment : le rack se découpe en rangées, chacune à la couleur de
    // son emplacement le moins récemment inventorié.
    const cels = opts.cellules ? opts.cellules(e) : null;
    if (cels && cels.length) {
      const pas = long / cels.length, ins = Math.min(1, court * 0.08);
      cels.forEach((c, i) => {
        const r = e.vertical
          ? { x: e.x + ins, y: e.y + i * pas + 0.3, width: e.w - 2 * ins, height: Math.max(0.5, pas - 0.6) }
          : { x: e.x + i * pas + 0.3, y: e.y + ins, width: Math.max(0.5, pas - 0.6), height: e.h - 2 * ins };
        const cel = mk('rect', Object.assign(r, { class: 'ps-cel ps-cel-' + c.couleur }), g);
        const tt = mk('title', null, cel);
        tt.textContent = (e.libelle || e.prefixe) + ' · rangée ' + c.rangee
          + (c.codes ? ' · ' + c.codes.join(', ') : '');
      });
    }

    let lib = e.libelle || '';
    const n = opts.compte ? opts.compte(e) : null;
    if (n != null && lib) lib += ' · ' + n;
    const max = e.type === 'rack' ? 9 : 8;
    const clsLib = 'ps-lib' + (cels && cels.length ? ' ps-lib-halo' : '');
    if (e.sous_titre && court >= 16) {
      const fs = taillePolice(lib, long, court / 2, max);
      const fs2 = taillePolice(e.sous_titre, long, court / 2, max - 1.5);
      const dy = (fs + fs2) / 2 * 0.62;
      if (e.vertical) {
        texte(g, lib, cx - dy, cy, fs, clsLib, true);
        texte(g, e.sous_titre, cx + dy, cy, fs2, 'ps-sous', true);
      } else {
        texte(g, lib, cx, cy - dy, fs, clsLib);
        texte(g, e.sous_titre, cx, cy + dy, fs2, 'ps-sous');
      }
    } else if (lib) {
      // Libellé long dans une boîte haute : sur deux lignes plutôt qu'en tout petit.
      const mots = lib.split(' ');
      const fs1 = taillePolice(lib, long, court, max);
      if (!e.vertical && mots.length >= 3 && court >= 22 && fs1 < 5.5) {
        const moitie = Math.ceil(mots.length / 2);
        const l1 = mots.slice(0, moitie).join(' '), l2 = mots.slice(moitie).join(' ');
        const fs = Math.min(taillePolice(l1, long, court / 2, max), taillePolice(l2, long, court / 2, max));
        texte(g, l1, cx, cy - fs * 0.6, fs, clsLib);
        texte(g, l2, cx, cy + fs * 0.6, fs, clsLib);
      } else {
        texte(g, lib, cx, cy, fs1, clsLib, e.vertical);
      }
    }
    if (cels && cels.length) return;

    // Barre d'inventaire : répartition des emplacements par ancienneté.
    const st = opts.statut ? opts.statut(e) : null;
    if (st) {
      const total = COULEURS.reduce((a, c) => a + (st[c] || 0), 0);
      if (total > 0) {
        const ep = Math.min(2.4, court * 0.18);
        let pos = 0;
        COULEURS.forEach(c => {
          const v = st[c] || 0;
          if (!v) return;
          const part = (v / total) * long;
          if (e.vertical) mk('rect', { x: e.x + e.w - ep, y: e.y + e.h - pos - part, width: ep, height: part, class: 'ps-inv ps-inv-' + c }, g);
          else mk('rect', { x: e.x + pos, y: e.y + e.h - ep, width: part, height: ep, class: 'ps-inv ps-inv-' + c }, g);
          pos += part;
        });
      }
    }
  }

  function dessinerTitre(g, e) {
    const cx = e.x + e.w / 2;
    const fs = taillePolice(e.libelle, e.w, e.sous_titre ? e.h * 0.6 : e.h, 14);
    if (e.sous_titre) {
      texte(g, e.libelle, cx, e.y + fs * 0.6, fs, 'ps-titre');
      texte(g, e.sous_titre, cx, e.y + fs * 1.2 + fs * 0.45, fs * 0.62, 'ps-titre-sous');
    } else {
      texte(g, e.libelle, cx, e.y + e.h / 2, fs, 'ps-titre');
    }
    // Surface cliquable (édition) : le texte seul est trop fin à attraper.
    mk('rect', { x: e.x, y: e.y, width: e.w, height: e.h, class: 'ps-zone-clic' }, g);
  }

  function dessinerPoints(g, e, edition) {
    const pts = (e.points || []).map(p => p.join(',')).join(' ');
    if (e.type === 'contour') {
      mk('polygon', { points: pts, class: 'ps-contour' }, g);
    } else if (e.type === 'batiment') {
      mk('polygon', { points: pts, class: 'ps-bat' }, g);
      if (edition && e.libelle && e.points && e.points.length) {
        const x0 = Math.min(...e.points.map(p => p[0])), y0 = Math.min(...e.points.map(p => p[1]));
        const t = mk('text', { x: x0 + 3, y: y0 + 7, 'font-size': 5.5, class: 'ps-bat-lib' }, g);
        t.textContent = e.libelle;
      }
    } else if (e.type === 'limite') {
      mk('polyline', { points: pts, class: 'ps-limite-clic' }, g);
      mk('polyline', { points: pts, class: 'ps-limite' }, g);
    } else {
      mk('polyline', { points: pts, class: 'ps-limite-clic' }, g);
      mk('polyline', { points: pts, class: 'ps-entree', 'marker-end': 'url(#ps-fleche)' }, g);
    }
  }

  function reduireAnimations() {
    const h = document.documentElement, b = document.body;
    return h.classList.contains('reduce-anim') || h.classList.contains('perf-eco')
      || (b && b.classList.contains('perf-eco'))
      || (window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches);
  }

  function monter(conteneur, elements, opts) {
    opts = opts || {};
    const edition = opts.mode === 'edition';
    let els = (elements || []).map(e => Object.assign({}, e));
    let selId = null;
    const focus = !edition && opts.batiment ? opts.batiment : null;
    // Vue site : on clique un bâtiment. Sans bâtiment dessiné, on clique les racks.
    const vueSite = !edition && !focus && els.some(e => e.type === 'batiment');
    let vb = cadreCourant();

    conteneur.innerHTML = '';
    conteneur.classList.add('ps-wrap');
    conteneur.classList.toggle('ps-edition', edition);
    conteneur.classList.toggle('ps-vue-site', vueSite);
    conteneur.classList.toggle('ps-vue-batiment', !!focus);
    const svg = mk('svg', { class: 'ps-svg', role: 'img', 'aria-label': focus ? (focus.libelle || 'Bâtiment') : 'Plan du site' }, conteneur);

    function cadreCourant() {
      if (focus) return cadre([focus]);
      return cadre(els.filter(e => e.type !== 'batiment' || edition));
    }

    function visibles() {
      if (!focus) return els;
      return elementsDuBatiment(focus, els);
    }

    function pointSvg(evt) {
      const pt = svg.createSVGPoint();
      pt.x = evt.clientX; pt.y = evt.clientY;
      const m = svg.getScreenCTM();
      return m ? pt.matrixTransform(m.inverse()) : { x: 0, y: 0 };
    }

    function poserCadre(v) { svg.setAttribute('viewBox', `${v.x} ${v.y} ${v.w} ${v.h}`); }

    function dessiner() {
      svg.innerHTML = '';
      poserCadre(vb);
      const defs = mk('defs', null, svg);
      const mark = mk('marker', { id: 'ps-fleche', viewBox: '0 0 10 10', refX: 8, refY: 5, markerWidth: 5, markerHeight: 5, orient: 'auto-start-reverse' }, defs);
      mk('path', { d: 'M0,0 L10,5 L0,10 z', class: 'ps-fleche' }, mark);

      // Vue bâtiment : le bâtiment tient lieu de contour.
      if (focus) {
        mk('polygon', { points: (focus.points || []).map(p => p.join(',')).join(' '), class: 'ps-contour ps-bat-focus' }, svg);
      }

      // Ordre de peinture : contours d'abord, puis surfaces, textes et traits.
      // En vue site, les bâtiments passent au-dessus de tout : ce sont eux qu'on clique.
      const rang = t => ({
        contour: 0, batiment: vueSite ? 9 : 0.5, locaux: 1, machine: 1, zone: 1,
        sol: 2, divers: 2, allee: 2, rack: 3, titre: 4, limite: 5, entree: 5,
      }[t] ?? 3);
      visibles().slice().sort((a, b) => rang(a.type) - rang(b.type) || (a.ordre || 0) - (b.ordre || 0)).forEach(e => {
        const lie = TYPES_LIENS.includes(e.type) && !!e.prefixe;
        const bat = e.type === 'batiment';
        const cliquable = edition || (vueSite ? bat : lie);
        const g = mk('g', {
          class: 'ps-el ps-t-' + e.type + (lie ? ' ps-lie' : '') + (e.id === selId ? ' ps-sel' : ''),
          'data-id': e.id,
          tabindex: cliquable ? 0 : null,
          role: cliquable ? 'button' : null,
        }, svg);
        if (cliquable) {
          const tt = mk('title', null, g);
          tt.textContent = bat && vueSite
            ? (e.libelle || 'Bâtiment') + ' — voir le détail des emplacements'
            : (e.libelle || LIBELLES_TYPES[e.type] || '') + (e.prefixe ? ' — emplacements ' + e.prefixe + '…' : '');
        }
        if (TYPES_POINTS.includes(e.type)) dessinerPoints(g, e, edition);
        else if (e.type === 'titre') dessinerTitre(g, e);
        else dessinerRect(g, e, opts);
        if (e.id === selId && edition) poignees(g, e);
      });
    }

    function poignees(g, e) {
      if (TYPES_POINTS.includes(e.type)) {
        (e.points || []).forEach((p, i) => {
          mk('circle', { cx: p[0], cy: p[1], r: 3.2, class: 'ps-poignee', 'data-pt': i }, g);
        });
      } else {
        mk('rect', { x: e.x + e.w - 3, y: e.y + e.h - 3, width: 6, height: 6, class: 'ps-poignee', 'data-resize': 1 }, g);
      }
    }

    function trouver(id) { return els.find(e => String(e.id) === String(id)); }

    function choisir(e) {
      selId = e ? e.id : null;
      dessiner();
      if (opts.onSelect) opts.onSelect(e ? Object.assign({}, e) : null);
    }

    function activer(e) {
      if (vueSite) {
        if (e && e.type === 'batiment' && opts.onBatiment) opts.onBatiment(Object.assign({}, e));
        return;
      }
      if (!edition && e && !(TYPES_LIENS.includes(e.type) && e.prefixe)) { choisir(null); return; }
      choisir(e);
    }

    svg.addEventListener('click', evt => {
      if (glisse && glisse.bouge) return;
      const g = evt.target.closest('.ps-el');
      activer(g ? trouver(g.getAttribute('data-id')) : null);
    });
    svg.addEventListener('keydown', evt => {
      if (evt.key !== 'Enter' && evt.key !== ' ') return;
      const g = evt.target.closest && evt.target.closest('.ps-el');
      if (g) { evt.preventDefault(); activer(trouver(g.getAttribute('data-id'))); }
    });

    // ── Édition : déplacer, redimensionner, bouger un point ─────────
    let glisse = null;
    if (edition) {
      svg.addEventListener('pointerdown', evt => {
        const g = evt.target.closest('.ps-el');
        if (!g) return;
        const e = trouver(g.getAttribute('data-id'));
        if (!e || e.id !== selId) return;   // on ne glisse que l'élément sélectionné
        const p = pointSvg(evt);
        glisse = {
          e, x0: p.x, y0: p.y, bouge: false,
          orig: JSON.parse(JSON.stringify(e)),
          pt: evt.target.hasAttribute('data-pt') ? +evt.target.getAttribute('data-pt') : null,
          resize: evt.target.hasAttribute('data-resize'),
        };
        try { svg.setPointerCapture(evt.pointerId); } catch (e) {}
        evt.preventDefault();
      });
      svg.addEventListener('pointermove', evt => {
        if (!glisse) return;
        const p = pointSvg(evt);
        const dx = Math.round(p.x - glisse.x0), dy = Math.round(p.y - glisse.y0);
        if (!glisse.bouge && Math.abs(dx) + Math.abs(dy) < 1) return;
        glisse.bouge = true;
        const e = glisse.e, o = glisse.orig;
        if (glisse.pt != null) {
          e.points[glisse.pt] = [o.points[glisse.pt][0] + dx, o.points[glisse.pt][1] + dy];
        } else if (TYPES_POINTS.includes(e.type)) {
          e.points = o.points.map(q => [q[0] + dx, q[1] + dy]);
        } else if (glisse.resize) {
          e.w = Math.max(4, o.w + dx); e.h = Math.max(4, o.h + dy);
        } else {
          e.x = o.x + dx; e.y = o.y + dy;
        }
        dessiner();
      });
      const fin = () => {
        if (!glisse) return;
        const g = glisse;
        setTimeout(() => { glisse = null; }, 0);
        if (g.bouge && opts.onChange) opts.onChange(Object.assign({}, g.e));
        if (g.bouge && opts.onSelect) opts.onSelect(Object.assign({}, g.e));
      };
      svg.addEventListener('pointerup', fin);
      svg.addEventListener('pointercancel', fin);
    }

    dessiner();

    // Zoom animé de la vue site vers le bâtiment : on part du cadre du site.
    if (focus && opts.zoomDepuisSite && !reduireAnimations()) {
      const depart = cadre(els.filter(e => e.type !== 'batiment'));
      const arrivee = vb, t0 = performance.now(), duree = 380;
      const pas = t => {
        const k = Math.min(1, (t - t0) / duree), a = 1 - Math.pow(1 - k, 3);
        poserCadre({
          x: depart.x + (arrivee.x - depart.x) * a, y: depart.y + (arrivee.y - depart.y) * a,
          w: depart.w + (arrivee.w - depart.w) * a, h: depart.h + (arrivee.h - depart.h) * a,
        });
        if (k < 1) requestAnimationFrame(pas);
      };
      poserCadre(depart);
      requestAnimationFrame(pas);
      // Onglet masqué : requestAnimationFrame ne tourne pas, on pose le cadre final.
      setTimeout(() => poserCadre(arrivee), duree + 120);
    }

    return {
      selectionner(id) { selId = id; dessiner(); },
      redessiner(elements, garderCadre) {
        els = (elements || []).map(e => Object.assign({}, e));
        if (!garderCadre) vb = cadreCourant();
        dessiner();
      },
      recadrer() { vb = cadreCourant(); dessiner(); },
      // Centre de la vue actuelle : où poser un nouvel élément.
      centre() { return { x: Math.round(vb.x + vb.w / 2), y: Math.round(vb.y + vb.h / 2) }; },
    };
  }

  // Légende : types présents sur le plan, dans l'ordre de la légende d'origine.
  function legende(elements) {
    const presents = new Set((elements || []).map(e => e.type));
    const ordre = ['rack', 'sol', 'zone', 'machine', 'divers', 'locaux', 'entree', 'limite'];
    const wrap = document.createElement('div');
    wrap.className = 'ps-legende';
    ordre.filter(t => presents.has(t)).forEach(t => {
      const it = document.createElement('span');
      it.className = 'ps-legende-item';
      const sw = document.createElement('span');
      sw.className = 'ps-legende-sw ps-sw-' + t;
      it.appendChild(sw);
      it.appendChild(document.createTextNode(LIBELLES_TYPES[t]));
      wrap.appendChild(it);
    });
    return wrap;
  }

  function codesDe(e, codes) {
    const pre = (e && e.prefixe || '').toUpperCase();
    if (!pre) return [];
    return (codes || []).filter(c => {
      c = String(c).toUpperCase();
      return c === pre || (c.startsWith(pre) && /\d/.test(c.charAt(pre.length)));
    });
  }

  window.MysPlanSite = {
    monter, legende, codesDe, elementsDuBatiment, decouperCode,
    TYPES_POINTS, TYPES_LIENS, LIBELLES_TYPES, COULEURS,
  };
})();

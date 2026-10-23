/* MyTools › Calculs bobine — calculs d'atelier, un à la fois.
 *
 *   metrage     Métrage ↔ diamètre : longueur enroulée, ou diamètre atteint.
 *   fronts      Fronts sur la laize : combien d'étiquettes de front, chute.
 *   etiquettes  Étiquettes par bobine, ou métrage pour une quantité visée.
 *   carton      Carton optimal parmi les références carton de MyStock
 *               (GET /api/tools/cartons, dimensions lues dans la désignation).
 *
 * Retour d'Eugène (21/10/2026) : « trop d'info visible ». Un seul calcul à
 * l'écran (onglets, dans l'adresse : ?outil=calculs&calcul=…), l'essentiel en
 * clair, le secondaire (espaces, rive, jeu, matière) dans « Réglages fins ».
 *
 * Formules (mêmes conventions que le reste de MySifa) :
 *   métrage (m)  = π × ((Øbobine/2)² − (Ømandrin/2)²) ÷ épaisseur   (mm, µm ; mm² ÷ µm = m)
 *                  — celle du widget « Métrage bobine » de MyStock ;
 *   Øbobine (mm) = 2 × √((Ømandrin/2)² + métrage × épaisseur ÷ π)
 *   fronts       = ⌊(laize − 2 × rive) ÷ (étiquette + espace)⌋     (of-fiches-techniques)
 *   métrage      = quantité ÷ fronts × (hauteur + espace) ÷ 1000
 *   carton       bobines rangées en grille, toujours debout (base au sol, axe
 *                vertical — règle d'atelier, 23/10/2026) ; dimensions du carton
 *                diminuées du jeu.
 *
 * Épaisseur : une épaisseur type (GET /api/stock/metrage-epaisseurs), ou la
 * somme des couches choisies parmi les matières MyStock — frontal + adhésif +
 * glassine (GET /api/tools/couches : fiche technique, sinon MyStock, sinon
 * RVGI). Aucune règle ne déduit une épaisseur du grammage : une couche sans
 * épaisseur connue se saisit. Le total remplit le champ Épaisseur, qui reste
 * modifiable.
 *
 * Retour du 23/10/2026 : Réglages fins dans une carte à part, résumé visible
 * replié ; un schéma à l'échelle à droite de chaque calcul
 * (static/mysifa_tools_calculs_schemas.js).
 *
 * La saisie du métrage est partagée avec le widget de MyStock (clé
 * `mysifa_mtr_saisie_v1`). Rien n'est enregistré côté serveur.
 *
 *   MyToolsCalculs.mount(root, ctx)
 *   MyToolsCalculs.adresse = { etat() → {calcul, couches, type}, aller({…}) }
 *     couches = { <catégorie>: <id matière> }, type = id d'épaisseur type
 */
(function () {
  'use strict';
  if (window.MyToolsCalculs) return;

  const LS_MTR = 'mysifa_mtr_saisie_v1';
  const LS_CALC = 'mysifa_tools_calculs_v2';
  // [id, titre, ce que le calculateur donne, icône (grille 24)]
  const ONGLETS = [
    ['metrage', 'Métrage ↔ diamètre', 'La longueur enroulée sur une bobine, ou le diamètre qu\'elle atteint.',
      '<circle cx="10" cy="10" r="6.5"/><circle cx="10" cy="10" r="2"/><path d="M10 16.5h10.5"/>'],
    ['fronts', 'Fronts sur la laize', 'Combien d\'étiquettes de front tiennent sur la bobine, et la chute.',
      '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M9 5v14M15 5v14"/>'],
    ['etiquettes', 'Étiquettes par bobine', 'Combien d\'étiquettes sur un métrage, ou quel métrage pour une quantité.',
      '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M5 9h14M5 15h14"/>'],
    ['carton', 'Carton optimal', 'Le carton de nos références qui range le mieux les bobines.',
      '<path d="M12 3.5l8 4.5v8l-8 4.5L4 16V8z"/><path d="M4 8l8 4.5L20 8M12 12.5v8"/>'],
  ];
  const svg = (d, t) => '<svg width="' + (t || 22) + '" height="' + (t || 22) + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';

  // ── Calculs purs (tests/test_tools_calculs.js) ─────────────────────
  const n = v => { const x = parseFloat(String(v == null ? '' : v).replace(',', '.')); return isFinite(x) ? x : NaN; };
  const n0 = v => (isNaN(n(v)) ? 0 : n(v));

  function metrage(microns, dMandrin, dBobine) {
    const e = n(microns), d = n(dMandrin), D = n(dBobine);
    if (!(e > 0) || !(d > 0) || !(D > 0)) return { vide: true };
    if (D <= d) return { erreur: 'Le diamètre de la bobine doit dépasser celui du mandrin.' };
    return { metres: Math.PI * ((D / 2) * (D / 2) - (d / 2) * (d / 2)) / e };
  }
  function diametre(microns, dMandrin, metres) {
    const e = n(microns), d = n(dMandrin), L = n(metres);
    if (!(e > 0) || !(d > 0) || !(L > 0)) return { vide: true };
    return { mm: 2 * Math.sqrt((d / 2) * (d / 2) + L * e / Math.PI) };
  }
  function fronts(laize, largeur, espace, rive) {
    const W = n(laize), l = n(largeur), g = n0(espace), r = n0(rive);
    if (!(W > 0) || !(l > 0)) return { vide: true };
    if (g < 0 || r < 0) return { erreur: 'Espace et rive ne peuvent pas être négatifs.' };
    const module = l + g, nb = Math.floor((W - 2 * r + 1e-9) / module);
    if (nb < 1) return { erreur: 'Aucune étiquette ne tient sur cette laize.', module };
    const utilisee = nb * module;
    return { nb, module, utilisee, chute: W - utilisee, chutePct: (W - utilisee) / W * 100 };
  }
  function laizeMini(nb, largeur, espace, rive) {
    const N = Math.floor(n(nb)), l = n(largeur);
    if (!(N >= 1) || !(l > 0)) return null;
    return N * (l + n0(espace)) + 2 * n0(rive);
  }
  function etiquettes(metres, hauteur, espace, nbFronts) {
    const L = n(metres), h = n(hauteur), f = Math.floor(n(nbFronts)) || 1;
    if (!(L > 0) || !(h > 0)) return { vide: true };
    const module = h + n0(espace), parFront = Math.floor((L * 1000 + 1e-6) / module);
    return { parFront, total: parFront * f, module };
  }
  function metragePour(quantite, hauteur, espace, nbFronts) {
    const q = n(quantite), h = n(hauteur), f = Math.floor(n(nbFronts)) || 1;
    if (!(q > 0) || !(h > 0)) return null;
    return Math.ceil(q / f) * (h + n0(espace)) / 1000;
  }

  // Épaisseur d'une matière composée : somme des couches choisies.
  // `couches` : [{ libelle, microns }] (microns vide = inconnue). Rend null si
  // aucune couche n'est choisie ; `complet` = toutes les épaisseurs connues.
  function epaisseurCouches(couches) {
    const ch = (couches || []).filter(Boolean);
    if (!ch.length) return null;
    let total = 0;
    const manquantes = [];
    ch.forEach(c => { const e = n(c.microns); if (e > 0) total += e; else manquantes.push(c.libelle); });
    return { total, manquantes, complet: !manquantes.length, nb: ch.length };
  }

  // Rangement de bobines (Ø D, largeur L) dans un carton (l × w × h, intérieur),
  // en grille. `sens` : { debout, couche }.
  function rangement(D, L, carton, jeu, sens) {
    const j = n0(jeu), l = carton.l - j, w = carton.w - j, h = carton.h - j;
    if (!(D > 0) || !(L > 0) || l <= 0 || w <= 0 || h <= 0) return null;
    const essais = [];
    if (sens.debout) essais.push({ sens: 'debout', axe: 'v', a: Math.floor(l / D), b: Math.floor(w / D), c: Math.floor(h / L) });
    if (sens.couche) {
      essais.push({ sens: 'couchées', axe: 'l', a: Math.floor(l / L), b: Math.floor(w / D), c: Math.floor(h / D) });
      essais.push({ sens: 'couchées', axe: 'w', a: Math.floor(l / D), b: Math.floor(w / L), c: Math.floor(h / D) });
    }
    let mieux = null;
    essais.forEach(e => { e.nb = e.a * e.b * e.c; if (e.nb > 0 && (!mieux || e.nb > mieux.nb)) mieux = e; });
    return mieux;
  }
  // Classement des cartons pour Q bobines (facultatif). « Optimal » = le moins
  // de vide : avec Q, le plus petit volume d'emballage au total (nb de cartons ×
  // volume), puis le moins de cartons ; sans Q, le meilleur remplissage d'un carton.
  // (Un grand box d'une seule unité rempli à 4 % ne passe pas devant deux cartons pleins.)
  function classerCartons(cartons, D, L, quantite, jeu, sens, priorite) {
    const Q = Math.floor(n(quantite)) || 0;
    const vBob = Math.PI * (D / 2) * (D / 2) * L;
    const res = [];
    (cartons || []).forEach(c => {
      const r = rangement(D, L, c, jeu, sens);
      if (!r) return;
      const vCarton = c.l * c.w * c.h;
      const ligne = { carton: c, rang: r, parCarton: r.nb, remplissage: r.nb * vBob / vCarton };
      if (Q > 0) {
        ligne.nbCartons = Math.ceil(Q / r.nb);
        ligne.dernier = Q - (ligne.nbCartons - 1) * r.nb;
        ligne.volumeTotal = ligne.nbCartons * vCarton;
        ligne.remplissageTotal = Q * vBob / ligne.volumeTotal;
      }
      res.push(ligne);
    });
    // À volume équivalent (moins de 5 % d'écart), le moins de cartons l'emporte :
    // dix petits cartons ne valent pas trois moyens pour 2 % de vide en moins.
    const procheVol = (a, b) => Math.abs(a - b) / Math.max(a, b) < 0.05;
    res.sort((x, y) => {
      if (!(Q > 0)) return (y.remplissage - x.remplissage) || (y.parCarton - x.parCarton);
      if (priorite === 'cartons') return (x.nbCartons - y.nbCartons) || (x.volumeTotal - y.volumeTotal);
      return procheVol(x.volumeTotal, y.volumeTotal) ? (x.nbCartons - y.nbCartons) || (x.volumeTotal - y.volumeTotal) : x.volumeTotal - y.volumeTotal;
    });
    return res;
  }

  // ── Interface ──────────────────────────────────────────────────────
  let CTX = { toast: () => {}, surChange: null };
  const C = {
    host: null, onglet: 'metrage', epaisseurs: null, cartons: null, ecartes: [], tousCartons: false,
    couches: null,      // [{categorie, libelle, matieres:[{id, libelle, epaisseur_um, source, grammage_gsm}]}]
    choix: {},          // { categorie: id matière }
    umCouche: {},       // { categorie: µm saisis pour la couche }
    adresseAttente: null,
  };
  const fmt = (x, dec) => Number(x).toLocaleString('fr-FR', { minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0 });
  const fmtL = x => Number(x).toLocaleString('fr-FR', { maximumFractionDigits: 2 });
  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  function lire(cle) { try { return JSON.parse(localStorage.getItem(cle) || '{}') || {}; } catch (e) { return {}; } }
  function ecrire(cle, v) { try { localStorage.setItem(cle, JSON.stringify(v)); } catch (e) {} }
  function signaler() { if (typeof CTX.surChange === 'function') { try { CTX.surChange(); } catch (e) {} } }
  const $ = id => C.host.querySelector('#' + id);
  const val = id => ($(id) ? $(id).value : '');
  const SCH = () => window.MyToolsCalculsSchemas || null;

  const CHAMPS = ['ep', 'dm', 'db', 'lm', 'laize', 'larg', 'espl', 'rive', 'nbv', 'haut', 'espa', 'nbf', 'l3m', 'qte', 'cd', 'cl', 'cq', 'jeu'];
  function champ(id, label, attrs, bulle) {
    const a = Object.assign({ type: 'number', min: '0', step: 'any', inputmode: 'decimal' }, attrs || {});
    return '<label class="tcal-champ" for="tcal-' + id + '"' + (bulle ? ' data-bulle="' + esc(bulle) + '"' : '') + '><span>' + esc(label) + '</span>'
      + '<input id="tcal-' + id + '" class="tcal-in"' + Object.keys(a).map(k => ' ' + k + '="' + esc(a[k]) + '"').join('') + '></label>';
  }
  // Question à deux réponses, en cartes : « Ce que je cherche : … ».
  const question = (nom, libelle, choix) => '<div class="tcal-question"><div class="tcal-question-l">' + esc(libelle) + '</div>'
    + '<div class="tcal-choix" role="radiogroup" data-seg="' + nom + '">'
    + choix.map(c => '<button type="button" role="radio" class="tcal-choix-b" data-v="' + c[0] + '">'
      + '<span class="tcal-choix-coche" aria-hidden="true"></span><span class="tcal-choix-txt"><b>' + esc(c[1]) + '</b><small>' + esc(c[2]) + '</small></span></button>').join('')
    + '</div></div>';
  const seg = (nom, choix) => '<div class="tcal-seg" role="group" data-seg="' + nom + '">'
    + choix.map(c => '<button type="button" class="tcal-seg-b" data-v="' + c[0] + '"' + (c[2] ? ' data-bulle="' + esc(c[2]) + '"' : '') + '>' + esc(c[1]) + '</button>').join('') + '</div>';
  const res = id => '<div class="tcal-res tcal-res--vide" id="tcal-r-' + id + '"><div class="tcal-res-v">—</div><div class="tcal-res-l"></div></div>';
  // Réglages fins : une carte à part, ouverte par défaut (retours d'Eugène du
  // 21 et du 23/10) ; repliée, elle résume ce qui est réglé.
  const IC_FINS = '<line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="18" x2="20" y2="18"/><circle cx="9" cy="6" r="2"/><circle cx="15" cy="12" r="2"/><circle cx="8" cy="18" r="2"/>';
  const fins = (id, contenu, aide) => '<section class="tcal-carte tcal-fins-carte"><details class="tcal-fins" id="tcal-f-' + id + '" open>'
    + '<summary data-bulle="Replier"><span class="tcal-fins-ic">' + svg(IC_FINS, 18) + '</span>'
    + '<span class="tcal-fins-tx"><span class="tcal-fins-t">Réglages fins</span><span class="tcal-fins-aide">' + esc(aide) + '</span>'
    + '<span class="tcal-fins-resume" id="tcal-fr-' + id + '"></span></span>'
    + '<svg class="tcal-fins-chev" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg></summary>'
    + '<div class="tcal-fins-corps">' + contenu + '</div></details></section>';
  const schema = id => '<aside class="tcal-schema" aria-label="Schéma"><div class="tcal-schema-tete"><span class="tcal-schema-t">Schéma</span>'
    + '<span class="tcal-schema-ex" id="tcal-sx-' + id + '" hidden>Exemple</span></div>'
    + '<div class="tcal-schema-dessin" id="tcal-s-' + id + '"></div><div class="tcal-schema-leg" id="tcal-sl-' + id + '"></div></aside>';
  const panneau = (id, carte, reglages) => '<section class="tcal-panneau" data-panneau="' + id + '"' + (id === 'metrage' ? '' : ' hidden') + '>'
    + '<div class="tcal-gauche"><div class="tcal-carte">' + tete(id) + carte + '</div>' + reglages + '</div>' + schema(id) + '</section>';

  function tete(id) {
    const o = ONGLETS.find(x => x[0] === id);
    return '<header class="tcal-tete"><span class="tcal-tete-ic">' + svg(o[3], 26) + '</span><div><h2>' + esc(o[1]) + '</h2><p>' + esc(o[2]) + '</p></div></header>';
  }
  function construire() {
    const h = C.host;
    h.className = 'tcal';
    h.innerHTML =
      '<div class="tcal-onglets" role="tablist" aria-label="Calculateurs">' + ONGLETS.map(o =>
        '<button type="button" role="tab" class="tcal-onglet" data-onglet="' + o[0] + '">'
        + '<span class="tcal-onglet-ic">' + svg(o[3]) + '</span><span class="tcal-onglet-t">' + esc(o[1]) + '</span>'
        + '<span class="tcal-onglet-d">' + esc(o[2]) + '</span></button>').join('') + '</div>'
      + panneau('metrage',
        question('sens', 'Ce que je cherche', [['metrage', 'Le métrage', 'Je mesure le Ø de la bobine → j\'obtiens les mètres'],
          ['diametre', 'Le diamètre', 'Je connais les mètres → j\'obtiens le Ø de la bobine']])
        + '<div class="tcal-grille">' + champ('ep', 'Épaisseur (µm)', { placeholder: '145' }, 'Matière + adhésif + glassine')
        + champ('dm', 'Ø mandrin (mm)', { placeholder: '76' }, 'Diamètre extérieur')
        + champ('db', 'Ø bobine (mm)', { placeholder: '1000' }, 'Diamètre extérieur')
        + champ('lm', 'Métrage (m)', { placeholder: '2000' }) + '</div>'
        + res('metrage')
        + '<div class="tcal-err" id="tcal-e-metrage"></div>',
        fins('metrage',
          '<div class="tcal-fins-bloc"><div class="tcal-titre">Épaisseur type</div>'
          + '<label class="tcal-champ" for="tcal-type"><span class="tcal-sr">Épaisseur type</span><select id="tcal-type" class="tcal-in"><option value="">Aucune — saisie libre ou couches</option></select></label></div>'
          + '<div class="tcal-fins-bloc"><div class="tcal-titre">Ou la matière couche par couche</div>'
          + '<div class="tcal-couches" id="tcal-couches"><div class="tcal-aide">Chargement des matières MyStock…</div></div>'
          + '<div class="tcal-couches-total" id="tcal-c-total"></div></div>',
          'Matière : épaisseur type, ou frontal + adhésif + glassine'))
      + panneau('fronts',
        '<div class="tcal-grille">' + champ('laize', 'Laize bobine (mm)', { placeholder: '440' }) + champ('larg', 'Largeur étiquette (mm)', { placeholder: '104,5' }) + '</div>'
        + res('fronts') + '<div class="tcal-detail" id="tcal-d-fronts"></div><div class="tcal-err" id="tcal-e-fronts"></div>'
        + '<div class="tcal-detail" id="tcal-d-fronts2"></div>',
        fins('fronts', '<div class="tcal-grille">' + champ('espl', 'Espace entre fronts (mm)', { placeholder: '0' }) + champ('rive', 'Rive par bord (mm)', { placeholder: '0' })
          + champ('nbv', 'Fronts voulus', { placeholder: '4', step: '1', min: '1', inputmode: 'numeric' }, 'Donne la laize minimale') + '</div>',
          'Espace entre fronts, rive, laize minimale'))
      + panneau('etiquettes',
        question('sens3', 'Ce que je cherche', [['qte', 'Le nombre d\'étiquettes', 'Je connais le métrage → j\'obtiens la quantité'],
          ['metres', 'Le métrage', 'Je connais la quantité → j\'obtiens les mètres']])
        + '<div class="tcal-grille">' + champ('haut', 'Hauteur étiquette (mm)', { placeholder: '148,4' }, 'Dans le sens de déroulement')
        + champ('nbf', 'Fronts', { placeholder: '1', step: '1', min: '1', inputmode: 'numeric' })
        + champ('l3m', 'Métrage (m)', { placeholder: '2000' })
        + champ('qte', 'Quantité visée', { placeholder: '10000', step: '1', inputmode: 'numeric' }, 'Étiquettes') + '</div>'
        + '<div class="tcal-liens" id="tcal-l-etiquettes"></div>'
        + res('etiquettes') + '<div class="tcal-detail" id="tcal-d-etiquettes"></div>',
        fins('etiquettes', '<div class="tcal-grille">' + champ('espa', 'Espace entre étiquettes (mm)', { placeholder: '0' }) + '</div>', 'Espace entre étiquettes'))
      + panneau('carton',
        '<div class="tcal-grille">' + champ('cd', 'Ø bobine (mm)', { placeholder: '200' }, 'Diamètre extérieur')
        + champ('cl', 'Largeur bobine (mm)', { placeholder: '110' }, 'Laize de la bobine')
        + champ('cq', 'Nombre de bobines', { placeholder: 'facultatif', step: '1', inputmode: 'numeric' }, 'Pour compter les cartons') + '</div>'
        + '<div data-si-quantite>' + seg('priorite', [['vide', 'Moins de vide', 'Le moins d\'air au total'], ['cartons', 'Moins de cartons', 'Le moins de colis']]) + '</div>'
        + '<div class="tcal-liens" id="tcal-l-carton"></div>'
        + '<div id="tcal-cartons"></div>',
        fins('carton', '<div class="tcal-grille">' + champ('jeu', 'Jeu (mm)', { placeholder: '4' }, 'Retiré de chaque dimension du carton')
          + '<div class="tcal-aide">Bobines toujours debout, base au sol, empilées par couches.</div></div>',
          'Jeu'));

    const m = lire(LS_MTR), c = lire(LS_CALC);
    $('tcal-ep').value = m.ep != null ? m.ep : '';
    $('tcal-dm').value = m.dm != null ? m.dm : '';
    $('tcal-db').value = m.db != null ? m.db : '';
    CHAMPS.forEach(k => { if (!['ep', 'dm', 'db'].includes(k) && c[k] != null && $('tcal-' + k)) $('tcal-' + k).value = c[k]; });
    C.sens = c.sens === 'diametre' ? 'diametre' : 'metrage';
    C.sens3 = c.sens3 === 'metres' ? 'metres' : 'qte';
    C.priorite = c.priorite === 'cartons' ? 'cartons' : 'vide';
    if (!C.ongletAdresse && ONGLETS.some(o => o[0] === c.onglet)) C.onglet = c.onglet;
    if (!C.adresseAttente) {
      C.typeMem = m.type || '';
      C.choix = (c.choix && typeof c.choix === 'object') ? c.choix : {};
      C.umCouche = (c.umCouche && typeof c.umCouche === 'object') ? c.umCouche : {};
    }

    h.addEventListener('click', e => {
      const o = e.target.closest('[data-onglet]');
      if (o) { C.onglet = o.getAttribute('data-onglet'); maj(); return; }
      const s = e.target.closest('[data-seg] [data-v]');
      if (s) { C[s.parentElement.getAttribute('data-seg')] = s.getAttribute('data-v'); maj(); return; }
      const r = e.target.closest('[data-reprendre]');
      if (r) { $(r.getAttribute('data-reprendre')).value = r.getAttribute('data-valeur'); maj(); return; }
      if (e.target.closest('[data-tous-cartons]')) { C.tousCartons = !C.tousCartons; maj(); }
    });
    h.addEventListener('change', e => {
      const t = e.target;
      if (t.id === 'tcal-type') {
        const ty = (C.epaisseurs || []).find(x => String(x.id) === t.value);
        if (ty) { $('tcal-ep').value = String(ty.microns); C.choix = {}; C.umCouche = {}; (C.couches || []).forEach(co => majLigne(co.categorie)); }
        C.typeMem = t.value;
        maj();
      } else if (t.hasAttribute('data-couche')) {
        const cat = t.getAttribute('data-couche');
        if (t.value) C.choix[cat] = t.value; else delete C.choix[cat];
        const mat = matiere(cat, t.value);
        C.umCouche[cat] = mat && mat.epaisseur_um ? String(mat.epaisseur_um) : '';
        if (t.value) { C.typeMem = ''; $('tcal-type').value = ''; }
        majLigne(cat);
        reporterEpaisseur();
        maj();
      }
    });
    h.addEventListener('input', e => {
      const t = e.target;
      if (t.hasAttribute('data-couche-um')) { C.umCouche[t.getAttribute('data-couche-um')] = t.value; reporterEpaisseur(); }
      maj();
    });
    h.querySelectorAll('details.tcal-fins').forEach(d => d.addEventListener('toggle', () => {
      const s = d.querySelector('summary'); if (s) s.setAttribute('data-bulle', d.open ? 'Replier' : 'Déplier');
    }));
    remplirTypes();
    rendreCouches();
    maj();
  }

  function remplirTypes() {
    const sel = $('tcal-type');
    if (!sel || !C.epaisseurs) return;
    sel.querySelectorAll('option:not([value=""])').forEach(o => o.remove());
    C.epaisseurs.forEach(t => {
      const o = document.createElement('option');
      o.value = String(t.id); o.textContent = t.libelle + ' — ' + fmt(t.microns, t.microns % 1 ? 1 : 0) + ' µm';
      sel.appendChild(o);
    });
    sel.value = C.typeMem && C.epaisseurs.some(t => String(t.id) === String(C.typeMem)) ? String(C.typeMem) : '';
  }

  // ── Couches : frontal + adhésif + glassine ─────────────────────────
  const matiere = (cat, id) => {
    const co = (C.couches || []).find(x => x.categorie === cat);
    return co && id ? co.matieres.find(mm => String(mm.id) === String(id)) || null : null;
  };
  function couchesChoisies() {
    return (C.couches || []).filter(co => C.choix[co.categorie] && matiere(co.categorie, C.choix[co.categorie]))
      .map(co => ({ categorie: co.categorie, libelle: co.libelle, matiere: matiere(co.categorie, C.choix[co.categorie]), microns: C.umCouche[co.categorie] }));
  }
  // Le total remplit Épaisseur, dès que toutes les couches choisies ont la leur.
  function reporterEpaisseur() {
    const t = epaisseurCouches(couchesChoisies());
    if (t && t.complet && t.total > 0) $('tcal-ep').value = String(Math.round(t.total * 100) / 100);
  }
  function rendreCouches() {
    const z = $('tcal-couches');
    if (!z) return;
    if (C.couches === null) return;
    if (!C.couches.length) { z.innerHTML = '<div class="tcal-aide">Aucune couche déclarée.</div>'; return; }
    const actif = document.activeElement, focusId = actif && actif.id, deb = actif && actif.selectionStart, fin = actif && actif.selectionEnd;
    z.innerHTML = '';
    C.couches.forEach(co => {
      const cat = co.categorie;
      const ligne = document.createElement('div');
      ligne.className = 'tcal-couche';
      const nom = document.createElement('span'); nom.className = 'tcal-couche-nom'; nom.textContent = co.libelle;
      const sel = document.createElement('select');
      sel.className = 'tcal-in'; sel.id = 'tcal-c-' + cat; sel.setAttribute('data-couche', cat); sel.setAttribute('aria-label', co.libelle);
      const o0 = document.createElement('option'); o0.value = ''; o0.textContent = co.matieres.length ? 'Aucun' : 'Aucune matière dans MyStock'; sel.appendChild(o0);
      co.matieres.forEach(mm => {
        const o = document.createElement('option'); o.value = String(mm.id);
        o.textContent = mm.libelle + (mm.epaisseur_um ? ' — ' + fmtL(mm.epaisseur_um) + ' µm' : ' — épaisseur inconnue');
        sel.appendChild(o);
      });
      const um = document.createElement('label'); um.className = 'tcal-couche-um';
      const inp = document.createElement('input');
      Object.assign(inp, { type: 'number', min: '0', step: 'any', className: 'tcal-in', id: 'tcal-cu-' + cat });
      inp.setAttribute('inputmode', 'decimal'); inp.setAttribute('data-couche-um', cat); inp.setAttribute('aria-label', 'Épaisseur ' + co.libelle + ' (µm)');
      const u = document.createElement('span'); u.textContent = 'µm';
      um.append(inp, u);
      const src = document.createElement('span'); src.className = 'tcal-couche-src'; src.id = 'tcal-cs-' + cat;
      ligne.append(nom, sel, um, src);
      z.appendChild(ligne);
      majLigne(cat);
    });
    if (focusId) { const el = $(focusId); if (el) { el.focus(); try { if (deb != null) el.setSelectionRange(deb, fin); } catch (e) {} } }
  }
  // Une ligne de couche mise à jour sur place (le select garde le focus).
  function majLigne(cat) {
    const sel = $('tcal-c-' + cat), inp = $('tcal-cu-' + cat), src = $('tcal-cs-' + cat);
    if (!sel || !inp || !src) return;
    const mat = matiere(cat, C.choix[cat]);
    sel.value = mat ? String(mat.id) : '';
    inp.value = mat ? (C.umCouche[cat] != null ? C.umCouche[cat] : '') : '';
    inp.disabled = !mat;
    inp.placeholder = mat ? 'à saisir' : '—';
    majSource(cat);
  }
  function majSource(cat) {
    const src = $('tcal-cs-' + cat), mat = matiere(cat, C.choix[cat]);
    if (!src) return;
    src.classList.remove('tcal-couche-src--manque');
    if (!mat) { src.textContent = ''; return; }
    if (mat.epaisseur_um) {
      src.textContent = n(C.umCouche[cat]) === mat.epaisseur_um ? 'Épaisseur : ' + mat.source : 'Modifiée (' + mat.source + ' : ' + fmtL(mat.epaisseur_um) + ' µm)';
    } else {
      const g = mat.grammage_gsm ? 'grammage ' + fmtL(mat.grammage_gsm) + ' g/m²' : '';
      if (n(C.umCouche[cat]) > 0) src.textContent = 'Épaisseur saisie — inconnue dans MyStock' + (g ? ' (' + g + ')' : '');
      else { src.textContent = 'Épaisseur inconnue' + (g ? ' (' + g + ')' : '') + ' — à saisir'; src.classList.add('tcal-couche-src--manque'); }
    }
  }
  function majCouches() {
    const z = $('tcal-c-total');
    if (!z) return;
    const ch = couchesChoisies(), t = epaisseurCouches(ch);
    (C.couches || []).forEach(co => majSource(co.categorie));
    if (!t) { z.textContent = ''; z.className = 'tcal-couches-total'; return; }
    const parts = ch.map(c => c.libelle + ' ' + (n(c.microns) > 0 ? fmtL(n(c.microns)) : '?'));
    const ep = n(val('tcal-ep'));
    let txt = parts.join(' + ') + ' = ' + fmtL(t.total) + ' µm';
    if (!t.complet) txt += ' — épaisseur à saisir : ' + t.manquantes.join(', ') + ' (aucune règle ne la déduit du grammage)';
    else if (ep > 0 && Math.abs(ep - t.total) > 0.005) txt += ' — Épaisseur modifiée à la main : ' + fmtL(ep) + ' µm retenus';
    else txt += ' → reporté dans Épaisseur';
    z.textContent = txt;
    z.className = 'tcal-couches-total' + (t.complet ? '' : ' tcal-couches-total--manque');
  }
  function resumeMetrage() {
    const ch = couchesChoisies(), t = epaisseurCouches(ch), ep = n(val('tcal-ep'));
    if (t) return ch.map(c => c.matiere.libelle).join(' · ') + ' = ' + fmtL(t.total) + ' µm' + (t.complet ? '' : ' (incomplet)');
    const ty = (C.epaisseurs || []).find(x => String(x.id) === String(val('tcal-type')));
    if (ty) return ty.libelle + ' — ' + fmtL(ty.microns) + ' µm';
    return ep > 0 ? 'Épaisseur saisie : ' + fmtL(ep) + ' µm' : 'Aucune matière choisie';
  }
  function resume(id, txt) { const z = $('tcal-fr-' + id); if (z) z.textContent = txt; }

  function resultat(id, valeur, libelle, vide) {
    const r = $('tcal-r-' + id);
    r.classList.toggle('tcal-res--vide', !!vide);
    r.querySelector('.tcal-res-v').textContent = valeur;
    r.querySelector('.tcal-res-l').textContent = libelle;
  }
  const lien = (cible, valeur, texte) => '<button type="button" class="tcal-lien" data-reprendre="' + cible + '" data-valeur="' + valeur + '" data-bulle="Copier">' + esc(texte) + '</button>';
  const montrer = (id, oui) => { const e = $(id); if (e) e.closest('.tcal-champ').hidden = !oui; };
  function dessiner(id, r) {
    const z = $('tcal-s-' + id);
    if (!z || !r) return;
    if (z._svg !== r.svg) { z.innerHTML = r.svg; z._svg = r.svg; }
    z.classList.toggle('tcal-schema--exemple', !!r.exemple);
    $('tcal-sx-' + id).hidden = !r.exemple;
    const l = $('tcal-sl-' + id);
    if (l._html !== r.legende) { l.innerHTML = r.legende; l._html = r.legende; }
  }

  function maj() {
    if (!C.host) return;
    const c = { sens: C.sens, sens3: C.sens3, priorite: C.priorite, onglet: C.onglet,
      choix: C.choix, umCouche: C.umCouche };
    CHAMPS.forEach(k => { if (!['ep', 'dm', 'db'].includes(k)) c[k] = val('tcal-' + k); });
    ecrire(LS_CALC, c);
    ecrire(LS_MTR, Object.assign(lire(LS_MTR), { type: $('tcal-type').value, ep: val('tcal-ep'), dm: val('tcal-dm'), db: val('tcal-db') }));

    C.host.querySelectorAll('[data-onglet]').forEach(b => { const on = b.getAttribute('data-onglet') === C.onglet; b.classList.toggle('actif', on); b.setAttribute('aria-selected', on ? 'true' : 'false'); });
    C.host.querySelectorAll('[data-panneau]').forEach(p => { p.hidden = p.getAttribute('data-panneau') !== C.onglet; });
    C.host.querySelectorAll('[data-seg]').forEach(g => g.querySelectorAll('[data-v]').forEach(b => {
      const on = b.getAttribute('data-v') === C[g.getAttribute('data-seg')];
      b.classList.toggle('active', on); if (b.getAttribute('role') === 'radio') b.setAttribute('aria-checked', on ? 'true' : 'false');
    }));
    const S = SCH();

    // Métrage ↔ diamètre
    montrer('tcal-db', C.sens === 'metrage'); montrer('tcal-lm', C.sens === 'diametre');
    let metres = null, diam = null;
    $('tcal-e-metrage').textContent = '';
    if (C.sens === 'metrage') {
      const r = metrage(val('tcal-ep'), val('tcal-dm'), val('tcal-db'));
      if (r.erreur) $('tcal-e-metrage').textContent = r.erreur;
      if (r.metres != null) { metres = r.metres; diam = n(val('tcal-db')); resultat('metrage', '≈ ' + fmt(r.metres) + ' m', 'métrage enroulé (estimation)'); }
      else resultat('metrage', '—', 'Épaisseur et diamètres à renseigner', true);
    } else {
      const r = diametre(val('tcal-ep'), val('tcal-dm'), val('tcal-lm'));
      if (r.mm != null) { metres = n(val('tcal-lm')); diam = r.mm; resultat('metrage', '≈ Ø ' + fmt(r.mm) + ' mm', 'diamètre extérieur de la bobine'); }
      else resultat('metrage', '—', 'Épaisseur, mandrin et métrage à renseigner', true);
    }
    majCouches();
    resume('metrage', resumeMetrage());
    if (S && C.onglet === 'metrage') dessiner('metrage', S.metrage({ dm: val('tcal-dm'), db: diam, ep: val('tcal-ep'), metres }));

    // Fronts
    const f = fronts(val('tcal-laize'), val('tcal-larg'), val('tcal-espl'), val('tcal-rive'));
    $('tcal-e-fronts').textContent = f.erreur || '';
    if (f.nb) {
      resultat('fronts', f.nb + ' front' + (f.nb > 1 ? 's' : ''), 'chute ' + fmt(f.chute, 1) + ' mm (' + fmt(f.chutePct, 1) + ' %)');
      $('tcal-d-fronts').textContent = 'Laize utilisée ' + fmt(f.utilisee, 2) + ' mm · module ' + fmt(f.module, 2) + ' mm';
    } else { resultat('fronts', '—', 'Laize et largeur d\'étiquette à renseigner', true); $('tcal-d-fronts').textContent = ''; }
    const lmin = laizeMini(val('tcal-nbv'), val('tcal-larg'), val('tcal-espl'), val('tcal-rive'));
    $('tcal-d-fronts2').textContent = lmin != null ? 'Laize minimale pour ' + Math.floor(n(val('tcal-nbv'))) + ' fronts : ' + fmt(lmin, 2) + ' mm' : '';
    const rf = [];
    if (n(val('tcal-espl')) > 0) rf.push('espace ' + fmtL(n(val('tcal-espl'))) + ' mm');
    if (n(val('tcal-rive')) > 0) rf.push('rive ' + fmtL(n(val('tcal-rive'))) + ' mm');
    if (n(val('tcal-nbv')) >= 1) rf.push(Math.floor(n(val('tcal-nbv'))) + ' fronts voulus');
    resume('fronts', rf.length ? rf.join(' · ') : 'Espace et rive à 0');
    if (S && C.onglet === 'fronts') dessiner('fronts', S.fronts({ laize: val('tcal-laize'), larg: val('tcal-larg'), espl: val('tcal-espl'), rive: val('tcal-rive'), nb: f.nb || 0, haut: val('tcal-haut'), espa: val('tcal-espa') }));

    // Étiquettes / bobine
    montrer('tcal-l3m', C.sens3 === 'qte'); montrer('tcal-qte', C.sens3 === 'metres');
    const nbf = Math.floor(n(val('tcal-nbf'))) || 1;
    const liens = [];
    if (C.sens3 === 'qte' && metres != null && Math.round(metres) !== Math.round(n(val('tcal-l3m')))) liens.push(lien('tcal-l3m', String(Math.round(metres)), 'Métrage : ' + fmt(metres) + ' m'));
    if (f.nb && f.nb !== Math.floor(n(val('tcal-nbf')))) liens.push(lien('tcal-nbf', String(f.nb), 'Fronts : ' + f.nb));
    $('tcal-l-etiquettes').innerHTML = liens.join('');
    let schEt = { total: null, metres: null };
    if (C.sens3 === 'qte') {
      const e = etiquettes(val('tcal-l3m'), val('tcal-haut'), val('tcal-espa'), nbf);
      if (e.total != null) {
        schEt = { total: e.total, metres: n(val('tcal-l3m')) };
        resultat('etiquettes', fmt(e.total) + ' étiquettes', 'sur ' + fmt(n(val('tcal-l3m'))) + ' m');
        $('tcal-d-etiquettes').textContent = nbf > 1 ? fmt(e.parFront) + ' par front × ' + nbf : '';
      } else { resultat('etiquettes', '—', 'Hauteur d\'étiquette et métrage à renseigner', true); $('tcal-d-etiquettes').textContent = ''; }
    } else {
      const b = metragePour(val('tcal-qte'), val('tcal-haut'), val('tcal-espa'), nbf);
      if (b != null) {
        schEt = { total: Math.floor(n(val('tcal-qte'))), metres: b };
        resultat('etiquettes', fmt(b, b < 100 ? 1 : 0) + ' m', 'pour ' + fmt(n(val('tcal-qte'))) + ' étiquettes');
        const d = diametre(val('tcal-ep'), val('tcal-dm'), b);
        $('tcal-d-etiquettes').textContent = d.mm != null ? 'Ø bobine ≈ ' + fmt(d.mm) + ' mm' : '';
      } else { resultat('etiquettes', '—', 'Hauteur d\'étiquette et quantité à renseigner', true); $('tcal-d-etiquettes').textContent = ''; }
    }
    resume('etiquettes', n(val('tcal-espa')) > 0 ? 'Espace ' + fmtL(n(val('tcal-espa'))) + ' mm' : 'Espace à 0');
    if (S && C.onglet === 'etiquettes') dessiner('etiquettes', S.etiquettes(Object.assign({ haut: val('tcal-haut'), espa: val('tcal-espa'), nbf: val('tcal-nbf'), larg: val('tcal-larg'), espl: val('tcal-espl') }, schEt)));

    // Carton
    const lc = [];
    if (diam != null && Math.round(diam) !== Math.round(n(val('tcal-cd')))) lc.push(lien('tcal-cd', String(Math.round(diam)), 'Ø : ' + fmt(diam) + ' mm'));
    if (f.nb && Math.abs(f.module - n(val('tcal-cl'))) > 0.05) lc.push(lien('tcal-cl', String(Math.round(f.module * 10) / 10), 'Largeur : ' + fmt(f.module, 1) + ' mm'));
    $('tcal-l-carton').innerHTML = lc.join('');
    resume('carton', 'Jeu ' + fmtL(val('tcal-jeu') === '' ? 4 : n0(val('tcal-jeu'))) + ' mm · bobines debout');
    rendreCartons();
    signaler();
  }

  function rendreCartons() {
    const z = $('tcal-cartons');
    if (C.onglet !== 'carton') return;
    const S = SCH(), vide = () => S && dessiner('carton', S.carton({}));
    if (C.cartons === null) { z.innerHTML = '<div class="tcal-res tcal-res--vide"><div class="tcal-res-l">Chargement des références carton…</div></div>'; vide(); return; }
    const D = n(val('tcal-cd')), L = n(val('tcal-cl'));
    // Toujours debout : une bobine se pose sur sa base, jamais sur sa tranche.
    const sens = { debout: true, couche: false };
    if (!(D > 0) || !(L > 0)) { z.innerHTML = '<div class="tcal-res tcal-res--vide"><div class="tcal-res-v">—</div><div class="tcal-res-l">Diamètre et largeur de bobine à renseigner — ' + C.cartons.length + ' références carton</div></div>'; vide(); return; }
    const jeu = val('tcal-jeu') === '' ? 4 : val('tcal-jeu');
    const Q = Math.floor(n(val('tcal-cq'))) || 0;
    C.host.querySelector('[data-si-quantite]').hidden = !Q;
    const lignes = classerCartons(C.cartons, D, L, Q, jeu, sens, C.priorite);
    if (!lignes.length) { z.innerHTML = '<div class="tcal-err">Aucune de nos ' + C.cartons.length + ' références ne contient une bobine de Ø ' + fmt(D) + ' × ' + fmt(L) + ' mm.</div>'; vide(); return; }
    const m = lignes[0], c = m.carton;
    let h = '<div class="tcal-res"><div class="tcal-res-v">' + esc(c.libelle) + '</div><div class="tcal-res-l">'
      + m.parCarton + ' bobine' + (m.parCarton > 1 ? 's' : '') + ' par carton · ' + m.rang.a + ' × ' + m.rang.b + ' × ' + m.rang.c + ' ' + m.rang.sens
      + (Q ? ' · ' + m.nbCartons + ' carton' + (m.nbCartons > 1 ? 's' : '') + ' pour ' + fmt(Q) + ' bobines' + (m.nbCartons > 1 && m.dernier < m.parCarton ? ' (dernier : ' + m.dernier + ')' : '') : '')
      + ' · remplissage ' + fmt((Q ? m.remplissageTotal : m.remplissage) * 100) + ' %</div></div>';
    const autres = lignes.slice(1, C.tousCartons ? lignes.length : 5);
    if (autres.length) {
      h += '<div class="tcal-titre">Autres possibilités</div><div class="tcal-cartons">' + autres.map(x =>
        '<div class="tcal-carton"><span class="tcal-carton-nom">' + esc(x.carton.libelle) + '</span>'
        + '<span class="tcal-carton-chiffres">' + x.parCarton + ' / carton' + (Q ? ' · ' + x.nbCartons + ' carton' + (x.nbCartons > 1 ? 's' : '') : '') + '</span>'
        + '<span class="tcal-jauge" data-bulle="Remplissage ' + fmt((Q ? x.remplissageTotal : x.remplissage) * 100) + ' %"><i style="width:' + Math.round((Q ? x.remplissageTotal : x.remplissage) * 100) + '%"></i></span></div>').join('') + '</div>';
      if (lignes.length > 5) h += '<button type="button" class="tcal-lien" data-tous-cartons data-bulle="' + (C.tousCartons ? 'Réduire' : 'Tout') + '">' + (C.tousCartons ? 'Moins de cartons' : 'Les ' + lignes.length + ' cartons possibles') + '</button>';
    }
    h += '<p class="tcal-aide">Rangement en grille, jeu de ' + fmt(n0(jeu)) + ' mm retiré de chaque dimension. Dimensions lues dans les désignations MyStock (' + C.cartons.length + ' références' + (C.ecartes.length ? ', ' + C.ecartes.length + ' écartées' : '') + ').</p>';
    z.innerHTML = h;
    if (S) dessiner('carton', S.carton({ meilleur: m, D, L, jeu, dm: n(val('tcal-dm')) }));
  }

  // Choix de l'adresse en attente des matières : appliqués à leur arrivée.
  function appliquerAdresse() {
    const a = C.adresseAttente;
    if (!a || C.couches === null || C.epaisseurs === null) return;
    C.adresseAttente = null;
    if (a.couches !== undefined) {
      // Même matière qu'avant : l'épaisseur saisie pour la couche est gardée.
      const avant = C.choix, umAvant = C.umCouche;
      C.choix = {}; C.umCouche = {};
      Object.keys(a.couches || {}).forEach(cat => {
        const mat = matiere(cat, a.couches[cat]);
        if (!mat) return;
        C.choix[cat] = String(mat.id);
        const garde = String(avant[cat] || '') === String(mat.id) && n(umAvant[cat]) > 0;
        C.umCouche[cat] = garde ? String(umAvant[cat]) : (mat.epaisseur_um ? String(mat.epaisseur_um) : '');
      });
    }
    if (a.type !== undefined) C.typeMem = a.type && (C.epaisseurs || []).some(t => String(t.id) === String(a.type)) ? String(a.type) : '';
    if (Object.keys(C.choix).length) { C.typeMem = ''; reporterEpaisseur(); }
    else if (C.typeMem) { const ty = C.epaisseurs.find(t => String(t.id) === String(C.typeMem)); if (ty) $('tcal-ep').value = String(ty.microns); }
    remplirTypes();
    rendreCouches();
  }

  async function charger() {
    const lireJson = async (url, defaut) => {
      try { const r = await fetch(url, { credentials: 'include', cache: 'no-store' }); return r.ok ? await r.json() : defaut; } catch (e) { return defaut; }
    };
    const [ep, co, ca] = await Promise.all([
      lireJson('/api/stock/metrage-epaisseurs', []),
      lireJson('/api/tools/couches', { couches: [] }),
      lireJson('/api/tools/cartons', { cartons: [], ecartes: [] }),
    ]);
    C.epaisseurs = Array.isArray(ep) ? ep : [];
    C.couches = (co && Array.isArray(co.couches)) ? co.couches : [];
    // Une matière disparue de MyStock ne reste pas choisie.
    Object.keys(C.choix).forEach(cat => { if (!matiere(cat, C.choix[cat])) { delete C.choix[cat]; delete C.umCouche[cat]; } });
    C.cartons = (ca && ca.cartons) || []; C.ecartes = (ca && ca.ecartes) || [];
    remplirTypes();
    rendreCouches();
    appliquerAdresse();
    maj();
  }

  function mount(root, ctx) {
    if (ctx) CTX = Object.assign(CTX, ctx);
    if (!root) return;
    if (!C.host) { C.host = document.createElement('div'); root.appendChild(C.host); construire(); charger(); return; }
    root.appendChild(C.host);
  }

  window.MyToolsCalculs = {
    mount,
    adresse: {
      // Ce que l'adresse porte : le calcul, et la matière du métrage (couches
      // choisies, ou épaisseur type). Les valeurs saisies restent des saisies.
      etat: () => {
        const a = C.adresseAttente;
        const couches = a && a.couches !== undefined ? Object.assign({}, a.couches || {}) : Object.assign({}, C.choix);
        const type = a && a.type !== undefined ? a.type || '' : (Object.keys(C.choix).length ? '' : (C.host ? val('tcal-type') : C.typeMem || ''));
        return { calcul: C.onglet, couches, type };
      },
      // a.couches / a.type : undefined = ne pas toucher, null ou {} = aucun.
      aller: a => {
        a = a || {};
        if (a.calcul !== undefined) {
          C.onglet = ONGLETS.some(x => x[0] === a.calcul) ? a.calcul : 'metrage';
          C.ongletAdresse = true;
        }
        if (a.couches !== undefined || a.type !== undefined) {
          C.adresseAttente = Object.assign(C.adresseAttente || {}, a.couches !== undefined ? { couches: a.couches || {} } : {}, a.type !== undefined ? { type: a.type || '' } : {});
          if (C.host) appliquerAdresse();
        }
        if (C.host) maj();
      },
    },
    _interne: { metrage, diametre, fronts, laizeMini, etiquettes, metragePour, rangement, classerCartons, epaisseurCouches },
  };
})();

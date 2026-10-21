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
 *   carton       bobines rangées en grille, debout (axe vertical) ou couchées
 *                (axe le long d'un côté) ; dimensions du carton diminuées du jeu.
 *
 * La saisie du métrage est partagée avec le widget de MyStock (clé
 * `mysifa_mtr_saisie_v1`). Rien n'est enregistré côté serveur.
 *
 *   MyToolsCalculs.mount(root, ctx)
 *   MyToolsCalculs.adresse = { etat() → {calcul}, aller({calcul}) }
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

  // Rangement de bobines (Ø D, largeur L) dans un carton (l × w × h, intérieur),
  // en grille. `sens` : { debout, couche }.
  function rangement(D, L, carton, jeu, sens) {
    const j = n0(jeu), l = carton.l - j, w = carton.w - j, h = carton.h - j;
    if (!(D > 0) || !(L > 0) || l <= 0 || w <= 0 || h <= 0) return null;
    const essais = [];
    if (sens.debout) essais.push({ sens: 'debout', a: Math.floor(l / D), b: Math.floor(w / D), c: Math.floor(h / L) });
    if (sens.couche) {
      essais.push({ sens: 'couchées', a: Math.floor(l / L), b: Math.floor(w / D), c: Math.floor(h / D) });
      essais.push({ sens: 'couchées', a: Math.floor(l / D), b: Math.floor(w / L), c: Math.floor(h / D) });
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
  const C = { host: null, onglet: 'metrage', epaisseurs: null, cartons: null, ecartes: [], tousCartons: false };
  const fmt = (x, dec) => Number(x).toLocaleString('fr-FR', { minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0 });
  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  function lire(cle) { try { return JSON.parse(localStorage.getItem(cle) || '{}') || {}; } catch (e) { return {}; } }
  function ecrire(cle, v) { try { localStorage.setItem(cle, JSON.stringify(v)); } catch (e) {} }
  function signaler() { if (typeof CTX.surChange === 'function') { try { CTX.surChange(); } catch (e) {} } }
  const $ = id => C.host.querySelector('#' + id);
  const val = id => ($(id) ? $(id).value : '');

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
  // Ouverts par défaut (retour d'Eugène du 21/10) : on peut toujours les replier.
  const fins = (contenu, bulle) => '<details class="tcal-fins" open><summary data-bulle="' + esc(bulle || 'Valeurs par défaut sinon') + '">Réglages fins</summary><div class="tcal-grille">' + contenu + '</div></details>';

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
      + '<section class="tcal-carte" data-panneau="metrage">' + tete('metrage')
      + question('sens', 'Ce que je cherche', [['metrage', 'Le métrage', 'Je mesure le Ø de la bobine → j\'obtiens les mètres'],
        ['diametre', 'Le diamètre', 'Je connais les mètres → j\'obtiens le Ø de la bobine']])
      + '<div class="tcal-grille">' + champ('ep', 'Épaisseur (µm)', { placeholder: '145' }, 'Matière + adhésif + glassine')
      + champ('dm', 'Ø mandrin (mm)', { placeholder: '76' }, 'Diamètre extérieur')
      + champ('db', 'Ø bobine (mm)', { placeholder: '1000' }, 'Diamètre extérieur')
      + champ('lm', 'Métrage (m)', { placeholder: '2000' }) + '</div>'
      + res('metrage')
      + '<div class="tcal-err" id="tcal-e-metrage"></div>'
      + fins('<label class="tcal-champ" for="tcal-type"><span>Matière</span><select id="tcal-type" class="tcal-in"><option value="">Saisie libre</option></select></label>',
        'Épaisseurs types de MyStock')
      + '</section>'
      + '<section class="tcal-carte" data-panneau="fronts" hidden>' + tete('fronts')
      + '<div class="tcal-grille">' + champ('laize', 'Laize bobine (mm)', { placeholder: '440' }) + champ('larg', 'Largeur étiquette (mm)', { placeholder: '104,5' }) + '</div>'
      + res('fronts') + '<div class="tcal-detail" id="tcal-d-fronts"></div><div class="tcal-err" id="tcal-e-fronts"></div>'
      + fins(champ('espl', 'Espace entre fronts (mm)', { placeholder: '0' }) + champ('rive', 'Rive par bord (mm)', { placeholder: '0' })
        + champ('nbv', 'Fronts voulus', { placeholder: '4', step: '1', min: '1', inputmode: 'numeric' }, 'Donne la laize minimale'))
      + '<div class="tcal-detail" id="tcal-d-fronts2"></div>'
      + '</section>'
      + '<section class="tcal-carte" data-panneau="etiquettes" hidden>' + tete('etiquettes')
      + question('sens3', 'Ce que je cherche', [['qte', 'Le nombre d\'étiquettes', 'Je connais le métrage → j\'obtiens la quantité'],
        ['metres', 'Le métrage', 'Je connais la quantité → j\'obtiens les mètres']])
      + '<div class="tcal-grille">' + champ('haut', 'Hauteur étiquette (mm)', { placeholder: '148,4' }, 'Dans le sens de déroulement')
      + champ('nbf', 'Fronts', { placeholder: '1', step: '1', min: '1', inputmode: 'numeric' })
      + champ('l3m', 'Métrage (m)', { placeholder: '2000' })
      + champ('qte', 'Quantité visée', { placeholder: '10000', step: '1', inputmode: 'numeric' }, 'Étiquettes') + '</div>'
      + '<div class="tcal-liens" id="tcal-l-etiquettes"></div>'
      + res('etiquettes') + '<div class="tcal-detail" id="tcal-d-etiquettes"></div>'
      + fins(champ('espa', 'Espace entre étiquettes (mm)', { placeholder: '0' }))
      + '</section>'
      + '<section class="tcal-carte" data-panneau="carton" hidden>' + tete('carton')
      + '<div class="tcal-grille">' + champ('cd', 'Ø bobine (mm)', { placeholder: '200' }, 'Diamètre extérieur')
      + champ('cl', 'Largeur bobine (mm)', { placeholder: '110' }, 'Laize de la bobine')
      + champ('cq', 'Nombre de bobines', { placeholder: 'facultatif', step: '1', inputmode: 'numeric' }, 'Pour compter les cartons') + '</div>'
      + '<div data-si-quantite>' + seg('priorite', [['vide', 'Moins de vide', 'Le moins d\'air au total'], ['cartons', 'Moins de cartons', 'Le moins de colis']]) + '</div>'
      + '<div class="tcal-liens" id="tcal-l-carton"></div>'
      + '<div id="tcal-cartons"></div>'
      + fins(champ('jeu', 'Jeu (mm)', { placeholder: '4' }, 'Retiré de chaque dimension du carton')
        + '<label class="tcal-case" data-bulle="Axe vertical"><input type="checkbox" id="tcal-debout"> Bobines debout</label>'
        + '<label class="tcal-case" data-bulle="Axe horizontal"><input type="checkbox" id="tcal-couche"> Bobines couchées</label>',
        'Jeu et sens de rangement')
      + '</section>';

    const m = lire(LS_MTR), c = lire(LS_CALC);
    $('tcal-ep').value = m.ep != null ? m.ep : '';
    $('tcal-dm').value = m.dm != null ? m.dm : '';
    $('tcal-db').value = m.db != null ? m.db : '';
    CHAMPS.forEach(k => { if (!['ep', 'dm', 'db'].includes(k) && c[k] != null && $('tcal-' + k)) $('tcal-' + k).value = c[k]; });
    C.sens = c.sens === 'diametre' ? 'diametre' : 'metrage';
    C.sens3 = c.sens3 === 'metres' ? 'metres' : 'qte';
    C.priorite = c.priorite === 'cartons' ? 'cartons' : 'vide';
    $('tcal-debout').checked = c.debout !== false;
    $('tcal-couche').checked = c.couche !== false;
    if (!C.ongletAdresse && ONGLETS.some(o => o[0] === c.onglet)) C.onglet = c.onglet;
    C.typeMem = m.type || '';

    h.addEventListener('click', e => {
      const o = e.target.closest('[data-onglet]');
      if (o) { C.onglet = o.getAttribute('data-onglet'); maj(); return; }
      const s = e.target.closest('[data-seg] [data-v]');
      if (s) { C[s.parentElement.getAttribute('data-seg')] = s.getAttribute('data-v'); maj(); return; }
      const r = e.target.closest('[data-reprendre]');
      if (r) { $(r.getAttribute('data-reprendre')).value = r.getAttribute('data-valeur'); maj(); return; }
      if (e.target.closest('[data-tous-cartons]')) { C.tousCartons = !C.tousCartons; maj(); }
    });
    $('tcal-type').addEventListener('change', () => {
      const t = (C.epaisseurs || []).find(x => String(x.id) === $('tcal-type').value);
      if (t) $('tcal-ep').value = String(t.microns);
      maj();
    });
    h.addEventListener('input', maj);
    remplirTypes();
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
    if (C.typeMem && C.epaisseurs.some(t => String(t.id) === String(C.typeMem))) sel.value = String(C.typeMem);
  }

  function resultat(id, valeur, libelle, vide) {
    const r = $('tcal-r-' + id);
    r.classList.toggle('tcal-res--vide', !!vide);
    r.querySelector('.tcal-res-v').textContent = valeur;
    r.querySelector('.tcal-res-l').textContent = libelle;
  }
  const lien = (cible, valeur, texte) => '<button type="button" class="tcal-lien" data-reprendre="' + cible + '" data-valeur="' + valeur + '" data-bulle="Copier ici">' + esc(texte) + '</button>';
  const montrer = (id, oui) => { const e = $(id); if (e) e.closest('.tcal-champ').hidden = !oui; };

  function maj() {
    if (!C.host) return;
    const c = { sens: C.sens, sens3: C.sens3, priorite: C.priorite, onglet: C.onglet, debout: $('tcal-debout').checked, couche: $('tcal-couche').checked };
    CHAMPS.forEach(k => { if (!['ep', 'dm', 'db'].includes(k)) c[k] = val('tcal-' + k); });
    ecrire(LS_CALC, c);
    ecrire(LS_MTR, Object.assign(lire(LS_MTR), { type: $('tcal-type').value, ep: val('tcal-ep'), dm: val('tcal-dm'), db: val('tcal-db') }));

    C.host.querySelectorAll('[data-onglet]').forEach(b => { const on = b.getAttribute('data-onglet') === C.onglet; b.classList.toggle('actif', on); b.setAttribute('aria-selected', on ? 'true' : 'false'); });
    C.host.querySelectorAll('[data-panneau]').forEach(p => { p.hidden = p.getAttribute('data-panneau') !== C.onglet; });
    C.host.querySelectorAll('[data-seg]').forEach(g => g.querySelectorAll('[data-v]').forEach(b => {
      const on = b.getAttribute('data-v') === C[g.getAttribute('data-seg')];
      b.classList.toggle('active', on); if (b.getAttribute('role') === 'radio') b.setAttribute('aria-checked', on ? 'true' : 'false');
    }));

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

    // Fronts
    const f = fronts(val('tcal-laize'), val('tcal-larg'), val('tcal-espl'), val('tcal-rive'));
    $('tcal-e-fronts').textContent = f.erreur || '';
    if (f.nb) {
      resultat('fronts', f.nb + ' front' + (f.nb > 1 ? 's' : ''), 'chute ' + fmt(f.chute, 1) + ' mm (' + fmt(f.chutePct, 1) + ' %)');
      $('tcal-d-fronts').textContent = 'Laize utilisée ' + fmt(f.utilisee, 2) + ' mm · module ' + fmt(f.module, 2) + ' mm';
    } else { resultat('fronts', '—', 'Laize et largeur d\'étiquette à renseigner', true); $('tcal-d-fronts').textContent = ''; }
    const lmin = laizeMini(val('tcal-nbv'), val('tcal-larg'), val('tcal-espl'), val('tcal-rive'));
    $('tcal-d-fronts2').textContent = lmin != null ? 'Laize minimale pour ' + Math.floor(n(val('tcal-nbv'))) + ' fronts : ' + fmt(lmin, 2) + ' mm' : '';

    // Étiquettes / bobine
    montrer('tcal-l3m', C.sens3 === 'qte'); montrer('tcal-qte', C.sens3 === 'metres');
    const nbf = Math.floor(n(val('tcal-nbf'))) || 1;
    const liens = [];
    if (C.sens3 === 'qte' && metres != null && Math.round(metres) !== Math.round(n(val('tcal-l3m')))) liens.push(lien('tcal-l3m', String(Math.round(metres)), 'Métrage : ' + fmt(metres) + ' m'));
    if (f.nb && f.nb !== Math.floor(n(val('tcal-nbf')))) liens.push(lien('tcal-nbf', String(f.nb), 'Fronts : ' + f.nb));
    $('tcal-l-etiquettes').innerHTML = liens.join('');
    if (C.sens3 === 'qte') {
      const e = etiquettes(val('tcal-l3m'), val('tcal-haut'), val('tcal-espa'), nbf);
      if (e.total != null) {
        resultat('etiquettes', fmt(e.total) + ' étiquettes', 'sur ' + fmt(n(val('tcal-l3m'))) + ' m');
        $('tcal-d-etiquettes').textContent = nbf > 1 ? fmt(e.parFront) + ' par front × ' + nbf : '';
      } else { resultat('etiquettes', '—', 'Hauteur d\'étiquette et métrage à renseigner', true); $('tcal-d-etiquettes').textContent = ''; }
    } else {
      const b = metragePour(val('tcal-qte'), val('tcal-haut'), val('tcal-espa'), nbf);
      if (b != null) {
        resultat('etiquettes', fmt(b, b < 100 ? 1 : 0) + ' m', 'pour ' + fmt(n(val('tcal-qte'))) + ' étiquettes');
        const d = diametre(val('tcal-ep'), val('tcal-dm'), b);
        $('tcal-d-etiquettes').textContent = d.mm != null ? 'Ø bobine ≈ ' + fmt(d.mm) + ' mm' : '';
      } else { resultat('etiquettes', '—', 'Hauteur d\'étiquette et quantité à renseigner', true); $('tcal-d-etiquettes').textContent = ''; }
    }

    // Carton
    const lc = [];
    if (diam != null && Math.round(diam) !== Math.round(n(val('tcal-cd')))) lc.push(lien('tcal-cd', String(Math.round(diam)), 'Ø : ' + fmt(diam) + ' mm'));
    if (f.nb && Math.abs(f.module - n(val('tcal-cl'))) > 0.05) lc.push(lien('tcal-cl', String(Math.round(f.module * 10) / 10), 'Largeur : ' + fmt(f.module, 1) + ' mm'));
    $('tcal-l-carton').innerHTML = lc.join('');
    rendreCartons();
    signaler();
  }

  function rendreCartons() {
    const z = $('tcal-cartons');
    if (C.onglet !== 'carton') return;
    if (C.cartons === null) { z.innerHTML = '<div class="tcal-res tcal-res--vide"><div class="tcal-res-l">Chargement des références carton…</div></div>'; return; }
    const D = n(val('tcal-cd')), L = n(val('tcal-cl'));
    const sens = { debout: $('tcal-debout').checked, couche: $('tcal-couche').checked };
    if (!(D > 0) || !(L > 0)) { z.innerHTML = '<div class="tcal-res tcal-res--vide"><div class="tcal-res-v">—</div><div class="tcal-res-l">Diamètre et largeur de bobine à renseigner — ' + C.cartons.length + ' références carton</div></div>'; return; }
    if (!sens.debout && !sens.couche) { z.innerHTML = '<div class="tcal-err">Cocher au moins un sens de rangement (Réglages fins).</div>'; return; }
    const jeu = val('tcal-jeu') === '' ? 4 : val('tcal-jeu');
    const Q = Math.floor(n(val('tcal-cq'))) || 0;
    C.host.querySelector('[data-si-quantite]').hidden = !Q;
    const lignes = classerCartons(C.cartons, D, L, Q, jeu, sens, C.priorite);
    if (!lignes.length) { z.innerHTML = '<div class="tcal-err">Aucune de nos ' + C.cartons.length + ' références ne contient une bobine de Ø ' + fmt(D) + ' × ' + fmt(L) + ' mm.</div>'; return; }
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
      if (lignes.length > 5) h += '<button type="button" class="tcal-lien" data-tous-cartons>' + (C.tousCartons ? 'Moins de cartons' : 'Les ' + lignes.length + ' cartons possibles') + '</button>';
    }
    h += '<p class="tcal-aide">Rangement en grille, jeu de ' + fmt(n0(jeu)) + ' mm retiré de chaque dimension. Dimensions lues dans les désignations MyStock (' + C.cartons.length + ' références' + (C.ecartes.length ? ', ' + C.ecartes.length + ' écartées' : '') + ').</p>';
    z.innerHTML = h;
  }

  async function charger() {
    try {
      const r = await fetch('/api/stock/metrage-epaisseurs', { credentials: 'include', cache: 'no-store' });
      C.epaisseurs = r.ok ? await r.json() : [];
      if (!Array.isArray(C.epaisseurs)) C.epaisseurs = [];
    } catch (e) { C.epaisseurs = []; }
    remplirTypes();
    try {
      const r = await fetch('/api/tools/cartons', { credentials: 'include', cache: 'no-store' });
      const d = r.ok ? await r.json() : { cartons: [], ecartes: [] };
      C.cartons = d.cartons || []; C.ecartes = d.ecartes || [];
    } catch (e) { C.cartons = []; }
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
      etat: () => ({ calcul: C.onglet }),
      aller: a => {
        const o = a && ONGLETS.some(x => x[0] === a.calcul) ? a.calcul : 'metrage';
        C.onglet = o; C.ongletAdresse = true;
        if (C.host) maj();
      },
    },
    _interne: { metrage, diametre, fronts, laizeMini, etiquettes, metragePour, rangement, classerCartons },
  };
})();

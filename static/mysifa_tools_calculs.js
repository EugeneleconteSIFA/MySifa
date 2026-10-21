/* MyTools › Calculs bobine — trois calculs d'atelier reliés entre eux.
 *
 *   1. Métrage ↔ diamètre   longueur enroulée d'après l'épaisseur et les
 *                           diamètres, ou diamètre atteint pour un métrage.
 *   2. Fronts sur la laize   combien d'étiquettes de front, laize utilisée, chute.
 *   3. Étiquettes / bobine   étiquettes sur un métrage, ou métrage et diamètre
 *                           pour une quantité visée.
 *
 * Formules (mêmes conventions que le reste de MySifa) :
 *   métrage (m)  = π × ((Øbobine/2)² − (Ømandrin/2)²) ÷ épaisseur
 *                  diamètres en mm, épaisseur en µm (mm² ÷ µm = m) — celle du
 *                  widget « Métrage bobine » de MyStock et du classeur atelier ;
 *   Øbobine (mm) = 2 × √((Ømandrin/2)² + métrage × épaisseur ÷ π)   (l'inverse) ;
 *   module       = étiquette + espace, dans chaque sens ;
 *   fronts       = ⌊(laize − 2 × rive) ÷ module en laize⌋
 *                  (« nb_fronts ≈ laize_bobine ÷ laize_module », of-fiches-techniques) ;
 *   métrage      = quantité ÷ fronts × module en avance ÷ 1000.
 *
 * Les épaisseurs types viennent de /api/stock/metrage-epaisseurs (gérées dans
 * MyStock). La saisie du métrage est partagée avec le widget de MyStock
 * (clé localStorage `mysifa_mtr_saisie_v1`). Rien n'est enregistré côté serveur.
 *
 *   MyToolsCalculs.mount(root, ctx)   ctx = { toast(msg, type) }
 */
(function () {
  'use strict';
  if (window.MyToolsCalculs) return;

  const LS_MTR = 'mysifa_mtr_saisie_v1';
  const LS_CALC = 'mysifa_tools_calculs_v1';

  // ── Calculs purs (testés par tests/test_tools_calculs.js) ──────────
  const n = v => { const x = parseFloat(String(v == null ? '' : v).replace(',', '.')); return isFinite(x) ? x : NaN; };

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
    const W = n(laize), l = n(largeur), g = isNaN(n(espace)) ? 0 : n(espace), r = isNaN(n(rive)) ? 0 : n(rive);
    if (!(W > 0) || !(l > 0)) return { vide: true };
    if (g < 0 || r < 0) return { erreur: 'Espace et rive ne peuvent pas être négatifs.' };
    const module = l + g;
    const utile = W - 2 * r;
    const nb = Math.floor((utile + 1e-9) / module);
    if (nb < 1) return { erreur: 'Aucune étiquette ne tient sur cette laize.', module };
    const utilisee = nb * module;
    return { nb, module, utilisee, chute: W - utilisee, chutePct: (W - utilisee) / W * 100 };
  }

  function laizeMini(nb, largeur, espace, rive) {
    const N = Math.floor(n(nb)), l = n(largeur), g = isNaN(n(espace)) ? 0 : n(espace), r = isNaN(n(rive)) ? 0 : n(rive);
    if (!(N >= 1) || !(l > 0)) return null;
    return N * (l + g) + 2 * r;
  }

  function etiquettes(metres, hauteur, espace, nbFronts) {
    const L = n(metres), h = n(hauteur), g = isNaN(n(espace)) ? 0 : n(espace), f = Math.floor(n(nbFronts)) || 1;
    if (!(L > 0) || !(h > 0)) return { vide: true };
    const module = h + g;
    const parFront = Math.floor((L * 1000 + 1e-6) / module);
    return { parFront, total: parFront * f, module };
  }

  function metragePour(quantite, hauteur, espace, nbFronts) {
    const q = n(quantite), h = n(hauteur), g = isNaN(n(espace)) ? 0 : n(espace), f = Math.floor(n(nbFronts)) || 1;
    if (!(q > 0) || !(h > 0)) return null;
    return Math.ceil(q / f) * (h + g) / 1000;
  }

  // ── Interface ──────────────────────────────────────────────────────
  let CTX = { toast: () => {} };
  const C = { host: null, epaisseurs: null };

  const fmt = (x, dec) => Number(x).toLocaleString('fr-FR', { minimumFractionDigits: dec || 0, maximumFractionDigits: dec || 0 });
  function lire(cle) { try { return JSON.parse(localStorage.getItem(cle) || '{}') || {}; } catch (e) { return {}; } }
  function ecrire(cle, v) { try { localStorage.setItem(cle, JSON.stringify(v)); } catch (e) {} }

  function champ(id, label, attrs) {
    const a = Object.assign({ type: 'number', min: '0', step: 'any', inputmode: 'decimal' }, attrs || {});
    const w = document.createElement('label'); w.className = 'tcal-champ'; w.htmlFor = id;
    const s = document.createElement('span'); s.textContent = label;
    const i = document.createElement('input'); i.id = id; i.className = 'tcal-in';
    Object.keys(a).forEach(k => i.setAttribute(k, a[k]));
    w.append(s, i);
    return w;
  }
  const $ = id => C.host.querySelector('#' + id);
  const val = id => ($(id) ? $(id).value : '');

  function resultat(id, valeur, libelle, vide) {
    const r = $(id);
    r.classList.toggle('tcal-res--vide', !!vide);
    r.querySelector('.tcal-res-v').textContent = valeur;
    r.querySelector('.tcal-res-l').textContent = libelle;
  }
  function blocRes(id) {
    return '<div class="tcal-res tcal-res--vide" id="' + id + '"><div class="tcal-res-v">—</div><div class="tcal-res-l"></div></div>';
  }

  function construire() {
    const h = C.host;
    h.className = 'tcal';
    h.innerHTML =
      '<section class="tcal-carte">'
      + '<header><h2>Métrage ↔ diamètre</h2><p>Longueur enroulée sur une bobine, ou diamètre atteint pour un métrage.</p></header>'
      + '<div class="tcal-seg" role="group" aria-label="Sens du calcul">'
      + '<button type="button" class="tcal-seg-b" data-sens="metrage">Je connais le diamètre</button>'
      + '<button type="button" class="tcal-seg-b" data-sens="diametre">Je connais le métrage</button></div>'
      + '<div class="tcal-grille">'
      + '<label class="tcal-champ" for="tcal-type"><span>Matière</span><select id="tcal-type" class="tcal-in"><option value="">Saisie libre</option></select></label>'
      + '</div><div class="tcal-grille" id="tcal-g1"></div>'
      + blocRes('tcal-r1')
      + '<div class="tcal-err" id="tcal-e1"></div>'
      + '<p class="tcal-aide">Estimation : le serrage de l\'enroulement fait varier le métrage réel. Épaisseurs types gérées dans MyStock.</p>'
      + '</section>'
      + '<section class="tcal-carte">'
      + '<header><h2>Fronts sur la laize</h2><p>Combien d\'étiquettes de front, et ce qu\'il reste en chute.</p></header>'
      + '<div class="tcal-grille" id="tcal-g2"></div>'
      + blocRes('tcal-r2')
      + '<div class="tcal-detail" id="tcal-d2"></div>'
      + '<div class="tcal-err" id="tcal-e2"></div>'
      + '<div class="tcal-grille tcal-grille--sep" id="tcal-g2b"></div>'
      + '<div class="tcal-detail" id="tcal-d2b"></div>'
      + '</section>'
      + '<section class="tcal-carte">'
      + '<header><h2>Étiquettes par bobine</h2><p>Quantité sur un métrage, ou métrage et diamètre pour une quantité visée.</p></header>'
      + '<div class="tcal-grille" id="tcal-g3"></div>'
      + '<div class="tcal-liens" id="tcal-l3"></div>'
      + blocRes('tcal-r3')
      + '<div class="tcal-detail" id="tcal-d3"></div>'
      + '<div class="tcal-grille tcal-grille--sep" id="tcal-g3b"></div>'
      + '<div class="tcal-detail" id="tcal-d3b"></div>'
      + '</section>';

    $('tcal-g1').append(
      champ('tcal-ep', 'Épaisseur (µm)', { placeholder: 'Ex. 145' }),
      champ('tcal-dm', 'Ø ext. mandrin (mm)', { placeholder: 'Ex. 76' }),
      champ('tcal-db', 'Ø ext. bobine (mm)', { placeholder: 'Ex. 1000' }),
      champ('tcal-lm', 'Métrage (m)', { placeholder: 'Ex. 2000' }));
    $('tcal-g2').append(
      champ('tcal-laize', 'Laize bobine (mm)', { placeholder: 'Ex. 440' }),
      champ('tcal-larg', 'Largeur étiquette (mm)', { placeholder: 'Ex. 104,5' }),
      champ('tcal-espl', 'Espace entre fronts (mm)', { placeholder: 'Ex. 3,25' }),
      champ('tcal-rive', 'Rive mini par bord (mm)', { placeholder: '0' }));
    $('tcal-g2b').append(champ('tcal-nbv', 'Fronts voulus', { placeholder: 'Ex. 4', step: '1', min: '1', inputmode: 'numeric' }));
    $('tcal-g3').append(
      champ('tcal-haut', 'Hauteur étiquette (mm)', { placeholder: 'Ex. 148,4' }),
      champ('tcal-espa', 'Espace entre étiquettes (mm)', { placeholder: 'Ex. 4' }),
      champ('tcal-nbf', 'Fronts', { placeholder: '1', step: '1', min: '1', inputmode: 'numeric' }),
      champ('tcal-l3m', 'Métrage (m)', { placeholder: 'Ex. 2000' }));
    $('tcal-g3b').append(champ('tcal-qte', 'Quantité visée (étiquettes)', { placeholder: 'Ex. 10000', step: '1', inputmode: 'numeric' }));

    // Valeurs mémorisées : métrage partagé avec MyStock, le reste propre à MyTools.
    const m = lire(LS_MTR), c = lire(LS_CALC);
    $('tcal-ep').value = m.ep != null ? m.ep : '';
    $('tcal-dm').value = m.dm != null ? m.dm : '';
    $('tcal-db').value = m.db != null ? m.db : '';
    ['lm', 'laize', 'larg', 'espl', 'rive', 'nbv', 'haut', 'espa', 'nbf', 'l3m', 'qte'].forEach(k => {
      if (c[k] != null && $('tcal-' + k)) $('tcal-' + k).value = c[k];
    });
    C.sens = c.sens === 'diametre' ? 'diametre' : 'metrage';
    C.typeMem = m.type || '';

    h.querySelectorAll('.tcal-seg-b').forEach(b => b.addEventListener('click', () => { C.sens = b.getAttribute('data-sens'); maj(); }));
    $('tcal-type').addEventListener('change', () => {
      const t = (C.epaisseurs || []).find(x => String(x.id) === $('tcal-type').value);
      if (t) $('tcal-ep').value = String(t.microns);
      maj();
    });
    $('tcal-ep').addEventListener('input', () => {
      const t = (C.epaisseurs || []).find(x => String(x.id) === $('tcal-type').value);
      if (t && n($('tcal-ep').value) !== t.microns) $('tcal-type').value = '';
    });
    h.addEventListener('input', maj);
    h.addEventListener('click', e => {
      const b = e.target.closest('[data-reprendre]');
      if (!b) return;
      const cible = b.getAttribute('data-reprendre');
      $(cible).value = b.getAttribute('data-valeur');
      maj();
    });
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

  function lien(cible, valeur, texte) {
    return '<button type="button" class="tcal-lien" data-reprendre="' + cible + '" data-valeur="' + valeur + '">' + texte + '</button>';
  }

  function maj() {
    if (!C.host) return;
    // Mémorisation
    ecrire(LS_MTR, Object.assign(lire(LS_MTR), { type: $('tcal-type').value, ep: val('tcal-ep'), dm: val('tcal-dm'), db: val('tcal-db') }));
    const c = { sens: C.sens };
    ['lm', 'laize', 'larg', 'espl', 'rive', 'nbv', 'haut', 'espa', 'nbf', 'l3m', 'qte'].forEach(k => { c[k] = val('tcal-' + k); });
    ecrire(LS_CALC, c);

    // 1. Métrage ↔ diamètre
    C.host.querySelectorAll('.tcal-seg-b').forEach(b => b.classList.toggle('active', b.getAttribute('data-sens') === C.sens));
    $('tcal-db').closest('.tcal-champ').style.display = C.sens === 'metrage' ? '' : 'none';
    $('tcal-lm').closest('.tcal-champ').style.display = C.sens === 'diametre' ? '' : 'none';
    let metres = null;
    $('tcal-e1').textContent = '';
    if (C.sens === 'metrage') {
      const r = metrage(val('tcal-ep'), val('tcal-dm'), val('tcal-db'));
      if (r.erreur) $('tcal-e1').textContent = r.erreur;
      if (r.metres != null) { metres = r.metres; resultat('tcal-r1', '≈ ' + fmt(r.metres) + ' m', 'métrage enroulé'); }
      else resultat('tcal-r1', '—', 'Épaisseur et diamètres à renseigner', true);
    } else {
      const r = diametre(val('tcal-ep'), val('tcal-dm'), val('tcal-lm'));
      if (r.mm != null) { metres = n(val('tcal-lm')); resultat('tcal-r1', '≈ Ø ' + fmt(r.mm) + ' mm', 'diamètre extérieur de la bobine'); }
      else resultat('tcal-r1', '—', 'Épaisseur, mandrin et métrage à renseigner', true);
    }

    // 2. Fronts sur la laize
    const f = fronts(val('tcal-laize'), val('tcal-larg'), val('tcal-espl'), val('tcal-rive'));
    $('tcal-e2').textContent = f.erreur || '';
    if (f.nb) {
      resultat('tcal-r2', f.nb + ' front' + (f.nb > 1 ? 's' : ''), 'sur ' + fmt(n(val('tcal-laize')), 1) + ' mm de laize');
      $('tcal-d2').textContent = 'Module ' + fmt(f.module, 2) + ' mm · laize utilisée ' + fmt(f.utilisee, 2)
        + ' mm · chute ' + fmt(f.chute, 2) + ' mm (' + fmt(f.chutePct, 1) + ' %)';
    } else {
      resultat('tcal-r2', '—', 'Laize et largeur d\'étiquette à renseigner', true);
      $('tcal-d2').textContent = '';
    }
    const lmin = laizeMini(val('tcal-nbv'), val('tcal-larg'), val('tcal-espl'), val('tcal-rive'));
    $('tcal-d2b').textContent = lmin != null ? 'Laize minimale pour ' + Math.floor(n(val('tcal-nbv'))) + ' fronts : ' + fmt(lmin, 2) + ' mm' : '';

    // 3. Étiquettes par bobine — liens de reprise depuis les deux autres calculs
    const liens = [];
    if (metres != null && Math.round(metres) !== Math.round(n(val('tcal-l3m')))) liens.push(lien('tcal-l3m', String(Math.round(metres)), 'Reprendre ' + fmt(metres) + ' m'));
    if (f.nb && f.nb !== Math.floor(n(val('tcal-nbf')))) liens.push(lien('tcal-nbf', String(f.nb), 'Reprendre ' + f.nb + ' front' + (f.nb > 1 ? 's' : '')));
    $('tcal-l3').innerHTML = liens.join('');
    const nbf = Math.floor(n(val('tcal-nbf'))) || 1;
    const e = etiquettes(val('tcal-l3m'), val('tcal-haut'), val('tcal-espa'), nbf);
    if (e.total != null) {
      resultat('tcal-r3', fmt(e.total) + ' étiquettes', 'sur ' + fmt(n(val('tcal-l3m'))) + ' m');
      $('tcal-d3').textContent = (nbf > 1 ? fmt(e.parFront) + ' par front × ' + nbf + ' · ' : '') + 'module en avance ' + fmt(e.module, 2) + ' mm';
    } else {
      resultat('tcal-r3', '—', 'Hauteur d\'étiquette et métrage à renseigner', true);
      $('tcal-d3').textContent = '';
    }
    const besoin = metragePour(val('tcal-qte'), val('tcal-haut'), val('tcal-espa'), nbf);
    if (besoin != null) {
      let t = 'Pour ' + fmt(n(val('tcal-qte'))) + ' étiquettes : ' + fmt(besoin, besoin < 100 ? 1 : 0) + ' m';
      const d = diametre(val('tcal-ep'), val('tcal-dm'), besoin);
      if (d.mm != null) t += ' · Ø bobine ≈ ' + fmt(d.mm) + ' mm';
      else t += ' — renseigner épaisseur et mandrin plus haut pour le diamètre';
      $('tcal-d3b').textContent = t;
    } else $('tcal-d3b').textContent = '';
  }

  async function chargerEpaisseurs() {
    try {
      const r = await fetch('/api/stock/metrage-epaisseurs', { credentials: 'include', cache: 'no-store' });
      C.epaisseurs = r.ok ? await r.json() : [];
      if (!Array.isArray(C.epaisseurs)) C.epaisseurs = [];
    } catch (e) { C.epaisseurs = []; }
    remplirTypes();
  }

  function mount(root, ctx) {
    if (ctx) CTX = Object.assign(CTX, ctx);
    if (!root) return;
    if (!C.host) {
      C.host = document.createElement('div');
      root.appendChild(C.host);
      construire();
      chargerEpaisseurs();
      return;
    }
    root.appendChild(C.host);
  }

  window.MyToolsCalculs = {
    mount,
    _interne: { metrage, diametre, fronts, laizeMini, etiquettes, metragePour },
  };
})();

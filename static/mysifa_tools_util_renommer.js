/* MyTools › Utilitaires › Renommer — renommer un lot de fichiers, d'un coup.
 *
 * Les fichiers déposés restent sur le poste : on calcule les nouveaux noms,
 * on les montre avant/après, puis on rend un zip (JSZip, sans recompression)
 * qui contient les fichiers renommés. Les originaux ne sont jamais modifiés.
 *
 * Règles, appliquées dans cet ordre : nouveau nom (remplace le nom d'origine),
 * remplacement (texte ou expression régulière), casse, préfixe et suffixe,
 * date (du fichier ou du jour), numéro. L'extension est gardée. Caractères
 * interdits par Windows retirés ; deux noms identiques reçoivent « (2) ».
 *
 * Adresse : tri (ajout par défaut, nom, date, taille). Les règles saisies n'y vont pas.
 */
(function () {
  'use strict';
  if (window.MyToolsUtil_renommer) return;

  const URL_JSZIP = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
  const TRIS = [['ajout', 'Ordre d\'ajout', 'Dépôt'], ['nom', 'Nom', 'Alphabétique'], ['date', 'Date', 'Plus ancien'], ['taille', 'Taille', 'Plus petit']];

  // ── Logique pure (tests/test_tools_utilitaires.js) ────────────────
  function decouper(nom) {
    const m = String(nom).match(/^(.+?)(\.[A-Za-z0-9]{1,8})?$/);
    return m ? { base: m[1], ext: m[2] || '' } : { base: String(nom), ext: '' };
  }
  const pad = (n, c) => String(n).padStart(c, '0');
  function formatDate(ms, format) {
    const d = new Date(ms);
    const a = d.getFullYear(), m = pad(d.getMonth() + 1, 2), j = pad(d.getDate(), 2);
    if (format === 'aaaammjj') return '' + a + m + j;
    if (format === 'jj-mm-aaaa') return j + '-' + m + '-' + a;
    return a + '-' + m + '-' + j;
  }
  // Retire ce que Windows, macOS et les zip refusent ; jamais de nom vide.
  function nettoyer(nom) {
    const s = String(nom).replace(/[\\/:*?"<>|\u0000-\u001f]/g, '').replace(/\s+/g, ' ').replace(/^[\s.]+|[\s.]+$/g, '');
    return s || 'fichier';
  }
  function trier(fichiers, tri) {
    const l = fichiers.slice();
    if (tri === 'nom') l.sort((a, b) => a.nom.localeCompare(b.nom, 'fr', { numeric: true, sensitivity: 'base' }));
    else if (tri === 'date') l.sort((a, b) => (a.date - b.date) || a.nom.localeCompare(b.nom, 'fr', { numeric: true }));
    else if (tri === 'taille') l.sort((a, b) => (a.taille - b.taille) || a.nom.localeCompare(b.nom, 'fr', { numeric: true }));
    return l;
  }
  function appliquerRegles(fichiers, R, aujourdhui) {
    R = R || {};
    let motif = null;
    if (R.chercher) {
      if (R.regex) {
        try { motif = new RegExp(R.chercher, 'gi'); }
        catch (e) { return { erreur: 'Expression régulière invalide : ' + e.message }; }
      } else motif = new RegExp(R.chercher.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    }
    const num = R.numero || {}, dt = R.date || {};
    const depart = Number.isFinite(Number(num.depart)) ? Number(num.depart) : 1;
    const pas = Number.isFinite(Number(num.pas)) && Number(num.pas) !== 0 ? Number(num.pas) : 1;
    const chiffres = Math.max(1, Math.min(8, Math.floor(Number(num.chiffres)) || 1));
    const vus = new Map();
    const lignes = fichiers.map((f, i) => {
      const p = decouper(f.nom);
      let b = R.nouveau ? String(R.nouveau) : p.base;
      if (motif) b = b.replace(motif, R.remplacer == null ? '' : String(R.remplacer));
      if (R.casse === 'min') b = b.toLocaleLowerCase('fr');
      else if (R.casse === 'maj') b = b.toLocaleUpperCase('fr');
      b = (R.prefixe || '') + b + (R.suffixe || '');
      if (dt.actif) {
        const v = formatDate(dt.source === 'jour' ? (aujourdhui || Date.now()) : f.date, dt.format);
        const sep = dt.sep == null ? '_' : dt.sep;
        b = dt.position === 'fin' ? b + sep + v : v + sep + b;
      }
      if (num.actif) {
        const n = depart + i * pas, v = (n < 0 ? '-' : '') + pad(Math.abs(n), chiffres);
        const sep = num.sep == null ? '_' : num.sep;
        b = num.position === 'debut' ? v + sep + b : b + sep + v;
      }
      const ext = R.ext === 'min' ? p.ext.toLowerCase() : p.ext;
      return { nom: f.nom, base: nettoyer(b), ext };
    });
    lignes.forEach(l => {
      let nouveau = l.base + l.ext, k = nouveau.toLowerCase(), n = 1;
      l.conflit = false;
      while (vus.has(k)) { n++; nouveau = l.base + ' (' + n + ')' + l.ext; k = nouveau.toLowerCase(); l.conflit = true; }
      vus.set(k, true);
      l.nouveau = nouveau;
      l.change = nouveau !== l.nom;
      delete l.base; delete l.ext;
    });
    return { lignes };
  }

  // ── Interface ──────────────────────────────────────────────────────
  let U = null;
  const N = { host: null, fichiers: [], tri: 'ajout', seq: 0 };
  const $ = s => N.host.querySelector(s);

  function champ(id, libelle, attrs) {
    const l = U.el('label', 'tut-champ');
    l.appendChild(U.el('span', null, libelle));
    const i = U.el('input', 'tut-in'); i.id = 'tut-r-' + id;
    Object.assign(i, Object.assign({ type: 'text', autocomplete: 'off', spellcheck: false }, attrs || {}));
    l.appendChild(i);
    return l;
  }
  function choix(id, libelle, options) {
    const l = U.el('label', 'tut-champ');
    l.appendChild(U.el('span', null, libelle));
    const s = U.el('select', 'tut-in'); s.id = 'tut-r-' + id;
    options.forEach(o => { const op = U.el('option', null, o[1]); op.value = o[0]; s.appendChild(op); });
    l.appendChild(s);
    return l;
  }
  function caseA(id, libelle, bulle) {
    const l = U.el('label', 'tut-case'); if (bulle) l.setAttribute('data-bulle', bulle);
    const i = U.el('input'); i.type = 'checkbox'; i.id = 'tut-r-' + id;
    l.append(i, document.createTextNode(' ' + libelle));
    return l;
  }
  const v = id => { const e = $('#tut-r-' + id); return e ? (e.type === 'checkbox' ? e.checked : e.value) : ''; };

  function construire() {
    const h = N.host;
    h.appendChild(U.tete('renommer'));
    const c1 = U.el('section', 'tut-carte');
    c1.appendChild(U.depot({ multiple: true, titre: 'Déposer les fichiers à renommer', aide: 'ou cliquer pour choisir — ils ne quittent pas le poste', surFichiers: ajouter }));
    h.appendChild(c1);

    const c2 = U.el('section', 'tut-carte');
    c2.appendChild(U.el('div', 'tut-titre', 'Règles'));
    let g = U.el('div', 'tut-grille');
    g.append(champ('nouveau', 'Nouveau nom', { placeholder: 'vide = nom d\'origine' }), champ('prefixe', 'Préfixe', { placeholder: 'ex. BAT_' }), champ('suffixe', 'Suffixe', { placeholder: 'ex. _v2' }));
    c2.appendChild(g);
    g = U.el('div', 'tut-grille');
    g.append(champ('chercher', 'Remplacer…', { placeholder: 'texte à chercher' }), champ('remplacer', '… par', { placeholder: 'vide = supprimer' }));
    const rx = U.el('div', 'tut-champ tut-champ--cases');
    rx.appendChild(caseA('regex', 'Expression régulière', 'Regex'));
    g.appendChild(rx);
    c2.appendChild(g);
    g = U.el('div', 'tut-grille tut-grille--blocs');
    const bn = U.el('div', 'tut-bloc');
    bn.appendChild(caseA('num', 'Numéroter', 'Numéro'));
    const gn = U.el('div', 'tut-grille tut-grille--serree');
    gn.append(choix('npos', 'Position', [['fin', 'À la fin'], ['debut', 'Au début']]), champ('ndep', 'Départ', { value: '1', inputMode: 'numeric' }),
      champ('npas', 'Pas', { value: '1', inputMode: 'numeric' }), champ('nch', 'Chiffres', { value: '3', inputMode: 'numeric' }), champ('nsep', 'Séparateur', { value: '_' }));
    bn.appendChild(gn);
    const bd = U.el('div', 'tut-bloc');
    bd.appendChild(caseA('date', 'Ajouter une date', 'Date'));
    const gd = U.el('div', 'tut-grille tut-grille--serree');
    gd.append(choix('dsrc', 'Date', [['fichier', 'Du fichier'], ['jour', 'Du jour']]), choix('dfmt', 'Format', [['aaaa-mm-jj', 'AAAA-MM-JJ'], ['aaaammjj', 'AAAAMMJJ'], ['jj-mm-aaaa', 'JJ-MM-AAAA']]),
      choix('dpos', 'Position', [['debut', 'Au début'], ['fin', 'À la fin']]), champ('dsep', 'Séparateur', { value: '_' }));
    bd.appendChild(gd);
    g.append(bn, bd);
    c2.appendChild(g);
    g = U.el('div', 'tut-grille');
    g.append(choix('casse', 'Casse', [['aucune', 'Inchangée'], ['min', 'minuscules'], ['maj', 'MAJUSCULES']]), choix('ext', 'Extension', [['garder', 'Inchangée'], ['min', 'En minuscules']]));
    c2.appendChild(g);
    h.appendChild(c2);

    const c3 = U.el('section', 'tut-carte');
    const l = U.el('div', 'tut-ligne');
    l.appendChild(U.el('span', 'tut-lib', 'Ordre'));
    N.choixTri = U.pastilles(TRIS, N.tri, x => { N.tri = x; maj(); U.signaler(); });
    l.appendChild(N.choixTri);
    c3.appendChild(l);
    c3.appendChild(U.el('div', 'tut-err', '')).id = 'tut-r-err';
    const ap = U.el('div', 'tut-renommer'); ap.id = 'tut-r-liste';
    c3.appendChild(ap);
    const act = U.el('div', 'tut-actions');
    const z = U.bouton('tut-btn tut-btn--plein', 'telecharger', 'Télécharger en zip', 'Zip');
    z.id = 'tut-r-zip'; z.addEventListener('click', zipper);
    const vd = U.bouton('tut-btn', 'vider', 'Vider la liste', 'Vider');
    vd.addEventListener('click', () => { N.fichiers = []; maj(); });
    act.append(z, vd);
    c3.appendChild(act);
    c3.appendChild(U.el('div', 'tut-etape', '')).id = 'tut-r-etape';
    h.appendChild(c3);
    let t = 0;
    c2.addEventListener('input', () => { clearTimeout(t); t = setTimeout(maj, 120); });
    c2.addEventListener('change', maj);
    maj();
  }

  function ajouter(liste) {
    liste.forEach(f => N.fichiers.push({ id: ++N.seq, nom: f.name, date: f.lastModified || Date.now(), taille: f.size, f }));
    maj();
  }
  function regles() {
    return {
      nouveau: v('nouveau'), prefixe: v('prefixe'), suffixe: v('suffixe'), chercher: v('chercher'), remplacer: v('remplacer'), regex: v('regex'),
      numero: { actif: v('num'), position: v('npos'), depart: v('ndep'), pas: v('npas'), chiffres: v('nch'), sep: v('nsep') },
      date: { actif: v('date'), source: v('dsrc'), format: v('dfmt'), position: v('dpos'), sep: v('dsep') },
      casse: v('casse'), ext: v('ext'),
    };
  }
  function calcul() {
    const l = trier(N.fichiers, N.tri);
    const r = appliquerRegles(l, regles());
    if (r.lignes) r.lignes.forEach((x, i) => { x.id = l[i].id; x.f = l[i].f; });
    return r;
  }
  function maj() {
    if (!N.host) return;
    N.choixTri.choisir(N.tri);
    const r = calcul(), z = $('#tut-r-liste'), err = $('#tut-r-err');
    err.textContent = r.erreur || '';
    z.textContent = '';
    $('#tut-r-zip').disabled = !N.fichiers.length || !!r.erreur;
    if (!N.fichiers.length) { z.appendChild(U.el('div', 'tut-vide-l', 'Aucun fichier. L\'aperçu des nouveaux noms s\'affiche ici.')); return; }
    if (r.erreur) return;
    const nb = r.lignes.filter(x => x.change).length;
    z.appendChild(U.el('div', 'tut-titre', N.fichiers.length + ' fichier' + (N.fichiers.length > 1 ? 's' : '') + ' · ' + nb + ' renommé' + (nb > 1 ? 's' : '')));
    r.lignes.forEach(x => {
      const li = U.el('div', 'tut-ren-l' + (x.change ? '' : ' tut-ren-l--idem') + (x.conflit ? ' tut-ren-l--conflit' : ''));
      li.appendChild(U.el('span', 'tut-ren-avant', x.nom));
      li.appendChild(U.el('span', 'tut-ren-fleche', '→'));
      const ap = U.el('span', 'tut-ren-apres', x.nouveau);
      if (x.conflit) ap.setAttribute('data-bulle', 'Doublon numéroté');
      li.appendChild(ap);
      const b = U.bouton('tut-x', 'retirer', '', 'Retirer');
      b.addEventListener('click', () => { N.fichiers = N.fichiers.filter(f => f.id !== x.id); maj(); });
      li.appendChild(b);
      z.appendChild(li);
    });
  }
  async function zipper() {
    const r = calcul();
    if (!r.lignes || !r.lignes.length) return;
    const b = $('#tut-r-zip'), et = $('#tut-r-etape');
    b.disabled = true; et.textContent = 'Préparation du zip…';
    try {
      await U.chargerScript(URL_JSZIP);
      const zip = new window.JSZip();
      r.lignes.forEach(x => zip.file(x.nouveau, x.f, { date: new Date(x.f.lastModified || Date.now()), binary: true }));
      const blob = await zip.generateAsync({ type: 'blob', compression: 'STORE' }, m => { et.textContent = 'Zip : ' + Math.round(m.percent) + ' %'; });
      U.telecharger(blob, 'fichiers-renommes-' + new Date().toISOString().slice(0, 10) + '.zip');
      et.textContent = '';
      U.toast('Zip prêt : ' + r.lignes.length + ' fichiers.', 'success');
    } catch (e) { et.textContent = ''; U.toast(e.message || 'Zip impossible.', 'danger'); }
    finally { b.disabled = false; }
  }

  window.MyToolsUtil_renommer = {
    cles: ['tri'],
    mount(host, outils) { U = outils; N.host = host; construire(); },
    etat: () => (N.tri !== 'ajout' ? { tri: N.tri } : {}),
    aller(p) { N.tri = p && TRIS.some(t => t[0] === p.tri) ? p.tri : 'ajout'; if (N.host) maj(); },
    _interne: { decouper, formatDate, nettoyer, trier, appliquerRegles },
  };
})();

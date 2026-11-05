/* MyTools › Utilitaires › Archives — créer un zip, ouvrir un zip.
 *
 *   creer   fichiers et dossiers déposés → un zip (stockage, normale, forte)
 *   ouvrir  un zip → liste de son contenu (dossiers, tailles, dates), extraction
 *           d'un fichier à la fois
 *
 * JSZip, version figée, dans le navigateur : l'archive ne quitte pas le poste.
 * Les zips chiffrés ne s'ouvrent pas (JSZip ne gère pas le chiffrement) : le
 * message le dit. Un fichier extrait est téléchargé sous son seul nom, jamais
 * sous un chemin de l'archive (« ../ » ignoré).
 *
 * Adresse : archive (creer par défaut, ouvrir), compression (normale par défaut,
 * stockage, forte). L'archive ouverte et la recherche n'y vont pas.
 */
(function () {
  'use strict';
  if (window.MyToolsUtil_archives) return;

  const URL_JSZIP = 'https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js';
  const MODES = [['creer', 'Créer un zip', 'Compresser'], ['ouvrir', 'Ouvrir un zip', 'Extraire']];
  const COMPRESSIONS = [['stockage', 'Sans compression', 'Rapide'], ['normale', 'Normale', 'Équilibrée'], ['forte', 'Forte', 'Plus petit']];

  // ── Logique pure (tests/test_tools_utilitaires.js) ────────────────
  // Chemin d'archive sûr : séparateurs « / », sans « .. », « . », lecteur ni racine.
  function cheminSur(p) {
    return String(p == null ? '' : p).replace(/\\/g, '/').split('/')
      .map(s => s.replace(/[\u0000-\u001f]/g, '').trim())
      .filter(s => s && s !== '.' && s !== '..' && !/^[A-Za-z]:$/.test(s)).join('/');
  }
  const nomSeul = p => { const c = cheminSur(p).split('/'); return c[c.length - 1] || 'fichier'; };
  function optionsCompression(c) {
    if (c === 'stockage') return { compression: 'STORE' };
    return { compression: 'DEFLATE', compressionOptions: { level: c === 'forte' ? 9 : 6 } };
  }
  // Noms en double dans un même zip : « (2) » avant l'extension.
  function dedoublonner(chemins) {
    const vus = new Set();
    return chemins.map(c => {
      let p = cheminSur(c) || 'fichier', n = 1;
      const m = p.match(/^(.*?)(\.[^./]{1,8})?$/), base = m[1], ext = m[2] || '';
      while (vus.has(p.toLowerCase())) { n++; p = base + ' (' + n + ')' + ext; }
      vus.add(p.toLowerCase());
      return p;
    });
  }
  // Entrées JSZip → lignes triées (dossiers d'abord), avec profondeur.
  function lignesArchive(entrees) {
    return entrees.map(e => ({ chemin: cheminSur(e.chemin), dossier: !!e.dossier, taille: e.taille || 0, date: e.date || null }))
      .filter(e => e.chemin)
      .sort((a, b) => {
        const pa = a.chemin.split('/'), pb = b.chemin.split('/');
        for (let i = 0; i < Math.min(pa.length, pb.length); i++) {
          if (pa[i] !== pb[i]) {
            const da = i < pa.length - 1 || a.dossier, db = i < pb.length - 1 || b.dossier;
            if (da !== db) return da ? -1 : 1;
            return pa[i].localeCompare(pb[i], 'fr', { numeric: true, sensitivity: 'base' });
          }
        }
        return pa.length - pb.length;
      })
      .map(e => Object.assign(e, { profondeur: e.chemin.split('/').length - 1, nom: e.chemin.split('/').pop() }));
  }

  // ── Interface ──────────────────────────────────────────────────────
  let U = null;
  const Z = { host: null, mode: 'creer', compression: 'normale', fichiers: [], seq: 0, zip: null, nomZip: '', lignes: [] };
  const $ = s => Z.host.querySelector(s);
  const fmtDate = d => (d ? new Date(d).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '');

  function construire() {
    const h = Z.host;
    h.appendChild(U.tete('archives'));
    Z.choixMode = U.pastilles(MODES, Z.mode, v => { Z.mode = v; afficher(); U.signaler(); }, 'tut-pastilles--grandes');
    h.appendChild(Z.choixMode);

    // Créer
    const cc = U.el('section', 'tut-carte'); cc.setAttribute('data-mode', 'creer');
    cc.appendChild(U.depot({ multiple: true, titre: 'Déposer les fichiers à archiver', aide: 'ou cliquer pour choisir — un dossier déposé garde son arborescence', surFichiers: l => ajouter(l.map(f => [f, f.name])) }));
    const ld = U.el('div', 'tut-actions');
    const bdos = U.bouton('tut-btn', 'dossier', 'Ajouter un dossier', 'Dossier');
    const idos = U.el('input'); idos.type = 'file'; idos.hidden = true; idos.webkitdirectory = true; idos.multiple = true;
    bdos.addEventListener('click', () => idos.click());
    idos.addEventListener('change', () => { ajouter(Array.from(idos.files).map(f => [f, f.webkitRelativePath || f.name])); idos.value = ''; });
    ld.append(bdos, idos);
    cc.appendChild(ld);
    // Glisser un dossier sur la zone : on parcourt l'arborescence.
    const zd = cc.querySelector('.tut-depot');
    zd.addEventListener('drop', e => {
      const items = e.dataTransfer && e.dataTransfer.items;
      if (!items || !items.length || !items[0].webkitGetAsEntry) return;
      const entrees = Array.from(items).map(i => i.webkitGetAsEntry()).filter(Boolean);
      if (!entrees.some(x => x.isDirectory)) return;
      e.preventDefault(); e.stopImmediatePropagation(); zd.classList.remove('tut-survol');
      parcourir(entrees).then(ajouter);
    }, true);
    const g = U.el('div', 'tut-grille');
    const ln = U.el('label', 'tut-champ'); ln.appendChild(U.el('span', null, 'Nom du zip'));
    const in1 = U.el('input', 'tut-in'); in1.id = 'tut-a-nom'; in1.placeholder = 'archive'; in1.autocomplete = 'off';
    ln.appendChild(in1); g.appendChild(ln);
    const lc = U.el('div', 'tut-champ'); lc.appendChild(U.el('span', null, 'Compression'));
    Z.choixComp = U.pastilles(COMPRESSIONS, Z.compression, v => { Z.compression = v; U.signaler(); });
    lc.appendChild(Z.choixComp); g.appendChild(lc);
    cc.appendChild(g);
    const lst = U.el('div', 'tut-arch-liste'); lst.id = 'tut-a-liste';
    cc.appendChild(lst);
    const act = U.el('div', 'tut-actions');
    const bz = U.bouton('tut-btn tut-btn--plein', 'telecharger', 'Créer le zip', 'Créer'); bz.id = 'tut-a-zip';
    bz.addEventListener('click', creer);
    const bv = U.bouton('tut-btn', 'vider', 'Vider', 'Vider');
    bv.addEventListener('click', () => { Z.fichiers = []; majCreer(); });
    act.append(bz, bv);
    cc.appendChild(act);
    cc.appendChild(U.el('div', 'tut-etape', '')).id = 'tut-a-etape';
    h.appendChild(cc);

    // Ouvrir
    const co = U.el('section', 'tut-carte'); co.setAttribute('data-mode', 'ouvrir');
    co.appendChild(U.depot({ multiple: false, accept: '.zip,application/zip', titre: 'Déposer un fichier .zip', aide: 'ou cliquer pour choisir — il est lu sur le poste', surFichiers: l => ouvrir(l[0]) }));
    const rech = U.el('input', 'tut-in'); rech.id = 'tut-a-rech'; rech.type = 'search'; rech.placeholder = 'Rechercher dans l\'archive (nom, dossier)'; rech.hidden = true;
    rech.addEventListener('input', majOuvrir);
    rech.addEventListener('keydown', e => { if (e.key === 'Escape') { rech.value = ''; majOuvrir(); } });
    co.appendChild(rech);
    const lo = U.el('div', 'tut-arch-contenu'); lo.id = 'tut-a-contenu';
    co.appendChild(lo);
    h.appendChild(co);
    afficher();
  }

  function parcourir(entrees) {
    const sortie = [];
    const lireDossier = d => new Promise(ok => {
      const r = d.createReader(), tout = [];
      const lot = () => r.readEntries(l => { if (!l.length) ok(tout); else { tout.push(...l); lot(); } }, () => ok(tout));
      lot();
    });
    const visiter = async (e, chemin) => {
      if (e.isFile) await new Promise(ok => e.file(f => { sortie.push([f, chemin + f.name]); ok(); }, () => ok()));
      else if (e.isDirectory) { for (const x of await lireDossier(e)) await visiter(x, chemin + e.name + '/'); }
    };
    return (async () => { for (const e of entrees) await visiter(e, ''); return sortie; })();
  }
  function ajouter(paires) {
    paires.forEach(p => Z.fichiers.push({ id: ++Z.seq, f: p[0], chemin: cheminSur(p[1]) || p[0].name }));
    majCreer();
  }
  function afficher() {
    Z.choixMode.choisir(Z.mode); Z.choixComp.choisir(Z.compression);
    Z.host.querySelectorAll('[data-mode]').forEach(e => { e.hidden = e.getAttribute('data-mode') !== Z.mode; });
    majCreer(); majOuvrir();
  }
  function majCreer() {
    const l = $('#tut-a-liste');
    l.textContent = '';
    $('#tut-a-zip').disabled = !Z.fichiers.length;
    if (!Z.fichiers.length) return;
    const total = Z.fichiers.reduce((s, x) => s + x.f.size, 0);
    l.appendChild(U.el('div', 'tut-titre', Z.fichiers.length + ' fichier' + (Z.fichiers.length > 1 ? 's' : '') + ' · ' + U.taille(total)));
    Z.fichiers.slice(0, 500).forEach(x => {
      const li = U.el('div', 'tut-arch-l');
      li.appendChild(U.el('span', 'tut-arch-nom', x.chemin));
      li.appendChild(U.el('small', null, U.taille(x.f.size)));
      const b = U.bouton('tut-x', 'retirer', '', 'Retirer');
      b.addEventListener('click', () => { Z.fichiers = Z.fichiers.filter(y => y.id !== x.id); majCreer(); });
      li.appendChild(b);
      l.appendChild(li);
    });
    if (Z.fichiers.length > 500) l.appendChild(U.el('div', 'tut-aide', '… et ' + (Z.fichiers.length - 500) + ' autres.'));
  }
  async function creer() {
    if (!Z.fichiers.length) return;
    const b = $('#tut-a-zip'), et = $('#tut-a-etape');
    b.disabled = true; et.textContent = 'Préparation…';
    try {
      await U.chargerScript(URL_JSZIP);
      const zip = new window.JSZip();
      const chemins = dedoublonner(Z.fichiers.map(x => x.chemin));
      Z.fichiers.forEach((x, i) => zip.file(chemins[i], x.f, { date: new Date(x.f.lastModified || Date.now()), binary: true }));
      const blob = await zip.generateAsync(Object.assign({ type: 'blob' }, optionsCompression(Z.compression)), m => { et.textContent = 'Compression : ' + Math.round(m.percent) + ' %'; });
      const nom = (($('#tut-a-nom').value || '').trim().replace(/[\\/:*?"<>|]/g, '').replace(/\.zip$/i, '') || 'archive') + '.zip';
      U.telecharger(blob, nom);
      et.textContent = nom + ' · ' + U.taille(blob.size);
      U.toast('Zip créé.', 'success');
    } catch (e) { et.textContent = ''; U.toast(e.message || 'Zip impossible.', 'danger'); }
    finally { b.disabled = false; }
  }
  async function ouvrir(f) {
    if (!f) return;
    const c = $('#tut-a-contenu');
    c.textContent = ''; c.appendChild(U.el('div', 'tut-vide-l', 'Lecture de ' + f.name + '…'));
    try {
      await U.chargerScript(URL_JSZIP);
      const zip = await window.JSZip.loadAsync(f);
      Z.zip = zip; Z.nomZip = f.name; Z.tailleZip = f.size;
      const ent = [];
      zip.forEach((chemin, e) => ent.push({ chemin, dossier: e.dir, taille: e._data && e._data.uncompressedSize, date: e.date }));
      Z.lignes = lignesArchive(ent);
      $('#tut-a-rech').hidden = false; $('#tut-a-rech').value = '';
    } catch (e) {
      Z.zip = null; Z.lignes = [];
      const m = String(e && e.message || e);
      c.textContent = '';
      c.appendChild(U.el('div', 'tut-err', /encrypt/i.test(m) ? 'Archive chiffrée : elle ne peut pas être ouverte ici.' : 'Ce fichier n\'est pas un zip lisible.'));
      return;
    }
    majOuvrir();
  }
  function majOuvrir() {
    const c = $('#tut-a-contenu');
    if (!Z.zip) { if (!c.querySelector('.tut-err')) c.textContent = ''; return; }
    c.textContent = '';
    const fichiers = Z.lignes.filter(x => !x.dossier);
    const total = fichiers.reduce((s, x) => s + x.taille, 0);
    c.appendChild(U.el('div', 'tut-titre', Z.nomZip + ' · ' + fichiers.length + ' fichier' + (fichiers.length > 1 ? 's' : '') + ' · ' + U.taille(total) + ' décompressés (' + U.taille(Z.tailleZip) + ' compressés)'));
    const q = ($('#tut-a-rech').value || '').trim().toLocaleLowerCase('fr');
    const vis = q ? Z.lignes.filter(x => x.chemin.toLocaleLowerCase('fr').indexOf(q) !== -1) : Z.lignes;
    if (!vis.length) { c.appendChild(U.el('div', 'tut-vide-l', 'Aucun résultat pour « ' + q + ' »')); return; }
    vis.slice(0, 2000).forEach(x => {
      const li = U.el('div', 'tut-arch-l' + (x.dossier ? ' tut-arch-l--dossier' : ''));
      li.style.paddingLeft = (10 + (q ? 0 : x.profondeur) * 18) + 'px';
      const ic = U.el('span', 'tut-arch-ic'); ic.innerHTML = U.svg(x.dossier ? U.IC.dossier : U.IC.fichier, 15);
      li.appendChild(ic);
      li.appendChild(U.el('span', 'tut-arch-nom', q ? x.chemin : x.nom));
      if (!x.dossier) {
        li.appendChild(U.el('small', null, U.taille(x.taille) + (x.date ? ' · ' + fmtDate(x.date) : '')));
        const b = U.bouton('tut-btn tut-btn--petit', 'telecharger', 'Extraire', 'Extraire');
        b.addEventListener('click', () => extraire(x.chemin, b));
        li.appendChild(b);
      }
      c.appendChild(li);
    });
    if (vis.length > 2000) c.appendChild(U.el('div', 'tut-aide', 'Affichage limité à 2 000 entrées : affiner la recherche.'));
  }
  async function extraire(chemin, b) {
    const e = Z.zip && Object.values(Z.zip.files).find(x => cheminSur(x.name) === chemin);
    if (!e) return;
    b.disabled = true;
    try { U.telecharger(await e.async('blob'), nomSeul(chemin)); }
    catch (err) { U.toast('Extraction impossible : fichier endommagé ou chiffré.', 'danger'); }
    finally { b.disabled = false; }
  }

  window.MyToolsUtil_archives = {
    cles: ['archive', 'compression'],
    mount(host, outils) { U = outils; Z.host = host; construire(); },
    etat: () => {
      const e = {};
      if (Z.mode !== 'creer') e.archive = Z.mode;
      if (Z.mode === 'creer' && Z.compression !== 'normale') e.compression = Z.compression;
      return e;
    },
    aller(p) {
      p = p || {};
      Z.mode = p.archive === 'ouvrir' ? 'ouvrir' : 'creer';
      Z.compression = COMPRESSIONS.some(c => c[0] === p.compression) ? p.compression : 'normale';
      if (Z.host) afficher();
    },
    _interne: { cheminSur, nomSeul, optionsCompression, dedoublonner, lignesArchive },
  };
})();

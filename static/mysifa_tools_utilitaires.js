/* MyTools › Utilitaires — six petits outils du quotidien, un à la fois.
 *
 *   qr        Codes : QR, Code 128, EAN-13, DataMatrix (bwip-js)        static/mysifa_tools_util_qr.js
 *   scanner   Scanner de documents : photo → bords, redressement, PDF   static/mysifa_tools_util_scanner.js
 *   comparer  Comparer deux textes, deux listes ou deux tableaux CSV     static/mysifa_tools_util_comparer.js
 *   unites    Unités et couleurs : longueurs, grammage, laize, CMJN…     static/mysifa_tools_util_unites.js
 *   renommer  Renommer des fichiers en lot, téléchargés en zip           static/mysifa_tools_util_renommer.js
 *   archives  Créer un zip, ouvrir un zip et en extraire un fichier      static/mysifa_tools_util_archives.js
 *
 * Tout se passe dans le navigateur : aucun fichier ne quitte le poste. Seules
 * les bibliothèques (bwip-js, pdf-lib, tesseract.js et ses langues, JSZip)
 * sont téléchargées depuis leur CDN, en version figée.
 *
 * Chaque sous-outil est chargé au premier usage et s'expose sous
 * window.MyToolsUtil_<id> = { mount(host, ctx), etat() → {cle: valeur},
 * aller(params), cles, demonter(), _interne }. Ce fichier ne fait que les
 * onglets, le chargement et l'adresse :
 *   /tools?outil=utilitaires&sous=<id>&<options du sous-outil>
 * Une option égale à son défaut n'est pas écrite ; les saisies libres (texte
 * à encoder, textes comparés, règles de renommage) n'y vont jamais.
 *
 *   MyToolsUtilitaires.mount(root, ctx)
 *   MyToolsUtilitaires.adresse = { etat() → {sous, options}, aller({sous, params}) }
 *   MyToolsUtilitaires.outils   helpers partagés par les sous-outils
 */
(function () {
  'use strict';
  if (window.MyToolsUtilitaires) return;

  // [id, titre, description courte, icône (grille 24), fichier]
  const SOUS = [
    ['qr', 'Codes', 'QR, Code 128, EAN-13, DataMatrix à copier ou télécharger.',
      '<rect x="3" y="3" width="6.5" height="6.5" rx="1"/><rect x="14.5" y="3" width="6.5" height="6.5" rx="1"/><rect x="3" y="14.5" width="6.5" height="6.5" rx="1"/><path d="M14.5 14.5h2.5v2.5h-2.5zM19.5 19.5H21V21h-1.5zM14.5 20.5h2M21 14.5v2.5M12 3v3.5M12 10v2H9.5"/>'],
    ['scanner', 'Scanner', 'Photo d\'un document → page redressée, contrastée, en PDF.',
      '<path d="M3 8.5A2 2 0 0 1 5 6.5h2l1.5-2.5h7L17 6.5h2a2 2 0 0 1 2 2V18a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9.5 10h5v6.5h-5z"/><path d="M11 12.5h2M11 14.5h2"/>'],
    ['comparer', 'Comparer', 'Deux textes, deux listes ou deux tableaux CSV.',
      '<rect x="3" y="3.5" width="7.5" height="17" rx="1.5"/><rect x="13.5" y="3.5" width="7.5" height="17" rx="1.5"/><path d="M5.25 12h3M15.75 12h3M17.25 10.5v3"/>'],
    ['unites', 'Unités et couleurs', 'Longueurs, grammage, laize ↔ m², CMJN, contraste, Pantone.',
      '<path d="M3.5 16.5L16.5 3.5l4 4-13 13z"/><path d="M7 13l2 2M10 10l2 2M13 7l2 2"/>'],
    ['renommer', 'Renommer', 'Préfixe, numéro, date, remplacement sur tout un lot.',
      '<path d="M3 19l4.5-13L12 19M4.6 14.5h5.8"/><path d="M14 20l6.6-6.6a1.6 1.6 0 0 0-2.2-2.2L11.8 17.8V20z"/>'],
    ['archives', 'Archives', 'Créer un zip, ouvrir un zip et en extraire un fichier.',
      '<rect x="3" y="3.5" width="18" height="5" rx="1"/><path d="M5 8.5v10.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8.5"/><path d="M10 12.5h4"/>'],
  ];
  const IDS = SOUS.map(s => s[0]);
  // Clés d'adresse de chaque sous-outil (validées par le sous-outil lui-même).
  const CLES = {
    qr: ['format'], scanner: ['rendu', 'mise'], comparer: ['comparaison', 'niveau', 'casse', 'espaces'],
    unites: ['conv'], renommer: ['tri'], archives: ['archive', 'compression'],
  };
  const DEFAUT = 'qr';

  // ── Helpers partagés ──────────────────────────────────────────────
  const esc = s => String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const svg = (d, t) => '<svg width="' + (t || 18) + '" height="' + (t || 18) + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + d + '</svg>';
  const IC = {
    copier: '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
    telecharger: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    deposer: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
    retirer: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    haut: '<polyline points="18 15 12 9 6 15"/>',
    bas: '<polyline points="6 9 12 15 18 9"/>',
    tourner: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
    vider: '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    inverser: '<path d="M7 4L3 8l4 4"/><path d="M3 8h13a5 5 0 0 1 0 10h-2"/>',
    dossier: '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
    fichier: '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
    camera: '<path d="M3 8.5A2 2 0 0 1 5 6.5h2l1.5-2.5h7L17 6.5h2a2 2 0 0 1 2 2V18a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><circle cx="12" cy="13" r="3.5"/>',
  };
  const taille = n => (n >= 1e9 ? (n / 1e9).toFixed(2).replace('.', ',') + ' Go' : n >= 1e6 ? (n / 1e6).toFixed(1).replace('.', ',') + ' Mo' : n >= 1e3 ? Math.round(n / 1e3) + ' Ko' : n + ' o');
  const _scripts = {};
  function chargerScript(url) {
    if (_scripts[url]) return _scripts[url];
    _scripts[url] = new Promise((ok, ko) => {
      const s = document.createElement('script');
      s.src = url; s.async = true;
      s.onload = () => ok();
      s.onerror = () => { _scripts[url] = null; s.remove(); ko(new Error('Bibliothèque indisponible — vérifier la connexion.')); };
      document.head.appendChild(s);
    });
    return _scripts[url];
  }
  function telecharger(blob, nom) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = nom;
    document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
  }
  async function copierTexte(t) {
    try { await navigator.clipboard.writeText(t); return true; }
    catch (e) {
      const ta = document.createElement('textarea');
      ta.value = t; ta.style.cssText = 'position:fixed;opacity:0';
      document.body.appendChild(ta); ta.select();
      let ok = false; try { ok = document.execCommand('copy'); } catch (e2) {}
      ta.remove(); return ok;
    }
  }
  const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
  // Bouton à icône + libellé, avec sa bulle d'un mot.
  function bouton(cls, icone, libelle, bulle) {
    const b = el('button', cls);
    b.type = 'button';
    b.innerHTML = (icone ? svg(IC[icone] || icone, 16) : '') + (libelle ? '<span>' + esc(libelle) + '</span>' : '');
    if (bulle) b.setAttribute('data-bulle', bulle);
    if (!libelle && bulle) b.setAttribute('aria-label', bulle);
    return b;
  }
  // Zone de dépôt : clic, clavier ou glisser-déposer. `o` = { multiple, accept,
  // titre, aide, dossier (bouton « dossier » en plus), surFichiers(files) }.
  function depot(o) {
    const z = el('div', 'tut-depot');
    z.tabIndex = 0; z.setAttribute('role', 'button');
    z.setAttribute('data-bulle', o.bulle || 'Déposer');
    z.innerHTML = '<span class="tut-depot-ic">' + svg(IC.deposer, 26) + '</span><strong></strong><span class="tut-depot-aide"></span>';
    z.querySelector('strong').textContent = o.titre || 'Déposer des fichiers ici';
    z.querySelector('.tut-depot-aide').textContent = o.aide || 'ou cliquer pour choisir';
    const inp = el('input'); inp.type = 'file'; inp.hidden = true;
    if (o.multiple) inp.multiple = true;
    if (o.accept) inp.accept = o.accept;
    z.appendChild(inp);
    const rendre = l => { const f = Array.from(l || []); if (f.length) o.surFichiers(f); };
    inp.addEventListener('change', () => { rendre(inp.files); inp.value = ''; });
    z.addEventListener('click', e => { if (e.target === inp) return; inp.click(); });
    z.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); inp.click(); } });
    z.addEventListener('dragover', e => { e.preventDefault(); z.classList.add('tut-survol'); });
    z.addEventListener('dragleave', () => z.classList.remove('tut-survol'));
    z.addEventListener('drop', e => { e.preventDefault(); z.classList.remove('tut-survol'); rendre(e.dataTransfer && e.dataTransfer.files); });
    return z;
  }
  // Groupe de pastilles exclusives. `choix` = [[valeur, libellé, bulle]].
  function pastilles(choix, valeur, surChoix, cls) {
    const g = el('div', 'tut-pastilles' + (cls ? ' ' + cls : ''));
    g.setAttribute('role', 'group');
    choix.forEach(c => {
      const b = el('button', 'tut-pastille', c[1]);
      b.type = 'button'; b.setAttribute('data-v', c[0]);
      if (c[2]) b.setAttribute('data-bulle', c[2]);
      b.addEventListener('click', () => { g.querySelectorAll('.tut-pastille').forEach(x => x.classList.toggle('actif', x === b)); surChoix(c[0]); });
      g.appendChild(b);
    });
    g.choisir = v => g.querySelectorAll('.tut-pastille').forEach(x => x.classList.toggle('actif', x.getAttribute('data-v') === v));
    g.choisir(valeur);
    return g;
  }
  function tete(id) {
    const s = SOUS.find(x => x[0] === id);
    const h = el('header', 'tut-tete');
    h.innerHTML = '<span class="tut-tete-ic">' + svg(s[3], 26) + '</span><div><h2></h2><p></p></div>';
    h.querySelector('h2').textContent = s[1];
    h.querySelector('p').textContent = s[2];
    return h;
  }

  // ── État ───────────────────────────────────────────────────────────
  let CTX = { toast: () => {}, surChange: null };
  const C = { host: null, sous: DEFAUT, hosts: {}, attente: {}, charges: {}, monte: {} };
  const glob = id => window['MyToolsUtil_' + id];
  function signaler() { if (CTX && typeof CTX.surChange === 'function') { try { CTX.surChange(); } catch (e) {} } }
  const outils = { esc, svg, IC, taille, chargerScript, telecharger, copierTexte, el, bouton, depot, pastilles, tete,
    toast: (m, t) => CTX.toast(m, t), signaler };

  function chargerSous(id) {
    if (glob(id)) return Promise.resolve();
    if (C.charges[id]) return C.charges[id];
    const T = window.__MYTOOLS__ || {};
    const v = T.version ? '?v=' + encodeURIComponent(T.version) : '';
    C.charges[id] = new Promise((ok, ko) => {
      const s = document.createElement('script');
      s.src = '/static/mysifa_tools_util_' + id + '.js' + v;
      s.onload = () => ok();
      s.onerror = () => { C.charges[id] = null; s.remove(); ko(new Error('Outil indisponible — recharger la page.')); };
      document.head.appendChild(s);
    });
    return C.charges[id];
  }

  function construire() {
    const h = C.host;
    h.className = 'tut';
    const nav = el('div', 'tut-onglets');
    nav.setAttribute('role', 'tablist'); nav.setAttribute('aria-label', 'Utilitaires');
    SOUS.forEach(s => {
      const b = el('button', 'tut-onglet');
      b.type = 'button'; b.setAttribute('role', 'tab'); b.setAttribute('data-sous', s[0]);
      b.setAttribute('data-bulle', s[1]);
      b.innerHTML = '<span class="tut-onglet-ic">' + svg(s[3], 20) + '</span><span class="tut-onglet-t">' + esc(s[1]) + '</span>';
      b.addEventListener('click', () => { if (C.sous !== s[0]) { C.sous = s[0]; afficher(); } });
      nav.appendChild(b);
    });
    h.appendChild(nav);
    const zone = el('div', 'tut-zone');
    h.appendChild(zone);
    C.zone = zone;
  }

  function afficher() {
    if (!C.host) return;
    C.affiche = true;
    const id = C.sous;
    C.host.querySelectorAll('[data-sous]').forEach(b => {
      const on = b.getAttribute('data-sous') === id;
      b.classList.toggle('actif', on); b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    Object.keys(C.hosts).forEach(k => { C.hosts[k].hidden = k !== id; });
    // Un sous-outil masqué coupe ce qui tourne (caméra du scanner).
    Object.keys(C.monte).forEach(k => {
      if (k !== id) { const m = glob(k); if (m && typeof m.masquer === 'function') { try { m.masquer(); } catch (e) {} } }
    });
    if (!C.hosts[id]) {
      const hh = el('div', 'tut-sous');
      hh.setAttribute('data-sous-zone', id);
      C.hosts[id] = hh;
      C.zone.appendChild(hh);
    }
    const host = C.hosts[id];
    if (C.monte[id]) { signaler(); return; }
    host.innerHTML = '<div class="tut-vide"><span class="spin"></span> Chargement…</div>';
    signaler();
    chargerSous(id).then(() => {
      const m = glob(id);
      if (!m || C.monte[id]) return;
      host.innerHTML = '';
      C.monte[id] = true;
      m.mount(host, outils);
      const a = C.attente[id];
      C.attente[id] = null;
      if (a && typeof m.aller === 'function') { try { m.aller(a); } catch (e) {} }
      signaler();
    }).catch(e => { host.textContent = ''; host.appendChild(el('div', 'tut-vide', e.message)); });
  }

  function mount(root, ctx) {
    if (ctx) CTX = Object.assign({}, CTX, ctx);
    if (!root) return;
    // Premier affichage différé d'un tour : une adresse appliquée juste après
    // le montage (sous-onglet demandé) évite de charger d'abord celui par défaut.
    if (!C.host) { C.host = el('div'); root.appendChild(C.host); construire(); Promise.resolve().then(() => { if (!C.affiche) afficher(); }); return; }
    root.appendChild(C.host);
    afficher();
  }
  function demonter() {
    Object.keys(C.monte).forEach(k => { const m = glob(k); if (m && typeof m.masquer === 'function') { try { m.masquer(); } catch (e) {} } });
  }

  window.MyToolsUtilitaires = {
    mount, demonter, outils, SOUS: IDS, CLES,
    adresse: {
      // Options non par défaut du sous-outil affiché ; celles d'une adresse en
      // attente de chargement tant que le sous-outil n'est pas là.
      etat: () => {
        const m = glob(C.sous);
        let options = {};
        if (m && C.monte[C.sous] && typeof m.etat === 'function') { try { options = m.etat() || {}; } catch (e) {} }
        else if (C.attente[C.sous]) options = Object.assign({}, C.attente[C.sous]);
        return { sous: C.sous, options };
      },
      // `params` : objet brut des clés de l'adresse ; chaque sous-outil valide les siennes.
      aller: a => {
        const id = a && IDS.indexOf(a.sous) !== -1 ? a.sous : DEFAUT;
        const p = (a && a.params) || {};
        C.sous = id;
        const m = glob(id);
        if (m && C.monte[id]) { if (typeof m.aller === 'function') { try { m.aller(p); } catch (e) {} } }
        else {
          // Seules les clés connues de ce sous-outil attendent son chargement.
          const garde = {};
          (CLES[id] || []).forEach(k => { if (p[k] != null && /^[a-z0-9_-]{1,20}$/.test(String(p[k]))) garde[k] = String(p[k]); });
          C.attente[id] = garde;
        }
        if (C.host) afficher();
      },
    },
  };
})();

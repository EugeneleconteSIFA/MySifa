/* MyTools › Traducteur — pleine page, sur l'API DeepL déjà servie par
 * app/routers/translate.py (cache + suivi du quota). La modale du portail
 * (openMyTraduction, portal_assets.py) reste : c'est l'accès rapide, ceci
 * l'écran de travail.
 *
 *   MyToolsTraduction.mount(root, ctx)
 *   MyToolsTraduction.adresse = { etat() → {de, vers}, aller({de, vers}, complet) }
 *
 * Les langues vont dans l'adresse, jamais le texte. Elles sont aussi
 * mémorisées dans `mytraduction_prefs`, la clé de la modale du portail : les
 * deux écrans partagent le même choix.
 */
(function () {
  'use strict';
  if (window.MyToolsTraduction) return;

  const LS = 'mytraduction_prefs';
  const LIMITE = 100000;
  let CTX = { toast: () => {}, surChange: null };
  const T = { host: null, langs: null, de: 'auto', vers: 'EN', formalite: 'default', enCours: false, detectee: null };

  function prefs() { try { return JSON.parse(localStorage.getItem(LS) || '{}') || {}; } catch (e) { return {}; } }
  function garder() {
    try { localStorage.setItem(LS, JSON.stringify(Object.assign(prefs(), { source: T.de, target: T.vers, formality: T.formalite }))); } catch (e) {}
  }
  function signaler() { if (typeof CTX.surChange === 'function') { try { CTX.surChange(); } catch (e) {} } }
  function codes() { return (T.langs || []).map(l => l.code); }

  async function chargerLangues() {
    if (T.langs) return;
    try {
      const r = await fetch('/api/translate/langs', { credentials: 'include' });
      if (!r.ok) throw new Error();
      T.langs = (await r.json()).langs || [];
    } catch (e) {
      T.langs = [{ code: 'FR', label: 'Français' }, { code: 'EN', label: 'Anglais' }, { code: 'DE', label: 'Allemand' },
                 { code: 'ES', label: 'Espagnol' }, { code: 'IT', label: 'Italien' }, { code: 'NL', label: 'Néerlandais' }];
    }
  }

  async function usage() {
    const z = T.host && T.host.querySelector('.ttr-usage');
    if (!z) return;
    try {
      const r = await fetch('/api/translate/usage', { credentials: 'include' });
      if (!r.ok) return;
      const u = await r.json();
      const parts = [];
      if (u.deepl_limit && u.deepl_used != null) {
        parts.push('Quota DeepL : ' + Number(u.deepl_used).toLocaleString('fr-FR') + ' / '
          + Number(u.deepl_limit).toLocaleString('fr-FR') + ' car. (' + Math.round(u.deepl_used / u.deepl_limit * 100) + ' %)');
      }
      if (u.cache_hits > 0) parts.push(u.cache_hits + ' depuis le cache ce mois');
      z.textContent = parts.join(' · ');
    } catch (e) {}
  }

  function option(sel, code, label, choisi) {
    const o = document.createElement('option');
    o.value = code; o.textContent = label; if (code === choisi) o.selected = true;
    sel.appendChild(o);
  }

  function construire() {
    const h = T.host;
    h.innerHTML = '';
    h.className = 'ttr';
    h.innerHTML =
      '<div class="ttr-barre">'
      + '<select class="ttr-select" data-r="de" aria-label="Langue source"></select>'
      + '<button type="button" class="ttr-btn ttr-swap" data-r="swap" title="Inverser les langues" aria-label="Inverser les langues">'
      + '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 16V4M3 8l4-4 4 4"/><path d="M17 8v12M21 16l-4 4-4-4"/></svg></button>'
      + '<select class="ttr-select" data-r="vers" aria-label="Langue cible"></select>'
      + '<div class="ttr-seg" role="group" aria-label="Registre">'
      + '<button type="button" class="ttr-seg-b" data-f="default">Neutre</button>'
      + '<button type="button" class="ttr-seg-b" data-f="more">Vouvoiement</button>'
      + '<button type="button" class="ttr-seg-b" data-f="less">Tutoiement</button></div>'
      + '</div>'
      + '<div class="ttr-panneaux">'
      + '<div class="ttr-panneau"><textarea class="ttr-zone" data-r="src" placeholder="Saisir ou coller le texte à traduire, ou déposer un fichier .txt" spellcheck="true"></textarea>'
      + '<div class="ttr-pied"><span class="ttr-compte" data-r="compte">0 caractère</span>'
      + '<span class="ttr-actions"><button type="button" class="ttr-btn" data-r="effacer">Effacer</button>'
      + '<button type="button" class="ttr-btn ttr-btn-accent" data-r="go">Traduire</button></span></div></div>'
      + '<div class="ttr-panneau ttr-panneau-sortie"><textarea class="ttr-zone" data-r="dst" readonly placeholder="Traduction"></textarea>'
      + '<div class="ttr-pied"><span class="ttr-detecte" data-r="detecte"></span>'
      + '<span class="ttr-actions"><button type="button" class="ttr-btn" data-r="copier">Copier</button>'
      + '<button type="button" class="ttr-btn" data-r="telecharger">Télécharger .txt</button></span></div></div>'
      + '</div>'
      + '<div class="ttr-aide">Cmd/Ctrl + Entrée pour traduire. <span class="ttr-usage"></span></div>';
    const q = r => h.querySelector('[data-r="' + r + '"]');
    const de = q('de'), vers = q('vers'), src = q('src'), dst = q('dst');
    option(de, 'auto', 'Détecter la langue', T.de);
    T.langs.forEach(l => option(de, l.code, l.label, T.de));
    T.langs.forEach(l => option(vers, l.code, l.label, T.vers));
    de.addEventListener('change', () => { T.de = de.value; garder(); signaler(); });
    vers.addEventListener('change', () => { T.vers = vers.value; garder(); signaler(); if (src.value.trim()) traduire(); });
    q('swap').addEventListener('click', () => {
      const ancienne = T.de === 'auto' ? (T.detectee || null) : T.de;
      if (!ancienne || codes().indexOf(ancienne) === -1) { CTX.toast('Choisir la langue source avant d\'inverser.', 'info'); return; }
      T.de = T.vers; T.vers = ancienne;
      if (dst.value) { src.value = dst.value; dst.value = ''; }
      garder(); construireSelections(); compter(); signaler();
    });
    h.querySelectorAll('.ttr-seg-b').forEach(b => b.addEventListener('click', () => {
      T.formalite = b.getAttribute('data-f'); garder(); majSeg(); if (src.value.trim()) traduire();
    }));
    src.addEventListener('input', compter);
    src.addEventListener('keydown', e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); traduire(); } });
    src.addEventListener('dragover', e => { e.preventDefault(); src.classList.add('ttr-depot'); });
    src.addEventListener('dragleave', () => src.classList.remove('ttr-depot'));
    src.addEventListener('drop', async e => {
      e.preventDefault(); src.classList.remove('ttr-depot');
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (!f) return;
      if (!/^text\//.test(f.type) && !/\.(txt|csv|md)$/i.test(f.name)) { CTX.toast('Fichier non lu — seuls les fichiers texte (.txt, .csv, .md) se déposent ici.', 'danger'); return; }
      src.value = (await f.text()).slice(0, LIMITE); compter();
    });
    q('effacer').addEventListener('click', () => { src.value = ''; dst.value = ''; T.detectee = null; q('detecte').textContent = ''; compter(); src.focus(); });
    q('go').addEventListener('click', traduire);
    q('copier').addEventListener('click', async () => {
      if (!dst.value) return;
      try { await navigator.clipboard.writeText(dst.value); CTX.toast('Traduction copiée.', 'success'); }
      catch (e) { dst.select(); CTX.toast('Copie refusée par le navigateur — texte sélectionné.', 'info'); }
    });
    q('telecharger').addEventListener('click', () => {
      if (!dst.value) return;
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob([dst.value], { type: 'text/plain;charset=utf-8' }));
      a.download = 'traduction-' + T.vers.toLowerCase() + '.txt';
      document.body.appendChild(a); a.click();
      setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 800);
    });
    majSeg(); compter(); usage();
  }

  function construireSelections() {
    const de = T.host.querySelector('[data-r="de"]'), vers = T.host.querySelector('[data-r="vers"]');
    if (de) de.value = T.de;
    if (vers) vers.value = T.vers;
  }
  function majSeg() {
    T.host.querySelectorAll('.ttr-seg-b').forEach(b => b.classList.toggle('active', b.getAttribute('data-f') === T.formalite));
  }
  function compter() {
    const src = T.host.querySelector('[data-r="src"]'), c = T.host.querySelector('[data-r="compte"]');
    const n = src.value.length;
    c.textContent = n.toLocaleString('fr-FR') + ' caractère' + (n > 1 ? 's' : '') + (n > LIMITE ? ' — limite ' + LIMITE.toLocaleString('fr-FR') : '');
    c.classList.toggle('ttr-trop', n > LIMITE);
  }

  async function traduire() {
    if (T.enCours) return;
    const src = T.host.querySelector('[data-r="src"]'), dst = T.host.querySelector('[data-r="dst"]');
    const go = T.host.querySelector('[data-r="go"]'), det = T.host.querySelector('[data-r="detecte"]');
    const texte = src.value.trim();
    if (!texte) { CTX.toast('Texte vide — rien à traduire.', 'info'); return; }
    if (texte.length > LIMITE) { CTX.toast('Texte trop long — ' + LIMITE.toLocaleString('fr-FR') + ' caractères maximum.', 'danger'); return; }
    T.enCours = true; go.disabled = true; go.textContent = 'Traduction…';
    try {
      const r = await fetch('/api/translate', {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: texte, target_lang: T.vers, source_lang: T.de === 'auto' ? null : T.de, formality: T.formalite }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : 'Traduction impossible (' + r.status + ').');
      dst.value = d.translated || '';
      T.detectee = d.source_detected || null;
      const nom = T.detectee && (T.langs.find(l => l.code === T.detectee) || {}).label;
      det.textContent = (T.de === 'auto' && nom ? 'Détecté : ' + nom : '') + (d.cached ? (nom && T.de === 'auto' ? ' · ' : '') + 'depuis le cache' : '');
      usage();
    } catch (e) {
      CTX.toast(e.message || 'Traduction impossible.', 'danger');
    } finally {
      T.enCours = false; go.disabled = false; go.textContent = 'Traduire';
    }
  }

  async function mount(root, ctx) {
    if (ctx) CTX = Object.assign(CTX, ctx);
    if (!root) return;
    if (!T.host) {
      const p = prefs();
      if (p.source) T.de = p.source;
      if (p.target) T.vers = p.target;
      if (p.formality) T.formalite = p.formality;
      T.host = document.createElement('div');
      root.appendChild(T.host);
      T.host.textContent = 'Chargement…';
      await chargerLangues();
      if (T.de !== 'auto' && codes().indexOf(T.de) === -1) T.de = 'auto';
      if (codes().indexOf(T.vers) === -1) T.vers = 'EN';
      construire();
      signaler();
      requestAnimationFrame(() => { const s = T.host.querySelector('[data-r="src"]'); if (s) s.focus(); });
      return;
    }
    root.appendChild(T.host);
  }

  window.MyToolsTraduction = {
    mount,
    adresse: {
      etat: () => ({ de: T.de, vers: T.vers }),
      aller: (a, complet) => {
        const ok = c => !T.langs || codes().indexOf(c) !== -1;
        if (a && a.de && (a.de === 'auto' || ok(a.de))) T.de = a.de; else if (complet) T.de = 'auto';
        if (a && a.vers && ok(a.vers)) T.vers = a.vers; else if (complet) T.vers = 'EN';
        if (T.host && T.langs) construireSelections();
      },
    },
  };
})();

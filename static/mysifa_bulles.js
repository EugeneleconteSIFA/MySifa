/* MySifa — infobulles courtes, communes à MyTools (et MyBAT pour l'outil Image).
 *
 * Tout élément qui porte `data-bulle="Mot"` affiche au survol ou au focus
 * clavier une infobulle d'un ou deux mots, presque tout de suite (le `title`
 * natif met près d'une seconde et s'étale en phrase). Un raccourci clavier
 * éventuel va dans `data-bulle-touche="⌘Z"`, affiché plus discret.
 *
 * Une seule bulle flottante, en position fixe sur `document.body` : elle
 * n'est jamais coupée par un conteneur `overflow:hidden` ni par le bord de
 * l'écran (elle passe au-dessus du bouton s'il n'y a pas la place dessous, et
 * se recale latéralement). Ignorée au toucher : elle resterait affichée.
 *
 * Le `title` natif d'un élément qui a une `data-bulle` est retiré à la volée
 * (sinon deux infobulles), et recopié en `aria-label` s'il n'y en avait pas.
 */
(function () {
  'use strict';
  if (window.MySifaBulles) return;

  const DELAI = 120;
  let bulle = null, cible = null, minuteur = 0;

  function css() {
    if (document.getElementById('mysifa-bulles-css')) return;
    const s = document.createElement('style');
    s.id = 'mysifa-bulles-css';
    s.textContent =
      '#mysifa-bulle{position:fixed;z-index:100000;pointer-events:none;padding:5px 9px;border-radius:7px;' +
      'background:var(--text);color:var(--card);font:600 12px/1.3 "Segoe UI",system-ui,sans-serif;white-space:nowrap;' +
      'box-shadow:0 4px 14px rgba(0,0,0,.25);opacity:0;transform:translateY(-2px);transition:opacity .08s,transform .08s}' +
      '#mysifa-bulle.vu{opacity:1;transform:none}' +
      '#mysifa-bulle .touche{margin-left:7px;opacity:.6;font-weight:500}' +
      '#mysifa-bulle::after{content:"";position:absolute;left:var(--fleche,50%);width:8px;height:8px;' +
      'background:inherit;transform:translateX(-50%) rotate(45deg)}' +
      '#mysifa-bulle[data-sens="bas"]::after{top:-4px}#mysifa-bulle[data-sens="haut"]::after{bottom:-4px}' +
      '@media (prefers-reduced-motion:reduce){#mysifa-bulle{transition:none}}';
    document.head.appendChild(s);
  }

  function preparer(el) {
    if (el.hasAttribute('title')) {
      if (!el.hasAttribute('aria-label') && !(el.textContent || '').trim()) el.setAttribute('aria-label', el.getAttribute('title'));
      el.removeAttribute('title');
    }
  }

  function placer() {
    if (!bulle || !cible || !cible.isConnected) { cacher(); return; }
    const r = cible.getBoundingClientRect();
    const b = bulle.getBoundingClientRect();
    const marge = 6, vw = document.documentElement.clientWidth, vh = document.documentElement.clientHeight;
    let haut = r.bottom + 8, sens = 'bas';
    if (haut + b.height > vh - marge) { haut = r.top - 8 - b.height; sens = 'haut'; }
    const centre = r.left + r.width / 2;
    let gauche = Math.max(marge, Math.min(vw - marge - b.width, centre - b.width / 2));
    bulle.style.top = Math.round(haut) + 'px';
    bulle.style.left = Math.round(gauche) + 'px';
    bulle.style.setProperty('--fleche', Math.round(Math.max(10, Math.min(b.width - 10, centre - gauche))) + 'px');
    bulle.setAttribute('data-sens', sens);
  }

  function montrer(el) {
    const texte = (el.getAttribute('data-bulle') || '').trim();
    if (!texte) return;
    css();
    if (!bulle) { bulle = document.createElement('div'); bulle.id = 'mysifa-bulle'; bulle.setAttribute('role', 'tooltip'); document.body.appendChild(bulle); }
    bulle.textContent = texte;
    const t = el.getAttribute('data-bulle-touche');
    if (t) { const s = document.createElement('span'); s.className = 'touche'; s.textContent = t; bulle.appendChild(s); }
    bulle.classList.remove('vu');
    bulle.style.display = 'block';
    placer();
    requestAnimationFrame(() => { if (bulle && cible === el) bulle.classList.add('vu'); });
  }

  function cacher() {
    clearTimeout(minuteur);
    cible = null;
    if (bulle) { bulle.classList.remove('vu'); bulle.style.display = 'none'; }
  }

  function entrer(ev, clavier) {
    if (!clavier && ev.pointerType === 'touch') return;
    const el = ev.target && ev.target.closest ? ev.target.closest('[data-bulle]') : null;
    if (!el || el === cible) return;
    preparer(el);
    cacher();
    cible = el;
    minuteur = setTimeout(() => { if (cible === el) montrer(el); }, clavier ? 0 : DELAI);
  }

  function sortir(ev) {
    if (!cible) return;
    const vers = ev.relatedTarget;
    if (vers && cible.contains(vers)) return;
    cacher();
  }

  document.addEventListener('pointerover', e => entrer(e, false), true);
  document.addEventListener('pointerout', sortir, true);
  document.addEventListener('focusin', e => { if (e.target.matches && e.target.matches(':focus-visible')) entrer(e, true); }, true);
  document.addEventListener('focusout', cacher, true);
  document.addEventListener('pointerdown', cacher, true);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') cacher(); }, true);
  window.addEventListener('scroll', cacher, true);
  window.addEventListener('resize', cacher);

  // Raccourci selon la plateforme : bulleTouche('Z') → « ⌘Z » ou « Ctrl+Z ».
  const mac = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent);
  window.MySifaBulles = {
    cacher,
    touche: k => (mac ? '⌘' : 'Ctrl+') + k,
  };
})();

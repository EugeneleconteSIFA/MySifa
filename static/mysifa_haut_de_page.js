/* Bouton flottant « Haut de page » + raccourci Maj+Entrée.
 *
 * Les longues listes (MyStock, Coûts matières) défilent dans un conteneur de
 * la page (#scroll-area, .content), pas dans la fenêtre : on retient donc le
 * dernier élément qui a défilé, et c'est lui qu'on remonte. Le bouton
 * n'apparaît qu'une fois la liste descendue d'un écran.
 *
 * Maj+Entrée est ignoré dans un champ de saisie (retour à la ligne d'un
 * textarea, validation d'un formulaire) et quand une fenêtre est ouverte.
 *
 * Inclusion : <script src="/static/mysifa_haut_de_page.js?v=1" defer></script>
 */
(function () {
  if (window.__mysifaHautDePage) return;
  window.__mysifaHautDePage = true;

  var SEUIL = 600;      // px défilés avant d'afficher le bouton
  var cible = null;     // dernier conteneur qui a défilé
  var bouton = null;

  function haut(el) {
    if (!el || el === document || el === document.documentElement || el === document.body) {
      return window.scrollY || document.documentElement.scrollTop || 0;
    }
    return el.scrollTop || 0;
  }

  function embarque() {
    return !!(window.MySifaBlocs && window.MySifaBlocs.embarque);
  }

  function styles() {
    var st = document.createElement('style');
    st.textContent =
      '.mysifa-haut-page{position:fixed;right:24px;bottom:96px;z-index:80;' +
      'display:inline-flex;align-items:center;gap:6px;padding:9px 14px;border-radius:999px;' +
      'background:var(--card);color:var(--text);border:1px solid var(--border);' +
      'font:600 12px/1 "Segoe UI",system-ui,sans-serif;cursor:pointer;' +
      'box-shadow:0 6px 18px rgba(0,0,0,.18);opacity:0;transform:translateY(8px);' +
      'pointer-events:none;transition:opacity .15s,transform .15s}' +
      '.mysifa-haut-page.visible{opacity:1;transform:none;pointer-events:auto}' +
      '.mysifa-haut-page:hover{background:var(--bg);color:var(--accent);border-color:var(--accent)}' +
      '.mysifa-haut-page kbd{font:600 10px/1 "Segoe UI",system-ui,sans-serif;color:var(--muted);' +
      'border:1px solid var(--border);border-radius:4px;padding:2px 4px;margin-left:2px}' +
      // Sous 900 px, aucun bouton flottant (cf. mysifa_outils_mobile.js).
      '@media (max-width:899px){.mysifa-haut-page{display:none}}';
    document.head.appendChild(st);
  }

  function creer() {
    bouton = document.createElement('button');
    bouton.type = 'button';
    bouton.className = 'mysifa-haut-page';
    bouton.title = 'Revenir en haut de page (Maj+Entrée)';
    bouton.setAttribute('aria-label', 'Haut de page');
    bouton.innerHTML =
      '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" ' +
      'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="18 15 12 9 6 15"/></svg>' +
      '<span>Haut de page</span><kbd>Maj+Entrée</kbd>';
    bouton.addEventListener('click', remonter);
    document.body.appendChild(bouton);
  }

  function rafraichir() {
    if (!bouton) return;
    bouton.classList.toggle('visible', haut(cible) > SEUIL);
  }

  function remonter() {
    var el = cible;
    if (!el || el === document || el === document.documentElement || el === document.body) {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      el.scrollTo({ top: 0, behavior: 'smooth' });
    }
  }

  function enSaisie(e) {
    var t = e.target;
    if (!t) return false;
    if (t.isContentEditable) return true;
    var tag = (t.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || tag === 'select';
  }

  function fenetreOuverte() {
    var mroot = document.getElementById('mroot');
    if (mroot && mroot.firstElementChild) return true;
    var modal = document.getElementById('modal-root');
    return !!(modal && modal.firstElementChild);
  }

  function demarrer() {
    if (embarque()) return;
    styles();
    creer();
    // Capture : un scroll ne remonte pas dans le DOM, seule la phase de
    // capture voit celui d'un conteneur interne.
    document.addEventListener('scroll', function (e) {
      var t = e.target;
      // Les petites zones défilantes (listes déroulantes, cellules) ne
      // prennent pas la main : seul un conteneur assez haut compte.
      if (t && t !== document && t.clientHeight && t.clientHeight < window.innerHeight * 0.5) return;
      cible = t;
      rafraichir();
    }, true);
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' || !e.shiftKey || e.ctrlKey || e.altKey || e.metaKey) return;
      if (enSaisie(e) || fenetreOuverte()) return;
      e.preventDefault();
      remonter();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', demarrer);
  else demarrer();
})();

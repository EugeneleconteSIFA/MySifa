/* Fenêtre de confirmation commune de MySifa (remplace window.confirm).
 *
 * Extraite de mysifa_maint_form.js (maintConfirm), qui la garde comme alias,
 * pour servir aussi aux pages qui ne chargent pas le module Maintenance
 * (Mon coffre…). Même rendu partout : titre, message, détail facultatif,
 * bouton rouge pour une action destructrice (danger: true).
 *
 *   const ok = await mysifaConfirm({title, message, detail, confirmLabel,
 *                                   cancelLabel, danger});
 *
 * Style injecté par le module (classes mysifa-cfm-), sur les seules variables
 * CSS communes du thème : il marche sur n'importe quelle page.
 */
(function () {
  'use strict';

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  // Pourquoi une modale maison plutot que confirm() : la boite native est
  // dessinee par le navigateur, pas par l'app. Elle ignore le theme clair /
  // sombre, elle tronque les retours a la ligne selon le navigateur, et elle
  // ne sait pas distinguer une action destructrice d'une action anodine.
  //
  // Retourne une promesse resolue a true (confirme) ou false (annule).
  function mysifaConfirm(opts) {
    const o = opts || {};
    const titre   = o.title   || 'Confirmer';
    const corps   = o.message || '';
    const detail  = o.detail  || '';
    const okTxt   = o.confirmLabel || 'Confirmer';
    const koTxt   = o.cancelLabel  || 'Annuler';
    const danger  = !!o.danger;

    if (!document.getElementById('mysifa-cfm-style')) {
      const st = document.createElement('style');
      st.id = 'mysifa-cfm-style';
      st.textContent =
        '.mysifa-cfm-ov{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:3000;display:flex;'
      + 'align-items:center;justify-content:center;padding:20px;backdrop-filter:blur(2px)}'
      + '.mysifa-cfm-card{background:var(--card);border:1px solid var(--border);border-radius:14px;'
      + 'width:100%;max-width:460px;box-shadow:0 20px 60px rgba(0,0,0,.45);overflow:hidden;'
      + 'font-family:inherit}'
      + '.mysifa-cfm-head{display:flex;align-items:center;gap:10px;padding:18px 22px;'
      + 'border-bottom:1px solid var(--border)}'
      + '.mysifa-cfm-title{font-size:14px;font-weight:700;color:var(--text);'
      + 'text-transform:uppercase;letter-spacing:.5px}'
      + '.mysifa-cfm-ico{display:inline-flex;color:var(--muted)}'
      + '.mysifa-cfm-ico.danger{color:var(--danger,#f87171)}'
      + '.mysifa-cfm-body{padding:20px 22px;font-size:13px;line-height:1.55;color:var(--text)}'
      + '.mysifa-cfm-detail{margin-top:10px;font-size:12px;line-height:1.5;color:var(--muted)}'
      + '.mysifa-cfm-foot{display:flex;justify-content:flex-end;gap:8px;padding:14px 22px;'
      + 'border-top:1px solid var(--border);background:var(--bg)}'
      + '.mysifa-cfm-btn{display:inline-flex;align-items:center;gap:8px;padding:10px 16px;'
      + 'border-radius:10px;font-size:13px;font-weight:600;font-family:inherit;cursor:pointer;'
      + 'transition:.15s}'
      + '.mysifa-cfm-ghost{border:1px solid var(--border);background:var(--card);color:var(--text2)}'
      + '.mysifa-cfm-ghost:hover{border-color:var(--accent);color:var(--accent)}'
      + '.mysifa-cfm-ok{border:none;background:var(--accent);color:var(--accent-fg);font-weight:700}'
      // --accent-fg suit le theme : encre sombre sur le rouge clair du mode
      // sombre, blanc sur le rouge profond du mode clair. Un #fff en dur
      // donnait du blanc sur #f87171 -- illisible. C'est aussi la convention
      // deja suivie par .toast.danger dans les deux pages hotes.
      + '.mysifa-cfm-ok.danger{background:var(--danger,#f87171);color:var(--accent-fg,#fff)}'
      + '.mysifa-cfm-ok:hover{filter:brightness(1.08)}';
      document.head.appendChild(st);
    }

    const ico = danger
      ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
      : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>';

    const ov = document.createElement('div');
    ov.className = 'mysifa-cfm-ov';
    ov.setAttribute('role', 'dialog');
    ov.setAttribute('aria-modal', 'true');
    ov.innerHTML =
      '<div class="mysifa-cfm-card">'
    +   '<div class="mysifa-cfm-head">'
    +     '<span class="mysifa-cfm-ico' + (danger ? ' danger' : '') + '">' + ico + '</span>'
    +     '<span class="mysifa-cfm-title">' + esc(titre) + '</span>'
    +   '</div>'
    +   '<div class="mysifa-cfm-body">' + esc(corps)
    +     (detail ? '<div class="mysifa-cfm-detail">' + esc(detail) + '</div>' : '')
    +   '</div>'
    +   '<div class="mysifa-cfm-foot">'
    +     '<button type="button" class="mysifa-cfm-btn mysifa-cfm-ghost" data-cfm="0">' + esc(koTxt) + '</button>'
    +     '<button type="button" class="mysifa-cfm-btn mysifa-cfm-ok' + (danger ? ' danger' : '') + '" data-cfm="1">' + esc(okTxt) + '</button>'
    +   '</div>'
    + '</div>';
    document.body.appendChild(ov);

    return new Promise(function (resolve) {
      let clos = false;
      function fermer(val) {
        if (clos) return;           // un double-clic ne doit pas resoudre deux fois
        clos = true;
        document.removeEventListener('keydown', onKey);
        ov.remove();
        resolve(val);
      }
      function onKey(e) {
        if (e.key === 'Escape') fermer(false);
        if (e.key === 'Enter')  fermer(true);
      }
      ov.querySelectorAll('[data-cfm]').forEach(function (b) {
        b.addEventListener('click', function () {
          fermer(b.getAttribute('data-cfm') === '1');
        });
      });
      // Clic sur le fond = annulation, jamais validation.
      ov.addEventListener('click', function (e) { if (e.target === ov) fermer(false); });
      document.addEventListener('keydown', onKey);
      const ok = ov.querySelector('.mysifa-cfm-ok');
      if (ok) ok.focus();
    });
  }

  window.mysifaConfirm = mysifaConfirm;
})();

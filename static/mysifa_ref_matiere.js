/* ============================================================
   MySifa — Sélecteur de référence matière  (v1.0)
   ------------------------------------------------------------
   Un OF et une fiche technique désignent des matières : un carton,
   un mandrin, une palette, un adhésif, un support, une glassine.
   Elles étaient tapées en texte libre, puis rapprochées après coup
   d'une référence MyStock par `mp_fiche_mapping`. Une frappe près
   — « ITASA KA » contre « ITASA jaune KA » — et le besoin matière
   sort faux, sans que rien ne le signale à l'écran.

   Ce composant fait choisir la référence AU MOMENT de la saisie.
   La désignation choisie devient le texte imprimé sur le document :
   une seule vérité, plus de rapprochement à deviner.

   Le bouton « Créer la référence » n'est pas un confort. Sans lui,
   une ADV qui ne trouve pas son carton dans la liste retape du
   texte libre, et le composant n'aura servi à rien. La création est
   volontairement pauvre — référence, désignation, sous-catégorie —
   et pose un brouillon : ni prix, ni laize, ni seuil, parce qu'un
   prix inventé est pire qu'un prix absent, il se propage dans la
   valorisation sans jamais lever d'alerte. MyStock complète ensuite,
   depuis « matières à compléter ».

   ── API ─────────────────────────────────────────────────────────
   MysRefMatiere.ouvrir({
     famille,     'support'|'glassine'|'adhesif'|'carton'|'mandrin'|'palette'
     titre,       intitulé affiché (défaut : la famille)
     valeur,      texte actuel — sert de recherche initiale
     refId,       id actuellement retenu, pour le marquer
     onChoisir,   (ref) => void   ref : {id, reference, designation, …}
     onFermer,    () => void
   })
   ============================================================ */
(function (global) {
  'use strict';

  var LIBELLES = {
    support:  'Support / frontal',
    glassine: 'Glassine',
    adhesif:  'Adhésif',
    carton:   'Carton',
    mandrin:  'Mandrin',
    palette:  'Palette',
  };

  var CSS = [
    '.mrm-fond{position:fixed;inset:0;z-index:9100;display:flex;align-items:center;',
    '  justify-content:center;background:rgba(2,6,23,.62);padding:20px}',
    '.mrm{width:min(680px,96vw);max-height:86vh;display:flex;flex-direction:column;',
    '  background:var(--card,#fff);color:var(--text,#111);border:1px solid var(--border,#dcdfe4);',
    '  border-radius:14px;overflow:hidden;box-shadow:0 24px 70px rgba(0,0,0,.4);font:14px/1.45 inherit}',
    '.mrm-tete{display:flex;align-items:center;gap:12px;padding:14px 16px;',
    '  border-bottom:1px solid var(--border,#dcdfe4)}',
    '.mrm-tete h2{margin:0;font-size:16px;font-weight:800}',
    '.mrm-tete .st{margin:2px 0 0;font-size:12px;color:var(--muted,#6b7280)}',
    '.mrm-x{margin-left:auto;border:1px solid var(--border,#dcdfe4);background:var(--bg,#f6f7f9);',
    '  color:var(--text2,#374151);border-radius:9px;width:30px;height:30px;cursor:pointer;font-size:17px;line-height:1}',
    '.mrm-x:hover{background:#ef4444;border-color:#ef4444;color:#fff}',
    '.mrm-rech{padding:12px 16px;border-bottom:1px solid var(--border,#dcdfe4)}',
    '.mrm-rech input{width:100%;box-sizing:border-box;background:var(--bg,#f6f7f9);',
    '  border:1px solid var(--border,#dcdfe4);border-radius:9px;padding:9px 12px;',
    '  color:var(--text,#111);font:inherit;outline:none}',
    '.mrm-liste{flex:1;overflow:auto;min-height:120px}',
    '.mrm-l{display:flex;gap:10px;align-items:baseline;padding:9px 16px;cursor:pointer;',
    '  border-bottom:1px solid var(--border,#eee)}',
    '.mrm-l:hover{background:var(--accent-bg,#eef2ff)}',
    '.mrm-l.vise{background:var(--accent-bg,#eef2ff)}',
    '.mrm-l .ref{min-width:120px;font-weight:700;font-size:13px}',
    '.mrm-l .des{flex:1;font-size:13px}',
    '.mrm-l .sc{font-size:12px;color:var(--muted,#6b7280)}',
    '.mrm-l .br{font-size:11px;font-weight:700;color:#b45309;border:1px solid #fcd34d;',
    '  background:#fef3c7;border-radius:6px;padding:1px 6px}',
    '.mrm-vide{padding:22px 16px;text-align:center;color:var(--muted,#6b7280);font-size:13px}',
    '.mrm-pied{display:flex;align-items:center;gap:10px;padding:12px 16px;',
    '  border-top:1px solid var(--border,#dcdfe4);flex-wrap:wrap}',
    '.mrm-b{border:1px solid var(--border,#dcdfe4);background:transparent;color:var(--text,#111);',
    '  border-radius:9px;padding:8px 13px;cursor:pointer;font:inherit;font-weight:600}',
    '.mrm-b.p{border:none;background:var(--accent,#4f46e5);color:#fff;font-weight:700}',
    '.mrm-neuf{padding:12px 16px;border-top:1px solid var(--border,#dcdfe4);',
    '  display:grid;grid-template-columns:1fr 1fr;gap:10px}',
    '.mrm-neuf label{display:block;font-size:11px;font-weight:700;text-transform:uppercase;',
    '  letter-spacing:.5px;color:var(--muted,#6b7280);margin-bottom:4px}',
    '.mrm-neuf input{width:100%;box-sizing:border-box;background:var(--bg,#f6f7f9);',
    '  border:1px solid var(--border,#dcdfe4);border-radius:9px;padding:8px 11px;',
    '  color:var(--text,#111);font:inherit;outline:none}',
    '.mrm-neuf .plein{grid-column:1/-1}',
    '.mrm-note{grid-column:1/-1;font-size:12px;color:var(--muted,#6b7280)}',
  ].join('');

  function styler() {
    if (document.getElementById('mrm-css')) return;
    var st = document.createElement('style');
    st.id = 'mrm-css';
    st.textContent = CSS;
    document.head.appendChild(st);
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  async function api(url, opts) {
    var r = await fetch(url, Object.assign({ credentials: 'include' }, opts || {}));
    if (!r.ok) {
      var d = null;
      try { d = await r.json(); } catch (e) { /* réponse non JSON */ }
      throw new Error((d && d.detail) || ('Erreur ' + r.status));
    }
    return r.json();
  }

  function ouvrir(o) {
    o = o || {};
    styler();
    var famille = o.famille;
    if (!LIBELLES[famille]) { console.warn('MysRefMatiere : famille inconnue', famille); return; }

    var refs = [], vise = -1, minuteur = null, creation = false;

    var fond = document.createElement('div');
    fond.className = 'mrm-fond';
    fond.addEventListener('mousedown', function (e) { if (e.target === fond) fermer(); });
    document.body.appendChild(fond);

    fond.innerHTML =
      '<div class="mrm" role="dialog" aria-modal="true">' +
      '  <div class="mrm-tete">' +
      '    <div><h2>' + esc(o.titre || LIBELLES[famille]) + '</h2>' +
      '      <p class="st">La désignation choisie devient le texte imprimé sur le document.</p></div>' +
      '    <button class="mrm-x" data-x aria-label="Fermer">×</button>' +
      '  </div>' +
      '  <div class="mrm-rech"><input data-q type="text" autocomplete="off" ' +
      '     placeholder="Rechercher une référence, une désignation…"></div>' +
      '  <div class="mrm-liste" data-liste></div>' +
      '  <div data-neuf></div>' +
      '  <div class="mrm-pied">' +
      '    <button class="mrm-b" data-creer>+ Créer la référence</button>' +
      '    <span style="flex:1"></span>' +
      '    <button class="mrm-b" data-annuler>Annuler</button>' +
      '  </div>' +
      '</div>';

    var input = fond.querySelector('[data-q]');
    var liste = fond.querySelector('[data-liste]');
    var zoneNeuf = fond.querySelector('[data-neuf]');

    function fermer() {
      document.removeEventListener('keydown', auClavier, true);
      if (fond.parentNode) fond.parentNode.removeChild(fond);
      if (o.onFermer) o.onFermer();
    }

    function peindre() {
      if (!refs.length) {
        liste.innerHTML = '<div class="mrm-vide">Aucune référence ne correspond. ' +
          'Créez-la plutôt que de saisir du texte libre — c\'est elle qui reliera ' +
          'ce document au stock.</div>';
        return;
      }
      liste.innerHTML = refs.map(function (r, i) {
        return '<div class="mrm-l' + (i === vise ? ' vise' : '') + '" data-i="' + i + '">' +
          '<span class="ref">' + esc(r.reference) + '</span>' +
          '<span class="des">' + esc(r.designation) + '</span>' +
          (r.sous_categorie ? '<span class="sc">' + esc(r.sous_categorie) + '</span>' : '') +
          (r.brouillon ? '<span class="br">brouillon</span>' : '') +
          (String(r.id) === String(o.refId) ? '<span class="sc">✓ actuelle</span>' : '') +
          '</div>';
      }).join('');
      Array.prototype.forEach.call(liste.querySelectorAll('[data-i]'), function (el) {
        el.addEventListener('click', function () { prendre(refs[Number(el.dataset.i)]); });
      });
    }

    async function chercher() {
      try {
        var d = await api('/api/stock/matieres/referentiel?famille=' +
          encodeURIComponent(famille) + '&q=' + encodeURIComponent(input.value.trim()));
        refs = d.references || [];
        vise = refs.length ? 0 : -1;
        peindre();
      } catch (e) {
        liste.innerHTML = '<div class="mrm-vide">' + esc(e.message) + '</div>';
      }
    }

    function prendre(r) {
      if (!r) return;
      if (o.onChoisir) o.onChoisir(r);
      fermer();
    }

    function basculerCreation() {
      creation = !creation;
      if (!creation) { zoneNeuf.innerHTML = ''; return; }
      // La désignation part de ce qui est tapé : neuf fois sur dix, l'ADV a
      // déjà écrit le libellé exact avant de constater qu'il n'existe pas.
      var propose = input.value.trim();
      zoneNeuf.innerHTML =
        '<div class="mrm-neuf">' +
        '  <div class="plein"><label>Désignation</label>' +
        '    <input data-n-des value="' + esc(propose) + '"></div>' +
        '  <div><label>Référence (à défaut : la désignation)</label><input data-n-ref></div>' +
        '  <div><label>Sous-catégorie</label><input data-n-sc></div>' +
        '  <div class="mrm-note">Créée en brouillon : ni prix, ni laize, ni seuil. ' +
        'Elle remonte dans « matières à compléter » de MyStock.</div>' +
        '  <div class="plein" style="display:flex;gap:10px;justify-content:flex-end">' +
        '    <button class="mrm-b" data-n-annuler>Annuler</button>' +
        '    <button class="mrm-b p" data-n-ok>Créer et choisir</button></div>' +
        '</div>';
      var des = zoneNeuf.querySelector('[data-n-des]');
      des.focus(); des.select();
      zoneNeuf.querySelector('[data-n-annuler]').addEventListener('click', basculerCreation);
      zoneNeuf.querySelector('[data-n-ok]').addEventListener('click', creer);
      zoneNeuf.addEventListener('keydown', function (e) {
        if (e.key === 'Enter') { e.preventDefault(); creer(); }
      });
    }

    async function creer() {
      var des = (zoneNeuf.querySelector('[data-n-des]') || {}).value || '';
      var ref = (zoneNeuf.querySelector('[data-n-ref]') || {}).value || '';
      var sc = (zoneNeuf.querySelector('[data-n-sc]') || {}).value || '';
      if (!des.trim()) { alert('Désignation obligatoire.'); return; }
      var btn = zoneNeuf.querySelector('[data-n-ok]');
      if (btn) { btn.disabled = true; btn.textContent = 'Création…'; }
      try {
        var d = await api('/api/stock/matieres/brouillon', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            famille: famille, designation: des.trim(),
            reference: ref.trim(), sous_categorie: sc.trim(),
          }),
        });
        prendre({
          id: d.id, reference: (ref.trim() || des.trim()),
          designation: d.designation || des.trim(),
          sous_categorie: sc.trim() || null, brouillon: !d.existait,
        });
      } catch (e) {
        alert(e.message);
        if (btn) { btn.disabled = false; btn.textContent = 'Créer et choisir'; }
      }
    }

    function auClavier(e) {
      if (e.key === 'Escape') { e.stopPropagation(); fermer(); return; }
      if (creation || !refs.length) return;
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        vise = e.key === 'ArrowDown' ? Math.min(refs.length - 1, vise + 1) : Math.max(0, vise - 1);
        peindre();
        var el = liste.querySelector('[data-i="' + vise + '"]');
        if (el) el.scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'Enter' && vise >= 0) {
        e.preventDefault();
        prendre(refs[vise]);
      }
    }

    fond.querySelector('[data-x]').addEventListener('click', fermer);
    fond.querySelector('[data-annuler]').addEventListener('click', fermer);
    fond.querySelector('[data-creer]').addEventListener('click', basculerCreation);
    input.addEventListener('input', function () {
      clearTimeout(minuteur);
      minuteur = setTimeout(chercher, 250);
    });
    document.addEventListener('keydown', auClavier, true);

    input.value = (o.valeur || '').trim();
    input.focus();
    chercher();
  }

  global.MysRefMatiere = { ouvrir: ouvrir, LIBELLES: LIBELLES };
})(window);

/*
 * MySifa — éditeur de formulaires (MyQualité › Formulaires).
 *
 *   const ed = MysifaFormulaireEditeur.monter(conteneur, schema, {onChange})
 *   ed.schema()   → copie du schéma en cours
 *
 * L'état (le schéma) fait foi : une frappe dans un champ met l'état à jour
 * sans redessiner (le curseur ne saute pas) ; un geste qui change la
 * structure (ajout, suppression, déplacement, changement de type, case qui
 * révèle des champs) redessine les cartes depuis l'état, en rendant le focus
 * au champ qui l'avait.
 *
 * Champs des questions : ceux de app/services/qualite_formulaires.py, que le
 * serveur nettoie de toute façon à l'enregistrement.
 */
(function () {
  'use strict';
  if (window.MysifaFormulaireEditeur) return;

  const esc = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const nid = (p) => p + Math.random().toString(16).slice(2, 10);

  const TYPES = [
    { v: 'text',   l: 'Texte' },
    { v: 'value',  l: 'Nombre' },
    { v: 'choice', l: 'Choix' },
    { v: 'date',   l: 'Date' },
    { v: 'scale',  l: 'Note' },
  ];
  // Boutons d'ajout : « Oui / Non » est un choix préréglé, pas un type.
  const AJOUTS = [
    { cle: 'text', l: 'Texte' },
    { cle: 'value', l: 'Nombre' },
    { cle: 'choice', l: 'Choix' },
    { cle: 'ouinon', l: 'Oui / Non' },
    { cle: 'date', l: 'Date' },
    { cle: 'scale', l: 'Note' },
  ];
  const POINTS_DEFAUT = ['Début de prod', 'Milieu de prod', 'Fin de prod'];

  function nouvelleQuestion(cle) {
    const q = { id: nid('q_'), type: cle === 'ouinon' ? 'choice' : cle, label: '' };
    if (cle === 'choice') { q.responses = ['Option 1', 'Option 2']; q.multi = false; }
    if (cle === 'ouinon') { q.responses = ['Oui', 'Non']; q.multi = false; }
    if (cle === 'scale') { q.min = 1; q.max = 5; }
    return q;
  }

  // Changement de type : libellé, obligation et aide restent, le reste repart
  // des valeurs par défaut du nouveau type.
  function changerType(q, t) {
    const base = nouvelleQuestion(t);
    const garde = { id: q.id, label: q.label, required: q.required, help: q.help };
    Object.keys(q).forEach(k => delete q[k]);
    Object.assign(q, base, garde);
    Object.keys(q).forEach(k => { if (q[k] === undefined) delete q[k]; });
  }

  function injecterCss() {
    if (document.getElementById('mysifa-formulaire-editeur-css')) return;
    const st = document.createElement('style');
    st.id = 'mysifa-formulaire-editeur-css';
    st.textContent = [
      '.fe{display:flex;flex-direction:column;gap:14px}',
      '.fe-sec{border:1px solid var(--border);border-radius:12px;background:var(--card);padding:14px;display:flex;flex-direction:column;gap:10px}',
      '.fe-sec-hd{display:flex;align-items:center;gap:8px}',
      '.fe-sec-num{font-size:11px;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.5px;flex:1}',
      '.fe-in{width:100%;box-sizing:border-box;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px 11px;font-size:13px;font-family:inherit;color:var(--text);transition:border-color .15s}',
      '.fe-in:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}',
      '.fe-in.fe-titre{font-size:15px;font-weight:700}',
      'textarea.fe-in{resize:vertical}',
      '.fe-qs{display:flex;flex-direction:column;gap:8px;min-height:8px}',
      '.fe-q{border:1px solid var(--border);border-radius:10px;background:var(--bg);padding:10px 12px;display:flex;flex-direction:column;gap:8px}',
      '.fe-q.fe-glisse{opacity:.45;border-style:dashed}',
      '.fe-q-hd{display:flex;align-items:center;gap:6px;flex-wrap:wrap}',
      '.fe-q-hd .fe-label{flex:1;min-width:160px;font-weight:600}',
      '.fe-q-hd select{width:auto;flex:0 0 auto}',
      '.fe-poignee{flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;width:22px;height:32px;color:var(--muted);cursor:grab;border-radius:6px}',
      '.fe-poignee:hover{color:var(--accent);background:var(--accent-bg)}',
      '.fe-ico{flex:0 0 auto;display:inline-flex;align-items:center;justify-content:center;min-width:30px;height:30px;padding:0 6px;border:1px solid var(--border);border-radius:8px;background:var(--card);color:var(--text2);cursor:pointer;font-family:inherit;font-size:13px}',
      '.fe-ico:hover:not(:disabled){border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}',
      '.fe-ico:disabled{opacity:.35;cursor:default}',
      '.fe-ico.fe-danger:hover:not(:disabled){border-color:var(--danger);color:var(--danger);background:transparent}',
      '.fe-coche{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text2);cursor:pointer}',
      '.fe-coche input{width:14px;height:14px;accent-color:var(--accent);cursor:pointer;margin:0}',
      '.fe-coche.fe-nc input{accent-color:var(--danger)}',
      '.fe-lbl{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}',
      '.fe-grille{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}',
      '.fe-grille2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}',
      '@media(max-width:560px){.fe-grille{grid-template-columns:repeat(2,minmax(0,1fr))}}',
      '.fe-rep{display:flex;align-items:center;gap:6px}',
      '.fe-rep .fe-in{flex:1;min-width:0;padding:6px 10px}',
      '.fe-ajouts{display:flex;flex-wrap:wrap;gap:6px;align-items:center}',
      '.fe-ajouts-lbl{font-size:12px;color:var(--muted);margin-right:2px}',
      '.fe-btn{display:inline-flex;align-items:center;gap:6px;padding:7px 12px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text2);font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}',
      '.fe-sec .fe-btn{background:var(--bg)}',
      '.fe-btn:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}',
      '.fe-aide{font-size:11px;color:var(--muted)}',
      '.fe-vide{font-size:12px;color:var(--muted);font-style:italic;padding:4px 2px}'
    ].join('\n');
    document.head.appendChild(st);
  }

  const ICO = {
    poignee: '<svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><circle cx="9" cy="6" r="1.6"/><circle cx="15" cy="6" r="1.6"/><circle cx="9" cy="12" r="1.6"/><circle cx="15" cy="12" r="1.6"/><circle cx="9" cy="18" r="1.6"/><circle cx="15" cy="18" r="1.6"/></svg>',
    haut: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m18 15-6-6-6 6"/></svg>',
    bas: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>',
    copie: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>',
    croix: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12"/></svg>',
  };

  function monter(el, schemaInitial, opts) {
    opts = opts || {};
    injecterCss();
    const st = { schema: JSON.parse(JSON.stringify(schemaInitial || {})) };
    if (!Array.isArray(st.schema.sections) || !st.schema.sections.length) {
      st.schema.sections = [{ id: nid('s_'), titre: '', description: '', questions: [] }];
    }
    const secs = () => st.schema.sections;
    const notifier = () => { if (typeof opts.onChange === 'function') opts.onChange(); };

    // ── Rendu ──
    const num = (v) => (v == null || v === '') ? '' : esc(String(v));
    const coche = (k, on, lbl, cls) => '<label class="fe-coche' + (cls ? ' ' + cls : '') + '"><input type="checkbox" data-k="' + k + '"' + (on ? ' checked' : '') + '><span>' + lbl + '</span></label>';

    function corps(q) {
      if (q.type === 'text') {
        return coche('long', q.long, 'Réponse longue (plusieurs lignes)')
          + '<div><div class="fe-lbl">Texte d\'exemple <span style="text-transform:none;letter-spacing:0">(optionnel)</span></div><input class="fe-in" data-k="placeholder" maxlength="80" value="' + esc(q.placeholder || '') + '"></div>';
      }
      if (q.type === 'value') {
        const multi = Array.isArray(q.points) && q.points.length > 1;
        return '<div class="fe-grille">'
          + '<div><div class="fe-lbl">Unité</div><input class="fe-in" data-k="unit" maxlength="20" placeholder="g, mm, °C…" value="' + esc(q.unit || '') + '"></div>'
          + '<div><div class="fe-lbl">Min</div><input class="fe-in" type="number" step="any" data-k="min" value="' + num(q.min) + '"></div>'
          + '<div><div class="fe-lbl">Cible</div><input class="fe-in" type="number" step="any" data-k="target_value" value="' + num(q.target_value) + '"></div>'
          + '<div><div class="fe-lbl">Max</div><input class="fe-in" type="number" step="any" data-k="max" value="' + num(q.max) + '"></div>'
          + '</div>'
          + coche('out_of_range_is_nc', q.out_of_range_is_nc, 'Valeur hors tolérance = <strong style="color:var(--danger)">non-conformité</strong> <span class="fe-aide">(Min ou Max requis)</span>', 'fe-nc')
          + '<div><div class="fe-lbl">Texte d\'exemple <span style="text-transform:none;letter-spacing:0">(optionnel)</span></div><input class="fe-in" data-k="placeholder" maxlength="60" placeholder="Valeur" value="' + esc(q.placeholder || '') + '"></div>'
          + '<div><div class="fe-lbl">Nombre de valeurs</div><select class="fe-in" data-k="mesures">'
          +   '<option value="une"' + (!multi && !q.points_libres ? ' selected' : '') + '>Une seule valeur</option>'
          +   '<option value="fixes"' + (multi && !q.points_libres ? ' selected' : '') + '>Plusieurs valeurs, libellés fixes</option>'
          +   '<option value="libres"' + (q.points_libres ? ' selected' : '') + '>Nombre libre : le destinataire ajoute ses valeurs</option>'
          + '</select></div>'
          + (multi && !q.points_libres ? '<div><input class="fe-in" data-k="points" maxlength="300" value="' + esc(q.points.join(' / ')) + '"><div class="fe-aide" style="margin-top:4px">Un libellé par mesure, séparés par « / » (10 au plus).</div></div>' : '')
          + (q.points_libres ? '<div class="fe-grille" style="grid-template-columns:2fr 1fr 1fr">'
              + '<div><div class="fe-lbl">Libellé d\'une valeur</div><input class="fe-in" data-k="libelle_point" maxlength="30" placeholder="Front" value="' + esc(q.libelle_point || '') + '"></div>'
              + '<div><div class="fe-lbl">Minimum</div><input class="fe-in" type="number" min="1" max="50" step="1" data-k="min_points" value="' + num(q.min_points || 1) + '"></div>'
              + '<div><div class="fe-lbl">Maximum</div><input class="fe-in" type="number" min="1" max="50" step="1" data-k="max_points" value="' + num(q.max_points || 50) + '"></div>'
              + '</div><div class="fe-aide">Le destinataire part du minimum de lignes (« Front 1 »…) et en ajoute autant qu\'il en faut, jusqu\'au maximum.</div>' : '');
      }
      if (q.type === 'choice') {
        const reps = q.responses || [];
        const nc = q.nc_responses || [];
        const lignes = reps.map((r, i) => '<div class="fe-rep">'
          + '<input class="fe-in" data-k="resp" data-i="' + i + '" maxlength="150" value="' + esc(r) + '">'
          + '<label class="fe-coche fe-nc" title="Cette réponse signale une non-conformité"><input type="checkbox" data-k="resp_nc" data-i="' + i + '"' + (nc.indexOf(r) !== -1 ? ' checked' : '') + '><span>NC</span></label>'
          + '<button type="button" class="fe-ico fe-danger" data-act="del-resp" data-i="' + i + '" title="Retirer cette réponse"' + (reps.length <= 1 ? ' disabled' : '') + '>' + ICO.croix + '</button>'
          + '</div>').join('');
        return '<div class="fe-grille2">'
          + '<div><div class="fe-lbl">Réponses</div><select class="fe-in" data-k="multi"><option value="0"' + (!q.multi ? ' selected' : '') + '>Une seule</option><option value="1"' + (q.multi ? ' selected' : '') + '>Plusieurs</option></select></div>'
          + (!q.multi ? '<div><div class="fe-lbl">Affichage</div><select class="fe-in" data-k="display"><option value="chips"' + (q.display !== 'select' ? ' selected' : '') + '>Boutons</option><option value="select"' + (q.display === 'select' ? ' selected' : '') + '>Liste déroulante</option></select></div>' : '<div></div>')
          + '</div>'
          + '<div style="display:flex;flex-direction:column;gap:4px">' + lignes + '</div>'
          + '<div><button type="button" class="fe-btn" data-act="add-resp">+ Ajouter une réponse</button></div>'
          + coche('allow_other', q.allow_other, 'Ajouter « Autre » avec une précision libre')
          + (q.allow_other ? coche('other_is_nc', q.other_is_nc, '« Autre » = <strong style="color:var(--danger)">non-conformité</strong>', 'fe-nc') : '');
      }
      if (q.type === 'scale') {
        const opt = (a, b, cur) => { let h = ''; for (let i = a; i <= b; i++) h += '<option value="' + i + '"' + (i === cur ? ' selected' : '') + '>' + i + '</option>'; return h; };
        return '<div class="fe-grille">'
          + '<div><div class="fe-lbl">De</div><select class="fe-in" data-k="min">' + opt(0, 1, q.min === 0 ? 0 : 1) + '</select></div>'
          + '<div><div class="fe-lbl">À</div><select class="fe-in" data-k="max">' + opt(2, 10, q.max || 5) + '</select></div>'
          + '<div><div class="fe-lbl">Libellé bas</div><input class="fe-in" data-k="label_min" maxlength="40" placeholder="Pas du tout" value="' + esc(q.label_min || '') + '"></div>'
          + '<div><div class="fe-lbl">Libellé haut</div><input class="fe-in" data-k="label_max" maxlength="40" placeholder="Tout à fait" value="' + esc(q.label_max || '') + '"></div>'
          + '</div>';
      }
      return '';
    }

    function carteQuestion(q, si, qi, nbQ) {
      const types = TYPES.map(t => '<option value="' + t.v + '"' + (t.v === q.type ? ' selected' : '') + '>' + t.l + '</option>').join('');
      return '<div class="fe-q" data-s="' + si + '" data-q="' + qi + '">'
        + '<div class="fe-q-hd">'
        +   '<span class="fe-poignee" data-act="armer" title="Glisser pour déplacer">' + ICO.poignee + '</span>'
        +   '<input class="fe-in fe-label" data-k="label" maxlength="300" placeholder="Question" value="' + esc(q.label || '') + '">'
        +   '<select class="fe-in" data-k="type" aria-label="Type de question">' + types + '</select>'
        +   '<button type="button" class="fe-ico" data-act="up-q" title="Monter"' + (si === 0 && qi === 0 ? ' disabled' : '') + '>' + ICO.haut + '</button>'
        +   '<button type="button" class="fe-ico" data-act="down-q" title="Descendre"' + (si === secs().length - 1 && qi === nbQ - 1 ? ' disabled' : '') + '>' + ICO.bas + '</button>'
        +   '<button type="button" class="fe-ico" data-act="dup-q" title="Dupliquer">' + ICO.copie + '</button>'
        +   '<button type="button" class="fe-ico fe-danger" data-act="del-q" title="Supprimer la question">' + ICO.croix + '</button>'
        + '</div>'
        + coche('required', q.required, 'Réponse obligatoire', 'fe-nc')
        + corps(q)
        + '<div><div class="fe-lbl">Aide / méthode <span style="text-transform:none;letter-spacing:0">(optionnel)</span></div><textarea class="fe-in" data-k="help" rows="2" maxlength="600" placeholder="Affichée sous la question.">' + esc(q.help || '') + '</textarea></div>'
        + '</div>';
    }

    function carteSection(s, si) {
      const n = secs().length;
      const qs = s.questions || [];
      return '<div class="fe-sec" data-s="' + si + '">'
        + '<div class="fe-sec-hd"><span class="fe-sec-num">Section ' + (si + 1) + ' / ' + n + '</span>'
        +   '<button type="button" class="fe-ico" data-act="up-s" title="Monter la section"' + (si === 0 ? ' disabled' : '') + '>' + ICO.haut + '</button>'
        +   '<button type="button" class="fe-ico" data-act="down-s" title="Descendre la section"' + (si === n - 1 ? ' disabled' : '') + '>' + ICO.bas + '</button>'
        +   '<button type="button" class="fe-ico fe-danger" data-act="del-s" title="Supprimer la section"' + (n <= 1 ? ' disabled' : '') + '>' + ICO.croix + '</button>'
        + '</div>'
        + '<input class="fe-in fe-titre" data-k="titre" maxlength="200" placeholder="Titre de la section (optionnel)" value="' + esc(s.titre || '') + '">'
        + '<textarea class="fe-in" data-k="description" rows="1" maxlength="1000" placeholder="Description (optionnel)">' + esc(s.description || '') + '</textarea>'
        + '<div class="fe-qs" data-s="' + si + '">'
        +   (qs.length ? qs.map((q, qi) => carteQuestion(q, si, qi, qs.length)).join('') : '<div class="fe-vide">Aucune question dans cette section.</div>')
        + '</div>'
        + '<div class="fe-ajouts"><span class="fe-ajouts-lbl">Ajouter :</span>'
        +   AJOUTS.map(a => '<button type="button" class="fe-btn" data-act="add-q" data-t="' + a.cle + '">' + a.l + '</button>').join('')
        + '</div>'
        + '</div>';
    }

    function dessiner() {
      // Rend le focus et le curseur au champ qui les avait.
      const ae = document.activeElement;
      let cle = null, pos = null;
      if (ae && el.contains(ae) && ae.getAttribute('data-k')) {
        const c = ae.closest('[data-q]') || ae.closest('[data-s]');
        cle = [c && c.getAttribute('data-s'), c && c.getAttribute('data-q'), ae.getAttribute('data-k'), ae.getAttribute('data-i')];
        try { pos = [ae.selectionStart, ae.selectionEnd]; } catch (e) {}
      }
      el.innerHTML = '<div class="fe">' + secs().map(carteSection).join('')
        + '<div><button type="button" class="fe-btn" data-act="add-s">+ Ajouter une section</button></div></div>';
      if (cle) {
        const sel = (cle[1] != null ? '.fe-q[data-s="' + cle[0] + '"][data-q="' + cle[1] + '"]' : '.fe-sec[data-s="' + cle[0] + '"]')
          + ' [data-k="' + cle[2] + '"]' + (cle[3] != null ? '[data-i="' + cle[3] + '"]' : '');
        const cible = el.querySelector(sel);
        if (cible) { cible.focus(); if (pos && pos[0] != null) { try { cible.setSelectionRange(pos[0], pos[1]); } catch (e) {} } }
      }
    }

    // ── Saisie ──
    function cibleDe(t) {
      const qEl = t.closest('.fe-q');
      const sEl = t.closest('.fe-sec');
      const s = sEl ? secs()[+sEl.getAttribute('data-s')] : null;
      const q = (qEl && s) ? s.questions[+qEl.getAttribute('data-q')] : null;
      return { s, q, si: sEl ? +sEl.getAttribute('data-s') : -1, qi: qEl ? +qEl.getAttribute('data-q') : -1 };
    }
    const nombre = (v) => { const n = parseFloat(String(v).replace(',', '.')); return isFinite(n) ? n : null; };

    function surSaisie(ev, structurel) {
      const t = ev.target;
      const k = t.getAttribute && t.getAttribute('data-k');
      if (!k) return;
      const { s, q } = cibleDe(t);
      if (!q) {
        if (s && (k === 'titre' || k === 'description')) { s[k] = t.value; notifier(); }
        return;
      }
      let redessiner = false;
      const v = t.type === 'checkbox' ? t.checked : t.value;
      if (k === 'type') { changerType(q, v); redessiner = true; }
      else if (['min', 'max', 'target_value'].indexOf(k) !== -1) {
        const n = q.type === 'scale' ? parseInt(v, 10) : nombre(v);
        if (n === null || isNaN(n)) delete q[k]; else q[k] = n;
      }
      else if (k === 'multi') { q.multi = v === '1'; if (q.multi) delete q.display; redessiner = true; }
      else if (k === 'display') { if (v === 'select') q.display = 'select'; else delete q.display; }
      else if (k === 'mesures') {
        delete q.points_libres; delete q.libelle_point; delete q.min_points; delete q.max_points;
        if (v === 'fixes') q.points = (q.points && q.points.length > 1) ? q.points : POINTS_DEFAUT.slice();
        else delete q.points;
        if (v === 'libres') { q.points_libres = true; q.min_points = 1; q.max_points = 50; }
        redessiner = true;
      }
      else if (k === 'min_points' || k === 'max_points') {
        const n = parseInt(v, 10);
        if (!isNaN(n)) q[k] = Math.max(1, Math.min(50, n));
      }
      else if (k === 'points') { q.points = String(v).split('/').map(x => x.trim()).filter(Boolean).slice(0, 10); }
      else if (k === 'resp') {
        const i = +t.getAttribute('data-i');
        const ancien = q.responses[i];
        q.responses[i] = v;
        if (q.nc_responses) q.nc_responses = q.nc_responses.map(r => r === ancien ? v : r);
      }
      else if (k === 'resp_nc') {
        const r = q.responses[+t.getAttribute('data-i')];
        const nc = (q.nc_responses || []).filter(x => x !== r);
        if (v) nc.push(r);
        if (nc.length) q.nc_responses = nc; else delete q.nc_responses;
      }
      else if (typeof v === 'boolean') {
        if (v) q[k] = true; else delete q[k];
        if (k === 'allow_other' && !v) delete q.other_is_nc;
        redessiner = (k === 'allow_other');
      }
      else { if (v === '') delete q[k]; else q[k] = v; }
      if (redessiner && structurel) dessiner();
      notifier();
    }
    el.addEventListener('input', (ev) => { if (ev.target.tagName !== 'SELECT' && ev.target.type !== 'checkbox') surSaisie(ev, false); });
    el.addEventListener('change', (ev) => { if (ev.target.tagName === 'SELECT' || ev.target.type === 'checkbox') surSaisie(ev, true); });

    // ── Gestes ──
    function deplacerQuestion(si, qi, sens) {
      const liste = secs()[si].questions;
      const q = liste[qi];
      if (sens < 0) {
        if (qi > 0) { liste.splice(qi, 1); liste.splice(qi - 1, 0, q); }
        else if (si > 0) { liste.splice(qi, 1); secs()[si - 1].questions.push(q); }
      } else {
        if (qi < liste.length - 1) { liste.splice(qi, 1); liste.splice(qi + 1, 0, q); }
        else if (si < secs().length - 1) { liste.splice(qi, 1); secs()[si + 1].questions.unshift(q); }
      }
    }
    el.addEventListener('click', (ev) => {
      const b = ev.target.closest('[data-act]');
      if (!b || !el.contains(b) || b.disabled) return;
      const act = b.getAttribute('data-act');
      if (act === 'armer') return;
      const { s, q, si, qi } = cibleDe(b);
      let focusLabel = null;
      if (act === 'add-q' && s) {
        const nq = nouvelleQuestion(b.getAttribute('data-t'));
        s.questions.push(nq); focusLabel = [si, s.questions.length - 1];
      } else if (act === 'del-q' && q) {
        if ((q.label || '').trim() && !confirm('Supprimer la question « ' + q.label + ' » ?')) return;
        s.questions.splice(qi, 1);
      } else if (act === 'dup-q' && q) {
        const c = JSON.parse(JSON.stringify(q)); c.id = nid('q_');
        if (c.label) c.label = (c.label + ' (copie)').slice(0, 300);
        s.questions.splice(qi + 1, 0, c); focusLabel = [si, qi + 1];
      } else if (act === 'up-q' && q) deplacerQuestion(si, qi, -1);
      else if (act === 'down-q' && q) deplacerQuestion(si, qi, 1);
      else if (act === 'add-resp' && q) { q.responses.push('Option ' + (q.responses.length + 1)); }
      else if (act === 'del-resp' && q) {
        const r = q.responses.splice(+b.getAttribute('data-i'), 1)[0];
        if (q.nc_responses) { q.nc_responses = q.nc_responses.filter(x => x !== r); if (!q.nc_responses.length) delete q.nc_responses; }
      }
      else if (act === 'add-s') { secs().push({ id: nid('s_'), titre: '', description: '', questions: [] }); }
      else if (act === 'del-s' && s) {
        if (s.questions.length && !confirm('Supprimer la section ' + (si + 1) + ' et ses ' + s.questions.length + ' question(s) ?')) return;
        secs().splice(si, 1);
      }
      else if (act === 'up-s' && si > 0) { const x = secs().splice(si, 1)[0]; secs().splice(si - 1, 0, x); }
      else if (act === 'down-s' && si < secs().length - 1) { const x = secs().splice(si, 1)[0]; secs().splice(si + 1, 0, x); }
      else return;
      dessiner();
      notifier();
      if (focusLabel) el.querySelector('.fe-q[data-s="' + focusLabel[0] + '"][data-q="' + focusLabel[1] + '"] .fe-label')?.focus();
    });

    // ── Glisser depuis la poignée (entre sections aussi) ──
    let glisse = null;
    el.addEventListener('mousedown', (ev) => {
      const p = ev.target.closest('.fe-poignee');
      if (p) p.closest('.fe-q').setAttribute('draggable', 'true');
    });
    el.addEventListener('mouseup', (ev) => {
      const p = ev.target.closest('.fe-poignee');
      if (p && !glisse) p.closest('.fe-q').removeAttribute('draggable');
    });
    el.addEventListener('dragstart', (ev) => {
      const c = ev.target.closest && ev.target.closest('.fe-q');
      if (!c || c.getAttribute('draggable') !== 'true') return;
      glisse = c; c.classList.add('fe-glisse');
      try { ev.dataTransfer.effectAllowed = 'move'; ev.dataTransfer.setData('text/plain', ''); } catch (e) {}
    });
    el.addEventListener('dragover', (ev) => {
      if (!glisse) return;
      const liste = ev.target.closest && ev.target.closest('.fe-qs');
      if (!liste) return;
      ev.preventDefault();
      const cartes = Array.from(liste.querySelectorAll(':scope > .fe-q')).filter(c => c !== glisse);
      const avant = cartes.find(c => { const r = c.getBoundingClientRect(); return ev.clientY < r.top + r.height / 2; });
      liste.querySelector(':scope > .fe-vide')?.remove();
      if (avant) { if (glisse.nextElementSibling !== avant) liste.insertBefore(glisse, avant); }
      else if (liste.lastElementChild !== glisse) liste.appendChild(glisse);
    });
    el.addEventListener('drop', (ev) => { if (glisse) ev.preventDefault(); });
    el.addEventListener('dragend', () => {
      if (!glisse) return;
      glisse.classList.remove('fe-glisse');
      glisse.removeAttribute('draggable');
      glisse = null;
      // Le DOM porte le nouvel ordre : on le recopie dans l'état.
      const anciennes = secs().map(s => s.questions.slice());
      el.querySelectorAll('.fe-qs').forEach(liste => {
        const si = +liste.getAttribute('data-s');
        secs()[si].questions = Array.from(liste.querySelectorAll(':scope > .fe-q'))
          .map(c => anciennes[+c.getAttribute('data-s')][+c.getAttribute('data-q')]).filter(Boolean);
      });
      dessiner();
      notifier();
    });

    dessiner();
    return {
      schema: () => JSON.parse(JSON.stringify(st.schema)),
    };
  }

  window.MysifaFormulaireEditeur = { monter: monter };
})();

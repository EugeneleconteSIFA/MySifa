/*
 * MySifa — moteur de rendu des formulaires (MyQualité › Formulaires).
 *
 * Dessine un formulaire à remplir à partir de son schéma, lit les réponses et
 * dit ce qui manque. Un seul rendu pour tous les usages : aperçu de l'éditeur
 * aujourd'hui, portail public des destinataires et questionnaire des alertes
 * maintenance ensuite. Structure du schéma : app/services/qualite_formulaires.py.
 *
 *   MysifaFormulaire.rendre(schema, conteneur, {onChange})
 *   MysifaFormulaire.lire(conteneur)       → {id_question: réponse}
 *   MysifaFormulaire.manquantes(conteneur) → [id_question obligatoire sans réponse]
 *
 * Réponses : text/date → chaîne ; value → nombre, ou liste de nombres (null
 * pour une mesure vide) quand la question a plusieurs mesures ; choice → liste
 * de libellés, « Autre » compris, avec la précision sous `<id>_other` ;
 * scale → nombre.
 *
 * Aucune dépendance : tout est échappé ici, aucune donnée n'entre en innerHTML
 * sans passer par esc().
 */
(function () {
  'use strict';
  if (window.MysifaFormulaire) return;

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  const num = (x) => { const n = parseFloat(String(x == null ? '' : x).replace(',', '.')); return isFinite(n) ? n : null; };
  const fmt = (n) => String(n).replace('.', ',');

  function injecterCss() {
    if (document.getElementById('mysifa-formulaire-css')) return;
    const st = document.createElement('style');
    st.id = 'mysifa-formulaire-css';
    st.textContent = [
      '.mf{display:flex;flex-direction:column;gap:14px;font-family:inherit;color:var(--text)}',
      '.mf-sec{display:flex;flex-direction:column;gap:14px}',
      '.mf-sec+.mf-sec{border-top:1px solid var(--border);padding-top:14px}',
      '.mf-sec-titre{font-size:15px;font-weight:700;margin:0}',
      '.mf-sec-desc{font-size:13px;color:var(--text2);margin:-8px 0 0;white-space:pre-wrap;line-height:1.45}',
      '.mf-q{display:flex;flex-direction:column;gap:6px}',
      '.mf-q-label{font-size:14px;font-weight:600;line-height:1.35}',
      '.mf-q-label .mf-req{color:var(--danger);margin-left:3px}',
      '.mf-q-aide{font-size:12px;color:var(--muted);white-space:pre-wrap;line-height:1.4;margin-top:-2px}',
      '.mf-in{width:100%;box-sizing:border-box;background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px 11px;font-size:13px;font-family:inherit;color:var(--text);transition:border-color .15s}',
      '.mf-in:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}',
      'textarea.mf-in{resize:vertical;min-height:70px}',
      '.mf-ligne{display:flex;align-items:center;gap:8px}',
      '.mf-ligne .mf-in{flex:1;min-width:0}',
      '.mf-mesure{flex:0 0 110px;font-size:12px;font-weight:600;color:var(--text2)}',
      '.mf-unite{font-size:12px;color:var(--text2);font-weight:500}',
      '.mf-ecart{font-size:11px;font-weight:600;color:var(--muted);min-width:52px;text-align:right;font-variant-numeric:tabular-nums}',
      '.mf-indic{font-size:11px;color:var(--muted)}',
      '.mf-hors{border-color:var(--danger) !important;color:var(--danger)}',
      '.mf-chips{display:flex;flex-wrap:wrap;gap:6px}',
      '.mf-chip{position:relative;display:inline-flex;align-items:center;padding:6px 12px;border-radius:999px;border:1.5px solid var(--border);background:var(--card);font-size:13px;cursor:pointer;user-select:none}',
      '.mf-chip input{position:absolute;opacity:0;width:0;height:0;pointer-events:none}',
      '.mf-chip:has(input:checked){background:var(--accent);border-color:var(--accent);color:white}',
      '.mf-chip:has(input:focus-visible){outline:2px solid var(--accent);outline-offset:2px}',
      '.mf-echelle{display:flex;flex-wrap:wrap;gap:6px;align-items:center}',
      '.mf-echelle .mf-chip{min-width:38px;justify-content:center}',
      '.mf-echelle-lbl{font-size:11px;color:var(--muted)}',
      '.mf-vide{font-size:13px;color:var(--muted);font-style:italic}'
    ].join('\n');
    document.head.appendChild(st);
  }

  function libelle(q) {
    return '<div class="mf-q-label">' + esc(q.label || 'Question sans libellé')
      + (q.required ? '<span class="mf-req" title="Réponse obligatoire">*</span>' : '') + '</div>'
      + (q.help ? '<div class="mf-q-aide">' + esc(q.help) + '</div>' : '');
  }

  function champValeur(q) {
    const pts = (Array.isArray(q.points) && q.points.length > 1) ? q.points : [null];
    const ph = esc(q.placeholder || 'Valeur');
    const unite = q.unit ? '<span class="mf-unite">' + esc(q.unit) + '</span>' : '';
    const ecart = q.target_value != null ? '<span class="mf-ecart"></span>' : '';
    const lignes = pts.map((pl, k) => '<div class="mf-ligne">'
      + (pl != null ? '<span class="mf-mesure">' + esc(pl) + '</span>' : '')
      + '<input type="number" step="any" inputmode="decimal" class="mf-in mf-val" data-k="' + k + '" placeholder="' + ph + '">'
      + unite + ecart + '</div>').join('');
    const indic = [];
    if (q.min != null || q.max != null) indic.push('Tolérance : ' + (q.min != null ? fmt(q.min) : '−∞') + ' à ' + (q.max != null ? fmt(q.max) : '+∞'));
    if (q.target_value != null) indic.push('Cible : ' + fmt(q.target_value));
    return lignes + (indic.length ? '<div class="mf-indic">' + esc(indic.join(' · ') + (q.unit ? ' ' + q.unit : '')) + '</div>' : '');
  }

  function champChoix(q) {
    const reps = Array.isArray(q.responses) ? q.responses : [];
    if (q.display === 'select' && !q.multi) {
      return '<select class="mf-in mf-select"><option value="">Choisir…</option>'
        + reps.map(r => '<option value="' + esc(r) + '">' + esc(r) + '</option>').join('')
        + (q.allow_other ? '<option value="__autre">Autre</option>' : '') + '</select>'
        + (q.allow_other ? '<input type="text" class="mf-in mf-autre" maxlength="500" placeholder="Préciser" style="display:none">' : '');
    }
    const type = q.multi ? 'checkbox' : 'radio';
    const nom = 'mf-' + q.id;
    return '<div class="mf-chips">'
      + reps.map(r => '<label class="mf-chip"><input type="' + type + '" name="' + esc(nom) + '" class="mf-opt" value="' + esc(r) + '"><span>' + esc(r) + '</span></label>').join('')
      + (q.allow_other ? '<label class="mf-chip"><input type="' + type + '" name="' + esc(nom) + '" class="mf-opt mf-opt-autre" value="Autre"><span>Autre</span></label>' : '')
      + '</div>'
      + (q.allow_other ? '<input type="text" class="mf-in mf-autre" maxlength="500" placeholder="Préciser" style="display:none">' : '');
  }

  function champEchelle(q) {
    const bas = q.min === 0 ? 0 : 1;
    const haut = Math.max(2, Math.min(10, parseInt(q.max, 10) || 5));
    let h = '<div class="mf-echelle">';
    if (q.label_min) h += '<span class="mf-echelle-lbl">' + esc(q.label_min) + '</span>';
    for (let i = bas; i <= haut; i++) {
      h += '<label class="mf-chip"><input type="radio" name="' + esc('mf-' + q.id) + '" class="mf-opt" value="' + i + '"><span>' + i + '</span></label>';
    }
    if (q.label_max) h += '<span class="mf-echelle-lbl">' + esc(q.label_max) + '</span>';
    return h + '</div>';
  }

  function question(q) {
    let champ;
    if (q.type === 'value') champ = champValeur(q);
    else if (q.type === 'choice') champ = champChoix(q);
    else if (q.type === 'scale') champ = champEchelle(q);
    else if (q.type === 'date') champ = '<input type="date" class="mf-in mf-texte" style="max-width:200px">';
    else if (q.long) champ = '<textarea class="mf-in mf-texte" rows="3" maxlength="5000" placeholder="' + esc(q.placeholder || '') + '"></textarea>';
    else champ = '<input type="text" class="mf-in mf-texte" maxlength="1000" placeholder="' + esc(q.placeholder || '') + '">';
    return '<div class="mf-q" data-qid="' + esc(q.id) + '" data-type="' + esc(q.type) + '"' + (q.required ? ' data-req="1"' : '') + '>'
      + libelle(q) + champ + '</div>';
  }

  function rendre(schema, el, opts) {
    if (!el) return;
    opts = opts || {};
    injecterCss();
    const sections = (schema && Array.isArray(schema.sections)) ? schema.sections : [];
    const parId = {};
    const html = sections.map(s => {
      const qs = (s.questions || []);
      qs.forEach(q => { parId[q.id] = q; });
      if (!qs.length && !s.titre) return '';
      return '<section class="mf-sec">'
        + (s.titre ? '<h3 class="mf-sec-titre">' + esc(s.titre) + '</h3>' : '')
        + (s.description ? '<p class="mf-sec-desc">' + esc(s.description) + '</p>' : '')
        + qs.map(question).join('')
        + '</section>';
    }).join('');
    el.innerHTML = '<div class="mf">' + (html || '<div class="mf-vide">Aucune question pour l\'instant.</div>') + '</div>';
    el._mfQuestions = parId;
    const surSaisie = (ev) => {
      const qEl = ev.target.closest && ev.target.closest('.mf-q');
      if (qEl) maj(qEl, parId[qEl.getAttribute('data-qid')]);
      if (typeof opts.onChange === 'function') opts.onChange();
    };
    el.oninput = surSaisie;
    el.onchange = surSaisie;
  }

  // Écart à la cible, mesure hors tolérance, champ « Autre » : recalculés
  // à chaque saisie sur la question touchée.
  function maj(qEl, q) {
    if (!q) return;
    if (q.type === 'value') {
      qEl.querySelectorAll('.mf-val').forEach(inp => {
        const n = num(inp.value);
        const hors = n !== null && ((q.min != null && n < q.min) || (q.max != null && n > q.max));
        inp.classList.toggle('mf-hors', hors);
        const ec = inp.parentElement.querySelector('.mf-ecart');
        if (ec) {
          if (n === null || q.target_value == null) ec.textContent = '';
          else {
            const e = Math.round((n - q.target_value) * 1000) / 1000;
            ec.textContent = 'écart ' + (e > 0 ? '+' : (e < 0 ? '−' : '')) + fmt(Math.abs(e));
          }
          ec.style.color = hors ? 'var(--danger)' : '';
        }
      });
    } else if (q.type === 'choice' && q.allow_other) {
      const autre = qEl.querySelector('.mf-autre');
      const sel = qEl.querySelector('.mf-select');
      const on = sel ? sel.value === '__autre' : !!qEl.querySelector('.mf-opt-autre:checked');
      if (autre) { autre.style.display = on ? '' : 'none'; if (!on) autre.value = ''; }
    }
  }

  function reponseDe(qEl, q) {
    if (!q) return undefined;
    if (q.type === 'value') {
      const vals = Array.from(qEl.querySelectorAll('.mf-val')).map(i => num(i.value));
      if (vals.length > 1) return vals.some(v => v !== null) ? vals : undefined;
      return vals[0] !== null ? vals[0] : undefined;
    }
    if (q.type === 'choice') {
      const sel = qEl.querySelector('.mf-select');
      if (sel) return sel.value ? [sel.value === '__autre' ? 'Autre' : sel.value] : undefined;
      const c = Array.from(qEl.querySelectorAll('.mf-opt:checked')).map(i => i.value);
      return c.length ? c : undefined;
    }
    if (q.type === 'scale') {
      const c = qEl.querySelector('.mf-opt:checked');
      return c ? Number(c.value) : undefined;
    }
    const t = (qEl.querySelector('.mf-texte')?.value || '').trim();
    return t || undefined;
  }

  function lire(el) {
    const out = {};
    const parId = (el && el._mfQuestions) || {};
    (el ? el.querySelectorAll('.mf-q') : []).forEach(qEl => {
      const id = qEl.getAttribute('data-qid');
      const r = reponseDe(qEl, parId[id]);
      if (r !== undefined) out[id] = r;
      const autre = (qEl.querySelector('.mf-autre')?.value || '').trim();
      if (autre) out[id + '_other'] = autre.slice(0, 500);
    });
    return out;
  }

  function manquantes(el) {
    const parId = (el && el._mfQuestions) || {};
    const out = [];
    (el ? el.querySelectorAll('.mf-q[data-req="1"]') : []).forEach(qEl => {
      const id = qEl.getAttribute('data-qid');
      const q = parId[id];
      const r = reponseDe(qEl, q);
      // Plusieurs mesures : une question obligatoire attend toutes les mesures.
      if (r === undefined || (Array.isArray(r) && q && q.type === 'value' && r.some(v => v === null))) out.push(id);
    });
    return out;
  }

  window.MysifaFormulaire = { rendre: rendre, lire: lire, manquantes: manquantes, esc: esc };
})();

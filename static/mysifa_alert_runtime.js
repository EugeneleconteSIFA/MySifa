/* MySifa — Runtime des alertes maintenance côté opérateur.
 *
 * Polleur 15 s qui interroge /api/maintenance/alerts/active et affiche les
 * alertes retournées avec le même style que le mode test (.ta-sim, .ta-chip).
 * À la validation, POST sur /api/maintenance/alerts/{id}/ack puis fermeture.
 *
 * Usage : <script src="/static/mysifa_alert_runtime.js"></script>
 *         <script>MysifaAlerts.start();</script>
 */
(function() {
  'use strict';

  // ── Injection CSS (les mêmes règles que /settings, pour que /prod soit autonome) ──
  (function injectAlertCSS() {
    if (document.getElementById('mysifa-alert-runtime-css')) return;
    const style = document.createElement('style');
    style.id = 'mysifa-alert-runtime-css';
    style.textContent = [
      /* v2.3.20 — CSS de positionnement réécrit depuis zéro. Approche simple :
         .ta-sim-alert est en position:fixed (dans le viewport), pas dans un
         parent flex/absolute. Toutes les propriétés critiques ont !important
         pour bloquer tout override futur. */

      /* CONTAINER : plein viewport transparent, capture les clics uniquement en mode bloquant */
      '.ta-sim{position:fixed;inset:0;z-index:2000;pointer-events:none;box-sizing:border-box}',
      '.ta-sim.ta-blocking{background:rgba(0,0,0,.45);pointer-events:auto;animation:taSimFade .15s ease-out}',
      /* v2.3.26 : les alertes bloquantes ne peuvent pas être réduites — bouton "-" masqué */
      '.ta-sim.ta-blocking .ta-sim-min{display:none !important}',

      /* ALERTE : positionnée dans le viewport (fixed), indépendante du container */
      '.ta-sim-alert{position:fixed !important;background:var(--card);border:2px solid var(--accent);border-radius:12px;box-shadow:0 16px 48px rgba(0,0,0,.5);padding:16px 18px;max-height:calc(100vh - 40px);overflow-y:auto;animation:taSimSlide .2s ease-out;pointer-events:auto;box-sizing:border-box;transition:width .18s ease,height .18s ease,padding .18s ease,border-radius .18s ease}',

      /* TAILLES : largeur fixe avec fallback viewport */
      '.ta-sz-small .ta-sim-alert{width:260px !important;max-width:calc(100vw - 40px) !important}',
      '.ta-sz-medium .ta-sim-alert{width:340px !important;max-width:calc(100vw - 40px) !important}',
      '.ta-sz-large .ta-sim-alert{width:440px !important;max-width:calc(100vw - 40px) !important}',

      /* PLACEMENTS : ancrage direct dans le viewport avec reset explicite des autres axes */
      '.ta-sim.ta-pl-top-right .ta-sim-alert{top:20px !important;right:20px !important;left:auto !important;bottom:auto !important;transform:none !important}',
      '.ta-sim.ta-pl-center .ta-sim-alert{top:50% !important;left:50% !important;right:auto !important;bottom:auto !important;transform:translate(-50%,-50%) !important}',

      /* Titre et boutons */
      '.ta-sim-title{font-size:18px;font-weight:700;color:var(--text);margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid var(--accent);line-height:1.3;letter-spacing:-0.01em;cursor:grab;user-select:none}',
      '.ta-sim-title.ta-dragging{cursor:grabbing}',
      '.ta-sim-actions{display:flex;gap:6px;margin-top:10px}',
      '.ta-sim-btn{flex:1;padding:9px;border-radius:8px;font-size:13px;font-weight:600;border:none;cursor:pointer;font-family:inherit;background:var(--accent);color:#fff}',
      '.ta-sim-btn:hover{filter:brightness(1.05)}',

      /* Bouton minimize (en haut-droite de l'alerte) */
      '.ta-sim-min{position:absolute;top:10px;right:12px;background:transparent;border:none;padding:6px;cursor:pointer;color:var(--muted);border-radius:6px;line-height:0;transition:background .12s,color .12s;z-index:1}',
      '.ta-sim-min:hover{background:var(--bg);color:var(--text)}',
      '.ta-sim-restore-icon{display:none;align-items:center;justify-content:center;width:100%;height:100%;color:#fff}',

      /* État minimize : bulle 56x56 (override le placement/taille via ta-minimized qui est plus spécifique) */
      '.ta-sim-alert.ta-minimized{width:56px !important;height:56px !important;min-width:0;max-width:56px !important;padding:0 !important;border-radius:50% !important;cursor:pointer;background:var(--accent);border-color:var(--accent);overflow:hidden;display:flex;align-items:center;justify-content:center;box-shadow:0 6px 20px rgba(0,0,0,.4);animation:taMinPulse 1.8s ease-in-out infinite}',
      '.ta-sim-alert.ta-minimized>*:not(.ta-sim-restore-icon){display:none !important}',
      '.ta-sim-alert.ta-minimized .ta-sim-restore-icon{display:flex}',
      '.ta-sim-alert.ta-minimized:hover{filter:brightness(1.08);animation:none}',

      /* Chips (réponses) */
      '.ta-chip{display:inline-flex;align-items:center;padding:5px 11px;border-radius:999px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:12px;font-weight:500;cursor:pointer;user-select:none;transition:background .12s ease,color .12s ease,border-color .12s ease;font-family:inherit;line-height:1.2}',
      '.ta-chip input{position:absolute;opacity:0;width:0;height:0;pointer-events:none}',
      '.ta-chip:hover{border-color:var(--accent)}',
      '.ta-chip:has(input:checked){background:var(--accent);color:#fff;border-color:var(--accent)}',
      '.ta-chip span{white-space:nowrap}',
      '.ta-chip-other{border-style:dashed}',

      /* Animations */
      '@keyframes taSimFade{from{opacity:0}to{opacity:1}}',
      '@keyframes taSimSlide{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}',
      '@keyframes taMinPulse{0%,100%{box-shadow:0 6px 20px rgba(0,0,0,.4)}50%{box-shadow:0 6px 20px rgba(0,0,0,.4),0 0 0 10px rgba(34,211,238,.28)}}',

      /* Mobile : marges réduites, largeur presque pleine */
      '@media(max-width:600px){.ta-sim-alert{padding:14px}.ta-sz-small .ta-sim-alert,.ta-sz-medium .ta-sim-alert,.ta-sz-large .ta-sim-alert{width:calc(100vw - 24px) !important;max-width:calc(100vw - 24px) !important}.ta-sim.ta-pl-top-right .ta-sim-alert{top:12px !important;right:12px !important}}',

      /* Bouton "Quitter le test" du simulateur — fixed indépendant */
      '.ta-sim-exit{position:fixed;top:12px;left:12px;z-index:2100;background:rgba(0,0,0,.7);color:#fff;border:none;padding:6px 12px;border-radius:6px;font-size:12px;font-family:inherit;cursor:pointer;pointer-events:auto}',
      '.ta-sim-exit:hover{background:rgba(0,0,0,.9)}'
    ].join('\n');
    document.head.appendChild(style);
  })();


  const POLL_INTERVAL_MS = 15000;
  const FETCH_OPTS = { credentials: 'same-origin' };

  let _settings = { placement: 'top-right', size: 'medium', block_production: false, stack_mode: 'queue', min_gap_minutes: 5 };
  let _displayed = new Map();  // v2.2.66 : id → wrap DOM element (pour pouvoir fermer côté client si backend a ack en silence)
  // v2.3.6 : file d'attente de resolvers pour waitForBlockingAck()
  let _blockingAckResolvers = [];  // [{resolve, reject}]
  // v2.3.9 : Set des IDs d'alertes affichées via showBlockingAlerts. Ces alertes
  // ne sont PAS dans /alerts/active (retirées en v2.2.89 pour after_calage),
  // donc le poll cleanup les supprimerait à chaque itération sans ce flag.
  let _displayedBlocking = new Set();
  let _pollTimer = null;
  let _started = false;

  function _esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function _attr(s) { return _esc(s); }

  function _toast(msg, isErr) {
    // v2.3.32 : préfère le showToast de la page (fabrication_page.py) qui
    // utilise le style vert "Saisie enregistrée" en bas au centre. Fallback
    // vers le toast global html.py (bottom-right) si le page-level manque.
    if (typeof window.showToast === 'function') {
      try { return window.showToast(msg, isErr ? 'danger' : 'success'); } catch(_) {}
    }
    if (typeof window.toast === 'function') return window.toast(msg, !!isErr);
    if (window.console) window.console.log('[alerts]', msg);
  }

  function _stripAutoPrefix(nom) {
    // Retire le préfixe "Contrôle : XX – " des alertes auto-générées pour
    // l'affichage opérateur — on garde le nom canonique en base mais on
    // n'expose que le libellé du code à l'opérateur.
    if (!nom) return '';
    return String(nom).replace(/^Contr[oôö]le\s*:\s*\d+\s*[–\-]\s*/i, '');
  }

  function _triggerLabel(t) {
    if (!t || !t.type) return 'Manuel';
    if (t.type === 'manual')   return 'Manuel — déclenché par l\'opérateur';
    if (t.type === 'periodic') {
      const m = (t.interval_minutes != null) ? t.interval_minutes
                : (t.interval_hours != null ? Math.round(t.interval_hours * 60) : '?');
      return 'Périodique — toutes les ' + m + ' min';
    }
    if (t.type === 'calendar') return 'Calendaire — ' + (t.time || '??:??');
    if (t.type === 'event')    return 'Événementiel';
    return String(t.type);
  }

  async function _loadSettings() {
    try {
      const r = await fetch('/api/maintenance/alert-settings', FETCH_OPTS);
      if (!r.ok) return;
      const s = await r.json();
      let placement = s.placement || 'center';
      if (placement !== 'center' && placement !== 'top-right' && placement !== 'bottom-right') placement = 'center';
      let minGap = 5;
      if(s.min_gap_minutes != null){
        const parsed = parseInt(s.min_gap_minutes, 10);
        if(!isNaN(parsed) && parsed >= 0) minGap = parsed;
      }
      _settings = {
        placement: placement,
        size: s.size || 'medium',
        block_production: !!s.block_production,
        stack_mode: 'queue',
        min_gap_minutes: minGap,
      };
    } catch (e) { /* défaut conservé */ }
  }

  async function _fetchActive() {
    try {
      const r = await fetch('/api/maintenance/alerts/active', FETCH_OPTS);
      if (!r.ok) return { items: [] };
      return await r.json();
    } catch (e) { return { items: [] }; }
  }

  function _normalizeAlert(a) {
    const p = a.params || {};
    const trig = Object.assign({}, p.trigger || {});
    if (trig.interval_minutes == null && trig.interval_hours != null) {
      trig.interval_minutes = Math.round(Number(trig.interval_hours) * 60);
    }
    const tgt = p.target || {};
    let machines = Array.isArray(tgt.machines) ? tgt.machines : ['*'];
    const val = Object.assign({ button_label: 'Valider' }, p.validation || {});
    const dismiss = Object.assign({ enabled: false, label: 'Fermer l\'alerte' }, p.dismiss_button || {});
    const cl = Object.assign({ enabled: false, items: [] }, p.checklist || {});
    if (!Array.isArray(cl.items)) cl.items = [];
    cl.items = cl.items.map(it => {
      if (typeof it === 'string') return { type: 'choice', label: it, responses: ['Conforme'], multi: true };
      const t = (it && it.type) || 'choice';
      if (t === 'value') {
        return {
          type: 'value', label: (it && it.label) || '',
          unit: (it && it.unit) || '',
          min: (it && it.min != null && it.min !== '') ? Number(it.min) : null,
          max: (it && it.max != null && it.max !== '') ? Number(it.max) : null,
          required: !!(it && it.required),
        };
      }
      const responses = Array.isArray(it && it.responses) ? it.responses.filter(r => typeof r === 'string' && r.trim()) : [];
      return {
        type: 'choice', label: (it && it.label) || '',
        responses: responses.length ? responses : ['Conforme'],
        multi: (it && it.multi === false) ? false : true,
        allow_other: !!(it && it.allow_other),
        required: !!(it && it.required),
      };
    });
    const description = (typeof p.description === 'string') ? p.description : '';
    // v2.3.12 : placement + size par alerte (fallback sur les défauts si absent)
    const _pl = ['top-right','center'].indexOf(p && p.placement) >= 0 ? p.placement : null;  // v2.3.17
    const _sz = ['small','medium','large'].indexOf(p && p.size) >= 0 ? p.size : null;
    return { id: a.id, nom: a.nom, linked_maint_code: a.linked_maint_code || '',
             description: description,
             trigger: trig, target: { machines }, validation: val, checklist: cl,
             dismiss_button: dismiss,
             block_production: !!(p && p.block_production),
             placement: _pl, size: _sz };  // v2.3.12
  }

  function _onValueInput(inp) {
    const item = inp.closest('.ta-cl-item');
    if (!item) return;
    const minAttr = item.getAttribute('data-min');
    const maxAttr = item.getAttribute('data-max');
    const v = parseFloat(inp.value);
    let oor = false;
    if (!isNaN(v)) {
      if (minAttr !== null && minAttr !== '' && v < parseFloat(minAttr)) oor = true;
      if (maxAttr !== null && maxAttr !== '' && v > parseFloat(maxAttr)) oor = true;
    }
    inp.style.borderColor = oor ? 'var(--danger)' : 'var(--border)';
    inp.style.color = oor ? 'var(--danger)' : 'var(--text)';
  }
  window._mysifaAlertOnValueInput = _onValueInput;

  function _onOtherChange(inp) {
    const item = inp.closest('.ta-cl-item');
    if (!item) return;
    const txt = item.querySelector('.ta-cl-other-text');
    if (!txt) return;
    const show = !!inp.checked;
    txt.style.display = show ? '' : 'none';
    if (show) { setTimeout(() => txt.focus(), 30); }
    else { txt.value = ''; }
  }
  window._mysifaAlertOnOtherChange = _onOtherChange;

  function _renderChecklist(cl) {
    if (!cl.enabled || !cl.items.length) return '';
    return '<label style="display:block;font-size:10px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Points de contrôle</label>'
      + '<div style="display:flex;flex-direction:column;gap:10px;margin-bottom:10px" class="ta-checklist">'
      +   cl.items.map((it, idx) => {
            if (it.type === 'value') {
              const unit = it.unit ? '<span style="font-size:12px;color:var(--text2);font-weight:500;min-width:24px">' + _esc(it.unit) + '</span>' : '';
              let hint = '';
              if (it.min != null || it.max != null) {
                const minStr = (it.min != null) ? String(it.min) : '−∞';
                const maxStr = (it.max != null) ? String(it.max) : '+∞';
                hint = '<div style="font-size:10px;color:var(--muted);margin-top:3px">Tolérance : ' + _esc(minStr) + ' à ' + _esc(maxStr) + (it.unit ? ' ' + _esc(it.unit) : '') + '</div>';
              }
              const _reqStarV = it.required ? '<span style="color:var(--danger);font-weight:700;margin-left:2px" title="Question obligatoire">*</span>' : '';
              return '<div class="ta-cl-item" data-point-idx="' + idx + '" data-type="value"'
                + (it.required ? ' data-required="1"' : '')
                + (it.min != null ? ' data-min="' + _esc(String(it.min)) + '"' : '')
                + (it.max != null ? ' data-max="' + _esc(String(it.max)) + '"' : '') + '>'
                + '<div style="font-size:14px;font-weight:700;color:var(--text);margin-bottom:6px;display:flex;align-items:center;gap:6px"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--accent);flex-shrink:0"></span>' + _esc(it.label) + _reqStarV + '</div>'
                + '<div style="display:flex;align-items:center;gap:8px">'
                +   '<input type="number" step="any" class="ta-cl-val" data-point="' + idx + '" placeholder="Valeur" style="flex:1;padding:6px 10px;border-radius:7px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;box-sizing:border-box" oninput="window._mysifaAlertOnValueInput(this)">'
                +   unit
                + '</div>'
                + hint
                + '</div>';
            }
            const isMulti = it.multi !== false;
            const inputType = isMulti ? 'checkbox' : 'radio';
            const inputName = isMulti ? '' : ' name="ta-cl-resp-' + idx + '"';
            const respHtml = it.responses.map(r =>
              '<label class="ta-chip">'
              + '<input type="' + inputType + '" class="ta-cl-resp" data-point="' + idx + '"' + inputName + '>'
              + '<span>' + _esc(r) + '</span>'
              + '</label>'
            ).join('');
            let otherHtml = '';
            if (it.allow_other) {
              otherHtml = '<label class="ta-chip ta-chip-other">'
                + '<input type="' + inputType + '" class="ta-cl-resp ta-cl-resp-other" data-point="' + idx + '"' + inputName + ' onchange="window._mysifaAlertOnOtherChange(this)">'
                + '<span>Autre</span>'
                + '</label>';
            }
            const otherArea = it.allow_other
              ? '<textarea class="ta-cl-other-text" data-point="' + idx + '" rows="2" placeholder="Précise (optionnel)" style="display:none;width:100%;margin-top:6px;padding:7px 10px;border-radius:7px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:12px;box-sizing:border-box;resize:vertical;font-family:inherit"></textarea>'
              : '';
            const _reqStarC = it.required ? '<span style="color:var(--danger);font-weight:700;margin-left:2px" title="Question obligatoire">*</span>' : '';
            return '<div class="ta-cl-item" data-point-idx="' + idx + '" data-type="choice"' + (it.allow_other ? ' data-allow-other="1"' : '') + (it.required ? ' data-required="1"' : '') + '>'
              + '<div style="font-size:14px;font-weight:700;color:var(--text);margin-bottom:6px;display:flex;align-items:center;gap:6px"><span style="display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--accent);flex-shrink:0"></span>' + _esc(it.label) + _reqStarC + '</div>'
              + '<div style="display:flex;flex-wrap:wrap;gap:5px">' + respHtml + otherHtml + '</div>'
              + otherArea
              + '</div>';
          }).join('')
      + '</div>';
  }

  function _readResponses(wrap) {
    const responses = {};
    wrap.querySelectorAll('.ta-cl-item').forEach(item => {
      const idx = item.getAttribute('data-point-idx');
      const t = item.getAttribute('data-type') || 'choice';
      if (t === 'value') {
        const v = (item.querySelector('.ta-cl-val')?.value || '').trim();
        if (v !== '') responses[idx] = parseFloat(v);
      } else {
        const checks = Array.from(item.querySelectorAll('.ta-cl-resp:checked'));
        if (checks.length) {
          responses[idx] = checks.map(c => {
            const txt = c.parentElement?.querySelector('span')?.textContent || '';
            return txt.trim();
          });
        }
        // Si Autre est activé et coché, on remonte l'explication libre (optionnelle)
        const otherChecked = item.querySelector('.ta-cl-resp-other:checked');
        if (otherChecked) {
          const txt = (item.querySelector('.ta-cl-other-text')?.value || '').trim();
          if (txt) responses[idx + '_other'] = txt.slice(0, 500);
        }
      }
    });
    return responses;
  }

  function _isComplete(wrap, alert) {
    // v2.2.85 : ne bloque que sur les questions REQUIRED. Les autres restent
    // optionnelles (l'opérateur peut valider sans y répondre).
    if (!alert.checklist.enabled) return true;
    const items = wrap.querySelectorAll('.ta-cl-item');
    for (const it of items) {
      if (it.getAttribute('data-required') !== '1') continue;
      const t = it.getAttribute('data-type') || 'choice';
      if (t === 'value') {
        const v = (it.querySelector('.ta-cl-val')?.value || '').trim();
        if (v === '') return false;
      } else {
        if (!it.querySelectorAll('.ta-cl-resp:checked').length) return false;
      }
    }
    return true;
  }
  // v2.2.85 : recalcule l'état disabled du bouton Valider selon les required
  function _updateValidateState(wrap, alert) {
    const btn = wrap.querySelector('.ta-validate');
    if (!btn) return;
    const ok = _isComplete(wrap, alert);
    btn.disabled = !ok;
    btn.style.opacity = ok ? '' : '.5';
    btn.style.cursor = ok ? '' : 'not-allowed';
  }

  // Retrouve le no_dossier sur lequel l'operateur travaille au moment de
  // l'ack. Ordre de priorite :
  //   1. window.S.dossier (si on est sur la page /prod, deja hydrate)
  //   2. /api/fabrication/dossier-en-cours -> dossier (01 sans 89 aujourd'hui)
  //   3. /api/fabrication/dossier-en-cours -> last_touched_today (01/89 du jour)
  // Jamais bloquant : en cas d'erreur, renvoie '' et l'ack passe quand meme.
  async function _currentNoDossier() {
    try {
      const sDos = window.S && window.S.dossier;
      if (sDos && (sDos.reference || sDos.no_dossier)) {
        return String(sDos.reference || sDos.no_dossier).trim();
      }
    } catch (e) {}
    try {
      const r = await fetch('/api/fabrication/dossier-en-cours', { credentials: 'same-origin' });
      if (!r.ok) return '';
      const d = await r.json();
      const dos = d && d.dossier;
      if (dos && (dos.no_dossier || dos.reference)) {
        return String(dos.no_dossier || dos.reference).trim();
      }
      const lt = d && d.last_touched_today;
      if (lt && (lt.no_dossier || lt.reference)) {
        return String(lt.no_dossier || lt.reference).trim();
      }
      return '';
    } catch (e) {
      return '';
    }
  }

  async function _submitAck(alertId, wrap, alert) {
    // v2.3.13 : mode simulation — ne fait rien côté serveur, retourne true.
    if (alert && alert.__simulate) {
      return true;
    }
    const responses = _readResponses(wrap);
    const comment = wrap.querySelector('.ta-comment')?.value || '';
    // v163+ : priorité au no_dossier fourni par le backend dans /alerts/active
    // (c'est le dossier qui a déclenché l'alerte, ex. le 89 pour dossier_end).
    // Fallback sur la détection locale si le backend n'a rien fourni
    // (alertes non-événementielles).
    let no_dossier = (alert && typeof alert.no_dossier === 'string')
      ? alert.no_dossier.trim() : '';
    if (!no_dossier) {
      no_dossier = await _currentNoDossier();
    }
    try {
      const r = await fetch('/api/maintenance/alerts/' + alertId + '/ack', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ responses, comment, no_dossier }),
      });
      if (!r.ok) {
        let msg = 'Erreur lors de la validation';
        try { const j = await r.json(); msg = j.detail || msg; } catch (e) {}
        _toast(msg, true);
        return false;
      }
      return true;
    } catch (e) {
      _toast('Erreur réseau — réessaie', true);
      return false;
    }
  }

  // v2.3.25 : position par ID d'alerte — chaque alerte garde sa propre
  // position sauvegardée. Deux alertes différentes ne s'influencent plus
  // (avant : une clé unique 'mysifa_alert_position' partagée pour toutes).
  function _posKey(alertId) {
    return 'mysifa_alert_position_' + String(alertId || '_default');
  }

  function _loadAlertPos(alertId) {
    try {
      const raw = localStorage.getItem(_posKey(alertId));
      if (!raw) return null;
      const p = JSON.parse(raw);
      if (p && typeof p.left === 'number' && typeof p.top === 'number') return p;
    } catch (e) {}
    return null;
  }

  function _saveAlertPos(alertId, left, top) {
    try {
      localStorage.setItem(_posKey(alertId), JSON.stringify({ left: left, top: top }));
    } catch (e) {}
  }

  function _applyAlertPos(alertEl, alertId) {
    const pos = _loadAlertPos(alertId);
    if (!pos) return;
    const w = window.innerWidth || document.documentElement.clientWidth;
    const h = window.innerHeight || document.documentElement.clientHeight;
    const rect = alertEl.getBoundingClientRect();
    const maxLeft = Math.max(0, w - Math.min(rect.width, 200));
    const maxTop = Math.max(0, h - Math.min(rect.height, 100));
    const left = Math.max(0, Math.min(pos.left, maxLeft));
    const top = Math.max(0, Math.min(pos.top, maxTop));
    // v2.3.23 : setProperty(..., 'important') pour restaurer la position
    // sauvegardée malgré les !important du placement (v2.3.20).
    alertEl.style.setProperty('position', 'fixed', 'important');
    alertEl.style.setProperty('left', left + 'px', 'important');
    alertEl.style.setProperty('top', top + 'px', 'important');
    alertEl.style.setProperty('right', 'auto', 'important');
    alertEl.style.setProperty('bottom', 'auto', 'important');
    alertEl.style.setProperty('transform', 'none', 'important');
    alertEl.style.setProperty('margin', '0', 'important');
  }

  let _dragState = null;

  // v2.3.25 : récupère l'ID d'alerte depuis le wrapper parent (data-attr posé
  // dans _renderAlert). Utilisé pour sauvegarder la position par alerte.
  function _alertIdFromEl(alertEl) {
    if (!alertEl) return null;
    const wrap = alertEl.closest('.ta-sim');
    if (!wrap) return null;
    return wrap.getAttribute('data-alert-runtime-id') || null;
  }

  function _startDrag(ev, alertEl) {
    if (ev.target.closest('button, input, textarea, label, select')) return;
    const isTouch = !!(ev.touches && ev.touches.length);
    const clientX = isTouch ? ev.touches[0].clientX : ev.clientX;
    const clientY = isTouch ? ev.touches[0].clientY : ev.clientY;
    const rect = alertEl.getBoundingClientRect();
    _dragState = {
      offsetX: clientX - rect.left,
      offsetY: clientY - rect.top,
      alertEl: alertEl,
      alertId: _alertIdFromEl(alertEl),
    };
    const title = alertEl.querySelector('.ta-sim-title');
    if (title) title.classList.add('ta-dragging');
    document.addEventListener('mousemove', _doDrag);
    document.addEventListener('mouseup', _endDrag);
    document.addEventListener('touchmove', _doDrag, { passive: false });
    document.addEventListener('touchend', _endDrag);
    ev.preventDefault();
  }

  function _doDrag(ev) {
    if (!_dragState) return;
    if (ev.touches) ev.preventDefault();
    const isTouch = !!(ev.touches && ev.touches.length);
    const clientX = isTouch ? ev.touches[0].clientX : ev.clientX;
    const clientY = isTouch ? ev.touches[0].clientY : ev.clientY;
    const newLeft = clientX - _dragState.offsetX;
    const newTop = clientY - _dragState.offsetY;
    const el = _dragState.alertEl;
    // v2.3.23 : setProperty(..., 'important') pour override le CSS !important
    // du placement (v2.3.20). Sans ça le drag n'a aucun effet visuel.
    el.style.setProperty('position', 'fixed', 'important');
    el.style.setProperty('left', newLeft + 'px', 'important');
    el.style.setProperty('top', newTop + 'px', 'important');
    el.style.setProperty('right', 'auto', 'important');
    el.style.setProperty('bottom', 'auto', 'important');
    el.style.setProperty('transform', 'none', 'important');
    el.style.setProperty('margin', '0', 'important');
  }

  function _endDrag() {
    if (!_dragState) return;
    const el = _dragState.alertEl;
    const rect = el.getBoundingClientRect();
    _saveAlertPos(_dragState.alertId, rect.left, rect.top);
    const title = el.querySelector('.ta-sim-title');
    if (title) title.classList.remove('ta-dragging');
    document.removeEventListener('mousemove', _doDrag);
    document.removeEventListener('mouseup', _endDrag);
    document.removeEventListener('touchmove', _doDrag);
    document.removeEventListener('touchend', _endDrag);
    _dragState = null;
  }

  function _minimizeAlert(alertEl, targetX, targetY) {
    // Mémorise la position déployée pour la restaurer au clic sur le cercle.
    const rect = alertEl.getBoundingClientRect();
    alertEl._expandedPos = { left: rect.left, top: rect.top };

    // Positionne le cercle réduit centré sur (targetX, targetY) si fournis
    // (typiquement, le centre du bouton "-"). Sinon retombe sur le coin haut-gauche.
    const size = 56;
    let left, top;
    if (typeof targetX === 'number' && typeof targetY === 'number') {
      left = targetX - size / 2;
      top = targetY - size / 2;
    } else {
      left = rect.left;
      top = rect.top;
    }
    const w = window.innerWidth || document.documentElement.clientWidth;
    const h = window.innerHeight || document.documentElement.clientHeight;
    left = Math.max(0, Math.min(left, w - size));
    top = Math.max(0, Math.min(top, h - size));

    alertEl.style.position = 'fixed';
    alertEl.style.left = left + 'px';
    alertEl.style.top = top + 'px';
    alertEl.style.right = 'auto';
    alertEl.style.bottom = 'auto';
    alertEl.style.margin = '0';
    alertEl.classList.add('ta-minimized');
    alertEl.setAttribute('title', 'Cliquer pour rouvrir l\'alerte');
    if (!alertEl._minHandlerAttached) {
      alertEl._minHandlerAttached = true;
      alertEl.addEventListener('mousedown', (ev) => _startMinInteract(ev, alertEl));
      alertEl.addEventListener('touchstart', (ev) => _startMinInteract(ev, alertEl), { passive: false });
    }
  }

  function _restoreAlert(alertEl) {
    alertEl.classList.remove('ta-minimized');
    alertEl.removeAttribute('title');
    // Restaure la position exacte qu'occupait l'alerte avant réduction.
    if (alertEl._expandedPos) {
      alertEl.style.left = alertEl._expandedPos.left + 'px';
      alertEl.style.top = alertEl._expandedPos.top + 'px';
    }
  }

  function _startMinInteract(ev, alertEl) {
    if (!alertEl.classList.contains('ta-minimized')) return;
    if (ev.target.closest('button, input, textarea, select')) return;
    const isTouch = !!(ev.touches && ev.touches.length);
    const startX = isTouch ? ev.touches[0].clientX : ev.clientX;
    const startY = isTouch ? ev.touches[0].clientY : ev.clientY;
    const rect = alertEl.getBoundingClientRect();
    const offsetX = startX - rect.left;
    const offsetY = startY - rect.top;
    const threshold = 5;
    let hasMoved = false;

    function onMove(mv) {
      if (mv.touches) mv.preventDefault();
      const cx = mv.touches ? mv.touches[0].clientX : mv.clientX;
      const cy = mv.touches ? mv.touches[0].clientY : mv.clientY;
      const dx = Math.abs(cx - startX);
      const dy = Math.abs(cy - startY);
      if (!hasMoved && (dx > threshold || dy > threshold)) hasMoved = true;
      if (hasMoved) {
        alertEl.style.left = (cx - offsetX) + 'px';
        alertEl.style.top = (cy - offsetY) + 'px';
      }
    }

    function onEnd() {
      document.removeEventListener('mousemove', onMove);
      document.removeEventListener('mouseup', onEnd);
      document.removeEventListener('touchmove', onMove);
      document.removeEventListener('touchend', onEnd);
      if (!hasMoved) {
        _restoreAlert(alertEl);
      } else {
        const r = alertEl.getBoundingClientRect();
        _saveAlertPos(_alertIdFromEl(alertEl), r.left, r.top);
      }
    }

    document.addEventListener('mousemove', onMove);
    document.addEventListener('mouseup', onEnd);
    document.addEventListener('touchmove', onMove, { passive: false });
    document.addEventListener('touchend', onEnd);
    ev.preventDefault();
  }

  function _renderAlert(alert) {
    const wrap = document.createElement('div');
    // v2.3.12 : priorité aux valeurs par alerte, fallback aux réglages globaux
    const _p = alert.placement || _settings.placement || 'top-right';
    const _s = alert.size || _settings.size || 'medium';
    wrap.className = 'ta-sim ta-pl-' + _p + ' ta-sz-' + _s;
    wrap.setAttribute('data-alert-runtime-id', String(alert.id));
    // v2.2.88 : bloquant par alerte (défaut) ; fallback sur le réglage global si présent (rétrocompat).
    if (alert.block_production || _settings.block_production) wrap.classList.add('ta-blocking');
    const machines = alert.target.machines || ['*'];
    const machinesLbl = machines.includes('*') ? 'Toutes les machines' : machines.map(_esc).join(', ');

    const _desc = (alert && typeof alert.description === 'string') ? alert.description.trim() : '';
    const _descHtml = _desc
      ? '<div class="ta-sim-desc" style="font-size:13px;color:var(--text2);line-height:1.5;margin:-8px 0 14px 0;padding:10px 12px;border-left:3px solid var(--accent);background:var(--accent-bg);border-radius:0 6px 6px 0;white-space:pre-wrap">' + _esc(_desc) + '</div>'
      : '';
    const html = '<div class="ta-sim-alert">'
      + '<button type="button" class="ta-sim-min" title="Réduire l\'alerte" aria-label="Réduire l\'alerte">'
      +   '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>'
      + '</button>'
      + '<span class="ta-sim-restore-icon" aria-hidden="true">'
      +   '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9"/><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0"/></svg>'
      + '</span>'
      + '<div class="ta-sim-title">' + _esc(_stripAutoPrefix(alert.nom)) + '</div>'
      + _descHtml
      + _renderChecklist(alert.checklist)
      + '<label style="display:block;font-size:10px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin:8px 0 4px 0">Commentaire (optionnel)</label>'
      + '<textarea class="ta-comment" rows="2" placeholder="Ajoute un commentaire libre" style="width:100%;padding:7px 10px;border-radius:7px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:12px;box-sizing:border-box;resize:vertical;font-family:inherit"></textarea>'
      + '<div class="ta-sim-actions">'
      +   '<button type="button" class="ta-sim-btn ta-validate">' + _esc(alert.validation.button_label) + '</button>'
      +   (alert.dismiss_button && alert.dismiss_button.enabled
          ? '<button type="button" class="ta-sim-btn ta-dismiss" style="background:#f97316;color:#fff;border-color:#f97316">' + _esc(alert.dismiss_button.label || 'Fermer l\'alerte') + '</button>'
          : '')
      + '</div>'
      + '</div>';
    wrap.innerHTML = html;
    document.body.appendChild(wrap);
    // v2.3.29 : garde une référence à l'objet alerte sur le wrap pour que
    // flushOpenAcks() puisse resoumettre les données saisies sans dépendre
    // du closure du bouton Valider.
    wrap._alert = alert;

    const alertEl = wrap.querySelector('.ta-sim-alert');
    // v2.3.24 : les alertes bloquantes NE sont PAS déplaçables — elles
    // restent à leur placement configuré (centre ou coin haut droit).
    // v2.3.25 : position sauvegardée par ID d'alerte (pas de position
    // globale partagée entre toutes les alertes).
    const _isBlocking = !!alert.block_production;
    if (alertEl && !_isBlocking) _applyAlertPos(alertEl, alert.id);

    const titleEl = wrap.querySelector('.ta-sim-title');
    if (titleEl && alertEl && !_isBlocking) {
      titleEl.addEventListener('mousedown', (ev) => _startDrag(ev, alertEl));
      titleEl.addEventListener('touchstart', (ev) => _startDrag(ev, alertEl), { passive: false });
    } else if (titleEl && _isBlocking) {
      // Curseur par défaut (pas de grab) pour indiquer que le titre n'est pas cliquable-glissable
      titleEl.style.cursor = 'default';
    }

    const minBtn = wrap.querySelector('.ta-sim-min');
    // v2.3.26 : pas de bouton "réduire" pour les alertes bloquantes (masqué par
    // CSS + handler non attaché — l'utilisateur doit valider ou fermer).
    if (minBtn && alertEl && !_isBlocking) {
      minBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const btnRect = minBtn.getBoundingClientRect();
        const cx = btnRect.left + btnRect.width / 2;
        const cy = btnRect.top + btnRect.height / 2;
        _minimizeAlert(alertEl, cx, cy);
      });
    }

    const closeWithSuccess = (viaDismiss) => {
      wrap.remove();
      _displayed.delete(alert.id);
      _displayedBlocking.delete(alert.id);  // v2.3.9
      console.log('[MysifaAlerts] closeWithSuccess id=', alert.id, 'viaDismiss=', viaDismiss, 'waiters=', _blockingAckResolvers.length);
      const cbs = _blockingAckResolvers.slice();
      _blockingAckResolvers = [];
      cbs.forEach(cb => {
        try {
          if (viaDismiss) cb.reject(new Error('dismissed'));
          else cb.resolve();
        } catch (e) {}
      });
    };

    const onValidate = async () => {
      // v2.2.85 : bouton disabled tant que required pas OK, donc si on arrive
      // ici, tout est valide. Plus de warning "valider quand même" — les
      // questions non-required peuvent rester vides sans souci.
      if (!_isComplete(wrap, alert)) return;  // sécurité (bouton disabled)
      // v2.4.3 : garde-fou anti double-submit — si l'op clique en rafale, on
      // ne lance qu'UN seul POST /ack. Sans ça chaque clic crée une ligne
      // d'historique (bug observé : 20 acks identiques à la même seconde).
      if (wrap._ackSubmitting) return;
      wrap._ackSubmitting = true;
      const btnEl = wrap.querySelector('.ta-validate');
      if (btnEl) { btnEl.disabled = true; btnEl.style.opacity = '.5'; btnEl.style.cursor = 'wait'; }
      let ok = false;
      try {
        ok = await _submitAck(alert.id, wrap, alert);
      } finally {
        if (!ok && btnEl) { btnEl.disabled = false; btnEl.style.opacity = ''; btnEl.style.cursor = ''; }
        if (!ok) wrap._ackSubmitting = false;
      }
      if (ok) {
        // v2.3.32 : remerciement à l'opérateur (style toast vert
        // "Saisie enregistrée" de fabrication_page.py via showToast).
        _toast('Merci pour votre réponse au questionnaire.');
        closeWithSuccess();
      }
    };
    wrap.querySelector('.ta-validate').addEventListener('click', onValidate);
    // v2.2.85 : brancher les listeners d'inputs pour mettre à jour l'état disabled
    // du bouton Valider en temps réel selon les questions obligatoires.
    const _syncValidate = () => _updateValidateState(wrap, alert);
    wrap.querySelectorAll('.ta-cl-resp, .ta-cl-val').forEach(el => {
      el.addEventListener('change', _syncValidate);
      el.addEventListener('input', _syncValidate);
    });
    _syncValidate();

    // v164 : bouton dismiss (fermeture silencieuse, aucune trace)
    const dismissBtn = wrap.querySelector('.ta-dismiss');
    if (dismissBtn) {
      dismissBtn.addEventListener('click', async () => {
        try {
          const r = await fetch('/api/maintenance/alerts/' + alert.id + '/dismiss', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json' },
            body: '{}',
          });
          if (!r.ok) {
            _toast('Fermeture refusée.', true);
            return;
          }
          closeWithSuccess(true);  // v2.3.6 : dismiss → reject les waiters
        } catch (e) {
          _toast('Erreur réseau — réessaie', true);
        }
      });
    }
    return wrap;
  }

  async function _poll() {
    const r = await _fetchActive();
    const items = (r && Array.isArray(r.items)) ? r.items : [];
    // v2.2.66 + v2.3.8 : ferme visuellement les alertes qui ne sont plus
    // renvoyées par le serveur, MAIS bypasse les alertes bloquantes affichées
    // via 423 (elles ne sont pas dans /alerts/active — c'est normal).
    const activeIds = new Set(items.map(it => it.id));
    for (const [dispId, wrap] of Array.from(_displayed.entries())) {
      if (!activeIds.has(dispId)) {
        // v2.3.9 : bypass si alerte bloquante (source: 423). Set JS + attribut
        // DOM en double sécurité.
        if (_displayedBlocking.has(dispId)) continue;
        if (wrap && wrap.getAttribute && wrap.getAttribute('data-blocking-alert') === '1') continue;
        try { if (wrap && wrap.remove) wrap.remove(); } catch (e) {}
        _displayed.delete(dispId);
      }
    }
    // Ajout des nouvelles alertes.
    for (const raw of items) {
      if (_displayed.has(raw.id)) continue;
      // Queue mode : au plus UNE alerte visible à la fois sur l'écran de
      // l'opérateur. Tant qu'une alerte est en cours (non validée), on ne
      // pousse rien de nouveau, quelle que soit la file d'attente.
      if (_settings.stack_mode !== 'stack' && _displayed.size > 0) {
        break;
      }
      const alert = _normalizeAlert(raw);
      const wrap = _renderAlert(alert);
      _displayed.set(raw.id, wrap);
      if (_settings.stack_mode !== 'stack') {
        break;
      }
    }
  }

  // v2.2.89 : afficher des alertes bloquantes récupérées par le front (via 423)
  async function _showBlockingAlerts(items) {
    if (!Array.isArray(items) || !items.length) return;
    if (!_started) {
      try { await _loadSettings(); } catch(e){}
    }
    for (const raw of items) {
      if (_displayed.has(raw.id)) continue;
      const alert = _normalizeAlert(raw);
      const wrap = _renderAlert(alert);
      // v2.3.9 : marqueur DOM + Set JS pour double sécurité contre le cleanup.
      wrap.setAttribute('data-blocking-alert', '1');
      _displayed.set(raw.id, wrap);
      _displayedBlocking.add(raw.id);
      console.log('[MysifaAlerts] showBlockingAlerts add id=', raw.id, 'blocking Set size=', _displayedBlocking.size);
    }
  }

  // v2.3.29 : détecte si l'opérateur a déjà commencé à remplir une alerte
  // (au moins une case cochée, une valeur saisie ou un commentaire écrit).
  // Sert de garde-fou avant flushOpenAcks : on ne soumet pas un ack vide.
  function _hasUserInput(wrap) {
    if (!wrap) return false;
    const cmt = (wrap.querySelector('.ta-comment')?.value || '').trim();
    if (cmt) return true;
    const responses = _readResponses(wrap);
    return responses && Object.keys(responses).length > 0;
  }

  // v2.3.29 : soumet toutes les alertes non-bloquantes qui ont déjà des
  // données saisies par l'opérateur, puis retire leur DOM. Appelé avant
  // toute saisie non-productive (code != 01 et != 03) pour éviter que
  // _auto_ack_periodic_alerts_on_arret côté serveur écrase la saisie
  // avec un ack vide "Fermée auto : XX – <label>".
  async function _flushOpenAcks() {
    const wraps = Array.from(document.querySelectorAll('.ta-sim'));
    const results = [];
    for (const wrap of wraps) {
      // Ignore : mode simulation (bouton "Tester sur moi") + alertes bloquantes
      // (elles exigent une interaction explicite, pas de flush silencieux)
      if (wrap.getAttribute('data-simulate') === '1') continue;
      if (wrap.classList.contains('ta-blocking')) continue;
      const alert = wrap._alert;
      if (!alert || alert.__simulate) continue;
      if (!_hasUserInput(wrap)) continue;
      // Soumission — reprend la même logique que le bouton Valider.
      const ok = await _submitAck(alert.id, wrap, alert);
      results.push({ id: alert.id, ok });
      if (ok) {
        try { wrap.remove(); } catch(_) {}
        _displayed.delete(alert.id);
        _displayedBlocking.delete(alert.id);
      }
    }
    return results;
  }

  window.MysifaAlerts = {
    start: async function() {
      if (_started) return;
      _started = true;
      await _loadSettings();
      await _poll();
      if (_pollTimer) clearInterval(_pollTimer);
      _pollTimer = setInterval(_poll, POLL_INTERVAL_MS);
    },
    stop: function() {
      _started = false;
      if (_pollTimer) clearInterval(_pollTimer);
      _pollTimer = null;
    },
    refresh: function() { return _poll(); },
    showBlockingAlerts: function(items) { return _showBlockingAlerts(items); },
    // v2.3.29 : à appeler côté client avant toute saisie non-productive
    // pour préserver les données que l'op a déjà saisies dans une alerte
    // (sinon l'auto-close backend écrit un ack vide "Fermée auto : XX").
    flushOpenAcks: function() { return _flushOpenAcks(); },
    // v2.3.6 : retourne une Promise résolue quand toutes les alertes bloquantes
    // à l'écran sont ACK (rejetée si dismiss). Permet à fabrication_page de
    // retenter automatiquement la saisie 03/88 après validation.
    waitForBlockingAck: function() {
      return new Promise((resolve, reject) => {
        _blockingAckResolvers.push({ resolve, reject });
      });
    },
    // v2.3.13 : mode simulation. Prend un objet alerte au format DB
    // ({id, nom, params, ...}) et l'affiche en réutilisant la vraie fonction
    // _renderAlert. Aucune trace en base : le submit d'ack est court-circuité.
    // Utilisé par le bouton "Tester sur moi" de l'admin, garantit que tout
    // changement du runtime bénéficie automatiquement au simulateur.
    simulate: async function(rawAlert, opts) {
      opts = opts || {};
      if (!_started) {
        try { await _loadSettings(); } catch(e){}
      }
      const alert = _normalizeAlert(rawAlert);
      alert.__simulate = true;  // flag inspecté par _submitAck
      const wrap = _renderAlert(alert);
      wrap.setAttribute('data-simulate', '1');
      _displayed.set(alert.id, wrap);
      _displayedBlocking.add(alert.id);  // ne pas cleanup par le poll
      // Ajouter un bouton "Quitter le test" si demandé
      if (opts.exitButton !== false) {
        const exitBtn = document.createElement('button');
        exitBtn.className = 'ta-sim-exit';
        exitBtn.textContent = '× Quitter le test';
        exitBtn.addEventListener('click', () => {
          try { wrap.remove(); } catch(e) {}
          _displayed.delete(alert.id);
          _displayedBlocking.delete(alert.id);
        });
        wrap.appendChild(exitBtn);
      }
      return wrap;
    },
  };
})();

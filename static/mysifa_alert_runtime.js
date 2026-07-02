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
      '.ta-sim{position:fixed;inset:0;display:flex;z-index:2000;pointer-events:none;padding:20px;box-sizing:border-box}',
      '.ta-sim.ta-blocking{background:rgba(0,0,0,.45);pointer-events:auto;animation:taSimFade .15s ease-out}',
      '.ta-sim.ta-pl-center{align-items:center;justify-content:center}',
      '.ta-sim.ta-pl-top-right{align-items:flex-start;justify-content:flex-end}',
      '.ta-sim.ta-pl-bottom-right{align-items:flex-end;justify-content:flex-end}',
      '.ta-sim-alert{background:var(--card);border:1px solid var(--border);border-radius:12px;box-shadow:0 16px 48px rgba(0,0,0,.5);padding:14px 16px;max-height:calc(100vh - 40px);overflow-y:auto;animation:taSimSlide .2s ease-out;pointer-events:auto}',
      '.ta-sz-small .ta-sim-alert{max-width:240px;width:100%}',
      '.ta-sz-medium .ta-sim-alert{max-width:320px;width:100%}',
      '.ta-sz-large .ta-sim-alert{max-width:420px;width:100%}',
      '.ta-sim-title{font-size:13px;font-weight:700;color:var(--text);margin-bottom:3px}',
      '.ta-sim-sub{font-size:11px;color:var(--muted);margin-bottom:10px}',
      '.ta-sim-actions{display:flex;gap:6px;margin-top:10px}',
      '.ta-sim-btn{flex:1;padding:9px;border-radius:8px;font-size:13px;font-weight:600;border:none;cursor:pointer;font-family:inherit;background:var(--accent);color:#fff}',
      '.ta-sim-btn:hover{filter:brightness(1.05)}',
      '.ta-chip{display:inline-flex;align-items:center;padding:5px 11px;border-radius:999px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:12px;font-weight:500;cursor:pointer;user-select:none;transition:background .12s ease,color .12s ease,border-color .12s ease;font-family:inherit;line-height:1.2}',
      '.ta-chip input{position:absolute;opacity:0;width:0;height:0;pointer-events:none}',
      '.ta-chip:hover{border-color:var(--accent)}',
      '.ta-chip:has(input:checked){background:var(--accent);color:#fff;border-color:var(--accent)}',
      '.ta-chip span{white-space:nowrap}',
      '@keyframes taSimFade{from{opacity:0}to{opacity:1}}',
      '@keyframes taSimSlide{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}',
      '@media(max-width:600px){.ta-sim{padding:12px}.ta-sz-small .ta-sim-alert,.ta-sz-medium .ta-sim-alert,.ta-sz-large .ta-sim-alert{max-width:calc(100vw - 24px)}}'
    ].join('\n');
    document.head.appendChild(style);
  })();


  const POLL_INTERVAL_MS = 15000;
  const FETCH_OPTS = { credentials: 'same-origin' };

  let _settings = { placement: 'top-right', size: 'medium', block_production: false, stack_mode: 'queue', min_gap_minutes: 5 };
  let _displayed = new Set();
  let _pollTimer = null;
  let _started = false;

  function _esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function _attr(s) { return _esc(s); }

  function _toast(msg, isErr) {
    if (typeof window.toast === 'function') return window.toast(msg, !!isErr);
    if (window.console) window.console.log('[alerts]', msg);
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
        };
      }
      const responses = Array.isArray(it && it.responses) ? it.responses.filter(r => typeof r === 'string' && r.trim()) : [];
      return {
        type: 'choice', label: (it && it.label) || '',
        responses: responses.length ? responses : ['Conforme'],
        multi: (it && it.multi === false) ? false : true,
      };
    });
    return { id: a.id, nom: a.nom, linked_maint_code: a.linked_maint_code || '',
             trigger: trig, target: { machines }, validation: val, checklist: cl };
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
              return '<div class="ta-cl-item" data-point-idx="' + idx + '" data-type="value"'
                + (it.min != null ? ' data-min="' + _esc(String(it.min)) + '"' : '')
                + (it.max != null ? ' data-max="' + _esc(String(it.max)) + '"' : '') + '>'
                + '<div style="font-size:12px;font-weight:600;color:var(--text);margin-bottom:4px">' + _esc(it.label) + '</div>'
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
            return '<div class="ta-cl-item" data-point-idx="' + idx + '" data-type="choice">'
              + '<div style="font-size:12px;font-weight:600;color:var(--text);margin-bottom:4px">' + _esc(it.label) + '</div>'
              + '<div style="display:flex;flex-wrap:wrap;gap:5px">' + respHtml + '</div>'
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
      }
    });
    return responses;
  }

  function _isComplete(wrap, alert) {
    if (!alert.checklist.enabled) return true;
    const items = wrap.querySelectorAll('.ta-cl-item');
    for (const it of items) {
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

  async function _submitAck(alertId, wrap) {
    const responses = _readResponses(wrap);
    const comment = wrap.querySelector('.ta-comment')?.value || '';
    try {
      const r = await fetch('/api/maintenance/alerts/' + alertId + '/ack', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ responses, comment }),
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

  function _renderAlert(alert) {
    const wrap = document.createElement('div');
    wrap.className = 'ta-sim ta-pl-' + _settings.placement + ' ta-sz-' + _settings.size;
    if (_settings.block_production) wrap.classList.add('ta-blocking');
    const machines = alert.target.machines || ['*'];
    const machinesLbl = machines.includes('*') ? 'Toutes les machines' : machines.map(_esc).join(', ');

    const html = '<div class="ta-sim-alert">'
      + '<div class="ta-sim-title">' + _esc(alert.nom) + '</div>'
      + '<div class="ta-sim-sub">' + machinesLbl + ' · ' + _esc(_triggerLabel(alert.trigger)) + '</div>'
      + _renderChecklist(alert.checklist)
      + '<label style="display:block;font-size:10px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin:8px 0 4px 0">Commentaire (optionnel)</label>'
      + '<textarea class="ta-comment" rows="2" placeholder="Ajoute un commentaire libre" style="width:100%;padding:7px 10px;border-radius:7px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:12px;box-sizing:border-box;resize:vertical;font-family:inherit"></textarea>'
      + '<div class="ta-sim-actions">'
      +   '<button type="button" class="ta-sim-btn ta-validate">' + _esc(alert.validation.button_label) + '</button>'
      + '</div>'
      + '</div>';
    wrap.innerHTML = html;
    document.body.appendChild(wrap);

    const closeWithSuccess = () => {
      wrap.remove();
      _displayed.delete(alert.id);
    };

    const onValidate = async () => {
      if (_isComplete(wrap, alert)) {
        const ok = await _submitAck(alert.id, wrap);
        if (ok) { _toast('Contrôle validé.'); closeWithSuccess(); }
        return;
      }
      const actions = wrap.querySelector('.ta-sim-actions');
      if (!actions) return;
      actions.innerHTML = '<div style="display:flex;flex-direction:column;gap:8px;width:100%">'
        + '<div style="font-size:12px;color:var(--warn);line-height:1.4;text-align:center">Certains points ne sont pas remplis. Valider quand même ?</div>'
        + '<div style="display:flex;gap:6px">'
        +   '<button type="button" class="ta-sim-btn ta-edit" style="flex:1;background:var(--bg);color:var(--text);border:1px solid var(--border)">Modifier</button>'
        +   '<button type="button" class="ta-sim-btn ta-confirm" style="flex:1">Valider quand même</button>'
        + '</div>'
        + '</div>';
      actions.querySelector('.ta-confirm').addEventListener('click', async () => {
        const ok = await _submitAck(alert.id, wrap);
        if (ok) { _toast('Contrôle validé.'); closeWithSuccess(); }
      });
      actions.querySelector('.ta-edit').addEventListener('click', () => {
        actions.innerHTML = '<button type="button" class="ta-sim-btn ta-validate">' + _esc(alert.validation.button_label) + '</button>';
        actions.querySelector('.ta-validate').addEventListener('click', onValidate);
      });
    };
    wrap.querySelector('.ta-validate').addEventListener('click', onValidate);
  }

  async function _poll() {
    const r = await _fetchActive();
    const items = (r && Array.isArray(r.items)) ? r.items : [];
    for (const raw of items) {
      if (_displayed.has(raw.id)) continue;
      // Queue mode : au plus UNE alerte visible à la fois sur l'écran de
      // l'opérateur. Tant qu'une alerte est en cours (non validée), on ne
      // pousse rien de nouveau, quelle que soit la file d'attente.
      if (_settings.stack_mode !== 'stack' && _displayed.size > 0) {
        break;
      }
      _displayed.add(raw.id);
      const alert = _normalizeAlert(raw);
      _renderAlert(alert);
      if (_settings.stack_mode !== 'stack') {
        break;
      }
    }
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
  };
})();

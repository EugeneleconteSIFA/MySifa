/*
 * MySifa — Panneau « Promouvoir v1 → v2 » + « Sync DB v2 → v1 » (Paramètres › Déploiement).
 *
 * Fichier EXTERNE et AUTONOME. Contexte : ces fonctions vivaient dans le script
 * inline de settings_page.py et ont été supprimées par accident lors d'un refacto
 * (bouton promote bloqué sur « Chargement… », versions en « ••• »). Réintégrées
 * ici en externe et sans dépendance aux globals du script inline (fetch relatif),
 * pour qu'un futur refacto de settings_page.py ne puisse plus les casser.
 *
 * Back-end inchangé : GET /api/promote/status · POST /api/promote · POST /api/sync-db-v1
 * (app/routers/settings.py). Les IDs DOM (pr-*, db-sync-*) sont dans settings_page.py.
 */
(function () {
  "use strict";

  function _prEsc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // Fetch JSON autonome (n'utilise pas le helper `api` du script inline).
  async function _prGetJson(url) {
    const r = await fetch(url, { credentials: 'include', headers: {} });
    if (!r.ok) throw new Error('HTTP ' + r.status);
    return await r.json();
  }

  async function loadPromoteStatus() {
    const v2v = document.getElementById('pr-v2-version');
    const v2h = document.getElementById('pr-v2-head');
    const nxv = document.getElementById('pr-next-version');
    const orh = document.getElementById('pr-origin-head');
    const commitsEl = document.getElementById('pr-commits');
    const goBtn = document.getElementById('pr-go-btn');
    const blocked = document.getElementById('pr-blocked-reason');
    if (!commitsEl) return; // panneau promote absent de cette page
    commitsEl.innerHTML = '<div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Chargement…</div>';
    let data;
    try {
      data = await _prGetJson('/api/promote/status');
      if (!data) return;
    } catch (e) {
      commitsEl.innerHTML = '<div style="padding:18px;color:var(--danger);font-size:13px">Erreur de chargement : ' + _prEsc(e && e.message ? e.message : String(e)) + '</div>';
      return;
    }
    if (v2v) v2v.textContent = data.v2_version ? 'v' + data.v2_version : '—';
    if (v2h) v2h.textContent = data.v2_head || '';
    if (nxv) nxv.textContent = data.next_version ? 'v' + data.next_version : '—';
    if (orh) orh.textContent = data.origin_head || '';

    if (!data.commits_ahead || data.commits_ahead.length === 0) {
      commitsEl.innerHTML = '<div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Rien à promouvoir — v2 est déjà à jour.</div>';
    } else {
      commitsEl.innerHTML = data.commits_ahead.map(function (c) {
        return '<div style="display:flex;gap:10px;padding:8px 10px;border-bottom:1px solid var(--border);align-items:flex-start">'
          + '<span style="font-family:\'SFMono-Regular\',Menlo,monospace;font-size:11px;color:var(--accent);min-width:60px">' + _prEsc(c.hash) + '</span>'
          + '<div style="flex:1;min-width:0">'
            + '<div style="font-size:13px;color:var(--text);overflow:hidden;text-overflow:ellipsis">' + _prEsc(c.subject) + '</div>'
            + '<div style="font-size:11px;color:var(--muted);margin-top:2px">' + _prEsc(c.author) + ' · ' + _prEsc(c.date) + '</div>'
          + '</div>'
        + '</div>';
      }).join('');
    }

    if (goBtn) goBtn.disabled = !data.can_promote;
    if (blocked) blocked.textContent = data.can_promote ? '' : (data.reason || '');
  }

  async function runPromote() {
    const goBtn = document.getElementById('pr-go-btn');
    const notesEl = document.getElementById('pr-notes');
    const outCard = document.getElementById('pr-output-card');
    const outEl = document.getElementById('pr-output');
    const notes = (notesEl && notesEl.value || '').trim();

    if (!confirm('Promouvoir v1 → v2 maintenant ?\nBackup DB, pull, bump patch, restart, healthcheck.\nRollback auto si KO.')) return;

    if (goBtn) { goBtn.disabled = true; goBtn.textContent = 'Promotion en cours…'; }
    if (outCard) outCard.style.display = 'block';
    if (outEl) outEl.textContent = '';

    try {
      const r = await fetch('/api/promote', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: notes }),
      });
      if (!r.ok) {
        if (outEl) outEl.textContent += '[HTTP ' + r.status + '] ' + (await r.text().catch(function () { return ''; })) + '\n';
        if (goBtn) { goBtn.disabled = false; goBtn.textContent = 'Promouvoir maintenant'; }
        return;
      }
      // Stream la réponse ligne par ligne
      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const step = await reader.read();
        if (step.done) break;
        if (outEl) { outEl.textContent += decoder.decode(step.value, { stream: true }); outEl.scrollTop = outEl.scrollHeight; }
      }
    } catch (e) {
      if (outEl) outEl.textContent += '\n[Erreur réseau : ' + (e && e.message ? e.message : String(e)) + ']\n';
    } finally {
      if (goBtn) goBtn.textContent = 'Promouvoir maintenant';
      setTimeout(function () { loadPromoteStatus(); }, 500);
    }
  }

  // ─── Sync DB v2 → v1 ────────────────────────────────────────────────
  async function syncDbV1() {
    const btn = document.getElementById('db-sync-btn');
    const status = document.getElementById('db-sync-status');
    if (!btn) return;
    if (!confirm('⚠ Synchroniser DB v2 → v1 ?\n\nCette action écrase intégralement la DB v1 par la copie live de v2.\nToutes les données créées sur v1 depuis la dernière resync seront perdues.\n\nUn backup pré-resync est conservé automatiquement.\nv1 redémarrera dans ~15s.\n\nContinuer ?')) return;
    const original = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Synchronisation…';
    if (status) status.textContent = '';
    try {
      const r = await fetch('/api/sync-db-v1', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
      });
      const text = await r.text().catch(function () { return ''; });
      if (!r.ok) {
        if (status) { status.textContent = 'Echec (HTTP ' + r.status + ')'; status.style.color = 'var(--danger)'; }
        if (typeof showToast === 'function') showToast('Sync DB echouee : ' + (text || r.status), 'danger');
        else alert('Sync DB echouee : ' + (text || r.status));
      } else {
        if (status) { status.textContent = 'OK · ' + new Date().toLocaleTimeString(); status.style.color = 'var(--success, var(--ok))'; }
        if (typeof showToast === 'function') showToast('Resync lancee. v1 redemarrera dans ~15s.', 'success');
      }
    } catch (e) {
      if (status) { status.textContent = 'Erreur reseau'; status.style.color = 'var(--danger)'; }
      if (typeof showToast === 'function') showToast('Erreur reseau : ' + (e && e.message ? e.message : String(e)), 'danger');
    } finally {
      btn.disabled = false;
      btn.textContent = original;
    }
  }

  // Exposition globale pour les onclick inline du HTML (loadPromoteStatus(), runPromote(), syncDbV1()).
  window.loadPromoteStatus = loadPromoteStatus;
  window.runPromote = runPromote;
  window.syncDbV1 = syncDbV1;
})();

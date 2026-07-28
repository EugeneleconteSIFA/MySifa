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
      _phLoaded = false;  // la promotion vient d'ajouter une release : forcer le rechargement
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

  // ─── Sous-onglets Déployer / Historique ─────────────────────────────
  function pmSetSub(which) {
    document.querySelectorAll('.pm-sub').forEach(function (b) {
      const on = b.dataset.pmsub === which;
      b.classList.toggle('active', on);
      b.style.color = on ? 'var(--text)' : 'var(--muted)';
      b.style.borderBottom = '2px solid ' + (on ? 'var(--accent)' : 'transparent');
    });
    const dep = document.getElementById('pm-sub-deploy');
    const his = document.getElementById('pm-sub-hist');
    if (dep) dep.classList.toggle('hidden', which !== 'deploy');
    if (his) his.classList.toggle('hidden', which !== 'hist');
    if (which === 'hist') loadPromoteHistory();
  }

  // ─── Historique des mises à jour ────────────────────────────────────
  // Timeline dépliable : une ligne par release (version, date, statut, nb de
  // commits), le détail des commits + les notes de release au clic.
  let _phLoaded = false;

  const _PH_STATUTS = {
    success:  { label: 'Promu',    color: 'var(--success, var(--ok, #16a34a))' },
    rollback: { label: 'Rollback', color: 'var(--danger)' },
    failed:   { label: 'Échec',    color: 'var(--danger)' },
  };

  // "2026-07-27T14:32:05" / "2026-07-27 14:32" → "27/07/2026 · 14:32"
  function _phDate(raw) {
    if (!raw) return '';
    const m = String(raw).match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
    if (!m) return String(raw);
    return m[3] + '/' + m[2] + '/' + m[1] + ' · ' + m[4] + ':' + m[5];
  }

  function _phCommitRows(commits) {
    if (!commits || !commits.length) {
      return '<div style="padding:14px;color:var(--muted);font-size:12px">Aucun commit listé pour cette release.</div>';
    }
    return commits.map(function (c) {
      return '<div style="display:flex;gap:10px;padding:7px 10px;border-bottom:1px solid var(--border);align-items:flex-start">'
        + '<span style="font-family:\'SFMono-Regular\',Menlo,monospace;font-size:11px;color:var(--accent);min-width:58px">' + _prEsc(c.hash) + '</span>'
        + '<div style="flex:1;min-width:0">'
          + '<div style="font-size:12.5px;color:var(--text)">' + _prEsc(c.subject) + '</div>'
          + '<div style="font-size:11px;color:var(--muted);margin-top:2px">' + _prEsc(c.author) + ' · ' + _prEsc(c.date) + '</div>'
        + '</div>'
      + '</div>';
    }).join('');
  }

  function _phReleaseCard(rel, idx) {
    const st = _PH_STATUTS[rel.statut] || _PH_STATUTS.success;
    const ver = rel.version ? 'v' + rel.version : '—';
    const from = rel.version_avant ? 'v' + rel.version_avant + ' → ' : '';
    const n = rel.commits_count || (rel.commits ? rel.commits.length : 0);

    let head = '<div onclick="phToggle(' + idx + ')" style="display:flex;align-items:center;gap:12px;padding:12px 14px;cursor:pointer;flex-wrap:wrap">'
      + '<svg id="ph-chev-' + idx + '" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="color:var(--muted);flex-shrink:0;transition:transform .15s"><polyline points="9 18 15 12 9 6"/></svg>'
      + '<span style="font-family:\'SFMono-Regular\',Menlo,monospace;font-size:14px;font-weight:700;color:var(--text);min-width:70px">' + _prEsc(ver) + '</span>'
      + '<span style="font-size:12px;color:var(--muted);min-width:130px">' + _prEsc(_phDate(rel.date)) + '</span>'
      + '<span style="font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;color:' + st.color + ';border:1px solid ' + st.color + ';border-radius:20px;padding:2px 9px">' + _prEsc(st.label) + '</span>'
      + '<span style="font-size:12px;color:var(--muted);flex:1;min-width:120px">' + _prEsc(from) + n + ' commit' + (n > 1 ? 's' : '') + '</span>'
      + '<span style="font-family:\'SFMono-Regular\',Menlo,monospace;font-size:11px;color:var(--muted)">' + _prEsc(rel.head || '') + '</span>';
    if (rel.source === 'git') {
      head += '<span title="Reconstruit depuis git — antérieur au suivi en base" style="font-size:10px;color:var(--muted);border:1px dashed var(--border);border-radius:20px;padding:2px 8px">git</span>';
    }
    head += '</div>';

    let body = '<div id="ph-body-' + idx + '" class="hidden" style="border-top:1px solid var(--border);background:var(--bg)">';
    if (rel.message) {
      body += '<div style="padding:10px 14px;font-size:12px;color:var(--danger)">' + _prEsc(rel.message) + '</div>';
    }
    if (rel.notes) {
      body += '<div style="padding:12px 14px;border-bottom:1px solid var(--border)">'
        + '<div style="font-size:10px;font-weight:800;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Notes de release</div>'
        + '<div style="font-size:12.5px;color:var(--text2);line-height:1.6">' + _prEsc(rel.notes) + '</div>'
        + '</div>';
    }
    body += '<div style="max-height:320px;overflow:auto">' + _phCommitRows(rel.commits) + '</div>';
    body += '</div>';

    return '<div style="border:1px solid var(--border);border-radius:10px;margin-bottom:8px;overflow:hidden">' + head + body + '</div>';
  }

  function phToggle(idx) {
    const body = document.getElementById('ph-body-' + idx);
    const chev = document.getElementById('ph-chev-' + idx);
    if (!body) return;
    const opening = body.classList.contains('hidden');
    body.classList.toggle('hidden', !opening);
    if (chev) chev.style.transform = opening ? 'rotate(90deg)' : 'rotate(0deg)';
  }

  async function loadPromoteHistory(force) {
    const list = document.getElementById('ph-list');
    const meta = document.getElementById('ph-meta');
    if (!list) return;
    if (_phLoaded && !force) return;   // déjà chargé : on ne re-fetch qu'au bouton Rafraîchir
    list.innerHTML = '<div style="padding:28px;text-align:center;color:var(--muted);font-size:13px">Chargement…</div>';

    let data;
    try {
      data = await _prGetJson('/api/promote/history');
    } catch (e) {
      list.innerHTML = '<div style="padding:18px;color:var(--danger);font-size:13px">Erreur de chargement : ' + _prEsc(e && e.message ? e.message : String(e)) + '</div>';
      return;
    }
    _phLoaded = true;

    const rel = data.releases || [];
    if (!rel.length) {
      list.innerHTML = '<div style="padding:28px;text-align:center;color:var(--muted);font-size:13px">Aucune mise en production enregistrée pour le moment.</div>';
      if (meta) meta.textContent = '';
      return;
    }
    list.innerHTML = rel.map(_phReleaseCard).join('');
    if (meta) {
      meta.textContent = rel.length + ' release' + (rel.length > 1 ? 's' : '')
        + (data.has_db_rows ? '' : ' · historique reconstruit depuis git (le suivi en base démarre à la prochaine promotion)');
    }
  }

  // Exposition globale pour les onclick inline du HTML.
  window.loadPromoteStatus = loadPromoteStatus;
  window.runPromote = runPromote;
  window.syncDbV1 = syncDbV1;
  window.pmSetSub = pmSetSub;
  window.loadPromoteHistory = loadPromoteHistory;
  window.phToggle = phToggle;
})();

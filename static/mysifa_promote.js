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

  // MySifa modal de confirmation (style aligne sur _openDeleteCaseModal cote maintenance).
  // Retourne une Promise<boolean> : true si l'utilisateur confirme, false sinon.
  // opts : { title, summary, warning, confirmLabel, confirmColor }
  function _prConfirmModal(opts) {
    opts = opts || {};
    return new Promise(function (resolve) {
      var existing = document.getElementById('pr-confirm-overlay');
      if (existing) existing.remove();
      var wrap = document.createElement('div');
      wrap.id = 'pr-confirm-overlay';
      wrap.style.cssText = 'display:flex;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.55);z-index:9999;align-items:center;justify-content:center';
      var done = false;
      function close(val) {
        if (done) return; done = true;
        try { document.removeEventListener('keydown', escHandler, true); } catch(_) {}
        wrap.remove();
        resolve(val);
      }
      function escHandler(e) { if (e.key === 'Escape') { e.preventDefault(); close(false); } }
      document.addEventListener('keydown', escHandler, true);
      wrap.addEventListener('click', function (e) { if (e.target === wrap) close(false); });

      var title = opts.title || 'Confirmer ?';
      var summary = opts.summary || '';
      var warning = opts.warning || '';
      var confirmLabel = opts.confirmLabel || 'Confirmer';
      var confirmColor = opts.confirmColor || 'var(--danger)';

      wrap.innerHTML = ''
        + '<div role="dialog" aria-modal="true" style="max-width:520px;width:calc(100% - 40px);background:var(--card);border:1px solid var(--border);border-radius:12px;padding:22px;box-shadow:0 20px 50px rgba(0,0,0,0.4)">'
        +   '<div style="color:' + confirmColor + ';font-size:16px;font-weight:700;margin-bottom:12px;display:flex;align-items:center;gap:8px">'
        +     '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.29 3.86l-8.18 14.16A2 2 0 0 0 3.83 21h16.34a2 2 0 0 0 1.72-2.98L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>'
        +     _prEsc(title)
        +   '</div>'
        +   (summary ? '<div style="padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-bottom:14px;font-size:13px;line-height:1.5;color:var(--text)">' + summary + '</div>' : '')
        +   (warning ? '<div style="font-size:13px;color:var(--text);line-height:1.5;margin-bottom:16px">' + warning + '</div>' : '')
        +   '<div style="display:flex;justify-content:flex-end;gap:10px">'
        +     '<button type="button" id="pr-confirm-cancel" style="background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer;font-family:inherit;font-size:13px">Annuler</button>'
        +     '<button type="button" id="pr-confirm-ok" style="background:' + confirmColor + ';color:#fff;border:none;border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer;font-family:inherit;font-size:13px">' + _prEsc(confirmLabel) + '</button>'
        +   '</div>'
        + '</div>';

      document.body.appendChild(wrap);
      var cancelBtn = document.getElementById('pr-confirm-cancel');
      var okBtn     = document.getElementById('pr-confirm-ok');
      if (cancelBtn) cancelBtn.addEventListener('click', function () { close(false); });
      if (okBtn)     okBtn.addEventListener('click', function () { close(true); });
      requestAnimationFrame(function () { if (cancelBtn) cancelBtn.focus(); });
    });
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

    // La santé du dépôt se rafraîchit avec le reste de l'onglet Déployer.
    loadDeploiementSante();
  }

  async function runPromote() {
    const goBtn = document.getElementById('pr-go-btn');
    const notesEl = document.getElementById('pr-notes');
    const outCard = document.getElementById('pr-output-card');
    const outEl = document.getElementById('pr-output');
    const notes = (notesEl && notesEl.value || '').trim();

    var ok = await _prConfirmModal({
      title: 'Promouvoir v1 → v2 maintenant ?',
      summary: 'Bascule en production les commits déjà validés sur v1.',
      warning: 'Séquence : <strong>backup DB → pull → bump patch → restart → healthcheck</strong>. Rollback automatique si le healthcheck échoue.',
      confirmLabel: 'Promouvoir',
      confirmColor: 'var(--accent)',
    });
    if (!ok) return;

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
    var ok = await _prConfirmModal({
      title: 'Synchroniser DB v2 → v1 ?',
      summary: 'Cette action <strong>écrase intégralement</strong> la DB v1 par la copie live de v2.',
      warning: 'Toutes les données créées sur v1 depuis la dernière resync seront perdues.<br><br>Un backup pré-resync est conservé automatiquement. v1 redémarrera dans ~15s.',
      confirmLabel: 'Synchroniser',
      confirmColor: 'var(--danger)',
    });
    if (!ok) return;
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

  // ─── Santé du dépôt : migrations, branches, propreté du dossier ─────
  // Vue de consultation seule : aucune action destructive n'est exposée ici.
  // Elle répond à une question simple avant de promouvoir : est-ce que le
  // schéma est à jour, est-ce qu'il reste des branches mortes, est-ce que le
  // dossier de travail est propre.

  const _DS_OUVERT = { migrations: false, branches: false, dossier: false };
  let _dsData = null;

  function _dsScore(label, valeur, sous, couleur) {
    return '<div style="background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;flex:1;min-width:160px">'
      + '<div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">' + label + '</div>'
      + '<div style="font-size:15px;font-weight:700;color:' + (couleur || 'var(--text)') + '">' + valeur + '</div>'
      + '<div style="font-size:11px;color:var(--muted);margin-top:2px">' + sous + '</div>'
      + '</div>';
  }

  function _dsSection(cle, titre, badge, badgeCouleur, contenu) {
    const ouvert = !!_DS_OUVERT[cle];
    return '<div style="border:1px solid var(--border);border-radius:10px;margin-top:10px;overflow:hidden">'
      + '<button type="button" onclick="dsToggle(\'' + cle + '\')" style="width:100%;display:flex;align-items:center;gap:10px;background:transparent;border:none;padding:11px 14px;cursor:pointer;font-family:inherit;text-align:left">'
        + '<span style="color:var(--muted);font-size:9px;display:inline-block;width:10px;transform:rotate(' + (ouvert ? '90deg' : '0deg') + ')">&#9654;</span>'
        + '<span style="flex:1;font-size:13px;font-weight:700;color:var(--text)">' + titre + '</span>'
        + (badge ? '<span style="font-size:11px;font-weight:700;color:' + (badgeCouleur || 'var(--muted)') + '">' + badge + '</span>' : '')
      + '</button>'
      + (ouvert ? '<div style="border-top:1px solid var(--border)">' + contenu + '</div>' : '')
      + '</div>';
  }

  function _dsVide(texte) {
    return '<div style="padding:16px;text-align:center;color:var(--muted);font-size:12px">' + texte + '</div>';
  }

  function _dsTh(txt, align) {
    return '<th style="text-align:' + (align || 'left') + ';padding:7px 12px;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;white-space:nowrap">' + txt + '</th>';
  }

  function _dsTd(html, style) {
    return '<td style="padding:8px 12px;font-size:12px;color:var(--text2);vertical-align:top;' + (style || '') + '">' + html + '</td>';
  }

  // ─ Note de santé ─
  // Le score est calculé côté serveur ; la vue l'affiche ET affiche ce qui
  // coûte des points. Une note qui baisse sans dire de quoi ne sert à rien.
  function _dsNoteCouleur(lettre) {
    if (lettre === 'A' || lettre === 'B') return 'var(--success, #16a34a)';
    if (lettre === 'C') return 'var(--warn)';
    return 'var(--danger)';
  }

  function _dsNoteHtml(note) {
    if (!note) return '';
    const couleur = _dsNoteCouleur(note.lettre);
    const criteres = note.criteres || [];
    const perdants = criteres.filter(function (c) { return c.perdu > 0; });
    const sains = criteres.filter(function (c) { return !c.perdu; });

    let out = '<div style="background:var(--card);border:1px solid var(--border);border-left:4px solid '
        + couleur + ';border-radius:12px;padding:14px 16px;margin-bottom:14px">'
      + '<div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">'
        + '<div style="display:flex;align-items:baseline;gap:3px">'
          + '<span style="font-size:34px;font-weight:800;line-height:1;color:' + couleur + '">'
            + _prEsc(String(note.score)) + '</span>'
          + '<span style="font-size:13px;font-weight:700;color:var(--muted)">/100</span>'
        + '</div>'
        + '<div style="display:flex;align-items:center;justify-content:center;width:30px;height:30px;'
          + 'border-radius:8px;background:' + couleur + ';color:var(--bg);font-size:15px;font-weight:800">'
          + _prEsc(note.lettre) + '</div>'
        + '<div style="flex:1;min-width:180px">'
          + '<div style="font-size:13px;font-weight:700;color:var(--text)">Note de santé du dépôt — '
            + _prEsc(note.libelle) + '</div>'
          + '<div style="font-size:11px;color:var(--muted);margin-top:2px">'
            + (perdants.length
                ? perdants.length + ' critère' + (perdants.length > 1 ? 's' : '') + ' à corriger · '
                  + note.perdu + ' point' + (note.perdu > 1 ? 's' : '') + ' perdu' + (note.perdu > 1 ? 's' : '')
                : 'Aucun point perdu')
          + '</div>'
        + '</div>'
      + '</div>'
      + '<div style="height:6px;border-radius:4px;background:var(--bg);margin-top:12px;overflow:hidden">'
        + '<div style="height:100%;width:' + Math.max(2, Math.min(100, note.score)) + '%;background:' + couleur + '"></div>'
      + '</div>';

    if (perdants.length) {
      out += '<div style="margin-top:12px;display:flex;flex-direction:column;gap:9px">'
        + perdants.map(function (c) {
            return '<div style="display:flex;gap:10px;align-items:flex-start">'
              + '<span style="flex:0 0 auto;min-width:48px;text-align:center;font-size:11px;font-weight:800;'
                + 'color:var(--warn);background:color-mix(in srgb, var(--warn) 14%, transparent);border-radius:6px;padding:3px 6px">&minus;'
                + _prEsc(String(c.perdu)) + ' pt' + (c.perdu > 1 ? 's' : '') + '</span>'
              + '<div style="flex:1;min-width:0">'
                + '<div style="font-size:12.5px;font-weight:700;color:var(--text)">' + _prEsc(c.label) + '</div>'
                + '<div style="font-size:11.5px;color:var(--muted);line-height:1.5;margin-top:1px">'
                  + _prEsc(c.detail) + '</div>'
              + '</div></div>';
          }).join('')
        + '</div>';
    }
    if (sains.length) {
      out += '<div style="margin-top:11px;padding-top:9px;border-top:1px solid var(--border);'
        + 'font-size:11px;color:var(--muted);line-height:1.55">Sans reproche&nbsp;: '
        + sains.map(function (c) { return _prEsc(c.label.toLowerCase()); }).join(', ') + '.</div>';
    }
    return out + '</div>';
  }

  // Commande de ménage — construite ici, jamais exécutée côté serveur : la
  // suppression de branches appartient au terminal, pas à une page web.
  function _dsCommandeMenage(branches) {
    const mortes = (branches || [])
      .filter(function (b) { return b.a_nettoyer; })
      .map(function (b) { return b.nom; });
    if (!mortes.length) return '';
    return 'git fetch origin --prune\n'
      + 'git push origin --delete ' + mortes.join(' ') + '\n'
      + 'git remote prune origin';
  }

  function _dsMenageHtml(branches) {
    const cmd = _dsCommandeMenage(branches);
    if (!cmd) return '';
    return '<div style="margin-top:10px">'
      + '<button type="button" onclick="dsCopierMenage()"'
        + ' onmouseover="this.style.background=\'var(--card)\'"'
        + ' onmouseout="this.style.background=\'var(--bg)\'"'
        + ' style="background:var(--bg);border:1px solid var(--border);border-radius:8px;'
        + 'padding:7px 13px;font-family:inherit;font-size:12px;font-weight:700;'
        + 'color:var(--text);cursor:pointer">Copier la commande de suppression</button>'
      + '<div style="margin-top:8px;max-height:130px;overflow:auto;background:var(--bg);'
        + 'border:1px solid var(--border);border-radius:8px;padding:9px 11px;'
        + 'font-family:\'SFMono-Regular\',Menlo,monospace;font-size:11px;color:var(--text2);'
        + 'white-space:pre-wrap;word-break:break-all;line-height:1.6">' + _prEsc(cmd) + '</div>'
      + '</div>';
  }

  function dsCopierMenage() {
    const cmd = _dsCommandeMenage((_dsData || {}).branches);
    if (!cmd) return;
    const fini = function (ok) {
      if (typeof showToast === 'function') {
        showToast(ok ? 'Commande copiée — à coller dans ton terminal.'
                     : 'Copie impossible — sélectionne la commande à la main.',
                  ok ? 'success' : 'danger');
      }
    };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(cmd).then(function () { fini(true); },
                                             function () { fini(false); });
      return;
    }
    try {
      const zone = document.createElement('textarea');
      zone.value = cmd;
      zone.style.position = 'fixed';
      zone.style.opacity = '0';
      document.body.appendChild(zone);
      zone.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(zone);
      fini(ok);
    } catch (e) {
      fini(false);
    }
  }

  // ─ Migrations ─
  function _dsMigrationsHtml(mig) {
    let out = '';
    if (mig.en_attente && mig.en_attente.length) {
      out += '<div style="padding:12px 14px;background:color-mix(in srgb, var(--warn) 10%, transparent);border-bottom:1px solid var(--border)">'
        + '<div style="font-size:11px;font-weight:700;color:var(--warn);text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px">En attente sur cette instance</div>'
        + mig.en_attente.map(function (m) {
            return '<div style="font-size:12px;color:var(--text);font-family:\'SFMono-Regular\',Menlo,monospace">'
              + _prEsc(m.nom) + ' <span style="color:var(--muted)">&middot; ' + _prEsc(m.fichier) + '</span></div>';
          }).join('')
        + '<div style="font-size:11px;color:var(--muted);margin-top:6px">Elles s\'appliqueront au prochain démarrage de l\'application.</div>'
        + '</div>';
    }
    if (mig.doublons && mig.doublons.length) {
      out += '<div style="padding:12px 14px;background:color-mix(in srgb, var(--danger) 10%, transparent);border-bottom:1px solid var(--border)">'
        + '<div style="font-size:11px;font-weight:700;color:var(--danger);text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px">Numéros en double</div>'
        + mig.doublons.map(function (d) {
            return '<div style="font-size:12px;color:var(--text)">v' + _prEsc(d.cle) + ' &rarr; ' + _prEsc((d.noms || []).join(', ')) + '</div>';
          }).join('')
        + '<div style="font-size:11px;color:var(--muted);margin-top:6px">Deux migrations partagent un numéro : la seconde ne s\'exécute jamais.</div>'
        + '</div>';
    }
    if (!mig.appliquees || !mig.appliquees.length) return out + _dsVide('Aucune migration enregistrée.');
    out += '<div style="max-height:340px;overflow:auto">'
      + '<table style="width:100%;border-collapse:collapse">'
      + '<thead><tr style="border-bottom:1px solid var(--border)">'
        + _dsTh('Clé') + _dsTh('Migration') + _dsTh('Type') + _dsTh('Appliquée le', 'right')
      + '</tr></thead><tbody>'
      + mig.appliquees.map(function (m) {
          const fichier = m.source === 'fichier';
          return '<tr style="border-bottom:1px solid var(--border)">'
            + _dsTd('<span style="font-family:\'SFMono-Regular\',Menlo,monospace;color:var(--accent)">' + _prEsc(fichier ? '—' : 'v' + m.cle) + '</span>', 'white-space:nowrap')
            + _dsTd('<span style="color:var(--text)">' + _prEsc(m.nom || '(sans nom)') + '</span>')
            + _dsTd('<span style="font-size:11px;color:var(--muted)">' + (fichier ? 'fichier' : 'numérotée') + '</span>', 'white-space:nowrap')
            + _dsTd('<span style="font-size:11px;color:var(--muted)">' + _prEsc(m.date || '') + '</span>', 'text-align:right;white-space:nowrap')
          + '</tr>';
        }).join('')
      + '</tbody></table></div>';
    if (mig.nb_appliquees > mig.appliquees.length) {
      out += '<div style="padding:8px 14px;font-size:11px;color:var(--muted);border-top:1px solid var(--border)">'
        + mig.appliquees.length + ' plus récentes affichées sur ' + mig.nb_appliquees + '.</div>';
    }
    return out;
  }

  // ─ Branches ─
  function _dsBranchesHtml(branches) {
    if (!branches || !branches.length) return _dsVide('Aucune branche distante lisible depuis cette instance.');
    return '<div style="max-height:360px;overflow:auto">'
      + '<table style="width:100%;border-collapse:collapse">'
      + '<thead><tr style="border-bottom:1px solid var(--border)">'
        + _dsTh('Branche') + _dsTh('Dernier commit') + _dsTh('Auteur') + _dsTh('Âge', 'right') + _dsTh('État', 'right')
      + '</tr></thead><tbody>'
      + branches.map(function (b) {
          let etat, couleur;
          if (b.protegee) { etat = 'protégée'; couleur = 'var(--muted)'; }
          else if (b.a_nettoyer) { etat = 'à supprimer'; couleur = 'var(--warn)'; }
          else if (b.fusionnee) { etat = 'fusionnée'; couleur = 'var(--muted)'; }
          else { etat = 'en cours'; couleur = 'var(--accent)'; }
          const age = (b.jours == null) ? '' : (b.jours === 0 ? "aujourd'hui" : b.jours + ' j');
          return '<tr style="border-bottom:1px solid var(--border)' + (b.a_nettoyer ? ';background:color-mix(in srgb, var(--warn) 7%, transparent)' : '') + '">'
            + _dsTd('<span style="font-family:\'SFMono-Regular\',Menlo,monospace;color:var(--text);font-weight:600">' + _prEsc(b.nom) + '</span>')
            + _dsTd('<span style="color:var(--text2)">' + _prEsc(b.dernier_commit || '') + '</span>')
            + _dsTd('<span style="font-size:11px;color:var(--muted)">' + _prEsc(b.auteur || '') + '</span>', 'white-space:nowrap')
            + _dsTd('<span style="font-size:11px;color:var(--muted)">' + _prEsc(age) + '</span>', 'text-align:right;white-space:nowrap')
            + _dsTd('<span style="font-size:11px;font-weight:700;color:' + couleur + '">' + etat + '</span>', 'text-align:right;white-space:nowrap')
          + '</tr>';
        }).join('')
      + '</tbody></table></div>'
      + '<div style="padding:10px 14px;border-top:1px solid var(--border)">'
      + '<div style="font-size:11px;color:var(--muted);line-height:1.6">'
      + 'Une branche est signalée « à supprimer » quand elle est déjà fusionnée dans staging et sans activité depuis plus de deux semaines. La suppression se fait depuis ton terminal.'
      + '</div>'
      + _dsMenageHtml(branches)
      + '</div>';
  }

  // ─ Dossier de travail ─
  function _dsFichiersHtml(titre, liste, total) {
    if (!total) return '';
    return '<div style="margin-top:10px">'
      + '<div style="font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px">' + titre + ' (' + total + ')</div>'
      + '<div style="font-family:\'SFMono-Regular\',Menlo,monospace;font-size:11px;color:var(--text2);line-height:1.7">'
      + liste.map(function (f) { return _prEsc(f); }).join('<br>')
      + (total > liste.length ? '<br><span style="color:var(--muted)">… et ' + (total - liste.length) + ' autre(s)</span>' : '')
      + '</div></div>';
  }

  function _dsDossierHtml(d) {
    let out = '<div style="padding:12px 14px">'
      + '<div style="font-size:12px;color:var(--text2)">Branche courante&nbsp;: '
      + '<span style="font-family:\'SFMono-Regular\',Menlo,monospace;color:var(--text);font-weight:600">' + _prEsc(d.branche) + '</span></div>';
    if (d.verrou_git) {
      out += '<div style="margin-top:10px;background:color-mix(in srgb, var(--danger) 10%, transparent);border:1px solid color-mix(in srgb, var(--danger) 35%, transparent);border-radius:8px;padding:9px 12px;font-size:12px;color:var(--text)">'
        + 'Un verrou <span style="font-family:\'SFMono-Regular\',Menlo,monospace">.git/index.lock</span> traîne dans le dépôt. '
        + 'Il bloque toute commande git tant qu\'il n\'est pas supprimé.</div>';
    }
    if (d.propre) {
      out += '<div style="margin-top:10px;font-size:12px;color:var(--success, #16a34a)">Dossier propre — rien en attente de commit.</div>';
    }
    out += _dsFichiersHtml('Modifiés non commités', d.modifies || [], d.nb_modifies || 0);
    out += _dsFichiersHtml('Non suivis', d.non_suivis || [], d.nb_non_suivis || 0);
    return out + '</div>';
  }

  function _dsRender() {
    const body = document.getElementById('ds-body');
    if (!body || !_dsData) return;
    const d = _dsData;
    const mig = d.migrations || {};
    const branches = d.branches || [];
    const dossier = d.dossier || {};

    const nbAttente = (mig.en_attente || []).length;
    const nbNettoyer = branches.filter(function (b) { return b.a_nettoyer; }).length;
    const nbActives = branches.filter(function (b) { return !b.fusionnee && !b.protegee; }).length;

    let html = _dsNoteHtml(d.note);

    if (d.alertes && d.alertes.length) {
      html += '<div style="background:color-mix(in srgb, var(--warn) 10%, transparent);border:1px solid color-mix(in srgb, var(--warn) 40%, transparent);border-left:4px solid var(--warn);border-radius:10px;padding:11px 15px;margin-bottom:14px">'
        + d.alertes.map(function (a) {
            return '<div style="font-size:12.5px;color:var(--text);line-height:1.55">• ' + _prEsc(a) + '</div>';
          }).join('')
        + '</div>';
    } else {
      html += '<div style="background:color-mix(in srgb, var(--success, #16a34a) 10%, transparent);border:1px solid color-mix(in srgb, var(--success, #16a34a) 35%, transparent);border-left:4px solid var(--success, #16a34a);border-radius:10px;padding:11px 15px;margin-bottom:14px;font-size:12.5px;color:var(--text)">'
        + 'Rien à signaler : schéma à jour, pas de branche morte, dossier propre.</div>';
    }

    html += '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-bottom:4px">'
      + _dsScore('Migrations',
          _prEsc(String(mig.nb_appliquees || 0)) + ' appliquées',
          nbAttente ? (nbAttente + ' en attente') : 'schéma à jour',
          nbAttente ? 'var(--warn)' : 'var(--text)')
      + _dsScore('Branches distantes',
          _prEsc(String(branches.length)) + ' au total',
          nbActives + ' en cours · ' + nbNettoyer + ' à nettoyer',
          nbNettoyer ? 'var(--warn)' : 'var(--text)')
      + _dsScore('Dossier de travail',
          dossier.propre ? 'Propre' : ((dossier.nb_modifies || 0) + (dossier.nb_non_suivis || 0)) + ' fichier(s)',
          _prEsc(dossier.branche || '—'),
          dossier.propre ? 'var(--success, #16a34a)' : 'var(--warn)')
      + '</div>';

    html += _dsSection('migrations', 'Migrations de base de données',
      nbAttente ? nbAttente + ' en attente' : 'à jour',
      nbAttente ? 'var(--warn)' : 'var(--muted)',
      _dsMigrationsHtml(mig));

    html += _dsSection('branches', 'Branches sur le dépôt distant',
      nbNettoyer ? nbNettoyer + ' à nettoyer' : branches.length + ' branches',
      nbNettoyer ? 'var(--warn)' : 'var(--muted)',
      _dsBranchesHtml(branches));

    html += _dsSection('dossier', 'Dossier de travail de cette instance',
      dossier.propre ? 'propre' : (dossier.nb_modifies || 0) + ' modifié(s)',
      dossier.propre ? 'var(--muted)' : 'var(--warn)',
      _dsDossierHtml(dossier));

    body.innerHTML = html;
  }

  function dsToggle(cle) {
    _DS_OUVERT[cle] = !_DS_OUVERT[cle];
    _dsRender();
  }

  async function loadDeploiementSante() {
    const body = document.getElementById('ds-body');
    if (!body) return; // panneau absent de cette page
    body.innerHTML = '<div style="padding:24px;text-align:center;color:var(--muted);font-size:13px">Chargement…</div>';
    try {
      _dsData = await _prGetJson('/api/deploiement/sante');
    } catch (e) {
      _dsData = null;
      body.innerHTML = '<div style="padding:18px;color:var(--danger);font-size:13px">Erreur de chargement : '
        + _prEsc(e && e.message ? e.message : String(e)) + '</div>';
      return;
    }
    _dsRender();
  }

  // Exposition globale pour les onclick inline du HTML.
  window.loadPromoteStatus = loadPromoteStatus;
  window.runPromote = runPromote;
  window.syncDbV1 = syncDbV1;
  window.pmSetSub = pmSetSub;
  window.loadPromoteHistory = loadPromoteHistory;
  window.phToggle = phToggle;
  window.loadDeploiementSante = loadDeploiementSante;
  window.dsToggle = dsToggle;
  window.dsCopierMenage = dsCopierMenage;
})();

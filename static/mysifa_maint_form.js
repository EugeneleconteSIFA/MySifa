/**
 * mysifa_maint_form.js — Codes maintenance + interventions libres (module partagé).
 *
 * Source de vérité unique du CRUD codes maintenance et de la curation
 * interventions libres, utilisé par :
 *   - /settings    → app/web/settings_page.py
 *   - /maintenance → app/web/maintenance_page.py
 *
 * Avant ce module (jusqu'à v2.4.17), 11 fonctions + 4 helpers étaient
 * dupliqués dans les 2 fichiers Python — chaque évolution devait être
 * portée à la main dans les deux copies. Même classe de bug que celle
 * traitée pour le formulaire d'alertes en v2.4.14 (mysifa_alert_form.js).
 *
 * Contenu :
 *   - Constante MAINT_CODES_STORAGE_KEY (migration one-shot localStorage)
 *   - Sub-globals mutables (window._maintItems, _libresItems, etc.)
 *   - 11 fonctions cibles + 4 helpers (_maintCatLabel, _fmtLibreDate,
 *     _updateLibresSelectionUI, _renderMaintFormDocs).
 *
 * Bug latent corrigé au passage : loadMaintCodes de maintenance_page.py
 * référençait MAINT_CODES_STORAGE_KEY sans le déclarer — masqué par un
 * try/catch silencieux. Le module partagé le rend disponible aux 2 pages.
 *
 * Dépendances runtime attendues (fournies par la page hôte) :
 *   - window.esc(s)                — escape HTML
 *   - window.toast(msg, isErr)     — notif
 *   - window.api(path, opt)        — fetch wrapper (JSON parse + throw)
 *   - window.deleteMaintCode(code)         — action listing
 *   - window.libresDelete/Rename/ToggleSelection — actions listing libres
 *   - window.confirm, window.document, window.localStorage
 *
 * Toutes les fonctions internes sont ré-exposées sur window.* pour que les
 * onclick="openMaintForm(...)" inline continuent à fonctionner.
 */
(function () {
  'use strict';
  if (window.MysifaMaintForm) return;

  // Fallbacks défensifs si la page hôte ne fournit pas esc/toast/api
  var esc   = window.esc   || function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var toast = window.toast || function (m, err) { if (window.console) window.console.log('[maint-form]', m, err ? 'ERROR' : ''); };
  var api   = window.api   || function () { throw new Error('window.api indisponible'); };

  // ─── Constante ─────────────────────────────────────────────
  var MAINT_CODES_STORAGE_KEY = 'mysifa_settings_maint_codes_v1';

  // ─── Sub-globals mutables (exposés sur window pour les fonctions non-extraites) ───
  if (typeof window._maintItems     === 'undefined') window._maintItems     = [];
  if (typeof window._maintEditCode  === 'undefined') window._maintEditCode  = null;
  if (typeof window._libresItems    === 'undefined') window._libresItems    = [];
  if (typeof window._libresSelection === 'undefined') window._libresSelection = new Set();
  if (typeof window._lastAckByCode  === 'undefined') window._lastAckByCode  = {};

  // ── _maintCatLabel ──
  function _maintCatLabel(cat) {
    // Depuis v178 : "interventions" est scindée en "entretien" (UI: Nettoyage)
    // et "remplacements" (UI: Interventions). Labels renommés v179.
    // 'interventions' et 'suivi' (legacy) sont remappés vers Nettoyage à l'affichage.
    if (cat === 'remplacements') return 'Interventions';
    if (cat === 'entretien' || cat === 'interventions' || cat === 'suivi') return 'Nettoyage';
    return 'Contrôles';
  }

  // ── _fmtLibreDate ──
  function _fmtLibreDate(iso) {
    if (!iso) return '—';
    try {
      const d = new Date(iso);
      if (isNaN(d.getTime())) return '—';
      const pad = n => (n < 10 ? '0' + n : '' + n);
      return pad(d.getDate()) + '/' + pad(d.getMonth() + 1) + '/' + d.getFullYear();
    } catch (e) { return '—'; }
  }

  // ── _updateLibresSelectionUI ──
  function _updateLibresSelectionUI() {
    const btn = document.getElementById('libres-merge-btn');
    const cnt = document.getElementById('libres-selection-count');
    const n = _libresSelection.size;
    if (btn) btn.disabled = (n !== 2);
    if (cnt) {
      if (n === 0) cnt.textContent = '';
      else if (n === 1) cnt.textContent = '1 titre selectionne - coche un 2e pour fusionner';
      else if (n === 2) cnt.textContent = '2 titres selectionnes - pret a fusionner';
      else cnt.textContent = n + ' selectionnes (max 2)';
    }
  }

  // ── _maintResetDocPicker ──
  function _maintResetDocPicker() {
    const inp = document.getElementById('maint-form-doc-file');
    if (inp) inp.value = '';
  }

  // ── _maintTogglePeriodiqueUI ──
  function _maintTogglePeriodiqueUI(){
    // v2.2.17 — perSel retiré (périodicité cachée).
    const intInp = document.getElementById('maint-intervalle');
    const mInp   = document.getElementById('maint-metrage-ref');
    if (!perSel || !intInp || !mInp) return;
    perSel.disabled = false;
    const isPeriodic = (perSel.value === 'oui');
    intInp.disabled = !isPeriodic;
    intInp.style.opacity = isPeriodic ? '1' : '0.5';
    mInp.disabled   = !isPeriodic;
    mInp.style.opacity = isPeriodic ? '1' : '0.5';
    mInp.style.display = '';
    if (!isPeriodic) {
      intInp.value = '';
      mInp.value   = '';
    }
  }

  // ── _renderMaintFormDocs ──
  async function _renderMaintFormDocs(code) {
    const list = document.getElementById('maint-form-docs-list');
    if (!list) return;
    list.innerHTML = '<p style="color:var(--muted);font-size:12px;font-style:italic">Chargement…</p>';
    try {
      const r = await api('/api/maintenance/codes/' + encodeURIComponent(code) + '/docs');
      const items = Array.isArray(r.items) ? r.items : [];
      if (!items.length) {
        list.innerHTML = '<p style="color:var(--muted);font-size:12px;font-style:italic">Aucun document attache pour l\'instant.</p>';
        return;
      }
      list.innerHTML = items.map(d => {
        const sz = d.size_bytes != null ? (Math.round(d.size_bytes/1024) + ' Ko') : '';
        const dt = d.uploaded_at ? esc(d.uploaded_at.slice(0,16).replace('T',' ')) : '';
        const meta = [sz, dt, d.uploaded_by ? esc(d.uploaded_by) : ''].filter(Boolean).join(' · ');
        return '<div class="maint-doc-row">'
          + '<div class="maint-doc-row-info">'
          +   '<span class="maint-doc-row-name" title="' + esc(d.filename) + '">' + esc(d.filename) + '</span>'
          +   '<span class="maint-doc-row-meta">' + meta + '</span>'
          + '</div>'
          + '<a class="maint-doc-row-link" href="/api/maintenance/docs/' + d.id + '/download" target="_blank" rel="noopener">Telecharger</a>'
          + '<button type="button" class="maint-doc-row-del" data-form-doc-del="' + d.id + '">Supprimer</button>'
          + '</div>';
      }).join('');
      list.querySelectorAll('[data-form-doc-del]').forEach(b => {
        b.addEventListener('click', async () => {
          if (!confirm('Supprimer ce document ?')) return;
          try {
            await api('/api/maintenance/docs/' + b.getAttribute('data-form-doc-del'), { method: 'DELETE' });
            toast('Document supprime');
            await _renderMaintFormDocs(code);
            if (typeof loadMaintCodes === 'function') await loadMaintCodes();
          } catch(e) { toast(e && e.message ? e.message : 'Erreur', true); }
        });
      });
    } catch(e) {
      list.innerHTML = '<p style="color:var(--danger);font-size:12px">Impossible de charger les documents.</p>';
    }
  }

  // ── _bindMaintFormDocUpload ──
  function _bindMaintFormDocUpload(code) { /* upload direct via _maintOnDocFileChange */ }

  // ── _maintOnDocFileChange ──
  async function _maintOnDocFileChange() {
    const inp = document.getElementById('maint-form-doc-file');
    const f = inp && inp.files && inp.files[0];
    if (!f) return;
    if (f.size > 20 * 1024 * 1024) {
      toast('Fichier trop volumineux (max 20 Mo)', true);
      inp.value = '';
      return;
    }
    const codeInp = document.getElementById('maint-code');
    const codeNow = codeInp ? (codeInp.value || '').trim() : '';
    if (!codeNow) {
      toast('Renseigne d\'abord le code', true);
      inp.value = '';
      return;
    }
    const btn = document.getElementById('maint-form-doc-add-btn');
    if (btn) btn.disabled = true;
    const fd = new FormData();
    fd.append('file', f);
    try {
      const res = await fetch('/api/maintenance/codes/' + encodeURIComponent(codeNow) + '/docs', {
        method: 'POST', credentials: 'same-origin', body: fd
      });
      if (!res.ok) {
        let msg = 'Upload echoue';
        try { const j = await res.json(); msg = j.detail || msg; } catch(e){}
        toast(msg, true); return;
      }
      toast('Document ajoute');
      inp.value = '';
      const listEl = document.getElementById('maint-form-docs-list');
      if (listEl) listEl.style.display = '';
      await _renderMaintFormDocs(codeNow);
      if (typeof loadMaintCodes === 'function') await loadMaintCodes();
    } catch(e) {
      toast('Erreur reseau', true);
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  // ── _maintTriggerDocPicker ──
  async function _maintTriggerDocPicker() {
    const codeInp = document.getElementById('maint-code');
    const codeNow = codeInp ? (codeInp.value || '').trim() : '';
    if (!codeNow) { toast('Renseigne d\'abord le code', true); return; }
    // En creation : sauvegarde le code en base avant l'upload, pour eviter
    // a l'utilisateur de devoir fermer le form et rouvrir en Modifier.
    const codeExists = Array.isArray(_maintItems) && _maintItems.some(x => String(x.code) === String(codeNow));
    if (!codeExists) {
      const labelInp = document.getElementById('maint-label');
      const labelNow = labelInp ? (labelInp.value || '').trim() : '';
      if (!labelNow) { toast('Renseigne le libelle avant d\'attacher un fichier', true); return; }
      const niveau = parseInt(document.getElementById('maint-niveau').value, 10) || 1;
      const rawCat = (document.getElementById('maint-categorie')?.value || '').trim();
      const categorie = (rawCat === 'entretien' || rawCat === 'remplacements' || rawCat === 'controles')
        ? rawCat
        : (rawCat === 'interventions' ? 'entretien' : 'controles');
      // v2.2.17 — periodique forcé à true (concept retiré côté UI).
      const periodique = true;
      const intervalle  = (document.getElementById('maint-intervalle')?.value  || '').trim();
      const metrage_ref = (document.getElementById('maint-metrage-ref')?.value || '').trim();
      const payload = { code: codeNow, label: labelNow, niveau, categorie, periodique, intervalle, metrage_ref };
      try {
        await api('/api/maintenance/codes', { method: 'POST', body: JSON.stringify(payload) });
        toast('Code enregistre - upload en cours');
        window._maintEditCode = codeNow;
        codeInp.disabled = true;
        await loadMaintCodes();
        const listEl = document.getElementById('maint-form-docs-list');
        if (listEl) { listEl.style.display = ''; listEl.innerHTML = '<p style="color:var(--muted);font-size:12px;font-style:italic">Aucun document attache pour l\'instant.</p>'; }
      } catch(e) {
        toast(e && e.message ? e.message : 'Impossible d\'enregistrer le code', true);
        return;
      }
    }
    const inp = document.getElementById('maint-form-doc-file');
    if (inp) inp.click();
  }

  // ── loadMaintCodes ──
  async function loadMaintCodes() {
    try {
      const r = await api('/api/maintenance/codes');
      window._maintItems = (r && Array.isArray(r.items)) ? r.items : [];
    } catch (e) {
      toast('Erreur de chargement des codes maintenance : ' + (e && e.message ? e.message : e), true);
      window._maintItems = [];
    }
    // Migration one-shot : si la liste serveur est vide ET qu'on a des codes en
    // localStorage (heritage de l'ancienne implementation), on propose l'import.
    if (_maintItems.length === 0) {
      try {
        const raw = localStorage.getItem(MAINT_CODES_STORAGE_KEY);
        const local = raw ? JSON.parse(raw) : [];
        if (Array.isArray(local) && local.length > 0) {
          if (confirm(local.length + ' code(s) maintenance trouve(s) dans le stockage local du navigateur.\n\nLes importer dans la base de donnees ? (recommande, ils seront ensuite disponibles sur tous les navigateurs et synchronises v2 -> v1)')) {
            try {
              const res = await api('/api/maintenance/codes/bulk-import', {
                method: 'POST',
                body: JSON.stringify({ items: local }),
              });
              toast((res?.imported || 0) + ' code(s) importe(s)');
              try { localStorage.removeItem(MAINT_CODES_STORAGE_KEY); } catch (e) {}
              const r2 = await api('/api/maintenance/codes');
              window._maintItems = (r2 && Array.isArray(r2.items)) ? r2.items : [];
            } catch (e) {
              toast('Echec de l\'import : ' + (e && e.message ? e.message : e), true);
            }
          }
        }
      } catch (e) {}
    }
    renderMaintList();
  }

  // ── renderMaintList ──
  function renderMaintList() {
    const el = document.getElementById('maint-list');
    if (!el) return;
    // Reconstruire la map code -> dernière intervention depuis les alertes auto.
    window._lastAckByCode = {};
    if (Array.isArray(_alertsData)) {
      _alertsData.forEach(a => {
        if (a && a.linked_maint_code) {
          _lastAckByCode[String(a.linked_maint_code)] = a.last_ack_at || '';
        }
      });
    }
    const q = (document.getElementById('maint-filter')?.value || '').trim().toLowerCase();
    let items = _maintItems.slice();
    // Normaliser la catégorie sur les anciens enregistrements
    items.forEach(o => { if (!o.categorie) o.categorie = 'controles'; });
    if (q) {
      items = items.filter(o => {
        const periodLbl = (o.periodique ? 'oui' : 'non');
        return String(o.code || '').toLowerCase().includes(q) ||
          String(o.label || '').toLowerCase().includes(q) ||
          ('n' + (o.niveau || '')).toLowerCase().includes(q) ||
          _maintCatLabel(o.categorie).toLowerCase().includes(q) ||
          // v2.2.17 — periodique retiré du filtre
          String(o.intervalle || '').toLowerCase().includes(q) ||
          String(o.metrage_ref || '').toLowerCase().includes(q);
      });
    }
    // Ordre des catégories : Contrôles → Entretien → Remplacements. Les codes
    // legacy ('interventions', 'suivi') sont remappés vers 'entretien' à l'affichage.
    const _normCat = (c) => {
      if (c === 'remplacements') return 'remplacements';
      if (c === 'entretien' || c === 'interventions' || c === 'suivi') return 'entretien';
      return 'controles';
    };
    const _catOrder = (c) => {
      const n = _normCat(c);
      return n === 'controles' ? 0 : (n === 'entretien' ? 1 : 2);
    };
    items.sort((a, b) => {
      const da = _catOrder(a.categorie);
      const db = _catOrder(b.categorie);
      if (da !== db) return da - db;
      const ac = String(a.code || '').padStart(6, '0');
      const bc = String(b.code || '').padStart(6, '0');
      return ac.localeCompare(bc, 'fr');
    });
    if (!items.length) {
      el.innerHTML = '<p style="color:var(--muted);font-size:13px">Aucun code' + (q ? ' pour ce filtre' : '') + '.</p>';
      return;
    }
    const byCat = { controles: [], entretien: [], remplacements: [] };
    items.forEach(o => { byCat[_normCat(o.categorie)].push(o); });
    let body = '';
    ['controles', 'entretien', 'remplacements'].forEach(cat => {
      if (!byCat[cat].length) return;
      body += '<tr class="op-cat-row"><td colspan="8">' + esc(_maintCatLabel(cat)) + '</td></tr>';
      byCat[cat].forEach(o => {
        const c = esc(String(o.code));
        const niv = parseInt(o.niveau, 10) || 1;
        const catCls = cat;
        // v2.2.17 — Périodicité retirée : tous les codes sont périodiques.
        const intervalleDisplay = o.intervalle ? esc(o.intervalle) : '<span style="color:var(--muted);font-style:italic">À compléter</span>';
        const metrageDisplay = o.metrage_ref ? esc(o.metrage_ref) : '<span style="color:var(--muted);font-style:italic">À compléter</span>';
        body += '<tr>'
          + '<td class="op-code-cell">' + c + '</td>'
          + '<td class="op-lbl-cell">' + esc(o.label || '') + '</td>'
          + '<td><span class="niv-badge" data-niv="' + niv + '">N' + niv + '</span></td>'
          + '<td><span class="op-pill ' + catCls + '">' + esc(_maintCatLabel(cat)) + '</span></td>'
          + '<td>' + intervalleDisplay + '</td>'
          + '<td>' + metrageDisplay + '</td>'
          + '<td><button type="button" class="btn-sm btn-ghost maint-docs-btn" data-maint-docs="' + c + '" title="Gerer les documents attaches a ce code">'
          +   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>'
          +   ' <span class="maint-docs-count" data-count="' + (o.docs_count || 0) + '">' + (o.docs_count || 0) + '</span>'
          + '</button></td>'
          + '<td><div class="op-act">'
          + '<button type="button" class="btn-sm btn-ghost" data-maint-edit="' + c + '">Modifier</button>'
          + '<button type="button" class="btn-sm btn-ghost danger" data-maint-del="' + c + '">Supprimer</button>'
          + '</div></td></tr>';
      });
    });
    el.innerHTML = '<div class="table-wrap op-table-wrap"><table class="op-table"><thead><tr>'
      + '<th>Code</th><th>Libellé</th><th>Niveau</th><th>Catégorie</th><th>Intervalle de temps</th><th>Réf. métrage</th><th>Documents</th><th>Actions</th>'
      + '</tr></thead><tbody>' + body + '</tbody></table></div>';
    el.querySelectorAll('[data-maint-edit]').forEach(btn => {
      btn.addEventListener('click', () => openMaintForm(btn.getAttribute('data-maint-edit')));
    });
    el.querySelectorAll('[data-maint-del]').forEach(btn => {
      btn.addEventListener('click', () => deleteMaintCode(btn.getAttribute('data-maint-del')));
    });
    el.querySelectorAll('[data-maint-docs]').forEach(btn => {
      btn.addEventListener('click', () => openMaintDocsModal(btn.getAttribute('data-maint-docs')));
    });
  }

  // ── openMaintForm ──
  function openMaintForm(code) {
    window._maintEditCode = code || null;
    const wrap = document.getElementById('maint-form-wrap');
    const title = document.getElementById('maint-form-title');
    const codeInp = document.getElementById('maint-code');
    if (!wrap) return;
    wrap.classList.remove('hidden');
    const catSel = document.getElementById('maint-categorie');
    // v2.2.17 — perSel retiré (périodicité cachée).
    const intInp = document.getElementById('maint-intervalle');
    const mInp   = document.getElementById('maint-metrage-ref');
    if (code) {
      const o = _maintItems.find(x => String(x.code) === String(code));
      if (!o) return;
      title.textContent = 'Modifier le code ' + code;
      codeInp.value = o.code;
      codeInp.disabled = true;
      document.getElementById('maint-label').value = o.label || '';
      document.getElementById('maint-niveau').value = String(o.niveau || 1);
      if (catSel) {
        // Depuis v178 : 3 catégories ('controles', 'entretien', 'remplacements').
        // Codes legacy ('interventions', 'suivi') sont remappés vers 'entretien' à l'édition.
        let c;
        if (o.categorie === 'remplacements') c = 'remplacements';
        else if (o.categorie === 'entretien' || o.categorie === 'interventions' || o.categorie === 'suivi') c = 'entretien';
        else c = 'controles';
        catSel.value = c;
      }
      if (intInp) intInp.value = o.intervalle || '';
      if (mInp)   mInp.value   = o.metrage_ref || '';
    } else {
      title.textContent = 'Nouveau code';
      codeInp.value = '';
      codeInp.disabled = false;
      document.getElementById('maint-label').value = '';
      document.getElementById('maint-niveau').value = '1';
      if (catSel) catSel.value = 'controles';
      if (intInp) intInp.value = '';
      if (mInp)   mInp.value   = '';
    }
    // Section Documents : visible dans les 2 modes.
    // En creation : la liste est masquee (aucun doc encore), l'upload est
    // possible des que le code est saisi. En edition : la liste est chargee
    // et l'upload attache directement au code existant.
    const docsWrap = document.getElementById('maint-form-docs');
    const docsList = document.getElementById('maint-form-docs-list');
    const docsHint = document.getElementById('maint-form-docs-hint');
    if (docsWrap) {
      docsWrap.style.display = '';
      _maintResetDocPicker();
      _bindMaintFormDocUpload(code);
      if (code) {
        if (docsHint) docsHint.textContent = 'Fichiers explicatifs consultes par les operateurs quand ils executent l\'operation.';
        if (docsList) docsList.style.display = '';
        _renderMaintFormDocs(code);
      } else {
        if (docsHint) docsHint.textContent = 'Saisis le code puis attache un document. L\'envoi cree le code s\'il n\'existe pas encore.';
        if (docsList) docsList.style.display = 'none';
      }
    }
    // v2.2.34 : le scroller varie selon la page (window en Paramètres, .main en MyMaintenance).
    // On tente les 2 : celui qui n'est pas le vrai scroller no-op silencieusement.
    try {
      window.scrollTo({ top: 0, behavior: 'smooth' });
      const m = document.querySelector('.main');
      if (m) { if (m.scrollTo) m.scrollTo({ top: 0, behavior: 'smooth' }); else m.scrollTop = 0; }
    } catch(e) {
      try { window.scrollTo(0, 0); } catch(e2) {}
      try { document.querySelector('.main').scrollTop = 0; } catch(e3) {}
    }
    codeInp.focus();
  }

  // ── openMaintDocsModal ──
  async function openMaintDocsModal(code) {
    const item = _maintItems.find(x => String(x.code) === String(code));
    const label = item ? item.label : '';
    const overlay = document.createElement('div');
    overlay.className = 'alert-modal-overlay';
    overlay.innerHTML = '<div class="alert-modal" style="max-width:560px">'
      + '<div class="alert-modal-head"><h3>Documents · ' + esc(code) + (label ? ' – ' + esc(label) : '') + '</h3><button type="button" class="btn-sm btn-ghost" data-close>×</button></div>'
      + '<div class="alert-modal-body">'
      +   '<div id="maint-docs-list" style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px"><p style="color:var(--muted);font-size:12px">Chargement…</p></div>'
      +   '<input type="file" id="maint-doc-file" style="position:absolute;left:-9999px;top:auto;width:1px;height:1px;overflow:hidden">'
      +   '<button type="button" class="maint-doc-add-btn" id="maint-doc-add-btn">'
      +     '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>'
      +     '<span>Ajouter un fichier</span>'
      +   '</button>'
      +   '<div style="font-size:11px;color:var(--muted);margin-top:8px">20 Mo max par fichier.</div>'
      + '</div>'
      + '<div class="alert-modal-foot">'
      +   '<button type="button" class="btn btn-sec" data-close>Fermer</button>'
      + '</div></div>';
    document.body.appendChild(overlay);
    const close = () => overlay.remove();
    overlay.querySelectorAll('[data-close]').forEach(el => el.addEventListener('click', close));
    overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });

    const listEl = overlay.querySelector('#maint-docs-list');
    const renderDocs = (items) => {
      if (!items.length) {
        listEl.innerHTML = '<p style="color:var(--muted);font-size:12px;font-style:italic">Aucun document pour l\'instant.</p>';
        return;
      }
      listEl.innerHTML = items.map(d => {
        const sz = d.size_bytes != null ? (Math.round(d.size_bytes / 1024) + ' Ko') : '';
        const dt = d.uploaded_at ? esc(d.uploaded_at.slice(0, 16).replace('T', ' ')) : '';
        return '<div class="maint-doc-row" style="display:flex;align-items:center;gap:8px;padding:8px 10px;border:1px solid var(--border);border-radius:8px;background:var(--card)">'
          +   '<div style="flex:1;min-width:0"><div style="font-size:13px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="' + esc(d.filename) + '">' + esc(d.filename) + '</div>'
          +   '<div style="font-size:10px;color:var(--muted)">' + sz + (dt ? ' · ' + dt : '') + (d.uploaded_by ? ' · ' + esc(d.uploaded_by) : '') + '</div></div>'
          +   '<a class="btn-sm btn-ghost" href="/api/maintenance/docs/' + d.id + '/download" target="_blank" rel="noopener" style="text-decoration:none">Telecharger</a>'
          +   '<button type="button" class="btn-sm btn-ghost danger" data-doc-del="' + d.id + '">Supprimer</button>'
          + '</div>';
      }).join('');
      listEl.querySelectorAll('[data-doc-del]').forEach(b => {
        b.addEventListener('click', async () => {
          if (!confirm('Supprimer ce document ?')) return;
          try {
            await api('/api/maintenance/docs/' + b.getAttribute('data-doc-del'), { method: 'DELETE' });
            toast('Document supprime');
            await refresh();
            if (typeof loadMaintCodes === 'function') await loadMaintCodes();
          } catch(e) { toast(e && e.message ? e.message : 'Erreur', true); }
        });
      });
    };
    const refresh = async () => {
      try {
        const r = await api('/api/maintenance/codes/' + encodeURIComponent(code) + '/docs');
        renderDocs(Array.isArray(r.items) ? r.items : []);
      } catch(e) {
        listEl.innerHTML = '<p style="color:var(--danger);font-size:12px">' + esc(e.message || 'Erreur') + '</p>';
      }
    };
    await refresh();

    const fileInp = overlay.querySelector('#maint-doc-file');
    const addBtn = overlay.querySelector('#maint-doc-add-btn');
    addBtn.addEventListener('click', () => fileInp.click());
    fileInp.addEventListener('change', async () => {
      const f = fileInp.files && fileInp.files[0];
      if (!f) return;
      if (f.size > 20 * 1024 * 1024) { toast('Fichier trop volumineux (max 20 Mo)', true); fileInp.value=''; return; }
      addBtn.disabled = true;
      const fd = new FormData();
      fd.append('file', f);
      try {
        const res = await fetch('/api/maintenance/codes/' + encodeURIComponent(code) + '/docs', {
          method: 'POST', credentials: 'same-origin', body: fd
        });
        if (!res.ok) {
          let msg = 'Upload echoue';
          try { const j = await res.json(); msg = j.detail || msg; } catch(e){}
          toast(msg, true); return;
        }
        toast('Document ajoute');
        fileInp.value = '';
        await refresh();
        if (typeof loadMaintCodes === 'function') await loadMaintCodes();
      } catch(e) { toast('Erreur reseau', true); } finally { addBtn.disabled = false; }
    });
  }

  // ── loadLibres ──
  async function loadLibres() {
    const listEl = document.getElementById('libres-list');
    if (!listEl) return;
    try {
      const r = await api('/api/maintenance/codes/libres');
      window._libresItems = (r && Array.isArray(r.items)) ? r.items : [];
    } catch (e) {
      window._libresItems = [];
    }
    _libresSelection.clear();
    _updateLibresSelectionUI();
    renderLibresList();
  }

  // ── renderLibresList ──
  function renderLibresList() {
    const el = document.getElementById('libres-list');
    if (!el) return;
    const q = (document.getElementById('libres-filter') && document.getElementById('libres-filter').value || '').trim().toLowerCase();
    let items = _libresItems.slice();
    if (q) {
      items = items.filter(o =>
        String(o.label || '').toLowerCase().includes(q) ||
        String(o.code || '').toLowerCase().includes(q)
      );
    }
    if (!items.length) {
      el.innerHTML = '<p style="color:var(--muted);font-size:13px">' +
        (q ? 'Aucun titre pour ce filtre.' : 'Aucune intervention libre saisie pour l\u2019instant.') + '</p>';
      return;
    }
    const rows = items.map(o => {
      const codeEsc = esc(String(o.code));
      const labelEsc = esc(String(o.label || ''));
      const checked = _libresSelection.has(o.code) ? ' checked' : '';
      const usage = o.usage_count;
      const usageChip = usage > 0
        ? '<span style="display:inline-flex;align-items:center;padding:2px 8px;border-radius:12px;background:var(--accent-bg);color:var(--accent);font-size:11px;font-weight:700">' + usage + ' saisie' + (usage > 1 ? 's' : '') + '</span>'
        : '<span style="color:var(--muted);font-size:11px;font-style:italic">Jamais utilise</span>';
      // v2.2.41 : bouton Archiver retiré — un libre est créé au moment de sa 1ère
      // utilisation, donc usage_count >= 1 dès la naissance, le bouton était mort.
      // Nettoyage désormais uniquement via Fusion.
      const delBtn = '';
      return '<tr>' +
        '<td style="width:34px;padding:4px 8px"><input type="checkbox" data-libre-sel="' + codeEsc + '"' + checked + '></td>' +
        '<td style="font-family:monospace;font-size:11px;color:var(--muted)">' + codeEsc + '</td>' +
        '<td><span style="color:var(--text);font-weight:500">' + labelEsc + '</span></td>' +
        '<td>' + usageChip + '</td>' +
        '<td style="font-size:12px;color:var(--text2);white-space:nowrap">' + _fmtLibreDate(o.last_used_at) + '</td>' +
        '<td style="font-size:12px;color:var(--muted);white-space:nowrap">' + _fmtLibreDate(o.created_at) + '</td>' +
        '<td style="text-align:right;white-space:nowrap">' +
          '<button type="button" class="btn-sm btn-ghost" data-libre-rename="' + codeEsc + '">Renommer</button> ' +
          '<button type="button" class="btn-sm btn-ghost" data-libre-attach="' + codeEsc + '" title="Rattacher ce titre a une operation recurrente existante : ses saisies deviennent des saisies recurrentes et le titre disparait.">Rattacher</button> ' +
          '<button type="button" class="btn-sm btn-ghost" data-libre-promote="' + codeEsc + '" title="Transformer ce titre en operation recurrente du catalogue, en conservant ses saisies passees.">Transformer</button> ' +
          delBtn +
        '</td>' +
      '</tr>';
    }).join('');
    el.innerHTML = '<div class="table-wrap op-table-wrap"><table class="op-table">' +
      '<thead><tr>' +
        '<th></th>' +
        '<th>Code</th>' +
        '<th>Titre</th>' +
        '<th>Usage</th>' +
        '<th>Derniere utilisation</th>' +
        '<th>Cree le</th>' +
        '<th style="text-align:right">Actions</th>' +
      '</tr></thead>' +
      '<tbody>' + rows + '</tbody></table></div>';
    // Bind event delegation (checkbox + rename + delete)
    el.querySelectorAll('[data-libre-sel]').forEach(cb => {
      cb.addEventListener('change', () => {
        libresToggleSelection(cb.getAttribute('data-libre-sel'), cb.checked);
      });
    });
    el.querySelectorAll('[data-libre-rename]').forEach(btn => {
      btn.addEventListener('click', () => {
        const code = btn.getAttribute('data-libre-rename');
        const it = _libresItems.find(x => x.code === code);
        if (it) libresRename(code, it.label);
      });
    });
    el.querySelectorAll('[data-libre-attach]').forEach(btn => {
      btn.addEventListener('click', () => {
        openLibreAttachModal(btn.getAttribute('data-libre-attach'));
      });
    });
    el.querySelectorAll('[data-libre-promote]').forEach(btn => {
      btn.addEventListener('click', () => {
        openLibrePromoteModal(btn.getAttribute('data-libre-promote'));
      });
    });
    el.querySelectorAll('[data-libre-del]').forEach(btn => {
      btn.addEventListener('click', () => {
        const code = btn.getAttribute('data-libre-del');
        const it = _libresItems.find(x => x.code === code);
        if (it) libresDelete(code, it.label);
      });
    });
  }

  // ── Rattachement / transformation des interventions libres (v2.5.11) ──
  //
  // Deux sorties possibles pour un titre saisi hors catalogue :
  //   - Rattacher  : le titre etait une operation du catalogue mal nommee.
  //                  Ses saisies basculent sur le code recurrent choisi et le
  //                  titre disparait (liste + historique).
  //   - Transformer: le titre decrit une vraie operation recurrente manquante.
  //                  Il devient un code du catalogue en gardant ses saisies.
  // Les deux sont irreversibles hors SQL : le modal l'annonce et rappelle le
  // nombre de saisies impactees.

  // Rafraichit tout ce qui depend du referentiel des codes apres une action.
  async function _libresRefreshAfterAction() {
    try { await loadLibres(); } catch (e) {}
    try { if (typeof window.loadMaintCodes === 'function') await window.loadMaintCodes(); } catch (e) {}
    try { if (typeof window.renderMaintList === 'function') window.renderMaintList(); } catch (e) {}
    // Page MyMaintenance uniquement : cartes Suivi machine + historique.
    try {
      if (typeof window.loadOpsTypes === 'function') {
        await window.loadOpsTypes();
        if (typeof window.renderMaintCards === 'function') window.renderMaintCards();
        if (typeof window.renderOpsTypes === 'function') window.renderOpsTypes();
      }
    } catch (e) {}
    try { if (typeof window.refreshOpsHistoryNow === 'function') window.refreshOpsHistoryNow(); } catch (e) {}
  }

  function _libresSaisiesLabel(n) {
    return n + ' saisie' + (n > 1 ? 's' : '');
  }

  // Codes recurrents disponibles comme cible de rattachement.
  // /api/maintenance/codes exclut deja les libres (include_libres=0 par defaut).
  async function _libresFetchTargets() {
    const r = await api('/api/maintenance/codes');
    const items = (r && Array.isArray(r.items)) ? r.items : [];
    return items.slice().sort(function (a, b) {
      const na = parseInt(a.code, 10), nb = parseInt(b.code, 10);
      if (!isNaN(na) && !isNaN(nb) && na !== nb) return na - nb;
      return String(a.code).localeCompare(String(b.code));
    });
  }

  // Prochain code numerique libre, pour pre-remplir la transformation.
  function _libresNextFreeCode(items) {
    let max = 0;
    (items || []).forEach(function (it) {
      const n = parseInt(it.code, 10);
      if (!isNaN(n) && n > max) max = n;
    });
    return String(max + 1);
  }

  function _libresModal(titleHtml, bodyHtml, okLabel) {
    const overlay = document.createElement('div');
    overlay.className = 'alert-modal-overlay';
    overlay.innerHTML = '<div class="alert-modal" style="max-width:560px">'
      + '<div class="alert-modal-head"><h3>' + titleHtml + '</h3>'
      +   '<button type="button" class="btn-sm btn-ghost" data-close>&times;</button></div>'
      + '<div class="alert-modal-body">' + bodyHtml + '</div>'
      + '<div class="alert-modal-foot">'
      +   '<button type="button" class="btn btn-sec" data-close>Annuler</button>'
      +   '<button type="button" class="btn" data-ok>' + okLabel + '</button>'
      + '</div></div>';
    document.body.appendChild(overlay);
    const close = function () { overlay.remove(); };
    overlay.querySelectorAll('[data-close]').forEach(function (el) {
      el.addEventListener('click', close);
    });
    overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
    return { overlay: overlay, close: close, okBtn: overlay.querySelector('[data-ok]') };
  }

  // ── Modal « Rattacher » ──
  async function openLibreAttachModal(code) {
    const it = (window._libresItems || []).find(function (x) { return x.code === code; });
    if (!it) { toast('Titre introuvable', true); return; }
    let targets;
    try {
      targets = await _libresFetchTargets();
    } catch (e) {
      toast('Impossible de charger les operations recurrentes', true); return;
    }
    if (!targets.length) { toast('Aucune operation recurrente disponible', true); return; }
    const opts = targets.map(function (t) {
      return '<option value="' + esc(String(t.code)) + '">' + esc(String(t.code)) + ' — '
        + esc(String(t.label || '')) + ' (' + esc(_maintCatLabel(t.categorie)) + ')</option>';
    }).join('');
    const body =
      '<p style="font-size:13px;color:var(--text2);margin:0 0 12px">Les <strong>'
      + _libresSaisiesLabel(it.usage_count) + '</strong> de « ' + esc(it.label)
      + ' » seront rattachees a l’operation recurrente choisie et compteront comme des saisies recurrentes classiques. Le titre inhabituel disparaitra de la liste et de l’historique.</p>'
      + '<label style="display:block;font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin-bottom:6px">Operation recurrente cible</label>'
      + '<input type="search" id="libre-attach-filter" class="op-filter" placeholder="Filtrer (code, libelle…)" style="width:100%;margin-bottom:8px">'
      + '<select id="libre-attach-target" size="8" style="width:100%;font-size:13px">' + opts + '</select>'
      + '<p style="font-size:11px;color:var(--muted);margin:10px 0 0">Si un creneau contient deja une saisie du code cible, les deux saisies sont fusionnees (observations et pieces concatenees, durees additionnees).<br>Action irreversible hors SQL manuel.</p>';
    const m = _libresModal('Rattacher · ' + esc(it.label), body, 'Rattacher');
    const sel = m.overlay.querySelector('#libre-attach-target');
    const filt = m.overlay.querySelector('#libre-attach-filter');
    filt.addEventListener('input', function () {
      const q = filt.value.trim().toLowerCase();
      Array.prototype.forEach.call(sel.options, function (o) {
        o.hidden = q ? o.textContent.toLowerCase().indexOf(q) === -1 : false;
      });
    });
    m.okBtn.addEventListener('click', async function () {
      const target = sel.value;
      if (!target) { toast('Choisis une operation cible', true); return; }
      const tLabel = sel.options[sel.selectedIndex].textContent;
      if (!confirm('Rattacher « ' + it.label + ' » (' + _libresSaisiesLabel(it.usage_count)
        + ') a :\n' + tLabel + '\n\nLe titre inhabituel sera supprime. Action irreversible.')) return;
      m.okBtn.disabled = true;
      try {
        const r = await api('/api/maintenance/codes/libres/' + encodeURIComponent(code) + '/attach', {
          method: 'POST',
          body: JSON.stringify({ target_code: target }),
        });
        const nb = (r && r.total) || 0;
        const fus = (r && r.merged) || 0;
        toast(_libresSaisiesLabel(nb) + ' rattachee' + (nb > 1 ? 's' : '')
          + (fus ? ' (dont ' + fus + ' fusionnee' + (fus > 1 ? 's' : '') + ')' : ''));
        m.close();
        await _libresRefreshAfterAction();
      } catch (e) {
        m.okBtn.disabled = false;
        toast(e && e.message ? e.message : 'Erreur', true);
      }
    });
  }

  // ── Modal « Transformer » ──
  async function openLibrePromoteModal(code) {
    const it = (window._libresItems || []).find(function (x) { return x.code === code; });
    if (!it) { toast('Titre introuvable', true); return; }
    let existing = [];
    try { existing = await _libresFetchTargets(); } catch (e) { existing = []; }
    const nextCode = _libresNextFreeCode(existing);
    const cats = [['controles', 'Controles'], ['entretien', 'Nettoyage'], ['remplacements', 'Interventions']];
    const catOpts = cats.map(function (c) {
      const selAttr = (c[0] === (it.categorie || 'remplacements')) ? ' selected' : '';
      return '<option value="' + c[0] + '"' + selAttr + '>' + c[1] + '</option>';
    }).join('');
    const nivOpts = [1, 2, 3].map(function (n) {
      return '<option value="' + n + '"' + (n === (it.niveau || 1) ? ' selected' : '') + '>N' + n + '</option>';
    }).join('');
    const body =
      '<p style="font-size:13px;color:var(--text2);margin:0 0 12px">« ' + esc(it.label)
      + ' » devient une operation recurrente du catalogue. Ses <strong>'
      + _libresSaisiesLabel(it.usage_count)
      + '</strong> sont conservees : elles deviennent l’historique de la nouvelle operation, la carte Suivi machine affichera directement la derniere intervention.</p>'
      + '<div class="form-grid" style="grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px">'
      +   '<div><label style="display:block;font-size:11px;color:var(--muted);font-weight:700;margin-bottom:4px">Code</label>'
      +     '<input type="text" id="libre-promo-code" value="' + esc(nextCode) + '" inputmode="numeric" maxlength="4" style="width:100%"></div>'
      +   '<div><label style="display:block;font-size:11px;color:var(--muted);font-weight:700;margin-bottom:4px">Niveau</label>'
      +     '<select id="libre-promo-niveau" style="width:100%">' + nivOpts + '</select></div>'
      +   '<div><label style="display:block;font-size:11px;color:var(--muted);font-weight:700;margin-bottom:4px">Categorie</label>'
      +     '<select id="libre-promo-cat" style="width:100%">' + catOpts + '</select></div>'
      + '</div>'
      + '<div style="margin-top:10px"><label style="display:block;font-size:11px;color:var(--muted);font-weight:700;margin-bottom:4px">Libelle</label>'
      +   '<input type="text" id="libre-promo-label" value="' + esc(it.label || '') + '" style="width:100%"></div>'
      + '<div style="margin-top:10px"><label style="display:block;font-size:11px;color:var(--muted);font-weight:700;margin-bottom:4px">Intervalle (obligatoire)</label>'
      +   '<input type="text" id="libre-promo-intervalle" placeholder="ex. Hebdo, 30 jours, 6 mois" maxlength="80" style="width:100%"></div>'
      + '<div style="margin-top:10px"><label style="display:block;font-size:11px;color:var(--muted);font-weight:700;margin-bottom:4px">Reference metrage (optionnel)</label>'
      +   '<input type="text" id="libre-promo-metrage" placeholder="ex. 5000 m, 10 km" maxlength="80" style="width:100%"></div>'
      + '<p style="font-size:11px;color:var(--muted);margin:12px 0 0">Sans intervalle, la carte ne peut pas calculer d’echeance : le champ est donc requis.<br>Action irreversible hors SQL manuel.</p>';
    const m = _libresModal('Transformer en recurrente · ' + esc(it.label), body, 'Transformer');
    m.okBtn.addEventListener('click', async function () {
      const q = function (id) { return m.overlay.querySelector(id); };
      const newCode = q('#libre-promo-code').value.trim();
      const label = q('#libre-promo-label').value.trim();
      const intervalle = q('#libre-promo-intervalle').value.trim();
      if (!newCode) { toast('Code obligatoire', true); return; }
      if (!label) { toast('Libelle obligatoire', true); return; }
      if (!intervalle) { toast('Intervalle obligatoire', true); return; }
      if (existing.some(function (t) { return String(t.code) === newCode; })) {
        toast('Le code ' + newCode + ' existe deja', true); return;
      }
      if (!confirm('Transformer « ' + it.label + ' » en operation recurrente ' + newCode
        + ' ?\n\n' + _libresSaisiesLabel(it.usage_count)
        + ' reprise' + (it.usage_count > 1 ? 's' : '') + ' dans l’historique. Action irreversible.')) return;
      m.okBtn.disabled = true;
      try {
        const r = await api('/api/maintenance/codes/libres/' + encodeURIComponent(code) + '/promote', {
          method: 'POST',
          body: JSON.stringify({
            new_code: newCode,
            label: label,
            niveau: parseInt(q('#libre-promo-niveau').value, 10) || 1,
            categorie: q('#libre-promo-cat').value,
            intervalle: intervalle,
            metrage_ref: q('#libre-promo-metrage').value.trim(),
          }),
        });
        toast('Operation recurrente ' + ((r && r.code) || newCode) + ' creee');
        m.close();
        await _libresRefreshAfterAction();
      } catch (e) {
        m.okBtn.disabled = false;
        toast(e && e.message ? e.message : 'Erreur', true);
      }
    });
  }

  // ─────────────────────────────────────────────────────────
  // Expose tout sur window pour compat onclick="..." inline
  // ─────────────────────────────────────────────────────────
  try { window._maintCatLabel = _maintCatLabel; } catch(e) {}
  try { window._fmtLibreDate = _fmtLibreDate; } catch(e) {}
  try { window._updateLibresSelectionUI = _updateLibresSelectionUI; } catch(e) {}
  try { window._maintResetDocPicker = _maintResetDocPicker; } catch(e) {}
  try { window._maintTogglePeriodiqueUI = _maintTogglePeriodiqueUI; } catch(e) {}
  try { window._renderMaintFormDocs = _renderMaintFormDocs; } catch(e) {}
  try { window._bindMaintFormDocUpload = _bindMaintFormDocUpload; } catch(e) {}
  try { window._maintOnDocFileChange = _maintOnDocFileChange; } catch(e) {}
  try { window._maintTriggerDocPicker = _maintTriggerDocPicker; } catch(e) {}
  try { window.loadMaintCodes = loadMaintCodes; } catch(e) {}
  try { window.renderMaintList = renderMaintList; } catch(e) {}
  try { window.openMaintForm = openMaintForm; } catch(e) {}
  try { window.openMaintDocsModal = openMaintDocsModal; } catch(e) {}
  try { window.loadLibres = loadLibres; } catch(e) {}
  try { window.renderLibresList = renderLibresList; } catch(e) {}
  try { window.openLibreAttachModal = openLibreAttachModal; } catch(e) {}
  try { window.openLibrePromoteModal = openLibrePromoteModal; } catch(e) {}
  try { window.MAINT_CODES_STORAGE_KEY = MAINT_CODES_STORAGE_KEY; } catch(e) {}

  window.MysifaMaintForm = {
    _maintCatLabel: _maintCatLabel,
    _fmtLibreDate: _fmtLibreDate,
    _updateLibresSelectionUI: _updateLibresSelectionUI,
    _maintResetDocPicker: _maintResetDocPicker,
    _maintTogglePeriodiqueUI: _maintTogglePeriodiqueUI,
    _renderMaintFormDocs: _renderMaintFormDocs,
    _bindMaintFormDocUpload: _bindMaintFormDocUpload,
    _maintOnDocFileChange: _maintOnDocFileChange,
    _maintTriggerDocPicker: _maintTriggerDocPicker,
    loadMaintCodes: loadMaintCodes,
    renderMaintList: renderMaintList,
    openMaintForm: openMaintForm,
    openMaintDocsModal: openMaintDocsModal,
    loadLibres: loadLibres,
    renderLibresList: renderLibresList,
    openLibreAttachModal: openLibreAttachModal,
    openLibrePromoteModal: openLibrePromoteModal,
    MAINT_CODES_STORAGE_KEY: MAINT_CODES_STORAGE_KEY
  };
})();

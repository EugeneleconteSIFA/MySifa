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

  // ── Pièces d'usure (v229) ──────────────────────────────────────────────
  // Le rattachement d'un code à une pièce d'usure était auparavant DEVINÉ à
  // partir du libellé ("couteaux" + "bande" + absence de "contre"...). Il est
  // désormais explicite : deux selects, une relation en base. Renommer un code
  // n'a plus aucun effet sur sa carte.
  window._maintUsurePieces = window._maintUsurePieces || [];

  async function loadUsurePieces() {
    try {
      const r = await api('/api/maintenance/usure-pieces');
      window._maintUsurePieces = (r && Array.isArray(r.items)) ? r.items : [];
    } catch (e) {
      // Non bloquant : sans le référentiel, le select reste sur "aucune" et le
      // reste du formulaire fonctionne normalement.
      window._maintUsurePieces = [];
    }
    return window._maintUsurePieces;
  }

  function _maintUsurePieceById(id) {
    if (id === null || id === undefined || id === '') return null;
    return (window._maintUsurePieces || []).find(p => String(p.id) === String(id)) || null;
  }

  // v230 — Divulgation progressive. Un code ordinaire ne voit qu'une case à
  // cocher. Cochée, elle révèle la pièce et la Réf. métrage ; une seconde case
  // révèle la position. La position est saisie LIBREMENT (elle n'est plus
  // choisie dans une liste déclarée sur la pièce) : le champ propose en
  // suggestions les positions déjà en usage sur la pièce, pour éviter que
  // « bande » et « bandes » créent deux onglets pour la même chose.
  function _maintFillPieceOptions(sel) {
    const pieces = window._maintUsurePieces || [];
    sel.innerHTML = '<option value="">— Choisir —</option>'
      + pieces.map(p => '<option value="' + esc(String(p.id)) + '">' + esc(p.label) + '</option>').join('')
      + '<option value="__new__">+ Nouvelle pièce…</option>';
  }

  function _maintSelectedUsurePiece() {
    const sel = document.getElementById('maint-usure-piece');
    return sel ? _maintUsurePieceById(sel.value) : null;
  }

  // v231 : le rattachement pièce d'usure n'existe QUE sur la catégorie
  // Interventions — c'est la seule dont les cartes s'affichent sur l'accueil
  // Maintenance. Ailleurs, le bloc n'est pas grisé mais absent : proposer une
  // option qui ne produira rien visuellement n'aide personne.
  function _maintUsureAllowed() {
    const catSel = document.getElementById('maint-categorie');
    return !!catSel && catSel.value === 'remplacements';
  }

  function _maintOnCategorieChange() {
    const on = document.getElementById('maint-usure-on');
    if (!_maintUsureAllowed() && on && on.checked) {
      // Détacher en silence ferait perdre un rattachement sans que personne
      // ne s'en aperçoive à l'enregistrement. On le dit.
      on.checked = false;
      const sel = document.getElementById('maint-usure-piece');
      if (sel) sel.value = '';
      const hp = document.getElementById('maint-usure-haspos');
      if (hp) hp.checked = false;
      toast('Rattachement pièce d\'usure retiré : réservé à la catégorie Interventions.');
    }
    _maintRefreshUsureUI();
  }

  function _maintRefreshUsureUI() {
    const on      = document.getElementById('maint-usure-on');
    const fields  = document.getElementById('maint-usure-fields');
    const block   = document.getElementById('maint-usure-block');
    const hasPos  = document.getElementById('maint-usure-haspos');
    const posWrap = document.getElementById('maint-usure-pos-wrap');
    const posInp  = document.getElementById('maint-usure-position');
    const dl      = document.getElementById('maint-usure-position-list');
    const mInp    = document.getElementById('maint-metrage-ref');
    const hint    = document.getElementById('maint-usure-hint');
    if (!on || !fields) return;

    const allowed = _maintUsureAllowed();
    if (block) block.style.display = allowed ? 'flex' : 'none';
    if (!allowed) {
      if (on.checked) on.checked = false;
      const mi = document.getElementById('maint-metrage-ref');
      if (mi) mi.value = '';
      return;
    }
    fields.style.display = on.checked ? 'flex' : 'none';
    if (!on.checked && mInp) mInp.value = '';
    if (posWrap) posWrap.style.display = (on.checked && hasPos && hasPos.checked) ? 'inline-block' : 'none';
    if (!(hasPos && hasPos.checked) && posInp) posInp.value = '';

    const piece = _maintSelectedUsurePiece();
    const positions = (piece && Array.isArray(piece.positions)) ? piece.positions : [];
    if (dl) {
      dl.innerHTML = positions
        .map(x => '<option value="' + esc(x) + '"></option>').join('');
    }

    if (!hint) return;
    const msgs = [];
    if (on.checked) {
      if (!piece) {
        msgs.push('Choisis une pièce : sans rattachement, ce code reste une opération ordinaire.');
      } else {
        // Cohérence du mode : le serveur refuse de mélanger, autant le dire ici.
        const posOn = !!(hasPos && hasPos.checked);
        if (positions.length && !posOn) {
          msgs.push('« ' + piece.label + ' » utilise déjà des positions (' + positions.join(', ') + '). Un code sans position sera refusé.');
        }
        if (!positions.length && posOn && (piece.codes_count || 0) > 0) {
          msgs.push('« ' + piece.label + ' » a déjà un code sans position. Ajouter une position ici sera refusé tant que l\'autre code n\'en a pas.');
        }
        if (mInp && !(mInp.value || '').trim()) {
          msgs.push('Sans référence métrage, l\'anneau Métrage de la carte restera vide — la pièce fonctionnera sur le temps seul.');
        }
      }
    }
    if (!msgs.length) { hint.style.display = 'none'; hint.innerHTML = ''; return; }
    hint.style.display = '';
    hint.innerHTML = msgs.map(m => '<div>· ' + esc(m) + '</div>').join('');
  }

  function _maintOnUsureToggle() {
    const on = document.getElementById('maint-usure-on');
    const sel = document.getElementById('maint-usure-piece');
    if (on && !on.checked) {
      // Décocher détache réellement : sinon un code garderait un rattachement
      // invisible, que le formulaire renverrait tel quel à l'enregistrement.
      if (sel) sel.value = '';
      const hp = document.getElementById('maint-usure-haspos');
      if (hp) hp.checked = false;
    } else if (on && on.checked && sel && !sel.options.length) {
      _maintFillPieceOptions(sel);
    }
    _maintRefreshUsureUI();
  }

  function _maintOnUsureHasPosChange() { _maintRefreshUsureUI(); }
  function _maintOnUsurePositionInput() { _maintRefreshUsureUI(); }

  async function _maintOnUsurePieceChange() {
    const sel = document.getElementById('maint-usure-piece');
    if (sel && sel.value === '__new__') {
      // On ne laisse jamais « __new__ » sélectionné : en cas d'annulation le
      // select doit revenir à un état valide, pas à une valeur sentinelle qui
      // partirait dans le payload.
      sel.value = '';
      const label = prompt('Nom de la nouvelle pièce d\'usure (ex. Galets de pression) :', '');
      if (label && label.trim()) {
        try {
          const r = await api('/api/maintenance/usure-pieces', {
            method: 'POST', body: JSON.stringify({ label: label.trim() }),
          });
          await loadUsurePieces();
          _maintFillPieceOptions(sel);
          if (r && r.id) sel.value = String(r.id);
          toast('Pièce créée');
          if (typeof renderUsurePiecesList === 'function'
              && document.getElementById('usure-list')) {
            await loadUsurePiecesAdmin();
          }
        } catch (e) {
          toast(e && e.message ? e.message : 'Erreur', true);
        }
      }
    }
    _maintRefreshUsureUI();
  }

  // Remplit les contrôles à l'ouverture du formulaire.
  function _maintFillUsureSelects(pieceId, position) {
    const on  = document.getElementById('maint-usure-on');
    const sel = document.getElementById('maint-usure-piece');
    const hp  = document.getElementById('maint-usure-haspos');
    const pi  = document.getElementById('maint-usure-position');
    if (!on || !sel) return;
    _maintFillPieceOptions(sel);
    sel.value = (pieceId === null || pieceId === undefined) ? '' : String(pieceId);
    // Pièce désactivée ou supprimée entre-temps : on retombe sur « aucune »
    // plutôt que d'afficher une valeur fantôme.
    if (sel.value && !_maintUsurePieceById(sel.value)) sel.value = '';
    on.checked = !!sel.value;
    const pos = (position || '').trim();
    if (hp) hp.checked = !!pos;
    if (pi) pi.value = pos;
    _maintRefreshUsureUI();
  }

  // Lu par saveMaintForm des 2 pages hôtes : une seule source de vérité pour
  // traduire l'état des cases en payload.
  function _maintUsurePayload() {
    const on = document.getElementById('maint-usure-on');
    if (!on || !on.checked) return { usure_piece_id: null, usure_position: '' };
    const sel = document.getElementById('maint-usure-piece');
    const hp  = document.getElementById('maint-usure-haspos');
    const pi  = document.getElementById('maint-usure-position');
    const pid = (sel && sel.value && sel.value !== '__new__') ? sel.value : '';
    const pos = (hp && hp.checked && pi) ? (pi.value || '').trim() : '';
    return { usure_piece_id: pid || null, usure_position: pos };
  }

  // ── Administration du référentiel des pièces d'usure (v229) ────────────
  // Écran Paramètres → Maintenance → Pièces d'usure. Le DOM n'existe que sur
  // /settings : toutes les fonctions sortent proprement si l'élément est absent,
  // ce qui permet au module partagé de rester chargé sur /maintenance.
  window._usurePiecesAdmin = window._usurePiecesAdmin || [];
  let _usureEditId = null;

  async function loadUsurePiecesAdmin() {
    const box = document.getElementById('usure-list');
    if (!box) return;
    try {
      const r = await api('/api/maintenance/usure-pieces?include_inactifs=true');
      window._usurePiecesAdmin = (r && Array.isArray(r.items)) ? r.items : [];
      if (r && r.migrated === false) {
        box.innerHTML = '<p style="color:var(--danger,#f87171);font-size:13px">Migration DB manquante : la table des pièces d\'usure n\'existe pas encore sur cette instance.</p>';
        return;
      }
    } catch (e) {
      box.innerHTML = '<p style="color:var(--danger,#f87171);font-size:13px">Erreur de chargement : ' + esc(e && e.message ? e.message : String(e)) + '</p>';
      return;
    }
    renderUsurePiecesList();
  }

  function renderUsurePiecesList() {
    const el = document.getElementById('usure-list');
    if (!el) return;
    const items = window._usurePiecesAdmin || [];
    if (!items.length) {
      el.innerHTML = '<p style="color:var(--muted);font-size:13px">Aucune pièce d\'usure. Ajoute-en une pour la voir apparaître sur l\'accueil Maintenance.</p>';
      return;
    }
    let body = '';
    items.forEach(p => {
      const positions = Array.isArray(p.positions) ? p.positions : [];
      // v230 : les positions sont un REFLET des codes rattachés, plus une
      // liste déclarée — d'où la lecture seule ici.
      const posHtml = positions.length
        ? positions.map(x => '<span class="op-pill" style="margin-right:4px">' + esc(x.charAt(0).toUpperCase() + x.slice(1)) + '</span>').join('')
        : '<span style="color:var(--muted);font-style:italic">sans position</span>';
      const n = p.codes_count || 0;
      const cntColor = (n === 0) ? 'var(--danger,#f87171)' : 'var(--text)';
      const cntTitle = (n === 0) ? 'Aucun code rattaché : la carte restera vide' : '';
      body += '<tr' + (p.actif ? '' : ' style="opacity:.5"') + '>'
        + '<td class="op-lbl-cell">' + esc(p.label) + (p.actif ? '' : ' <span style="font-size:10px;color:var(--muted)">(désactivée)</span>') + '</td>'
        + '<td><code style="font-size:11px;color:var(--muted)">' + esc(p.cle) + '</code></td>'
        + '<td>' + posHtml + '</td>'
        + '<td style="color:' + cntColor + '" title="' + esc(cntTitle) + '">' + n + '</td>'
        + '<td>' + (p.ordre || 0) + '</td>'
        + '<td><div class="op-act">'
        +   '<button type="button" class="btn-sm btn-ghost" data-usure-edit="' + esc(String(p.id)) + '">Modifier</button>'
        +   '<button type="button" class="btn-sm btn-ghost" data-usure-toggle="' + esc(String(p.id)) + '">' + (p.actif ? 'Désactiver' : 'Réactiver') + '</button>'
        +   '<button type="button" class="btn-sm btn-ghost danger" data-usure-del="' + esc(String(p.id)) + '">Supprimer</button>'
        + '</div></td></tr>';
    });
    el.innerHTML = '<div class="table-wrap op-table-wrap"><table class="op-table"><thead><tr>'
      + '<th>Pièce</th><th>Clé</th><th>Positions</th><th title="Nombre de codes maintenance rattachés à cette pièce">Codes</th><th>Ordre</th><th>Actions</th>'
      + '</tr></thead><tbody>' + body + '</tbody></table></div>';
    el.querySelectorAll('[data-usure-edit]').forEach(b => b.addEventListener('click', () => openUsurePieceForm(b.getAttribute('data-usure-edit'))));
    el.querySelectorAll('[data-usure-toggle]').forEach(b => b.addEventListener('click', () => toggleUsurePiece(b.getAttribute('data-usure-toggle'))));
    el.querySelectorAll('[data-usure-del]').forEach(b => b.addEventListener('click', () => deleteUsurePiece(b.getAttribute('data-usure-del'))));
  }

  function _usurePieceAdminById(id) {
    return (window._usurePiecesAdmin || []).find(p => String(p.id) === String(id)) || null;
  }

  function openUsurePieceForm(id) {
    const wrap = document.getElementById('usure-form-wrap');
    if (!wrap) return;
    _usureEditId = id || null;
    wrap.classList.remove('hidden');
    const title = document.getElementById('usure-form-title');
    const lab = document.getElementById('usure-label');
    const ord = document.getElementById('usure-ordre');
    if (id) {
      const p = _usurePieceAdminById(id);
      if (!p) return;
      if (title) title.textContent = 'Modifier « ' + p.label + ' »';
      if (lab) lab.value = p.label || '';
      if (ord) ord.value = String(p.ordre || 0);
    } else {
      if (title) title.textContent = 'Nouvelle pièce';
      if (lab) lab.value = '';
      if (ord) ord.value = '';
    }
    if (lab) lab.focus();
  }

  function closeUsurePieceForm() {
    _usureEditId = null;
    const wrap = document.getElementById('usure-form-wrap');
    if (wrap) wrap.classList.add('hidden');
  }

  async function saveUsurePieceForm() {
    const label = (document.getElementById('usure-label')?.value || '').trim();
    const ordRaw = (document.getElementById('usure-ordre')?.value || '').trim();
    if (!label) { toast('Libellé obligatoire', true); return; }
    // v230 : les positions ne se déclarent plus ici — elles se saisissent sur
    // chaque code et la pièce ne fait que les refléter.
    const payload = { label: label };
    if (ordRaw !== '') payload.ordre = parseInt(ordRaw, 10) || 0;
    try {
      if (_usureEditId) {
        await api('/api/maintenance/usure-pieces/' + encodeURIComponent(_usureEditId), {
          method: 'PUT', body: JSON.stringify(payload),
        });
      } else {
        await api('/api/maintenance/usure-pieces', {
          method: 'POST', body: JSON.stringify(payload),
        });
      }
      toast('Pièce enregistrée');
    } catch (e) {
      toast(e && e.message ? e.message : 'Erreur', true);
      return;
    }
    closeUsurePieceForm();
    await loadUsurePiecesAdmin();
    // Le référentiel utilisé par le formulaire des codes ET par la colonne
    // « Pièce d'usure » doit refléter le changement sans rechargement de page.
    await loadUsurePieces();
    if (typeof renderMaintList === 'function') renderMaintList();
  }

  async function toggleUsurePiece(id) {
    const p = _usurePieceAdminById(id);
    if (!p) return;
    try {
      await api('/api/maintenance/usure-pieces/' + encodeURIComponent(id), {
        method: 'PUT', body: JSON.stringify({ actif: !p.actif }),
      });
    } catch (e) {
      toast(e && e.message ? e.message : 'Erreur', true);
      return;
    }
    await loadUsurePiecesAdmin();
    await loadUsurePieces();
    if (typeof renderMaintList === 'function') renderMaintList();
  }

  async function deleteUsurePiece(id) {
    const p = _usurePieceAdminById(id);
    if (!p) return;
    if (!confirm('Supprimer la pièce « ' + p.label + ' » ?\n\nSa carte disparaîtra de l\'accueil Maintenance. Les codes maintenance ne sont pas supprimés — il faut les avoir détachés au préalable.')) return;
    try {
      await api('/api/maintenance/usure-pieces/' + encodeURIComponent(id), { method: 'DELETE' });
      toast('Pièce supprimée');
    } catch (e) {
      toast(e && e.message ? e.message : 'Erreur', true);
      return;
    }
    await loadUsurePiecesAdmin();
    await loadUsurePieces();
    if (typeof renderMaintList === 'function') renderMaintList();
  }

  // ── loadMaintCodes ──
  async function loadMaintCodes() {
    // Le référentiel des pièces alimente le select du formulaire ET le badge
    // de la liste : il doit être chargé avant le premier renderMaintList.
    await loadUsurePieces();
    try {
      // v2.7.1 : include_archived=1 — les codes archives doivent rester
      // visibles ICI (c'est le seul endroit d'ou on peut les reactiver),
      // mais ils sont masques par defaut au rendu et restent exclus partout
      // ailleurs, ou l'API les filtre deja.
      const r = await api('/api/maintenance/codes?include_archived=1');
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
              const r2 = await api('/api/maintenance/codes?include_archived=1');
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

  // Contenu de la colonne « Pièce d'usure » — c'est la réponse à « comment
  // reconnaître un code pièce d'usure ». Avant v229 il n'y avait rien à
  // afficher : l'information n'existait nulle part en base.
  //
  // Colonne et non badge collé au libellé : les libellés d'aujourd'hui
  // répètent le nom de la pièce ("Changement couteaux bande"), ce qui faisait
  // lire le badge comme une redondance. En colonne, on balaie le rattachement
  // réel d'un coup d'œil — y compris les codes qui n'en ont pas.
  function _maintUsureCell(o) {
    const none = '<span style="color:var(--muted)">—</span>';
    if (!o || o.usure_piece_id === null || o.usure_piece_id === undefined) return none;
    const piece = _maintUsurePieceById(o.usure_piece_id);
    // Pièce désactivée ou supprimée : on le dit, plutôt que d'afficher « — »
    // qui laisserait croire que le code n'a jamais été rattaché.
    if (!piece) return '<span style="color:var(--danger,#f87171)" title="La pièce référencée n\'existe plus ou est désactivée">pièce introuvable</span>';
    const pos = (o.usure_position || '').trim();
    const txt = piece.label + (pos ? ' · ' + pos.charAt(0).toUpperCase() + pos.slice(1) : '');
    return '<span style="display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;border-radius:5px;'
         + 'background:var(--accent-bg);color:var(--accent);border:1px solid var(--accent);'
         + 'white-space:nowrap">' + esc(txt) + '</span>';
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
    // v2.7.1 : les codes archives sont hors catalogue. On les garde en memoire
    // pour pouvoir les reactiver, mais ils n'encombrent la liste que si on les
    // demande explicitement.
    const _archives = items.filter(o => o && o.archived);
    if (!window._maintShowArchived) {
      items = items.filter(o => !(o && o.archived));
    }
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
          String(o.metrage_ref || '').toLowerCase().includes(q) ||
          // v229 : filtrer par nom de pièce ("couteaux") remonte tous ses codes,
          // même si leur libellé ne contient pas le mot.
          (function(){
            const pc = _maintUsurePieceById(o.usure_piece_id);
            if (!pc) return false;
            return (pc.label + ' ' + (o.usure_position || '')).toLowerCase().includes(q);
          })();
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
      body += '<tr class="op-cat-row"><td colspan="9">' + esc(_maintCatLabel(cat)) + '</td></tr>';
      byCat[cat].forEach(o => {
        const c = esc(String(o.code));
        const niv = parseInt(o.niveau, 10) || 1;
        const catCls = cat;
        // v2.2.17 — Périodicité retirée : tous les codes sont périodiques.
        const intervalleDisplay = o.intervalle ? esc(o.intervalle) : '<span style="color:var(--muted);font-style:italic">À compléter</span>';
        // v230 : la réf. métrage n'existe que pour les pièces d'usure. Pour un
        // code ordinaire, un tiret — « À compléter » laissait croire qu'il
        // manquait une information alors que le champ ne le concerne pas.
        const _estUsure = (o.usure_piece_id !== null && o.usure_piece_id !== undefined);
        const metrageDisplay = !_estUsure
          ? '<span style="color:var(--muted)">—</span>'
          : (o.metrage_ref ? esc(o.metrage_ref)
                           : '<span style="color:var(--muted);font-style:italic">À compléter</span>');
        const _arch = !!o.archived;
        const _archChip = _arch
          ? ' <span class="maint-arch-chip" title="Code archive : il porte des saisies, '
            + 'son libelle reste lisible dans l\'historique mais il n\'est plus '
            + 'proposé à la saisie.">archivé</span>'
          : '';
        body += '<tr' + (_arch ? ' class="maint-row-archived"' : '') + '>'
          + '<td class="op-code-cell">' + c + '</td>'
          + '<td class="op-lbl-cell">' + esc(o.label || '') + _archChip + '</td>'
          + '<td><span class="niv-badge" data-niv="' + niv + '">N' + niv + '</span></td>'
          + '<td><span class="op-pill ' + catCls + '">' + esc(_maintCatLabel(cat)) + '</span></td>'
          + '<td>' + intervalleDisplay + '</td>'
          + '<td>' + _maintUsureCell(o) + '</td>'
          + '<td>' + metrageDisplay + '</td>'
          + '<td><button type="button" class="btn-sm btn-ghost maint-docs-btn" data-maint-docs="' + c + '" title="Gerer les documents attaches a ce code">'
          +   '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:middle"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>'
          +   ' <span class="maint-docs-count" data-count="' + (o.docs_count || 0) + '">' + (o.docs_count || 0) + '</span>'
          + '</button></td>'
          + '<td><div class="op-act">'
          + (_arch
              ? '<button type="button" class="btn-sm btn-ghost" data-maint-restore="' + c + '">Réactiver</button>'
              : '<button type="button" class="btn-sm btn-ghost" data-maint-edit="' + c + '">Modifier</button>'
                + '<button type="button" class="btn-sm btn-ghost danger" data-maint-del="' + c + '">Supprimer</button>')
          + '</div></td></tr>';
      });
    });
    // Le bandeau est la seule trace visible des codes archives : sans lui,
    // un code disparu du catalogue passerait pour supprime.
    let bandeau = '';
    if (_archives.length) {
      bandeau = '<div class="maint-arch-bar">'
        + '<span>' + _archives.length + ' code(s) archivé(s)'
        + ' — retirés du catalogue, mais toujours lisibles dans l\'historique.</span>'
        + '<button type="button" class="btn-sm btn-ghost" id="maint-arch-toggle">'
        + (window._maintShowArchived ? 'Masquer' : 'Afficher') + '</button>'
        + '</div>';
    }
    el.innerHTML = bandeau + '<div class="table-wrap op-table-wrap"><table class="op-table"><thead><tr>'
      + '<th>Code</th><th>Libellé</th><th>Niveau</th><th>Catégorie</th><th>Intervalle de temps</th><th>Pièce d\'usure</th><th>Réf. métrage</th><th>Documents</th><th>Actions</th>'
      + '</tr></thead><tbody>' + body + '</tbody></table></div>';
    const _tgl = document.getElementById('maint-arch-toggle');
    if (_tgl) _tgl.addEventListener('click', () => {
      window._maintShowArchived = !window._maintShowArchived;
      renderMaintList();
    });
    el.querySelectorAll('[data-maint-edit]').forEach(btn => {
      btn.addEventListener('click', () => openMaintForm(btn.getAttribute('data-maint-edit')));
    });
    el.querySelectorAll('[data-maint-del]').forEach(btn => {
      btn.addEventListener('click', () => deleteMaintCode(btn.getAttribute('data-maint-del')));
    });
    el.querySelectorAll('[data-maint-docs]').forEach(btn => {
      btn.addEventListener('click', () => openMaintDocsModal(btn.getAttribute('data-maint-docs')));
    });
    el.querySelectorAll('[data-maint-restore]').forEach(btn => {
      btn.addEventListener('click', () => restoreMaintCode(btn.getAttribute('data-maint-restore')));
    });
  }

  // ── maintConfirm ──────────────────────────────────────────────────────
  // Remplacement de window.confirm pour les actions du catalogue.
  //
  // Pourquoi une modale maison plutot que confirm() : la boite native est
  // dessinee par le navigateur, pas par l'app. Elle ignore le theme clair /
  // sombre, elle tronque les retours a la ligne selon le navigateur, et elle
  // ne sait pas distinguer une action destructrice d'une action anodine.
  // Sur une action ou la nuance compte -- « supprime » contre « archive » --
  // ce n'est pas un detail cosmetique.
  //
  // Autonome a dessein : le style est injecte par le module (classes prefixees
  // mysifa-cfm-) et n'emprunte que les variables CSS communes aux deux pages
  // hotes. /settings n'a pas les classes .modal-* de /maintenance ; s'appuyer
  // dessus aurait donne une modale nue sur une page sur deux.
  //
  // Retourne une promesse resolue a true (confirme) ou false (annule).
  function maintConfirm(opts) {
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

  // ── restoreMaintCode ──
  // Sortie de secours de l'archivage : le code repasse dans le catalogue avec
  // son historique intact. Vit dans le module partage (et non dans les deux
  // pages hotes) pour ne pas recreer la duplication que ce fichier a supprimee.
  async function restoreMaintCode(code) {
    if (!code) return;
    const item = Array.isArray(_maintItems)
      ? _maintItems.find(x => String(x.code) === String(code)) : null;
    const ok = await maintConfirm({
      title: 'Réactiver le code ' + code,
      message: (item && item.label ? '« ' + item.label + ' »' : 'Ce code')
             + ' redevient disponible à la saisie.',
      detail: 'Il retrouve sa place dans le catalogue avec tout son historique. '
            + 'Aucune saisie passée n\'est modifiée.',
      confirmLabel: 'Réactiver',
    });
    if (!ok) return;
    try {
      await api('/api/maintenance/codes/' + encodeURIComponent(code) + '/restore',
                { method: 'POST' });
      toast('Code ' + code + ' réactivé');
    } catch (e) {
      toast(e && e.message ? e.message : 'Erreur lors de la réactivation', true);
      return;
    }
    await loadMaintCodes();
    // Le catalogue vient de changer : les listes deja chargees ailleurs dans la
    // page (modal « Enregistrer une operation », filtres) sont perimees.
    if (typeof window.maintOnCatalogueChanged === 'function') {
      try { await window.maintOnCatalogueChanged(); } catch (e) {}
    }
    if (typeof window.loadAlerts === 'function') { try { await window.loadAlerts(); } catch (e) {} }
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
      _maintFillUsureSelects(o.usure_piece_id, o.usure_position || '');
    } else {
      title.textContent = 'Nouveau code';
      codeInp.value = '';
      codeInp.disabled = false;
      document.getElementById('maint-label').value = '';
      document.getElementById('maint-niveau').value = '1';
      if (catSel) catSel.value = 'controles';
      if (intInp) intInp.value = '';
      if (mInp)   mInp.value   = '';
      _maintFillUsureSelects(null, '');
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
  // Les deux sont irreversibles hors SQL : la confirmation l'annonce et
  // rappelle le nombre de saisies impactees.
  //
  // Styles : le module est partage entre /maintenance et /settings, or les
  // classes .modal-card / .ops-input n'existent que dans maintenance_page.py.
  // On injecte donc une feuille autonome (prefixe .mlx-) qui reprend le design
  // system MyMaintenance a partir des variables CSS presentes sur les 2 pages.

  var _MLX_CSS = [
    '.mlx-overlay{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:1600;display:flex;align-items:center;justify-content:center;padding:20px;backdrop-filter:blur(2px)}',
    '.mlx-card{background:var(--card);border:1px solid var(--border);border-radius:14px;width:100%;max-width:560px;max-height:90vh;display:flex;flex-direction:column;box-shadow:0 20px 60px rgba(0,0,0,.45);overflow:hidden}',
    '.mlx-card--sm{max-width:440px}',
    '.mlx-head{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:18px 22px;border-bottom:1px solid var(--border)}',
    '.mlx-title{font-size:14px;font-weight:700;color:var(--text);text-transform:uppercase;letter-spacing:.5px}',
    '.mlx-close{background:transparent;border:none;color:var(--muted);cursor:pointer;padding:6px;border-radius:8px;display:inline-flex;align-items:center;transition:.15s;line-height:1}',
    '.mlx-close:hover{color:var(--danger);background:var(--bg)}',
    '.mlx-body{padding:20px 22px;overflow-y:auto;flex:1}',
    '.mlx-foot{display:flex;justify-content:flex-end;gap:8px;padding:14px 22px;border-top:1px solid var(--border);background:var(--bg)}',
    '.mlx-intro{font-size:13px;line-height:1.55;color:var(--text2);margin:0 0 16px}',
    '.mlx-intro strong{color:var(--text)}',
    '.mlx-label{display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}',
    '.mlx-label .req{color:var(--danger);margin-left:3px}',
    '.mlx-input,.mlx-select{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit;transition:border-color .15s,box-shadow .15s;width:100%;box-sizing:border-box}',
    '.mlx-input:focus,.mlx-select:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}',
    '.mlx-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px}',
    '.mlx-field{display:flex;flex-direction:column;margin-bottom:14px}',
    '.mlx-list{border:1px solid var(--border);border-radius:10px;background:var(--bg);max-height:232px;overflow-y:auto;padding:4px}',
    '.mlx-opt{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:8px;cursor:pointer;font-size:13px;color:var(--text2);transition:background .12s,color .12s}',
    '.mlx-opt:hover{background:var(--card);color:var(--text)}',
    '.mlx-opt.selected{background:var(--accent);color:var(--accent-fg,#fff);font-weight:600}',
    '.mlx-opt-code{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:11px;opacity:.75;min-width:32px}',
    '.mlx-opt-lab{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}',
    '.mlx-opt-cat{font-size:10px;text-transform:uppercase;letter-spacing:.4px;opacity:.7;white-space:nowrap}',
    '.mlx-empty{padding:16px;text-align:center;color:var(--muted);font-size:12px;font-style:italic}',
    '.mlx-note{font-size:11px;line-height:1.55;color:var(--muted);margin:12px 0 0}',
    '.mlx-btn{display:inline-flex;align-items:center;gap:8px;padding:10px 18px;border-radius:10px;border:1px solid var(--accent);background:var(--accent);color:var(--accent-fg,#fff);font-size:13px;font-weight:700;font-family:inherit;cursor:pointer;transition:.15s}',
    '.mlx-btn:hover{filter:brightness(1.07)}',
    '.mlx-btn:disabled{opacity:.5;cursor:not-allowed;filter:none}',
    '.mlx-btn--danger{background:var(--danger);border-color:var(--danger);color:#fff}',
    '.mlx-btn-ghost{display:inline-flex;align-items:center;gap:8px;padding:10px 16px;border-radius:10px;border:1px solid var(--border);background:transparent;color:var(--text2);font-size:13px;font-weight:600;font-family:inherit;cursor:pointer;transition:.15s}',
    '.mlx-btn-ghost:hover{border-color:var(--accent);color:var(--accent)}',
    '.mlx-recap{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:14px 16px;margin:0 0 14px;display:flex;flex-direction:column;gap:10px}',
    '.mlx-recap-row{display:flex;gap:12px;align-items:baseline}',
    '.mlx-recap-k{color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.5px;min-width:72px;flex-shrink:0}',
    '.mlx-recap-v{font-size:13px;color:var(--text);font-weight:600;line-height:1.4}',
    '.mlx-warn{display:flex;gap:9px;align-items:flex-start;font-size:12px;line-height:1.5;color:var(--danger);background:var(--bg);border:1px solid var(--danger);border-radius:10px;padding:11px 13px}',
    '.mlx-warn svg{flex-shrink:0;margin-top:1px}'
  ].join('\n');

  function _libresEnsureStyles() {
    if (document.getElementById('mlx-styles')) return;
    var st = document.createElement('style');
    st.id = 'mlx-styles';
    st.textContent = _MLX_CSS;
    (document.head || document.documentElement).appendChild(st);
  }

  var _MLX_CLOSE_SVG = '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
  var _MLX_WARN_SVG = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>';

  // Modal generique au style MyMaintenance (.modal-card).
  function _libresModal(title, bodyHtml, okLabel, opts) {
    _libresEnsureStyles();
    opts = opts || {};
    var overlay = document.createElement('div');
    overlay.className = 'mlx-overlay';
    overlay.innerHTML = '<div class="mlx-card' + (opts.small ? ' mlx-card--sm' : '') + '" role="dialog" aria-modal="true">'
      + '<div class="mlx-head"><div class="mlx-title">' + title + '</div>'
      +   '<button type="button" class="mlx-close" data-close aria-label="Fermer">' + _MLX_CLOSE_SVG + '</button></div>'
      + '<div class="mlx-body">' + bodyHtml + '</div>'
      + '<div class="mlx-foot">'
      +   '<button type="button" class="mlx-btn-ghost" data-close>Annuler</button>'
      +   '<button type="button" class="mlx-btn' + (opts.danger ? ' mlx-btn--danger' : '') + '" data-ok>' + okLabel + '</button>'
      + '</div></div>';
    document.body.appendChild(overlay);
    var close = function () { overlay.remove(); document.removeEventListener('keydown', onKey); };
    var onKey = function (e) { if (e.key === 'Escape') { close(); if (opts.onEscape) opts.onEscape(); } };
    document.addEventListener('keydown', onKey);
    overlay.querySelectorAll('[data-close]').forEach(function (el) {
      el.addEventListener('click', function () { close(); if (opts.onCancel) opts.onCancel(); });
    });
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) { close(); if (opts.onCancel) opts.onCancel(); }
    });
    return { overlay: overlay, close: close, okBtn: overlay.querySelector('[data-ok]') };
  }

  // Confirmation stylee (remplace window.confirm) -> Promise<boolean>.
  function _libresConfirm(title, bodyHtml, okLabel) {
    return new Promise(function (resolve) {
      var done = false;
      var settle = function (v) { if (!done) { done = true; resolve(v); } };
      var m = _libresModal(title, bodyHtml, okLabel, {
        small: true, danger: true,
        onCancel: function () { settle(false); },
        onEscape: function () { settle(false); },
      });
      m.okBtn.addEventListener('click', function () { m.close(); settle(true); });
      m.okBtn.focus();
    });
  }

  function _libresRecap(rows) {
    return '<div class="mlx-recap">' + rows.map(function (r) {
      return '<div class="mlx-recap-row"><div class="mlx-recap-k">' + r[0]
        + '</div><div class="mlx-recap-v">' + r[1] + '</div></div>';
    }).join('') + '</div>';
  }

  function _libresWarn(text) {
    return '<div class="mlx-warn">' + _MLX_WARN_SVG + '<span>' + text + '</span></div>';
  }

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
    const optsHtml = targets.map(function (t) {
      return '<div class="mlx-opt" data-code="' + esc(String(t.code)) + '" role="option">'
        + '<span class="mlx-opt-code">' + esc(String(t.code)) + '</span>'
        + '<span class="mlx-opt-lab">' + esc(String(t.label || '')) + '</span>'
        + '<span class="mlx-opt-cat">' + esc(_maintCatLabel(t.categorie)) + '</span>'
        + '</div>';
    }).join('');
    const body =
      '<p class="mlx-intro">Les <strong>' + _libresSaisiesLabel(it.usage_count) + '</strong> de « '
      + esc(it.label) + ' » seront rattachees a l’operation recurrente choisie et compteront comme des saisies recurrentes classiques. Le titre inhabituel disparaitra de la liste et de l’historique.</p>'
      + '<div class="mlx-field">'
      +   '<label class="mlx-label" for="libre-attach-filter">Operation recurrente cible<span class="req">*</span></label>'
      +   '<input type="search" id="libre-attach-filter" class="mlx-input" placeholder="Filtrer (code, libelle…)" style="margin-bottom:8px">'
      +   '<div class="mlx-list" id="libre-attach-list" role="listbox">' + optsHtml
      +     '<div class="mlx-empty" id="libre-attach-empty" style="display:none">Aucune operation pour ce filtre.</div>'
      +   '</div>'
      + '</div>'
      + '<p class="mlx-note">Si un creneau contient deja une saisie du code cible, les deux saisies sont fusionnees : observations et pieces concatenees, durees additionnees.</p>';
    const m = _libresModal('Rattacher · ' + esc(it.label), body, 'Rattacher');
    const list = m.overlay.querySelector('#libre-attach-list');
    const empty = m.overlay.querySelector('#libre-attach-empty');
    const filt = m.overlay.querySelector('#libre-attach-filter');
    let selected = null;
    m.okBtn.disabled = true;
    list.querySelectorAll('.mlx-opt').forEach(function (opt) {
      opt.addEventListener('click', function () {
        list.querySelectorAll('.mlx-opt').forEach(function (o) { o.classList.remove('selected'); });
        opt.classList.add('selected');
        selected = {
          code: opt.getAttribute('data-code'),
          label: opt.querySelector('.mlx-opt-lab').textContent,
        };
        m.okBtn.disabled = false;
      });
    });
    filt.addEventListener('input', function () {
      const q = filt.value.trim().toLowerCase();
      let visible = 0;
      list.querySelectorAll('.mlx-opt').forEach(function (o) {
        const hit = !q || o.textContent.toLowerCase().indexOf(q) !== -1;
        o.style.display = hit ? '' : 'none';
        if (hit) visible++;
      });
      empty.style.display = visible ? 'none' : '';
    });
    setTimeout(function () { try { filt.focus(); } catch (e) {} }, 30);

    m.okBtn.addEventListener('click', async function () {
      if (!selected) return;
      const ok = await _libresConfirm(
        'Confirmer le rattachement',
        _libresRecap([
          ['Titre', esc(it.label) + ' <span style="color:var(--muted);font-weight:400">(' + _libresSaisiesLabel(it.usage_count) + ')</span>'],
          ['Rattache a', esc(selected.code) + ' — ' + esc(selected.label)],
        ])
        + _libresWarn('Le titre inhabituel sera supprime et ses saisies compteront comme des saisies recurrentes. Action irreversible.'),
        'Rattacher'
      );
      if (!ok) return;
      m.okBtn.disabled = true;
      try {
        const r = await api('/api/maintenance/codes/libres/' + encodeURIComponent(code) + '/attach', {
          method: 'POST',
          body: JSON.stringify({ target_code: selected.code }),
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
      '<p class="mlx-intro">« ' + esc(it.label) + ' » devient une operation recurrente du catalogue. Ses <strong>'
      + _libresSaisiesLabel(it.usage_count) + '</strong> sont conservees : elles deviennent l’historique de la nouvelle operation, la carte Suivi machine affichera directement la derniere intervention.</p>'
      + '<div class="mlx-grid" style="margin-bottom:14px">'
      +   '<div class="mlx-field" style="margin-bottom:0"><label class="mlx-label" for="libre-promo-code">Code<span class="req">*</span></label>'
      +     '<input type="text" id="libre-promo-code" class="mlx-input" value="' + esc(nextCode) + '" inputmode="numeric" maxlength="4"></div>'
      +   '<div class="mlx-field" style="margin-bottom:0"><label class="mlx-label" for="libre-promo-niveau">Niveau</label>'
      +     '<select id="libre-promo-niveau" class="mlx-select">' + nivOpts + '</select></div>'
      +   '<div class="mlx-field" style="margin-bottom:0"><label class="mlx-label" for="libre-promo-cat">Categorie</label>'
      +     '<select id="libre-promo-cat" class="mlx-select">' + catOpts + '</select></div>'
      + '</div>'
      + '<div class="mlx-field"><label class="mlx-label" for="libre-promo-label">Libelle<span class="req">*</span></label>'
      +   '<input type="text" id="libre-promo-label" class="mlx-input" value="' + esc(it.label || '') + '"></div>'
      + '<div class="mlx-field"><label class="mlx-label" for="libre-promo-intervalle">Intervalle<span class="req">*</span></label>'
      +   '<input type="text" id="libre-promo-intervalle" class="mlx-input" placeholder="ex. Hebdo, 30 jours, 6 mois" maxlength="80"></div>'
      + '<div class="mlx-field" style="margin-bottom:0"><label class="mlx-label" for="libre-promo-metrage">Reference metrage (optionnel)</label>'
      +   '<input type="text" id="libre-promo-metrage" class="mlx-input" placeholder="ex. 5000 m, 10 km" maxlength="80"></div>'
      + '<p class="mlx-note">Sans intervalle, la carte ne peut pas calculer d’echeance : le champ est donc requis.</p>';
    const m = _libresModal('Transformer en recurrente · ' + esc(it.label), body, 'Transformer');
    setTimeout(function () {
      try { m.overlay.querySelector('#libre-promo-intervalle').focus(); } catch (e) {}
    }, 30);

    m.okBtn.addEventListener('click', async function () {
      const q = function (id) { return m.overlay.querySelector(id); };
      const newCode = q('#libre-promo-code').value.trim();
      const label = q('#libre-promo-label').value.trim();
      const intervalle = q('#libre-promo-intervalle').value.trim();
      const catSel = q('#libre-promo-cat');
      if (!newCode) { toast('Code obligatoire', true); q('#libre-promo-code').focus(); return; }
      if (!label) { toast('Libelle obligatoire', true); q('#libre-promo-label').focus(); return; }
      if (!intervalle) { toast('Intervalle obligatoire', true); q('#libre-promo-intervalle').focus(); return; }
      if (existing.some(function (t) { return String(t.code) === newCode; })) {
        toast('Le code ' + newCode + ' existe deja', true); q('#libre-promo-code').focus(); return;
      }
      const ok = await _libresConfirm(
        'Confirmer la transformation',
        _libresRecap([
          ['Nouveau code', esc(newCode) + ' — ' + esc(label)],
          ['Categorie', esc(catSel.options[catSel.selectedIndex].textContent) + ' · N' + q('#libre-promo-niveau').value + ' · ' + esc(intervalle)],
          ['Historique', _libresSaisiesLabel(it.usage_count) + ' reprise' + (it.usage_count > 1 ? 's' : '')],
        ])
        + _libresWarn('Le titre inhabituel « ' + esc(it.label) + ' » sera remplace par ce code du catalogue. Action irreversible.'),
        'Transformer'
      );
      if (!ok) return;
      m.okBtn.disabled = true;
      try {
        const r = await api('/api/maintenance/codes/libres/' + encodeURIComponent(code) + '/promote', {
          method: 'POST',
          body: JSON.stringify({
            new_code: newCode,
            label: label,
            niveau: parseInt(q('#libre-promo-niveau').value, 10) || 1,
            categorie: catSel.value,
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
  try { window.restoreMaintCode = restoreMaintCode; } catch(e) {}
  try { window.maintConfirm = maintConfirm; } catch(e) {}
  try { window.renderMaintList = renderMaintList; } catch(e) {}
  try { window.openMaintForm = openMaintForm; } catch(e) {}
  try { window.loadUsurePieces = loadUsurePieces; } catch(e) {}
  try { window._maintFillUsureSelects = _maintFillUsureSelects; } catch(e) {}
  try { window._maintUsureCell = _maintUsureCell; } catch(e) {}
  try { window.loadUsurePiecesAdmin = loadUsurePiecesAdmin; } catch(e) {}
  try { window.renderUsurePiecesList = renderUsurePiecesList; } catch(e) {}
  try { window.openUsurePieceForm = openUsurePieceForm; } catch(e) {}
  try { window.closeUsurePieceForm = closeUsurePieceForm; } catch(e) {}
  try { window.saveUsurePieceForm = saveUsurePieceForm; } catch(e) {}
  try { window.toggleUsurePiece = toggleUsurePiece; } catch(e) {}
  try { window.deleteUsurePiece = deleteUsurePiece; } catch(e) {}
  try { window._maintRefreshUsureUI = _maintRefreshUsureUI; } catch(e) {}
  try { window._maintOnUsurePieceChange = _maintOnUsurePieceChange; } catch(e) {}
  try { window._maintOnUsureToggle = _maintOnUsureToggle; } catch(e) {}
  try { window._maintOnCategorieChange = _maintOnCategorieChange; } catch(e) {}
  try { window._maintUsureAllowed = _maintUsureAllowed; } catch(e) {}
  try { window._maintOnUsureHasPosChange = _maintOnUsureHasPosChange; } catch(e) {}
  try { window._maintOnUsurePositionInput = _maintOnUsurePositionInput; } catch(e) {}
  try { window._maintUsurePayload = _maintUsurePayload; } catch(e) {}
  try { window._maintUsurePieceById = _maintUsurePieceById; } catch(e) {}
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
    restoreMaintCode: restoreMaintCode,
    maintConfirm: maintConfirm,
    renderMaintList: renderMaintList,
    openMaintForm: openMaintForm,
    openMaintDocsModal: openMaintDocsModal,
    loadUsurePieces: loadUsurePieces,
    _maintFillUsureSelects: _maintFillUsureSelects,
    loadUsurePiecesAdmin: loadUsurePiecesAdmin,
    renderUsurePiecesList: renderUsurePiecesList,
    openUsurePieceForm: openUsurePieceForm,
    saveUsurePieceForm: saveUsurePieceForm,
    _maintRefreshUsureUI: _maintRefreshUsureUI,
    _maintUsurePieceById: _maintUsurePieceById,
    loadLibres: loadLibres,
    renderLibresList: renderLibresList,
    openLibreAttachModal: openLibreAttachModal,
    openLibrePromoteModal: openLibrePromoteModal,
    MAINT_CODES_STORAGE_KEY: MAINT_CODES_STORAGE_KEY
  };
})();

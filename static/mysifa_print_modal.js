// MySifa Print Modal — v1.7
// Genere depuis app/web/print_modal.py — voir header de mysifa_print_modal.css.
// Wrapper toast/showToast (prod_core utilise toast(), fabrication utilise showToast()).

// ─── MySifa Print Modal — v1.7 ─────────────────────────────────────
// Popup partage : choix imprimante + options + submit vers POST /api/print/pdf

// Wrapper toast : mysifa_prod_core.js expose `toast(msg,type)` (defaut = success,
// type='error' pour erreur). D'autres pages exposent `showToast(msg,type)` (type
// = 'success' | 'danger'). On sniffe l'API disponible.
function _mysifaPrintToast(msg, type){
  // Normalise le type : 'danger' → 'error' pour toast(), inverse pour showToast()
  if(typeof toast === 'function'){
    var t = (type === 'danger') ? 'error' : (type === 'success' ? undefined : type);
    return toast(msg, t);
  }
  if(typeof showToast === 'function'){
    var t2 = (type === 'error') ? 'danger' : type;
    return showToast(msg, t2);
  }
  // Fallback console
  console.log('[print]', type || 'info', msg);
}

let _mysifaPrintState = null;

function _mysifaPrintEscHtml(s){
  return String(s==null?'':s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

async function openPrintModal(opts){
  opts = opts || {};
  if(!opts.entityType || !opts.entityId){
    _mysifaPrintToast('Impression : entityType/entityId requis.','danger');
    return;
  }
  _mysifaPrintClose();  // au cas ou un modal serait deja ouvert
  const backdrop = document.createElement('div');
  backdrop.className = 'mysifa-print-backdrop';
  backdrop.id = '_mysifa_print_backdrop';
  backdrop.addEventListener('click', function(e){
    if(e.target === backdrop) _mysifaPrintClose();
  });
  document.addEventListener('keydown', _mysifaPrintOnKey);
  const title = opts.title || 'Imprimer le document';
  const subtitle = opts.subtitle || '';
  backdrop.innerHTML = `
    <div class="mysifa-print-modal" role="dialog" aria-modal="true">
      <div class="mysifa-print-head">
        <div class="mysifa-print-head-info">
          <h3 class="mysifa-print-title">${_mysifaPrintEscHtml(title)}</h3>
          ${subtitle ? `<p class="mysifa-print-subtitle">${_mysifaPrintEscHtml(subtitle)}</p>` : ''}
        </div>
        <button type="button" class="mysifa-print-close" onclick="_mysifaPrintClose()" title="Fermer" aria-label="Fermer">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
      <div class="mysifa-print-body" id="_mysifa_print_body">
        <div class="mysifa-print-loading">Chargement des imprimantes…</div>
      </div>
      <div class="mysifa-print-foot">
        <button type="button" class="mysifa-print-btn" onclick="_mysifaPrintClose()">Annuler</button>
        <button type="button" class="mysifa-print-btn primary" id="_mysifa_print_submit" disabled onclick="_mysifaPrintSubmit()">Imprimer</button>
      </div>
    </div>
  `;
  document.body.appendChild(backdrop);
  _mysifaPrintState = {
    entityType: opts.entityType,
    entityId: opts.entityId,
    printers: [],
    defaults: {},
    usageKey: opts.entityType === 'of' ? 'of_document' : 'fiche_technique',
    form: null,
  };
  await _mysifaPrintLoad();
}

function _mysifaPrintClose(){
  const el = document.getElementById('_mysifa_print_backdrop');
  if(el) el.remove();
  document.removeEventListener('keydown', _mysifaPrintOnKey);
  _mysifaPrintState = null;
}

function _mysifaPrintOnKey(e){
  if(e.key === 'Escape'){ e.preventDefault(); _mysifaPrintClose(); }
}

async function _mysifaPrintLoad(){
  const body = document.getElementById('_mysifa_print_body');
  if(!body || !_mysifaPrintState) return;
  try{
    // Recupere imprimantes + defauts en parallele
    const [imps, defaults] = await Promise.all([
      _mysifaPrintApi('/api/print/my-imprimantes'),
      _mysifaPrintApi('/api/print/my-defaults'),
    ]);
    _mysifaPrintState.printers = Array.isArray(imps) ? imps.filter(p => p.langage === 'pdf') : [];
    _mysifaPrintState.defaults = defaults || {};
    _mysifaPrintRenderForm();
  }catch(err){
    body.innerHTML = `<div class="mysifa-print-empty">
      Impossible de charger les imprimantes.<br>
      <span style="font-size:11px">${_mysifaPrintEscHtml((err && err.message) || err)}</span>
    </div>`;
  }
}

// Wrapper API compatible avec les 3 conventions rencontrees dans MySifa :
// - apiFetch(path, opts)  qui retourne le JSON parse (fabrication_page)
// - api(path, opts)       qui retourne le JSON parse (settings, print, stock)
// - api(path, opts)       qui retourne le Response de fetch (qualite)
// Fallback direct sur fetch() si aucun de ces helpers n'existe.
async function _mysifaPrintApi(path, opts){
  opts = opts || {};
  // On serialize le body en JSON si c'est un objet (ce que fetch attend, et ce
  // que apiFetch/api gerent bien en general).
  if(opts.body && typeof opts.body !== 'string'){
    opts = Object.assign({}, opts, {
      body: JSON.stringify(opts.body),
      headers: Object.assign({'Content-Type': 'application/json'}, opts.headers || {}),
    });
  }
  const _handleResponse = async function(r){
    if(r && typeof r.ok === 'boolean' && typeof r.json === 'function'){
      if(!r.ok){
        let detail = 'HTTP ' + r.status;
        try{ const j = await r.json(); if(j && j.detail) detail = j.detail; }catch(e){}
        const err = new Error(detail); err.status = r.status; throw err;
      }
      return await r.json();
    }
    return r;  // deja JSON parse
  };
  if(typeof apiFetch === 'function'){
    return await apiFetch(path, opts);
  }
  if(typeof api === 'function'){
    const r = await api(path, opts);
    return await _handleResponse(r);
  }
  // Fallback fetch direct
  const init = Object.assign({method: opts.method || 'GET', credentials: 'include'}, opts);
  const r = await fetch(path, init);
  return await _handleResponse(r);
}

function _mysifaPrintRenderForm(){
  const body = document.getElementById('_mysifa_print_body');
  const submit = document.getElementById('_mysifa_print_submit');
  const st = _mysifaPrintState;
  if(!body || !st) return;

  if(!st.printers.length){
    body.innerHTML = `<div class="mysifa-print-empty">
      Aucune imprimante bureautique (PDF) n'est configuree.<br>
      Un administrateur peut en ajouter dans <a href="/settings" style="color:var(--accent)">Parametres &gt; Imprimantes</a>
      (type de connexion : Locale Windows, langage : PDF).
    </div>`;
    if(submit) submit.disabled = true;
    return;
  }

  // Imprimante par defaut pour cet usage
  const defImpId = st.defaults[st.usageKey];
  const selected = st.printers.find(p => p.id === defImpId) || st.printers[0];

  st.form = {
    imprimante_id: selected.id,
    copies: 1,
    duplex: 'simplex',
    format: 'A4',
    bin: '',
    color: 'color',
  };

  const impOpts = st.printers.map(p => {
    const label = p.poste ? `${_mysifaPrintEscHtml(p.nom)} — ${_mysifaPrintEscHtml(p.poste)}` : _mysifaPrintEscHtml(p.nom);
    return `<option value="${p.id}" ${p.id === selected.id ? 'selected' : ''}>${label}</option>`;
  }).join('');

  body.innerHTML = `
    <div class="mysifa-print-field">
      <label class="mysifa-print-label">Imprimante</label>
      <select class="mysifa-print-select" id="_mp_imp" onchange="_mysifaPrintFieldChange('imprimante_id', this.value, true)">${impOpts}</select>
    </div>

    <div class="mysifa-print-row">
      <div class="mysifa-print-field">
        <label class="mysifa-print-label">Copies</label>
        <input type="number" min="1" max="99" value="1" class="mysifa-print-input" id="_mp_copies"
               oninput="_mysifaPrintFieldChange('copies', this.value, true)">
      </div>
      <div class="mysifa-print-field">
        <label class="mysifa-print-label">Format</label>
        <select class="mysifa-print-select" id="_mp_format" onchange="_mysifaPrintFieldChange('format', this.value)">
          <option value="A4" selected>A4</option>
          <option value="A5">A5</option>
          <option value="A3">A3</option>
          <option value="Letter">Letter</option>
          <option value="Legal">Legal</option>
        </select>
      </div>
    </div>

    <div class="mysifa-print-field">
      <label class="mysifa-print-label">Recto/Verso</label>
      <div class="mysifa-print-radios" id="_mp_duplex">
        <div class="mysifa-print-radio checked" data-val="simplex" onclick="_mysifaPrintRadio('duplex','simplex',this)">Recto seul</div>
        <div class="mysifa-print-radio" data-val="long-edge" onclick="_mysifaPrintRadio('duplex','long-edge',this)">Recto/verso (bord long)</div>
        <div class="mysifa-print-radio" data-val="short-edge" onclick="_mysifaPrintRadio('duplex','short-edge',this)">Recto/verso (bord court)</div>
      </div>
    </div>

    <div class="mysifa-print-row">
      <div class="mysifa-print-field">
        <label class="mysifa-print-label">Bac papier (optionnel)</label>
        <input type="text" placeholder="ex: Bac 1, Tray2…" class="mysifa-print-input" id="_mp_bin"
               oninput="_mysifaPrintFieldChange('bin', this.value)">
      </div>
      <div class="mysifa-print-field">
        <label class="mysifa-print-label">Couleur</label>
        <label class="mysifa-print-toggle" id="_mp_mono_wrap">
          <input type="checkbox" id="_mp_mono" onchange="_mysifaPrintToggleMono(this)">
          <span>Noir &amp; blanc</span>
        </label>
      </div>
    </div>

    <p class="mysifa-print-hint">
      Le PDF est envoye a votre agent d'impression local ; il apparait sur l'imprimante en quelques secondes.
      <span id="_mp_imp_meta"></span>
    </p>
  `;
  _mysifaPrintUpdateImpMeta();
  if(submit) submit.disabled = false;
}

function _mysifaPrintFieldChange(field, value, isNum){
  if(!_mysifaPrintState || !_mysifaPrintState.form) return;
  if(isNum){
    const n = parseInt(value, 10);
    _mysifaPrintState.form[field] = isNaN(n) ? 1 : n;
  } else {
    _mysifaPrintState.form[field] = value;
  }
  if(field === 'imprimante_id') _mysifaPrintUpdateImpMeta();
}

function _mysifaPrintRadio(field, val, el){
  if(!_mysifaPrintState || !_mysifaPrintState.form) return;
  _mysifaPrintState.form[field] = val;
  const parent = el.parentNode;
  parent.querySelectorAll('.mysifa-print-radio').forEach(r => r.classList.remove('checked'));
  el.classList.add('checked');
}

function _mysifaPrintToggleMono(cb){
  if(!_mysifaPrintState || !_mysifaPrintState.form) return;
  _mysifaPrintState.form.color = cb.checked ? 'monochrome' : 'color';
  const wrap = document.getElementById('_mp_mono_wrap');
  if(wrap) wrap.classList.toggle('checked', cb.checked);
}

function _mysifaPrintUpdateImpMeta(){
  const meta = document.getElementById('_mp_imp_meta');
  const st = _mysifaPrintState;
  if(!meta || !st) return;
  const imp = st.printers.find(p => p.id === parseInt(st.form.imprimante_id, 10));
  if(!imp){ meta.textContent = ''; return; }
  meta.innerHTML = imp.poste
    ? ` <span style="opacity:.7">— cible : ${_mysifaPrintEscHtml(imp.nom)} (${_mysifaPrintEscHtml(imp.poste)})</span>`
    : ` <span style="opacity:.7">— cible : ${_mysifaPrintEscHtml(imp.nom)}</span>`;
}

async function _mysifaPrintSubmit(){
  const st = _mysifaPrintState;
  const submit = document.getElementById('_mysifa_print_submit');
  if(!st || !st.form) return;
  if(submit){ submit.disabled = true; submit.textContent = 'Envoi…'; }
  try{
    const body = {
      entity_type: st.entityType,
      entity_id: st.entityId,
      imprimante_id: parseInt(st.form.imprimante_id, 10),
      copies: Math.max(1, Math.min(99, parseInt(st.form.copies, 10) || 1)),
      duplex: st.form.duplex,
      format: st.form.format,
      bin: st.form.bin || null,
      color: st.form.color,
    };
    const r = await _mysifaPrintApi('/api/print/pdf', {method: 'POST', body: body});
    _mysifaPrintToast(`Impression envoyee a ${r.imprimante || 'l\'imprimante'}.`, 'success');
    _mysifaPrintClose();
  }catch(err){
    _mysifaPrintToast('Impression impossible : ' + ((err && err.message) || err), 'danger');
    if(submit){ submit.disabled = false; submit.textContent = 'Imprimer'; }
  }
}

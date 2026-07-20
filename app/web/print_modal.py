"""
MySifa — Modal d'impression PDF partage (v1.7).

Compose CSS + JS + fonction Python renvoyant l'HTML minimal a injecter dans une
page. Concu pour etre inclus dans n'importe quelle page qui doit ouvrir un
popup "choisir imprimante + options + imprimer un PDF".

Utilisation (cote page qui integre) :

    from app.web.print_modal import PRINT_MODAL_CSS, PRINT_MODAL_JS

    # Dans le <style> de la page :
    style_html += PRINT_MODAL_CSS

    # Dans le <script> de la page (apres les helpers `api()`, `showToast()`) :
    script_js += PRINT_MODAL_JS

Cote frontend, appeler :

    openPrintModal({
        entityType: 'of' | 'fiche',
        entityId: 42,
        title: 'Imprimer OF-2026-042',           // affiche dans l'entete
        subtitle: 'Client Machin — Ref XYZ',     // optionnel
    });

Le popup se charge du reste : liste des imprimantes (langage=pdf uniquement),
defauts utilisateur, params (copies/duplex/format/bac/N&B), soumission a
POST /api/print/pdf, toasts de succes/erreur.

Le popup depend de :
  - api(path, opts)     — helper HTTP (deja present partout dans MySifa)
  - showToast(msg,type) — deja present dans html.py

Il ne depend pas de framework externe et respecte le design system MySifa
(variables CSS --bg, --card, --border, --text, --accent, --danger, --warn...).
"""

from __future__ import annotations


# ═══════════════════════════════════════════════════════════════════════
# CSS
# ═══════════════════════════════════════════════════════════════════════

PRINT_MODAL_CSS = """
/* MySifa Print Modal — v1.7 */
.mysifa-print-backdrop{
  position:fixed;inset:0;background:rgba(2,6,15,.72);backdrop-filter:blur(3px);
  z-index:99998;display:flex;align-items:center;justify-content:center;
  animation:mysifa-print-fade .15s ease-out;
}
body.light .mysifa-print-backdrop{background:rgba(15,23,42,.45)}
@keyframes mysifa-print-fade{from{opacity:0}to{opacity:1}}
.mysifa-print-modal{
  background:var(--card);border:1px solid var(--border);border-radius:14px;
  width:min(520px,92vw);max-height:88vh;overflow:hidden;
  display:flex;flex-direction:column;
  box-shadow:0 20px 60px -12px rgba(0,0,0,.6);
  animation:mysifa-print-pop .18s cubic-bezier(.16,1,.3,1);
}
@keyframes mysifa-print-pop{from{opacity:0;transform:translateY(8px) scale(.98)}to{opacity:1;transform:none}}
.mysifa-print-head{
  padding:18px 22px 14px;border-bottom:1px solid var(--border);
  display:flex;align-items:flex-start;justify-content:space-between;gap:12px;
}
.mysifa-print-head-info{min-width:0;flex:1}
.mysifa-print-title{
  font-size:16px;font-weight:700;color:var(--text);margin:0 0 4px 0;
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
}
.mysifa-print-subtitle{font-size:12px;color:var(--muted);margin:0}
.mysifa-print-close{
  background:transparent;border:0;padding:4px;cursor:pointer;color:var(--muted);
  border-radius:6px;transition:background .12s,color .12s;line-height:0;
}
.mysifa-print-close:hover{background:var(--bg);color:var(--text)}
.mysifa-print-body{padding:16px 22px;overflow-y:auto;display:flex;flex-direction:column;gap:14px}
.mysifa-print-loading{
  padding:32px 0;text-align:center;color:var(--muted);font-size:13px;
}
.mysifa-print-empty{
  padding:24px 16px;text-align:center;color:var(--muted);
  border:1px dashed var(--border);border-radius:10px;font-size:13px;line-height:1.6;
}
.mysifa-print-field{display:flex;flex-direction:column;gap:6px}
.mysifa-print-label{
  font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;
  letter-spacing:.5px;
}
.mysifa-print-select,.mysifa-print-input{
  background:var(--bg);border:1px solid var(--border);border-radius:10px;
  padding:10px 12px;color:var(--text);font-size:13px;
  transition:border-color .12s,box-shadow .12s;font-family:inherit;
}
.mysifa-print-select:focus,.mysifa-print-input:focus{
  outline:none;border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12);
}
.mysifa-print-row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
@media(max-width:520px){.mysifa-print-row{grid-template-columns:1fr}}
.mysifa-print-radios{display:flex;gap:8px;flex-wrap:wrap}
.mysifa-print-radio{
  flex:1;min-width:80px;padding:8px 10px;background:var(--bg);border:1px solid var(--border);
  border-radius:8px;cursor:pointer;text-align:center;font-size:12px;color:var(--text2);
  transition:all .12s;user-select:none;
}
.mysifa-print-radio:hover{border-color:var(--accent)}
.mysifa-print-radio.checked{
  background:var(--accent-bg);border-color:var(--accent);color:var(--accent);font-weight:600;
}
.mysifa-print-toggle{
  display:flex;align-items:center;gap:10px;padding:10px 12px;background:var(--bg);
  border:1px solid var(--border);border-radius:10px;cursor:pointer;font-size:13px;
  color:var(--text2);user-select:none;transition:border-color .12s;
}
.mysifa-print-toggle:hover{border-color:var(--accent)}
.mysifa-print-toggle input{margin:0;accent-color:var(--accent)}
.mysifa-print-toggle.checked{color:var(--text)}
.mysifa-print-foot{
  padding:14px 22px;border-top:1px solid var(--border);
  display:flex;justify-content:flex-end;gap:8px;background:var(--bg);
}
.mysifa-print-btn{
  padding:9px 16px;border-radius:9px;border:1px solid var(--border);
  background:transparent;color:var(--text);font-size:13px;font-weight:600;
  cursor:pointer;transition:filter .12s,border-color .12s,background .12s;
  font-family:inherit;
}
.mysifa-print-btn:hover:not(:disabled){filter:brightness(1.05);border-color:var(--accent)}
.mysifa-print-btn:disabled{opacity:.5;cursor:not-allowed}
.mysifa-print-btn.primary{
  background:var(--accent);border-color:var(--accent);color:#04121a;
}
.mysifa-print-btn.primary:hover:not(:disabled){filter:brightness(1.08);border-color:var(--accent)}
body.light .mysifa-print-btn.primary{color:#fff}
.mysifa-print-hint{
  font-size:11px;color:var(--muted);margin:0;line-height:1.5;
}
.mysifa-print-hint a{color:var(--accent);text-decoration:none}
.mysifa-print-hint a:hover{text-decoration:underline}
.mysifa-print-imp-meta{
  font-size:11px;color:var(--muted);margin-top:4px;
}
"""


# ═══════════════════════════════════════════════════════════════════════
# JS
# ═══════════════════════════════════════════════════════════════════════
#
# Fournit :
#   - openPrintModal(opts)       — API publique
#   - _mysifaPrintClose()        — ferme le modal (Escape ou clic backdrop)
#   - _mysifaPrintSubmit()       — POST /api/print/pdf
#   - _mysifaPrintLoad(opts)     — charge imprimantes + defauts et rend le form
#
# Le modal est injecte dans document.body via un div temporaire, pas dans
# #mroot, pour ne pas entrer en conflit avec les autres modals des pages.

PRINT_MODAL_JS = r"""
// ─── MySifa Print Modal — v1.7 ─────────────────────────────────────
// Popup partage : choix imprimante + options + submit vers POST /api/print/pdf

let _mysifaPrintState = null;

function _mysifaPrintEscHtml(s){
  return String(s==null?'':s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}

async function openPrintModal(opts){
  opts = opts || {};
  if(!opts.entityType || !opts.entityId){
    if(typeof showToast==='function') showToast('Impression : entityType/entityId requis.','danger');
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
    if(typeof showToast === 'function'){
      showToast(`Impression envoyee a ${r.imprimante || 'l\'imprimante'}.`, 'success');
    }
    _mysifaPrintClose();
  }catch(err){
    if(typeof showToast === 'function'){
      showToast('Impression impossible : ' + ((err && err.message) || err), 'danger');
    }
    if(submit){ submit.disabled = false; submit.textContent = 'Imprimer'; }
  }
}
"""


def print_modal_bundle() -> tuple[str, str]:
    """Renvoie le tuple (css, js) a injecter dans une page qui veut le modal.

    Utilise ainsi dans les pages :

        from app.web.print_modal import print_modal_bundle
        css_extra, js_extra = print_modal_bundle()
    """
    return PRINT_MODAL_CSS, PRINT_MODAL_JS

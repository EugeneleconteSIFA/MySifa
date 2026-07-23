/**
 * mysifa_ack_viewer.js — Viewer partagé pour visualiser une alerte validée.
 *
 * Source de vérité unique du modal détail d'un ack d'alerte, utilisé par :
 *   - /maintenance (via maintenance_page.py, ouvert au clic dans l'historique)
 *   - /prod       (via html.py, ouvert au clic sur une ligne kind=alert_ack)
 *
 * API publique :
 *   window.MysifaAckViewer.open(ack)
 *     ack = {
 *       alert_nom      : string,   // titre affiché en haut du modal
 *       responses      : object,   // map { "<idx>": value|array, "<idx>_other": string }
 *       checklist_items: array,    // items du checklist (voir _renderChecklist)
 *       comment        : string,   // commentaire libre opérateur (peut être vide)
 *       machine        : string,
 *       date           : string,   // format libre — sera passé à new Date()
 *       operateur      : string,
 *       no_dossier     : string,   // affiché en badge sous la checklist si non vide
 *     }
 *
 *   window.MysifaAckViewer.close()  // ferme le modal si ouvert
 *
 * Design : reprend fidèlement les classes CSS du runtime des alertes
 * (mysifa_alert_runtime.js) — .ta-sim, .ta-sim-alert, .ta-sim-title,
 * .ta-sim-sub, .ta-chip, .ta-cl-item, .ta-sim-actions, .ta-sim-btn.
 * Les CSS sont injectées à la volée si absentes (idempotent).
 */
(function(){
  'use strict';
  if(window.MysifaAckViewer) return;  // évite double-init

  const OVERLAY_ID = 'mysifa-ack-viewer-overlay';
  const STYLE_ID   = 'mysifa-ack-viewer-css';

  function _esc(s){
    return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function _fmtDate(v){
    try{
      if(!v) return '';
      const d = new Date(v);
      if(isNaN(d)) return String(v);
      const pad = n=>String(n).padStart(2,'0');
      return pad(d.getDate())+'/'+pad(d.getMonth()+1)+'/'+d.getFullYear()
        +' '+pad(d.getHours())+':'+pad(d.getMinutes())+':'+pad(d.getSeconds());
    }catch(e){ return String(v); }
  }

  function _injectCss(){
    if(document.getElementById(STYLE_ID)) return;
    const s = document.createElement('style');
    s.id = STYLE_ID;
    s.textContent = [
      // Backdrop plein écran + card centrée — identique au runtime des alertes
      '.ta-sim{position:fixed;inset:0;z-index:2000;pointer-events:none;box-sizing:border-box}',
      '.ta-sim.ta-blocking{background:rgba(0,0,0,.45);pointer-events:auto;animation:mysifaAckFade .15s ease-out}',
      '.ta-sim.ta-pl-center .ta-sim-alert{position:fixed;top:50%;left:50%;right:auto;bottom:auto;transform:translate(-50%,-50%)}',
      // v2.3.44 : largeur réduite (560 → 460) et max-height plus contrainte (85vh) pour un modal plus compact et scrollable.
      '.ta-sim-alert{background:var(--card);border:2px solid var(--accent);border-radius:12px;box-shadow:0 16px 48px rgba(0,0,0,.5);padding:16px 18px;max-height:85vh;overflow-y:auto;pointer-events:auto;box-sizing:border-box;width:460px;max-width:calc(100vw - 40px);animation:mysifaAckSlide .2s ease-out}',
      '.ta-sim-title{font-size:18px;font-weight:700;color:var(--text);margin-bottom:8px;padding-bottom:12px;border-bottom:2px solid var(--accent);line-height:1.3;letter-spacing:-0.01em}',
      '.ta-sim-sub{font-size:12px;color:var(--text2);margin-bottom:14px;letter-spacing:.2px}',
      '.ta-sim-actions{display:flex;gap:6px;margin-top:14px}',
      '.ta-sim-btn{flex:1;padding:9px;border-radius:8px;font-size:13px;font-weight:600;border:none;cursor:pointer;font-family:inherit;background:var(--accent);color:#fff}',
      '.ta-sim-btn:hover{filter:brightness(1.05)}',
      // Checklist item + chips (choix cochés en accent)
      '.ta-cl-item{display:flex;flex-direction:column;gap:6px}',
      '.ta-chip{display:inline-flex;align-items:center;padding:5px 11px;border-radius:999px;border:1.5px solid var(--border);background:var(--bg);color:var(--text);font-size:12px;font-weight:500;user-select:none;font-family:inherit;line-height:1.2;position:relative}',
      '.ta-chip input{position:absolute;opacity:0;width:0;height:0;pointer-events:none}',
      '.ta-chip:has(input:checked){background:var(--accent);color:#fff;border-color:var(--accent)}',
      '.ta-chip span{white-space:nowrap}',
      // Badge dossier (repris de ack-di-badge du runtime)
      '.mysifa-ack-viewer-badge{display:inline-flex;align-items:center;padding:5px 11px;border-radius:8px;border:1px solid var(--accent);background:var(--accent-bg);color:var(--accent);font-size:12px;font-weight:600}',
      // Animations
      '@keyframes mysifaAckFade{from{opacity:0}to{opacity:1}}',
      '@keyframes mysifaAckSlide{from{opacity:0;transform:translate(-50%,-48%)}to{opacity:1;transform:translate(-50%,-50%)}}',
      // Mobile
      '@media(max-width:600px){.ta-sim-alert{width:calc(100vw - 24px) !important;max-width:calc(100vw - 24px) !important;padding:14px}}',
    ].join('\n');
    document.head.appendChild(s);
  }

  function _renderChecklist(items, responses){
    if(!Array.isArray(items) || !items.length) return '';
    const rows = items.map((it, idx)=>{
      const r = responses ? responses[String(idx)] : undefined;
      if(it && it.type === 'value'){
        const val  = (r != null && r !== '') ? String(r) : '';
        const unit = it.unit
          ? '<span style="font-size:12px;color:var(--text2);font-weight:500;min-width:24px">'+_esc(it.unit)+'</span>'
          : '';
        return '<div class="ta-cl-item" data-type="value">'
          +   '<div style="font-size:12px;font-weight:600;color:var(--text);margin-bottom:4px">'+_esc(it.label||'')+'</div>'
          +   '<div style="display:flex;align-items:center;gap:8px">'
          +     '<input type="text" disabled value="'+_esc(val)+'" style="flex:1;padding:6px 10px;border-radius:7px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:13px;font-family:inherit;box-sizing:border-box;opacity:.85">'
          +     unit
          +   '</div>'
          + '</div>';
      }
      // choice : chips cochés uniquement
      const selected = Array.isArray(r) ? r : (r != null ? [String(r)] : []);
      const respHtml = selected.length
        ? selected.map(s => '<label class="ta-chip"><input type="checkbox" disabled checked><span>'+_esc(s)+'</span></label>').join(' ')
        : '<span style="font-size:12px;color:var(--muted);font-style:italic">Aucune réponse cochée</span>';
      const otherTxt = responses ? responses[String(idx)+'_other'] : undefined;
      const otherHtml = (otherTxt != null && String(otherTxt).trim() !== '')
        ? '<div style="margin-top:6px;padding:6px 10px;border-left:3px solid var(--accent);background:var(--accent-bg);border-radius:0 6px 6px 0;font-size:12px;color:var(--text2);white-space:pre-wrap">'+_esc(String(otherTxt))+'</div>'
        : '';
      return '<div class="ta-cl-item" data-type="choice">'
        +   '<div style="font-size:12px;font-weight:600;color:var(--text);margin-bottom:4px">'+_esc(it.label||'')+'</div>'
        +   '<div style="display:flex;flex-wrap:wrap;gap:5px">'+respHtml+'</div>'
        +   otherHtml
        + '</div>';
    }).join('');
    return '<label style="display:block;font-size:10px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px">Points de contrôle</label>'
      + '<div style="display:flex;flex-direction:column;gap:10px;margin-bottom:10px">'+rows+'</div>';
  }

  function close(){
    const el = document.getElementById(OVERLAY_ID);
    if(el){ try{ el.remove(); }catch(_){} }
    document.removeEventListener('keydown', _escHandler);
  }

  function _escHandler(e){ if(e && e.key === 'Escape') close(); }

  function open(ack){
    if(!ack || typeof ack !== 'object') return;
    _injectCss();
    // Ferme un modal précédent éventuel
    const prev = document.getElementById(OVERLAY_ID);
    if(prev){ try{ prev.remove(); }catch(_){} }

    const items      = Array.isArray(ack.checklist_items) ? ack.checklist_items : [];
    const responses  = (ack.responses && typeof ack.responses === 'object') ? ack.responses : {};
    const commentTxt = String(ack.comment || '');
    const contextLine = _esc(ack.machine||'—') + ' · ' + _esc(_fmtDate(ack.date)) + ' · ' + _esc(ack.operateur||'—');
    const noDos = String(ack.no_dossier || '').trim();
    const dossierHtml = noDos
      ? '<div style="margin:12px 0 6px 0"><span class="mysifa-ack-viewer-badge">Dossier '+_esc(noDos)+'</span></div>'
      : '';

    const overlay = document.createElement('div');
    overlay.className = 'ta-sim ta-pl-center ta-blocking';
    overlay.id = OVERLAY_ID;
    overlay.innerHTML = '<div class="ta-sim-alert">'
      + '<div class="ta-sim-title">'+_esc(ack.alert_nom || 'Alerte')+'</div>'
      + '<div class="ta-sim-sub">'+contextLine+'</div>'
      + _renderChecklist(items, responses)
      + dossierHtml
      + '<label style="display:block;font-size:10px;font-weight:600;color:var(--text2);text-transform:uppercase;letter-spacing:.5px;margin:8px 0 4px 0">Commentaire</label>'
      + '<textarea disabled rows="2" placeholder="(aucun commentaire)" style="width:100%;padding:7px 10px;border-radius:7px;border:1px solid var(--border);background:var(--bg);color:var(--text);font-size:12px;box-sizing:border-box;resize:vertical;font-family:inherit;opacity:.85">'+_esc(commentTxt)+'</textarea>'
      + '<div class="ta-sim-actions">'
      +   '<button type="button" class="ta-sim-btn" data-close>Fermer</button>'
      + '</div>'
      + '</div>';
    document.body.appendChild(overlay);
    overlay.addEventListener('click', (e)=>{ if(e.target === overlay) close(); });
    overlay.querySelectorAll('[data-close]').forEach(btn=>btn.addEventListener('click', close));
    document.addEventListener('keydown', _escHandler);
  }

  window.MysifaAckViewer = { open: open, close: close };
})();

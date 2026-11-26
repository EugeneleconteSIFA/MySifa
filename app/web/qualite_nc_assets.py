"""MyQualité — Non-conformités : liste, fiche, archives, création.

Injecté dans app/web/qualite_page.py (`__NC_CSS__` dans le <style>,
`__NC_JS__` dans le script principal). Partage l'état `S`, `api()`,
`escHtml()`, `fmtDate()` et `showToast()` de la page.

Parcours voulu simple, lisible par quelqu'un qui arrive :
  liste des NC en cours (client, produit, dernière étape, alerte si rien n'a
  bougé depuis NC_RELANCE_JOURS jours) → fiche d'une NC en sections
  (la NC, photos et documents, cause, actions correctives, suivi) →
  « Clôturer et archiver » / « Rouvrir » ; bouton « Archives » sur la liste.
"""

NC_CSS = r"""
.ncx .btn-ghost{background:var(--card)}
.ncx .card .btn-ghost,.ncx .modal .btn-ghost{background:var(--bg)}
.ncx .btn-ghost:hover{background:var(--bg)}
.ncx .card .btn-ghost:hover,.ncx .modal .btn-ghost:hover{background:var(--card)}
.ncx .btn-accent{color:white}
.ncx .form-input,.ncx .form-select,.ncx .form-textarea{background:var(--card)}
.ncx .form-input:disabled,.ncx .form-select:disabled,.ncx .form-textarea:disabled{color:var(--text2);cursor:default}

.nc-kpis{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}
.nc-kpi{flex:1 1 180px;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 16px;display:flex;align-items:center;gap:12px}
.nc-kpi-val{font-size:26px;font-weight:800;line-height:1;color:var(--text)}
.nc-kpi-lbl{font-size:12px;color:var(--text2);line-height:1.35}
.nc-kpi.warn{border-color:color-mix(in srgb,var(--warn) 55%,var(--border))}
.nc-kpi.warn .nc-kpi-val{color:var(--warn)}

.nc-list{display:flex;flex-direction:column;gap:8px}
.nc-row{display:grid;grid-template-columns:minmax(170px,1.1fr) minmax(130px,.8fr) minmax(220px,2fr) 150px;gap:16px;align-items:center;background:var(--card);border:1px solid var(--border);border-left:4px solid var(--border);border-radius:12px;padding:12px 16px;cursor:pointer;text-align:left;font-family:inherit;color:var(--text);width:100%;transition:border-color .15s,background .15s}
.nc-row:hover{border-color:var(--accent);background:var(--bg)}
.nc-row.relance{border-left-color:var(--warn)}
.nc-row-head{display:none}
.nc-cell-lbl{display:none;font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:2px}
.nc-client{font-weight:700;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nc-num{font-family:ui-monospace,monospace;font-size:11px;color:var(--muted);margin-top:3px}
.nc-prod{font-size:13px;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nc-prod-sub{font-size:11px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;margin-top:2px}
.nc-etape{font-size:13px;color:var(--text2);line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.nc-etape-vide{color:var(--muted);font-style:italic}
.nc-quand{font-size:12px;color:var(--text2);text-align:right}
.nc-quand-date{font-family:ui-monospace,monospace}
.nc-pill{display:inline-flex;align-items:center;gap:5px;padding:3px 9px;border-radius:999px;font-size:11px;font-weight:700;white-space:nowrap}
.nc-pill.warn{background:color-mix(in srgb,var(--warn) 14%,transparent);color:var(--warn)}
.nc-pill.ok{background:color-mix(in srgb,var(--ok) 14%,transparent);color:var(--ok)}
.nc-pill.neutre{background:var(--bg);color:var(--text2);border:1px solid var(--border)}
.nc-pill.accent{background:var(--accent-bg);color:var(--accent)}
.nc-list-head{display:grid;grid-template-columns:minmax(170px,1.1fr) minmax(130px,.8fr) minmax(220px,2fr) 150px;gap:16px;padding:0 20px 2px;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.nc-list-head div:last-child{text-align:right}
@media (max-width:900px){
  .nc-list-head{display:none}
  .nc-row{grid-template-columns:1fr;gap:8px}
  .nc-cell-lbl{display:block}
  .nc-quand{text-align:left}
}

.nc-head{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;margin-bottom:14px}
.nc-head-title{font-size:22px;font-weight:800;letter-spacing:-.4px;line-height:1.2}
.nc-head-sub{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:8px;font-size:12px;color:var(--muted)}
.nc-head-actions{display:flex;gap:8px;flex-wrap:wrap}
.nc-banner{display:flex;gap:10px;align-items:center;padding:12px 16px;border-radius:12px;margin-bottom:16px;font-size:13px;font-weight:600;background:color-mix(in srgb,var(--warn) 12%,transparent);color:var(--warn);border:1px solid color-mix(in srgb,var(--warn) 40%,transparent)}
.nc-banner.archive{background:var(--card);color:var(--text2);border-color:var(--border)}
.nc-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(320px,400px);gap:16px;align-items:start}
.nc-layout>.nc-col-suivi{position:sticky;top:16px}
@media (max-width:1180px){.nc-layout{grid-template-columns:1fr}.nc-layout>.nc-col-suivi{position:static}}
.nc-sec-title{display:flex;align-items:center;gap:10px;font-size:13px;font-weight:800;text-transform:uppercase;letter-spacing:.5px;margin-bottom:14px;color:var(--text)}
.nc-sec-num{width:24px;height:24px;border-radius:50%;background:var(--accent-bg);color:var(--accent);display:inline-flex;align-items:center;justify-content:center;font-size:12px;flex-shrink:0}
.nc-sec-hint{font-size:12px;color:var(--muted);margin:-8px 0 12px 34px;line-height:1.4}
.nc-check{display:flex;align-items:center;gap:12px;padding:12px 14px;border:1.5px solid var(--border);border-radius:10px;cursor:pointer;background:var(--bg);font-size:13px;font-weight:600;color:var(--text);user-select:none}
.nc-check input{width:18px;height:18px;accent-color:var(--ok);cursor:pointer;flex-shrink:0}
.nc-check.on{border-color:var(--ok);background:color-mix(in srgb,var(--ok) 10%,transparent)}
.nc-check-sub{font-size:11px;font-weight:400;color:var(--muted);margin-left:auto}
@media (max-width:700px){.ncx .form-grid{grid-template-columns:1fr}.ncx .form-grid .col-2{grid-column:auto}}

.nc-photos{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px;margin-top:14px}
.nc-photo{position:relative;border-radius:10px;overflow:hidden;border:1px solid var(--border);aspect-ratio:4/3;background:var(--bg)}
.nc-photo img{width:100%;height:100%;object-fit:cover;display:block;cursor:zoom-in}
.nc-photo-del{position:absolute;top:6px;right:6px;width:26px;height:26px;border-radius:8px;border:none;background:var(--card);color:var(--text2);cursor:pointer;display:flex;align-items:center;justify-content:center;opacity:.92}
.nc-photo-del:hover{color:var(--danger)}
.nc-docs{display:flex;flex-direction:column;gap:6px;margin-top:12px}
.nc-doc{display:flex;align-items:center;gap:10px;padding:9px 12px;border:1px solid var(--border);border-radius:10px;background:var(--bg);font-size:13px}
.nc-doc a{color:var(--text);text-decoration:none;font-weight:600;flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nc-doc a:hover{color:var(--accent)}
.nc-doc-meta{font-size:11px;color:var(--muted);white-space:nowrap}
.nc-doc-del{background:none;border:none;color:var(--muted);cursor:pointer;padding:2px;display:flex}
.nc-doc-del:hover{color:var(--danger)}
.ncx .upload-zone{padding:16px;background:var(--bg)}

.nc-add{display:flex;flex-direction:column;gap:8px;padding-bottom:14px;margin-bottom:6px;border-bottom:1px solid var(--border)}
.nc-add-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.nc-add-row .form-input{width:auto;flex:0 0 150px}
.nc-tl{list-style:none;margin:0;padding:0}
.nc-tl li{position:relative;padding:12px 0 12px 22px;border-bottom:1px solid var(--border)}
.nc-tl li:last-child{border-bottom:none}
.nc-tl li::before{content:"";position:absolute;left:3px;top:17px;width:9px;height:9px;border-radius:50%;background:var(--border)}
.nc-tl li:first-child::before{background:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.nc-tl-head{display:flex;gap:8px;align-items:baseline;flex-wrap:wrap;font-size:12px;color:var(--muted)}
.nc-tl-date{font-weight:700;color:var(--text);font-family:ui-monospace,monospace}
.nc-tl-texte{font-size:13px;color:var(--text);line-height:1.5;margin-top:4px;white-space:pre-wrap;word-break:break-word}
.nc-tl-tools{margin-left:auto;display:flex;gap:2px}
.nc-tl-tools button{background:none;border:none;color:var(--muted);cursor:pointer;padding:3px;border-radius:6px;display:flex}
.nc-tl-tools button:hover{color:var(--accent);background:var(--bg)}
.nc-tl-tools button.del:hover{color:var(--danger)}

.nc-files-pending{display:flex;flex-direction:column;gap:6px;margin-top:10px}
.nc-file-pending{display:flex;align-items:center;gap:10px;font-size:12px;padding:7px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg)}
.nc-file-pending span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nc-file-pending img{width:34px;height:34px;object-fit:cover;border-radius:6px}
.nc-zoom{position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:1100;display:flex;align-items:center;justify-content:center;padding:24px;cursor:zoom-out}
.nc-zoom img{max-width:100%;max-height:100%;border-radius:8px}
"""

NC_JS = r"""
// ══════════════════════════════════════════════════════════════════
// ── Non-conformités (app/web/qualite_nc_assets.py) ─────────────────
// ══════════════════════════════════════════════════════════════════
const NC_ICO = {
  plus: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
  archive: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="5" rx="1"/><path d="M4 9v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9"/><line x1="10" y1="13" x2="14" y2="13"/></svg>',
  back: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polyline points="15 18 9 12 15 6"/></svg>',
  pdf: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><polyline points="9 15 12 18 15 15"/></svg>',
  rouvrir: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"/></svg>',
  poubelle: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/></svg>',
  crayon: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/></svg>',
  croix: '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>',
  alerte: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
  upload: '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>',
  doc: '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
  check: '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
};

function _ncRo(){ return !!S.isQualiteReadonly; }
function _ncDis(){ return _ncRo() ? ' disabled' : ''; }
function _ncToday(){ const d=new Date(); return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0'); }
function _ncIsImage(f){ return /^image\//.test(f.mime_type||'') && f.mime_type!=='image/svg+xml' || /\.(jpe?g|png|gif|webp|bmp)$/i.test(f.original_name||''); }
function _ncProduit(n){ return n.ref_client || n.descriptif_produit || ''; }
function _ncJours(n){
  const j=n.jours_sans_action;
  if(j==null) return '';
  if(j<=0) return "aujourd'hui";
  if(j===1) return 'hier';
  return 'il y a '+j+' j';
}
function _ncFocus(){
  const ae=document.activeElement;
  return ae&&ae.id?{id:ae.id,s:ae.selectionStart,e:ae.selectionEnd}:null;
}
function _ncRefocus(f){
  if(!f) return;
  const el=document.getElementById(f.id);
  if(el){el.focus();if(f.s!=null){try{el.setSelectionRange(f.s,f.e);}catch(e){}}}
}

// ── Chargement ─────────────────────────────────────────────────────
async function loadNCs(){
  try{
    const arch=!!S.ncArchives;
    const r=await api('/api/qualite/nc'+(arch?'?archives=1':''));
    if(!r.ok){showToast('Chargement des NC impossible.','danger');return;}
    const d=await r.json();
    if(arch!==!!S.ncArchives) return;   // on a changé de liste entre-temps
    S.ncs=d;
    if(S.view==='list') renderList();
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau.','danger');}
}
function ncSetArchives(on){
  S.ncArchives=!!on; S.search=''; S.ncs=[];
  const c=document.getElementById('content'); if(c) c.innerHTML='<div class="empty"><div class="spin"></div></div>';
  if(S.view!=='list') setView('list'); else renderList();
  loadNCs();
}

// ── Liste ──────────────────────────────────────────────────────────
function filteredNCs(){
  let list=S.ncs.slice();
  const q=(S.search||'').trim().toLowerCase();
  if(q){
    list=list.filter(n=>[n.numero,n.client_fournisseur,n.ref_client,n.descriptif_produit,n.no_dossier,n.numero_ar,n.description,
      n.derniere_etape&&n.derniere_etape.texte].some(v=>(v||'').toLowerCase().includes(q)));
  }
  if(S.ncArchives){
    list.sort((a,b)=>String(b.date_cloture||'').localeCompare(String(a.date_cloture||'')));
  } else {
    // Les NC à faire avancer d'abord (la plus en retard en tête), puis la plus récente.
    list.sort((a,b)=>(b.a_relancer-a.a_relancer) || (b.a_relancer ? (b.jours_sans_action-a.jours_sans_action) : String(b.derniere_action_at||'').localeCompare(String(a.derniere_action_at||''))));
  }
  return list;
}
function onSearch(v){
  S.search=v;
  const box=document.getElementById('nc-list-box');
  if(box) box.innerHTML=_ncListBody(); else renderList();
}

function _ncListBody(){
  const list=filteredNCs();
  if(!list.length){
    const q=(S.search||'').trim();
    return `<div class="empty">
      <div class="empty-title">${q?'Aucun résultat pour « '+escHtml(q)+' »':(S.ncArchives?'Aucune NC archivée':'Aucune NC en cours')}</div>
      <div class="empty-sub">${(!q&&!S.ncArchives&&!_ncRo())?'Ouvrez une NC avec le bouton « Nouvelle NC ».':''}</div>
    </div>`;
  }
  const head=`<div class="nc-list-head"><div>Client</div><div>Produit</div><div>Où on en est</div><div>${S.ncArchives?'Clôturée':'Dernière action'}</div></div>`;
  const rows=list.map(n=>{
    const et=n.derniere_etape;
    const etape=et?escHtml(et.texte):'<span class="nc-etape-vide">Aucune étape de suivi</span>';
    let quand;
    if(S.ncArchives){
      quand=`<span class="nc-quand-date">${escHtml(fmtDate(n.date_cloture))}</span>`;
    } else {
      quand=`<div class="nc-quand-date">${escHtml(fmtDate(n.derniere_action_at))}</div>`
        +(n.a_relancer
          ? `<div style="margin-top:4px"><span class="nc-pill warn" title="Aucune étape de suivi depuis plus de ${n.relance_jours} jours">${NC_ICO.alerte} À faire avancer · ${n.jours_sans_action} j</span></div>`
          : `<div style="margin-top:3px;color:var(--muted)">${escHtml(_ncJours(n))}</div>`);
    }
    const ar=(!S.ncArchives&&n.type_nc==='client'&&!n.ar_client_envoye)?' · <span style="color:var(--warn)">accusé de réception à envoyer</span>':'';
    return `<button type="button" class="nc-row${(!S.ncArchives&&n.a_relancer)?' relance':''}" onclick="openDetail(${n.id})">
      <div><div class="nc-cell-lbl">Client</div><div class="nc-client" title="${escAttr(n.client_fournisseur||'')}">${escHtml(n.client_fournisseur||'—')}</div><div class="nc-num">${escHtml(n.numero||'')}${ar}</div></div>
      <div><div class="nc-cell-lbl">Produit</div><div class="nc-prod" title="${escAttr(_ncProduit(n))}">${escHtml(_ncProduit(n)||'—')}</div>${(n.ref_client&&n.descriptif_produit)?`<div class="nc-prod-sub">${escHtml(n.descriptif_produit)}</div>`:''}</div>
      <div><div class="nc-cell-lbl">Où on en est</div><div class="nc-etape">${etape}</div></div>
      <div class="nc-quand"><div class="nc-cell-lbl">${S.ncArchives?'Clôturée':'Dernière action'}</div>${quand}</div>
    </button>`;
  }).join('');
  return head+'<div class="nc-list">'+rows+'</div>';
}

function renderList(){
  const f=_ncFocus();
  const enCours=S.ncArchives?[]:S.ncs;
  const nRel=enCours.filter(n=>n.a_relancer).length;
  const nAr=enCours.filter(n=>n.type_nc==='client'&&!n.ar_client_envoye).length;
  const st=k=>enCours.filter(n=>n.statut===k).length;
  const kpis=S.ncArchives?'':`
    <div class="nc-kpis" data-bloc="qualite.nc.statuts"
      data-bloc-valeur-ouvertes="${enCours.length}"
      data-bloc-valeur-a-relancer="${nRel}"
      data-bloc-valeur-en-analyse="${st('en_analyse')}"
      data-bloc-valeur-action-corrective="${st('action_corrective')}"
      data-bloc-valeur-en-verification="${st('en_verification')}"
      data-bloc-valeur-non-lues="${S.unread||0}">
      <div class="nc-kpi"><div class="nc-kpi-val">${enCours.length}</div><div class="nc-kpi-lbl">NC en cours</div></div>
      <div class="nc-kpi${nRel?' warn':''}"><div class="nc-kpi-val">${nRel}</div><div class="nc-kpi-lbl">à faire avancer<br><span style="color:var(--muted)">rien depuis plus de ${(enCours[0]&&enCours[0].relance_jours)||7} jours</span></div></div>
      <div class="nc-kpi${nAr?' warn':''}"><div class="nc-kpi-val">${nAr}</div><div class="nc-kpi-lbl">accusé de réception client<br><span style="color:var(--muted)">pas encore envoyé</span></div></div>
    </div>`;
  const actions=S.ncArchives
    ? `<button type="button" class="btn btn-ghost" onclick="ncSetArchives(false)">${NC_ICO.back} NC en cours</button>`
    : `<button type="button" class="btn btn-ghost" onclick="ncSetArchives(true)">${NC_ICO.archive} Archives</button>
       <button type="button" class="btn btn-ghost qual-write" onclick="openImportModal()">Importer xlsx</button>
       <button type="button" class="btn btn-accent qual-write" onclick="openCreateModal()">${NC_ICO.plus} Nouvelle NC</button>`;
  document.getElementById('content').innerHTML=`<div class="ncx">
    <div class="page-header">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <div>
          <div class="page-title">${S.ncArchives?'NC <span>archivées</span>':'Non-<span>conformités</span>'}</div>
          <div class="page-subtitle">${S.ncArchives?'NC clôturées. Une NC archivée peut être rouverte depuis sa fiche.':'Une ligne par NC en cours : client, produit et la dernière étape du suivi.'}</div>
        </div>
        <button type="button" class="qual-help-btn" data-guide="nc-list" onclick="openGuide('nc-list')" title="Guide Non-conformités" aria-label="Guide Non-conformités">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>
        </button>
      </div>
      <div class="header-actions" style="display:flex;gap:8px;flex-wrap:wrap">${actions}</div>
    </div>
    ${kpis}
    <div class="toolbar">
      <div class="search-wrap">
        <span class="search-ico"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></span>
        <input type="text" id="search-input" class="search-input" placeholder="Rechercher (client, produit, n° NC, dossier, observation…)" value="${escAttr(S.search||'')}" oninput="onSearch(this.value)" onkeydown="if(event.key==='Escape'){this.value='';onSearch('');}">
      </div>
    </div>
    <div id="nc-list-box">${_ncListBody()}</div>
  </div>`;
  _ncRefocus(f);
}

// ── Fiche ──────────────────────────────────────────────────────────
async function openDetail(id){
  S.view='detail'; S.ncEditSuivi=null;
  if(!S.current||S.current.id!==id){ S.current=null; S.currentFiles=[]; renderDetail(); }
  try{
    const r=await api('/api/qualite/nc/'+id);
    if(!r.ok){showToast('NC introuvable.','danger');return;}
    S.current=await r.json();
    document.getElementById('mobile-sub').textContent=S.current.client_fournisseur||S.current.numero||'NC';
    await loadFiles(id);
    renderDetail();
    // L'ancien fil de discussion a été repris en étapes de suivi : on le marque lu.
    api('/api/qualite/nc/'+id+'/messages').then(()=>loadUnread()).catch(()=>{});
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau.','danger');}
}
async function loadFiles(id){
  try{const r=await api('/api/qualite/nc/'+id+'/fichiers');if(r.ok) S.currentFiles=await r.json();}catch(e){}
}
function setDetailTab(){ renderDetail(); }

function _ncChamp(label, field, val, opts){
  opts=opts||{};
  const type=opts.type||'text';
  const id='ncf-'+field;
  const ph=opts.ph?` placeholder="${escAttr(opts.ph)}"`:'';
  const cls=opts.col2?' class="col-2"':'';
  if(type==='textarea'){
    return `<div${cls}><label class="form-label" for="${id}">${escHtml(label)}</label>
      <textarea class="form-textarea" id="${id}" rows="${opts.rows||3}"${ph}${_ncDis()} oninput="saveField('${field}',this.value)">${escHtml(val||'')}</textarea></div>`;
  }
  const extra=opts.picker?`<button type="button" class="btn btn-ghost btn-sm qual-write" onclick="openDossierPicker('${id}')">Rechercher</button>`:'';
  const input=`<input type="${type}" class="form-input" id="${id}" value="${escAttr(val||'')}"${ph}${_ncDis()} ${type==='date'?'onchange':'oninput'}="saveField('${field}',this.value)"${opts.picker?` onchange="saveField('${field}',this.value)"`:''}>`;
  return `<div${cls}><label class="form-label" for="${id}">${escHtml(label)}</label>${extra?`<div style="display:flex;gap:6px">${input}${extra}</div>`:input}</div>`;
}

function renderDetail(){
  const root=document.getElementById('content');
  if(!S.current){root.innerHTML='<div class="empty"><div class="spin"></div></div>';return;}
  const f=_ncFocus();
  const n=S.current;
  const archivee=n.statut==='cloturee';
  const ro=_ncRo();

  const pills=[];
  pills.push(archivee?`<span class="nc-pill neutre">Archivée le ${escHtml(fmtDate(n.date_cloture))}</span>`:`<span class="nc-pill accent">En cours</span>`);
  pills.push(n.ar_client_envoye?`<span class="nc-pill ok">${NC_ICO.check} Accusé de réception envoyé</span>`:`<span class="nc-pill warn">Accusé de réception non envoyé</span>`);
  pills.push(`<span>${escHtml(n.numero||'')}</span>`);
  if(n.date_nc) pills.push(`<span>NC du ${escHtml(fmtDate(n.date_nc))}</span>`);

  const actions=[`<a class="btn btn-ghost btn-sm" href="/api/qualite/nc/${n.id}/pdf" target="_blank" rel="noopener">${NC_ICO.pdf} Fiche PDF</a>`];
  if(!ro){
    actions.push(archivee
      ? `<button type="button" class="btn btn-accent btn-sm" onclick="ncRouvrir()">${NC_ICO.rouvrir} Rouvrir la NC</button>`
      : `<button type="button" class="btn btn-accent btn-sm" onclick="ncConfirmerCloture()">${NC_ICO.archive} Clôturer et archiver</button>`);
    actions.push(`<button type="button" class="btn btn-ghost btn-sm" onclick="openDelModal(${n.id})" title="Supprimer définitivement">${NC_ICO.poubelle}</button>`);
  }

  let banner='';
  if(archivee) banner=`<div class="nc-banner archive">${NC_ICO.archive} Cette NC est clôturée et archivée. « Rouvrir la NC » la remet dans la liste des NC en cours.</div>`;
  else if(n.a_relancer) banner=`<div class="nc-banner">${NC_ICO.alerte} Aucune avancée depuis ${n.jours_sans_action} jours. Ajoutez une étape dans le suivi pour dire où on en est.</div>`;

  const titre=n.client_fournisseur||n.titre||n.numero;
  const prod=_ncProduit(n);

  // 1 · La NC
  const arOn=!!n.ar_client_envoye;
  const secNC=`<div class="card">
    <div class="nc-sec-title"><span class="nc-sec-num">1</span>La non-conformité</div>
    <div class="form-grid">
      ${_ncChamp('Date de la NC','date_nc',n.date_nc,{type:'date'})}
      ${_ncChamp('Client','client_fournisseur',n.client_fournisseur,{ph:'Nom du client'})}
      ${_ncChamp('Référence produit','ref_client',n.ref_client,{ph:'Référence du produit'})}
      ${_ncChamp('Désignation produit','descriptif_produit',n.descriptif_produit,{ph:'ex : étiquette 100 x 150'})}
      ${_ncChamp('Référence dossier','no_dossier',n.no_dossier,{picker:true,ph:'ex : 1153/0030'})}
      ${_ncChamp('N° de commande (AR)','numero_ar',n.numero_ar,{ph:'ex : 9930854'})}
      ${_ncChamp('Quantité concernée','quantite_concernee',n.quantite_concernee,{ph:'ex : 150 000 ex'})}
      <div><label class="form-label" for="ncf-pilote_id">Responsable du suivi</label>
        <select class="form-select" id="ncf-pilote_id"${_ncDis()} onchange="saveField('pilote_id',this.value?parseInt(this.value):null)">
          <option value="">—</option>${S.users.map(u=>`<option value="${u.id}"${n.pilote_id==u.id?' selected':''}>${escHtml(u.nom)}</option>`).join('')}
        </select></div>
      ${_ncChamp('Observation','description',n.description,{type:'textarea',rows:4,col2:true,ph:'Ce qui a été constaté, par qui, sur quelle quantité…'})}
      <div class="col-2">
        <label class="nc-check${arOn?' on':''}">
          <input type="checkbox"${arOn?' checked':''}${_ncDis()} onchange="ncToggleAr(this.checked)">
          Accusé de réception NC client envoyé
          ${arOn&&n.ar_client_envoye_at?`<span class="nc-check-sub">le ${escHtml(fmtDate(n.ar_client_envoye_at))}</span>`:''}
        </label>
      </div>
      <div><label class="form-label" for="ncf-type_nc">Origine</label>
        <select class="form-select" id="ncf-type_nc"${_ncDis()} onchange="saveField('type_nc',this.value)">
          ${TYPES.map(t=>`<option value="${t.k}"${n.type_nc===t.k?' selected':''}>${escHtml(t.label)}</option>`).join('')}
        </select></div>
      <div><label class="form-label" for="ncf-gravite">Gravité</label>
        <select class="form-select" id="ncf-gravite"${_ncDis()} onchange="saveField('gravite',this.value)">
          ${GRAVITES.map(g=>`<option value="${g.k}"${n.gravite===g.k?' selected':''}>${escHtml(g.label)}</option>`).join('')}
        </select></div>
    </div>
  </div>`;

  // 2 · Photos et documents
  const files=S.currentFiles||[];
  const imgs=files.filter(_ncIsImage), docs=files.filter(x=>!_ncIsImage(x));
  const url=fid=>`/api/qualite/nc/${n.id}/fichiers/${fid}`;
  const secFiles=`<div class="card">
    <div class="nc-sec-title"><span class="nc-sec-num">2</span>Photos et documents${files.length?` <span class="nc-pill neutre">${files.length}</span>`:''}</div>
    <div class="nc-sec-hint">Photos du défaut, boucle d'emails avec le client, bon de livraison…</div>
    <label class="upload-zone qual-write" ondragover="onDragOver(event)" ondragleave="onDragLeave(event)" ondrop="onDrop(event, ${n.id})">
      <div style="display:flex;justify-content:center;margin-bottom:6px">${NC_ICO.upload}</div>
      <div style="font-size:13px">Glisser des fichiers ici, ou cliquer pour choisir</div>
      <input type="file" multiple onchange="onFileInput(event, ${n.id})">
    </label>
    ${imgs.length?`<div class="nc-photos">${imgs.map(x=>`<div class="nc-photo">
        <img src="${url(x.id)}" alt="${escAttr(x.original_name||'')}" loading="lazy" onclick="ncZoom('${url(x.id)}')">
        <button type="button" class="nc-photo-del qual-write" title="Supprimer la photo" onclick="delFichier(${x.id})">${NC_ICO.croix}</button>
      </div>`).join('')}</div>`:''}
    ${docs.length?`<div class="nc-docs">${docs.map(x=>`<div class="nc-doc">${NC_ICO.doc}
        <a href="${url(x.id)}" target="_blank" rel="noopener" title="${escAttr(x.original_name||'')}">${escHtml(x.original_name||'')}</a>
        <span class="nc-doc-meta">${escHtml(fmtDate(x.uploaded_at))}</span>
        <button type="button" class="nc-doc-del qual-write" title="Supprimer" onclick="delFichier(${x.id})">${NC_ICO.croix}</button>
      </div>`).join('')}</div>`:''}
    ${(!files.length&&ro)?'<div class="form-hint">Aucun fichier.</div>':''}
  </div>`;

  // 3 · Cause
  const secCause=`<div class="card">
    <div class="nc-sec-title"><span class="nc-sec-num">3</span>Cause de la NC</div>
    <div class="nc-sec-hint">Pourquoi c'est arrivé : la cause d'origine, pas seulement le symptôme.</div>
    <div class="form-grid cols-1">${_ncChamp('Cause','analyse_causes',n.analyse_causes,{type:'textarea',rows:4,ph:'ex : adhésif standard utilisé au lieu de l\'adhésif grand froid'})}</div>
  </div>`;

  // 4 · Actions correctives
  const secActions=`<div class="card">
    <div class="nc-sec-title"><span class="nc-sec-num">4</span>Actions correctives</div>
    <div class="form-grid cols-1">
      ${_ncChamp('Ce qu\'on fait pour corriger','action_corrective',n.action_corrective,{type:'textarea',rows:3,ph:'ex : réimpression de la commande, avoir au client…'})}
      ${_ncChamp('Ce qu\'on change pour que ça ne se reproduise pas','action_preventive',n.action_preventive,{type:'textarea',rows:3,ph:'ex : contrôle de l\'adhésif à la prise de commande'})}
    </div>
  </div>`;

  // 5 · Suivi
  const suivis=n.suivis||[];
  const addForm=ro?'':`<div class="nc-add">
      <label class="form-label" for="nc-suivi-texte" style="margin:0">Nouvelle étape</label>
      <textarea class="form-textarea" id="nc-suivi-texte" rows="2" placeholder="Où on en est : échantillons reçus, client relancé, avoir émis…" onkeydown="if(event.key==='Enter'&&(event.ctrlKey||event.metaKey)){event.preventDefault();ncAjouterSuivi();}"></textarea>
      <div class="nc-add-row">
        <input type="date" class="form-input" id="nc-suivi-date" value="${_ncToday()}" max="${_ncToday()}" title="Date de l'action">
        <button type="button" class="btn btn-accent btn-sm" onclick="ncAjouterSuivi()">${NC_ICO.plus} Ajouter l'étape</button>
      </div>
    </div>`;
  const tl=suivis.length?`<ul class="nc-tl">${suivis.map(s=>{
      if(S.ncEditSuivi===s.id){
        return `<li><div class="nc-add" style="border:none;margin:0;padding:0">
          <textarea class="form-textarea" id="nc-edit-texte" rows="2">${escHtml(s.texte||'')}</textarea>
          <div class="nc-add-row"><input type="date" class="form-input" id="nc-edit-date" value="${escAttr(s.date_action||'')}" max="${_ncToday()}">
            <button type="button" class="btn btn-accent btn-sm" onclick="ncEnregistrerSuivi(${s.id})">Enregistrer</button>
            <button type="button" class="btn btn-ghost btn-sm" onclick="S.ncEditSuivi=null;renderDetail()">Annuler</button></div>
        </div></li>`;
      }
      const tools=ro?'':`<span class="nc-tl-tools"><button type="button" title="Modifier" onclick="S.ncEditSuivi=${s.id};renderDetail();requestAnimationFrame(()=>document.getElementById('nc-edit-texte')?.focus())">${NC_ICO.crayon}</button><button type="button" class="del" title="Supprimer l'étape" onclick="ncSupprimerSuivi(${s.id})">${NC_ICO.croix}</button></span>`;
      return `<li><div class="nc-tl-head"><span class="nc-tl-date">${escHtml(fmtDate(s.date_action))}</span><span>${escHtml(s.auteur_nom||'')}</span>${tools}</div>
        <div class="nc-tl-texte">${escHtml(s.texte||'')}</div></li>`;
    }).join('')}</ul>`:'<div class="form-hint">Aucune étape pour le moment.</div>';
  const secSuivi=`<div class="card">
    <div class="nc-sec-title"><span class="nc-sec-num">5</span>Suivi</div>
    <div class="nc-sec-hint">Une étape à chaque avancée. La plus récente est en haut.</div>
    ${addForm}${tl}
  </div>`;

  // Compléments existants : prise de connaissance par service, validations.
  const meIsAdmin=S.me&&['administration','administration_ventes','administration_technique','direction','superadmin'].includes(S.me.role);
  const secValid=`<div class="card">
    <div class="card-title">Validations</div>
    <div class="valid-grid">
      ${validBox('Direction Qualité', n.validation_qualite_nom, n.validation_qualite_at, 'qualite', meIsAdmin)}
      ${validBox('Direction Industrielle', n.validation_industrielle_nom, n.validation_industrielle_at, 'industrielle', meIsAdmin)}
    </div>
  </div>`;

  root.innerHTML=`<div class="ncx">
    <button type="button" class="detail-back" onclick="ncRetourListe()">${NC_ICO.back} ${archivee?'Retour aux archives':'Retour à la liste'}</button>
    <div class="nc-head">
      <div>
        <div class="nc-head-title">${escHtml(titre||'')}${prod?` <span style="color:var(--muted);font-weight:600">· ${escHtml(prod)}</span>`:''}</div>
        <div class="nc-head-sub">${pills.join('')}</div>
      </div>
      <div class="nc-head-actions">${actions.join('')}</div>
    </div>
    ${banner}
    <div class="nc-layout">
      <div>${secNC}${secFiles}${secCause}${secActions}${ackCardHtml(n)}${secValid}</div>
      <div class="nc-col-suivi">${secSuivi}</div>
    </div>
  </div>`;
  _ncRefocus(f);
}

function ncRetourListe(){
  const arch=S.current&&S.current.statut==='cloturee';
  S.current=null;
  if(!!S.ncArchives!==!!arch){ ncSetArchives(arch); return; }
  setView('list'); loadNCs();
}
function ncZoom(src){
  const m=document.getElementById('mroot'); if(!m) return;
  m.innerHTML=`<div class="nc-zoom" onclick="document.getElementById('mroot').innerHTML=''"><img src="${escAttr(src)}" alt=""></div>`;
}

let _saveTimers={};
function saveField(field, value){
  if(_ncRo()||!S.current) return;
  S.current[field]=value;
  const id=S.current.id;
  clearTimeout(_saveTimers[field]);
  _saveTimers[field]=setTimeout(async()=>{
    try{
      const body={};body[field]=value;
      const r=await api('/api/qualite/nc/'+id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      if(!r.ok){const d=await r.json().catch(()=>({}));showToast(d.detail||'Enregistrement impossible.','danger');return;}
      const d=await r.json();
      if(S.current&&S.current.id===id){
        // Ne pas écraser une frappe en cours dans un autre champ.
        ['statut','date_cloture','titre','updated_at','service_acks','ar_client_envoye','ar_client_envoye_at','pilote_nom','a_relancer','jours_sans_action','derniere_action_at'].forEach(k=>{S.current[k]=d[k];});
      }
    }catch(e){if(e.message!=='unauth')showToast('Erreur réseau.','danger');}
  }, 500);
}

async function ncToggleAr(on){
  if(_ncRo()||!S.current) return;
  try{
    const r=await api('/api/qualite/nc/'+S.current.id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({ar_client_envoye:!!on})});
    if(!r.ok){showToast('Enregistrement impossible.','danger');return;}
    S.current=await r.json(); renderDetail();
    showToast(on?'Accusé de réception noté comme envoyé.':'Accusé de réception noté comme non envoyé.','success');
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau.','danger');}
}

async function _ncSuiviRequete(path, method, body, ok){
  if(_ncRo()||!S.current) return false;
  try{
    const r=await api(path,{method,headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
    if(!r.ok){const d=await r.json().catch(()=>({}));showToast(d.detail||'Enregistrement impossible.','danger');return false;}
    const files=S.currentFiles;
    S.current=await r.json(); S.currentFiles=files; S.ncEditSuivi=null;
    renderDetail(); if(ok) showToast(ok,'success');
    return true;
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau.','danger');return false;}
}
async function ncAjouterSuivi(){
  const t=document.getElementById('nc-suivi-texte'), d=document.getElementById('nc-suivi-date');
  const texte=(t&&t.value||'').trim();
  if(!texte){showToast('Décrire l\'étape avant de l\'ajouter.','danger');t&&t.focus();return;}
  await _ncSuiviRequete('/api/qualite/nc/'+S.current.id+'/suivis','POST',{texte,date_action:d&&d.value||null},'Étape ajoutée.');
}
async function ncEnregistrerSuivi(sid){
  const texte=(document.getElementById('nc-edit-texte')?.value||'').trim();
  const date_action=document.getElementById('nc-edit-date')?.value||null;
  if(!texte){showToast('Le texte de l\'étape est vide.','danger');return;}
  await _ncSuiviRequete('/api/qualite/nc/'+S.current.id+'/suivis/'+sid,'PUT',{texte,date_action},'Étape modifiée.');
}
async function ncSupprimerSuivi(sid){
  if(!confirm('Supprimer cette étape du suivi ?')) return;
  await _ncSuiviRequete('/api/qualite/nc/'+S.current.id+'/suivis/'+sid,'DELETE',null,'Étape supprimée.');
}

function ncConfirmerCloture(){
  if(_ncRo()||!S.current) return;
  const n=S.current;
  const manque=[];
  if(!(n.analyse_causes||'').trim()) manque.push('la cause');
  if(!(n.action_corrective||'').trim()) manque.push('les actions correctives');
  if(n.type_nc==='client'&&!n.ar_client_envoye) manque.push('l\'accusé de réception client');
  document.getElementById('mroot').innerHTML=`<div class="modal-ov" onclick="if(event.target===this)ncFermerModale()"><div class="modal ncx" style="max-width:460px" onclick="event.stopPropagation()">
    <button type="button" class="modal-close" onclick="ncFermerModale()">×</button>
    <div class="modal-title">Clôturer et archiver cette NC ?</div>
    <p style="font-size:13px;color:var(--text2);line-height:1.6;margin:0">Elle quitte la liste des NC en cours et rejoint les archives. Elle pourra être rouverte à tout moment.</p>
    ${manque.length?`<div class="nc-banner" style="margin:14px 0 0">${NC_ICO.alerte} Non renseigné : ${escHtml(manque.join(', '))}.</div>`:''}
    <div class="modal-actions">
      <button type="button" class="btn btn-ghost" onclick="ncFermerModale()">Annuler</button>
      <button type="button" class="btn btn-accent" onclick="ncCloturer()">${NC_ICO.archive} Clôturer et archiver</button>
    </div>
  </div></div>`;
}
function ncFermerModale(){ const m=document.getElementById('mroot'); if(m) m.innerHTML=''; }
async function ncCloturer(){
  ncFermerModale();
  const ok=await _ncSuiviRequete('/api/qualite/nc/'+S.current.id+'/cloturer','POST',null,'NC clôturée et archivée.');
  if(ok) S.ncs=S.ncs.filter(x=>x.id!==S.current.id);
}
async function ncRouvrir(){
  await _ncSuiviRequete('/api/qualite/nc/'+S.current.id+'/rouvrir','POST',null,'NC rouverte.');
}

// Fichiers de la fiche
function onDragOver(e){e.preventDefault();e.currentTarget.classList.add('drag');}
function onDragLeave(e){e.currentTarget.classList.remove('drag');}
async function onDrop(e, ncId){
  e.preventDefault();e.currentTarget.classList.remove('drag');
  for(const f of Array.from(e.dataTransfer.files||[])) await uploadFile(ncId, f, true);
  renderDetail(); showToast('Fichier(s) ajouté(s).','success');
}
async function onFileInput(e, ncId){
  const files=Array.from(e.target.files||[]);
  for(const f of files) await uploadFile(ncId, f, true);
  e.target.value='';
  if(files.length){ renderDetail(); showToast(files.length>1?files.length+' fichiers ajoutés.':'Fichier ajouté.','success'); }
}
async function uploadFile(ncId, file, silencieux){
  if(_ncRo()) return false;
  try{
    const fd=new FormData();fd.append('file', file);
    const r=await api('/api/qualite/nc/'+ncId+'/fichiers',{method:'POST',body:fd});
    if(!r.ok){const d=await r.json().catch(()=>({}));showToast((d.detail||'Envoi impossible')+' : '+file.name,'danger');return false;}
    const list=await r.json();
    if(S.current&&S.current.id===ncId) S.currentFiles=list;
    if(!silencieux){ renderDetail(); showToast('Fichier ajouté.','success'); }
    return true;
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau.','danger');return false;}
}
async function delFichier(fileId){
  if(_ncRo()||!S.current) return;
  if(!confirm('Supprimer ce fichier ?')) return;
  try{
    const r=await api('/api/qualite/nc/'+S.current.id+'/fichiers/'+fileId,{method:'DELETE'});
    if(!r.ok){showToast('Suppression impossible.','danger');return;}
    await loadFiles(S.current.id);renderDetail();showToast('Fichier supprimé.','info');
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau.','danger');}
}

// Prise de connaissance par service et validations (inchangées).
function ackCardHtml(n){
  if(!S.ackServices||!S.ackServices.length) return '';
  const acks=n.service_acks||{};
  const items=S.ackServices.map(function(s){
    const a=acks[s.key];
    const sub=a?(escHtml(a.user_nom||'?')+' · '+escHtml(fmtDateTime(a.ack_at))):'En attente';
    return '<div class="ack-card-item'+(S.myAckService===s.key?' mine':'')+'">'
      +'<span class="ack-dot'+(a?' done':'')+'" style="color:'+s.color+'"></span>'
      +'<div class="ack-card-info"><div class="ack-card-label">'+escHtml(s.label)+'</div><div class="ack-card-sub">'+sub+'</div></div></div>';
  }).join('');
  let actions='';
  if(S.myAckService){
    const mine=acks[S.myAckService];
    actions=mine
      ? '<div class="ack-card-actions"><span style="font-size:12px;color:var(--ok);font-weight:600">✓ Votre service a pris connaissance de cette NC le '+escHtml(fmtDateTime(mine.ack_at))+'</span><button type="button" class="btn btn-ghost btn-sm" onclick="unackCurrentNC()">Retirer</button></div>'
      : '<div class="ack-card-actions"><button type="button" class="btn btn-accent btn-sm" onclick="ackCurrentNC()">Marquer comme lu</button><span style="font-size:11px;color:var(--muted)">au nom de votre service</span></div>';
  }
  return '<div class="card"><div class="card-title">Prise de connaissance par service</div><div class="ack-card-row">'+items+'</div>'+actions+'</div>';
}
async function _ncAck(method, msg){
  if(!S.current) return;
  try{
    const r=await api('/api/qualite/nc/'+S.current.id+'/ack',{method});
    if(!r.ok){showToast('Enregistrement impossible.','danger');return;}
    const d=await r.json(); S.current.service_acks=d.service_acks; renderDetail(); showToast(msg,'success');
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau.','danger');}
}
function ackCurrentNC(){ return _ncAck('POST','Prise de connaissance enregistrée.'); }
function unackCurrentNC(){ return _ncAck('DELETE','Prise de connaissance retirée.'); }

function validBox(label, name, at, kind, canSign){
  const signed=!!name;
  return `<div class="valid-box${signed?' signed':''}">
    <div class="valid-box-title">${escHtml(label)}</div>
    ${signed?`<div class="valid-box-name">${escHtml(name)}</div><div class="valid-box-date">Signé le ${escHtml(fmtDateTime(at))}</div>`:'<div style="font-size:12px;color:var(--muted)">En attente de signature</div>'}
    ${(canSign&&!_ncRo())?`<div class="valid-box-actions">${signed?`<button type="button" class="btn btn-ghost btn-sm" onclick="revokeValid('${kind}')">Retirer la signature</button>`:`<button type="button" class="btn btn-ok btn-sm" onclick="signValid('${kind}')">Signer</button>`}</div>`:''}
  </div>`;
}
async function _ncValid(kind, revoke, msg){
  if(_ncRo()||!S.current) return;
  try{
    const r=await api('/api/qualite/nc/'+S.current.id+'/valider',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,revoke})});
    if(!r.ok){const d=await r.json().catch(()=>({}));showToast(d.detail||'Enregistrement impossible.','danger');return;}
    const files=S.currentFiles; S.current=await r.json(); S.currentFiles=files; renderDetail(); showToast(msg,'success');
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau.','danger');}
}
function signValid(kind){ return _ncValid(kind,false,'Signature enregistrée.'); }
function revokeValid(kind){ if(confirm('Retirer la signature ?')) return _ncValid(kind,true,'Signature retirée.'); }

// ── Création ───────────────────────────────────────────────────────
function openCreateModal(){
  if(_ncRo()) return;
  S.ncNouveauxFichiers=[];
  ['c-client','c-refprod','c-designation','c-dossier','c-ar','c-desc'].forEach(id=>{const el=document.getElementById(id);if(el) el.value='';});
  document.getElementById('c-date').value=_ncToday();
  document.getElementById('c-date').max=_ncToday();
  document.getElementById('c-type').value='client';
  const ar=document.getElementById('c-arclient'); ar.checked=false; ar.closest('.nc-check').classList.remove('on');
  _ncRenderNouveauxFichiers();
  document.getElementById('create-modal').style.display='flex';
  requestAnimationFrame(()=>document.getElementById('c-client').focus());
}
function closeCreateModal(){document.getElementById('create-modal').style.display='none';S.ncNouveauxFichiers=[];}
function ncAjouterNouveauxFichiers(list){
  for(const f of Array.from(list||[])) S.ncNouveauxFichiers.push(f);
  _ncRenderNouveauxFichiers();
}
function ncRetirerNouveauFichier(i){ S.ncNouveauxFichiers.splice(i,1); _ncRenderNouveauxFichiers(); }
function _ncRenderNouveauxFichiers(){
  const box=document.getElementById('c-files'); if(!box) return;
  (S._ncApercus||[]).forEach(u=>URL.revokeObjectURL(u)); S._ncApercus=[];
  box.innerHTML='';
  (S.ncNouveauxFichiers||[]).forEach((f,i)=>{
    const row=document.createElement('div'); row.className='nc-file-pending';
    if(/^image\//.test(f.type)){ const u=URL.createObjectURL(f); S._ncApercus.push(u); const im=document.createElement('img'); im.src=u; im.alt=''; row.appendChild(im); }
    else { const s=document.createElement('span'); s.innerHTML=NC_ICO.doc; s.style.flex='0 0 auto'; row.appendChild(s); }
    const nm=document.createElement('span'); nm.textContent=f.name; row.appendChild(nm);
    const b=document.createElement('button'); b.type='button'; b.className='nc-doc-del'; b.title='Retirer'; b.innerHTML=NC_ICO.croix; b.onclick=()=>ncRetirerNouveauFichier(i); row.appendChild(b);
    box.appendChild(row);
  });
}
async function submitCreate(){
  if(_ncRo()) return;
  const v=id=>(document.getElementById(id).value||'').trim();
  const body={
    date_nc:v('c-date')||null,
    client_fournisseur:v('c-client')||null,
    ref_client:v('c-refprod')||null,
    descriptif_produit:v('c-designation')||null,
    no_dossier:v('c-dossier')||null,
    numero_ar:v('c-ar')||null,
    description:v('c-desc')||null,
    type_nc:document.getElementById('c-type').value,
    gravite:'mineure',
    ar_client_envoye:document.getElementById('c-arclient').checked,
  };
  if(!body.client_fournisseur){showToast('Indiquer le client.','danger');document.getElementById('c-client').focus();return;}
  if(!body.description){showToast('Décrire ce qui a été observé.','danger');document.getElementById('c-desc').focus();return;}
  const btn=document.getElementById('create-btn');
  btn.disabled=true;btn.textContent='Création…';
  try{
    const r=await api('/api/qualite/nc',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    if(!r.ok){const d=await r.json().catch(()=>({}));showToast(d.detail||'Création impossible.','danger');return;}
    const nc=await r.json();
    const fichiers=(S.ncNouveauxFichiers||[]).slice();
    let ko=0;
    for(let i=0;i<fichiers.length;i++){
      btn.textContent='Envoi des fichiers '+(i+1)+'/'+fichiers.length+'…';
      if(!(await uploadFile(nc.id, fichiers[i], true))) ko++;
    }
    closeCreateModal();
    showToast(ko?('NC créée — '+ko+' fichier(s) non envoyé(s).'):'NC créée.', ko?'danger':'success');
    S.ncArchives=false;
    loadNCs();
    openDetail(nc.id);
  }catch(e){if(e.message!=='unauth')showToast('Erreur réseau.','danger');}
  finally{btn.disabled=false;btn.textContent='Créer la NC';}
}
"""

# Fenêtre de création : remplace le contenu de #create-modal de la page.
NC_CREATE_MODAL = r"""<div class="modal-ov" id="create-modal" style="display:none" onclick="if(event.target===this)closeCreateModal()">
  <div class="modal lg ncx" onclick="event.stopPropagation()">
    <button type="button" class="modal-close" onclick="closeCreateModal()">×</button>
    <div class="modal-title">Nouvelle non-conformité</div>
    <div class="form-grid">
      <div>
        <label class="form-label" for="c-date">Date</label>
        <input type="date" class="form-input" id="c-date">
      </div>
      <div>
        <label class="form-label" for="c-client">Client</label>
        <input type="text" class="form-input" id="c-client" placeholder="Nom du client" autocomplete="off">
      </div>
      <div>
        <label class="form-label" for="c-refprod">Référence produit</label>
        <input type="text" class="form-input" id="c-refprod" placeholder="Référence du produit">
      </div>
      <div>
        <label class="form-label" for="c-designation">Désignation produit <span style="text-transform:none;color:var(--muted);font-weight:400">(facultatif)</span></label>
        <input type="text" class="form-input" id="c-designation" placeholder="ex : étiquette 100 x 150">
      </div>
      <div>
        <label class="form-label" for="c-dossier">Référence dossier <span style="text-transform:none;color:var(--muted);font-weight:400">(facultatif)</span></label>
        <div style="display:flex;gap:6px">
          <input type="text" class="form-input" id="c-dossier" placeholder="ex : 1153/0030">
          <button type="button" class="btn btn-ghost btn-sm" onclick="openDossierPicker('c-dossier')">Rechercher</button>
        </div>
      </div>
      <div>
        <label class="form-label" for="c-ar">N° de commande AR <span style="text-transform:none;color:var(--muted);font-weight:400">(facultatif)</span></label>
        <input type="text" class="form-input" id="c-ar" placeholder="ex : 9930854">
      </div>
      <div class="col-2">
        <label class="form-label" for="c-desc">Observation</label>
        <textarea class="form-textarea" id="c-desc" rows="4" placeholder="Ce qui a été constaté, par qui, sur quelle quantité…"></textarea>
      </div>
      <div class="col-2">
        <label class="form-label">Photos et documents</label>
        <label class="upload-zone" ondragover="event.preventDefault();this.classList.add('drag')" ondragleave="this.classList.remove('drag')" ondrop="event.preventDefault();this.classList.remove('drag');ncAjouterNouveauxFichiers(event.dataTransfer.files)">
          <div style="font-size:13px">Glisser les photos ou la boucle d'emails ici, ou cliquer pour choisir</div>
          <input type="file" multiple onchange="ncAjouterNouveauxFichiers(this.files);this.value=''">
        </label>
        <div class="nc-files-pending" id="c-files"></div>
      </div>
      <div class="col-2">
        <label class="nc-check">
          <input type="checkbox" id="c-arclient" onchange="this.closest('.nc-check').classList.toggle('on',this.checked)">
          Accusé de réception NC client envoyé
        </label>
      </div>
      <div>
        <label class="form-label" for="c-type">Origine</label>
        <select class="form-select" id="c-type">
          <option value="client">Client (réclamation)</option>
          <option value="interne">Interne (production)</option>
          <option value="fournisseur">Fournisseur</option>
          <option value="logistique">Logistique / expédition</option>
        </select>
      </div>
    </div>
    <div class="modal-actions">
      <button type="button" class="btn btn-ghost" onclick="closeCreateModal()">Annuler</button>
      <button type="button" class="btn btn-accent" id="create-btn" onclick="submitCreate()">Créer la NC</button>
    </div>
  </div>
</div>"""

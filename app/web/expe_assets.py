"""MyExpé — assets CSS/JS (injectés dans app/web/html.py). Pas de route FastAPI ici."""
import json

from app.web.expe_france_delais_data import DELAIS_FRANCE_JSON
from app.web.expe_france_map_svg import EXPE_FRANCE_SVG_MARKUP

EXPE_TRANSPORTEURS_CSS = r"""
/* ── MyExpé — transporteurs ── */
.expe-trp-panel .btn,.expe-trp-modal .btn,.expe-trp-panel .btn-accent,.expe-trp-modal .btn-accent{margin-top:0;border-radius:10px;padding:10px 18px;font-weight:700}
.btn-accent{background:var(--accent);color:var(--bg);border:none;border-radius:10px;padding:10px 18px;font-size:13px;font-weight:700;
  cursor:pointer;font-family:inherit;transition:filter .15s}
.btn-accent:hover:not(:disabled){filter:brightness(1.05)}
.btn-accent:disabled{opacity:.5;cursor:not-allowed}

.expe-trp-overlay{position:fixed;inset:0;background:color-mix(in srgb,var(--bg) 55%,transparent);z-index:11500;
  opacity:0;pointer-events:none;transition:opacity .2s}
.expe-trp-overlay.open{opacity:1;pointer-events:auto}
.expe-trp-panel{position:fixed;top:0;right:0;bottom:0;width:min(720px,100vw);max-width:100%;
  background:var(--card);border-left:1px solid var(--border);z-index:11501;display:flex;flex-direction:column;
  transform:translateX(105%);transition:transform .22s ease;box-shadow:-12px 0 40px color-mix(in srgb,var(--bg) 80%,transparent)}
.expe-trp-panel.open{transform:translateX(0)}
.expe-trp-head{display:flex;align-items:center;gap:12px;flex-wrap:wrap;padding:16px 18px;border-bottom:1px solid var(--border);flex-shrink:0}
.expe-trp-head h2{font-size:15px;font-weight:800;color:var(--text);margin:0;flex:1;min-width:120px}
.expe-trp-search{flex:1;min-width:180px;max-width:320px;padding:12px 16px;background:var(--bg);border:1px solid var(--border);
  border-radius:10px;color:var(--text);font-size:14px;font-family:inherit;outline:none}
.expe-trp-search:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 12%,transparent)}
.expe-trp-body{flex:1;overflow-y:auto;padding:14px 18px 24px}
.expe-trp-close{padding:8px 10px;border-radius:10px;border:1px solid var(--border);background:transparent;color:var(--text2);
  cursor:pointer;display:inline-flex;align-items:center;justify-content:center}
.expe-trp-close:hover{border-color:var(--accent);color:var(--accent)}

.expe-trp-table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:12px;background:var(--card)}
.expe-trp-table-wrap table.table-std{margin:0}
.expe-trp-table-wrap table.table-std td{vertical-align:middle}
.expe-trp-row-inactive td{opacity:.55}
.expe-trp-name{font-size:13px;font-weight:800;color:var(--text);line-height:1.3;white-space:nowrap}
.expe-trp-actions{display:inline-flex;align-items:center;gap:4px;flex-shrink:0}
.expe-trp-cell-badges{display:flex;flex-wrap:wrap;gap:4px;align-items:center}
.expe-trp-zone{font-size:10px;font-weight:700;padding:2px 7px;border-radius:6px;background:var(--accent-bg);
  color:var(--accent);border:1px solid color-mix(in srgb,var(--accent) 28%,transparent);letter-spacing:.2px;white-space:nowrap}
.expe-trp-contact-col{font-size:12px;color:var(--text2);line-height:1.45;min-width:140px}
.expe-trp-contact-line{display:inline-flex;align-items:center;gap:5px;max-width:220px}
.expe-trp-contact-line svg{flex-shrink:0;color:var(--muted)}
.expe-trp-contact-line a{color:var(--accent);text-decoration:none;font-weight:600}
.expe-trp-contact-line a:hover{text-decoration:underline}
.expe-trp-tarif a{color:var(--accent);font-weight:600;text-decoration:none;font-size:12px;display:inline-flex;align-items:center;gap:5px}
.expe-trp-tarif a:hover{text-decoration:underline}
.expe-trp-badge-inactif{font-size:10px;font-weight:700;padding:2px 7px;border-radius:6px;background:color-mix(in srgb,var(--muted) 18%,transparent);
  color:var(--muted);border:1px solid var(--border);margin-left:8px;vertical-align:middle}
.expe-trp-empty{padding:24px;text-align:center;color:var(--muted);font-size:13px}
.expe-trp-page-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.expe-trp-page-head .expe-trp-search{flex:1;min-width:200px;max-width:400px}
.expe-trp-svc{font-size:10px;font-weight:700;padding:2px 7px;border-radius:6px;background:var(--bg);border:1px solid var(--border);color:var(--text2);white-space:nowrap}
.expe-trp-portail{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:600;color:var(--accent);text-decoration:none}
.expe-trp-portail:hover{text-decoration:underline}
.expe-trp-num{font-variant-numeric:tabular-nums;font-family:ui-monospace,SFMono-Regular,monospace;font-size:12px}

.expe-trp-modal-overlay{position:fixed;inset:0;background:color-mix(in srgb,var(--bg) 60%,transparent);z-index:12000;
  display:flex;align-items:center;justify-content:center;padding:16px}
.expe-trp-modal{width:100%;max-width:560px;max-height:min(92vh,900px);overflow:auto;background:var(--card);
  border:1px solid var(--border);border-radius:12px;padding:18px 18px 16px;position:relative}
.expe-trp-modal h3{font-size:15px;font-weight:800;margin:0 0 14px;color:var(--text)}
.expe-trp-sec{margin-bottom:16px}
.expe-trp-sec-title{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px}
.expe-trp-field{margin-bottom:10px}
.expe-trp-field label{display:block;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;
  letter-spacing:.5px;margin-bottom:6px}
.expe-trp-field input[type="text"],.expe-trp-field input[type="email"],.expe-trp-field input[type="tel"],
.expe-trp-field input[type="number"]{width:100%;padding:12px 16px;background:var(--bg);border:1px solid var(--border);
  border-radius:10px;color:var(--text);font-size:14px;font-family:inherit;outline:none}
.expe-trp-field input:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 12%,transparent)}
.expe-trp-checks{display:flex;flex-direction:column;gap:8px}
.expe-trp-check{display:flex;align-items:center;gap:10px;font-size:13px;color:var(--text);cursor:pointer}
.expe-trp-check input{width:16px;height:16px;accent-color:var(--accent)}
.expe-trp-drop{border:2px dashed var(--border);border-radius:12px;padding:20px;text-align:center;background:var(--bg);
  cursor:pointer;transition:border-color .15s,background .15s}
.expe-trp-drop:hover,.expe-trp-drop.drag{border-color:var(--accent);background:var(--accent-bg)}
.expe-trp-drop-hint{font-size:12px;color:var(--muted);margin-top:6px;line-height:1.5}
.expe-trp-tarif-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:8px}
.expe-trp-modal-actions{display:flex;gap:10px;justify-content:flex-end;margin-top:16px;padding-top:14px;border-top:1px solid var(--border)}
.expe-trp-tabs{display:flex;gap:6px;margin-bottom:14px;border-bottom:1px solid var(--border)}
.expe-trp-tab{padding:8px 14px;font-size:12px;font-weight:700;color:var(--muted);background:transparent;border:none;border-bottom:2px solid transparent;cursor:pointer}
.expe-trp-tab.active{color:var(--accent);border-bottom-color:var(--accent);background:var(--accent-bg)}
.expe-trp-tarif-banner{display:flex;flex-wrap:wrap;align-items:center;gap:10px;padding:12px 14px;background:color-mix(in srgb,var(--warn) 12%,transparent);border:1px solid color-mix(in srgb,var(--warn) 35%,transparent);border-radius:10px;margin-bottom:12px;font-size:13px;color:var(--text2)}
.expe-trp-tarif-actions{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px}
.expe-trp-tarif-sec{margin-bottom:18px}
.expe-trp-tarif-sec-h{display:flex;align-items:center;gap:8px;font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.expe-trp-badge-actif{font-size:10px;font-weight:700;padding:2px 8px;border-radius:6px;background:color-mix(in srgb,var(--success) 15%,transparent);color:var(--success)}
.expe-trp-tarif-table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:10px}
.expe-trp-tarif-table-wrap table.table-std{margin:0;font-size:12px}
.expe-trp-tarif-table-wrap table.table-std th,.expe-trp-tarif-table-wrap table.table-std td{padding:8px 10px}
@media(max-width:640px){
  .expe-trp-panel{width:100%}
  .expe-trp-head{padding:12px 14px}
  .expe-trp-search{max-width:none;width:100%;order:3}
}
"""

EXPE_TRANSPORTEURS_JS = r"""
// ── MyExpé — référentiel transporteurs (état T) ─────────────────
const T={
  list:[],
  filter:'',
  panelOpen:false,
  pageLoaded:false,
  loading:false,
  modalOpen:false,
  editId:null,
  form:{},
  saving:false,
  tarifFile:null,
  uploadDrag:false,
  modalTab:'fiche',
  tarifs_lignes:[],
  tarifs_frais:[],
  tarifs_loading:false,
  tarifs_parsing:false
};

function escHtml(t){
  return String(t==null?'':t).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function escAttr(t){
  return escHtml(t).replace(/"/g,'&quot;');
}

function expeCanWrite(){
  const r=(S.user&&S.user.role)||(typeof window.__USER_ROLE__==='string'?window.__USER_ROLE__:'')||'';
  return r==='superadmin'||r==='direction'||r==='administration'||r==='expedition';
}

function expeTrpIconPhone(size){
  const s=size||14;
  const el=document.createElementNS('http://www.w3.org/2000/svg','svg');
  el.setAttribute('width',s);el.setAttribute('height',s);el.setAttribute('viewBox','0 0 24 24');
  el.setAttribute('fill','none');el.setAttribute('stroke','currentColor');el.setAttribute('stroke-width','2');
  el.innerHTML='<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0 1 22 16.92z"/>';
  return el;
}

function expeTrpZonesBadges(tr){
  const z=[];
  if(tr.zone_france)z.push('France');
  if(tr.zone_france_hors_paris)z.push('Hors Paris');
  if(tr.zone_affretement)z.push('Affrètement >6 pal.');
  if(tr.zone_messagerie)z.push('Messagerie <6 pal.');
  return z;
}

function expeTrpServiceBadges(tr){
  if(!tr)return [];
  const out=[];
  if(Number(tr.accepte_poids))out.push('Poids');
  if(Number(tr.accepte_palette))out.push('Palette');
  if(tr.palette_max!=null&&tr.palette_max!=='')out.push('Max '+tr.palette_max+' pal.');
  return out;
}

function expeTrpIsPortailUrl(v){
  const s=String(v||'').trim().toLowerCase();
  return s.startsWith('http://')||s.startsWith('https://');
}

function expeTrpOpenContact(tr){
  const email=(tr&&tr.contact_email||'').trim();
  if(expeTrpIsPortailUrl(email)){
    window.open(email,'_blank','noopener');
    return;
  }
  if(email){
    const nom=(tr&&tr.nom)||'';
    const s=encodeURIComponent('Demande de tarif SIFA - '+nom);
    const b=encodeURIComponent('Bonjour,\n\nNous souhaitons obtenir un tarif pour un départ.\n\nCordialement,\nSIFA Roubaix');
    window.location.href='mailto:'+email+'?subject='+s+'&body='+b;
    return;
  }
  if(typeof expeOpenContact==='function'&&tr&&tr.nom)expeOpenContact(tr.nom);
}

function expeTrpFiltered(){
  const q=(T.filter||'').trim().toLowerCase();
  const norm=s=>{
    try{return (s||'').toLowerCase().normalize('NFD').replace(/\p{M}/gu,'');}
    catch(e){return (s||'').toLowerCase();}
  };
  const qq=norm(q);
  let rows=(T.list||[]).slice();
  if(qq){
    rows=rows.filter(tr=>norm(tr.nom||'').includes(qq));
  }
  rows.sort((a,b)=>{
    const aa=(a.actif!=null?Number(a.actif):1)?1:0;
    const bb=(b.actif!=null?Number(b.actif):1)?1:0;
    if(bb!==aa)return bb-aa;
    return String(a.nom||'').localeCompare(String(b.nom||''),'fr');
  });
  return rows;
}

async function loadTransporteurs(){
  T.loading=true;
  render();
  try{
    const rows=await api('/api/expe/transporteurs');
    T.list=Array.isArray(rows)?rows:[];
  }catch(e){
    showToast(e.message||'Chargement impossible','danger');
    T.list=[];
  }
  T.loading=false;
  renderTransporteurs();
}

function renderTransporteurs(){
  const ae=document.activeElement;
  const focusId=ae&&ae.id&&(ae.id==='expe-trp-search'||ae.id==='expe-trp-page-search')?ae.id:null;
  const caretStart=ae&&typeof ae.selectionStart==='number'?ae.selectionStart:null;
  const caretEnd=ae&&typeof ae.selectionEnd==='number'?ae.selectionEnd:null;
  render();
  if(focusId){
    requestAnimationFrame(()=>{
      const el=document.getElementById(focusId);
      if(el){
        try{
          el.focus();
          if(caretStart!=null)el.setSelectionRange(caretStart,caretEnd!=null?caretEnd:caretStart);
        }catch(e){}
      }
    });
  }
}

function openExpeTranspPanel(){
  T.panelOpen=true;
  if(!T.list.length&&!T.loading)void loadTransporteurs();
  else render();
}

function closeExpeTranspPanel(){
  T.panelOpen=false;
  render();
}

function openTransporteurModal(id){
  const isEdit=id!=null&&id!=='';
  if(isEdit){
    const tr=(T.list||[]).find(x=>Number(x.id)===Number(id));
    if(!tr){showToast('Transporteur introuvable','danger');return;}
    T.editId=tr.id;
    T.form={
      nom:tr.nom||'',
      taxe_carburant_pct:tr.taxe_carburant_pct!=null?String(tr.taxe_carburant_pct):'0',
      contact_nom:tr.contact_nom||'',
      contact_email:tr.contact_email||'',
      contact_tel:tr.contact_tel||'',
      zone_france:!!Number(tr.zone_france),
      zone_france_hors_paris:!!Number(tr.zone_france_hors_paris),
      zone_affretement:!!Number(tr.zone_affretement),
      zone_messagerie:!!Number(tr.zone_messagerie),
      actif:tr.actif==null?true:!!Number(tr.actif),
      tarif_filename:tr.tarif_filename||'',
      tarif_url:tr.tarif_url||''
    };
  }else{
    T.editId=null;
    T.form={
      nom:'',taxe_carburant_pct:'0',contact_nom:'',contact_email:'',contact_tel:'',
      zone_france:true,zone_france_hors_paris:false,zone_affretement:false,zone_messagerie:false,
      actif:true,tarif_filename:'',tarif_url:''
    };
  }
  T.tarifFile=null;
  T.modalTab='fiche';
  T.tarifs_lignes=[];
  T.tarifs_frais=[];
  T.modalOpen=true;
  render();
}

function closeTransporteurModal(){
  T.modalOpen=false;
  T.editId=null;
  T.tarifFile=null;
  T.modalTab='fiche';
  T.tarifs_lignes=[];
  T.tarifs_frais=[];
  render();
}

function setTransporteurModalTab(tab){
  T.modalTab=tab;
  if(tab==='tarifs'&&T.editId!=null)void loadTarifsTransporteur(T.editId);
  else render();
}

async function loadTarifsTransporteur(transporteurId){
  T.tarifs_loading=true;
  render();
  try{
    const data=await api('/api/expe/transporteurs/'+transporteurId+'/tarifs');
    T.tarifs_lignes=data.lignes||[];
    T.tarifs_frais=data.frais||[];
  }catch(e){
    showToast(e.message||'Chargement tarifs impossible','danger');
    T.tarifs_lignes=[];
    T.tarifs_frais=[];
  }
  T.tarifs_loading=false;
  render();
}

function expeTrpTarifRowCells(l,withCheck){
  const trMax=l.tranche_max!=null&&l.tranche_max!==''?String(l.tranche_max):'∞';
  const cells=[
    withCheck?h('td',null,h('input',{type:'checkbox',className:'tarif-check','data-id':String(l.id)})):null,
    h('td',null,escHtml(l.type_envoi||'')),
    h('td',null,escHtml(l.base_calcul||'')),
    h('td',null,escHtml((l.zone_type||'')+' '+String(l.zone_valeur||''))),
    h('td',null,escHtml(String(l.tranche_min!=null?l.tranche_min:0)+' – '+trMax)),
    h('td',null,escHtml(String(l.prix!=null?l.prix:''))),
    h('td',null,escHtml(l.unite||'')),
    h('td',null,l.mini_perception!=null&&l.mini_perception!==''?escHtml(String(l.mini_perception)):'—')
  ].filter(Boolean);
  return h('tr',null,...cells);
}

function expeTrpTarifsTable(lignes,withCheck){
  if(!lignes.length)return h('p',{style:{color:'var(--muted)',fontSize:'13px',margin:'0'}},'Aucune ligne.');
  const head=h('tr',null,
    withCheck?h('th',{style:{width:'28px'}},''):null,
    h('th',null,'Type'),h('th',null,'Base'),h('th',null,'Zone'),
    h('th',null,'Tranche'),h('th',null,'Prix'),h('th',null,'Unité'),h('th',null,'Mini perception')
  );
  const body=lignes.map(l=>expeTrpTarifRowCells(l,withCheck));
  return h('div',{className:'expe-trp-tarif-table-wrap'},
    h('table',{className:'table-std'},h('thead',null,head),h('tbody',null,...body))
  );
}

async function validerTarifsBrouillon(ids){
  if(T.editId==null)return;
  try{
    const body=ids&&ids.length?{ids:ids.map(Number)}:{};
    const res=await api('/api/expe/transporteurs/'+T.editId+'/tarifs/valider',{
      method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)
    });
    showToast((res.actives!=null?res.actives:0)+' ligne(s) active(s).','success');
    await loadTarifsTransporteur(T.editId);
  }catch(e){
    showToast(e.message||'Validation impossible','danger');
  }
}

function activerTarifsSelection(){
  const checks=document.querySelectorAll('.tarif-check:checked');
  const ids=Array.from(checks).map(el=>Number(el.getAttribute('data-id'))).filter(n=>!isNaN(n));
  if(!ids.length){showToast('Sélectionnez au moins une ligne.','danger');return;}
  void validerTarifsBrouillon(ids);
}

async function importTarifsCsv(file){
  if(!file||T.editId==null)return;
  const fd=new FormData();
  fd.append('file',file);
  try{
    const res=await api('/api/expe/transporteurs/'+T.editId+'/tarifs/import-csv',{method:'POST',body:fd});
    showToast(res.message||(res.inserted+' lignes importées. Validez pour activer.'),'success');
    await loadTarifsTransporteur(T.editId);
  }catch(e){
    showToast(e.message||'Import impossible','danger');
  }
}

function _tarifsFileExt(){
  const fname=(T.form&&(T.form.tarif_filename||T.form.tarif_url))||'';
  if(fname){
    const parts=fname.split('.');
    if(parts.length>1)return parts.pop().toLowerCase();
  }
  const tr=(T.list||[]).find(t=>Number(t.id)===Number(T.editId));
  const fn=(tr&&(tr.tarif_filename||tr.tarif_url))||'';
  const p=fn.split('.');
  return p.length>1?p.pop().toLowerCase():'';
}

function _tarifsParserLabel(){
  return ['xlsx','xls'].includes(_tarifsFileExt())?'Parser (Excel)':'Parser avec IA';
}

async function parserTarifs(){
  if(T.editId==null)return;
  const ext=_tarifsFileExt();
  const isExcel=['xlsx','xls'].includes(ext);
  const endpoint=isExcel
    ?'/api/expe/transporteurs/'+T.editId+'/tarifs/parse-excel'
    :'/api/expe/transporteurs/'+T.editId+'/tarif/parse';
  T.tarifs_parsing=true;
  render();
  try{
    const res=await api(endpoint,{method:'POST'});
    showToast(res.message||(res.lignes_extraites+' lignes extraites.'),'success');
    await loadTarifsTransporteur(T.editId);
  }catch(e){
    const msg=e&&e.message?String(e.message):'Erreur lors du parsing.';
    if(msg.indexOf('Format non reconnu')>=0){
      showToast('Format non reconnu. Contacter l\'équipe pour ajouter le support de ce format.','danger');
      console.error('Structure du fichier :',msg);
    }else{
      showToast(msg,'danger');
    }
  }
  T.tarifs_parsing=false;
  render();
}

function renderTarifsOnglet(){
  if(T.tarifs_loading){
    return h('div',{style:{color:'var(--muted)',fontSize:'13px',padding:'12px 0'}},'Chargement…');
  }
  const brouillons=(T.tarifs_lignes||[]).filter(l=>!Number(l.actif));
  const actifs=(T.tarifs_lignes||[]).filter(l=>Number(l.actif));
  const kids=[];
  if(expeCanWrite()){
    const csvInp=h('input',{type:'file',accept:'.csv',style:{display:'none'}});
    csvInp.addEventListener('change',e=>{
      const f=e.target.files&&e.target.files[0];
      if(f)void importTarifsCsv(f);
      e.target.value='';
    });
    kids.push(h('div',{className:'expe-trp-tarif-actions'},
      h('button',{type:'button',className:'btn btn-ghost',onClick:()=>csvInp.click()},'Importer CSV'),
      h('button',{type:'button',id:'btn-parser-tarif',className:'btn btn-ghost',disabled:!!T.tarifs_parsing,
        onClick:()=>void parserTarifs()},
        T.tarifs_parsing
          ?(['xlsx','xls'].includes(_tarifsFileExt())?'Analyse Excel en cours…':'Analyse IA en cours…')
          :_tarifsParserLabel()),
      csvInp
    ));
  }
  if(brouillons.length&&expeCanWrite()){
    kids.push(h('div',{className:'expe-trp-tarif-banner'},
      h('span',null,'Ces lignes sont en brouillon — elles ne sont pas utilisées par le comparateur.'),
      h('button',{type:'button',className:'btn btn-accent',onClick:()=>void validerTarifsBrouillon(null)},'Tout activer'),
      h('button',{type:'button',className:'btn btn-ghost',onClick:activerTarifsSelection},'Activer la sélection')
    ));
  }
  kids.push(h('div',{className:'expe-trp-tarif-sec'},
    h('div',{className:'expe-trp-tarif-sec-h'},'Brouillons en attente de validation'),
    expeTrpTarifsTable(brouillons,true)
  ));
  kids.push(h('div',{className:'expe-trp-tarif-sec'},
    h('div',{className:'expe-trp-tarif-sec-h'},
      h('span',null,'Tarifs actifs'),
      actifs.length?h('span',{className:'expe-trp-badge-actif'},'Actif'):null
    ),
    expeTrpTarifsTable(actifs,false)
  ));
  const fraisRows=(T.tarifs_frais||[]);
  if(fraisRows.length){
    const fHead=h('tr',null,
      h('th',null,'Libellé'),h('th',null,'Mode'),h('th',null,'Valeur'),
      h('th',null,'Mini'),h('th',null,'Inclus auto')
    );
    const fBody=fraisRows.map(fr=>h('tr',null,
      h('td',null,escHtml(fr.libelle||'')),
      h('td',null,escHtml(fr.mode||'')),
      h('td',null,escHtml(String(fr.valeur!=null?fr.valeur:''))),
      h('td',null,fr.mini!=null&&fr.mini!==''?escHtml(String(fr.mini)):'—'),
      h('td',null,h('input',{type:'checkbox',disabled:true,checked:!!Number(fr.applique_defaut)}))
    ));
    kids.push(h('div',{className:'expe-trp-tarif-sec'},
      h('div',{className:'expe-trp-tarif-sec-h'},'Frais annexes'),
      h('div',{className:'expe-trp-tarif-table-wrap'},
        h('table',{className:'table-std'},h('thead',null,fHead),h('tbody',null,...fBody))
      )
    ));
  }else{
    kids.push(h('div',{className:'expe-trp-tarif-sec'},
      h('div',{className:'expe-trp-tarif-sec-h'},'Frais annexes'),
      h('p',{style:{color:'var(--muted)',fontSize:'13px',margin:'0'}},'Aucun frais annexe.')
    ));
  }
  return h('div',null,...kids);
}

function expeTrpBodyFromForm(){
  return {
    nom:(T.form.nom||'').trim(),
    taxe_carburant_pct:(T.form.taxe_carburant_pct||'').trim()||'0',
    contact_nom:(T.form.contact_nom||'').trim()||null,
    contact_email:(T.form.contact_email||'').trim()||null,
    contact_tel:(T.form.contact_tel||'').trim()||null,
    zone_france:T.form.zone_france?1:0,
    zone_france_hors_paris:T.form.zone_france_hors_paris?1:0,
    zone_affretement:T.form.zone_affretement?1:0,
    zone_messagerie:T.form.zone_messagerie?1:0,
    actif:T.form.actif?1:0
  };
}

async function saveTransporteur(){
  if(T.saving)return;
  const body=expeTrpBodyFromForm();
  if(!body.nom){showToast('Nom du transporteur obligatoire','danger');return;}
  T.saving=true;
  render();
  try{
    let saved;
    if(T.editId!=null){
      saved=await api('/api/expe/transporteurs/'+T.editId,{
        method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)
      });
      showToast('Transporteur modifié.','success');
    }else{
      saved=await api('/api/expe/transporteurs',{
        method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)
      });
      showToast('Transporteur enregistré.','success');
    }
    if(T.tarifFile&&saved&&saved.id){
      await uploadTarif(saved.id,T.tarifFile);
    }
    T.saving=false;
    closeTransporteurModal();
    await loadTransporteurs();
  }catch(e){
    T.saving=false;
    showToast(e.message||'Enregistrement impossible','danger');
    render();
  }
}

async function uploadTarif(id,file){
  if(!file||!id)return;
  const ext=(file.name||'').split('.').pop().toLowerCase();
  const ok=['pdf','xlsx','xls','jpg','jpeg','png','webp','gif'];
  if(!ok.includes(ext)){
    showToast('Format non accepté (PDF, Excel, image).','danger');
    return;
  }
  if(file.size>10*1024*1024){
    showToast('Fichier trop volumineux (max 10 Mo).','danger');
    return;
  }
  const fd=new FormData();
  fd.append('fichier',file);
  try{
    await api('/api/expe/transporteurs/'+id+'/tarif',{method:'POST',body:fd});
    showToast('Tarif enregistré.','success');
    await loadTransporteurs();
    if(T.editId!=null&&Number(T.editId)===Number(id)){
      const tr=(T.list||[]).find(x=>Number(x.id)===Number(id));
      if(tr){
        T.form.tarif_filename=tr.tarif_filename||'';
        T.form.tarif_url=tr.tarif_url||'';
      }
      if(T.modalOpen)render();
    }
  }catch(e){
    showToast(e.message||'Upload impossible','danger');
  }
}

async function deleteTarif(id){
  if(!confirm('Supprimer le fichier tarif ?'))return;
  try{
    await api('/api/expe/transporteurs/'+id+'/tarif',{method:'DELETE'});
    showToast('Tarif supprimé.','success');
    if(T.editId!=null&&Number(T.editId)===Number(id)){
      T.form.tarif_filename='';
      T.form.tarif_url='';
    }
    await loadTransporteurs();
  }catch(e){
    showToast(e.message||'Suppression impossible','danger');
  }
}

function expeTrpTarifUrl(id){
  return '/api/expe/transporteurs/'+id+'/tarif';
}

async function toggleActif(id,actif){
  const tr=(T.list||[]).find(x=>Number(x.id)===Number(id));
  if(!tr)return;
  const next=actif?1:0;
  if(!next){
    if(!confirm('Désactiver ce transporteur ?'))return;
  }
  try{
    await api('/api/expe/transporteurs/'+id,{
      method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({actif:next})
    });
    showToast(next?'Transporteur réactivé.':'Transporteur désactivé.','success');
    await loadTransporteurs();
  }catch(e){
    showToast(e.message||'Mise à jour impossible','danger');
  }
}

function expeTrpBadgesCell(badges,cls){
  if(!badges||!badges.length)return h('span',{style:{color:'var(--muted)'}},'—');
  return h('div',{className:'expe-trp-cell-badges'},...badges.map(b=>h('span',{className:cls||'expe-trp-zone'},b)));
}

function expeTrpContactCell(tr){
  const emailRaw=(tr.contact_email||'').trim();
  const lines=[];
  if(tr.contact_nom){
    lines.push(h('div',{className:'expe-trp-contact-line'},iconEl('user',12),' ',escHtml(tr.contact_nom)));
  }
  if(tr.contact_tel){
    lines.push(h('div',{className:'expe-trp-contact-line'},expeTrpIconPhone(12),' ',escHtml(tr.contact_tel)));
  }
  if(emailRaw){
    if(expeTrpIsPortailUrl(emailRaw)){
      lines.push(h('a',{className:'expe-trp-portail',href:emailRaw,target:'_blank',rel:'noopener',onClick:e=>e.stopPropagation()},
        iconEl('arrow-right',12),' Portail'));
    }else{
      lines.push(h('a',{className:'expe-trp-contact-line',href:'mailto:'+encodeURIComponent(emailRaw),onClick:e=>e.stopPropagation()},
        iconEl('mail',12),' ',escHtml(emailRaw)));
    }
  }
  if(!lines.length)return h('span',{style:{color:'var(--muted)'}},'—');
  const kids=[...lines];
  if(emailRaw||tr.contact_tel){
    kids.push(h('button',{type:'button',className:'btn-ghost',style:{marginTop:'4px',padding:'4px 8px',fontSize:'11px'},
      onClick:()=>expeTrpOpenContact(tr)},
      iconEl(expeTrpIsPortailUrl(emailRaw)?'arrow-right':'mail',12),
      ' ',expeTrpIsPortailUrl(emailRaw)?'Portail':'Contacter'));
  }
  return h('div',{className:'expe-trp-contact-col'},...kids);
}

function renderExpeTranspList(){
  const rows=expeTrpFiltered();
  if(T.loading&&!rows.length){
    return h('div',{className:'expe-trp-empty'},'Chargement…');
  }
  if(!rows.length){
    const q=(T.filter||'').trim();
    return h('div',{className:'expe-trp-empty'},
      q?'Aucun résultat pour « '+escHtml(q)+' »':'Aucun transporteur enregistré.'
    );
  }
  const head=h('tr',null,
    h('th',null,'Transporteur'),
    h('th',null,'Zones'),
    h('th',null,'Comparateur'),
    h('th',null,'Carburant'),
    h('th',null,'Contact'),
    h('th',null,'Tarif'),
    expeCanWrite()?h('th',{style:{width:'1%',whiteSpace:'nowrap'}},''):null
  );
  const body=rows.map(tr=>{
    const inactive=!Number(tr.actif);
    const zones=expeTrpZonesBadges(tr);
    const taxe=tr.taxe_carburant_pct!=null?Number(tr.taxe_carburant_pct):0;
    const services=expeTrpServiceBadges(tr);
    const isActive=!!Number(tr.actif);
    const nameCell=h('td',null,
      h('span',{className:'expe-trp-name'},escHtml(tr.nom||'')),
      inactive?h('span',{className:'expe-trp-badge-inactif'},'Inactif'):null
    );
    const tarifCell=tr.tarif_url
      ? h('td',{className:'expe-trp-tarif'},
          h('a',{href:expeTrpTarifUrl(tr.id),target:'_blank',rel:'noopener'},iconEl('file',12),' ',escHtml(tr.tarif_filename||'Tarif')))
      : h('td',{style:{color:'var(--muted)',fontSize:'12px'}},'—');
    const actionCell=expeCanWrite()?h('td',{style:{whiteSpace:'nowrap'}},
      h('div',{className:'expe-trp-actions'},
        h('button',{type:'button',className:'btn-ghost',title:'Modifier',onClick:()=>openTransporteurModal(tr.id)},iconEl('edit',14)),
        h('button',{type:'button',className:'btn-ghost',title:isActive?'Désactiver':'Réactiver',
          onClick:()=>toggleActif(tr.id,isActive?0:1)},iconEl('sliders',14))
      )
    ):null;
    return h('tr',{className:inactive?'expe-trp-row-inactive':''},
      nameCell,
      h('td',null,expeTrpBadgesCell(zones,'expe-trp-zone')),
      h('td',null,expeTrpBadgesCell(services,'expe-trp-svc')),
      h('td',{className:'expe-trp-num'},escHtml(String(taxe))+' %'),
      h('td',null,expeTrpContactCell(tr)),
      tarifCell,
      actionCell
    );
  });
  return h('div',{className:'expe-trp-table-wrap'},
    h('table',{className:'table-std expe-trp-table'},h('thead',null,head),h('tbody',null,...body))
  );
}

function renderExpeTranspPanel(){
  const overlay=h('div',{className:'expe-trp-overlay'+(T.panelOpen?' open':'')});
  overlay.addEventListener('click',e=>{if(e.target===overlay)closeExpeTranspPanel();});
  const panel=h('div',{className:'expe-trp-panel'+(T.panelOpen?' open':'')});
  const search=h('input',{
    id:'expe-trp-search',
    type:'search',
    className:'expe-trp-search',
    placeholder:'Rechercher un transporteur…',
    value:T.filter||'',
    onInput:e=>{T.filter=e.target.value;renderTransporteurs();}
  });
  search.addEventListener('keydown',e=>{
    if(e.key==='Escape'){T.filter='';renderTransporteurs();}
  });
  const headKids=[
    h('h2',null,'Transporteurs'),
    search,
  ];
  if(expeCanWrite()){
    headKids.splice(1,0,h('button',{type:'button',className:'btn btn-accent',onClick:()=>openTransporteurModal(null)},iconEl('plus',14),' Ajouter'));
  }
  panel.appendChild(h('div',{className:'expe-trp-head'},...headKids,
    h('button',{type:'button',className:'expe-trp-close',title:'Fermer',onClick:closeExpeTranspPanel},iconEl('x',18))
  ));
  const body=h('div',{className:'expe-trp-body'});
  body.appendChild(renderExpeTranspList());
  panel.appendChild(body);
  overlay.appendChild(panel);
  return overlay;
}

function renderExpeTransporteurModal(){
  if(!T.modalOpen)return null;
  const isEdit=T.editId!=null;
  const f=T.form||{};
  const overlay=h('div',{className:'expe-trp-modal-overlay'});
  overlay.addEventListener('click',e=>{if(e.target===overlay)closeTransporteurModal();});
  const box=h('div',{className:'expe-trp-modal'});
  const mkText=(label,key,opts)=>{
    const o=opts||{};
    const inp=h('input',{type:o.type||'text',value:f[key]!=null?String(f[key]):'',
      placeholder:o.placeholder||'',step:o.step,min:o.min});
    inp.addEventListener('input',e=>{T.form[key]=e.target.value;});
    return h('div',{className:'expe-trp-field'},h('label',null,label),inp);
  };
  const mkCheck=(label,key)=>{
    const cb=h('input',{type:'checkbox'});
    cb.checked=!!f[key];
    cb.addEventListener('change',e=>{T.form[key]=e.target.checked;});
    const row=h('label',{className:'expe-trp-check'},cb,h('span',null,label));
    return row;
  };
  box.appendChild(h('h3',null,isEdit?'Modifier le transporteur':'Ajouter un transporteur'));
  if(isEdit){
    box.appendChild(h('div',{className:'expe-trp-tabs'},
      h('button',{type:'button',className:'expe-trp-tab'+(T.modalTab==='fiche'?' active':''),onClick:()=>setTransporteurModalTab('fiche')},'Fiche'),
      h('button',{type:'button',className:'expe-trp-tab'+(T.modalTab==='tarifs'?' active':''),onClick:()=>setTransporteurModalTab('tarifs')},'Tarifs')
    ));
  }
  if(isEdit&&T.modalTab==='tarifs'){
    box.appendChild(renderTarifsOnglet());
  }else{
    const ident=h('div',{className:'expe-trp-sec'},
      h('div',{className:'expe-trp-sec-title'},'Identité'),
      mkText('Nom du transporteur *','nom'),
      mkText('Taxe carburant %','taxe_carburant_pct',{type:'number',step:'0.1',min:'0'})
    );
    const contact=h('div',{className:'expe-trp-sec'},
      h('div',{className:'expe-trp-sec-title'},'Contact'),
      mkText('Nom du contact','contact_nom'),
      mkText('Email','contact_email',{type:'email'}),
      mkText('Téléphone','contact_tel',{type:'tel'})
    );
    const zones=h('div',{className:'expe-trp-sec'},
      h('div',{className:'expe-trp-sec-title'},'Zones desservies'),
      h('div',{className:'expe-trp-checks'},
        mkCheck('France','zone_france'),
        mkCheck('France hors Paris','zone_france_hors_paris'),
        mkCheck('Affrètement (> 6 palettes)','zone_affretement'),
        mkCheck('Messagerie / Ramasse (< 6 palettes)','zone_messagerie')
      )
    );
    box.appendChild(ident);
    box.appendChild(contact);
    box.appendChild(zones);
    if(isEdit){
      const tarifSec=h('div',{className:'expe-trp-sec'},
        h('div',{className:'expe-trp-sec-title'},'Fichier tarif source')
      );
      if(f.tarif_url){
        const row=h('div',{className:'expe-trp-tarif-row'},
          h('span',{style:{fontSize:'13px',color:'var(--text2)'}},iconEl('file',14),' ',escHtml(f.tarif_filename||'Fichier tarif')),
          h('a',{className:'btn btn-ghost',href:expeTrpTarifUrl(T.editId),target:'_blank',rel:'noopener'},'Voir'),
          h('button',{type:'button',className:'btn btn-danger',onClick:()=>deleteTarif(T.editId)},'Supprimer')
        );
        tarifSec.appendChild(row);
      }
      const drop=h('div',{className:'expe-trp-drop'+(T.uploadDrag?' drag':'')},
        h('div',{style:{fontSize:'13px',color:'var(--text2)'}},iconEl('upload',20),' Déposer un fichier ou cliquer'),
        h('div',{className:'expe-trp-drop-hint'},'Formats acceptés : PDF, Excel, image · max 10 Mo')
      );
      const fileInp=h('input',{type:'file',accept:'.pdf,.xlsx,.xls,.jpg,.jpeg,.png,.webp,.gif',style:{display:'none'}});
      const onPick=async file=>{
        if(!file)return;
        if(T.editId!=null){await uploadTarif(T.editId,file);}
        else{T.tarifFile=file;showToast('Fichier prêt — enregistrez pour envoyer.','info');render();}
      };
      fileInp.addEventListener('change',e=>{const file=e.target.files&&e.target.files[0];void onPick(file);});
      drop.addEventListener('click',()=>fileInp.click());
      drop.addEventListener('dragover',e=>{e.preventDefault();T.uploadDrag=true;render();});
      drop.addEventListener('dragleave',()=>{T.uploadDrag=false;render();});
      drop.addEventListener('drop',e=>{
        e.preventDefault();T.uploadDrag=false;
        const file=e.dataTransfer.files&&e.dataTransfer.files[0];
        void onPick(file);
      });
      if(T.tarifFile){
        drop.appendChild(h('div',{style:{marginTop:'8px',fontSize:'12px',color:'var(--accent)',fontWeight:'600'}},
          'Sélectionné : '+escHtml(T.tarifFile.name)));
      }
      tarifSec.appendChild(drop);
      tarifSec.appendChild(fileInp);
      box.appendChild(tarifSec);
    }else{
      box.appendChild(h('div',{className:'expe-trp-sec'},
        h('div',{className:'expe-trp-sec-title'},'Fichier tarif source'),
        h('p',{className:'expe-trp-drop-hint'},'Après création, ouvrez la fiche pour déposer un fichier tarif.')
      ));
    }
  }
  const onFicheTab=!isEdit||T.modalTab==='fiche';
  box.appendChild(h('div',{className:'expe-trp-modal-actions'},
    h('button',{type:'button',className:'btn btn-ghost',onClick:closeTransporteurModal},'Annuler'),
    onFicheTab?h('button',{type:'button',className:'btn btn-accent',disabled:!!T.saving,onClick:()=>saveTransporteur()},
      T.saving?'Enregistrement…':'Enregistrer'):null
  ));
  overlay.appendChild(box);
  return overlay;
}

function renderExpeTransporteurs(){
  if(!T.pageLoaded&&!T.loading){
    T.pageLoaded=true;
    void loadTransporteurs();
  }
  const search=h('input',{
    id:'expe-trp-page-search',
    type:'search',
    className:'expe-trp-search',
    placeholder:'Rechercher un transporteur…',
    value:T.filter||'',
    onInput:e=>{T.filter=e.target.value;renderTransporteurs();}
  });
  search.addEventListener('keydown',e=>{
    if(e.key==='Escape'){T.filter='';renderTransporteurs();}
  });
  const headKids=[
    search,
    h('button',{type:'button',className:'btn btn-ghost',onClick:openExpeTranspPanel},iconEl('layers',14),' Panneau latéral'),
    expeCanWrite()?h('button',{type:'button',className:'btn btn-accent',onClick:()=>openTransporteurModal(null)},iconEl('plus',14),' Ajouter'):null
  ];
  return h('div',{className:'expe-trp-page'},
    h('div',{className:'expe-trp-page-head'},...headKids),
    renderExpeTranspList()
  );
}
"""

EXPE_COMPARATEUR_CSS = r"""
/* ── MyExpé — comparateur tarifs (API) ── */
.expe-cmp-wrap{max-width:640px}
.expe-cmp-title{font-size:15px;font-weight:700;color:var(--text);margin:0 0 20px}
.expe-cmp-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:12px}
@media(max-width:520px){.expe-cmp-grid{grid-template-columns:1fr}}
.expe-cmp-label{display:flex;flex-direction:column;gap:6px;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text2)}
.expe-cmp-inp{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 16px;color:var(--text);font-size:14px;font-family:inherit;outline:none;width:100%}
.expe-cmp-inp:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 12%,transparent)}
.expe-cmp-btn{background:var(--accent);color:var(--bg);border:none;border-radius:10px;padding:12px 24px;font-weight:700;font-size:14px;cursor:pointer;font-family:inherit}
.expe-cmp-btn:hover:not(:disabled){filter:brightness(1.05)}
.expe-cmp-btn:disabled{opacity:.5;cursor:not-allowed}
.expe-cmp-results{margin-top:24px}
.expe-cmp-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;position:relative}
.expe-cmp-card.best{border-color:var(--accent)}
.expe-cmp-badge{position:absolute;top:12px;right:12px;background:var(--accent);color:var(--bg);font-size:11px;font-weight:700;padding:3px 8px;border-radius:6px}
.expe-cmp-cards{display:flex;flex-direction:column;gap:8px}
.expe-cmp-ne-row{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:12px 16px;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
"""

EXPE_COMPARATEUR_JS = r"""
// ── MyExpé — comparateur tarifs (API expe_tarifs) ─────────────────

function expeCompareIcon(size){
  const s=size||16;
  const el=document.createElementNS('http://www.w3.org/2000/svg','svg');
  el.setAttribute('width',s);el.setAttribute('height',s);el.setAttribute('viewBox','0 0 24 24');
  el.setAttribute('fill','none');el.setAttribute('stroke','currentColor');el.setAttribute('stroke-width','2');
  el.setAttribute('stroke-linecap','round');el.setAttribute('stroke-linejoin','round');
  el.innerHTML='<line x1="2" y1="12" x2="22" y2="12"/><path d="M6 12l-4 8h8L6 12z"/><path d="M18 12l-4 8h8L18 12z"/><line x1="12" y1="2" x2="12" y2="12"/>';
  return el;
}

function renderResultatsComparateur(data){
  const el=document.getElementById('cmp-resultats');
  if(!el)return;
  const elig=data.eligibles||[];
  const noelig=data.non_eligibles||[];
  if(!elig.length&&!noelig.length){
    el.innerHTML='<p style="color:var(--muted);font-size:13px">Aucun résultat.</p>';
    return;
  }
  let html='';
  if(data.departement_deduit){
    html+='<p style="font-size:12px;color:var(--muted);margin:0 0 16px">Département déduit du code postal : <strong>'+escHtml(data.departement_deduit)+'</strong></p>';
  }
  if(elig.length){
    html+='<div style="margin-bottom:24px"><div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text2);margin-bottom:10px">'
      +elig.length+' transporteur'+(elig.length>1?'s':'')+' éligible'+(elig.length>1?'s':'')
      +'</div><div class="expe-cmp-cards">';
    elig.forEach(e=>{
      const mc=!!e.moins_cher;
      html+='<div class="expe-cmp-card'+(mc?' best':'')+'">'
        +(mc?'<span class="expe-cmp-badge">Moins cher</span>':'')
        +'<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;flex-wrap:wrap">'
        +'<span style="font-size:15px;font-weight:700;color:var(--text)">'+escHtml(e.transporteur)+'</span>'
        +'<span style="font-size:18px;font-weight:700;color:'+(mc?'var(--accent)':'var(--text)')+'">'+Number(e.prix_ht).toFixed(2)+' €</span>'
        +'<span style="font-size:12px;color:var(--muted)">HT</span></div>'
        +'<details style="font-size:12px;color:var(--text2)"><summary style="cursor:pointer;color:var(--muted);margin-bottom:4px">Détail du calcul</summary>'
        +'<div style="margin-top:8px;padding:10px;background:var(--bg);border-radius:8px;display:flex;flex-direction:column;gap:4px">'
        +'<div>Base : '+escHtml((e.detail_calcul&&e.detail_calcul.base)||'')+'</div>'
        +((e.detail_calcul&&e.detail_calcul.frais)||[]).map(fr=>'<div>'+escHtml(fr.libelle)+' : '+escHtml(fr.detail)+'</div>').join('')
        +'<div style="border-top:1px solid var(--border);margin-top:6px;padding-top:6px;font-weight:700;color:var(--text)">Total : '+Number(e.prix_ht).toFixed(2)+' € HT</div>'
        +'</div></details></div>';
    });
    html+='</div></div>';
  }
  if(noelig.length){
    html+='<details style="margin-top:8px"><summary style="font-size:12px;color:var(--muted);cursor:pointer">'
      +noelig.length+' transporteur'+(noelig.length>1?'s':'')+' non éligible'+(noelig.length>1?'s':'')+' — voir les raisons</summary>'
      +'<div style="margin-top:8px;display:flex;flex-direction:column;gap:6px">';
    noelig.forEach(ne=>{
      html+='<div class="expe-cmp-ne-row"><span style="font-size:13px;color:var(--text2)">'+escHtml(ne.transporteur)+'</span>'
        +'<span style="font-size:12px;color:var(--muted)">'+escHtml(ne.raison)+'</span></div>';
    });
    html+='</div></details>';
  }
  el.innerHTML=html;
}

async function lancerComparateur(){
  const poids=parseFloat(document.getElementById('cmp-poids')&&document.getElementById('cmp-poids').value)||0;
  const nb_palette=parseFloat(document.getElementById('cmp-pal')&&document.getElementById('cmp-pal').value)||0;
  const cp=(document.getElementById('cmp-cp')&&document.getElementById('cmp-cp').value||'').trim();
  const type_envoi=document.getElementById('cmp-type')&&document.getElementById('cmp-type').value||'messagerie';
  if(!cp){showToast('Code postal destination obligatoire','danger');return;}
  if(!poids&&!nb_palette){showToast('Saisir au moins un poids ou un nombre de palettes','danger');return;}
  S.comparateur_form={poids_total_kg:poids,nb_palette,code_postal_destination:cp,type_envoi};
  const btn=document.getElementById('btn-comparer');
  const resEl=document.getElementById('cmp-resultats');
  if(btn){btn.disabled=true;btn.textContent='Calcul en cours...';}
  if(resEl)resEl.innerHTML='<p style="color:var(--muted);font-size:13px">Calcul en cours...</p>';
  try{
    const data=await api('/api/expe/comparateur',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({poids_total_kg:poids,nb_palette,code_postal_destination:cp,type_envoi})
    });
    renderResultatsComparateur(data);
  }catch(e){
    showToast(e.message||'Erreur lors du calcul','danger');
    if(resEl)resEl.innerHTML='';
  }finally{
    if(btn){btn.disabled=false;btn.textContent='Comparer';}
  }
}

function renderExpeComparateurTarifs(){
  const f=S.comparateur_form||{};
  const mkInp=(id,type,val,placeholder,extra)=>{
    const o=extra||{};
    const inp=h('input',{id,type,value:val!=null&&val!==''?String(val):'',placeholder,className:'expe-cmp-inp'});
    if(o.step)inp.step=o.step;
    if(o.min!=null)inp.min=o.min;
    return inp;
  };
  const typeSel=h('select',{id:'cmp-type',className:'expe-cmp-inp'},
    h('option',{value:'messagerie',selected:(f.type_envoi||'messagerie')==='messagerie'},'Messagerie'),
    h('option',{value:'ramasse',selected:f.type_envoi==='ramasse'},'Ramasse'),
    h('option',{value:'affretement',selected:f.type_envoi==='affretement'},'Affrètement')
  );
  const btn=h('button',{id:'btn-comparer',type:'button',className:'expe-cmp-btn'},'Comparer');
  btn.addEventListener('click',()=>void lancerComparateur());
  const grid=h('div',{className:'expe-cmp-grid'},
    h('label',{className:'expe-cmp-label'},'Poids total (kg)',mkInp('cmp-poids','number',f.poids_total_kg,'ex : 340',{step:'0.1',min:'0'})),
    h('label',{className:'expe-cmp-label'},'Nombre de palettes',mkInp('cmp-pal','number',f.nb_palette,'ex : 3',{step:'1',min:'0'})),
    h('label',{className:'expe-cmp-label'},'Code postal destination',mkInp('cmp-cp','text',f.code_postal_destination,'ex : 75011')),
    h('label',{className:'expe-cmp-label'},'Type d\'envoi',typeSel)
  );
  [].forEach.call(grid.querySelectorAll('input'),inp=>{
    inp.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();void lancerComparateur();}});
  });
  typeSel.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();void lancerComparateur();}});
  const wrap=h('div',{id:'section-comparateur',className:'expe-cmp-wrap'},
    h('h2',{className:'expe-cmp-title'},'Comparer les transporteurs'),
    grid,
    btn,
    h('div',{id:'cmp-resultats',className:'expe-cmp-results'})
  );
  return wrap;
}

function ouvrirComparateurDepuisDepart(departId,poids,nb_palette,cp){
  S.comparateur_form={
    poids_total_kg:poids,
    nb_palette:nb_palette,
    code_postal_destination:cp,
    type_envoi:nb_palette>=6?'affretement':'messagerie',
    _source_depart_id:departId
  };
  set({expeTab:'comparateur'});
  requestAnimationFrame(()=>{
    requestAnimationFrame(()=>{
      const fPoids=document.getElementById('cmp-poids');
      const fPal=document.getElementById('cmp-pal');
      const fCp=document.getElementById('cmp-cp');
      const fType=document.getElementById('cmp-type');
      if(fPoids)fPoids.value=poids||'';
      if(fPal)fPal.value=nb_palette||'';
      if(fCp)fCp.value=cp||'';
      if(fType)fType.value=nb_palette>=6?'affretement':'messagerie';
      if(typeof lancerComparateur==='function')void lancerComparateur();
    });
  });
}
"""

EXPE_DEVIS_JS = r"""
// ── MyExpé — devis & prospects ───────────────────────────────────

function expeDevisIcon(size){
  const s=size||16;
  const el=document.createElementNS('http://www.w3.org/2000/svg','svg');
  el.setAttribute('width',s);el.setAttribute('height',s);el.setAttribute('viewBox','0 0 24 24');
  el.setAttribute('fill','none');el.setAttribute('stroke','currentColor');el.setAttribute('stroke-width','2');
  el.setAttribute('stroke-linecap','round');el.setAttribute('stroke-linejoin','round');
  el.innerHTML='<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>';
  return el;
}

function ouvrirDevisDepuisDepart(departId,poids,nb_palette,cp){
  set({expeTab:'devis'});
  requestAnimationFrame(()=>{
    ouvrirModalNouvelleDemande({
      id:departId,
      poids_total_kg:poids,
      nb_palette:nb_palette,
      code_postal_destination:cp
    });
  });
}

function fermerExpeDevisModal(){
  set({expeDevisModal:null});
}

async function chargerDemandes(){
  const statut=S.devis_filtre||'ouverte';
  try{
    S.devis_demandes=await api('/api/expe/devis/demandes?statut='+encodeURIComponent(statut))||[];
  }catch(e){
    showToast(e.message||'Chargement impossible','danger');
    S.devis_demandes=[];
  }
  render();
}

async function chargerProspects(){
  try{
    S.prospects=await api('/api/expe/prospects')||[];
  }catch(e){
    showToast(e.message||'Chargement impossible','danger');
    S.prospects=[];
  }
  render();
}

function ouvrirModalNouvelleDemande(departPreRempli){
  const d=departPreRempli||{};
  set({expeDevisModal:{type:'nouvelle',departId:d.id||null,form:{
    poids_total_kg:d.poids_total_kg!=null?String(d.poids_total_kg):'',
    nb_palette:d.nb_palette!=null?String(d.nb_palette):'',
    code_postal_destination:d.code_postal_destination||'',
    type_envoi:(d.nb_palette||0)>=6?'affretement':(d.type_envoi||'messagerie'),
    contraintes:''
  }}});
}

async function validerNouvelleDemande(){
  const m=S.expeDevisModal;
  if(!m||m.type!=='nouvelle')return;
  const f=m.form||{};
  const cp=(f.code_postal_destination||'').trim();
  if(!cp){showToast('Code postal destination obligatoire','danger');return;}
  try{
    const demande=await api('/api/expe/devis/demandes',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        depart_id:m.departId||null,
        poids_total_kg:parseFloat(f.poids_total_kg)||null,
        nb_palette:parseFloat(f.nb_palette)||null,
        code_postal_destination:cp,
        type_envoi:f.type_envoi||'messagerie',
        contraintes:(f.contraintes||'').trim()||null
      })
    });
    fermerExpeDevisModal();
    showToast('Demande créée.','success');
    await chargerDemandes();
    await ouvrirDetailDemande(demande.id);
  }catch(e){
    showToast(e.message||'Erreur','danger');
  }
}

async function ouvrirDetailDemande(demandeId){
  try{
    const data=await api('/api/expe/devis/demandes/'+demandeId);
    set({expeDevisModal:{type:'detail',demandeId,demande:data.demande,reponses:data.reponses||[]}});
  }catch(e){
    showToast(e.message||'Chargement impossible','danger');
  }
}

async function ouvrirModalEnvoi(demandeId){
  if(!T.list.length&&!T.loading)await loadTransporteurs();
  set({expeDevisModal:{type:'envoi',demandeId,checks:{}}});
}

async function confirmerEnvoi(demandeId){
  const m=S.expeDevisModal;
  const checks=m&&m.checks?m.checks:{};
  const trpIds=[],extras=[];
  Object.keys(checks).forEach(k=>{
    const c=checks[k];
    if(!c.checked)return;
    if(c.kind==='actif')trpIds.push(Number(c.id));
    else extras.push({nom:c.nom,email:c.email});
  });
  if(!trpIds.length&&!extras.length){
    showToast('Sélectionner au moins un transporteur','danger');
    return;
  }
  try{
    const res=await api('/api/expe/devis/demandes/'+demandeId+'/envoyer',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({transporteur_ids:trpIds,transporteur_extras:extras})
    });
    fermerExpeDevisModal();
    showToast(res.envoyes+' email'+(res.envoyes>1?'s':'')+' envoyé'+(res.envoyes>1?'s':'')+'.','success');
    if(res.echecs>0)showToast(res.echecs+' échec(s) : '+((res.destinataires_ko||[]).join(', ')),'danger');
    await chargerDemandes();
    await ouvrirDetailDemande(demandeId);
  }catch(e){
    showToast(e.message||'Erreur envoi','danger');
  }
}

function ouvrirSaisieReponse(reponseId,demandeId){
  set({expeDevisModal:{type:'saisie',reponseId,demandeId,form:{prix:'',delai:'',comment:''}}});
}

async function validerSaisieReponse(reponseId,demandeId){
  const m=S.expeDevisModal;
  const prix=parseFloat(m&&m.form&&m.form.prix);
  if(isNaN(prix)){showToast('Prix obligatoire','danger');return;}
  try{
    await api('/api/expe/devis/reponses/'+reponseId,{
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        prix,
        delai_jours:parseInt(m.form.delai,10)||null,
        commentaire:(m.form.comment||'').trim()||null
      })
    });
    showToast('Réponse enregistrée.','success');
    await ouvrirDetailDemande(demandeId);
  }catch(e){
    showToast(e.message||'Erreur','danger');
  }
}

async function retenirReponse(reponseId,demandeId){
  if(!confirm('Retenir ce transporteur et clôturer la demande ?'))return;
  try{
    await api('/api/expe/devis/reponses/'+reponseId+'/retenir',{method:'POST'});
    showToast('Transporteur retenu. Demande clôturée.','success');
    fermerExpeDevisModal();
    await chargerDemandes();
  }catch(e){
    showToast(e.message||'Erreur','danger');
  }
}

function ouvrirModalProspect(prospectId){
  const p=prospectId?(S.prospects||[]).find(x=>Number(x.id)===Number(prospectId)):null;
  set({expeDevisModal:{type:'prospect',prospectId:prospectId||null,form:p?{
    nom:p.nom||'',statut_demarchage:p.statut_demarchage||'a_contacter',
    type_service:p.type_service||'messagerie',contact_email:p.contact_email||'',
    contact_tel:p.contact_tel||'',zone_couverte:p.zone_couverte||'',
    capacite_max_pal:p.capacite_max_pal!=null?String(p.capacite_max_pal):'',
    notes:p.notes||''
  }:{
    nom:'',statut_demarchage:'a_contacter',type_service:'messagerie',
    contact_email:'',contact_tel:'',zone_couverte:'',capacite_max_pal:'',notes:''
  }}});
}

async function sauvegarderProspect(){
  const m=S.expeDevisModal;
  if(!m||m.type!=='prospect')return;
  const f=m.form||{};
  const nom=(f.nom||'').trim();
  if(!nom){showToast('Nom obligatoire','danger');return;}
  const body={
    nom,statut_demarchage:f.statut_demarchage,type_service:f.type_service,
    contact_email:(f.contact_email||'').trim()||null,
    contact_tel:(f.contact_tel||'').trim()||null,
    zone_couverte:(f.zone_couverte||'').trim()||null,
    capacite_max_pal:parseInt(f.capacite_max_pal,10)||null,
    notes:(f.notes||'').trim()||null
  };
  try{
    if(m.prospectId){
      await api('/api/expe/prospects/'+m.prospectId,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      showToast('Prospect modifié.','success');
    }else{
      await api('/api/expe/prospects',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      showToast('Prospect ajouté.','success');
    }
    fermerExpeDevisModal();
    await chargerProspects();
  }catch(e){
    showToast(e.message||'Erreur','danger');
  }
}

async function supprimerProspect(prospectId){
  if(!confirm('Supprimer ce prospect ?'))return;
  try{
    await api('/api/expe/prospects/'+prospectId,{method:'DELETE'});
    showToast('Prospect supprimé.','success');
    fermerExpeDevisModal();
    await chargerProspects();
  }catch(e){
    showToast(e.message||'Suppression impossible','danger');
  }
}

function expeDevisStatutLabel(st){
  const m={
    envoyee:{t:'Envoyée',c:'var(--muted)'},
    ouvert:{t:'Ouverte',c:'var(--warn)'},
    recue:{t:'Reçue',c:'var(--accent)'},
    retenue:{t:'Retenue',c:'var(--success)'},
    refusee:{t:'Refusée',c:'var(--muted)',strike:true},
    echec:{t:'Échec envoi',c:'var(--danger)'}
  };
  return m[st]||{t:st||'—',c:'var(--muted)'};
}

function expeDevisSuiviTag(d){
  const env=Number(d.nb_envoyes)||0;
  const rep=Number(d.nb_recus)||0;
  if(!env&&!rep)return null;
  const parts=[];
  if(env)parts.push(env+' envoyé'+(env>1?'s':''));
  if(rep)parts.push(rep+' réponse'+(rep>1?'s':''));
  return h('span',{className:'expe-devis-pill accent'},parts.join(' / '));
}

function renderExpeDevisModal(){
  const m=S.expeDevisModal;
  if(!m)return null;
  const overlay=h('div',{className:'expe-devis-modal-overlay'});
  overlay.addEventListener('click',e=>{if(e.target===overlay)fermerExpeDevisModal();});
  const box=h('div',{className:'expe-devis-modal'});
  const closeBtn=h('button',{type:'button',className:'btn-ghost expe-devis-close',onClick:fermerExpeDevisModal},iconEl('x',16));

  if(m.type==='nouvelle'){
    const f=m.form||{};
    const mk=(label,key,opts)=>{
      const o=opts||{};
      const inp=h('input',{type:o.type||'text',className:'expe-devis-inp',value:f[key]!=null?String(f[key]):''});
      if(o.step)inp.step=o.step;
      inp.addEventListener('input',e=>{m.form[key]=e.target.value;});
      return h('label',{className:'expe-devis-label'},label,inp);
    };
    const typeSel=h('select',{className:'expe-devis-inp'},
      h('option',{value:'messagerie',selected:(f.type_envoi||'messagerie')==='messagerie'},'Messagerie'),
      h('option',{value:'ramasse',selected:f.type_envoi==='ramasse'},'Ramasse'),
      h('option',{value:'affretement',selected:f.type_envoi==='affretement'},'Affrètement')
    );
    typeSel.addEventListener('change',e=>{m.form.type_envoi=e.target.value;});
    box.appendChild(h('div',{className:'expe-devis-modal-head'},
      h('span',{style:{fontWeight:'700',fontSize:'15px'}},'Nouvelle demande de devis'),closeBtn));
    box.appendChild(h('div',{className:'expe-devis-grid'},
      mk('Poids (kg)','poids_total_kg',{type:'number',step:'0.1'}),
      mk('Palettes','nb_palette',{type:'number',step:'1'}),
      mk('CP destination','code_postal_destination'),
      h('label',{className:'expe-devis-label'},'Type d\'envoi',typeSel),
      (()=>{
        const c=h('input',{type:'text',className:'expe-devis-inp',value:f.contraintes||'',placeholder:'Délai, RDV…'});
        c.addEventListener('input',e=>{m.form.contraintes=e.target.value;});
        return h('label',{className:'expe-devis-label',style:{gridColumn:'1 / -1'}},'Contraintes',c);
      })()
    ));
    box.appendChild(h('div',{className:'expe-devis-modal-foot'},
      h('button',{type:'button',className:'btn btn-ghost',onClick:fermerExpeDevisModal},'Annuler'),
      h('button',{type:'button',className:'btn btn-accent',onClick:()=>void validerNouvelleDemande()},'Créer la demande')
    ));
  }else if(m.type==='detail'){
    const d=m.demande||{};
    const reps=m.reponses||[];
    box.appendChild(h('div',{className:'expe-devis-modal-head'},
      h('span',{style:{fontWeight:'700',fontSize:'15px'}},'Demande #'+d.id+' — '+escHtml(d.code_postal_destination||'')),
      closeBtn));
    box.appendChild(h('div',{style:{fontSize:'12px',color:'var(--muted)',marginBottom:'16px'}},
      (d.poids_total_kg?d.poids_total_kg+' kg · ':'')+
      (d.nb_palette?d.nb_palette+' pal. · ':'')+
      escHtml(d.type_envoi||'')+
      (d.contraintes?' · '+escHtml(d.contraintes):'')
    ));
    if(d.statut==='ouverte'&&expeCanWrite()){
      box.appendChild(h('div',{style:{marginBottom:'16px'}},
        h('button',{type:'button',className:'btn btn-accent',onClick:()=>void ouvrirModalEnvoi(d.id)},'Envoyer les demandes')
      ));
    }
    const head=h('tr',null,
      h('th',null,'Transporteur'),h('th',null,'Statut'),h('th',null,'Prix HT'),
      h('th',null,'Délai'),h('th',null,'Commentaire'),h('th',null,'')
    );
    const body=reps.length?reps.map(r=>{
      const sl=expeDevisStatutLabel(r.statut);
      const acts=[];
      if(r.statut==='recue'&&expeCanWrite())acts.push(h('button',{type:'button',className:'btn-ghost',style:{fontSize:'12px',color:'var(--success)'},onClick:()=>void retenirReponse(r.id,d.id)},'Retenir'));
      if((r.statut==='envoyee'||r.statut==='echec')&&expeCanWrite())acts.push(h('button',{type:'button',className:'btn-ghost',style:{fontSize:'12px'},onClick:()=>ouvrirSaisieReponse(r.id,d.id)},'Saisir réponse'));
      return h('tr',null,
        h('td',{style:{fontWeight:'600'}},escHtml(r.nom_transporteur||'—')),
        h('td',null,h('span',{style:{color:sl.c,textDecoration:sl.strike?'line-through':'none'}},sl.t)),
        h('td',null,r.prix!=null?Number(r.prix).toFixed(2)+' €':'—'),
        h('td',null,r.delai_jours!=null?'J+'+r.delai_jours:'—'),
        h('td',{style:{fontSize:'12px',color:'var(--text2)'}},escHtml(r.commentaire||'')),
        h('td',null,...acts)
      );
    }):[h('tr',null,h('td',{colSpan:6,style:{color:'var(--muted)',fontStyle:'italic'}},'Aucune réponse.'))];
    box.appendChild(h('div',{className:'expe-devis-table-wrap'},
      h('table',{className:'table-std'},h('thead',null,head),h('tbody',null,...body))
    ));
  }else if(m.type==='envoi'){
    const trps=(T.list||[]).filter(t=>Number(t.actif)&&t.contact_email&&String(t.contact_email).includes('@'));
    const prospects=(S.prospects||[]).filter(p=>p.statut_demarchage!=='ecarte'&&p.contact_email&&String(p.contact_email).includes('@'));
    if(!m.checks)m.checks={};
    box.appendChild(h('div',{className:'expe-devis-modal-head'},
      h('span',{style:{fontWeight:'700',fontSize:'15px'}},'Envoyer les demandes de tarif'),closeBtn));
    box.appendChild(h('p',{style:{fontSize:'12px',color:'var(--muted)',margin:'0 0 12px'}},
      'Reply-To : votre email · copie ',
      h('strong',null,'expeditions@sifa.pro')
    ));
    const list=h('div',{className:'expe-devis-envoi-list'});
    trps.forEach(t=>{
      const key='t'+t.id;
      if(m.checks[key]==null)m.checks[key]={checked:true,kind:'actif',id:t.id};
      const cb=h('input',{type:'checkbox'});
      cb.checked=!!m.checks[key].checked;
      cb.addEventListener('change',e=>{m.checks[key].checked=e.target.checked;});
      list.appendChild(h('label',{className:'expe-devis-envoi-row'},
        cb,
        h('span',{style:{fontWeight:'600',fontSize:'13px'}},escHtml(t.nom)),
        h('span',{style:{fontSize:'12px',color:'var(--muted)'}},escHtml(t.contact_email))
      ));
    });
    if(prospects.length){
      list.appendChild(h('div',{className:'expe-devis-envoi-sep'},'Prospects'));
      prospects.forEach(p=>{
        const key='p'+p.id;
        if(m.checks[key]==null)m.checks[key]={checked:false,kind:'prospect',nom:p.nom,email:p.contact_email};
        const cb=h('input',{type:'checkbox'});
        cb.checked=!!m.checks[key].checked;
        cb.addEventListener('change',e=>{m.checks[key].checked=e.target.checked;});
        list.appendChild(h('label',{className:'expe-devis-envoi-row'},
          cb,
          h('span',{style:{fontWeight:'600',fontSize:'13px'}},escHtml(p.nom)),
          h('span',{style:{fontSize:'12px',color:'var(--muted)'}},escHtml(p.contact_email)),
          h('span',{style:{fontSize:'11px',color:'var(--warn)'}},'prospect')
        ));
      });
    }
    box.appendChild(list);
    box.appendChild(h('div',{className:'expe-devis-modal-foot'},
      h('button',{type:'button',className:'btn btn-ghost',onClick:fermerExpeDevisModal},'Annuler'),
      h('button',{type:'button',className:'btn btn-accent',onClick:()=>void confirmerEnvoi(m.demandeId)},'Envoyer')
    ));
  }else if(m.type==='saisie'){
    const f=m.form||{};
    box.appendChild(h('div',{className:'expe-devis-modal-head'},
      h('span',{style:{fontWeight:'700',fontSize:'15px'}},'Saisir la réponse reçue'),closeBtn));
    const prix=h('input',{type:'number',step:'0.01',className:'expe-devis-inp',value:f.prix});
    prix.addEventListener('input',e=>{f.prix=e.target.value;});
    const del=h('input',{type:'number',className:'expe-devis-inp',value:f.delai});
    del.addEventListener('input',e=>{f.delai=e.target.value;});
    const com=h('input',{type:'text',className:'expe-devis-inp',value:f.comment});
    com.addEventListener('input',e=>{f.comment=e.target.value;});
    box.appendChild(h('div',{className:'expe-devis-grid'},
      h('label',{className:'expe-devis-label'},'Prix HT (€)',prix),
      h('label',{className:'expe-devis-label'},'Délai (j. ouvrés)',del),
      h('label',{className:'expe-devis-label',style:{gridColumn:'1 / -1'}},'Commentaire',com)
    ));
    box.appendChild(h('div',{className:'expe-devis-modal-foot'},
      h('button',{type:'button',className:'btn btn-ghost',onClick:()=>void ouvrirDetailDemande(m.demandeId)},'Retour'),
      h('button',{type:'button',className:'btn btn-accent',onClick:()=>void validerSaisieReponse(m.reponseId,m.demandeId)},'Enregistrer')
    ));
  }else if(m.type==='prospect'){
    const f=m.form||{};
    const mk=(label,key,opts)=>{
      const o=opts||{};
      let el;
      if(o.select){
        el=o.select;
      }else{
        el=h('input',{type:o.type||'text',className:'expe-devis-inp',value:f[key]!=null?String(f[key]):''});
        el.addEventListener('input',e=>{f[key]=e.target.value;});
      }
      return h('label',{className:'expe-devis-label',style:o.full?{gridColumn:'1 / -1'}:null},label,el);
    };
    const statSel=h('select',{className:'expe-devis-inp'},
      ...['a_contacter','en_discussion','reference','ecarte'].map(v=>{
        const labels={a_contacter:'A contacter',en_discussion:'En discussion',reference:'Référence',ecarte:'Ecarté'};
        return h('option',{value:v,selected:(f.statut_demarchage||'a_contacter')===v},labels[v]);
      })
    );
    statSel.addEventListener('change',e=>{f.statut_demarchage=e.target.value;});
    const typeSel=h('select',{className:'expe-devis-inp'},
      h('option',{value:'messagerie',selected:(f.type_service||'messagerie')==='messagerie'},'Messagerie'),
      h('option',{value:'affretement',selected:f.type_service==='affretement'},'Affrètement'),
      h('option',{value:'les_deux',selected:f.type_service==='les_deux'},'Les deux')
    );
    typeSel.addEventListener('change',e=>{f.type_service=e.target.value;});
    box.appendChild(h('div',{className:'expe-devis-modal-head'},
      h('span',{style:{fontWeight:'700',fontSize:'15px'}},m.prospectId?'Modifier le prospect':'Nouveau prospect'),closeBtn));
    box.appendChild(h('div',{className:'expe-devis-grid'},
      mk('Nom du transporteur *','nom',{full:true}),
      mk('Statut','statut_demarchage',{select:statSel}),
      mk('Type de service','type_service',{select:typeSel}),
      mk('Email','contact_email',{type:'email'}),
      mk('Téléphone','contact_tel'),
      mk('Zone couverte','zone_couverte'),
      mk('Capacité max (pal.)','capacite_max_pal',{type:'number'}),
      mk('Notes','notes',{full:true})
    ));
    if(m.prospectId&&expeCanWrite()){
      box.appendChild(h('button',{type:'button',className:'btn-ghost',style:{color:'var(--danger)',fontSize:'12px',marginBottom:'12px'},
        onClick:()=>void supprimerProspect(m.prospectId)},'Supprimer ce prospect'));
    }
    box.appendChild(h('div',{className:'expe-devis-modal-foot'},
      h('button',{type:'button',className:'btn btn-ghost',onClick:fermerExpeDevisModal},'Annuler'),
      h('button',{type:'button',className:'btn btn-accent',onClick:()=>void sauvegarderProspect()},m.prospectId?'Enregistrer':'Créer')
    ));
  }

  overlay.appendChild(box);
  return overlay;
}

function renderExpeDevisSection(){
  const demandes=S.devis_demandes||[];
  const filtre=S.devis_filtre||'ouverte';
  const head=h('div',{className:'expe-devis-page-head'},
    expeCanWrite()?h('button',{type:'button',className:'btn btn-accent',onClick:()=>ouvrirModalNouvelleDemande(null)},iconEl('plus',14),' Nouvelle demande'):null,
    h('div',{className:'expe-devis-filtre'},
      h('button',{type:'button',className:'btn-ghost'+(filtre==='ouverte'?' active-filtre':''),onClick:()=>{S.devis_filtre='ouverte';void chargerDemandes();}},'Ouvertes'),
      h('button',{type:'button',className:'btn-ghost'+(filtre==='toutes'?' active-filtre':''),onClick:()=>{S.devis_filtre='toutes';void chargerDemandes();}},'Toutes')
    )
  );
  let list;
  if(!demandes.length){
    list=h('p',{style:{color:'var(--muted)',fontSize:'13px',margin:'24px 0'}},'Aucune demande en cours.');
  }else{
    list=h('div',{className:'expe-devis-cards'},
      ...demandes.map(d=>{
        const pills=[];
        const suivi=expeDevisSuiviTag(d);
        if(suivi)pills.push(suivi);
        if(d.statut==='cloturee')pills.push(h('span',{className:'expe-devis-pill muted'},'Clôturée'));
        const card=h('div',{className:'expe-devis-card',onClick:()=>void ouvrirDetailDemande(d.id)},
          h('div',{style:{display:'flex',justifyContent:'space-between',alignItems:'flex-start',gap:'12px'}},
            h('div',null,
              h('div',{style:{fontSize:'13px',fontWeight:'700',color:'var(--text)',marginBottom:'4px'}},
                'Demande #'+d.id+' — '+escHtml(d.code_postal_destination||'CP inconnu')+' — '+escHtml(d.type_envoi||'')),
              h('div',{style:{fontSize:'12px',color:'var(--muted)'}},
                (d.poids_total_kg?d.poids_total_kg+' kg ':'')+
                (d.nb_palette?d.nb_palette+' pal. ':'')+
                '· '+(d.created_at||'').slice(0,10)
              )
            ),
            h('div',{style:{display:'flex',gap:'6px',flexWrap:'wrap'}},...pills)
          ),
          d.contraintes?h('div',{style:{marginTop:'8px',fontSize:'12px',color:'var(--text2)'}},escHtml(d.contraintes)):null
        );
        return card;
      })
    );
  }
  return h('div',{id:'section-devis'},head,list);
}

function renderExpeProspectsSection(){
  const rows=S.prospects||[];
  const LABELS={
    a_contacter:{label:'A contacter',color:'var(--warn)'},
    en_discussion:{label:'En discussion',color:'var(--accent)'},
    reference:{label:'Référence',color:'var(--success)'},
    ecarte:{label:'Ecarté',color:'var(--muted)'}
  };
  const head=h('div',{style:{display:'flex',justifyContent:'flex-end',marginBottom:'12px'}},
    expeCanWrite()?h('button',{type:'button',className:'btn btn-accent',onClick:()=>ouvrirModalProspect(null)},'Ajouter un prospect'):null
  );
  const thead=h('tr',null,
    h('th',null,'Nom'),h('th',null,'Zone'),h('th',null,'Service'),
    h('th',null,'Capacité'),h('th',null,'Statut'),h('th',null,'Email'),h('th',null,'')
  );
  const tbody=rows.length?rows.map(p=>{
    const s=LABELS[p.statut_demarchage]||{label:p.statut_demarchage,color:'var(--muted)'};
    return h('tr',null,
      h('td',{style:{fontWeight:'600'}},escHtml(p.nom)),
      h('td',null,escHtml(p.zone_couverte||'—')),
      h('td',null,escHtml(p.type_service||'—')),
      h('td',null,p.capacite_max_pal!=null?p.capacite_max_pal+' pal.':'—'),
      h('td',null,h('span',{style:{color:s.color,fontWeight:'600',fontSize:'12px'}},escHtml(s.label))),
      h('td',{style:{fontSize:'12px',color:'var(--text2)'}},escHtml(p.contact_email||'—')),
      expeCanWrite()?h('td',null,h('button',{type:'button',className:'btn-ghost',title:'Modifier',onClick:e=>{e.stopPropagation();ouvrirModalProspect(p.id);}},iconEl('edit',14))):h('td',null,'—')
    );
  }):[h('tr',null,h('td',{colSpan:7,style:{color:'var(--muted)',fontStyle:'italic'}},'Aucun prospect.'))];
  return h('div',{id:'section-prospects'},
    head,
    h('div',{className:'expe-devis-table-wrap'},
      h('table',{className:'table-std'},h('thead',null,thead),h('tbody',null,...tbody))
    )
  );
}
"""

EXPE_DEVIS_CSS = r"""
/* ── MyExpé — devis & prospects ── */
.expe-devis-modal-overlay{position:fixed;inset:0;background:color-mix(in srgb,var(--bg) 60%,transparent);z-index:12100;
  display:flex;align-items:center;justify-content:center;padding:16px}
.expe-devis-modal{width:100%;max-width:720px;max-height:min(92vh,900px);overflow:auto;background:var(--card);
  border:1px solid var(--border);border-radius:12px;padding:18px}
.expe-devis-modal-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;gap:12px}
.expe-devis-close{padding:6px 8px}
.expe-devis-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:16px}
@media(max-width:520px){.expe-devis-grid{grid-template-columns:1fr}}
.expe-devis-label{display:flex;flex-direction:column;gap:6px;font-size:12px;font-weight:600;text-transform:uppercase;
  letter-spacing:.5px;color:var(--text2)}
.expe-devis-inp{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 16px;
  color:var(--text);font-size:14px;font-family:inherit;outline:none;width:100%}
.expe-devis-inp:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 12%,transparent)}
.expe-devis-modal-foot{display:flex;justify-content:flex-end;gap:8px;margin-top:16px;padding-top:14px;border-top:1px solid var(--border)}
.expe-devis-page-head{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;margin-bottom:16px}
.expe-devis-filtre{display:flex;gap:6px}
.expe-devis-filtre .active-filtre{background:var(--accent-bg);color:var(--accent);border-color:var(--accent)}
.expe-devis-cards{display:flex;flex-direction:column;gap:8px}
.expe-devis-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 20px;cursor:pointer;
  transition:border-color .15s}
.expe-devis-card:hover{border-color:var(--accent)}
.expe-devis-pill{font-size:11px;font-weight:700;padding:3px 10px;border-radius:20px;white-space:nowrap}
.expe-devis-pill.accent{background:var(--accent-bg);color:var(--accent)}
.expe-devis-pill.muted{background:color-mix(in srgb,var(--muted) 12%,transparent);color:var(--muted)}
.expe-devis-pill.ok{background:color-mix(in srgb,var(--success) 15%,transparent);color:var(--success)}
.expe-devis-table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:10px}
.expe-devis-table-wrap table.table-std{margin:0;font-size:13px}
.expe-devis-envoi-list{max-height:320px;overflow-y:auto;margin-bottom:12px}
.expe-devis-envoi-row{display:flex;align-items:center;gap:10px;padding:8px 0;border-bottom:1px solid var(--border);cursor:pointer;font-size:13px}
.expe-devis-envoi-sep{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);margin:12px 0 4px}
"""

EXPE_CARTE_FRANCE_CSS = r"""
/* ── MyExpé — carte France délais (widget dock, style calculette) ── */
.expe-carte-fab-icon{width:22px;height:22px;flex-shrink:0;background-color:var(--bg);
  mask:url(/static/expe_france_fab_icon.png) center/contain no-repeat;
  -webkit-mask:url(/static/expe_france_fab_icon.png) center/contain no-repeat}
.expe-carte-panel{width:min(920px,calc(100vw - 48px));max-height:min(720px,calc(100dvh - 100px))}
.expe-carte-panel-body{flex:1;min-height:0;overflow:auto;display:flex;flex-direction:column;gap:12px;padding:12px 14px 14px}
.expe-carte-toolbar-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap;flex-shrink:0}
.expe-carte-head{display:flex;align-items:center;gap:12px;flex-wrap:wrap;flex-shrink:0}
.expe-carte-search{flex:1;min-width:200px;max-width:360px;padding:12px 16px;background:var(--bg);border:1px solid var(--border);
  border-radius:10px;color:var(--text);font-size:14px;font-family:inherit;outline:none}
.expe-carte-search:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 12%,transparent)}
.expe-carte-body{flex:1;overflow:auto;padding:14px 18px 18px;display:grid;grid-template-columns:1fr minmax(200px,260px);gap:18px;align-items:start}
@media(max-width:900px){.expe-carte-body{grid-template-columns:1fr}}
.expe-carte-map-col{min-width:0}
.expe-carte-svg-wrap{width:100%;min-height:400px;max-height:700px;overflow:hidden;display:flex;align-items:center;justify-content:center;
  background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:8px}
.expe-carte-svg{width:100%;height:auto;max-height:680px;display:block}
.expe-carte-svg path,.expe-carte-svg rect[id]{cursor:pointer;stroke:var(--border);stroke-width:1.2;transition:fill .15s,stroke .15s,filter .15s}
.expe-carte-svg path:hover,.expe-carte-svg rect[id]:hover{filter:brightness(1.08)}
.expe-carte-dept--highlight{stroke:var(--accent)!important;stroke-width:2.5!important;filter:drop-shadow(0 0 6px color-mix(in srgb,var(--accent) 45%,transparent))}
.expe-carte-dept--selected{stroke:var(--text)!important;stroke-width:2!important}
.expe-carte-legend{display:flex;flex-direction:column;gap:10px;font-size:12px;color:var(--text2)}
.expe-carte-legend-title{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px}
.expe-carte-legend-item{display:flex;align-items:center;gap:10px}
.expe-carte-swatch{width:14px;height:14px;border-radius:4px;flex-shrink:0;border:1px solid var(--border)}
.expe-carte-hint{font-size:11px;color:var(--muted);line-height:1.5;margin-top:4px}
.expe-carte-toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.expe-carte-edit-bar{margin-top:12px;padding:12px;background:var(--bg);border:1px solid var(--border);border-radius:10px;display:none;gap:10px;flex-wrap:wrap;align-items:flex-end}
.expe-carte-edit-bar.open{display:flex}
.expe-carte-edit-bar label{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;display:block;margin-bottom:4px}
.expe-carte-edit-bar input,.expe-carte-edit-bar select{padding:10px 12px;background:var(--card);border:1px solid var(--border);border-radius:10px;color:var(--text);font-size:13px;font-family:inherit}
.expe-carte-tooltip{position:fixed;z-index:13000;pointer-events:none;padding:8px 12px;background:var(--card);border:1px solid var(--border);
  border-radius:10px;font-size:12px;color:var(--text);box-shadow:0 8px 24px color-mix(in srgb,var(--bg) 50%,transparent);max-width:280px;line-height:1.45}
.expe-carte-msg{font-size:12px;color:var(--warn);min-height:18px;margin-top:6px}
@media(max-width:900px){
  .expe-carte-panel{width:auto;max-height:none}
  .expe-carte-svg-wrap{min-height:280px;max-height:420px}
}
"""

EXPE_CARTE_FRANCE_JS = (
    r"""
// ── MyExpé — carte France (état C) ───────────────────────────────
const DELAIS_FRANCE_DEFAULT = """
    + DELAIS_FRANCE_JSON
    + r""";
const EXPE_FRANCE_SVG_MARKUP = """
    + json.dumps(EXPE_FRANCE_SVG_MARKUP)
    + r""";
const EXPE_ZONE_COLORS = {
  france: 'var(--accent)',
  france_hors_paris: 'var(--warn)',
  affretement: '#a78bfa',
  messagerie: 'var(--success)'
};
const EXPE_ZONE_LABELS = {
  france: 'France',
  france_hors_paris: 'France hors Paris',
  affretement: 'Affrètement (> 6 pal.)',
  messagerie: 'Messagerie / Ramasse (< 6 pal.)'
};

const C = {
  panelOpen: false,
  search: '',
  editMode: false,
  editDept: null,
  highlighted: null,
  selected: null,
  msg: ''
};

let DELAIS_FRANCE = {};

function expeCanEditDelais(){
  return expeCanWrite()&&((S.user&&S.user.role)==='superadmin'||(S.user&&S.user.role)==='direction');
}

async function expeLoadDelaisFromAPI(typeEnvoi){
  typeEnvoi=typeEnvoi||'default';
  try{
    const data=await api('/api/expe/delais?type_envoi='+encodeURIComponent(typeEnvoi));
    DELAIS_FRANCE=Object.assign({},JSON.parse(JSON.stringify(DELAIS_FRANCE_DEFAULT)),data||{});
  }catch(e){
    console.warn('[expe] Impossible de charger les délais depuis l\'API, utilisation des défauts.',e);
    DELAIS_FRANCE=JSON.parse(JSON.stringify(DELAIS_FRANCE_DEFAULT));
  }
}

async function expeResetDelais(){
  if(!confirm('Réinitialiser tous les délais aux valeurs par défaut ? Cette action s\'applique à tous les utilisateurs.'))return;
  try{
    await api('/api/expe/delais/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({type_envoi:'default'})});
    await expeLoadDelaisFromAPI();
    applyDelaisToMap();
    showToast('Délais réinitialisés.','success');
    refreshExpeCartePanel();
  }catch(e){
    showToast(e.message||'Erreur lors de la réinitialisation','danger');
  }
}

function getDeptData(num){
  const k=String(num||'').trim();
  return DELAIS_FRANCE[k]||null;
}

function expeNorm(s){
  try{return (s||'').toLowerCase().normalize('NFD').replace(/\p{M}/gu,'').trim();}
  catch(e){return (s||'').toLowerCase().trim();}
}

function expeZoneFill(zone){
  return EXPE_ZONE_COLORS[zone]||EXPE_ZONE_COLORS.france;
}

function applyDelaisToMap(){
  const host=document.getElementById('expe-carte-svg-host');
  if(!host)return;
  host.querySelectorAll('path[id], rect[id][data-dept]').forEach(el=>{
    const id=el.getAttribute('data-dept')||el.id;
    const d=getDeptData(id);
    if(!d)return;
    el.setAttribute('fill',expeZoneFill(d.zone));
    el.setAttribute('stroke','var(--border)');
    el.setAttribute('stroke-width','1.2');
  });
}

function showTooltipDept(numDept,x,y){
  let tip=document.getElementById('expe-carte-tooltip');
  if(!tip){
    tip=document.createElement('div');
    tip.id='expe-carte-tooltip';
    tip.className='expe-carte-tooltip';
    document.body.appendChild(tip);
  }
  const d=getDeptData(numDept);
  if(!d){tip.style.display='none';return;}
  tip.innerHTML=escHtml(numDept)+' — '+escHtml(d.label)+'<br><span style="color:var(--text2)">Délai : </span><strong>'+escHtml(d.delai)+'</strong>';
  tip.style.display='block';
  const pad=14;
  let left=(x||0)+pad;
  let top=(y||0)+pad;
  const rect=tip.getBoundingClientRect();
  if(left+rect.width>window.innerWidth-8)left=window.innerWidth-rect.width-8;
  if(top+rect.height>window.innerHeight-8)top=(y||0)-rect.height-pad;
  tip.style.left=left+'px';
  tip.style.top=top+'px';
}

function hideTooltipDept(){
  const tip=document.getElementById('expe-carte-tooltip');
  if(tip)tip.style.display='none';
}

function highlightDept(numDept){
  const host=document.getElementById('expe-carte-svg-host');
  if(!host)return;
  C.highlighted=numDept;
  host.querySelectorAll('.expe-carte-dept--highlight').forEach(el=>el.classList.remove('expe-carte-dept--highlight'));
  const id=String(numDept);
  let el=host.querySelector('[id="'+id+'"]');
  if(!el)el=host.querySelector('[data-dept="'+id+'"]');
  if(el){
    el.classList.add('expe-carte-dept--highlight');
    try{el.scrollIntoView({block:'nearest',inline:'nearest',behavior:'smooth'});}catch(e){}
    const r=el.getBoundingClientRect();
    showTooltipDept(id,r.left+r.width/2,r.top);
  }
}

function setExpeCarteOpen(open){
  C.panelOpen=!!open;
  const panel=document.getElementById('expe-carte-panel');
  const fab=document.getElementById('expe-carte-fab');
  if(panel)panel.style.display=open?'flex':'none';
  if(fab)fab.classList.toggle('expe-carte-fab-active',open);
  if(open){
    refreshExpeCartePanel();
    queueMicrotask(()=>void initCarteExpe());
  }else{
    C.editMode=false;
    hideTooltipDept();
  }
  if(window.MySifaDock&&typeof window.MySifaDock.layout==='function')window.MySifaDock.layout();
}
window.setExpeCarteOpen=setExpeCarteOpen;

function bindMapEvents(host){
  const onEnter=(el,e)=>{
    const id=el.getAttribute('data-dept')||el.id;
    showTooltipDept(id,e.clientX,e.clientY);
  };
  const onMove=(el,e)=>{
    const id=el.getAttribute('data-dept')||el.id;
    showTooltipDept(id,e.clientX,e.clientY);
  };
  host.querySelectorAll('path[id], rect[id][data-dept]').forEach(el=>{
    el.addEventListener('mouseenter',e=>onEnter(el,e));
    el.addEventListener('mousemove',e=>onMove(el,e));
    el.addEventListener('mouseleave',()=>{if(C.highlighted!==(el.getAttribute('data-dept')||el.id))hideTooltipDept();});
    el.addEventListener('click',e=>{
      e.stopPropagation();
      const id=el.getAttribute('data-dept')||el.id;
      C.selected=id;
      if(C.editMode&&expeCanEditDelais()){
        C.editDept=id;
        highlightDept(id);
        refreshExpeCartePanel();
        queueMicrotask(()=>initCarteExpe());
        return;
      }
      highlightDept(id);
    });
  });
}

async function initCarteExpe(){
  const host=document.getElementById('expe-carte-svg-host');
  if(!host||!C.panelOpen)return;
  if(!host.querySelector('svg.expe-carte-svg')){
    host.innerHTML=EXPE_FRANCE_SVG_MARKUP;
    bindMapEvents(host);
  }
  await expeLoadDelaisFromAPI();
  applyDelaisToMap();
  if(C.highlighted)highlightDept(C.highlighted);
}

async function searchDept(query){
  const q=(query||'').trim();
  C.msg='';
  if(!q){C.highlighted=null;hideTooltipDept();applyDelaisToMap();refreshExpeCartePanel();return;}
  const norm=expeNorm(q);
  const qu=q.toUpperCase();
  if(DELAIS_FRANCE[qu]){C.msg='';highlightDept(qu);refreshExpeCartePanel();return;}
  if(DELAIS_FRANCE[q]){C.msg='';highlightDept(q);refreshExpeCartePanel();return;}
  const key=Object.keys(DELAIS_FRANCE).find(k=>k.toUpperCase()===qu);
  if(key){C.msg='';highlightDept(key);refreshExpeCartePanel();return;}
  for(const [k,v] of Object.entries(DELAIS_FRANCE)){
    if(expeNorm(v.label).includes(norm)||expeNorm(k)===norm){
      C.msg='';
      highlightDept(k);
      refreshExpeCartePanel();
      return;
    }
  }
  try{
    const url='https://geo.api.gouv.fr/communes?nom='+encodeURIComponent(q)+'&fields=departement&limit=5';
    const res=await fetch(url);
    if(!res.ok)throw new Error('API indisponible');
    const data=await res.json();
    if(Array.isArray(data)&&data.length){
      const dep=(data[0].departement&&data[0].departement.code)||(data[0].codeDepartement)||'';
      if(dep&&DELAIS_FRANCE[dep]){highlightDept(dep);return;}
    }
  }catch(e){}
  C.msg='Département introuvable — vérifier le numéro ou le nom';
  showToast(C.msg,'danger');
  refreshExpeCartePanel();
}

async function saveEditDelais(){
  if(!C.editDept||!expeCanEditDelais())return;
  const delInp=document.getElementById('expe-carte-edit-delai');
  const zoneSel=document.getElementById('expe-carte-edit-zone');
  const delai=(delInp&&delInp.value||'').trim();
  const zone=zoneSel&&zoneSel.value;
  if(!delai){showToast('Délai obligatoire','danger');return;}
  if(!DELAIS_FRANCE[C.editDept]){
    DELAIS_FRANCE[C.editDept]={label:C.editDept,zone:'france',delai:'J+2'};
  }
  DELAIS_FRANCE[C.editDept].delai=delai;
  DELAIS_FRANCE[C.editDept].zone=zone||DELAIS_FRANCE[C.editDept].zone;
  applyDelaisToMap();
  highlightDept(C.editDept);
  try{
    await api('/api/expe/delais',{
      method:'PUT',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        overrides:{[C.editDept]:{delai:delai,zone:DELAIS_FRANCE[C.editDept].zone}},
        type_envoi:'default'
      })
    });
    showToast('Délai enregistré.','success');
  }catch(e){
    showToast(e.message||'Erreur — délai non sauvegardé','danger');
    await expeLoadDelaisFromAPI();
    applyDelaisToMap();
    if(C.highlighted)highlightDept(C.highlighted);
  }
}

function renderExpeCarteLegend(){
  const zones=['france','france_hors_paris','affretement','messagerie'];
  const samples={};
  zones.forEach(z=>{
    const found=Object.values(DELAIS_FRANCE).find(d=>d.zone===z);
    samples[z]=found?found.delai:'J+2';
  });
  return h('div',{className:'expe-carte-legend'},
    h('div',{className:'expe-carte-legend-title'},'Légende'),
    ...zones.map(z=>h('div',{className:'expe-carte-legend-item'},
      h('span',{className:'expe-carte-swatch',style:{background:expeZoneFill(z)}}),
      h('span',null,EXPE_ZONE_LABELS[z]+' — '+samples[z])
    )),
    h('div',{className:'expe-carte-hint'},'Départs depuis Roubaix (59 — Nord). Survolez un département pour voir les délais.')
  );
}

function refreshExpeCartePanel(){
  const body=document.getElementById('expe-carte-panel-body');
  if(!body||!C.panelOpen)return;
  const ae=document.activeElement;
  const focusId=ae&&ae.id;
  const caretStart=ae&&ae.selectionStart;
  const caretEnd=ae&&ae.selectionEnd;
  const hadSvg=!!document.getElementById('expe-carte-svg-host')?.querySelector('svg.expe-carte-svg');
  const canEdit=expeCanEditDelais();
  const search=h('input',{
    id:'expe-carte-search',
    type:'search',
    className:'expe-carte-search',
    placeholder:'Département (59) ou ville (Lille, Nord…)',
    value:C.search||'',
    onInput:e=>{C.search=e.target.value;},
    onKeydown:e=>{if(e.key==='Enter'){e.preventDefault();void searchDept(C.search);}if(e.key==='Escape'){e.preventDefault();C.search='';C.msg='';C.highlighted=null;hideTooltipDept();applyDelaisToMap();refreshExpeCartePanel();}}
  });
  const toolbar=h('div',{className:'expe-carte-toolbar'},
    h('button',{type:'button',className:'btn btn-ghost',onClick:()=>void searchDept(C.search)},iconEl('search',14),' Rechercher'),
    canEdit?h('button',{type:'button',className:'btn btn-ghost'+(C.editMode?' is-active':''),style:C.editMode?{borderColor:'var(--accent)',color:'var(--accent)'}:null,
      onClick:()=>{C.editMode=!C.editMode;C.editDept=null;refreshExpeCartePanel();queueMicrotask(()=>initCarteExpe());}},iconEl('edit',14),' Modifier les délais'):null,
    canEdit?h('button',{type:'button',className:'btn btn-ghost',onClick:()=>void expeResetDelais()},'Réinitialiser'):null
  );
  const mapHost=h('div',{id:'expe-carte-svg-host',className:'expe-carte-svg-wrap'});
  const msgEl=h('div',{className:'expe-carte-msg'},C.msg||'');
  const editBar=h('div',{className:'expe-carte-edit-bar'+(C.editDept&&C.editMode?' open':'')});
  if(C.editDept&&C.editMode){
    const d=getDeptData(C.editDept)||{label:C.editDept,delai:'J+2',zone:'france'};
    const delInp=h('input',{id:'expe-carte-edit-delai',type:'text',value:d.delai});
    const zoneSel=h('select',{id:'expe-carte-edit-zone'},
      ...Object.keys(EXPE_ZONE_LABELS).map(z=>h('option',{value:z,selected:d.zone===z},EXPE_ZONE_LABELS[z]))
    );
    editBar.appendChild(h('div',null,h('label',null,'Département'),h('div',{style:{fontSize:'13px',fontWeight:'700',color:'var(--text)'}},escHtml(C.editDept)+' — '+escHtml(d.label))));
    editBar.appendChild(h('div',null,h('label',null,'Délai'),delInp));
    editBar.appendChild(h('div',null,h('label',null,'Zone'),zoneSel));
    editBar.appendChild(h('button',{type:'button',className:'btn btn-accent',style:{alignSelf:'flex-end'},onClick:()=>void saveEditDelais()},'Enregistrer'));
  }
  const inner=h('div',null,
    h('div',{className:'expe-carte-toolbar-row'},search,toolbar),
    h('div',{className:'expe-carte-body'},
      h('div',{className:'expe-carte-map-col'},mapHost,msgEl,editBar),
      renderExpeCarteLegend()
    )
  );
  body.replaceChildren(inner);
  if(focusId){
    const el=document.getElementById(focusId);
    if(el){
      el.focus();
      if(caretStart!=null){try{el.setSelectionRange(caretStart,caretEnd);}catch(e){}}
    }
  }
  if(!hadSvg)queueMicrotask(()=>void initCarteExpe());
  else{void expeLoadDelaisFromAPI().then(()=>{applyDelaisToMap();if(C.highlighted)highlightDept(C.highlighted);});}
}
"""
)

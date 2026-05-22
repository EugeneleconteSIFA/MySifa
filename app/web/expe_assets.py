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
  uploadDrag:false
};

const EXPE_TRP_META={
  'Coupé':{poids:true,palette:true,palMax:5},
  'Ceva':{poids:true,palette:true,palMax:4},
  'Coquelle':{palette:true,palMax:33},
  'Dimotrans':{palette:true,palMax:28}
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

function expeTrpServiceBadges(nom){
  const m=EXPE_TRP_META[nom];
  if(!m)return [];
  const out=[];
  if(m.poids)out.push('Poids');
  if(m.palette)out.push('Palette');
  if(m.palMax)out.push('Max '+m.palMax+' pal.');
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
  T.modalOpen=true;
  render();
}

function closeTransporteurModal(){
  T.modalOpen=false;
  T.editId=null;
  T.tarifFile=null;
  render();
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
    const services=expeTrpServiceBadges(tr.nom||'');
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
      h('div',{className:'expe-trp-sec-title'},'Tarifs')
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
      h('div',{className:'expe-trp-sec-title'},'Tarifs'),
      h('p',{className:'expe-trp-drop-hint'},'Après création, ouvrez la fiche pour déposer un fichier tarif.')
    ));
  }
  box.appendChild(h('div',{className:'expe-trp-modal-actions'},
    h('button',{type:'button',className:'btn btn-ghost',onClick:closeTransporteurModal},'Annuler'),
    h('button',{type:'button',className:'btn btn-accent',disabled:!!T.saving,onClick:()=>saveTransporteur()},
      T.saving?'Enregistrement…':'Enregistrer')
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
const EXPE_LS_DELAIS_KEY = 'mysifa_expe_delais_v2';
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

function expeLoadDelaisOverrides(){
  try{
    const raw=localStorage.getItem(EXPE_LS_DELAIS_KEY);
    return raw?JSON.parse(raw):{};
  }catch(e){return {};}
}

function expeSaveDelaisOverrides(ov){
  try{localStorage.setItem(EXPE_LS_DELAIS_KEY,JSON.stringify(ov||{}));}catch(e){}
}

function expeMergeDelais(){
  const base=JSON.parse(JSON.stringify(DELAIS_FRANCE_DEFAULT));
  const ov=expeLoadDelaisOverrides();
  Object.keys(ov).forEach(k=>{
    if(!base[k])base[k]={label:k,zone:'france',delai:'J+2'};
    if(ov[k].delai!=null)base[k].delai=ov[k].delai;
    if(ov[k].zone)base[k].zone=ov[k].zone;
    if(ov[k].label)base[k].label=ov[k].label;
  });
  DELAIS_FRANCE=base;
}

function expeResetDelais(){
  if(!confirm('Réinitialiser tous les délais aux valeurs par défaut ?'))return;
  try{localStorage.removeItem(EXPE_LS_DELAIS_KEY);}catch(e){}
  expeMergeDelais();
  applyDelaisToMap();
  showToast('Délais réinitialisés.','success');
  refreshExpeCartePanel();
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
    expeMergeDelais();
    refreshExpeCartePanel();
    queueMicrotask(()=>initCarteExpe());
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

function initCarteExpe(){
  const host=document.getElementById('expe-carte-svg-host');
  if(!host||!C.panelOpen)return;
  if(!host.querySelector('svg.expe-carte-svg')){
    host.innerHTML=EXPE_FRANCE_SVG_MARKUP;
    bindMapEvents(host);
  }
  expeMergeDelais();
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

function saveEditDelais(){
  if(!C.editDept||!expeCanEditDelais())return;
  const delInp=document.getElementById('expe-carte-edit-delai');
  const zoneSel=document.getElementById('expe-carte-edit-zone');
  const delai=(delInp&&delInp.value||'').trim();
  const zone=zoneSel&&zoneSel.value;
  if(!delai){showToast('Délai obligatoire','danger');return;}
  const ov=expeLoadDelaisOverrides();
  ov[C.editDept]={delai:delai,zone:zone||DELAIS_FRANCE[C.editDept].zone};
  expeSaveDelaisOverrides(ov);
  expeMergeDelais();
  applyDelaisToMap();
  highlightDept(C.editDept);
  showToast('Délai enregistré.','success');
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
    canEdit?h('button',{type:'button',className:'btn btn-ghost',onClick:expeResetDelais},'Réinitialiser'):null
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
    editBar.appendChild(h('button',{type:'button',className:'btn btn-accent',style:{alignSelf:'flex-end'},onClick:saveEditDelais},'Enregistrer'));
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
  if(!hadSvg)queueMicrotask(()=>initCarteExpe());
  else{expeMergeDelais();applyDelaisToMap();if(C.highlighted)highlightDept(C.highlighted);}
}
"""
)

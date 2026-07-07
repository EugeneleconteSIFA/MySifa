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
.expe-trp-contact-col{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--text2);
  line-height:1.4;min-width:200px;max-width:280px}
.expe-trp-contact-line{display:flex;align-items:center;gap:6px;min-width:0;color:var(--text2);
  text-decoration:none}
.expe-trp-contact-line svg{flex-shrink:0;color:var(--muted)}
.expe-trp-contact-line .lbl{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
  color:inherit}
.expe-trp-contact-line.tel-link{color:var(--text2)}
.expe-trp-contact-line.tel-link:hover{color:var(--accent)}
.expe-trp-contact-line.tel-link:hover svg{color:var(--accent)}
.expe-trp-contact-line .lbl.tel{font-variant-numeric:tabular-nums;font-family:ui-monospace,SFMono-Regular,monospace;
  font-size:11.5px;color:var(--text)}
.expe-trp-contact-line a.lbl{color:var(--accent);font-weight:600}
.expe-trp-contact-line a.lbl:hover{text-decoration:underline}
.expe-trp-contact-email-row{align-items:center}
.expe-trp-emails-badge{flex-shrink:0;font-size:10px;font-weight:700;padding:1px 6px;border-radius:5px;
  background:var(--accent-bg);color:var(--accent);border:1px solid color-mix(in srgb,var(--accent) 28%,transparent);
  letter-spacing:.2px}
.expe-trp-portail-chip{display:inline-flex;align-items:center;gap:5px;padding:3px 8px;border-radius:6px;
  background:color-mix(in srgb,var(--accent) 14%,transparent);
  border:1px solid color-mix(in srgb,var(--accent) 38%,transparent);
  color:var(--accent);font-size:11px;font-weight:700;text-decoration:none;letter-spacing:.2px;
  max-width:100%;overflow:hidden}
.expe-trp-portail-chip:hover{background:color-mix(in srgb,var(--accent) 22%,transparent);text-decoration:none}
.expe-trp-portail-chip svg{flex-shrink:0}
.expe-trp-portail-chip .lbl{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.expe-trp-contact-acts{display:flex;gap:4px;margin-top:2px;flex-wrap:wrap}
.expe-trp-act{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;
  border:1px solid var(--border);background:var(--card);color:var(--muted);border-radius:6px;
  cursor:pointer;padding:0;text-decoration:none;transition:border-color .12s,color .12s,background .12s}
.expe-trp-act:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg);text-decoration:none}
.expe-trp-act svg{display:block}
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

/* ── Portail séparé + multi-emails (modal transporteur) ── */
.expe-trp-portail-inp-wrap{display:flex;gap:8px;align-items:stretch;width:100%}
.expe-trp-portail-inp-wrap input[type="url"]{flex:1;padding:12px 16px;background:var(--bg);border:1px solid var(--border);
  border-radius:10px;color:var(--text);font-size:14px;font-family:inherit;outline:none}
.expe-trp-portail-inp-wrap input[type="url"]:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 12%,transparent)}
.expe-trp-portail-open{display:inline-flex;align-items:center;gap:5px;padding:10px 14px !important;border:1px solid var(--border);
  border-radius:10px;background:var(--card);color:var(--text2);font-size:12px;font-weight:600;text-decoration:none;
  white-space:nowrap}
.expe-trp-portail-open:hover{border-color:var(--accent);color:var(--accent);text-decoration:none}
.expe-trp-emails-list{display:flex;flex-direction:column;gap:6px;margin-bottom:8px}
.expe-trp-email-row{display:flex;gap:6px;align-items:center}
.expe-trp-email-row input[type="email"]{flex:1;padding:12px 16px;background:var(--bg);border:1px solid var(--border);
  border-radius:10px;color:var(--text);font-size:14px;font-family:inherit;outline:none}
.expe-trp-email-row input[type="email"]:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 12%,transparent)}
.expe-trp-email-rm{flex-shrink:0;width:36px;height:36px;display:inline-flex;align-items:center;justify-content:center;
  border:1px solid var(--border);background:var(--card);color:var(--muted);border-radius:10px;cursor:pointer;
  transition:border-color .15s,color .15s}
.expe-trp-email-rm:hover{border-color:var(--danger);color:var(--danger)}
.expe-trp-email-add{font-size:12px;padding:6px 12px !important;border:1px dashed var(--border) !important;
  background:transparent !important;color:var(--text2) !important;border-radius:10px;display:inline-flex;
  align-items:center;gap:6px;cursor:pointer}
.expe-trp-email-add:hover{border-color:var(--accent) !important;color:var(--accent) !important}
/* Téléphones multiples : numéro + service */
.expe-trp-tel-svc-inline{color:var(--muted);font-size:11px;font-weight:500;margin-left:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.expe-trp-tels-list{display:flex;flex-direction:column;gap:6px;margin-bottom:8px}
.expe-trp-tel-row{display:grid;grid-template-columns:minmax(140px,1fr) minmax(140px,1.2fr) 36px;gap:6px;align-items:center}
.expe-trp-tel-row input{padding:12px 16px;background:var(--bg);border:1px solid var(--border);
  border-radius:10px;color:var(--text);font-size:14px;font-family:inherit;outline:none;min-width:0}
.expe-trp-tel-row input:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 12%,transparent)}
.expe-trp-tel-rm{flex-shrink:0;width:36px;height:36px;display:inline-flex;align-items:center;justify-content:center;
  border:1px solid var(--border);background:var(--card);color:var(--muted);border-radius:10px;cursor:pointer;
  transition:border-color .15s,color .15s}
.expe-trp-tel-rm:hover{border-color:var(--danger);color:var(--danger)}
.expe-trp-tel-add{font-size:12px;padding:6px 12px !important;border:1px dashed var(--border) !important;
  background:transparent !important;color:var(--text2) !important;border-radius:10px;display:inline-flex;
  align-items:center;gap:6px;cursor:pointer}
.expe-trp-tel-add:hover{border-color:var(--accent) !important;color:var(--accent) !important}
@media(max-width:520px){
  .expe-trp-tel-row{grid-template-columns:1fr 36px;grid-template-rows:auto auto;gap:6px}
  .expe-trp-tel-row .expe-trp-tel-svc{grid-column:1/2}
  .expe-trp-tel-rm{grid-row:1/3;grid-column:2/3;height:auto;align-self:stretch}
}
@media(max-width:640px){
  .expe-trp-panel{width:100%}
  .expe-trp-head{padding:12px 14px}
  .expe-trp-search{max-width:none;width:100%;order:3}
}

/* ── Tag coloré transporteur ── */
.expe-trp-tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 9px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
  line-height: 1.4;
}

/* Picker de couleur */
.trp-cpk-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
}
.trp-cpk-sw {
  width: 22px;
  height: 22px;
  border-radius: 5px;
  cursor: pointer;
  border: 2px solid transparent;
  transition: transform 0.1s, border-color 0.1s;
  flex-shrink: 0;
}
.trp-cpk-sw:hover { transform: scale(1.15); border-color: var(--text); }
.trp-cpk-sw.sel { border-color: var(--text); box-shadow: 0 0 0 2px var(--accent); }
.trp-cpk-none {
  background: var(--bg);
  border: 2px dashed var(--border) !important;
  position: relative;
}
.trp-cpk-none::after {
  content: '×';
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: var(--muted);
  font-weight: 700;
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

const TRP_PALETTE = [
  "#93c5fd","#c4b5fd","#6ee7b7","#fde68a","#fca5a5","#67e8f9",
  "#a5b4fc","#bbf7d0","#f0abfc","#fdba74","#99f6e4","#fef08a",
  "#bfdbfe","#ddd6fe","#a7f3d0","#fecaca","#fed7aa","#e9d5ff",
  "#3b82f6","#8b5cf6","#10b981","#f59e0b","#ef4444","#06b6d4",
  "#6366f1","#22c55e","#d946ef","#f97316","#64748b","#94a3b8",
];

function trpTag(nom, couleur) {
  const bg = couleur || 'var(--accent-bg)';
  const isHex = bg && bg.startsWith('#');
  let textColor = 'var(--text)';
  if (isHex) {
    const r = parseInt(bg.slice(1,3),16);
    const g = parseInt(bg.slice(3,5),16);
    const b = parseInt(bg.slice(5,7),16);
    const lum = (0.299*r + 0.587*g + 0.114*b) / 255;
    textColor = lum > 0.55 ? '#1e293b' : '#f1f5f9';
  }
  const el = document.createElement('span');
  el.className = 'expe-trp-tag';
  el.style.background = bg;
  el.style.color = textColor;
  el.textContent = nom || '—';
  return el;
}

function getTrpColor(transporteurId) {
  const tr = (T.list || []).find(x => Number(x.id) === Number(transporteurId));
  return tr ? (tr.couleur || '') : '';
}

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
  const emails=expeTrpReadEmails(tr);
  const portail=expeTrpReadPortail(tr);
  if(emails.length){
    const nom=(tr&&tr.nom)||'';
    const s=encodeURIComponent('Demande de tarif SIFA - '+nom);
    const b=encodeURIComponent('Bonjour,\n\nNous souhaitons obtenir un tarif pour un départ.\n\nCordialement,\nSIFA Roubaix');
    window.location.href='mailto:'+emails.join(',')+'?subject='+s+'&body='+b;
    return;
  }
  if(portail){
    window.open(portail,'_blank','noopener');
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

function expeTrpReadEmails(tr){
  if(!tr)return [];
  if(Array.isArray(tr.contact_emails))return tr.contact_emails.filter(e=>e&&String(e).includes('@'));
  if(typeof tr.contact_emails==='string'&&tr.contact_emails.trim()){
    const s=tr.contact_emails.trim();
    if(s.startsWith('[')){
      try{const arr=JSON.parse(s);return Array.isArray(arr)?arr.filter(e=>e&&String(e).includes('@')):[];}catch(e){}
    }
    return s.split(/[,;\n\r\t]+/).map(v=>v.trim()).filter(v=>v.includes('@'));
  }
  // Fallback ancien champ
  const legacy=(tr.contact_email||'').trim();
  if(legacy&&legacy.includes('@')&&!/^https?:\/\//i.test(legacy))return [legacy];
  return [];
}

function expeTrpReadPortail(tr){
  if(!tr)return '';
  const p=(tr.contact_portail_url||'').trim();
  if(p)return p;
  const legacy=(tr.contact_email||'').trim();
  if(/^https?:\/\//i.test(legacy))return legacy;
  return '';
}

// Lit la liste de téléphones [{numero, service}] depuis un transporteur.
// Supporte : Array déjà normalisé, string JSON, string séparée par , ; ou saut de ligne.
// Fallback : contact_tel legacy en single-entry.
function expeTrpReadTels(tr){
  if(!tr)return [];
  const norm=arr=>{
    const out=[];
    const seen=new Set();
    (arr||[]).forEach(item=>{
      let numero='';let service='';
      if(item&&typeof item==='object'){
        numero=String(item.numero||item.tel||'').trim();
        service=String(item.service||item.label||'').trim();
      }else{
        numero=String(item||'').trim();
      }
      if(!numero)return;
      const key=numero+'|'+service.toLowerCase();
      if(seen.has(key))return;
      seen.add(key);
      out.push({numero:numero,service:service});
    });
    return out;
  };
  if(Array.isArray(tr.contact_tels))return norm(tr.contact_tels);
  if(typeof tr.contact_tels==='string'&&tr.contact_tels.trim()){
    const s=tr.contact_tels.trim();
    if(s.startsWith('[')){
      try{const arr=JSON.parse(s);if(Array.isArray(arr))return norm(arr);}catch(e){}
    }
    return norm(s.split(/[,;\n\r\t]+/));
  }
  const legacy=(tr.contact_tel||'').trim();
  if(legacy)return norm(legacy.split(/[,;\n\r\t]+/));
  return [];
}

function openTransporteurModal(id){
  const isEdit=id!=null&&id!=='';
  if(isEdit){
    const tr=(T.list||[]).find(x=>Number(x.id)===Number(id));
    if(!tr){showToast('Transporteur introuvable','danger');return;}
    T.editId=tr.id;
    const emails=expeTrpReadEmails(tr);
    const tels=expeTrpReadTels(tr);
    T.form={
      nom:tr.nom||'',
      taxe_carburant_pct:tr.taxe_carburant_pct!=null?String(tr.taxe_carburant_pct):'0',
      contact_nom:tr.contact_nom||'',
      contact_portail_url:expeTrpReadPortail(tr),
      contact_emails:emails.length?emails:[''],
      contact_tels:tels.length?tels:[{numero:'',service:''}],
      contact_tel:tr.contact_tel||'',
      zone_france:!!Number(tr.zone_france),
      zone_france_hors_paris:!!Number(tr.zone_france_hors_paris),
      zone_affretement:!!Number(tr.zone_affretement),
      zone_messagerie:!!Number(tr.zone_messagerie),
      actif:tr.actif==null?true:!!Number(tr.actif),
      tarif_filename:tr.tarif_filename||'',
      tarif_url:tr.tarif_url||'',
      couleur:tr.couleur||''
    };
  }else{
    T.editId=null;
    T.form={
      nom:'',taxe_carburant_pct:'0',contact_nom:'',
      contact_portail_url:'',contact_emails:[''],contact_tels:[{numero:'',service:''}],contact_tel:'',
      zone_france:true,zone_france_hors_paris:false,zone_affretement:false,zone_messagerie:false,
      actif:true,tarif_filename:'',tarif_url:'',couleur:''
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

async function viderTarifsTransporteur(){
  if(T.editId==null)return;
  const nL=(T.tarifs_lignes||[]).length;
  const nF=(T.tarifs_frais||[]).length;
  if(!nL&&!nF){
    showToast('Aucun tarif importé à supprimer.','info');
    return;
  }
  const msg='Supprimer tous les tarifs importés pour ce transporteur ?\n\n'
    +(nL?nL+' ligne(s) tarifaire(s)':'')
    +(nL&&nF?' et ':'')
    +(nF?nF+' frais annexe(s)':'')
    +'\n\nLe fichier source uploadé n\'est pas supprimé.';
  if(!confirm(msg))return;
  try{
    const res=await api('/api/expe/transporteurs/'+T.editId+'/tarifs',{method:'DELETE'});
    const dl=res.deleted_lignes!=null?res.deleted_lignes:0;
    const df=res.deleted_frais!=null?res.deleted_frais:0;
    showToast('Tarifs supprimés ('+dl+' ligne(s), '+df+' frais).','success');
    await loadTarifsTransporteur(T.editId);
    render();
  }catch(e){
    showToast(e.message||'Suppression impossible','danger');
  }
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
    const hasTarifs=(T.tarifs_lignes||[]).length>0||(T.tarifs_frais||[]).length>0;
    kids.push(h('div',{className:'expe-trp-tarif-actions'},
      h('button',{type:'button',className:'btn btn-ghost',onClick:()=>csvInp.click()},'Importer CSV'),
      h('button',{type:'button',id:'btn-parser-tarif',className:'btn btn-ghost',disabled:!!T.tarifs_parsing,
        onClick:()=>void parserTarifs()},
        T.tarifs_parsing
          ?(['xlsx','xls'].includes(_tarifsFileExt())?'Analyse Excel en cours…':'Analyse IA en cours…')
          :_tarifsParserLabel()),
      h('button',{type:'button',className:'btn btn-danger',disabled:!hasTarifs,
        onClick:()=>void viderTarifsTransporteur()},'Vider les tarifs'),
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
  const emails=(T.form.contact_emails||[])
    .map(e=>(e||'').trim())
    .filter(e=>e&&e.includes('@'));
  const tels=(T.form.contact_tels||[])
    .map(t=>({numero:((t&&t.numero)||'').trim(),service:((t&&t.service)||'').trim()}))
    .filter(t=>t.numero);
  return {
    nom:(T.form.nom||'').trim(),
    taxe_carburant_pct:(T.form.taxe_carburant_pct||'').trim()||'0',
    contact_nom:(T.form.contact_nom||'').trim()||null,
    contact_portail_url:(T.form.contact_portail_url||'').trim()||null,
    contact_emails:emails,
    contact_tels:tels,
    zone_france:T.form.zone_france?1:0,
    zone_france_hors_paris:T.form.zone_france_hors_paris?1:0,
    zone_affretement:T.form.zone_affretement?1:0,
    zone_messagerie:T.form.zone_messagerie?1:0,
    couleur:T.form.couleur||null,
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

function expeFormatPhoneFR(s){
  const raw=String(s||'').trim();
  if(!raw)return '';
  const digits=raw.replace(/[^0-9+]/g,'');
  // Numéro français à 10 chiffres commençant par 0 → "06 19 76 54 32"
  if(/^0\d{9}$/.test(digits)){
    return digits.match(/.{1,2}/g).join(' ');
  }
  // Format international +33 6 19 76 54 32
  if(/^\+33\d{9}$/.test(digits)){
    const rest=digits.slice(3);
    return '+33 '+rest[0]+' '+rest.slice(1).match(/.{1,2}/g).join(' ');
  }
  return raw;
}

function expeTelHref(s){
  const digits=String(s||'').replace(/[^0-9+]/g,'');
  return digits?'tel:'+digits:null;
}

function expeTrpCopyText(text,label){
  if(!text)return;
  const done=()=>showToast((label||'Copié')+' : '+text,'success');
  try{
    if(navigator.clipboard&&navigator.clipboard.writeText){
      navigator.clipboard.writeText(text).then(done,()=>{});
      return;
    }
  }catch(e){}
  const ta=document.createElement('textarea');
  ta.value=text;ta.style.position='fixed';ta.style.opacity='0';
  document.body.appendChild(ta);ta.select();
  try{document.execCommand('copy');done();}catch(e){}
  document.body.removeChild(ta);
}

function expeTrpContactCell(tr){
  const emails=expeTrpReadEmails(tr);
  const portail=expeTrpReadPortail(tr);
  const nom=(tr.contact_nom||'').trim();
  const tels=expeTrpReadTels(tr);
  const tel=tels.length?tels[0].numero:'';
  if(!portail&&!nom&&!tel&&!emails.length)return h('span',{style:{color:'var(--muted)'}},'—');

  const cell=h('div',{className:'expe-trp-contact-col'});

  // 1. Portail en chip distinctif (toujours en haut quand présent)
  if(portail){
    const label=nom||'Portail transporteur';
    const chip=h('a',{className:'expe-trp-portail-chip',href:portail,target:'_blank',rel:'noopener',
      title:portail,onClick:e=>e.stopPropagation()},
      iconEl('external',11),h('span',{className:'lbl'},escHtml(label)));
    cell.appendChild(chip);
  }

  // 2. Nom du contact (uniquement si pas déjà affiché dans le chip portail)
  if(nom&&!portail){
    cell.appendChild(h('div',{className:'expe-trp-contact-line',title:nom},
      iconEl('user',12),h('span',{className:'lbl'},escHtml(nom))));
  }

  // 3. Téléphones formatés — 1er numéro + badge +N si plusieurs, tooltip = liste complète
  if(tels.length){
    const fmtList=tels.map(t=>{
      const f=expeFormatPhoneFR(t.numero);
      return t.service?(f+' — '+t.service):f;
    });
    const first=tels[0];
    const firstFmt=expeFormatPhoneFR(first.numero);
    const firstSvc=first.service||'';
    const more=tels.length-1;
    const tipText=fmtList.join('\n');
    const href=expeTelHref(first.numero);
    const telKids=[
      expeTrpIconPhone(12),
      h('span',{className:'lbl tel'},escHtml(firstFmt))
    ];
    if(firstSvc){
      telKids.push(h('span',{className:'expe-trp-tel-svc-inline'},' · '+escHtml(firstSvc)));
    }
    if(more>0){
      telKids.push(h('span',{className:'expe-trp-emails-badge',title:tipText},'+'+more));
    }
    if(href){
      cell.appendChild(h('a',{className:'expe-trp-contact-line tel-link',href:href,
        title:tipText,onClick:e=>e.stopPropagation()},...telKids));
    }else{
      cell.appendChild(h('div',{className:'expe-trp-contact-line',title:tipText},...telKids));
    }
  }

  // 4. Email — première adresse + badge +N (tooltip = liste complète)
  if(emails.length){
    const first=emails[0];
    const more=emails.length-1;
    const tipText=emails.join(', ');
    const row=h('div',{className:'expe-trp-contact-line expe-trp-contact-email-row',title:tipText});
    row.appendChild(iconEl('mail',12));
    row.appendChild(h('a',{className:'lbl',href:'mailto:'+encodeURIComponent(emails.join(',')),
      title:tipText,onClick:e=>e.stopPropagation()},escHtml(first)));
    if(more>0){
      row.appendChild(h('span',{className:'expe-trp-emails-badge',title:tipText},'+'+more));
    }
    cell.appendChild(row);
  }

  // 5. Mini-actions (icônes) — toujours visibles si on a tel ou emails
  const actionable=tel||emails.length;
  if(actionable){
    const acts=h('div',{className:'expe-trp-contact-acts'});
    if(emails.length){
      acts.appendChild(h('button',{type:'button',className:'expe-trp-act',title:'Écrire à '+(emails.length>1?'tous':emails[0]),
        onClick:e=>{e.stopPropagation();expeTrpOpenContact(tr);}},iconEl('mail',12)));
      acts.appendChild(h('button',{type:'button',className:'expe-trp-act',title:'Copier '+(emails.length>1?'les emails':'l’email'),
        onClick:e=>{e.stopPropagation();expeTrpCopyText(emails.join(', '),emails.length>1?'Emails copiés':'Email copié');}},
        iconEl('copy',12)));
    }
    if(tel){
      const href=expeTelHref(tel);
      if(href){
        acts.appendChild(h('a',{className:'expe-trp-act',href:href,title:'Appeler '+expeFormatPhoneFR(tel),
          onClick:e=>e.stopPropagation()},expeTrpIconPhone(12)));
      }
      const copyText=tels.map(t=>{
        const f=expeFormatPhoneFR(t.numero);
        return t.service?(f+' ('+t.service+')'):f;
      }).join(', ');
      const copyTitle=tels.length>1?'Copier les téléphones':'Copier le téléphone';
      const copyToast=tels.length>1?'Téléphones copiés':'Téléphone copié';
      acts.appendChild(h('button',{type:'button',className:'expe-trp-act',title:copyTitle,
        onClick:e=>{e.stopPropagation();expeTrpCopyText(copyText,copyToast);}},
        iconEl('copy',12)));
    }
    cell.appendChild(acts);
  }
  return cell;
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
    const curColor=tr.couleur||'';
    const nameCell=h('td',null,
      curColor?trpTag(tr.nom||'',tr.couleur):h('span',{className:'expe-trp-name'},escHtml(tr.nom||'')),
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
    const curColor=T.form.couleur||'';
    const swatches=TRP_PALETTE.map(c=>{
      const sw=document.createElement('div');
      sw.className='trp-cpk-sw'+(c===curColor?' sel':'');
      sw.style.background=c;
      sw.title=c;
      sw.addEventListener('click',()=>{
        T.form.couleur=c;
        render();
      });
      return sw;
    });
    const noColorBtn=document.createElement('div');
    noColorBtn.className='trp-cpk-sw trp-cpk-none'+(!curColor?' sel':'');
    noColorBtn.title='Aucune couleur';
    noColorBtn.addEventListener('click',()=>{
      T.form.couleur='';
      render();
    });
    const cpkGrid=document.createElement('div');
    cpkGrid.className='trp-cpk-grid';
    cpkGrid.appendChild(noColorBtn);
    swatches.forEach(sw=>cpkGrid.appendChild(sw));
    const preview=curColor
      ?trpTag(T.form.nom||'Aperçu',curColor)
      :h('span',{style:{color:'var(--muted)',fontSize:'12px'}},'Aucune couleur sélectionnée');
    const colorSec=h('div',{className:'expe-trp-field'},
      h('label',null,'Couleur du transporteur'),
      cpkGrid,
      h('div',{style:{marginTop:'8px'}},preview)
    );
    ident.appendChild(colorSec);
    // Portail (URL séparée)
    const portailVal=T.form.contact_portail_url||'';
    const portailInp=h('input',{type:'url',value:portailVal,placeholder:'https://…'});
    portailInp.addEventListener('input',e=>{T.form.contact_portail_url=e.target.value;});
    const portailRow=h('div',{className:'expe-trp-field expe-trp-portail-row'},
      h('label',null,'Portail transporteur (URL)'),
      h('div',{className:'expe-trp-portail-inp-wrap'},
        portailInp,
        portailVal?h('a',{className:'btn btn-ghost expe-trp-portail-open',href:portailVal,target:'_blank',rel:'noopener'},
          iconEl('external',14),' Ouvrir'):null
      )
    );

    // Liste d'emails dynamique
    if(!Array.isArray(T.form.contact_emails))T.form.contact_emails=[''];
    if(!T.form.contact_emails.length)T.form.contact_emails=[''];
    const emailsList=h('div',{className:'expe-trp-emails-list'});
    T.form.contact_emails.forEach((val,idx)=>{
      const inp=h('input',{type:'email',value:val||'',placeholder:'nom@domaine.fr'});
      inp.addEventListener('input',e=>{
        const arr=(T.form.contact_emails||[]).slice();
        arr[idx]=e.target.value;
        T.form.contact_emails=arr;
      });
      const removeBtn=h('button',{type:'button',className:'expe-trp-email-rm',title:'Retirer cette adresse',
        onClick:()=>{
          const arr=(T.form.contact_emails||[]).slice();
          arr.splice(idx,1);
          T.form.contact_emails=arr.length?arr:[''];
          render();
        }},iconEl('x',12));
      emailsList.appendChild(h('div',{className:'expe-trp-email-row'},inp,removeBtn));
    });
    const addEmailBtn=h('button',{type:'button',className:'btn btn-ghost expe-trp-email-add',
      onClick:()=>{
        const arr=(T.form.contact_emails||[]).slice();
        arr.push('');
        T.form.contact_emails=arr;
        render();
      }},iconEl('plus',12),' Ajouter une adresse');
    const emailsField=h('div',{className:'expe-trp-field'},
      h('label',null,'Adresses email'),
      emailsList,
      addEmailBtn
    );

    // Liste de téléphones dynamique : [{numero, service}]
    if(!Array.isArray(T.form.contact_tels)){
      // Migration legacy : si l'ancien champ contact_tel existe (string), on l'utilise
      const legacy=(T.form.contact_tel||'').trim();
      T.form.contact_tels=legacy?[{numero:legacy,service:''}]:[{numero:'',service:''}];
    }
    if(!T.form.contact_tels.length)T.form.contact_tels=[{numero:'',service:''}];
    const telsList=h('div',{className:'expe-trp-tels-list'});
    T.form.contact_tels.forEach((entry,idx)=>{
      const numVal=(entry&&entry.numero)||'';
      const svcVal=(entry&&entry.service)||'';
      const numInp=h('input',{type:'tel',value:numVal,placeholder:'06.68.69.18.03',className:'expe-trp-tel-num'});
      numInp.addEventListener('input',e=>{
        const arr=(T.form.contact_tels||[]).slice();
        const cur=Object.assign({},arr[idx]||{});
        cur.numero=e.target.value;
        arr[idx]=cur;
        T.form.contact_tels=arr;
      });
      const svcInp=h('input',{type:'text',value:svcVal,placeholder:'Service ou nom (facultatif)',className:'expe-trp-tel-svc'});
      svcInp.addEventListener('input',e=>{
        const arr=(T.form.contact_tels||[]).slice();
        const cur=Object.assign({},arr[idx]||{});
        cur.service=e.target.value;
        arr[idx]=cur;
        T.form.contact_tels=arr;
      });
      const removeTelBtn=h('button',{type:'button',className:'expe-trp-tel-rm',title:'Retirer ce numéro',
        onClick:()=>{
          const arr=(T.form.contact_tels||[]).slice();
          arr.splice(idx,1);
          T.form.contact_tels=arr.length?arr:[{numero:'',service:''}];
          render();
        }},iconEl('x',12));
      telsList.appendChild(h('div',{className:'expe-trp-tel-row'},numInp,svcInp,removeTelBtn));
    });
    const addTelBtn=h('button',{type:'button',className:'btn btn-ghost expe-trp-tel-add',
      onClick:()=>{
        const arr=(T.form.contact_tels||[]).slice();
        arr.push({numero:'',service:''});
        T.form.contact_tels=arr;
        render();
      }},iconEl('plus',12),' Ajouter un numéro');
    const telsField=h('div',{className:'expe-trp-field'},
      h('label',null,'Téléphones'),
      telsList,
      addTelBtn
    );

    const contact=h('div',{className:'expe-trp-sec'},
      h('div',{className:'expe-trp-sec-title'},'Contact'),
      mkText('Nom du contact','contact_nom'),
      portailRow,
      emailsField,
      telsField
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
.expe-cmp-title{font-size:15px;font-weight:700;color:var(--text);margin:0 0 14px}
.expe-cmp-form{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px 20px;margin-bottom:4px}
.expe-cmp-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px 12px;margin-bottom:16px}
@media(max-width:520px){.expe-cmp-grid{grid-template-columns:1fr}}
.expe-cmp-label{display:flex;flex-direction:column;gap:6px;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text2)}
.expe-cmp-inp{background:color-mix(in srgb,var(--bg) 88%,var(--card));border:1px solid var(--border);border-radius:10px;
  padding:12px 16px;color:var(--text);font-size:14px;font-family:inherit;outline:none;width:100%;
  transition:border-color .15s,box-shadow .15s,background .15s}
.expe-cmp-inp:hover{background:color-mix(in srgb,var(--bg) 72%,var(--card));border-color:color-mix(in srgb,var(--accent) 25%,var(--border))}
.expe-cmp-inp:focus{background:var(--bg);border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 12%,transparent)}
.expe-cmp-inp:is(select){cursor:pointer;appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2394a3b8' stroke-width='2'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 14px center;padding-right:40px}
body.light .expe-cmp-inp{background:var(--bg)}
body.light .expe-cmp-inp:hover{background:color-mix(in srgb,var(--bg) 94%,var(--border))}
body.light .expe-cmp-inp:focus{background:var(--card)}
.expe-cmp-form-actions{display:flex;justify-content:flex-start}
.expe-cmp-btn{background:var(--accent);color:var(--bg);border:none;border-radius:10px;padding:12px 24px;font-weight:700;font-size:14px;cursor:pointer;font-family:inherit}
.expe-cmp-btn:hover:not(:disabled){filter:brightness(1.05)}
.expe-cmp-btn:disabled{opacity:.5;cursor:not-allowed}
.expe-cmp-results{margin-top:24px}
.expe-cmp-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px;position:relative}
.expe-cmp-card.best{border-color:var(--accent)}
.expe-cmp-card-cont{margin-left:8px;border-left:2px solid var(--border);border-top-left-radius:0;border-bottom-left-radius:0}
.expe-cmp-badge{position:absolute;top:12px;right:12px;background:var(--accent);color:var(--bg);font-size:11px;font-weight:700;padding:3px 8px;border-radius:6px}
.expe-cmp-methode-badge{display:inline-block;background:var(--accent-bg);color:var(--accent);border-radius:6px;font-size:11px;font-weight:600;padding:2px 8px}
.expe-cmp-card-header{display:flex;flex-direction:column;align-items:flex-start;gap:4px;margin-bottom:8px}
.expe-cmp-card-name{font-size:15px;font-weight:700;color:var(--text);display:block}
.expe-cmp-card-price-row{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.expe-cmp-card-price{font-size:18px;font-weight:700;color:var(--text)}
.expe-cmp-card.best .expe-cmp-card-price{color:var(--accent)}
.expe-cmp-card-price-ht{font-size:12px;color:var(--muted)}
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
    const nbTrp=new Set(elig.map(e=>e.transporteur_id)).size;
    html+='<div style="margin-bottom:24px"><div style="font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text2);margin-bottom:10px">'
      +nbTrp+' transporteur'+(nbTrp>1?'s':'')+' éligible'+(nbTrp>1?'s':'')
      +'</div><div class="expe-cmp-cards">';
    elig.forEach((e,i)=>{
      const mc=!!e.moins_cher;
      const prev=i>0?elig[i-1]:null;
      const isCont=prev&&prev.transporteur_id===e.transporteur_id;
      const methode=e.methode_tarification||'';
      const cardCls='expe-cmp-card'+(mc?' best':'')+(isCont?' expe-cmp-card-cont':'');
      let header='';
      if(!isCont){
        const couleur=getTrpColor(e.transporteur_id);
        if(couleur){
          const bg=couleur;
          const r2=parseInt(bg.slice(1,3),16),g2=parseInt(bg.slice(3,5),16),b2=parseInt(bg.slice(5,7),16);
          const lum=(0.299*r2+0.587*g2+0.114*b2)/255;
          const fg=lum>0.55?'#1e293b':'#f1f5f9';
          header+='<span class="expe-trp-tag" style="background:'+escHtml(bg)+';color:'+fg+'">'+escHtml(e.transporteur)+'</span>';
        }else{
          header+='<span class="expe-cmp-card-name">'+escHtml(e.transporteur)+'</span>';
        }
      }
      if(methode){
        header+='<span class="expe-cmp-methode-badge">'+escHtml(methode)+'</span>';
      }
      html+='<div class="'+cardCls+'">'
        +(mc?'<span class="expe-cmp-badge">Moins cher</span>':'')
        +(header?'<div class="expe-cmp-card-header">'+header+'</div>':'')
        +'<div class="expe-cmp-card-price-row">'
        +'<span class="expe-cmp-card-price">'+Number(e.prix_ht).toFixed(2)+' €</span>'
        +'<span class="expe-cmp-card-price-ht">HT</span></div>'
        +'<details style="font-size:12px;color:var(--text2)"><summary style="cursor:pointer;color:var(--muted);margin-bottom:4px">Détail du calcul</summary>'
        +'<div style="margin-top:8px;padding:10px;background:var(--bg);border-radius:8px;display:flex;flex-direction:column;gap:4px">'
        +'<div>Méthode : '+escHtml(methode)+'</div>'
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
  const resetBtn=h('button',{type:'button',className:'btn-ghost',style:{marginLeft:'8px'}},'Remettre à 0');
  resetBtn.addEventListener('click',()=>{
    document.getElementById('cmp-poids').value='';
    document.getElementById('cmp-pal').value='';
    document.getElementById('cmp-cp').value='';
    document.getElementById('cmp-type').value='messagerie';
    document.getElementById('cmp-resultats').innerHTML='';
    S.comparateur_form={poids_total_kg:'',nb_palette:'',code_postal_destination:'',type_envoi:'messagerie'};
  });
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
    h('div',{className:'expe-cmp-form'},
      grid,
      h('div',{className:'expe-cmp-form-actions'},btn,resetBtn)
    ),
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
    client:d.client||'',
    poids_total_kg:d.poids_total_kg!=null?String(d.poids_total_kg):'',
    nb_palette:d.nb_palette!=null?String(d.nb_palette):'',
    code_postal_destination:d.code_postal_destination||'',
    type_envoi:(d.nb_palette||0)>=6?'affretement':(d.type_envoi||'messagerie'),
    contraintes:'',
    piece_jointe_file:null
  }}});
}

async function validerNouvelleDemande(){
  const m=S.expeDevisModal;
  if(!m||m.type!=='nouvelle')return;
  const f=m.form||{};
  const cp=(f.code_postal_destination||'').trim();
  const client=(f.client||'').trim();
  if(!client){showToast('Client obligatoire','danger');return;}
  if(!cp){showToast('Code postal destination obligatoire','danger');return;}
  try{
    const demande=await api('/api/expe/devis/demandes',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        client,
        depart_id:m.departId||null,
        poids_total_kg:parseFloat(f.poids_total_kg)||null,
        nb_palette:parseFloat(f.nb_palette)||null,
        code_postal_destination:cp,
        type_envoi:f.type_envoi||'messagerie',
        contraintes:(f.contraintes||'').trim()||null
      })
    });
    // Si un fichier a été sélectionné, on l'upload après la création.
    // Le second appel ne bloque pas la création si l'upload échoue (on prévient).
    const fileObj=f.piece_jointe_file;
    if(fileObj&&fileObj instanceof File){
      try{
        const fd=new FormData();
        fd.append('file',fileObj);
        const r=await fetch('/api/expe/devis/demandes/'+demande.id+'/piece-jointe',{
          method:'POST',
          credentials:'include',
          body:fd
        });
        if(!r.ok){
          const txt=await r.text().catch(()=>String(r.status));
          showToast('Demande créée mais pièce jointe non sauvée : '+(txt||r.status),'danger');
        }
      }catch(e){
        showToast('Demande créée mais pièce jointe non sauvée : '+(e.message||e),'danger');
      }
    }
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

async function cloturerDemande(demandeId,ev){
  if(ev&&ev.stopPropagation)ev.stopPropagation();
  if(!confirm('Clôturer cette demande ? Elle sera déplacée dans l’historique.'))return;
  try{
    await api('/api/expe/devis/demandes/'+demandeId+'/cloturer',{method:'POST'});
    showToast('Demande clôturée.','success');
    fermerExpeDevisModal();
    await chargerDemandes();
  }catch(e){
    showToast(e.message||'Erreur','danger');
  }
}

function devisRefLabel(d){
  if(!d)return '';
  return d.reference?('Demande '+d.reference):('Demande #'+d.id);
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

function expeDevisMeilleursReponses(reps){
  const list=(reps||[]).filter(r=>r.statut!=='refusee');
  const avecPrix=list.filter(r=>r.prix!=null);
  const avecDelai=list.filter(r=>r.delai_jours!=null);
  const bestPrix=avecPrix.length?Math.min(...avecPrix.map(r=>Number(r.prix))):null;
  const bestDelai=avecDelai.length?Math.min(...avecDelai.map(r=>Number(r.delai_jours))):null;
  return {bestPrix,bestDelai};
}

function expeDevisCellValeur(txt,isBest){
  return isBest?h('strong',null,txt):txt;
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
      (()=>{
        const c=h('input',{type:'text',className:'expe-devis-inp',value:f.client||'',placeholder:'Nom du client'});
        c.addEventListener('input',e=>{m.form.client=e.target.value;});
        return h('label',{className:'expe-devis-label',style:{gridColumn:'1 / -1'}},'Client *',c);
      })(),
      mk('Poids (kg)','poids_total_kg',{type:'number',step:'0.1'}),
      mk('Palettes','nb_palette',{type:'number',step:'1'}),
      mk('CP destination *','code_postal_destination'),
      h('label',{className:'expe-devis-label'},'Type d\'envoi',typeSel),
      (()=>{
        const c=h('input',{type:'text',className:'expe-devis-inp',value:f.contraintes||'',placeholder:'Délai, RDV…'});
        c.addEventListener('input',e=>{m.form.contraintes=e.target.value;});
        return h('label',{className:'expe-devis-label',style:{gridColumn:'1 / -1'}},'Contraintes',c);
      })(),
      (()=>{
        // Pièce jointe : input file natif caché, déclenché par un bouton stylé
        // cohérent avec le design system (btn btn-ghost). Max 20 Mo côté serveur.
        const fileInp=h('input',{type:'file',style:{display:'none'}});
        const btnLbl=h('span',null,m.form.piece_jointe_file?'Changer de fichier':'Sélectionner un fichier');
        const btn=h('button',{type:'button',className:'btn btn-ghost',onClick:()=>fileInp.click()},btnLbl);
        const info=h('div',{style:{fontSize:'12px',color:'var(--muted)',marginTop:'6px'}},
          m.form.piece_jointe_file?('Sélectionné : '+(m.form.piece_jointe_file.name||'')):'Optionnel — max 20 Mo'
        );
        fileInp.addEventListener('change',e=>{
          const ff=(e.target.files&&e.target.files[0])||null;
          m.form.piece_jointe_file=ff;
          btnLbl.textContent=ff?'Changer de fichier':'Sélectionner un fichier';
          info.textContent=ff?('Sélectionné : '+(ff.name||'')):'Optionnel — max 20 Mo';
        });
        return h('label',{className:'expe-devis-label',style:{gridColumn:'1 / -1'}},'Pièce jointe',
          h('div',{style:{display:'flex',flexDirection:'column',alignItems:'flex-start',gap:'2px'}},btn,info,fileInp)
        );
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
      h('span',{style:{fontWeight:'700',fontSize:'15px'}},devisRefLabel(d)+' — '+escHtml(d.code_postal_destination||'')),
      closeBtn));
    box.appendChild(h('div',{style:{fontSize:'12px',color:'var(--muted)',marginBottom:'16px'}},
      (d.client?escHtml(d.client)+' · ':'')+
      (d.poids_total_kg?d.poids_total_kg+' kg · ':'')+
      (d.nb_palette?d.nb_palette+' pal. · ':'')+
      escHtml(d.type_envoi||'')+
      (d.contraintes?' · '+escHtml(d.contraintes):'')
    ));
    // Lien vers la pièce jointe si présente
    if(d.piece_jointe_path){
      const a=h('a',{
        href:'/api/expe/devis/demandes/'+d.id+'/piece-jointe',
        target:'_blank',
        rel:'noopener',
        style:{display:'inline-flex',alignItems:'center',gap:'6px',marginBottom:'14px',fontSize:'13px',color:'var(--accent)',textDecoration:'none'}
      },'Pièce jointe : '+escHtml(d.piece_jointe_filename||'fichier'));
      box.appendChild(a);
    }
    if(d.statut==='ouverte'&&expeCanWrite()){
      box.appendChild(h('div',{style:{marginBottom:'16px',display:'flex',gap:'8px',flexWrap:'wrap'}},
        h('button',{type:'button',className:'btn btn-accent',onClick:()=>void ouvrirModalEnvoi(d.id)},'Envoyer les demandes'),
        h('button',{type:'button',className:'btn',style:{color:'var(--danger)',borderColor:'var(--danger)'},
          title:'Clôturer cette demande (déplace dans l’historique)',
          onClick:()=>void cloturerDemande(d.id)},iconEl('check-circle',12),' Clôturer')
      ));
    }
    const {bestPrix,bestDelai}=expeDevisMeilleursReponses(reps);
    const head=h('tr',null,
      h('th',null,'Transporteur'),h('th',null,'Statut'),h('th',null,'Prix HT'),
      h('th',null,'Délai'),h('th',null,'Commentaire'),h('th',null,'')
    );
    const body=reps.length?reps.map(r=>{
      const sl=expeDevisStatutLabel(r.statut);
      const acts=[];
      if(r.statut==='recue'&&expeCanWrite())acts.push(h('button',{type:'button',className:'btn-ghost',style:{fontSize:'12px',color:'var(--success)'},onClick:()=>void retenirReponse(r.id,d.id)},'Retenir'));
      if((r.statut==='envoyee'||r.statut==='echec')&&expeCanWrite())acts.push(h('button',{type:'button',className:'btn-ghost',style:{fontSize:'12px'},onClick:()=>ouvrirSaisieReponse(r.id,d.id)},'Saisir réponse'));
      const prixTxt=r.prix!=null?Number(r.prix).toFixed(2)+' €':'—';
      const delTxt=r.delai_jours!=null?'J+'+r.delai_jours:'—';
      const isBestPrix=r.prix!=null&&bestPrix!=null&&Number(r.prix)===bestPrix;
      const isBestDelai=r.delai_jours!=null&&bestDelai!=null&&Number(r.delai_jours)===bestDelai;
      return h('tr',null,
        h('td',{style:{fontWeight:'600'}},escHtml(r.nom_transporteur||'—')),
        h('td',null,h('span',{style:{color:sl.c,textDecoration:sl.strike?'line-through':'none'}},sl.t)),
        h('td',null,expeDevisCellValeur(prixTxt,isBestPrix)),
        h('td',null,expeDevisCellValeur(delTxt,isBestDelai)),
        h('td',{style:{fontSize:'12px',color:'var(--text2)'}},escHtml(r.commentaire||'')),
        h('td',null,...acts)
      );
    }):[h('tr',null,h('td',{colSpan:6,style:{color:'var(--muted)',fontStyle:'italic'}},'Aucune réponse.'))];
    box.appendChild(h('div',{className:'expe-devis-table-wrap'},
      h('table',{className:'table-std'},h('thead',null,head),h('tbody',null,...body))
    ));
  }else if(m.type==='envoi'){
    const trps=(T.list||[]).filter(t=>{
      if(!Number(t.actif))return false;
      const ems=expeTrpReadEmails(t);
      return ems.length>0;
    });
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
      const ems=expeTrpReadEmails(t);
      const emailsLabel=ems.length<=1?ems[0]:ems[0]+' (+'+(ems.length-1)+')';
      list.appendChild(h('label',{className:'expe-devis-envoi-row',title:ems.join(', ')},
        cb,
        h('span',{style:{fontWeight:'600',fontSize:'13px'}},escHtml(t.nom)),
        h('span',{style:{fontSize:'12px',color:'var(--muted)'}},escHtml(emailsLabel))
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
  const emptyMsg=filtre==='historique'
    ? 'Aucune demande clôturée.'
    : (filtre==='toutes' ? 'Aucune demande enregistrée.' : 'Aucune demande en cours.');
  const head=h('div',{className:'expe-devis-page-head'},
    expeCanWrite()?h('button',{type:'button',className:'btn btn-accent',onClick:()=>ouvrirModalNouvelleDemande(null)},iconEl('plus',14),' Nouvelle demande'):null,
    h('div',{className:'expe-devis-filtre'},
      h('button',{type:'button',className:'btn-ghost'+(filtre==='ouverte'?' active-filtre':''),onClick:()=>{S.devis_filtre='ouverte';void chargerDemandes();}},'Ouvertes'),
      h('button',{type:'button',className:'btn-ghost'+(filtre==='historique'?' active-filtre':''),onClick:()=>{S.devis_filtre='historique';void chargerDemandes();}},'Historique'),
      h('button',{type:'button',className:'btn-ghost'+(filtre==='toutes'?' active-filtre':''),onClick:()=>{S.devis_filtre='toutes';void chargerDemandes();}},'Toutes')
    )
  );
  let list;
  if(!demandes.length){
    list=h('p',{style:{color:'var(--muted)',fontSize:'13px',margin:'24px 0'}},emptyMsg);
  }else{
    list=h('div',{className:'expe-devis-cards'},
      ...demandes.map(d=>{
        const pills=[];
        const suivi=expeDevisSuiviTag(d);
        if(suivi)pills.push(suivi);
        if(d.statut==='cloturee')pills.push(h('span',{className:'expe-devis-pill muted'},'Clôturée'));
        const actions=[];
        if(d.statut==='ouverte'&&expeCanWrite()){
          actions.push(h('button',{
            type:'button',
            className:'btn-ghost',
            style:{fontSize:'12px',color:'var(--danger)',padding:'4px 8px'},
            title:'Clôturer cette demande (déplace dans l’historique)',
            onClick:e=>void cloturerDemande(d.id,e)
          },iconEl('check-circle',12),' Clôturer'));
        }
        const card=h('div',{className:'expe-devis-card',onClick:()=>void ouvrirDetailDemande(d.id)},
          h('div',{style:{display:'flex',justifyContent:'space-between',alignItems:'flex-start',gap:'12px'}},
            h('div',null,
              h('div',{style:{fontSize:'13px',fontWeight:'700',color:'var(--text)',marginBottom:'4px'}},
                devisRefLabel(d)+' — '+escHtml(d.code_postal_destination||'CP inconnu')+' — '+escHtml(d.type_envoi||'')),
              h('div',{style:{fontSize:'12px',color:'var(--muted)'}},
                (d.poids_total_kg?d.poids_total_kg+' kg ':'')+
                (d.nb_palette?d.nb_palette+' pal. ':'')+
                '· '+(d.created_at||'').slice(0,10)
              )
            ),
            h('div',{style:{display:'flex',gap:'6px',flexWrap:'wrap',alignItems:'center'}},...pills,...actions)
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
    const rowCls=p.statut_demarchage==='ecarte'?'expe-prospect-ecarte':'';
    return h('tr',{className:rowCls},
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
    h('div',{className:'expe-prospects-table-wrap'},
      h('table',{className:'table-std expe-prospects-table'},h('thead',null,thead),h('tbody',null,...tbody))
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
.expe-prospects-table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:12px;background:var(--card)}
.expe-prospects-table-wrap table.expe-prospects-table{margin:0;font-size:13px}
.expe-prospects-table-wrap .expe-prospects-table th{
  background:color-mix(in srgb,var(--bg) 50%,var(--card));
  border-bottom:1px solid var(--border);
  padding:10px 14px;
}
.expe-prospects-table-wrap .expe-prospects-table td{
  padding:10px 14px;
  border-bottom:1px solid color-mix(in srgb,var(--border) 65%,transparent);
  vertical-align:middle;
  color:var(--text);
}
.expe-prospects-table tbody tr:nth-child(even) td{
  background:color-mix(in srgb,var(--muted) 7%,transparent);
}
.expe-prospects-table tbody tr:hover td{
  background:color-mix(in srgb,var(--accent) 11%,transparent);
}
.expe-prospects-table tbody tr.expe-prospect-ecarte td{
  color:var(--text2);
  background:color-mix(in srgb,var(--muted) 5%,transparent);
}
.expe-prospects-table tbody tr.expe-prospect-ecarte:nth-child(even) td{
  background:color-mix(in srgb,var(--muted) 10%,transparent);
}
.expe-prospects-table tbody tr:last-child td{border-bottom:none}
body.light .expe-prospects-table tbody tr:nth-child(even) td{
  background:color-mix(in srgb,var(--border) 40%,var(--card));
}
body.light .expe-prospects-table tbody tr:hover td{
  background:color-mix(in srgb,var(--accent) 9%,var(--card));
}
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


EXPE_MAIN_CSS = r"""
/* ── MyExpé ─────────────────────────────────────────────────────── */
.expe-fields{display:grid;grid-template-columns:repeat(4,minmax(150px,1fr));gap:12px}
@media(max-width:1100px){.expe-fields{grid-template-columns:repeat(2,minmax(150px,1fr))}}
@media(max-width:520px){.expe-fields{grid-template-columns:1fr}}
.expe-field label{display:block;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px}
.expe-field input,.expe-field select{width:100%;padding:10px 14px;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:14px;font-family:inherit;outline:none}
.expe-field input:focus,.expe-field select:focus{border-color:var(--accent)}
.expe-help{font-size:10px;color:var(--muted);margin-top:4px}
.expe-departs-table tbody tr:nth-child(even) td{background:rgba(148,163,184,.06)}
.expe-departs-table tbody tr:hover td{background:rgba(34,211,238,.06)}
.expe-dep-actions-td{max-width:none!important;overflow:visible;text-overflow:clip;white-space:normal;vertical-align:middle}
.expe-day-sep-row td.expe-day-sep-cell {
  padding: 28px 14px 12px !important;
  background: var(--bg) !important;
  border-top: 2px solid var(--border);
}
.expe-departs-table tbody tr.expe-day-sep-row:hover td{background:var(--bg)!important}
.expe-day-sep-label {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text2);
}
.expe-dep-actions-cell{display:flex;flex-direction:row;align-items:center;justify-content:flex-end;gap:10px}
.expe-dep-acts{display:grid;grid-template-columns:repeat(3,1fr);gap:4px;flex-shrink:0}
.expe-dep-acts .btn-ghost,.expe-dep-acts .btn-danger{width:32px;height:30px;padding:0;margin:0;
  display:flex;align-items:center;justify-content:center;border-radius:6px}
.expe-dep-valider-btn{margin:0;padding:8px 12px;font-size:11px;font-weight:700;border-radius:10px;
  white-space:nowrap;flex-shrink:0}
.expe-dep-invalider-btn{margin:0;padding:8px 12px;font-size:11px;font-weight:700;border-radius:10px;
  white-space:nowrap;flex-shrink:0;background:color-mix(in srgb,var(--warn) 18%,transparent);
  border:1px solid color-mix(in srgb,var(--warn) 45%,var(--border));color:var(--warn)}
.expe-dep-invalider-btn:hover{filter:brightness(1.06)}
.expe-hist-pager{display:flex;align-items:center;justify-content:flex-end;gap:8px;flex-wrap:wrap;
  padding:12px 18px;border-top:1px solid var(--border)}
.expe-hist-pager .page-btn{padding:6px 12px;border-radius:7px;border:1px solid var(--border);
  background:transparent;color:var(--text2);cursor:pointer;font-size:12px;font-family:inherit}
.expe-hist-pager .page-btn:hover:not(:disabled){border-color:var(--accent);color:var(--accent)}
.expe-hist-pager .page-btn:disabled{opacity:.35;cursor:not-allowed}
.expe-hist-pager .page-info{font-size:12px;color:var(--muted);padding:0 4px;white-space:nowrap}
.expe-dep-ab[title],.expe-dep-valider-btn[title],.expe-dep-invalider-btn[title]{position:relative;overflow:visible}
.expe-dep-ab[title]:hover::after,.expe-dep-valider-btn[title]:hover::after,.expe-dep-invalider-btn[title]:hover::after{
  content:attr(title);position:absolute;bottom:calc(100% + 7px);left:50%;transform:translateX(-50%);
  background:var(--card);border:1px solid var(--border);border-radius:7px;
  padding:6px 10px;font-size:10px;font-weight:500;color:var(--text2);line-height:1.4;
  white-space:normal;max-width:240px;text-align:center;
  pointer-events:none;z-index:200;box-shadow:0 4px 16px color-mix(in srgb,var(--bg) 55%,transparent)}
.expe-dep-ab[title]:hover::before,.expe-dep-valider-btn[title]:hover::before,.expe-dep-invalider-btn[title]:hover::before{
  content:'';position:absolute;bottom:calc(100% + 2px);left:50%;transform:translateX(-50%);
  border:5px solid transparent;border-top-color:var(--border);pointer-events:none;z-index:200}
.expe-hist-table th{padding:6px 10px;font-size:9px}

/* MyExpé — onglets internes modal Ajouter départ */
.expe-form-tabs{display:flex;gap:4px;margin-bottom:14px;border-bottom:1px solid var(--border);padding-bottom:0}
.expe-form-tab{background:transparent;border:none;color:var(--muted);font-size:13px;font-weight:600;padding:10px 16px;cursor:pointer;border-bottom:2px solid transparent;display:inline-flex;align-items:center;gap:6px;transition:color .15s,border-color .15s}
.expe-form-tab:hover{color:var(--text2)}
.expe-form-tab.active{color:var(--accent);border-bottom-color:var(--accent)}

/* MyExpé — picker dossier */
.expe-picker-wrap{display:flex;flex-direction:column;gap:10px}
.expe-picker-hint{font-size:11px;color:var(--muted);line-height:1.5;padding:0 2px}
.expe-picker-search{width:100%;padding:10px 14px;border:1px solid var(--border);background:var(--bg);color:var(--text);border-radius:10px;font-size:13px;outline:none;transition:border-color .15s}
.expe-picker-search:focus{border-color:var(--accent)}
.expe-picker-list{max-height:420px;overflow-y:auto;border:1px solid var(--border);border-radius:10px;background:var(--bg);padding:6px}
.expe-picker-section{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;padding:8px 6px 4px}
.expe-picker-item{padding:10px 12px;margin:2px 0;border:1px solid var(--border);border-radius:8px;cursor:pointer;background:var(--card);transition:border-color .15s,background .15s}
.expe-picker-item:hover{border-color:var(--accent);background:var(--accent-bg)}
.expe-picker-item--active{border-left:3px solid var(--accent)}
.expe-picker-line1{font-size:13px;font-weight:700;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.expe-picker-ref{color:var(--accent);font-family:monospace}
.expe-picker-sep{color:var(--muted);font-weight:400}
.expe-picker-client{color:var(--text)}
.expe-picker-line2{font-size:12px;color:var(--text2);margin-top:3px}
.expe-picker-meta{font-size:10px;color:var(--muted);display:flex;gap:8px;margin-top:5px;flex-wrap:wrap;align-items:center}
.expe-picker-statut{padding:2px 8px;border-radius:10px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;font-size:9px}
.expe-picker-statut--en_cours{background:rgba(34,211,238,.18);color:var(--accent)}
.expe-picker-statut--attente{background:rgba(251,191,36,.18);color:var(--warn)}
.expe-picker-statut--termine{background:rgba(52,211,153,.18);color:var(--success,#34d399)}
.expe-picker-warn{background:rgba(248,113,113,.15);color:var(--danger);padding:2px 8px;border-radius:10px;font-weight:600;font-size:9px;text-transform:uppercase;letter-spacing:.3px}
.expe-picker-empty{padding:24px 12px;text-align:center;color:var(--muted);font-size:13px}

/* MyExpé — sidebar sections collapsibles */
.expe-sidebar-sections{display:flex;flex-direction:column;gap:2px}
.expe-sec-header{display:flex;align-items:center;gap:8px;background:transparent;border:none;
  padding:14px 16px 6px 12px;cursor:pointer;color:var(--muted);
  font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:.7px;
  width:100%;text-align:left;transition:color .15s}
.expe-sec-header:hover{color:var(--text2)}
.expe-sec-header.has-active{color:var(--text2)}
.expe-sec-header .expe-sec-chev{display:inline-flex;transition:transform .15s;flex-shrink:0;color:var(--muted)}
.expe-sec-header.collapsed .expe-sec-chev{opacity:.6}
.expe-sec-header.has-active .expe-sec-chev{color:var(--accent)}
.expe-sec-label{flex:1}
.expe-sec-body{display:flex;flex-direction:column;gap:2px;padding-bottom:4px}

/* MyExpé — Palettes Europe */
.expe-pal-eur-totaux{display:grid;grid-template-columns:repeat(4,minmax(140px,1fr));gap:12px;margin-bottom:14px}
@media(max-width:760px){.expe-pal-eur-totaux{grid-template-columns:repeat(2,1fr)}}
.expe-pal-eur-tot-card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:14px 18px}
.expe-pal-eur-tot-card--ok{border-left:3px solid var(--success,#34d399)}
.expe-pal-eur-tot-card--warn{border-left:3px solid var(--warn)}
.expe-pal-eur-tot-card--bad{border-left:3px solid var(--danger)}
.expe-pal-eur-tot-lbl{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.6px;margin-bottom:6px}
.expe-pal-eur-tot-val{font-size:24px;font-weight:800;color:var(--text);font-family:monospace}
.expe-pal-eur-recap{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px}
.expe-pal-eur-recap-card{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 14px}
.expe-pal-eur-recap-card--debt{border-left:3px solid var(--warn)}
.expe-pal-eur-recap-client{font-size:13px;font-weight:700;color:var(--text);margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.expe-pal-eur-recap-row{display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:12px}
.expe-pal-eur-recap-row--solde{margin-top:6px;padding-top:6px;border-top:1px solid var(--border);font-weight:700}
.expe-pal-eur-recap-lbl{color:var(--text2)}
.expe-pal-eur-recap-val{font-family:monospace;font-weight:600;color:var(--text)}
.expe-pal-eur-recap-val--ok{color:var(--success,#34d399)}
.expe-pal-eur-recap-val--bad{color:var(--danger)}
.expe-pal-eur-recap-val--warn{color:var(--warn)}
.expe-pal-eur-badge{padding:3px 10px;border-radius:12px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;font-size:10px;white-space:nowrap}
.expe-pal-eur-badge--en_attente{background:rgba(251,191,36,.18);color:var(--warn)}
.expe-pal-eur-badge--retournee{background:rgba(52,211,153,.18);color:var(--success,#34d399)}
.expe-pal-eur-badge--perdue{background:rgba(248,113,113,.18);color:var(--danger)}
.expe-pal-eur-acts-cell{white-space:nowrap;text-align:right}
.expe-pal-eur-acts{display:inline-flex;gap:4px;justify-content:flex-end}
.expe-pal-eur-act{width:30px;height:30px;padding:0;display:inline-flex;align-items:center;justify-content:center;
  background:transparent;border:1px solid var(--border);border-radius:7px;cursor:pointer;color:var(--text2);
  transition:border-color .15s,color .15s,background .15s}
.expe-pal-eur-act:hover{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.expe-pal-eur-act--ok:hover{border-color:var(--success,#34d399);color:var(--success,#34d399);background:rgba(52,211,153,.12)}
.expe-pal-eur-act--bad:hover{border-color:var(--danger);color:var(--danger);background:rgba(248,113,113,.12)}
.expe-hist-table td{padding:6px 10px;max-width:140px}
.expe-hist-table td:nth-child(1){max-width:110px} /* Validé le */
.expe-hist-table td:nth-child(2){max-width:120px} /* Par */
.expe-hist-table td:nth-child(4){max-width:160px} /* Client */
.expe-hist-table td:nth-child(5){max-width:160px} /* Réf SIFA */
.expe-hist-table td:nth-child(7){max-width:140px} /* Cde transp. */
.expe-hist-table td:nth-child(8){max-width:140px} /* N° BL */
.expe-hist-table td:nth-child(9){max-width:140px} /* Transp. */
.expe-top3{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;margin-bottom:18px}
.expe-score{background:var(--card);border:1px solid var(--border);border-radius:14px;overflow:hidden;position:relative}
.expe-score .stripe{height:4px}
.expe-score .body{padding:16px 20px}
.expe-score .carrier{font-size:18px;font-weight:800;letter-spacing:-.5px}
.expe-score .price{font-size:28px;font-weight:800;font-family:monospace;margin:8px 0}
.expe-score .price .unit{font-size:13px;font-weight:500;color:var(--muted);margin-left:4px}
.expe-score .medal{font-size:24px;flex-shrink:0}
.expe-note{font-size:10px;color:rgba(148,163,184,.8);margin-top:12px}

/* MyExpé — mobile : titres de page / sections déjà dans la topbar */
@media (max-width:900px){
  body.mysifa-app-expe .main .container > h1,
  body.mysifa-app-expe .main .container > .subtitle{
    display:none!important;
  }
  body.mysifa-app-expe .expe-mobile-hide-head{display:none!important}
  body.mysifa-app-expe .card-header:has(> .expe-mobile-hide-head:only-child){display:none}
  body.mysifa-app-expe .card-header:has(> h3.expe-mobile-hide-head){
    min-height:0;
    padding-top:10px;
    padding-bottom:10px;
  }
}
"""

EXPE_MAIN_JS = r"""
// ── MyExpé ────────────────────────────────────────────────────────
const EXPE_CONTACTS_KEY='mysifa_transport_contacts';
const EXPE_DEFAULT_CONTACTS={
  'Coupé':{type:'url',value:'https://coupe.station-chargeur.com/coupe/',label:'Portail Coupé'},
  'Ceva':{type:'url',value:'https://connect.gefco.net/psc-portal/login.html#LogIn',label:'Portail Ceva/Gefco'},
  'Coquelle':{type:'email',value:'eugeneleconte@outlook.com',label:'Mail Coquelle'},
  'Dimotrans':{type:'email',value:'eugeneleconte@outlook.com',label:'Mail Dimotrans'},
};
const EXPE_COLORS={'Coupé':'#22d3ee','Coquelle':'#a78bfa','Ceva':'#34d399','Dimotrans':'#fbbf24'};
function expeCC(c){return EXPE_COLORS[c]||'#94a3b8';}
function expeLoadContacts(){
  try{return {...EXPE_DEFAULT_CONTACTS,...JSON.parse(localStorage.getItem(EXPE_CONTACTS_KEY)||'{}')};}
  catch(e){return {...EXPE_DEFAULT_CONTACTS};}
}
function expeEnsureContacts(){if(!S.expeContacts)S.expeContacts=expeLoadContacts();return S.expeContacts;}
function expeOpenContact(carrier){
  if(typeof T!=='undefined'&&Array.isArray(T.list)){
    const tr=T.list.find(x=>String(x.nom||'')===String(carrier||''));
    if(tr&&typeof expeTrpOpenContact==='function'){expeTrpOpenContact(tr);return;}
  }
  const c=expeEnsureContacts()[carrier];if(!c)return;
  if(c.type==='url')window.open(c.value,'_blank','noopener');
  else{
    const s=encodeURIComponent('Demande de tarif SIFA - '+carrier);
    const b=encodeURIComponent('Bonjour,\n\nNous souhaitons obtenir un tarif pour :\n- Département : '+(S.expeDept||'')+'\n- Poids : '+(S.expeKg||'?')+' kg\n- Palettes : '+(S.expeNbPal||'?')+'\n\nCordialement,\nSIFA Roubaix');
    window.location.href='mailto:'+c.value+'?subject='+s+'&body='+b;
  }
}
async function ensureExpeRawData(){
  if(S.expeRaw||S.expeRawLoading)return;
  S.expeRawLoading=true;S.expeRawError=null;render();
  try{
    const r=await fetch('/static/transport_tarifs.json?v=4',{credentials:'same-origin'});
    if(!r.ok)throw new Error('HTTP '+r.status);
    S.expeRaw=await r.json();S.expeRawLoading=false;render();
  }catch(e){S.expeRawLoading=false;S.expeRawError='Impossible de charger les grilles.';render();}
}

// ── Calcul poids ─────────────────────────────────────────────────
function _calcCoupePoids(raw,dept,kg){
  const p=raw.coupe_poids&&raw.coupe_poids[dept];if(!p)return null;
  const b=raw.coupe_poids_brackets;
  for(let i=0;i<b.length;i++){
    if(kg<=b[i]){
      if(i<10)return p[i];
      return p[i]!=null?(kg/100)*p[i]:null;
    }
  }
  return null;
}
function _calcCevaPoids(raw,dept,kg){
  const p=raw.ceva_poids&&raw.ceva_poids[dept];if(!p)return null;
  const b=raw.ceva_poids_brackets;
  for(let i=0;i<b.length;i++){
    if(kg<=b[i]){
      if(i<10)return p[i];
      return p[i]!=null?(kg/100)*p[i]:null;
    }
  }
  return null;
}

// ── Calcul palette ───────────────────────────────────────────────
function _calcCoupePal(raw,dept,n){
  const p=raw.coupe_pal&&raw.coupe_pal[dept];
  if(!p||n<1||n>5)return null;
  return p[n-1]||null;
}
function _calcCevaPal(raw,dept,n){
  const p=raw.ceva_pal&&raw.ceva_pal[dept];
  if(!p||n<1||n>4)return null;
  return p[n-1]||null;
}
function _calcCoquellePal(raw,dept,n){
  const p=raw.coquelle_pal&&raw.coquelle_pal[dept];
  if(!p||n<1||n>33)return null;
  return p[n-1]||null;
}
function _calcDimotransPal(raw,dept,n){
  const p=raw.dimotrans_pal&&raw.dimotrans_pal[dept];
  if(!p||n<1||n>28)return null;
  return p[Math.min(n,28)-1]||null;
}

function expeCompute(){
  if(!S.expeRaw){toast('Grilles non chargées','warn');return;}
  const raw=S.expeRaw;
  const d=String(S.expeDept||'').trim().padStart(2,'0');
  const kg=Number(S.expeKg)||0;
  const nbPal=parseInt(S.expeNbPal,10)||0;
  const fuel=(Number(S.expeFuelPct)||0)/100;
  const r2=v=>v!=null?Math.round(v*100)/100:null;
  const af=v=>v!=null?r2(v*(1+fuel)):null;

  const poids=[];
  if(kg>0){
    [{c:'Coupé',fn:_calcCoupePoids},{c:'Ceva',fn:_calcCevaPoids}].forEach(({c,fn})=>{
      const p=af(fn(raw,d,kg));
      if(p!=null&&p>0)poids.push({carrier:c,price:p});
    });
    poids.sort((a,b)=>a.price-b.price);
  }
  const palette=[];
  if(nbPal>0){
    [
      {c:'Coupé',fn:_calcCoupePal,max:5},
      {c:'Coquelle',fn:_calcCoquellePal,max:33},
      {c:'Ceva',fn:_calcCevaPal,max:4},
      {c:'Dimotrans',fn:_calcDimotransPal,max:28},
    ].forEach(({c,fn})=>{
      const p=af(fn(raw,d,nbPal));
      if(p!=null&&p>0)palette.push({carrier:c,price:p});
    });
    palette.sort((a,b)=>a.price-b.price);
  }
  set({expeResults:{dept:d,kg,nbPal,fuel:Number(S.expeFuelPct)||0,poids,palette}});
}

// ── UI helpers ───────────────────────────────────────────────────
function renderExpeScore(item,rank){
  const col=expeCC(item.carrier);
  const medals=['\u{1F947}','\u{1F948}','\u{1F949}'];
  return h('div',{className:'expe-score'},
    h('div',{className:'stripe',style:{background:col}}),
    h('div',{className:'body'},
      h('div',{style:{display:'flex',justifyContent:'space-between',alignItems:'flex-start'}},
        h('div',{className:'carrier',style:{color:col}},item.carrier),
        rank<3?h('span',{className:'medal'},medals[rank]):null
      ),
      h('div',{className:'price',style:{color:'var(--text)'}},
        item.price.toFixed(2),
        h('span',{className:'unit'},'\u20ac HT')
      ),
      h('button',{className:'btn-ghost',
        style:{width:'100%',borderColor:col+'55',color:col},
        onClick:()=>expeOpenContact(item.carrier)
      },expeEnsureContacts()[item.carrier]&&expeEnsureContacts()[item.carrier].type==='url'?'Portail':'Contacter')
    )
  );
}
function renderExpeRankTable(title,rows){
  if(!rows||!rows.length)return h('div',{className:'card-empty'},'Aucun tarif disponible.');
  return h('div',{className:'card',style:{marginTop:10}},
    h('div',{className:'card-header'},h('h3',null,title+' ('+rows.length+')')),
    h('div',{style:{overflowX:'auto'}},
      h('table',{style:{minWidth:500}},
        h('thead',null,h('tr',null,
          h('th',null,'#'),h('th',null,'Transporteur'),h('th',null,'Prix HT'),h('th',null,'Contact')
        )),
        h('tbody',null,...rows.map((r,i)=>{
          const col=expeCC(r.carrier);
          return h('tr',null,
            h('td',null,String(i+1)),
            h('td',null,h('span',{style:{fontWeight:700,color:col}},r.carrier)),
            h('td',null,h('span',{style:{fontFamily:'monospace',fontWeight:800,color:col}},r.price.toFixed(2)+' \u20ac')),
            h('td',null,h('button',{className:'btn-ghost',style:{borderColor:col+'44',color:col},
              onClick:()=>expeOpenContact(r.carrier)
            },expeEnsureContacts()[r.carrier]&&expeEnsureContacts()[r.carrier].type==='url'?'Portail':'Email'))
          );
        }))
      )
    )
  );
}
function renderExpeContactModal(){
  const cur=JSON.parse(JSON.stringify(expeEnsureContacts()));
  const overlay=h('div',{className:'contact-modal-overlay'});
  const box=h('div',{className:'contact-modal',style:{maxWidth:520}});
  box.appendChild(h('div',{className:'contact-modal-head'},
    h('h3',null,'Contacts transporteurs'),
    h('button',{className:'contact-close-btn',onClick:()=>set({expeShowContacts:false})},'\u2715')
  ));
  const body=h('div',{className:'contact-modal-body',style:{display:'grid',gap:10}});
  Object.keys(cur).forEach(name=>{
    const row=h('div',{style:{border:'1px solid var(--border)',borderRadius:10,padding:10}});
    row.appendChild(h('div',{style:{fontSize:13,fontWeight:700,color:expeCC(name),marginBottom:8}},name));
    const sel=h('select',{className:'form-sel',style:{width:110}},
      h('option',{value:'email',selected:cur[name].type==='email'},'Email'),
      h('option',{value:'url',selected:cur[name].type==='url'},'Site web'));
    const inp=h('input',{value:cur[name].value||'',placeholder:cur[name].type==='url'?'https://...':'contact@...',style:{flex:1,minWidth:0}});
    sel.addEventListener('change',e=>{cur[name].type=e.target.value;});
    inp.addEventListener('input',e=>{cur[name].value=e.target.value;});
    row.appendChild(h('div',{style:{display:'flex',gap:8,flexWrap:'wrap'}},sel,inp));
    body.appendChild(row);
  });
  box.appendChild(body);
  box.appendChild(h('div',{className:'contact-modal-actions'},
    h('button',{className:'btn-ghost',onClick:()=>set({expeShowContacts:false})},'Annuler'),
    h('button',{className:'btn-sm',onClick:()=>{
      try{localStorage.setItem(EXPE_CONTACTS_KEY,JSON.stringify(cur));}catch(e){}
      set({expeContacts:{...EXPE_DEFAULT_CONTACTS,...cur},expeShowContacts:false});
    }},'Enregistrer')
  ));
  overlay.appendChild(box);
  overlay.addEventListener('click',e=>{if(e.target===overlay)set({expeShowContacts:false});});
  return overlay;
}
function renderExpeComparateur(){
  return renderExpeComparateurTarifs();
}
__EXPE_COMPARATEUR_JS__
__EXPE_DEVIS_JS__
__EXPE_TRANSPORTEURS_JS__
__EXPE_CARTE_FRANCE_JS__
function renderExpePoids(){
  const rows=S.expePoidsRows||[];
  const fKg=v=>v.toFixed(3)+'\u00a0kg';
  const wNum=x=>{const v=parseFloat(x);return Number.isFinite(v)?v:0;};

  // Recalcul sans rerender (garde le focus dans les inputs)
  const weightEls=[];
  let etiqTotalEl=null, palTotalEl=null, grandTotalEl=null, grandPalPartEl=null;
  function recalc(){
    const gram=wNum(S.expePoidsGram)||155;
    const coeff=wNum(S.expePoidsCoeff)||1.05;
    let etiqTotal=0;
    for(let i=0;i<rows.length;i++){
      const r=rows[i]||{};
      const q=wNum(r.qty), l=wNum(r.laize), d=wNum(r.dev);
      const w = (q&&l&&d) ? (q*l*d*coeff*gram/1e6) : null;
      if(w!=null) etiqTotal += w;
      if(weightEls[i]) weightEls[i].textContent = w!=null ? fKg(w) : '—';
      if(weightEls[i]){
        weightEls[i].style.opacity = w!=null ? '1' : '0.25';
        weightEls[i].style.fontWeight = w!=null ? '600' : 'normal';
      }
    }
    const palNb=wNum(S.expoPoidsPalNb)||0;
    const palKg=wNum(S.expoPoidsPalKg)||0;
    const palTotal=palNb*palKg;
    const grandTotal=etiqTotal+palTotal;
    if(etiqTotalEl) etiqTotalEl.textContent = etiqTotal>0 ? fKg(etiqTotal) : '—';
    if(palTotalEl) palTotalEl.textContent = palTotal>0 ? fKg(palTotal) : '—';
    if(grandTotalEl) grandTotalEl.textContent = grandTotal>0 ? grandTotal.toFixed(3)+'\u00a0kg' : '—';
    if(grandPalPartEl) grandPalPartEl.textContent = (grandTotal>0&&palTotal>0) ? ('dont palette\u00a0: '+fKg(palTotal)) : '';
  }

  const inp=(val,cb,extra={})=>{
    const el=h('input',Object.assign({type:'number',min:'0',step:'any',placeholder:'0',value:val,
      style:{width:'100%',padding:'0.3rem 0.5rem',borderRadius:'6px',border:'1px solid var(--border)',
             background:'var(--card)',color:'var(--fg)',fontSize:'0.85rem',boxSizing:'border-box'}},extra));
    el.addEventListener('input',e=>cb(e.target.value));
    return el;
  };
  const paramCard=h('div',{className:'card',style:{marginBottom:'1rem'}},
    h('div',{className:'card-header'},h('span',null,'Paramètres')),
    h('div',{style:{padding:'1rem 1rem 1.25rem'}},
      h('div',{style:{marginBottom:'1rem'}},
        h('div',{style:{display:'flex',alignItems:'center',gap:'0.5rem'}},
          (()=>{
            const el=h('input',{type:'number',min:'1',step:'any',placeholder:'155',
              value:S.expePoidsGram||'',
              style:{width:'90px',padding:'0.3rem 0.5rem',borderRadius:'6px',border:'1px solid var(--border)',
                     background:'var(--card)',color:'var(--fg)',fontSize:'0.85rem'}});
            el.addEventListener('input',e=>{S.expePoidsGram=e.target.value;recalc();});
            return el;
          })(),
          h('span',{style:{fontSize:'0.85rem',opacity:0.75}},'g/m²')
        )
      ),
      h('div',null,
        h('label',{style:{display:'block',fontSize:'0.75rem',opacity:0.65,marginBottom:'0.45rem'}},'Coefficient'),
        (()=>{const el=h('input',{type:'number',step:'0.01',min:'0.1',value:S.expePoidsCoeff,
          style:{width:'90px',padding:'0.3rem 0.5rem',borderRadius:'6px',border:'1px solid var(--border)',
                 background:'var(--card)',color:'var(--fg)',fontSize:'0.85rem'}});
          el.addEventListener('input',e=>{S.expePoidsCoeff=e.target.value;recalc();});return el;})()
      )
    )
  );

  const thStyle={padding:'0.4rem 0.5rem',textAlign:'left',fontSize:'0.75rem',opacity:0.6,fontWeight:'600',borderBottom:'1px solid var(--border)'};
  const tdStyle={padding:'0.3rem 0.4rem',verticalAlign:'middle'};
  const thead=h('thead',null,h('tr',null,
    h('th',{style:{...thStyle,width:'1.8rem',textAlign:'center'}},'#'),
    h('th',{style:thStyle},'Qté (mille)'),
    h('th',{style:thStyle},'Laize (mm)'),
    h('th',{style:thStyle},'Développé (mm)'),
    h('th',{style:{...thStyle,textAlign:'right'}},'Poids (kg)')
  ));
  const tbody=h('tbody',null,...rows.map((r,i)=>{
    const updateRow=(key,val)=>{
      if(!S.expePoidsRows) S.expePoidsRows=[];
      if(!S.expePoidsRows[i]) S.expePoidsRows[i]={qty:'',laize:'',dev:''};
      S.expePoidsRows[i][key]=val;
      recalc();
    };
    const wEl=h('span',null,'—');
    weightEls[i]=wEl;
    return h('tr',null,
      h('td',{style:{...tdStyle,textAlign:'center',fontSize:'0.75rem',opacity:0.4}},String(i+1)),
      h('td',{style:tdStyle},inp(r.qty,v=>updateRow('qty',v))),
      h('td',{style:tdStyle},inp(r.laize,v=>updateRow('laize',v))),
      h('td',{style:tdStyle},inp(r.dev,v=>updateRow('dev',v))),
      h('td',{style:{...tdStyle,textAlign:'right',fontWeight:'normal',opacity:0.25,fontSize:'0.85rem',whiteSpace:'nowrap'}},wEl)
    );
  }));

  const resetBtn=h('button',{className:'btn-ghost',style:{padding:'0.25rem 0.65rem',fontSize:'0.8rem',marginRight:'0.4rem'}},'Remettre à 0');
  resetBtn.addEventListener('click',()=>{
    set({expePoidsRows:[{qty:'',laize:'',dev:''},{qty:'',laize:'',dev:''},{qty:'',laize:'',dev:''},{qty:'',laize:'',dev:''}]});
  });
  const addBtn=h('button',{style:{padding:'0.25rem 0.65rem',fontSize:'0.8rem',borderRadius:'6px',cursor:'pointer',
    border:'1px solid var(--border)',background:'transparent',color:'var(--fg)'}},'+\u00a0Ligne');
  addBtn.addEventListener('click',()=>set({expePoidsRows:[...rows,{qty:'',laize:'',dev:''}]}));
  const delBtn=(rows.length>1)?h('button',{style:{padding:'0.25rem 0.65rem',fontSize:'0.8rem',borderRadius:'6px',cursor:'pointer',
    border:'1px solid var(--border)',background:'transparent',color:'var(--fg)',marginLeft:'0.4rem'}},'\u2212\u00a0Ligne'):null;
  if(delBtn)delBtn.addEventListener('click',()=>set({expePoidsRows:rows.slice(0,-1)}));

  const rowsCard=h('div',{className:'card',style:{marginBottom:'1rem'}},
    h('div',{className:'card-header',style:{display:'flex',alignItems:'center',justifyContent:'space-between'}},
      h('span',null,'Étiquettes'),
      h('div',null,resetBtn,addBtn,delBtn||null)
    ),
    h('div',{style:{overflowX:'auto',padding:'0.25rem 0.75rem 0.75rem'}},
      h('table',{style:{width:'100%',borderCollapse:'collapse',fontSize:'0.88rem'}},thead,tbody)
    ),
    (()=>{
      etiqTotalEl=h('strong',null,'—');
      return h('div',{style:{padding:'0.1rem 1rem 0.75rem',textAlign:'right',fontSize:'0.88rem',opacity:0.75}},
        'Sous-total étiquettes\u00a0: ',etiqTotalEl
      );
    })()
  );

  const palCard=h('div',{className:'card',style:{marginBottom:'1rem'}},
    h('div',{className:'card-header'},h('span',null,'Palette (optionnel)')),
    h('div',{style:{padding:'1rem',display:'flex',gap:'1rem',flexWrap:'wrap',alignItems:'flex-end'}},
      h('div',{style:{flex:'0 0 100px'}},
        h('label',{style:{display:'block',fontSize:'0.75rem',opacity:0.65,marginBottom:'0.4rem'}},'Nb palettes'),
        (()=>{const el=h('input',{type:'number',min:'0',step:'1',placeholder:'0',value:S.expoPoidsPalNb,
          style:{width:'100%',padding:'0.3rem 0.5rem',borderRadius:'6px',border:'1px solid var(--border)',
                 background:'var(--card)',color:'var(--fg)',fontSize:'0.85rem'}});
          el.addEventListener('input',e=>{S.expoPoidsPalNb=e.target.value;recalc();});return el;})()
      ),
      h('div',{style:{flex:'0 0 120px'}},
        h('label',{style:{display:'block',fontSize:'0.75rem',opacity:0.65,marginBottom:'0.4rem'}},'Poids / palette (kg)'),
        (()=>{const el=h('input',{type:'number',min:'0',step:'any',placeholder:'0',value:S.expoPoidsPalKg,
          style:{width:'100%',padding:'0.3rem 0.5rem',borderRadius:'6px',border:'1px solid var(--border)',
                 background:'var(--card)',color:'var(--fg)',fontSize:'0.85rem'}});
          el.addEventListener('input',e=>{S.expoPoidsPalKg=e.target.value;recalc();});return el;})()
      ),
      (()=>{
        palTotalEl=h('strong',null,'—');
        return h('div',{style:{paddingBottom:'0.2rem',fontSize:'0.88rem',opacity:0.75}},
          'Sous-total\u00a0: ',palTotalEl
        );
      })()
    )
  );

  const totalCard=h('div',{className:'card',style:{textAlign:'center',padding:'1.5rem 1rem',
    background:'var(--accent)',color:'#fff',borderRadius:'12px',marginBottom:'0.5rem'}},
    h('div',{style:{fontSize:'0.78rem',letterSpacing:'0.08em',opacity:0.85,marginBottom:'0.4rem'}},'POIDS TOTAL ESTIMÉ'),
    (()=>{
      grandTotalEl=h('div',{style:{fontSize:'2.4rem',fontWeight:'700',letterSpacing:'-1px',lineHeight:1.1}},'—');
      grandPalPartEl=h('div',{style:{fontSize:'0.8rem',opacity:0.8,marginTop:'0.35rem'}},'');
      return h('div',null,grandTotalEl,grandPalPartEl);
    })()
  );

  const root=h('div',{style:{maxWidth:'680px'}},
    h('p',{style:{opacity:0.55,fontSize:'0.82rem',marginBottom:'1.25rem',fontStyle:'italic'}},
      'Formule\u00a0: Qté\u2009(mille)\u2009×\u2009Laize\u2009×\u2009Développé\u2009×\u2009Coeff\u2009×\u2009Grammage\u2009/\u20091\u202f000\u202f000'),
    paramCard,rowsCard,palCard,totalCard
  );
  // Initial calc after DOM is built
  queueMicrotask(recalc);
  return root;
}

function expeParisDayISO(){
  try{return new Date().toLocaleDateString('sv-SE',{timeZone:'Europe/Paris'});}
  catch(e){const d=new Date();return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');}
}
async function loadExpePaletteTypes(){
  if(S.app!=='expe')return;
  if(S.expePaletteTypesLoading) return;
  if((S.expePaletteTypes||[]).length) return;
  set({expePaletteTypesLoading:true});
  try{
    const rows=await api('/api/expe/matieres-palettes');
    set({expePaletteTypes:Array.isArray(rows)?rows:[],expePaletteTypesLoading:false});
  }catch(e){
    set({expePaletteTypesLoading:false});
  }
}
function expePaletteTypeLabel(row){
  if(!row) return '—';
  if((row.type_colis||'').trim().toLowerCase()==='vrac') return 'Vrac';
  if(row.type_palette_label) return row.type_palette_label;
  const id=row.type_palette_matiere_id;
  if(id==null||id==='') return '—';
  const items=S.expePaletteTypes||[];
  const m=items.find(x=>String(x.id)===String(id));
  if(!m) return '—';
  const ref=(m.reference||'').trim();
  const des=(m.designation||'').trim();
  return ref?(des?ref+' — '+des:ref):'—';
}
async function loadExpeDepartJour(){
  if(S.app!=='expe')return;
  void loadExpePaletteTypes();
  if(_expeJourInflight)return await _expeJourInflight;
  _expeJourInflight=(async()=>{
    set({expeDepartLoading:true});
    try{
      const rows=await api('/api/expe/departs/jour');
      set({expeDepartList:Array.isArray(rows)?rows:[],expeDepartLoading:false});
    }catch(e){
      set({expeDepartLoading:false});
      toast(e.message||'Chargement impossible','error');
    }
  })();
  try{return await _expeJourInflight;}finally{_expeJourInflight=null;}
}
async function loadExpeDepartHistorique(resetPage){
  if(S.app!=='expe')return;
  void loadExpePaletteTypes();
  if(resetPage) S.expeDepartHistPage=1;
  // Préserver le focus/caret de la searchbar pendant les re-renders (chargement + résultats)
  const qEl = document.getElementById('expe-hist-search');
  const hadFocus = !!(qEl && document.activeElement === qEl);
  const caret = (hadFocus && typeof qEl.selectionStart === 'number') ? [qEl.selectionStart, qEl.selectionEnd] : null;

  set({expeDepartHistLoading:true});
  try{
    const qq=(S.expeDepartHistQ||'').trim();
    const page=S.expeDepartHistPage||1;
    const data=await api('/api/expe/departs/historique?q='+encodeURIComponent(qq)+'&page='+page+'&limit=50');
    const rows=Array.isArray(data)?data:(data&&data.rows)||[];
    set({
      expeDepartHist:rows,
      expeDepartHistTotal:data&&data.total!=null?data.total:rows.length,
      expeDepartHistPage:data&&data.page!=null?data.page:page,
      expeDepartHistPages:data&&data.pages!=null?data.pages:1,
      expeDepartHistLoading:false
    });
  }catch(e){
    set({expeDepartHistLoading:false});
    toast(e.message||'Chargement impossible','error');
  }
  if(hadFocus){
    requestAnimationFrame(()=>{
      const ne = document.getElementById('expe-hist-search');
      if(!ne) return;
      try{
        ne.focus();
        if(caret){
          const a=Math.min(caret[0]!=null?caret[0]:0, ne.value.length);
          const b=Math.min(caret[1]!=null?caret[1]:a, ne.value.length);
          ne.setSelectionRange(a,b);
        }
      }catch(e){}
    });
  }
}
function scheduleExpeHistSearch(){
  if(_expeHistSearchT)clearTimeout(_expeHistSearchT);
  _expeHistSearchT=setTimeout(()=>{loadExpeDepartHistorique(true);},380);
}
function expeHistChangePage(delta){
  const pages=S.expeDepartHistPages||1;
  const next=(S.expeDepartHistPage||1)+delta;
  if(next<1||next>pages)return;
  S.expeDepartHistPage=next;
  void loadExpeDepartHistorique();
}
async function expeValiderDepart(id){
  try{
    await api('/api/expe/departs/'+id+'/valider',{method:'POST'});
    toast('Départ validé — entrée dans l\'historique');
    await loadExpeDepartJour();
  }catch(e){toast(e.message||'Validation impossible','error');}
}
async function expeInvaliderDepart(id){
  if(!confirm('Remettre ce départ dans le suivi du jour ?\n\nIl disparaîtra de l\'historique et pourra être modifié ou validé à nouveau.')) return;
  try{
    await api('/api/expe/departs/'+id+'/invalider',{method:'POST'});
    toast('Départ remis dans le suivi du jour');
    await loadExpeDepartHistorique();
    if((S.expeDepartSubTab||'jour')==='jour') await loadExpeDepartJour();
  }catch(e){toast(e.message||'Action impossible','error');}
}

function expeOpenDepartModal(prefill, mode){
  const dayVal=(S.expeDepartJourDate&&String(S.expeDepartJourDate).trim())||expeParisDayISO();
  const src = prefill || {};
  const srcDate = (src.date_enlevement||'') ? String(src.date_enlevement).slice(0,10) : '';
  void loadExpePaletteTypes();
  // En édition ou duplication : onglet manuel direct ; nouveau départ : onglet picker dossier
  const isEdit = !!(mode==='edit' && src && src.id);
  const initialTab = (mode==='new' && !prefill) ? 'dossier' : 'manuel';
  if(initialTab==='dossier'){
    void loadExpeDepartDossiers();
  }
  set({
    expeDepartModalOpen:true,
    expeDepartEditId: isEdit ? src.id : null,
    expeDepartFormTab: initialTab,
    expeDepartDossierQuery:'',
    expeDepartDossierHi:-1,
    expeDepartForm:{
      date_enlevement: srcDate || dayVal,
      affreteurs: src.affreteurs||'',
      transporteur: src.transporteur||'',
      client: src.client||'',
      code_postal_destination: src.code_postal_destination||'',
      ref_sifa: src.ref_sifa||'',
      arc: src.arc||'',
      no_cde_transport: src.no_cde_transport||'',
      no_bl: src.no_bl||'',
      type_palette_matiere_id: (src.type_colis||'').trim().toLowerCase()==='vrac'
        ? '__vrac__'
        : (src.type_palette_matiere_id!=null && src.type_palette_matiere_id!=='')
          ? String(src.type_palette_matiere_id) : '',
      nb_palette: (src.nb_palette!=null && src.nb_palette!=='') ? String(src.nb_palette) : '',
      poids_total_kg: (src.poids_total_kg!=null && src.poids_total_kg!=='') ? String(src.poids_total_kg) : '',
      date_livraison: (src.date_livraison||'') ? String(src.date_livraison).slice(0,10) : '',
      planning_entry_id: (src.planning_entry_id!=null && src.planning_entry_id!=='') ? String(src.planning_entry_id) : '',
      palette_europe: src.palette_europe ? 1 : 0,
    }
  });
}
function expeCloseDepartModal(){
  set({expeDepartModalOpen:false, expeDepartEditId:null, expeDepartFormTab:'dossier'});
}

// Charge la liste des dossiers disponibles pour le picker MyExpé
async function loadExpeDepartDossiers(force){
  if(S.expeDepartDossiersLoading) return;
  if(!force && (S.expeDepartDossiers||[]).length) return;
  set({expeDepartDossiersLoading:true});
  try{
    const data = await api('/api/expe/dossiers-disponibles');
    const list = (data && Array.isArray(data.dossiers)) ? data.dossiers : [];
    set({expeDepartDossiers:list, expeDepartDossiersLoading:false});
  }catch(e){
    set({expeDepartDossiersLoading:false});
    toast(e.message||'Chargement des dossiers impossible','error');
  }
}

// Filtre + tri pour le picker (recherche libre)
function _expeFilterDossiers(q){
  const list = S.expeDepartDossiers || [];
  const term = (q||'').trim().toLowerCase();
  if(!term) return list.slice();
  const norm = s => String(s||'').toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
  const lqNorm = norm(term);
  return list.filter(d=>{
    const fields = [
      d.reference, d.client, d.ref_produit, d.description,
      d.numero_of, d.machine_nom, d.date_livraison,
    ];
    return fields.some(f=>{
      if(f==null||f==='') return false;
      const s = String(f).toLowerCase();
      return s.includes(term) || norm(s).includes(lqNorm);
    });
  });
}

// Au clic sur un dossier : pré-remplit le form et bascule onglet "Saisie manuelle"
function expeSelectDossier(d){
  if(!d) return;
  const f = S.expeDepartForm || {};
  // ARC = pe.reference (numéro de dossier). On surcharge toujours.
  f.arc = d.reference || f.arc || '';
  f.client = d.client || f.client || '';
  f.ref_sifa = d.ref_produit || f.ref_sifa || '';
  f.date_livraison = (d.date_livraison||'').slice(0,10) || f.date_livraison || '';
  f.planning_entry_id = d.id ? String(d.id) : '';
  // Estimation nb palettes via fiche technique si dispo (cartons sol × hauteur ÷ ratio)
  // Si pas de donnée fiche : laisser vide pour saisie manuelle
  if(!f.nb_palette){
    const nSol = parseFloat(d.ft_palette_nb_cartons_sol || d.ft_nb_au_sol || 0);
    const nHaut = parseFloat(d.ft_palette_nb_cartons_hauteur || d.ft_nb_etage || 0);
    if(nSol > 0 && nHaut > 0){
      // Fiche technique donne 1 palette ; quantité réelle dépend de l'OF
      f.nb_palette = '1';
    }
  }
  // type_palette : si fiche technique donne palette_type connu, essayer de matcher la réf MyStock
  if(!f.type_palette_matiere_id && d.ft_palette_type){
    const pt = String(d.ft_palette_type||'').toLowerCase().trim();
    const items = S.expePaletteTypes || [];
    const match = items.find(m=>{
      const ref = String(m.reference||'').toLowerCase();
      const des = String(m.designation||'').toLowerCase();
      return pt && (ref.includes(pt) || des.includes(pt) || pt.includes(ref));
    });
    if(match){
      f.type_palette_matiere_id = String(match.id);
      if(match.is_europe) f.palette_europe = 1;
    }
  }
  set({expeDepartForm:f, expeDepartFormTab:'manuel'});
  toast('Champs préremplis depuis le dossier '+(d.reference||''));
}

// Recherche dans le picker — re-render incrémental sans reconstruire la searchbar
function _expeRefreshDossierPickerList(){
  const list = document.getElementById('expe-picker-list-inner');
  if(!list) return;
  list.innerHTML = '';
  _expeBuildDossierPickerItems(S.expeDepartDossierQuery).forEach(el=>list.appendChild(el));
}

function _expeBuildDossierPickerItems(q){
  const filtered = _expeFilterDossiers(q);
  if(!filtered.length){
    const empty = document.createElement('div');
    empty.className = 'expe-picker-empty';
    empty.textContent = q ? ('Aucun résultat pour « '+q+' »')
                          : (S.expeDepartDossiersLoading ? 'Chargement…' : 'Aucun dossier disponible');
    return [empty];
  }
  const sectionLabel = (sec)=>{
    if(sec==='en_cours') return 'En cours';
    if(sec==='prochain') return 'Prochain en attente';
    if(sec==='termine_recent') return 'Récemment terminés';
    return 'Autres dossiers';
  };
  const sectionOrder = ['en_cours','prochain','termine_recent','autre'];
  // Regrouper par section uniquement si pas de recherche active
  const groups = {};
  filtered.forEach(d=>{
    const k = d.displayed_section || 'autre';
    (groups[k] = groups[k]||[]).push(d);
  });
  const els = [];
  sectionOrder.forEach(sec=>{
    const arr = groups[sec];
    if(!arr || !arr.length) return;
    if(!q){
      const lbl = document.createElement('div');
      lbl.className = 'expe-picker-section';
      lbl.textContent = sectionLabel(sec);
      els.push(lbl);
    }
    arr.forEach(d=>{
      const dossierBlocked = d.departs_count && d.departs_count > 0;
      const ref = d.reference || '—';
      const client = d.client || 'Client non renseigné';
      const refProd = d.ref_produit || d.description || '';
      const livr = d.date_livraison ? d.date_livraison.slice(0,10) : '';
      const wrap = document.createElement('div');
      wrap.className = 'expe-picker-item'+(sec==='en_cours'?' expe-picker-item--active':'');
      wrap.onclick = ()=>expeSelectDossier(d);
      const line1 = document.createElement('div');
      line1.className = 'expe-picker-line1';
      line1.innerHTML = '<span class="expe-picker-ref">'+escHtml(ref)+'</span>'
                     + '<span class="expe-picker-sep">·</span>'
                     + '<span class="expe-picker-client">'+escHtml(client)+'</span>';
      wrap.appendChild(line1);
      const line2 = document.createElement('div');
      line2.className = 'expe-picker-line2';
      const parts = [];
      if(refProd) parts.push(escHtml(refProd));
      if(d.machine_nom) parts.push(escHtml(d.machine_nom));
      if(livr) parts.push('Livr. '+escHtml(livr));
      line2.innerHTML = parts.join('  ·  ');
      if(parts.length) wrap.appendChild(line2);
      const meta = document.createElement('div');
      meta.className = 'expe-picker-meta';
      const statutLbl = d.statut==='en_cours'?'En cours'
                      : d.statut==='termine'?'Terminé'
                      : d.statut==='attente'?'En attente':(d.statut||'');
      meta.innerHTML = '<span class="expe-picker-statut expe-picker-statut--'+escAttr(d.statut||'')+'">'+escHtml(statutLbl)+'</span>'
                     + (dossierBlocked ? '<span class="expe-picker-warn">Déjà expédié ('+d.departs_count+')</span>' : '');
      wrap.appendChild(meta);
      els.push(wrap);
    });
  });
  return els;
}

function renderExpeDepartModal(){
  if(!S.expeDepartModalOpen) return null;
  const dayVal=(S.expeDepartJourDate&&String(S.expeDepartJourDate).trim())||expeParisDayISO();
  const f=S.expeDepartForm||{};
  const isEdit = !!S.expeDepartEditId;
  const formTab = S.expeDepartFormTab || (isEdit ? 'manuel' : 'dossier');

  function mk(label,key,type,ph){
    const i=h('input',{type:type||'text',placeholder:ph||'',value:(f[key]!=null?String(f[key]):''),name:key});
    i.addEventListener('input',e=>{S.expeDepartForm[key]=e.target.value; expeScheduleSaveLocal();});
    return h('div',{className:'expe-field'},h('label',null,label),i);
  }

  const paletteItems=S.expePaletteTypes||[];
  const palSel=h('select',{name:'type_palette_matiere_id'});
  palSel.appendChild(h('option',{value:''},'— Sélectionner —'));
  paletteItems.forEach(m=>{
    const ref=(m.reference||'').trim();
    const des=(m.designation||'').trim();
    const lbl=ref?(des?ref+' — '+des:ref):('Réf. #'+m.id);
    const opt=h('option',{value:String(m.id)},lbl);
    if(String(f.type_palette_matiere_id||'')===String(m.id)) opt.selected=true;
    palSel.appendChild(opt);
  });
  const vracOpt=h('option',{value:'__vrac__'},'Vrac (sans palette — UPS…)');
  if(f.type_palette_matiere_id==='__vrac__') vracOpt.selected=true;
  palSel.appendChild(vracOpt);
  palSel.addEventListener('change',e=>{
    S.expeDepartForm.type_palette_matiere_id=e.target.value;
    expeScheduleSaveLocal();
  });
  const palField=h('div',{className:'expe-field'},
    h('label',null,'Type de palette'),
    palSel
  );
  if(!paletteItems.length && S.expePaletteTypesLoading){
    palField.appendChild(h('div',{style:{fontSize:'12px',color:'var(--muted)',marginTop:'4px'}},'Chargement des références…'));
  }else if(!paletteItems.length){
    palField.appendChild(h('div',{style:{fontSize:'12px',color:'var(--muted)',marginTop:'4px'}},
      'Aucune référence palette active (MyStock > Matières premières).'));
  }

  const overlay=h('div',{className:'add-row-modal',style:{zIndex:12000}});
  overlay.addEventListener('click',e=>{if(e.target===overlay)expeCloseDepartModal();});

  const box=h('div',{className:'add-row-form',style:{maxWidth:'760px'}});
  const closeBtn=h('button',{type:'button',className:'add-row-close',onClick:expeCloseDepartModal},'×');
  const header=h('div',{className:'add-row-header'},
    h('h3',null,isEdit?'Modifier un départ':'Ajouter un départ'),
    h('div',{className:'badge',style:{marginLeft:'auto'}},'Jour : ',dayVal)
  );

  const form=h('form',{onSubmit:async(e)=>{
    e.preventDefault();
    if(S.expeDepartSubmitting) return;
    const dateEnl = (S.expeDepartForm.date_enlevement||'').trim() || dayVal;
    const body={
      date_enlevement: dateEnl,
      affreteurs:(S.expeDepartForm.affreteurs||'').trim()||null,
      transporteur:(S.expeDepartForm.transporteur||'').trim()||null,
      client:(S.expeDepartForm.client||'').trim()||null,
      code_postal_destination:(S.expeDepartForm.code_postal_destination||'').trim()||null,
      ref_sifa:(S.expeDepartForm.ref_sifa||'').trim()||null,
      arc:(S.expeDepartForm.arc||'').trim()||null,
      no_cde_transport:(S.expeDepartForm.no_cde_transport||'').trim()||null,
      no_bl:(S.expeDepartForm.no_bl||'').trim()||null,
      type_palette_matiere_id:(S.expeDepartForm.type_palette_matiere_id||'')==='__vrac__'?null:(S.expeDepartForm.type_palette_matiere_id||'').trim()||null,
      type_colis:(S.expeDepartForm.type_palette_matiere_id||'')==='__vrac__'?'vrac':null,
      nb_palette:(S.expeDepartForm.nb_palette||'').trim()||null,
      poids_total_kg:(S.expeDepartForm.poids_total_kg||'').trim()||null,
      date_livraison:(S.expeDepartForm.date_livraison||'').trim()||null,
      planning_entry_id:(S.expeDepartForm.planning_entry_id||'').trim()||null,
      palette_europe: S.expeDepartForm.palette_europe ? 1 : 0
    };
    if(!body.date_enlevement){toast("Date d'enlèvement obligatoire",'error');return;}
    set({expeDepartSubmitting:true});
    try{
      if(isEdit){
        await api('/api/expe/departs/'+S.expeDepartEditId,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        toast('Départ modifié');
      }else{
        await api('/api/expe/departs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        toast('Départ enregistré');
      }
      set({expeDepartSubmitting:false});
      expeCloseDepartModal();
      if((S.expeDepartSubTab||'jour')==='historique') await loadExpeDepartHistorique();
      else await loadExpeDepartJour();
    }catch(err){
      set({expeDepartSubmitting:false});
      toast(err.message||'Erreur','error');
    }
  }});

  // Case à cocher palette Europe (modifiable manuellement)
  const europeCheck = h('input',{type:'checkbox',id:'expe-form-pal-europe'});
  europeCheck.checked = !!(f.palette_europe);
  europeCheck.addEventListener('change',e=>{
    S.expeDepartForm.palette_europe = e.target.checked ? 1 : 0;
    expeScheduleSaveLocal();
  });
  const europeField = h('div',{className:'expe-field'},
    h('label',null,'Palette Europe (consignée)'),
    h('div',{style:{display:'flex',alignItems:'center',gap:'8px',padding:'8px 0'}},
      europeCheck,
      h('label',{htmlFor:'expe-form-pal-europe',style:{fontSize:'12px',color:'var(--text2)',cursor:'pointer'}},
        'Suivre le retour de cette palette dans l\'onglet Palettes Europe')
    )
  );

  const fields=h('div',{className:'expe-fields'},
    mk("Date d'enlèvement",'date_enlevement','date'),
    mk('Affréteurs','affreteurs'),
    mk('Transporteur','transporteur'),
    mk('Client','client'),
    mk('Code postal / destination','code_postal_destination'),
    mk('Réf. SIFA','ref_sifa'),
    mk('ARC','arc'),
    mk('N° commande transporteur','no_cde_transport'),
    mk('N° BL','no_bl'),
    palField,
    mk('Nombre de palettes','nb_palette','number','ex: 2'),
    mk('Poids total (kg)','poids_total_kg','number','ex: 1325'),
    mk('Date livraison (prévue)','date_livraison','date'),
    europeField
  );

  // Onglets internes : "Depuis un dossier" / "Saisie manuelle" — masqués en édition
  const tabsNav = !isEdit ? h('div',{className:'expe-form-tabs'},
    h('button',{type:'button',
      className:'expe-form-tab'+(formTab==='dossier'?' active':''),
      onClick:()=>{
        set({expeDepartFormTab:'dossier', expeDepartDossierQuery:'', expeDepartDossierHi:-1});
        void loadExpeDepartDossiers();
      }},
      iconEl('folder',13),' Depuis un dossier'),
    h('button',{type:'button',
      className:'expe-form-tab'+(formTab==='manuel'?' active':''),
      onClick:()=>set({expeDepartFormTab:'manuel'})},
      iconEl('edit',13),' Saisie manuelle')
  ) : null;

  // Picker dossier (onglet "Depuis un dossier")
  let pickerBody = null;
  if(!isEdit && formTab==='dossier'){
    const searchInp = h('input',{
      type:'text',
      id:'expe-picker-search',
      className:'expe-picker-search',
      placeholder:'Rechercher (réf dossier, client, réf produit, OF…)',
      autoComplete:'off',
      value:S.expeDepartDossierQuery||'',
    });
    searchInp.addEventListener('input',e=>{
      S.expeDepartDossierQuery = e.target.value;
      _expeRefreshDossierPickerList();
    });
    const listEl = h('div',{className:'expe-picker-list',id:'expe-picker-list-inner'});
    requestAnimationFrame(()=>{
      _expeRefreshDossierPickerList();
      document.getElementById('expe-picker-search')?.focus();
    });
    pickerBody = h('div',{className:'expe-picker-wrap'},
      h('div',{className:'expe-picker-hint'},
        'Sélectionnez un dossier pour préremplir ARC, client, réf. SIFA, type et nb de palettes, livraison prévue. Vous pourrez ensuite ajuster manuellement.'),
      searchInp,
      listEl,
      h('div',{style:{display:'flex',justifyContent:'flex-end',marginTop:'10px'}},
        h('button',{type:'button',className:'btn-ghost',
          style:{fontSize:'12px',padding:'6px 12px'},
          onClick:()=>set({expeDepartFormTab:'manuel'})},
          'Continuer en saisie manuelle →')
      )
    );
  }

  const actions=h('div',{className:'form-actions'},
    h('button',{type:'button',className:'btn-ghost',onClick:expeCloseDepartModal},'Annuler'),
    h('button',{type:'submit',className:'btn',disabled:!!S.expeDepartSubmitting},S.expeDepartSubmitting?'Enregistrement…':'Enregistrer le départ')
  );

  if(tabsNav) form.appendChild(tabsNav);
  if(pickerBody) form.appendChild(pickerBody);
  if(formTab==='manuel' || isEdit){
    form.appendChild(fields);
    form.appendChild(actions);
  }
  box.appendChild(closeBtn);
  box.appendChild(header);
  box.appendChild(form);
  overlay.appendChild(box);
  return overlay;
}

// Résolution couleur transporteur : JOIN DB en priorité, sinon lookup par nom dans T.list
function trpColorFromRow(r){
  if(r.transporteur_couleur)return r.transporteur_couleur;
  const nom=(r.transporteur||'').trim().toLowerCase();
  if(!nom)return '';
  const t=(T.list||[]).find(x=>(x.nom||'').trim().toLowerCase()===nom);
  return t?(t.couleur||''):'';
}

function expeDepartActsGrid(buttons,validerBtn){
  const kids=(buttons||[]).filter(Boolean);
  if(!kids.length&&!validerBtn) return null;
  return h('div',{className:'expe-dep-actions-cell'},
    kids.length?h('div',{className:'expe-dep-acts'},...kids):null,
    validerBtn||null
  );
}

// ── MyExpé : suivi des palettes Europe ────────────────────────
async function loadExpePalettesEurope(){
  if(S.app!=='expe')return;
  if(S.expePalettesEuropeLoading) return;
  set({expePalettesEuropeLoading:true});
  try{
    const params = new URLSearchParams();
    if(S.expePalettesEuropeStatutFilter) params.set('statut', S.expePalettesEuropeStatutFilter);
    if(S.expePalettesEuropeClientFilter) params.set('client', S.expePalettesEuropeClientFilter);
    if(S.expePalettesEuropeQuery) params.set('q', S.expePalettesEuropeQuery);
    const qs = params.toString();
    const data = await api('/api/expe/palettes-europe'+(qs?'?'+qs:''));
    set({expePalettesEuropeData:data, expePalettesEuropeLoading:false});
  }catch(e){
    set({expePalettesEuropeLoading:false});
    toast(e.message||'Chargement palettes Europe impossible','error');
  }
}

async function expeChangePaletteEuropeStatut(departId, statut, dateRetour){
  try{
    const body = {statut: statut};
    if(dateRetour !== undefined) body.date_retour = dateRetour;
    await api('/api/expe/departs/'+departId+'/palette-europe', {
      method:'PATCH',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify(body)
    });
    toast('Statut palette mis à jour');
    await loadExpePalettesEurope();
  }catch(e){
    toast(e.message||'Mise à jour impossible','error');
  }
}

function _expePalEuropeStatutLabel(s){
  if(s==='retournee') return 'Retournée';
  if(s==='perdue') return 'Perdue';
  return 'En attente';
}

function _expePalEuropeStatutBadge(s){
  const lbl = _expePalEuropeStatutLabel(s);
  const cls = 'expe-pal-eur-badge expe-pal-eur-badge--'+(s||'en_attente');
  return h('span',{className:cls},lbl);
}

function renderExpePalettesEurope(){
  const data = S.expePalettesEuropeData || {departs:[], recap_clients:[], totaux:{}};
  const departs = data.departs || [];
  const recap = data.recap_clients || [];
  const tot = data.totaux || {};
  const subTab = S.expePalEurSubTab || 'suivi';

  // Sous-onglets
  const subTabs = [
    {key:'suivi', label:'Suivi', icon:'clipboard'},
    {key:'recap', label:'Récap clients', icon:'users'},
  ];
  const subNav = h('div',{className:'nav-tabs',style:{marginBottom:'16px'}},
    ...subTabs.map(t=>h('button',{
      type:'button',
      className:'nav-tab'+(subTab===t.key?' active':''),
      onClick:()=>set({expePalEurSubTab:t.key})
    },iconEl(t.icon,14),' ',t.label))
  );

  // Bandeau totaux (commun aux deux sous-onglets)
  const totauxBlock = h('div',{className:'expe-pal-eur-totaux'},
    h('div',{className:'expe-pal-eur-tot-card'},
      h('div',{className:'expe-pal-eur-tot-lbl'},'Total envoyées'),
      h('div',{className:'expe-pal-eur-tot-val'},String(tot.nb_pal_envoyees||0))
    ),
    h('div',{className:'expe-pal-eur-tot-card expe-pal-eur-tot-card--ok'},
      h('div',{className:'expe-pal-eur-tot-lbl'},'Retournées'),
      h('div',{className:'expe-pal-eur-tot-val'},String(tot.nb_pal_retournees||0))
    ),
    h('div',{className:'expe-pal-eur-tot-card expe-pal-eur-tot-card--warn'},
      h('div',{className:'expe-pal-eur-tot-lbl'},'En attente'),
      h('div',{className:'expe-pal-eur-tot-val'},String(tot.nb_pal_en_attente||0))
    ),
    h('div',{className:'expe-pal-eur-tot-card expe-pal-eur-tot-card--bad'},
      h('div',{className:'expe-pal-eur-tot-lbl'},'Perdues'),
      h('div',{className:'expe-pal-eur-tot-val'},String(tot.nb_pal_perdues||0))
    )
  );

  // Filtres
  const statutSel = h('select',{
    value:S.expePalettesEuropeStatutFilter||'',
    onChange:e=>{
      S.expePalettesEuropeStatutFilter = e.target.value;
      void loadExpePalettesEurope();
    }
  });
  ['','en_attente','retournee','perdue'].forEach(v=>{
    const lbl = v===''?'Tous statuts':_expePalEuropeStatutLabel(v);
    const opt = h('option',{value:v},lbl);
    if((S.expePalettesEuropeStatutFilter||'')===v) opt.selected=true;
    statutSel.appendChild(opt);
  });

  const searchInp = h('input',{
    id:'expe-pal-eur-search',
    type:'search',
    placeholder:'Rechercher (client, ARC, BL…)',
    value:S.expePalettesEuropeQuery||'',
    style:{flex:'1',minWidth:'240px',padding:'8px 12px',borderRadius:'8px',
      border:'1px solid var(--border)',background:'var(--bg)',color:'var(--text)',fontSize:'13px'}
  });
  let _palEurSearchT = null;
  searchInp.addEventListener('input',e=>{
    S.expePalettesEuropeQuery = e.target.value;
    if(_palEurSearchT) clearTimeout(_palEurSearchT);
    _palEurSearchT = setTimeout(()=>void loadExpePalettesEurope(), 380);
  });

  // Vue récap par client (cards)
  const recapCards = recap.length ? h('div',{className:'expe-pal-eur-recap'},
    ...recap.map(r=>{
      const solde = (parseFloat(r.nb_pal_en_attente)||0);
      return h('div',{className:'expe-pal-eur-recap-card'+(solde>0?' expe-pal-eur-recap-card--debt':'')},
        h('div',{className:'expe-pal-eur-recap-client'},r.client||'—'),
        h('div',{className:'expe-pal-eur-recap-row'},
          h('span',{className:'expe-pal-eur-recap-lbl'},'Envoyées'),
          h('span',{className:'expe-pal-eur-recap-val'},String(r.nb_pal_envoyees||0))
        ),
        h('div',{className:'expe-pal-eur-recap-row'},
          h('span',{className:'expe-pal-eur-recap-lbl'},'Retournées'),
          h('span',{className:'expe-pal-eur-recap-val expe-pal-eur-recap-val--ok'},String(r.nb_pal_retournees||0))
        ),
        h('div',{className:'expe-pal-eur-recap-row'},
          h('span',{className:'expe-pal-eur-recap-lbl'},'Perdues'),
          h('span',{className:'expe-pal-eur-recap-val expe-pal-eur-recap-val--bad'},String(r.nb_pal_perdues||0))
        ),
        h('div',{className:'expe-pal-eur-recap-row expe-pal-eur-recap-row--solde'},
          h('span',{className:'expe-pal-eur-recap-lbl'},'En attente'),
          h('span',{className:'expe-pal-eur-recap-val'+(solde>0?' expe-pal-eur-recap-val--warn':'')},String(solde))
        ),
        h('button',{type:'button',className:'btn-ghost',
          style:{fontSize:'11px',padding:'4px 8px',marginTop:'8px',width:'100%'},
          onClick:()=>{S.expePalettesEuropeClientFilter = r.client || ''; void loadExpePalettesEurope();}
        },'Filtrer ses départs')
      );
    })
  ) : h('div',{style:{padding:'18px',color:'var(--muted)',fontSize:'13px',textAlign:'center'}},
    'Aucune palette Europe enregistrée.');

  // Tableau des départs palette Europe
  const head = h('tr',null,
    ...['Date enl.','Client','Transp.','ARC','N° BL','Pal.','Statut','Date retour','Note','Actions'].map(t=>h('th',null,t))
  );
  const bodyRows = departs.length ? departs.map(r=>{
    const statut = r.palette_europe_statut || 'en_attente';
    const noteInp = h('input',{
      type:'text',
      placeholder:'Note…',
      value:r.palette_europe_note||'',
      style:{width:'100%',padding:'4px 8px',fontSize:'11px',background:'var(--bg)',
        border:'1px solid var(--border)',borderRadius:'6px',color:'var(--text)'}
    });
    let _noteT = null;
    noteInp.addEventListener('input',e=>{
      const v = e.target.value;
      if(_noteT) clearTimeout(_noteT);
      _noteT = setTimeout(async()=>{
        try{
          await api('/api/expe/departs/'+r.id+'/palette-europe',{
            method:'PATCH',
            headers:{'Content-Type':'application/json'},
            body: JSON.stringify({note: v})
          });
        }catch(e){ /* silencieux */ }
      }, 800);
    });
    const dateInp = h('input',{
      type:'date',
      value:(r.palette_europe_date_retour||'').slice(0,10),
      style:{padding:'4px 8px',fontSize:'12px',background:'var(--bg)',
        border:'1px solid var(--border)',borderRadius:'6px',color:'var(--text)'}
    });
    dateInp.addEventListener('change',async(e)=>{
      const v = e.target.value;
      try{
        await api('/api/expe/departs/'+r.id+'/palette-europe',{
          method:'PATCH',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({date_retour: v, statut: v ? 'retournee' : statut})
        });
        toast('Date retour enregistrée');
        await loadExpePalettesEurope();
      }catch(e){ toast(e.message||'Erreur','error'); }
    });
    return h('tr',null,
      h('td',null,(r.date_enlevement||'').slice(0,10)),
      h('td',null,r.client||'—'),
      h('td',null,(c=>c?trpTag(r.transporteur||'—',c):(r.transporteur||'—'))(trpColorFromRow(r))),
      h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.arc||'—'),
      h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.no_bl||'—'),
      h('td',{style:{textAlign:'right',fontWeight:'700'}},r.nb_palette!=null?String(r.nb_palette):'—'),
      h('td',null,_expePalEuropeStatutBadge(statut)),
      h('td',null,dateInp),
      h('td',{style:{minWidth:'140px'}},noteInp),
      h('td',{className:'expe-pal-eur-acts-cell'},
        h('div',{className:'expe-pal-eur-acts'},
          statut!=='retournee' ? h('button',{type:'button',className:'expe-pal-eur-act expe-pal-eur-act--ok',
            title:'Marquer comme retournée (date du jour)',
            onClick:()=>expeChangePaletteEuropeStatut(r.id,'retournee',expeParisDayISO())
          },iconEl('check-circle',14)) : null,
          statut!=='perdue' ? h('button',{type:'button',className:'expe-pal-eur-act expe-pal-eur-act--bad',
            title:'Marquer comme perdue',
            onClick:()=>{
              if(!confirm('Marquer cette palette comme perdue ?')) return;
              expeChangePaletteEuropeStatut(r.id,'perdue', null);
            }
          },iconEl('x',14)) : null,
          statut!=='en_attente' ? h('button',{type:'button',className:'expe-pal-eur-act',
            title:'Réinitialiser le statut (en attente)',
            onClick:()=>expeChangePaletteEuropeStatut(r.id,'en_attente', '')
          },iconEl('rotate-ccw',13)) : null
        )
      )
    );
  }) : [h('tr',null,h('td',{colSpan:10,style:{color:'var(--muted)',padding:'18px',textAlign:'center'}},
    S.expePalettesEuropeLoading?'Chargement…':'Aucun départ palette Europe pour ces filtres'))];

  // Bloc Suivi : filtre + tableau détaillé
  const suiviBlock = h('div',{className:'card'},
    h('div',{className:'card-header',style:{display:'flex',gap:'10px',alignItems:'center',flexWrap:'wrap'}},
      h('h3',{className:'expe-mobile-hide-head'},'Départs détaillés'),
      h('div',{style:{display:'flex',gap:'10px',alignItems:'center',marginLeft:'auto',flexWrap:'wrap'}},
        statutSel,
        searchInp,
        S.expePalettesEuropeClientFilter ? h('button',{type:'button',className:'btn-ghost',
          style:{fontSize:'12px',padding:'4px 10px'},
          onClick:()=>{S.expePalettesEuropeClientFilter=''; void loadExpePalettesEurope();}
        },'× Filtre : '+S.expePalettesEuropeClientFilter) : null
      )
    ),
    h('div',{style:{overflowX:'auto'}},
      h('table',{className:'table-std expe-departs-table'},
        h('thead',null,head),
        h('tbody',null,...bodyRows)
      )
    )
  );

  // Bloc Récap : cards par client
  const recapBlock = h('div',{className:'card'},
    h('div',{className:'card-header'},
      h('h3',{className:'expe-mobile-hide-head'},'Récap par client'),
      h('div',{style:{fontSize:'11px',color:'var(--muted)',marginLeft:'auto'}},
        recap.length+' client'+(recap.length>1?'s':'')+' avec palette Europe')
    ),
    h('div',{style:{padding:'14px 18px'}}, recapCards)
  );

  return h('div',null,
    subNav,
    totauxBlock,
    subTab==='recap' ? recapBlock : suiviBlock
  );
}

function renderExpeSuiviDeparts(){
  const btnBarStyle={display:'flex',gap:'10px',alignItems:'center',flexWrap:'wrap'};
  const btnPairStyle={
    minWidth:'160px',
    padding:'10px 16px',
    fontSize:'13px',
    borderRadius:'10px',
    fontWeight:'800',
    whiteSpace:'nowrap',
    display:'inline-flex',
    alignItems:'center',
    justifyContent:'center',
    gap:'8px',
    lineHeight:1
  };
  const topBar=h('div',{className:'card',style:{marginBottom:'12px'}},
    h('div',{className:'card-header',style:{display:'flex',justifyContent:'flex-start',alignItems:'center',gap:'12px',flexWrap:'wrap'}},
      h('h3',{className:'expe-mobile-hide-head'},'Départs programmés'),
      expeCanWrite()?h('div',{style:btnBarStyle},
        h('button',{className:'btn',type:'button',style:btnPairStyle,onClick:()=>expeOpenDepartModal(null,'new')},iconEl('plus',14),' Ajouter')
      ):null
    )
  );
  const rows=S.expeDepartList||[];
  const head=h('tr',null,
    ...['Date enl.','Affr.','Transp.','Client','Destination','Réf SIFA','ARC','Cde transp.','N° BL','Type pal.','Pal.','Poids kg','Liv. prév.',''].map(t=>h('th',null,t))
  );
  function formatDateFr(iso){
    if(!iso||iso.length<10)return iso||'—';
    const d=new Date(iso+'T00:00:00');
    const jours=['Dimanche','Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi'];
    const mois=['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre'];
    return jours[d.getDay()]+' '+d.getDate()+' '+mois[d.getMonth()]+' '+d.getFullYear();
  }
  let prevDate=null;
  const bodyRows=[];
  rows.forEach(r=>{
    const dateEnl=(r.date_enlevement||'').slice(0,10);
    if(dateEnl!==prevDate){
      bodyRows.push(
        h('tr',{className:'expe-day-sep-row'},
          h('td',{colSpan:14,className:'expe-day-sep-cell'},
            h('span',{className:'expe-day-sep-label'},formatDateFr(dateEnl))
          )
        )
      );
      prevDate=dateEnl;
    }
    bodyRows.push(h('tr',null,
      h('td',null,dateEnl),
      h('td',null,r.affreteurs||'—'),
      h('td',null,(c=>c?trpTag(r.transporteur||'—',c):(r.transporteur||'—'))(trpColorFromRow(r))),
      h('td',null,r.client||'—'),
      h('td',{style:{maxWidth:'140px',fontSize:'12px'}},r.code_postal_destination||'—'),
      h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.ref_sifa||'—'),
      h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.arc||'—'),
      h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.no_cde_transport||'—'),
      h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.no_bl||'—'),
      h('td',{style:{fontSize:'12px',maxWidth:'120px'}},expePaletteTypeLabel(r)),
      h('td',null,r.nb_palette!=null?String(r.nb_palette):'—'),
      h('td',null,r.poids_total_kg!=null?String(r.poids_total_kg):'—'),
      h('td',null,(r.date_livraison||'').slice(0,10)||'—'),
      expeCanWrite()?h('td',{className:'expe-dep-actions-td'},
        expeDepartActsGrid([
          r.code_postal_destination?h('button',{className:'btn-ghost expe-dep-ab',type:'button',
            title:'Ouvrir une demande de devis préremplie avec les données de ce départ',
            onClick:()=>ouvrirDevisDepuisDepart(r.id,parseFloat(r.poids_total_kg)||0,parseFloat(r.nb_palette)||0,String(r.code_postal_destination||''))},expeDevisIcon(14)):null,
          (r.code_postal_destination&&(r.poids_total_kg||r.nb_palette))?h('button',{className:'btn-ghost expe-dep-ab',type:'button',
            title:'Comparer les tarifs des transporteurs pour ce départ',
            onClick:()=>ouvrirComparateurDepuisDepart(r.id,parseFloat(r.poids_total_kg)||0,parseFloat(r.nb_palette)||0,String(r.code_postal_destination||''))},expeCompareIcon(14)):null,
          h('button',{className:'btn-ghost expe-dep-ab',type:'button',title:'Dupliquer ce départ en nouvelle saisie',
            onClick:()=>expeOpenDepartModal(r,'new')},iconEl('copy',14)),
          h('button',{className:'btn-ghost expe-dep-ab',type:'button',title:'Modifier les informations de ce départ',
            onClick:()=>expeOpenDepartModal(r,'edit')},iconEl('edit',14)),
          h('button',{className:'btn-danger expe-dep-ab',type:'button',title:'Supprimer définitivement ce départ',onClick:async()=>{
            if(!confirm('Supprimer ce départ ?')) return;
            try{
              await api('/api/expe/departs/'+r.id,{method:'DELETE'});
              toast('Départ supprimé');
              await loadExpeDepartJour();
            }catch(e){toast(e.message||'Suppression impossible','error');}
          }},iconEl('trash',14))
        ],h('button',{className:'btn expe-dep-valider-btn',type:'button',
          title:'Valider ce départ et l\'archiver dans l\'historique',
          onClick:()=>expeValiderDepart(r.id)},'Valider'))
      ):h('td',null,'—')
    ));
  });
  const body=rows.length?bodyRows:[h('tr',null,h('td',{colSpan:14,style:{color:'var(--muted)'}},S.expeDepartLoading?'Chargement…':'Aucun départ en attente pour ce jour'))];
  const listCard=h('div',{className:'card'},
    h('div',{className:'card-header'},h('h3',{className:'expe-mobile-hide-head'},'Départs programmés (en attente de validation)')),
    h('div',{style:{overflowX:'auto'}},h('table',{className:'table-std expe-departs-table'},h('thead',null,head),h('tbody',null,...body)))
  );
  return h('div',null,topBar,listCard);
}

function renderExpeHistoriqueDeparts(){
  const qInp=h('input',{
    id:'expe-hist-search',
    type:'search',
    placeholder:'Réf. SIFA, client, ARC, BL, type palette, transporteur…',
    value:S.expeDepartHistQ||'',
    style:{width:'100%',maxWidth:'560px',padding:'10px 12px',borderRadius:'8px',border:'1px solid var(--border)',background:'var(--bg)',color:'var(--text)',marginBottom:'12px'},
    onInput:e=>{
      // Ne pas déclencher un render à chaque caractère (sinon perte de focus).
      S.expeDepartHistQ = e.target.value;
      scheduleExpeHistSearch();
    }
  });
  const rows=S.expeDepartHist||[];
  const total=S.expeDepartHistTotal||0;
  const page=S.expeDepartHistPage||1;
  const pages=S.expeDepartHistPages||1;
  const limit=50;
  const from=total===0?0:(page-1)*limit+1;
  const to=Math.min(page*limit,total);
  const head=h('tr',null,
    ...['Validé le','Date enl.','Client','Réf SIFA','ARC','Cde transp.','N° BL','Transp.','Type pal.','Pal.','Poids','Liv. prév.',''].map(t=>h('th',null,t))
  );
  const body=rows.length?rows.map(r=>h('tr',null,
    h('td',{style:{fontSize:'12px',whiteSpace:'nowrap'}},(r.validated_at||'').replace('T',' ').slice(0,16)||'—'),
    h('td',null,(r.date_enlevement||'').slice(0,10)),
    h('td',null,r.client||'—'),
    h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.ref_sifa||'—'),
    h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.arc||'—'),
    h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.no_cde_transport||'—'),
    h('td',{style:{fontFamily:'monospace',fontSize:'12px'}},r.no_bl||'—'),
    h('td',null,(c=>c?trpTag(r.transporteur||'—',c):(r.transporteur||'—'))(trpColorFromRow(r))),
    h('td',{style:{fontSize:'12px',maxWidth:'120px'}},expePaletteTypeLabel(r)),
    h('td',null,r.nb_palette!=null?String(r.nb_palette):'—'),
    h('td',null,r.poids_total_kg!=null?String(r.poids_total_kg):'—'),
    h('td',null,(r.date_livraison||'').slice(0,10)||'—'),
    expeCanWrite()?h('td',{className:'expe-dep-actions-td'},
      expeDepartActsGrid([
        h('button',{className:'btn-ghost expe-dep-ab',type:'button',title:'Dupliquer ce départ en nouvelle saisie',
          onClick:()=>expeOpenDepartModal(r,'new')},iconEl('copy',14)),
        h('button',{className:'btn-ghost expe-dep-ab',type:'button',title:'Modifier les informations de ce départ',
          onClick:()=>expeOpenDepartModal(r,'edit')},iconEl('edit',14)),
        h('button',{className:'btn-danger expe-dep-ab',type:'button',title:'Supprimer définitivement ce départ de l\'historique',onClick:async()=>{
          if(!confirm('Supprimer ce départ ?')) return;
          try{
            await api('/api/expe/departs/'+r.id,{method:'DELETE'});
            toast('Départ supprimé');
            await loadExpeDepartHistorique();
          }catch(e){toast(e.message||'Suppression impossible','error');}
        }},iconEl('trash',14))
      ],
      h('button',{className:'btn expe-dep-invalider-btn',type:'button',
        title:'Annuler la validation et remettre ce départ dans le suivi du jour',
        onClick:()=>void expeInvaliderDepart(r.id)},'Invalider'))
    ):h('td',null,'—')
  )):[h('tr',null,h('td',{colSpan:13,style:{color:'var(--muted)'}},S.expeDepartHistLoading?'Chargement…':'Aucune entrée (ou affiner la recherche)'))];
  const pager=h('div',{className:'expe-hist-pager'},
    h('span',{className:'page-info'},
      total===0?'Aucun résultat':(from+'–'+to+' / '+total.toLocaleString('fr')+(pages>1?' · page '+page+'/'+pages:''))
    ),
    h('button',{type:'button',className:'page-btn',disabled:page<=1,onClick:()=>expeHistChangePage(-1)},'‹ Précédent'),
    h('button',{type:'button',className:'page-btn',disabled:page>=pages,onClick:()=>expeHistChangePage(1)},'Suivant ›')
  );
  return h('div',null,
    h('div',{className:'card',style:{marginBottom:'12px',padding:'14px 18px'}},
      h('h3',{style:{fontSize:'14px',fontWeight:'700',marginBottom:'8px'}},'Recherche'),
      h('div',{className:'expe-help',style:{marginBottom:'8px'}},'Mots séparés par des espaces : tous doivent être trouvés (ref., client, ARC, BL, etc.). Insensible à la casse. Résultats paginés par 50.'),
      qInp
    ),
    h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',{className:'expe-mobile-hide-head'},'Historique des départs validés')),
      h('div',{style:{overflowX:'auto'}},h('table',{className:'table-std expe-hist-table'},h('thead',null,head),h('tbody',null,...body))),
      pager
    )
  );
}

function renderExpeSuiviDepartsWithSubtabs(){
  const sub=S.expeDepartSubTab||'jour';
  const tabs=[
    {key:'jour',label:'Départs programmés',icon:'clipboard'},
    {key:'historique',label:'Historique',icon:'folder'},
  ];
  const subNav=h('div',{className:'nav-tabs',style:{marginBottom:'16px'}},
    ...tabs.map(t=>h('button',{
      type:'button',
      className:'nav-tab'+(sub===t.key?' active':''),
      onClick:()=>set({expeDepartSubTab:t.key})
    },iconEl(t.icon,14),' ',t.label))
  );
  const body=sub==='historique'?renderExpeHistoriqueDeparts():renderExpeSuiviDeparts();
  // Modal monté au niveau parent : reste accessible quel que soit le sous-onglet
  // (sinon, modifier une ligne depuis l'Historique forçait à revenir sur "Départs du jour").
  return h('div',null,subNav,body,renderExpeDepartModal());
}

function renderExpe(){
  const isLight=document.body.classList.contains('light');
  if(S.expeTab==='historique_departs'){
    S.expeTab='suivi_departs';
    S.expeDepartSubTab='historique';
  }
  if(S.expeTab==='dashboard')S.expeTab='suivi_departs';
  const tab=S.expeTab||'suivi_departs';
  const sub=S.expeDepartSubTab||'jour';
  const loadKey=tab==='suivi_departs'?tab+'_'+sub:tab;
  if(loadKey!==_expeLastRenderedInnerTab){
    _expeLastRenderedInnerTab=loadKey;
    if(tab==='suivi_departs'){
      if(!T.list.length&&!T.loading)void loadTransporteurs();
      if(sub==='jour')void loadExpeDepartJour();
      else void loadExpeDepartHistorique();
    }else if(tab==='comparateur'){if(!T.list.length&&!T.loading)void loadTransporteurs();}
    else if(tab==='devis'){void chargerDemandes();if(!T.list.length&&!T.loading)void loadTransporteurs();}
    else if(tab==='prospects'){void chargerProspects();}
    else if(tab==='transporteurs'&&!T.pageLoaded){T.pageLoaded=true;void loadTransporteurs();}
    else if(tab==='palettes_europe'){void loadExpePalettesEurope();}
  }

  const sidebar=h('nav',{className:'sidebar'},
    h('div',{className:'logo'},
      h('div',{className:'logo-brand'},'My',h('span',null,'Expé')),
      h('div',{className:'logo-sub'},'by SIFA')
    ),
    // Sections collapsibles
    (()=>{
      const SECTIONS = [
        { key:'ops', label:'Opérations', items:[
          {tab:'suivi_departs',  ico:'clipboard', label:'Départs'},
          {tab:'palettes_europe',ico:'pallet',    label:'Palettes Europe'},
        ]},
        { key:'prep', label:'Préparation envoi', items:[
          {tab:'comparateur',ico:'sliders',   label:'Comparateur tarifs'},
          {tab:'devis',      ico:'mail',      label:'Devis transporteurs'},
          {tab:'poids',      ico:'calculator',label:'Calcul poids'},
        ]},
        { key:'ref', label:'Référentiel', items:[
          {tab:'transporteurs',ico:'truck',label:'Transporteurs'},
          {tab:'prospects',    ico:'users',label:'Prospects'},
        ]},
      ];
      const lsKey = (k)=>'mysifa.expe.section.'+k;
      const isCollapsed = (k)=>{
        try{ return localStorage.getItem(lsKey(k)) === 'collapsed'; }catch(e){ return false; }
      };
      const toggleSection = (k)=>{
        try{
          const cur = isCollapsed(k);
          localStorage.setItem(lsKey(k), cur?'expanded':'collapsed');
        }catch(e){}
        render();
      };
      const wrap = h('div',{className:'expe-sidebar-sections'});
      SECTIONS.forEach(sec=>{
        const collapsed = isCollapsed(sec.key);
        const hasActive = sec.items.some(it=>it.tab===tab);
        const header = h('button',{
          type:'button',
          className:'expe-sec-header'+(collapsed?' collapsed':'')+(hasActive?' has-active':''),
          onClick:()=>toggleSection(sec.key),
          'aria-expanded': String(!collapsed)
        },
          h('span',{className:'expe-sec-chev'},iconEl(collapsed?'chevron-right':'chevron-down',12)),
          h('span',{className:'expe-sec-label'},sec.label)
        );
        wrap.appendChild(header);
        if(!collapsed){
          const body = h('div',{className:'expe-sec-body'});
          sec.items.forEach(it=>{
            body.appendChild(
              h('button',{
                className:'nav-btn'+(tab===it.tab?' active':''),
                onClick:()=>set({expeTab:it.tab})
              }, iconEl(it.ico,15), '  ', it.label)
            );
          });
          wrap.appendChild(body);
        }
      });
      return wrap;
    })(),
    renderExpePlanningNav(),
    h('div',{className:'sidebar-bottom'},
      h('button',{className:'nav-btn back-mysifa',onClick:()=>{window.location.href='/'}},
        '← Retour ',h('span',{className:'wm'},'My',h('span',null,'Sifa'))
      ),
      sidebarUserChip(S.user),
      (()=>{
        const b=h('button',{className:'support-btn',title:'Contacter le support',onClick:()=>set({contactOpen:true})});
        const ico=h('span',{className:'support-ico'});
        try{ico.innerHTML=(window.MySifaSupport&&typeof window.MySifaSupport.iconSvg==='function')?window.MySifaSupport.iconSvg():'';}catch(e){ico.innerHTML='';}
        b.appendChild(ico);b.appendChild(h('span',null,'Contacter le support'));return b;
      })(),
      h('button',{className:'theme-btn',onClick:()=>{MySifaTheme.toggleMode();render();}},
        h('span',{className:'theme-ico'},iconEl(isLight?'sun':'moon',16)),
        h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
      ),
      h('button',{className:'logout-btn',onClick:doLogout},iconEl('log-out',14),' Déconnexion')
    )
  );
  const topbar=h('div',{className:'mobile-topbar'},
    h('button',{type:'button',className:'mobile-menu-btn',onClick:toggleSidebar,'aria-label':'Menu'},iconEl('menu',20)),
    h('div',null,
      h('div',{className:'mobile-topbar-title'},'MyExpé'),
      h('div',{className:'mobile-topbar-sub'},
        tab==='suivi_departs'?(sub==='historique'?'Historique départs':'Départs programmés'):
        tab==='palettes_europe'?'Suivi des palettes Europe consignées':
        tab==='transporteurs'?'Transporteurs':tab==='devis'?'Demandes de devis':tab==='prospects'?'Prospects transporteurs':tab==='poids'?'Calcul poids':'Comparateur tarifs')
    ),
    h('button',{type:'button',className:'mobile-home-btn',onClick:()=>{window.location.href='/'},'aria-label':'Accueil'},iconEl('home',20))
  );

  const content=tab==='suivi_departs'?renderExpeSuiviDepartsWithSubtabs():
    tab==='palettes_europe'?renderExpePalettesEurope():
    tab==='transporteurs'?renderExpeTransporteurs():tab==='poids'?renderExpePoids():
    tab==='devis'?renderExpeDevisSection():tab==='prospects'?renderExpeProspectsSection():
    renderExpeComparateur();
  // Motion : cascade d'entree au changement d'onglet uniquement. On pose
  // data-page-enter sur la .container (topbar, h1, sous-titre, contenu
  // cascadent ensemble) — effet plus visible que sur le seul wrapper du tab.
  const _moExpeKey=tab+'|'+(tab==='suivi_departs'?sub:'');
  const _moExpeEnter=(window._moExpeLastKey!==_moExpeKey);
  window._moExpeLastKey=_moExpeKey;
  // 2e niveau : data-page-enter sur le contenu du tab — les sous-onglets et
  // les cartes internes cascadent en parallele de la cascade .container.
  if(_moExpeEnter && content && content.nodeType===1){
    try{ content.setAttribute('data-page-enter',''); }catch(_){}
  }
  const contentWrap=content;

  return h('div',null,
    S.sidebarOpen?h('div',{className:'sidebar-overlay',onClick:closeSidebar}):null,
    h('div',{className:'app'},
      sidebar,
      h('main',{className:'main'},
        h('div',Object.assign({className:'container'},_moExpeEnter?{'data-page-enter':''}:{},(tab==='suivi_departs'||tab==='palettes_europe')?{style:{maxWidth:'1600px'}}:{}),
          topbar,
          h('h1',null,'MyExpé'),
          !expeCanWrite()?h('div',{className:'readonly-notice',style:{marginBottom:'12px'}},iconEl('eye',13),' Lecture seule — consultation des départs, transporteurs et délais'):null,
          h('div',{className:'subtitle'},
            tab==='suivi_departs'?(sub==='historique'?'Recherche multi-critères sur les départs validés'
              :'Enregistrement des enlèvements et validation vers l\'historique')
            :tab==='palettes_europe'?'Suivi des palettes Europe consignées — quels clients, combien, et combien sont revenues'
            :tab==='comparateur'?'Comparaison des transporteurs selon les grilles tarifaires actives en base'
            :tab==='devis'?'Prospection parallèle — demandes de tarif aux transporteurs'
            :tab==='prospects'?'Transporteurs hors référentiel — suivi de démarchage'
            :tab==='poids'?'Estimation du poids d\'un envoi d\'étiquettes'
            :'Référentiel transporteurs, zones et tarifs'),
          contentWrap
        )
      )
    ),
    renderExpeTranspPanel(),
    renderExpeTransporteurModal(),
    renderExpeDevisModal(),
    S.expeShowContacts?renderExpeContactModal():null
  );
}
"""

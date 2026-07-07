"""MySifa — Coffre RH (vue salarié).

Route : /coffre — tout utilisateur authentifié voit ses propres bulletins,
contrats, attestations et gère ses notes de frais.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION
from services.auth_service import get_current_user

router = APIRouter()


@router.get("/coffre", response_class=HTMLResponse)
def coffre_page(request: Request):
    try:
        _ = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/coffre", status_code=302)
        raise
    return HTMLResponse(content=COFFRE_HTML.replace("__V_LABEL__", f"v{APP_VERSION}"))


COFFRE_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Mon coffre RH — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);--ok:#34d399;--danger:#f87171;--warn:#fbbf24}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);--ok:#059669;--danger:#dc2626;--warn:#d97706}
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.wrap{max-width:1080px;margin:0 auto;padding:24px 20px 60px}
.head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:22px;flex-wrap:wrap}
.head h1{margin:0;font-size:22px;font-weight:800}
.head .sub{font-size:12px;color:var(--muted);margin-top:4px}
.head .back{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border-radius:10px;background:transparent;border:1px solid var(--border);color:var(--text2);text-decoration:none;font-size:12px;font-weight:600;transition:all .15s}
.head .back:hover{border-color:var(--accent);color:var(--accent)}
.tabs{display:flex;gap:6px;border-bottom:1px solid var(--border);margin-bottom:20px;overflow-x:auto}
.tab{padding:10px 16px;background:transparent;border:none;color:var(--muted);font-size:13px;font-weight:600;cursor:pointer;border-bottom:2px solid transparent;transition:all .15s;font-family:inherit;white-space:nowrap}
.tab:hover{color:var(--text2)}
.tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.info-banner{background:var(--accent-bg);border:1px solid var(--border);border-radius:10px;padding:12px 16px;font-size:12px;color:var(--text2);line-height:1.5;margin-bottom:18px}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px;margin-bottom:16px}
.card h2{margin:0 0 14px;font-size:15px;font-weight:700}
.year-group{margin-bottom:20px}
.year-title{font-size:13px;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.doc-list{display:grid;gap:8px;grid-template-columns:repeat(auto-fill,minmax(220px,1fr))}
.doc-item{display:flex;align-items:center;gap:10px;padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;transition:all .15s;cursor:pointer;text-decoration:none;color:inherit}
.doc-item:hover{border-color:var(--accent);background:var(--accent-bg)}
.doc-icon{width:32px;height:32px;flex-shrink:0;display:flex;align-items:center;justify-content:center;background:var(--accent-bg);color:var(--accent);border-radius:8px}
.doc-info{flex:1;min-width:0}
.doc-title{font-size:13px;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.doc-meta{font-size:11px;color:var(--muted);margin-top:2px}
.doc-badge{font-size:9px;padding:2px 6px;border-radius:4px;background:var(--accent);color:#0a0e17;font-weight:700;text-transform:uppercase;letter-spacing:.3px}
.empty{text-align:center;padding:40px 20px;color:var(--muted);font-size:13px}
.btn{padding:10px 18px;border-radius:10px;border:none;background:var(--accent);color:#0a0e17;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s;display:inline-flex;align-items:center;gap:8px}
.btn:hover{filter:brightness(1.08)}
.btn.ghost{background:transparent;border:1px solid var(--border);color:var(--text2)}
.btn.ghost:hover{border-color:var(--accent);color:var(--accent);filter:none}
.btn.danger{background:var(--danger);color:#fff}
.btn.small{padding:6px 10px;font-size:11px;border-radius:7px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 12px;background:var(--bg);color:var(--muted);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border)}
td{padding:12px;border-bottom:1px solid var(--border);color:var(--text2)}
tr:hover td{background:var(--accent-bg)}
.statut{display:inline-block;padding:3px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px}
.statut.brouillon{background:rgba(148,163,184,.15);color:var(--muted)}
.statut.soumise{background:rgba(251,191,36,.15);color:var(--warn)}
.statut.validee{background:rgba(34,211,238,.15);color:var(--accent)}
.statut.payee{background:rgba(52,211,153,.15);color:var(--ok)}
.statut.refusee{background:rgba(248,113,113,.15);color:var(--danger)}
.montant{font-family:'SF Mono','Consolas',monospace;font-weight:700;color:var(--text)}
.modal-back{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:200;display:flex;align-items:center;justify-content:center;padding:16px}
.modal{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:22px;max-width:460px;width:100%;max-height:90vh;overflow:auto}
.modal h3{margin:0 0 16px;font-size:16px;font-weight:700}
.field{margin-bottom:14px}
.field label{display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.field input,.field select,.field textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none;transition:border-color .15s}
.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
.field textarea{min-height:70px;resize:vertical}
.file-drop{border:1.5px dashed var(--border);border-radius:8px;padding:16px;text-align:center;font-size:12px;color:var(--muted);cursor:pointer;transition:all .15s}
.file-drop:hover{border-color:var(--accent);color:var(--accent)}
.file-drop.has-file{border-style:solid;color:var(--text2);background:var(--bg)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.modal-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:18px;flex-wrap:wrap}
.toast{position:fixed;top:24px;right:24px;background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:8px;padding:12px 18px;font-size:13px;color:var(--text);z-index:1000;box-shadow:0 10px 24px rgba(0,0,0,.3);animation:slideIn .2s}
.toast.error{border-left-color:var(--danger)}
.toast.ok{border-left-color:var(--ok)}
@keyframes slideIn{from{transform:translateX(20px);opacity:0}to{transform:translateX(0);opacity:1}}
.filters{display:flex;gap:10px;align-items:center;margin-bottom:14px;flex-wrap:wrap}
.filters select{padding:7px 10px;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text2);font-size:12px;font-family:inherit}
@media(max-width:640px){.wrap{padding:14px 12px 40px}.head h1{font-size:18px}.doc-list{grid-template-columns:1fr}.row2{grid-template-columns:1fr}table{font-size:12px}th,td{padding:8px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <div>
      <h1>Mon coffre RH</h1>
      <div class="sub">Bulletins de paie, contrats et notes de frais</div>
    </div>
    <a href="/" class="back">← Retour au portail</a>
  </div>

  <div class="info-banner">
    Coffre interne SIFA — consultation et sauvegarde de vos documents.
    Le bulletin officiel reste celui remis en main propre par la comptabilité.
  </div>

  <div class="tabs">
    <button type="button" class="tab active" data-tab="bulletins">Mes bulletins</button>
    <button type="button" class="tab" data-tab="documents">Autres documents</button>
    <button type="button" class="tab" data-tab="ndf">Mes notes de frais</button>
  </div>

  <section id="panel-bulletins">
    <div class="card">
      <div class="filters">
        <label style="font-size:12px;color:var(--muted)">Année :</label>
        <select id="filter-bul-annee"><option value="">Toutes</option></select>
      </div>
      <div id="bul-container"><div class="empty">Chargement…</div></div>
    </div>
  </section>

  <section id="panel-documents" style="display:none">
    <div class="card">
      <h2>Contrats, attestations et autres documents</h2>
      <div id="doc-container"><div class="empty">Chargement…</div></div>
    </div>
  </section>

  <section id="panel-ndf" style="display:none">
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:10px">
        <h2 style="margin:0">Mes notes de frais</h2>
        <button type="button" class="btn" onclick="openNdfModal()">+ Nouvelle note</button>
      </div>
      <div id="ndf-container"><div class="empty">Chargement…</div></div>
    </div>
  </section>

  <div style="text-align:center;margin-top:30px;font-size:11px;color:var(--muted);font-family:'SF Mono','Consolas',monospace">MySifa __V_LABEL__</div>
</div>

<script>
const DOC_TYPE_LABELS = {bulletin_paie:'Bulletin de paie',contrat:'Contrat',attestation:'Attestation',autre:'Autre'};
const MOIS_LABELS = ['','Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];

function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function fmtMontant(n){return (Number(n)||0).toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2})+' €';}
function fmtDate(s){if(!s)return '';const d=new Date(s.substr(0,10));return isNaN(d)?s:d.toLocaleDateString('fr-FR');}
function toast(msg,type){const t=document.createElement('div');t.className='toast '+(type==='error'?'error':'ok');t.textContent=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),3500);}
async function api(url,opts){opts=opts||{};opts.credentials='include';const r=await fetch(url,opts);if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||j.message||m;}catch(e){}throw new Error(m);}return r.json();}

// ── Tabs ──
document.querySelectorAll('.tab').forEach(t=>{
  t.onclick=()=>{
    document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
    t.classList.add('active');
    ['bulletins','documents','ndf'].forEach(k=>{
      document.getElementById('panel-'+k).style.display=(k===t.dataset.tab?'':'none');
    });
  };
});

// ── Bulletins ──
let bulData={documents:[],annees_disponibles:[]};

async function loadBulletins(){
  const annee=document.getElementById('filter-bul-annee').value;
  try{
    const url='/api/coffre/documents?type=bulletin_paie'+(annee?'&annee='+annee:'');
    bulData=await api(url);
    // Peupler filtre annees si premier chargement
    if(!annee){
      const sel=document.getElementById('filter-bul-annee');
      sel.innerHTML='<option value="">Toutes</option>'+bulData.annees_disponibles.map(a=>`<option value="${a}">${a}</option>`).join('');
    }
    renderBulletins();
  }catch(e){document.getElementById('bul-container').innerHTML='<div class="empty">Erreur : '+esc(e.message)+'</div>';}
}
function renderBulletins(){
  const c=document.getElementById('bul-container');
  if(!bulData.documents.length){c.innerHTML='<div class="empty">Aucun bulletin disponible pour l\'instant.</div>';return;}
  const byYear={};
  bulData.documents.forEach(d=>{const y=d.annee||'—';(byYear[y]=byYear[y]||[]).push(d);});
  c.innerHTML=Object.keys(byYear).sort((a,b)=>String(b).localeCompare(String(a))).map(y=>`
    <div class="year-group">
      <div class="year-title">${esc(y)}</div>
      <div class="doc-list">
        ${byYear[y].map(d=>`
          <a class="doc-item" href="/api/coffre/documents/${d.id}/download" target="_blank" rel="noopener">
            <div class="doc-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            </div>
            <div class="doc-info">
              <div class="doc-title">${esc(MOIS_LABELS[d.mois]||d.libelle||'Bulletin')} ${esc(d.annee||'')}</div>
              <div class="doc-meta">${d.consulte_at?'Consulté':'Non consulté'} · ${Math.round((d.taille_bytes||0)/1024)} Ko</div>
            </div>
          </a>
        `).join('')}
      </div>
    </div>
  `).join('');
}
document.getElementById('filter-bul-annee').addEventListener('change',loadBulletins);

// ── Autres documents ──
async function loadDocs(){
  try{
    const j=await api('/api/coffre/documents');
    const docs=j.documents.filter(d=>d.type!=='bulletin_paie');
    const c=document.getElementById('doc-container');
    if(!docs.length){c.innerHTML='<div class="empty">Aucun autre document.</div>';return;}
    c.innerHTML='<div class="doc-list">'+docs.map(d=>`
      <a class="doc-item" href="/api/coffre/documents/${d.id}/download" target="_blank" rel="noopener">
        <div class="doc-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
        </div>
        <div class="doc-info">
          <div class="doc-title">${esc(d.libelle||DOC_TYPE_LABELS[d.type]||d.type)}</div>
          <div class="doc-meta">${esc(DOC_TYPE_LABELS[d.type]||d.type)} · ${esc(fmtDate(d.uploaded_at))}</div>
        </div>
      </a>
    `).join('')+'</div>';
  }catch(e){document.getElementById('doc-container').innerHTML='<div class="empty">Erreur : '+esc(e.message)+'</div>';}
}

// ── Notes de frais ──
async function loadNdf(){
  try{
    const j=await api('/api/coffre/notes-frais');
    const c=document.getElementById('ndf-container');
    if(!j.notes.length){c.innerHTML='<div class="empty">Aucune note de frais. Cliquez sur « Nouvelle note » pour en créer une.</div>';return;}
    c.innerHTML=`<table>
      <thead><tr><th>Date</th><th>Catégorie</th><th>Description</th><th style="text-align:right">Montant</th><th>Statut</th><th></th></tr></thead>
      <tbody>${j.notes.map(n=>`
        <tr>
          <td>${esc(fmtDate(n.date_frais))}</td>
          <td>${esc(n.categorie||'—')}</td>
          <td style="max-width:280px">${esc((n.description||'').slice(0,80))}${(n.description||'').length>80?'…':''}${n.motif_refus?'<div style="font-size:11px;color:var(--danger);margin-top:3px">Refus : '+esc(n.motif_refus)+'</div>':''}</td>
          <td style="text-align:right" class="montant">${fmtMontant(n.montant_ttc)}</td>
          <td><span class="statut ${esc(n.statut)}">${esc(n.statut)}</span></td>
          <td style="text-align:right;white-space:nowrap">
            ${n.justificatif_nom?`<a class="btn ghost small" href="/api/coffre/notes-frais/${n.id}/justificatif" target="_blank" rel="noopener">Voir</a>`:''}
            ${n.statut==='brouillon'?`
              <button class="btn small" onclick="submitNdf(${n.id})">Soumettre</button>
              <button class="btn ghost small" onclick="deleteNdf(${n.id})">×</button>
            `:''}
          </td>
        </tr>
      `).join('')}</tbody>
    </table>`;
  }catch(e){document.getElementById('ndf-container').innerHTML='<div class="empty">Erreur : '+esc(e.message)+'</div>';}
}
async function submitNdf(id){
  if(!confirm('Soumettre cette note de frais à la comptabilité ?\nUne fois soumise, elle ne pourra plus être modifiée.'))return;
  try{await api('/api/coffre/notes-frais/'+id+'/soumettre',{method:'POST'});toast('Note soumise');loadNdf();}catch(e){toast(e.message,'error');}
}
async function deleteNdf(id){
  if(!confirm('Supprimer ce brouillon ?'))return;
  try{await api('/api/coffre/notes-frais/'+id,{method:'DELETE'});toast('Brouillon supprimé');loadNdf();}catch(e){toast(e.message,'error');}
}

function openNdfModal(){
  const back=document.createElement('div');back.className='modal-back';
  const today=new Date().toISOString().slice(0,10);
  back.innerHTML=`<div class="modal">
    <h3>Nouvelle note de frais</h3>
    <form id="ndf-form">
      <div class="row2">
        <div class="field"><label>Date du frais</label><input type="date" name="date_frais" value="${today}" required></div>
        <div class="field"><label>Montant TTC (€)</label><input type="number" step="0.01" min="0.01" name="montant_ttc" required placeholder="0,00"></div>
      </div>
      <div class="row2">
        <div class="field"><label>Catégorie</label><input type="text" name="categorie" placeholder="ex. Repas client, train Paris…" maxlength="80"></div>
        <div class="field"><label>TVA (optionnel)</label><input type="number" step="0.01" min="0" name="montant_tva" placeholder="0,00"></div>
      </div>
      <div class="field"><label>Description</label><textarea name="description" placeholder="Détails, contexte, participants…" maxlength="1000"></textarea></div>
      <div class="field">
        <label>Justificatif (PDF, JPG, PNG — 10 Mo max)</label>
        <label class="file-drop" id="drop-label">
          <span id="drop-txt">Choisir un fichier ou glisser-déposer</span>
          <input type="file" name="justificatif" id="ndf-file" accept="application/pdf,image/*" style="display:none">
        </label>
      </div>
      <div class="modal-actions">
        <button type="button" class="btn ghost" id="ndf-cancel">Annuler</button>
        <button type="submit" class="btn ghost" name="soumettre" value="0">Enregistrer brouillon</button>
        <button type="submit" class="btn" name="soumettre" value="1">Soumettre à la compta</button>
      </div>
    </form>
  </div>`;
  document.body.appendChild(back);
  const fileEl=back.querySelector('#ndf-file');
  const dropLbl=back.querySelector('#drop-label');
  const dropTxt=back.querySelector('#drop-txt');
  fileEl.addEventListener('change',()=>{
    if(fileEl.files.length){dropLbl.classList.add('has-file');dropTxt.textContent=fileEl.files[0].name;}
    else{dropLbl.classList.remove('has-file');dropTxt.textContent='Choisir un fichier ou glisser-déposer';}
  });
  back.querySelector('#ndf-cancel').onclick=()=>back.remove();
  back.onclick=(e)=>{if(e.target===back)back.remove();};
  const form=back.querySelector('#ndf-form');
  form.addEventListener('submit',async(e)=>{
    e.preventDefault();
    const btn=e.submitter;
    const fd=new FormData(form);
    fd.set('soumettre',btn && btn.value==='1'?'1':'0');
    try{
      const r=await fetch('/api/coffre/notes-frais',{method:'POST',credentials:'include',body:fd});
      if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||m;}catch{}throw new Error(m);}
      toast(btn.value==='1'?'Note soumise':'Brouillon enregistré');
      back.remove();
      loadNdf();
    }catch(e){toast(e.message,'error');}
  });
}

// Initial load
loadBulletins();
loadDocs();
loadNdf();
</script>
</body>
</html>
"""

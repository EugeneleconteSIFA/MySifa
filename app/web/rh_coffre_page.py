"""MySifa — Coffre RH (vue comptabilité).

Route : /rh/coffre — réservée aux rôles comptabilité et superadmin.
Dashboard mensuel des bulletins, upload ZIP, impression, validation NDF.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from config import APP_VERSION, ROLE_COMPTABILITE, ROLE_SUPERADMIN
from services.auth_service import get_current_user

router = APIRouter()


@router.get("/rh/coffre", response_class=HTMLResponse)
def rh_coffre_page(request: Request):
    try:
        u = get_current_user(request)
    except HTTPException as e:
        if e.status_code == 401:
            return RedirectResponse(url="/?next=/rh/coffre", status_code=302)
        raise
    if u.get("role") not in {ROLE_COMPTABILITE, ROLE_SUPERADMIN}:
        return RedirectResponse(url="/coffre", status_code=302)
    return HTMLResponse(content=RH_COFFRE_HTML.replace("__V_LABEL__", f"v{APP_VERSION}"))


RH_COFFRE_HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#0a0e17">
<title>Coffre RH — Comptabilité — MySifa</title>
<link rel="icon" type="image/png" sizes="192x192" href="/static/mys_icon_192.png">
<link rel="stylesheet" href="/static/mysifa_theme.css">
<link rel="stylesheet" href="/static/mysifa_user_chip.css">
<style>
:root{--bg:#0a0e17;--card:#111827;--border:#1e293b;--text:#f1f5f9;--text2:#cbd5e1;--muted:#94a3b8;--accent:#22d3ee;--accent-bg:rgba(34,211,238,.12);--ok:#34d399;--danger:#f87171;--warn:#fbbf24}
body.light{--bg:#f1f5f9;--card:#fff;--border:#e2e8f0;--text:#0f172a;--text2:#475569;--muted:#64748b;--accent:#0891b2;--accent-bg:rgba(8,145,178,.10);--ok:#059669;--danger:#dc2626;--warn:#d97706}
*{box-sizing:border-box}
body{margin:0;font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.wrap{max-width:1280px;margin:0 auto;padding:24px 20px 60px}
.head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:22px;flex-wrap:wrap}
.head h1{margin:0;font-size:22px;font-weight:800}
.head .sub{font-size:12px;color:var(--muted);margin-top:4px}
.head .back{display:inline-flex;align-items:center;gap:6px;padding:8px 14px;border-radius:10px;background:transparent;border:1px solid var(--border);color:var(--text2);text-decoration:none;font-size:12px;font-weight:600}
.head .back:hover{border-color:var(--accent);color:var(--accent)}
.tabs{display:flex;gap:6px;border-bottom:1px solid var(--border);margin-bottom:20px;overflow-x:auto}
.tab{padding:10px 16px;background:transparent;border:none;color:var(--muted);font-size:13px;font-weight:600;cursor:pointer;border-bottom:2px solid transparent;font-family:inherit;white-space:nowrap}
.tab:hover{color:var(--text2)}
.tab.active{color:var(--accent);border-bottom-color:var(--accent)}
.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:18px;margin-bottom:16px}
.card h2{margin:0 0 14px;font-size:15px;font-weight:700}
.toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:14px}
.toolbar select,.toolbar input{padding:8px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:13px;font-family:inherit;outline:none}
.toolbar select:focus,.toolbar input:focus{border-color:var(--accent)}
.btn{padding:9px 16px;border-radius:10px;border:none;background:var(--accent);color:#0a0e17;font-weight:700;font-size:13px;cursor:pointer;font-family:inherit;transition:filter .15s;display:inline-flex;align-items:center;gap:6px}
.btn:hover{filter:brightness(1.08)}
.btn.ghost{background:transparent;border:1px solid var(--border);color:var(--text2)}
.btn.ghost:hover{border-color:var(--accent);color:var(--accent);filter:none}
.btn.danger{background:var(--danger);color:#fff}
.btn.ok{background:var(--ok);color:#0a0e17}
.btn.small{padding:5px 10px;font-size:11px;border-radius:7px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;padding:10px 12px;background:var(--bg);color:var(--muted);font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--border);position:sticky;top:0;z-index:1}
td{padding:10px 12px;border-bottom:1px solid var(--border);color:var(--text2)}
tr:hover td{background:var(--accent-bg)}
.badge{display:inline-block;padding:2px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px}
.b-manquant{background:rgba(148,163,184,.15);color:var(--muted)}
.b-depose{background:rgba(251,191,36,.15);color:var(--warn)}
.b-distribue{background:rgba(34,211,238,.15);color:var(--accent)}
.b-consulte{background:rgba(52,211,153,.15);color:var(--ok)}
.statut{display:inline-block;padding:3px 8px;border-radius:6px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.4px}
.statut.brouillon{background:rgba(148,163,184,.15);color:var(--muted)}
.statut.soumise{background:rgba(251,191,36,.15);color:var(--warn)}
.statut.validee{background:rgba(34,211,238,.15);color:var(--accent)}
.statut.payee{background:rgba(52,211,153,.15);color:var(--ok)}
.statut.refusee{background:rgba(248,113,113,.15);color:var(--danger)}
.montant{font-family:'SF Mono','Consolas',monospace;font-weight:700;color:var(--text);text-align:right}
.upload-zone{border:2px dashed var(--border);border-radius:12px;padding:24px;text-align:center;transition:all .15s;cursor:pointer;background:var(--bg)}
.upload-zone:hover,.upload-zone.dragover{border-color:var(--accent);background:var(--accent-bg);color:var(--accent)}
.upload-zone .u-icon{font-size:32px;margin-bottom:8px;color:var(--accent)}
.upload-zone .u-hint{font-size:11px;color:var(--muted);margin-top:6px}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:16px}
.stat{background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 14px}
.stat-lbl{font-size:10px;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;font-weight:600}
.stat-val{font-size:22px;font-weight:800;color:var(--text);margin-top:4px}
.stat.warn .stat-val{color:var(--warn)}
.stat.ok .stat-val{color:var(--ok)}
.stat.danger .stat-val{color:var(--danger)}
.modal-back{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:200;display:flex;align-items:center;justify-content:center;padding:16px}
.modal{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:22px;max-width:520px;width:100%;max-height:90vh;overflow:auto}
.modal h3{margin:0 0 16px;font-size:16px;font-weight:700}
.field{margin-bottom:14px}
.field label{display:block;font-size:11px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.field input,.field select,.field textarea{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:10px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none}
.field input:focus,.field select:focus,.field textarea:focus{border-color:var(--accent)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.modal-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:18px}
.toast{position:fixed;top:24px;right:24px;background:var(--card);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:8px;padding:12px 18px;font-size:13px;color:var(--text);z-index:1000;box-shadow:0 10px 24px rgba(0,0,0,.3)}
.toast.error{border-left-color:var(--danger)}
.toast.ok{border-left-color:var(--ok)}
.upload-result{margin-top:14px;padding:14px;border-radius:10px;background:var(--bg);border:1px solid var(--border);font-size:12px;max-height:280px;overflow:auto}
.upload-result h4{margin:0 0 8px;font-size:12px;font-weight:700;color:var(--text)}
.upload-result ul{margin:0 0 12px;padding-left:20px}
.upload-result li{margin-bottom:3px;color:var(--text2)}
@media(max-width:768px){.wrap{padding:14px 12px 40px}.head h1{font-size:18px}.row2{grid-template-columns:1fr}table{font-size:12px}th,td{padding:6px 8px}}
</style>
</head>
<body>
<div class="wrap">
  <div class="head">
    <div>
      <h1>Coffre RH — Comptabilité</h1>
      <div class="sub">Dépôt bulletins · impression · validation notes de frais</div>
    </div>
    <a href="/" class="back">← Retour au portail</a>
  </div>

  <div class="tabs">
    <button type="button" class="tab active" data-tab="bulletins">Bulletins</button>
    <button type="button" class="tab" data-tab="ndf">Notes de frais</button>
  </div>

  <section id="panel-bulletins">
    <div class="card">
      <h2>Upload des bulletins mensuels</h2>
      <div class="toolbar">
        <label style="font-size:12px;color:var(--muted)">Année :</label>
        <select id="upl-annee"></select>
        <label style="font-size:12px;color:var(--muted)">Mois :</label>
        <select id="upl-mois"></select>
      </div>
      <label for="zip-file" class="upload-zone" id="zip-drop">
        <div class="u-icon">↑</div>
        <div><strong>Déposer un ZIP</strong> ou cliquer pour choisir</div>
        <div class="u-hint">Fichiers attendus : <code>Bulletin_YYYY_MM_NOM_Prenom.pdf</code></div>
      </label>
      <input type="file" id="zip-file" accept=".zip" style="display:none">
      <div id="upl-result"></div>
    </div>

    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:14px">
        <h2 style="margin:0">Dashboard mensuel</h2>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button type="button" class="btn ghost" onclick="openSingleUpload()">Upload individuel</button>
          <button type="button" class="btn ok" onclick="printAll(true)">Imprimer et marquer distribués</button>
          <button type="button" class="btn" onclick="printAll(false)">Imprimer tout (PDF)</button>
        </div>
      </div>
      <div class="stats" id="dash-stats"></div>
      <div style="overflow-x:auto"><div id="dash-container"></div></div>
    </div>
  </section>

  <section id="panel-ndf" style="display:none">
    <div class="card">
      <div class="toolbar">
        <label style="font-size:12px;color:var(--muted)">Statut :</label>
        <select id="ndf-statut">
          <option value="">Tous</option>
          <option value="soumise" selected>Soumises (à traiter)</option>
          <option value="validee">Validées</option>
          <option value="payee">Payées</option>
          <option value="refusee">Refusées</option>
          <option value="brouillon">Brouillons</option>
        </select>
        <label style="font-size:12px;color:var(--muted)">Année :</label>
        <select id="ndf-annee"><option value="">Toutes</option></select>
        <button type="button" class="btn ghost" onclick="exportNdf()">Export CSV</button>
      </div>
      <div id="ndf-container"></div>
    </div>
  </section>

  <div style="text-align:center;margin-top:30px;font-size:11px;color:var(--muted);font-family:'SF Mono','Consolas',monospace">MySifa __V_LABEL__</div>
</div>

<script>
const MOIS_LABELS=['','Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function fmtMontant(n){return (Number(n)||0).toLocaleString('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2})+' €';}
function fmtDate(s){if(!s)return '';const d=new Date(s.substr(0,10));return isNaN(d)?s:d.toLocaleDateString('fr-FR');}
function toast(msg,type){const t=document.createElement('div');t.className='toast '+(type==='error'?'error':'ok');t.textContent=msg;document.body.appendChild(t);setTimeout(()=>t.remove(),3500);}
async function api(url,opts){opts=opts||{};opts.credentials='include';const r=await fetch(url,opts);if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||j.message||m;}catch(e){}throw new Error(m);}return r.json();}

// Tabs
document.querySelectorAll('.tab').forEach(t=>{
  t.onclick=()=>{
    document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));
    t.classList.add('active');
    ['bulletins','ndf'].forEach(k=>{document.getElementById('panel-'+k).style.display=(k===t.dataset.tab?'':'none');});
    if(t.dataset.tab==='ndf')loadNdf();
  };
});

// ── Année/mois pickers ──
const now=new Date();const curYear=now.getFullYear();const curMonth=now.getMonth()+1;
['upl-annee'].forEach(id=>{
  const sel=document.getElementById(id);
  for(let y=curYear+1;y>=curYear-5;y--){sel.innerHTML+=`<option value="${y}" ${y===curYear?'selected':''}>${y}</option>`;}
});
{
  const sel=document.getElementById('upl-mois');
  for(let m=1;m<=12;m++){sel.innerHTML+=`<option value="${m}" ${m===curMonth?'selected':''}>${String(m).padStart(2,'0')} — ${MOIS_LABELS[m]}</option>`;}
}
{
  const sel=document.getElementById('ndf-annee');
  for(let y=curYear;y>=curYear-5;y--){sel.innerHTML+=`<option value="${y}">${y}</option>`;}
}

// ── Upload ZIP ──
const dropZone=document.getElementById('zip-drop');
const fileInput=document.getElementById('zip-file');
dropZone.onclick=()=>fileInput.click();
['dragenter','dragover'].forEach(ev=>dropZone.addEventListener(ev,e=>{e.preventDefault();dropZone.classList.add('dragover');}));
['dragleave','drop'].forEach(ev=>dropZone.addEventListener(ev,e=>{e.preventDefault();dropZone.classList.remove('dragover');}));
dropZone.addEventListener('drop',e=>{if(e.dataTransfer.files.length){uploadZip(e.dataTransfer.files[0]);}});
fileInput.addEventListener('change',()=>{if(fileInput.files.length)uploadZip(fileInput.files[0]);});

async function uploadZip(file){
  if(!file.name.toLowerCase().endsWith('.zip')){toast('ZIP requis','error');return;}
  const res=document.getElementById('upl-result');
  res.innerHTML='<div class="upload-result">Traitement en cours…</div>';
  const fd=new FormData();fd.append('file',file);
  try{
    const r=await fetch('/api/rh-coffre/upload-zip',{method:'POST',credentials:'include',body:fd});
    if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||m;}catch{}throw new Error(m);}
    const j=await r.json();
    res.innerHTML=`<div class="upload-result">
      <h4>Résultat : ${j.total_matched} bulletin(s) importé(s)${j.total_unmatched?' — '+j.total_unmatched+' non identifié(s)':''}</h4>
      ${j.matched.length?`<h4 style="margin-top:12px">Importés</h4><ul>${j.matched.map(x=>`<li>${esc(x.fichier)} → ${esc(x.employe)}</li>`).join('')}</ul>`:''}
      ${j.unmatched.length?`<h4 style="color:var(--warn)">Non identifiés (à uploader manuellement)</h4><ul>${j.unmatched.map(x=>`<li>${esc(x.fichier)} — ${esc(x.raison)}</li>`).join('')}</ul>`:''}
      ${j.skipped.length?`<h4 style="color:var(--muted)">Ignorés</h4><ul>${j.skipped.map(x=>`<li>${esc(x.fichier)} — ${esc(x.raison)}</li>`).join('')}</ul>`:''}
    </div>`;
    toast(`${j.total_matched} bulletin(s) importé(s)`);
    loadDashboard();
  }catch(e){res.innerHTML='<div class="upload-result" style="color:var(--danger)">Erreur : '+esc(e.message)+'</div>';toast(e.message,'error');}
  fileInput.value='';
}

// ── Dashboard mensuel ──
async function loadDashboard(){
  const annee=document.getElementById('upl-annee').value;
  const mois=document.getElementById('upl-mois').value;
  try{
    const j=await api(`/api/rh-coffre/dashboard?annee=${annee}&mois=${mois}`);
    const stats={total:j.lignes.length,depose:0,distribue:0,consulte:0,manquant:0};
    j.lignes.forEach(l=>{stats[l.statut==='déposé'?'depose':l.statut==='distribué'?'distribue':l.statut==='consulté'?'consulte':'manquant']++;});
    document.getElementById('dash-stats').innerHTML=`
      <div class="stat"><div class="stat-lbl">Salariés</div><div class="stat-val">${stats.total}</div></div>
      <div class="stat ${stats.manquant?'danger':''}"><div class="stat-lbl">Manquants</div><div class="stat-val">${stats.manquant}</div></div>
      <div class="stat warn"><div class="stat-lbl">Déposés</div><div class="stat-val">${stats.depose}</div></div>
      <div class="stat"><div class="stat-lbl">Distribués</div><div class="stat-val">${stats.distribue}</div></div>
      <div class="stat ok"><div class="stat-lbl">Consultés</div><div class="stat-val">${stats.consulte}</div></div>`;
    const c=document.getElementById('dash-container');
    if(!j.lignes.length){c.innerHTML='<p style="color:var(--muted);text-align:center;padding:30px 0">Aucun salarié actif.</p>';return;}
    c.innerHTML=`<table>
      <thead><tr><th>Salarié</th><th>Matricule</th><th>Statut</th><th>Fichier</th><th>Déposé le</th><th>Distribué le</th><th></th></tr></thead>
      <tbody>${j.lignes.map(l=>{
        const badgeClass={'manquant':'b-manquant','déposé':'b-depose','distribué':'b-distribue','consulté':'b-consulte'}[l.statut]||'b-manquant';
        return `<tr>
          <td><strong>${esc(l.nom)}</strong></td>
          <td>${esc(l.matricule||'—')}</td>
          <td><span class="badge ${badgeClass}">${esc(l.statut)}</span></td>
          <td>${l.document?esc(l.document.fichier_nom):'—'}</td>
          <td>${l.document?esc(fmtDate(l.document.uploaded_at)):'—'}</td>
          <td>${l.document && l.document.distribue_at?esc(fmtDate(l.document.distribue_at)):'—'}</td>
          <td style="text-align:right">${l.document?`<a class="btn ghost small" href="/api/coffre/documents/${l.document.id}/download" target="_blank" rel="noopener">Voir</a> <button class="btn ghost small" onclick="delDoc(${l.document.id})">×</button>`:''}</td>
        </tr>`;
      }).join('')}</tbody>
    </table>`;
  }catch(e){toast(e.message,'error');}
}
document.getElementById('upl-annee').addEventListener('change',loadDashboard);
document.getElementById('upl-mois').addEventListener('change',loadDashboard);

async function delDoc(id){
  if(!confirm('Supprimer ce document ? (soft delete — récupérable en DB)'))return;
  try{await api('/api/rh-coffre/documents/'+id,{method:'DELETE'});toast('Document supprimé');loadDashboard();}catch(e){toast(e.message,'error');}
}

function printAll(mark){
  const annee=document.getElementById('upl-annee').value;
  const mois=document.getElementById('upl-mois').value;
  if(mark && !confirm(`Imprimer et marquer tous les bulletins de ${MOIS_LABELS[+mois]} ${annee} comme distribués ?`))return;
  window.open(`/api/rh-coffre/print?annee=${annee}&mois=${mois}&mark_distribue=${mark?'1':'0'}`,'_blank');
  if(mark)setTimeout(loadDashboard,1500);
}

// ── Upload individuel ──
async function openSingleUpload(){
  let employes=[];
  try{const j=await api('/api/rh-coffre/employes');employes=j.employes;}catch(e){toast(e.message,'error');return;}
  const back=document.createElement('div');back.className='modal-back';
  back.innerHTML=`<div class="modal">
    <h3>Upload individuel</h3>
    <form id="s-form">
      <div class="field"><label>Salarié</label><select name="employe_user_id" required>${employes.map(e=>`<option value="${e.id}">${esc(e.nom)}${e.matricule?' — '+esc(e.matricule):''}</option>`).join('')}</select></div>
      <div class="field"><label>Type</label><select name="type" required>
        <option value="bulletin_paie">Bulletin de paie</option>
        <option value="contrat">Contrat</option>
        <option value="attestation">Attestation</option>
        <option value="autre">Autre</option>
      </select></div>
      <div class="row2">
        <div class="field"><label>Année</label><input type="number" name="annee" min="2000" max="2100" value="${curYear}"></div>
        <div class="field"><label>Mois</label><input type="number" name="mois" min="1" max="12" value="${curMonth}"></div>
      </div>
      <div class="field"><label>Libellé (optionnel)</label><input type="text" name="libelle" placeholder="ex. Avenant contrat"></div>
      <div class="field"><label>Fichier (25 Mo max)</label><input type="file" name="fichier" required accept=".pdf,image/*"></div>
      <div class="modal-actions">
        <button type="button" class="btn ghost" onclick="this.closest('.modal-back').remove()">Annuler</button>
        <button type="submit" class="btn">Envoyer</button>
      </div>
    </form>
  </div>`;
  document.body.appendChild(back);
  back.querySelector('#s-form').addEventListener('submit',async e=>{
    e.preventDefault();
    const fd=new FormData(e.target);
    try{
      const r=await fetch('/api/rh-coffre/upload-single',{method:'POST',credentials:'include',body:fd});
      if(!r.ok){let m='Erreur';try{const j=await r.json();m=j.detail||m;}catch{}throw new Error(m);}
      toast('Document ajouté');back.remove();loadDashboard();
    }catch(e){toast(e.message,'error');}
  });
}

// ── Notes de frais ──
async function loadNdf(){
  const statut=document.getElementById('ndf-statut').value;
  const annee=document.getElementById('ndf-annee').value;
  try{
    const j=await api(`/api/rh-coffre/ndf?statut=${statut}&annee=${annee}`);
    const c=document.getElementById('ndf-container');
    if(!j.notes.length){c.innerHTML='<p style="color:var(--muted);text-align:center;padding:30px 0">Aucune note de frais.</p>';return;}
    c.innerHTML=`<table>
      <thead><tr><th>Salarié</th><th>Date</th><th>Catégorie</th><th>Description</th><th style="text-align:right">Montant</th><th>Statut</th><th>Actions</th></tr></thead>
      <tbody>${j.notes.map(n=>`
        <tr>
          <td><strong>${esc(n.employe_nom)}</strong><br><span style="font-size:11px;color:var(--muted)">${esc(n.matricule||'')}</span></td>
          <td>${esc(fmtDate(n.date_frais))}</td>
          <td>${esc(n.categorie||'—')}</td>
          <td style="max-width:260px">${esc((n.description||'').slice(0,90))}${(n.description||'').length>90?'…':''}${n.motif_refus?'<div style="font-size:11px;color:var(--danger);margin-top:3px">Refus : '+esc(n.motif_refus)+'</div>':''}</td>
          <td class="montant">${fmtMontant(n.montant_ttc)}${n.montant_tva?`<div style="font-size:10px;color:var(--muted);font-weight:400">TVA ${fmtMontant(n.montant_tva)}</div>`:''}</td>
          <td><span class="statut ${esc(n.statut)}">${esc(n.statut)}</span></td>
          <td style="white-space:nowrap;text-align:right">
            ${n.justificatif_nom?`<a class="btn ghost small" href="/api/coffre/notes-frais/${n.id}/justificatif" target="_blank" rel="noopener">Voir</a>`:''}
            ${n.statut==='soumise'||n.statut==='refusee'?`<button class="btn small" onclick="validerNdf(${n.id})">Valider</button>`:''}
            ${n.statut==='soumise'?`<button class="btn ghost small" onclick="refuserNdf(${n.id})">Refuser</button>`:''}
            ${n.statut==='validee'?`<button class="btn ok small" onclick="marquerPayee(${n.id})">Marquer payée</button>`:''}
          </td>
        </tr>
      `).join('')}</tbody>
    </table>`;
  }catch(e){document.getElementById('ndf-container').innerHTML='<p style="color:var(--danger)">Erreur : '+esc(e.message)+'</p>';}
}
document.getElementById('ndf-statut').addEventListener('change',loadNdf);
document.getElementById('ndf-annee').addEventListener('change',loadNdf);

async function validerNdf(id){
  if(!confirm('Valider cette note de frais ?'))return;
  try{await api('/api/rh-coffre/ndf/'+id+'/valider',{method:'POST'});toast('Note validée');loadNdf();}catch(e){toast(e.message,'error');}
}
async function refuserNdf(id){
  const motif=prompt('Motif du refus (obligatoire) :');
  if(!motif||!motif.trim())return;
  try{
    await api('/api/rh-coffre/ndf/'+id+'/refuser',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({motif:motif.trim()})});
    toast('Note refusée');loadNdf();
  }catch(e){toast(e.message,'error');}
}
async function marquerPayee(id){
  if(!confirm('Marquer cette note comme payée ? (à faire après avoir effectué le virement)'))return;
  try{await api('/api/rh-coffre/ndf/'+id+'/marquer-payee',{method:'POST'});toast('Note marquée payée');loadNdf();}catch(e){toast(e.message,'error');}
}
function exportNdf(){
  const statut=document.getElementById('ndf-statut').value;
  const annee=document.getElementById('ndf-annee').value;
  window.open(`/api/rh-coffre/ndf/export?statut=${statut}&annee=${annee}`,'_blank');
}

// Initial load
loadDashboard();
</script>
</body>
</html>
"""

"""MyCompta — assets CSS/JS (injectés dans app/web/html.py). Pas de route FastAPI ici."""

COMPTA_MAIN_CSS = r"""
/* MyCompta — barre d'ajout (acheteurs / comptes) */
.compta-add-bar{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:20px;margin-bottom:16px}
.compta-add-bar h3{font-size:15px;font-weight:700;color:var(--text);margin:0 0 14px}
.compta-add-bar-meta{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.compta-add-bar-meta .hint{font-size:12px;color:var(--muted)}
.compta-add-bar-fields{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px}
.compta-add-bar-fields label{display:block;font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:4px}
.compta-add-bar-fields input{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:12px 16px;color:var(--text);font-size:14px;font-family:inherit;outline:none;transition:border-color .15s,box-shadow .15s}
.compta-add-bar-fields input:focus{border-color:var(--accent);box-shadow:0 0 0 3px rgba(34,211,238,.12)}
body.light .compta-add-bar-fields input:focus{box-shadow:0 0 0 3px rgba(8,145,178,.12)}
.compta-add-bar-actions{display:flex;gap:10px;margin-top:14px;align-items:center}
"""

COMPTA_MAIN_JS = r"""
// ── MyCompta (placeholder v0) ─────────────────────────────────────
// ══════════════════════════════════════════════════════════════════
// ── PAIE (onglet MyCompta) ────────────────────────────────────────
// ══════════════════════════════════════════════════════════════════
const PAIE_MOIS_FR=['','Janvier','Février','Mars','Avril','Mai','Juin','Juillet','Août','Septembre','Octobre','Novembre','Décembre'];

const PAIE_SECTIONS=[
  {title:'📋 Contrat & Salaire',fields:[
    {key:'matricule',       label:'Matricule',          type:'text',   fixed:true},
    {key:'contrat_type',    label:'Type de contrat',    type:'select', fixed:true, opts:['CDI','CDD','Intérim','Stage','Apprentissage']},
    {key:'date_debut',      label:'Date de début',      type:'date',   fixed:true},
    {key:'date_fin',        label:'Date de fin',        type:'date',   fixed:true},
    {key:'nb_heures_base',  label:'Heures de base',     type:'number', fixed:true, step:'0.01'},
    {key:'taux_horaire',    label:'Taux horaire (€)',   type:'number', fixed:true, step:'0.01'},
    {key:'salaire_mensuel', label:'Salaire mensuel (€)',type:'number', fixed:true, step:'0.01'},
    {key:'mutuelle',        label:'Mutuelle',           type:'select', fixed:true, opts:['Non','Oui']},
    {key:'avantage_voiture',label:'Avantage voiture (€)',type:'number',fixed:true, step:'0.01'},
    {key:'prime_anciennete',label:'Prime ancienneté (%)',type:'number',fixed:true, step:'0.01'},
  ]},
  {title:'⏱ Heures & Compteurs',fields:[
    {key:'compteur_hs_m1',              label:'Compteur HS M-1',        type:'text'},
    {key:'nb_heures_payer',             label:'Nb heures à payer',      type:'number',step:'0.01'},
    {key:'heures_nuit',                 label:'Heures de nuit',         type:'text'},
    {key:'heures_nuit_ferie',           label:'Nuit férié',             type:'text'},
    {key:'heures_nuit_dimanche',        label:'Nuit dimanche',          type:'text'},
    {key:'heures_nuit_dimanche_ferie',  label:'Nuit dim. férié',        type:'text'},
    {key:'heures_sup_25',               label:'Heures sup 25%',         type:'text'},
    {key:'heures_sup_50',               label:'Heures sup 50%',         type:'text'},
    {key:'heures_sup_nuit',             label:'Heures sup nuit',        type:'text'},
    {key:'heures_ferie',                label:'Heures j. férié (+150%)',type:'text'},
  ]},
  {title:'💰 Primes & Commissions',fields:[
    {key:'augmentation_salaire', label:'Augmentation salaire (€)',  type:'number',step:'0.01'},
    {key:'commissions_ventes',   label:'Commissions ventes (€)',    type:'number',step:'0.01'},
    {key:'prime_objectifs',      label:"Prime d'objectifs (€)",     type:'number',step:'0.01'},
    {key:'prime_inflation',      label:'Prime inflation (€)',       type:'number',step:'0.01'},
    {key:'prime_exceptionnelle', label:'Prime exceptionnelle (€)',  type:'number',step:'0.01'},
    {key:'prime_equipe',         label:'Prime équipe (€)',          type:'number',step:'0.01'},
    {key:'panier',               label:'Panier (6,47€/j)',          type:'number',step:'0.01'},
    {key:'solde_tout_compte',    label:'Solde tout compte',         type:'select', opts:['','Oui','Non']},
  ]},
  {title:'🏖 Absences',fields:[
    {key:'absence_heures',          label:'Absence (heures)',          type:'text'},
    {key:'absence_maladie_heures',  label:'Maladie (heures)',          type:'text'},
    {key:'absence_maladie_jours',   label:'Maladie (jours)',           type:'text'},
    {key:'absence_deces_mariage',   label:'Décès / Mariage',          type:'text'},
    {key:'absence_cp_heures',       label:'Congés payés (h)',          type:'text'},
    {key:'absence_cp_jours',        label:'Congés payés (j)',          type:'text'},
    {key:'date_conges_payes',       label:'Dates des CP',              type:'text'},
    {key:'absence_rtt',             label:'RTT',                       type:'text'},
    {key:'absence_css_heures',      label:'Congés sans solde (h)',     type:'text'},
    {key:'absence_css_jours',       label:'Congés sans solde (j)',     type:'text'},
    {key:'absence_non_justifie_h',  label:'Non justifiée (h)',         type:'text'},
    {key:'absence_non_justifie_j',  label:'Non justifiée (j)',         type:'text'},
    {key:'absence_justifiee_np_h',  label:'Justifiée non payée (h)',   type:'text'},
    {key:'absence_justifiee_np_j',  label:'Justifiée non payée (j)',   type:'text'},
    {key:'absence_at_heures',       label:'AT (heures)',               type:'text'},
    {key:'absence_at_jours',        label:'AT (jours)',                type:'text'},
    {key:'mi_temps_therapeutique',  label:'Mi-temps thérapeutique',   type:'text'},
    {key:'absence_chomage_partiel', label:'Chômage partiel',          type:'text'},
    {key:'absence_conge_parentale', label:'Congé parental',           type:'text'},
  ]},
  {title:'💳 Frais & Divers',fields:[
    {key:'frais_pro',           label:'Frais pro (€)',            type:'number',step:'0.01'},
    {key:'frais_transport',     label:'Remb. transport (€)',      type:'number',step:'0.01'},
    {key:'pret_sifa',           label:'Prêt SIFA (€)',            type:'number',step:'0.01'},
    {key:'atd',                 label:'ATD (€)',                  type:'number',step:'0.01'},
    {key:'acompte_exceptionnel',label:'Acompte exceptionnel (€)', type:'number',step:'0.01'},
  ]},
  {title:'📝 Information',fields:[
    {key:'information',label:'Note libre',type:'textarea',full:true},
  ]},
];

async function paieLoadEmployes(){
  if(S.paieEmpLoaded) return;
  try{
    const d=await api('/api/paie/employes');
    S.paieEmployes=d.employes||[];
    S.paieEmpLoaded=true;
    render();
  }catch(e){toast('Erreur chargement employés: '+e.message,'error');}
}

async function paieLoadVars(){
  const pk=S.paieAnnee+'_'+S.paieMois;
  if(S.paieVarsCache[pk]!==undefined) return;
  S.paieVarsCache[pk]={};
  try{
    const d=await api('/api/paie/variables/'+S.paieAnnee+'/'+S.paieMois);
    S.paieVarsCache[pk]=d.variables||{};
  }catch(e){}
}

function paieGetFixed(userId){
  const pk=S.paieAnnee+'_'+S.paieMois;
  // Priorité aux données fixes historiques pour ce mois, sinon les données globales
  const cached=((S.paieVarsCache[pk]||{})[String(userId)]||{}).fixed||{};
  const e=S.paieEmployes.find(x=>x.user_id===userId)||{};
  return {
    matricule:cached.matricule??e.matricule,
    contrat_type:cached.contrat_type??e.contrat_type??'CDI',
    date_debut:cached.date_debut??e.date_debut,
    date_fin:cached.date_fin??e.date_fin,
    nb_heures_base:cached.nb_heures_base??e.nb_heures_base,
    taux_horaire:cached.taux_horaire??e.taux_horaire,
    salaire_mensuel:cached.salaire_mensuel??e.salaire_mensuel,
    prime_anciennete:cached.prime_anciennete??e.prime_anciennete,
    mutuelle:cached.mutuelle??e.mutuelle??'Non',
    avantage_voiture:cached.avantage_voiture??e.avantage_voiture
  };
}
function paieGetVar(userId){
  const pk=S.paieAnnee+'_'+S.paieMois;
  const cached=((S.paieVarsCache[pk]||{})[String(userId)]||{}).data||{};
  return {...cached,...(S.paiePendingVar[userId]||{})};
}

async function paieSaveEmp(userId,btnEl){
  if(btnEl){btnEl.disabled=true;btnEl.textContent='Enregistrement…';}
  try{
    const isReadonly=S.paieMonthReadonly;
    
    // Si mois passé, ne pas sauvegarder les données fixes (elles sont historiques)
    if(!isReadonly){
      const fixPending=S.paiePendingFixed[userId]||{};
      const emp=S.paieEmployes.find(x=>x.user_id===userId)||{};
      const fixBody={
        matricule:fixPending.matricule??emp.matricule,
        contrat_type:fixPending.contrat_type??emp.contrat_type,
        date_debut:fixPending.date_debut??emp.date_debut,
        date_fin:fixPending.date_fin??emp.date_fin,
        nb_heures_base:fixPending.nb_heures_base??emp.nb_heures_base,
        taux_horaire:fixPending.taux_horaire??emp.taux_horaire,
        salaire_mensuel:fixPending.salaire_mensuel??emp.salaire_mensuel,
        prime_anciennete:fixPending.prime_anciennete??emp.prime_anciennete,
        mutuelle:fixPending.mutuelle??emp.mutuelle,
        avantage_voiture:fixPending.avantage_voiture??emp.avantage_voiture,
      };
      await api('/api/paie/employes/'+userId+'/fixed',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify(fixBody)});
      Object.assign(emp,fixBody);
    }
    
    // Sauvegarder toujours les variables (même pour mois passés si on veut corriger une erreur)
    const varData=paieGetVar(userId);
    await api('/api/paie/variables/'+S.paieAnnee+'/'+S.paieMois+'/'+userId,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({data:varData})});
    const pk=S.paieAnnee+'_'+S.paieMois;
    if(!S.paieVarsCache[pk])S.paieVarsCache[pk]={};
    S.paieVarsCache[pk][String(userId)]={data:varData};
    
    delete S.paiePendingFixed[userId];
    delete S.paiePendingVar[userId];
    toast('Enregistré','success');
    if(btnEl){btnEl.disabled=false;btnEl.textContent='✅ Enregistré';btnEl.className='paie-svbtn saved';setTimeout(()=>{if(btnEl){btnEl.textContent='💾 Enregistrer';btnEl.className='paie-svbtn';}},2500);}
    render();
  }catch(e){
    toast('Erreur: '+e.message,'error');
    if(btnEl){btnEl.disabled=false;btnEl.textContent='💾 Enregistrer';}
  }
}

async function paieExport(){
  S.paieExporting=true;render();
  try{
    const r=await fetch('/api/paie/export/'+S.paieAnnee+'/'+S.paieMois,{credentials:'include'});
    if(!r.ok)throw new Error('Erreur '+r.status);
    const blob=await r.blob();
    const a=document.createElement('a');
    a.href=URL.createObjectURL(blob);
    a.download='paie_'+S.paieAnnee+'_'+String(S.paieMois).padStart(2,'0')+'_'+PAIE_MOIS_FR[S.paieMois]+'.xlsx';
    a.click();
    toast('Export téléchargé','success');
  }catch(e){toast('Export échoué: '+e.message,'error');}
  S.paieExporting=false;render();
}

async function paieShowHistory(){
  S.paieShowHist=true;S.paieHistData=null;render();
  try{
    const d=await api('/api/paie/historique');
    S.paieHistData=d.periodes||[];
    render();
  }catch(e){S.paieHistData=[];render();}
}

function paieChangePeriod(delta){
  let m=S.paieMois+delta,y=S.paieAnnee;
  if(m<1){m=12;y--;}if(m>12){m=1;y++;}
  S.paieMois=m;S.paieAnnee=y;
  S.paiePendingVar={};
  paieLoadVars().then(()=>render());
}

function renderPaieForm(userId){
  const emp=S.paieEmployes.find(x=>x.user_id===userId);
  if(!emp)return h('div',{className:'paie-ph'},'Employé introuvable');
  const varD=paieGetVar(userId);
  const fixD=paieGetFixed(userId);
  const wrap=h('div',null);
  // Header
  const btnSave=h('button',{className:'paie-svbtn'});
  btnSave.textContent='💾 Enregistrer';
  btnSave.onclick=()=>paieSaveEmp(userId,btnSave);
  const meta=h('div',{className:'paie-emp-hdr-meta'});
  [emp.contrat_type||'CDI', emp.salaire_mensuel?Number(emp.salaire_mensuel).toLocaleString('fr-FR')+' €':null, emp.date_debut?'Depuis '+emp.date_debut:null].filter(Boolean)
    .forEach(t=>{const b=h('span',{className:'paie-badge'});b.textContent=t;meta.appendChild(b);});
  const nm=h('div',{className:'paie-emp-hdr-name'});nm.textContent=emp.nom_complet||'';
  const nmWrap=h('div',null,nm,meta);
  const hdr=h('div',{className:'paie-emp-hdr'},nmWrap,btnSave);
  wrap.appendChild(hdr);
  // Sections
  PAIE_SECTIONS.forEach(sec=>{
    const sEl=h('div',{className:'paie-sec'});
    const tEl=h('div',{className:'paie-sec-title'});tEl.textContent=sec.title;sEl.appendChild(tEl);
    const grid=h('div',{className:'paie-fgrid'});
    sec.fields.forEach(f=>{
      const cell=h('div',{className:'paie-f'+(f.full?' full':'')});
      const lbl=h('div',{className:'paie-flbl'});lbl.textContent=f.label;cell.appendChild(lbl);
      const val=f.fixed?(fixD[f.key]??''):(varD[f.key]??'');
      let inp;
      if(f.type==='select'){
        inp=document.createElement('select');
        (f.opts||[]).forEach(o=>{const op=document.createElement('option');op.value=o;op.textContent=o;if(String(val)===o)op.selected=true;inp.appendChild(op);});
      }else if(f.type==='textarea'){
        inp=document.createElement('textarea');inp.value=val||'';
      }else{
        inp=document.createElement('input');inp.type=f.type||'text';if(f.step)inp.step=f.step;inp.value=val!=null?val:'';
      }
      inp.addEventListener('input',()=>{
        if(f.fixed){if(!S.paiePendingFixed[userId])S.paiePendingFixed[userId]={};S.paiePendingFixed[userId][f.key]=inp.value;}
        else{if(!S.paiePendingVar[userId])S.paiePendingVar[userId]={};S.paiePendingVar[userId][f.key]=inp.value;}
      });
      cell.appendChild(inp);grid.appendChild(cell);
    });
    sEl.appendChild(grid);wrap.appendChild(sEl);
  });
  return wrap;
}

function renderPaieEmployeeList(){
  const tokens=(S.paieEmpSearch||'').toLowerCase().trim().split(/\s+/).filter(Boolean);
  const scoreM=(hay,toks)=>{if(!toks.length)return 1;const h2=(hay||'').toLowerCase();let s=0;for(const t of toks)if(h2.includes(t))s+=(h2.startsWith(t)?2:1);return s;};
  let list=S.paieEmployes.filter(e=>{if(!tokens.length)return true;return scoreM([e.nom_complet,e.contrat_type,e.email].join(' '),tokens)>0;})
    .sort((a,b)=>{if(!tokens.length)return(a.nom_complet||'').localeCompare(b.nom_complet||'','fr');const sa=scoreM([a.nom_complet,a.contrat_type].join(' '),tokens);const sb=scoreM([b.nom_complet,b.contrat_type].join(' '),tokens);return sb-sa;});
  const ul=h('div',{className:'paie-emp-list'});
  if(!list.length){const em=h('div',{style:{padding:'12px',fontSize:'11px',color:'var(--muted)',textAlign:'center'}});em.textContent='Aucun résultat';ul.appendChild(em);return ul;}
  list.forEach(emp=>{
    const div=h('div',{className:'paie-emp-item'+(emp.user_id===S.paieCurrentEmpId?' active':'')});
    const dirty=!!(S.paiePendingVar[emp.user_id]||S.paiePendingFixed[emp.user_id]);
    const nm=h('div',{className:'paie-emp-name'});nm.textContent=emp.nom_complet||(emp.nom+' '+emp.prenom);
    if(dirty){const dot=h('span',{className:'paie-unsaved'});nm.appendChild(dot);}
    const sub=h('div',{className:'paie-emp-sub'});sub.textContent=(emp.contrat_type||'CDI')+' · '+(emp.email||'');
    div.appendChild(nm);div.appendChild(sub);
    div.onclick=()=>{S.paieCurrentEmpId=emp.user_id;render();};
    ul.appendChild(div);
  });
  return ul;
}

function renderPaieTab(){
  // Load data if needed
  if(!S.paieEmpLoaded){paieLoadEmployes();return h('div',{className:'paie-ph'},'Chargement…');}

  // Déterminer le type de mois (passé, en cours, futur)
  const now=new Date();
  const currentYear=now.getFullYear();
  const currentMonth=now.getMonth()+1;
  let monthStatus='';
  let monthStatusColor='';
  if(S.paieAnnee<currentYear||(S.paieAnnee===currentYear&&S.paieMois<currentMonth)){
    monthStatus='Mois passé - Lecture seule';
    monthStatusColor='var(--warn)';
  }else if(S.paieAnnee===currentYear&&S.paieMois===currentMonth){
    monthStatus='Mois en cours';
    monthStatusColor='var(--ok)';
  }else{
    monthStatus='Mois futur';
    monthStatusColor='var(--accent)';
  }
  S.paieMonthStatus=monthStatus;
  S.paieMonthReadonly=(monthStatus==='Mois passé - Lecture seule');

  // Period bar
  const periodStr=PAIE_MOIS_FR[S.paieMois]+' '+S.paieAnnee;
  const prevBtn=h('button',{className:'paie-pbtn',onClick:()=>paieChangePeriod(-1)});prevBtn.textContent='‹';
  const nextBtn=h('button',{className:'paie-pbtn',onClick:()=>paieChangePeriod(+1)});nextBtn.textContent='›';
  const lbl=h('div',{className:'paie-plbl'});lbl.textContent=periodStr;
  const histBtn=h('button',{className:'paie-hist-btn',onClick:paieShowHistory});histBtn.innerHTML=icon('clock',13)+' Historique';
  const xBtn=h('button',{className:'paie-xbtn',disabled:S.paieExporting,onClick:paieExport});
  xBtn.innerHTML=icon('download',13)+' Exporter Excel';
  if(S.paieExporting)xBtn.innerHTML='Génération…';
  const periodBar=h('div',{className:'paie-period-bar'},h('div',{className:'paie-period-nav'},prevBtn,lbl,nextBtn),histBtn,xBtn);

  // Employee list panel
  const srch=h('input',{type:'search',placeholder:'Rechercher un employé…',style:{width:'100%',padding:'7px 10px',background:'var(--bg)',border:'1.5px solid var(--border)',borderRadius:'8px',color:'var(--text)',fontSize:'12px',fontFamily:'inherit',outline:'none'}});
  srch.value=S.paieEmpSearch||'';
  srch.addEventListener('input',()=>{S.paieEmpSearch=srch.value;const list=srch.closest('.paie-layout').querySelector('.paie-emp-list');if(list){const ul=renderPaieEmployeeList();list.replaceWith(ul);}});
  const hint=h('div',{className:'paie-emp-hint'});hint.textContent='Cherchez par nom, prénom ou contrat';
  const empHead=h('div',{className:'paie-emp-head'},srch,hint);
  const empList=renderPaieEmployeeList();
  const empPanel=h('div',{className:'paie-emp-panel'},empHead,empList);

  // Right column
  const formScroll=h('div',{className:'paie-form-scroll'});
  if(S.paieCurrentEmpId){
    formScroll.appendChild(renderPaieForm(S.paieCurrentEmpId));
  }else{
    const ph=h('div',{className:'paie-ph'});ph.textContent='← Sélectionnez un employé';
    formScroll.appendChild(ph);
  }
  const formCol=h('div',{className:'paie-form-col'},periodBar,formScroll);
  const layout=h('div',{className:'paie-layout'},empPanel,formCol);

  // History modal
  if(S.paieShowHist){
    const histEl=h('div',{className:'paie-hist-modal'});
    histEl.onclick=(e)=>{if(e.target===histEl){S.paieShowHist=false;render();}};
    const card=h('div',{className:'paie-hist-card'});
    const htit=h('div',{style:{fontSize:'14px',fontWeight:800,marginBottom:'12px'}});htit.textContent='📋 Historique des périodes';
    const hlist=h('div',{style:{overflowY:'auto',flex:1}});
    if(S.paieHistData===null){const ld=h('div',{style:{padding:'12px',color:'var(--muted)',fontSize:'12px'}});ld.textContent='Chargement…';hlist.appendChild(ld);}
    else if(!S.paieHistData.length){const em=h('div',{style:{padding:'12px',color:'var(--muted)',fontSize:'12px'}});em.textContent='Aucune période enregistrée.';hlist.appendChild(em);}
    else{S.paieHistData.forEach(p=>{const active=p.annee===S.paieAnnee&&p.mois===S.paieMois;const it=h('div',{className:'paie-hist-item'+(active?' active':'')});const ilab=h('div');const iname=h('div',{style:{fontSize:'13px',fontWeight:700,color:'var(--accent)'}});iname.textContent=p.mois_label+' '+p.annee;const isub=h('div',{style:{fontSize:'11px',color:'var(--muted)'}});isub.textContent=p.nb_employes+' employé(s) · '+(p.last_update||'').slice(0,10);ilab.append(iname,isub);const iact=h('span',{style:{fontSize:'11px',color:'var(--accent)'}});iact.textContent=active?'✓ Période actuelle':'→ Aller';it.append(ilab,iact);it.onclick=()=>{S.paieAnnee=p.annee;S.paieMois=p.mois;S.paiePendingVar={};S.paieShowHist=false;paieLoadVars().then(()=>render());};hlist.appendChild(it);});}
    const closeBtn=h('button',{style:{marginTop:'12px',padding:'9px',borderRadius:'8px',border:'1px solid var(--border)',background:'transparent',color:'var(--text2)',cursor:'pointer',fontFamily:'inherit',fontSize:'12px',width:'100%'},onClick:()=>{S.paieShowHist=false;render();}});closeBtn.textContent='Fermer';
    card.append(htit,hlist,closeBtn);histEl.appendChild(card);
    return h('div',null,layout,histEl);
  }
  return layout;
}

function closeComptaAcheteurModal(){set({comptaEditAcheteurId:null});}
function closeComptaCompteModal(){set({comptaEditCompteId:null});}
function closeComptaBanqueModal(){set({comptaEditBanqueId:null});}

function renderComptaBanqueModal(){
  const editId=S.comptaEditBanqueId;
  if(!editId)return null;
  const cur=(S.comptaBanques||[]).find(x=>String(x.id)===String(editId));
  if(!cur)return null;
  const codeI=h('input',{type:'text',placeholder:'Code vendeur (ex: 98, 100)',value:cur.code_vendeur||''});
  const numI=h('input',{type:'text',placeholder:'Numéro de compte',value:cur.numero_compte||''});
  const libI=h('input',{type:'text',placeholder:'Libellé (optionnel)',value:cur.libelle||''});
  const overlay=h('div',{className:'add-row-modal',style:{zIndex:12000}});
  overlay.addEventListener('click',e=>{if(e.target===overlay)closeComptaBanqueModal();});
  const form=h('div',{className:'add-row-form',style:{maxWidth:'560px'},onClick:e=>e.stopPropagation()},
    h('button',{type:'button',className:'add-row-close',onClick:closeComptaBanqueModal},'×'),
    h('h3',null,'Modifier un code de banque'),
    h('div',{className:'form-row'},
      h('div',null,h('label',null,'Code vendeur'),codeI),
      h('div',null,h('label',null,'Numéro de compte'),numI)
    ),
    h('div',{className:'form-row'},
      h('div',{style:{gridColumn:'span 2'}},h('label',null,'Libellé'),libI)
    ),
    h('div',{className:'form-actions'},
      h('button',{type:'button',className:'btn-ghost',onClick:closeComptaBanqueModal},'Annuler'),
      h('button',{type:'button',className:'btn-sm',onClick:()=>{
        const payload={code_vendeur:codeI.value,numero_compte:numI.value,libelle:libI.value||null};
        if(!payload.code_vendeur||!payload.numero_compte){toast('Code vendeur et numéro de compte obligatoires','error');return;}
        comptaUpdateBanque(editId,payload);
      }},'Enregistrer')
    )
  );
  overlay.appendChild(form);
  return overlay;
}

function renderComptaAcheteurModal(){
  const editId=S.comptaEditAcheteurId;
  if(!editId)return null;
  const cur=(S.comptaAcheteurs||[]).find(x=>String(x.id)===String(editId));
  if(!cur)return null;
  const codeI=h('input',{type:'text',placeholder:'Code vendeur (optionnel)',value:cur.code_vendeur||''});
  const numCompteI=h('input',{type:'text',placeholder:'Numéro de compte',value:cur.identifiant||''});
  const rsI=h('input',{type:'text',placeholder:'Raison sociale',value:cur.raison_sociale||''});
  const overlay=h('div',{className:'add-row-modal',style:{zIndex:12000}});
  overlay.addEventListener('click',e=>{if(e.target===overlay)closeComptaAcheteurModal();});
  const form=h('div',{className:'add-row-form',style:{maxWidth:'560px'},onClick:e=>e.stopPropagation()},
    h('button',{type:'button',className:'add-row-close',onClick:closeComptaAcheteurModal},'×'),
    h('h3',null,'Modifier un acheteur'),
    h('div',{className:'form-row'},
      h('div',null,h('label',null,'Code vendeur'),codeI),
      h('div',null,h('label',null,'Numéro de compte'),numCompteI)
    ),
    h('div',{className:'form-row'},
      h('div',{style:{gridColumn:'span 2'}},h('label',null,'Raison sociale'),rsI)
    ),
    h('div',{className:'form-actions'},
      h('button',{type:'button',className:'btn-ghost',onClick:closeComptaAcheteurModal},'Annuler'),
      h('button',{type:'button',className:'btn-sm',onClick:()=>{
        const payload={code_vendeur:codeI.value||null,identifiant:numCompteI.value,raison_sociale:rsI.value};
        if(!payload.identifiant||!payload.raison_sociale){toast('Numéro de compte et raison sociale obligatoires','error');return;}
        comptaUpdateAcheteur(editId,payload);
      }},'Enregistrer')
    )
  );
  overlay.appendChild(form);
  return overlay;
}

function renderComptaCompteModal(){
  const editId=S.comptaEditCompteId;
  if(!editId)return null;
  const cur=(S.comptaComptes||[]).find(x=>String(x.id)===String(editId));
  if(!cur)return null;
  const libI=h('input',{type:'text',placeholder:'Libellé condensé',value:cur.libelle_condense||''});
  const numI=h('input',{type:'text',placeholder:'Numéro de compte',value:cur.numero_compte||''});
  const overlay=h('div',{className:'add-row-modal',style:{zIndex:12000}});
  overlay.addEventListener('click',e=>{if(e.target===overlay)closeComptaCompteModal();});
  const form=h('div',{className:'add-row-form',style:{maxWidth:'560px'},onClick:e=>e.stopPropagation()},
    h('button',{type:'button',className:'add-row-close',onClick:closeComptaCompteModal},'×'),
    h('h3',null,'Modifier un compte'),
    h('div',{className:'form-row'},
      h('div',null,h('label',null,'Libellé condensé'),libI),
      h('div',null,h('label',null,'Numéro de compte'),numI)
    ),
    h('div',{className:'form-actions'},
      h('button',{type:'button',className:'btn-ghost',onClick:closeComptaCompteModal},'Annuler'),
      h('button',{type:'button',className:'btn-sm',onClick:()=>{
        const payload={libelle_condense:libI.value,numero_compte:numI.value};
        if(!payload.libelle_condense||!payload.numero_compte){toast('Libellé et numéro de compte obligatoires','error');return;}
        comptaUpdateCompte(editId,payload);
      }},'Enregistrer')
    )
  );
  overlay.appendChild(form);
  return overlay;
}

function renderCompta(){
  const isLight=document.body.classList.contains('light');
  const tab = S.comptaTab || 'factor';
  const sidebar=h('nav',{className:'sidebar'},
    h('div',{className:'logo'},
      h('div',{className:'logo-row'},
        h('div',{className:'logo-brand'},'My',h('span',null,'Compta')),
      ),
      h('div',{className:'logo-sub'},'by __APP_ORG_NAME__')
    ),
    h('div',{className:'nav-scroll tabs',style:{width:'100%',margin:0}},
      h('div',{className:'nav-group-label'},'Import'),
      h('button',{className:'nav-btn'+(tab==='factor'?' active':''),onClick:()=>{set({comptaTab:'factor'});}},
        iconEl('upload',15),'  Import Factor'),
      h('button',{className:'nav-btn'+(tab==='acheteurs'?' active':''),onClick:()=>{set({comptaTab:'acheteurs'});loadComptaAcheteurs();}},
        iconEl('users',15),'  Acheteurs'),
      h('button',{className:'nav-btn'+(tab==='comptes'?' active':''),onClick:()=>{set({comptaTab:'comptes'});loadComptaComptes();}},
        iconEl('file',15),'  Table des comptes'),
      h('button',{className:'nav-btn'+(tab==='banques'?' active':''),onClick:()=>{set({comptaTab:'banques'});loadComptaBanques();}},
        iconEl('credit-card',15),'  Code de banque'),
      h('div',{className:'nav-group-label'},'Autres modules'),
      h('button',{className:'nav-btn'+(tab==='cession'?' active':''),onClick:()=>{set({comptaTab:'cession'});}},
        iconEl('clock',15),'  Cession (en cours)'),
      h('button',{className:'nav-btn'+(tab==='paie'?' active':''),onClick:()=>{if(!S.paieEmpLoaded){paieLoadEmployes();}paieLoadVars().then(()=>render());set({comptaTab:'paie'});}},
        iconEl('credit-card',15),'  Paies')
    ),
    h('div',{className:'sidebar-bottom'},
      h('button',{className:'nav-btn back-mysifa',onClick:()=>{window.location.href='/' }},
        '← Retour ',
        h('span',{className:'wm'},'My',h('span',null,'Sifa'))
      ),
      sidebarUserChip(S.user),
      (() => {
        const b=h('button',{
          className:'support-btn',
          title:'Contacter le support',
          onClick:()=>set({contactOpen:true})
        });
        const ico=h('span',{className:'support-ico'});
        try{
          ico.innerHTML=(window.MySifaSupport && typeof window.MySifaSupport.iconSvg==='function')?window.MySifaSupport.iconSvg():'';
        }catch(e){ ico.innerHTML=''; }
        b.appendChild(ico);
        b.appendChild(h('span',null,'Contacter le support'));
        return b;
      })(),
      h('button',{
        className:'theme-btn',
        onClick:()=>{MySifaTheme.toggleMode();render();},
        title:'Changer le thème'
      },
        h('span',{className:'theme-ico'},iconEl(isLight?'sun':'moon',16)),
        h('span',{className:'theme-label'},isLight?'Mode clair':'Mode sombre')
      ),
      h('button',{className:'logout-btn',onClick:doLogout},iconEl('log-out',14),' Déconnexion')
    )
  );

  const topbar=h('div',{className:'mobile-topbar'},
    h('button',{type:'button',className:'mobile-menu-btn',onClick:toggleSidebar,'aria-label':'Menu'},iconEl('menu',20)),
    h('div',null,
      h('div',{className:'mobile-topbar-title'},'MyCompta'),
      h('div',{className:'mobile-topbar-sub'},'Comptabilité')
    ),
    h('button',{type:'button',className:'mobile-home-btn',onClick:()=>{window.location.href='/'},'aria-label':'Accueil'},iconEl('home',20))
  );

  let content;
  if(tab==='factor'){
    const factorMode=S.comptaFactorMode||'file';
    const modeBar=h('div',{style:{display:'flex',gap:'8px',marginBottom:'12px',flexWrap:'wrap'}},
      h('button',{className:factorMode==='file'?'btn-sm':'btn-ghost btn-sm',type:'button',onClick:()=>set({comptaFactorMode:'file'})},
        iconEl('upload',13),' Fichier'),
      h('button',{className:factorMode==='paste'?'btn-sm':'btn-ghost btn-sm',type:'button',onClick:()=>set({comptaFactorMode:'paste'})},
        iconEl('clipboard',13),' Coller')
    );
    const inp=h('input',{type:'file',accept:'.xlsx,.xlsm,.xls,.csv,.txt',style:{display:'none'}});
    const zone=h('div',{className:'drop-zone',style:{marginBottom:'16px'}},
      h('div',{className:'dz-icon'},iconEl('cloud-upload',36)),
      h('div',{className:'dz-title'},'Dépose le fichier Factor'),
      h('div',{className:'dz-sub'},'Excel (.xlsx, .xls) ou CSV (.csv)')
    );
    zone.addEventListener('click',()=>inp.click());
    zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('drag');});
    zone.addEventListener('dragleave',()=>zone.classList.remove('drag'));
    zone.addEventListener('drop',e=>{
      e.preventDefault();zone.classList.remove('drag');
      const f=e.dataTransfer.files[0];if(f)comptaTransform(f);
    });
    inp.addEventListener('change',e=>{const f=e.target.files[0];if(f)comptaTransform(f);});
    const pasteTa=h('textarea',{
      className:'form-sel',
      style:{width:'100%',minHeight:'180px',fontFamily:'ui-monospace,monospace',fontSize:'12px',resize:'vertical',boxSizing:'border-box'},
      placeholder:'Collez ici les lignes Factor (ligne d\'en-tête incluse). Séparateur ; , ou tabulation.',
      value:S.comptaPasteText||''
    });
    pasteTa.addEventListener('input',e=>{S.comptaPasteText=e.target.value;});
    const pasteFromClip=h('button',{className:'btn-ghost btn-sm',type:'button',onClick:async()=>{
      try{
        const t=await navigator.clipboard.readText();
        S.comptaPasteText=t||'';
        set({comptaPasteText:S.comptaPasteText});
      }catch(e){toast('Impossible de lire le presse-papiers','error');}
    }},iconEl('clipboard',13),' Lire le presse-papiers');
    const pasteGo=h('button',{className:'btn-sm',type:'button',onClick:()=>comptaTransformPaste(pasteTa.value)},
      iconEl('upload',13),' Transformer');
    const pasteBlock=h('div',{className:'card',style:{marginBottom:'16px',padding:'14px 18px'}},
      h('div',{style:{fontSize:'13px',fontWeight:'600',color:'var(--text)',marginBottom:'8px'}},'Coller les lignes Factor'),
      h('div',{style:{fontSize:'12px',color:'var(--muted)',marginBottom:'10px',lineHeight:'1.5'}},
        'Copiez les lignes depuis Factor ou Excel, puis collez-les ci-dessous (en-têtes requis).'),
      pasteTa,
      h('div',{style:{display:'flex',gap:'8px',marginTop:'10px',flexWrap:'wrap'}},pasteFromClip,pasteGo)
    );
    const importBlock=factorMode==='paste'?pasteBlock:zone;

    const r=S.comptaResult;
    const miss=r && r.missing ? r.missing : null;
    const missBox = miss ? h('div',{className:'card',style:{marginBottom:'16px'}},
      h('div',{className:'card-header'},h('h3',null,'Contrôles')),
      h('div',{style:{padding:'14px 18px',fontSize:'12px',color:'var(--muted)',lineHeight:'1.6'}},
        (miss.comptes && miss.comptes.length)
          ? h('div',null,
              h('div',{style:{fontWeight:'700',color:'var(--text)',marginBottom:'6px'}},'Libellés manquants dans Table des comptes'),
              ...miss.comptes.slice(0,12).map(x=>h('div',null,'- ',x.libelle_key,' (',x.count,')'))
            )
          : h('div',null,'✅ Aucun libellé manquant dans la table des comptes.'),
        h('div',{style:{height:'10px'}}),
        (miss.acheteurs && miss.acheteurs.length)
          ? h('div',null,
              h('div',{style:{fontWeight:'700',color:'var(--text)',marginBottom:'6px'}},'Acheteurs non reconnus'),
              ...miss.acheteurs.slice(0,12).map(x=>h('div',null,'- ',x.buyer,' (',x.count,')'))
            )
          : h('div',null,'✅ Aucun acheteur manquant.'),
        h('div',{style:{height:'10px'}}),
        (miss.banques && miss.banques.length)
          ? h('div',null,
              h('div',{style:{fontWeight:'700',color:'var(--text)',marginBottom:'6px'}},'Codes vendeur sans compte CAF (Code de banque)'),
              ...miss.banques.slice(0,12).map(x=>h('div',null,'- ',x.code_vendeur,' (',x.count,')'))
            )
          : h('div',null,'✅ Tous les codes vendeur ont un compte CAF.')
      )
    ) : null;

    const cw = r && r.cw_text ? r.cw_text : '';
    const copyBtn=h('button',{className:'btn-sm',onClick:async()=>{
      try{ await navigator.clipboard.writeText(cw); toast('Copié pour CW'); }
      catch(e){ toast('Impossible de copier','error'); }
    }},iconEl('copy',13),' Copier pour CW');

    function fmtAmt(v){
      const n = (typeof v==='number') ? v : (v==null?0:Number(v));
      if(!isFinite(n) || n===0) return '';
      try{
        return new Intl.NumberFormat('fr-FR',{minimumFractionDigits:0,maximumFractionDigits:2}).format(n);
      }catch(e){
        return String(n);
      }
    }

    const rows = (r && Array.isArray(r.rows)) ? r.rows : [];
    const tbl = rows.length ? (()=>{
      const head=h('thead',null,
        h('tr',null,
          h('th',null,'Date'),
          h('th',null,'Code vendeur'),
          h('th',null,'Compte'),
          h('th',null,'Libellé'),
          h('th',null,'Débit'),
          h('th',null,'Crédit')
        )
      );
      const body=h('tbody',null,
        ...rows.map((rr,idx)=>{
          const pb = rr && rr.problem ? String(rr.problem) : '';
          const cls = pb ? ('cw-row-bad') : '';
          const title = pb
            ? ((pb==='compte_manquant'?'Compte manquant (Table des comptes)'
              : pb==='banque_manquante'?'Compte CAF manquant (Code de banque)'
              : 'Acheteur non reconnu') + (rr.problem_detail?(' — '+rr.problem_detail):''))
            : '';
          return h('tr',{className:cls, title},
            h('td',null, rr.date||''),
            h('td',null, rr.code_vendeur||''),
            h('td',null, rr.compte||''),
            h('td',null, rr.libelle||''),
            h('td',null, fmtAmt(rr.debit)),
            h('td',null, fmtAmt(rr.credit))
          );
        })
      );

      const table=h('table',{style:{minWidth:'980px'}}, head, body);
      const top=h('div',{className:'tbl-scroll top'}); // barre de scroll horizontale
      const bot=h('div',{className:'tbl-scroll bot'}, table);
      top.addEventListener('scroll',()=>{ bot.scrollLeft = top.scrollLeft; });
      bot.addEventListener('scroll',()=>{ top.scrollLeft = bot.scrollLeft; });
      // sync initial width
      requestAnimationFrame(()=>{ top.scrollLeft = bot.scrollLeft; });
      return h('div',{className:'cw-table'},
        top,
        bot
      );
    })() : h('div',{className:'card-empty'},'Aucun résultat. Importez un fichier ou collez des lignes.');

    content=h('div',null, modeBar, importBlock, inp,
      missBox,
      h('div',{className:'card'},
        h('div',{className:'card-header'},h('h3',null,'Résultat (à coller dans CW)'), copyBtn),
        h('div',{style:{padding:'14px 18px'}}, tbl)
      )
    );
  }else if(tab==='acheteurs'){
    const list=S.comptaAcheteurs||[];
    const imp=h('input',{type:'file',accept:'.xlsx,.xlsm,.xls',style:{display:'none'}});
    const impBtn=h('button',{className:'btn-ghost',onClick:()=>imp.click()},iconEl('upload',13),' Importer Excel');
    imp.addEventListener('change',e=>{const f=e.target.files[0];if(f)comptaImportAcheteurs(f);});
    const code=h('input',{type:'text',placeholder:'Code vendeur (optionnel)'});
    const numCompte=h('input',{type:'text',placeholder:'Numéro de compte'});
    const rs=h('input',{type:'text',placeholder:'Raison sociale (ex: COME BACK GRAPHIC ASSOCIES)'});
    const form=h('div',{className:'compta-add-bar'},
      h('h3',null,'Ajouter un acheteur'),
      h('div',{className:'compta-add-bar-meta'},
        h('span',{className:'hint'},'Feuille: ACHETEURS'),
        impBtn,
        imp
      ),
      h('div',{className:'compta-add-bar-fields'},
        h('div',null,h('label',null,'Code vendeur'),code),
        h('div',null,h('label',null,'Numéro de compte'),numCompte),
        h('div',null,h('label',null,'Raison sociale'),rs)
      ),
      h('div',{className:'compta-add-bar-actions'},
        h('button',{className:'btn-sm',onClick:()=>{
          const payload={code_vendeur:code.value||null,identifiant:numCompte.value,raison_sociale:rs.value};
          if(!payload.identifiant||!payload.raison_sociale){toast('Numéro de compte et raison sociale obligatoires','error');return;}
          comptaUpsertAcheteurs([payload]);
          code.value='';numCompte.value='';rs.value='';
        }},'Ajouter')
      )
    );
    const rows=list.length? h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',null,'Acheteurs ('+list.length+')')),
      h('div',{style:{padding:'10px 16px'}},...list.slice(0,500).map(a=>h('div',{className:'import-row'},
        h('div',{style:{flex:1}},h('div',{style:{fontSize:'13px',fontWeight:'600'}},a.raison_sociale),h('div',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace'}},(a.code_vendeur||'—')+' · '+a.identifiant)),
        h('button',{className:'btn-ghost',onClick:()=>set({comptaEditAcheteurId:a.id})},iconEl('edit',13),' Modifier'),
        h('button',{className:'btn-danger',onClick:()=>comptaDeleteAcheteur(a.id)},iconEl('trash',13),' Supprimer')
      )))
    ) : h('div',{className:'card-empty'},'Aucun acheteur');
    content=h('div',null,form,rows);
  }else if(tab==='comptes'){
    const list=S.comptaComptes||[];
    const imp=h('input',{type:'file',accept:'.xlsx,.xlsm,.xls',style:{display:'none'}});
    const impBtn=h('button',{className:'btn-ghost',onClick:()=>imp.click()},iconEl('upload',13),' Importer Excel');
    imp.addEventListener('change',e=>{const f=e.target.files[0];if(f)comptaImportComptes(f);});
    const lib=h('input',{type:'text',placeholder:'Libellé condensé (ex: Achat de Factures)'});
    const num=h('input',{type:'text',placeholder:'Numéro de compte (ex: 519320000000)'});
    const form=h('div',{className:'compta-add-bar'},
      h('h3',null,'Ajouter un libellé'),
      h('div',{className:'compta-add-bar-meta'},
        h('span',{className:'hint'},'Feuille: TABLE DES COMPTES'),
        impBtn,
        imp
      ),
      h('div',{className:'compta-add-bar-fields'},
        h('div',null,h('label',null,'Libellé condensé'),lib),
        h('div',null,h('label',null,'Numéro de compte'),num)
      ),
      h('div',{className:'compta-add-bar-actions'},
        h('button',{className:'btn-sm',onClick:()=>{
          const payload={libelle_condense:lib.value,numero_compte:num.value};
          if(!payload.libelle_condense||!payload.numero_compte){toast('Libellé et numéro de compte obligatoires','error');return;}
          comptaUpsertComptes([payload]);
          lib.value='';num.value='';
        }},'Ajouter')
      )
    );
    const rows=list.length? h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',null,'Table des comptes ('+list.length+')')),
      h('div',{style:{padding:'10px 16px'}},...list.slice(0,500).map(a=>h('div',{className:'import-row'},
        h('div',{style:{flex:1}},h('div',{style:{fontSize:'13px',fontWeight:'600'}},a.libelle_condense),h('div',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace'}},a.numero_compte)),
        h('button',{className:'btn-ghost',onClick:()=>set({comptaEditCompteId:a.id})},iconEl('edit',13),' Modifier'),
        h('button',{className:'btn-danger',onClick:()=>comptaDeleteCompte(a.id)},iconEl('trash',13),' Supprimer')
      )))
    ) : h('div',{className:'card-empty'},'Aucun compte');
    content=h('div',null,form,rows);
  }else if(tab==='banques'){
    const list=S.comptaBanques||[];
    const code=h('input',{type:'text',placeholder:'Code vendeur (ex: 98, 100)'});
    const num=h('input',{type:'text',placeholder:'Numéro de compte (ex: 519320000000)'});
    const lib=h('input',{type:'text',placeholder:'Libellé (optionnel)'});
    const form=h('div',{className:'compta-add-bar'},
      h('h3',null,'Ajouter un code de banque'),
      h('div',{className:'compta-add-bar-meta'},
        h('span',{className:'hint'},'Compte CAF de contrepartie selon le code vendeur Factor')
      ),
      h('div',{className:'compta-add-bar-fields'},
        h('div',null,h('label',null,'Code vendeur'),code),
        h('div',null,h('label',null,'Numéro de compte'),num),
        h('div',null,h('label',null,'Libellé'),lib)
      ),
      h('div',{className:'compta-add-bar-actions'},
        h('button',{className:'btn-sm',onClick:()=>{
          const payload={code_vendeur:code.value,numero_compte:num.value,libelle:lib.value||null};
          if(!payload.code_vendeur||!payload.numero_compte){toast('Code vendeur et numéro de compte obligatoires','error');return;}
          comptaUpsertBanques([payload]);
          code.value='';num.value='';lib.value='';
        }},'Ajouter')
      )
    );
    const rows=list.length? h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',null,'Codes de banque ('+list.length+')')),
      h('div',{style:{padding:'10px 16px'}},...list.map(b=>h('div',{className:'import-row'},
        h('div',{style:{flex:1}},
          h('div',{style:{fontSize:'13px',fontWeight:'600'}},'Vendeur ',b.code_vendeur,(b.libelle?(' — '+b.libelle):'')),
          h('div',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace'}},b.numero_compte)
        ),
        h('button',{className:'btn-ghost',onClick:()=>set({comptaEditBanqueId:b.id})},iconEl('edit',13),' Modifier'),
        h('button',{className:'btn-danger',onClick:()=>comptaDeleteBanque(b.id)},iconEl('trash',13),' Supprimer')
      )))
    ) : h('div',{className:'card-empty'},'Aucun code de banque — ajoutez au moins 98 et 100');
    content=h('div',null,form,rows);
  }else if(tab==='cession'){
    content=h('div',null,
      h('div',{className:'card',style:{padding:'40px',textAlign:'center'}},
        h('div',{style:{fontSize:'48px',marginBottom:'20px'}},'🚧'),
        h('h2',{style:{color:'var(--muted)'}},'Cession'),
        h('p',{style:{color:'var(--muted)',marginTop:'10px'}},'En cours de développement...')
      )
    );
  }else if(tab==='paie'){
    content=renderPaieTab();
  }

  const body=h('div',{className:'app'},
    sidebar,
    h('main',{className:'main'},
      h('div',{className:'container'},
        topbar,
          h('h1',null,S.comptaTab==='paie'?'Gestion des Paies':'MyCompta'),
        h('div',{className:'subtitle'},S.comptaTab==='paie'?'Saisie mensuelle · Export xlsx':'Import Factor → mise en forme → copier vers CW'),
        content
      )
    )
  );

  return h('div',null,
    S.sidebarOpen?h('div',{className:'sidebar-overlay',onClick:closeSidebar}):null,
    body,
    renderComptaAcheteurModal(),
    renderComptaCompteModal(),
    renderComptaBanqueModal()
  );
}
"""

"""MyCompta — Comparaison factures (JS).

Onglet « Comparaison factures » : analyse des ventes RVGI / grand-livre CW,
revérification avec le seul fichier corrigé, versions, écarts justifiés.
Concaténé dans COMPTA_MAIN_JS (app/web/compta_assets.py), avant renderCompta()
qui appelle renderComptaComparaison(). API : /api/compta/comparaison-factures
et /api/compta/comparaisons… (app/routers/compta.py), calcul dans
app/services/compta_comparaison_factures.py.
"""

COMPTA_COMPARAISON_JS = r"""
// ── COMPARAISON FACTURES ─────────────────────────────────────────
// Analyse des ventes RVGI (HT) et grand-livre clients CW (TTC), en PDF.
// Un seul dépôt pour les deux : le serveur reconnaît chaque document.
// Rapprochement par numéro + date (app/services/compta_comparaison_factures.py).
// Chaque comparaison est enregistrée ; sur une comparaison ouverte, déposer le
// seul fichier corrigé crée la version suivante, avec le bilan des corrections.
// Un écart normal se justifie (commentaire) et sort du compte des écarts.
// Adresse : comparaison=<id de la version>, filtre=… (static/compta_url.js).
// Hors adresse : fichiers en cours de dépôt, saisie d'une justification
// (formulaire en ligne, création en cours).
const COMPTA_CMP_STATUTS={
  montant:{lib:'Montant',ton:'danger'},
  numero:{lib:'Numéro',ton:'warn'},
  date:{lib:'Date',ton:'warn'},
  rvgi_seul:{lib:'Absente de CW',ton:'danger'},
  cw_seul:{lib:'Absente de RVGI',ton:'danger'},
  tva:{lib:'TVA isolée',ton:'warn'},
  retire:{lib:'Retirée',ton:'success'},
  ok:{lib:'Concordante',ton:'success'},
};
const COMPTA_CMP_FILTRES=['ecarts','tout','corriges','justifies','montant','numero','date','rvgi_seul','cw_seul','tva','ok'];
const comptaCmpEstEcart=l=>l.statut!=='ok'&&l.statut!=='retire';
const comptaCmpATraiter=l=>comptaCmpEstEcart(l)&&!l.justif;
function comptaCmpFiltrer(lignes,f){
  if(f==='tout') return lignes;
  if(f==='ecarts') return lignes.filter(comptaCmpATraiter);
  if(f==='corriges') return lignes.filter(l=>l.evolution==='corrige');
  if(f==='justifies') return lignes.filter(l=>comptaCmpEstEcart(l)&&l.justif);
  return lignes.filter(l=>l.statut===f);
}
function comptaCmpEur(v){
  if(v==null||!isFinite(v)) return '—';
  return new Intl.NumberFormat('fr-FR',{minimumFractionDigits:2,maximumFractionDigits:2}).format(v)+' €';
}
function comptaCmpDate(d){ return d?(d.slice(8,10)+'/'+d.slice(5,7)+'/'+d.slice(0,4)):''; }
function comptaCmpHorodatage(iso){
  return iso?(iso.slice(8,10)+'/'+iso.slice(5,7)+'/'+iso.slice(0,4)+' à '+iso.slice(11,16)):'';
}
function comptaCmpPastilleTon(lib,ton,plein){
  return h('span',{style:{display:'inline-block',whiteSpace:'nowrap',fontSize:'11px',fontWeight:'700',
    padding:'3px 9px',borderRadius:'20px',color:'var(--'+ton+')',
    border:plein?'none':('1px solid var(--'+ton+')'),
    background:plein?('color-mix(in srgb, var(--'+ton+') 14%, transparent)'):'transparent'}},lib);
}
function comptaCmpBadge(statut){
  const st=COMPTA_CMP_STATUTS[statut]||{lib:statut,ton:'muted'};
  return comptaCmpPastilleTon(st.lib,st.ton,true);
}

// ── Appels ──
function comptaCmpApres(r,message){
  set({comptaCmpRes:r,comptaCmpId:r.id,comptaCmpDocs:[],comptaCmpEnCours:false,comptaCmpErreur:null,
    comptaCmpFiltre:r.bilan&&r.bilan.corriges?'corriges':(S.comptaCmpFiltre||'ecarts')});
  comptaCmpChargerHist();
  if(message) toast(message, r.nb_a_traiter?'info':'success');
}
async function comptaComparer(){
  const docs=S.comptaCmpDocs||[];
  if(docs.length<2) return;
  set({comptaCmpEnCours:true,comptaCmpErreur:null});
  try{
    const fd=new FormData();
    fd.append('doc_a',docs[0]);fd.append('doc_b',docs[1]);
    const r=await api('/api/compta/comparaison-factures',{method:'POST',body:fd});
    if(!r){set({comptaCmpEnCours:false});return;}
    const n=r.nb_a_traiter;
    comptaCmpApres(r,n?(n+' écart'+(n>1?'s':'')+' à examiner.'):'Les deux documents concordent.');
  }catch(e){
    set({comptaCmpEnCours:false,comptaCmpErreur:e.message||'Comparaison impossible.'});
  }
}
async function comptaCmpReverifier(pdf){
  const base=S.comptaCmpRes;
  set({comptaCmpDocs:pdf,comptaCmpEnCours:true,comptaCmpErreur:null});
  try{
    const fd=new FormData();
    fd.append('doc_a',pdf[0]); if(pdf[1]) fd.append('doc_b',pdf[1]);
    const r=await api('/api/compta/comparaisons/'+base.id+'/reverifier',{method:'POST',body:fd});
    if(!r){set({comptaCmpEnCours:false,comptaCmpDocs:[]});return;}
    const b=r.bilan||{};
    comptaCmpApres(r,'v'+r.version+' : '+(b.corriges||0)+' corrigé'+((b.corriges||0)>1?'s':'')
      +', '+r.nb_a_traiter+' à traiter.');
  }catch(e){
    set({comptaCmpEnCours:false,comptaCmpDocs:[],comptaCmpErreur:e.message||'Revérification impossible.'});
  }
}
// Sur une comparaison revérifiable : un ou deux PDF corrigés relancent la
// vérification aussitôt. Sinon : deux PDF au plus, la comparaison part dès
// que les deux sont là.
function comptaCmpAjouter(fichiers){
  const pdf=[...(fichiers||[])].filter(f=>/\.pdf$/i.test(f.name));
  if(!pdf.length){toast('PDF attendu.','error');return;}
  const r=S.comptaCmpRes;
  if(r&&r.reverifiable&&!(S.comptaCmpDocs||[]).length){ comptaCmpReverifier(pdf.slice(-2)); return; }
  const docs=[...(S.comptaCmpDocs||[]),...pdf].slice(-2);
  set({comptaCmpDocs:docs,comptaCmpRes:null,comptaCmpId:null,comptaCmpErreur:null});
  if(docs.length===2) comptaComparer();
}
function comptaCmpNouvelle(){
  set({comptaCmpDocs:[],comptaCmpRes:null,comptaCmpId:null,comptaCmpErreur:null,comptaCmpEnCours:false,
    comptaCmpJustifCle:null,comptaCmpFiltre:'ecarts'});
}
async function comptaCmpChargerHist(){
  try{ const l=await api('/api/compta/comparaisons'); if(l) set({comptaCmpHist:l}); }catch(e){}
}
async function comptaCmpOuvrir(id){
  if(id==null) return;
  set({comptaCmpId:id,comptaCmpDocs:[],comptaCmpErreur:null,comptaCmpEnCours:true,comptaCmpJustifCle:null});
  try{
    const r=await api('/api/compta/comparaisons/'+encodeURIComponent(id));
    if(!r){set({comptaCmpEnCours:false});return;}
    if(S.comptaCmpId!==id) return;
    set({comptaCmpRes:r,comptaCmpEnCours:false});
  }catch(e){
    set({comptaCmpRes:null,comptaCmpId:null,comptaCmpEnCours:false,comptaCmpErreur:e.message||'Comparaison introuvable.'});
  }
}
async function comptaCmpSupprimer(c){
  const v=c.version>1?(' et ses '+c.version+' versions'):'';
  if(!confirm('Supprimer la comparaison du '+comptaCmpHorodatage(c.cree_le)+v+' ?'))return;
  try{
    await api('/api/compta/comparaisons/'+c.id,{method:'DELETE'});
    if(S.comptaCmpRes&&S.comptaCmpRes.dossier_id===c.dossier_id) comptaCmpNouvelle();
    toast('Comparaison supprimée.');
    comptaCmpChargerHist();
  }catch(e){toast(e.message||'Suppression impossible.','error');}
}
async function comptaCmpJustifier(cle){
  const txt=(S.comptaCmpJustifTxt||'').trim();
  if(!txt){toast('Commentaire obligatoire — dire pourquoi l\'écart est normal.','error');return;}
  try{
    const r=await api('/api/compta/comparaisons/'+S.comptaCmpRes.id+'/justifications',{
      method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({cle,commentaire:txt})});
    if(!r) return;
    set({comptaCmpRes:r,comptaCmpJustifCle:null,comptaCmpJustifTxt:''});
    toast('Écart justifié.');
    comptaCmpChargerHist();
  }catch(e){toast(e.message||'Justification impossible.','error');}
}
async function comptaCmpDejustifier(cle){
  try{
    const r=await api('/api/compta/comparaisons/'+S.comptaCmpRes.id+'/justifications?cle='+encodeURIComponent(cle),{method:'DELETE'});
    if(!r) return;
    set({comptaCmpRes:r});
    toast('Justification retirée.');
    comptaCmpChargerHist();
  }catch(e){toast(e.message||'Action impossible.','error');}
}

// ── Dépôt ──
function renderComptaCmpDepot(){
  const docs=S.comptaCmpDocs||[];
  const r=S.comptaCmpRes;
  const enCours=!!S.comptaCmpEnCours;
  const reverif=!!(r&&r.reverifiable);
  const inp=h('input',{type:'file',accept:'.pdf,application/pdf',multiple:'',style:{display:'none'}});
  inp.addEventListener('change',e=>{comptaCmpAjouter(e.target.files);inp.value='';});
  // Fichiers montrés : ceux en cours d'envoi, sinon ceux de la version
  // ouverte (noms enregistrés, les PDF ne sont pas gardés).
  const fichiers=docs.length
    ? docs.map(f=>({nom:f.name,type:null}))
    : ((r&&r.fichiers)||[]);
  const pastille=(f)=>h('span',{style:{display:'inline-flex',alignItems:'center',gap:'6px',maxWidth:'100%',
      padding:'5px 10px',borderRadius:'8px',background:'var(--bg)',border:'1px solid var(--border)',fontSize:'12px'}},
    iconEl('file-text',13),
    h('span',{style:{overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}},f.nom),
    f.type?h('span',{style:{fontSize:'10px',fontWeight:'700',color:'var(--accent)'}},f.type==='rvgi'?'RVGI':'CW'):null,
    f.corrige?h('span',{style:{fontSize:'10px',fontWeight:'700',color:'var(--success)'}},'corrigé'):null
  );
  let titre, aide;
  if(enCours){
    titre=reverif&&docs.length?'Revérification…':'Comparaison…';
    aide=reverif&&docs.length?'Seul le document déposé est relu, l\'autre est repris de la version ouverte.':'Lecture des deux PDF.';
  }else if(docs.length===1){
    titre='1 / 2 document'; aide='Ajoute le second PDF : la comparaison démarre aussitôt.';
  }else if(r&&r.id){
    titre='Comparaison n° '+r.dossier_id+' · v'+r.version;
    aide=reverif
      ?'Dépose ici le ou les fichiers corrigés : la vérification repart aussitôt, sans redéposer l\'autre.'
      :'Comparaison enregistrée avant la revérification : pour la refaire, lance une nouvelle comparaison.';
  }else{
    titre='Dépose les deux PDF ici';
    aide='Analyse des ventes RVGI et grand-livre clients CW du même mois, dans n\'importe quel ordre.';
  }
  const erreur=S.comptaCmpErreur&&!enCours;
  const zone=h('div',{className:'drop-zone',
      style:{flex:'1 1 320px',minWidth:'0',margin:'0',padding:'16px 18px',display:'flex',alignItems:'center',gap:'14px',textAlign:'left'}},
    h('div',{className:'dz-icon',style:{margin:'0'}},iconEl(reverif&&!docs.length?'rotate-cw':'cloud-upload',28)),
    h('div',{style:{flex:'1',minWidth:'0'}},
      h('div',{className:'dz-title',style:{margin:'0 0 4px'}},titre),
      fichiers.length?h('div',{style:{display:'flex',gap:'6px',flexWrap:'wrap',marginBottom:'4px'}},...fichiers.map(pastille)):null,
      h('div',{className:'dz-sub',style:{color:erreur?'var(--danger)':null}},erreur?S.comptaCmpErreur:aide)
    )
  );
  zone.addEventListener('click',()=>inp.click());
  zone.addEventListener('dragover',e=>{e.preventDefault();zone.classList.add('drag');});
  zone.addEventListener('dragleave',()=>zone.classList.remove('drag'));
  zone.addEventListener('drop',e=>{e.preventDefault();zone.classList.remove('drag');comptaCmpAjouter(e.dataTransfer.files);});
  return h('div',{className:'card',style:{padding:'14px',marginBottom:'16px'}},
    h('div',{style:{display:'flex',gap:'14px',alignItems:'center',flexWrap:'wrap'}},
      zone,inp,
      h('button',{type:'button',className:'btn-sm',
        style:{background:'var(--bg)',border:'1px solid var(--border)',color:'var(--text)'},
        onClick:comptaCmpNouvelle},iconEl('copy',13),' Nouvelle comparaison')
    ),
    renderComptaCmpVersions(r)
  );
}
// Versions du dossier ouvert : v1 · v2 · v3, avec les écarts à traiter.
function renderComptaCmpVersions(r){
  if(!r||!r.versions||r.versions.length<2) return null;
  return h('div',{style:{display:'flex',gap:'6px',flexWrap:'wrap',alignItems:'center',marginTop:'12px'}},
    h('span',{style:{fontSize:'11px',fontWeight:'600',textTransform:'uppercase',letterSpacing:'.5px',color:'var(--muted)',marginRight:'4px'}},'Versions'),
    ...r.versions.map(v=>{
      const actif=v.id===r.id;
      return h('button',{type:'button',className:'btn-sm',
        title:comptaCmpHorodatage(v.cree_le),
        style:actif?{background:'var(--accent-bg)',border:'1px solid var(--accent)',color:'var(--accent)'}
                   :{background:'var(--bg)',border:'1px solid var(--border)',color:'var(--text2)'},
        onClick:()=>{ if(!actif) comptaCmpOuvrir(v.id); }},
        'v'+v.version+' · ',
        h('span',{style:{color:v.nb_a_traiter?'var(--danger)':'var(--success)',fontWeight:'700'}},
          v.nb_a_traiter?(v.nb_a_traiter+' écart'+(v.nb_a_traiter>1?'s':'')):'0 écart'));
    })
  );
}

// ── Résultat ──
function renderComptaCmpTuile(lib,val,ton,filtre,detail,tonDetail){
  const actif=filtre&&(S.comptaCmpFiltre||'ecarts')===filtre;
  return h('div',{className:'card',
    style:{flex:'1 1 150px',padding:'12px 16px',cursor:filtre?'pointer':'default',
      borderColor:actif?'var(--accent)':'var(--border)'},
    onClick:filtre?()=>set({comptaCmpFiltre:filtre}):null},
    h('div',{style:{fontSize:'11px',fontWeight:'600',textTransform:'uppercase',letterSpacing:'.5px',color:'var(--muted)'}},lib),
    h('div',{style:{fontSize:'22px',fontWeight:'700',marginTop:'4px',color:ton?('var(--'+ton+')'):'var(--text)'}},String(val)),
    detail?h('div',{style:{fontSize:'12px',marginTop:'2px',color:tonDetail?('var(--'+tonDetail+')'):'var(--muted)'}},detail):null
  );
}
function renderComptaCmpBilan(r){
  const b=r.bilan;
  if(!b) return null;
  const seg=(n,lib,ton,filtre)=>h('span',{
      style:{cursor:filtre?'pointer':'default',fontWeight:'700',color:n?('var(--'+ton+')'):'var(--muted)'},
      onClick:filtre?()=>set({comptaCmpFiltre:filtre}):null},
    n+' '+lib+(n>1?'s':''));
  return h('div',{className:'card',style:{padding:'12px 16px',marginBottom:'12px',display:'flex',gap:'14px',
      flexWrap:'wrap',alignItems:'center',borderColor:b.nouveaux?'var(--danger)':'var(--success)'}},
    h('span',{style:{fontSize:'13px',color:'var(--text2)'}},
      'Par rapport à la v'+b.precedente_version+' ('+(b.remplaces||[]).map(t=>t==='rvgi'?'RVGI':'CW').join(' et ')+' corrigé'+((b.remplaces||[]).length>1?'s':'')+') :'),
    seg(b.corriges,'corrigé','success','corriges'),
    seg(b.restants,'restant','warn','ecarts'),
    seg(b.nouveaux,'nouveau','danger','ecarts')
  );
}
function renderComptaCmpPiste(l,r){
  if(l.justif){
    return h('div',null,
      h('div',{style:{display:'flex',gap:'8px',alignItems:'center',flexWrap:'wrap'}},
        comptaCmpPastilleTon('Justifié','success',true),
        h('span',{style:{color:'var(--text)'}},l.justif.commentaire)),
      h('div',{style:{fontSize:'11px',color:'var(--muted)',marginTop:'3px'}},
        (l.justif.par?l.justif.par+' · ':'')+comptaCmpHorodatage(l.justif.le)+' · ',
        h('span',{style:{cursor:'pointer',textDecoration:'underline'},onClick:()=>comptaCmpDejustifier(l.cle)},'Retirer')),
      l.piste?h('div',{style:{fontSize:'11px',color:'var(--muted)',marginTop:'3px'}},l.piste):null
    );
  }
  const enEdition=S.comptaCmpJustifCle===l.cle;
  const blocs=[h('div',null,l.piste||'')];
  if(l.justif_caduque) blocs.push(h('div',{style:{fontSize:'11px',color:'var(--warn)',marginTop:'3px'}},
    'Justification caduque, les montants ont changé : « '+l.justif_caduque+' »'));
  if(comptaCmpEstEcart(l)&&r.id){
    if(enEdition){
      const inp=h('input',{type:'text',maxlength:'300',placeholder:'Pourquoi cet écart est normal (escompte voulu…)',
        value:S.comptaCmpJustifTxt||'',
        style:{flex:'1 1 200px',minWidth:'0',background:'var(--card)',border:'1px solid var(--border)',
          borderRadius:'8px',padding:'6px 10px',color:'var(--text)',fontSize:'12px'}});
      inp.addEventListener('input',e=>{S.comptaCmpJustifTxt=e.target.value;});
      inp.addEventListener('keydown',e=>{
        if(e.key==='Enter') comptaCmpJustifier(l.cle);
        if(e.key==='Escape') set({comptaCmpJustifCle:null,comptaCmpJustifTxt:''});
      });
      requestAnimationFrame(()=>inp.focus());
      blocs.push(h('div',{style:{display:'flex',gap:'6px',marginTop:'6px',flexWrap:'wrap'}},inp,
        h('button',{type:'button',className:'btn-sm',onClick:()=>comptaCmpJustifier(l.cle)},'Justifier'),
        h('button',{type:'button',className:'btn-sm',
          style:{background:'var(--bg)',border:'1px solid var(--border)',color:'var(--text2)'},
          onClick:()=>set({comptaCmpJustifCle:null,comptaCmpJustifTxt:''})},'Annuler')));
    }else{
      blocs.push(h('span',{style:{display:'inline-block',marginTop:'4px',fontSize:'11px',fontWeight:'600',
          color:'var(--accent)',cursor:'pointer'},
        onClick:()=>set({comptaCmpJustifCle:l.cle,comptaCmpJustifTxt:l.justif_caduque||''})},'Justifier cet écart'));
    }
  }
  return h('div',null,...blocs);
}
function renderComptaCmpResultat(r){
  const filtre=S.comptaCmpFiltre||'ecarts';
  if(!r) r={lignes:[],compte:{},vide:true};
  const vide=!!r.vide;
  const lignes=comptaCmpFiltrer(r.lignes,filtre);
  const nb={
    ecarts:r.lignes.filter(comptaCmpATraiter).length,
    justifies:r.lignes.filter(l=>comptaCmpEstEcart(l)&&l.justif).length,
    corriges:r.lignes.filter(l=>l.evolution==='corrige').length,
    tout:r.lignes.length,
  };
  Object.keys(COMPTA_CMP_STATUTS).forEach(k=>{nb[k]=r.lignes.filter(l=>l.statut===k).length;});
  const per=r.periode_rvgi||r.periode_cw;
  const alertes=[];
  if(r.total_ht_rvgi_edition!=null && Math.abs(r.total_ht_rvgi_edition-r.total_ht_rvgi)>0.01)
    alertes.push('Lecture RVGI incomplète : '+comptaCmpEur(r.total_ht_rvgi)+' lus pour un total édité de '+comptaCmpEur(r.total_ht_rvgi_edition)+'.');
  if(r.periode_rvgi&&r.periode_cw&&(r.periode_rvgi[0]!==r.periode_cw[0]||r.periode_rvgi[1]!==r.periode_cw[1]))
    alertes.push('Périodes différentes : RVGI du '+comptaCmpDate(r.periode_rvgi[0])+' au '+comptaCmpDate(r.periode_rvgi[1])
      +', CW du '+comptaCmpDate(r.periode_cw[0])+' au '+comptaCmpDate(r.periode_cw[1])+'.');

  const tuiles=h('div',{style:{display:'flex',gap:'12px',flexWrap:'wrap',marginBottom:'12px'}},
    renderComptaCmpTuile('Écarts à traiter',vide?'—':nb.ecarts,vide?null:(nb.ecarts?'danger':'success'),vide?null:'ecarts',
      !vide&&nb.justifies?('+ '+nb.justifies+' justifié'+(nb.justifies>1?'s':'')):null,'success'),
    renderComptaCmpTuile('Concordantes',vide?'—':nb.ok,vide?null:'success',vide?null:'ok'),
    renderComptaCmpTuile('Factures RVGI',vide?'—':r.nb_rvgi,null,vide?null:'tout'),
    renderComptaCmpTuile('Écritures CW',vide?'—':r.nb_cw,null,null),
    // TTC contre TTC : RVGI ne donne que le HT, son TTC est recalculé
    // facture par facture avec la TVA reconnue (service, total_ttc_rvgi).
    renderComptaCmpTuile('Total TTC RVGI',comptaCmpEur(r.total_ttc_rvgi),null,null,
      vide?null:('HT '+comptaCmpEur(r.total_ht_rvgi)+' + TVA'+(r.nb_taux_supposes?(' · '+r.nb_taux_supposes+' taux supposé'+(r.nb_taux_supposes>1?'s':'')):''))),
    renderComptaCmpTuile('Total TTC CW',comptaCmpEur(r.total_ttc_cw),null,null,
      vide?null:(Math.abs(r.ecart_ttc)<0.01?'Égal au TTC RVGI'
        :('Écart '+(r.ecart_ttc>0?'+':'')+comptaCmpEur(r.ecart_ttc))),
      vide?null:(Math.abs(r.ecart_ttc)<0.01?'success':'danger'))
  );
  const libs={ecarts:'À traiter',tout:'Toutes',corriges:'Corrigés',justifies:'Justifiés'};
  const chips=vide?null:h('div',{style:{display:'flex',gap:'6px',flexWrap:'wrap',marginBottom:'12px'}},
    ...COMPTA_CMP_FILTRES.filter(k=>k==='ecarts'||k==='tout'||(k!=='ok'&&nb[k])).map(k=>{
      const lib=(libs[k]||COMPTA_CMP_STATUTS[k].lib)+' ('+nb[k]+')';
      const actif=filtre===k;
      return h('button',{type:'button',className:'btn-sm',
        style:actif?{background:'var(--accent-bg)',border:'1px solid var(--accent)',color:'var(--accent)'}
                   :{background:'var(--bg)',border:'1px solid var(--border)',color:'var(--text2)'},
        onClick:()=>set({comptaCmpFiltre:k})},lib);
    })
  );
  const num=(v)=>h('td',{style:{textAlign:'right',whiteSpace:'nowrap',fontVariantNumeric:'tabular-nums'}},v);
  const tableau=lignes.length ? h('div',{style:{overflowX:'auto'}},
    h('table',{style:{width:'100%'}},
      h('thead',null,h('tr',null,
        h('th',null,'Statut'),h('th',null,'Facture'),h('th',null,'Client'),
        h('th',{style:{textAlign:'right'}},'HT RVGI'),h('th',{style:{textAlign:'right'}},'TTC CW'),
        h('th',{style:{textAlign:'right'}},'TVA'),h('th',null,'Piste'))),
      h('tbody',null,...lignes.map(l=>{
        const autreNum=l.numero_cw&&l.numero_cw!==l.numero;
        const autreDate=l.date_cw&&l.date_cw!==l.date;
        return h('tr',null,
          h('td',null,
            h('div',{style:{display:'flex',flexDirection:'column',gap:'4px',alignItems:'flex-start'}},
              comptaCmpBadge(l.statut),
              l.evolution==='corrige'&&l.statut!=='retire'?comptaCmpPastilleTon('Corrigé','success',false):null,
              l.evolution==='nouveau'?comptaCmpPastilleTon('Nouveau','danger',false):null)),
          h('td',{style:{whiteSpace:'nowrap'}},
            h('div',{style:{fontFamily:'monospace',fontWeight:'600'}},l.numero),
            h('div',{style:{fontSize:'11px',color:'var(--muted)'}},comptaCmpDate(l.date)),
            (autreNum||autreDate)?h('div',{style:{fontSize:'11px',color:'var(--warn)'}},
              'CW : '+(autreNum?l.numero_cw+' ':'')+(autreDate?comptaCmpDate(l.date_cw):'')):null),
          h('td',null,
            h('div',null,l.client_rvgi||l.client_cw||''),
            l.compte_cw?h('div',{style:{fontSize:'11px',color:'var(--muted)',fontFamily:'monospace'}},l.compte_cw):null),
          num(comptaCmpEur(l.ht)),
          num(comptaCmpEur(l.ttc)),
          num(l.taux!=null?(String(l.taux).replace('.',',')+' %'):'—'),
          h('td',{style:{fontSize:'12px',color:'var(--text2)',minWidth:'280px',whiteSpace:'normal',overflow:'visible',textOverflow:'clip',lineHeight:'1.45'}},
            renderComptaCmpPiste(l,r))
        );
      }))
    )
  ) : h('div',{className:'card-empty'},vide?'Dépose les deux PDF pour lancer la comparaison.'
      :filtre==='ecarts'?(nb.justifies?'Plus aucun écart à traiter : les écarts restants sont justifiés.':'Aucun écart : les deux documents concordent.')
      :'Aucune facture dans ce filtre.');

  return h('div',null,
    per?h('div',{style:{fontSize:'12px',color:'var(--muted)',marginBottom:'10px'}},
      'Période du '+comptaCmpDate(per[0])+' au '+comptaCmpDate(per[1])
      +' · tolérance '+String(r.tolerance).replace('.',',')+' € sur le TTC'):null,
    ...alertes.map(a=>h('div',{className:'card',style:{padding:'10px 16px',marginBottom:'10px',
      borderColor:'var(--danger)',color:'var(--danger)',fontSize:'13px'}},a)),
    vide?null:renderComptaCmpBilan(r),
    tuiles,
    h('div',{className:'card'},
      h('div',{className:'card-header'},h('h3',null,'Factures')),
      h('div',{style:{padding:'14px 18px'}},chips,tableau)
    )
  );
}

// ── Historique : une ligne par comparaison, sa dernière version ──
function renderComptaCmpHistorique(){
  const liste=S.comptaCmpHist||[];
  if(!liste.length) return null;
  const fmtPer=p=>p&&p[0]?(comptaCmpDate(p[0])+' – '+comptaCmpDate(p[1])):'Période inconnue';
  const dossierOuvert=S.comptaCmpRes&&S.comptaCmpRes.dossier_id;
  return h('div',{className:'card',style:{marginTop:'16px'}},
    h('div',{className:'card-header'},h('h3',null,'Comparaisons enregistrées ('+liste.length+')')),
    h('div',{style:{padding:'6px 12px 10px'}},...liste.map(c=>{
      const actif=dossierOuvert===c.dossier_id;
      const prog=(c.progression||[c.nb_ecarts]);
      return h('div',{className:'import-row',
          style:{cursor:'pointer',borderRadius:'8px',padding:'8px 10px',
            background:actif?'var(--accent-bg)':null},
          onClick:()=>{ if(S.comptaCmpId!==c.id) comptaCmpOuvrir(c.id); }},
        h('div',{style:{flex:'1',minWidth:'0'}},
          h('div',{style:{fontSize:'13px',fontWeight:'600',color:actif?'var(--accent)':'var(--text)'}},
            'Période '+fmtPer(c.periode)+(c.version>1?(' · v'+c.version):'')),
          h('div',{style:{fontSize:'11px',color:'var(--muted)',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}},
            comptaCmpHorodatage(c.cree_le)+(c.cree_par?(' · '+c.cree_par):'')+' · '+(c.fichiers||[]).map(f=>f.nom).join(' · '))
        ),
        h('span',{style:{fontSize:'12px',fontWeight:'700',whiteSpace:'nowrap',
          color:c.nb_ecarts?'var(--danger)':'var(--success)'},
          title:prog.length>1?'Écarts à traiter, version par version':''},
          prog.length>1?(prog.join(' → ')+' écart'+(c.nb_ecarts>1?'s':''))
            :(c.nb_ecarts?(c.nb_ecarts+' écart'+(c.nb_ecarts>1?'s':'')):'Concordant')),
        h('button',{type:'button',className:'btn-sm','aria-label':'Supprimer',title:'Supprimer',
          style:{background:'var(--bg)',border:'1px solid var(--border)',color:'var(--muted)',padding:'4px 8px'},
          onClick:e=>{e.stopPropagation();comptaCmpSupprimer(c);}},iconEl('trash',13))
      );
    }))
  );
}
function renderComptaComparaison(){
  if(!S.comptaCmpHistCharge){ S.comptaCmpHistCharge=true; comptaCmpChargerHist(); }
  return h('div',null,renderComptaCmpDepot(),renderComptaCmpResultat(S.comptaCmpRes||null),renderComptaCmpHistorique());
}

"""

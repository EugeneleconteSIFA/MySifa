"""MyExpé — onglet Emails commandes : CSS/JS injectés dans app/web/html.py.

L'agent relève la boîte commandes@ (lecture seule), classe chaque email et le
rapproche des commandes RVGI ; cet onglet sert à suivre le traitement. Les
styles de tableau, de tuiles et de modale sont ceux du Pilotage
(`expe_pilotage_assets.py`) : seules les pastilles propres aux emails sont ici.

Le corps d'un email est une saisie libre venue de l'extérieur : il ne passe
jamais par innerHTML, uniquement par des nœuds texte (`h()` crée des nœuds
texte pour ses enfants chaîne).
"""

EXPE_EMAILS_CSS = r"""
.expe-em-cat{display:inline-block;font-size:11px;font-weight:600;padding:2px 8px;border-radius:999px;
  background:var(--bg);border:1px solid var(--border);color:var(--text2);white-space:nowrap}
.expe-em-cat--reclamation{border-color:var(--danger);color:var(--danger)}
.expe-em-cat--nouvelle_commande{border-color:var(--accent);color:var(--accent)}
.expe-em-cat--aucune{font-style:italic;color:var(--muted)}
.expe-em-urgent{font-size:11px;font-weight:700;color:var(--danger);margin-left:6px}
.expe-em-sujet{font-weight:600;color:var(--text)}
.expe-em-resume{font-size:12px;color:var(--text2);margin-top:2px;line-height:1.45}
.expe-em-row{cursor:pointer}
.expe-em-row:hover td{background:var(--accent-bg)}
.expe-em-cde{font-family:monospace;font-size:11px;margin-right:8px;color:var(--accent);text-decoration:none}
.expe-em-cde--inconnue{color:var(--muted)}
.expe-em-statut{padding:4px 8px;background:var(--bg);border:1px solid var(--border);border-radius:7px;
  color:var(--text);font-size:12px;font-family:inherit}
.expe-em-corps{white-space:pre-wrap;font-size:12.5px;line-height:1.55;color:var(--text2);background:var(--bg);
  border:1px solid var(--border);border-radius:8px;padding:12px 14px;max-height:46vh;overflow:auto}
.expe-em-champs{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:14px}
.expe-em-champs label{display:block;font-size:10px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;
  color:var(--muted);margin-bottom:5px}
.expe-em-champs select,.expe-em-note{width:100%;padding:7px 10px;background:var(--bg);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font:inherit;font-size:13px}
.expe-em-note{min-height:56px;resize:vertical;margin-bottom:14px}
.expe-em-erreur{font-size:12px;color:var(--danger);margin-bottom:10px}
.expe-em-reglages-msg{font-size:12px;margin-top:10px;color:var(--text2)}
.expe-em-reglages-msg--ko{color:var(--danger)}
.expe-em-reglages-msg--ok{color:var(--success)}
"""

EXPE_EMAILS_JS = r"""
var _expeEmSearchTimer=null;
const EXPE_EM_FILTRES=[
  {key:'ouverts',label:'À suivre'},
  {key:'a_traiter',label:'À traiter'},
  {key:'en_cours',label:'En cours'},
  {key:'traite',label:'Traités'},
  {key:'tous',label:'Tout'}
];

async function loadExpeEmails(){
  S.expeEmLoading=true;
  try{
    const d=await api('/api/expe/emails?statut='+encodeURIComponent(S.expeEmFiltre||'ouverts'));
    set({expeEmails:d,expeEmLoading:false});
  }catch(e){
    S.expeEmLoading=false;
    showToast(e.message||'Emails indisponibles','danger');
    render();
  }
}

async function expeEmOuvrir(id){
  try{
    const d=await api('/api/expe/emails/'+encodeURIComponent(id));
    set({expeEmModal:d});
  }catch(e){showToast(e.message||'Email introuvable','danger');}
}

async function expeEmMaj(id,vals,silencieux){
  try{
    const d=await api('/api/expe/emails/'+encodeURIComponent(id),{method:'PATCH',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(vals)});
    if(S.expeEmModal&&S.expeEmModal.id===id)S.expeEmModal=d;
    if(!silencieux)showToast('Suivi enregistré.','success');
    await loadExpeEmails();
  }catch(e){showToast(e.message||'Enregistrement impossible','danger');}
}

async function expeEmReclasser(id){
  showToast('Classement en cours…','info');
  try{
    const d=await api('/api/expe/emails/'+encodeURIComponent(id)+'/reclasser',{method:'POST'});
    set({expeEmModal:d});
    if(d.erreur_classement)showToast(d.erreur_classement,'danger');
    else showToast('Email reclassé.','success');
    await loadExpeEmails();
  }catch(e){showToast(e.message||'Classement impossible','danger');}
}

async function expeEmRelever(){
  showToast('Relevé de la boîte…','info');
  try{
    const r=await api('/api/expe/emails/relever',{method:'POST'});
    showToast(r.nouveaux+' nouvel(aux) email(s), '+r.classes+' classé(s).','success');
    await loadExpeEmails();
  }catch(e){showToast(e.message||'Relevé impossible','danger');}
}

async function expeEmTester(){
  set({expeEmTest:{encours:true}});
  try{
    const r=await api('/api/expe/emails/tester',{method:'POST'});
    set({expeEmTest:r});
  }catch(e){set({expeEmTest:{ok:false,message:e.message||'Test impossible'}});}
}

async function expeEmEnregistrerReglages(vals){
  try{
    await api('/api/expe/emails/reglages',{method:'PUT',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(vals)});
    showToast('Réglages enregistrés.','success');
    await loadExpeEmails();
  }catch(e){showToast(e.message||'Enregistrement impossible','danger');}
}

function _expeEmQuand(iso){
  if(!iso)return '';
  const d=new Date(iso);
  if(isNaN(d))return iso;
  const auj=new Date();
  const hm=String(d.getHours()).padStart(2,'0')+':'+String(d.getMinutes()).padStart(2,'0');
  if(d.toDateString()===auj.toDateString())return hm;
  return String(d.getDate()).padStart(2,'0')+'/'+String(d.getMonth()+1).padStart(2,'0')+' '+hm;
}

function _expeEmCat(e){
  if(!e.categorie)return h('span',{className:'expe-em-cat expe-em-cat--aucune'},
    e.erreur_classement?'Non classé':'En cours de tri');
  return h('span',{className:'expe-em-cat expe-em-cat--'+e.categorie},e.categorie_label);
}

function _expeEmCommandes(e){
  const cdes=(e.commandes_rvgi||[]);
  if(!cdes.length)return h('span',{className:'expe-pil-nul'},'—');
  return h('div',null,...cdes.map(function(c){
    return c.connue
      ?h('a',{className:'expe-em-cde',href:'/erp#/commandes?q='+encodeURIComponent(c.numero),
          target:'_blank',rel:'noopener',onClick:function(ev){ev.stopPropagation();},
          title:'Ouvrir la commande dans l’ERP'},c.numero)
      :h('span',{className:'expe-em-cde expe-em-cde--inconnue',title:'Numéro absent du miroir RVGI'},c.numero);
  }));
}

function _expeEmCorrespond(e,q){
  if(!q)return true;
  const t=[e.sujet,e.expediteur,e.expediteur_nom,e.client,e.resume,e.categorie_label,
    ...(e.commandes_rvgi||[]).map(function(c){return c.numero;}),
    ...(e.dossiers||[]).map(function(d){return d.reference;})].join(' ').toLowerCase();
  return q.toLowerCase().split(/\s+/).every(function(m){return !m||t.indexOf(m)>=0;});
}

function _expeEmTuiles(r){
  const t=[
    {lbl:'À traiter',val:r.a_traiter,cls:''},
    {lbl:'Sans réponse depuis '+((S.expeEmails&&S.expeEmails.reglages.delai_relance_h)||24)+' h',
     val:r.en_retard,cls:r.en_retard?'expe-pil-tuile--retard':''},
    {lbl:'En cours',val:r.en_cours,cls:''},
    {lbl:'Réclamations ouvertes',val:r.reclamations,cls:r.reclamations?'expe-pil-tuile--warn':''}
  ];
  return h('div',{className:'expe-pil-tuiles'},
    ...t.map(function(x){
      return h('div',{className:'expe-pil-tuile '+x.cls},
        h('div',{className:'expe-pil-tuile-lbl'},x.lbl),
        h('div',{className:'expe-pil-tuile-val'},String(x.val||0)));
    }));
}

function _expeEmStatutSelect(e){
  const d=S.expeEmails||{};
  const sel=h('select',{className:'expe-em-statut',disabled:!expeCanWrite(),
    onClick:function(ev){ev.stopPropagation();},
    onChange:function(ev){void expeEmMaj(e.id,{statut:ev.target.value},true);}},
    ...Object.keys(d.statuts||{}).map(function(k){
      return h('option',{value:k,selected:e.statut===k},d.statuts[k]);
    }));
  return sel;
}

function _expeEmReglages(d){
  if(!S.expeEmReglagesOuvert){
    return h('div',{className:'expe-pil-reglages'},
      h('button',{type:'button',className:'expe-pil-act',
        onClick:function(){set({expeEmReglagesOuvert:true});}},
        iconEl('sliders',13),' Réglages de l’agent'));
  }
  const r=d.reglages||{};
  const peut=expeCanWrite();
  const actif=h('input',{type:'checkbox',checked:!!r.actif,disabled:!peut,style:{width:'auto'}});
  const delai=h('input',{type:'number',min:'1',max:'240',step:'1',value:String(r.delai_relance_h||24),disabled:!peut});
  const t=S.expeEmTest;
  return h('div',{className:'card expe-pil-reglages'},
    h('div',{className:'card-header'},h('h3',null,'Réglages de l’agent')),
    h('div',{className:'expe-pil-reglages-corps'},
      h('div',{className:'expe-pil-aide',style:{margin:'0 0 14px'}},
        'Toutes les 5 minutes, l’agent lit les nouveaux emails de '+(r.boite||'la boîte')+
        ', les classe et les rapproche des commandes RVGI. Lecture seule : rien n’est modifié dans Outlook.'),
      h('div',{className:'expe-pil-reglages-grid'},
        h('div',null,h('label',null,'Relevé automatique'),
          h('label',{style:{display:'flex',gap:'8px',alignItems:'center',textTransform:'none',
            letterSpacing:'0',fontSize:'13px',color:'var(--text)'}},actif,' Activé')),
        h('div',null,h('label',null,'Relance après (heures)'),delai,
          h('div',{className:'expe-pil-aide'},'Un email « À traiter » plus ancien est signalé en retard.'))),
      t?h('div',{className:'expe-em-reglages-msg'+(t.encours?'':(t.ok?' expe-em-reglages-msg--ok':' expe-em-reglages-msg--ko'))},
          t.encours?'Test en cours…':t.message):null,
      h('div',{className:'expe-pil-reglages-actions'},
        peut?h('button',{type:'button',className:'btn-accent',onClick:function(){
          void expeEmEnregistrerReglages({actif:actif.checked,delai_relance_h:delai.value});
        }},'Enregistrer'):null,
        h('button',{type:'button',className:'expe-pil-act',onClick:function(){void expeEmTester();}},
          'Tester l’accès à la boîte'),
        peut?h('button',{type:'button',className:'expe-pil-act',onClick:function(){void expeEmRelever();}},
          'Relever maintenant'):null,
        h('button',{type:'button',className:'expe-pil-act',
          onClick:function(){set({expeEmReglagesOuvert:false});}},'Fermer'))));
}

function _expeEmModal(){
  const e=S.expeEmModal;
  if(!e)return null;
  const d=S.expeEmails||{};
  const peut=expeCanWrite();
  const fermer=function(){set({expeEmModal:null});};
  const cat=h('select',{disabled:!peut,onChange:function(ev){void expeEmMaj(e.id,{categorie:ev.target.value});}},
    ...(e.categorie?[]:[h('option',{value:'',selected:true},'Non classé')]),
    ...Object.keys(d.categories||{}).map(function(k){
      return h('option',{value:k,selected:e.categorie===k},d.categories[k]);
    }));
  const statut=h('select',{disabled:!peut,onChange:function(ev){void expeEmMaj(e.id,{statut:ev.target.value});}},
    ...Object.keys(d.statuts||{}).map(function(k){
      return h('option',{value:k,selected:e.statut===k},d.statuts[k]);
    }));
  const note=h('textarea',{className:'expe-em-note',disabled:!peut,
    placeholder:'Note de suivi (visible par l’équipe)'});
  note.value=e.note||'';
  const overlay=h('div',{className:'expe-pil-modal-overlay',
    onClick:function(ev){if(ev.target===overlay)fermer();}});
  const infos=[
    e.client?'Client : '+e.client:null,
    e.date_souhaitee?'Date souhaitée : '+e.date_souhaitee.split('-').reverse().join('/'):null,
    e.pris_par?'Pris en charge par '+e.pris_par:null,
    e.a_pj?'Pièce jointe dans Outlook':null
  ].filter(Boolean).join(' · ');
  overlay.appendChild(h('div',{className:'expe-pil-modal expe-pil-modal--large'},
    h('div',{className:'expe-pil-modal-head'},
      h('div',null,
        h('h3',{className:'expe-pil-modal-titre'},e.sujet||'(sans objet)'),
        h('div',{className:'expe-pil-modal-sous'},
          (e.expediteur_nom?e.expediteur_nom+' · ':'')+(e.expediteur||'')+' · '+_expeEmQuand(e.recu_le))),
      h('button',{type:'button',className:'expe-pil-modal-x','aria-label':'Fermer',onClick:fermer},iconEl('x',15))),
    h('div',{className:'expe-pil-modal-corps'},
      e.erreur_classement?h('div',{className:'expe-em-erreur'},'Classement : '+e.erreur_classement):null,
      e.resume?h('div',{className:'expe-em-resume',style:{marginBottom:'10px',fontSize:'13px'}},e.resume):null,
      infos?h('div',{className:'expe-pil-avert'},infos):null,
      h('div',{className:'expe-em-champs'},
        h('div',null,h('label',null,'Statut'),statut),
        h('div',null,h('label',null,'Catégorie'),cat),
        h('div',null,h('label',null,'Commandes RVGI'),_expeEmCommandes(e)),
        (e.dossiers||[]).length?h('div',null,h('label',null,'Dossiers MySifa'),
          h('div',null,...e.dossiers.map(function(x){
            return h('span',{className:'expe-pil-dos-ref'},x.reference||('#'+x.id));
          }))):null),
      h('label',{style:{display:'block',fontSize:'10px',fontWeight:'600',letterSpacing:'.5px',
        textTransform:'uppercase',color:'var(--muted)',marginBottom:'5px'}},'Note'),
      note,
      h('div',{className:'expe-em-corps'},e.corps||e.apercu||'')),
    h('div',{className:'expe-pil-modal-foot'},
      e.lien_outlook?h('a',{className:'expe-pil-act',href:e.lien_outlook,target:'_blank',rel:'noopener'},
        'Ouvrir dans Outlook'):h('span'),
      h('div',{className:'expe-pil-modal-foot-droite'},
        peut?h('button',{type:'button',className:'expe-pil-act',onClick:function(){void expeEmReclasser(e.id);}},
          'Reclasser'):null,
        peut?h('button',{type:'button',className:'btn-accent',onClick:function(){
          void expeEmMaj(e.id,{note:note.value});
        }},'Enregistrer la note'):null))));
  return overlay;
}

function renderExpeEmails(){
  const d=S.expeEmails;
  if(!d){
    return h('div',{className:'card'},h('div',{className:'expe-pil-vide'},
      S.expeEmLoading?'Chargement des emails…':'Aucune donnée.'));
  }
  const filtre=S.expeEmFiltre||'ouverts';
  const q=S.expeEmQ||'';
  const emails=(d.emails||[]).filter(function(e){return _expeEmCorrespond(e,q);});
  const recherche=h('input',{id:'expe-em-search',className:'expe-pil-search',type:'search',
    placeholder:'Rechercher (objet, client, expéditeur, n° de commande…)',value:q,
    onKeyDown:function(ev){if(ev.key==='Escape'){S.expeEmQ='';render();}},
    onInput:function(ev){
      S.expeEmQ=ev.target.value;
      if(_expeEmSearchTimer)clearTimeout(_expeEmSearchTimer);
      _expeEmSearchTimer=setTimeout(function(){
        const pos=ev.target.selectionStart;
        render();
        requestAnimationFrame(function(){
          const el=document.getElementById('expe-em-search');
          if(el){el.focus();try{el.setSelectionRange(pos,pos);}catch(_e){}}
        });
      },250);
    }});
  const barre=h('div',{className:'expe-pil-barre'},
    h('div',{className:'expe-pil-seg'},
      ...EXPE_EM_FILTRES.map(function(f){
        return h('button',{type:'button',className:(filtre===f.key?'on':''),
          onClick:function(){S.expeEmFiltre=f.key;void loadExpeEmails();}},f.label);
      })),
    recherche,
    h('button',{type:'button',className:'expe-pil-act',title:'Recharger',
      onClick:function(){void loadExpeEmails();}},iconEl('rotate-cw',13),' Actualiser'));

  const notes=[];
  if(!d.reglages.actif)notes.push('Relevé automatique désactivé — voir « Réglages de l’agent » en bas de page.');
  if(d.resume.non_classes)notes.push(d.resume.non_classes+' email(s) en attente de classement.');

  const vide=q?'Aucun résultat pour « '+q+' »':'Aucun email ici.';
  const table=h('div',{className:'card'},
    h('div',{className:'expe-pil-wrap'},
      h('table',{className:'expe-pil-table'},
        h('thead',null,h('tr',null,
          ...['Reçu','Expéditeur','Objet','Catégorie','Commandes','Statut'].map(function(x){return h('th',null,x);}))),
        h('tbody',null,
          ...(emails.length?emails.map(function(e){
            return h('tr',{className:'expe-em-row'+(e.en_retard?' expe-pil-row--retard':
                (e.urgence==='haute'&&e.statut==='a_traiter'?' expe-pil-row--urgent':''))+
                (e.statut==='traite'||e.statut==='ignore'?' expe-pil-row--parti':''),
                onClick:function(){void expeEmOuvrir(e.id);}},
              h('td',null,h('div',{className:'expe-pil-quand'},_expeEmQuand(e.recu_le)),
                e.en_retard?h('div',{className:'expe-pil-meta expe-pil-meta--retard'},'sans réponse'):null),
              h('td',null,h('div',{className:'expe-pil-client'},e.client||e.expediteur_nom||e.expediteur),
                h('div',{className:'expe-pil-dest'},e.expediteur)),
              h('td',null,h('div',{className:'expe-em-sujet'},e.sujet||'(sans objet)',
                  e.urgence==='haute'?h('span',{className:'expe-em-urgent'},'urgent'):null,
                  e.a_pj?h('span',{className:'expe-pil-meta',style:{marginLeft:'6px'}},'· PJ'):null),
                e.resume?h('div',{className:'expe-em-resume'},e.resume):null),
              h('td',null,_expeEmCat(e)),
              h('td',null,_expeEmCommandes(e)),
              h('td',null,_expeEmStatutSelect(e),
                e.pris_par?h('div',{className:'expe-pil-meta'},e.pris_par):null));
          }):[h('tr',null,h('td',{colSpan:6},h('div',{className:'expe-pil-vide'},vide)))])))));

  return h('div',null,
    _expeEmTuiles(d.resume||{}),
    notes.length?h('div',{className:'expe-pil-avert'},notes.join('  ·  ')):null,
    barre,
    table,
    _expeEmReglages(d),
    _expeEmModal());
}
"""

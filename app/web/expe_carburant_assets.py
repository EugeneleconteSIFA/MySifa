"""MyExpé — onglet Taxe carburant : CSS/JS injectés dans app/web/html.py.

L'API est dans app/routers/expe_carburant.py, la logique dans
app/services/expe_carburant.py. La saisie du transporteur passe par le
portail transporteur (bloc en tête de son espace).

Ce que l'écran doit dire d'un coup d'oeil : quel taux on applique à chaque
transporteur, de quand il date, et qui n'a pas encore répondu à la dernière
demande. Le taux reste modifiable ici (un transporteur qui l'envoie encore par
email), et toute modification entre dans le même historique que les saisies
du portail.
"""

EXPE_CARBURANT_CSS = r"""
/* ── MyExpé — taxe carburant ── */
.expe-carb-tuiles{display:flex;flex-wrap:wrap;gap:22px;padding:12px 14px;margin-bottom:12px;
  background:var(--card);border:1px solid var(--border);border-radius:10px}
.expe-carb-tuile{min-width:110px}
.expe-carb-tuile-lbl{font-size:10px;font-weight:600;letter-spacing:.4px;text-transform:uppercase;color:var(--muted)}
.expe-carb-tuile-val{font-size:19px;font-weight:700;color:var(--text);line-height:1.2;margin-top:1px}
.expe-carb-tuile--warn .expe-carb-tuile-val{color:var(--warn)}

.expe-carb-barre{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.expe-carb-barre-txt{font-size:12px;color:var(--muted);flex:1;min-width:220px;line-height:1.5}
.expe-carb-btn{display:inline-flex;align-items:center;gap:7px;border-radius:10px;padding:9px 16px;
  font-size:13px;font-weight:700;cursor:pointer;font-family:inherit;border:1px solid var(--accent);
  background:var(--accent);color:white;transition:filter .15s}
.expe-carb-btn:hover{filter:brightness(1.07)}
.expe-carb-btn:disabled{opacity:.5;cursor:not-allowed}
.expe-carb-btn2{display:inline-flex;align-items:center;gap:6px;border-radius:8px;padding:5px 10px;
  font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;border:1px solid var(--border);
  background:var(--bg);color:var(--text2);white-space:nowrap}
.expe-carb-btn2:hover{border-color:var(--accent);color:var(--accent)}
.expe-carb-btn2.on{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}

.expe-carb-card{background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden}
.expe-carb-wrap{overflow-x:auto}
.expe-carb-table{width:100%;border-collapse:collapse;font-size:13px}
.expe-carb-table th{font-size:10px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;
  color:var(--muted);text-align:left;padding:9px 12px;border-bottom:1px solid var(--border);white-space:nowrap}
.expe-carb-table td{padding:9px 12px;border-bottom:1px solid var(--border);vertical-align:middle}
.expe-carb-table tr:last-child td{border-bottom:none}
.expe-carb-row--attente td:first-child{box-shadow:inset 3px 0 0 var(--warn)}
.expe-carb-nom{font-weight:700;color:var(--text)}
.expe-carb-sub{font-size:11px;color:var(--muted);margin-top:1px}
.expe-carb-pct{font-size:16px;font-weight:800;color:var(--text);font-variant-numeric:tabular-nums;white-space:nowrap}
.expe-carb-pct--vide{color:var(--muted);font-weight:600;font-size:13px}
.expe-carb-date{white-space:nowrap}
.expe-carb-vieux{color:var(--warn)}

.expe-carb-pill{display:inline-flex;align-items:center;padding:2px 9px;border-radius:20px;font-size:11px;
  font-weight:700;white-space:nowrap;border:1px solid var(--border);color:var(--muted);background:var(--bg)}
.expe-carb-pill--ok{color:var(--success);border-color:color-mix(in srgb,var(--success) 45%,transparent);
  background:color-mix(in srgb,var(--success) 10%,transparent)}
.expe-carb-pill--attente{color:var(--warn);border-color:color-mix(in srgb,var(--warn) 45%,transparent);
  background:color-mix(in srgb,var(--warn) 10%,transparent)}

.expe-carb-edit{display:flex;gap:6px;align-items:center}
.expe-carb-edit input{width:84px;padding:6px 8px;background:var(--bg);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-size:13px;font-family:inherit;outline:none;text-align:right}
.expe-carb-edit input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}

.expe-carb-hist td{background:var(--bg);padding:10px 16px 12px}
.expe-carb-hist-list{display:flex;flex-direction:column;gap:5px;font-size:12px;color:var(--text2)}
.expe-carb-hist-li{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}
.expe-carb-hist-d{font-family:monospace;font-size:11px;color:var(--muted);min-width:118px}
.expe-carb-hist-v{font-weight:700;color:var(--text)}
.expe-carb-vide{padding:28px;text-align:center;color:var(--muted);font-size:13px}

.expe-carb-ov{position:fixed;inset:0;background:color-mix(in srgb,var(--bg) 60%,transparent);
  z-index:12400;display:flex;align-items:center;justify-content:center;padding:20px;overflow:auto}
.expe-carb-box{background:var(--card);border:1px solid var(--border);border-radius:16px;
  width:min(560px,100%);max-height:calc(100dvh - 60px);display:flex;flex-direction:column;padding:22px 24px}
.expe-carb-box h3{font-size:16px;font-weight:800;color:var(--text);margin:0 0 4px}
.expe-carb-box p{font-size:13px;color:var(--text2);margin:0 0 12px;line-height:1.55}
.expe-carb-sel{display:flex;gap:8px;margin-bottom:8px}
.expe-carb-dest{overflow:auto;border:1px solid var(--border);border-radius:10px;min-height:80px}
.expe-carb-dest label{display:flex;gap:10px;align-items:flex-start;padding:9px 12px;
  border-bottom:1px solid var(--border);cursor:pointer;font-size:13px;color:var(--text)}
.expe-carb-dest label:last-child{border-bottom:none}
.expe-carb-dest label.off{cursor:not-allowed;opacity:.55}
.expe-carb-dest input{margin-top:2px;accent-color:var(--accent)}
.expe-carb-foot{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}
"""

EXPE_CARBURANT_JS = r"""
// ── MyExpé — Taxe carburant ──────────────────────────────────────────────
//
// Toutes les écritures renvoient la liste recalculée par le serveur : l'état
// affiché est toujours celui de la base.

// Au-delà, un taux est signalé comme ancien : la taxe se révise chaque mois
// chez la plupart des transporteurs.
var EXPE_CARB_JOURS_ANCIEN=45;

function _expeCarb(){
  if(!S.expeCarb)S.expeCarb={list:null,loading:false,open:null,hist:{},edit:null,modal:null,sending:false};
  return S.expeCarb;
}

async function loadExpeCarburant(){
  const C=_expeCarb();
  C.loading=true;render();
  try{
    const data=await api('/api/expe/carburant');
    C.list=(data&&data.transporteurs)||[];
  }catch(e){
    showToast(e.message||'Chargement de la taxe carburant impossible','danger');
  }
  C.loading=false;render();
}

function _expeCarbPct(v){
  if(v==null||!isFinite(Number(v)))return '—';
  return String(Number(Number(v).toFixed(2))).replace('.',',')+' %';
}
function _expeCarbJour(iso){
  const m=/^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso||''));
  return m?(m[3]+'/'+m[2]+'/'+m[1]):'—';
}
function _expeCarbHeure(iso){
  const s=String(iso||'');
  return _expeCarbJour(s)+(s.length>=16?(' '+s.slice(11,16)):'');
}
function _expeCarbAge(iso){
  if(!iso)return null;
  const d=new Date(String(iso).slice(0,10)+'T00:00:00');
  if(isNaN(d))return null;
  return Math.floor((Date.now()-d.getTime())/86400000);
}
function _expeCarbQui(email){
  const e=String(email||'');
  return e.indexOf('@')>0?e.split('@')[0]:e;
}

function _expeCarbStatut(t){
  if(t.statut==='en_attente')return h('span',{className:'expe-carb-pill expe-carb-pill--attente',
    title:'Demande envoyée le '+_expeCarbJour(t.demande_le)+', pas de saisie depuis'},'En attente');
  if(t.statut==='a_jour')return h('span',{className:'expe-carb-pill expe-carb-pill--ok'},'À jour');
  // Un taux présent sans date vient d'avant le suivi : il existe, on ne sait
  // juste pas de quand il date.
  if(t.pct)return h('span',{className:'expe-carb-pill',title:'Taux saisi avant la mise en place du suivi'},'Non datée');
  return h('span',{className:'expe-carb-pill'},'Jamais renseignée');
}

// ── Actions ─────────────────────────────────────────────────────────────

async function expeCarbToggleHist(id){
  const C=_expeCarb();
  if(C.open===id){C.open=null;render();return;}
  C.open=id;render();
  await _expeCarbChargerHist(id);
}

async function _expeCarbChargerHist(id){
  const C=_expeCarb();
  try{
    const data=await api('/api/expe/carburant/'+id+'/historique');
    C.hist[id]=(data&&data.historique)||[];
  }catch(e){showToast(e.message||'Historique indisponible','danger');}
  render();
}

async function expeCarbEnregistrer(t){
  const C=_expeCarb();
  const inp=document.getElementById('expe-carb-in-'+t.id);
  const raw=String(inp?inp.value:'').replace(',','.').trim();
  const pct=parseFloat(raw);
  if(raw===''||!isFinite(pct)||pct<0||pct>100){
    showToast('Taux invalide — valeur entre 0 et 100 %.','danger');return;
  }
  try{
    await api('/api/expe/transporteurs/'+t.id,{
      method:'PUT',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({taxe_carburant_pct:pct})
    });
    C.edit=null;
    delete C.hist[t.id];
    // La fiche transporteur en mémoire porte aussi le taux (comparateur).
    if(typeof T!=='undefined'&&T.list){
      const f=T.list.find(x=>x.id===t.id);if(f)f.taxe_carburant_pct=pct;
    }
    showToast('Taxe carburant enregistrée.','success');
    await loadExpeCarburant();
    if(C.open===t.id)await _expeCarbChargerHist(t.id);
  }catch(e){showToast(e.message||'Enregistrement impossible','danger');}
}

function expeCarbOuvrirDemande(){
  const C=_expeCarb();
  const avecEmail=(C.list||[]).filter(t=>(t.emails||[]).length);
  C.modal={sel:new Set(avecEmail.map(t=>t.id))};
  render();
}

async function expeCarbEnvoyer(){
  const C=_expeCarb();
  if(!C.modal||C.sending)return;
  const ids=Array.from(C.modal.sel);
  if(!ids.length){showToast('Aucun transporteur sélectionné.','danger');return;}
  C.sending=true;render();
  try{
    const r=await api('/api/expe/carburant/demander',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({transporteur_ids:ids})
    });
    C.list=(r&&r.transporteurs)||C.list;
    C.modal=null;
    const n=(r&&r.envoyes||[]).length, ko=(r&&r.echecs||[]).length;
    if(ko)showToast('Demande envoyée à '+n+' transporteur(s). Échec : '+r.echecs.join(', ')+'.','danger');
    else showToast('Demande envoyée à '+n+' transporteur(s).','success');
  }catch(e){showToast(e.message||'Envoi impossible','danger');}
  C.sending=false;render();
}

// ── Rendu ───────────────────────────────────────────────────────────────

function _expeCarbTuiles(list){
  const n=k=>list.filter(t=>t.statut===k).length;
  const renseignes=list.filter(t=>t.maj_le||t.pct);
  const moy=renseignes.length?renseignes.reduce((s,t)=>s+Number(t.pct||0),0)/renseignes.length:null;
  const anciens=list.filter(_expeCarbAncien).length;
  const tuiles=[
    {lbl:'Transporteurs actifs',val:String(list.length)},
    {lbl:'À jour',val:String(n('a_jour'))},
    {lbl:'En attente de réponse',val:String(n('en_attente')),cls:n('en_attente')?'expe-carb-tuile--warn':''},
    {lbl:'Jamais mise à jour',val:String(n('jamais'))},
    {lbl:'Taux de plus de '+EXPE_CARB_JOURS_ANCIEN+' j',val:String(anciens),cls:anciens?'expe-carb-tuile--warn':''},
    {lbl:'Taux moyen',val:moy==null?'—':_expeCarbPct(moy)}
  ];
  // Widget d'accueil (app/services/blocs_registre.py) : mêmes chiffres que
  // les tuiles, recalculés par la source sur la même API.
  const bloc={
    'data-bloc':'expe.carburant.resume',
    'data-bloc-valeur-actifs':String(list.length),
    'data-bloc-valeur-a-jour':String(n('a_jour')),
    'data-bloc-valeur-en-attente':String(n('en_attente')),
    'data-bloc-valeur-jamais':String(n('jamais')),
    'data-bloc-valeur-anciens':String(anciens),
    'data-bloc-valeur-moyen':moy==null?'—':_expeCarbPct(moy)
  };
  if(moy!=null)bloc['data-bloc-nombre-moyen']=String(Number(moy.toFixed(2)));
  return h('div',Object.assign({className:'expe-carb-tuiles'},bloc),
    ...tuiles.map(x=>h('div',{className:'expe-carb-tuile '+(x.cls||'')},
      h('div',{className:'expe-carb-tuile-lbl'},x.lbl),
      h('div',{className:'expe-carb-tuile-val'},x.val))));
}

function _expeCarbCellulePct(t){
  const C=_expeCarb();
  if(C.edit===t.id){
    const inp=h('input',{type:'number',step:'0.01',min:'0',max:'100',id:'expe-carb-in-'+t.id,
      value:String(t.pct),inputmode:'decimal'});
    inp.addEventListener('keydown',e=>{
      if(e.key==='Enter')void expeCarbEnregistrer(t);
      if(e.key==='Escape'){C.edit=null;render();}
    });
    setTimeout(()=>{try{inp.focus();inp.select();}catch(_){}},0);
    return h('td',null,h('div',{className:'expe-carb-edit'},inp,
      h('button',{type:'button',className:'expe-carb-btn2 on',onClick:()=>void expeCarbEnregistrer(t)},'OK'),
      h('button',{type:'button',className:'expe-carb-btn2',onClick:()=>{C.edit=null;render();}},'Annuler')));
  }
  const vide=!t.maj_le&&!t.pct;
  return h('td',null,
    h('span',{className:'expe-carb-pct'+(vide?' expe-carb-pct--vide':'')},vide?'Non renseignée':_expeCarbPct(t.pct)));
}

// Taux saisi il y a plus de EXPE_CARB_JOURS_ANCIEN jours.
function _expeCarbAncien(t){
  const age=_expeCarbAge(t.maj_le);
  return age!=null&&age>EXPE_CARB_JOURS_ANCIEN;
}

// Libellé du statut, tel que la pastille l'affiche (_expeCarbStatut).
function _expeCarbStatutTexte(t){
  if(t.statut==='en_attente')return 'En attente';
  if(t.statut==='a_jour')return 'À jour';
  return t.pct?'Non datée':'Jamais renseignée';
}

// Ligne d'un transporteur, capturable en widget d'accueil : l'objet suivi est
// l'id du transporteur dans le référentiel.
function _expeCarbBloc(t){
  const vide=!t.maj_le&&!t.pct;
  const age=_expeCarbAge(t.maj_le);
  const b={
    'data-bloc':'expe.carburant.transporteur',
    'data-bloc-objet':String(t.id),
    'data-bloc-objet-libelle':t.nom||'',
    'data-bloc-valeur-taux':vide?'Non renseignée':_expeCarbPct(t.pct),
    'data-bloc-valeur-statut':_expeCarbStatutTexte(t),
    'data-bloc-valeur-maj':t.maj_le?_expeCarbJour(t.maj_le):'—',
    'data-bloc-valeur-age':age==null?'—':(age+' j')
  };
  if(!vide)b['data-bloc-nombre-taux']=String(Number(Number(t.pct||0).toFixed(2)));
  if(age!=null)b['data-bloc-nombre-age']=String(age);
  return b;
}

function _expeCarbLigne(t){
  const C=_expeCarb();
  const age=_expeCarbAge(t.maj_le);
  const ancien=_expeCarbAncien(t);
  const majCell=t.maj_le
    ? h('td',{className:'expe-carb-date'},
        h('div',{className:ancien?'expe-carb-vieux':'',
          title:ancien?('Taux saisi il y a '+age+' jours'):''},_expeCarbJour(t.maj_le)),
        h('div',{className:'expe-carb-sub'},
          (t.maj_source==='portail'?'Portail':'Manuel')+(t.maj_par?(' · '+_expeCarbQui(t.maj_par)):'')))
    : h('td',{className:'expe-carb-date'},h('span',{className:'expe-carb-sub'},'—'));
  const demCell=t.demande_le
    ? h('td',{className:'expe-carb-date'},_expeCarbJour(t.demande_le),
        t.demande_par?h('div',{className:'expe-carb-sub'},_expeCarbQui(t.demande_par)):null)
    : h('td',{className:'expe-carb-date'},h('span',{className:'expe-carb-sub'},'—'));
  const actions=h('td',{style:{whiteSpace:'nowrap',textAlign:'right'}},
    expeCanWrite()&&C.edit!==t.id
      ?h('button',{type:'button',className:'expe-carb-btn2',title:'Saisir le taux à la main',
          onClick:()=>{C.edit=t.id;render();}},iconEl('pencil',12),' Modifier')
      :null,
    ' ',
    h('button',{type:'button',className:'expe-carb-btn2'+(C.open===t.id?' on':''),
      onClick:()=>void expeCarbToggleHist(t.id)},iconEl('clock',12),' Historique'));
  const rows=[h('tr',Object.assign({className:t.statut==='en_attente'?'expe-carb-row--attente':''},_expeCarbBloc(t)),
    h('td',null,h('div',{className:'expe-carb-nom'},t.nom),
      h('div',{className:'expe-carb-sub'},(t.emails||[]).length?((t.emails.length)+' contact(s) email'):'Aucun email de contact')),
    _expeCarbCellulePct(t),
    majCell,
    demCell,
    h('td',null,_expeCarbStatut(t)),
    actions)];
  if(C.open===t.id)rows.push(_expeCarbHistorique(t));
  return rows;
}

function _expeCarbHistorique(t){
  const C=_expeCarb();
  const hist=C.hist[t.id];
  let contenu;
  if(!hist)contenu=h('div',{className:'expe-carb-sub'},'Chargement…');
  else if(!hist.length)contenu=h('div',{className:'expe-carb-sub'},'Aucun événement enregistré.');
  else contenu=h('div',{className:'expe-carb-hist-list'},...hist.map(ev=>{
    let txt;
    if(ev.evenement==='demande'){
      txt=[h('span',null,'Demande de mise à jour envoyée'+(ev.auteur?(' par '+_expeCarbQui(ev.auteur)):''))];
    }else{
      const avant=ev.pct_avant!=null?(_expeCarbPct(ev.pct_avant)+' → '):'';
      txt=[h('span',{className:'expe-carb-hist-v'},avant+_expeCarbPct(ev.pct)),
        h('span',null,(ev.source==='portail'?'saisi sur le portail':'saisi à la main')+(ev.auteur?(' par '+ev.auteur):''))];
    }
    return h('div',{className:'expe-carb-hist-li'},h('span',{className:'expe-carb-hist-d'},_expeCarbHeure(ev.created_at)),...txt);
  }));
  return h('tr',{className:'expe-carb-hist'},h('td',{colSpan:'6'},contenu));
}

function renderExpeCarburant(){
  const C=_expeCarb();
  // Chargé par renderExpe() à chaque entrée dans l'onglet.
  if(C.list===null){
    return h('div',null,h('div',{className:'expe-carb-vide'},'Chargement…'));
  }
  const list=C.list;
  const barre=h('div',{className:'expe-carb-barre'},
    h('div',{className:'expe-carb-barre-txt'},
      'Pourcentage ajouté au prix de grille par le comparateur, sauf si la grille porte déjà une ligne gasoil. '
      +'Chaque transporteur peut le renseigner lui-même depuis son espace sur le portail transporteur.'),
    expeCanWrite()
      ?h('button',{type:'button',className:'expe-carb-btn',onClick:expeCarbOuvrirDemande,disabled:!list.length},
          iconEl('send',14),'Demander la mise à jour')
      :null);
  const table=list.length
    ? h('div',{className:'expe-carb-wrap'},h('table',{className:'expe-carb-table'},
        h('thead',null,h('tr',null,
          h('th',null,'Transporteur'),h('th',null,'Taxe carburant'),h('th',null,'Mise à jour'),
          h('th',null,'Dernière demande'),h('th',null,'Statut'),h('th',null,''))),
        h('tbody',null,...list.flatMap(_expeCarbLigne))))
    : h('div',{className:'expe-carb-vide'},'Aucun transporteur actif dans le référentiel.');
  return h('div',null,_expeCarbTuiles(list),barre,h('div',{className:'expe-carb-card'},table));
}

function renderExpeCarburantModal(){
  const C=S.expeCarb;
  if(!C||!C.modal)return null;
  const sel=C.modal.sel;
  const list=C.list||[];
  const fermer=()=>{if(!C.sending){C.modal=null;render();}};
  const ov=h('div',{className:'expe-carb-ov'});
  ov.addEventListener('click',e=>{if(e.target===ov)fermer();});
  const avecEmail=list.filter(t=>(t.emails||[]).length);
  const dest=h('div',{className:'expe-carb-dest'},...list.map(t=>{
    const ok=(t.emails||[]).length>0;
    const cb=h('input',{type:'checkbox',checked:ok&&sel.has(t.id),disabled:!ok});
    cb.addEventListener('change',()=>{if(cb.checked)sel.add(t.id);else sel.delete(t.id);render();});
    return h('label',{className:ok?'':'off'},cb,
      h('div',null,h('div',{style:{fontWeight:'700'}},t.nom),
        h('div',{className:'expe-carb-sub'},ok?t.emails.join(', '):'Aucun email de contact — à compléter dans la fiche transporteur')));
  }));
  const n=sel.size;
  ov.appendChild(h('div',{className:'expe-carb-box'},
      h('h3',null,'Demander la taxe carburant'),
      h('p',null,'Chaque transporteur reçoit un email qui ouvre son espace sur le portail, où il saisit son taux. '
        +'Vous recevez un email de confirmation à chaque saisie.'),
      h('div',{className:'expe-carb-sel'},
        h('button',{type:'button',className:'expe-carb-btn2',onClick:()=>{avecEmail.forEach(t=>sel.add(t.id));render();}},'Tout cocher'),
        h('button',{type:'button',className:'expe-carb-btn2',onClick:()=>{sel.clear();render();}},'Tout décocher'),
        h('button',{type:'button',className:'expe-carb-btn2',
          onClick:()=>{sel.clear();list.filter(t=>t.statut!=='a_jour'&&(t.emails||[]).length).forEach(t=>sel.add(t.id));render();}},
          'Sans réponse seulement')),
      dest,
      h('div',{className:'expe-carb-foot'},
        h('button',{type:'button',className:'expe-carb-btn2',onClick:fermer,disabled:C.sending},'Annuler'),
        h('button',{type:'button',className:'expe-carb-btn',onClick:()=>void expeCarbEnvoyer(),disabled:C.sending||!n},
          iconEl('send',14),C.sending?'Envoi en cours…':('Envoyer à '+n+' transporteur'+(n>1?'s':''))))));
  return ov;
}
"""

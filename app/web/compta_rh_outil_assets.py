"""MyCompta — onglet « Outil RH » : CSS et JS.

Concaténés en tête de COMPTA_MAIN_CSS / COMPTA_MAIN_JS (app/web/compta_assets.py).
API : app/routers/rh_outil.py.

Les fenêtres (choix d'un employé, d'une formation, catalogue, confirmation)
sont construites hors de render() et posées sur <body>, comme dans
Maintenance : un re-render de MyCompta (toast, rechargement de la liste) ne
les ferme pas et ne fait pas perdre la saisie en cours.
"""

RH_OUTIL_CSS = r"""
/* MyCompta — Outil RH */
.rho-bar{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-bottom:12px}
.rho-tag{display:inline-block;font-size:10px;font-weight:600;color:var(--muted);border:1px solid var(--border);border-radius:5px;padding:1px 6px;margin-left:8px;vertical-align:middle}
.rho-search,.rho-input{width:100%;box-sizing:border-box;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:14px;font-family:inherit;outline:none}
.rho-search{margin-bottom:10px}
.rho-search:focus,.rho-input:focus{border-color:var(--accent)}
.rho-list{max-height:360px;overflow-y:auto;display:flex;flex-direction:column;gap:4px}
.rho-emp{display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:var(--bg);border:1px solid var(--border);border-radius:9px;padding:9px 12px;color:var(--text);font-family:inherit;font-size:13px;cursor:pointer}
.rho-emp:hover{border-color:var(--accent)}
.rho-emp[disabled]{cursor:default;opacity:.55}
.rho-emp[disabled]:hover{border-color:var(--border)}
.rho-sub{font-size:11px;color:var(--muted)}
.rho-empty{padding:18px;text-align:center;color:var(--muted);font-size:13px}
.rho-table{width:100%;border-collapse:collapse;font-size:13px}
.rho-table th{text-align:left;font-size:10px;font-weight:600;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;padding:10px 16px;border-bottom:1px solid var(--border)}
.rho-table td{padding:10px 16px;border-bottom:1px solid var(--border);vertical-align:top}
.rho-table tr:last-child td{border-bottom:none}
.rho-table .rho-c{text-align:center;width:1%;white-space:nowrap}
.rho-table input[type=checkbox],.rho-form input[type=checkbox]{width:16px;height:16px;accent-color:var(--accent);cursor:pointer;flex-shrink:0;margin:0}
.rho-del{padding:5px 8px;border-radius:6px;border:1px solid rgba(248,113,113,.3);background:transparent;cursor:pointer;color:var(--danger);display:inline-flex;align-items:center}
.rho-del:hover{background:rgba(248,113,113,.12)}
/* Colonne Formations : une ligne par formation de l'employé */
.rho-forms{display:flex;flex-direction:column;gap:4px;min-width:200px}
.rho-form{display:flex;align-items:center;gap:8px;padding:2px 0}
.rho-form .rho-form-lbl{flex:1;cursor:pointer;color:var(--text2)}
.rho-form.done .rho-form-lbl{color:var(--muted);text-decoration:line-through}
.rho-form-x{border:none;background:transparent;color:var(--muted);cursor:pointer;font-size:15px;line-height:1;padding:2px 5px;border-radius:5px;opacity:0;transition:opacity .15s}
.rho-form:hover .rho-form-x,.rho-form-x:focus-visible{opacity:1}
.rho-form-x:hover{color:var(--danger);background:rgba(248,113,113,.12)}
@media (hover:none){.rho-form-x{opacity:1}}
.rho-form-add{align-self:flex-start;border:1px dashed var(--border);background:transparent;color:var(--muted);border-radius:6px;padding:3px 9px;font-size:11px;font-weight:600;cursor:pointer;font-family:inherit;display:inline-flex;align-items:center;gap:4px;margin-top:2px}
.rho-form-add:hover{border-color:var(--accent);color:var(--accent)}
.rho-form-none{font-size:12px;color:var(--muted)}
/* Catalogue */
.rho-cat-row{display:flex;align-items:center;gap:8px}
.rho-cat-row .rho-input{padding:8px 12px;font-size:13px}
.rho-cat-row .rho-sub{white-space:nowrap;min-width:78px;text-align:right}
.rho-cat-add{display:flex;gap:8px;margin-top:12px}
/* Fenêtres : même dessin que les modales de suppression de Maintenance */
.rho-ov{position:fixed;inset:0;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center}
.rho-dlg{position:relative;max-width:520px;width:calc(100% - 40px);max-height:calc(100vh - 40px);overflow-y:auto;box-sizing:border-box;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:22px;box-shadow:0 20px 50px rgba(0,0,0,.4)}
.rho-dlg-title{color:var(--text);font-size:16px;font-weight:700;margin:0 0 14px;padding-right:30px}
.rho-dlg-title.danger{color:var(--danger);display:flex;align-items:center;gap:8px}
.rho-dlg-close{position:absolute;top:16px;right:16px;border:1px solid var(--border);background:var(--card);color:var(--muted);border-radius:8px;width:28px;height:28px;cursor:pointer;font-size:16px;line-height:1}
.rho-dlg-close:hover{color:var(--text)}
.rho-confirm-sum{padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-bottom:14px}
.rho-confirm-txt{font-size:13px;color:var(--text);line-height:1.5;margin-bottom:16px}
.rho-confirm-act{display:flex;justify-content:flex-end;gap:10px}
.rho-confirm-act button{border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer;font-family:inherit;font-size:13px}
.rho-confirm-act .rho-cancel{background:var(--card);color:var(--text);border:1px solid var(--border)}
.rho-confirm-act .rho-ok{background:var(--danger);color:#fff;border:none}
.rho-confirm-act button[disabled]{opacity:.6;cursor:default}
"""

RH_OUTIL_JS = r"""
// ══════════════════════════════════════════════════════════════════
// ── OUTIL RH (onglet MyCompta) ────────────────────────────────────
// ══════════════════════════════════════════════════════════════════
// Même droit que MyCompta : qui voit MyCompta voit l'onglet. Le serveur
// vérifie le même accès (app/routers/rh_outil.py).

// Cases fixes de la checklist, dans l'ordre d'affichage. Chaque clé est un
// champ de l'API (CHECKLIST dans app/routers/rh_outil.py). La colonne
// Formations est à part : sa liste varie d'un employé à l'autre.
const RH_OUTIL_COLONNES=[
  {cle:'reglement_signe',label:'Règlement signé'},
];

function rhOutilJson(method,body){
  return {method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)};
}

async function rhOutilLoad(){
  try{
    const d=await api('/api/rh-outil/membres');
    if(!d)return;
    set({rhOutilMembres:d.membres||[],rhOutilLoaded:true});
  }catch(e){toast(e.message,'error');}
}

// ── Fenêtres ──────────────────────────────────────────────────────
// Une pile : Échap et le clic à côté ne ferment que la fenêtre du dessus.
function rhOutilFenetre(){
  const ov=h('div',{className:'rho-ov'});
  ov.style.zIndex=String(12000+document.querySelectorAll('.rho-ov').length*10);
  const auDessus=()=>{const all=document.querySelectorAll('.rho-ov');return all[all.length-1]===ov;};
  const onKey=e=>{if(e.key==='Escape'&&auDessus()){e.preventDefault();e.stopPropagation();fermer();}};
  const fermer=()=>{document.removeEventListener('keydown',onKey,true);ov.remove();};
  document.addEventListener('keydown',onKey,true);
  ov.addEventListener('click',e=>{if(e.target===ov)fermer();});
  return {ov,fermer};
}
function rhOutilDialogue(titre,fermer,...enfants){
  return h('div',{className:'rho-dlg',role:'dialog','aria-modal':'true'},
    h('button',{type:'button',className:'rho-dlg-close','aria-label':'Fermer',onClick:fermer},'×'),
    h('h3',{className:'rho-dlg-title'},titre),
    ...enfants
  );
}

// Confirmation de suppression. opts : {titre, nom, sous, texte, label, onConfirm}
// onConfirm lève une erreur pour garder la fenêtre ouverte.
function rhOutilConfirmer(opts){
  const {ov,fermer}=rhOutilFenetre();
  const cancel=h('button',{type:'button',className:'rho-cancel',onClick:fermer},'Annuler');
  const ok=h('button',{type:'button',className:'rho-ok'},opts.label||'Supprimer');
  ok.addEventListener('click',async()=>{
    ok.disabled=true;cancel.disabled=true;
    try{await opts.onConfirm();fermer();}
    catch(_){ok.disabled=false;cancel.disabled=false;}
  });
  ov.appendChild(h('div',{className:'rho-dlg',role:'dialog','aria-modal':'true'},
    h('div',{className:'rho-dlg-title danger'},iconEl('trash',18),opts.titre),
    h('div',{className:'rho-confirm-sum'},
      h('div',{style:{fontSize:'13px',fontWeight:'600',color:'var(--text)'}},opts.nom||'—'),
      opts.sous?h('div',{className:'rho-sub'},opts.sous):null
    ),
    h('div',{className:'rho-confirm-txt'},opts.texte||''),
    h('div',{className:'rho-confirm-act'},cancel,ok)
  ));
  document.body.appendChild(ov);
  requestAnimationFrame(()=>cancel.focus());
}

// Liste filtrable. opts : {titre, placeholder, items:[{label,sub,tags,disabled,valeur}],
// vide, onPick(valeur)} — onPick lève une erreur pour garder la fenêtre ouverte.
function rhOutilChoisir(opts){
  const {ov,fermer}=rhOutilFenetre();
  const items=opts.items||[];
  const listEl=h('div',{className:'rho-list'});
  const remplir=q=>{
    const n=String(q||'').trim().toLowerCase();
    const vis=items.filter(it=>!n||String(it.label||'').toLowerCase().includes(n)||String(it.sub||'').toLowerCase().includes(n));
    listEl.replaceChildren(...(vis.length?vis.map(it=>h('button',{type:'button',className:'rho-emp',disabled:!!it.disabled,onClick:async()=>{
        if(it.disabled)return;
        try{await opts.onPick(it.valeur);fermer();}catch(_){}
      }},
      h('div',{style:{flex:1}},
        h('div',null,it.label||'—',...(it.tags||[]).map(t=>h('span',{className:'rho-tag'},t))),
        it.sub?h('div',{className:'rho-sub'},it.sub):null
      )
    )):[h('div',{className:'rho-empty'},items.length?'Aucun résultat.':(opts.vide||'Liste vide.'))]));
  };
  // type=search, pas de « email » / « utilisateur » autour du champ : sinon
  // Safari le prend pour un identifiant et propose les mots de passe.
  const search=h('input',{type:'search',name:'rho-recherche',className:'rho-search',placeholder:opts.placeholder||'Rechercher…',
    autocomplete:'off',autocorrect:'off',autocapitalize:'off',spellcheck:'false','data-1p-ignore':'','data-lpignore':'true','data-form-type':'other'});
  search.addEventListener('input',()=>remplir(search.value));
  remplir('');
  ov.appendChild(rhOutilDialogue(opts.titre,fermer,search,listEl));
  document.body.appendChild(ov);
  requestAnimationFrame(()=>search.focus());
}

// ── Employés ──────────────────────────────────────────────────────
async function rhOutilAjouterEmploye(){
  let d;
  try{d=await api('/api/rh-outil/employes');}catch(e){toast(e.message,'error');return;}
  if(!d)return;
  rhOutilChoisir({
    titre:'Ajouter un employé',
    placeholder:'Rechercher un employé…',
    vide:'Aucun compte.',
    items:(d.employes||[]).map(e=>({
      valeur:e.user_id,label:e.nom,sub:e.email,disabled:e.deja_ajoute,
      tags:[e.actif?null:'Désactivé',e.deja_ajoute?'Déjà ajouté':null].filter(Boolean),
    })),
    onPick:async userId=>{
      try{
        await api('/api/rh-outil/membres',rhOutilJson('POST',{user_id:userId}));
      }catch(e){toast(e.message,'error');throw e;}
      await rhOutilLoad();
      toast('Employé ajouté.');
    },
  });
}
function rhOutilRetirerEmploye(m){
  rhOutilConfirmer({
    titre:'Retirer cet employé ?',nom:m.nom,sous:m.email,label:'Retirer',
    texte:'L’employé sort de la liste de l’Outil RH, avec sa checklist et ses formations. Son compte MySifa n’est pas touché.',
    onConfirm:async()=>{
      try{await api('/api/rh-outil/membres/'+m.id,{method:'DELETE'});}
      catch(e){toast(e.message,'error');throw e;}
      await rhOutilLoad();
      toast('Employé retiré.');
    },
  });
}
async function rhOutilCocher(m,cle,box){
  const v=box.checked;
  try{
    await api('/api/rh-outil/membres/'+m.id,rhOutilJson('PATCH',{[cle]:v}));
    m[cle]=v;
  }catch(e){box.checked=!v;toast(e.message,'error');}
}

// ── Formations d'un employé ───────────────────────────────────────
async function rhOutilAttribuer(m){
  let d;
  try{d=await api('/api/rh-outil/formations');}catch(e){toast(e.message,'error');return;}
  if(!d)return;
  const cat=d.formations||[];
  if(!cat.length){toast('Catalogue vide — ajoutez des formations avec « Gérer les formations ».','error');return;}
  const deja=new Set((m.formations||[]).map(f=>f.formation_id));
  rhOutilChoisir({
    titre:'Formation pour '+(m.nom||'cet employé'),
    placeholder:'Rechercher une formation…',
    items:cat.map(f=>({valeur:f.id,label:f.libelle,disabled:deja.has(f.id),tags:deja.has(f.id)?['Déjà attribuée']:[]})),
    onPick:async formationId=>{
      try{await api('/api/rh-outil/membres/'+m.id+'/formations',rhOutilJson('POST',{formation_id:formationId}));}
      catch(e){toast(e.message,'error');throw e;}
      await rhOutilLoad();
    },
  });
}
async function rhOutilCocherFormation(f,box,ligne){
  const v=box.checked;
  try{
    await api('/api/rh-outil/membre-formations/'+f.id,rhOutilJson('PATCH',{fait:v}));
    f.fait=v;ligne.classList.toggle('done',v);
  }catch(e){box.checked=!v;toast(e.message,'error');}
}
async function rhOutilRetirerFormation(m,f){
  const retirer=async()=>{
    try{await api('/api/rh-outil/membre-formations/'+f.id,{method:'DELETE'});}
    catch(e){toast(e.message,'error');throw e;}
    await rhOutilLoad();
  };
  // Une formation pas encore faite se retire sans confirmation : rien n'est perdu.
  if(!f.fait){try{await retirer();}catch(_){}return;}
  rhOutilConfirmer({
    titre:'Retirer cette formation ?',nom:f.libelle,sous:m.nom,label:'Retirer',
    texte:'La formation est cochée comme faite : ce suivi sera perdu pour cet employé. Le catalogue n’est pas modifié.',
    onConfirm:retirer,
  });
}

// ── Catalogue des formations ──────────────────────────────────────
function rhOutilCatalogue(){
  const {ov,fermer}=rhOutilFenetre();
  const listEl=h('div',{className:'rho-list'},h('div',{className:'rho-empty'},'Chargement…'));
  // Après chaque changement : le catalogue se redessine seul, le tableau
  // dessous est rechargé (intitulés et formations supprimées).
  const rafraichir=async()=>{
    let d;
    try{d=await api('/api/rh-outil/formations');}catch(e){toast(e.message,'error');return;}
    if(!d)return;
    const cat=d.formations||[];
    listEl.replaceChildren(...(cat.length?cat.map(f=>{
      const inp=h('input',{type:'text',className:'rho-input',value:f.libelle,maxlength:'120','aria-label':'Intitulé',
        autocomplete:'off','data-1p-ignore':'','data-lpignore':'true','data-form-type':'other'});
      const enregistrer=async()=>{
        const v=inp.value.trim();
        if(!v||v===f.libelle){inp.value=f.libelle;return;}
        try{
          await api('/api/rh-outil/formations/'+f.id,rhOutilJson('PUT',{libelle:v}));
          f.libelle=v;inp.value=v;
          rhOutilLoad();
          toast('Formation renommée.');
        }catch(e){inp.value=f.libelle;toast(e.message,'error');}
      };
      inp.addEventListener('keydown',e=>{
        if(e.key==='Enter'){e.preventDefault();inp.blur();}
        else if(e.key==='Escape'){e.preventDefault();e.stopPropagation();inp.value=f.libelle;inp.blur();}
      });
      inp.addEventListener('blur',enregistrer);
      const nb=f.nb_employes;
      return h('div',{className:'rho-cat-row'},
        inp,
        h('span',{className:'rho-sub'},nb+' employé'+(nb>1?'s':'')),
        h('button',{type:'button',className:'rho-del',title:'Supprimer du catalogue',onClick:()=>rhOutilConfirmer({
          titre:'Supprimer cette formation ?',nom:f.libelle,label:'Supprimer',
          sous:nb?(nb+' employé'+(nb>1?'s l’ont':' l’a')+' dans sa liste'):'Attribuée à aucun employé',
          texte:nb?'Elle disparaît du catalogue et de la liste de chaque employé qui l’a, avec son suivi.':'Elle disparaît du catalogue.',
          onConfirm:async()=>{
            try{await api('/api/rh-outil/formations/'+f.id,{method:'DELETE'});}
            catch(e){toast(e.message,'error');throw e;}
            await rafraichir();rhOutilLoad();
            toast('Formation supprimée.');
          },
        })},iconEl('trash',13))
      );
    }):[h('div',{className:'rho-empty'},'Aucune formation au catalogue.')]));
  };
  const nouv=h('input',{type:'text',className:'rho-input',placeholder:'Nouvelle formation…',maxlength:'120',
    autocomplete:'off','data-1p-ignore':'','data-lpignore':'true','data-form-type':'other'});
  const ajouter=async()=>{
    const v=nouv.value.trim();
    if(!v)return;
    try{
      await api('/api/rh-outil/formations',rhOutilJson('POST',{libelle:v}));
      nouv.value='';
      await rafraichir();
      nouv.focus();
    }catch(e){toast(e.message,'error');}
  };
  nouv.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();ajouter();}});
  ov.appendChild(rhOutilDialogue('Catalogue des formations',fermer,
    listEl,
    h('div',{className:'rho-cat-add'},nouv,h('button',{type:'button',className:'btn-sm',onClick:ajouter},iconEl('plus',13),' Ajouter'))
  ));
  document.body.appendChild(ov);
  rafraichir();
  requestAnimationFrame(()=>nouv.focus());
}

// ── Onglet ────────────────────────────────────────────────────────
function rhOutilCelluleFormations(m){
  const forms=m.formations||[];
  return h('div',{className:'rho-forms'},
    ...(forms.length?forms.map(f=>{
      const box=h('input',{type:'checkbox',checked:!!f.fait,'aria-label':f.libelle+' · '+(m.nom||'')});
      const ligne=h('div',{className:'rho-form'+(f.fait?' done':'')},
        box,
        h('span',{className:'rho-form-lbl'},f.libelle),
        h('button',{type:'button',className:'rho-form-x',title:'Retirer cette formation',onClick:()=>rhOutilRetirerFormation(m,f)},'×')
      );
      box.addEventListener('change',()=>rhOutilCocherFormation(f,box,ligne));
      ligne.querySelector('.rho-form-lbl').addEventListener('click',()=>{box.checked=!box.checked;rhOutilCocherFormation(f,box,ligne);});
      return ligne;
    }):[h('div',{className:'rho-form-none'},'Aucune formation')]),
    h('button',{type:'button',className:'rho-form-add',onClick:()=>rhOutilAttribuer(m)},iconEl('plus',11),'Formation')
  );
}

function renderRhOutilTab(){
  const list=S.rhOutilMembres||[];
  const bar=h('div',{className:'rho-bar'},
    h('button',{type:'button',className:'btn-ghost btn-sm',onClick:rhOutilCatalogue},iconEl('sliders',13),' Gérer les formations'),
    h('button',{type:'button',className:'btn-sm',onClick:rhOutilAjouterEmploye},iconEl('plus',13),' Ajouter un utilisateur')
  );
  if(!S.rhOutilLoaded)return h('div',null,bar,h('div',{className:'card-empty'},'Chargement…'));
  if(!list.length)return h('div',null,bar,h('div',{className:'card-empty'},'Aucun employé — utilisez « Ajouter un utilisateur ».'));
  return h('div',null,bar,h('div',{className:'card'},
    h('div',{className:'card-header'},h('h3',null,'Employés ('+list.length+')')),
    h('div',{style:{overflowX:'auto'}},h('table',{className:'rho-table'},
      h('thead',null,h('tr',null,
        h('th',null,'Employé'),
        ...RH_OUTIL_COLONNES.map(c=>h('th',{className:'rho-c'},c.label)),
        h('th',null,'Formations'),
        h('th',{className:'rho-c'},'')
      )),
      h('tbody',null,...list.map(m=>h('tr',null,
        h('td',null,
          h('div',{style:{fontWeight:'600'}},m.nom||'—',m.actif?null:h('span',{className:'rho-tag'},'Désactivé')),
          h('div',{className:'rho-sub'},m.email||'')
        ),
        ...RH_OUTIL_COLONNES.map(c=>{
          const box=h('input',{type:'checkbox',checked:!!m[c.cle],title:c.label,'aria-label':c.label+' · '+(m.nom||'')});
          box.addEventListener('change',()=>rhOutilCocher(m,c.cle,box));
          return h('td',{className:'rho-c'},box);
        }),
        h('td',null,rhOutilCelluleFormations(m)),
        h('td',{className:'rho-c'},h('button',{type:'button',className:'rho-del',title:'Retirer de la liste',onClick:()=>rhOutilRetirerEmploye(m)},iconEl('trash',13)))
      )))
    ))
  ));
}

"""

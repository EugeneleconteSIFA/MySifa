"""MyRH — Outil RH : intitulés de poste (CSS et JS).

Catalogue des postes (MyRH › Catalogues › Postes), postes d'un employé
(colonne « Service et contrat », fenêtre « Postes »), sélecteur de postes
réutilisé par « Ajouter un employé » et « Exigé pour ». Concaténé après
RH_OUTIL_CATALOGUES_JS dans COMPTA_MAIN_JS (app/web/compta_assets.py) ; utilise
ses fonctions communes (rhOutilFenetre, rhOutilDialogue, rhOutilConfirmer,
rhOutilCase, _rhoCatVues…). API : app/routers/rh_outil_postes.py.
"""

RH_OUTIL_POSTES_CSS = r"""
/* MyRH — postes */
.rho-cv .rho-cat-row.poste{grid-template-columns:minmax(0,1fr) 1fr 1fr}
@media (min-width:821px){
  .rho-cv .rho-cat-row.poste{grid-template-columns:minmax(220px,2.2fr) minmax(170px,1fr) minmax(120px,.8fr) 84px 34px}
}
.rho-postes{display:flex;flex-wrap:wrap;gap:4px;margin:5px 0 2px}
.rho-poste{display:inline-flex;align-items:center;font-size:11px;font-weight:600;color:var(--accent);background:var(--accent-bg);border-radius:6px;padding:2px 7px;white-space:nowrap}
.rho-poste-edit{display:inline-flex;align-items:center;gap:3px;font-size:11px;font-weight:600;font-family:inherit;color:var(--muted);background:var(--bg);border:1px dashed var(--border);border-radius:6px;padding:2px 7px;cursor:pointer;transition:border-color .15s,color .15s}
.rho-poste-edit:hover{border-color:var(--accent);color:var(--accent)}
.rho-chips{display:flex;flex-wrap:wrap;gap:6px}
.rho-chip{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--border);background:var(--bg);color:var(--text2);border-radius:999px;padding:5px 11px;font-size:12px;font-weight:600;font-family:inherit;cursor:pointer;transition:background .15s,border-color .15s,color .15s}
.rho-chip:hover{border-color:var(--accent);color:var(--accent)}
.rho-chip.on{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.rho-chips-vide{font-size:12px;color:var(--muted)}
/* « Exigé pour » : un service et ses postes forment un seul bloc */
/* flex-shrink:0 : la liste est une colonne flex de hauteur limitée ; sans lui
   le bloc est comprimé et ses derniers postes disparaissent. */
.rho-svc-bloc{flex-shrink:0;border:1px solid var(--border);border-radius:9px;background:var(--bg)}
.rho-svc-bloc:hover{border-color:var(--accent)}
.rho-svc-bloc>.rho-check-row{border:0;border-radius:0;background:transparent}
.rho-svc-postes{margin:0 10px 8px 19px;padding:2px 0 2px 14px;border-left:2px solid var(--border)}
.rho-svc-postes-t{font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin:2px 0 2px 2px}
.rho-check-row.sous{border:0;border-radius:7px;background:transparent;padding:4px 8px;font-size:12.5px;color:var(--text2)}
.rho-check-row.sous:hover{background:var(--card)}
.rho-check-row.sous.couvert{opacity:.55;cursor:default}
.rho-inclus{display:none;font-size:11px;font-style:italic;color:var(--muted)}
.rho-check-row.sous.couvert .rho-inclus{display:inline}
.rho-cv .rho-sect.vide .rho-sect-t{color:var(--muted)}
.rho-cv .rho-cat-row.rho-poste-vide{display:flex;align-items:center;justify-content:space-between;gap:12px;font-size:12.5px;font-style:italic;color:var(--muted)}
.rho-cv .rho-cat-row.rho-poste-vide .rho-mini{width:auto;font-style:normal}
.rho-poste-grp{margin-top:12px}
.rho-poste-grp:first-child{margin-top:0}
"""

RH_OUTIL_POSTES_JS = r"""
// ── Postes ────────────────────────────────────────────────────────
// Un poste appartient à un service ; un employé peut en occuper plusieurs.
// Une formation exigée pour un poste est attribuée à ceux qui l'occupent.
function rhOutilPostesDe(service){return (S.rhOutilPostes||[]).filter(p=>p.service===service);}

// Sélecteur de postes en pastilles. `services` : codes à proposer (dans cet
// ordre) ; `choisis` : Set d'identifiants, modifié sur place.
function rhOutilChoixPostes(services,choisis,surChange){
  const el=h('div');
  const peindre=()=>{
    const groupes=services.map(code=>({code,postes:rhOutilPostesDe(code)})).filter(g=>g.postes.length);
    if(!groupes.length){
      el.replaceChildren(h('div',{className:'rho-chips-vide'},(S.rhOutilPostes||[]).length
        ?'Aucun poste pour ce service — à créer dans Catalogues › Postes.'
        :'Aucun poste au catalogue — à créer dans Catalogues › Postes.'));
      return;
    }
    const plusieurs=groupes.length>1;
    el.replaceChildren(...groupes.map(g=>h('div',{className:'rho-poste-grp'},
      plusieurs?h('div',{className:'rho-sect-t'},(S.rhOutilServices||[]).find(s=>s.code===g.code)?.label||g.code):null,
      h('div',{className:'rho-chips'},...g.postes.map(p=>h('button',{type:'button',className:'rho-chip'+(choisis.has(p.id)?' on':''),
        'aria-pressed':String(choisis.has(p.id)),
        onClick:()=>{if(choisis.has(p.id))choisis.delete(p.id);else choisis.add(p.id);peindre();if(surChange)surChange();}},
        choisis.has(p.id)?'✓':null,p.libelle))))));
  };
  peindre();
  return {el,peindre};
}

// Postes d'un employé suivi (fenêtre). Son service d'abord, puis les autres.
function rhOutilPostesEmploye(m){
  const {ov,fermer}=rhOutilFenetre();
  const choisis=new Set((m.postes||[]).map(p=>p.id));
  const avant=new Set(choisis);
  const autres=(S.rhOutilServices||[]).map(s=>s.code).filter(c=>c!==m.service);
  const services=[m.service].concat(autres);
  const choix=rhOutilChoixPostes(services,choisis);
  const err=h('div',{className:'rho-err',role:'alert'});
  const ok=h('button',{type:'button',className:'rho-btn accent'},'Enregistrer');
  ok.addEventListener('click',async()=>{
    if(choisis.size===avant.size&&[...choisis].every(i=>avant.has(i))){fermer();return;}
    ok.disabled=true;
    let r;
    try{r=await api('/api/rh-outil/membres/'+m.id+'/postes',rhOutilJson('PUT',{postes:[...choisis]}));}
    catch(e){err.textContent=e.message;ok.disabled=false;return;}
    fermer();
    await rhOutilLoad();
    const n=(r&&r.attribues)||0;
    toast('Postes enregistrés'+(n?' — '+n+' formation'+(n>1?'s ajoutées':' ajoutée'):'')+'.');
  });
  ov.appendChild(rhOutilDialogue('Postes',fermer,
    h('div',{className:'rho-cat-legend'},(m.nom||'')+' · '+(m.service_label||'sans service')+'. Ajouter un poste attribue les formations exigées pour lui ; en retirer un ne retire aucune formation.'),
    h('div',{className:'rho-scroll'},choix.el),
    err,
    h('div',{className:'rho-dlg-foot'},h('button',{type:'button',className:'rho-btn',onClick:fermer},'Annuler'),ok)
  ));
  document.body.appendChild(ov);
}

// Cellule « Service et contrat » : les postes sous le service.
function rhOutilCellulePostes(m){
  const ps=m.postes||[];
  return h('div',{className:'rho-postes'},
    ...ps.map(p=>h('span',{className:'rho-poste',title:'Poste'},p.libelle)),
    h('button',{type:'button',className:'rho-poste-edit',title:'Postes occupés',onClick:()=>rhOutilPostesEmploye(m)},
      ps.length?iconEl('edit',10):iconEl('plus',10),ps.length?null:'Poste'));
}

// ── Catalogue des postes (onglet Catalogues › Postes) ──
// Vue gardée entre deux rendus, comme les catalogues (rhOutilCatalogueVue).
function rhOutilPostesVue(){
  if(_rhoCatVues.postes)return _rhoCatVues.postes;
  const base='/api/rh-outil/postes';
  const listEl=h('div',{className:'rho-list rho-cv-table'},h('div',{className:'rho-empty'},'Chargement…'));
  const titre=h('h3',null,'Postes');
  const optionsServices=()=>(S.rhOutilServices||[]).map(s=>h('option',{value:s.code},s.label));
  const nouvSvc=h('select',{className:'rho-select','aria-label':'Service du nouveau poste'});
  const peindreNouvSvc=()=>{
    const v=nouvSvc.value;
    nouvSvc.replaceChildren(h('option',{value:''},'Service…'),...optionsServices());
    if(v)nouvSvc.value=v;
  };
  const rafraichir=async()=>{
    let d;
    try{d=await api(base);}catch(e){toast(e.message,'error');return;}
    if(!d)return;
    const postes=d.postes||[];
    S.rhOutilPostes=postes;
    titre.textContent='Postes ('+postes.length+')';
    peindreNouvSvc();
    const ligne=p=>{
      const inp=h('input',{type:'text',className:'rho-input',value:p.libelle,maxlength:'120','aria-label':'Intitulé du poste','data-rho-esc':'',...RHO_NO_AUTOFILL});
      const enregistrer=async()=>{
        const v=inp.value.trim();
        if(!v||v===p.libelle){inp.value=p.libelle;return;}
        try{await api(base+'/'+p.id,rhOutilJson('PUT',{libelle:v}));p.libelle=v;toast('Poste renommé.');rhOutilLoad();}
        catch(e){inp.value=p.libelle;toast(e.message,'error');}
      };
      inp.addEventListener('keydown',e=>{
        if(e.key==='Enter'){e.preventDefault();inp.blur();}
        else if(e.key==='Escape'){e.preventDefault();inp.value=p.libelle;inp.blur();}
      });
      // Même garde que les catalogues : un rendu de page n'est pas une fin de saisie.
      inp.addEventListener('blur',()=>setTimeout(()=>{if(document.activeElement!==inp)enregistrer();},0));
      const svc=h('select',{className:'rho-select','aria-label':'Service de '+p.libelle},...optionsServices());
      svc.value=p.service;
      svc.addEventListener('change',async()=>{
        try{await api(base+'/'+p.id,rhOutilJson('PUT',{service:svc.value}));await rafraichir();rhOutilLoad();toast('Poste déplacé.');}
        catch(e){svc.value=p.service;toast(e.message,'error');}
      });
      const nf=p.nb_formations,ne=p.nb_employes;
      return h('div',{className:'rho-cat-row poste'},inp,svc,
        h('span',{className:'rho-sub',style:{textAlign:'left'}},nf?nf+' formation'+(nf>1?'s exigées':' exigée'):'Aucune formation'),
        h('span',{className:'rho-sub'},ne+' employé'+(ne>1?'s':'')),
        h('button',{type:'button',className:'rho-del',title:'Supprimer le poste',onClick:()=>rhOutilConfirmer({
          titre:'Supprimer ce poste ?',nom:p.libelle,label:'Supprimer',
          sous:p.service_label+' · '+(ne?ne+' employé'+(ne>1?'s l’occupent':' l’occupe'):'personne ne l’occupe'),
          texte:'Il est retiré des employés et des exigences de formation. Les formations déjà attribuées restent.',
          onConfirm:async()=>{
            try{await api(base+'/'+p.id,{method:'DELETE'});}
            catch(e){toast(e.message,'error');throw e;}
            await rafraichir();rhOutilLoad();toast('Poste supprimé.');
          },
        })},iconEl('trash',13)));
    };
    const entete=h('div',{className:'rho-cat-row poste rho-cat-head','aria-hidden':'true'},
      h('span',null,'Intitulé'),h('span',null,'Service'),h('span',null,'Formations'),h('span',null,'Employés'),h('span',null,''));
    // Tous les services : ceux qui ont des postes d'abord, puis ceux qui n'en
    // ont aucun, pour montrer ce qui reste à décrire.
    const groupes=(S.rhOutilServices||[]).map(s=>({code:s.code,libelle:s.label,items:postes.filter(p=>p.service===s.code)}));
    const pleins=groupes.filter(g=>g.items.length),vides=groupes.filter(g=>!g.items.length);
    // Raccourci : préremplit le service dans la ligne d'ajout.
    const ajouterDans=code=>{nouvSvc.value=code;nouv.focus();nouv.scrollIntoView({block:'center',behavior:'smooth'});};
    listEl.replaceChildren(entete,
      ...pleins.map(g=>h('div',{className:'rho-sect'},
        h('div',{className:'rho-sect-t'},g.libelle+' · '+g.items.length),
        h('div',{className:'rho-list'},...g.items.map(ligne)))),
      ...vides.map(g=>h('div',{className:'rho-sect vide'},
        h('div',{className:'rho-sect-t'},g.libelle+' · 0'),
        h('div',{className:'rho-cat-row rho-poste-vide'},
          h('span',null,'Aucun poste'),
          h('button',{type:'button',className:'rho-mini',onClick:()=>ajouterDans(g.code)},iconEl('plus',11),'Ajouter un poste')))));
  };
  const nouv=h('input',{type:'text',className:'rho-input',placeholder:'Nouveau poste…',maxlength:'120',...RHO_NO_AUTOFILL});
  const ajouter=async()=>{
    const v=nouv.value.trim();
    if(!v)return;
    if(!nouvSvc.value){toast('Service obligatoire.','error');nouvSvc.focus();return;}
    try{
      await api(base,rhOutilJson('POST',{libelle:v,service:nouvSvc.value}));
      nouv.value='';
      await rafraichir();
      rhOutilLoad();
      nouv.focus();
    }catch(e){toast(e.message,'error');}
  };
  nouv.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();ajouter();}});
  peindreNouvSvc();
  const el=h('div',{className:'card rho-cv'},
    h('div',{className:'card-header'},titre),
    h('div',{className:'rho-cv-body'},
      h('div',{className:'rho-cat-add'},nouv,nouvSvc,h('button',{type:'button',className:'rho-btn accent',onClick:ajouter},iconEl('plus',13),'Ajouter')),
      h('div',{className:'rho-cat-legend'},'Un poste appartient à un service ; un employé peut en occuper plusieurs. Les formations exigées pour un poste (onglet Formations, « Exigé pour ») sont attribuées à ceux qui l’occupent.'),
      listEl
    )
  );
  const vue={el,rafraichir,nouv};
  _rhoCatVues.postes=vue;
  rafraichir();
  return vue;
}
"""

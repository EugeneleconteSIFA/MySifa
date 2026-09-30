"""MyCompta — Outil RH : catalogues (formations, documents administratifs).

« Exigé pour » (tous / services / contrats), catégories et justificatifs des
formations, fenêtres de catalogue. Concaténé après RH_OUTIL_JS dans
COMPTA_MAIN_JS (app/web/compta_assets.py) ; utilise ses fonctions communes
(rhOutilFenetre, rhOutilDialogue, rhOutilConfirmer, rhOutilCase…).
API : app/routers/rh_outil.py, app/routers/rh_outil_formations.py.
"""

RH_OUTIL_CATALOGUES_JS = r"""
// ── « Exigé pour » d'un élément du catalogue ──────────────────────
// Un seul réglage, trois états exclusifs : personne, tous les employés, ou
// certains services (celui du compte de l'employé, Paramètres › Comptes).
function rhOutilLibelleExige(x){
  if(x.obligatoire)return 'Tous les employés';
  const n=(x.cibles||[]).length;
  // Formations : par service ; documents administratifs : par contrat.
  return n?n+(x.__cible==='contrat'?' contrat':' service')+(n>1?'s':''):'Personne';
}
// Cibles possibles d'une liste : services (formations) ou contrats (documents).
// Renvoie [{code, label, membre:m=>bool}].
function rhOutilCibles(L){
  if(L.cible==='contrat')return (S.rhOutilContrats||[]).map(c=>({code:c,label:c,membre:m=>m.contrat_type===c}));
  return (S.rhOutilServices||[]).map(sv=>({code:sv.code,label:sv.label,membre:m=>m.service===sv.code}));
}
function rhOutilExigePour(L,x,apres){
  const services=rhOutilCibles(L);
  const membres=S.rhOutilMembres||[];
  const {ov,fermer}=rhOutilFenetre();
  const avant=new Set(x.cibles||[]);
  const tousBox=rhOutilCase(!!x.obligatoire,'Tous les employés');
  const cases=new Map();
  const liste=h('div',{className:'rho-list'},...services.map(sv=>{
    const box=rhOutilCase(!x.obligatoire&&avant.has(sv.code),sv.label);
    cases.set(sv.code,box);
    const nb=membres.filter(sv.membre).length;
    return h('label',{className:'rho-check-row'},box,h('span',{style:{flex:1}},sv.label),
      h('span',{className:'rho-sub'},nb?nb+' employé'+(nb>1?'s':'')+' suivi'+(nb>1?'s':''):''));
  }));
  // « Tous les employés » coché : les cibles sont grisées et ne comptent pas.
  const peindre=()=>{
    liste.classList.toggle('off',tousBox.checked);
    cases.forEach(b=>{b.disabled=tousBox.checked;});
  };
  tousBox.addEventListener('change',peindre);
  peindre();
  const enregistrer=async()=>{
    const tous=tousBox.checked;
    const voulus=tous?[]:[...cases].filter(([,b])=>b.checked).map(([c])=>c);
    const nouveaux=new Set(voulus.filter(c=>!avant.has(c)));
    // Combien d'employés vont le recevoir maintenant.
    const aDeja=m=>(m[L.cle]||[]).some(e=>e.element_id===x.id);
    const dansNouvelles=m=>services.some(sv=>nouveaux.has(sv.code)&&sv.membre(m));
    const manquants=membres.filter(m=>!aDeja(m)&&(tous?!x.obligatoire:dansNouvelles(m))).length;
    const envoyer=async()=>{
      let r;
      try{r=await api('/api/rh-outil/'+L.cle+'/catalogue/'+x.id+'/exige',rhOutilJson('PUT',{tous,cibles:voulus}));}
      catch(e){toast(e.message,'error');throw e;}
      x.obligatoire=tous;x.cibles=voulus;
      const n=(r&&r.attribues)||0;
      toast('Enregistré'+(n?' — '+L.ajoute+' à '+n+' employé'+(n>1?'s':''):'')+'.');
      fermer();
      if(apres)await apres();
      rhOutilLoad();
    };
    if(!manquants){try{await envoyer();}catch(_){}return;}
    rhOutilConfirmer({
      ton:'info',titre:tous?'Exiger pour tous les employés ?':(L.cible==='contrat'?'Exiger pour ces contrats ?':'Exiger pour ces services ?'),nom:x.libelle,label:'Enregistrer',
      sous:manquants+' employé'+(manquants>1?'s':'')+' concerné'+(manquants>1?'s ne l’ont':' ne l’a')+' pas encore',
      texte:L.il+' sera '+L.ajoute+' tout de suite à '+(manquants>1?'ces employés':'cet employé')+', puis à chaque employé '+(tous?'':(L.cible==='contrat'?'sous l’un de ces contrats ':'de ces services '))+'ajouté ensuite. Le retirer de « Exigé pour » plus tard ne retirera rien.',
      onConfirm:envoyer,
    });
  };
  ov.appendChild(rhOutilDialogue('Exigé pour',fermer,
    h('div',{className:'rho-cat-legend'},x.libelle),
    h('label',{className:'rho-check-row tous'},tousBox,h('span',{style:{flex:1}},'Tous les employés'),
      h('span',{className:'rho-sub'},membres.length+' employé'+(membres.length>1?'s':'')+' suivi'+(membres.length>1?'s':''))),
    h('div',{className:'rho-sep'},L.cible==='contrat'?'Ou seulement certains contrats':'Ou seulement certains services'),
    h('div',{className:'rho-scroll'},liste),
    h('div',{className:'rho-dlg-foot'},
      h('button',{type:'button',className:'rho-btn',onClick:fermer},'Annuler'),
      h('button',{type:'button',className:'rho-btn accent',onClick:enregistrer},'Enregistrer'))
  ));
  document.body.appendChild(ov);
}

// ── Catégories de formations ──────────────────────────────────────
function rhOutilNomCategorie(id){
  const c=(S.rhOutilCategories||[]).find(x=>x.id===id);
  return c?c.libelle:'Sans catégorie';
}
// Regroupe des éléments par catégorie, dans l'ordre du référentiel, les
// éléments sans catégorie en dernier. Renvoie [{id, libelle, items}].
function rhOutilParCategorie(items){
  const groupes=(S.rhOutilCategories||[]).map(c=>({id:c.id,libelle:c.libelle,items:[]}));
  const autres={id:null,libelle:'Sans catégorie',items:[]};
  items.forEach(x=>{(groupes.find(g=>g.id===x.categorie_id)||autres).items.push(x);});
  return groupes.concat([autres]).filter(g=>g.items.length);
}
function rhOutilGererCategories(apres){
  const {ov,fermer}=rhOutilFenetre();
  const base='/api/rh-outil/formations/categories';
  const listEl=h('div',{className:'rho-list'},h('div',{className:'rho-empty'},'Chargement…'));
  const rafraichir=async()=>{
    let d;
    try{d=await api(base);}catch(e){toast(e.message,'error');return;}
    if(!d)return;
    S.rhOutilCategories=d.categories||[];
    listEl.replaceChildren(...(S.rhOutilCategories.length?S.rhOutilCategories.map(c=>{
      const inp=h('input',{type:'text',className:'rho-input',value:c.libelle,maxlength:'120','aria-label':'Intitulé de la catégorie','data-rho-esc':'',...RHO_NO_AUTOFILL});
      const enregistrer=async()=>{
        const v=inp.value.trim();
        if(!v||v===c.libelle){inp.value=c.libelle;return;}
        try{await api(base+'/'+c.id,rhOutilJson('PUT',{libelle:v}));c.libelle=v;toast('Catégorie renommée.');if(apres)apres();rhOutilLoad();}
        catch(e){inp.value=c.libelle;toast(e.message,'error');}
      };
      inp.addEventListener('keydown',e=>{
        if(e.key==='Enter'){e.preventDefault();inp.blur();}
        else if(e.key==='Escape'){e.preventDefault();inp.value=c.libelle;inp.blur();}
      });
      inp.addEventListener('blur',enregistrer);
      const nb=c.nb_formations;
      return h('div',{className:'rho-cat-row f'},inp,
        h('span',{className:'rho-sub'},nb+' formation'+(nb>1?'s':'')),
        h('button',{type:'button',className:'rho-del',title:'Supprimer la catégorie',onClick:()=>rhOutilConfirmer({
          titre:'Supprimer cette catégorie ?',nom:c.libelle,label:'Supprimer',
          sous:nb?nb+' formation'+(nb>1?'s':'')+' rangée'+(nb>1?'s':'')+' dedans':'Aucune formation dedans',
          texte:'Les formations ne sont pas supprimées : elles passent « Sans catégorie ».',
          onConfirm:async()=>{
            try{await api(base+'/'+c.id,{method:'DELETE'});}
            catch(e){toast(e.message,'error');throw e;}
            await rafraichir();if(apres)apres();rhOutilLoad();toast('Catégorie supprimée.');
          },
        })},iconEl('trash',13)));
    }):[h('div',{className:'rho-empty'},'Aucune catégorie.')]));
  };
  const nouv=h('input',{type:'text',className:'rho-input',placeholder:'Nouvelle catégorie…',maxlength:'120',...RHO_NO_AUTOFILL});
  const ajouter=async()=>{
    const v=nouv.value.trim();if(!v)return;
    try{await api(base,rhOutilJson('POST',{libelle:v}));nouv.value='';await rafraichir();if(apres)apres();rhOutilLoad();nouv.focus();}
    catch(e){toast(e.message,'error');}
  };
  nouv.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();ajouter();}});
  ov.appendChild(rhOutilDialogue('Catégories de formations',fermer,
    h('div',{className:'rho-cat-legend'},'Supprimer une catégorie ne supprime pas ses formations : elles passent « Sans catégorie ».'),
    listEl,
    h('div',{className:'rho-cat-add'},nouv,h('button',{type:'button',className:'rho-btn accent',onClick:ajouter},iconEl('plus',13),'Ajouter'))
  ));
  document.body.appendChild(ov);
  rafraichir();
}

// ── Justificatifs attendus d'une formation ────────────────────────
// Définis dans la formation (attestation, certificat…) ; chaque employé qui a
// la formation a une case par justificatif, sous la formation, avec pièces
// jointes. Ce ne sont pas des documents administratifs.
function rhOutilJustificatifs(x,apres){
  const {ov,fermer}=rhOutilFenetre();
  const base='/api/rh-outil/formations/justificatifs';
  const listEl=h('div',{className:'rho-list'});
  const nbAvec=()=>(S.rhOutilMembres||[]).filter(m=>(m.formations||[]).some(f=>f.element_id===x.id)).length;
  const dessiner=()=>{
    const js=x.justificatifs||[];
    listEl.replaceChildren(...(js.length?js.map(jj=>{
      const inp=h('input',{type:'text',className:'rho-input',value:jj.libelle,maxlength:'120','aria-label':'Intitulé du justificatif','data-rho-esc':'',...RHO_NO_AUTOFILL});
      const enregistrer=async()=>{
        const v=inp.value.trim();
        if(!v||v===jj.libelle){inp.value=jj.libelle;return;}
        try{await api(base+'/'+jj.id,rhOutilJson('PUT',{libelle:v}));jj.libelle=v;toast('Justificatif renommé.');rhOutilLoad();}
        catch(e){inp.value=jj.libelle;toast(e.message,'error');}
      };
      inp.addEventListener('keydown',e=>{
        if(e.key==='Enter'){e.preventDefault();inp.blur();}
        else if(e.key==='Escape'){e.preventDefault();inp.value=jj.libelle;inp.blur();}
      });
      inp.addEventListener('blur',enregistrer);
      return h('div',{className:'rho-cat-row f'},inp,h('span',{className:'rho-sub'},''),
        h('button',{type:'button',className:'rho-del',title:'Supprimer le justificatif',onClick:()=>rhOutilConfirmer({
          titre:'Supprimer ce justificatif ?',nom:jj.libelle,sous:x.libelle,label:'Supprimer',
          texte:'Il n’est plus attendu pour cette formation : la case disparaît chez chaque employé, avec ses pièces jointes.',
          onConfirm:async()=>{
            try{await api(base+'/'+jj.id,{method:'DELETE'});}
            catch(e){toast(e.message,'error');throw e;}
            x.justificatifs=js.filter(o=>o.id!==jj.id);dessiner();rhOutilLoad();if(apres)apres();
            toast('Justificatif supprimé.');
          },
        })},iconEl('trash',13)));
    }):[h('div',{className:'rho-empty'},'Aucun justificatif attendu.')]));
  };
  const nouv=h('input',{type:'text',className:'rho-input',placeholder:'Ex. Attestation de formation…',maxlength:'120',...RHO_NO_AUTOFILL});
  const ajouter=async()=>{
    const v=nouv.value.trim();if(!v)return;
    let r;
    try{r=await api('/api/rh-outil/formations/catalogue/'+x.id+'/justificatifs',rhOutilJson('POST',{libelle:v}));}
    catch(e){toast(e.message,'error');return;}
    x.justificatifs=(x.justificatifs||[]).concat([{id:r.id,libelle:v}]);
    nouv.value='';dessiner();rhOutilLoad();if(apres)apres();nouv.focus();
    const n=(r&&r.attribues)||0;
    if(n)toast('Attendu chez '+n+' employé'+(n>1?'s qui ont':' qui a')+' déjà la formation.');
  };
  nouv.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();ajouter();}});
  const n=nbAvec();
  ov.appendChild(rhOutilDialogue('Justificatifs attendus',fermer,
    h('div',{className:'rho-cat-legend'},x.libelle+' · une case par justificatif apparaît sous la formation, chez chaque employé qui l’a'+(n?' ('+n+' aujourd’hui)':'')+'. Les pièces jointes s’y déposent.'),
    listEl,
    h('div',{className:'rho-cat-add'},nouv,h('button',{type:'button',className:'rho-btn accent',onClick:ajouter},iconEl('plus',13),'Ajouter'))
  ));
  dessiner();
  document.body.appendChild(ov);
  requestAnimationFrame(()=>nouv.focus());
}

// ── Catalogues ────────────────────────────────────────────────────
function rhOutilCatalogue(L){
  const {ov,fermer}=rhOutilFenetre();
  const base='/api/rh-outil/'+L.cle+'/catalogue';
  const listEl=h('div',{className:'rho-list'},h('div',{className:'rho-empty'},'Chargement…'));
  // Après chaque changement : le catalogue se redessine seul, le tableau
  // dessous est rechargé (intitulés et éléments supprimés).
  const rafraichir=async()=>{
    let d;
    try{d=await api(base);}catch(e){toast(e.message,'error');return;}
    if(!d)return;
    const cat=d.elements||[];
    const ligne=x=>{
      const inp=h('input',{type:'text',className:'rho-input',value:x.libelle,maxlength:'120','aria-label':'Intitulé','data-rho-esc':'',...RHO_NO_AUTOFILL});
      const enregistrer=async()=>{
        const v=inp.value.trim();
        if(!v||v===x.libelle){inp.value=x.libelle;return;}
        try{
          await api(base+'/'+x.id,rhOutilJson('PUT',{libelle:v}));
          x.libelle=v;inp.value=v;
          rhOutilLoad();
          toast(L.renomme);
        }catch(e){inp.value=x.libelle;toast(e.message,'error');}
      };
      inp.addEventListener('keydown',e=>{
        if(e.key==='Enter'){e.preventDefault();inp.blur();}
        else if(e.key==='Escape'){e.preventDefault();inp.value=x.libelle;inp.blur();}
      });
      inp.addEventListener('blur',enregistrer);
      const nb=x.nb_employes;
      x.__cible=L.cible;
      const exige=h('button',{type:'button',className:'rho-mini'+(x.obligatoire||(x.cibles||[]).length?' on':''),
          title:'Exigé pour : '+rhOutilLibelleExige(x)+' — cliquer pour modifier',
          onClick:()=>rhOutilExigePour(L,x,rafraichir)},iconEl('users',11),rhOutilLibelleExige(x));
      const suppr=
        h('button',{type:'button',className:'rho-del',title:'Supprimer du catalogue',onClick:()=>rhOutilConfirmer({
          titre:L.supprTitre,nom:x.libelle,label:'Supprimer',
          sous:nb?(nb+' employé'+(nb>1?'s l’ont':' l’a')+' dans sa liste'):'Attribué à aucun employé',
          texte:nb?L.supprTxtN:L.supprTxt0,
          onConfirm:async()=>{
            try{await api(base+'/'+x.id,{method:'DELETE'});}
            catch(e){toast(e.message,'error');throw e;}
            await rafraichir();rhOutilLoad();
            toast(L.supprime);
          },
        })},iconEl('trash',13));
      const compte=h('span',{className:'rho-sub'},nb+' employé'+(nb>1?'s':''));
      if(!L.categories)return h('div',{className:'rho-cat-row'},inp,exige,compte,suppr);
      // Formations : intitulé en haut, réglages (catégorie, exigé pour,
      // justificatifs) dessous, pour garder un intitulé lisible.
      const selCat=h('select',{className:'rho-select','aria-label':'Catégorie de '+x.libelle},
        h('option',{value:''},'Sans catégorie'),
        ...(S.rhOutilCategories||[]).map(c=>h('option',{value:String(c.id)},c.libelle)));
      selCat.value=x.categorie_id?String(x.categorie_id):'';
      selCat.addEventListener('change',async()=>{
        const v=selCat.value?Number(selCat.value):null;
        try{await api(base+'/'+x.id+'/categorie',rhOutilJson('PUT',{categorie_id:v}));x.categorie_id=v;await rafraichir();rhOutilLoad();}
        catch(e){selCat.value=x.categorie_id?String(x.categorie_id):'';toast(e.message,'error');}
      });
      const nd=(x.justificatifs||[]).length;
      const docs=h('button',{type:'button',className:'rho-mini'+(nd?' on':''),title:'Justificatifs attendus pour cette formation',
        onClick:()=>rhOutilJustificatifs(x,rafraichir)},iconEl('file-text',11),nd?nd+' justificatif'+(nd>1?'s':''):'Justificatifs');
      return h('div',{className:'rho-fbloc'},
        h('div',{className:'rho-cat-row f'},inp,compte,suppr),
        h('div',{className:'rho-fctl'},selCat,exige,docs));
    };
    if(!cat.length){listEl.replaceChildren(h('div',{className:'rho-empty'},L.catVide));return;}
    if(!L.categories){listEl.replaceChildren(...cat.map(ligne));return;}
    listEl.replaceChildren(...rhOutilParCategorie(cat).map(g=>h('div',{className:'rho-sect'},
      h('div',{className:'rho-sect-t'},g.libelle+' · '+g.items.length),
      h('div',{className:'rho-list'},...g.items.map(ligne)))));
  };
  const nouv=h('input',{type:'text',className:'rho-input',placeholder:L.nouveau,maxlength:'120',...RHO_NO_AUTOFILL});
  const nouvCat=L.categories?h('select',{className:'rho-select','aria-label':'Catégorie de la nouvelle formation'},
    ...(S.rhOutilCategories||[]).map(c=>h('option',{value:String(c.id)},c.libelle)),h('option',{value:''},'Sans catégorie')):null;
  const ajouter=async()=>{
    const v=nouv.value.trim();
    if(!v)return;
    try{
      await api(base,rhOutilJson('POST',{libelle:v,categorie_id:nouvCat&&nouvCat.value?Number(nouvCat.value):null}));
      nouv.value='';
      await rafraichir();
      nouv.focus();
    }catch(e){toast(e.message,'error');}
  };
  nouv.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();ajouter();}});
  const dlg=rhOutilDialogueLarge(L.catalogue,fermer,
    L.categories?h('div',{className:'rho-dlg-tools'},h('button',{type:'button',className:'rho-mini',onClick:()=>rhOutilGererCategories(rafraichir)},iconEl('sliders',11),'Gérer les catégories')):null,
    h('div',{className:'rho-cat-legend'},'« Exigé pour » : attribué d’office aux employés concernés, présents et à venir.'+(L.categories?' Les justificatifs (attestations…) se déclarent dans chaque formation.':' Documents administratifs : exigés pour tous ou selon le contrat.')+' Retirable ensuite employé par employé.'),
    h('div',{className:'rho-scroll'},listEl),
    h('div',{className:'rho-cat-add'},nouv,nouvCat,h('button',{type:'button',className:'rho-btn accent',onClick:ajouter},iconEl('plus',13),'Ajouter'))
  );
  if(L.categories)dlg.classList.add('xl');
  ov.appendChild(dlg);
  document.body.appendChild(ov);
  rafraichir();
  requestAnimationFrame(()=>nouv.focus());
}

"""

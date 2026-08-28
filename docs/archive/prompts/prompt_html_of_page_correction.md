# Prompt Windsurf — Correction OF page dans html.py

## Contexte

La page "OF" que l'utilisateur voit dans MyProd est dans `app/web/html.py`, PAS dans
`fabrication_page.py`. Toutes les améliorations (pagination, searchbar, sous-onglets, fiches
techniques, sélection/suppression en masse, bouton modifier) doivent être faites dans `html.py`.

Problème immédiat : `loadOfImports` attend un tableau plat mais l'API retourne maintenant
`{total, offset, limit, rows}` → "Aucun OF importé" alors que 525 OFs existent en base.

Dans `html.py`, les utilitaires sont différents de fabrication_page.py :
- Appels API : `api(path, opts)` (pas `apiFetch`)
- Toasts : `toast(msg, type)` avec type `'error'` (pas `showToast`)
- Icônes : `iconEl(name, size)` (pas `svgIcon`)

Ne pas toucher : `production_data`, `planning_entries`, `DB_PATH`, les autres pages.

---

## ÉTAPE 1 — État initial (ligne ~2147)

Cherche :
```javascript
ofImports:[],ofImportsLoading:false,ofImportModal:null,
```
Remplace par :
```javascript
ofImports:[],ofImportsLoading:false,ofImportModal:null,
ofSearch:'',ofPage:0,ofTotal:0,ofSubTab:'of',
ofSelected:new Set(),
fiches:[],fichesLoading:false,ficheSearch:'',fichePage:0,ficheTotal:0,
ficheSelected:new Set(),ficheEditModal:null,
```

---

## ÉTAPE 2 — Renommer le lien sidebar (ligne ~7107)

Cherche :
```javascript
{key:'of',label:'OF',icon:'file'}
```
Remplace par :
```javascript
{key:'of',label:'Fiches + OF',icon:'file'}
```

---

## ÉTAPE 3 — Remplacer `loadOfImports` (ligne ~10344)

Remplace la fonction `loadOfImports` existante par :

```javascript
async function loadOfImports(){
  set({ofImportsLoading:true});
  try{
    const q=encodeURIComponent(S.ofSearch||'');
    const offset=(S.ofPage||0)*50;
    const url='/api/of/list?limit=50&offset='+offset+(q?'&q='+q:'');
    const data=await api(url);
    set({
      ofImports: Array.isArray(data.rows)?data.rows:[],
      ofTotal:   data.total||0,
      ofImportsLoading:false,
    });
  }catch(e){
    set({ofImportsLoading:false});
    toast(e.message||'Erreur chargement des OF','error');
  }
}

async function loadFiches(){
  set({fichesLoading:true});
  try{
    const q=encodeURIComponent(S.ficheSearch||'');
    const offset=(S.fichePage||0)*50;
    const url='/api/fiches-techniques/list?limit=50&offset='+offset+(q?'&q='+q:'');
    const data=await api(url);
    set({fiches:Array.isArray(data.rows)?data.rows:[],ficheTotal:data.total||0,fichesLoading:false});
  }catch(e){
    set({fichesLoading:false});
    toast(e.message||'Erreur chargement fiches techniques','error');
  }
}
```

---

## ÉTAPE 4 — Ajouter les fonctions modal édition OF

Après `loadFiches`, ajouter :

```javascript
function openOfEditModal(row){
  set({ofEditModal:{...row}});
  renderOfEditModal();
}
function closeOfEditModal(){
  set({ofEditModal:null});
  render();
}
async function saveOfEdit(){
  const m=S.ofEditModal;
  if(!m) return;
  const payload={
    of_numero:     document.getElementById('ofe-numero')?.value.trim()||null,
    reference:     document.getElementById('ofe-reference')?.value.trim()||null,
    machine:       document.getElementById('ofe-machine')?.value.trim()||null,
    delai_client:  document.getElementById('ofe-delai')?.value.trim()||null,
    format:        document.getElementById('ofe-format')?.value.trim()||null,
    date_creation: document.getElementById('ofe-date')?.value.trim()||null,
    qte_etiquettes:parseFloat(document.getElementById('ofe-qte')?.value)||null,
    qte_bobines:   parseFloat(document.getElementById('ofe-bobines')?.value)||null,
  };
  try{
    await api('/api/of/'+m.id,{method:'PATCH',body:JSON.stringify(payload)});
    toast('OF mis à jour.');
    closeOfEditModal();
    await loadOfImports();
    render();
  }catch(e){
    toast(e.message||'Erreur mise à jour.','error');
  }
}
function renderOfEditModal(){
  // Rendu via innerHTML dans un overlay flottant
  const existing=document.getElementById('of-edit-overlay');
  if(existing) existing.remove();
  const m=S.ofEditModal;
  if(!m) return;
  function field(id,label,val,type='text'){
    return `<div style="margin-bottom:12px">
      <label style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:5px">${label}</label>
      <input id="${id}" type="${type}" value="${String(val||'').replace(/"/g,'&quot;')}"
        style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box">
    </div>`;
  }
  const overlay=document.createElement('div');
  overlay.id='of-edit-overlay';
  overlay.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1000;display:flex;align-items:center;justify-content:center;padding:16px';
  overlay.onclick=e=>{if(e.target===overlay)closeOfEditModal();};
  overlay.innerHTML=`
    <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px;max-width:520px;width:100%;max-height:90vh;overflow-y:auto">
      <div style="font-size:15px;font-weight:700;color:var(--text);margin-bottom:20px">Modifier l'OF</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px">
        ${field('ofe-numero','OF n°',m.of_numero)}
        ${field('ofe-reference','Référence',m.reference)}
        ${field('ofe-machine','Machine',m.machine)}
        ${field('ofe-delai','Délai client',m.delai_client)}
        ${field('ofe-format','Format',m.format)}
        ${field('ofe-date','Date création',(m.date_creation||'').slice(0,10),'date')}
        ${field('ofe-qte','Qté étiquettes',m.qte_etiquettes,'number')}
        ${field('ofe-bobines','Qté bobines',m.qte_bobines,'number')}
      </div>
      <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:8px">
        <button onclick="closeOfEditModal()" style="padding:9px 16px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;font-size:13px">Annuler</button>
        <button onclick="saveOfEdit()" style="padding:9px 16px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-family:inherit;font-size:13px;font-weight:700">Enregistrer</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
}

function openFicheEditModal(row){
  set({ficheEditModal:{...row}});
  renderFicheEditModal();
}
function closeFicheEditModal(){
  set({ficheEditModal:null});
  render();
}
async function saveFicheEdit(){
  const m=S.ficheEditModal;
  if(!m) return;
  const payload={
    reference:      document.getElementById('fce-ref')?.value.trim()||null,
    designation:    document.getElementById('fce-desig')?.value.trim()||null,
    client:         document.getElementById('fce-client')?.value.trim()||null,
    format:         document.getElementById('fce-format')?.value.trim()||null,
    laize:          parseFloat(document.getElementById('fce-laize')?.value)||null,
    matiere:        document.getElementById('fce-matiere')?.value.trim()||null,
    adhesif:        document.getElementById('fce-adhesif')?.value.trim()||null,
    conditionnement:document.getElementById('fce-cond')?.value.trim()||null,
    notes:          document.getElementById('fce-notes')?.value.trim()||null,
  };
  try{
    await api('/api/fiches-techniques/'+m.id,{method:'PATCH',body:JSON.stringify(payload)});
    toast('Fiche mise à jour.');
    closeFicheEditModal();
    await loadFiches();
    render();
  }catch(e){
    toast(e.message||'Erreur mise à jour.','error');
  }
}
function renderFicheEditModal(){
  const existing=document.getElementById('fiche-edit-overlay');
  if(existing) existing.remove();
  const m=S.ficheEditModal;
  if(!m) return;
  function field(id,label,val,type='text'){
    return `<div style="margin-bottom:12px">
      <label style="font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--muted);display:block;margin-bottom:5px">${label}</label>
      <input id="${id}" type="${type}" value="${String(val||'').replace(/"/g,'&quot;')}"
        style="width:100%;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box">
    </div>`;
  }
  const overlay=document.createElement('div');
  overlay.id='fiche-edit-overlay';
  overlay.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:1000;display:flex;align-items:center;justify-content:center;padding:16px';
  overlay.onclick=e=>{if(e.target===overlay)closeFicheEditModal();};
  overlay.innerHTML=`
    <div style="background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px;max-width:560px;width:100%;max-height:90vh;overflow-y:auto">
      <div style="font-size:15px;font-weight:700;color:var(--text);margin-bottom:20px">Modifier la fiche technique</div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 16px">
        ${field('fce-ref','Référence',m.reference)}
        ${field('fce-desig','Désignation',m.designation)}
        ${field('fce-client','Client',m.client)}
        ${field('fce-format','Format',m.format)}
        ${field('fce-laize','Laize (mm)',m.laize,'number')}
        ${field('fce-matiere','Matière',m.matiere)}
        ${field('fce-adhesif','Adhésif',m.adhesif)}
        ${field('fce-cond','Conditionnement',m.conditionnement)}
      </div>
      ${field('fce-notes','Notes',m.notes)}
      <div style="display:flex;justify-content:flex-end;gap:10px;margin-top:8px">
        <button onclick="closeFicheEditModal()" style="padding:9px 16px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-family:inherit;font-size:13px">Annuler</button>
        <button onclick="saveFicheEdit()" style="padding:9px 16px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-family:inherit;font-size:13px;font-weight:700">Enregistrer</button>
      </div>
    </div>`;
  document.body.appendChild(overlay);
}
```

---

## ÉTAPE 5 — Remplacer `renderOfPage` (ligne ~10423)

Remplace la fonction `renderOfPage` existante (de `function renderOfPage(){` jusqu'à la `}` fermante, ligne ~10472) par :

```javascript
function renderPaginationBar(page, total, pageSize, onPrev, onNext){
  const totalPages=Math.max(1,Math.ceil(total/pageSize));
  const start=total===0?0:page*pageSize+1;
  const end=Math.min((page+1)*pageSize,total);
  return h('div',{style:{display:'flex',alignItems:'center',gap:'10px',padding:'12px 0',fontSize:'12px',color:'var(--muted)'}},
    h('button',{
      style:'padding:6px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px',
      disabled:page===0, onClick:onPrev
    },'← Préc.'),
    h('span',null,total===0?'Aucun résultat':`${start}–${end} sur ${total}`),
    h('button',{
      style:'padding:6px 12px;border-radius:8px;border:1px solid var(--border);background:transparent;color:var(--text2);cursor:pointer;font-size:12px',
      disabled:page>=totalPages-1, onClick:onNext
    },'Suiv. →'),
  );
}

function renderOfTab(){
  const PAGE_SIZE=50;
  const total=S.ofTotal||0;
  const page=S.ofPage||0;

  // Toolbar
  const toolbar=h('div',{style:{display:'flex',alignItems:'center',gap:'10px',marginBottom:'16px',flexWrap:'wrap'}},
    h('input',{
      id:'of-search-html',
      type:'text',
      placeholder:'Rechercher (OF n°, référence, machine…)',
      value:S.ofSearch||'',
      style:'flex:1;min-width:200px;max-width:320px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none',
      oninput:async function(e){
        const v=e.target.value;
        const ss=e.target.selectionStart, se=e.target.selectionEnd;
        set({ofSearch:v,ofPage:0});
        await loadOfImports();
        render();
        requestAnimationFrame(()=>{
          const el=document.getElementById('of-search-html');
          if(el){el.focus();try{el.setSelectionRange(ss,se);}catch(x){}}
        });
      },
      onkeydown:function(e){
        if(e.key==='Escape'){set({ofSearch:'',ofPage:0});loadOfImports().then(()=>render());e.target.value='';}
      },
    }),
    h('button',{
      style:'padding:9px 14px;border-radius:8px;border:none;background:var(--accent);color:#fff;cursor:pointer;font-size:13px;font-weight:700;white-space:nowrap',
      onClick:openOfImportModal
    },iconEl('upload',13),' Importer un OF'),
    S.user&&S.user.role==='superadmin'&&S.ofSelected.size>0
      ? h('button',{
          style:'padding:9px 14px;border-radius:8px;border:none;background:var(--danger);color:#fff;cursor:pointer;font-size:13px;font-weight:700;white-space:nowrap',
          onClick:async()=>{
            const n=S.ofSelected.size;
            if(!confirm(`Supprimer ${n} OF${n>1?'s':''} ?`)) return;
            try{
              await api('/api/of/bulk',{method:'DELETE',body:JSON.stringify({ids:[...S.ofSelected]})});
              toast(`${n} OF${n>1?'s':''} supprimé${n>1?'s':''}.`);
              set({ofSelected:new Set()});
              await loadOfImports();
              render();
            }catch(e){toast(e.message||'Erreur.','error');}
          }
        },iconEl('trash',13),` Supprimer (${S.ofSelected.size})`)
      : null
  );

  const rows=(S.ofImports||[]).map(row=>{
    const stCls=prodOfStatutClass(row.statut);
    const dateCrea=(row.date_creation||'').slice(0,10)||'—';
    const acts=[
      h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:transparent;cursor:pointer',
        title:'Modifier', onClick:()=>openOfEditModal(row)
      },iconEl('edit',13)),
    ];
    if(row.pdf_filename){
      acts.push(h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:transparent;cursor:pointer',
        title:'Télécharger PDF', onClick:()=>{window.open('/api/of/'+row.id+'/pdf','_blank');}
      },iconEl('download',13)));
    }
    if(S.user&&S.user.role==='superadmin'){
      acts.push(h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid rgba(248,113,113,.3);background:transparent;cursor:pointer;color:var(--danger)',
        title:'Supprimer', onClick:()=>ofDeleteImport(row.id)
      },iconEl('trash',13)));
    }
    return h('tr',null,
      h('td',{style:{width:'36px'}},
        h('input',{type:'checkbox',checked:S.ofSelected.has(row.id),style:'cursor:pointer',
          onChange:function(e){
            const sel=new Set(S.ofSelected);
            if(e.target.checked)sel.add(row.id);else sel.delete(row.id);
            set({ofSelected:sel});render();
          }
        })
      ),
      h('td',null,
        h('div',null,escHtml(row.of_numero||'—')),
        row.imported_by?h('div',{style:{fontSize:'11px',color:'var(--muted)'}},escHtml(row.imported_by)):null,
      ),
      h('td',null,escHtml(row.reference||'—')),
      h('td',null,escHtml(row.machine||'—')),
      h('td',null,escHtml(row.delai_client||'—')),
      h('td',null,row.qte_etiquettes!=null?escHtml(String(row.qte_etiquettes)):'—'),
      h('td',null,escHtml(dateCrea)),
      h('td',null,h('span',{className:stCls},prodOfStatutLabel(row.statut))),
      h('td',null,h('div',{style:{display:'flex',gap:'4px'}},...acts)),
    );
  });

  const empty=h('tr',null,
    h('td',{colSpan:'9',style:{textAlign:'center',color:'var(--muted)',padding:'24px'}},
      S.ofImportsLoading?'Chargement…':(S.ofSearch?`Aucun résultat pour « ${escHtml(S.ofSearch)} »`:'Aucun OF importé')
    )
  );

  return h('div',{className:'card'},
    toolbar,
    h('div',{style:{overflowX:'auto'}},
      h('table',{className:'table-std'},
        h('thead',null,h('tr',null,
          h('th',{style:{width:'36px'}},
            h('input',{type:'checkbox',style:'cursor:pointer',
              checked:(S.ofImports||[]).length>0&&(S.ofImports||[]).every(r=>S.ofSelected.has(r.id)),
              onChange:function(e){
                const ids=(S.ofImports||[]).map(r=>r.id);
                set({ofSelected:e.target.checked?new Set(ids):new Set()});render();
              }
            })
          ),
          h('th',null,'OF n°'),h('th',null,'Référence'),h('th',null,'Machine'),
          h('th',null,'Délai client'),h('th',null,'Qté étiquettes'),h('th',null,'Date création'),
          h('th',null,'Statut'),h('th',null,'Actions')
        )),
        h('tbody',null,...(rows.length?rows:[empty]))
      )
    ),
    renderPaginationBar(page,total,50,
      async()=>{if(page>0){set({ofPage:page-1});await loadOfImports();render();}},
      async()=>{if(page<Math.ceil(total/50)-1){set({ofPage:page+1});await loadOfImports();render();}}
    )
  );
}

function renderFichesTab(){
  const PAGE_SIZE=50;
  const total=S.ficheTotal||0;
  const page=S.fichePage||0;

  const toolbar=h('div',{style:{display:'flex',alignItems:'center',gap:'10px',marginBottom:'16px',flexWrap:'wrap'}},
    h('input',{
      id:'fiche-search-html',
      type:'text',
      placeholder:'Rechercher (référence, désignation, client…)',
      value:S.ficheSearch||'',
      style:'flex:1;min-width:200px;max-width:320px;background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:9px 12px;color:var(--text);font-size:13px;font-family:inherit;outline:none',
      oninput:async function(e){
        const v=e.target.value;
        const ss=e.target.selectionStart,se=e.target.selectionEnd;
        set({ficheSearch:v,fichePage:0});
        await loadFiches();render();
        requestAnimationFrame(()=>{
          const el=document.getElementById('fiche-search-html');
          if(el){el.focus();try{el.setSelectionRange(ss,se);}catch(x){}}
        });
      },
      onkeydown:function(e){
        if(e.key==='Escape'){set({ficheSearch:'',fichePage:0});loadFiches().then(()=>render());e.target.value='';}
      },
    }),
    S.user&&S.user.role==='superadmin'&&S.ficheSelected.size>0
      ? h('button',{
          style:'padding:9px 14px;border-radius:8px;border:none;background:var(--danger);color:#fff;cursor:pointer;font-size:13px;font-weight:700;white-space:nowrap',
          onClick:async()=>{
            const n=S.ficheSelected.size;
            if(!confirm(`Supprimer ${n} fiche${n>1?'s':''} ?`)) return;
            try{
              await api('/api/fiches-techniques/bulk',{method:'DELETE',body:JSON.stringify({ids:[...S.ficheSelected]})});
              toast(`${n} fiche${n>1?'s':''} supprimée${n>1?'s':''}.`);
              set({ficheSelected:new Set()});
              await loadFiches();render();
            }catch(e){toast(e.message||'Erreur.','error');}
          }
        },iconEl('trash',13),` Supprimer (${S.ficheSelected.size})`)
      : null
  );

  const rows=(S.fiches||[]).map(row=>{
    const acts=[
      h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid var(--border);background:transparent;cursor:pointer',
        title:'Modifier',onClick:()=>openFicheEditModal(row)
      },iconEl('edit',13)),
    ];
    if(S.user&&S.user.role==='superadmin'){
      acts.push(h('button',{
        style:'padding:4px 8px;border-radius:6px;border:1px solid rgba(248,113,113,.3);background:transparent;cursor:pointer;color:var(--danger)',
        title:'Supprimer',
        onClick:async()=>{
          if(!confirm('Supprimer cette fiche ?')) return;
          try{await api('/api/fiches-techniques/'+row.id,{method:'DELETE'});toast('Fiche supprimée.');await loadFiches();render();}
          catch(e){toast(e.message||'Erreur.','error');}
        }
      },iconEl('trash',13)));
    }
    return h('tr',null,
      h('td',{style:{width:'36px'}},
        h('input',{type:'checkbox',checked:S.ficheSelected.has(row.id),style:'cursor:pointer',
          onChange:function(e){
            const sel=new Set(S.ficheSelected);
            if(e.target.checked)sel.add(row.id);else sel.delete(row.id);
            set({ficheSelected:sel});render();
          }
        })
      ),
      h('td',null,escHtml(row.reference||'—')),
      h('td',null,escHtml(row.designation||'—')),
      h('td',null,escHtml(row.client||'—')),
      h('td',null,escHtml(row.format||'—')),
      h('td',null,row.laize!=null?escHtml(String(row.laize)+' mm'):'—'),
      h('td',null,escHtml(row.matiere||'—')),
      h('td',null,escHtml(row.source||'—')),
      h('td',null,h('div',{style:{display:'flex',gap:'4px'}},...acts)),
    );
  });

  const empty=h('tr',null,
    h('td',{colSpan:'9',style:{textAlign:'center',color:'var(--muted)',padding:'24px'}},
      S.fichesLoading?'Chargement…':(S.ficheSearch?`Aucun résultat pour « ${escHtml(S.ficheSearch)} »`:'Aucune fiche technique importée')
    )
  );

  return h('div',{className:'card'},
    toolbar,
    h('div',{style:{overflowX:'auto'}},
      h('table',{className:'table-std'},
        h('thead',null,h('tr',null,
          h('th',{style:{width:'36px'}},
            h('input',{type:'checkbox',style:'cursor:pointer',
              checked:(S.fiches||[]).length>0&&(S.fiches||[]).every(r=>S.ficheSelected.has(r.id)),
              onChange:function(e){
                const ids=(S.fiches||[]).map(r=>r.id);
                set({ficheSelected:e.target.checked?new Set(ids):new Set()});render();
              }
            })
          ),
          h('th',null,'Référence'),h('th',null,'Désignation'),h('th',null,'Client'),
          h('th',null,'Format'),h('th',null,'Laize'),h('th',null,'Matière'),
          h('th',null,'Source'),h('th',null,'Actions')
        )),
        h('tbody',null,...(rows.length?rows:[empty]))
      )
    ),
    renderPaginationBar(page,total,50,
      async()=>{if(page>0){set({fichePage:page-1});await loadFiches();render();}},
      async()=>{if(page<Math.ceil(total/50)-1){set({fichePage:page+1});await loadFiches();render();}}
    )
  );
}

function renderOfPage(){
  // Sous-navigation
  const subNav=h('div',{style:{display:'flex',gap:'0',borderBottom:'1px solid var(--border)',marginBottom:'20px'}},
    h('button',{
      style:`padding:10px 18px;font-size:13px;font-weight:600;border:none;background:transparent;cursor:pointer;border-bottom:2px solid ${S.ofSubTab==='of'?'var(--accent)':'transparent'};color:${S.ofSubTab==='of'?'var(--accent)':'var(--muted)'};font-family:inherit`,
      onClick:()=>{set({ofSubTab:'of'});render();}
    },'Ordres de fabrication'),
    h('button',{
      style:`padding:10px 18px;font-size:13px;font-weight:600;border:none;background:transparent;cursor:pointer;border-bottom:2px solid ${S.ofSubTab==='fiche'?'var(--accent)':'transparent'};color:${S.ofSubTab==='fiche'?'var(--accent)':'var(--muted)'};font-family:inherit`,
      onClick:async()=>{set({ofSubTab:'fiche'});await loadFiches();render();}
    },'Fiches techniques'),
  );
  return h('div',null,
    subNav,
    S.ofSubTab==='fiche' ? renderFichesTab() : renderOfTab()
  );
}
```

---

## ÉTAPE 6 — Charger les fiches au changement de page

Cherche les deux occurrences de :
```javascript
if(S.page==='of' && canAccessOfTab()) await loadOfImports();
```
Dans chacune, ajouter après :
```javascript
if(S.page==='of' && canAccessOfTab()){
  await loadOfImports();
  if(S.ofSubTab==='fiche') await loadFiches();
}
```
(Remplacer la ligne existante par ce bloc dans les deux endroits.)

---

## Points de vigilance

- `api()` et `toast()` sont les utilitaires de `html.py` — NE PAS utiliser `apiFetch` ou `showToast`
- `iconEl()` est l'utilitaire icônes de `html.py` — NE PAS utiliser `svgIcon`
- `S.ofSelected` et `S.ficheSelected` sont des `Set` — toujours recréer avec `new Set(...)` avant de `set()`
- Les modals d'édition utilisent `document.body.appendChild` (pas `mroot`) car `html.py` n'a pas de `mroot`
- Ne pas toucher à `renderOfImportModal`, `ofHandlePdfFile`, `ofValidateImport`, `ofDeleteImport`

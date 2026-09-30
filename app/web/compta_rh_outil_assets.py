"""MyCompta — onglet « Outil RH » : CSS et JS.

Concaténés en tête de COMPTA_MAIN_CSS / COMPTA_MAIN_JS (app/web/compta_assets.py).
API : app/routers/rh_outil.py.

Les fenêtres (choix d'un employé, d'un élément, catalogue, confirmation)
sont construites hors de render() et posées sur <body>, comme dans
Maintenance : un re-render de MyCompta (toast, rechargement de la liste) ne
les ferme pas et ne fait pas perdre la saisie en cours.
"""

RH_OUTIL_CSS = r"""
/* MyCompta — Outil RH */
.rho-bar{display:flex;justify-content:flex-end;gap:8px;flex-wrap:wrap;margin-bottom:14px}
.rho-btn{display:inline-flex;align-items:center;gap:6px;border-radius:10px;padding:8px 14px;font-size:12px;font-weight:700;font-family:inherit;cursor:pointer;background:var(--card);color:var(--text2);border:1px solid var(--border);transition:background .15s,border-color .15s,color .15s,filter .15s}
.rho-btn:hover{background:var(--bg);border-color:var(--accent);color:var(--accent)}
.rho-btn.accent{background:var(--accent);border-color:var(--accent);color:white}
.rho-btn.accent:hover{background:var(--accent);color:white;filter:brightness(1.07)}
.rho-dlg .rho-btn:not(.accent){background:var(--bg)}
.rho-tag{display:inline-block;font-size:10px;font-weight:600;color:var(--muted);background:var(--bg);border:1px solid var(--border);border-radius:5px;padding:1px 6px;margin-left:8px;vertical-align:middle}
.rho-sub{font-size:11px;color:var(--muted)}
.rho-empty{padding:18px;text-align:center;color:var(--muted);font-size:13px}

/* Case à cocher MySifa : dessinée ici, pas la case native du navigateur */
.rho-chk{appearance:none;-webkit-appearance:none;width:18px;height:18px;margin:0;flex-shrink:0;border:1.5px solid var(--muted);border-radius:5px;background:var(--bg);cursor:pointer;transition:background-color .15s,border-color .15s,box-shadow .15s;vertical-align:middle}
.rho-chk:hover{border-color:var(--accent)}
.rho-chk:checked{border-color:var(--accent);background:var(--accent) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='3.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='20 6 9 17 4 12'/%3E%3C/svg%3E") center/12px 12px no-repeat}
.rho-chk:focus-visible{outline:none;box-shadow:0 0 0 3px var(--accent-bg)}

/* Tableau : base table-std de MySifa, cellules multi-lignes */
.rho-table th{font-family:inherit;padding:10px 16px}
.rho-table td{white-space:normal;max-width:none;overflow:visible;vertical-align:top;color:var(--text);padding:14px 16px}
.rho-table tr:hover td{background:var(--bg)}
.rho-table .rho-c{text-align:center;width:1%;white-space:nowrap}
.rho-table td.rho-c{vertical-align:middle}
.rho-emp-cell{display:flex;align-items:center;gap:10px;min-width:180px}
.rho-avatar{width:32px;height:32px;border-radius:50%;background:var(--accent-bg);color:var(--accent);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;flex-shrink:0}
.rho-emp-nom{font-weight:600;font-size:13px;color:var(--text)}
.rho-seg{display:inline-flex;gap:2px;padding:2px;border:1px solid var(--border);border-radius:8px;background:var(--bg)}
.rho-seg button{border:none;background:transparent;color:var(--muted);font-family:inherit;font-size:11px;font-weight:700;padding:4px 11px;border-radius:6px;cursor:pointer;transition:background-color .15s,color .15s}
.rho-seg button:hover{color:var(--text)}
.rho-seg button:focus-visible{outline:none;box-shadow:0 0 0 3px var(--accent-bg)}
.rho-seg button.on.oui{background:var(--accent);color:white}
.rho-seg button.on.non{background:var(--card);color:var(--text);box-shadow:0 0 0 1px var(--border)}
.rho-seg[aria-busy=true]{opacity:.6;pointer-events:none}
.rho-del{padding:6px 8px;border-radius:8px;border:1px solid var(--border);background:var(--bg);cursor:pointer;color:var(--muted);display:inline-flex;align-items:center;transition:background .15s,border-color .15s,color .15s}
.rho-del:hover{color:var(--danger);border-color:rgba(248,113,113,.35);background:rgba(248,113,113,.12)}

/* Colonnes-listes (Formations, Documents) : une ligne par élément */
.rho-items{display:flex;flex-direction:column;gap:6px;min-width:190px}
.rho-item{display:flex;align-items:center;gap:9px}
.rho-item-lbl{flex:1;font-size:12.5px;color:var(--text2);cursor:pointer;line-height:1.3}
.rho-item.done .rho-item-lbl{color:var(--text)}
.rho-item-x{border:none;background:transparent;color:var(--muted);cursor:pointer;font-size:15px;line-height:1;padding:1px 5px;border-radius:5px;opacity:0;transition:opacity .15s}
.rho-item:hover .rho-item-x,.rho-item-x:focus-visible{opacity:1}
.rho-item-x:hover{color:var(--danger);background:rgba(248,113,113,.12)}
@media (hover:none){.rho-item-x{opacity:1}}
.rho-item-none{font-size:12px;color:var(--muted)}
.rho-pj{display:inline-flex;align-items:center;gap:3px;border:1px solid transparent;background:transparent;color:var(--muted);font-family:inherit;font-size:11px;font-weight:700;padding:1px 5px;border-radius:6px;cursor:pointer;opacity:.45;transition:opacity .15s,color .15s,border-color .15s,background-color .15s}
.rho-pj.has{opacity:1;color:var(--accent);background:var(--accent-bg)}
.rho-item:hover .rho-pj,.rho-pj:focus-visible{opacity:1}
.rho-pj:hover{border-color:var(--accent);color:var(--accent)}
@media (hover:none){.rho-pj{opacity:1}}
.rho-drop{border:1.5px dashed var(--border);border-radius:10px;background:var(--bg);padding:18px 14px;text-align:center;cursor:pointer;color:var(--muted);font-size:12px;transition:border-color .15s,background-color .15s,color .15s;margin-top:12px}
.rho-drop:hover,.rho-drop.drag{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.rho-drop b{display:block;font-size:13px;color:var(--text);margin-bottom:3px}
.rho-drop.busy{opacity:.6;pointer-events:none}
.rho-pj-row{display:flex;align-items:center;gap:10px;background:var(--bg);border:1px solid var(--border);border-radius:9px;padding:8px 10px}
.rho-pj-ico{width:30px;height:30px;border-radius:7px;background:var(--accent-bg);color:var(--accent);display:flex;align-items:center;justify-content:center;flex-shrink:0}
.rho-pj-nom{font-size:13px;font-weight:600;color:var(--text);word-break:break-all;text-decoration:none}
.rho-pj-nom:hover{color:var(--accent);text-decoration:underline}
.rho-pj-row .rho-del{background:var(--card)}
.rho-items-foot{display:flex;align-items:center;gap:8px;margin-top:2px}
.rho-add{border:1px dashed var(--border);background:var(--bg);color:var(--muted);border-radius:7px;padding:4px 10px;font-size:11px;font-weight:600;cursor:pointer;font-family:inherit;display:inline-flex;align-items:center;gap:4px;transition:border-color .15s,color .15s}
.rho-add:hover{border-color:var(--accent);color:var(--accent)}
.rho-count{font-size:11px;font-weight:600;color:var(--muted)}
.rho-count.full{color:var(--accent)}

/* Colonne Dossier : statut calculé, filtre au clic sur le titre */
.rho-statut{display:inline-flex;align-items:center;gap:5px;font-size:11px;font-weight:700;border-radius:20px;padding:3px 10px;white-space:nowrap}
.rho-statut.ok{color:var(--success);background:color-mix(in srgb,var(--success) 13%,transparent)}
.rho-statut.ko{color:var(--warn);background:color-mix(in srgb,var(--warn) 13%,transparent)}
.rho-th-btn{display:inline-flex;align-items:center;gap:6px;background:none;border:none;padding:0;margin:0;font:inherit;color:inherit;text-transform:inherit;letter-spacing:inherit;cursor:pointer}
.rho-th-btn:hover{color:var(--accent)}
.rho-th-btn:focus-visible{outline:none;box-shadow:0 0 0 3px var(--accent-bg);border-radius:4px}
.rho-th-filtre{font-size:10px;font-weight:700;text-transform:none;letter-spacing:0;border-radius:20px;padding:1px 8px;background:var(--bg);border:1px solid var(--border);color:var(--muted)}
.rho-th-filtre.on{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}

/* Service (celui du compte, lecture seule) et filtre */
.rho-svc{font-size:12.5px;font-weight:600;color:var(--text2);white-space:nowrap}
.rho-svc.vide{color:var(--muted);font-weight:500}
.rho-select{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:7px 12px;color:var(--text);font-size:12px;font-weight:600;font-family:inherit;cursor:pointer;outline:none;max-width:260px}
.rho-select:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.rho-select.on{border-color:var(--accent);color:var(--accent);background:var(--accent-bg)}
.rho-bar-spacer{flex:1}
.rho-mini{display:inline-flex;align-items:center;gap:4px;border:1px solid var(--border);background:var(--bg);color:var(--muted);border-radius:7px;padding:4px 9px;font-size:11px;font-weight:600;font-family:inherit;cursor:pointer;white-space:nowrap;transition:border-color .15s,color .15s}
.rho-mini:hover{border-color:var(--accent);color:var(--accent)}
.rho-mini.on{color:var(--accent);border-color:var(--accent);background:var(--accent-bg)}
.rho-dlg.large{max-width:680px}
.rho-check-row{display:flex;align-items:center;gap:9px;padding:6px 10px;background:var(--bg);border:1px solid var(--border);border-radius:9px;font-size:13px;color:var(--text);cursor:pointer}
.rho-check-row:hover{border-color:var(--accent)}
.rho-scroll{max-height:min(420px,calc(100vh - 260px));overflow-y:auto;padding-right:2px}
.rho-dlg-foot{display:flex;justify-content:flex-end;gap:8px;margin-top:14px}

/* Fenêtres : même dessin que les modales de suppression de Maintenance */
.rho-ov{position:fixed;inset:0;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center}
.rho-dlg{position:relative;max-width:520px;width:calc(100% - 40px);max-height:calc(100vh - 40px);overflow-y:auto;box-sizing:border-box;background:var(--card);border:1px solid var(--border);border-radius:12px;padding:22px;box-shadow:0 20px 50px rgba(0,0,0,.4)}
.rho-dlg-title{color:var(--text);font-size:16px;font-weight:700;margin:0 0 14px;padding-right:30px}
.rho-dlg-title.danger{color:var(--danger);display:flex;align-items:center;gap:8px}
.rho-dlg-close{position:absolute;top:16px;right:16px;border:1px solid var(--border);background:var(--bg);color:var(--muted);border-radius:8px;width:28px;height:28px;cursor:pointer;font-size:16px;line-height:1}
.rho-dlg-close:hover{color:var(--text)}
.rho-search,.rho-input{width:100%;box-sizing:border-box;background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:10px 14px;color:var(--text);font-size:14px;font-family:inherit;outline:none;transition:border-color .15s,box-shadow .15s}
.rho-search{margin-bottom:10px}
.rho-search:focus,.rho-input:focus{border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-bg)}
.rho-list{max-height:360px;overflow-y:auto;display:flex;flex-direction:column;gap:4px}
.rho-opt{display:flex;align-items:center;gap:10px;width:100%;text-align:left;background:var(--bg);border:1px solid var(--border);border-radius:9px;padding:9px 12px;color:var(--text);font-family:inherit;font-size:13px;cursor:pointer;transition:border-color .15s}
.rho-opt:hover{border-color:var(--accent)}
.rho-opt[disabled]{cursor:default;opacity:.55}
.rho-opt[disabled]:hover{border-color:var(--border)}
.rho-cat-row{display:flex;align-items:center;gap:8px}
.rho-cat-row .rho-input{padding:8px 12px;font-size:13px}
.rho-cat-row .rho-sub{white-space:nowrap;min-width:78px;text-align:right}
.rho-cat-add{display:flex;gap:8px;margin-top:12px}
.rho-oblig{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:600;color:var(--muted);cursor:pointer;white-space:nowrap;user-select:none}
.rho-oblig:has(.rho-chk:checked){color:var(--accent)}
.rho-cat-legend{font-size:11px;color:var(--muted);margin:-6px 0 12px;line-height:1.4}
.rho-dlg-title.info{display:flex;align-items:center;gap:8px}
.rho-confirm-act .rho-ok.accent{background:var(--accent)}
.rho-confirm-sum{padding:12px 14px;background:var(--bg);border:1px solid var(--border);border-radius:10px;margin-bottom:14px}
.rho-confirm-txt{font-size:13px;color:var(--text);line-height:1.5;margin-bottom:16px}
.rho-confirm-act{display:flex;justify-content:flex-end;gap:10px}
.rho-confirm-act button{border-radius:10px;padding:10px 18px;font-weight:700;cursor:pointer;font-family:inherit;font-size:13px}
.rho-confirm-act .rho-cancel{background:var(--bg);color:var(--text);border:1px solid var(--border)}
.rho-confirm-act .rho-ok{background:var(--danger);color:white;border:none}
.rho-confirm-act button[disabled]{opacity:.6;cursor:default}
"""

RH_OUTIL_JS = r"""
// ══════════════════════════════════════════════════════════════════
// ── OUTIL RH (onglet MyCompta) ────────────────────────────────────
// ══════════════════════════════════════════════════════════════════
// Même droit que MyCompta : qui voit MyCompta voit l'onglet. Le serveur
// vérifie le même accès (app/routers/rh_outil.py).

// Listes par employé, dans l'ordre des colonnes. `cle` = LISTES côté API.
const RH_OUTIL_LISTES=[
  {cle:'formations',titre:'Formations',bouton:'Formation',gerer:'Gérer les formations',catalogue:'Catalogue des formations',
   aucun:'Aucune formation',rechercher:'Rechercher une formation…',nouveau:'Nouvelle formation…',pour:'Formation pour ',
   deja:'Déjà attribuée',vide:'Catalogue vide — ajoutez des formations avec « Gérer les formations ».',catVide:'Aucune formation au catalogue.',
   retirerTitre:'Retirer cette formation ?',retirerTxt:'La formation est cochée comme faite : ce suivi sera perdu pour cet employé. Le catalogue n’est pas modifié.',
   supprTitre:'Supprimer cette formation ?',supprTxtN:'Elle disparaît du catalogue et de la liste de chaque employé qui l’a, avec son suivi.',supprTxt0:'Elle disparaît du catalogue.',
   renomme:'Formation renommée.',supprime:'Formation supprimée.',etat:'faite',
   obligTitre:'Rendre cette formation obligatoire pour tous ?',il:'Elle',ajoute:'ajoutée',obligOk:'Formation obligatoire pour tous'},
  {cle:'documents',titre:'Documents',bouton:'Document',gerer:'Gérer les documents',catalogue:'Catalogue des documents',
   aucun:'Aucun document',rechercher:'Rechercher un document…',nouveau:'Nouveau document…',pour:'Document pour ',
   deja:'Déjà attribué',vide:'Catalogue vide — ajoutez des documents avec « Gérer les documents ».',catVide:'Aucun document au catalogue.',
   retirerTitre:'Retirer ce document ?',retirerTxt:'Le document est coché comme vérifié : ce suivi sera perdu pour cet employé. Le catalogue n’est pas modifié.',
   supprTitre:'Supprimer ce document ?',supprTxtN:'Il disparaît du catalogue et de la liste de chaque employé qui l’a, avec son suivi et ses pièces jointes.',supprTxt0:'Il disparaît du catalogue.',
   renomme:'Document renommé.',supprime:'Document supprimé.',etat:'vérifié',
   obligTitre:'Rendre ce document obligatoire pour tous ?',il:'Il',ajoute:'ajouté',obligOk:'Document obligatoire pour tous',
   pieces:true},
];
// Champs Oui / Non, après les listes. `cle` = CHECKLIST côté API.
const RH_OUTIL_COLONNES=[
  {cle:'reglement_signe',label:'Règlement signé'},
];

// Filtre de la colonne Dossier : chaque clic sur le titre passe au suivant.
const RHO_FILTRES=[
  {cle:'tous',label:'Tous les employés',court:'Tous'},
  {cle:'complet',label:'Complet',court:'Complet'},
  {cle:'incomplet',label:'Incomplet',court:'Incomplet'},
];

// Dossier complet : toutes les cases fixes cochées, et chaque liste a au
// moins un élément, tous cochés. Un employé dont on n'a encore rien
// renseigné est donc Incomplet.
function rhOutilComplet(m){
  return RH_OUTIL_COLONNES.every(c=>!!m[c.cle])
    && RH_OUTIL_LISTES.every(L=>{const it=m[L.cle]||[];return it.length>0&&it.every(x=>x.fait);});
}
function rhOutilBadge(m){
  const ok=rhOutilComplet(m);
  return h('span',{className:'rho-statut '+(ok?'ok':'ko')},iconEl(ok?'check-circle':'alert-circle',12),ok?'Complet':'Incomplet');
}
// Après une coche, seul le badge de la ligne est redessiné : le tableau ne
// bouge pas, même si l'employé ne correspond plus au filtre actif (il en
// sortira au prochain rechargement).
function rhOutilMajStatut(m){
  const cell=document.querySelector('td[data-rho-statut="'+m.id+'"]');
  if(cell)cell.replaceChildren(rhOutilBadge(m));
}

// Attributs qui empêchent Safari et les gestionnaires de mots de passe de
// prendre un champ pour un identifiant.
const RHO_NO_AUTOFILL={autocomplete:'off',autocorrect:'off',autocapitalize:'off',spellcheck:'false','data-1p-ignore':'','data-lpignore':'true','data-form-type':'other'};

function rhOutilJson(method,body){
  return {method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)};
}
function rhOutilInitiales(nom){
  const p=String(nom||'').trim().split(/\s+/).filter(Boolean);
  return ((p[0]||'')[0]||'').concat((p[1]||'')[0]||'').toUpperCase()||'·';
}
function rhOutilCase(checked,label){
  return h('input',{type:'checkbox',className:'rho-chk',checked:!!checked,'aria-label':label});
}

async function rhOutilLoad(){
  try{
    const [d,sv]=await Promise.all([api('/api/rh-outil/membres'),api('/api/rh-outil/services')]);
    if(!d||!sv)return;
    set({rhOutilMembres:d.membres||[],rhOutilServices:sv.services||[],rhOutilLoaded:true});
  }catch(e){toast(e.message,'error');}
}

// ── Fenêtres ──────────────────────────────────────────────────────
// Une pile : Échap et le clic à côté ne ferment que la fenêtre du dessus.
// Un champ marqué data-rho-esc garde Échap pour lui (annuler une saisie).
function rhOutilFenetre(){
  const ov=h('div',{className:'rho-ov'});
  ov.style.zIndex=String(12000+document.querySelectorAll('.rho-ov').length*10);
  const auDessus=()=>{const all=document.querySelectorAll('.rho-ov');return all[all.length-1]===ov;};
  const onKey=e=>{
    if(e.key!=='Escape'||!auDessus())return;
    if(e.target&&e.target.dataset&&e.target.dataset.rhoEsc!==undefined)return;
    e.preventDefault();e.stopPropagation();fermer();
  };
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

function rhOutilDialogueLarge(...a){const d=rhOutilDialogue(...a);d.classList.add('large');return d;}

// Confirmation. opts : {titre, nom, sous, texte, label, ton, onConfirm}
// ton : 'danger' (défaut, suppression) ou 'info' (action de masse non destructive).
// onConfirm lève une erreur pour garder la fenêtre ouverte.
function rhOutilConfirmer(opts){
  const {ov,fermer}=rhOutilFenetre();
  const cancel=h('button',{type:'button',className:'rho-cancel',onClick:fermer},'Annuler');
  const info=opts.ton==='info';
  const ok=h('button',{type:'button',className:'rho-ok'+(info?' accent':'')},opts.label||'Supprimer');
  ok.addEventListener('click',async()=>{
    ok.disabled=true;cancel.disabled=true;
    try{await opts.onConfirm();fermer();}
    catch(_){ok.disabled=false;cancel.disabled=false;}
  });
  ov.appendChild(h('div',{className:'rho-dlg',role:'dialog','aria-modal':'true'},
    info?h('div',{className:'rho-dlg-title info'},iconEl('check-circle',18),opts.titre)
        :h('div',{className:'rho-dlg-title danger'},iconEl('trash',18),opts.titre),
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
    listEl.replaceChildren(...(vis.length?vis.map(it=>h('button',{type:'button',className:'rho-opt',disabled:!!it.disabled,onClick:async()=>{
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
  const search=h('input',{type:'search',name:'rho-recherche',className:'rho-search',placeholder:opts.placeholder||'Rechercher…',...RHO_NO_AUTOFILL});
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
      try{await api('/api/rh-outil/membres',rhOutilJson('POST',{user_id:userId}));}
      catch(e){toast(e.message,'error');throw e;}
      await rhOutilLoad();
      toast('Employé ajouté.');
    },
  });
}
function rhOutilRetirerEmploye(m){
  rhOutilConfirmer({
    titre:'Retirer cet employé ?',nom:m.nom,sous:m.email,label:'Retirer',
    texte:'L’employé sort de la liste de l’Outil RH, avec toute sa checklist et les pièces jointes de ses documents. Son compte MySifa n’est pas touché.',
    onConfirm:async()=>{
      try{await api('/api/rh-outil/membres/'+m.id,{method:'DELETE'});}
      catch(e){toast(e.message,'error');throw e;}
      await rhOutilLoad();
      toast('Employé retiré.');
    },
  });
}
// Sélecteur Oui | Non d'une case fixe (Règlement signé). Le choix s'affiche
// tout de suite ; en cas d'erreur, il revient à la valeur enregistrée.
function rhOutilOuiNon(m,c){
  const seg=h('div',{className:'rho-seg',role:'radiogroup','aria-label':c.label+' · '+(m.nom||'')});
  const peindre=v=>{
    seg.querySelectorAll('button').forEach(b=>{
      const on=(b.dataset.v==='1')===v;
      b.classList.toggle('on',on);b.setAttribute('aria-checked',on?'true':'false');
    });
  };
  const choisir=async v=>{
    if(!!m[c.cle]===v)return;
    peindre(v);seg.setAttribute('aria-busy','true');
    try{
      await api('/api/rh-outil/membres/'+m.id,rhOutilJson('PATCH',{[c.cle]:v}));
      m[c.cle]=v;
      rhOutilMajStatut(m);
    }catch(e){peindre(!!m[c.cle]);toast(e.message,'error');}
    finally{seg.removeAttribute('aria-busy');}
  };
  seg.append(
    h('button',{type:'button',className:'oui',role:'radio','data-v':'1',onClick:()=>choisir(true)},'Oui'),
    h('button',{type:'button',className:'non',role:'radio','data-v':'0',onClick:()=>choisir(false)},'Non')
  );
  peindre(!!m[c.cle]);
  return seg;
}

// ── Listes d'un employé (formations, documents) ───────────────────
async function rhOutilAttribuer(L,m){
  let d;
  try{d=await api('/api/rh-outil/'+L.cle+'/catalogue');}catch(e){toast(e.message,'error');return;}
  if(!d)return;
  const cat=d.elements||[];
  if(!cat.length){toast(L.vide,'error');return;}
  const deja=new Set((m[L.cle]||[]).map(x=>x.element_id));
  rhOutilChoisir({
    titre:L.pour+(m.nom||'cet employé'),
    placeholder:L.rechercher,
    items:cat.map(x=>({valeur:x.id,label:x.libelle,disabled:deja.has(x.id),tags:deja.has(x.id)?[L.deja]:[]})),
    onPick:async elementId=>{
      try{await api('/api/rh-outil/membres/'+m.id+'/'+L.cle,rhOutilJson('POST',{element_id:elementId}));}
      catch(e){toast(e.message,'error');throw e;}
      await rhOutilLoad();
    },
  });
}
async function rhOutilCocherElement(L,m,x,box,ligne){
  const v=box.checked;
  try{
    await api('/api/rh-outil/'+L.cle+'/attributions/'+x.id,rhOutilJson('PATCH',{fait:v}));
    x.fait=v;ligne.classList.toggle('done',v);
    // Le compteur de la cellule suit sans redessiner le tableau.
    const cell=ligne.closest('.rho-items');
    if(cell)rhOutilMajCompteur(cell);
    rhOutilMajStatut(m);
  }catch(e){box.checked=!v;toast(e.message,'error');}
}
function rhOutilMajCompteur(cell){
  const cnt=cell.querySelector('.rho-count');if(!cnt)return;
  const all=cell.querySelectorAll('.rho-item').length;
  const ok=cell.querySelectorAll('.rho-item.done').length;
  cnt.textContent=ok+'/'+all;
  cnt.classList.toggle('full',all>0&&ok===all);
}
async function rhOutilRetirerElement(L,m,x){
  const retirer=async()=>{
    try{await api('/api/rh-outil/'+L.cle+'/attributions/'+x.id,{method:'DELETE'});}
    catch(e){toast(e.message,'error');throw e;}
    await rhOutilLoad();
  };
  // Rien à perdre (pas coché, pas de pièce jointe) : retrait sans confirmation.
  const nbP=(x.pieces||[]).length;
  if(!x.fait&&!nbP){try{await retirer();}catch(_){}return;}
  const txtP=nbP?' '+nbP+' pièce'+(nbP>1?'s jointes seront supprimées':' jointe sera supprimée')+'.':'';
  rhOutilConfirmer({titre:L.retirerTitre,nom:x.libelle,sous:m.nom,label:'Retirer',
    texte:(x.fait?L.retirerTxt:'Le catalogue n’est pas modifié.')+txtP,onConfirm:retirer});
}

// ── Pièces jointes d'un document ──────────────────────────────────
const RHO_PJ_ACCEPT='.pdf,.jpg,.jpeg,.png,.webp,.heic,application/pdf,image/jpeg,image/png,image/webp,image/heic';
function rhOutilTaille(o){
  o=Number(o)||0;
  return o<1024?o+' o':o<1048576?Math.round(o/1024)+' Ko':(o/1048576).toFixed(1).replace('.',',')+' Mo';
}
// « 2026-09-29T10:12:00 » (heure Paris, sans fuseau) → « 29/09/2026 10:12 »
function rhOutilDate(iso){
  const r=String(iso||'').match(/^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/);
  return r?r[3]+'/'+r[2]+'/'+r[1]+' '+r[4]+':'+r[5]:'—';
}
function rhOutilBoutonPieces(L,m,x){
  const n=(x.pieces||[]).length;
  return h('button',{type:'button',className:'rho-pj'+(n?' has':''),
    title:n?(n+' pièce'+(n>1?'s jointes':' jointe')):'Ajouter une pièce jointe',
    'aria-label':'Pièces jointes · '+x.libelle+' · '+n,
    onClick:()=>rhOutilPieces(L,m,x)},iconEl('paperclip',12),n?String(n):null);
}
function rhOutilPieces(L,m,x){
  const {ov,fermer}=rhOutilFenetre();
  const base='/api/rh-outil/documents/attributions/'+x.id+'/pieces';
  const listEl=h('div',{className:'rho-list'},h('div',{className:'rho-empty'},'Chargement…'));
  const rafraichir=async()=>{
    let d;
    try{d=await api(base);}catch(e){toast(e.message,'error');return;}
    if(!d)return;
    const pcs=d.pieces||[];
    x.pieces=pcs;
    listEl.replaceChildren(...(pcs.length?pcs.map(p=>{
      const url=API+'/api/rh-outil/pieces/'+p.id;
      return h('div',{className:'rho-pj-row'},
        h('div',{className:'rho-pj-ico','aria-hidden':'true'},iconEl(p.mime==='application/pdf'?'file-text':'file',15)),
        h('div',{style:{flex:1,minWidth:0}},
          h('a',{className:'rho-pj-nom',href:url+'?apercu=1',target:'_blank',rel:'noopener',title:'Ouvrir dans un nouvel onglet'},p.nom),
          h('div',{className:'rho-sub'},rhOutilTaille(p.taille)+' · '+(p.ajoute_par||'—')+' · '+rhOutilDate(p.ajoute_le))
        ),
        h('a',{className:'rho-del',href:url,title:'Télécharger','aria-label':'Télécharger '+p.nom},iconEl('download',13)),
        h('button',{type:'button',className:'rho-del',title:'Supprimer',onClick:()=>rhOutilConfirmer({
          titre:'Supprimer cette pièce jointe ?',nom:p.nom,sous:x.libelle+' · '+(m.nom||''),label:'Supprimer',
          texte:'Le fichier est effacé du serveur. Cette action ne peut pas être annulée.',
          onConfirm:async()=>{
            try{await api('/api/rh-outil/pieces/'+p.id,{method:'DELETE'});}
            catch(e){toast(e.message,'error');throw e;}
            await rafraichir();rhOutilLoad();
            toast('Pièce jointe supprimée.');
          },
        })},iconEl('trash',13))
      );
    }):[h('div',{className:'rho-empty'},'Aucune pièce jointe.')]));
  };
  const input=h('input',{type:'file',multiple:'',accept:RHO_PJ_ACCEPT,style:{display:'none'}});
  const drop=h('div',{className:'rho-drop',role:'button',tabindex:'0'},
    h('b',null,'Déposer des fichiers ici'),'ou cliquer pour choisir · PDF, JPG, PNG, WEBP, HEIC');
  // Envoi un par un : un fichier refusé n'empêche pas les suivants.
  const envoyer=async fichiers=>{
    const liste=[...fichiers];if(!liste.length)return;
    drop.classList.add('busy');
    let ok=0;
    for(const f of liste){
      const fd=new FormData();fd.append('fichier',f);
      try{await api(base,{method:'POST',body:fd});ok++;}
      catch(e){toast(f.name+' : '+e.message,'error');}
    }
    drop.classList.remove('busy');input.value='';
    await rafraichir();rhOutilLoad();
    if(ok)toast(ok>1?ok+' pièces jointes ajoutées.':'Pièce jointe ajoutée.');
  };
  input.addEventListener('change',()=>envoyer(input.files));
  drop.addEventListener('click',()=>input.click());
  drop.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();input.click();}});
  drop.addEventListener('dragover',e=>{e.preventDefault();drop.classList.add('drag');});
  drop.addEventListener('dragleave',()=>drop.classList.remove('drag'));
  drop.addEventListener('drop',e=>{e.preventDefault();drop.classList.remove('drag');envoyer(e.dataTransfer.files);});
  ov.appendChild(rhOutilDialogue('Pièces jointes',fermer,
    h('div',{className:'rho-cat-legend'},x.libelle+' · '+(m.nom||'')),
    listEl,drop,input
  ));
  document.body.appendChild(ov);
  rafraichir();
}

// ── Services pour lesquels un élément du catalogue est exigé ──────
// Le service d'un employé est celui de son compte (Paramètres › Comptes),
// jamais modifié ici.
function rhOutilServicesExiges(L,x,apres){
  const services=S.rhOutilServices||[];
  const {ov,fermer}=rhOutilFenetre();
  const avant=new Set(x.services||[]);
  const cases=new Map();
  const zone=h('div',{className:'rho-scroll'},h('div',{className:'rho-list'},...services.map(sv=>{
    const box=rhOutilCase(avant.has(sv.code),sv.label);
    cases.set(sv.code,box);
    const nb=(S.rhOutilMembres||[]).filter(m=>m.service===sv.code).length;
    return h('label',{className:'rho-check-row'},box,h('span',{style:{flex:1}},sv.label),
      h('span',{className:'rho-sub'},nb?nb+' employé'+(nb>1?'s':'')+' suivi'+(nb>1?'s':''):''));
  })));
  const enregistrer=async()=>{
    const voulus=[...cases].filter(([,b])=>b.checked).map(([c])=>c);
    const nouveaux=new Set(voulus.filter(c=>!avant.has(c)));
    // Combien d'employés vont le recevoir : ceux d'un service nouvellement
    // coché qui ne l'ont pas encore.
    const manquants=(S.rhOutilMembres||[]).filter(m=>
      nouveaux.has(m.service)&&!(m[L.cle]||[]).some(e=>e.element_id===x.id)).length;
    const envoyer=async()=>{
      let r;
      try{r=await api('/api/rh-outil/'+L.cle+'/catalogue/'+x.id+'/services',rhOutilJson('PUT',{services:voulus}));}
      catch(e){toast(e.message,'error');throw e;}
      x.services=voulus;
      const n=(r&&r.attribues)||0;
      toast('Services enregistrés'+(n?' — '+L.ajoute+' à '+n+' employé'+(n>1?'s':''):'')+'.');
      fermer();
      if(apres)await apres();
      rhOutilLoad();
    };
    if(!manquants){try{await envoyer();}catch(_){}return;}
    rhOutilConfirmer({
      ton:'info',titre:'Exiger pour ces services ?',nom:x.libelle,label:'Enregistrer',
      sous:manquants+' employé'+(manquants>1?'s':'')+' concerné'+(manquants>1?'s ne l’ont':' ne l’a')+' pas encore',
      texte:L.il+' sera '+L.ajoute+' tout de suite à '+(manquants>1?'ces employés':'cet employé')+', puis à chaque employé de ces services ajouté ensuite. Décocher un service plus tard ne retirera rien.',
      onConfirm:envoyer,
    });
  };
  ov.appendChild(rhOutilDialogue('Exigé pour les services',fermer,
    h('div',{className:'rho-cat-legend'},x.libelle+' · le service est celui du compte de l’employé (Paramètres › Comptes).'),
    zone,
    h('div',{className:'rho-dlg-foot'},
      h('button',{type:'button',className:'rho-btn',onClick:fermer},'Annuler'),
      h('button',{type:'button',className:'rho-btn accent',onClick:enregistrer},'Enregistrer'))
  ));
  document.body.appendChild(ov);
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
    listEl.replaceChildren(...(cat.length?cat.map(x=>{
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
      const obl=rhOutilCase(x.obligatoire,'Obligatoire pour tous · '+x.libelle);
      const basculer=async v=>{
        try{
          const r=await api(base+'/'+x.id,rhOutilJson('PATCH',{obligatoire:v}));
          x.obligatoire=v;
          if(v){
            const n=(r&&r.attribues)||0;
            toast(L.obligOk+(n?' — '+L.ajoute+' à '+n+' employé'+(n>1?'s':'')+'.':'.'));
            await rafraichir();rhOutilLoad();
          }else rhOutilLoad();
        }catch(e){obl.checked=!v;toast(e.message,'error');throw e;}
      };
      obl.addEventListener('change',()=>{
        const v=obl.checked;
        // Décocher ne retire rien : pas de confirmation. Cocher touche tous
        // les employés qui ne l'ont pas : on annonce combien avant.
        const manquants=Math.max(0,(S.rhOutilMembres||[]).length-nb);
        if(!v||!manquants){basculer(v).catch(()=>{});return;}
        obl.checked=false;
        rhOutilConfirmer({
          ton:'info',titre:L.obligTitre,nom:x.libelle,label:'Rendre obligatoire pour tous',
          sous:manquants+' employé'+(manquants>1?'s ne l’ont':' ne l’a')+' pas encore',
          texte:L.il+' sera '+L.ajoute+' tout de suite à '+(manquants>1?'ces employés':'cet employé')+', puis à chaque employé ajouté ensuite. Décocher la case plus tard ne retirera rien.',
          onConfirm:async()=>{obl.checked=true;await basculer(true);},
        });
      });
      return h('div',{className:'rho-cat-row'},
        inp,
        h('label',{className:'rho-oblig',title:'Attribué d’office à chaque employé'},obl,'Obligatoire pour tous'),
        h('button',{type:'button',className:'rho-mini'+((x.services||[]).length?' on':''),title:'Services pour lesquels il est exigé',
          onClick:()=>rhOutilServicesExiges(L,x,rafraichir)},iconEl('users',11),
          (x.services||[]).length?x.services.length+' service'+(x.services.length>1?'s':''):'Services'),
        h('span',{className:'rho-sub'},nb+' employé'+(nb>1?'s':'')),
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
        })},iconEl('trash',13))
      );
    }):[h('div',{className:'rho-empty'},L.catVide)]));
  };
  const nouv=h('input',{type:'text',className:'rho-input',placeholder:L.nouveau,maxlength:'120',...RHO_NO_AUTOFILL});
  const ajouter=async()=>{
    const v=nouv.value.trim();
    if(!v)return;
    try{
      await api(base,rhOutilJson('POST',{libelle:v}));
      nouv.value='';
      await rafraichir();
      nouv.focus();
    }catch(e){toast(e.message,'error');}
  };
  nouv.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();ajouter();}});
  ov.appendChild(rhOutilDialogueLarge(L.catalogue,fermer,
    h('div',{className:'rho-cat-legend'},'« Obligatoire pour tous » : attribué d’office à chaque employé, présent et à venir. Retirable ensuite employé par employé.'),
    listEl,
    h('div',{className:'rho-cat-add'},nouv,h('button',{type:'button',className:'rho-btn accent',onClick:ajouter},iconEl('plus',13),'Ajouter'))
  ));
  document.body.appendChild(ov);
  rafraichir();
  requestAnimationFrame(()=>nouv.focus());
}

// ── Onglet ────────────────────────────────────────────────────────
function rhOutilCelluleListe(L,m){
  const items=m[L.cle]||[];
  const nbOk=items.filter(x=>x.fait).length;
  return h('div',{className:'rho-items'},
    ...(items.length?items.map(x=>{
      const box=rhOutilCase(x.fait,x.libelle+' · '+L.etat);
      const lbl=h('span',{className:'rho-item-lbl'},x.libelle);
      const ligne=h('div',{className:'rho-item'+(x.fait?' done':'')},
        box,lbl,
        L.pieces?rhOutilBoutonPieces(L,m,x):null,
        h('button',{type:'button',className:'rho-item-x',title:'Retirer',onClick:()=>rhOutilRetirerElement(L,m,x)},'×')
      );
      box.addEventListener('change',()=>rhOutilCocherElement(L,m,x,box,ligne));
      lbl.addEventListener('click',()=>{box.checked=!box.checked;rhOutilCocherElement(L,m,x,box,ligne);});
      return ligne;
    }):[h('div',{className:'rho-item-none'},L.aucun)]),
    h('div',{className:'rho-items-foot'},
      h('button',{type:'button',className:'rho-add',onClick:()=>rhOutilAttribuer(L,m)},iconEl('plus',11),L.bouton),
      items.length?h('span',{className:'rho-count'+(nbOk===items.length?' full':'')},nbOk+'/'+items.length):null
    )
  );
}

function renderRhOutilTab(){
  const list=S.rhOutilMembres||[];
  // Filtre par service : seulement les services présents dans la liste.
  const fs=S.rhOutilFiltreService||'';
  const presents=new Set(list.map(m=>m.service));
  const selFiltre=h('select',{className:'rho-select'+(fs?' on':''),'aria-label':'Filtrer par service'},
    h('option',{value:''},'Tous les services'),
    ...(S.rhOutilServices||[]).filter(sv=>presents.has(sv.code)).map(sv=>h('option',{value:sv.code},sv.label))
  );
  selFiltre.value=fs;
  if(selFiltre.value!==fs)selFiltre.value='';
  selFiltre.addEventListener('change',()=>set({rhOutilFiltreService:selFiltre.value}));
  const bar=h('div',{className:'rho-bar'},
    list.length?selFiltre:null,
    h('div',{className:'rho-bar-spacer'}),
    ...RH_OUTIL_LISTES.map(L=>h('button',{type:'button',className:'rho-btn',onClick:()=>rhOutilCatalogue(L)},iconEl('sliders',13),L.gerer)),
    h('button',{type:'button',className:'rho-btn accent',onClick:rhOutilAjouterEmploye},iconEl('plus',13),'Ajouter un utilisateur')
  );
  if(!S.rhOutilLoaded)return h('div',null,bar,h('div',{className:'card-empty'},'Chargement…'));
  if(!list.length)return h('div',null,bar,h('div',{className:'card-empty'},'Aucun employé — utilisez « Ajouter un utilisateur ».'));
  const iF=Math.max(0,RHO_FILTRES.findIndex(f=>f.cle===(S.rhOutilFiltre||'tous')));
  const filtre=RHO_FILTRES[iF],suivant=RHO_FILTRES[(iF+1)%RHO_FILTRES.length];
  const fsVal=selFiltre.value;
  const vis=list.filter(m=>(!fsVal||m.service===fsVal)&&(filtre.cle==='tous'||rhOutilComplet(m)===(filtre.cle==='complet')));
  const filtre_actif=filtre.cle!=='tous'||!!fsVal;
  const nbCol=2+RH_OUTIL_LISTES.length+RH_OUTIL_COLONNES.length+2;
  const thDossier=h('th',{className:'rho-c'},
    h('button',{type:'button',className:'rho-th-btn',title:'Filtre : '+filtre.label+' — cliquer pour afficher « '+suivant.label+' »',
      'aria-label':'Dossier, filtre '+filtre.label+'. Cliquer pour afficher '+suivant.label,
      onClick:()=>set({rhOutilFiltre:suivant.cle})},
      'Dossier',h('span',{className:'rho-th-filtre'+(filtre.cle==='tous'?'':' on')},filtre.court)
    )
  );
  return h('div',null,bar,h('div',{className:'card'},
    h('div',{className:'card-header'},h('h3',null,'Employés ('+(filtre_actif?vis.length+' sur '+list.length:list.length)+')')),
    h('div',{style:{overflowX:'auto'}},h('table',{className:'table-std rho-table'},
      h('thead',null,h('tr',null,
        h('th',null,'Employé'),
        h('th',null,'Service'),
        ...RH_OUTIL_LISTES.map(L=>h('th',null,L.titre)),
        ...RH_OUTIL_COLONNES.map(c=>h('th',{className:'rho-c'},c.label)),
        thDossier,
        h('th',{className:'rho-c'},'')
      )),
      h('tbody',null,...(vis.length?[]:[h('tr',null,h('td',{colspan:String(nbCol),className:'rho-empty'},
        fsVal?'Aucun employé ne correspond aux filtres.':filtre.cle==='complet'?'Aucun dossier complet.':'Aucun dossier incomplet.'))]),...vis.map(m=>h('tr',null,
        h('td',null,h('div',{className:'rho-emp-cell'},
          h('div',{className:'rho-avatar','aria-hidden':'true'},rhOutilInitiales(m.nom)),
          h('div',null,
            h('div',{className:'rho-emp-nom'},m.nom||'—',m.actif?null:h('span',{className:'rho-tag'},'Désactivé')),
            h('div',{className:'rho-sub'},m.email||'')
          )
        )),
        h('td',null,h('span',{className:'rho-svc'+(m.service_label?'':' vide')},m.service_label||'Non renseigné')),
        ...RH_OUTIL_LISTES.map(L=>h('td',null,rhOutilCelluleListe(L,m))),
        ...RH_OUTIL_COLONNES.map(c=>h('td',{className:'rho-c'},rhOutilOuiNon(m,c))),
        h('td',{className:'rho-c','data-rho-statut':String(m.id)},rhOutilBadge(m)),
        h('td',{className:'rho-c'},h('button',{type:'button',className:'rho-del',title:'Retirer de la liste',onClick:()=>rhOutilRetirerEmploye(m)},iconEl('trash',13)))
      )))
    ))
  ));
}

"""

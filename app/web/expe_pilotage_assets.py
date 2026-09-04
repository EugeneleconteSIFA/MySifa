"""MyExpé — onglet Pilotage : CSS/JS injectés dans app/web/html.py.

Pas de route FastAPI ici. L'API est dans app/routers/expe_pilotage.py, la
construction de la vue dans app/services/expe_pilotage.py.

Le parti pris d'affichage : une ligne = un envoi, et les trois questions
d'Eugène deviennent trois colonnes qui se lisent de gauche à droite dans
l'ordre où elles se posent — transport commandé, parti, bon de livraison. Ce
qui n'est pas encore fait est un bouton ; ce qui est fait est une pastille avec
sa date. Rien à ouvrir pour savoir où on en est.
"""

EXPE_PILOTAGE_CSS = r"""
/* ── MyExpé — pilotage des expéditions ── */
.expe-pil-tuiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-bottom:14px}
.expe-pil-tuile{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 14px}
.expe-pil-tuile-lbl{font-size:11px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;color:var(--muted)}
.expe-pil-tuile-val{font-size:26px;font-weight:800;color:var(--text);line-height:1.15;margin-top:4px}
.expe-pil-tuile--retard{border-color:var(--danger)}
.expe-pil-tuile--retard .expe-pil-tuile-val{color:var(--danger)}
.expe-pil-tuile--warn{border-color:var(--warn)}
.expe-pil-tuile--warn .expe-pil-tuile-val{color:var(--warn)}
.expe-pil-tuile--ok .expe-pil-tuile-val{color:var(--success)}

.expe-pil-barre{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:12px}
.expe-pil-seg{display:flex;gap:4px;flex-wrap:wrap}
.expe-pil-seg button{background:var(--card);border:1px solid var(--border);color:var(--text2);
  border-radius:9px;padding:7px 13px;font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;
  transition:filter .15s}
.expe-pil-seg button:hover{background:var(--bg)}
.expe-pil-seg button.on{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.expe-pil-search{flex:1;min-width:180px;max-width:340px;padding:9px 13px;background:var(--card);
  border:1px solid var(--border);border-radius:10px;color:var(--text);font-size:13px;font-family:inherit;outline:none}
.expe-pil-search:focus{border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 12%,transparent)}

.expe-pil-wrap{overflow-x:auto}
.expe-pil-table{width:100%;border-collapse:collapse;font-size:13px}
.expe-pil-table th{font-size:11px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;
  color:var(--muted);text-align:left;padding:9px 10px;border-bottom:1px solid var(--border);white-space:nowrap}
.expe-pil-table td{padding:10px;border-bottom:1px solid var(--border);vertical-align:top}
.expe-pil-table tr:last-child td{border-bottom:none}
.expe-pil-row--retard{background:color-mix(in srgb,var(--danger) 7%,transparent)}
.expe-pil-row--urgent{background:color-mix(in srgb,var(--warn) 8%,transparent)}
.expe-pil-row--parti{opacity:.62}

.expe-pil-quand{font-weight:800;white-space:nowrap}
.expe-pil-j{font-size:11px;font-weight:700;white-space:nowrap}
.expe-pil-j--retard{color:var(--danger)}
.expe-pil-j--urgent{color:var(--warn)}
.expe-pil-j--ok{color:var(--muted)}
.expe-pil-src{font-size:10px;font-weight:700;letter-spacing:.3px;text-transform:uppercase;color:var(--muted);
  border:1px solid var(--border);border-radius:6px;padding:1px 5px;display:inline-block;margin-top:3px}

.expe-pil-client{font-weight:700;color:var(--text)}
.expe-pil-dest{font-size:12px;color:var(--muted);margin-top:2px}
.expe-pil-dos{font-size:12px;color:var(--text2);margin-top:2px;line-height:1.5}
.expe-pil-dos-ref{border:1px solid var(--border);border-radius:6px;padding:1px 6px;margin-right:4px;
  display:inline-block;font-family:monospace;font-size:11px}
.expe-pil-dos-ref--prod{border-color:var(--warn);color:var(--warn)}
.expe-pil-dos-ref--ok{border-color:var(--success);color:var(--success)}

.expe-pil-pal{display:flex;align-items:center;gap:6px}
.expe-pil-pal-val{font-family:monospace;font-size:15px;font-weight:800}
.expe-pil-pal-input{width:62px;padding:5px 7px;background:var(--bg);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-size:13px;font-family:monospace;text-align:right;outline:none}
.expe-pil-pal-input:focus{border-color:var(--accent)}
.expe-pil-pal-src{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;color:var(--muted)}
.expe-pil-pal-src--estime{color:var(--warn)}

.expe-pil-jalon{display:inline-flex;align-items:center;gap:5px;font-size:12px;white-space:nowrap}
.expe-pil-jalon--ok{color:var(--success);font-weight:700}
.expe-pil-jalon-date{font-size:11px;color:var(--muted);display:block;margin-top:2px}
.expe-pil-act{background:var(--bg);border:1px solid var(--border);color:var(--text);border-radius:8px;
  padding:6px 11px;font-size:12px;font-weight:700;cursor:pointer;font-family:inherit;white-space:nowrap;
  transition:filter .15s}
.expe-pil-act:hover{border-color:var(--accent);color:var(--accent)}
.expe-pil-act--go{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.expe-pil-act:disabled{opacity:.45;cursor:not-allowed}

.expe-pil-flag{font-size:11px;font-weight:700;border-radius:6px;padding:1px 6px;display:inline-block;margin-top:4px}
.expe-pil-flag--prod{background:color-mix(in srgb,var(--danger) 15%,transparent);color:var(--danger)}
.expe-pil-flag--part{background:color-mix(in srgb,var(--warn) 15%,transparent);color:var(--warn)}
.expe-pil-flag--fsc{background:color-mix(in srgb,var(--accent) 15%,transparent);color:var(--accent)}

.expe-pil-vide{text-align:center;color:var(--muted);padding:26px 12px;font-size:13px}
.expe-pil-avert{border:1px solid var(--warn);background:color-mix(in srgb,var(--warn) 10%,transparent);
  color:var(--text);border-radius:10px;padding:10px 13px;font-size:12px;margin-bottom:12px}

.expe-pil-reglages{margin-top:14px}
.expe-pil-reglages-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-top:10px}
.expe-pil-reglages label{display:block;font-size:11px;font-weight:600;letter-spacing:.5px;
  text-transform:uppercase;color:var(--muted);margin-bottom:5px}
.expe-pil-reglages input{width:100%;padding:8px 11px;background:var(--bg);border:1px solid var(--border);
  border-radius:9px;color:var(--text);font-size:13px;font-family:inherit;outline:none}
.expe-pil-reglages input:focus{border-color:var(--accent)}
.expe-pil-aide{font-size:11px;color:var(--muted);margin-top:5px;line-height:1.45}

/* Cartes sous 860 px : le tableau a huit colonnes, il ne tient pas. */
@media (max-width:860px){
  .expe-pil-cartes{display:flex;flex-direction:column;gap:10px}
  .expe-pil-carte{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:12px 13px}
  .expe-pil-carte--retard{border-color:var(--danger)}
  .expe-pil-carte--urgent{border-color:var(--warn)}
  .expe-pil-carte-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
  .expe-pil-carte-jalons{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;
    padding-top:10px;border-top:1px solid var(--border)}
}
"""


EXPE_PILOTAGE_JS = r"""
// ── MyExpé — Pilotage des expéditions ────────────────────────────────────
//
// Répond à trois questions par envoi : le transport est-il commandé, est-ce
// parti, le bon de livraison est-il fait ? Et surtout : que faut-il commander
// AUJOURD'HUI pour ce qui part la semaine prochaine.
//
// Toutes les actions renvoient le tableau recalculé par le serveur : on ne
// modifie jamais l'état local à la main après une écriture, sinon l'écran et
// la base se mettent à raconter deux histoires différentes.

var EXPE_PIL_FILTRES=[
  {key:'a_faire',  label:'À traiter'},
  {key:'retard',   label:'En retard'},
  {key:'commande', label:'Transport commandé'},
  {key:'parti',    label:'Partis'},
  {key:'tout',     label:'Tout'}
];

var _expePilSearchTimer=null;

async function loadExpePilotage(){
  set({expePilotageLoading:true});
  try{
    const data=await api('/api/expe/pilotage');
    set({expePilotage:data,expePilotageLoading:false});
  }catch(e){
    set({expePilotageLoading:false});
    showToast(e.message||'Chargement du pilotage impossible','danger');
  }
}

function _expePilJourFR(iso){
  if(!iso)return '—';
  const s=String(iso).slice(0,10);
  const m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
  return m?(m[3]+'/'+m[2]+'/'+m[1]):s;
}

function _expePilSrcLabel(src){
  if(src==='rvgi')return 'RVGI';
  if(src==='planning')return 'Planning';
  if(src==='fin_prod')return 'Fin de prod';
  return 'À dater';
}

function _expePilJours(env){
  const j=env.jours_restants;
  if(j===null||j===undefined)return {txt:'date inconnue',cls:'expe-pil-j--retard'};
  if(j<0)return {txt:'en retard de '+Math.abs(j)+' j',cls:'expe-pil-j--retard'};
  if(j===0)return {txt:'aujourd’hui',cls:'expe-pil-j--urgent'};
  if(j===1)return {txt:'demain',cls:'expe-pil-j--urgent'};
  return {txt:'dans '+j+' j',cls:'expe-pil-j--ok'};
}

function _expePilCorrespond(env,q){
  if(!q)return true;
  const t=(q||'').toLowerCase();
  const blob=[env.client,env.destinataire,env.ville,env.code_postal,
    (env.commandes_rvgi||[]).join(' '),
    (env.dossiers||[]).map(function(d){return d.reference;}).join(' '),
    (env.jalons&&env.jalons.transport.transporteur)||'',
    (env.jalons&&env.jalons.bl.numeros||[]).join(' ')].join(' ').toLowerCase();
  return t.split(/\s+/).filter(Boolean).every(function(tok){return blob.indexOf(tok)!==-1;});
}

function _expePilFiltre(envois,filtre,q){
  return envois.filter(function(e){
    if(!_expePilCorrespond(e,q))return false;
    if(filtre==='tout')return true;
    if(filtre==='retard')return e.alerte==='retard';
    if(filtre==='commande')return e.jalons.transport.fait&&e.alerte!=='parti';
    if(filtre==='parti')return e.alerte==='parti';
    // 'a_faire' par défaut : ce qui demande une décision maintenant.
    return e.alerte==='retard'||e.alerte==='urgent'||e.alerte==='a_commander';
  });
}


// ── Actions ─────────────────────────────────────────────────────────────

async function expePilAction(cle,verbe,body){
  try{
    const data=await api('/api/expe/pilotage/envois/'+encodeURIComponent(cle)+'/'+verbe,{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body||{})
    });
    set({expePilotage:data,expePilModal:null});
    return true;
  }catch(e){
    showToast(e.message||'Action impossible','danger');
    return false;
  }
}

function expePilOuvrirTransport(env){
  set({expePilModal:{
    cle:env.cle_envoi,
    client:env.client,
    ville:env.ville,
    code_postal:env.code_postal,
    transporteur:(env.jalons.transport.transporteur)||'',
    no_cde_transport:(env.jalons.transport.reference)||'',
    date_enlevement:env.date_cible||'',
    nb_palette:(env.nb_palette!=null?String(env.nb_palette):''),
    type_envoi:env.type_envoi,
    prod_prete:env.prod_prete,
    prod_fin_prevue:env.prod_fin_prevue
  }});
}

async function expePilValiderTransport(){
  const m=S.expePilModal;
  if(!m)return;
  const ok=await expePilAction(m.cle,'transport',{
    transporteur:m.transporteur||null,
    no_cde_transport:m.no_cde_transport||null,
    date_enlevement:m.date_enlevement||null,
    nb_palette:m.nb_palette||null
  });
  if(ok)showToast('Transport commandé. Le départ rejoint « Départs programmés ».','success');
}

async function expePilMarquerParti(env){
  const ok=await expePilAction(env.cle_envoi,'parti',{});
  if(ok)showToast('Envoi déclaré parti.','success');
}

async function expePilPalettes(env,valeur){
  const v=String(valeur||'').replace(',','.').trim();
  if(v===''||!isFinite(parseFloat(v))){showToast('Nombre de palettes invalide.','danger');return;}
  const ok=await expePilAction(env.cle_envoi,'palettes',{nb_palette:parseFloat(v)});
  if(ok)showToast('Palettes mises à jour.','success');
}

async function expePilEnregistrerReglages(vals){
  try{
    await api('/api/expe/pilotage/params',{method:'PUT',
      headers:{'Content-Type':'application/json'},body:JSON.stringify(vals)});
    showToast('Réglages enregistrés.','success');
    await loadExpePilotage();
  }catch(e){
    showToast(e.message||'Enregistrement impossible','danger');
  }
}
"""


# Rendu. Séparé du bloc d'actions ci-dessus pour que chaque morceau tienne sous
# les yeux ; les deux sont concaténés à l'injection.
EXPE_PILOTAGE_JS += r"""

function _expePilTuiles(r){
  const t=[
    {lbl:'En retard',        val:r.retard,             cls:r.retard?'expe-pil-tuile--retard':''},
    {lbl:'À commander',      val:r.a_commander,        cls:r.a_commander?'expe-pil-tuile--warn':''},
    {lbl:'Palettes à réserver',val:r.palettes_a_reserver||0,cls:''},
    {lbl:'Transport commandé',val:r.transport_commande, cls:'expe-pil-tuile--ok'},
    {lbl:'Sans BL',          val:r.bl_manquant,        cls:''}
  ];
  return h('div',{className:'expe-pil-tuiles'},
    ...t.map(function(x){
      return h('div',{className:'expe-pil-tuile '+x.cls},
        h('div',{className:'expe-pil-tuile-lbl'},x.lbl),
        h('div',{className:'expe-pil-tuile-val'},String(x.val!=null?x.val:0)));
    }));
}

function _expePilCelluleQuand(env){
  const j=_expePilJours(env);
  return h('td',null,
    h('div',{className:'expe-pil-quand'},_expePilJourFR(env.date_cible)),
    h('div',{className:'expe-pil-j '+j.cls},j.txt),
    h('span',{className:'expe-pil-src',title:'Origine de la date d’expédition visée'},
      _expePilSrcLabel(env.date_cible_source))
  );
}

function _expePilCelluleEnvoi(env){
  const dos=(env.dossiers||[]).map(function(d){
    const cls=d.etat==='termine'?'expe-pil-dos-ref--ok':
              (d.etat==='en_cours'?'expe-pil-dos-ref--prod':'');
    return h('span',{className:'expe-pil-dos-ref '+cls,
      title:(d.machine||'')+' · '+(d.etat==='termine'?'production terminée':
             d.etat==='en_cours'?'en production':'en attente de production')},
      d.reference||('#'+d.id));
  });
  const flags=[];
  if(env.prod_apres_expedition)
    flags.push(h('span',{className:'expe-pil-flag expe-pil-flag--prod',
      title:'Fin de production prévue le '+_expePilJourFR(env.prod_fin_prevue)},
      'Prod après la date d’expédition'));
  if((env.dossiers||[]).some(function(d){return d.fsc_requis;}))
    flags.push(h('span',{className:'expe-pil-flag expe-pil-flag--fsc'},'FSC'));
  if((env.dossiers||[]).some(function(d){return d.prise_rdv;}))
    flags.push(h('span',{className:'expe-pil-flag expe-pil-flag--part'},'Prise de RDV'));
  return h('td',null,
    h('div',{className:'expe-pil-client'},env.client||'—'),
    h('div',{className:'expe-pil-dest'},
      [env.code_postal,env.ville].filter(Boolean).join(' ')||'destination inconnue'),
    dos.length?h('div',{className:'expe-pil-dos'},...dos):null,
    flags.length?h('div',null,...flags):null
  );
}

function _expePilCellulePalettes(env){
  const src=env.nb_palette_source;
  const libelle={saisi:'saisi',bl:'bon de livraison',estime:'estimé'}[src]||'à estimer';
  const val=env.nb_palette;
  const peut=expeCanWrite()&&env.alerte!=='parti';
  const champ=peut?h('input',{
    className:'expe-pil-pal-input',
    type:'text',
    value:(val!=null?String(val):''),
    placeholder:'—',
    title:'Corriger le nombre de palettes',
    onKeyDown:function(e){if(e.key==='Enter'){e.preventDefault();void expePilPalettes(env,e.target.value);}},
    onBlur:function(e){
      const av=(val!=null?String(val):'');
      if(e.target.value.trim()!==av.trim())void expePilPalettes(env,e.target.value);
    }
  }):h('span',{className:'expe-pil-pal-val'},val!=null?String(val):'—');
  return h('td',null,
    h('div',{className:'expe-pil-pal'},champ),
    h('div',{className:'expe-pil-pal-src'+(src==='estime'?' expe-pil-pal-src--estime':'')},libelle),
    env.nb_palette_estime_partiel?h('div',{className:'expe-pil-flag expe-pil-flag--part',
      title:(env.manques||[]).join(' · ')},'estimation partielle'):null,
    (val==null&&(env.manques||[]).length)?h('div',{className:'expe-pil-aide',
      title:(env.manques||[]).join(' · ')},'Fiche incomplète'):null
  );
}

function _expePilCelluleTransport(env){
  const t=env.jalons.transport;
  if(t.fait){
    return h('td',null,
      h('span',{className:'expe-pil-jalon expe-pil-jalon--ok'},iconEl('check',13),' ',
        t.transporteur||'commandé'),
      h('span',{className:'expe-pil-jalon-date'},
        (t.reference?t.reference+' · ':'')+
        (t.date_enlevement?'enlèv. '+_expePilJourFR(t.date_enlevement):'')),
      (!t.date_confirmee&&t.date_enlevement)?h('span',{className:'expe-pil-jalon-date',
        title:'Date déduite du planning, pas encore arrêtée avec le transporteur'},'date prévisionnelle'):null
    );
  }
  if(!expeCanWrite())return h('td',null,h('span',{className:'expe-pil-jalon'},'—'));
  const presse=env.alerte==='retard'||env.alerte==='urgent'||env.alerte==='a_commander';
  return h('td',null,
    h('button',{type:'button',className:'expe-pil-act'+(presse?' expe-pil-act--go':''),
      title:env.a_commander_le?('À commander au plus tard le '+_expePilJourFR(env.a_commander_le)):'',
      onClick:function(){expePilOuvrirTransport(env);}},'Commander'),
    env.a_commander_le?h('span',{className:'expe-pil-jalon-date'},
      'au plus tard le '+_expePilJourFR(env.a_commander_le)):null
  );
}

function _expePilCelluleParti(env){
  const p=env.jalons.parti;
  if(p.fait)return h('td',null,
    h('span',{className:'expe-pil-jalon expe-pil-jalon--ok'},iconEl('check',13),' Parti'),
    h('span',{className:'expe-pil-jalon-date'},_expePilJourFR(p.le)));
  if(!expeCanWrite())return h('td',null,h('span',{className:'expe-pil-jalon'},'—'));
  const pret=env.jalons.transport.fait;
  return h('td',null,
    h('button',{type:'button',className:'expe-pil-act',disabled:!pret,
      title:pret?'Déclarer l’enlèvement effectué':'Commander le transport d’abord',
      onClick:function(){void expePilMarquerParti(env);}},'Parti'));
}

function _expePilCelluleBL(env){
  const bl=env.jalons.bl;
  if(bl.fait)return h('td',null,
    h('span',{className:'expe-pil-jalon expe-pil-jalon--ok'},iconEl('check',13),' ',
      bl.numeros.slice(0,2).join(' · ')),
    bl.numeros.length>2?h('span',{className:'expe-pil-jalon-date'},
      '+ '+(bl.numeros.length-2)+' autre(s)'):null);
  return h('td',null,h('span',{className:'expe-pil-jalon',
    title:'Le bon de livraison se crée dans RVGI — MySifa le lit, il ne l’écrit pas'},'À faire'));
}
"""


EXPE_PILOTAGE_JS += r"""

function _expePilCarte(env){
  const j=_expePilJours(env);
  const t=env.jalons.transport;
  return h('div',{className:'expe-pil-carte'+(env.alerte==='retard'?' expe-pil-carte--retard':
                                              env.alerte==='urgent'?' expe-pil-carte--urgent':'')},
    h('div',{className:'expe-pil-carte-head'},
      h('div',null,
        h('div',{className:'expe-pil-client'},env.client||'—'),
        h('div',{className:'expe-pil-dest'},
          [env.code_postal,env.ville].filter(Boolean).join(' ')||'destination inconnue')),
      h('div',{style:{textAlign:'right'}},
        h('div',{className:'expe-pil-quand'},_expePilJourFR(env.date_cible)),
        h('div',{className:'expe-pil-j '+j.cls},j.txt))
    ),
    h('div',{className:'expe-pil-dos'},
      (env.nb_palette!=null?env.nb_palette+' palette(s)':'palettes à estimer')+
      ' · '+(env.type_envoi==='affretement'?'affrètement':'messagerie')+
      ' · '+(env.dossiers||[]).length+' dossier(s)'),
    h('div',{className:'expe-pil-carte-jalons'},
      t.fait
        ?h('span',{className:'expe-pil-jalon expe-pil-jalon--ok'},iconEl('check',13),' ',
           t.transporteur||'Transport commandé')
        :(expeCanWrite()?h('button',{type:'button',className:'expe-pil-act expe-pil-act--go',
           onClick:function(){expePilOuvrirTransport(env);}},'Commander le transport')
          :h('span',{className:'expe-pil-jalon'},'Transport à commander')),
      env.jalons.parti.fait
        ?h('span',{className:'expe-pil-jalon expe-pil-jalon--ok'},iconEl('check',13),' Parti')
        :(expeCanWrite()&&t.fait?h('button',{type:'button',className:'expe-pil-act',
           onClick:function(){void expePilMarquerParti(env);}},'Parti'):null),
      env.jalons.bl.fait
        ?h('span',{className:'expe-pil-jalon expe-pil-jalon--ok'},iconEl('check',13),' BL ',
           env.jalons.bl.numeros[0]||'')
        :h('span',{className:'expe-pil-jalon'},'BL à faire')
    )
  );
}

function _expePilReglages(data){
  if(!S.expePilReglagesOuvert){
    return h('div',{className:'expe-pil-reglages'},
      h('button',{type:'button',className:'expe-pil-act',
        onClick:function(){set({expePilReglagesOuvert:true});}},
        iconEl('sliders',13),' Réglages du pilotage'));
  }
  const p=data.params||{};
  const champs=[
    {cle:'horizon_jours',label:'Horizon (jours)',
     aide:'Au-delà, les envois sortent du tableau — sauf ce qui est en retard ou à commander, jamais masqué.'},
    {cle:'preavis_messagerie_jours',label:'Préavis messagerie (jours)',
     aide:'À J-N avant la date d’expédition, l’envoi passe en « à commander ».'},
    {cle:'preavis_affretement_jours',label:'Préavis affrètement (jours)',
     aide:'Plus long : un camion complet se réserve plus tôt qu’une messagerie.'},
    {cle:'seuil_affretement_palettes',label:'Seuil affrètement (palettes)',
     aide:'Au-delà de ce nombre de palettes, l’envoi est traité en affrètement.'}
  ];
  const refs={};
  const grille=h('div',{className:'expe-pil-reglages-grid'},
    ...champs.map(function(c){
      const inp=h('input',{type:'number',step:'1',min:'0',value:String(p[c.cle]!=null?p[c.cle]:'')});
      refs[c.cle]=inp;
      return h('div',null,h('label',null,c.label),inp,h('div',{className:'expe-pil-aide'},c.aide));
    }));
  return h('div',{className:'card expe-pil-reglages'},
    h('div',{className:'card-header'},h('h3',null,'Réglages du pilotage')),
    grille,
    h('div',{style:{display:'flex',gap:'8px',marginTop:'14px',flexWrap:'wrap'}},
      expeCanWrite()?h('button',{type:'button',className:'btn-accent',onClick:function(){
        const vals={};champs.forEach(function(c){vals[c.cle]=refs[c.cle].value;});
        void expePilEnregistrerReglages(vals);
      }},'Enregistrer'):null,
      h('button',{type:'button',className:'expe-pil-act',
        onClick:function(){set({expePilReglagesOuvert:false});}},'Fermer'))
  );
}

function renderExpePilotageModal(){
  const m=S.expePilModal;
  if(!m)return null;
  const champ=function(cle,label,attrs){
    const inp=h('input',Object.assign({
      value:m[cle]||'',
      onInput:function(e){m[cle]=e.target.value;}
    },attrs||{}));
    return h('div',null,h('label',null,label),inp,null);
  };
  const overlay=h('div',{className:'expe-trp-overlay open',
    onClick:function(e){if(e.target===overlay)set({expePilModal:null});}});
  const box=h('div',{className:'card',style:{position:'fixed',top:'50%',left:'50%',
    transform:'translate(-50%,-50%)',zIndex:'11502',width:'min(480px,94vw)',
    maxHeight:'90vh',overflowY:'auto',padding:'18px 20px'}},
    h('h3',{style:{marginTop:'0'}},'Commander le transport'),
    h('div',{className:'expe-pil-dest',style:{marginBottom:'14px'}},
      (m.client||'')+' · '+[m.code_postal,m.ville].filter(Boolean).join(' ')+
      ' · '+(m.type_envoi==='affretement'?'affrètement':'messagerie')),
    (!m.prod_prete&&m.prod_fin_prevue)?h('div',{className:'expe-pil-avert'},
      'Production non terminée — fin prévue le '+_expePilJourFR(m.prod_fin_prevue)+
      '. Réserver maintenant reste possible : c’est même l’objet de cet écran.'):null,
    h('div',{className:'expe-pil-reglages-grid'},
      champ('transporteur','Transporteur',{type:'text',list:'expe-pil-trp',placeholder:'Nom du transporteur'}),
      champ('no_cde_transport','N° de commande transport',{type:'text',placeholder:'Référence ou « mail du … »'}),
      champ('date_enlevement','Date d’enlèvement',{type:'date'}),
      champ('nb_palette','Nombre de palettes',{type:'text',placeholder:'—'})
    ),
    h('datalist',{id:'expe-pil-trp'},
      ...((T&&T.list)||[]).map(function(t){return h('option',{value:t.nom||''});})),
    h('div',{className:'expe-pil-aide',style:{marginTop:'10px'}},
      'La plupart des transporteurs tarifent au nombre de palettes : c’est ce chiffre '+
      'qu’il faut donner, le poids vient ensuite.'),
    h('div',{style:{display:'flex',gap:'8px',marginTop:'16px',justifyContent:'flex-end'}},
      h('button',{type:'button',className:'expe-pil-act',
        onClick:function(){set({expePilModal:null});}},'Annuler'),
      h('button',{type:'button',className:'btn-accent',
        onClick:function(){void expePilValiderTransport();}},'Enregistrer'))
  );
  return h('div',null,overlay,box);
}

function renderExpePilotage(){
  const data=S.expePilotage;
  if(!data){
    return h('div',{className:'card'},
      h('div',{className:'expe-pil-vide'},
        S.expePilotageLoading?'Chargement du tableau de bord…':'Aucune donnée.'));
  }
  const filtre=S.expePilFiltre||'a_faire';
  const q=S.expePilQ||'';
  const envois=_expePilFiltre(data.envois||[],filtre,q);

  const recherche=h('input',{
    id:'expe-pil-search',
    className:'expe-pil-search',
    type:'search',
    placeholder:'Client, ville, n° de commande, dossier, transporteur…',
    value:q,
    onInput:function(e){
      // Pas de render par caractère : on perdrait le focus. On repousse.
      S.expePilQ=e.target.value;
      if(_expePilSearchTimer)clearTimeout(_expePilSearchTimer);
      _expePilSearchTimer=setTimeout(function(){
        const pos=e.target.selectionStart;
        render();
        requestAnimationFrame(function(){
          const el=document.getElementById('expe-pil-search');
          if(el){el.focus();try{el.setSelectionRange(pos,pos);}catch(_e){}}
        });
      },250);
    }
  });

  const barre=h('div',{className:'expe-pil-barre'},
    h('div',{className:'expe-pil-seg'},
      ...EXPE_PIL_FILTRES.map(function(f){
        return h('button',{type:'button',className:(filtre===f.key?'on':''),
          onClick:function(){set({expePilFiltre:f.key});}},f.label);
      })),
    recherche,
    h('button',{type:'button',className:'expe-pil-act',title:'Recharger',
      onClick:function(){void loadExpePilotage();}},iconEl('refresh-cw',13),' Actualiser')
  );

  const avert=[];
  if(data.rvgi&&!data.rvgi.present)
    avert.push(h('div',{className:'expe-pil-avert'},
      'Miroir RVGI indisponible — les dates d’expédition demandées, les adresses de '+
      'livraison et les bons de livraison ne sont pas affichés. Le reste du tableau '+
      'reste juste.'));
  if((data.resume||{}).sans_estimation)
    avert.push(h('div',{className:'expe-pil-avert'},
      (data.resume.sans_estimation)+' envoi(s) sans nombre de palettes : fiche technique '+
      'incomplète. Le chiffre peut être saisi directement dans la colonne Palettes.'));

  const corps=expeEnCartes()
    ? (envois.length
        ? h('div',{className:'expe-pil-cartes'},...envois.map(_expePilCarte))
        : h('div',{className:'card'},h('div',{className:'expe-pil-vide'},'Rien à traiter ici.')))
    : h('div',{className:'card'},
        h('div',{className:'expe-pil-wrap'},
          h('table',{className:'expe-pil-table'},
            h('thead',null,h('tr',null,
              ...['Départ visé','Envoi','Palettes','Transport','Parti','Bon de livraison']
                .map(function(x){return h('th',null,x);}))),
            h('tbody',null,
              ...(envois.length?envois.map(function(env){
                return h('tr',{className:'expe-pil-row'+
                    (env.alerte==='retard'?' expe-pil-row--retard':
                     env.alerte==='urgent'?' expe-pil-row--urgent':
                     env.alerte==='parti'?' expe-pil-row--parti':'')},
                  _expePilCelluleQuand(env),
                  _expePilCelluleEnvoi(env),
                  _expePilCellulePalettes(env),
                  _expePilCelluleTransport(env),
                  _expePilCelluleParti(env),
                  _expePilCelluleBL(env));
              }):[h('tr',null,h('td',{colSpan:6},
                    h('div',{className:'expe-pil-vide'},
                      q?'Aucun envoi ne correspond à cette recherche.'
                       :'Rien à traiter ici — voir « Tout » pour l’ensemble des envois.')))])))));

  return h('div',null,
    _expePilTuiles(data.resume||{}),
    ...avert,
    barre,
    corps,
    _expePilReglages(data),
    renderExpePilotageModal()
  );
}
"""

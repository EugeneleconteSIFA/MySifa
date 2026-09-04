"""MyExpé — onglet Pilotage : CSS/JS injectés dans app/web/html.py.

Pas de route FastAPI ici. L'API est dans app/routers/expe_pilotage.py, la
construction de la vue dans app/services/expe_pilotage.py.

Le parti pris d'affichage : une ligne = un envoi, et les trois questions
d'Eugène deviennent trois colonnes qui se lisent de gauche à droite dans
l'ordre où elles se posent — transport programmé, parti, bon de livraison. Ce
qui n'est pas encore fait est un bouton ; ce qui est fait est une pastille avec
sa date. Rien à ouvrir pour savoir où on en est.
"""

EXPE_PILOTAGE_CSS = r"""
/* ── MyExpé — pilotage des expéditions ──
 *
 * Densité : cet écran se lit d'un coup d'oeil, plusieurs fois par jour. La
 * couleur y est un signal, pas une decoration — elle ne sert qu'au retard et a
 * l'urgence, en filet vertical plutot qu'en aplat de ligne : un tableau ou une
 * ligne sur deux est teintee ne signale plus rien.
 */
.expe-pil-tuiles{display:flex;flex-wrap:wrap;gap:22px;padding:12px 14px;margin-bottom:12px;
  background:var(--card);border:1px solid var(--border);border-radius:10px}
.expe-pil-tuile{min-width:96px}
.expe-pil-tuile-lbl{font-size:10px;font-weight:600;letter-spacing:.4px;text-transform:uppercase;color:var(--muted)}
.expe-pil-tuile-val{font-size:19px;font-weight:700;color:var(--text);line-height:1.2;margin-top:1px}
.expe-pil-tuile--retard .expe-pil-tuile-val{color:var(--danger)}
.expe-pil-tuile--warn .expe-pil-tuile-val{color:var(--warn)}

.expe-pil-barre{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:10px}
.expe-pil-seg{display:flex;gap:3px;flex-wrap:wrap}
.expe-pil-seg button{background:var(--card);border:1px solid var(--border);color:var(--text2);
  border-radius:8px;padding:6px 11px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit}
.expe-pil-seg button:hover{background:var(--bg)}
.expe-pil-seg button.on{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.expe-pil-search{flex:1;min-width:170px;max-width:300px;padding:7px 11px;background:var(--card);
  border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:12px;font-family:inherit;outline:none}
.expe-pil-search:focus{border-color:var(--accent)}

.expe-pil-wrap{overflow-x:auto}
.expe-pil-table{width:100%;border-collapse:collapse;font-size:12.5px}
.expe-pil-table th{font-size:10px;font-weight:700;letter-spacing:.4px;text-transform:uppercase;
  color:var(--muted);text-align:left;padding:7px 10px;border-bottom:1px solid var(--border);white-space:nowrap}
.expe-pil-table td{padding:7px 10px;border-bottom:1px solid var(--border);vertical-align:top}
.expe-pil-table tr:last-child td{border-bottom:none}
/* Le filet vertical remplace l'aplat : meme information, sans repeindre la page. */
.expe-pil-row--retard td:first-child{box-shadow:inset 3px 0 0 var(--danger)}
.expe-pil-row--urgent td:first-child{box-shadow:inset 3px 0 0 var(--warn)}
.expe-pil-row--parti{opacity:.5}

.expe-pil-quand{font-weight:700;white-space:nowrap;font-size:13px}
.expe-pil-meta{font-size:11px;color:var(--muted);white-space:nowrap;margin-top:1px}
.expe-pil-meta--retard{color:var(--danger)}
.expe-pil-meta--urgent{color:var(--warn)}

.expe-pil-client{font-weight:600;color:var(--text)}
.expe-pil-dest{font-size:11px;color:var(--muted);margin-top:1px}
.expe-pil-dos{font-size:11px;color:var(--muted);margin-top:2px;line-height:1.6}
.expe-pil-dos-ref{font-family:monospace;font-size:11px;color:var(--text2);margin-right:8px;white-space:nowrap}
.expe-pil-dos-ref--prod{color:var(--warn)}

.expe-pil-pal{display:flex;align-items:baseline;gap:6px}
.expe-pil-pal-val{font-family:monospace;font-size:13px;font-weight:700}
.expe-pil-pal-input{width:52px;padding:4px 6px;background:var(--bg);border:1px solid var(--border);
  border-radius:6px;color:var(--text);font-size:12.5px;font-family:monospace;text-align:right;outline:none}
.expe-pil-pal-input:focus{border-color:var(--accent)}
.expe-pil-pal-src{font-size:11px;color:var(--muted)}
.expe-pil-pal-src--estime{font-style:italic}

.expe-pil-jalon{font-size:12px;white-space:nowrap;color:var(--text2)}
.expe-pil-jalon--ok{color:var(--success)}
.expe-pil-jalon-date{font-size:11px;color:var(--muted);display:block;margin-top:1px}
.expe-pil-nul{color:var(--muted);font-size:12px}
.expe-pil-act{background:var(--bg);border:1px solid var(--border);color:var(--text2);border-radius:7px;
  padding:4px 10px;font-size:12px;font-weight:600;cursor:pointer;font-family:inherit;white-space:nowrap}
.expe-pil-act:hover{border-color:var(--accent);color:var(--accent)}
.expe-pil-act--go{border-color:var(--accent);color:var(--accent)}
.expe-pil-act:disabled{opacity:.35;cursor:not-allowed}
.expe-pil-act:disabled:hover{border-color:var(--border);color:var(--text2)}

/* Marqueurs : du texte discret, pas des pastilles pleines. */
.expe-pil-flag{font-size:11px;margin-right:8px;white-space:nowrap}
.expe-pil-flag--prod{color:var(--danger)}
.expe-pil-flag--part{color:var(--warn)}
.expe-pil-flag--fsc{color:var(--accent)}

.expe-pil-vide{text-align:center;color:var(--muted);padding:24px 12px;font-size:12.5px}
.expe-pil-avert{font-size:11.5px;color:var(--muted);margin-bottom:8px;line-height:1.5}
.expe-pil-avert b{color:var(--text2);font-weight:600}

/* Reglages : la carte porte ses propres marges, la grille ne touche pas les bords. */
.expe-pil-reglages{margin-top:16px}
.expe-pil-reglages-corps{padding:16px 18px 18px}
.expe-pil-reglages-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:18px 20px}
.expe-pil-reglages label{display:block;font-size:10px;font-weight:600;letter-spacing:.5px;
  text-transform:uppercase;color:var(--muted);margin-bottom:6px}
.expe-pil-reglages input{width:100%;padding:8px 11px;background:var(--bg);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-size:13px;font-family:inherit;outline:none}
.expe-pil-reglages input:focus{border-color:var(--accent)}
.expe-pil-reglages-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:20px;
  padding-top:16px;border-top:1px solid var(--border)}
.expe-pil-aide{font-size:11px;color:var(--muted);margin-top:6px;line-height:1.45}

/* ── Modal « Programmer le transport » ──
 *
 * Meme grammaire que les autres modals MyExpe (overlay centre, entete avec
 * croix, pied a droite) : un ecran nouveau n'invente pas ses propres gestes.
 * Ce qu'il ajoute : un bandeau de contexte, parce qu'on programme un camion
 * en regardant la destination, les palettes et l'etat de la production —
 * aller les rechercher dans le tableau derriere le modal serait absurde.
 */
.expe-pil-modal-overlay{position:fixed;inset:0;background:color-mix(in srgb,var(--bg) 62%,transparent);
  z-index:12300;display:flex;align-items:center;justify-content:center;padding:16px;
  backdrop-filter:blur(2px)}
.expe-pil-modal{width:100%;max-width:600px;max-height:min(92vh,880px);overflow:auto;
  background:var(--card);border:1px solid var(--border);border-radius:14px;
  box-shadow:0 24px 60px color-mix(in srgb,var(--bg) 55%,transparent)}
.expe-pil-modal--large{max-width:820px}
.expe-pil-modal-head{display:flex;align-items:flex-start;justify-content:space-between;gap:12px;
  padding:18px 20px 14px;border-bottom:1px solid var(--border)}
.expe-pil-modal-titre{font-size:16px;font-weight:800;color:var(--text);margin:0}
.expe-pil-modal-sous{font-size:12px;color:var(--muted);margin-top:3px}
.expe-pil-modal-x{background:var(--bg);border:1px solid var(--border);color:var(--muted);
  border-radius:8px;width:30px;height:30px;display:inline-flex;align-items:center;justify-content:center;
  cursor:pointer;flex-shrink:0}
.expe-pil-modal-x:hover{color:var(--text);border-color:var(--accent)}
.expe-pil-modal-corps{padding:16px 20px 18px}

/* Bandeau de contexte : trois faits, alignes, sans ornement. */
.expe-pil-ctx{display:flex;flex-wrap:wrap;gap:20px;padding:11px 14px;margin-bottom:16px;
  background:var(--bg);border:1px solid var(--border);border-radius:10px}
.expe-pil-ctx-item{min-width:92px}
.expe-pil-ctx-lbl{font-size:10px;font-weight:600;letter-spacing:.4px;text-transform:uppercase;color:var(--muted)}
.expe-pil-ctx-val{font-size:14px;font-weight:700;color:var(--text);margin-top:2px}
.expe-pil-ctx-val--warn{color:var(--warn)}
.expe-pil-ctx-val--danger{color:var(--danger)}
.expe-pil-ctx-note{font-size:11px;color:var(--muted);font-weight:400;margin-top:1px}

.expe-pil-modal-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px 16px}
.expe-pil-modal-grid label{display:block;font-size:10px;font-weight:600;letter-spacing:.5px;
  text-transform:uppercase;color:var(--muted);margin-bottom:6px}
.expe-pil-modal-grid input{width:100%;padding:9px 12px;background:var(--bg);border:1px solid var(--border);
  border-radius:9px;color:var(--text);font-size:13px;font-family:inherit;outline:none;box-sizing:border-box}
.expe-pil-modal-grid input:focus{border-color:var(--accent);
  box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 12%,transparent)}
.expe-pil-modal-aide{font-size:11.5px;color:var(--muted);margin-top:12px;line-height:1.5}
.expe-pil-modal-foot{display:flex;align-items:center;gap:8px;flex-wrap:wrap;
  padding:14px 20px 18px;border-top:1px solid var(--border)}
.expe-pil-modal-foot-droite{margin-left:auto;display:flex;gap:8px}

/* Liste des departs a associer. */
.expe-pil-cand-liste{display:flex;flex-direction:column;gap:6px;max-height:46vh;overflow-y:auto;
  margin-top:12px}
.expe-pil-cand{display:flex;align-items:center;gap:12px;padding:9px 12px;background:var(--bg);
  border:1px solid var(--border);border-radius:9px;cursor:pointer;text-align:left;width:100%;
  font-family:inherit;color:var(--text)}
.expe-pil-cand:hover{border-color:var(--accent)}
.expe-pil-cand--pertinent{border-color:color-mix(in srgb,var(--accent) 45%,var(--border))}
.expe-pil-cand-date{font-weight:700;font-size:12.5px;white-space:nowrap;min-width:86px}
.expe-pil-cand-corps{flex:1;min-width:0}
.expe-pil-cand-titre{font-size:12.5px;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.expe-pil-cand-meta{font-size:11px;color:var(--muted);margin-top:1px}
.expe-pil-cand-raison{font-size:11px;color:var(--accent);white-space:nowrap}

/* Cartes sous 860 px : le tableau a six colonnes, il ne tient pas. */
@media (max-width:860px){
  .expe-pil-cartes{display:flex;flex-direction:column;gap:8px}
  .expe-pil-carte{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:11px 12px}
  .expe-pil-carte--retard{border-left:3px solid var(--danger)}
  .expe-pil-carte--urgent{border-left:3px solid var(--warn)}
  .expe-pil-carte-head{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}
  .expe-pil-carte-jalons{display:flex;gap:10px;flex-wrap:wrap;margin-top:9px;
    padding-top:9px;border-top:1px solid var(--border)}
  .expe-pil-tuiles{gap:16px}
}
"""


EXPE_PILOTAGE_JS = r"""
// ── MyExpé — Pilotage des expéditions ────────────────────────────────────
//
// Répond à trois questions par envoi : le transport est-il programmé, est-ce
// parti, le bon de livraison est-il fait ? Et surtout : que faut-il commander
// AUJOURD'HUI pour ce qui part la semaine prochaine.
//
// Toutes les actions renvoient le tableau recalculé par le serveur : on ne
// modifie jamais l'état local à la main après une écriture, sinon l'écran et
// la base se mettent à raconter deux histoires différentes.

var EXPE_PIL_FILTRES=[
  {key:'a_faire',  label:'À traiter'},
  {key:'retard',   label:'En retard'},
  {key:'commande', label:'Transport programmé'},
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
  if(j===null||j===undefined)return {txt:'date inconnue',cls:'expe-pil-meta--retard'};
  if(j<0)return {txt:'en retard de '+Math.abs(j)+' j',cls:'expe-pil-meta--retard'};
  if(j===0)return {txt:'aujourd’hui',cls:'expe-pil-meta--urgent'};
  if(j===1)return {txt:'demain',cls:'expe-pil-meta--urgent'};
  return {txt:'dans '+j+' j',cls:''};
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
    mode:'form',
    cle:env.cle_envoi,
    client:env.client,
    ville:env.ville,
    code_postal:env.code_postal,
    date_cible:env.date_cible,
    jours_restants:env.jours_restants,
    a_commander_le:env.a_commander_le,
    nb_dossiers:(env.dossiers||[]).length,
    nb_palette_source:env.nb_palette_source,
    transporteur:(env.jalons.transport.transporteur)||'',
    no_cde_transport:(env.jalons.transport.reference)||'',
    date_enlevement:env.date_cible||'',
    nb_palette:(env.nb_palette!=null?String(env.nb_palette):''),
    type_envoi:env.type_envoi,
    prod_prete:env.prod_prete,
    prod_fin_prevue:env.prod_fin_prevue,
    prod_apres_expedition:env.prod_apres_expedition,
    candidats:null,
    candidatsLoading:false
  }});
}

async function expePilChargerCandidats(){
  const m=S.expePilModal;
  if(!m)return;
  set({expePilModal:Object.assign({},m,{mode:'assoc',candidatsLoading:true})});
  try{
    const r=await api('/api/expe/pilotage/envois/'+encodeURIComponent(m.cle)+'/departs-candidats');
    const cur=S.expePilModal;
    if(!cur||cur.cle!==m.cle)return;
    set({expePilModal:Object.assign({},cur,{candidats:(r&&r.departs)||[],candidatsLoading:false})});
  }catch(e){
    const cur=S.expePilModal;
    if(cur)set({expePilModal:Object.assign({},cur,{candidats:[],candidatsLoading:false})});
    showToast(e.message||'Départs existants illisibles','danger');
  }
}

async function expePilAssocier(departId){
  const m=S.expePilModal;
  if(!m)return;
  const ok=await expePilAction(m.cle,'associer',{depart_id:departId});
  if(ok)showToast('Envoi rattaché au départ existant.','success');
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
  if(ok)showToast('Transport programmé. Le départ rejoint « Départs programmés ».','success');
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
    {lbl:'En retard',          val:r.retard,              cls:r.retard?'expe-pil-tuile--retard':''},
    {lbl:'À programmer',       val:r.a_commander,         cls:r.a_commander?'expe-pil-tuile--warn':''},
    {lbl:'Palettes à réserver',val:r.palettes_a_reserver||0,cls:''},
    {lbl:'Transport programmé',val:r.transport_commande,  cls:''},
    {lbl:'Sans BL',            val:r.bl_manquant,         cls:''}
  ];
  return h('div',{className:'expe-pil-tuiles'},
    ...t.map(function(x){
      return h('div',{className:'expe-pil-tuile '+x.cls},
        h('div',{className:'expe-pil-tuile-lbl'},x.lbl),
        h('div',{className:'expe-pil-tuile-val'},String(x.val!=null?x.val:0)));
    }));
}

function _expePilCelluleQuand(env){
  // Une date, une ligne de contexte. Le delai et l'origine de la date tiennent
  // ensemble : trois lignes empilees par cellule rendaient le tableau illisible.
  const j=_expePilJours(env);
  return h('td',null,
    h('div',{className:'expe-pil-quand'},_expePilJourFR(env.date_cible)),
    h('div',{className:'expe-pil-meta '+j.cls,
      title:'Origine de la date d’expédition visée : '+_expePilSrcLabel(env.date_cible_source)},
      j.txt+' · '+_expePilSrcLabel(env.date_cible_source))
  );
}

function _expePilCelluleEnvoi(env){
  const dos=(env.dossiers||[]).map(function(d){
    return h('span',{className:'expe-pil-dos-ref'+(d.etat==='en_cours'?' expe-pil-dos-ref--prod':''),
      title:(d.machine||'')+' · '+(d.etat==='termine'?'production terminée':
             d.etat==='en_cours'?'en production':'en attente de production')},
      d.reference||('#'+d.id));
  });
  const flags=[];
  if(env.prod_apres_expedition)
    flags.push(h('span',{className:'expe-pil-flag expe-pil-flag--prod',
      title:'Fin de production prévue le '+_expePilJourFR(env.prod_fin_prevue)+
            ', après la date d’expédition visée'},'Prod tardive'));
  if((env.dossiers||[]).some(function(d){return d.fsc_requis;}))
    flags.push(h('span',{className:'expe-pil-flag expe-pil-flag--fsc',title:'Dossier certifié FSC'},'FSC'));
  if((env.dossiers||[]).some(function(d){return d.prise_rdv;}))
    flags.push(h('span',{className:'expe-pil-flag expe-pil-flag--part',
      title:'Livraison sur rendez-vous'},'RDV'));
  return h('td',null,
    h('div',{className:'expe-pil-client'},env.client||'—'),
    h('div',{className:'expe-pil-dest'},
      [env.code_postal,env.ville].filter(Boolean).join(' ')||'destination inconnue'),
    (dos.length||flags.length)?h('div',{className:'expe-pil-dos'},...dos,...flags):null
  );
}

function _expePilCellulePalettes(env){
  const src=env.nb_palette_source;
  const val=env.nb_palette;
  const peut=expeCanWrite()&&env.alerte!=='parti';
  // Le mot sous le chiffre dit d'ou il vient — c'est ce qui distingue un
  // nombre valide d'une estimation. Il reste, mais discret : gris, minuscule.
  const libelle={saisi:'',bl:'du BL',estime:'estimé'}[src]||'à estimer';
  const manques=(env.manques||[]).join(' · ');
  const aide=src==='estime'
    ?('Estimé depuis la fiche technique'+(env.nb_palette_estime_partiel?' — partiel : '+manques:''))
    :(src==='bl'?'Compté sur le bon de livraison':(manques||'Corriger le nombre de palettes'));
  const champ=peut?h('input',{
    className:'expe-pil-pal-input',
    type:'text',
    value:(val!=null?String(val):''),
    placeholder:'—',
    title:aide,
    onKeyDown:function(e){if(e.key==='Enter'){e.preventDefault();void expePilPalettes(env,e.target.value);}},
    onBlur:function(e){
      const av=(val!=null?String(val):'');
      if(e.target.value.trim()!==av.trim())void expePilPalettes(env,e.target.value);
    }
  }):h('span',{className:'expe-pil-pal-val',title:aide},val!=null?String(val):'—');
  return h('td',null,
    h('div',{className:'expe-pil-pal'},champ,
      libelle?h('span',{className:'expe-pil-pal-src'+(src==='estime'?' expe-pil-pal-src--estime':''),
        title:aide},libelle+(env.nb_palette_estime_partiel?' (partiel)':'')):null)
  );
}

function _expePilCelluleTransport(env){
  const t=env.jalons.transport;
  if(t.fait){
    const detail=[t.reference,t.date_enlevement?'enlèv. '+_expePilJourFR(t.date_enlevement):'']
      .filter(Boolean).join(' · ');
    return h('td',null,
      h('div',{className:'expe-pil-jalon expe-pil-jalon--ok',
        title:(!t.date_confirmee&&t.date_enlevement)
          ?'Date déduite du planning, pas encore arrêtée avec le transporteur':''},
        t.transporteur||'Programmé'),
      detail?h('span',{className:'expe-pil-jalon-date'},detail):null
    );
  }
  if(!expeCanWrite())return h('td',null,h('span',{className:'expe-pil-nul'},'—'));
  // L'echeance ne s'affiche que quand elle compte. Sur un envoi qui part dans
  // trois semaines, « au plus tard le … » est du bruit sur chaque ligne.
  const presse=env.alerte==='retard'||env.alerte==='urgent'||env.alerte==='a_commander';
  return h('td',null,
    h('button',{type:'button',className:'expe-pil-act'+(presse?' expe-pil-act--go':''),
      title:env.a_commander_le?('À programmer au plus tard le '+_expePilJourFR(env.a_commander_le)):'',
      onClick:function(){expePilOuvrirTransport(env);}},'Programmer'),
    (presse&&env.a_commander_le)?h('span',{className:'expe-pil-jalon-date'},
      'avant le '+_expePilJourFR(env.a_commander_le)):null
  );
}

function _expePilCelluleParti(env){
  const p=env.jalons.parti;
  if(p.fait)return h('td',null,
    h('div',{className:'expe-pil-jalon expe-pil-jalon--ok'},'Parti'),
    h('span',{className:'expe-pil-jalon-date'},_expePilJourFR(p.le)));
  if(!expeCanWrite())return h('td',null,h('span',{className:'expe-pil-nul'},'—'));
  const pret=env.jalons.transport.fait;
  if(!pret)return h('td',null,h('span',{className:'expe-pil-nul',
    title:'Programmer le transport d’abord'},'—'));
  return h('td',null,
    h('button',{type:'button',className:'expe-pil-act',
      title:'Déclarer l’enlèvement effectué',
      onClick:function(){void expePilMarquerParti(env);}},'Parti'));
}

function _expePilCelluleBL(env){
  const bl=env.jalons.bl;
  if(!bl.fait)return h('td',null,h('span',{className:'expe-pil-nul',
    title:'Le bon de livraison se crée dans RVGI — MySifa le lit, il ne l’écrit pas'},'—'));
  return h('td',null,
    h('div',{className:'expe-pil-jalon expe-pil-jalon--ok',
      title:bl.numeros.join(' · ')},bl.numeros[0]),
    bl.numeros.length>1?h('span',{className:'expe-pil-jalon-date'},
      '+ '+(bl.numeros.length-1)):null);
}

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
        h('div',{className:'expe-pil-meta '+j.cls},j.txt))
    ),
    h('div',{className:'expe-pil-dos'},
      (env.nb_palette!=null?env.nb_palette+' palette(s)':'palettes à estimer')+
      ' · '+(env.type_envoi==='affretement'?'affrètement':'messagerie')+
      ' · '+(env.dossiers||[]).length+' dossier(s)'),
    h('div',{className:'expe-pil-carte-jalons'},
      t.fait
        ?h('span',{className:'expe-pil-jalon expe-pil-jalon--ok'},iconEl('check-circle',13),' ',
           t.transporteur||'Transport programmé')
        :(expeCanWrite()?h('button',{type:'button',className:'expe-pil-act expe-pil-act--go',
           onClick:function(){expePilOuvrirTransport(env);}},'Programmer le transport')
          :h('span',{className:'expe-pil-jalon'},'Transport à programmer')),
      env.jalons.parti.fait
        ?h('span',{className:'expe-pil-jalon expe-pil-jalon--ok'},iconEl('check-circle',13),' Parti')
        :(expeCanWrite()&&t.fait?h('button',{type:'button',className:'expe-pil-act',
           onClick:function(){void expePilMarquerParti(env);}},'Parti'):null),
      env.jalons.bl.fait
        ?h('span',{className:'expe-pil-jalon expe-pil-jalon--ok'},iconEl('check-circle',13),' BL ',
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
     aide:'Au-delà, les envois sortent du tableau — sauf ce qui est en retard ou à programmer, jamais masqué.'},
    {cle:'preavis_messagerie_jours',label:'Préavis messagerie (jours)',
     aide:'À J-N avant la date d’expédition, l’envoi passe en « à programmer ».'},
    {cle:'preavis_affretement_jours',label:'Préavis affrètement (jours)',
     aide:'Plus long : un camion complet se réserve plus tôt qu’une messagerie.'},
    {cle:'seuil_affretement_palettes',label:'Seuil affrètement (palettes)',
     aide:'Au-delà de ce nombre de palettes, l’envoi est traité en affrètement.'},
    {cle:'retard_max_jours',label:'Retard maximum affiché (jours)',
     aide:'Au-delà, le dossier est écarté et compté à part : ce n’est plus un transport en retard, c’est un dossier de planning à solder.'}
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
    h('div',{className:'expe-pil-reglages-corps'},
      grille,
      h('div',{className:'expe-pil-reglages-actions'},
        expeCanWrite()?h('button',{type:'button',className:'btn-accent',onClick:function(){
          const vals={};champs.forEach(function(c){vals[c.cle]=refs[c.cle].value;});
          void expePilEnregistrerReglages(vals);
        }},'Enregistrer'):null,
        h('button',{type:'button',className:'expe-pil-act',
          onClick:function(){set({expePilReglagesOuvert:false});}},'Fermer')))
  );
}

function _expePilModalFermer(){ set({expePilModal:null}); }

function _expePilModalContexte(m){
  // Trois faits qu'on regarde en programmant un camion. Ils sont ici pour ne
  // pas avoir a refermer le modal pour aller les relire dans le tableau.
  const items=[];
  items.push({lbl:'Départ visé',val:_expePilJourFR(m.date_cible),
    note:(m.jours_restants!=null
      ?(m.jours_restants<0?'en retard de '+Math.abs(m.jours_restants)+' j'
        :m.jours_restants===0?'aujourd’hui'
        :m.jours_restants===1?'demain':'dans '+m.jours_restants+' j')
      :'date à confirmer'),
    cls:(m.jours_restants!=null&&m.jours_restants<0)?'expe-pil-ctx-val--danger':''});
  items.push({lbl:'Palettes',
    val:(m.nb_palette!==''&&m.nb_palette!=null?String(m.nb_palette):'—'),
    note:({saisi:'saisi',bl:'du bon de livraison',estime:'estimé'}[m.nb_palette_source]||'à estimer'),
    cls:m.nb_palette_source==='estime'?'expe-pil-ctx-val--warn':''});
  items.push({lbl:'Production',
    val:m.prod_prete?'Terminée':'En cours',
    note:m.prod_prete?(m.nb_dossiers+' dossier(s)')
      :'fin prévue le '+_expePilJourFR(m.prod_fin_prevue),
    cls:m.prod_apres_expedition?'expe-pil-ctx-val--danger':(m.prod_prete?'':'expe-pil-ctx-val--warn')});
  return h('div',{className:'expe-pil-ctx'},
    ...items.map(function(x){
      return h('div',{className:'expe-pil-ctx-item'},
        h('div',{className:'expe-pil-ctx-lbl'},x.lbl),
        h('div',{className:'expe-pil-ctx-val '+(x.cls||'')},x.val),
        h('div',{className:'expe-pil-ctx-note'},x.note));
    }));
}

function _expePilModalForm(m){
  const champ=function(cle,label,attrs){
    const inp=h('input',Object.assign({
      value:m[cle]||'',
      onInput:function(e){m[cle]=e.target.value;}
    },attrs||{}));
    return h('div',null,h('label',null,label),inp);
  };
  return h('div',null,
    _expePilModalContexte(m),
    m.prod_apres_expedition?h('div',{className:'expe-pil-modal-aide',
      style:{color:'var(--danger)',marginTop:'0',marginBottom:'14px'}},
      'La production finit après la date visée — l’enlèvement devra être calé plus tard, '+
      'ou la production avancée.'):null,
    h('div',{className:'expe-pil-modal-grid'},
      champ('transporteur','Transporteur',
        {type:'text',list:'expe-pil-trp',placeholder:'Nom du transporteur',autofocus:true}),
      champ('no_cde_transport','N° de commande transport',
        {type:'text',placeholder:'Référence ou « mail du … »'}),
      champ('date_enlevement','Date d’enlèvement',{type:'date'}),
      champ('nb_palette','Nombre de palettes',{type:'text',placeholder:'—'})
    ),
    h('datalist',{id:'expe-pil-trp'},
      ...((T&&T.list)||[]).map(function(t){return h('option',{value:t.nom||''});})),
    h('div',{className:'expe-pil-modal-aide'},
      'La plupart des transporteurs tarifent au nombre de palettes : c’est ce chiffre '+
      'qu’il faut donner, le poids vient ensuite. Une date saisie ici vaut date arrêtée '+
      'avec le transporteur.')
  );
}

function _expePilModalAssoc(m){
  const cands=m.candidats||[];
  const q=(m.qCand||'').toLowerCase();
  const vus=cands.filter(function(d){
    if(!q)return true;
    return [d.client,d.transporteur,d.code_postal_destination,d.no_bl,d.no_cde_transport,
            d.arc,d.ref_sifa].join(' ').toLowerCase().indexOf(q)!==-1;
  });
  const liste=m.candidatsLoading
    ?[h('div',{className:'expe-pil-vide'},'Lecture des départs…')]
    :(vus.length?vus.map(function(d){
        return h('button',{type:'button',
          className:'expe-pil-cand'+(d.pertinent?' expe-pil-cand--pertinent':''),
          onClick:function(){void expePilAssocier(d.id);}},
          h('div',{className:'expe-pil-cand-date'},_expePilJourFR(d.date_enlevement)),
          h('div',{className:'expe-pil-cand-corps'},
            h('div',{className:'expe-pil-cand-titre'},
              (d.transporteur||'Transporteur non renseigné')+' · '+(d.client||'client non renseigné')),
            h('div',{className:'expe-pil-cand-meta'},
              [d.code_postal_destination||null,
               d.nb_palette!=null?d.nb_palette+' pal.':null,
               d.no_bl?'BL '+d.no_bl:null,
               d.nb_dossiers?d.nb_dossiers+' dossier(s)':'sans dossier'
              ].filter(Boolean).join(' · '))),
          d.raisons&&d.raisons.length
            ?h('div',{className:'expe-pil-cand-raison'},d.raisons.join(', ')):null
        );
      })
      :[h('div',{className:'expe-pil-vide'},
          q?'Aucun départ ne correspond.'
           :'Aucun départ programmé disponible — il faut en créer un.')]);
  return h('div',null,
    h('div',{className:'expe-pil-modal-aide',style:{marginTop:'0'}},
      'Rattacher évite de créer un second départ pour le même camion. Le départ choisi '+
      'garde son transporteur, sa date et ses palettes : les dossiers de cet envoi viennent '+
      's’y ajouter.'),
    // `.expe-pil-search` est taillee pour la barre de filtres (flex:1). Hors
    // conteneur flex, elle se replie sur son contenu : on lui rend sa largeur.
    h('input',{className:'expe-pil-search',
      style:{maxWidth:'none',width:'100%',boxSizing:'border-box',marginTop:'12px'},
      type:'search',placeholder:'Transporteur, client, CP, n° de BL…',
      value:m.qCand||'',
      onInput:function(e){
        m.qCand=e.target.value;
        if(_expePilSearchTimer)clearTimeout(_expePilSearchTimer);
        _expePilSearchTimer=setTimeout(function(){ render(); },250);
      }}),
    h('div',{className:'expe-pil-cand-liste'},...liste)
  );
}

function renderExpePilotageModal(){
  const m=S.expePilModal;
  if(!m)return null;
  const assoc=m.mode==='assoc';
  const overlay=h('div',{className:'expe-pil-modal-overlay',
    onClick:function(e){if(e.target===overlay)_expePilModalFermer();}});
  const box=h('div',{className:'expe-pil-modal'+(assoc?' expe-pil-modal--large':'')},
    h('div',{className:'expe-pil-modal-head'},
      h('div',null,
        h('h3',{className:'expe-pil-modal-titre'},
          assoc?'Associer un départ existant':'Programmer le transport'),
        h('div',{className:'expe-pil-modal-sous'},
          [(m.client||''),[m.code_postal,m.ville].filter(Boolean).join(' '),
           (m.type_envoi==='affretement'?'affrètement':'messagerie')].filter(Boolean).join(' · '))),
      h('button',{type:'button',className:'expe-pil-modal-x','aria-label':'Fermer',
        onClick:_expePilModalFermer},iconEl('x',15))),
    h('div',{className:'expe-pil-modal-corps'},
      assoc?_expePilModalAssoc(m):_expePilModalForm(m)),
    h('div',{className:'expe-pil-modal-foot'},
      assoc
        ?h('button',{type:'button',className:'expe-pil-act',
            onClick:function(){set({expePilModal:Object.assign({},m,{mode:'form'})});}},
            'Retour')
        :h('button',{type:'button',className:'expe-pil-act',
            title:'Rattacher cet envoi à un départ déjà saisi plutôt que d’en créer un',
            onClick:function(){void expePilChargerCandidats();}},
            'Associer un départ existant'),
      h('div',{className:'expe-pil-modal-foot-droite'},
        h('button',{type:'button',className:'expe-pil-act',
          onClick:_expePilModalFermer},'Annuler'),
        assoc?null:h('button',{type:'button',className:'btn-accent',
          onClick:function(){void expePilValiderTransport();}},'Programmer')))
  );
  overlay.appendChild(box);
  return overlay;
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
      onClick:function(){void loadExpePilotage();}},iconEl('rotate-cw',13),' Actualiser')
  );

  // Les notes de contexte tiennent sur une ligne grise sous la barre de filtres.
  // Ce sont des precisions, pas des alertes : les mettre en bandeau jaune leur
  // donnait plus de poids visuel qu'aux retards du tableau.
  const notes=[];
  if(data.rvgi&&!data.rvgi.present)
    notes.push('Miroir RVGI indisponible — dates demandées, adresses et BL non affichés.');
  if((data.resume||{}).sans_estimation)
    notes.push(data.resume.sans_estimation+' sans palettes (fiche incomplète, saisie possible).');
  if((data.resume||{}).dormants)
    notes.push(data.resume.dormants+' dossier(s) attendus avant le '+
      _expePilJourFR(data.dormants_avant)+' écartés — à solder dans MyProd.');
  const avert=notes.length
    ?[h('div',{className:'expe-pil-avert'},notes.join('  ·  '))]
    :[];

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

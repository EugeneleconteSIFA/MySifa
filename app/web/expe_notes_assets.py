"""MyExpé — note de confiance transporteur et zones géographiques (front).

Deux blocs séparés du gros `expe_assets.py` :

* `EXPE_NOTES_*` — badge A→F, modale d'avis (curseur d'étoiles par demies,
  thématique, commentaire), onglet « Suivi qualité » de la fiche transporteur.
* `EXPE_ZONES_*` — écran Référentiel › Zone géographique : on saisit une ville
  ou un code postal, on obtient les transporteurs à prioriser.

Le calcul de la note vit côté serveur (`app/services/expe_notes.py`). Ici on
ne fait qu'afficher et saisir : aucune règle métier ne doit être dupliquée,
sauf les libellés de lettres, qui suivent le serveur ligne pour ligne.
"""

from __future__ import annotations

EXPE_NOTES_CSS = r"""
/* ── MyExpé — note de confiance transporteur ── */

/* Le fond d'un badge de note est une couleur de sens (vert → rouge), pas une
   couleur de thème : le texte est donc figé en foncé sur les fonds clairs
   (A→D) et en blanc sur les rouges (E, F). C'est l'exception documentée du
   design system — `var(--text)` produirait ici du sombre sur sombre. */
.expe-note-badge{display:inline-flex;align-items:center;justify-content:center;
  min-width:24px;height:24px;padding:0 7px;border-radius:8px;font-size:13px;font-weight:800;
  letter-spacing:-.2px;flex-shrink:0;cursor:default;line-height:1}
.expe-note-badge.grand{min-width:46px;height:46px;border-radius:14px;font-size:24px;padding:0 12px}
.expe-note-badge.n-a{background:var(--success);color:#0a0e17}
.expe-note-badge.n-b{background:color-mix(in srgb,var(--success) 62%,var(--warn));color:#0a0e17}
.expe-note-badge.n-c{background:var(--warn);color:#0a0e17}
.expe-note-badge.n-d{background:color-mix(in srgb,var(--warn) 52%,var(--danger));color:#0a0e17}
.expe-note-badge.n-e{background:color-mix(in srgb,var(--danger) 78%,var(--warn));color:#ffffff}
.expe-note-badge.n-f{background:var(--danger);color:#ffffff}
.expe-note-badge.n-vide{background:var(--bg);border:1px dashed var(--border);color:var(--muted);font-weight:600}
.expe-note-badge.provisoire{box-shadow:0 0 0 2px color-mix(in srgb,var(--muted) 45%,transparent)}
/* Note de depart : aucun avis n'a encore ete emis. Le contour en pointilles la
   distingue d'une note gagnee, sans la faire disparaitre de la colonne. */
.expe-note-badge.depart{opacity:.72;outline:1px dashed color-mix(in srgb,var(--muted) 70%,transparent);outline-offset:1px}
.expe-note-cell{display:flex;align-items:center;gap:8px}
.expe-note-cell-txt{font-size:11px;color:var(--muted);line-height:1.3}

/* Boutons d'avis posés sur une ligne de départ */
.expe-avis-btn{display:inline-flex;align-items:center;justify-content:center;
  width:30px;height:28px;border-radius:8px;border:1px solid var(--border);
  background:var(--card);cursor:pointer;padding:0;transition:filter .15s,border-color .15s}
.expe-avis-btn:hover{filter:brightness(1.06)}
.expe-avis-btn.alerte{color:var(--danger);border-color:color-mix(in srgb,var(--danger) 35%,var(--border))}
.expe-avis-btn.appreciation{color:var(--success);border-color:color-mix(in srgb,var(--success) 35%,var(--border))}

/* Modale d'avis */
.expe-avis-overlay{position:fixed;inset:0;background:color-mix(in srgb,var(--bg) 60%,transparent);
  z-index:12400;display:flex;align-items:center;justify-content:center;padding:20px;overflow:auto}
.expe-avis-box{background:var(--card);border:1px solid var(--border);border-radius:16px;
  width:min(560px,100%);max-height:calc(100dvh - 60px);overflow:auto;padding:22px 24px}
.expe-avis-head{display:flex;align-items:flex-start;gap:12px;margin-bottom:4px}
.expe-avis-title{font-size:16px;font-weight:800;color:var(--text);margin:0}
.expe-avis-sub{font-size:12px;color:var(--muted);margin:4px 0 18px;line-height:1.5}
.expe-avis-trp{display:flex;align-items:center;gap:8px;margin-bottom:16px;flex-wrap:wrap}
.expe-avis-field{display:flex;flex-direction:column;gap:6px;margin-bottom:16px}
.expe-avis-field > label{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text2)}
.expe-avis-field select,.expe-avis-field textarea,.expe-avis-field input{
  background:var(--bg);border:1px solid var(--border);border-radius:10px;padding:11px 14px;
  color:var(--text);font-size:14px;font-family:inherit;outline:none;width:100%}
.expe-avis-field textarea{min-height:88px;resize:vertical;line-height:1.5}
.expe-avis-field select:focus,.expe-avis-field textarea:focus,.expe-avis-field input:focus{
  border-color:var(--accent);box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 12%,transparent)}
.expe-avis-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:20px}

/* Curseur d'étoiles /10, demi-étoile comprise */
.expe-stars{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.expe-stars-row{display:inline-flex;gap:2px;outline:none;border-radius:8px;padding:2px}
.expe-stars-row:focus-visible{box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 25%,transparent)}
.expe-star-cell{cursor:pointer;display:inline-flex;line-height:0}
.expe-star-svg .expe-star-bg{fill:var(--border)}
.expe-star-svg .expe-star-fg{fill:var(--warn)}
.expe-stars-val{font-size:15px;font-weight:800;color:var(--text);white-space:nowrap}
.expe-stars-hint{font-size:11px;color:var(--muted);margin-top:6px}

/* Onglet Suivi qualité de la fiche transporteur */
.expe-nq-entete{display:flex;align-items:center;gap:16px;background:var(--bg);border:1px solid var(--border);
  border-radius:12px;padding:16px 18px;margin-bottom:16px;flex-wrap:wrap}
.expe-nq-entete-txt{display:flex;flex-direction:column;gap:3px;min-width:0}
.expe-nq-lib{font-size:15px;font-weight:700;color:var(--text)}
.expe-nq-meta{font-size:12px;color:var(--muted);line-height:1.5}
.expe-nq-prov{display:inline-block;background:var(--accent-bg);color:var(--accent);border-radius:6px;
  font-size:11px;font-weight:700;padding:2px 8px;margin-top:4px}
.expe-nq-ajust{background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:16px 18px;margin-bottom:16px}
.expe-nq-ajust-title{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:var(--text2);margin-bottom:4px}
.expe-nq-ajust-help{font-size:12px;color:var(--muted);line-height:1.55;margin-bottom:12px}
.expe-nq-ajust-row{display:grid;grid-template-columns:190px minmax(0,1fr) auto;gap:10px;align-items:end}
@media(max-width:620px){.expe-nq-ajust-row{grid-template-columns:1fr}}
.expe-nq-filtres{display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap}
.expe-nq-filtre{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:7px 13px;
  font-size:12px;font-weight:600;color:var(--text2);cursor:pointer;font-family:inherit}
.expe-nq-filtre.active{background:var(--accent-bg);border-color:var(--accent);color:var(--accent)}
.expe-nq-liste{display:flex;flex-direction:column;gap:8px}
.expe-nq-item{background:var(--bg);border:1px solid var(--border);border-left-width:3px;border-radius:10px;padding:12px 14px}
.expe-nq-item.alerte{border-left-color:var(--danger)}
.expe-nq-item.appreciation{border-left-color:var(--success)}
.expe-nq-item.ajustement{border-left-color:var(--accent)}
.expe-nq-item-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px}
.expe-nq-item-them{font-size:13px;font-weight:700;color:var(--text)}
.expe-nq-item-note{font-size:12px;font-weight:800;color:var(--warn)}
.expe-nq-item-date{font-size:11px;color:var(--muted);margin-left:auto}
.expe-nq-item-com{font-size:13px;color:var(--text2);line-height:1.55;white-space:pre-wrap}
.expe-nq-item-ref{font-size:11px;color:var(--muted);margin-top:6px}
.expe-nq-item-rm{margin-left:8px;background:none;border:none;color:var(--muted);cursor:pointer;padding:2px;line-height:0}
.expe-nq-item-rm:hover{color:var(--danger)}
.expe-nq-vide{font-size:13px;color:var(--muted);padding:18px;text-align:center}

/* Référentiel des thématiques d'avis */
.expe-th-card{margin-top:14px}
.expe-th-head{display:flex;align-items:center;gap:10px;cursor:pointer;user-select:none}
.expe-th-chev{color:var(--muted);transition:transform .15s;display:inline-flex}
.expe-th-chev.open{transform:rotate(90deg)}
.expe-th-body{padding:4px 16px 16px}
.expe-th-row{display:grid;grid-template-columns:minmax(0,1fr) 150px 110px auto auto;gap:10px;align-items:center;
  padding:9px 0;border-bottom:1px solid var(--border)}
.expe-th-row:last-child{border-bottom:none}
@media(max-width:820px){.expe-th-row{grid-template-columns:1fr 1fr}}
.expe-th-row input,.expe-th-row select{background:var(--bg);border:1px solid var(--border);border-radius:8px;
  padding:8px 11px;color:var(--text);font-size:13px;font-family:inherit;outline:none;width:100%}
.expe-th-row input:focus,.expe-th-row select:focus{border-color:var(--accent)}
.expe-th-row.inactive{opacity:.55}
.expe-th-act{background:var(--bg);border:1px solid var(--border);border-radius:8px;padding:7px 9px;
  color:var(--text2);cursor:pointer;line-height:0}
.expe-th-act:hover{color:var(--danger);border-color:color-mix(in srgb,var(--danger) 40%,var(--border))}
.expe-th-aide{font-size:12px;color:var(--muted);line-height:1.6;margin:0 0 12px}
"""

EXPE_ZONES_CSS = r"""
/* ── MyExpé — Référentiel › Zone géographique ── */
.expe-zn-wrap{display:flex;flex-direction:column;gap:14px}
.expe-zn-form{display:grid;grid-template-columns:1fr 210px auto;gap:12px;align-items:end}
@media(max-width:760px){.expe-zn-form{grid-template-columns:1fr}}
.expe-zn-field{display:flex;flex-direction:column;gap:6px}
.expe-zn-field > label{font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.5px;color:var(--text2)}
.expe-zn-field input,.expe-zn-field select{background:var(--bg);border:1px solid var(--border);border-radius:10px;
  padding:12px 16px;color:var(--text);font-size:14px;font-family:inherit;outline:none;width:100%}
.expe-zn-field input:focus,.expe-zn-field select:focus{border-color:var(--accent);
  box-shadow:0 0 0 3px color-mix(in srgb,var(--accent) 12%,transparent)}
.expe-zn-layout{display:grid;grid-template-columns:minmax(0,1fr) minmax(340px,420px);gap:14px;align-items:start}
@media(max-width:1100px){.expe-zn-layout{grid-template-columns:1fr}}
.expe-zn-map-wrap{width:100%;background:var(--bg);border:1px solid var(--border);border-radius:12px;padding:8px;
  display:flex;align-items:center;justify-content:center;min-height:320px}
.expe-zn-map-wrap .expe-carte-svg{width:100%;height:auto;max-height:620px;display:block}
.expe-zn-dept--sel{stroke:var(--text)!important;stroke-width:2.4!important}
.expe-zn-legende{font-size:11px;color:var(--muted);line-height:1.6;margin-top:8px}
.expe-zn-dest{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.expe-zn-dest-cp{font-size:22px;font-weight:800;color:var(--text);letter-spacing:-.4px}
.expe-zn-dest-meta{font-size:12px;color:var(--muted)}
.expe-zn-liste{display:flex;flex-direction:column;gap:8px}
.expe-zn-item{display:flex;align-items:center;gap:12px;background:var(--bg);border:1px solid var(--border);
  border-radius:10px;padding:12px 14px}
.expe-zn-item.premier{border-color:var(--accent);background:var(--accent-bg)}
.expe-zn-item.hors-zone{opacity:.6}
.expe-zn-rang{font-size:13px;font-weight:800;color:var(--muted);width:20px;flex-shrink:0;text-align:center}
.expe-zn-corps{flex:1;min-width:0;display:flex;flex-direction:column;gap:4px}
.expe-zn-nom{font-size:14px;font-weight:700;color:var(--text);display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.expe-zn-meta{font-size:11px;color:var(--muted);line-height:1.5}
.expe-zn-tag{display:inline-block;background:var(--card);border:1px solid var(--border);border-radius:6px;
  font-size:10px;font-weight:600;padding:2px 7px;color:var(--text2)}
.expe-zn-tag.neuf{border-color:color-mix(in srgb,var(--accent) 40%,var(--border));color:var(--accent)}
.expe-zn-tag.hors{border-color:color-mix(in srgb,var(--warn) 45%,var(--border));color:var(--warn)}
.expe-zn-score{font-size:12px;font-weight:800;color:var(--text2);white-space:nowrap}
.expe-zn-vide{font-size:13px;color:var(--muted);padding:22px;text-align:center}
"""

EXPE_NOTES_JS = r"""
// ── MyExpé — note de confiance transporteur (état N) ──────────────
//
// N ne vit pas dans S : la modale d'avis se redessinerait à chaque frappe du
// commentaire si on passait par set(), et le curseur d'étoiles perdrait son
// état de survol. Les écritures dans N sont suivies d'un render() explicite
// quand l'écran doit bouger, et de rien du tout quand il ne doit pas.
const N={
  thematiques:[],
  thematiquesChargees:false,
  thematiquesEnCours:false,
  avis:null,
  hist:null,
  histTrpId:null,
  histLoading:false,
  histFiltre:'tous',
  ajustValeur:0,
  ajustMotif:'',
  ajustEnvoi:false
};

const EXPE_NOTE_LIBELLES={
  A:'À utiliser en priorité',
  B:'Fiable',
  C:'Correct',
  D:'À surveiller',
  E:'Problématique',
  F:'À éviter'
};
// Doit rester aligné sur expe_notes.AJUSTEMENT_MAX cote serveur.
const EXPE_AJUST_MAX=3;
// En dessous, la note s'affiche mais reste marquée provisoire (idem serveur).
const EXPE_NOTE_SEUIL_FIABILITE=3;
// Doit rester aligné sur expe_notes.NOTE_DEPART — sert aux libellés, pas au
// calcul : la valeur affichée vient toujours du serveur.
const EXPE_NOTE_DEPART=5;

function expeNoteLibelle(lettre){
  return EXPE_NOTE_LIBELLES[String(lettre||'').toUpperCase()]||'Non noté';
}

function expeNoteFmt(valeur){
  if(valeur==null)return '';
  return Number(valeur).toFixed(1).replace('.',',');
}

// Badge A→F. `source` accepte aussi bien une ligne transporteur
// (note_lettre / note_valeur / note_nb_avis) que le dict renvoyé par l'API
// des avis (lettre / valeur / nb_avis) — les deux circulent dans l'écran.
function expeNoteBadge(source,opts){
  const o=opts||{};
  const s=source||{};
  const lettre=String(s.note_lettre||s.lettre||'').toUpperCase();
  const valeur=(s.note_valeur!=null?s.note_valeur:s.valeur);
  const nb=Number(s.note_nb_avis!=null?s.note_nb_avis:(s.nb_avis||0))||0;
  const el=document.createElement('span');
  el.className='expe-note-badge'+(o.grand?' grand':'');
  if(!lettre){
    // Cache jamais calculé (transporteur créé avant la migration) : on ne
    // fabrique pas une lettre côté écran, c'est le serveur qui la donne.
    el.classList.add('n-vide');
    el.textContent='—';
    el.title='Note non calculée — elle apparaîtra au prochain enregistrement.';
    return el;
  }
  el.classList.add('n-'+lettre.toLowerCase());
  el.textContent=lettre;
  if(!nb)el.classList.add('depart');
  else if(nb<EXPE_NOTE_SEUIL_FIABILITE)el.classList.add('provisoire');
  const bouts=[lettre+' — '+expeNoteLibelle(lettre)];
  if(valeur!=null)bouts.push(expeNoteFmt(valeur)+'/10');
  if(!nb){
    bouts.push('note de départ, aucun avis émis');
  }else{
    bouts.push(nb+' avis');
    if(nb<EXPE_NOTE_SEUIL_FIABILITE)bouts.push('note provisoire');
  }
  el.title=bouts.join(' · ');
  return el;
}

// Même badge, en chaîne HTML — le comparateur construit ses cartes en
// innerHTML et ne peut pas recevoir un noeud.
function expeNoteBadgeHtml(source,opts){
  return expeNoteBadge(source,opts).outerHTML;
}

function expeIconAlerte(size){
  const s=size||14;
  const el=document.createElementNS('http://www.w3.org/2000/svg','svg');
  el.setAttribute('width',s);el.setAttribute('height',s);el.setAttribute('viewBox','0 0 24 24');
  el.setAttribute('fill','none');el.setAttribute('stroke','currentColor');el.setAttribute('stroke-width','2');
  el.setAttribute('stroke-linecap','round');el.setAttribute('stroke-linejoin','round');
  el.innerHTML='<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>'
    +'<line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>';
  return el;
}

function expeIconPouce(size){
  const s=size||14;
  const el=document.createElementNS('http://www.w3.org/2000/svg','svg');
  el.setAttribute('width',s);el.setAttribute('height',s);el.setAttribute('viewBox','0 0 24 24');
  el.setAttribute('fill','none');el.setAttribute('stroke','currentColor');el.setAttribute('stroke-width','2');
  el.setAttribute('stroke-linecap','round');el.setAttribute('stroke-linejoin','round');
  el.innerHTML='<path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3z"/>'
    +'<line x1="7" y1="22" x2="2" y2="22"/><line x1="2" y1="11" x2="7" y2="11"/>'
    +'<line x1="2" y1="11" x2="2" y2="22"/>';
  return el;
}

// ── Curseur d'étoiles /10, demi-étoile comprise ───────────────────
let _expeStarSeq=0;

function expeEtoileEl(fraction,taille){
  const s=taille||24;
  const ns='http://www.w3.org/2000/svg';
  const d='M12 2.6l2.9 5.9 6.5.95-4.7 4.6 1.1 6.45L12 17.45 6.2 20.5l1.1-6.45-4.7-4.6 6.5-.95z';
  const svg=document.createElementNS(ns,'svg');
  svg.setAttribute('width',s);svg.setAttribute('height',s);
  svg.setAttribute('viewBox','0 0 24 24');
  svg.setAttribute('class','expe-star-svg');
  const fond=document.createElementNS(ns,'path');
  fond.setAttribute('d',d);fond.setAttribute('class','expe-star-bg');
  svg.appendChild(fond);
  const part=Math.max(0,Math.min(1,fraction));
  if(part>0){
    // Demi-étoile = découpe rectangulaire du chemin plein. Un dégradé donnerait
    // le même rendu mais se comporte mal quand la couleur suit le thème.
    const cid='expe-star-clip-'+(++_expeStarSeq);
    const defs=document.createElementNS(ns,'defs');
    const clip=document.createElementNS(ns,'clipPath');
    clip.setAttribute('id',cid);
    const rect=document.createElementNS(ns,'rect');
    rect.setAttribute('x','0');rect.setAttribute('y','0');
    rect.setAttribute('width',String(24*part));rect.setAttribute('height','24');
    clip.appendChild(rect);defs.appendChild(clip);svg.appendChild(defs);
    const plein=document.createElementNS(ns,'path');
    plein.setAttribute('d',d);plein.setAttribute('class','expe-star-fg');
    plein.setAttribute('clip-path','url(#'+cid+')');
    svg.appendChild(plein);
  }
  return svg;
}

function expeNoteCurseur(valeurInitiale,onChange){
  let valeur=Math.max(0,Math.min(10,Number(valeurInitiale)||0));
  const rangee=h('div',{className:'expe-stars-row',tabIndex:0,role:'slider',
    'aria-valuemin':'0','aria-valuemax':'10'});
  const lecture=h('div',{className:'expe-stars-val'});

  function demiDepuisEvent(cell,e){
    const r=cell.getBoundingClientRect();
    return (e.clientX-r.left)<r.width/2?0.5:1;
  }
  function peindre(v){
    rangee.innerHTML='';
    for(let i=1;i<=10;i++){
      const cell=h('span',{className:'expe-star-cell'});
      cell.appendChild(expeEtoileEl(v-(i-1),24));
      cell.addEventListener('mousemove',e=>peindre(i-1+demiDepuisEvent(cell,e)));
      cell.addEventListener('click',e=>{
        valeur=i-1+demiDepuisEvent(cell,e);
        peindre(valeur);
        if(onChange)onChange(valeur);
      });
      rangee.appendChild(cell);
    }
    lecture.textContent=expeNoteFmt(Math.round(v*2)/2)+' / 10';
    rangee.setAttribute('aria-valuenow',String(valeur));
  }
  rangee.addEventListener('mouseleave',()=>peindre(valeur));
  rangee.addEventListener('keydown',e=>{
    if(e.key==='ArrowRight'||e.key==='ArrowUp')valeur=Math.min(10,valeur+0.5);
    else if(e.key==='ArrowLeft'||e.key==='ArrowDown')valeur=Math.max(0,valeur-0.5);
    else return;
    e.preventDefault();
    peindre(valeur);
    if(onChange)onChange(valeur);
  });
  peindre(valeur);
  return h('div',null,
    h('div',{className:'expe-stars'},rangee,lecture),
    h('div',{className:'expe-stars-hint'},'Clic sur la moitié gauche d\'une étoile pour une demi-étoile · flèches du clavier pour ajuster')
  );
}

// ── Chargement des thématiques ────────────────────────────────────
async function expeChargerThematiques(force){
  if(N.thematiquesEnCours)return;
  if(N.thematiquesChargees&&!force)return;
  N.thematiquesEnCours=true;
  try{
    const rows=await api('/api/expe/avis/thematiques');
    N.thematiques=Array.isArray(rows)?rows:[];
    N.thematiquesChargees=true;
  }catch(e){
    N.thematiques=[];
  }
  N.thematiquesEnCours=false;
  render();
}

function expeThematiquesPour(sens){
  return (N.thematiques||[]).filter(t=>{
    const s=String(t.sens||'les_deux');
    return s==='les_deux'||s===sens;
  });
}

// ── Ouverture de la modale d'avis depuis une ligne de départ ──────
function expeTrpIdDepuisDepart(r){
  if(r&&r.transporteur_id)return Number(r.transporteur_id);
  const nom=String((r&&r.transporteur)||'').trim().toLowerCase();
  if(!nom)return null;
  const t=(T.list||[]).find(x=>String(x.nom||'').trim().toLowerCase()===nom);
  return t?Number(t.id):null;
}

function expeDepartRef(r){
  return [
    String(r.date_enlevement||'').slice(0,10),
    r.client||'',
    r.no_bl?('BL '+r.no_bl):'',
    r.code_postal_destination||''
  ].filter(Boolean).join(' · ');
}

function expeOuvrirAvis(r,sens){
  const tid=expeTrpIdDepuisDepart(r);
  if(!tid){
    toast('Transporteur hors référentiel — ajoutez-le dans Référentiel > Transporteurs pour pouvoir le noter.','error');
    return;
  }
  void expeChargerThematiques();
  N.avis={
    transporteur_id:tid,
    transporteur:r.transporteur||'',
    depart_id:r.id||null,
    depart_ref:expeDepartRef(r),
    // Le bouton n'impose pas la note, il oriente le curseur : un incident
    // part bas, une satisfaction part haut, et l'utilisateur ajuste.
    sens:sens,
    note:(sens==='alerte'?3:8),
    thematique_id:null,
    commentaire:'',
    envoi:false
  };
  render();
}

function expeFermerAvis(){
  N.avis=null;
  render();
}

async function expeEnvoyerAvis(){
  const a=N.avis;
  if(!a)return;
  if(!a.thematique_id){toast('Sélectionner une thématique.','error');return;}
  a.envoi=true;
  render();
  try{
    await api('/api/expe/transporteurs/'+a.transporteur_id+'/avis',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        depart_id:a.depart_id,
        sens:a.sens,
        note:a.note,
        thematique_id:a.thematique_id,
        commentaire:a.commentaire
      })
    });
    const trpId=a.transporteur_id;
    const sens=a.sens;
    N.avis=null;
    toast(sens==='alerte'?'Signalement enregistré.':'Appréciation enregistrée.');
    await loadTransporteurs();
    if(N.histTrpId&&Number(N.histTrpId)===Number(trpId))await expeChargerHistoriqueNote(trpId);
    if(typeof Z!=='undefined'&&Z&&Z.data)void expeZonesRelancer();
  }catch(e){
    a.envoi=false;
    toast(e.message||'Enregistrement impossible','error');
  }
  render();
}

function renderExpeAvisModal(){
  const a=N.avis;
  if(!a)return null;
  const estAlerte=a.sens==='alerte';
  const overlay=h('div',{className:'expe-avis-overlay'});
  overlay.addEventListener('click',e=>{if(e.target===overlay)expeFermerAvis();});
  const box=h('div',{className:'expe-avis-box'});

  box.appendChild(h('div',{className:'expe-avis-head'},
    h('span',{className:'expe-avis-btn '+(estAlerte?'alerte':'appreciation')},
      estAlerte?expeIconAlerte(15):expeIconPouce(15)),
    h('h3',{className:'expe-avis-title'},estAlerte?'Signaler un problème':'Apprécier ce transporteur')
  ));
  box.appendChild(h('p',{className:'expe-avis-sub'},
    estAlerte
      ?'Ce que vous saisissez ici fait baisser la note de confiance du transporteur.'
      :'Ce que vous saisissez ici fait monter la note de confiance du transporteur.'
  ));

  const couleur=getTrpColor(a.transporteur_id);
  box.appendChild(h('div',{className:'expe-avis-trp'},
    couleur?trpTag(a.transporteur||'—',couleur):h('strong',null,a.transporteur||'—'),
    a.depart_ref?h('span',{className:'expe-avis-sub',style:{margin:'0'}},a.depart_ref):null
  ));

  box.appendChild(h('div',{className:'expe-avis-field'},
    h('label',null,'Note de l\'expédition'),
    expeNoteCurseur(a.note,v=>{a.note=v;})
  ));

  const dispo=expeThematiquesPour(a.sens);
  const sel=h('select',null,h('option',{value:''},
    dispo.length?'Choisir une thématique…':'Chargement…'));
  dispo.forEach(t=>{
    const o=h('option',{value:String(t.id)},t.libelle);
    if(Number(a.thematique_id)===Number(t.id))o.selected=true;
    sel.appendChild(o);
  });
  sel.addEventListener('change',e=>{a.thematique_id=e.target.value?Number(e.target.value):null;});
  box.appendChild(h('div',{className:'expe-avis-field'},
    h('label',null,'Thématique'),sel));

  const com=h('textarea',{placeholder:estAlerte
    ?'Ce qui s\'est mal passé : faits, dates, conséquence pour le client…'
    :'Ce qui s\'est bien passé : ce qui mérite d\'être retenu pour la prochaine fois…'});
  com.value=a.commentaire||'';
  com.addEventListener('input',e=>{a.commentaire=e.target.value;});
  box.appendChild(h('div',{className:'expe-avis-field'},
    h('label',null,'Commentaire'),com));

  box.appendChild(h('div',{className:'expe-avis-actions'},
    h('button',{type:'button',className:'btn btn-ghost',onClick:expeFermerAvis},'Annuler'),
    h('button',{type:'button',className:'btn btn-accent',disabled:!!a.envoi,
      onClick:()=>void expeEnvoyerAvis()},a.envoi?'Enregistrement…':'Enregistrer')
  ));

  overlay.appendChild(box);
  return overlay;
}

// Paire de boutons posée sur une ligne de départ.
function expeAvisBoutons(r){
  if(!expeCanWrite())return [];
  if(!r||!(r.transporteur||r.transporteur_id))return [];
  return [
    h('button',{className:'expe-avis-btn alerte',type:'button',
      title:'Signaler un problème sur cette expédition',
      onClick:()=>expeOuvrirAvis(r,'alerte')},expeIconAlerte(14)),
    h('button',{className:'expe-avis-btn appreciation',type:'button',
      title:'Apprécier cette expédition',
      onClick:()=>expeOuvrirAvis(r,'appreciation')},expeIconPouce(14))
  ];
}

// ── Onglet « Suivi qualité » de la fiche transporteur ─────────────
async function expeChargerHistoriqueNote(transporteurId){
  N.histTrpId=Number(transporteurId);
  N.histLoading=true;
  render();
  try{
    N.hist=await api('/api/expe/transporteurs/'+transporteurId+'/avis');
  }catch(e){
    N.hist=null;
    toast(e.message||'Historique indisponible','error');
  }
  N.histLoading=false;
  render();
}

async function expeEnvoyerAjustement(){
  const trpId=N.histTrpId;
  if(!trpId)return;
  const valeur=Number(N.ajustValeur)||0;
  if(!valeur){toast('Choisir un ajustement différent de zéro.','error');return;}
  if(!String(N.ajustMotif||'').trim()){
    toast('Motif obligatoire pour un ajustement manuel.','error');
    return;
  }
  N.ajustEnvoi=true;
  render();
  try{
    await api('/api/expe/transporteurs/'+trpId+'/ajustement',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({ajustement:valeur,commentaire:N.ajustMotif})
    });
    N.ajustValeur=0;
    N.ajustMotif='';
    N.ajustEnvoi=false;
    toast('Ajustement enregistré.');
    await loadTransporteurs();
    await expeChargerHistoriqueNote(trpId);
    return;
  }catch(e){
    toast(e.message||'Ajustement impossible','error');
  }
  N.ajustEnvoi=false;
  render();
}

async function expeSupprimerAvis(avisId){
  if(!confirm('Supprimer cette entrée de l\'historique ? La note sera recalculée.'))return;
  try{
    await api('/api/expe/avis/'+avisId,{method:'DELETE'});
    toast('Entrée supprimée.');
    await loadTransporteurs();
    if(N.histTrpId)await expeChargerHistoriqueNote(N.histTrpId);
  }catch(e){
    toast(e.message||'Suppression impossible','error');
  }
}

function expeNoteItemDate(iso){
  return String(iso||'').replace('T',' ').slice(0,16)||'—';
}

function renderExpeTrpNoteOnglet(){
  const wrap=h('div',{className:'expe-trp-sec'});
  if(N.histLoading&&!N.hist){
    wrap.appendChild(h('div',{className:'expe-nq-vide'},'Chargement…'));
    return wrap;
  }
  const data=N.hist||{note:{},avis:[]};
  const note=data.note||{};
  const avis=data.avis||[];

  const meta=[];
  if(note.valeur!=null)meta.push(expeNoteFmt(note.valeur)+'/10');
  meta.push(note.nb_avis?((note.nb_avis)+' avis'):'note de départ, aucun avis');
  if(note.nb_alertes)meta.push(note.nb_alertes+' signalement'+(note.nb_alertes>1?'s':''));
  if(note.ajustement)meta.push('ajustement manuel '+(note.ajustement>0?'+':'')+expeNoteFmt(note.ajustement)+' pt');
  wrap.appendChild(h('div',{className:'expe-nq-entete'},
    expeNoteBadge(note,{grand:true}),
    h('div',{className:'expe-nq-entete-txt'},
      h('div',{className:'expe-nq-lib'},expeNoteLibelle(note.lettre)),
      h('div',{className:'expe-nq-meta'},meta.join(' · ')),
      note.provisoire?h('span',{className:'expe-nq-prov'},'Note provisoire — moins de '+EXPE_NOTE_SEUIL_FIABILITE+' avis'):null,
      note.par_defaut
        ?h('div',{className:'expe-nq-meta'},
            'Tous les transporteurs partent de '+expeNoteFmt(EXPE_NOTE_DEPART)+'/10. '
            +'Cette note de départ pèse comme un avis, et s\'efface à mesure que de vrais avis arrivent.')
        :null
    )
  ));

  if(expeCanWrite()){
    const sel=h('select',null);
    for(let p=-EXPE_AJUST_MAX*2;p<=EXPE_AJUST_MAX*2;p++){
      const v=p/2;
      const o=h('option',{value:String(v)},
        v===0?'Aucun ajustement':((v>0?'+':'')+expeNoteFmt(v)+' point'+(Math.abs(v)>1?'s':'')));
      if(Number(N.ajustValeur)===v)o.selected=true;
      sel.appendChild(o);
    }
    sel.addEventListener('change',e=>{N.ajustValeur=Number(e.target.value)||0;});
    const motif=h('input',{type:'text',placeholder:'Motif — visible dans l\'historique'});
    motif.value=N.ajustMotif||'';
    motif.addEventListener('input',e=>{N.ajustMotif=e.target.value;});
    wrap.appendChild(h('div',{className:'expe-nq-ajust'},
      h('div',{className:'expe-nq-ajust-title'},'Ajuster la note'),
      h('div',{className:'expe-nq-ajust-help'},
        'L\'ajustement s\'ajoute en points à la moyenne des avis, il ne la remplace pas : '
        +'les avis suivants continuent de faire bouger la note. Il est tracé dans l\'historique ci-dessous, '
        +'et se cumule avec les ajustements précédents dans la limite de ±'+EXPE_AJUST_MAX+' points.'),
      h('div',{className:'expe-nq-ajust-row'},
        h('div',{className:'expe-avis-field',style:{margin:'0'}},h('label',null,'Ajustement'),sel),
        h('div',{className:'expe-avis-field',style:{margin:'0'}},h('label',null,'Motif'),motif),
        h('button',{type:'button',className:'btn btn-accent',disabled:!!N.ajustEnvoi,
          onClick:()=>void expeEnvoyerAjustement()},N.ajustEnvoi?'…':'Appliquer')
      )
    ));
  }

  const barre=h('div',{className:'expe-nq-filtres'});
  [['tous','Tout'],['alerte','Signalements'],['appreciation','Appréciations'],['ajustement','Ajustements']]
    .forEach(function(paire){
      const k=paire[0],l=paire[1];
      barre.appendChild(h('button',{type:'button',
        className:'expe-nq-filtre'+((N.histFiltre||'tous')===k?' active':''),
        onClick:()=>{N.histFiltre=k;render();}},l));
    });
  wrap.appendChild(h('div',{className:'expe-trp-sec-title'},'Historique des avis'));
  wrap.appendChild(barre);

  const f=N.histFiltre||'tous';
  const visibles=avis.filter(a=>{
    if(f==='tous')return true;
    if(f==='ajustement')return (a.type||'avis')==='ajustement';
    return (a.type||'avis')==='avis'&&a.sens===f;
  });
  const liste=h('div',{className:'expe-nq-liste'});
  if(!visibles.length){
    liste.appendChild(h('div',{className:'expe-nq-vide'},
      avis.length?'Aucune entrée pour ce filtre.':'Aucun avis émis sur ce transporteur.'));
  }
  visibles.forEach(a=>{
    const estAjust=(a.type||'avis')==='ajustement';
    const item=h('div',{className:'expe-nq-item '+(estAjust?'ajustement':(a.sens==='alerte'?'alerte':'appreciation'))});
    const tete=h('div',{className:'expe-nq-item-head'});
    tete.appendChild(h('span',{className:'expe-nq-item-them'},
      estAjust?'Ajustement manuel':(a.thematique_libelle||'Thématique retirée')));
    if(estAjust){
      tete.appendChild(h('span',{className:'expe-nq-item-note'},
        (a.ajustement>0?'+':'')+expeNoteFmt(a.ajustement)+' pt'));
    }else if(a.note!=null){
      tete.appendChild(h('span',{className:'expe-nq-item-note'},expeNoteFmt(a.note)+'/10'));
    }
    tete.appendChild(h('span',{className:'expe-nq-item-date'},
      expeNoteItemDate(a.created_at)+(a.auteur_nom?(' · '+a.auteur_nom):'')));
    if(expeCanWrite()){
      tete.appendChild(h('button',{type:'button',className:'expe-nq-item-rm',
        title:'Supprimer cette entrée',onClick:()=>void expeSupprimerAvis(a.id)},iconEl('trash',13)));
    }
    item.appendChild(tete);
    if(a.commentaire)item.appendChild(h('div',{className:'expe-nq-item-com'},a.commentaire));
    if(a.depart_ref)item.appendChild(h('div',{className:'expe-nq-item-ref'},'Expédition : '+a.depart_ref));
    liste.appendChild(item);
  });
  wrap.appendChild(liste);
  return wrap;
}
"""

EXPE_ZONES_JS = r"""
// ── MyExpé — Référentiel › Zone géographique (état Z) ─────────────
//
// On saisit une ville ou un code postal, on obtient les transporteurs à
// prioriser sur cette destination : croisement de l'historique réel des
// départs et de la note de confiance. La carte reprend le SVG des
// départements déjà utilisé par le widget des délais — un département est
// colorié de la couleur du transporteur recommandé, et reste neutre s'il n'a
// jamais été livré : mieux vaut un blanc qu'une recommandation inventée.
//
// Les render() passent par renderTransporteurs(), qui rend la main au champ
// en cours de saisie. Un render() nu viderait le champ destination pendant
// la frappe — c'est le bug qu'a connu le comparateur.
const Z={
  saisie:'',
  typeEnvoi:'',
  dept:'',
  data:null,
  loading:false,
  suggestions:[],
  suggTimer:null,
  carte:null,
  carteChargee:false,
  carteEnCours:false
};

async function expeZonesChargerCarte(){
  if(Z.carteEnCours)return;
  Z.carteEnCours=true;
  try{
    Z.carte=await api('/api/expe/zones/carte'+(Z.typeEnvoi?('?type_envoi='+encodeURIComponent(Z.typeEnvoi)):''));
    Z.carteChargee=true;
  }catch(e){
    Z.carte={};
    Z.carteChargee=true;
  }
  Z.carteEnCours=false;
  renderTransporteurs();
}

function expeZonesSuggerer(q){
  if(Z.suggTimer)clearTimeout(Z.suggTimer);
  Z.suggTimer=setTimeout(async()=>{
    if(String(q||'').trim().length<2){Z.suggestions=[];return;}
    try{
      const rows=await api('/api/expe/zones/villes?q='+encodeURIComponent(q));
      Z.suggestions=Array.isArray(rows)?rows:[];
    }catch(e){
      Z.suggestions=[];
    }
    const dl=document.getElementById('expe-zn-villes');
    if(dl){
      dl.innerHTML='';
      Z.suggestions.forEach(s=>{
        const o=document.createElement('option');
        o.value=s.ville;
        o.label=s.cp+' — '+s.ville;
        dl.appendChild(o);
      });
    }
  },320);
}

async function expeZonesInterroger(params){
  Z.loading=true;
  renderTransporteurs();
  try{
    const qs=new URLSearchParams();
    Object.keys(params||{}).forEach(k=>{if(params[k])qs.set(k,params[k]);});
    if(Z.typeEnvoi)qs.set('type_envoi',Z.typeEnvoi);
    Z.data=await api('/api/expe/zones/recommandation?'+qs.toString());
    Z.dept=(Z.data&&Z.data.departement)||'';
  }catch(e){
    Z.data=null;
    toast(e.message||'Destination introuvable','error');
  }
  Z.loading=false;
  renderTransporteurs();
}

function expeZonesRechercher(){
  const saisie=String(Z.saisie||'').trim();
  if(!saisie){toast('Saisir une ville ou un code postal.','error');return;}
  // Le serveur sait déjà démêler ville et code postal : on lui envoie la
  // saisie telle quelle plutôt que de dupliquer la règle ici.
  void expeZonesInterroger({ville:saisie});
}

function expeZonesRelancer(){
  if(!Z.data)return;
  Z.carteChargee=false;
  void expeZonesChargerCarte();
  if(Z.dept)void expeZonesInterroger({dept:Z.dept});
}

function expeZonesClicDept(dept){
  Z.saisie='';
  void expeZonesInterroger({dept:dept});
}

function expeZonesAppliquerCarte(){
  const host=document.getElementById('expe-zn-svg-host');
  if(!host)return;
  const carte=Z.carte||{};
  host.querySelectorAll('path[id], rect[id][data-dept]').forEach(el=>{
    const code=el.getAttribute('data-dept')||el.id;
    if(!code)return;
    const info=carte[code];
    el.style.cursor='pointer';
    el.style.fill=info?(info.couleur||'var(--accent-bg)'):'var(--card)';
    el.classList.toggle('expe-zn-dept--sel',Z.dept===code);
    const bouts=[code];
    if(info){
      bouts.push('à prioriser : '+info.transporteur+(info.note_lettre?(' ('+info.note_lettre+')'):''));
      bouts.push(info.nb_expeditions+' expédition'+(info.nb_expeditions>1?'s':''));
    }else{
      bouts.push('aucun départ enregistré');
    }
    el.setAttribute('title',bouts.join(' · '));
    if(!el.dataset.znWired){
      el.dataset.znWired='1';
      el.addEventListener('click',()=>expeZonesClicDept(code));
    }
  });
}

function renderExpeZones(){
  if(!Z.carteChargee&&!Z.carteEnCours)void expeZonesChargerCarte();

  const inp=h('input',{type:'text',id:'expe-zn-saisie',list:'expe-zn-villes',
    placeholder:'Ville ou code postal — ex : Lyon, ou 69003',value:Z.saisie||''});
  inp.addEventListener('input',e=>{Z.saisie=e.target.value;expeZonesSuggerer(e.target.value);});
  inp.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();expeZonesRechercher();}});
  const dl=h('datalist',{id:'expe-zn-villes'});
  (Z.suggestions||[]).forEach(s=>{
    const o=h('option',{value:s.ville});
    o.label=s.cp+' — '+s.ville;
    dl.appendChild(o);
  });

  const typeSel=h('select',null,
    h('option',{value:''},'Tous types'),
    h('option',{value:'messagerie'},'Messagerie'),
    h('option',{value:'ramasse'},'Ramasse'),
    h('option',{value:'affretement'},'Affrètement')
  );
  typeSel.value=Z.typeEnvoi||'';
  typeSel.addEventListener('change',e=>{
    Z.typeEnvoi=e.target.value;
    Z.carteChargee=false;
    void expeZonesChargerCarte();
    if(Z.dept)void expeZonesInterroger({dept:Z.dept});
  });

  const formCard=h('div',{className:'card',style:{padding:'16px 18px'}},
    h('div',{className:'expe-zn-form'},
      h('div',{className:'expe-zn-field'},h('label',null,'Destination'),inp,dl),
      h('div',{className:'expe-zn-field'},h('label',null,'Type d\'envoi'),typeSel),
      h('button',{type:'button',className:'btn btn-accent',disabled:!!Z.loading,
        onClick:expeZonesRechercher},Z.loading?'Recherche…':'Rechercher')
    ),
    h('div',{className:'expe-help',style:{marginTop:'10px'}},
      'Les villes proposées sont celles du référentiel clients. Un code postal non répertorié '
      +'reste accepté : seul le département compte pour le classement.')
  );

  const mapCard=h('div',{className:'card'},
    h('div',{className:'card-header'},h('h3',{className:'expe-mobile-hide-head'},'Carte des destinations')),
    h('div',{style:{padding:'12px 14px 16px'}},
      h('div',{className:'expe-zn-map-wrap',id:'expe-zn-svg-host'}),
      h('div',{className:'expe-zn-legende'},
        'Chaque département est colorié de la couleur du transporteur à prioriser. '
        +'Un département neutre n\'a encore aucun départ enregistré. Cliquer sur un département '
        +'affiche son classement.')
    )
  );

  const panneau=h('div',{className:'card'});
  panneau.appendChild(h('div',{className:'card-header'},
    h('h3',{className:'expe-mobile-hide-head'},'Transporteurs à prioriser')));
  const corps=h('div',{style:{padding:'14px 16px 16px'}});
  if(Z.loading){
    corps.appendChild(h('div',{className:'expe-zn-vide'},'Calcul en cours…'));
  }else if(!Z.data){
    corps.appendChild(h('div',{className:'expe-zn-vide'},
      'Saisir une ville ou un code postal, ou cliquer sur un département de la carte.'));
  }else{
    const d=Z.data;
    const dest=d.destination||{};
    const meta=[];
    if(dest.ville)meta.push(dest.ville);
    if(d.delai&&d.delai.delai_texte)meta.push('délai indicatif '+d.delai.delai_texte);
    corps.appendChild(h('div',{className:'expe-zn-dest'},
      h('span',{className:'expe-zn-dest-cp'},'Département '+(d.departement||'—')),
      meta.length?h('span',{className:'expe-zn-dest-meta'},meta.join(' · ')):null
    ));
    // Un nombre sans unite lisible ne veut rien dire : la legende est dans
    // l'ecran, pas seulement dans l'infobulle du chiffre.
    corps.appendChild(h('div',{className:'expe-zn-legende',style:{margin:'0 0 12px'}},
      'Score de priorité sur 100 : note de confiance 55 %, expéditions déjà faites '
      +'vers ce département 30 %, ancienneté de la dernière 15 %.'));
    const liste=h('div',{className:'expe-zn-liste'});
    const rows=d.transporteurs||[];
    if(!rows.length){
      liste.appendChild(h('div',{className:'expe-zn-vide'},'Aucun transporteur actif.'));
    }
    rows.forEach(r=>{
      const tags=[];
      if(r.jamais_utilise)tags.push(h('span',{className:'expe-zn-tag neuf'},'Jamais utilisé ici'));
      if(!r.eligible_zone)tags.push(h('span',{className:'expe-zn-tag hors'},'Hors zone déclarée'));
      if(r.grille_tarifaire)tags.push(h('span',{className:'expe-zn-tag'},'Grille tarifaire'));
      const detail=[];
      detail.push(r.nb_expeditions+' expédition'+(r.nb_expeditions>1?'s':'')+' sur ce département');
      if(r.derniere_expedition)detail.push('dernière le '+r.derniere_expedition);
      detail.push(r.nb_avis?(r.nb_avis+' avis'):'note de départ');
      liste.appendChild(h('div',{className:'expe-zn-item'+(r.rang===1?' premier':'')+(r.eligible_zone?'':' hors-zone')},
        h('span',{className:'expe-zn-rang'},String(r.rang)),
        expeNoteBadge(r),
        h('div',{className:'expe-zn-corps'},
          h('div',{className:'expe-zn-nom'},
            r.couleur?trpTag(r.transporteur,r.couleur):h('span',null,r.transporteur),
            ...tags),
          h('div',{className:'expe-zn-meta'},detail.join(' · '))
        ),
        h('span',{className:'expe-zn-score',title:'Score de priorité sur 100 : note de confiance 55 %, expéditions déjà faites vers ce département 30 %, ancienneté de la dernière 15 %'},
          r.score>0?(Math.round(r.score)+' / 100'):'—')
      ));
    });
    corps.appendChild(liste);
  }
  panneau.appendChild(corps);

  requestAnimationFrame(()=>{
    const host=document.getElementById('expe-zn-svg-host');
    if(host&&!host.firstChild&&typeof EXPE_FRANCE_SVG_MARKUP==='string'){
      host.innerHTML=EXPE_FRANCE_SVG_MARKUP;
    }
    expeZonesAppliquerCarte();
  });

  return h('div',{className:'expe-zn-wrap'},
    formCard,
    h('div',{className:'expe-zn-layout'},mapCard,panneau)
  );
}
"""

EXPE_THEMATIQUES_JS = r"""
// ── MyExpé — référentiel des thématiques d'avis ───────────────────
//
// Rien de métier n'est codé en dur : la liste des sujets sur lesquels on juge
// un transporteur, et le poids de chacun, s'éditent ici. Un colis perdu doit
// pouvoir peser plus qu'un retard d'une heure sans qu'on touche au code.

function expeThSectionOuverte(){
  try{return localStorage.getItem('mysifa.expe.thematiques')==='ouvert';}catch(e){return false;}
}

function expeThBasculerSection(){
  try{
    localStorage.setItem('mysifa.expe.thematiques',expeThSectionOuverte()?'ferme':'ouvert');
  }catch(e){}
  void expeChargerThematiques(true);
  render();
}

async function expeThEnregistrer(id,champ,valeur){
  const corps={};
  corps[champ]=valeur;
  try{
    await api('/api/expe/avis/thematiques/'+id,{
      method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(corps)});
    await expeChargerThematiques(true);
    await loadTransporteurs();
    toast('Thématique mise à jour.');
  }catch(e){
    toast(e.message||'Mise à jour impossible','error');
  }
}

async function expeThAjouter(){
  const inp=document.getElementById('expe-th-nouveau');
  const libelle=inp?String(inp.value||'').trim():'';
  if(!libelle){toast('Saisir un libellé de thématique.','error');return;}
  try{
    await api('/api/expe/avis/thematiques',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({libelle:libelle,sens:'les_deux',poids:1})});
    if(inp)inp.value='';
    await expeChargerThematiques(true);
    toast('Thématique ajoutée.');
  }catch(e){
    toast(e.message||'Ajout impossible','error');
  }
}

async function expeThDesactiver(id,libelle){
  if(!confirm('Retirer « '+libelle+' » des thématiques proposées ?\n\nLes avis déjà émis la conservent et continuent de compter dans la note.'))return;
  try{
    await api('/api/expe/avis/thematiques/'+id,{method:'DELETE'});
    await expeChargerThematiques(true);
    toast('Thématique retirée.');
  }catch(e){
    toast(e.message||'Retrait impossible','error');
  }
}

function renderExpeThematiquesSection(){
  if(!expeCanWrite())return null;
  const ouverte=expeThSectionOuverte();
  const card=h('div',{className:'card expe-th-card'});
  card.appendChild(h('div',{className:'card-header'},
    h('div',{className:'expe-th-head',onClick:expeThBasculerSection},
      h('span',{className:'expe-th-chev'+(ouverte?' open':'')},iconEl('chevron-right',14)),
      h('h3',{style:{margin:'0'}},'Thématiques d\'avis'),
      h('span',{style:{fontSize:'12px',color:'var(--muted)'}},
        ouverte?'':'— sujets et poids utilisés pour calculer la note de confiance')
    )
  ));
  if(!ouverte)return card;

  const corps=h('div',{className:'expe-th-body'});
  corps.appendChild(h('p',{className:'expe-th-aide'},
    'Le poids dit combien une thématique compte dans la moyenne : 1 est la référence, '
    +'2 fait peser un avis deux fois plus lourd. Le sens détermine où la thématique est proposée — '
    +'dans un signalement, dans une appréciation, ou dans les deux.'));

  const rows=(N.thematiques||[]);
  if(!rows.length){
    corps.appendChild(h('div',{className:'expe-nq-vide'},
      N.thematiquesEnCours?'Chargement…':'Aucune thématique.'));
  }
  rows.forEach(t=>{
    const lib=h('input',{type:'text',value:t.libelle||''});
    lib.addEventListener('change',e=>void expeThEnregistrer(t.id,'libelle',e.target.value));
    const sens=h('select',null,
      h('option',{value:'les_deux'},'Les deux'),
      h('option',{value:'alerte'},'Signalement'),
      h('option',{value:'appreciation'},'Appréciation'));
    sens.value=t.sens||'les_deux';
    sens.addEventListener('change',e=>void expeThEnregistrer(t.id,'sens',e.target.value));
    const poids=h('input',{type:'number',step:'0.1',min:'0.1',max:'5',value:String(t.poids!=null?t.poids:1)});
    poids.addEventListener('change',e=>void expeThEnregistrer(t.id,'poids',Number(e.target.value)));
    corps.appendChild(h('div',{className:'expe-th-row'+(Number(t.actif)?'':' inactive')},
      lib,sens,poids,
      h('span',{style:{fontSize:'11px',color:'var(--muted)',whiteSpace:'nowrap'}},
        Number(t.actif)?'Active':'Retirée'),
      Number(t.actif)
        ?h('button',{type:'button',className:'expe-th-act',title:'Retirer cette thématique',
            onClick:()=>void expeThDesactiver(t.id,t.libelle)},iconEl('trash',13))
        :h('button',{type:'button',className:'expe-th-act',title:'Remettre cette thématique',
            onClick:()=>void expeThEnregistrer(t.id,'actif',true)},iconEl('rotate-ccw',13))
    ));
  });

  const nouveau=h('input',{type:'text',id:'expe-th-nouveau',placeholder:'Nouvelle thématique — ex : Qualité du sanglage'});
  nouveau.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();void expeThAjouter();}});
  corps.appendChild(h('div',{className:'expe-th-row',style:{marginTop:'8px',borderTop:'1px solid var(--border)',paddingTop:'14px'}},
    nouveau,
    h('span',null),h('span',null),h('span',null),
    h('button',{type:'button',className:'btn btn-accent',onClick:()=>void expeThAjouter()},'Ajouter')
  ));
  card.appendChild(corps);
  return card;
}
"""

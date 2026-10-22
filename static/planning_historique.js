/*
 * MySifa — Planning : fenêtre « Historique des modifications ».
 *
 * Tout ce qui a été modifié sur le Planning de production (dossiers, ordre,
 * horaires, jours off, réglages), lu dans le journal des actions par
 * GET /api/planning/historique (app/services/planning_historique.py), qui rend
 * déjà chaque ligne lisible : titre, machine, valeurs avant → après.
 *
 * Chargé après planning_url.js et avant le script principal : il ne fait que
 * déclarer des fonctions. S, MID, api(), escHtml(), icon(), closeM() et
 * planningModaleOuverte() appartiennent à la page et ne sont lus qu'à l'appel.
 *
 * Adresse (.claude/rules/url-etat.md) : `historique=machine|toutes`, plus
 * `hist_machine` (autre machine que celle de la page), `hist_utilisateur`,
 * `hist_action`, `hist_jours` (défaut 30, non écrit). La recherche texte n'y
 * va pas : c'est une saisie en cours.
 */
const _HIST_JOURS=[["7","7 derniers jours"],["30","30 derniers jours"],["90","90 derniers jours"],["0","Tout l'historique"]];
const _HIST_PAGE=100;
let _hist=null;   // état de la fenêtre ouverte, null sinon

function _histEtatInitial(portee){
  const u=window.MySifaUrl?MySifaUrl.lire():null;
  const g=(k,d)=>{ try{ const v=u&&u.get(k,null); return v==null?d:v; }catch(e){ return d; } };
  let machine=portee==="toutes"?"":String(MID||"");
  const hm=g("hist_machine",null);
  if(hm&&/^[0-9]+$/.test(hm)) machine=hm;
  const jours=g("hist_jours","30");
  return {
    machine,
    utilisateur:g("hist_utilisateur",""),
    action:(g("hist_action","")||"").replace(/[^A-Z_]/g,""),
    jours:_HIST_JOURS.some(j=>j[0]===jours)?jours:"30",
    q:"",
    lignes:[], total:0, machines:[], utilisateurs:[], actions:[],
    charge:false, erreur:"", seq:0,
  };
}

// Paramètres d'adresse de la fenêtre, ajoutés par planningParams().
function planningHistoriqueParams(){
  if(!_hist) return {};
  const p={};
  if(_hist.machine&&_hist.machine!==String(MID)) p.hist_machine=_hist.machine;
  if(_hist.utilisateur) p.hist_utilisateur=_hist.utilisateur;
  if(_hist.action) p.hist_action=_hist.action;
  if(_hist.jours!=="30") p.hist_jours=_hist.jours;
  return p;
}
function _histPortee(){ return _hist&&_hist.machine===""?"toutes":"machine"; }
function _histSyncUrl(){
  if(!_hist) return;
  S.urlModale={cle:"historique",id:_histPortee()};
  if(typeof planningSyncUrl==="function") planningSyncUrl();
}

function openHistoriqueModal(portee){
  _hist=_histEtatInitial(portee==="toutes"?"toutes":"machine");
  planningModaleOuverte("historique",_histPortee());
  document.getElementById("mroot").innerHTML=`<div class="mo" onclick="if(event.target===this)closeM()"><div class="md md--hist" role="dialog" aria-label="Historique des modifications">
    <div class="hist-hdr">
      <h3>${icon("clock",18)} Historique des modifications</h3>
      <button type="button" class="btn-s" onclick="closeM()">Fermer</button>
    </div>
    <p class="hist-sub">Tout ce qui a été modifié sur le planning de production : dossiers, ordre, horaires, jours off, réglages. Qui, quand, et la valeur d'avant quand elle est connue.</p>
    <div class="hist-filtres">
      <select id="hist-machine" aria-label="Machine" onchange="_histFiltre('machine',this.value)"></select>
      <select id="hist-jours" aria-label="Période" onchange="_histFiltre('jours',this.value)">
        ${_HIST_JOURS.map(j=>`<option value="${j[0]}"${j[0]===_hist.jours?" selected":""}>${j[1]}</option>`).join("")}
      </select>
      <select id="hist-utilisateur" aria-label="Utilisateur" onchange="_histFiltre('utilisateur',this.value)"></select>
      <select id="hist-action" aria-label="Type de modification" onchange="_histFiltre('action',this.value)"></select>
      <div class="hist-search">
        <input type="text" id="hist-q" placeholder="Rechercher (dossier, référence, date, utilisateur…)" autocomplete="off"
          oninput="_histRecherche(this.value)" onkeydown="if(event.key==='Escape'&&this.value){this.value='';_histRecherche('');event.stopPropagation();}">
      </div>
    </div>
    <div id="hist-compte" class="hist-compte"></div>
    <div id="hist-liste" class="hist-liste"><div class="hist-vide">Chargement de l'historique…</div></div>
  </div></div>`;
  _histCharger(false);
}

function _histFiltre(cle,val){
  if(!_hist) return;
  _hist[cle]=val;
  _histSyncUrl();
  _histCharger(false);
}
let _histMinuteur=null;
function _histRecherche(val){
  if(!_hist) return;
  clearTimeout(_histMinuteur);
  _histMinuteur=setTimeout(()=>{ if(_hist){ _hist.q=val.trim(); _histCharger(false); } },250);
}

async function _histCharger(suite){
  if(!_hist) return;
  const h=_hist, seq=++h.seq;
  const p=new URLSearchParams();
  if(h.machine) p.set("machine_id",h.machine);
  if(h.utilisateur) p.set("utilisateur",h.utilisateur);
  if(h.action) p.set("action",h.action);
  p.set("jours",h.jours);
  if(h.q) p.set("q",h.q);
  p.set("offset",suite?String(h.lignes.length):"0");
  p.set("limite",String(_HIST_PAGE));
  h.charge=true; h.erreur="";
  if(suite) _histRendreListe();
  try{
    const d=await api(`/historique?${p.toString()}`);
    if(_hist!==h||seq!==h.seq) return;          // fenêtre fermée ou filtre changé entre-temps
    h.lignes=suite?h.lignes.concat(d.lignes||[]):(d.lignes||[]);
    h.total=d.total||0;
    h.machines=d.machines||[]; h.utilisateurs=d.utilisateurs||[]; h.actions=d.actions||[];
  }catch(e){
    if(_hist!==h) return;
    h.erreur=apiErrorMessage(e,"Historique indisponible.");
  }
  h.charge=false;
  _histRendreFiltres();
  _histRendreListe();
}

function _histOptions(sel,vide,items,val){
  const el=document.getElementById(sel);
  if(!el) return;
  // Une valeur venue de l'adresse reste choisie même si la période ne la contient plus.
  if(val&&!items.some(i=>i[0]===val)) items=items.concat([[val,val]]);
  el.innerHTML=`<option value="">${escHtml(vide)}</option>`+items.map(i=>
    `<option value="${escAttr(i[0])}"${i[0]===val?" selected":""}>${escHtml(i[1])}</option>`).join("");
}
function _histRendreFiltres(){
  const h=_hist;
  _histOptions("hist-machine","Toutes les machines",h.machines.map(m=>[String(m.id),m.nom]),h.machine);
  _histOptions("hist-utilisateur","Tous les utilisateurs",h.utilisateurs.map(u=>[u,u]),h.utilisateur);
  _histOptions("hist-action","Tous les types",h.actions.map(a=>[a.valeur,a.libelle]),h.action);
}

function _histJour(iso){
  const d=new Date(iso+"T12:00:00");
  if(isNaN(d)) return iso;
  const auj=new Date(); auj.setHours(12,0,0,0);
  const ecart=Math.round((auj-d)/86400000);
  const lib=d.toLocaleDateString("fr-FR",{weekday:"long",day:"2-digit",month:"2-digit",year:"numeric"});
  return (ecart===0?"Aujourd'hui · ":ecart===1?"Hier · ":"")+lib.charAt(0).toUpperCase()+lib.slice(1);
}

function _histLigneDetail(l){
  const champ=l.champ?`<span class="hist-champ">${escHtml(l.champ)}</span>`:"";
  if(l.valeur!=null) return `<div class="hist-det">${champ}<span>${escHtml(l.valeur)}</span></div>`;
  return `<div class="hist-det">${champ}<span class="hist-avant">${escHtml(l.avant)}</span><span class="hist-fleche">→</span><span class="hist-apres">${escHtml(l.apres)}</span></div>`;
}

function _histRendreListe(){
  const h=_hist, box=document.getElementById("hist-liste"), cpt=document.getElementById("hist-compte");
  if(!h||!box) return;
  if(cpt) cpt.textContent=h.charge&&!h.lignes.length?"":`${h.total} modification${h.total>1?"s":""}`;
  if(h.erreur){ box.innerHTML=`<div class="hist-vide">${escHtml(h.erreur)}</div>`; return; }
  if(!h.lignes.length){
    box.innerHTML=`<div class="hist-vide">${h.charge?"Chargement de l'historique…":(h.q?`Aucun résultat pour « ${escHtml(h.q)} »`:"Aucune modification sur cette période.")}</div>`;
    return;
  }
  const toutes=!h.machine;
  let html="", jour="";
  for(const l of h.lignes){
    if(l.jour!==jour){ jour=l.jour; html+=`<div class="hist-jour">${escHtml(_histJour(jour))}</div>`; }
    const heure=(l.quand||"").slice(-5);
    html+=`<div class="hist-item${l.inchange?" hist-item--inchange":""}">
      <div class="hist-heure">${escHtml(heure)}</div>
      <div class="hist-corps">
        <div class="hist-tete">
          <span class="hist-badge" style="--hist-c:${escAttr(l.action_couleur||"var(--muted)")}">${escHtml(l.action_label||l.action)}</span>
          ${toutes&&l.machine?`<span class="hist-machine">${escHtml(l.machine)}</span>`:""}
          <span class="hist-titre">${escHtml(l.titre)}</span>
        </div>
        <div class="hist-qui">${escHtml(l.utilisateur)}${l.inchange?" · aucun changement":""}</div>
        ${(l.lignes||[]).map(_histLigneDetail).join("")}
      </div>
    </div>`;
  }
  if(h.lignes.length<h.total){
    html+=`<div class="hist-plus"><button type="button" class="btn-s" ${h.charge?"disabled":""} onclick="_histCharger(true)">${h.charge?"Chargement…":`Afficher les ${Math.min(_HIST_PAGE,h.total-h.lignes.length)} suivantes`}</button></div>`;
  }
  box.innerHTML=html;
}

// closeM() vide #mroot : on oublie l'état dès que la fenêtre n'est plus là.
function _histFermee(){ _hist=null; clearTimeout(_histMinuteur); }

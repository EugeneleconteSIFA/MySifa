/*
 * MySifa — Planning : adresse de la page (static/mysifa_url.js,
 * .claude/rules/url-etat.md).
 *
 * Extrait de app/web/planning_page.py le 15/10/2026 pour ne pas rallonger la
 * page. Chargé AVANT le script principal du Planning : il ne fait que déclarer
 * des fonctions et s'abonner au Retour du navigateur. S, MID, load(), render(),
 * openEdit()… appartiennent au script principal ; ils ne sont lus qu'à
 * l'appel, une fois la page démarrée (scripts classiques : les `let` de
 * premier niveau partagent la même portée globale).
 */
// ── Adresse de la page (static/mysifa_url.js, .claude/rules/url-etat.md) ──
// machine, vue (prod / expé), horizon (1w / 2w / 4w), semaine affichée (lundi
// en date, pas un décalage : un lien garde son sens la semaine suivante) et
// fenêtre ouverte (dossier, aperçu OF, statistiques). Recalculée à la fin de
// render(). Changer de semaine ou d'horizon remplace l'adresse ; ouvrir une
// fenêtre l'empile, la fermer recule.
let _urlPrete=false;            // posé à la fin du démarrage : avant, l'adresse
                                // porte encore q / tlq / auto / depuis-of à lire.
let _modaleUrl=null;            // fenêtre demandée par l'adresse, ouverte après load()
const _PLAN_VUES_URL=["prod","expe","prod_expe"];
const _PLAN_HORIZONS=["1w","2w","4w"];
// Par fenêtre : la forme de valeur admise, comment la rouvrir, la fermer.
// Toutes s'affichent dans #mroot (closeM) sauf l'aperçu OF, qui a sa surcouche.
const _PLAN_ID=/^[0-9]+$/, _PLAN_JOUR=/^\d{4}-\d{2}-\d{2}$/;
const _planJourDe=v=>new Date(v+"T12:00:00");
const _PLAN_MODALES={
  dossier:{ok:_PLAN_ID,ouvrir:v=>openEdit(Number(v)),              fermer:()=>closeM(true)},
  stats:  {ok:_PLAN_ID,ouvrir:v=>openDossierStatsModal(Number(v)), fermer:()=>closeM(true)},
  of:     {ok:_PLAN_ID,ouvrir:v=>openOfPreview(Number(v)),         fermer:()=>closeOfPreview(true)},
  fsc:    {ok:/^[A-Za-z0-9 ._+\-\/]{1,60}$/,ouvrir:v=>openFscRapport(v), fermer:()=>closeM(true)},
  // Réglages horaires par défaut de la machine (roue dentée de l'en-tête).
  reglages:{ok:/^machine$/,ouvrir:()=>openDefaultsModal(),         fermer:()=>closeM(true)},
  reglages_semaine:{ok:_PLAN_JOUR,ouvrir:v=>openWeekSettingsModal(getMon(_planJourDe(v)).getTime()), fermer:()=>closeM(true)},
  horaires:{ok:_PLAN_JOUR,ouvrir:v=>openHorairesModal(v,_planJourDe(v).getDay()), fermer:()=>closeM(true)},
  commentaire_jour:{ok:_PLAN_JOUR,ouvrir:v=>openDayCommentModal(v,_planJourDe(v).getDay()), fermer:()=>closeM(true)},
  commentaire_semaine:{ok:_PLAN_JOUR,ouvrir:v=>{const m=getMon(_planJourDe(v));openWeekCommentModal(semaineKey(m),m.getTime());}, fermer:()=>closeM(true)}
};
// Déclare la fenêtre qui vient de s'ouvrir (appelé en tête de chaque open…).
function planningModaleOuverte(cle,id){ S.urlModale={cle,id:String(id)}; planningSyncUrl(); }
function _planLundiIso(wo){ return ymdate(addD(getMon(new Date()),wo*7)); }
function planningParams(){
  const p={machine:MID||null};
  if(S.planningVue&&S.planningVue!=="prod") p.vue=S.planningVue;
  if(S.view&&S.view!=="2w") p.horizon=S.view;
  if(S.wo) p.semaine=_planLundiIso(S.wo);
  let nav="m"+MID+"/"+(S.planningVue||"prod");
  const mo=S.urlModale;
  if(mo&&mo.cle&&mo.id!=null){ p[mo.cle]=mo.id; nav+="/"+mo.cle; }
  return {params:p,nav};
}
function planningSyncUrl(){
  if(!_urlPrete||!window.MySifaUrl||!MID) return;
  try{ const r=planningParams(); MySifaUrl.ecrire(r.params,{navigation:r.nav}); }catch(e){}
}
// Horizon, semaine et fenêtre demandés par l'adresse. Rend vrai si la vue
// affichée change (il faut recharger le planning).
function planningLireUrl(complet){
  if(!window.MySifaUrl) return false;
  const u=MySifaUrl.lire();
  const avant=S.view+"|"+S.wo;
  const hz=u.get("horizon",null,_PLAN_HORIZONS);
  if(hz) S.view=hz; else if(complet) S.view="2w";
  const sem=u.get("semaine",null);
  if(sem&&/^\d{4}-\d{2}-\d{2}$/.test(sem)){
    const lundi=getMon(new Date(sem+"T00:00:00"));
    S.wo=Math.round((lundi-getMon(new Date()))/(7*86400000));
  }else if(complet) S.wo=0;
  _modaleUrl=null;
  Object.keys(_PLAN_MODALES).forEach(cle=>{
    const v=u.get(cle,null);
    if(v&&_PLAN_MODALES[cle].ok.test(v)) _modaleUrl={cle,id:v};
  });
  return avant!==S.view+"|"+S.wo;
}
function planningAppliquerModaleUrl(){
  const voulue=_modaleUrl; _modaleUrl=null;
  const cour=S.urlModale;
  if(cour&&(!voulue||voulue.cle!==cour.cle||String(voulue.id)!==String(cour.id))){
    try{ _PLAN_MODALES[cour.cle].fermer(); }catch(e){}
    // L'aperçu OF refermé rend la main à la fenêtre du dossier restée
    // dessous (closeOfPreview la remet dans S.urlModale) : ne pas l'effacer.
    if(S.urlModale===cour) S.urlModale=null;
  }
  const deja=S.urlModale;
  if(voulue&&!(deja&&deja.cle===voulue.cle&&String(deja.id)===String(voulue.id))){
    try{ _PLAN_MODALES[voulue.cle].ouvrir(voulue.id); }catch(e){}
  }
}
if(window.MySifaUrl){
  MySifaUrl.surRetour(async u=>{
    if(!_urlPrete) return;
    // Autre machine ou autre vue : la page se reconstruit entièrement, comme
    // au clic sur le sélecteur (qui recharge déjà la page).
    const m=parseInt(u.get("machine",""),10);
    const v=u.get("vue","prod",_PLAN_VUES_URL);
    if((isFinite(m)&&m!==MID)||v!==S.planningVue){ location.reload(); return; }
    if(planningLireUrl(true)){
      try{ localStorage.setItem("mysifa.planning.view",S.view); }catch(e){}
      await load();
    }
    planningAppliquerModaleUrl();
  });
}

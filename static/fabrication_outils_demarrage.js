/* Saisie Prod — l'outil (la plaque) confirmé au démarrage du dossier.

   La fiche technique dit quelle plaque le dossier DEVAIT utiliser. Dans
   « Démarrer un dossier », elle est proposée d'office : le conducteur confirme
   d'un appui, ou change (recherche, ou scan de l'étiquette de la plaque — le
   code-barres porte le numéro). Sans proposition de la fiche, c'est la plaque
   en place sur la machine qui est proposée.

   Quelles natures se confirment ici : `outil_types.au_demarrage`, servi par
   GET /api/fabrication/outils/demarrage. Rien n'est écrit en dur.

   Le choix part avec la saisie 01 (`outils_demarrage`). Il ne bloque jamais
   le démarrage : une ligne sans outil connu n'est simplement pas envoyée.

   Script classique chargé AVANT le script principal : il ne lit S, h(),
   apiFetch()… qu'à l'appel. Aucun nom de premier niveau ne doit exister
   ailleurs dans la page. */

const _debutOutilTimers = {};

function debutOutilCle(nature, ligne){ return nature.type_cle+':'+ligne.rang; }

/* Charge les natures à confirmer pour le dossier choisi, et pose le choix par
   défaut : l'outil de la fiche, sinon celui en place sur la machine. */
async function loadDebutOutils(ref){
  S.debutOutils = null;
  S.debutOutilsChoix = {};
  S.debutOutilsRes = {};
  if(!ref) return;
  let qs = '?no_dossier='+encodeURIComponent(ref);
  const mid = S.adminMachineId || (S.machine && S.machine.id);
  if(mid) qs += '&machine_id='+encodeURIComponent(mid);
  let d;
  try{
    d = await apiFetch('/api/fabrication/outils/demarrage'+qs);
  }catch(e){
    // Rien de bloquant : le dossier démarre sans confirmation d'outil.
    d = {natures:[], erreur:true};
  }
  if(S.debutMonteesPour !== ref) return;   // un autre dossier a été choisi entre-temps
  const choix = {};
  (d.natures||[]).forEach(n => (n.lignes||[]).forEach(l => {
    const prop = l.prevu || (l.rang === 1 && n.en_place
      ? {id:n.en_place.id, numero:n.en_place.numero, label:n.en_place.label, origine:'referentiel'}
      : null);
    choix[debutOutilCle(n, l)] = {mode: prop ? 'confirme' : 'change', outil: prop, q: ''};
  }));
  S.debutOutils = d;
  S.debutOutilsChoix = choix;
  if(S.showDebutModal) fabRenderPreserveUi({});
}

/* Ce qui part avec la saisie 01. */
function debutOutilsPayload(){
  const d = S.debutOutils;
  if(!d || !(d.natures||[]).length) return null;
  const out = [];
  d.natures.forEach(n => (n.lignes||[]).forEach(l => {
    const c = (S.debutOutilsChoix||{})[debutOutilCle(n, l)];
    if(!c || !c.outil) return;
    const o = c.outil;
    out.push(o.id
      ? {type:n.type_cle, rang:l.rang, outil_id:o.id}
      : {type:n.type_cle, rang:l.rang, numero:o.numero, label:o.label||null, origine:o.origine||''});
  }));
  return out.length ? out : null;
}

/* Une ligne sans outil choisi : le dossier démarre quand même, mais on le
   dit avant, pour qu'un oubli ne passe pas en silence. */
function debutOutilsManquants(){
  const d = S.debutOutils;
  if(!d) return [];
  const manque = [];
  (d.natures||[]).forEach(n => (n.lignes||[]).forEach(l => {
    const c = (S.debutOutilsChoix||{})[debutOutilCle(n, l)];
    if(!c || !c.outil) manque.push(n.label + (n.lignes.length > 1 ? ' '+l.rang : ''));
  }));
  return manque;
}

function debutOutilChoisir(cle, outil){
  const c = S.debutOutilsChoix[cle] || {};
  S.debutOutilsChoix[cle] = Object.assign({}, c, {mode:'confirme', outil:outil, q:''});
  S.debutOutilsRes[cle] = null;
  fabRenderPreserveUi({});
}

async function debutOutilChercher(cle, typeCle, terme){
  let d;
  try{
    d = await apiFetch('/api/fabrication/outils/recherche'
      +'?type='+encodeURIComponent(typeCle)+'&q='+encodeURIComponent(terme||''));
  }catch(e){
    d = {resultats:[], creation:null, _err:e.message};
  }
  S.debutOutilsRes[cle] = d;
  debutOutilPeupler(cle);
  return d;
}

/* Les résultats se posent dans leur conteneur sans redessiner la fenêtre :
   le champ de recherche garde le focus pendant la frappe. */
function debutOutilPeupler(cle){
  const hote = document.getElementById('debut-outil-res-'+cle.replace(/[^a-z0-9_-]/gi,'_'));
  if(!hote) return;
  const d = S.debutOutilsRes[cle];
  hote.innerHTML = '';
  if(!d) return;
  if(d._err){ hote.appendChild(h('div',{className:'fab-outil-vide'}, d._err)); return; }
  const lignes = [];
  if(d.creation){
    lignes.push(h('button',{type:'button', className:'fab-outil-item fab-outil-item--creer',
      onClick:()=>debutOutilChoisir(cle, {id:null, numero:d.creation, label:null, origine:'poste'})},
      svgIcon('plus-circle',14),
      h('span',{className:'fab-outil-num'},'Utiliser '+d.creation),
      h('span',{className:'fab-outil-badge'},'nouveau')));
  }
  (d.resultats||[]).forEach(o => {
    lignes.push(h('button',{type:'button', className:'fab-outil-item',
      onClick:()=>debutOutilChoisir(cle, o)},
      h('span',{className:'fab-outil-num'}, o.numero),
      o.label ? h('span',{className:'fab-outil-lbl'}, o.label) : null,
      h('span',{className:'fab-outil-badge'},
        (typeof OUTIL_ORIGINE_LABEL !== 'undefined' && OUTIL_ORIGINE_LABEL[o.origine]) || o.origine)));
  });
  if(!lignes.length){
    hote.appendChild(h('div',{className:'fab-outil-vide'},
      'Aucun outil ne correspond. Tapez le numéro complet pour l\'utiliser.'));
    return;
  }
  lignes.forEach(l => hote.appendChild(l));
}

function debutOutilLigne(n, l){
  const cle = debutOutilCle(n, l);
  const c = S.debutOutilsChoix[cle] || {mode:'change', outil:null, q:''};
  const nature = n.label + (n.lignes.length > 1 ? ' '+l.rang : '');
  const prevu = l.prevu;
  const ecart = prevu && c.outil && String(c.outil.numero).toLowerCase() !== String(prevu.numero).toLowerCase();

  // Ce qui est proposé, et d'où ça vient.
  const source = prevu
    ? 'Prévue par la fiche technique'
    : (l.rang === 1 && n.en_place ? 'En place sur la machine (rien sur la fiche)' : 'Rien sur la fiche, aucune en place connue');

  const entete = h('div',{className:'fab-demarrage-tete'},
    h('span',{className:'fab-demarrage-nature'}, nature),
    h('span',{className:'fab-demarrage-source'}, source));

  const choisi = c.outil
    ? h('div',{className:'fab-demarrage-choisi'+(ecart?' is-ecart':'')},
        svgIcon(ecart ? 'alert' : 'check', 16),
        h('span',{className:'fab-demarrage-num'}, c.outil.numero),
        c.outil.label ? h('span',{className:'fab-outil-lbl'}, c.outil.label) : null,
        ecart ? h('span',{className:'fab-demarrage-ecart'}, 'fiche : '+prevu.numero) : null)
    : h('div',{className:'fab-demarrage-vide'}, 'Aucune '+n.label.toLowerCase()+' choisie.');

  const boutons = h('div',{className:'fab-demarrage-choix'},
    h('button',{type:'button', className:'fab-demarrage-btn'+(c.mode==='confirme'&&c.outil?' is-actif':''),
      disabled:!c.outil,
      onClick:()=>{ S.debutOutilsChoix[cle] = Object.assign({}, c, {mode:'confirme'}); fabRenderPreserveUi({}); }},
      svgIcon('check',14),' Confirmer'),
    h('button',{type:'button', className:'fab-demarrage-btn'+(c.mode==='change'?' is-actif':''),
      onClick:()=>{
        S.debutOutilsChoix[cle] = Object.assign({}, c, {mode:'change'});
        S._debutOutilFocus = cle;
        fabRenderPreserveUi({});
      }},
      svgIcon('search',14),' Changer'));

  let recherche = null;
  if(c.mode === 'change'){
    const inp = h('input',{type:'search', autocomplete:'off', id:'debut-outil-q-'+cle.replace(/[^a-z0-9_-]/gi,'_'),
      placeholder:'Numéro de '+n.label.toLowerCase()+', ou scannez son étiquette'});
    inp.value = c.q || '';
    inp.addEventListener('input', e => {
      S.debutOutilsChoix[cle].q = e.target.value;
      if(_debutOutilTimers[cle]) clearTimeout(_debutOutilTimers[cle]);
      _debutOutilTimers[cle] = setTimeout(()=>debutOutilChercher(cle, n.type_cle, e.target.value), 250);
    });
    // Une douchette tape le numéro puis Entrée : le numéro exact est pris tel quel.
    inp.addEventListener('keydown', async e => {
      if(e.key === 'Escape'){ e.target.value = ''; S.debutOutilsChoix[cle].q = ''; S.debutOutilsRes[cle] = null; debutOutilPeupler(cle); return; }
      if(e.key !== 'Enter') return;
      e.preventDefault();
      const terme = String(e.target.value||'').trim();
      if(!terme) return;
      if(_debutOutilTimers[cle]) clearTimeout(_debutOutilTimers[cle]);
      const d = await debutOutilChercher(cle, n.type_cle, terme);
      const exact = (d.resultats||[]).find(o => String(o.numero).toLowerCase() === terme.toLowerCase());
      if(exact) debutOutilChoisir(cle, exact);
      else if(d.creation && d.creation.toLowerCase() === terme.toLowerCase())
        debutOutilChoisir(cle, {id:null, numero:d.creation, label:null, origine:'poste'});
    });
    recherche = h('div',null, inp,
      h('div',{className:'fab-outil-res', id:'debut-outil-res-'+cle.replace(/[^a-z0-9_-]/gi,'_')}));
    setTimeout(()=>debutOutilPeupler(cle), 0);
  }

  return h('div',{className:'fab-demarrage-outil'}, entete, choisi, boutons, recherche);
}

/* Le bloc de la fenêtre « Démarrer un dossier ». null s'il n'y a rien à
   confirmer (aucune nature marquée, ou lecture impossible). */
function renderDebutOutils(){
  const d = S.debutOutils;
  if(!d){
    return S.debutMonteesPour
      ? h('div',{className:'fab-field'}, h('div',{className:'fab-field-hint'},'Lecture de la fiche technique…'))
      : null;
  }
  if(!(d.natures||[]).length) return null;
  const blocs = [];
  d.natures.forEach(n => (n.lignes||[]).forEach(l => blocs.push(debutOutilLigne(n, l))));
  if(S._debutOutilFocus){
    const cible = 'debut-outil-q-'+S._debutOutilFocus.replace(/[^a-z0-9_-]/gi,'_');
    S._debutOutilFocus = null;
    // Après le focus que la fenêtre pose sur le compteur.
    requestAnimationFrame(()=>{ const el = document.getElementById(cible); if(el) el.focus(); });
  }
  return h('div',{className:'fab-field'},
    h('label',null, d.natures.length === 1 ? d.natures[0].label+' montée' : 'Outils montés'),
    h('div',{className:'fab-field-hint'},
      d.fiche ? 'D\'après la fiche '+d.fiche.reference+'. Confirmez, ou changez si ce n\'est pas celle-là.'
              : 'Aucune fiche technique trouvée pour ce dossier.'),
    blocs);
}

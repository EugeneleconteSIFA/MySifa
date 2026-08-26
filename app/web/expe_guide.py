"""MyExpé — guide in-app de l'onglet « Devis transporteurs ».

Contenu seul : le moteur est `static/mysifa_guides.js`, partagé avec MyQualité,
l'ERP et les plannings. Ce module ne fournit que le dictionnaire d'étapes, les
bullets par service et la fonction d'amorçage — rien à brancher côté backend,
la table `user_guide_progress` et les routes `/api/guides/*` existent déjà.

Le guide vit dans son propre fichier plutôt que dans `expe_assets.py` : ce
dernier passe déjà 6 000 lignes, et un guide se relit plus souvent qu'il ne se
modifie. Les deux n'ont pas le même rythme de vie.
"""

# Les illustrations sont des mini-mockups FIDÈLES de l'écran, pas des icônes :
# on doit reconnaître le composant réel. Couleurs exclusivement prises dans les
# variables du design system, pour qu'elles suivent le thème de l'utilisateur.
EXPE_DEVIS_GUIDE_JS = r"""
// ══════════════════════════════════════════════════════════════════
// Guide in-app — MyExpé, onglet Devis transporteurs
// (moteur partagé : /static/mysifa_guides.js)
// ══════════════════════════════════════════════════════════════════

const EXPE_DEVIS_TACHES_PAR_SERVICE = {
  expedition: [
    'Lancer une consultation dès qu\'un départ sort de la grille tarifaire.',
    'Saisir les réponses arrivées par email pour que le comparatif soit complet.',
    'Relancer les transporteurs silencieux avant la date limite.',
    'Retenir l\'offre choisie : le départ est créé et le transporteur prévenu.'
  ],
  administration: [
    'Vérifier qu\'une affaire a bien été mise en concurrence avant de la facturer.',
    'Retrouver le prix retenu et le comparatif imprimable d\'un départ passé.',
    'Contrôler la pièce jointe envoyée au transporteur retenu.'
  ],
  direction: [
    'Voir combien de transporteurs répondent réellement, et lesquels ignorent nos demandes.',
    'Comparer l\'écart entre le moins-disant et le retenu sur une consultation.',
    'Suivre le taux de réponse pour arbitrer le panel de transporteurs.'
  ]
};

function _expeDevisBullets(role){
  const bloc=(titre,items)=>'<div class="mguide-svc"><div class="mguide-svc-hd">'+
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>'+
    titre+'</div><ul class="mguide-svc-list">'+items.map(x=>'<li>'+x+'</li>').join('')+'</ul></div>';
  let out='<div class="mguide-tasks">';
  if(role==='superadmin'||role==='direction'){
    out+=bloc('Expéditions',EXPE_DEVIS_TACHES_PAR_SERVICE.expedition);
    out+=bloc('Administration',EXPE_DEVIS_TACHES_PAR_SERVICE.administration);
    out+=bloc('Direction',EXPE_DEVIS_TACHES_PAR_SERVICE.direction);
  }else if(role==='administration'||role==='administration_ventes'||role==='administration_technique'){
    out+=bloc('Ce que vous avez à faire ici',EXPE_DEVIS_TACHES_PAR_SERVICE.administration);
  }else{
    out+=bloc('Ce que vous avez à faire ici',EXPE_DEVIS_TACHES_PAR_SERVICE.expedition);
  }
  return out+'</div>';
}

const EXPE_GUIDES = {
  'expe-devis': { steps: [

    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>',
      title: 'Devis transporteurs',
      body: '<p>Cet onglet sert à mettre plusieurs transporteurs en concurrence sur un même envoi. On décrit la marchandise une fois, on interroge tout le panel d\'un coup, et les réponses reviennent dans un <strong>comparatif unique</strong>.</p><p>Chaque transporteur reçoit un lien vers un <span class="mguide-tag">portail</span> où il saisit son prix lui-même. Ceux qui préfèrent répondre par email, on saisit leur réponse à leur place — le comparatif ne fait pas la différence.</p>',
      extra: '__BULLETS__'
    },

    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>',
      title: 'Créer une demande en trois écrans',
      body: '<p><span class="mguide-hl">Nouvelle demande</span> ouvre un formulaire en trois temps : le <strong>général</strong> (client, code postal, poids, palettes), les <strong>détails</strong> (type d\'envoi, palette, date limite, contraintes, pièce jointe), puis les <strong>transporteurs</strong>.</p><p>Seuls le client et le code postal sont obligatoires. Le fil des étapes, en haut, permet de revenir corriger — sans repasser par tout le formulaire.</p>',
      illu: '<svg viewBox="0 0 340 150" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="6" y="6" width="328" height="138" rx="10" fill="var(--card)" stroke="var(--border)"/><text x="18" y="26" font-size="9.5" fill="var(--text)" font-weight="800">Nouvelle demande de devis</text><rect x="18" y="36" width="86" height="20" rx="7" fill="var(--accent-bg)" stroke="var(--accent)"/><circle cx="31" cy="46" r="7" fill="var(--accent)"/><text x="31" y="49" font-size="7.5" fill="#fff" text-anchor="middle" font-weight="700">1</text><text x="46" y="49" font-size="8" fill="var(--accent)" font-weight="700">Général</text><line x1="108" y1="46" x2="118" y2="46" stroke="var(--border)"/><rect x="122" y="36" width="82" height="20" rx="7" fill="var(--bg)" stroke="var(--border)"/><circle cx="135" cy="46" r="7" fill="var(--border)"/><text x="135" y="49" font-size="7.5" fill="var(--text2)" text-anchor="middle" font-weight="700">2</text><text x="149" y="49" font-size="8" fill="var(--muted)" font-weight="700">Détails</text><line x1="208" y1="46" x2="218" y2="46" stroke="var(--border)"/><rect x="222" y="36" width="100" height="20" rx="7" fill="var(--bg)" stroke="var(--border)"/><circle cx="235" cy="46" r="7" fill="var(--border)"/><text x="235" y="49" font-size="7.5" fill="var(--text2)" text-anchor="middle" font-weight="700">3</text><text x="249" y="49" font-size="8" fill="var(--muted)" font-weight="700">Transporteurs</text><text x="18" y="76" font-size="7" fill="var(--text2)" font-weight="700">CLIENT *</text><rect x="18" y="81" width="304" height="17" rx="6" fill="var(--bg)" stroke="var(--accent)"/><text x="26" y="93" font-size="8" fill="var(--text)">LIDL</text><text x="18" y="114" font-size="7" fill="var(--text2)" font-weight="700">CP DESTINATION *</text><rect x="18" y="119" width="96" height="17" rx="6" fill="var(--bg)" stroke="var(--border)"/><text x="26" y="131" font-size="8" fill="var(--text)">31200</text><text x="126" y="114" font-size="7" fill="var(--text2)" font-weight="700">POIDS (KG)</text><rect x="126" y="119" width="94" height="17" rx="6" fill="var(--bg)" stroke="var(--border)"/><text x="134" y="131" font-size="8" fill="var(--text)">10 000</text><text x="230" y="114" font-size="7" fill="var(--text2)" font-weight="700">PALETTES</text><rect x="230" y="119" width="92" height="17" rx="6" fill="var(--bg)" stroke="var(--border)"/><text x="238" y="131" font-size="8" fill="var(--text)">12</text></svg>'
    },

    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4z"/></svg>',
      title: 'Qui reçoit, et de quelle adresse',
      body: '<p>Le troisième écran liste les transporteurs actifs — tous cochés d\'entrée — et les prospects, décochés. <span class="mguide-hl">Créer et envoyer</span> part immédiatement ; <span class="mguide-hl">Créer sans envoyer</span> met la demande de côté, les emails partiront depuis son détail.</p><p>Les emails partent toujours de la boîte du <strong>service expéditions</strong>, jamais de votre adresse personnelle : vous êtes en copie, et les réponses reviennent sur la boîte partagée même si vous êtes absent.</p>',
      illu: '<svg viewBox="0 0 340 150" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="6" y="6" width="328" height="138" rx="10" fill="var(--card)" stroke="var(--border)"/><rect x="16" y="16" width="308" height="20" rx="7" fill="var(--accent-bg)"/><rect x="24" y="21" width="10" height="10" rx="2.5" fill="var(--accent)"/><path d="M26.5 26l2 2 3.5-3.5" stroke="#fff" stroke-width="1.4" fill="none"/><text x="42" y="30" font-size="8" fill="var(--text)" font-weight="700">Tout désélectionner</text><text x="316" y="30" font-size="7.5" fill="var(--muted)" text-anchor="end">8 destinataires</text><rect x="24" y="47" width="10" height="10" rx="2.5" fill="var(--accent)"/><path d="M26.5 52l2 2 3.5-3.5" stroke="#fff" stroke-width="1.4" fill="none"/><text x="42" y="56" font-size="8.5" fill="var(--text)" font-weight="700">Coquelle</text><text x="150" y="56" font-size="8" fill="var(--muted)">contact@coquelle.fr</text><line x1="16" y1="64" x2="324" y2="64" stroke="var(--border)"/><rect x="24" y="71" width="10" height="10" rx="2.5" fill="var(--accent)"/><path d="M26.5 76l2 2 3.5-3.5" stroke="#fff" stroke-width="1.4" fill="none"/><text x="42" y="80" font-size="8.5" fill="var(--text)" font-weight="700">Geodis</text><text x="150" y="80" font-size="8" fill="var(--muted)">tarifs@geodis.com</text><line x1="16" y1="88" x2="324" y2="88" stroke="var(--border)"/><rect x="24" y="95" width="10" height="10" rx="2.5" fill="var(--bg)" stroke="var(--border)"/><text x="42" y="104" font-size="8.5" fill="var(--text)" font-weight="700">TRANSBENELUX</text><text x="150" y="104" font-size="8" fill="var(--muted)">devis@transbenelux.be</text><text x="276" y="104" font-size="7" fill="var(--warn)" font-weight="700">prospect</text><rect x="16" y="116" width="180" height="20" rx="7" fill="var(--bg)" stroke="var(--border)"/><text x="106" y="130" font-size="8" fill="var(--text2)" text-anchor="middle">Créer sans envoyer</text><rect x="204" y="116" width="120" height="20" rx="7" fill="var(--accent)"/><text x="264" y="130" font-size="8" fill="#fff" text-anchor="middle" font-weight="700">Créer et envoyer</text></svg>'
    },

    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/><circle cx="8" cy="6" r="2" fill="var(--card)"/><circle cx="16" cy="12" r="2" fill="var(--card)"/></svg>',
      title: 'Le comparatif, et les réponses reçues par email',
      body: '<p>Une ligne par destinataire. Le <strong>meilleur prix</strong> et le <strong>meilleur délai</strong> sont mis en avant automatiquement. <span class="mguide-hl">Saisir réponse</span> enregistre ce qu\'un transporteur a répondu par mail, et reste disponible ensuite pour corriger.</p><p>Le prix est facultatif. Un transporteur qui écrit « je ne dessert pas cette zone » se note en cochant <span class="mguide-tag">Sans suite</span> : il sort du comparatif et cesse d\'être relancé, sans qu\'on lui invente un prix. La colonne <strong>Commentaire</strong> s\'édite d\'un clic, directement dans le tableau.</p>',
      illu: '<svg viewBox="0 0 340 150" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="6" y="6" width="328" height="138" rx="10" fill="var(--card)" stroke="var(--border)"/><rect x="6" y="6" width="328" height="20" rx="10" fill="var(--bg)"/><text x="18" y="20" font-size="7" fill="var(--muted)" font-weight="700">TRANSPORTEUR</text><text x="104" y="20" font-size="7" fill="var(--muted)" font-weight="700">STATUT</text><text x="160" y="20" font-size="7" fill="var(--muted)" font-weight="700">PRIX HT</text><text x="212" y="20" font-size="7" fill="var(--muted)" font-weight="700">DÉLAI</text><text x="256" y="20" font-size="7" fill="var(--muted)" font-weight="700">COMMENTAIRE</text><line x1="6" y1="26" x2="334" y2="26" stroke="var(--border)"/><text x="18" y="42" font-size="8.5" fill="var(--text)" font-weight="700">Coquelle</text><text x="104" y="42" font-size="8" fill="var(--accent)">Reçue</text><rect x="156" y="33" width="42" height="14" rx="5" fill="var(--accent-bg)"/><text x="177" y="43" font-size="8" fill="var(--accent)" text-anchor="middle" font-weight="800">412,00</text><text x="212" y="42" font-size="8" fill="var(--text)">J+2</text><text x="256" y="42" font-size="7.5" fill="var(--text2)">hayon inclus</text><line x1="6" y1="50" x2="334" y2="50" stroke="var(--border)"/><text x="18" y="66" font-size="8.5" fill="var(--text)" font-weight="700">Geodis</text><text x="104" y="66" font-size="8" fill="var(--accent)">Reçue</text><text x="177" y="66" font-size="8" fill="var(--text)" text-anchor="middle">468,50</text><rect x="208" y="57" width="28" height="14" rx="5" fill="var(--accent-bg)"/><text x="222" y="67" font-size="8" fill="var(--accent)" text-anchor="middle" font-weight="800">J+1</text><text x="256" y="66" font-size="7.5" fill="var(--text2)">—</text><line x1="6" y1="74" x2="334" y2="74" stroke="var(--border)"/><text x="18" y="90" font-size="8.5" fill="var(--muted)" font-weight="700">LEDY</text><text x="104" y="90" font-size="8" fill="var(--muted)">Sans suite</text><text x="177" y="90" font-size="8" fill="var(--muted)" text-anchor="middle">—</text><text x="212" y="90" font-size="8" fill="var(--muted)">—</text><text x="256" y="90" font-size="7.5" fill="var(--text2)">ne dessert pas le 31</text><line x1="6" y1="98" x2="334" y2="98" stroke="var(--border)"/><text x="18" y="114" font-size="8.5" fill="var(--text)" font-weight="700">GONDRAND</text><text x="104" y="114" font-size="8" fill="var(--warn)">Ouverte</text><text x="177" y="114" font-size="8" fill="var(--muted)" text-anchor="middle">—</text><text x="212" y="114" font-size="8" fill="var(--muted)">—</text><rect x="254" y="105" width="72" height="15" rx="5" fill="var(--bg)" stroke="var(--accent)"/><text x="260" y="116" font-size="7.5" fill="var(--muted)" font-style="italic">+ Commentaire</text><rect x="18" y="126" width="70" height="14" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="53" y="136" font-size="7.5" fill="var(--text2)" text-anchor="middle">Saisir réponse</text></svg>'
    },

    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>',
      title: 'Ce que vaut le suivi d\'engagement',
      body: '<p>La colonne <strong>Engagement</strong> dit ce qu\'on sait du transporteur. <span class="mguide-tag">Portail</span> est une certitude : il a ouvert la page. <span class="mguide-tag">Email ouvert</span> n\'est qu\'un indice — Outlook bloque les images par défaut, donc beaucoup de vraies lectures ne s\'y voient pas.</p><p>Vous êtes en copie de l\'email : votre propre relecture déclenche le même compteur. Elle est écartée quand on la reconnaît, et affichée à part (<span class="mguide-tag">+2 internes</span>). Sinon, l\'icône <strong>activité</strong> ouvre la chronologie où un bouton <span class="mguide-hl">C\'était nous</span> corrige la ligne.</p>',
      illu: '<svg viewBox="0 0 340 150" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="6" y="6" width="328" height="138" rx="10" fill="var(--card)" stroke="var(--border)"/><text x="18" y="24" font-size="9" fill="var(--text)" font-weight="800">Suivi transporteur</text><text x="18" y="36" font-size="7.5" fill="var(--muted)">Coquelle · contact@coquelle.fr</text><circle cx="24" cy="54" r="4" fill="var(--accent)"/><text x="38" y="52" font-size="8.5" fill="var(--text)" font-weight="700">Portail consulté</text><text x="38" y="62" font-size="7" fill="var(--muted)">2026-08-26T09:41 · portail</text><line x1="18" y1="70" x2="322" y2="70" stroke="var(--border)"/><circle cx="24" cy="86" r="4" fill="var(--accent)"/><text x="38" y="84" font-size="8.5" fill="var(--text)" font-weight="700">Email ouvert (demande de tarif)</text><text x="38" y="94" font-size="7" fill="var(--muted)">2026-08-26T08:12 · email · 92.154.13.4</text><rect x="38" y="99" width="62" height="14" rx="5" fill="var(--bg)" stroke="var(--border)"/><text x="69" y="109" font-size="7" fill="var(--text2)" text-anchor="middle" font-weight="700">C\'était nous</text><line x1="18" y1="120" x2="322" y2="120" stroke="var(--border)"/><circle cx="24" cy="134" r="4" fill="var(--muted)"/><text x="38" y="132" font-size="8.5" fill="var(--muted)" font-weight="700">Email ouvert</text><text x="120" y="132" font-size="7" fill="var(--warn)">Écarté — ouverture interne SIFA</text></svg>'
    },

    {
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d="M20.5 6.5 9.5 17.5 4 12"/></svg>',
      title: 'Relancer, puis retenir',
      body: '<p>Sur une ligne restée muette, l\'icône <strong>enveloppe</strong> envoie une relance — avec un message libre en tête si besoin. Le nombre de relances déjà parties est rappelé au survol, pour ne pas harceler un transporteur qui a simplement dit non ailleurs.</p><p><span class="mguide-hl">Retenir</span> fait trois choses d\'un coup : le transporteur reçoit une confirmation avec le récapitulatif de la mission, un <strong>départ pré-rempli</strong> est créé dans l\'onglet Départs, et la demande passe en historique. Le comparatif reste imprimable après coup.</p>',
      illu: '<svg viewBox="0 0 340 150" xmlns="http://www.w3.org/2000/svg" font-family="Segoe UI"><rect x="10" y="24" width="92" height="46" rx="9" fill="var(--card)" stroke="var(--accent)"/><text x="56" y="44" font-size="8.5" fill="var(--accent)" text-anchor="middle" font-weight="800">Retenir</text><text x="56" y="58" font-size="7" fill="var(--accent)" text-anchor="middle" opacity=".8">Coquelle · 412,00</text><path d="M106 47 L138 32" stroke="var(--border)" stroke-width="1.6" marker-end="url(#ed)"/><path d="M106 47 L138 47" stroke="var(--border)" stroke-width="1.6" marker-end="url(#ed)"/><path d="M106 47 L138 62" stroke="var(--border)" stroke-width="1.6" marker-end="url(#ed)"/><defs><marker id="ed" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6z" fill="var(--border)"/></marker></defs><rect x="142" y="20" width="188" height="24" rx="8" fill="var(--bg)" stroke="var(--border)"/><text x="152" y="35" font-size="8" fill="var(--text)" font-weight="700">Email de confirmation au transporteur</text><rect x="142" y="50" width="188" height="24" rx="8" fill="var(--bg)" stroke="var(--border)"/><text x="152" y="65" font-size="8" fill="var(--text)" font-weight="700">Départ pré-rempli dans MyExpé</text><rect x="142" y="80" width="188" height="24" rx="8" fill="var(--bg)" stroke="var(--border)"/><text x="152" y="95" font-size="8" fill="var(--text)" font-weight="700">Demande classée en historique</text><rect x="10" y="110" width="320" height="26" rx="8" fill="var(--card)" stroke="var(--border)"/><text x="22" y="126" font-size="8" fill="var(--text2)">Les autres lignes passent en </text><text x="152" y="126" font-size="8" fill="var(--muted)" font-weight="700">Refusée</text><text x="196" y="126" font-size="8" fill="var(--text2)">— sauf les « sans suite ».</text></svg>'
    }
  ]}
};

// Amorçage : appelé à chaque arrivée sur l'onglet Devis. Les appels répétés
// sont sans effet (le moteur ignore un guide déjà ouvert dans la session), ce
// qui évite de devoir suivre nous-mêmes l'état d'initialisation.
let _expeGuideBooted=false;
function expeDevisInitGuide(){
  try{
    if(!window.MySifaGuides)return;
    const role=(S.user&&S.user.role)||'';
    MySifaGuides.configure({role});
    // Les bullets de la 1re étape dépendent du rôle : on les injecte ici, une
    // fois l'utilisateur connu, plutôt que de figer le texte au chargement.
    const g=JSON.parse(JSON.stringify(EXPE_GUIDES));
    g['expe-devis'].steps[0].extra=_expeDevisBullets(role);
    MySifaGuides.registerMany(g);
    const apres=()=>{
      const slot=document.getElementById('expe-devis-guide-slot');
      if(slot&&typeof MySifaGuides.bookBtn==='function')slot.innerHTML=MySifaGuides.bookBtn('expe-devis');
      MySifaGuides.autoOpen('expe-devis');
    };
    if(_expeGuideBooted){apres();return;}
    _expeGuideBooted=true;
    MySifaGuides.boot().then(apres);
  }catch(e){}
}
"""

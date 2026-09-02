/*
 * Points de production : ce que le rendu de l'onglet Reunions doit produire.
 *
 * `static/mysifa_reunions.js` rend des chaines. Une regression y passe en
 * silence : personne ne leve d'exception si une moitie de ligne manque. C'est
 * exactement ce qui etait arrive au module Retour de prod — un mot parasite au
 * milieu d'une concatenation avait passe `node --check` sans broncher, et
 * l'insertion automatique de point-virgule coupait le `return` en deux. Seul un
 * appel reel le montre.
 *
 * Quatre familles de cas :
 *   - a vide, rien ne doit ressembler a un ecran plein ;
 *   - chaque fonction rend la ligne ENTIERE, pas son debut ;
 *   - aucune prose utilisateur ne sort sans echappement ;
 *   - le document imprime porte l'identite de la reunion, pas la page.
 *
 * Lancer : node tests/test_reunions_rendu.js
 */

const path = require("path");

global.window = global;
// L'ordre compte : le module resout MySifaRetourProd au montage, mais ses
// fonctions de rendu pur s'en servent pour echapper et formater les dates.
require(path.join(__dirname, "..", "static", "mysifa_retour_prod.js"));
require(path.join(__dirname, "..", "static", "mysifa_reunions.js"));
const M = global.MySifaReunions;

const ECHECS = [];
function verifier(cas, cond) {
  if (cond) { console.log("  ok     " + cas); }
  else { ECHECS.push(cas); console.log("  ECHEC  " + cas); }
}

const piegeNom = '<img src=x onerror="alert(1)">';

const REUNION = {
  id: 12, titre: "31/08/2026", statut: "ouverte", ouverte: true,
  ouverte_par: "Marc", ouverte_le: "2026-08-31T08:05:00",
  date_debut: "2026-08-28", date_fin: "2026-08-28",
  machine: "Cohesio 1", machines: ["Cohesio 1"],
  notes: "Tension a baisser sur D-501",
  participants: [{ nom: "Marc" }, { nom: "Sophie" }],
  actions: [
    { id: 1, texte: "Regler la tension", responsable: "Marc",
      echeance: "2026-09-02", fait: false },
    { id: 2, texte: "Commander le film", responsable: "", echeance: "", fait: true }
  ]
};

console.log("\n1. A vide, rien ne doit ressembler a un ecran plein");
verifier("liste non chargee : chargement", M.rendreListe(null).includes("Chargement"));
verifier("liste vide : message explicite",
         M.rendreListe([]).includes("Aucune r&eacute;union enregistr&eacute;e"));
verifier("liste vide : aucun tableau", !M.rendreListe([]).includes("<table"));
verifier("reunion absente : chargement", M.rendreReunion(null, null, {}).includes("Chargement"));
verifier("aucune action : message", M.rendreActions([]).includes("Aucune action"));
verifier("actions indefinies : message", M.rendreActions(undefined).includes("Aucune action"));
verifier("document sans reunion : vide", M.rendreDocument(null, null, "") === "");

console.log("\n2. La liste rend la ligne entiere");
const liste = M.rendreListe([{
  id: 12, titre: "31/08/2026", date_debut: "2026-08-28", date_fin: "2026-08-28",
  machine: "Cohesio 1", ouverte_par: "Marc", a_des_notes: true,
  participants: ["Marc", "Sophie"], nb_actions: 2, actions_restantes: 1, ouverte: true
}, {
  id: 11, titre: "27/08/2026", date_debut: "2026-08-25", date_fin: "2026-08-26",
  machine: "", ouverte_par: "Sophie", a_des_notes: false,
  participants: [], nb_actions: 3, actions_restantes: 0, ouverte: false
}]);
// La colonne « Actions a mener » : le detail quand l'API le sert, le compteur
// sinon. Les deux lignes ci-dessus n'ont que le compteur, celle-ci le detail.
const listeDetail = M.rendreListe([{
  id: 20, titre: "02/09/2026", date_debut: "2026-09-01", date_fin: "2026-09-02",
  machine: "", ouverte_par: "Marc", a_des_notes: true, participants: ["Marc"],
  nb_actions: 5, actions_restantes: 3, ouverte: false,
  actions: [
    { id: 1, texte: "Regler la tension", responsable: "Marc",
      echeance: "2026-09-05", fait: false },
    { id: 2, texte: "Commander le film", responsable: "", echeance: "", fait: true },
    { id: 3, texte: "Voir le calage", responsable: "Sophie", echeance: "", fait: false },
    { id: 4, texte: "Rappeler le client", responsable: "", echeance: "", fait: false },
    { id: 5, texte: "Nettoyer le poste", responsable: "", echeance: "", fait: true }
  ]
}]);
verifier("liste : identifiant de ligne", liste.includes('data-id="12"'));
verifier("liste : titre", liste.includes("31/08/2026"));
verifier("liste : jour unique sans fleche",
         liste.includes(">28/08/2026<") && !liste.includes("28/08/2026 → 28/08/2026"));
verifier("liste : plage avec fleche", liste.includes("25/08/2026 → 26/08/2026"));
verifier("liste : perimetre en sous-titre", liste.includes("Cohesio 1"));
verifier("liste : sans machine, tout l'atelier est dit",
         liste.includes("Toutes les machines"));
verifier("liste : presence de notes", liste.includes("notes") && liste.includes("sans notes"));
verifier("liste : participants", liste.includes("Marc, Sophie"));
verifier("liste : participants absents", liste.includes("—"));
verifier("liste : sans detail, le compteur reste", liste.includes("1 &agrave; faire"));
verifier("liste : sans detail, actions toutes faites", liste.includes("3 faites"));
verifier("liste : la reunion en cours est signalee", liste.includes(">en cours<"));
verifier("liste : plus de colonne Etat", liste.indexOf("&Eacute;tat") === -1);
verifier("liste : une reunion close ne porte pas de pastille d'etat",
         liste.indexOf(">close<") === -1);
verifier("liste : cinq colonnes", liste.split("<th>").length - 1 === 5);
verifier("liste : tableau ferme", liste.trim().endsWith("</table>"));

console.log("\n2 ter. La colonne dit les actions, pas leur nombre");
verifier("actions a mener : intitule de colonne",
         liste.includes("Actions &agrave; mener"));
verifier("actions a mener : le texte de l'action est la",
         listeDetail.includes("Regler la tension"));
verifier("actions a mener : responsable et echeance",
         listeDetail.includes("Marc · 05/09/2026"));
verifier("actions a mener : ce qui reste a faire passe devant",
         listeDetail.includes("Voir le calage") && listeDetail.includes("Rappeler le client")
         && listeDetail.indexOf("Commander le film") === -1);
verifier("actions a mener : trois lignes au plus",
         listeDetail.split('<div class="reu-todo"').length - 1 === 3);
verifier("actions a mener : le reste est compte",
         listeDetail.includes("+ 2 autres"));
verifier("actions a mener : une faite est marquee",
         M.rendreListe([{ id: 21, titre: "x", date_debut: "2026-09-01",
           date_fin: "2026-09-01", ouverte_par: "Marc", participants: [],
           nb_actions: 1, actions_restantes: 0, ouverte: false,
           actions: [{ id: 9, texte: "Fini", responsable: "", echeance: "", fait: true }]
         }]).includes('class="reu-todo fait"'));
verifier("actions a mener : sans action, un tiret",
         M.rendreListe([{ id: 22, titre: "x", date_debut: "2026-09-01",
           date_fin: "2026-09-01", ouverte_par: "Marc", participants: [],
           nb_actions: 0, ouverte: false, actions: [] }]).includes("&mdash;"));
verifier("actions a mener : texte echappe",
         !M.rendreListe([{ id: 23, titre: "x", date_debut: "2026-09-01",
           date_fin: "2026-09-01", ouverte_par: "Marc", participants: [],
           nb_actions: 1, actions_restantes: 1, ouverte: false,
           actions: [{ id: 9, texte: piegeNom, responsable: piegeNom, echeance: "",
                       fait: false }] }]).includes("<img src=x"));

console.log("\n2 bis. Chaque ligne porte sa corbeille");
verifier("corbeille : bouton par ligne",
         liste.split('data-suppr-reunion="').length === 3);
verifier("corbeille : identifiant porte", liste.includes('data-suppr-reunion="12"'));
verifier("corbeille : titre porte pour la confirmation",
         liste.includes('data-suppr-titre="31/08/2026"'));
verifier("corbeille : intitule accessible", liste.includes("aria-label=\"Supprimer"));
verifier("corbeille : icone et non emoji",
         liste.includes("<svg") && !/[\u{1F300}-\u{1FAFF}]/u.test(liste));
verifier("corbeille : derniere cellule de la ligne",
         liste.indexOf("reu-td-sup") > liste.indexOf("reu-td-act"));
verifier("corbeille : titre echappe dans l'attribut",
         !M.rendreListe([{ id: 1, titre: '" onfocus="alert(1)', date_debut: "2026-08-28",
           date_fin: "2026-08-28", ouverte_par: "x", participants: [], nb_actions: 0,
           ouverte: false }]).includes('data-suppr-titre="" onfocus='));

console.log("\n3. La reunion rend l'ecran entier");
const ecran = M.rendreReunion(REUNION, { machines: ["Cohesio 1", "Cohesio 2"] },
                              { notes: "Enregistre a 09:12" });
verifier("reunion : titre dans le champ", ecran.includes('value="31/08/2026"'));
verifier("reunion : auteur et date d'ouverture",
         ecran.includes("Ouverte par Marc") && ecran.includes("31/08/2026"));
verifier("reunion : bornes de periode",
         ecran.includes('id="reu-du" value="2026-08-28"') &&
         ecran.includes('id="reu-au" value="2026-08-28"'));
verifier("reunion : le perimetre est dans l'en-tete", ecran.includes("reu-mach"));
verifier("reunion : la machine retenue est cochee",
         ecran.includes('data-mach="Cohesio 1" aria-pressed="true"'));
verifier("reunion : l'autre ne l'est pas",
         ecran.includes('data-mach="Cohesio 2" aria-pressed="false"'));
verifier("reunion : bouton imprimer", ecran.includes('data-r="imprimer"'));
verifier("reunion : bouton plein ecran", ecran.includes('data-r="plein"')
         && ecran.includes("Plein &eacute;cran"));
verifier("reunion : en plein ecran, le bouton propose d'en sortir",
         M.rendreReunion(REUNION, null, { plein: true })
          .includes("Quitter le plein &eacute;cran"));
verifier("reunion : clore quand ouverte", ecran.includes("Clore la r&eacute;union"));
verifier("reunion : rouvrir quand close",
         M.rendreReunion(Object.assign({}, REUNION, { ouverte: false, statut: "close",
           close_le: "2026-08-31T10:00:00" }), null, {})
          .includes("Rouvrir la r&eacute;union"));
verifier("reunion : date de cloture affichee",
         M.rendreReunion(Object.assign({}, REUNION, { ouverte: false, statut: "close",
           close_le: "2026-08-31T10:00:00" }), null, {}).includes("close le 31/08/2026"));
verifier("reunion : contenant des chiffres", ecran.includes('id="reu-prod"'));
verifier("reunion : colonne de notes", ecran.includes('id="reu-notes"'));
verifier("reunion : etat d'enregistrement", ecran.includes("Enregistre a 09:12"));
verifier("reunion : formulaire d'action", ecran.includes('data-r="ajout-action"'));
verifier("reunion : bloc ferme", ecran.trim().endsWith("</div>"));
verifier("reunion : machines absentes ne cassent rien",
         M.rendreReunion(REUNION, null, {}).includes("data-mach-tout"));

console.log("\n3 ter. Le perimetre : une, plusieurs ou toutes les machines");
const MACHINES = ["Cohésio 1", "Cohésio 2", "Repiquage"];
const mTout = M.rendreMachines(MACHINES, []);
verifier("perimetre : « Toutes » actif quand rien n'est retenu",
         mTout.includes('data-mach-tout="1" aria-pressed="true"'));
verifier("perimetre : les trois machines proposees",
         mTout.split("data-mach=").length - 1 === 3);
verifier("perimetre : aucune cochee", mTout.indexOf('data-mach="Cohésio 1" aria-pressed="true"') === -1);
const mDeux = M.rendreMachines(MACHINES, ["Cohésio 1", "Repiquage"]);
verifier("perimetre : deux cochees",
         mDeux.split('aria-pressed="true"').length - 1 === 2);
verifier("perimetre : la bonne paire",
         mDeux.includes('data-mach="Cohésio 1" aria-pressed="true"')
         && mDeux.includes('data-mach="Repiquage" aria-pressed="true"'));
verifier("perimetre : « Toutes » s'eteint",
         mDeux.includes('data-mach-tout="1" aria-pressed="false"'));
verifier("perimetre : classe active posee", mDeux.includes('class="reu-mach-p actif"'));
verifier("perimetre : casse et accent ignores a la comparaison",
         M.rendreMachines(MACHINES, ["cohésio 1"])
          .includes('data-mach="Cohésio 1" aria-pressed="true"'));
verifier("perimetre : machine inconnue n'invente rien",
         M.rendreMachines(MACHINES, ["Bunsch"]).split("data-mach=").length - 1 === 3);
verifier("perimetre : sans machines disponibles, « Toutes » subsiste",
         M.rendreMachines([], []).includes("data-mach-tout"));
verifier("perimetre : nom echappe",
         !M.rendreMachines(['<img src=x onerror="alert(1)">'], []).includes("<img src=x"));

// Un poste hors production reste dans le selecteur, en retrait : on ne cache
// pas une machine, on arrete de la compter par defaut.
const mHors = M.rendreMachines(MACHINES, [], ["Repiquage"]);
verifier("hors prod : la pastille reste", mHors.includes('data-mach="Repiquage"'));
verifier("hors prod : elle est marquee",
         mHors.includes('class="reu-mach-p hors"') && mHors.includes("<em>hors prod</em>"));
verifier("hors prod : elle n'est pas cochee",
         mHors.includes('data-mach="Repiquage" title="Poste hors production'
                        + ' : non compt&eacute; par d&eacute;faut" aria-pressed="false"'));
verifier("hors prod : les autres ne sont pas marquees",
         mHors.split("reu-mach-p hors").length - 1 === 1);
verifier("hors prod : cochee explicitement, elle reste marquee mais active",
         M.rendreMachines(MACHINES, ["Repiquage"], ["Repiquage"])
          .includes('class="reu-mach-p actif hors"'));
verifier("hors prod : sans liste, rien n'est marque",
         M.rendreMachines(MACHINES, []).indexOf("hors prod") === -1);
verifier("hors prod : « Toutes » dit ce qu'elle couvre",
         mHors.includes("Toutes les machines de production"));

console.log("\n3 bis. Les participants s'ajoutent depuis une recherche");
const ANNUAIRE = [{ id: 1, nom: "Grégory Desreumaux" }, { id: 2, nom: "Manuel Lesaffre" },
                  { id: 3, nom: "Marc Dubois" }, { id: 4, nom: "Sophie Leroy" }];
const PRESENTS = [{ nom: "Marc Dubois" }];

const pVide = M.rendreParticipants([], ANNUAIRE, "");
verifier("participants : aucun present", pVide.includes("Personne pour l'instant"));
verifier("participants : champ de recherche", pVide.includes('id="reu-p-q"'));
verifier("participants : aucune suggestion sans frappe",
         pVide.indexOf("data-part-add") === -1);

const pAvec = M.rendreParticipants(PRESENTS, ANNUAIRE, "");
verifier("participants : pastille du present", pAvec.includes("Marc Dubois"));
verifier("participants : retrait possible", pAvec.includes('data-part-sup="Marc Dubois"'));

const pRech = M.rendreParticipants(PRESENTS, ANNUAIRE, "man");
verifier("recherche : trouve au milieu du nom",
         pRech.includes('data-part-add="Manuel Lesaffre"'));
verifier("recherche : ecarte ce qui ne correspond pas",
         pRech.indexOf("Sophie Leroy") === -1);
verifier("recherche : ecarte les deja presents",
         M.rendreParticipants(PRESENTS, ANNUAIRE, "marc")
          .indexOf('data-part-add="Marc Dubois"') === -1);
verifier("recherche : sans accent trouve avec accent",
         M.rendreParticipants([], ANNUAIRE, "gregory")
          .includes('data-part-add="Grégory Desreumaux"'));
verifier("recherche : casse ignoree",
         M.rendreParticipants([], ANNUAIRE, "SOPHIE").includes("Sophie Leroy"));
verifier("recherche : nom hors annuaire proposable",
         M.rendreParticipants([], ANNUAIRE, "Client Nestle").includes("hors annuaire"));
verifier("recherche : pas de doublon hors annuaire quand le nom existe",
         M.rendreParticipants([], ANNUAIRE, "Marc Dubois").indexOf("hors annuaire") === -1);
verifier("recherche : deja present, rien a proposer",
         M.rendreParticipants(PRESENTS, ANNUAIRE, "Marc Dubois")
          .includes("D&eacute;j&agrave; dans la r&eacute;union"));
verifier("recherche : au plus huit suggestions",
         M.rendreParticipants([], Array.from({ length: 20 },
           (_, i) => ({ id: i, nom: "Dupont " + i })), "dupont")
          .split("data-part-add").length - 1 === 8);
verifier("recherche : les debuts de mot passent devant",
         (function(){
           var h = M.rendreParticipants([], ANNUAIRE.concat([{ id: 5, nom: "Jean-Marie Petit" }]), "ma");
           return h.indexOf('data-part-add="Manuel Lesaffre"')
                < h.indexOf('data-part-add="Grégory Desreumaux"');
         })());
verifier("recherche : trait d'union coupe les mots",
         M.rendreParticipants([], [{ id: 1, nom: "Jean-Marie Petit" }], "marie")
          .includes('data-part-add="Jean-Marie Petit"'));
verifier("recherche : nom de famille atteignable",
         M.rendreParticipants([], ANNUAIRE, "lesaf")
          .includes('data-part-add="Manuel Lesaffre"'));
verifier("recherche : annuaire absent ne casse rien",
         M.rendreParticipants(PRESENTS, null, "man").includes("Marc Dubois"));
verifier("recherche : la frappe est reaffichee dans le champ",
         M.rendreParticipants([], ANNUAIRE, "man").includes('value="man"'));
verifier("participants : nom echappe dans la pastille",
         !M.rendreParticipants([{ nom: piegeNom }], [], "").includes("<img src=x"));
verifier("participants : nom echappe dans l'attribut de retrait",
         !M.rendreParticipants([{ nom: '" onfocus="x' }], [], "")
           .includes('data-part-sup="" onfocus='));
verifier("recherche : frappe echappee dans la proposition hors annuaire",
         !M.rendreParticipants([], [], piegeNom).includes("<img src=x"));
verifier("reunion : le bloc participants est dans la colonne",
         ecran.includes('id="reu-participants"') &&
         ecran.indexOf('id="reu-participants"') < ecran.indexOf('id="reu-notes"'));

console.log("\n4. Les actions rendent la ligne entiere");
const actions = M.rendreActions(REUNION.actions);
verifier("action : texte", actions.includes("Regler la tension"));
verifier("action : responsable", actions.includes("Marc"));
verifier("action : echeance formatee", actions.includes("pour le 02/09/2026"));
verifier("action : case a cocher", actions.includes('data-coche="1"'));
verifier("action : faite cochee", actions.includes('data-coche="2" checked'));
verifier("action : classe fait", actions.includes('class="reu-act fait"'));
verifier("action : suppression", actions.includes('data-sup="1"'));
verifier("action sans responsable ni echeance : pas de meta vide",
         M.rendreActions([{ id: 3, texte: "Voir", responsable: "", echeance: "", fait: false }])
          .indexOf("reu-a-meta") === -1);

console.log("\n5. Aucune prose utilisateur ne sort sans echappement");
const piege = '<img src=x onerror="alert(1)">';
const listeP = M.rendreListe([{ id: 1, titre: piege, date_debut: "2026-08-28",
  date_fin: "2026-08-28", ouverte_par: piege, participants: [piege],
  machine: piege, nb_actions: 0, ouverte: false }]);
verifier("liste : titre echappe", !listeP.includes("<img src=x"));
verifier("liste : auteur echappe", listeP.includes("&lt;img"));
verifier("liste : machine echappee", listeP.split("&lt;img").length > 3);
verifier("liste : titre echappe jusque dans la corbeille",
         !listeP.includes('data-suppr-titre="<img'));
const ecranP = M.rendreReunion(Object.assign({}, REUNION,
  { titre: '" onfocus="alert(1)', ouverte_par: piege }), { machines: [piege] }, {});
verifier("reunion : titre echappe dans l'attribut", !ecranP.includes('" onfocus='));
verifier("reunion : auteur echappe", !ecranP.includes("<img src=x"));
verifier("reunion : machine echappee dans l'option", !ecranP.includes('value="<img'));
verifier("actions : texte echappe",
         !M.rendreActions([{ id: 1, texte: piege, fait: false }]).includes("<img src=x"));
verifier("actions : responsable echappe",
         !M.rendreActions([{ id: 1, texte: "x", responsable: piege, fait: false }])
           .includes("<img src=x"));

console.log("\n6. Le document imprime porte l'identite de la reunion");
const doc = M.rendreDocument(REUNION, null, "Tension a baisser sur D-501");
verifier("document : marque", doc.includes("MySifa &mdash; Point de production"));
verifier("document : titre", doc.includes("<h2>31/08/2026</h2>"));
verifier("document : periode analysee", doc.includes("28/08/2026"));
verifier("document : perimetre", doc.includes("Cohesio 1"));
verifier("document : plusieurs machines listees",
         M.rendreDocument(Object.assign({}, REUNION,
           { machines: ["Cohesio 1", "Repiquage"] }), null, "")
          .includes("Cohesio 1 · Repiquage"));
verifier("document : participants", doc.includes("Marc, Sophie"));
verifier("document : ouverte par", doc.includes("Ouverte par</b> Marc"));
verifier("document : etat en cours", doc.includes("<b>en cours</b>"));
verifier("document : notes en texte", doc.includes("Tension a baisser sur D-501"));
verifier("document : pas de textarea", !doc.includes("<textarea"));
verifier("document : actions listees",
         doc.includes("Regler la tension") && doc.includes("Commander le film"));
verifier("document : action faite marquee", doc.includes("reu-doc-act fait"));
verifier("document : notes vides tolerees",
         M.rendreDocument(REUNION, null, "").includes('class="reu-doc-notes"'));
verifier("document : sans participants",
         M.rendreDocument(Object.assign({}, REUNION, { participants: [] }), null, "")
          .includes("non renseign"));
verifier("document : toutes les machines",
         M.rendreDocument(Object.assign({}, REUNION, { machine: "", machines: [] }), null, "")
          .includes("toutes les machines"));
verifier("document : notes echappees",
         !M.rendreDocument(REUNION, null, piege).includes("<img src=x"));

console.log("\n" + "=".repeat(60));
if (ECHECS.length) {
  console.log(ECHECS.length + " echec(s) :");
  ECHECS.forEach(e => console.log("  - " + e));
  process.exit(1);
}
console.log("Tous les cas passent.");

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

const REUNION = {
  id: 12, titre: "31/08/2026", statut: "ouverte", ouverte: true,
  ouverte_par: "Marc", ouverte_le: "2026-08-31T08:05:00",
  date_debut: "2026-08-28", date_fin: "2026-08-28", machine: "Cohesio 1",
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
verifier("reunion absente : chargement", M.rendreReunion(null, null, "").includes("Chargement"));
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
verifier("liste : identifiant de ligne", liste.includes('data-id="12"'));
verifier("liste : titre", liste.includes("31/08/2026"));
verifier("liste : jour unique sans fleche",
         liste.includes(">28/08/2026<") && !liste.includes("28/08/2026 → 28/08/2026"));
verifier("liste : plage avec fleche", liste.includes("25/08/2026 → 26/08/2026"));
verifier("liste : machine en sous-titre", liste.includes("Cohesio 1"));
verifier("liste : presence de notes", liste.includes("notes") && liste.includes("sans notes"));
verifier("liste : participants", liste.includes("Marc, Sophie"));
verifier("liste : participants absents", liste.includes("—"));
verifier("liste : actions restantes", liste.includes("1 &agrave; faire"));
verifier("liste : actions toutes faites", liste.includes("3 faites"));
verifier("liste : etat en cours", liste.includes(">en cours<"));
verifier("liste : etat close", liste.includes(">close<"));
verifier("liste : tableau ferme", liste.trim().endsWith("</table>"));

console.log("\n3. La reunion rend l'ecran entier");
const ecran = M.rendreReunion(REUNION, { machines: ["Cohesio 1", "Cohesio 2"] }, "Enregistre a 09:12");
verifier("reunion : titre dans le champ", ecran.includes('value="31/08/2026"'));
verifier("reunion : auteur et date d'ouverture",
         ecran.includes("Ouverte par Marc") && ecran.includes("31/08/2026"));
verifier("reunion : bornes de periode",
         ecran.includes('id="reu-du" value="2026-08-28"') &&
         ecran.includes('id="reu-au" value="2026-08-28"'));
verifier("reunion : machine selectionnee",
         ecran.includes('<option value="Cohesio 1" selected>'));
verifier("reunion : autre machine non selectionnee",
         ecran.includes('<option value="Cohesio 2">'));
verifier("reunion : toutes les machines proposees", ecran.includes("Toutes les machines"));
verifier("reunion : bouton imprimer", ecran.includes('data-r="imprimer"'));
verifier("reunion : clore quand ouverte", ecran.includes("Clore la r&eacute;union"));
verifier("reunion : rouvrir quand close",
         M.rendreReunion(Object.assign({}, REUNION, { ouverte: false, statut: "close",
           close_le: "2026-08-31T10:00:00" }), null, "")
          .includes("Rouvrir la r&eacute;union"));
verifier("reunion : date de cloture affichee",
         M.rendreReunion(Object.assign({}, REUNION, { ouverte: false, statut: "close",
           close_le: "2026-08-31T10:00:00" }), null, "").includes("close le 31/08/2026"));
verifier("reunion : contenant des chiffres", ecran.includes('id="reu-prod"'));
verifier("reunion : colonne de notes", ecran.includes('id="reu-notes"'));
verifier("reunion : etat d'enregistrement", ecran.includes("Enregistre a 09:12"));
verifier("reunion : formulaire d'action", ecran.includes('data-r="ajout-action"'));
verifier("reunion : bloc ferme", ecran.trim().endsWith("</div>"));
verifier("reunion : machines absentes ne cassent rien",
         M.rendreReunion(REUNION, null, "").includes("Toutes les machines"));

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
const ecranP = M.rendreReunion(Object.assign({}, REUNION,
  { titre: '" onfocus="alert(1)', ouverte_par: piege }), { machines: [piege] }, "");
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
verifier("document : machine", doc.includes("Cohesio 1"));
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
         M.rendreDocument(Object.assign({}, REUNION, { machine: "" }), null, "")
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

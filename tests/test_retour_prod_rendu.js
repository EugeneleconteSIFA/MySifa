/*
 * Retour de production : ce que le rendu partage doit produire.
 *
 * `static/mysifa_retour_prod.js` porte tout le rendu de l'onglet « Retour de
 * prod » de MyProd. Une regression y passe silencieusement : le module rend
 * des chaines, personne ne leve d'exception si une moitie manque.
 *
 * Ce test existe parce que `node --check` ne suffit pas. Un mot parasite laisse
 * au milieu d'une concatenation a passe la verification syntaxique sans broncher
 * — l'insertion automatique de point-virgule de JavaScript coupait le `return`
 * en deux, et `renderRecherche` ne rendait plus que la balise ouvrante. Seul un
 * appel reel le montre.
 *
 * Trois familles de cas :
 *   - a vide, rien ne doit ressembler a une carte pleine ;
 *   - chaque fonction rend la ligne ENTIERE, pas son debut ;
 *   - aucune prose utilisateur ne sort sans echappement.
 *
 * Lancer : node tests/test_retour_prod_rendu.js
 */

const path = require("path");

global.window = global;
require(path.join(__dirname, "..", "static", "mysifa_retour_prod.js"));
const M = global.MySifaRetourProd;

const ECHECS = [];
function verifier(cas, cond) {
  if (cond) { console.log("  ok     " + cas); }
  else { ECHECS.push(cas); console.log("  ECHEC  " + cas); }
}

console.log("\n1. A vide, rien ne doit ressembler a une carte pleine");
const vide = M.renderFeuille({
  machine: "Cohesio 1", dossiers: 0, periode: { label: "Jeudi 27/08/2026" }
});
verifier("feuille : message explicite", vide.includes("Aucun dossier"));
verifier("feuille : aucun KPI a zero", !vide.includes("rp-kpis"));
verifier("feuille : la machine reste nommee", vide.includes("Cohesio 1"));
verifier("liste vide", M.renderListe([]).includes("Aucun dossier"));
verifier("recherche vide", M.renderRecherche([], "zz").includes("Aucun dossier"));

console.log("\n2. Chaque fonction rend la ligne entiere");
const rech = M.renderRecherche([{
  no_dossier: "D-745", client: "Marche 745", designation: "Reliqua 3",
  machine: "Cohesio 1", nb_saisies: 5,
  derniere_saisie: "2026-08-27T10:00:00", cloture: true
}], "D-");
verifier("recherche : numero", rech.includes("D-745"));
verifier("recherche : client et compte de saisies",
         rech.includes("Marche 745") && rech.includes("5 saisies"));
verifier("recherche : date formatee", rech.includes("27/08/2026"));
verifier("recherche : pastille d'etat", rech.includes("clôturé"));
verifier("recherche : dossier en cours",
         M.renderRecherche([{ no_dossier: "D-800", nb_saisies: 1, cloture: false }], "D-")
          .includes("en cours"));

const feuille = M.renderFeuille({
  machine: "Cohesio 1", dossiers: 2, periode: { label: "Semaine 35", mode: "semaine", du: "24/08/2026", au: "30/08/2026" },
  conducteurs: ["Marc", "Sophie"],
  production: { metrage: 58500, minutes_production: 445, minutes_calage: 105,
                minutes_arret: 130, vitesse_m_min: 131.5, part_arret_pct: 19.1 },
  references: [{ no_dossier: "D-501", client: "NESTLE VEAUCHE", ref_produit_norm: "REF-A", metrage: 40000,
                 cadence_m_min: 33.2, vitesse_m_min: 41.6, cadence_reference_m_min: 57,
                 series_passees: 3, ecart_pct: -41.8 }],
  arrets_couteux: [{ code: "66", operation: "66 - Attente matiere", occurrences: 1, minutes_txt: "1 h 35" }],
  ecrits: [{ origine: "info_prod", texte: "Tension a baisser", no_dossier: "D-501",
             auteur: "Marc", cle: "infoprod:D-501", reference: "D-501", modifiable: true, valide: false },
           { origine: "commentaire", texte: "Casse a repetition", no_dossier: "D-501",
             auteur: "Sophie", cle: "saisie:12", reference: 12, modifiable: true,
             valide: true, valide_par: "Eugene", valide_le: "2026-08-28T09:00:00" },
           { origine: "annulation", texte: "Erreur de code", no_dossier: "D-501",
             auteur: "Marc", cle: "saisie:13", reference: 13, modifiable: false, valide: false }],
  vigilance: { info_prod_absente: 1 }, nb_nc: 2
});
verifier("feuille : les 4 KPI", (feuille.match(/rp-kpi"/g) || []).length === 4);
verifier("feuille : conducteurs credites", feuille.includes("Marc · Sophie"));
verifier("feuille : cadence et vitesse distinguees",
         feuille.includes("33,2 m/min") && feuille.includes("41,6 m/min") && feuille.includes("hors arrêts"));
verifier("feuille : repere historique", feuille.includes("57,0 m/min") && feuille.includes("3 prod."));
verifier("feuille : unite de la machine, jamais de m/h", !feuille.includes("m/h"));
verifier("feuille : le code n'est pas repete dans l'operation",
         feuille.includes(">Attente matiere<") && !feuille.includes(">66 - Attente matiere<"));
verifier("feuille : ecart negatif signale", feuille.includes("-42 %"));
verifier("feuille : arret nomme", feuille.includes("Attente matiere"));
verifier("feuille : le mot du conducteur remonte", feuille.includes("Tension a baisser"));
verifier("feuille : client dans la cadence", feuille.includes("NESTLE VEAUCHE"));
verifier("feuille : section Arrets", feuille.includes(">Arrêts</div>"));
verifier("feuille : plus de colonne Code dans les arrets", !feuille.includes("<th>Code</th>"));
verifier("feuille : les trois gestes sur une remontee",
         feuille.includes('data-valider="infoprod:D-501"')
         && feuille.includes('data-modif="infoprod:D-501"')
         && feuille.includes('data-commenter="infoprod:D-501"'));
verifier("feuille : une remontee traitee est marquee",
         feuille.includes("est-valide") && feuille.includes("traité par Eugene"));
verifier("feuille : bouton Devalider sur une remontee traitee", feuille.includes("Dévalider"));
verifier("feuille : un motif d'annulation ne se corrige pas",
         !feuille.includes('data-modif="saisie:13"'));
verifier("feuille : mais il se valide", feuille.includes('data-valider="saisie:13"'));
verifier("feuille : compteur de remontees a traiter", feuille.includes("2 à traiter"));

const toutes = M.renderFeuille(Object.assign({}, {
  toutes_machines: true, machines_couvertes: ["Cohesio 1", "Cohesio 2"],
  dossiers: 1, periode: { label: "Jeudi 27/08/2026" }, production: {},
  conducteurs: [], references: [], arrets_couteux: [], ecrits: [], vigilance: {}
}));
verifier("feuille : toutes les machines", toutes.includes("Toutes les machines"));
verifier("feuille : machines couvertes listees",
         toutes.includes("Cohesio 1 · Cohesio 2"));
verifier("feuille : vigilance comptee", feuille.includes("clôturé sans info prod"));
verifier("feuille : vigilance non nominative", !feuille.split("À reprendre")[1].includes("Marc"));
verifier("feuille : NC", feuille.includes("2 non-conformités"));

console.log("\n3. Aucune prose utilisateur ne sort sans echappement");
const xss = M.renderFeuille({
  machine: '<img src=x onerror=alert(1)>', dossiers: 1, periode: { label: "x" },
  production: {}, conducteurs: ['Marc<script>'], references: [], arrets_couteux: [],
  ecrits: [{ origine: "info_prod", texte: '<script>alert(1)</script>',
             no_dossier: 'D<1', auteur: 'a"b' }],
  vigilance: {}
});
verifier("machine echappee", !xss.includes("<img src=x"));
verifier("conducteur echappe", !xss.includes("Marc<script>"));
verifier("texte ecrit echappe", !xss.includes("<script>alert(1)</script>"));
verifier("auteur echappe", !xss.includes('a"b'));

const liste = M.renderListe([{ no_dossier: '"><b>x', client: "<i>", machine: "m",
  metrage_reel: 1, nb_seuils: 0, nb_nc: 0, nb_commentaires: 0 }]);
verifier("liste : numero echappe (attribut et texte)", !liste.includes('"><b>x'));
verifier("liste : client echappe", !liste.includes("<i>"));
verifier("recherche : donnee echappee",
         !M.renderRecherche([{ no_dossier: '"><b>', nb_saisies: 1, cloture: false }], "x")
           .includes('"><b>'));

console.log("\n4. Compte-rendu d'un dossier");
const crBase = {
  no_dossier: "D-745", existe: true,
  identite: { client: "Marche 745", designation: "Reliqua 3", machine: "Cohesio 1",
              ref_produit_norm: "REF-A", conducteurs: ["Marc"], cloture: true, nb_saisies: 5 },
  temps: { total_minutes: 400, categories: [
    { categorie: "production", label: "Production", minutes: 310, part_pct: 77.5, occurrences: 2 }] },
  metrage: { reel: 31500, prevu: 35000, fiable: true },
  vitesse_m_min: 101.6, cadence_m_min: 78.8,
  ecrits: { info_prod: null, commentaires: [] },
  seuils: [{ saisie_id: 3, operation_code: "64", operation: "Intervention technique",
             duree_saisie_txt: "45 min", operateur: "Marc",
             explication_texte: "", sans_explication: true }],
  non_conformites: [], vigilance: [{ cle: "info_prod_absente", texte: "Dossier cloture sans info prod." }]
};
const cr = M.renderCR(crBase);
verifier("CR : les deux vitesses distinguees",
         cr.includes("101,6 m/min") && cr.includes("78,8 m/min")
         && cr.includes("hors arrêts") && cr.includes("arrêts compris"));
verifier("CR : jamais de m/h", !cr.includes("m/h"));
verifier("CR : info prod absente signalee", cr.includes("Aucune info prod"));
verifier("CR : et due a la cloture", cr.includes("due à la clôture"));
verifier("CR : bouton de saisie propose", cr.includes('id="rp-ip-edit"') && cr.includes("Renseigner"));
verifier("CR : seuil sans explication signale", cr.includes("Sans explication"));
verifier("CR : bouton d'explication", cr.includes('data-seuil="3"') && cr.includes("Expliquer"));

const crOuvert = JSON.parse(JSON.stringify(crBase));
crOuvert.identite.cloture = false;
const co = M.renderCR(crOuvert);
verifier("CR : dossier en cours marque", co.includes("en cours"));
verifier("CR : info prod pas reclamee avant cloture",
         co.includes("pas encore clôturé") && !co.includes("due à la clôture"));

const crRempli = JSON.parse(JSON.stringify(crBase));
crRempli.ecrits.info_prod = { texte: "Tension a baisser", auteur: "Marc",
                              created_at: "2026-08-27T11:00:00",
                              cle: "infoprod:D-745", origine: "info_prod",
                              reference: "D-745", modifiable: true, valide: false };
crRempli.seuils[0].explication_texte = "Cellule rereglee";
crRempli.seuils[0].texte = "Cellule rereglee";
crRempli.seuils[0].cle = "seuil:3";
crRempli.seuils[0].origine = "arret";
crRempli.seuils[0].reference = 3;
crRempli.seuils[0].modifiable = true;
const cf = M.renderCR(crRempli);
verifier("CR : info prod affichee", cf.includes("Tension a baisser"));
verifier("CR : info prod actionnable", cf.includes('data-valider="infoprod:D-745"'));
verifier("CR : explication affichee", cf.includes("Cellule rereglee"));
verifier("CR : explication actionnable", cf.includes('data-modif="seuil:3"'));
verifier("CR : ajout de commentaire propose", cf.includes('id="rp-note-add"'));

const crXss = JSON.parse(JSON.stringify(crBase));
crXss.ecrits.info_prod = { texte: '<script>alert(1)</script>', auteur: '<b>' };
verifier("CR : info prod echappee",
         !M.renderCR(crXss).includes("<script>alert(1)</script>"));

console.log("\n3 bis. Frise de production");
const friseVide = M.renderFrise(null);
verifier("frise absente : rien rendu", friseVide === "");
verifier("frise vide : rien rendu", M.renderFrise({ vide: true, lignes: [] }) === "");

const frise = M.renderFrise({
  vide: false,
  axe: [{ jour: "2026-08-27", label: "Jeu 27/08", heures: 8, x: 0, largeur: 66.67, coupure_avant: false },
        { jour: "2026-08-29", label: "Sam 29/08", heures: 4, x: 66.67, largeur: 33.33, coupure_avant: true }],
  lignes: [{ machine: "Cohesio 1", slots: [{
    no_dossier: "D-1", client: "NESTLE", minutes: 480,
    debut: "2026-08-26T14:00:00", fin: "2026-08-28T10:00:00",
    x: 0, largeur: 66.67, deborde_avant: true, deborde_apres: true,
    segments: [{ categorie: "calage", label: "Calage", minutes: 60, x: 0, largeur: 12.5 },
               { categorie: "production", label: "Production", minutes: 420, x: 12.5, largeur: 87.5 }]
  }] }]
});
verifier("frise : les jours de l'axe", frise.includes("Jeu 27/08") && frise.includes("Sam 29/08"));
verifier("frise : largeurs posees en %", frise.includes("width:66.67%"));
verifier("frise : la coupure est marquee", frise.includes("rp-fr-jour coupe"));
verifier("frise : debordements des deux cotes",
         frise.includes("deborde-avant") && frise.includes("deborde-apres"));
verifier("frise : une phase par categorie",
         frise.includes("rp-fr-seg cat-calage") && frise.includes("rp-fr-seg cat-production"));
verifier("frise : le slot porte son dossier", frise.includes('data-dossier="D-1"'));
verifier("frise : legende presente", frise.includes("rp-fr-legende"));
verifier("frise : donnee echappee",
         !M.renderFrise({ vide:false, axe:[], lignes:[{ machine:'<b>x', slots:[] }] }).includes("<b>x"));

console.log("\n3 ter. Citations, masquage");
const avecReponse = M.renderEcrit({
  cle: "saisie:12", origine: "commentaire", reference: 12, no_dossier: "D-1",
  texte: "Casse a repetition", auteur: "Sophie", modifiable: true, valide: false,
  reponses: [{ texte: "Vu avec la maintenance", auteur: "Eugene",
               created_at: "2026-08-28T09:00:00" }]
});
verifier("la reponse est rendue en citation", avecReponse.includes("rp-citation"));
verifier("avec son texte", avecReponse.includes("Vu avec la maintenance"));
verifier("et son auteur", avecReponse.includes("Eugene"));
verifier("bouton Masquer propose", avecReponse.includes('data-masquer="saisie:12"')
         && avecReponse.includes(">Masquer</button>"));

const masque = M.renderEcrit({ cle: "saisie:13", origine: "commentaire", reference: 13,
  no_dossier: "D-1", texte: "10h", auteur: "Marc", modifiable: true, masque: true });
verifier("une remontee masquee est marquee", masque.includes("est-masque"));
verifier("et propose de la reafficher", masque.includes(">Réafficher</button>"));

const feuilleMasques = M.renderFeuille({
  machine: "Cohesio 1", dossiers: 1, periode: { label: "x" }, production: {},
  conducteurs: [], references: [], arrets_couteux: [], vigilance: {},
  ecrits: [{ cle: "saisie:1", texte: "Casse bande", origine: "commentaire",
             no_dossier: "D-1", auteur: "Marc", modifiable: true }],
  ecrits_masques: [{ cle: "saisie:9", texte: "10h", origine: "commentaire",
                     no_dossier: "D-1", auteur: "Marc", modifiable: true, masque: true }]
});
verifier("feuille : bouton des commentaires masques",
         feuilleMasques.includes("Commentaires masqués (1)"));
verifier("feuille : la liste masquee est repliee",
         feuilleMasques.includes('id="rp-masques" style="display:none"'));
verifier("feuille : le compteur ne compte que les visibles",
         feuilleMasques.includes("1 à traiter"));

console.log("\n4 bis. Slug de cle");
verifier("les deux-points ne peuvent pas etre un id DOM", M.slug("infoprod:D-501") === "infoprod_D-501");
verifier("slug d'une note", M.slug("note:7") === "note_7");

console.log("\n5. Formats");
verifier("vitesse en m/min", M.vitesse(33.2) === "33,2 m/min");
verifier("vitesse inconnue", M.vitesse(null) === "—");
verifier("code retire de l'operation", M.sansCode("66 - Attente matiere", "66") === "Attente matiere");
verifier("code absent : operation intacte", M.sansCode("Attente matiere", "66") === "Attente matiere");
verifier("code non prefixe : rien retire", M.sansCode("166 - Autre", "66") === "166 - Autre");
verifier("duree sous l'heure", M.minutesTxt(45) === "45 min");
verifier("heure pleine", M.minutesTxt(120) === "2 h");
verifier("heure et minutes", M.minutesTxt(95) === "1 h 35");
verifier("duree inconnue", M.minutesTxt(null) === "—");
verifier("milliers separes", M.fnum(127814) === "127 814");
verifier("decimale francaise", M.fnum(19.1, 1) === "19,1");
verifier("ecart sans repere", M.ecartHtml(null).includes("pas de repère"));
verifier("ecart positif signe", M.ecartHtml(33.3).includes("+33 %"));
verifier("date francaise", M.dateFr("2026-08-27T10:00:00") === "27/08/2026");
verifier("date absente", M.dateFr(null) === "");

console.log("\n" + "=".repeat(60));
if (ECHECS.length) {
  console.log(ECHECS.length + " echec(s) :");
  ECHECS.forEach(e => console.log("  - " + e));
  process.exit(1);
}
console.log("Tous les cas passent.");

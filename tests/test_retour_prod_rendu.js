/*
 * Retour de production : ce que le rendu partage doit produire.
 *
 * `static/mysifa_retour_prod.js` est charge par DEUX ecrans (la page
 * /rapports-prod et l'onglet « Retour de prod » de MyProd). Une regression ici
 * casse les deux d'un coup, et silencieusement : le module rend des chaines,
 * personne ne leve d'exception si une moitie manque.
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
                minutes_arret: 130, vitesse_m_h: 7888, part_arret_pct: 19.1 },
  references: [{ no_dossier: "D-501", ref_produit_norm: "REF-A", metrage: 40000,
                 cadence_m_h: 8727, vitesse_m_h: 10000, cadence_reference_m_h: 15000,
                 series_passees: 3, ecart_pct: -41.8 }],
  arrets_couteux: [{ code: "66", operation: "Attente matiere", occurrences: 1, minutes_txt: "1 h 35" }],
  ecrits: [{ origine: "info_prod", texte: "Tension a baisser", no_dossier: "D-501", auteur: "Marc" }],
  vigilance: { info_prod_absente: 1 }, nb_nc: 2
});
verifier("feuille : les 4 KPI", (feuille.match(/rp-kpi"/g) || []).length === 4);
verifier("feuille : conducteurs credites", feuille.includes("Marc · Sophie"));
verifier("feuille : cadence et vitesse distinguees",
         feuille.includes("8 727 m/h") && feuille.includes("hors arrêts"));
verifier("feuille : repere historique", feuille.includes("15 000 m/h") && feuille.includes("3 productions"));
verifier("feuille : ecart negatif signale", feuille.includes("-42 %"));
verifier("feuille : code d'arret couteux", feuille.includes("Attente matiere"));
verifier("feuille : le mot du conducteur remonte", feuille.includes("Tension a baisser"));
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
  vitesse_m_h: 6096, cadence_m_h: 4725,
  ecrits: { info_prod: null, commentaires: [] },
  seuils: [{ saisie_id: 3, operation_code: "64", operation: "Intervention technique",
             duree_saisie_txt: "45 min", operateur: "Marc",
             explication_texte: "", sans_explication: true }],
  non_conformites: [], vigilance: [{ cle: "info_prod_absente", texte: "Dossier cloture sans info prod." }]
};
const cr = M.renderCR(crBase);
verifier("CR : les deux vitesses distinguees",
         cr.includes("Vitesse de production") && cr.includes("Cadence"));
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
                              created_at: "2026-08-27T11:00:00" };
crRempli.seuils[0].explication_texte = "Cellule rereglee";
const cf = M.renderCR(crRempli);
verifier("CR : info prod affichee", cf.includes("Tension a baisser"));
verifier("CR : bouton devient Modifier", cf.includes("Modifier"));
verifier("CR : explication affichee", cf.includes("Cellule rereglee"));
verifier("CR : bouton devient Completer", cf.includes("Compléter"));

const crXss = JSON.parse(JSON.stringify(crBase));
crXss.ecrits.info_prod = { texte: '<script>alert(1)</script>', auteur: '<b>' };
verifier("CR : info prod echappee",
         !M.renderCR(crXss).includes("<script>alert(1)</script>"));

console.log("\n5. Formats");
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

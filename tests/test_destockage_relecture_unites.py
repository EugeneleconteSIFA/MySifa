"""
Relecture du déstockage en unités d'atelier — ce qui doit rester vrai.

Chaque bloc protège une décision du 10/09/2026 :

1. **On saisit dans l'unité de l'atelier** (ml, kg, mandrins, cartons,
   palettes) et le serveur convertit vers l'unité du stock avec le MÊME
   facteur que celui affiché — sinon le chiffre vu n'est pas le chiffre écrit.
2. **Cartons, palettes et mandrins ne se fractionnent pas** : arrondi à
   l'unité supérieure au déstockage automatique, entier exigé à l'ajustement.
3. **Un remplacement s'additionne par clé** : l'écran renvoie l'ancienne
   matière à 0 et la nouvelle à sa quantité ; la même clé envoyée deux fois
   n'est pas écrite deux fois.
4. **La relecture suivante lit le remplacement** : la matière ajoutée se
   rattache à la ligne de fiche qu'elle remplace, dans sa catégorie.
5. **L'annulation contre-passe le NET** et une entrée n'est jamais refusée
   pour stock négatif — c'est ce qui empêchait d'annuler un déstockage.

Code extrait par découpage de source, comme test_besoins_verrou_documents.py.
"""
import math
import re
import sqlite3
import sys
from typing import Optional

sys.path.insert(0, ".")

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


def proche(a, b, tol=1e-6):
    return a is not None and b is not None and abs(float(a) - float(b)) < tol


class HTTPException(Exception):
    def __init__(self, status_code, detail=""):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _f(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def _n(v, unite=""):
    return "%g%s" % (float(v), (" " + unite) if unite else "")


src = open("app/routers/besoins_matieres.py", encoding="utf-8").read()
ns = {"HTTPException": HTTPException, "_f": _f, "_n": _n, "math": math,
      "Optional": Optional, "_KINDS_BOBINE": frozenset({"support", "glassine"})}
exec(src[src.index("def _laizes_matiere("):src.index("def _etat_documents(")], ns)
exec(src[src.index("def _net_sorti("):src.index('@router.get("/api/stock/destockage/{planning_id}/relecture")')], ns)
exec(src[src.index("def _cibles_stock("):src.index('@router.post("/api/stock/destockage/{planning_id}/ajuster")')], ns)

conv = ns["_conversion_matiere"]
qad = ns["_quantite_a_destocker"]

print("1. Conversions")
c = conv("support", {"metres_lineaires_par_bobine": 7250}, None, 10)
check("frontal : saisie en ml", c["unite_reelle"], "ml")
check("frontal : 18 000 ml = 2,4828 bobines", round(18000 * c["facteur_stock"], 4), 2.4828)
c = conv("carton", {"unites_par_palette": 50}, None, 10)
check("carton : 121 cartons = 2,42 palettes", round(121 * c["facteur_stock"], 4), 2.42)
check("carton : simplifié en palettes", c["unite_simplifiee"], "palette")
check("carton : entier", c["entier"], True)
c = conv("carton", {}, None, 10)
check("carton sans conditionnement : non convertible", c["facteur_stock"], None)
check("et le manque est nommé", "Cartons par palette" in (c["manque"] or ""), True)
c = conv("mandrin", {"longueur_tube_mm": 1000, "unites_par_palette": 100}, 45, 10)
check("mandrin : 1 mandrin de 45 mm = 0,05 tube (perte 10 %)", round(c["facteur_simplifie"], 6), 0.05)
check("mandrin : simplifié en tubes", c["unite_simplifiee"], "tube")
check("mandrin : stock en palettes de tubes", round(c["facteur_stock"], 6), 0.0005)
c = conv("mandrin", {"longueur_tube_mm": 1000, "unites_par_palette": 100}, None, 10)
check("mandrin sans laize module : non convertible", c["facteur_stock"], None)
c = conv("adhesif", {}, None, 10)
check("adhésif : kg = kg", (c["unite_reelle"], c["facteur_stock"]), ("kg", 1.0))
check("retour au réel : 2,42 palettes = 121 cartons",
      ns["_depuis_stock"](conv("carton", {"unites_par_palette": 50}, None, 10), 2.42), 121.0)

print("2. Entiers au déstockage automatique")
r = qad({"kind": "palette", "quantite": 0.672}, {})
check("0,672 palette → 1 palette", r["quantite"], 1.0)
r = qad({"kind": "carton", "quantite": 120.3}, {"unites_par_palette": 50})
check("120,3 cartons → 121 cartons ÷ 50", r["quantite"], 2.42)
r = qad({"kind": "carton", "quantite": 121.0000001}, {"unites_par_palette": 50})
check("121,0000001 cartons ne devient pas 122", r["quantite"], 2.42)
r = qad({"kind": "mandrin", "quantite": 99.5, "besoin_palettes": 0.0995}, {})
check("99,5 mandrins → 100 mandrins en palettes", r["quantite"], 0.1)

print("3. Cibles d'ajustement")
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.executescript("""
    CREATE TABLE matieres_premieres (id INTEGER PRIMARY KEY, categorie TEXT,
        reference TEXT, designation TEXT, metres_lineaires_par_bobine REAL,
        longueur_tube_mm REAL, unites_par_palette REAL,
        actif INTEGER DEFAULT 1, brouillon INTEGER DEFAULT 0);
    INSERT INTO matieres_premieres VALUES
        (1,'frontal','PP95','PP blanc mat 95',7250,NULL,NULL,1,0),
        (2,'frontal','PP80','PP blanc 80',8000,NULL,NULL,1,0),
        (3,'carton','C305','Boîte 305',NULL,NULL,NULL,1,0),
        (4,'carton','C400','Boîte 400',NULL,NULL,50,1,0),
        (5,'palette','EUR','Palette',NULL,NULL,NULL,1,0);
    CREATE TABLE mp_mouvements (id INTEGER PRIMARY KEY, matiere_id INTEGER,
        laize_id INTEGER, type_mouvement TEXT, quantite REAL,
        planning_entry_id INTEGER);
""")
cibles = ns["_cibles_stock"]
cb = cibles(conn, [
    {"matiere_id": 1, "laize_id": 7, "quantite_reelle": 0},
    {"matiere_id": 2, "laize_id": 7, "quantite_reelle": 16000},
], None, 10)
check("remplacement : l'ancienne à 0", cb[(1, 7)], 0.0)
check("remplacement : la nouvelle convertie (16 000 ml = 2 bobines)", cb[(2, 7)], 2.0)
cb = cibles(conn, [
    {"matiere_id": 1, "laize_id": 7, "quantite_reelle": 0},
    {"matiere_id": 1, "laize_id": 7, "quantite_reelle": 14500},
], None, 10)
check("même matière gardée : 0 + quantité, pas le double", cb[(1, 7)], 2.0)


def refuse(libelle, lignes, morceau):
    global ko
    try:
        cibles(conn, lignes, None, 10)
    except HTTPException as e:
        check(libelle, morceau in e.detail, True)
        return
    ko += 1
    print(f"  KO  {libelle} — accepté")


refuse("carton fractionnaire refusé",
       [{"matiere_id": 4, "laize_id": None, "quantite_reelle": 12.5}], "entier")
refuse("carton sans conditionnement refusé s'il faut écrire",
       [{"matiere_id": 3, "laize_id": None, "quantite_reelle": 121}], "Cartons par palette")
refuse("bobine sans laize refusée",
       [{"matiere_id": 1, "laize_id": None, "quantite_reelle": 1000}], "laize")
cb = cibles(conn, [{"matiere_id": 3, "laize_id": None, "quantite_reelle": 0}], None, 10)
check("carton sans conditionnement à 0 : accepté (rien à écrire)", cb[(3, None)], 0.0)
cb = cibles(conn, [{"matiere_id": 1, "laize_id": 7, "quantite": 2.4826}], None, 10)
check("ancien appel en unité de stock : inchangé", cb[(1, 7)], 2.4826)

print("4. Appariement des remplacements")
lignes = [
    {"kind": "support", "matiere_id": 1, "matiere_ref": "PP95",
     "matiere_categorie": "frontal", "laize_id": 7, "sorti": 0.0},
    {"kind": "carton", "matiere_id": 3, "matiere_ref": "C305",
     "matiere_categorie": "carton", "laize_id": None, "sorti": 0.0},
]
ajouts = [
    {"matiere_id": 2, "matiere_ref": "PP80", "matiere_categorie": "frontal",
     "laize_id": 7, "sorti": 2.0, "laizes": []},
    {"matiere_id": 5, "matiere_ref": "EUR", "matiere_categorie": "palette",
     "laize_id": None, "sorti": 1.0, "laizes": []},
]
restes = ns["_apparier_remplacements"](lignes, ajouts)
check("le frontal ajouté remplace le frontal de la fiche", lignes[0]["matiere_id"], 2)
check("et la ligne dit ce qu'elle remplace", lignes[0]["remplace"]["matiere_ref"], "PP95")
check("une palette ne remplace pas un carton", lignes[1]["matiere_id"], 3)
check("la palette reste une ligne à part", [a["matiere_id"] for a in restes], [5])

print("5. Net sorti")
conn.executescript("""
    INSERT INTO mp_mouvements VALUES (1, 1, 7, 'sortie', 2.4826, 10);
    INSERT INTO mp_mouvements VALUES (2, 1, 7, 'entree', 0.5, 10);
    INSERT INTO mp_mouvements VALUES (3, 5, NULL, 'sortie', 1, 10);
""")
net, der = ns["_net_sorti"](conn, 10)
check("sortie moins retour d'ajustement", round(net[(1, 7)], 4), 1.9826)
check("l'annulation se rattache à la dernière sortie", der[(1, 7)], 1)

print("6. Une entrée n'est jamais refusée pour stock négatif")
src_stock = open("app/routers/stock.py", encoding="utf-8").read()
corps = src_stock[src_stock.index("def appliquer_mouvement_mp("):]
corps = corps[:corps.index("\n@router")]
check("le refus ne vise que les sorties",
      'if type_mvt == "sortie" and apres < 0 and not autoriser_negatif:' in corps, True)
src_annul = src[src.index('def destockage_annuler('):src.index("def _destockage_auto_un(")]
check("l'annulation écrit avec autoriser_negatif", "autoriser_negatif=True" in src_annul, True)
check("l'annulation part du net", "_net_sorti(conn, planning_id)" in src_annul, True)

print("7. Composition attendue d'un dossier")
exec(src[src.index("def _motif_reserve("):src.index("def _controle_donnees(")], ns)
compo = ns["_composition_attendue"]


def ligne(kind, cat=None, mid=1):
    return {"kind": kind, "matiere_id": mid, "matiere_categorie": cat,
            "destockable": True, "source_value": kind.upper()}


lg = [ligne("carton", "carton"), ligne("palette", "palette")]
ajout, notes = compo({"poste_sans_matiere": 0}, lg)
kinds = sorted(a["kind"] for a in ajout)
check("sans frontal ni mandrin : frontal/complexe et mandrin proposés", kinds, ["mandrin", "support"])
check("le frontal manquant met en réserve", [a["facultative"] for a in ajout if a["kind"] == "support"], [False])
check("le mandrin manquant ne met pas en réserve", [a["facultative"] for a in ajout if a["kind"] == "mandrin"], [True])
check("la réserve d'une ligne attendue se lit sans « support « support »",
      ns["_motif_reserve"](ajout[0]).startswith("Aucun") or ns["_motif_reserve"](ajout[0]).startswith("Pas de"), True)

lg = [ligne("support", "frontal"), ligne("mandrin", "mandrin"), ligne("carton", "carton")]
ajout, _ = compo({"poste_sans_matiere": 0}, lg)
check("un frontal appelle glassine, adhésif ; la palette manque",
      sorted(a["kind"] for a in ajout), ["adhesif", "glassine", "palette"])

lg = [ligne("support", "complexe"), ligne("adhesif", "adhesif"), ligne("glassine", "glassine"),
      ligne("mandrin", "mandrin"), ligne("carton", "carton"), ligne("palette", "palette")]
ajout, _ = compo({"poste_sans_matiere": 0}, lg)
check("un complexe complet : rien à ajouter", ajout, [])
adh = [l for l in lg if l["kind"] == "adhesif"][0]
check("l'adhésif d'un complexe ne sort pas d'office", (adh["destockable"], adh["inclus_complexe"]), (False, True))
check("et ne met pas en réserve", adh["facultative"], True)

lg = [ligne("mandrin", "mandrin"), ligne("carton", "carton"), ligne("palette", "palette")]
ajout, notes = compo({"poste_sans_matiere": 1, "machine_nom": "Repiquage"}, lg)
check("repiquage : aucun frontal attendu", ajout, [])
check("repiquage : l'écran dit pourquoi", "Repiquage" in (notes[0] if notes else ""), True)

lg = [ligne("support", None, mid=None), ligne("carton", "carton"), ligne("palette", "palette"), ligne("mandrin", "mandrin")]
ajout, _ = compo({"poste_sans_matiere": 0}, lg)
check("frontal non rattaché : on ne devine pas la glassine", ajout, [])

print("8. Compléter la fiche par l'OF")
conn.executescript("""
    CREATE TABLE of_imports (id INTEGER PRIMARY KEY, matiere TEXT, glassine TEXT,
        adhesif_label TEXT, mandrins_dia TEXT, cartons_type TEXT, qte_au_mille REAL);
    INSERT INTO of_imports VALUES (3, 'THERMIQUE ECO', 'ITASA KA', NULL, 'Tube 1500x76', 'Carton 385', NULL);
""")
pe = {"of_import_id": 3, "ft_support": "VELIN", "ft_glassine": None, "ft_mandrin_dia": "",
      "ft_cartons": None, "ft_adhesif": None}
faits = ns["_completer_depuis_of"](conn, pe)
check("la fiche prime sur l'OF", pe["ft_support"], "VELIN")
check("les cases vides prennent l'OF", (pe["ft_glassine"], pe["ft_mandrin_dia"], pe["ft_cartons"]),
      ("ITASA KA", "Tube 1500x76", "Carton 385"))
check("les natures complétées sont rendues", sorted(faits), ["carton", "glassine", "mandrin"])
check("une case vide de l'OF ne remplit rien", pe["ft_adhesif"], None)

print("9. Cartons entiers à la relecture")
r = qad({"kind": "carton", "quantite": 4}, {"unites_par_palette": 260})
check("4 cartons ÷ 260 écrits à 6 décimales", r["quantite"], 0.015385)
cv = conv("carton", {"unites_par_palette": 260}, None, 10)
check("une sortie ancienne à 0,0154 palette relit 4 cartons", ns["_depuis_stock"](cv, 0.0154), 4.0)

print()
if ko:
    print(f"ÉCHEC — {ko} vérification(s) en erreur.")
    sys.exit(1)
print("Tous les cas passent.")

"""
Dossier et devis côte à côte : format, quantité, étiquettes par rouleau,
matière, colle.

Les entrées reprennent de vraies lignes (OF de 9932755 Roquette, 148 × 80 PP
95 µ, « Bobine de 650 étiquettes », colle réf. 2028 ; OF de 9932862, THERMIQUE
PRO, « Bobine de 4.000 étiquettes ») et de vrais noms de devis.

Lancer : python3 tests/test_rentabilite_caracteristiques.py
"""
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from app.services.devis_rapprochement import vocabulaire          # noqa: E402
from app.services.rentabilite_caracteristiques import (             # noqa: E402
    comparer, ex_par_rouleau_devis, ex_par_rouleau_of,
)

FAIL = []


def check(nom, cond, detail=""):
    if cond:
        print(f"  ok  {nom}")
    else:
        print(f"  KO  {nom}\n     {detail}")
        FAIL.append(nom)


VOC = vocabulaire(
    ["PP 95µ BLANC MAT", "PP 95µ BLANC MAT", "THERMIQUE PRO", "THERMIQUE PRO", "THERMIQUE ECO",
     "THERMIQUE ECO", "Couché", "Couché", "Vélin", "Vélin"],
    ["Permanent 2028Y - 19", "Permanent 2028Y - 19", "Enlevable 4253", "Enlevable 4253"],
)

print("1. Étiquettes par rouleau")
check("OF : « Bobine de 4.000 étiquettes »", ex_par_rouleau_of("Bobine de 4.000 étiquettes Cartons 75", 600000, 150) == 4000)
check("OF : « Bobine de 1 000 étiquettes »", ex_par_rouleau_of("Bobine de 1 000 étiquettes Cartons 2", 60000, 60) == 1000)
check("OF sans conditionnement : quantité ÷ bobines", ex_par_rouleau_of(None, 120900, 186) == 650)
check("OF sans rien : inconnu", ex_par_rouleau_of(None, None, None) is None)
check("devis : valeur du classeur d'abord", ex_par_rouleau_devis(3500.0, "x B800.xlsx") == 3500)
check("devis : « B3500 » du nom de fichier en repli",
      ex_par_rouleau_devis(None, "80x40 thermique permanent bicolor laize 510 M76 B3500 12.936.000 10-11-2026.xlsx") == 3500)
check("devis : pas de « B » dans un mot", ex_par_rouleau_devis(None, "Bobst 148x80.xlsx") is None)

print("2. Roquette, devis concordant")
roquette = {"format_l": 148, "format_h": 80, "of_format": "148 x 80 mm", "of_qte_etiquettes": 120900,
            "of_qte_bobines": 186, "of_conditionnement": "Bobine de 650 étiquettes Cartons 31",
            "matiere": "PP 95µ BLANC MAT", "adhesif_label": None, "ref_adhesif": "2028"}
devis_ok = {"format_v": 148, "format_h": 80, "qte_etiquettes": 120000,
            "filename": "Roquette 148x80 PP blanc permanent 2028-19 B650 120.000 15-10-2026.xlsx"}
r = comparer(roquette, devis_ok, None, VOC)
L = {l["cle"]: l for l in r["lignes"]}
check("cinq lignes, dans l'ordre", [l["cle"] for l in r["lignes"]] == ["format", "quantite", "ex_rouleau", "matiere", "colle"])
check("format lu sur l'OF", L["format"]["dossier"] == "148 x 80 mm" and L["format"]["devis"] == "148 × 80 mm")
check("aucun écart", r["ecarts"] == 0, r["lignes"])
check("colle du dossier : référence de l'OF", L["colle"]["dossier"] == "réf. 2028", L["colle"])
check("colle du devis : type et code du nom", "Permanent" in L["colle"]["devis"] and "2028" in L["colle"]["devis"], L["colle"])
check("matière du devis : famille lue dans le nom, écrite comme l'OF", L["matiere"]["devis"].startswith("PP"), L["matiere"])

print("3. Écarts")
devis_ko = {"format_v": 80, "format_h": 40, "qte_etiquettes": 500000,
            "filename": "Roquette 80x40 thermique eco enlevable 4253 B3500 500.000.xlsx"}
r = comparer(roquette, devis_ko, None, VOC)
L = {l["cle"]: l for l in r["lignes"]}
check("format différent", L["format"]["ecart"])
check("quantité différente", L["quantite"]["ecart"])
check("étiquettes par rouleau différentes", L["ex_rouleau"]["ecart"] and L["ex_rouleau"]["devis"] == 3500)
check("matière différente : PP contre thermique", L["matiere"]["ecart"], L["matiere"])
check("colle différente : 2028 contre 4253", L["colle"]["ecart"], L["colle"])
check("cinq écarts comptés", r["ecarts"] == 5, r["ecarts"])
check("format inversé : pas un écart", not comparer(roquette, {**devis_ok, "format_v": 80, "format_h": 148},
                                                    None, VOC)["lignes"][0]["ecart"])

print("4. Multiple exact, côté inconnu")
r = comparer({**roquette, "of_qte_etiquettes": 240000}, devis_ok, None, VOC)
q = r["lignes"][1]
check("quantité double : pas un écart, noté", not q["ecart"] and q["note"] == "multiple exact", q)
r = comparer({"format_l": 148, "format_h": 80}, {"format_v": 148, "format_h": 80, "filename": "x.xlsx"}, None, VOC)
check("côtés inconnus : jamais un écart", r["ecarts"] == 0, r["lignes"])

print()
if FAIL:
    print(f"{len(FAIL)} échec(s) : {FAIL}")
    sys.exit(1)
print("Tous les tests passent.")

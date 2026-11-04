"""
Prix d'achat RVGI des produits finis sous-traités : conversions.

Ce que le test verrouille :
- le nombre d'étiquettes par rouleau se lit accolé au rouleau, jamais dans
  « spot toutes les 10 étiq. » d'une désignation ;
- achat au rouleau en dollars (cas 1004/0128) → prix au mille en euros ;
- achat au mille en euros → repris tel quel ;
- rien n'est inventé : rouleau sans nombre, devise sans taux, unité inconnue.

Lancer : python3 tests/test_pf_prix_achat.py
"""

import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)
os.environ["DB_PATH"] = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["ERP_MIRROR_DB"] = os.environ["DB_PATH"] + ".absent"
import database  # noqa: F401,E402  — le shim d'abord
from app.services import pf_prix_achat as pa  # noqa: E402

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(60) + f"{got!r}"
          + ("" if ok else f"   attendu {expected!r}"))
    if not ok:
        FAIL.append(label)


def achat(**k):
    base = {"pun": 1.0, "cua": "11", "ua_libelle": "Mille", "ua_nombre": 1000.0,
            "devise": "E", "numero": 1, "date": "2026-08-04", "fournisseur": "F", "textes": []}
    base.update(k)
    return base


check("rouleaux : « rolls of 2000 labels »", pa.etiquettes_par_rouleau("Box:15 rolls of 2000 labels"), 2000.0)
check("rouleaux : « rouleaux de 2 000 étiquettes »", pa.etiquettes_par_rouleau("Rouleaux de 2 000 étiquettes"), 2000.0)
check("rouleaux : « 2000 labels/roll »", pa.etiquettes_par_rouleau("2000 labels/roll"), 2000.0)
check("rouleaux : désignation « toutes les 10 étiq. » ignorée",
      pa.etiquettes_par_rouleau("1 coul. + noir au V° spot toutes les 10 étiq."), None)

r = pa.prix_achat(achat(pun=0.196, cua="ROLL", ua_libelle="Roll", ua_nombre=1.0, devise="DOL",
                        textes=["Etiquette 15 x 10 mm.", "spot toutes les 10 étiq.",
                                "Box:15 rolls of 2000 labels"]), True, 0.86)
check("1004/0128 : 0,196 USD/rouleau de 2000 → €/mille", r and r["prix"], 0.08428)
check("1004/0128 : la conversion est nommée", r and r["detail"], "2 000 étiq./rouleau · USD × 0.86")
check("1004/0128 : la source cite la commande", r and r["source"], "Achat RVGI n°1 · 04/08/2026")

check("au mille, en euros : repris tel quel", pa.prix_achat(achat(pun=18.3), True, 0.86)["prix"], 18.3)
check("au cent : ramené au mille", pa.prix_achat(achat(pun=2.0, cua="19", ua_libelle="Cent", ua_nombre=100.0), True, 0)["prix"], 20.0)
check("refus : rouleau sans nombre d'étiquettes",
      pa.prix_achat(achat(cua="ROLL", ua_libelle="Roll", ua_nombre=1.0), True, 0.86), None)
check("refus : dollars sans taux", pa.prix_achat(achat(devise="DOL"), True, 0), None)
check("refus : devise inconnue", pa.prix_achat(achat(devise="GBP"), True, 0.86), None)
check("refus : produit à l'unité acheté au mille", pa.prix_achat(achat(), False, 0.86), None)
check("bobine : « B1000/Etiq. 35 x 20 mm »", pa.etiquettes_par_rouleau("B1000/Etiq. 35 x 20 mm, 1 couleur."), 1000.0)
check("référence : « 1153/0005 - BOX DE 510 000 »", pa.cle_reference("1153/0005 - BOX DE 510 000"), "1153/0005")
v = pa.prix_achat(achat(pun=1.06, cua="5", ua_libelle="Bobine", ua_nombre=1.0, nature="Commande", numero=9931000,
                        date="2025-11-19", textes=["B1000/Etiq. 35 x 20 mm", "Bobine de 1000 étiquettes"]), True, 0.86)
check("vente 382/0100 : 1,06 €/bobine de 1000 → €/mille", v and v["prix"], 1.06)
check("vente : la source cite la commande client", v and v["source"], "Commande RVGI n°9931000 · 19/11/2025")
check("vente : origine commande", v and v["origine"], "commande_rvgi")
check("refus : vente au carton sans nombre d'étiquettes", pa.prix_achat(achat(cua="1", ua_libelle="Carton", ua_nombre=1.0, nature="Commande"), True, 0.86), None)
carton = dict(cua="1", ua_libelle="Carton", ua_nombre=1.0, nature="Commande", textes=["Carton de 13.500 étiquettes,"])
check("vente au carton de 13 500 → €/mille", round(pa.prix_achat(achat(pun=25.11, **carton), True, 0)["prix"], 4), 1.86)
check("carton : « C17.550/Etiquette »", pa.etiquettes_par_carton("C17.550/Etiquette 55 x 83 mm."), 17550.0)
check("produit au carton vendu au carton : repris tel quel",
      pa.prix_achat(achat(pun=44.9, **carton), False, 0, "carton", 570)["prix"], 44.9)
r = pa.prix_achat(achat(pun=45.455, **dict(carton, textes=["C17.550/Etiquette 55 x 83 mm."])), False, 0, "carton", 842400)
check("842 400 « cartons » de 17 550 : stock en étiquettes, prix à l'étiquette",
      r and round(r["prix"] * 842400, 2), 2181.82)
mille = dict(cua="11", ua_libelle="Mille", ua_nombre=1000.0, nature="Commande")
check("produit au carton vendu au mille : « Carton de 10 bobines soit 3.000 étiq. »",
      pa.prix_achat(achat(pun=4.97, textes=["Carton de 10 bobines soit 3.000 étiq."], **mille), False, 0, "carton", 100)["prix"], 14.91)
check("produit en bobine vendu au mille : « Bobine de 10.000 étiquettes »",
      pa.prix_achat(achat(pun=1.2, textes=["Bobine de 10.000 étiquettes"], **mille), False, 0, "bobine", 108)["prix"], 12.0)
check("refus : produit au carton vendu au mille sans nombre par carton",
      pa.prix_achat(achat(pun=4.97, **mille), False, 0, "carton", 100), None)
check("unité abrégée : « B 100 F » = « bobine 100 feuille »", pa.meme_unite("B 100 F", "bobine 100 feuille"), True)
check("contenants équivalents : boite = carton", pa.meme_unite("Boite", "carton"), True)
check("unités différentes : bobine ≠ carton", pa.meme_unite("Bobine", "carton"), False)
check("référence sans barre : « 10770035 »", pa.cle_reference("10770035"), "1077/0035")
t = pa.prix_achat(achat(pun=14.41, nature="Tarif", numero=None, date="2026-07-30"), True, 0)
check("tarif : source sans numéro", t and t["source"], "Tarif RVGI · 30/07/2026")
check("tarif : origine", t and t["origine"], "tarif_rvgi")
check("refus : produit en bobine vendu au carton",
      pa.prix_achat(achat(pun=44.9, **carton), False, 0, "bobine", 10), None)
check("produit à l'unité acheté à l'unité", pa.prix_achat(achat(pun=4.5, cua="U", ua_libelle="Unité", ua_nombre=1.0), False, 0)["prix"], 4.5)

print()
if FAIL:
    print("ÉCHEC : %d contrôle(s) en erreur" % len(FAIL))
    sys.exit(1)
print("Prix d'achat PF : tout est vert.")

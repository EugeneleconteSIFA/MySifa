"""
Paliers de quantite d'un devis, et recalage des temps devises.

Le piege que ce test garde : proratiser le calage. Monter un outil coute le
meme temps pour 100 000 que pour 1 000 000 d'etiquettes — c'est meme la raison
d'etre des paliers. Un recalage qui doublerait le calage avec la serie
afficherait un atelier « dans les temps » sur un dossier qui a derape.

Lancer : python3 tests/test_devis_paliers.py
"""

import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)

db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["DB_PATH"] = db
import config; config.DB_PATH = db                      # noqa: E402,E702
import database                                          # noqa: E402,F401
import app.core.database as dbmod                        # noqa: E402
dbmod.DB_PATH = db
with contextlib.redirect_stdout(io.StringIO()):
    dbmod.init_db()

from app.services.devis_paliers import (                 # noqa: E402
    ECART_MINI_PROPOSITION, palier_le_plus_proche, paliers_du_devis,
    proposition, recaler,
)

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(60) + f"{got}"
          + ("" if ok else f"   attendu {expected}"))
    if not ok:
        FAIL.append(label)


# Un devis reel : les temps sont calcules pour 500 000 ex.
DEVIS = {
    "id": 1, "qte_etiquettes": 500000.0,
    "temps_production_mn": 120.0, "metrage_production_ml": 6000.0,
    "temps_calage_mn": 90.0, "temps_calage_impression_mn": 60.0,
    "metrage_calage_ml": 400.0, "vitesse_theorique": 50.0, "gache": 300.0,
}

print("\n1. Recalage sur une autre quantite")

double = recaler(DEVIS, 1000000)
check("la quantite devient celle visee", double["qte_etiquettes"], 1000000.0)
check("le temps de production double", double["temps_production_mn"], 240.0)
check("le metrage double", double["metrage_production_ml"], 12000.0)
check("LE CALAGE OUTIL NE BOUGE PAS", double["temps_calage_mn"], 90.0)
check("LE CALAGE IMPRESSION NON PLUS", double["temps_calage_impression_mn"], 60.0)
check("le metrage de calage non plus", double["metrage_calage_ml"], 400.0)
check("la vitesse ne depend pas de la serie", double["vitesse_theorique"], 50.0)
check("la gache reste attachee au calage", double["gache"], 300.0)
check("le recalage se declare", double["recale"], True)
check("… avec son ratio", double["ratio_recalage"], 2.0)

tiers = recaler(DEVIS, 175000)
check("recalage vers le bas : temps", tiers["temps_production_mn"], 42.0)
check("recalage vers le bas : metrage", tiers["metrage_production_ml"], 2100.0)

egal = recaler(DEVIS, 500000)
check("meme quantite : rien n'est recale", egal["recale"], False)

print("\n2. Ce qui n'est pas recalculable")

sans = recaler({"qte_etiquettes": 0, "temps_production_mn": 120.0}, 900000)
check("quantite devisee inconnue : valeurs intactes",
      sans["temps_production_mn"], 120.0)
check("… et le dit", sans["recale"], False)
check("cible nulle : valeurs intactes",
      recaler(DEVIS, 0)["temps_production_mn"], 120.0)

print("\n3. Le palier le plus proche")

PALIERS = [{"rang": 1, "quantite": 500000.0, "prix_mille": 12.4},
           {"rang": 2, "quantite": 1000000.0, "prix_mille": 9.8}]

check("700 000 est relativement plus proche d'un million",
      palier_le_plus_proche(PALIERS, 700000)["rang"], 2)
check("520 000 reste sur le premier palier",
      palier_le_plus_proche(PALIERS, 520000)["rang"], 1)
check("sans palier, rien a proposer", palier_le_plus_proche([], 700000), None)
check("sans quantite non plus", palier_le_plus_proche(PALIERS, 0), None)

print("\n4. Quand proposer un recalage")

p = proposition(DEVIS, PALIERS, 1000000)
check("un facteur deux se propose", p["palier_rang"], 2)
check("… l'ecart est chiffre", p["ecart_pct"], 100.0)
check("… et le palier tombe pile", p["palier_exact"], True)
check("… avec son prix au mille", p["prix_mille"], 9.8)

entre = proposition(DEVIS, PALIERS, 700000)
check("entre deux paliers : on propose quand meme", entre["palier_rang"], 2)
check("… mais sans pretendre que le palier est exact", entre["palier_exact"], False)

check("un ecart de 4 % ne se propose pas", proposition(DEVIS, PALIERS, 520000), None)
check("le seuil est celui du garde-fou quantite", ECART_MINI_PROPOSITION, 0.10)
check("pas de quantite d'OF : rien", proposition(DEVIS, PALIERS, 0), None)

print("\n5. Lecture des paliers en base")

with dbmod.get_db() as conn:
    conn.execute("INSERT INTO devis (filename, imported_at) VALUES ('d.xlsx','2026-09-22')")
    did = conn.execute("SELECT id FROM devis ORDER BY id DESC LIMIT 1").fetchone()[0]
    autre = conn.execute(
        "INSERT INTO devis (filename, imported_at) VALUES ('autre.xlsx','2026-09-22')"
    ).lastrowid
    for devis_id, rang, qte, prix in ((did, 1, 500000, 12.4), (did, 2, 1000000, 9.8),
                                      (autre, 1, 42, 1.0)):
        conn.execute(
            "INSERT INTO devis_indicateurs (devis_id, libelle, valeur_nombre, cree_at) "
            "VALUES (?,?,?,?)",
            (devis_id, f"Quantité proposée (palier {rang})", qte, "2026-09-22"))
        conn.execute(
            "INSERT INTO devis_indicateurs (devis_id, libelle, valeur_nombre, cree_at) "
            "VALUES (?,?,?,?)",
            (devis_id, f"Prix au mille (palier {rang})", prix, "2026-09-22"))
    conn.commit()
    lus = paliers_du_devis(conn, did)

check("les deux paliers sont relus", len(lus), 2)
check("dans l'ordre des rangs", [p["rang"] for p in lus], [1, 2])
check("avec leur quantite", [p["quantite"] for p in lus], [500000.0, 1000000.0])
check("et leur prix", [p["prix_mille"] for p in lus], [12.4, 9.8])
check("CEUX D'UN AUTRE DEVIS NE REMONTENT PAS",
      all(p["quantite"] != 42.0 for p in lus), True)

print("\n6. Le contrat de l'ecran : proposer, pas trancher")

# Lu en texte : le routeur tire FastAPI, pas toujours installe sur le poste.
ROUTEUR = (RACINE / "app" / "routers" / "rentabilite.py").read_text(encoding="utf-8")
_d = ROUTEUR.index("def _palier_du_lien")
FONCTION = ROUTEUR[_d:ROUTEUR.index("def _qte_of")]

check("le recalage exige une validation", "and valide:" in FONCTION, True)
check("sans validation, le devis est rendu intact",
      'return {\n        "devis": dict(devis_row),' in FONCTION, True)
check("la quantite de reference vient de l'OF",
      "o.qte_etiquettes AS q" in ROUTEUR, True)
check("l'ecran peut afficher le chiffre d'origine",
      '"devis_origine"' in ROUTEUR, True)
check("annuler un recalage est possible",
      'qte_retenue=NULL' in ROUTEUR, True)

JS = (RACINE / "static" / "mysifa_prod_core.js").read_text(encoding="utf-8")
check("le bouton de recalage existe", "rentRetenirPalier" in JS, True)
check("le retour au classeur aussi", "rentAnnulerPalier" in JS, True)

print("")
if FAIL:
    print("ECHECS : " + ", ".join(FAIL))
    sys.exit(1)
print("TOUT EST VERT")

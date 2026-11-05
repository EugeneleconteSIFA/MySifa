"""
MyTools › Calculs bobine › Carton — lecture des références carton de MyStock.

Lancer : python3 tests/test_tools_cartons.py

Verrouille la lecture des dimensions dans les désignations réelles (mm, cm,
« X » majuscule, décimales à virgule ou point, préfixe « Boîte », « Conteneur »,
référence fournisseur), et le tri : couvercles et intercalaires écartés,
désignations sans dimensions écartées, matières d'une autre catégorie ignorées.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_cartons_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  — d'abord, toujours (CLAUDE.md)
from database import get_db  # noqa: E402
from app.services import cartons  # noqa: E402


class Dimensions(unittest.TestCase):
    CAS = {
        "Carton 385 x 385 x 208 mm": (385, 385, 208),
        "385 X 385 X 105 mm": (385, 385, 105),
        "Boîte 305 x 215 x 150 mm fond & couvercle": (305, 215, 150),
        "Carton RAJA CAS14 31x21.5x5.5 cm": (310, 215, 55),
        "Rajaposte brun 31 x 21,5 x 10 cm": (310, 215, 100),
        "Conteneur grand box 1180 x 780 x 1070 mm": (1180, 780, 1070),
        "305 x 210 x 80 F&C": (305, 210, 80),
    }

    def test_designations_reelles(self):
        for texte, attendu in self.CAS.items():
            self.assertEqual(cartons.dimensions(texte), attendu, texte)

    def test_illisible(self):
        self.assertIsNone(cartons.dimensions("Intercalaire Grand Box/Palette"))
        self.assertIsNone(cartons.dimensions("A voir selon stock"))


class Liste(unittest.TestCase):
    def test_tri(self):
        with get_db() as c:
            for cat, ref, des in [
                ("carton", "385 x 385 x 208 mm", "Carton 385 x 385 x 208 mm"),
                ("carton", "Couvercle 213 x 128 x 80 mm", "Couvercle 213 x 128 x 80 mm"),
                ("carton", "Intercalaire Grand Box/Palette", "Intercalaire grand box 1175 x 775 mm"),
                ("carton", "Sans dim", "Boîte spéciale client"),
                ("mandrin", "Tube 76 x 3 x 1500", "Tube 76 x 3 x 1500 mm"),
            ]:
                c.execute("INSERT INTO matieres_premieres (categorie, reference, designation, actif) VALUES (?,?,?,1)",
                          (cat, ref, des))
            c.commit()
            d = cartons.liste(c)
        libelles = [x["libelle"] for x in d["cartons"]]
        self.assertIn("Carton 385 x 385 x 208 mm", libelles)
        self.assertFalse(any("Couvercle" in x or "Intercalaire" in x or "Tube" in x for x in libelles))
        raisons = {x["libelle"]: x["raison"] for x in d["ecartes"]}
        self.assertEqual(raisons.get("Boîte spéciale client"), "dimensions illisibles")
        self.assertEqual(raisons.get("Couvercle 213 x 128 x 80 mm"), "sans volume utile")


class Couches(unittest.TestCase):
    """GET /api/tools/couches : frontaux, adhésifs, glassines et leur épaisseur."""

    def test_epaisseurs_et_sources(self):
        from app.services import couches_matieres
        with get_db() as c:
            ids = {}
            for cat, des, ep, gsm in [
                ("frontal", "Thermique test 70g", 72, 70),
                ("adhesif", "Adhésif test 20g", None, 20),
                ("glassine", "Glassine test 62g", None, 62),
                ("frontal", "Couché test", None, None),
                ("carton", "Carton 100 x 100 x 100 mm", None, None),
            ]:
                cur = c.execute("INSERT INTO matieres_premieres (categorie, reference, designation, actif, epaisseur_um, weight_gsm) "
                                "VALUES (?,?,?,1,?,?)", (cat, des, des, ep, gsm))
                ids[des] = cur.lastrowid
            # La fiche technique l'emporte sur MyStock.
            c.execute("INSERT INTO mp_fiche_technique (objet, objet_id, data) VALUES ('matiere', ?, ?)",
                      (ids["Glassine test 62g"], '{"epaisseur_um": "52"}'))
            c.commit()
            d = couches_matieres.liste(c)
        cats = [x["categorie"] for x in d["couches"]]
        self.assertEqual(cats, ["frontal", "adhesif", "glassine"])
        tout = {m["libelle"]: m for x in d["couches"] for m in x["matieres"]}
        self.assertNotIn("Carton 100 x 100 x 100 mm", tout)
        self.assertEqual(tout["Thermique test 70g"]["epaisseur_um"], 72)
        self.assertEqual(tout["Thermique test 70g"]["source"], "MyStock")
        self.assertEqual(tout["Glassine test 62g"]["epaisseur_um"], 52)
        self.assertEqual(tout["Glassine test 62g"]["source"], "Fiche technique")
        # Aucune déduction depuis le grammage : inconnue, grammage rendu pour l'écran.
        self.assertIsNone(tout["Adhésif test 20g"]["epaisseur_um"])
        self.assertEqual(tout["Adhésif test 20g"]["grammage_gsm"], 20)


if __name__ == "__main__":
    unittest.main(verbosity=1)

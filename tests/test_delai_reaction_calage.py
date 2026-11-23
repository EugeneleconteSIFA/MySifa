"""
Délai de réaction au passage calage → production.

Cas réel : 9932856 - L1 (Cohésio 1, 20/11/2026). Calage cliqué à 18:43:54,
« Production » à 18:53:09, fin à 18:58:00, 687 m au compteur. Sans correction,
4,8 min de production : 143 m/min affichés pour une machine qui tourne autour
de 100. Le clic « Production » arrive après le vrai démarrage.

Ce que le test garde :
1. un calage suivi d'une production du même dossier rend le délai à la
   production (9,25 min de calage → 6,25 ; 4,8 min de production → 7,8) ;
2. le délai ne dépasse jamais la durée du calage (L3 : 1,6 min de calage) ;
3. un calage suivi d'autre chose qu'une production ne bouge pas ;
4. délai à 0 : rien ne change.

Lancer : python3 tests/test_delai_reaction_calage.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base_temporaire  # noqa: E402,F401  — base jetable, avant tout le reste
import database  # noqa: E402,F401  — toujours avant app.*
import config  # noqa: E402

from app.services.timings import compute_dossier_times  # noqa: E402

OP = "Tony Cathelineau"


def saisies(*lignes):
    out = []
    for i, (heure, code, dossier, cat) in enumerate(lignes, start=1):
        out.append({"id": i, "operateur": OP, "date_operation": "2026-11-20T" + heure,
                    "operation_code": code, "no_dossier": dossier, "operation_category": cat,
                    "machine": "Cohésio 1"})
    return out


L1 = saisies(
    ("18:43:52", "01", "9932856 - L1", "personnel"),
    ("18:43:54", "02", "9932856 - L1", "calage"),
    ("18:53:09", "03", "9932856 - L1", "production"),
    ("18:58:00", "89", "9932856 - L1", "personnel"),
    ("18:59:26", "87", "", "personnel"),
)
L3 = saisies(
    ("16:23:48", "01", "9932856 - L3", "personnel"),
    ("16:23:51", "02", "9932856 - L3", "calage"),
    ("16:25:26", "03", "9932856 - L3", "production"),
    ("16:29:00", "89", "9932856 - L3", "personnel"),
)
CALAGE_PUIS_ARRET = saisies(
    ("08:00:00", "01", "D1", "personnel"),
    ("08:00:10", "02", "D1", "calage"),
    ("08:30:10", "53", "D1", "arret"),
    ("08:40:10", "03", "D1", "production"),
    ("09:40:10", "89", "D1", "personnel"),
)


def temps(rows, delai):
    ancien = config.PROD_DELAI_REACTION_CALAGE_MIN
    config.PROD_DELAI_REACTION_CALAGE_MIN = delai
    try:
        return [d for d in compute_dossier_times(rows) if d["no_dossier"]][0]
    finally:
        config.PROD_DELAI_REACTION_CALAGE_MIN = ancien


class TestDelaiReaction(unittest.TestCase):
    def test_rendu_a_la_production(self):
        t = temps(L1, 3)
        self.assertAlmostEqual(t["temps_calage_min"], 6.25, delta=0.06)
        self.assertAlmostEqual(t["temps_prod_min"], 7.8, places=1)
        self.assertEqual(t["delai_reaction_min"], 3.0)
        # 687 m : de 143 m/min à 88 m/min.
        self.assertLess(687 / t["temps_prod_min"], 100)

    def test_plafonne_au_calage(self):
        t = temps(L3, 3)
        self.assertEqual(t["temps_calage_min"], 0.0)
        self.assertAlmostEqual(t["delai_reaction_min"], 1.6, places=1)

    def test_calage_suivi_d_un_arret(self):
        t = temps(CALAGE_PUIS_ARRET, 3)
        self.assertAlmostEqual(t["temps_calage_min"], 30.0, places=1)
        self.assertAlmostEqual(t["temps_prod_min"], 60.0, places=1)
        self.assertEqual(t["delai_reaction_min"], 0.0)

    def test_desactive(self):
        t = temps(L1, 0)
        self.assertAlmostEqual(t["temps_calage_min"], 9.25, delta=0.06)
        self.assertAlmostEqual(t["temps_prod_min"], 4.8, places=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)

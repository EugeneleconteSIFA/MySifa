"""
Répartir un cycle de production sur plusieurs dossiers d'une même commande.

Cas réel du 20/11/2026 (Cohésio 1) : reprise de « 9932856 - L8 » à 6 h 39,
L8 puis L5 et L7 enchaînés sans changer de dossier, fin de production à 13 h
avec 19 162 m. Ce que le test protège :

1. L'aperçu propose les autres lignes de la commande sur la même machine,
   avec la quantité de leur OF, et pas les dossiers d'une autre commande.
2. Le découpage suit le prorata des quantités : heures et compteurs des
   coupures, le dernier segment finit sur la fin de production d'origine.
3. L'application crée fin / démarrage / production à chaque coupure, déplace
   l'arrêt saisi pendant le cycle dans le dossier où il tombe, et clôture
   chaque dossier au planning.
4. Les erreurs de saisie sont refusées : premier dossier différent du cycle,
   dossier d'une autre commande, quantité nulle.

Lancer : python3 tests/test_repartition_saisie.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base_temporaire  # noqa: E402,F401  — base jetable, avant tout le reste
import database  # noqa: E402,F401  — toujours avant app.*

MACHINE_ID = 90411
MACHINE = "Test Répartition"


def _saisie(conn, date, code, op, dossier, **champs):
    from config import classify_operation
    cl = classify_operation(op)
    cols = ["operateur", "date_operation", "operation", "operation_code",
            "operation_severity", "operation_category", "machine", "no_dossier",
            "client", "quantite_traitee", "data"]
    vals = ["907 - Opérateur matin", date, op, cl["code"], cl["severity"], cl["category"],
            MACHINE, dossier, "CLIENT TEST", champs.pop("quantite_traitee", 0), "{}"]
    for k, v in champs.items():
        cols.append(k)
        vals.append(v)
    return conn.execute(
        f"INSERT INTO production_data ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
        vals).lastrowid


class TestRepartition(unittest.TestCase):
    def setUp(self):
        from database import get_db
        with get_db() as conn:
            conn.execute("INSERT OR REPLACE INTO machines (id, nom, code, actif) VALUES (?,?,?,1)",
                         (MACHINE_ID, MACHINE, "TRP"))
            conn.execute("DELETE FROM planning_entries WHERE machine_id=?", (MACHINE_ID,))
            conn.execute("DELETE FROM production_data WHERE machine=?", (MACHINE,))
            self.pe = {}
            for pos, (ref, qte) in enumerate([("9932856 - L8", 783000), ("9932856 - L5", 1080000),
                                              ("9932856 - L7", 909000), ("9932999 - L1", 5000)]):
                of_id = conn.execute(
                    "INSERT INTO of_imports (of_numero, qte_etiquettes, date_import, statut) VALUES (?,?,?,?)",
                    (ref, qte, "2026-11-09T15:00:00", "valide")).lastrowid
                self.pe[ref] = conn.execute(
                    """INSERT INTO planning_entries (machine_id, position, reference, client,
                       duree_heures, statut, created_at, updated_at, of_import_id)
                       VALUES (?,?,?,?,2,'attente','2026-11-09T15:00:00','2026-11-09T15:00:00',?)""",
                    (MACHINE_ID, pos + 1, ref, "PERIMEDIAS", of_id)).lastrowid
            _saisie(conn, "2026-11-20T06:34:10", "01", "01 - Démarrer un dossier", "9932856 - L8",
                    metrage_total_debut=7823062)
            _saisie(conn, "2026-11-20T06:39:53", "03", "03 - Production", "9932856 - L8")
            # Arrêt pendant le cycle, vers 11 h 30 : il tombe dans L7.
            self.arret = _saisie(conn, "2026-11-20T11:30:00", "53", "53 - Casse bande", "9932856 - L8")
            _saisie(conn, "2026-11-20T11:40:00", "88", "88 - Reprise production", "9932856 - L8")
            self.fin = _saisie(conn, "2026-11-20T13:00:00", "89", "89 - Fin de production", "9932856 - L8",
                               quantite_traitee=0, metrage_total_fin=7842224, metrage_reel=7842224,
                               fin_dossier=1)
            conn.commit()

    def parts(self):
        return [{"no_dossier": "9932856 - L8", "quantite": 783000},
                {"no_dossier": "9932856 - L5", "quantite": 1080000},
                {"no_dossier": "9932856 - L7", "quantite": 909000}]

    def test_apercu_propose_la_commande(self):
        from database import get_db
        from app.services.repartition_saisie import apercu
        with get_db() as conn:
            ap = apercu(conn, self.fin)
        noms = [c["no_dossier"] for c in ap["candidats"]]
        self.assertEqual(noms, ["9932856 - L5", "9932856 - L7"])
        self.assertEqual(ap["candidats"][0]["qte_of"], 1080000)
        self.assertEqual(ap["metres"], 19162)
        self.assertEqual(ap["debut"], "2026-11-20T06:39:53")

    def test_plan_au_prorata(self):
        from database import get_db
        from app.services.repartition_saisie import plan
        with get_db() as conn:
            p = plan(conn, self.fin, self.parts())
        s = p["segments"]
        self.assertEqual([x["no_dossier"] for x in s], ["9932856 - L8", "9932856 - L5", "9932856 - L7"])
        # 6 h 20 min 07 s de cycle, L8 = 783 / 2 772 de la quantité.
        self.assertEqual(s[0]["fin"], "2026-11-20T08:27:15")
        self.assertEqual(s[2]["fin"], "2026-11-20T13:00:00")
        self.assertEqual(s[0]["compteur_debut"], 7823062)
        self.assertEqual(s[2]["compteur_fin"], 7842224)
        self.assertEqual(sum(x["metres"] for x in s), 19162)

    def test_appliquer(self):
        from database import get_db
        from app.services.repartition_saisie import appliquer
        with get_db() as conn:
            res = appliquer(conn, self.fin, self.parts(), "test@exemple.fr", "Testeur")
            self.assertEqual(len(res["crees"]), 6)
            lignes = [dict(r) for r in conn.execute(
                """SELECT date_operation, operation_code, no_dossier, quantite_traitee,
                          metrage_total_debut, metrage_total_fin, fin_dossier, est_manuel
                     FROM production_data WHERE machine=? ORDER BY date_operation, id""",
                (MACHINE,)).fetchall()]
            fins = [l for l in lignes if l["operation_code"] == "89"]
            self.assertEqual([(f["no_dossier"], f["quantite_traitee"]) for f in fins],
                             [("9932856 - L8", 783000), ("9932856 - L5", 1080000),
                              ("9932856 - L7", 909000)])
            self.assertTrue(all(f["fin_dossier"] == 1 for f in fins))
            deb_l5 = next(l for l in lignes if l["operation_code"] == "01" and l["no_dossier"].endswith("L5"))
            self.assertEqual(deb_l5["metrage_total_debut"], fins[0]["metrage_total_fin"])
            arret = conn.execute("SELECT no_dossier FROM production_data WHERE id=?",
                                 (self.arret,)).fetchone()[0]
            self.assertEqual(arret, "9932856 - L7")
            statuts = {ref: conn.execute("SELECT statut FROM planning_entries WHERE id=?",
                                         (pid,)).fetchone()[0] for ref, pid in self.pe.items()}
        self.assertEqual(statuts["9932856 - L5"], "termine")
        self.assertEqual(statuts["9932856 - L7"], "termine")
        self.assertEqual(statuts["9932999 - L1"], "attente")

    def test_refus(self):
        from database import get_db
        from app.services.repartition_saisie import plan
        with get_db() as conn:
            with self.assertRaises(ValueError):
                plan(conn, self.fin, list(reversed(self.parts())))
            with self.assertRaises(ValueError):
                plan(conn, self.fin, self.parts()[:1] + [{"no_dossier": "9932999 - L1", "quantite": 5000}])
            with self.assertRaises(ValueError):
                plan(conn, self.fin, self.parts()[:1] + [{"no_dossier": "9932856 - L5", "quantite": 0}])


if __name__ == "__main__":
    unittest.main(verbosity=2)

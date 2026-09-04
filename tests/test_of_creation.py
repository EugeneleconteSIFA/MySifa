"""Créer un OF et une fiche technique DANS MySifa.

Ce que ces tests protègent, et pourquoi chacun existe :

1. Le numéro d'un OF se PROPOSE depuis les commandes rattachées. C'est la règle
   des dossiers de fabrication, et la reproduire à la main côté client (ou la
   remplacer par un compteur) romprait le lien commande ↔ OF ↔ dossier que tout
   le rapprochement suppose.
2. `rvgi_rattachements` doit accepter `objet = 'of'`. La table est née avec un
   CHECK en dur à deux valeurs ; l'oublier fait échouer la création par une
   IntegrityError, au moment précis où l'ADV valide sa saisie.
3. Un OF de MySifa ne « couvre » pas une ligne de commande au sens du reliquat.
   Sans cette exception, le premier dossier issu d'un OF naîtrait « Reliquat ».
4. Ce qui est saisi est marqué manuel et le document reste à valider — c'est le
   contrat de `documents_verite`, et c'est ce qui empêche Access de réécrire
   par-dessus une saisie humaine.

Lancement : `python3 tests/test_of_creation.py`
"""

import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import rvgi_rattachement as ratt  # noqa: E402


def _base_rattachements(chemin):
    """Une base minimale portant la table telle que la migration la laisse."""
    conn = sqlite3.connect(chemin)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE rvgi_rattachements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        objet TEXT NOT NULL CHECK (objet IN ('dossier','depart','of')),
        objet_id INTEGER NOT NULL,
        piece TEXT NOT NULL CHECK (piece IN ('commande','livraison')),
        numero TEXT NOT NULL, ligne INTEGER, qte REAL,
        etat TEXT NOT NULL DEFAULT 'confirme' CHECK (etat IN ('confirme','a_verifier')),
        vu_qte REAL, vu_article TEXT, vu_client TEXT,
        cree_le TEXT NOT NULL, cree_par TEXT, confirme_le TEXT, note TEXT,
        UNIQUE(objet, objet_id, piece, numero, ligne))""")
    conn.execute("""CREATE TABLE of_imports (
        id INTEGER PRIMARY KEY, of_numero TEXT, reference TEXT,
        cmd_rvgi TEXT, rvgi_etat TEXT, rvgi_maj_le TEXT)""")
    conn.execute("""CREATE TABLE planning_entries (
        id INTEGER PRIMARY KEY, reference TEXT, numero_of TEXT,
        dos_rvgi TEXT, rvgi_etat TEXT, rvgi_maj_le TEXT)""")
    conn.execute("INSERT INTO of_imports (id, of_numero) VALUES (1, NULL)")
    conn.execute("INSERT INTO planning_entries (id, reference) VALUES (1, 'D1')")
    conn.commit()
    return conn


class TestNumeroProposeDepuisCommandes(unittest.TestCase):
    """Le numéro d'OF n'est pas inventé : il décrit ce qu'il couvre."""

    def test_une_commande_entiere(self):
        self.assertEqual(
            ratt.proposer_reference([{"numero": "9932128", "ligne": 1}],
                                    {"9932128": 1}),
            "9932128",
        )

    def test_quelques_lignes_d_une_commande(self):
        self.assertEqual(
            ratt.proposer_reference(
                [{"numero": "9932128", "ligne": 1}, {"numero": "9932128", "ligne": 3}],
                {"9932128": 6}),
            "9932128/L1+3",
        )

    def test_plusieurs_commandes(self):
        self.assertEqual(
            ratt.proposer_reference([{"numero": "9932128", "ligne": 1},
                                     {"numero": "9932129", "ligne": 1}]),
            "9932128+129",
        )

    def test_sans_commande_aucune_proposition(self):
        # C'est ce qui fait répondre 400 à la création : mieux vaut refuser que
        # produire un OF dont le numéro ne veut rien dire.
        self.assertEqual(ratt.proposer_reference([]), "")


class TestRattachementDUnOf(unittest.TestCase):

    def setUp(self):
        self.fichier = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        self.conn = _base_rattachements(self.fichier)

    def tearDown(self):
        self.conn.close()
        try:
            os.unlink(self.fichier)
        except OSError:
            pass

    def test_un_of_se_rattache_et_pose_son_etat(self):
        res = ratt.enregistrer(
            self.conn, "of", 1, "commande",
            [{"numero": "9932128", "ligne": 1, "confirme": True},
             {"numero": "9932129", "ligne": 2, "confirme": True}],
            "essai",
        )
        self.assertEqual(res["etat"], "lie")
        self.assertEqual(res["rattachements"], 2)
        ligne = self.conn.execute(
            "SELECT cmd_rvgi, rvgi_etat FROM of_imports WHERE id=1").fetchone()
        # La vitrine texte de l'OF, comme dos_rvgi pour un dossier.
        self.assertEqual(ligne["cmd_rvgi"], "9932128+129")
        self.assertEqual(ligne["rvgi_etat"], "lie")

    def test_un_of_ne_fait_pas_reliquat(self):
        lignes = [{"numero": "9932128", "ligne": 1, "confirme": True}]
        ratt.enregistrer(self.conn, "of", 1, "commande", lignes, "essai")
        # Le dossier qui sort de cet OF pointe la même ligne : il ne doit pas
        # naître « Reliquat 9932128 ».
        self.assertFalse(ratt.deja_couvertes(self.conn, lignes, "commande"))

    def test_un_dossier_deja_passe_fait_reliquat(self):
        lignes = [{"numero": "9932128", "ligne": 1, "confirme": True}]
        ratt.enregistrer(self.conn, "dossier", 1, "commande", lignes, "essai")
        self.assertTrue(ratt.deja_couvertes(self.conn, lignes, "commande"))

    def test_objet_inconnu_refuse(self):
        with self.assertRaises(ValueError):
            ratt.enregistrer(self.conn, "chose", 1, "commande", [], "essai")


class TestReferenceArticle(unittest.TestCase):
    """« 1026/0020 » est le couple code1/code2 d'un article de RVGI."""

    def test_reference_simple(self):
        self.assertEqual(ratt.couper_reference("1026/0020"), ("1026", "0020"))

    def test_suffixe_machine_ignore(self):
        self.assertEqual(ratt.couper_reference("1026/0020 - COHESIO 1"),
                         ("1026", "0020"))

    def test_zeros_de_tete_conserves(self):
        # « 0020 » et « 20 » sont deux articles différents dans l'ERP.
        self.assertEqual(ratt.couper_reference("1026/0020")[1], "0020")

    def test_ce_qui_n_est_pas_une_reference(self):
        for valeur in ("", None, "ABC", "1026", "1026/", "/0020", "1026/ABC"):
            self.assertIsNone(ratt.couper_reference(valeur), valeur)


class TestModeleOf(unittest.TestCase):
    """Le PDF d'un OF sans document d'origine."""

    def test_valeurs_posees_sur_le_modele(self):
        try:
            from app.services.of_pdf_generator import generate_of_pdf
        except ImportError as e:            # reportlab/pypdf absents
            self.skipTest(str(e))
        chemin = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data", "of_template.pdf")
        if not os.path.isfile(chemin):
            self.skipTest("modèle data/of_template.pdf absent")
        pdf = generate_of_pdf(
            {"of_numero": "9932128", "reference": "1026/0020", "laize": 470,
             "qte_etiquettes": 400000},
            template_path=chemin,
        )
        self.assertTrue(pdf.startswith(b"%PDF"))
        # Un « QQ » dans le flux fusionné fait afficher la page SANS aucune
        # valeur, sans erreur serveur : c'est le piège que _terminer_le_flux évite.
        self.assertNotIn(b"n Qq", pdf[:200])


if __name__ == "__main__":
    unittest.main(verbosity=2)

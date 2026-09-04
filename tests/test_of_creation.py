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
from app.services import rvgi_article_fiche as raf  # noqa: E402


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


class TestPrefillDepuisRvgi(unittest.TestCase):
    """La fiche technique déduite de l'article, vérifiée sur un document réel.

    Les valeurs attendues ne sortent pas du code : elles sont relevées sur la
    fiche de fabrication papier de 623/0014, celle que l'atelier utilise. C'est
    ce qui donne son sens au test — si un jour la lecture de `out_dec` change,
    c'est cette fiche-là qui doit continuer de tomber juste.
    """

    def setUp(self):
        self.fichier = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        c = sqlite3.connect(self.fichier)
        c.row_factory = sqlite3.Row
        c.execute("CREATE TABLE fic_art (corbeille INT, code1 TEXT, code2 TEXT, "
                  "libc1 TEXT, libc2 TEXT, libc3 TEXT, libc4 TEXT, cltc2 TEXT, "
                  "ftl REAL, fth REAL, pdsn REAL)")
        c.execute("CREATE TABLE gpr_ff (corbeille INT, code1 TEXT, code2 TEXT, "
                  "nmac1 INT, laiout REAL, laimat REAL, nbcoul INT, cliche TEXT, "
                  "m1cod1 TEXT, m1cod2 TEXT, ndec1 INT, ndec2 INT, ndec3 INT, amj TEXT)")
        c.execute("CREATE TABLE out_dec (corbeille INT, numero INT, machine INT, "
                  "nbd INT, nbl INT, nba INT, nbt INT, ftl REAL, fta REAL, lt REAL, "
                  "at REAL, espl REAL, espa REAL, eche REAL, ray REAL, eps REAL, hcou1 REAL)")
        c.execute("CREATE TABLE mat_mat (corbeille INT, code1 TEXT, code2 TEXT, "
                  "libc1 TEXT, libc2 TEXT, pds REAL, m1_epais REAL, m1_adh TEXT, m1_pro TEXT)")
        c.execute("CREATE TABLE mac_pro (corbeille INT, type INT, code INT, nom TEXT)")
        # Les quatre libellés tels qu'ils sont en production. `libc3` est mot
        # pour mot le conditionnement imprimé sur l'OF, `libc4` donne le
        # nombre de bobines par carton de la fiche.
        c.execute("INSERT INTO fic_art VALUES (0,'623','0014',"
                  "'Etiquette 105 x 148 mm.','Thermique Eco Permanent.',"
                  "'Bobine de 300 étiquettes, M. 25.','Carton de 16 bobines',"
                  "'REF-CLT',104.5,148.4,0)")
        c.execute("INSERT INTO gpr_ff VALUES (0,'623','0014',1,0,440.0,0,NULL,"
                  "'886','0021',2796,0,0,'2026-01-30 11:44:09')")
        c.execute("INSERT INTO out_dec VALUES (0,2796,1,192,4,4,16,104.5,148.4,"
                  "443.75,609.6,3.25,4.0,16.0,6.0,52,450)")
        c.execute("INSERT INTO mat_mat VALUES (0,'886','0021','Thermique Eco 70g',"
                  "'Permanent 19g, Jaune 60g Standard',149.0,0.0,'Permanent 19g',"
                  "'Jaune 60g Standard')")
        c.execute("INSERT INTO mac_pro VALUES (0,1,1,'COHESIO 1')")
        c.commit()
        self.conn = c

        import contextlib

        @contextlib.contextmanager
        def faux_miroir(avec_mysifa=False):
            yield c

        self._vrai = raf.miroir.get_erp_db
        self._vraies_tables = raf.miroir.tables_presentes
        raf.miroir.get_erp_db = faux_miroir
        raf.miroir.tables_presentes = lambda conn: {
            "fic_art", "gpr_ff", "out_dec", "mat_mat", "mac_pro"}

    def tearDown(self):
        raf.miroir.get_erp_db = self._vrai
        raf.miroir.tables_presentes = self._vraies_tables
        self.conn.close()
        try:
            os.unlink(self.fichier)
        except OSError:
            pass

    def test_geometrie_conforme_a_la_fiche_papier(self):
        champs = raf.prefill_fiche("623", "0014")["champs"]
        attendu = {
            # ÉTIQUETTE
            "eti_laize": 104.5, "eti_longueur": 148.4, "eti_rayons": 6.0,
            # MODULE = étiquette + espacement
            "mod_laize": 107.75, "mod_longueur": 152.4,
            # ÉCHENILLAGE — le latéral extérieur vaut la moitié de l'espacement
            "lateral_int": 3.25, "horizontal": 4.0, "lateral_ext": 1.625,
            # OUTIL 1
            "outil1_numero_sifa": "2796", "outil1_nb_dents": 192,
            "outil1_nb_front": 4, "outil1_nb_avance": 4,
            "outil1_epaisseur": 52.0, "outil1_laize": 440.0,
            # MATIÈRE
            "support": "Thermique Eco 70g", "adhesif": "Permanent 19g",
            "glassine": "Jaune 60g Standard", "grammage": 149.0,
            "machine": "COHESIO 1", "laize_optimale": 440.0,
        }
        for cle, val in attendu.items():
            self.assertEqual(champs.get(cle), val, cle)

    def test_le_nombre_de_fronts_ne_va_pas_dans_mod_nb_front(self):
        # `mod_nb_front` vaut 1 sur 878 fiches sur 909 en production : ce n'est
        # pas une donnée. Le vrai nombre de fronts est celui de l'outil.
        champs = raf.prefill_fiche("623", "0014")["champs"]
        self.assertNotIn("mod_nb_front", champs)
        self.assertEqual(champs["outil1_nb_front"], 4)

    def test_un_zero_de_rvgi_ne_devient_pas_une_valeur(self):
        # laiout = 0 et nbcoul = 0 sont des cases vides du logiciel. Les
        # recopier écrirait un zéro qui se lit ensuite comme vérifié.
        champs = raf.prefill_fiche("623", "0014")["champs"]
        self.assertNotIn("laize_optionnelle", champs)
        self.assertNotIn("nb_couleurs", champs)

    def test_chaque_champ_dit_d_ou_il_vient(self):
        res = raf.prefill_fiche("623", "0014")
        self.assertEqual(set(res["champs"]), set(res["provenance"]))
        self.assertEqual(res["provenance"]["eti_laize"], "out_dec")
        self.assertEqual(res["provenance"]["support"], "mat_mat")
        self.assertEqual(res["provenance"]["qte_au_mille"], "calcul")

    def test_sans_fiche_de_fabrication_on_le_dit(self):
        self.conn.execute("DELETE FROM gpr_ff")
        self.conn.commit()
        res = raf.prefill_fiche("623", "0014")
        self.assertTrue(res["manques"])
        self.assertNotIn("outil1_nb_front", res["champs"])
        # Le libellé et le format de l'article restent, eux.
        self.assertEqual(res["champs"]["eti_laize"], 104.5)

    def test_les_libelles_donnent_le_produit_fini(self):
        # « Bobine de 300 étiquettes, M. 25. » et « Carton de 16 bobines » :
        # trois valeurs de la fiche, dans des phrases. C'est ce que l'écran
        # MyERP affiche sous « Libellés », et c'est exploitable.
        champs = raf.prefill_fiche("623", "0014")["champs"]
        self.assertEqual(champs["conditionnement"], "Bobine de 300 étiquettes, M. 25")
        self.assertEqual(champs["nb_etiq_bobin"], 300)
        self.assertEqual(champs["nb_bobines_carton"], 16)
        self.assertEqual(champs["mandrin_dia"], "25")

    def test_of_depuis_le_meme_article(self):
        res = raf.prefill_of("623", "0014")
        champs = res["champs"]
        self.assertEqual(champs["reference"], "623/0014")
        self.assertEqual(champs["machine"], "COHESIO 1")
        # La « Laize » de l'OF est celle de la bobine montée, pas celle de
        # l'outil : 440 et non 443,75.
        self.assertEqual(champs["laize"], 440.0)
        self.assertEqual(champs["outil_1_numero"], "2796")
        self.assertEqual(champs["outil_1_hauteur"], 450.0)
        self.assertEqual(champs["conditionnement"], "Bobine de 300 étiquettes, M. 25")
        self.assertEqual(champs["matiere"], "Thermique Eco 70g")
        self.assertEqual(champs["glassine"], "Jaune 60g Standard")
        self.assertEqual(champs["adhesif_label"], "Permanent 19g")
        # Le chiffre encadré en orange sur l'OF, extrait du libellé matière.
        self.assertEqual(champs["qte_adhesif_g"], 19.0)
        # 1000 étiquettes ÷ 4 fronts × 152,4 mm = 38,1 m
        self.assertEqual(champs["qte_au_mille"], 38.1)

    def test_grammage_adhesif(self):
        self.assertEqual(raf._grammage_adhesif("Permanent 19g"), 19.0)
        self.assertEqual(raf._grammage_adhesif("Enlevable 1408 - 22"), None)
        self.assertEqual(raf._grammage_adhesif(None), None)

    def test_article_inconnu(self):
        self.assertIsNone(raf.prefill_fiche("999", "9999"))
        self.assertIsNone(raf.prefill_of("999", "9999"))


class TestRepliSurOfPrecedent(unittest.TestCase):
    """Sans fiche de fabrication RVGI, l'OF précédent prend le relais.

    C'est le cas MAJORITAIRE : `gpr_ff` ne couvre que 585 articles sur 7 688.
    Sans ce repli, le bouton « reprendre l'article » ne remplirait presque
    rien sur la plupart des commandes, et l'ADV retournerait à la recopie.
    """

    def setUp(self):
        self.fichier = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
        c = sqlite3.connect(self.fichier)
        c.row_factory = sqlite3.Row
        c.execute("""CREATE TABLE of_imports (
            id INTEGER PRIMARY KEY, of_numero TEXT, reference TEXT, machine TEXT,
            laize REAL, matiere TEXT, glassine TEXT, adhesif_label TEXT,
            conditionnement TEXT, outil_1_numero TEXT, outil_1_hauteur REAL,
            qte_etiquettes INTEGER, date_creation TEXT, date_import TEXT,
            matiere_ref_id INTEGER)""")
        c.execute("INSERT INTO of_imports (of_numero, reference, machine, laize, "
                  "matiere, glassine, adhesif_label, conditionnement, "
                  "outil_1_numero, outil_1_hauteur, qte_etiquettes, date_creation, "
                  "matiere_ref_id) VALUES "
                  "('9931861','24/0023 - COHESIO1','COHESIO 1',470,'THERMIQUE PRO',"
                  "'ITASA KA','Permanent 2028Y - 1','Paravent de 1 000 plis',"
                  "'2850',454,660000,'2026-05-15',42)")
        c.commit()
        self.conn = c

        import contextlib
        import database

        @contextlib.contextmanager
        def fausse_base():
            yield c

        self._vrai = database.get_db
        database.get_db = fausse_base

    def tearDown(self):
        import database
        database.get_db = self._vrai
        self.conn.close()
        try:
            os.unlink(self.fichier)
        except OSError:
            pass

    def test_le_produit_est_repris_pas_la_commande(self):
        champs, provenance = {}, {}
        source = raf._completer_depuis_mysifa("24/0023", champs, provenance)
        self.assertEqual(source, "OF 9931861")
        self.assertEqual(champs["machine"], "COHESIO 1")
        self.assertEqual(champs["laize"], 470)
        self.assertEqual(champs["outil_1_numero"], "2850")
        self.assertEqual(champs["matiere_ref_id"], 42)
        self.assertEqual(provenance["machine"], "OF 9931861")
        # Ce qui appartient à la commande du jour ne se reprend PAS : une
        # quantité recopiée d'un OF précédent est une erreur qui part en
        # production.
        self.assertNotIn("qte_etiquettes", champs)
        self.assertNotIn("of_numero", champs)
        self.assertNotIn("date_creation", champs)

    def test_le_suffixe_machine_de_la_reference_ne_bloque_pas(self):
        # L'OF est enregistré « 24/0023 - COHESIO1 », l'article vaut « 24/0023 ».
        champs, provenance = {}, {}
        self.assertEqual(raf._completer_depuis_mysifa("24/0023", champs, provenance),
                         "OF 9931861")

    def test_rvgi_garde_la_main(self):
        # Une valeur déjà posée par RVGI n'est jamais écrasée par l'historique.
        champs = {"machine": "COHESIO 2"}
        provenance = {"machine": "gpr_ff"}
        raf._completer_depuis_mysifa("24/0023", champs, provenance)
        self.assertEqual(champs["machine"], "COHESIO 2")
        self.assertEqual(provenance["machine"], "gpr_ff")

    def test_reference_jamais_fabriquee(self):
        champs, provenance = {}, {}
        self.assertIsNone(raf._completer_depuis_mysifa("999/9999", champs, provenance))
        self.assertEqual(champs, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)

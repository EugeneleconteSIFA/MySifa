"""
Nouvel ERP — calculs et cycle de vie des pièces (app/services/gc).

1. Montant de ligne : prix au mille, remise, arrondi au demi supérieur.
2. Totaux : TVA par taux, remise de pied par taux, TTC = HT + TVA.
3. Échéances : date de facture, fin de mois, jour fixe.
4. Numérotation : format, compteur, remise à 1 au changement d'année.
5. Chaîne devis → commande → BL → facture : liens de ligne, reliquats,
   état des pièces amont, mouvements de stock, échéances, numéros.
6. Refus : modifier une pièce validée, annuler une facture, valider pour un
   client bloqué, transformer deux fois au-delà du reste, avoir au-delà du
   facturé.
7. Annulation d'un BL : stock contrepassé, commande rouverte.

Lancer : python3 tests/test_gc_pieces.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_gc_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import database  # noqa: E402,F401 — le shim d'abord (CLAUDE.md)
from database import get_db  # noqa: E402
from app.services.gc import calculs, pieces  # noqa: E402
from app.services.gc.pieces import ErreurPiece  # noqa: E402

NOW = "2026-10-14T10:00:00"


def _base(conn):
    for t in ("gc_relances", "gc_reglements_affectations", "gc_reglements", "gc_mouvements", "gc_echeances", "gc_pieces_lignes", "gc_pieces", "gc_tarifs",
              "gc_articles", "gc_tiers_adresses", "gc_tiers"):
        conn.execute(f"DELETE FROM {t}")
    conn.execute("UPDATE gc_sequences SET prochain=1, annee=0, mois=0")
    conn.execute(
        """INSERT INTO gc_tiers (id, code, est_client, raison_sociale, condition_paiement, cree_le, modifie_le)
           VALUES (1, 'C1', 1, 'Client Un', '30FM', ?, ?)""", (NOW, NOW))
    conn.execute(
        """INSERT INTO gc_tiers (id, code, est_fournisseur, raison_sociale, cree_le, modifie_le)
           VALUES (2, 'F1', 1, 'Fournisseur Un', ?, ?)""", (NOW, NOW))
    conn.execute(
        """INSERT INTO gc_articles (id, code, libelle, nature, unite, base_prix, prix_vente_cents, tva_code,
               gere_stock, cree_le, modifie_le)
           VALUES (1, 'ETQ1', 'Étiquette test', 'pf', 'ETQ', 1000, 1250, 'N', 1, ?, ?)""", (NOW, NOW))
    conn.execute(
        """INSERT INTO gc_articles (id, code, libelle, nature, unite, base_prix, prix_vente_cents, tva_code,
               gere_stock, cree_le, modifie_le)
           VALUES (2, 'CALAGE', 'Frais de calage', 'service', 'FORF', 1, 8000, 'N', 0, ?, ?)""", (NOW, NOW))
    conn.execute(
        """INSERT INTO gc_tarifs (article_id, tiers_id, sens, qte_min_milli, prix_cents)
           VALUES (1, 1, 'vente', 50000000, 1100)""")


def _ligne(article, q, prix=None, base=None, **k):
    d = {"article_id": article, "quantite_milli": q}
    if prix is not None:
        d["prix_cents"] = prix
    if base is not None:
        d["base_prix"] = base
    d.update(k)
    return d


class Calculs(unittest.TestCase):
    def test_montant_ligne(self):
        # 12 500 étiquettes à 12,50 € le mille = 156,25 €
        self.assertEqual(calculs.montant_ligne(12_500_000, 1250, 1000), 15625)
        # 3 unités à 0,333 € → 0,999 → 1,00 €
        self.assertEqual(calculs.montant_ligne(3000, 333, 10), 100)
        # remise 10 % sur 100,00 € = 90,00 €
        self.assertEqual(calculs.montant_ligne(1000, 10000, 1, 1000), 9000)
        # demi-centime arrondi au supérieur : 0,5 unité à 0,01 €
        self.assertEqual(calculs.montant_ligne(500, 1, 1), 1)

    def test_totaux(self):
        t = calculs.totaux([
            {"montant_ht_cents": 10000, "taux_tva_bp": 2000},
            {"montant_ht_cents": 5000, "taux_tva_bp": 550},
        ], remise_piece_bp=1000)
        self.assertEqual(t["ht"], 9000 + 4500)
        self.assertEqual(t["tva"], 1800 + 248)   # 4500 × 5,5 % = 247,5 → 248
        self.assertEqual(t["ttc"], t["ht"] + t["tva"])

    def test_conditionnement_bobines(self):
        # Bon de commande RVGI 5568 : 56 400 m² en laize 470 = 120 000 ML = 10 bobines de 12 000
        cb = calculs.conditionnement_bobines(56_400_000, "M2", 4700, 12_000_000)
        self.assertEqual((cb["ml_milli"], cb["bobines"]), (120_000_000, 10))
        self.assertEqual(calculs.conditionnement_bobines(28_200_000, "M2", 4700, 10_000_000)["bobines"], 6)
        self.assertIsNone(calculs.conditionnement_bobines(1000, "ML", 4700, None))

    def test_echeance(self):
        d = date(2026, 10, 14)
        self.assertEqual(calculs.date_echeance(d, 30), date(2026, 11, 13))
        self.assertEqual(calculs.date_echeance(d, 30, True), date(2026, 11, 30))
        self.assertEqual(calculs.date_echeance(d, 45, True, 10), date(2026, 12, 10))
        self.assertEqual(calculs.date_echeance(date(2026, 12, 20), 0, True, 10), date(2027, 1, 10))

    def test_numero(self):
        self.assertEqual(calculs.formater_numero("FA{AA}{N:05}", 12, date(2026, 1, 1)), "FA2600012")
        self.assertEqual(calculs.formater_numero("{AAAA}-{MM}-{N}", 7, date(2026, 3, 1)), "2026-03-7")
        with get_db() as conn:
            _base(conn)
            self.assertEqual(calculs.prendre_numero(conn, "facture", date(2026, 12, 31)), "26120001")   # format RVGI
            self.assertEqual(calculs.prendre_numero(conn, "facture", date(2026, 12, 31)), "26120002")
            self.assertEqual(calculs.prendre_numero(conn, "facture", date(2027, 1, 1)), "27010001")
            # Devis : compteur mensuel ; commande : continu
            self.assertEqual(calculs.prendre_numero(conn, "devis", date(2026, 10, 30)), "2610001")
            self.assertEqual(calculs.prendre_numero(conn, "devis", date(2026, 10, 31)), "2610002")
            self.assertEqual(calculs.prendre_numero(conn, "devis", date(2026, 11, 2)), "2611001")
            conn.execute("UPDATE gc_sequences SET prochain=9932727 WHERE code='commande'")
            self.assertEqual(calculs.prendre_numero(conn, "commande", date(2026, 12, 31)), "9932727")
            self.assertEqual(calculs.prendre_numero(conn, "commande", date(2027, 1, 2)), "9932728")
            conn.rollback()


class Chaine(unittest.TestCase):
    def setUp(self):
        self.ctx = get_db()
        self.conn = self.ctx.__enter__()
        _base(self.conn)

    def tearDown(self):
        self.conn.rollback()
        self.ctx.__exit__(None, None, None)

    def test_prix_tarif_palier(self):
        c = self.conn
        self.assertEqual(pieces.prix(c, 1, 1, 10_000_000, "vente")["prix_cents"], 1250)
        p = pieces.prix(c, 1, 1, 60_000_000, "vente")
        self.assertEqual((p["prix_cents"], p["source"]), (1100, "tarif_tiers"))

    def test_chaine_complete(self):
        c = self.conn
        dv = pieces.creer(c, "devis", 1)
        pieces.enregistrer(c, dv, {"date_piece": "2026-10-14"}, [
            _ligne(1, 20_000_000, 1250, 1000), _ligne(2, 1000, 8000), {"libelle": "Texte libre"}])
        self.assertEqual(pieces.valider(c, dv), "2610001")      # format RVGI : AAMM + 3 chiffres

        co = pieces.transformer(c, [dv], "commande")
        # Le devis n'est accepté qu'à la validation de la commande ; le
        # brouillon suffit en revanche à empêcher une seconde transformation.
        self.assertEqual(pieces.charger(c, dv)["statut"], "valide")
        with self.assertRaises(ErreurPiece):
            pieces.transformer(c, [dv], "commande")
        cmd = pieces.charger(c, co)
        self.assertEqual(len(cmd["lignes"]), 2)   # la ligne de texte ne suit pas
        pieces.enregistrer(c, co, {"date_piece": "2026-10-14"}, None)
        self.assertEqual(pieces.valider(c, co), "0000001")      # compteur continu sur 7 chiffres
        self.assertEqual(pieces.charger(c, dv)["statut"], "solde")

        # Première livraison partielle : 12 000 étiquettes, calage livré
        bl = pieces.transformer(c, [co], "bl")
        l = pieces.charger(c, bl)["lignes"]
        l[0]["quantite_milli"] = 12_000_000
        pieces.enregistrer(c, bl, None, l)
        pieces.valider(c, bl)
        self.assertEqual(pieces.charger(c, co)["statut"], "partiel")
        stock = c.execute("SELECT SUM(quantite_milli) q FROM gc_mouvements WHERE article_id=1").fetchone()["q"]
        self.assertEqual(stock, -12_000_000)
        self.assertIsNone(c.execute("SELECT 1 FROM gc_mouvements WHERE article_id=2").fetchone())  # service

        # Reliquat : 8 000 étiquettes, plus de calage
        bl2 = pieces.transformer(c, [co], "bl")
        l2 = pieces.charger(c, bl2)["lignes"]
        self.assertEqual([x["quantite_milli"] for x in l2], [8_000_000])
        pieces.valider(c, bl2)
        self.assertEqual(pieces.charger(c, co)["statut"], "solde")
        with self.assertRaises(ErreurPiece):
            pieces.transformer(c, [co], "bl")

        # Une facture pour les deux BL
        fa = pieces.transformer(c, [bl, bl2], "facture")
        f = pieces.charger(c, fa)
        self.assertEqual(sum(x["montant_ht_cents"] for x in f["lignes"]), 25000 + 8000)
        self.assertRegex(pieces.valider(c, fa), r"^\d{4}0001$")          # AAMM + compteur mensuel
        f = pieces.charger(c, fa)
        self.assertEqual(f["total_ttc_cents"], 33000 + 6600)
        self.assertEqual(f["echeances"][0]["date_echeance"], "2026-11-30")
        self.assertEqual(f["echeances"][0]["montant_cents"], 39600)
        self.assertEqual({p["id"] for p in f["amont"]}, {bl, bl2})
        self.assertEqual(pieces.charger(c, bl)["statut"], "solde")

        # Refus
        with self.assertRaises(ErreurPiece):
            pieces.enregistrer(c, fa, {"notes": "x"}, None)
        with self.assertRaises(ErreurPiece):
            pieces.annuler(c, fa)
        with self.assertRaises(ErreurPiece):
            pieces.annuler(c, bl)       # facturé

        # Avoir partiel, puis avoir au-delà du facturé
        av = pieces.transformer(c, [fa], "avoir")
        la = pieces.charger(c, av)["lignes"]
        pieces.enregistrer(c, av, None, [dict(la[0], quantite_milli=1_000_000)])
        self.assertEqual(pieces.valider(c, av), "AV2600001")
        av2 = pieces.transformer(c, [fa], "avoir")
        la2 = pieces.charger(c, av2)["lignes"]
        self.assertEqual(la2[0]["quantite_milli"], 11_000_000)   # 12 000 du 1er BL − 1 000
        pieces.enregistrer(c, av2, None, [dict(la2[0], quantite_milli=11_000_001)])
        with self.assertRaises(ErreurPiece):
            pieces.valider(c, av2)

    def test_annulation_bl(self):
        c = self.conn
        co = pieces.creer(c, "commande", 1)
        pieces.enregistrer(c, co, None, [_ligne(1, 5_000_000, 1250, 1000)])
        pieces.valider(c, co)
        bl = pieces.transformer(c, [co], "bl")
        pieces.valider(c, bl)
        self.assertEqual(pieces.charger(c, co)["statut"], "solde")
        pieces.annuler(c, bl)
        self.assertEqual(pieces.charger(c, co)["statut"], "valide")
        q = c.execute("SELECT SUM(quantite_milli) q FROM gc_mouvements WHERE article_id=1").fetchone()["q"]
        self.assertEqual(q, 0)
        bl2 = pieces.transformer(c, [co], "bl")   # de nouveau possible
        self.assertEqual(pieces.charger(c, bl2)["lignes"][0]["quantite_milli"], 5_000_000)

    def test_refus(self):
        c = self.conn
        with self.assertRaises(ErreurPiece):
            pieces.creer(c, "commande", 2)          # fournisseur, pas client
        c.execute("UPDATE gc_tiers SET bloque=1 WHERE id=1")
        co = pieces.creer(c, "commande", 1)
        pieces.enregistrer(c, co, None, [_ligne(1, 1000, 100)])
        with self.assertRaises(ErreurPiece):
            pieces.valider(c, co)
        with self.assertRaises(ErreurPiece):
            pieces.enregistrer(c, co, None, [_ligne(1, 0, 100)])  # quantité nulle

    def test_reglements(self):
        from app.services.gc import compta
        c = self.conn
        co = pieces.creer(c, "commande", 1)
        pieces.enregistrer(c, co, None, [_ligne(2, 1000, 10000)])   # 100 € HT, 120 € TTC
        pieces.valider(c, co)
        bl = pieces.transformer(c, [co], "bl")
        pieces.valider(c, bl)
        fa = pieces.transformer(c, [bl], "facture")
        pieces.valider(c, fa)
        ech = compta.echeances(c, 1, ouvertes=True)
        self.assertEqual([e["reste_cents"] for e in ech], [12000])
        with self.assertRaises(ErreurPiece):     # au-delà du reste dû
            compta.enregistrer_reglement(c, {"tiers_id": 1, "date_reglement": "2026-10-20", "montant_cents": 15000,
                                             "affectations": [{"echeance_id": ech[0]["id"], "montant_cents": 13000}]})
        with self.assertRaises(ErreurPiece):     # affectations > montant
            compta.enregistrer_reglement(c, {"tiers_id": 1, "date_reglement": "2026-10-20", "montant_cents": 1000,
                                             "affectations": [{"echeance_id": ech[0]["id"], "montant_cents": 5000}]})
        r1 = compta.enregistrer_reglement(c, {"tiers_id": 1, "date_reglement": "2026-10-20", "montant_cents": 5000,
                                              "affectations": [{"echeance_id": ech[0]["id"], "montant_cents": 5000}]})
        self.assertEqual(pieces.charger(c, fa)["statut"], "partiel")
        compta.enregistrer_reglement(c, {"tiers_id": 1, "date_reglement": "2026-10-25", "montant_cents": 7000,
                                         "affectations": [{"echeance_id": ech[0]["id"], "montant_cents": 7000}]})
        self.assertEqual(pieces.charger(c, fa)["statut"], "solde")
        self.assertEqual(compta.echeances(c, 1, ouvertes=True), [])
        compta.supprimer_reglement(c, r1)
        self.assertEqual(pieces.charger(c, fa)["statut"], "partiel")
        self.assertEqual(compta.echeances(c, 1, ouvertes=True)[0]["reste_cents"], 5000)

    def test_of_et_duplication(self):
        c = self.conn
        c.execute("INSERT OR IGNORE INTO gc_sequences (code, libelle, format) VALUES ('of', 'OF', 'OF{AA}{N:05}')")
        c.execute(
            """INSERT INTO gc_articles (id, code, libelle, nature, unite, base_prix, prix_achat_cents, gere_stock,
                   cree_le, modifie_le) VALUES (3, 'MP1', 'Papier', 'mp', 'ML', 1, 50, 1, ?, ?)""", (NOW, NOW))
        co = pieces.creer(c, "commande", 1)
        pieces.enregistrer(c, co, None, [_ligne(1, 10_000_000, 1250, 1000), _ligne(2, 1000, 8000)])
        pieces.valider(c, co)
        of = pieces.transformer(c, [co], "of")
        lo = pieces.charger(c, of)["lignes"]
        self.assertEqual([x["article_id"] for x in lo], [1])          # le calage ne se fabrique pas
        pieces.valider(c, of)
        self.assertTrue(pieces.charger(c, of)["numero"].startswith("OF"))
        # L'OF n'empêche pas de livrer, ni ne compte comme livré
        self.assertEqual(pieces.charger(c, co)["statut"], "valide")
        pieces.declarer_consommation(c, of, 3, 2_000_000)
        pieces.declarer_production(c, of, 6_000_000)
        self.assertEqual(pieces.charger(c, of)["statut"], "partiel")
        pieces.declarer_production(c, of, 4_000_000)
        self.assertEqual(pieces.charger(c, of)["statut"], "solde")
        stock = {r["article_id"]: r["q"] for r in c.execute(
            "SELECT article_id, SUM(quantite_milli) q FROM gc_mouvements GROUP BY article_id").fetchall()}
        self.assertEqual(stock, {1: 10_000_000, 3: -2_000_000})
        with self.assertRaises(ErreurPiece):
            pieces.transformer(c, [co], "of")                          # déjà entièrement lancé
        bl = pieces.transformer(c, [co], "bl")                          # mais toujours livrable
        pieces.valider(c, bl)
        self.assertEqual(pieces.alertes_stock(c, bl), [])
        # Duplication : même tiers, mêmes lignes, sans lien amont
        d = pieces.dupliquer(c, co)
        dd = pieces.charger(c, d)
        self.assertEqual(dd["statut"], "brouillon")
        self.assertEqual([x["quantite_milli"] for x in dd["lignes"]], [10_000_000, 1000])
        self.assertTrue(all(x["ligne_amont_id"] is None for x in dd["lignes"]))

    def test_marche_et_appels(self):
        c = self.conn
        c.execute("INSERT OR IGNORE INTO gc_sequences (code, libelle, format) VALUES ('marche', 'Marché', 'MA{AA}{N:05}')")
        ma = pieces.creer(c, "marche", 1)
        pieces.enregistrer(c, ma, {"date_validite": "2099-12-31"}, [_ligne(1, 100_000_000, 1100, 1000)])
        pieces.valider(c, ma)
        a1 = pieces.transformer(c, [ma], "commande")
        l1 = pieces.charger(c, a1)["lignes"]
        self.assertEqual(l1[0]["prix_cents"], 1100)                     # prix du marché
        pieces.enregistrer(c, a1, None, [dict(l1[0], quantite_milli=30_000_000)])
        pieces.valider(c, a1)
        self.assertEqual(pieces.charger(c, ma)["statut"], "partiel")
        a2 = pieces.transformer(c, [ma], "commande")
        self.assertEqual(pieces.charger(c, a2)["lignes"][0]["quantite_milli"], 70_000_000)   # reste à appeler
        pieces.valider(c, a2)
        self.assertEqual(pieces.charger(c, ma)["statut"], "solde")
        # Marché échu : plus d'appel
        c.execute("UPDATE gc_pieces SET date_validite='2000-01-01', statut='valide' WHERE id=?", (ma,))
        c.execute("UPDATE gc_pieces_lignes SET quantite_milli=200000000 WHERE piece_id=?", (ma,))
        with self.assertRaises(ErreurPiece):
            pieces.transformer(c, [ma], "commande")

    def test_alerte_stock_negatif(self):
        c = self.conn
        co = pieces.creer(c, "commande", 1)
        pieces.enregistrer(c, co, None, [_ligne(1, 3_000_000, 1250, 1000)])
        pieces.valider(c, co)
        bl = pieces.transformer(c, [co], "bl")
        pieces.valider(c, bl)
        self.assertEqual(pieces.alertes_stock(c, bl), ["ETQ1 : stock -3 000 ETQ au dépôt PRINC"])

    def test_relances_et_transfert(self):
        from app.services.gc import compta, fichiers
        c = self.conn
        co = pieces.creer(c, "commande", 1)
        pieces.enregistrer(c, co, {"date_piece": "2026-01-05"}, [_ligne(2, 1000, 10000)])
        pieces.valider(c, co)
        bl = pieces.transformer(c, [co], "bl")
        pieces.enregistrer(c, bl, {"date_piece": "2026-01-06"}, None)
        pieces.valider(c, bl)
        fa = pieces.transformer(c, [bl], "facture")
        pieces.enregistrer(c, fa, {"date_piece": "2026-01-07"}, None)
        pieces.valider(c, fa)                                   # 30 FM → 28/02/2026
        self.assertEqual(compta.relances(c, "2026-02-28"), [])  # pas encore échue
        r = compta.relances(c, "2026-03-15")
        self.assertEqual((len(r), r[0]["echu_cents"], r[0]["niveau_propose"], r[0]["jours_retard"]), (1, 12000, 1, 15))
        compta.enregistrer_relance(c, 1, 1, "2026-03-15")
        self.assertEqual(compta.relances(c, "2026-03-30")[0]["niveau_propose"], 2)
        with self.assertRaises(ErreurPiece):
            compta.enregistrer_relance(c, 2, 1, "2026-03-15")   # rien d'échu
        # Transfert : deux mouvements, stock total inchangé
        c.execute("INSERT OR IGNORE INTO gc_depots (code, libelle) VALUES ('EXT', 'Externe')")
        fichiers.mouvement_manuel(c, {"type": "inventaire", "article_id": 1, "depot": "PRINC", "quantite_milli": 5_000_000})
        fichiers.mouvement_manuel(c, {"type": "transfert", "article_id": 1, "depot": "PRINC", "depot_destination": "EXT",
                                      "quantite_milli": 2_000_000})
        par = {r["depot"]: r["q"] for r in c.execute(
            "SELECT depot, SUM(quantite_milli) q FROM gc_mouvements WHERE article_id=1 GROUP BY depot").fetchall()}
        self.assertEqual(par, {"PRINC": 3_000_000, "EXT": 2_000_000})
        with self.assertRaises(ErreurPiece):
            fichiers.mouvement_manuel(c, {"type": "transfert", "article_id": 1, "depot": "PRINC",
                                          "depot_destination": "PRINC", "quantite_milli": 1000})

    def test_parite_rvgi(self):
        c = self.conn
        t = calculs.totaux([{"montant_ht_cents": 10000, "taux_tva_bp": 2000}], 1000, 200, 3000)
        self.assertEqual((t["remise"], t["escompte"], t["ht"], t["tva"], t["ttc"], t["net_a_payer"]),
                         (1000, 180, 8820, 1764, 10584, 7584))
        co = pieces.creer(c, "commande", 1)
        pieces.enregistrer(c, co, {"date_piece": "2026-10-01", "date_livraison": "2026-10-20", "jours_expedition": 2,
                                   "acompte_cents": 2000},
                           [_ligne(1, 5_000_000, 1250, 1000, date_livraison="2026-10-20", date_expedition="2026-10-18",
                                   origine_prod="stock", ref_client="REF-CLI-9")])
        l = pieces.charger(c, co)["lignes"][0]
        self.assertEqual((l["origine_prod"], l["laboratoire"], l["ref_client"]), ("stock", "renouvellement", "REF-CLI-9"))
        pieces.valider(c, co)
        k = [x for x in pieces.carnet(c, ["commande"]) if x["piece_id"] == co][0]
        self.assertEqual((k["date_expedition"], k["reste_milli"], k["position"], k["situation_of"]),
                         ("2026-10-18", 5_000_000, "valide", ""))
        bl = pieces.transformer(c, [co], "bl")
        lb = pieces.charger(c, bl)["lignes"][0]
        self.assertEqual((lb["date_expedition"], lb["origine_prod"], lb["ref_client"]), ("2026-10-18", "stock", "REF-CLI-9"))
        with self.assertRaises(ErreurPiece):
            pieces.enregistrer(c, bl, None, [dict(lb, origine_prod="inconnue")])
        pieces.enregistrer(c, bl, None, [dict(lb, quantite_milli=2_000_000)])
        pieces.valider(c, bl)
        k = [x for x in pieces.carnet(c, ["commande"]) if x["piece_id"] == co][0]
        self.assertEqual((k["repris_milli"], k["reste_milli"], k["position"]), (2_000_000, 3_000_000, "partiel"))
        fa = pieces.transformer(c, [bl], "facture")
        c.execute("UPDATE gc_pieces SET acompte_cents=1000 WHERE id=?", (fa,))
        pieces.valider(c, fa)
        f = pieces.charger(c, fa)
        self.assertEqual(f["echeances"][0]["montant_cents"], f["total_ttc_cents"] - 1000)

    def test_type_ligne_et_bat(self):
        c = self.conn
        c.execute("INSERT OR IGNORE INTO gc_sequences (code, libelle, format) VALUES ('of', 'OF', 'OF{AA}{N:05}')")
        c.execute("""INSERT INTO gc_articles (id, code, libelle, nature, unite, base_prix, prix_vente_cents, tva_code,
                   gere_stock, cree_le, modifie_le) VALUES (4, 'ETQ2', 'Étiquette 2', 'pf', 'ETQ', 1000, 900, 'N', 1, ?, ?)""",
                  (NOW, NOW))
        co = pieces.creer(c, "commande", 1)
        pieces.enregistrer(c, co, None, [
            _ligne(1, 1_000_000, 1250, 1000),                                      # normale
            _ligne(4, 2_000_000, 900, 1000, type_ligne="livrer_sans_facture"),     # échantillon
            _ligne(1, 3_000_000, 1250, 1000, type_ligne="stocker", laboratoire="creation"),
        ])
        pieces.valider(c, co)
        bl = pieces.transformer(c, [co], "bl")
        self.assertEqual([x["type_ligne"] for x in pieces.charger(c, bl)["lignes"]],
                         ["livrer_facturer", "livrer_sans_facture"])               # la ligne à stocker ne se livre pas
        pieces.valider(c, bl)
        self.assertEqual(pieces.charger(c, co)["statut"], "partiel")              # reste la ligne à stocker
        fa = pieces.transformer(c, [bl], "facture")
        self.assertEqual(len(pieces.charger(c, fa)["lignes"]), 1)                 # pas de facture pour l'échantillon
        pieces.valider(c, fa)
        self.assertEqual(pieces.charger(c, bl)["statut"], "solde")               # BL entièrement traité
        k = [x for x in pieces.carnet(c, ["commande"]) if x["piece_id"] == co and x["rang"] == 3][0]
        self.assertEqual((k["bat"], k["a_fabriquer_milli"]), ("non_rattache", 3_000_000))
        of = pieces.transformer(c, [co], "of")
        lo = [x for x in pieces.charger(c, of)["lignes"]]
        self.assertEqual(len(lo), 1)                                              # seule la ligne à stocker reste à fabriquer
        pieces.valider(c, of)
        self.assertEqual(len(pieces.alertes_bat(c, of)), 1)                        # BAT non rattaché
        pieces.declarer_production(c, of, 3_000_000)
        self.assertEqual(pieces.charger(c, co)["statut"], "solde")               # produite = ligne à stocker soldée

    def test_produit_du_client(self):
        from app.services.gc import fichiers
        c = self.conn
        with self.assertRaises(ErreurPiece):
            fichiers.enregistrer_article(c, None, {"libelle": "Sans client", "nature": "pf", "unite": "ETQ"})
        aid = fichiers.enregistrer_article(c, None, {"libelle": "Étiquette du client 1", "nature": "pf", "unite": "ETQ",
                                                     "client_id": 1, "base_prix": 1000})
        self.assertEqual(c.execute("SELECT code FROM gc_articles WHERE id=?", (aid,)).fetchone()["code"], "C1/0001")
        c.execute("""INSERT INTO gc_tiers (id, code, est_client, raison_sociale, cree_le, modifie_le)
                     VALUES (3, 'C2', 1, 'Autre client', ?, ?)""", (NOW, NOW))
        co = pieces.creer(c, "commande", 3)
        with self.assertRaises(ErreurPiece):
            pieces.enregistrer(c, co, None, [_ligne(aid, 1000, 100)])     # produit d'un autre client

    def test_appel_offre_et_stats(self):
        from app.services.gc import compta
        c = self.conn
        c.execute("INSERT OR IGNORE INTO gc_sequences (code, libelle, format, reinit) VALUES ('aof', 'AO', '{N}', 'jamais')")
        c.execute("UPDATE gc_sequences SET prochain=5568 WHERE code='aof'")
        ao = pieces.creer(c, "aof", 2)
        pieces.enregistrer(c, ao, None, [_ligne(1, 1_000_000, 900, 1000)])
        self.assertEqual(pieces.valider(c, ao), "5568")
        cf = pieces.transformer(c, [ao], "cde_fournisseur")
        pieces.valider(c, cf)
        self.assertEqual(pieces.charger(c, ao)["statut"], "solde")
        co = pieces.creer(c, "commande", 1)
        pieces.enregistrer(c, co, {"date_piece": "2026-03-02"}, [_ligne(2, 1000, 10000)])
        pieces.valider(c, co)
        bl = pieces.transformer(c, [co], "bl"); pieces.enregistrer(c, bl, {"date_piece": "2026-03-03"}, None); pieces.valider(c, bl)
        fa = pieces.transformer(c, [bl], "facture"); pieces.enregistrer(c, fa, {"date_piece": "2026-03-04"}, None); pieces.valider(c, fa)
        av = pieces.transformer(c, [fa], "avoir"); pieces.enregistrer(c, av, {"date_piece": "2026-04-01"}, None); pieces.valider(c, av)
        s = compta.statistiques(c, "2026-01-01", "2026-12-31")
        self.assertEqual(s["total_cents"], 0)                                     # facture − avoir
        self.assertEqual([m["ca_cents"] for m in s["par_mois"]], [10000, -10000])
        self.assertEqual(s["par_client"][0]["nb_factures"], 1)

    def test_prix_par_conditionnement(self):
        from app.services.gc import fichiers
        c = self.conn
        aid = fichiers.enregistrer_article(c, None, {"libelle": "Thermique 135 g", "nature": "mp", "unite": "M2",
                                                     "base_prix": 1, "prix_achat_cents": 50}, tarifs=[
            {"tiers_id": 2, "sens": "achat", "prix_cents": 46, "laize_dmm": 4700, "ml_par_bobine_milli": 12_000_000,
             "ref_fournisseur": "KPR-412"},
            {"tiers_id": 2, "sens": "achat", "prix_cents": 49, "laize_dmm": 3300, "ml_par_bobine_milli": 6_000_000},
        ])
        p470 = pieces.prix(c, aid, 2, 1000, "achat", None, 4700, None)
        p330 = pieces.prix(c, aid, 2, 1000, "achat", None, 3300, None)
        self.assertEqual((p470["prix_cents"], p470["ml_par_bobine_milli"], p470["ref_fournisseur"]), (46, 12_000_000, "KPR-412"))
        self.assertEqual(p330["prix_cents"], 49)
        self.assertEqual(len(pieces.conditionnements(c, aid, 2)), 2)
        cf = pieces.creer(c, "cde_fournisseur", 2)
        pieces.enregistrer(c, cf, None, [{"article_id": aid, "quantite_milli": 56_400_000, "prix_cents": 46,
                                          "laize_dmm": 4700, "ml_par_bobine_milli": 12_000_000}])
        pieces.valider(c, cf)
        re_ = pieces.transformer(c, [cf], "reception")
        l = pieces.charger(c, re_)["lignes"][0]
        self.assertEqual((l["laize_dmm"], l["ml_par_bobine_milli"]), (4700, 12_000_000))   # le conditionnement suit

    def test_prospect(self):
        from app.services.gc import fichiers
        c = self.conn
        pid = fichiers.enregistrer_tiers(c, None, {"raison_sociale": "Prospect SA", "est_prospect": 1})
        self.assertTrue(c.execute("SELECT code FROM gc_tiers WHERE id=?", (pid,)).fetchone()["code"].startswith("P"))
        dv = pieces.creer(c, "devis", pid)                      # devis possible
        pieces.enregistrer(c, dv, None, [_ligne(2, 1000, 100)])
        pieces.valider(c, dv)
        with self.assertRaises(ErreurPiece):
            pieces.transformer(c, [dv], "commande")            # commande : le passer client d'abord
        fichiers.enregistrer_tiers(c, pid, {"est_client": 1})
        self.assertIsNotNone(pieces.transformer(c, [dv], "commande"))

    def test_texte_automatique(self):
        c = self.conn
        c.execute("INSERT INTO gc_textes (code, libelle, texte) VALUES ('LIV', 'Livraison', 'Livraison sur rendez-vous.')")
        c.execute("UPDATE gc_tiers SET texte_bl='LIV' WHERE id=1")
        co = pieces.creer(c, "commande", 1)
        self.assertEqual(pieces.charger(c, co)["notes"], "")
        pieces.enregistrer(c, co, None, [_ligne(1, 1000, 100)])
        pieces.valider(c, co)
        bl = pieces.transformer(c, [co], "bl")
        self.assertEqual(pieces.charger(c, bl)["notes"], "Livraison sur rendez-vous.")

    def test_achat_reception_stock(self):
        c = self.conn
        c.execute("UPDATE gc_articles SET prix_achat_cents=900 WHERE id=1")
        cf = pieces.creer(c, "cde_fournisseur", 2)
        self.assertEqual(pieces.prix(c, 1, 2, 1000, "achat")["prix_cents"], 900)
        pieces.enregistrer(c, cf, None, [_ligne(1, 30_000_000, 900, 1000)])
        pieces.valider(c, cf)
        re_ = pieces.transformer(c, [cf], "reception")
        pieces.valider(c, re_)
        q = c.execute("SELECT SUM(quantite_milli) q FROM gc_mouvements WHERE article_id=1").fetchone()["q"]
        self.assertEqual(q, 30_000_000)
        self.assertEqual(pieces.charger(c, cf)["statut"], "solde")

    def test_reception_par_laize(self):
        from app.services.gc import fichiers
        c = self.conn
        cf = pieces.creer(c, "cde_fournisseur", 2)
        pieces.enregistrer(c, cf, None, [_ligne(1, 5_000_000, 900, 1000, laize_dmm=1600)])
        pieces.valider(c, cf)
        re_ = pieces.transformer(c, [cf], "reception")
        pieces.valider(c, re_)
        l = [s for s in fichiers.stock(c) if s["id"] == 1]
        self.assertEqual([(s["laize_dmm"], s["quantite_milli"]) for s in l], [(1600, 5_000_000)])

    def test_cahier_des_charges(self):
        from app.services.gc import cahiers
        c = self.conn
        cahiers.enregistrer(c, "tiers", 1, [{"etape": "livraison", "texte": "Colis complets uniquement.", "imprime": 1},
                                            {"etape": "devis", "texte": "Toujours deux paliers."}])
        cahiers.enregistrer(c, "article", 1, [{"etape": "livraison", "texte": "Mandrin 76."}])
        co = pieces.creer(c, "commande", 1)
        pieces.enregistrer(c, co, None, [_ligne(1, 1000, 100)])
        self.assertEqual(pieces.charger(c, co)["cahier"], [])
        pieces.valider(c, co)
        bl = pieces.transformer(c, [co], "bl")
        notes = pieces.charger(c, bl)["cahier"]
        self.assertEqual([n["texte"] for n in notes], ["Colis complets uniquement.", "Mandrin 76."])
        with self.assertRaises(pieces.ErreurPiece):
            cahiers.enregistrer(c, "tiers", 1, [{"etape": "nimporte", "texte": "x"}])
        c.execute("UPDATE gc_tiers SET instr_livraison_interne='Appeler avant.', instr_livraison_externe='Quai 3.' WHERE id=1")
        notes = pieces.charger(c, bl)["cahier"]
        self.assertEqual([(n["texte"], n["imprime"]) for n in notes][:2], [("Appeler avant.", 0), ("Quai 3.", 1)])


if __name__ == "__main__":
    unittest.main()

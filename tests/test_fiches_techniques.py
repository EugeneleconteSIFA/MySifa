"""Fiches techniques matière et produit (BOM) : saisie, héritage, PDF."""
import sys; sys.path.insert(0, '.')
import database  # noqa: F401 — d'abord, toujours
import sqlite3

import importlib
from app.services.pricing import fiche_technique as ft

mig = importlib.import_module("app.core.migrations.2026_10_07_fiches_techniques_matieres_produits")


def _base():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
      CREATE TABLE matieres_premieres (id INTEGER PRIMARY KEY, reference TEXT, designation TEXT,
        categorie TEXT, sous_section TEXT, couleur TEXT, weight_gsm REAL);
      CREATE TABLE mp_matiere_declinaison (id INTEGER PRIMARY KEY, matiere_id INTEGER);
      CREATE TABLE mp_produit (id INTEGER PRIMARY KEY, code TEXT, designation TEXT);
      CREATE TABLE mp_produit_composant (id INTEGER PRIMARY KEY, produit_id INTEGER, declinaison_id INTEGER,
        role TEXT, ordre INTEGER, grammage_gsm REAL);
      INSERT INTO matieres_premieres VALUES (1,'TH72','Thermique Protégé','frontal','thermique','Blanc',72),
        (2,'201','Adhésif permanent 201','adhesif',NULL,NULL,NULL),
        (3,'GJ58','Glassine jaune 58','glassine',NULL,'Jaune',58);
      INSERT INTO mp_matiere_declinaison VALUES (11,1),(12,2),(13,3);
      INSERT INTO mp_produit VALUES (5,'886-0001','Thermique Pro. Permanent 201');
      INSERT INTO mp_produit_composant VALUES (1,5,11,'FRONTAL',0,NULL),(2,5,12,'ADHESIF',1,20),(3,5,13,'GLASSINE',2,NULL);
    """)
    mig.appliquer(conn)
    mig.appliquer(conn)  # rejouable
    return conn


def test_heritage_et_pdf():
    conn = _base()
    ft.ecrire(conn, "matiere", 1, {"epaisseur_um": "62", "inconnu": "x"}, "test")
    ft.ecrire(conn, "matiere", 2, {"epaisseur_um": "27", "pouvoir_adhesif": "Inox 16 N/inch",
                                    "type_adhesif": "Permanent"}, "test")
    ft.ecrire(conn, "matiere", 3, {"epaisseur_um": "51"}, "test")
    assert "inconnu" not in ft.lire(conn, "matiere", 1)["data"]
    p = ft.produit(conn, 5)
    d = ft.donnees_produit(p)
    assert d["epaisseur_totale_um"] == "140"
    assert d["pouvoir_adhesif"] == "Inox 16 N/inch"
    assert p["composants"][1]["data"]["grammage_gsm"] == "20"
    assert p["composants"][0]["data"]["couleur"] == "Blanc"
    assert ft.pdf_produit(p)[:4] == b"%PDF"
    assert ft.pdf_matiere(ft.matiere(conn, 1))[:4] == b"%PDF"
    # Une fiche produit saisie l'emporte sur l'héritage.
    ft.ecrire(conn, "produit", 5, {"epaisseur_totale_um": "141"}, "test")
    assert ft.donnees_produit(ft.produit(conn, 5))["epaisseur_totale_um"] == "141"


if __name__ == "__main__":
    test_heritage_et_pdf()
    print("OK")

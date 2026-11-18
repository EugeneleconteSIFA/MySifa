"""
OF proposé depuis une fiche technique (12/11/2026).

Les cas sont des OF Access réels, recalculés à partir de leur fiche : ce que
le formulaire « Nouvel OF » d'Access a produit, MySifa doit le reproduire.

  9932770 - L1   4 000 000 étiq.  1164/0017-like  → 11 056 m, 8 000 bob., 45 cartons, 229 tubes, 107 kg
  9932770 - L2     650 000 étiq.                 →  1 797 m (1 796,6 arrondi au-dessus), 8 cartons, 38 tubes
  Marché 745     7 043 750 étiq.  875 / bobine    →  8 050 bob., 23 cartons, 384 tubes (mandrin 69,95)
  9932448+451    1 207 500 étiq.  1 750 / bobine  →    690 bob., 87 cartons, 37 tubes (tube 1500x76, mandrin 76,2)

Lancer : python3 tests/test_of_proposition.py
"""
import re
import sqlite3
import sys

sys.path.insert(0, ".")

from app.services import of_proposition as op

ko = 0


def verifier(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    ko += 0 if ok else 1
    print(("  OK  " if ok else "  KO  ") + libelle
          + ("" if ok else f" — obtenu {obtenu!r}, attendu {attendu!r}"))


FICHE_1164 = {
    "qte_au_mille": 2.7639999389648438, "mod_longueur": 27.64, "outil1_nb_front": 10,
    "nb_etiq_bobin": 500, "nb_bobines_carton": 180,
    "mandrin_dia": "Tube 1500x40", "mandrin_longueur": 42.4,
}

print("Quantités — OF 9932770 - L1")
c = op.calculer_quantites(FICHE_1164, 4_000_000, laize=440, grammage=22)
verifier("métrage", c.get("metrage"), 11056)
verifier("bobines", c.get("qte_bobines"), 8000)
verifier("mandrins = bobines", c.get("nb_mandrins"), 8000)
verifier("levées (Access : 800)", c.get("nb_levees"), 800)
verifier("cartons", c.get("nb_cartons"), 45)
verifier("tubes (35 mandrins par tube)", c.get("nb_tubes"), 229)
verifier("adhésif kg (Access : 107,0)", round(c.get("qte_adhesif_kg"), 1), 107.0)
verifier("rien ne manque", c.get("_manques"), [])

print("Quantités — OF 9932770 - L2")
c = op.calculer_quantites(FICHE_1164, 650_000, laize=440, grammage=22)
verifier("métrage arrondi au-dessus", c.get("metrage"), 1797)
verifier("cartons", c.get("nb_cartons"), 8)
verifier("tubes", c.get("nb_tubes"), 38)

print("Quantités — Marché 745")
c = op.calculer_quantites({
    "qte_au_mille": 21.77, "nb_etiq_bobin": 875, "nb_bobines_carton": 350,
    "mandrin_dia": "Tube 1500x40", "mandrin_longueur": 69.95,
}, 7_043_750)
verifier("bobines", c.get("qte_bobines"), 8050)
verifier("cartons", c.get("nb_cartons"), 23)
verifier("tubes (21 mandrins par tube)", c.get("nb_tubes"), 384)

print("Quantités — OF 9932448 + 9932451")
c = op.calculer_quantites({
    "qte_au_mille": 15.522, "nb_etiq_bobin": 1750, "nb_bobines_carton": 8,
    "mandrin_dia": "Tube 1500x76", "mandrin_longueur": 76.2,
}, 1_207_500)
verifier("bobines", c.get("qte_bobines"), 690)
verifier("cartons", c.get("nb_cartons"), 87)
verifier("tubes (19 mandrins par tube)", c.get("nb_tubes"), 37)

print("Levées — OF 9932856 - L6, 9932856 - L3, 9932796")
c = op.calculer_quantites({"nb_etiq_bobin": 1000, "outil1_nb_front": 9}, 1_120_000)
verifier("1 120 bobines ÷ 9 fronts → 125 (arrondi au-dessus)", c.get("nb_levees"), 125)
c = op.calculer_quantites({"nb_etiq_bobin": 1000, "outil1_nb_front": 9}, 60_000)
verifier("60 bobines ÷ 9 fronts → 7", c.get("nb_levees"), 7)
c = op.calculer_quantites({"nb_etiq_bobin": 3000, "outil1_nb_front": 11}, 2_409_000)
verifier("803 bobines ÷ 11 fronts → 73", c.get("nb_levees"), 73)
c = op.calculer_quantites({"nb_etiq_bobin": 1000, "mod_nb_front": 4}, 8000)
verifier("sans fronts de l'outil : pas de levées (jamais mod_nb_front)", "nb_levees" in c, False)

print("Produit vendu au mètre — OF Access 9932835 (122/0022)")
F122 = {"conditionnement": "Bobine de 45 ml", "nb_bobines_carton": 32, "outil1_nb_front": 5,
        "qte_au_mille": 8.600000381469727, "mod_longueur": 304.8,
        "mandrin_dia": "Tube 1500x40", "mandrin_longueur": 59.7}
verifier("reconnu au mètre", op.vendu_au_metre(F122), True)
verifier("une étiquette par bobine n'est pas au mètre", op.vendu_au_metre({"conditionnement": "Bobine de 500 étiquettes"}), False)
c = op.calculer_quantites(F122, 630)
verifier("630 rouleaux → 630 bobines (Access : 630)", c.get("qte_bobines"), 630)
verifier("→ 126 levées (Access : 126)", c.get("nb_levees"), 126)
verifier("→ métrage 5 418 (Access : 5 418)", c.get("metrage"), 5418)
verifier("→ 20 cartons de 32", c.get("nb_cartons"), 20)
verifier("pas de message « étiquettes par bobine »", [m for m in c["_manques"] if "bobine" in m], [])

print("OF Access 9931861 (24/0023, paravents) et 9931953 (901/0005) recalculés")
F24 = {"conditionnement": "Paravent de 1 000 plis de 4 étiquettes", "outil1_nb_front": 5, "nb_bobines_carton": 3,
       "qte_au_mille": 10.793999671936035}
c = op.calculer_quantites(F24, 660000, laize=470, grammage=19)
verifier("métrage 7 124 (Access : 7 124, pas 7 125)", c.get("metrage"), 7124)
verifier("165 paravents comptés comme bobines", c.get("qte_bobines"), 165)
verifier("165 mandrins", c.get("nb_mandrins"), 165)
verifier("33 levées", c.get("nb_levees"), 33)
verifier("55 cartons", c.get("nb_cartons"), 55)
verifier("adhésif 63,6 kg", round(c.get("qte_adhesif_kg"), 1), 63.6)
F901 = {"nb_etiq_bobin": 550, "outil1_nb_front": 3, "nb_bobines_carton": 18, "qte_au_mille": 50.8,
        "mandrin_dia": "Tube 1500x25", "mandrin_longueur": 103}
c = op.calculer_quantites(F901, 201300)
verifier("9931953 : métrage 10 226", c.get("metrage"), 10226)
verifier("9931953 : 366 bobines, 122 levées, 21 cartons, 27 tubes",
         (c.get("qte_bobines"), c.get("nb_levees"), c.get("nb_cartons"), c.get("nb_tubes")), (366, 122, 21, 27))

print("Cas limites")
c = op.calculer_quantites({"qte_au_mille": 2.0, "nb_etiq_bobin": 500,
                           "mandrin_dia": "Bague 63,7x25", "mandrin_longueur": 20}, 10_000)
verifier("une bague ne compte pas de tubes", "nb_tubes" in c, False)
verifier("sans nb bobines/carton : manque signalé",
         any("carton" in m for m in c["_manques"]), True)
c = op.calculer_quantites({"mod_longueur": 152.4, "outil1_nb_front": 3}, 1000)
verifier("qté au mille absente : module ÷ fronts de l'outil", c.get("metrage"), 51)
verifier("sans nb étiq./bobine : pas de bobines", "qte_bobines" in c, False)
c = op.calculer_quantites({"qte_au_mille": 2.0, "mod_nb_front": 1}, 1000)
verifier("mod_nb_front n'intervient jamais", c.get("metrage"), 2)
verifier("sans quantité : rien", op.calculer_quantites(FICHE_1164, ""), {"_manques": []})
verifier("longueur du tube lue dans le libellé", op.longueur_tube("Tube 1500x76 7mm"), 1500.0)
verifier("pas de tube supposé", op.longueur_tube("Mandrin 76"), None)

print("Étiquettes par bobine et tube lus dans les libellés")
verifier("« Bobine de 1 000 étiquettes » (fiche 945/0003)",
         op.etiquettes_par_bobine({"conditionnement": "Bobine de 1 000 étiquettes"}), (1000.0, "conditionnement"))
verifier("la colonne de la fiche prime",
         op.etiquettes_par_bobine({"nb_etiq_bobin": 500, "conditionnement": "Bobine de 1 000 étiquettes"}), (500.0, "fiche"))
verifier("paravent : plis × étiquettes, comme Access (OF 9931861)",
         op.etiquettes_par_bobine({"conditionnement": "Paravent de 1 000 plis de 4 étiquettes"}), (4000.0, "conditionnement"))
verifier("paquet : idem (95/0006)",
         op.etiquettes_par_bobine({"conditionnement": "Paquet de 1 000 plis de 1 étiquette"}), (1000.0, "conditionnement"))
c = op.calculer_quantites({"conditionnement": "Bobine de 1 000 étiquettes", "outil1_nb_front": 4,
                           "nb_bobines_carton": 10, "qte_au_mille": 31.75}, 70_000)
verifier("945/0003, 70 000 étiq. : 70 bobines", c.get("qte_bobines"), 70)
verifier("945/0003 : 18 levées", c.get("nb_levees"), 18)
verifier("945/0003 : 7 cartons", c.get("nb_cartons"), 7)
verifier("le repli est signalé", "conditionnement" in (c.get("_info") or ""), True)
verifier("désignation MyStock du tube",
         op.longueur_tube("Tube carton Ø 40 mm, Lg. 1500 mm, ép. 4 mm"), 1500.0)
verifier("« Lg » hors d'un tube : rien", op.longueur_tube("Bague Lg. 20 mm"), None)

print("Proposition complète depuis la fiche")
conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.executescript("""
CREATE TABLE fiches_techniques (
  id INTEGER PRIMARY KEY, reference TEXT, machine TEXT, format TEXT, valide INTEGER,
  laize_optimale REAL, support TEXT, glassine TEXT, adhesif TEXT, qte_au_mille REAL,
  mod_longueur REAL, outil1_nb_front INTEGER, mod_nb_front INTEGER,
  outil1_forme TEXT, outil1_numero_sifa TEXT, outil2_forme TEXT, outil2_numero_sifa TEXT,
  mandrin_dia TEXT, mandrin_longueur REAL, conditionnement TEXT, cartons TEXT,
  cales_sachets TEXT, palette_type TEXT, particularite TEXT,
  nb_etiq_bobin INTEGER, nb_bobines_carton INTEGER,
  support_ref_id INTEGER, glassine_ref_id INTEGER, adhesif_ref_id INTEGER,
  carton_ref_id INTEGER, mandrin_ref_id INTEGER, palette_ref_id INTEGER);
CREATE TABLE of_imports (id INTEGER PRIMARY KEY, adhesif_label TEXT, qte_adhesif_g REAL, of_numero TEXT);
INSERT INTO of_imports (adhesif_label, qte_adhesif_g) VALUES
  ('Enlevable 4007-22', 22), ('Permanent', NULL), ('enlevable 4007-22 ', NULL);
INSERT INTO fiches_techniques VALUES (
  17, '1164/0017', 'COHESIO 1', '40 x 25 mm', 0,
  440, 'Couché', 'ITASA Siliconé KAM20', 'Enlevable 4007-22', 2.7639999389648438,
  27.64, 10, 1, 'Plaque', '2418', NULL, NULL,
  'Tube 1500x40', 42.4, 'Bobine de 500 étiquettes', 'Carton 385 x 385 x 260 mm',
  NULL, 'PERDUE', 'Voir tableau au dos de l''OF', 500, 180,
  12, NULL, NULL, NULL, NULL, NULL);
INSERT INTO fiches_techniques (id, reference, machine, adhesif, qte_au_mille)
  VALUES (28, '1183/0028 - DSI', 'DSI', 'Permanent', 50.8);
""")

p = op.proposer(conn, 17, "90000")
ch = p["champs"]
verifier("référence = clé produit", ch.get("reference"), "1164/0017")
verifier("machine", ch.get("machine"), "COHESIO 1")
verifier("laize", ch.get("laize"), 440)
verifier("matière", ch.get("matiere"), "Couché")
verifier("outil 1", ch.get("outil_1_numero"), "2418")
verifier("conditionnement", ch.get("conditionnement"), "Bobine de 500 étiquettes")
verifier("référence MyStock du support → matière de l'OF", ch.get("matiere_ref_id"), 12)
verifier("une case vide de la fiche n'est pas posée", "cales_sachets" in ch, False)
verifier("métrage pour 90 000", ch.get("metrage"), 249)
verifier("bobines pour 90 000", ch.get("qte_bobines"), 180)
verifier("levées pour 90 000", ch.get("nb_levees"), 18)
verifier("qté au mille arrondie", ch.get("qte_au_mille"), 2.764)
verifier("tubes pour 90 000", ch.get("nb_tubes"), 6)
verifier("grammage repris d'un OF précédent", ch.get("qte_adhesif_g"), 22)
verifier("adhésif kg", ch.get("qte_adhesif_kg"), round(22 * 249 * 440 / 1e6, 3))
verifier("provenance du calcul", p["provenance"].get("metrage"), "calcul")
verifier("provenance de la fiche", p["provenance"].get("machine"), "fiche")
verifier("aucune quantité ni date recopiée",
         [k for k in ("qte_etiquettes", "delai_client", "of_numero", "date_creation") if k in ch], [])

p = op.proposer(conn, 28, "")
verifier("« 1183/0028 - DSI » → « 1183/0028 »", p["champs"].get("reference"), "1183/0028")
verifier("adhésif sans grammage connu : rien", "qte_adhesif_g" in p["champs"], False)
verifier("sans quantité : aucune case calculée", p["calcules"], [])
verifier("fiche inconnue", op.proposer(conn, 999, 10), None)

print("Depuis les commandes cochées (lignes réelles de RVGI)")
import contextlib
from app.services import erp_mirror as miroir
erp = sqlite3.connect(":memory:")
erp.row_factory = sqlite3.Row
erp.executescript("""
CREATE TABLE cde_entete (numero INTEGER, corbeille INTEGER);
CREATE TABLE cde_ligne (id INTEGER PRIMARY KEY, numero INTEGER, ligne INTEGER, code1 TEXT, code2 TEXT, qte INTEGER,
                        amjl TEXT, amje TEXT, corbeille INTEGER);
INSERT INTO cde_entete VALUES (9932770,0),(9932839,0),(9932840,0),(9932856,0),(9939999,1);
INSERT INTO cde_ligne (numero, ligne, code1, code2, qte, amjl, amje, corbeille) VALUES
 (9932770,1,'1164','0066',4000000,'2026-11-16 00:00','2026-11-13 00:00',0),
 (9932770,2,'1164','0067', 650000,'2026-11-16 00:00','2026-11-13 00:00',0),
 (9932839,1,'1183','0032',2000000,'2026-11-23 00:00','2026-11-18 00:00',0),
 (9932840,1,'1183','0032',2000000,'2026-11-22 00:00','2026-11-18 00:00',0),
 (9932856,1,'954','0087',  60000,'2026-11-27 00:00','2026-11-25 00:00',0),
 (9932856,9,'FR','FRAIS_DE_CLICHE',1,'2026-11-27 00:00','2026-11-25 00:00',0),
 (9939999,1,'1164','0017',  10000,'2026-11-30 00:00','2026-11-30 00:00',0);
""")
miroir.get_erp_db = lambda *a, **k: contextlib.nullcontext(erp)
erp.executescript("""
ALTER TABLE cde_ligne ADD COLUMN cuv TEXT DEFAULT '11';
ALTER TABLE cde_ligne ADD COLUMN des1 TEXT;
ALTER TABLE cde_ligne ADD COLUMN des2 TEXT;
ALTER TABLE cde_ligne ADD COLUMN des3 TEXT;
CREATE TABLE fic_ua (code TEXT, lib1 TEXT, nombre REAL, corbeille INTEGER);
INSERT INTO fic_ua VALUES ('11','Mille',1000,0),('5','Bobine',1,0),('1','Carton',1,0),('C','Carton',1,0);
""")
miroir.tables_presentes = lambda c: {"cde_ligne", "cde_entete", "fic_ua"}

lu = op.lire_commandes([{"numero": "9932770", "ligne": 1, "qte": None}])
verifier("L1 seule : un article", lu["articles"], ["1164/0066"])
verifier("L1 seule : quantité de la ligne", op.quantite_etiquettes(lu)[0], 4000000)
verifier("délai = date de livraison", lu["delai_client"], "2026-11-16")
lu = op.lire_commandes([{"numero": "9932770", "ligne": None}])
verifier("commande entière : deux articles", lu["articles"], ["1164/0066", "1164/0067"])
lu = op.lire_commandes([{"numero": "9932839", "ligne": None}, {"numero": "9932840", "ligne": None}])
verifier("deux commandes, même article", lu["articles"], ["1183/0032"])
verifier("quantités additionnées", op.quantite_etiquettes(lu)[0], 4000000)
verifier("la livraison la plus proche", lu["delai_client"], "2026-11-22")
lu = op.lire_commandes([{"numero": "9932856", "ligne": None}])
verifier("frais de cliché ignorés", lu["articles"], ["954/0087"])
lu = op.lire_commandes([{"numero": "9932770", "ligne": 2, "qte": 300000}])
verifier("quantité partielle du sélecteur", op.quantite_etiquettes(lu)[0], 300000)
lu = op.lire_commandes([{"numero": "9939999", "ligne": None}])
verifier("commande à la corbeille ignorée", lu["articles"], [])

conn.execute("ALTER TABLE fiches_techniques ADD COLUMN ref_produit_norm TEXT")
conn.executescript("""
UPDATE fiches_techniques SET ref_produit_norm = '1164/0017' WHERE id = 17;
UPDATE fiches_techniques SET ref_produit_norm = '1183/0028' WHERE id = 28;
INSERT INTO fiches_techniques (id, reference, ref_produit_norm, machine) VALUES
  (66, '1164/0066', '1164/0066', 'COHESIO 1'),
  (321, '1183/0032 - COHESIO1 - Laize 470', '1183/0032', 'COHESIO 1'),
  (322, '1183/0032 - COHESIO2 - Laize 570', '1183/0032', 'COHESIO 2');
""")
d = op.depuis_commandes(conn, [{"numero": "9932770", "ligne": 1}])
verifier("une fiche pour l'article : proposée", [f["id"] for f in d["fiches"]], [66])
verifier("dates de la commande : livraison et expédition",
         (d["date_livraison"], d["date_expedition"]), ("2026-11-16", "2026-11-13"))
verifier("délai proposé = livraison", d["delai_client"], "2026-11-16")
verifier("numéro proposé, tel que la création le donnera", d["numero"], "9932770/L1")
conn.execute("INSERT INTO of_imports (of_numero) VALUES ('9932770/L1')")
verifier("numéro déjà pris : suffixe (2) (règle num_of_auto)",
         op.depuis_commandes(conn, [{"numero": "9932770", "ligne": 1}])["numero"], "9932770/L1 (2)")
oid = conn.execute("SELECT id FROM of_imports WHERE of_numero = '9932770/L1'").fetchone()[0]
verifier("en modification, l'OF ne se compte pas lui-même : pas de (2)",
         op.depuis_commandes(conn, [{"numero": "9932770", "ligne": 1}], sauf_of_id=oid)["numero"], "9932770/L1")
conn.execute("DELETE FROM of_imports WHERE of_numero = '9932770/L1'")
verifier("l'id de la ligne revient pour « Voir la commande »",
         [(x["numero"], x["ligne"], bool(x["id"])) for x in d["lignes"]], [("9932770", 1, True)])
d = op.depuis_commandes(conn, [{"numero": "9932839", "ligne": None}, {"numero": "9932840", "ligne": None}])
verifier("deux fiches (une par machine) : l'ADV choisit", [f["id"] for f in d["fiches"]], [321, 322])
d = op.depuis_commandes(conn, [{"numero": "9932770", "ligne": None}])
verifier("deux articles : aucune fiche imposée", (d["article"], d["fiches"]), (None, []))
d = op.depuis_commandes(conn, [{"numero": "9932856", "ligne": 1}])
verifier("article sans fiche : liste vide", (d["article"], d["fiches"]), ("954/0087", []))

print("Unité de vente : bobines et cartons convertis en étiquettes")
erp.executescript("""
INSERT INTO cde_entete VALUES (9932858,0),(9932860,0),(9932501,0),(9932502,0);
INSERT INTO cde_ligne (numero, ligne, code1, code2, qte, amjl, amje, corbeille, cuv, des1, des2, des3) VALUES
 (9932858,1,'1183','0028',200,'2026-12-02 00:00','2026-12-01 00:00',0,'5','B440/Etiquette 102 x 150mm.','Thermique Eco Permanent,','Bobine de 440 étiquettes, M40, Enr. Ext.'),
 (9932860,1,'1183','0028',220,'2026-12-02 00:00','2026-12-01 00:00',0,'5','B440/Etiquette 102 x 150mm.','',''),
 (9932501,1,'1164','0017',3,'2026-12-02 00:00','2026-12-01 00:00',0,'1','C/60 000 Etiquettes 40x25','',''),
 (9932502,1,'1164','0017',4,'2026-12-02 00:00','2026-12-01 00:00',0,'5','Etiquette 40x25 en bobine','','');
""")
lu = op.lire_commandes([{"numero": "9932858", "ligne": 1}])
q, msgs = op.quantite_etiquettes(lu)
verifier("9932858 : 200 bobines de 440 = 88 000 étiquettes (était 200)", q, 88000)
verifier("la conversion est dite", msgs, ["9932858 L1 : 200 bobine de 440 étiquettes."])
lu = op.lire_commandes([{"numero": "9932858", "ligne": 1}, {"numero": "9932860", "ligne": 1}])
verifier("deux commandes en bobines additionnées", op.quantite_etiquettes(lu)[0], 184800)
lu = op.lire_commandes([{"numero": "9932858", "ligne": 1, "qte": 50}])
verifier("quantité partielle en bobines convertie aussi", op.quantite_etiquettes(lu)[0], 22000)
lu = op.lire_commandes([{"numero": "9932501", "ligne": 1}])
verifier("« C/60 000 » : 3 cartons = 180 000", op.quantite_etiquettes(lu)[0], 180000)
lu = op.lire_commandes([{"numero": "9932502", "ligne": 1}])
q, msgs = op.quantite_etiquettes(lu)
verifier("bobine sans nombre et sans fiche : rien d'inventé", q, None)
verifier("… et c'est signalé", "inconnu" in msgs[0], True)
verifier("bobine sans nombre : la fiche donne 500 / bobine", op.quantite_etiquettes(lu, {"nb_etiq_bobin": 500})[0], 2000)
verifier("paravent : nombre lu en tête", op.unite_de_vente("2", {"2": ("B 500 P", 1.0)}, "P500/ Etiq. 100x50")[1], 500.0)
verifier("« C50/rouleaux » : pas un nombre d'étiquettes", op.unite_de_vente("1", {"1": ("Carton", 1.0)}, "C50/rouleaux de 1000")[1], None)
verifier("« C11.200/étiq » : 11 200", op.unite_de_vente("1", {"1": ("Carton", 1.0)}, "C11.200/étiq 40x25")[1], 11200.0)
verifier("Mille : la quantité est déjà en étiquettes", op.unite_de_vente("11", {"11": ("Mille", 1000.0)}, "B500/Etiq. 9")[1], 1.0)

print("Commande au mètre : cartons de rouleaux")
erp.executescript("""
INSERT INTO cde_entete VALUES (9932835,0);
INSERT INTO cde_ligne (numero, ligne, code1, code2, qte, amjl, amje, corbeille, cuv, des1) VALUES
 (9932835,1,'122','0022',20,'2026-11-12 00:00','2026-11-10 00:00',0,'1','C32/Rouleaux, 58 x 45 ml');
""")
lu = op.lire_commandes([{"numero": "9932835", "ligne": 1}])
q, msgs = op.quantite_etiquettes(lu, F122)
verifier("20 cartons de 32 rouleaux = 640 rouleaux", q, 640)
verifier("conversion dite en rouleaux", msgs, ["9932835 L1 : 20 carton de 32 rouleaux."])
verifier("sans la fiche au mètre : rien d'inventé", op.quantite_etiquettes(lu)[0], None)

print("Numéro proposé : les lignes de frais ne comptent pas")
from app.services import rvgi_rattachement as ratt
erp.executescript("""
INSERT INTO cde_entete VALUES (9912584,0);
INSERT INTO cde_ligne (numero, ligne, code1, code2, qte, amjl, amje, corbeille) VALUES
 (9912584,1,'571','0095',200000,'2015-10-02 00:00','2015-10-01 00:00',0),
 (9912584,2,'FR','FRAIS_DOUTILS',1,'2015-10-02 00:00','2015-10-01 00:00',0),
 (9912584,3,'FR','FRAIS_DE_CLICHE',1,'2015-10-02 00:00','2015-10-01 00:00',0);
""")
produits, totaux = ratt.lignes_de_produit(erp, ["9912584", "9932856"])
verifier("9912584 : une seule ligne de produit", totaux.get("9912584"), 1)
verifier("9932856 : le cliché ne compte pas", ("9932856", 9) in produits, False)
def numero(choix):
    nommees = [x for x in choix if x["ligne"] is None or (x["numero"], x["ligne"]) in produits]
    return ratt.proposer_reference(nommees or choix, totaux)
verifier("L1 + frais d'outils → « 9912584 » (était 9912584/L1-2)",
         numero([{"numero": "9912584", "ligne": 1}, {"numero": "9912584", "ligne": 2}]), "9912584")
# Dans ce jeu, 9932856 n'a qu'une ligne de produit (L1) plus le cliché (L9).
verifier("seule ligne de produit cochée → la commande entière",
         numero([{"numero": "9932856", "ligne": 1}]), "9932856")
produits, totaux = ratt.lignes_de_produit(erp, ["9932770"])
verifier("une ligne parmi deux produits → « 9932770/L1 »",
         numero([{"numero": "9932770", "ligne": 1}]), "9932770/L1")
verifier("les deux produits → « 9932770 »",
         numero([{"numero": "9932770", "ligne": 1}, {"numero": "9932770", "ligne": 2}]), "9932770")
src_rv = open("app/routers/rvgi.py", encoding="utf-8").read()
verifier("la route du numéro utilise ce filtre", "ratt.lignes_de_produit(" in src_rv, True)

print("Recherche de commandes par numéro d'OF")
for q, attendu in [
    ("9932856/L", ["9932856"]), ("9932856/L2", ["9932856"]), ("9932856 - L1", ["9932856"]),
    ("9932128+129", ["9932128", "9932129"]),
    ("9932839, 840, 841 et 842", ["9932839", "9932840", "9932841", "9932842"]),
    ("9932858 à 861", ["9932858", "9932859", "9932860", "9932861"]),
    ("9932128/L1-3+5", ["9932128"]), ("9932128/L1 (2)", ["9932128"]),
    ("Reliquat 9932705 - L2", ["9932705"]), ("1164/0066", []), ("SONELOG", []),
]:
    verifier("« %s »" % q, ratt.numeros_dans_texte(q), attendu)

a_ratt = open("app/services/rvgi_rattachement.py", encoding="utf-8").read()
corps_cc = a_ratt[a_ratt.index("def chercher_commandes"):a_ratt.index("def _lire_lignes_commandes")]
verifier("la recherche de commandes s'en sert", "numeros_dans_texte(q)" in corps_cc, True)

print("Concordance fiche / commandes")
c_ok = op.controler_concordance(conn, [{"numero": "9932770", "ligne": 1}], 66)
verifier("fiche de l'article coché : acceptée", c_ok["ok"], True)
c_ko = op.controler_concordance(conn, [{"numero": "9932770", "ligne": 1}], 28)
verifier("fiche d'un autre produit : refusée", c_ko["ok"], False)
verifier("message explicite",
         c_ko["message"], "La fiche 1183/0028 - DSI ne correspond à aucun article des commandes cochées (1164/0066).")
c_multi = op.controler_concordance(conn, [{"numero": "9932770", "ligne": None}], 66)
verifier("deux articles cochés : refusé sans motif (un OF = un produit)", c_multi["ok"], False)
verifier("message : un OF ne couvre qu'un produit", "un OF ne couvre qu'un produit" in (c_multi["message"] or ""), True)
verifier("plusieurs commandes du MÊME article : accepté",
         op.controler_concordance(conn, [{"numero": "9932839", "ligne": None}, {"numero": "9932840", "ligne": None}], 321)["ok"], True)
verifier("ligne de frais cochée avec le produit : acceptée",
         op.controler_concordance(conn, [{"numero": "9932856", "ligne": 1}, {"numero": "9932856", "ligne": 9}], None, "954/0087")["ok"], True)
verifier("fiche par machine : la clé produit concorde",
         op.controler_concordance(conn, [{"numero": "9932839", "ligne": None}], 322)["ok"], True)
c_ref = op.controler_concordance(conn, [{"numero": "9932770", "ligne": 1}], 66, "1183/0032")
verifier("référence modifiée à la main : contrôlée aussi", c_ref["ok"], False)
verifier("sans commande (stock, marché) : rien à contrôler",
         op.controler_concordance(conn, [], 28), {"ok": True, "verifiable": False, "articles": [], "message": None})
verifier("commande à la corbeille : rien de vérifiable, pas de blocage",
         op.controler_concordance(conn, [{"numero": "9939999", "ligne": None}], 28)["ok"], True)

print("La création fait respecter le contrôle")
src_c = open("app/routers/of_import.py", encoding="utf-8").read()
corps = src_c[src_c.index("async def create_of"):src_c.index('@router.post("/api/fiches-techniques")')]
verifier("fiche obligatoire", "Choisissez la fiche technique de l'OF." in corps, True)
verifier("écart refusé sans motif", "controle[\"ok\"]" in corps and "status_code=409" in corps, True)
verifier("motif gardé dans les observations", "Écart fiche / commandes accepté" in corps, True)
verifier("écart journalisé", '"ecart_fiche_commandes": ecart' in corps, True)
verifier("route de contrôle avant /api/of/{of_id}",
         src_c.index('@router.get("/api/of/controle")') < src_c.index('@router.get("/api/of/{of_id}")'), True)

print("Route déclarée avant /api/of/{of_id}")
src = open("app/routers/of_import.py", encoding="utf-8").read()
verifier("ordre des routes",
         src.index('@router.get("/api/of/proposition")') < src.index('@router.get("/api/of/{of_id}")'), True)
verifier("ordre des routes (commandes)",
         src.index('@router.get("/api/of/depuis-commandes")') < src.index('@router.get("/api/of/{of_id}")'), True)

print("Aperçu en direct de l'OF")
src_a = open("app/routers/of_import.py", encoding="utf-8").read()
corps_a = src_a[src_a.index("async def of_apercu"):src_a.index('@router.get("/api/of/controle")')]
verifier("l'aperçu n'écrit rien en base", any(x in corps_a for x in ("INSERT", "UPDATE", "commit(")), False)
verifier("même générateur que l'OF enregistré", "generate_of_pdf(champs)" in corps_a, True)
from app.core.audit_taxonomy import SKIP_PREFIXES
verifier("aperçu exclu du journal", "/api/of/apercu" in SKIP_PREFIXES, True)

print("Impression et téléchargement de tous les OF")
src_p = open("app/routers/print.py", encoding="utf-8").read()
verifier("impression : OF sans PDF généré, plus refusé", "pdf_of_genere(entity_id)" in src_p
         and "Cet OF n'a pas de PDF associe" not in src_p, True)
corps_dl = src_a[src_a.index("def download_of_pdf"):src_a.index('@router.delete("/api/of/bulk")')]
verifier("téléchargement : OF sans PDF généré", "pdf_of_genere(of_id)" in corps_dl, True)
js = open("static/mysifa_prod_core.js", encoding="utf-8").read()
liste = js[js.index("const rows=(S.ofImports||[]).map(row=>{"):]
liste = liste[:liste.index("return h('tr',null,")]
verifier("liste : plus aucun bouton réservé aux OF déposés en PDF", "pdf_filename" in liste, False)

print("Scans d'OF dans la liste et la fenêtre")
ns_sc = {}
for nom in ("_SQL_SCAN_DE_OF", "_SQL_DERNIER_SCAN", "_SQL_DATE_SCAN"):
    exec(re.search(nom + r' = \(.*?\n\)', src_a, re.S).group(0), ns_sc)
sc = sqlite3.connect(":memory:")
sc.row_factory = sqlite3.Row
sc.executescript("""
CREATE TABLE of_imports (id INTEGER PRIMARY KEY, of_numero TEXT);
CREATE TABLE produit_documents (id INTEGER PRIMARY KEY, of_import_id INTEGER, of_numero TEXT,
  ref_produit_norm TEXT, nb_pages INTEGER, date_document TEXT, importe_le TEXT);
INSERT INTO of_imports VALUES (1121, '9932140'), (2, '9932178'), (3, 'sans scan');
INSERT INTO produit_documents VALUES
  (1, 1121, '9932140', '420/0018', 1, '24/06/2026', '2026-08-26'),
  (2, NULL, '9932178', '706/0003', 1, '2026-07-30T08:00', '2026-08-26'),
  (3, NULL, 'X', '420/0018', 1, '01/07/2026', '2026-08-26');
""")
scans = {r["id"]: r["scan_id"] for r in sc.execute(
    "SELECT o.id, (" + ns_sc["_SQL_DERNIER_SCAN"] + ") AS scan_id FROM of_imports o")}
verifier("scan relié par l'identifiant de l'OF", scans[1121], 1)
verifier("scan relié par le numéro d'OF", scans[2], 2)
verifier("OF sans scan", scans[3], None)
dates = [r[0] for r in sc.execute(
    "SELECT d.id FROM produit_documents d WHERE d.ref_produit_norm = '420/0018' ORDER BY (" +
    ns_sc["_SQL_DATE_SCAN"] + ") DESC")]
verifier("historique produit : le plus récent d'abord, dates mêlées", dates, [3, 1])
verifier("route des scans produit avant /api/of/{of_id}",
         src_a.index('@router.get("/api/of/scans-produit")') < src_a.index('@router.get("/api/of/{of_id}")'), True)

print("Tri de la liste des OF")
src_r = open("app/routers/of_import.py", encoding="utf-8").read()
# Les deux affectations sont des chaînes pures : on les rejoue telles quelles.
ns_tri = {}
exec(re.search(r'_SQL_DATE_CREATION_BRUTE = \(.*?\n\)', src_r, re.S).group(0), ns_tri)
exec(re.search(r'_SQL_DATE_CREATION_ISO = \(.*?\n\)', src_r, re.S).group(0), ns_tri)
expr = ns_tri["_SQL_DATE_CREATION_ISO"]
t = sqlite3.connect(":memory:")
t.execute("CREATE TABLE o (id INTEGER, date_creation TEXT, date_import TEXT)")
t.executemany("INSERT INTO o VALUES (?,?,?)", [
    (1, "31/10/2026", "2026-10-31T10:00:00"), (2, "05/11/2026", "2026-11-05T10:00:00"),
    (3, "2026-11-12", "2026-11-12T22:11:16"), (4, "12/11/2026", "2026-11-12T09:00:00"),
    (5, None, "2026-11-01T08:00:00"),
    (6, "2099-12-18", "2026-06-02T09:20:10")])
ordre = [r[0] for r in t.execute("SELECT id FROM o ORDER BY %s DESC, o.id DESC" % expr)]
verifier("OF créé aujourd'hui en tête, dates françaises et ISO mêlées ; "
         "date de création future rangée à sa date d'arrivée", ordre, [4, 3, 2, 5, 1, 6])

print("Dates de l'OF imprimé")
gen = open("app/services/of_pdf_generator.py", encoding="utf-8").read()
ns = {"re": re, "Any": object}
exec(re.search(r"def _fmt\(.*?\n\n\n", gen, re.S).group(0), ns)
exec(re.search(r"def _fmt_date\(.*?\n\n\n", gen, re.S).group(0), ns)
verifier("ISO → français", ns["_fmt_date"]("2026-11-18"), "18/11/2026")
verifier("français inchangé", ns["_fmt_date"]("18/11/2026"), "18/11/2026")
verifier("vide", ns["_fmt_date"](None), "")

print()
print("ÉCHECS : %d" % ko if ko else "Tout est vert.")
sys.exit(1 if ko else 0)

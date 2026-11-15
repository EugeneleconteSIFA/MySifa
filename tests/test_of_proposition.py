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
verifier("un paravent ne donne pas de nombre par bobine",
         op.etiquettes_par_bobine({"conditionnement": "Paravent de 1000 plis de 4 étiquettes"}), (None, None))
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
CREATE TABLE of_imports (id INTEGER PRIMARY KEY, adhesif_label TEXT, qte_adhesif_g REAL);
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
CREATE TABLE cde_ligne (numero INTEGER, ligne INTEGER, code1 TEXT, code2 TEXT, qte INTEGER,
                        amjl TEXT, amje TEXT, corbeille INTEGER);
INSERT INTO cde_entete VALUES (9932770,0),(9932839,0),(9932840,0),(9932856,0),(9939999,1);
INSERT INTO cde_ligne VALUES
 (9932770,1,'1164','0066',4000000,'2026-11-16 00:00','2026-11-13 00:00',0),
 (9932770,2,'1164','0067', 650000,'2026-11-16 00:00','2026-11-13 00:00',0),
 (9932839,1,'1183','0032',2000000,'2026-11-23 00:00','2026-11-18 00:00',0),
 (9932840,1,'1183','0032',2000000,'2026-11-22 00:00','2026-11-18 00:00',0),
 (9932856,1,'954','0087',  60000,'2026-11-27 00:00','2026-11-25 00:00',0),
 (9932856,9,'FR','FRAIS_DE_CLICHE',1,'2026-11-27 00:00','2026-11-25 00:00',0),
 (9939999,1,'1164','0017',  10000,'2026-11-30 00:00','2026-11-30 00:00',0);
""")
miroir.get_erp_db = lambda *a, **k: contextlib.nullcontext(erp)
miroir.tables_presentes = lambda c: {"cde_ligne", "cde_entete"}

lu = op.lire_commandes([{"numero": "9932770", "ligne": 1, "qte": None}])
verifier("L1 seule : un article", lu["articles"], ["1164/0066"])
verifier("L1 seule : quantité de la ligne", lu["qte_etiquettes"], 4000000)
verifier("délai = date de livraison", lu["delai_client"], "2026-11-16")
lu = op.lire_commandes([{"numero": "9932770", "ligne": None}])
verifier("commande entière : deux articles", lu["articles"], ["1164/0066", "1164/0067"])
lu = op.lire_commandes([{"numero": "9932839", "ligne": None}, {"numero": "9932840", "ligne": None}])
verifier("deux commandes, même article", lu["articles"], ["1183/0032"])
verifier("quantités additionnées", lu["qte_etiquettes"], 4000000)
verifier("la livraison la plus proche", lu["delai_client"], "2026-11-22")
lu = op.lire_commandes([{"numero": "9932856", "ligne": None}])
verifier("frais de cliché ignorés", lu["articles"], ["954/0087"])
lu = op.lire_commandes([{"numero": "9932770", "ligne": 2, "qte": 300000}])
verifier("quantité partielle du sélecteur", lu["qte_etiquettes"], 300000)
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
d = op.depuis_commandes(conn, [{"numero": "9932839", "ligne": None}, {"numero": "9932840", "ligne": None}])
verifier("deux fiches (une par machine) : l'ADV choisit", [f["id"] for f in d["fiches"]], [321, 322])
d = op.depuis_commandes(conn, [{"numero": "9932770", "ligne": None}])
verifier("deux articles : aucune fiche imposée", (d["article"], d["fiches"]), (None, []))
d = op.depuis_commandes(conn, [{"numero": "9932856", "ligne": 1}])
verifier("article sans fiche : liste vide", (d["article"], d["fiches"]), ("954/0087", []))

print("Route déclarée avant /api/of/{of_id}")
src = open("app/routers/of_import.py", encoding="utf-8").read()
verifier("ordre des routes",
         src.index('@router.get("/api/of/proposition")') < src.index('@router.get("/api/of/{of_id}")'), True)
verifier("ordre des routes (commandes)",
         src.index('@router.get("/api/of/depuis-commandes")') < src.index('@router.get("/api/of/{of_id}")'), True)

print("Tri de la liste des OF")
src_r = open("app/routers/of_import.py", encoding="utf-8").read()
expr = re.search(r'_SQL_DATE_CREATION_ISO = \((.*?)\n\)', src_r, re.S).group(1)
expr = "".join(re.findall(r'"((?:[^"\\]|\\.)*)"', expr))
t = sqlite3.connect(":memory:")
t.execute("CREATE TABLE o (id INTEGER, date_creation TEXT, date_import TEXT)")
t.executemany("INSERT INTO o VALUES (?,?,?)", [
    (1, "31/10/2026", "2026-10-31T10:00:00"), (2, "05/11/2026", "2026-11-05T10:00:00"),
    (3, "2026-11-12", "2026-11-12T22:11:16"), (4, "12/11/2026", "2026-11-12T09:00:00"),
    (5, None, "2026-11-01T08:00:00")])
ordre = [r[0] for r in t.execute("SELECT id FROM o ORDER BY %s DESC, o.id DESC" % expr)]
verifier("OF créé aujourd'hui en tête, dates françaises et ISO mêlées", ordre, [4, 3, 2, 5, 1])

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

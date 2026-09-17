"""
Choix de la fiche technique et OF complété depuis sa fiche (17/09/2026).

Cas réels relevés en production :
- dossier 9931675+996, Cohésio 2, laize 570 : l'écran montrait la fiche
  « 1220/0001 - COHESIO1 - Laize 470 » parce que « Cohésio 2 » ≠ « COHESIO 2 »
  en LOWER(TRIM()) ;
- OF 9931675 (Access) : référence = numéro d'OF, ni machine ni outil ;
- 102 dossiers dont `of_import_id` n'était pas dans `planning_of_links`.

Lancer : python3 tests/test_of_depuis_fiche.py
"""
import importlib.util
import sqlite3
import sys

sys.path.insert(0, ".")

from app.services.fiche_choix import cle_machine, meilleure_fiche, choisir_fiche, sql_cle_machine
from app.services import of_depuis_fiche as odf

ko = 0


def verifier(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    ko += 0 if ok else 1
    print(("  OK  " if ok else "  KO  ") + libelle + ("" if ok else f" — obtenu {obtenu!r}, attendu {attendu!r}"))


conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.executescript("""
CREATE TABLE machines (id INTEGER PRIMARY KEY, nom TEXT);
CREATE TABLE fiches_techniques (
  id INTEGER PRIMARY KEY, reference TEXT, ref_produit_norm TEXT, machine TEXT,
  laize REAL, laize_optimale REAL, format TEXT, support TEXT, glassine TEXT,
  adhesif TEXT, qte_au_mille REAL, outil1_forme TEXT, outil1_numero_sifa TEXT,
  outil2_forme TEXT, outil2_numero_sifa TEXT, mandrin_dia TEXT,
  mandrin_longueur REAL, conditionnement TEXT, cartons TEXT, cales_sachets TEXT,
  palette_type TEXT, particularite TEXT);
CREATE TABLE of_imports (id INTEGER PRIMARY KEY, of_numero TEXT, reference TEXT,
  machine TEXT, laize REAL, format TEXT, matiere TEXT, pdf_filename TEXT,
  outil_1_forme TEXT, outil_1_numero TEXT);
CREATE TABLE planning_entries (id INTEGER PRIMARY KEY, numero_of TEXT,
  ref_produit TEXT, machine_id INTEGER, laize REAL, of_import_id INTEGER);
CREATE TABLE planning_of_links (id INTEGER PRIMARY KEY AUTOINCREMENT,
  planning_entry_id INTEGER NOT NULL, of_import_id INTEGER NOT NULL,
  position INTEGER DEFAULT 0, created_by TEXT, created_at TEXT,
  UNIQUE(planning_entry_id, of_import_id));
CREATE TRIGGER trg_ins AFTER INSERT ON planning_of_links BEGIN
  UPDATE planning_entries SET of_import_id = (
    SELECT of_import_id FROM planning_of_links
    WHERE planning_entry_id = NEW.planning_entry_id
    ORDER BY position ASC, id ASC LIMIT 1)
  WHERE id = NEW.planning_entry_id;
END;
INSERT INTO machines VALUES (1,'Cohésio 1'),(3,'Cohésio 2'),(4,'DSI');
INSERT INTO fiches_techniques (id, reference, ref_produit_norm, machine, laize_optimale,
  format, support, glassine, adhesif, outil1_forme, outil1_numero_sifa, mandrin_dia,
  conditionnement, cartons) VALUES
 (13,'1220/0001 - COHESIO1 - Laize 470','1220/0001','COHESIO 1',470,'105 x 265 mm',
  'VELIN ETI MATT','ITASA jaune KA','Permanent 2021-19','Plaque','2419','Tube 1500x76',
  'Bobine de 1 600 étiquettes','Carton 385'),
 (780,'1220/0001 - COHESIO2 - Laize 570','1220/0001','COHESIO 2',570,'105 x 265 mm',
  'VELIN ETI MATT','ITASA jaune KA','Permanent 2028Y - 19','Plaque','2776','Tube 1500x76',
  'Bobine de 1 600 étiquettes','Carton 385');
INSERT INTO of_imports (id, of_numero, reference, machine, laize, format, matiere) VALUES
 (950,'9931675','9931675',NULL,NULL,NULL,NULL),
 (1409,'9931675+996','1220/0001 - COHESIO2 - Laize 570','COHESIO 2',570,
  '1220/0001 - COHESIO2 - Laize 570','VELIN ETI MATT'),
 (1500,'9939999','1220/0001',NULL,NULL,NULL,'PP 95µ BLANC MAT');
INSERT INTO planning_entries VALUES (93,'9931675+996','1220/0001',3,570,1409);
INSERT INTO planning_of_links (planning_entry_id, of_import_id, position) VALUES (93,950,0);
UPDATE planning_entries SET of_import_id = 1409 WHERE id = 93;
""")

print("Clé machine")
verifier("Cohésio 2 = COHESIO 2 = COHESIO2",
         {cle_machine("Cohésio 2"), cle_machine("COHESIO 2"), cle_machine("COHESIO2")}, {"cohesio2"})
verifier("équivalent SQL",
         conn.execute("SELECT " + sql_cle_machine("?"), ("Cohésio 2",)).fetchone()[0], "cohesio2")

print("Choix de la fiche")
fts = [dict(r) for r in conn.execute("SELECT * FROM fiches_techniques")]
verifier("machine accentuée du planning → fiche Cohésio 2",
         meilleure_fiche(fts, "Cohésio 2")["id"], 780)
verifier("machine inconnue, laize 570 → fiche laize 570",
         meilleure_fiche(fts, None, 570)["id"], 780)
verifier("référence exacte de l'OF prime sur la machine",
         meilleure_fiche(fts, "Cohésio 1", None, "1220/0001 - COHESIO2 - Laize 570")["id"], 780)
verifier("Cohésio 1 → fiche Cohésio 1", choisir_fiche(conn, "1220/0001", "Cohésio 1")["id"], 13)

print("OF complété depuis sa fiche")
of_seul = odf.completer_of(conn, {"id": 9, "of_numero": "Marché 746", "reference": "Marché 746"})
verifier("réf = numéro d'OF, ni dossier ni commande : rien n'est inventé",
         (of_seul["reference"], of_seul.get("_fiche_id")), ("Marché 746", None))

of1409 = odf.completer_of(conn, dict(conn.execute("SELECT * FROM of_imports WHERE id=1409").fetchone()))
verifier("référence ramenée à la clé produit", of1409["reference"], "1220/0001")
verifier("format = libellé de fiche remplacé par le vrai format", of1409["format"], "105 x 265 mm")
verifier("outil de la fiche Cohésio 2", (of1409["outil_1_forme"], of1409["outil_1_numero"]), ("Plaque", "2776"))
verifier("conditionnement repris", of1409.get("conditionnement"), "Bobine de 1 600 étiquettes")

# L'OF 950, relié au dossier 93 par planning_of_links, retrouve son produit
# par le dossier.
of950 = odf.completer_of(conn, dict(conn.execute("SELECT * FROM of_imports WHERE id=950").fetchone()))
verifier("réf = numéro d'OF → produit du dossier relié", of950["reference"], "1220/0001")
verifier("… machine et laize du dossier départagent la fiche", of950.get("_fiche_id"), 780)
verifier("… machine de la fiche posée sur l'OF", of950.get("machine"), "COHESIO 2")
of1500 = odf.completer_of(conn, dict(conn.execute("SELECT * FROM of_imports WHERE id=1500").fetchone()))
verifier("une matière portée par l'OF n'est jamais remplacée", of1500["matiere"], "PP 95µ BLANC MAT")

print("RVGI : un seul article, sinon rien")
verifier("numéro sans commande 99xxxxx", odf.article_rvgi_unique("Marché 746 - Reliquat 4"), None)

print("Migration : liens réalignés")
spec = importlib.util.spec_from_file_location(
    "mig", "app/core/migrations/2026_09_17_realigner_liens_of_planning.py")
mig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig)
mig.appliquer(conn)
liens = [r[0] for r in conn.execute(
    "SELECT of_import_id FROM planning_of_links WHERE planning_entry_id=93 ORDER BY position, id")]
verifier("OF de la colonne promu en tête, l'ancien lien conservé", liens, [1409, 950])
verifier("colonne inchangée",
         conn.execute("SELECT of_import_id FROM planning_entries WHERE id=93").fetchone()[0], 1409)
mig.appliquer(conn)
verifier("rejouable sans effet",
         conn.execute("SELECT COUNT(*) FROM planning_of_links WHERE planning_entry_id=93").fetchone()[0], 2)

# Colonne sur un OF sans PDF alors qu'un lien porte un vrai PDF : la colonne a tort.
conn.executescript("""
INSERT INTO of_imports (id, of_numero, pdf_filename) VALUES (2000,'9932314','a.pdf'),(2001,'9932314-317-318',NULL);
INSERT INTO planning_entries VALUES (427,'9932314-317-318',NULL,1,NULL,NULL);
INSERT INTO planning_of_links (planning_entry_id, of_import_id, position) VALUES (427,2000,0);
UPDATE planning_entries SET of_import_id = 2001 WHERE id = 427;
""")
mig.appliquer(conn)
verifier("un OF avec PDF n'est pas détrôné par un rendu sur modèle",
         conn.execute("SELECT of_import_id FROM planning_entries WHERE id=427").fetchone()[0], 2000)

print()
print("ÉCHECS : %d" % ko if ko else "Tous les cas passent.")
sys.exit(1 if ko else 0)

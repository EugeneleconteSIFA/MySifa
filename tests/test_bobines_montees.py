"""
Postes de deroulement, reconnaissance des bobines, bobines montees.

Chaque bloc protege une regle posee le 10/09/2026 avec l'atelier :

1. **Le poste se deduit du code avant le fournisseur.** Likexin livre glassine
   ET frontal : seule la regle de prefixe (G = glassine, le reste = frontal)
   les separe. Un fournisseur a nature unique (Kanzan) suffit ; un fournisseur
   qui designe les deux postes sans regle ne doit RIEN proposer.
2. **Un complexe va sur le poste frontal.** Un fournisseur « frontal +
   complexe » donne un poste sur, sans nature exacte.
3. **Un poste plein demonte la plus ancienne**, et l'annulation du scan rend
   sa place a la bobine poussee.
4. **Rescanner une bobine montee ne change rien**, et le meme scan sur le meme
   dossier est un doublon.
5. **Une bobine de nature inconnue n'occupe aucune place** tant que personne
   n'a tranche.
6. **Au demarrage d'un dossier, ce qui reste monte est repris sans rescan**,
   origine recopiee ; une bobine decochee est demontee ; la glassine n'est
   pas rattachee quand le poste frontal ne porte que des complexes (elle reste
   montee) ; une reprise ne duplique jamais.
7. **La memoire des natures n'apprend que ce qui est arrete** : jamais une
   categorie de fiche fournisseur (Burgo note « complexe » alors qu'il livre du
   frontal empoisonnerait la memoire).

Lancer : python3 tests/test_bobines_montees.py
"""
import importlib.util
import json
import sqlite3
import sys

sys.path.insert(0, ".")

from app.services import poste_bobine as pb        # noqa: E402
from app.services import bobines_montees as bm     # noqa: E402

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


def migration(chemin):
    spec = importlib.util.spec_from_file_location("m", chemin)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def base():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript("""
        CREATE TABLE machines (id INTEGER PRIMARY KEY, nom TEXT, code TEXT, actif INTEGER DEFAULT 1,
            sans_matiere_premiere INTEGER NOT NULL DEFAULT 0);
        INSERT INTO machines VALUES (1,'Cohésio 1','C1',1,0), (3,'Cohésio 2','C2',1,0), (5,'Repiquage','REP',1,1);
        CREATE TABLE fournisseurs_fsc (id INTEGER PRIMARY KEY, nom TEXT, licence TEXT, certificat TEXT,
            categories TEXT, actif INTEGER DEFAULT 1);
        INSERT INTO fournisseurs_fsc (id, nom, categories) VALUES
            (10,'Likexin','["sous_traitant","glassine","frontal","complexe"]'),
            (11,'Kanzan','["frontal"]'),
            (12,'Guyenne','["frontal","complexe"]'),
            (13,'Suzhou','["glassine","complexe","frontal"]'),
            (14,'Burgo / Mosaico','["complexe"]'),
            (15,'Sato', NULL);
        CREATE TABLE matieres_premieres (id INTEGER PRIMARY KEY, categorie TEXT, reference TEXT);
        INSERT INTO matieres_premieres VALUES (1,'glassine','GL62'), (2,'frontal','VEL80');
        CREATE TABLE stock_bobines (id INTEGER PRIMARY KEY, code_barre TEXT UNIQUE, matiere_id INTEGER);
        INSERT INTO stock_bobines VALUES (1,'PZH2604122-07',1);
        CREATE TABLE stock_receptions (id INTEGER PRIMARY KEY, fournisseur TEXT, certificat_fsc TEXT,
            fsc_type_claim TEXT);
        CREATE TABLE stock_reception_items (id INTEGER PRIMARY KEY, reception_id INTEGER, code_barre TEXT,
            scanned_at TEXT, matiere_id INTEGER);
        CREATE TABLE fab_matieres_utilisees (id INTEGER PRIMARY KEY AUTOINCREMENT, machine_id INTEGER,
            machine_nom TEXT, operateur TEXT, no_dossier TEXT, code_barre TEXT NOT NULL,
            scanned_at TEXT NOT NULL, reception_id INTEGER, liaison_mode TEXT,
            fournisseur_manual TEXT, certificat_fsc_manual TEXT, origine_detection TEXT,
            origine_confiance TEXT);
        CREATE TABLE bobine_signatures (id INTEGER PRIMARY KEY AUTOINCREMENT, type TEXT NOT NULL,
            valeur TEXT NOT NULL, specificite INTEGER NOT NULL DEFAULT 0,
            observations TEXT NOT NULL DEFAULT '{}', total INTEGER NOT NULL DEFAULT 0,
            premier_vu TEXT, dernier_vu TEXT, UNIQUE(type, valeur));
    """)
    # Historique : un scan Burgo, fournisseur a fiche « complexe ».
    conn.execute("""INSERT INTO fab_matieres_utilisees (machine_id, no_dossier, code_barre, scanned_at,
                    liaison_mode, fournisseur_manual) VALUES (1,'D0','217114111177','2026-09-01T10:00:00',
                    'manual','Burgo / Mosaico')""")
    conn.execute("""INSERT INTO fab_matieres_utilisees (machine_id, no_dossier, code_barre, scanned_at,
                    liaison_mode, fournisseur_manual) VALUES (1,'D0','G1101-26050456-470-35',
                    '2026-09-01T10:01:00','manual','Likexin')""")
    migration("app/core/migrations/2026_09_10_postes_deroulement.py").appliquer(conn)
    migration("app/core/migrations/2026_09_10_bobines_montees.py").appliquer(conn)
    migration("app/core/migrations/2026_09_10_bobines_montees_remplacement.py").appliquer(conn)
    migration("app/core/migrations/2026_09_10_bobines_heritees.py").appliquer(conn)
    return conn


def scan(conn, machine, code, dossier, quand):
    return conn.execute(
        "INSERT INTO fab_matieres_utilisees (machine_id, no_dossier, code_barre, scanned_at) VALUES (?,?,?,?)",
        (machine, dossier, code, quand)).lastrowid


print("\n1. Referentiel seede")
c = base()
check("2 postes par machine consommatrice, aucun sur le repiquage",
      [(r["machine_id"], r["poste"], r["places"]) for r in c.execute(
          "SELECT * FROM machine_postes_deroulement ORDER BY machine_id, poste")],
      [(1, "frontal", 2), (1, "glassine", 2), (3, "frontal", 2), (3, "glassine", 2)])
check("regles Likexin : G glassine, tout autre code frontal",
      sorted((r["motif"], r["categorie"]) for r in pb.regles_code(c)),
      [("", "frontal"), ("G", "glassine")])
migration("app/core/migrations/2026_09_10_postes_deroulement.py").appliquer(c)
check("migration rejouable sans doublon",
      c.execute("SELECT COUNT(*) FROM fournisseur_regles_code").fetchone()[0], 2)
try:
    pb.enregistrer_postes(c, 1, [{"poste": "frontal", "places": 9}], "t")
    check("places hors bornes refusees", "accepte", "refuse")
except ValueError:
    check("places hors bornes refusees", "refuse", "refuse")
check("0 place = poste inactif",
      [p["poste"] for p in pb.postes_machine(
          c, 3 if pb.enregistrer_postes(c, 3, [{"poste": "glassine", "places": 0}], "t") else 3)],
      ["frontal"])

print("\n2. Reconnaissance du poste")
L = {"fournisseur": "Likexin", "confiance": "probable"}
r = pb.resoudre(c, "G1101-26061706-470-4", machine_id=1, fournisseur=L)
check("Likexin G -> glassine par regle", (r["categorie"], r["poste"], r["source"]), ("glassine", "glassine", "regle"))
r = pb.resoudre(c, "R1101-26061705-470-22", machine_id=1, fournisseur=L)
check("Likexin R -> frontal par regle", (r["categorie"], r["poste"], r["source"]), ("frontal", "frontal", "regle"))
check("confiance plafonnee a celle du fournisseur", r["confiance"], "probable")
r = pb.resoudre(c, "60226140607", machine_id=1, fournisseur={"fournisseur": "Kanzan", "confiance": "certain"})
check("Kanzan (frontal seul) -> frontal", (r["categorie"], r["poste"], r["source"]), ("frontal", "frontal", "fournisseur"))
r = pb.resoudre(c, "GUY-1", machine_id=1, fournisseur={"fournisseur": "Guyenne", "confiance": "probable"})
check("frontal + complexe -> poste frontal, nature inconnue", (r["categorie"], r["poste"]), (None, "frontal"))
r = pb.resoudre(c, "SZ-99", machine_id=1, fournisseur={"fournisseur": "Suzhou", "confiance": "certain"})
check("fournisseur des deux postes sans regle -> rien", (r["trouve"], r["poste"]), (False, None))
r = pb.resoudre(c, "PZH2604122-07", machine_id=1, fournisseur={"fournisseur": "Suzhou", "confiance": "certain"})
check("bobine du stock -> nature de sa matiere, certaine", (r["categorie"], r["source"], r["confiance"]),
      ("glassine", "stock", "certain"))
r = pb.resoudre(c, "123", machine_id=1, fournisseur={"fournisseur": "Likexin", "confiance": "ambigu"})
check("fournisseur ambigu -> la regle ne s'applique pas", r["source"], None)

print("\n3. Memoire des natures")
check("reprise : Burgo (fiche « complexe ») n'est PAS appris",
      pb.resoudre(c, "217112111183", machine_id=1, fournisseur={})["trouve"], False)
for code in ("X9-001", "X9-002", "X9-003"):
    pb.apprendre_categorie(c, code, "glassine")
r = pb.resoudre(c, "X9-004", machine_id=1, fournisseur={})
check("3 saisies concordantes -> signature probable", (r["categorie"], r["source"], r["confiance"]),
      ("glassine", "signature", "probable"))
pb.apprendre_categorie(c, "X9-005", "frontal")
r = pb.resoudre(c, "X9-006", machine_id=1, fournisseur={})
check("3 glassine / 1 frontal -> glassine seulement suggeree (75 %)",
      (r["categorie"], r["confiance"]), ("glassine", "suggere"))
pb.apprendre_categorie(c, "X9-006", "frontal")
pb.apprendre_categorie(c, "X9-007", "frontal")
r = pb.resoudre(c, "X9-008", machine_id=1, fournisseur={})
check("forme vue a parts egales sous deux natures -> plus de proposition", r["trouve"], False)

print("\n4. Montage, places, doublon, annulation")
c = base()
a = scan(c, 1, "F-A", "D1", "2026-09-10T06:00:00")
b = scan(c, 1, "F-B", "D1", "2026-09-10T06:01:00")
check("A montee", bm.monter(c, 1, "F-A", categorie="frontal", fab_matiere_id=a, no_dossier="D1")["action"], "montee")
bm.monter(c, 1, "F-B", categorie="frontal", fab_matiere_id=b, no_dossier="D1")
check("rescan de B -> deja montee", bm.monter(c, 1, "F-B", categorie=None, no_dossier="D2")["action"], "deja_montee")
check("doublon : B deja montee ET deja scannee sur D1", bm.scan_en_double(c, 1, "F-B", "D1"), b)
check("pas de doublon sur un autre dossier", bm.scan_en_double(c, 1, "F-B", "D2"), None)
cc = scan(c, 1, "F-C", "D2", "2026-09-10T09:00:00")
res = bm.monter(c, 1, "F-C", categorie="complexe", fab_matiere_id=cc, no_dossier="D2")
check("C (complexe) sur poste frontal plein -> A demontee", [x["code_barre"] for x in res["demontees"]], ["F-A"])
check("poste frontal = B, C", [x["code_barre"] for x in bm.etat_machine(c, 1)["postes"][0]["bobines"]], ["F-B", "F-C"])
check("scan de C annule", bm.annuler_scan(c, cc), 1)
check("A retrouve sa place", [x["code_barre"] for x in bm.etat_machine(c, 1)["postes"][0]["bobines"]], ["F-A", "F-B"])

g = scan(c, 1, "G-1", "D2", "2026-09-10T09:05:00")
check("nature inconnue -> en attente", bm.monter(c, 1, "G-1", fab_matiere_id=g)["montee"]["poste"], None)
check("en attente n'occupe aucune place", bm.etat_machine(c, 1)["postes"][1]["libres"], 2)
res = bm.fixer_poste(c, g, "glassine", par="op")
check("l'operateur tranche -> montee sur glassine", (res["action"], res["montee"]["poste"]), ("poste_corrige", "glassine"))
check("la nature est ecrite sur le scan",
      tuple(c.execute("SELECT categorie_bobine, poste, poste_source FROM fab_matieres_utilisees WHERE id=?", (g,)).fetchone()),
      ("glassine", "glassine", "saisie"))
check("resolution suivante : deja montee", pb.resoudre(c, "G-1", machine_id=1)["source"], "montee")

res = bm.monter(c, 3, "G-1", categorie="glassine", no_dossier="D9")
check("scannee sur une autre machine -> montee la-bas", res["action"], "montee")
check("... et demontee ici (deplacee)",
      c.execute("SELECT motif_demontage FROM bobines_montees WHERE machine_id=1 AND code_barre='G-1'").fetchone()[0],
      "deplacee")
check("repiquage : aucun etat", bm.monter(c, 5, "Z-1", categorie="frontal")["action"], "sans_poste")

print("\n5. Reprise au demarrage d'un dossier (lot 4)")
c = base()
fa = c.execute("""INSERT INTO fab_matieres_utilisees (machine_id, no_dossier, code_barre, scanned_at,
                  liaison_mode, fournisseur_manual, certificat_fsc_manual) VALUES
                  (1,'D1','F-A','2026-09-10T06:00:00','manual','Kanzan','FSC-C000')""").lastrowid
g1 = scan(c, 1, "G-1", "D1", "2026-09-10T06:01:00")
bm.monter(c, 1, "F-A", categorie="frontal", fab_matiere_id=fa, no_dossier="D1")
bm.monter(c, 1, "G-1", categorie="glassine", fab_matiere_id=g1, no_dossier="D1")
res = bm.reprendre(c, 1, "D2", par="op", machine_nom="Cohésio 1")
check("D2 herite du frontal et de la glassine", sorted(b["code_barre"] for b in res["rattachees"]), ["F-A", "G-1"])
ligne = dict(c.execute("SELECT * FROM fab_matieres_utilisees WHERE no_dossier='D2' AND code_barre='F-A'").fetchone())
check("origine recopiee, heritage trace",
      (ligne["fournisseur_manual"], ligne["certificat_fsc_manual"], ligne["herite_de_id"], ligne["poste_source"]),
      ("Kanzan", "FSC-C000", fa, "montee"))
check("reprise rejouee -> aucun doublon", (len(bm.reprendre(c, 1, "D2")["rattachees"]),
      c.execute("SELECT COUNT(*) FROM fab_matieres_utilisees WHERE no_dossier='D2'").fetchone()[0]), (0, 2))
mont_fa = c.execute("SELECT id FROM bobines_montees WHERE code_barre='F-A'").fetchone()[0]
res = bm.reprendre(c, 1, "D3", retirer=[mont_fa, 99999])
check("frontal decoche -> demonte, seule la glassine passe",
      (res["retirees"], [b["code_barre"] for b in res["rattachees"]]), (["F-A"], ["G-1"]))
check("... heritee de D2, le dernier dossier qui l'a eue", res["rattachees"][0]["dossier_origine"], "D2")
cx = scan(c, 1, "CX-1", "D3", "2026-09-10T10:00:00")
bm.monter(c, 1, "CX-1", categorie="complexe", fab_matiere_id=cx, no_dossier="D3")
res = bm.reprendre(c, 1, "D4")
check("frontal = complexe seul -> glassine gardee mais non rattachee",
      ([b["code_barre"] for b in res["rattachees"]], res["glassine_non_rattachee"]), (["CX-1"], ["G-1"]))
check("... et toujours montee", [b["code_barre"] for b in bm.etat_machine(c, 1)["postes"][1]["bobines"]], ["G-1"])
xx = scan(c, 1, "XX-9", "D4", "2026-09-10T11:00:00")
bm.monter(c, 1, "XX-9", fab_matiere_id=xx)
check("poste inconnu -> rattachee par prudence",
      [b["code_barre"] for b in bm.reprendre(c, 1, "D5")["rattachees"]], ["G-1", "CX-1", "XX-9"])
check("etat : dernier dossier de chaque bobine",
      bm.etat_machine(c, 1)["postes"][0]["bobines"][0]["dernier_dossier"], "D5")

print("\n6. Diagnostic")
c = base()
dg = pb.diagnostic(c)
check("ambigus : Suzhou (Likexin a sa regle)", [f["nom"] for f in dg["ambigus"]], ["Suzhou"])

print()
print("TOUT PASSE" if ko == 0 else f"{ko} ECHEC(S)")
sys.exit(1 if ko else 0)

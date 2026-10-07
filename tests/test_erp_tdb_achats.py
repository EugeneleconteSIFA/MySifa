"""
TDB Achats de l'ERP : ce que compte chaque tuile (app/services/erp_tdb.py).

Ce que ce test protège — les pièges du carnet client, rejoués côté achats :

1. **Une ligne soldée ou partielle n'est pas « ouverte ».** La tuile compte
   `lpos = 0`, comme l'écran Commandes fournisseurs qu'elle ouvre.
2. **Une ligne sans commande n'existe pas.** L'export filtre `corbeille = 0`
   table par table : des lignes arrivent sans leur entête et resteraient
   « en cours » pour toujours.
3. **Une date sentinelle n'est pas un retard.** `30/11/1999` veut dire « non
   renseignée » ; au-delà de 90 jours la ligne est dormante, comptée à part.
4. **La réception se lit sur le couple (numéro, ligne)**, jamais sur le numéro
   seul.

Le miroir est un fichier SQLite temporaire : aucune base réelle n'est lue.
"""
import os
import sqlite3
import sys
import tempfile
from datetime import date, timedelta

sys.path.insert(0, ".")
from app.services import erp_mirror as miroir   # noqa: E402
from app.services import erp_tdb                # noqa: E402
from app.services import erp_types              # noqa: E402

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


def jour(n):
    return (date.today() + timedelta(days=n)).isoformat() + " 00:00:00"


dossier = tempfile.mkdtemp()
chemin = os.path.join(dossier, "miroir_achats.db")
c = sqlite3.connect(chemin)
c.executescript("""
CREATE TABLE cdf_entete(id INTEGER PRIMARY KEY, numero INTEGER, rs TEXT);
CREATE TABLE cdf_ligne(id INTEGER PRIMARY KEY, numero INTEGER, ligne INTEGER, lpos INTEGER,
                       amjl TEXT, type INTEGER, des1 TEXT, code1 TEXT, code2 TEXT, qte REAL);
CREATE TABLE lif_ligne(id INTEGER PRIMARY KEY, numero INTEGER, ligne INTEGER, ref TEXT,
                       amjl TEXT, qte REAL);
""")
c.executemany("INSERT INTO cdf_entete(numero, rs) VALUES (?, ?)",
              [(1, "FOU A"), (2, "FOU B"), (3, "FOU C")])
c.executemany(
    "INSERT INTO cdf_ligne(numero, ligne, lpos, amjl, type, des1, code1, code2, qte)"
    " VALUES (?,?,?,?,?,?,?,?,?)",
    [
        (1, 1, 0, jour(-3), 9, "En retard", "552", "0007", 100),
        (1, 2, 0, jour(3), 1, "Attendue cette semaine", "890", "0001", 5),
        (2, 1, 0, jour(-200), 11, "Dormante", "1", "1", 1),
        (2, 2, 2, jour(-5), 9, "Soldée", "1", "2", 3),
        (3, 1, 0, "1999-11-30 00:00:00", 9, "Date sentinelle", "1", "3", 1),
        (9, 1, 0, jour(-2), 9, "Orpheline", "1", "4", 1),
        (3, 2, 1, jour(-1), 3, "Partielle", "1", "5", 2),
    ])
c.executemany(
    "INSERT INTO lif_ligne(numero, ligne, ref, amjl, qte) VALUES (?,?,?,?,?)",
    [(1, 1, "BR1", jour(0), 50), (2, 2, "BR2", jour(-5), 3), (1, 1, "BR0", jour(-10), 10)])
c.commit()
c.close()

miroir.ERP_MIRROR_DB = chemin
erp_types.familles_par_type = lambda conn=None: {9: "matiere", 1: "sous_traitance", 11: "outillage"}

d = erp_tdb.achats()

print("\nCommandes fournisseurs ouvertes")
check("ouvertes : ni soldée, ni partielle, ni orpheline",
      (d["ouvertes"]["lignes"], d["ouvertes"]["commandes"]), (4, 3))
check("en retard : la sentinelle et la dormante écartées",
      (d["ouvertes"]["retard"]["lignes"], d["ouvertes"]["retard"]["commandes"]), (1, 1))
check("dormante comptée à part", d["ouvertes"]["dormant"]["lignes"], 1)
check("attendue sous 7 jours", d["ouvertes"]["semaine"]["lignes"], 1)
check("liste des retards", [r["des1"] for r in d["retards"]], ["En retard"])
check("par famille", [(f["famille"], f["lignes"], f["retard"]) for f in d["par_famille"]],
      [("matiere", 2, 1), ("sous_traitance", 1, 0), ("outillage", 1, 0)])

print("\nRéceptions des 7 derniers jours")
check("lignes et commandes", (d["receptions"]["lignes"], d["receptions"]["commandes"]), (2, 2))
check("aujourd'hui", d["receptions"]["aujourdhui"], 1)
check("désignation lue sur le couple (numéro, ligne)",
      [(r["ref"], r["designation"]) for r in d["receptions_items"]],
      [("BR1", "En retard"), ("BR2", "Soldée")])
check("rien d'indisponible", d["indispo"], [])

print("\nMiroir partiel")
c = sqlite3.connect(chemin)
c.execute("ALTER TABLE lif_ligne RENAME TO lif_ligne_absente")
c.commit()
c.close()
d = erp_tdb.achats()
check("réceptions muettes, sans faire tomber l'écran", d["receptions"], None)
check("les achats ouverts restent calculés", d["ouvertes"]["lignes"], 4)

print()
if ko:
    print(f"test_erp_tdb_achats : {ko} échec(s)")
    sys.exit(1)
print("test_erp_tdb_achats : OK")

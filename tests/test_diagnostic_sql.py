# -*- coding: utf-8 -*-
"""
Encadrement de la lecture SQL de diagnostic.

Ce qui est vérifié :
  - une lecture métier normale passe, y compris jointure, CTE, agrégat ;
  - une table hors liste blanche est refusée, et le motif est nommé ;
  - une colonne masquée revient NULL, et résiste à substr / length /
    group_concat / LIKE — il n'y a pas de chemin de reconstitution ;
  - toute écriture est refusée : UPDATE, DELETE, DROP, INSERT, ATTACH, PRAGMA,
    y compris un PRAGMA déguisé en fonction table ;
  - le schéma ne s'énumère pas, et une vue ne fait pas traverser la liste
    blanche ;
  - une fonction hors liste est refusée ;
  - deux instructions dans un seul appel sont refusées ;
  - une requête qui part en vrille est avortée, pas subie ;
  - le plafond de lignes tronque et le signale ;
  - liste blanche vide = rien ne sort.

Lancer : python3 tests/test_diagnostic_sql.py
"""

import os
import sqlite3
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

from app.services import diagnostic_sql as D

_ok = True
_RIEN = object()


def ok(libelle, valeur, attendu=_RIEN):
    global _ok
    bon = bool(valeur) if attendu is _RIEN else (valeur == attendu)
    if not bon:
        _ok = False
    print(("ok   " if bon else "ECHEC") + " " + libelle.ljust(58) + " " + repr(valeur)[:70])


def refuse(libelle, sql, motif_attendu=None):
    """Vérifie que la requête est bloquée, et que le motif est parlant."""
    global _ok
    try:
        D.executer(CHEMIN, sql)
    except (D.DiagnosticRefus, D.DiagnosticTropLong) as e:
        bon = motif_attendu is None or motif_attendu in str(e)
        if not bon:
            _ok = False
        print(("ok   " if bon else "ECHEC") + " " + libelle.ljust(58) + " " + str(e)[:70])
        return
    _ok = False
    print("ECHEC " + libelle.ljust(58) + " PASSEE ALORS QU'ELLE DEVAIT ETRE BLOQUEE")


def depot_de_test(chemin):
    """Base jouet qui imite la structure de MySifa : métier + sensible."""
    con = sqlite3.connect(chemin)
    con.executescript("""
        CREATE TABLE ordres_fabrication (id INTEGER, ref TEXT, metrage REAL, statut TEXT, machine_id INTEGER);
        CREATE TABLE operations (id INTEGER, of_id INTEGER, type TEXT, duree_min INTEGER);
        CREATE TABLE utilisateurs (id INTEGER, email TEXT, role TEXT, mot_de_passe_hash TEXT, totp_secret TEXT);
        CREATE TABLE paie (id INTEGER, salarie TEXT, brut REAL);
        CREATE TABLE gros (n INTEGER);
        CREATE VIEW vue_paie AS SELECT id, salarie, brut FROM paie;
    """)
    con.executemany("INSERT INTO ordres_fabrication VALUES (?,?,?,?,?)",
                    [(i, f"OF-{i}", 100.0 * i, "en_cours" if i % 2 else "termine", i % 3)
                     for i in range(1, 301)])
    con.executemany("INSERT INTO operations VALUES (?,?,?,?)",
                    [(i, i, "calage" if i % 2 else "tirage", 10 + i) for i in range(1, 301)])
    con.executemany("INSERT INTO utilisateurs VALUES (?,?,?,?,?)", [
        (1, "eleconte@sifa.pro", "super_admin", "$2b$12$abcdefghijkl", "JBSWY3DPEHPK3PXP"),
        (2, "op@sifa.pro", "operateur", "$2b$12$zzzzzzzzzzzz", "KRSXG5A="),
    ])
    con.execute("INSERT INTO paie VALUES (1,'X',3200.0)")
    con.executemany("INSERT INTO gros VALUES (?)", [(i,) for i in range(4000)])
    con.commit()
    con.close()


def main():
    global CHEMIN
    with tempfile.TemporaryDirectory() as tmp:
        CHEMIN = os.path.join(tmp, "test.db")
        depot_de_test(CHEMIN)

        print("--- liste blanche vide ---")
        D.TABLES_LISIBLES = set()
        refuse("rien ne sort tant que la liste blanche est vide",
               "SELECT 1", "TABLES_LISIBLES est vide")

        # Configuration de test : deux tables métier, plus utilisateurs avec
        # ses deux colonnes sensibles masquées.
        D.TABLES_LISIBLES = {"ordres_fabrication", "operations", "utilisateurs", "gros"}
        D.COLONNES_MASQUEES = {("utilisateurs", "mot_de_passe_hash"),
                               ("utilisateurs", "totp_secret")}

        print("\n--- lectures métier légitimes ---")
        r = D.executer(CHEMIN, "SELECT ref, metrage FROM ordres_fabrication WHERE id = 12")
        ok("un SELECT simple passe", r["lignes"], [["OF-12", 1200.0]])
        ok("les noms de colonnes sont rendus", r["colonnes"], ["ref", "metrage"])

        r = D.executer(CHEMIN, """
            SELECT o.ref, count(op.id) AS nb, sum(op.duree_min) AS total
            FROM ordres_fabrication o JOIN operations op ON op.of_id = o.id
            WHERE o.statut = 'en_cours' GROUP BY o.ref ORDER BY total DESC LIMIT 3
        """)
        ok("jointure + agrégat + GROUP BY + ORDER BY", r["nb_lignes"], 3)

        r = D.executer(CHEMIN, """
            WITH lents AS (SELECT of_id, duree_min FROM operations WHERE duree_min > 300)
            SELECT count(*) FROM lents
        """)
        ok("les CTE passent", r["lignes"][0][0] > 0, True)

        r = D.executer(CHEMIN, "SELECT ref FROM ordres_fabrication WHERE ref LIKE 'OF-1%'")
        ok("LIKE fonctionne (fonction en liste blanche)", r["nb_lignes"] > 0, True)

        r = D.executer(CHEMIN, "SELECT ref FROM ordres_fabrication WHERE id = ?", (7,))
        ok("les paramètres liés fonctionnent", r["lignes"], [["OF-7"]])

        print("\n--- tables hors liste blanche ---")
        refuse("SELECT sur la paie", "SELECT * FROM paie", "table paie")
        refuse("la paie via une jointure",
               "SELECT o.ref FROM ordres_fabrication o, paie p", "table paie")
        refuse("la paie via une sous-requête",
               "SELECT ref FROM ordres_fabrication WHERE id IN (SELECT id FROM paie)", "table paie")
        refuse("la paie via une CTE",
               "WITH p AS (SELECT * FROM paie) SELECT * FROM p", "table paie")
        refuse("la paie via une vue qui la traverse",
               "SELECT * FROM vue_paie", "table paie")
        refuse("le schema ne s'enumere pas",
               "SELECT name FROM sqlite_master", "table sqlite_master")

        print("\n--- colonnes masquées ---")
        r = D.executer(CHEMIN, "SELECT email, role, mot_de_passe_hash, totp_secret FROM utilisateurs")
        ok("la table reste lisible", r["lignes"][0][0], "eleconte@sifa.pro")
        ok("le hash revient NULL", r["lignes"][0][2], None)
        ok("le secret TOTP revient NULL", r["lignes"][0][3], None)

        r = D.executer(CHEMIN, "SELECT substr(mot_de_passe_hash,1,4) FROM utilisateurs")
        ok("substr() ne reconstitue rien", r["lignes"][0][0], None)
        r = D.executer(CHEMIN, "SELECT length(totp_secret) FROM utilisateurs")
        ok("length() ne fuit pas la taille", r["lignes"][0][0], None)
        r = D.executer(CHEMIN, "SELECT group_concat(mot_de_passe_hash) FROM utilisateurs")
        ok("group_concat() ne recolle rien", r["lignes"][0][0], None)
        r = D.executer(CHEMIN, "SELECT count(*) FROM utilisateurs WHERE totp_secret LIKE 'JBS%'")
        ok("un filtre LIKE ne devine pas le secret", r["lignes"][0][0], 0)
        r = D.executer(CHEMIN, "SELECT count(*) FROM utilisateurs WHERE mot_de_passe_hash IS NOT NULL")
        ok("IS NOT NULL ne confirme rien", r["lignes"][0][0], 0)

        print("\n--- écritures et commandes hors lecture ---")
        for libelle, sql in [
            ("UPDATE", "UPDATE ordres_fabrication SET metrage = 0"),
            ("DELETE", "DELETE FROM ordres_fabrication"),
            ("INSERT", "INSERT INTO ordres_fabrication VALUES (9,'x',1,'y',1)"),
            ("DROP", "DROP TABLE ordres_fabrication"),
            ("CREATE", "CREATE TABLE evasion (x INTEGER)"),
            ("ATTACH", "ATTACH DATABASE '/tmp/ailleurs.db' AS a"),
            ("PRAGMA", "PRAGMA table_info(paie)"),
        ]:
            refuse(libelle + " est refusé", sql)
        # pragma_table_info() est une fonction table : elle contourne la forme
        # `PRAGMA x` et doit tomber sur le meme refus, avec un motif nommé.
        # Pas de motif attendu ici : SQLite refuse cette forme sur une écriture
        # interne du schéma, dont le libellé exact dépend de sa version. Ce qui
        # compte est que la porte soit fermée, pas le mot employé.
        refuse("PRAGMA déguisé en fonction table",
               "SELECT name FROM pragma_table_info('paie')")

        print("\n--- fonctions et instructions multiples ---")
        refuse("une fonction hors liste (hex)", "SELECT hex(ref) FROM ordres_fabrication", "hex")
        refuse("deux instructions dans un seul appel",
               "SELECT 1 FROM ordres_fabrication; DROP TABLE gros")

        print("\n--- garde-fous de volume ---")
        r = D.executer(CHEMIN, "SELECT id FROM ordres_fabrication", lignes_max=50)
        ok("le plafond de lignes s'applique", r["nb_lignes"], 50)
        ok("et la troncature est signalée", r["tronque"], True)
        r = D.executer(CHEMIN, "SELECT id FROM ordres_fabrication WHERE id < 4")
        ok("une petite réponse n'est pas dite tronquée", r["tronque"], False)

        # 4000 x 4000 x 4000 lignes : sans garde-fou, le processus part pour
        # des heures. Le compteur d'opérations doit l'avorter.
        refuse("une jointure cartésienne est avortée",
               "SELECT count(*) FROM gros a, gros b, gros c")

        print("\n--- la base n'a pas bougé ---")
        con = sqlite3.connect(CHEMIN)
        ok("les OF sont toujours là", con.execute("SELECT count(*) FROM ordres_fabrication").fetchone()[0], 300)
        ok("aucune table n'a été créée",
           con.execute("SELECT count(*) FROM sqlite_master WHERE name='evasion'").fetchone()[0], 0)
        ok("les métrages sont intacts",
           con.execute("SELECT metrage FROM ordres_fabrication WHERE id=12").fetchone()[0], 1200.0)
        con.close()

    print("\n" + ("TOUT EST VERT" if _ok else "DES VERIFICATIONS ONT ECHOUE"))
    return 0 if _ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""
Applique la migration paie historique (janv–mars 2026) sur la base de production.

Usage (depuis la racine du repo, sur le VPS) :
    python3 scripts/run_paie_migration.py

Idempotent : les INSERT utilisent OR IGNORE, relancer est sans danger.
"""
import os
import sqlite3
import sys

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH   = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "data", "production.db"))
SQL_PATH  = os.path.join(BASE_DIR, "scripts", "paie_migration.sql")


def main():
    if not os.path.exists(DB_PATH):
        print(f"[erreur] Base introuvable : {DB_PATH}")
        sys.exit(1)

    with open(SQL_PATH, "r", encoding="utf-8") as f:
        sql = f.read()

    print(f"DB   : {DB_PATH}")
    print(f"SQL  : {SQL_PATH}")
    print("Exécution de la migration…")

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(sql)
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[erreur] {e}")
        sys.exit(1)
    finally:
        conn.close()

    # Rapport
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    emp_count = conn.execute("SELECT count(*) FROM paie_employes").fetchone()[0]
    var_count = conn.execute("SELECT count(*) FROM paie_variables").fetchone()[0]
    periods   = conn.execute(
        "SELECT annee, mois, count(*) n FROM paie_variables GROUP BY annee, mois ORDER BY mois"
    ).fetchall()
    conn.close()

    print(f"\n✓ Migration terminée")
    print(f"  paie_employes  : {emp_count} fiches")
    print(f"  paie_variables : {var_count} entrées")
    for p in periods:
        print(f"    {p['annee']}-{p['mois']:02d} : {p['n']} employés")


if __name__ == "__main__":
    main()

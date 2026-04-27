"""
Applique la migration paie historique (janv–mars 2026) sur la base de production.

Usage (depuis la racine du repo, sur le VPS) :
    python3 scripts/run_paie_migration.py

Idempotent : les INSERT utilisent OR IGNORE, relancer est sans danger.
"""
import os
import re
import sqlite3
import sys

BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH   = os.environ.get("DB_PATH", os.path.join(BASE_DIR, "data", "production.db"))
SQL_PATH  = os.path.join(BASE_DIR, "scripts", "paie_migration.sql")


def split_statements(sql: str) -> list[str]:
    """Split SQL file into individual statements, stripping comments/blank lines."""
    stmts = []
    for raw in sql.split(";"):
        # Strip inline and full-line SQL comments, then whitespace
        cleaned = re.sub(r"--[^\n]*", "", raw).strip()
        if cleaned:
            stmts.append(cleaned)
    return stmts


def main():
    if not os.path.exists(DB_PATH):
        print(f"[erreur] Base introuvable : {DB_PATH}")
        sys.exit(1)

    if not os.path.exists(SQL_PATH):
        print(f"[erreur] SQL introuvable : {SQL_PATH}")
        sys.exit(1)

    with open(SQL_PATH, "r", encoding="utf-8") as f:
        sql = f.read()

    stmts = split_statements(sql)
    print(f"DB   : {DB_PATH}")
    print(f"SQL  : {SQL_PATH} ({len(stmts)} statements)")

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = OFF")

    errors   = 0
    executed = 0
    try:
        conn.execute("BEGIN")
        for i, stmt in enumerate(stmts, 1):
            # Skip meta-statements already handled above
            upper = stmt.upper().lstrip()
            if upper.startswith("PRAGMA") or upper in ("BEGIN TRANSACTION", "COMMIT", "BEGIN"):
                continue
            try:
                conn.execute(stmt)
                executed += 1
            except sqlite3.IntegrityError:
                pass   # OR IGNORE — expected for idempotent re-runs
            except Exception as e:
                print(f"  [erreur stmt {i}] {e}")
                print(f"    → {stmt[:120]}")
                errors += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"[erreur fatale] {e}")
        conn.close()
        sys.exit(1)

    conn.execute("PRAGMA foreign_keys = ON")
    conn.close()

    if errors:
        print(f"\n[!] {errors} erreur(s) rencontrée(s) — données partiellement importées")
    else:
        print(f"\n✓ {executed} statements exécutés sans erreur")

    # Rapport
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        emp_count = conn.execute("SELECT count(*) FROM paie_employes").fetchone()[0]
        var_count = conn.execute("SELECT count(*) FROM paie_variables").fetchone()[0]
        periods   = conn.execute(
            "SELECT annee, mois, count(*) n FROM paie_variables GROUP BY annee, mois ORDER BY mois"
        ).fetchall()
        print(f"\n  paie_employes  : {emp_count} fiches")
        print(f"  paie_variables : {var_count} entrées")
        for p in periods:
            print(f"    {p['annee']}-{p['mois']:02d} : {p['n']} employés")
    except Exception as e:
        print(f"[erreur lecture] {e}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

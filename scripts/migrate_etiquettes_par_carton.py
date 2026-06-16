"""MySifa - Script one-shot migration 114 : parametrage carton repiquage.

Applique sur la base les memes operations que la migration 114 du _migrate() :
- Ajoute la colonne planning_entries.etiquettes_par_carton (INTEGER NULL)
- Ajoute la colonne production_data.nb_cartons (INTEGER DEFAULT 0)
- Cree la table repiquage_carton_courant (etat carton en cours par dossier+operateur)

Idempotent : enregistre la migration version=114 dans schema_migrations.
Une seconde execution ne refait rien.

Utilisation sur le VPS (v1 ou prod) :
    cd /home/sifa/production-saas-v1   # ou /home/sifa/production-saas pour prod
    python3 scripts/migrate_etiquettes_par_carton.py

Note : v1 et v2 partagent la meme base de donnees, donc une seule execution
suffit. Une fois jouee, la migration officielle dans _migrate() (version 114)
detectera la trace et ne refera rien lors de la promotion v2.
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Resolution du chemin DB via config.py (source de verite)
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import DB_PATH  # noqa: E402


def main() -> int:
    print(f"DB : {DB_PATH}")
    if not Path(DB_PATH).exists():
        print("ERREUR : fichier DB introuvable", file=sys.stderr)
        return 1

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        # Garantir l'existence de la table schema_migrations
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "  version INTEGER PRIMARY KEY,"
            "  name TEXT NOT NULL,"
            "  applied_at TEXT NOT NULL)"
        )

        deja = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version=114 LIMIT 1"
        ).fetchone()
        if deja:
            print("Migration 114 deja appliquee, rien a faire.")
            return 0

        # 1) planning_entries.etiquettes_par_carton
        pe_cols = {r[1] for r in conn.execute(
            "PRAGMA table_info(planning_entries)"
        ).fetchall()}
        if "etiquettes_par_carton" not in pe_cols:
            conn.execute(
                "ALTER TABLE planning_entries "
                "ADD COLUMN etiquettes_par_carton INTEGER"
            )
            print("  + colonne planning_entries.etiquettes_par_carton")
        else:
            print("  = colonne planning_entries.etiquettes_par_carton deja presente")

        # 2) production_data.nb_cartons
        pd_cols = {r[1] for r in conn.execute(
            "PRAGMA table_info(production_data)"
        ).fetchall()}
        if "nb_cartons" not in pd_cols:
            conn.execute(
                "ALTER TABLE production_data "
                "ADD COLUMN nb_cartons INTEGER DEFAULT 0"
            )
            print("  + colonne production_data.nb_cartons")
        else:
            print("  = colonne production_data.nb_cartons deja presente")

        # 3) table repiquage_carton_courant
        conn.execute(
            "CREATE TABLE IF NOT EXISTS repiquage_carton_courant ("
            "  id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "  no_dossier TEXT NOT NULL,"
            "  operateur TEXT NOT NULL,"
            "  nb_etiquettes INTEGER NOT NULL DEFAULT 0,"
            "  updated_at TEXT NOT NULL,"
            "  UNIQUE(no_dossier, operateur))"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rcc_dossier "
            "ON repiquage_carton_courant(no_dossier)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rcc_operateur "
            "ON repiquage_carton_courant(operateur)"
        )
        print("  + table repiquage_carton_courant (avec index)")

        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations "
            "(version, name, applied_at) VALUES (?, ?, ?)",
            (
                114,
                "repiquage_carton_parametrage_compteur",
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        print("Migration 114 enregistree. OK.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

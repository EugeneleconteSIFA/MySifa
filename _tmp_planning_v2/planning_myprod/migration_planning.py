"""
SIFA — Migration Planning v1.1 (standalone)
=============================================
Le planning est autonome : les infos dossier (référence, client, description)
sont stockées directement dans planning_entries, pas de lien vers la table dossiers.

Exécuter une seule fois :
    python migration_planning.py
"""

import sqlite3
import sys
from pathlib import Path

# Racine du dépôt MySifa (…/_tmp_planning_v2/planning_myprod → 2 niveaux au-dessus)
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from config import DB_PATH  # noqa: E402

MIGRATION_SQL = """
-- ═══════════════════════════════════════════════════════════════
-- TABLE : machines
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS machines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT UNIQUE NOT NULL,
    code TEXT UNIQUE NOT NULL,
    horaires_lundi TEXT DEFAULT '5,21',
    horaires_mardi TEXT DEFAULT '5,21',
    horaires_mercredi TEXT DEFAULT '5,21',
    horaires_jeudi TEXT DEFAULT '5,21',
    horaires_vendredi TEXT DEFAULT '6,20',
    horaires_samedi TEXT DEFAULT '6,18',
    actif INTEGER DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- ═══════════════════════════════════════════════════════════════
-- TABLE : planning_entries (standalone — pas de FK vers dossiers)
-- Toutes les infos du dossier sont saisies manuellement
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS planning_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id INTEGER NOT NULL,
    position INTEGER NOT NULL,
    reference TEXT NOT NULL,
    client TEXT DEFAULT '',
    description TEXT DEFAULT '',
    format_l REAL,
    format_h REAL,
    duree_heures REAL NOT NULL DEFAULT 8,
    statut TEXT NOT NULL DEFAULT 'attente',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (machine_id) REFERENCES machines(id)
);

-- ═══════════════════════════════════════════════════════════════
-- TABLE : planning_config (samedi travaillé par semaine)
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS planning_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id INTEGER NOT NULL,
    semaine TEXT NOT NULL,
    samedi_travaille INTEGER DEFAULT 0,
    notes TEXT DEFAULT '',
    FOREIGN KEY (machine_id) REFERENCES machines(id),
    UNIQUE(machine_id, semaine)
);

CREATE INDEX IF NOT EXISTS idx_pe_machine ON planning_entries(machine_id, position);
CREATE INDEX IF NOT EXISTS idx_pc_lookup ON planning_config(machine_id, semaine);

-- Machine initiale
INSERT OR IGNORE INTO machines (nom, code) VALUES ('Cohésion 1', 'C1');
"""


def run_migration():
    print(f"Migration planning → {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(MIGRATION_SQL)
    conn.commit()
    conn.close()
    print("OK — tables machines, planning_entries, planning_config créées.")
    print("Machine 'Cohésion 1' (C1) insérée.")


if __name__ == "__main__":
    run_migration()

"""
SIFA — Migration Planning v1.1 (standalone)
=============================================
Le planning est autonome : les infos dossier (référence, client, description)
sont stockées directement dans planning_entries, pas de lien vers la table dossiers.

Exécuter une seule fois :
    python migration_planning.py
"""

import sqlite3
import os

# ⚠️ Adapter le chemin si besoin (même chemin que dans ton database.py)
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "production.db")
# Si ta base est à la racine : DB_PATH = "production.db"

MIGRATION_SQL = """
-- ═══════════════════════════════════════════════════════════════
-- TABLE : machines
-- Liste des machines de production
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS machines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT UNIQUE NOT NULL,           -- ex: "Cohésio 1", "Cohésio 2"
    code TEXT UNIQUE NOT NULL,          -- ex: "C1", "C2"
    horaires_lundi TEXT DEFAULT '5,21',
    horaires_mardi TEXT DEFAULT '5,21',
    horaires_mercredi TEXT DEFAULT '5,21',
    horaires_jeudi TEXT DEFAULT '5,21',
    horaires_vendredi TEXT DEFAULT '6,20',
    horaires_samedi TEXT DEFAULT '6,18', -- utilisé seulement si samedi_travaille=1
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
    position INTEGER NOT NULL,              -- ordre dans la file (1 = premier)
    reference TEXT NOT NULL,
    client TEXT DEFAULT '',
    description TEXT DEFAULT '',
    format_l REAL,                          -- largeur étiquette en mm
    format_h REAL,                          -- hauteur étiquette en mm
    duree_heures REAL NOT NULL DEFAULT 8,   -- durée estimée (2 à 30h)
    statut TEXT NOT NULL DEFAULT 'attente', -- attente | en_cours | termine
    notes TEXT DEFAULT '',
    planned_start TEXT,
    planned_end TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (machine_id) REFERENCES machines(id)
);

-- ═══════════════════════════════════════════════════════════════
-- TABLE : planning_config
-- Config par machine par semaine (ex: samedi travaillé)
-- ═══════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS planning_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id INTEGER NOT NULL,
    semaine TEXT NOT NULL,                  -- format "2026-W14"
    samedi_travaille INTEGER DEFAULT 0,
    notes TEXT,
    FOREIGN KEY (machine_id) REFERENCES machines(id),
    UNIQUE(machine_id, semaine)
);

-- Index pour les requêtes fréquentes
CREATE INDEX IF NOT EXISTS idx_pe_machine ON planning_entries(machine_id, position);
CREATE INDEX IF NOT EXISTS idx_pc_lookup ON planning_config(machine_id, semaine);

CREATE TABLE IF NOT EXISTS planning_day_worked (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    machine_id INTEGER NOT NULL,
    date TEXT NOT NULL,
    is_worked INTEGER NOT NULL DEFAULT 0,
    UNIQUE(machine_id, date),
    FOREIGN KEY (machine_id) REFERENCES machines(id)
);
CREATE INDEX IF NOT EXISTS idx_pdw_lookup ON planning_day_worked(machine_id, date);

-- ═══════════════════════════════════════════════════════════════
-- Insertion machine initiale : Cohésio 1
-- ═══════════════════════════════════════════════════════════════
INSERT OR IGNORE INTO machines (nom, code) VALUES ('Cohésio 1', 'C1');
"""


def run_migration():
    print(f"Migration planning → {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(MIGRATION_SQL)
    conn.commit()
    conn.close()
    print("OK — tables machines, planning_entries, planning_config créées.")
    print("Machine 'Cohésio 1' (C1) insérée.")


if __name__ == "__main__":
    run_migration()


"""
SIFA — Database & helpers v0.5
Ajouts : colonnes traçabilité, détection doublons à l'import
"""
import sqlite3
import pandas as pd
import io
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Optional
from datetime import datetime
from contextlib import contextmanager
import threading
from config import DB_PATH, UPLOAD_DIR, ROLE_SUPERADMIN, SUPERADMIN_EMAIL, classify_operation
from app.services.emplacements_plan import reload_emplacements_plan, sync_emplacements_plan_to_db

# Baselinage des migrations SQL déjà regroupées dans _migrate (historique).
SCHEMA_MIGRATION_VERSION_BASELINE = 1


def _ensure_schema_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )"""
    )


def _record_schema_migration(conn: sqlite3.Connection, version: int, name: str) -> None:
    _ensure_schema_migrations_table(conn)
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations (version, name, applied_at) VALUES (?,?,?)",
        (version, name, datetime.now().isoformat()),
    )


_schema_migrate_lock = threading.Lock()
_schema_migrate_done = False


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Applique les migrations manquantes (idempotent, une fois par process)."""
    global _schema_migrate_done
    if _schema_migrate_done:
        return
    with _schema_migrate_lock:
        if _schema_migrate_done:
            return
        _migrate(conn)
        conn.commit()
        _schema_migrate_done = True


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                nom TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'employe',
                operateur_lie TEXT,
                actif INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                last_login TEXT
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE TABLE IF NOT EXISTS imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                row_count INTEGER DEFAULT 0,
                columns TEXT,
                status TEXT DEFAULT 'ok',
                file_path TEXT
            );
            CREATE TABLE IF NOT EXISTS production_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                import_id INTEGER,
                operateur TEXT,
                date_operation TEXT,
                operation TEXT,
                operation_code TEXT,
                operation_severity TEXT,
                operation_category TEXT,
                service TEXT,
                machine TEXT,
                no_dossier TEXT,
                client TEXT,
                designation TEXT,
                quantite_a_traiter REAL DEFAULT 0,
                quantite_traitee REAL DEFAULT 0,
                no_cde TEXT,
                date_exp TEXT,
                date_liv TEXT,
                type_dossier TEXT,
                data JSON NOT NULL,
                est_manuel INTEGER DEFAULT 0,
                modifie_par TEXT,
                modifie_le TEXT,
                modifie_note TEXT,
                FOREIGN KEY (import_id) REFERENCES imports(id)
            );
            CREATE TABLE IF NOT EXISTS dossiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT UNIQUE NOT NULL,
                client TEXT,
                description TEXT,
                devis_montant REAL,
                statut TEXT DEFAULT 'devis',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS devis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                client TEXT,
                date_devis TEXT,
                format_h REAL,
                format_v REAL,
                laize REAL,
                nb_couleurs INTEGER DEFAULT 0,
                temps_calage_mn REAL DEFAULT 0,
                metrage_calage_ml REAL DEFAULT 0,
                temps_production_mn REAL DEFAULT 0,
                metrage_production_ml REAL DEFAULT 0,
                vitesse_theorique REAL DEFAULT 0,
                qte_etiquettes REAL DEFAULT 0,
                gache REAL DEFAULT 0,
                statut TEXT DEFAULT 'en_attente',
                note TEXT,
                imported_at TEXT NOT NULL,
                imported_by TEXT
            );
            CREATE TABLE IF NOT EXISTS devis_dossiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                devis_id INTEGER NOT NULL,
                no_dossier TEXT NOT NULL,
                FOREIGN KEY (devis_id) REFERENCES devis(id)
            );
            CREATE INDEX IF NOT EXISTS idx_prod_operateur ON production_data(operateur);
            CREATE INDEX IF NOT EXISTS idx_prod_dossier   ON production_data(no_dossier);
            CREATE INDEX IF NOT EXISTS idx_prod_date      ON production_data(date_operation);
            CREATE INDEX IF NOT EXISTS idx_prod_severity  ON production_data(operation_severity);
            CREATE INDEX IF NOT EXISTS idx_prod_code      ON production_data(operation_code);
            CREATE INDEX IF NOT EXISTS idx_prod_import    ON production_data(import_id);
            CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
        """)
        _migrate(conn)
        conn.commit()
        global _schema_migrate_done
        _schema_migrate_done = True


def sync_emplacements_plan_from_csv(csv_path: Optional[Path] = None) -> int:
    """Recharge la table emplacements_plan depuis data/emplacements_plan.csv (voir services/emplacements_plan.py)."""
    return sync_emplacements_plan_to_db(DB_PATH, csv_path)


def _migrate_emplacements_plan(conn):
    """Référentiel plan MyStock (recherche, suggestions)."""
    reload_emplacements_plan(conn)


def _migrate(conn):
    """Ajoute colonnes manquantes sur base existante sans tout recréer."""
    _ensure_schema_migrations_table(conn)
    existing_pd = {row[1] for row in conn.execute("PRAGMA table_info(production_data)").fetchall()}
    for col, sql in [
        ("est_manuel",    "ALTER TABLE production_data ADD COLUMN est_manuel INTEGER DEFAULT 0"),
        ("modifie_par",   "ALTER TABLE production_data ADD COLUMN modifie_par TEXT"),
        ("modifie_le",    "ALTER TABLE production_data ADD COLUMN modifie_le TEXT"),
        ("modifie_note",  "ALTER TABLE production_data ADD COLUMN modifie_note TEXT"),
        ("commentaire",   "ALTER TABLE production_data ADD COLUMN commentaire TEXT"),
        ("metrage_prevu",        "ALTER TABLE production_data ADD COLUMN metrage_prevu REAL"),
        ("metrage_reel",         "ALTER TABLE production_data ADD COLUMN metrage_reel REAL"),
        ("metrage_total_debut",  "ALTER TABLE production_data ADD COLUMN metrage_total_debut REAL"),
        ("metrage_total_fin",    "ALTER TABLE production_data ADD COLUMN metrage_total_fin REAL"),
    ]:
        if col not in existing_pd:
            conn.execute(sql)

    # Migration : recopie metrage_prevu → metrage_total_debut et metrage_reel → metrage_total_fin
    # pour les lignes fabrication déjà existantes (exécution idempotente grâce au WHERE IS NULL)
    conn.execute("""UPDATE production_data
                    SET metrage_total_debut = metrage_prevu
                    WHERE operation_code = '01'
                      AND metrage_prevu IS NOT NULL
                      AND metrage_total_debut IS NULL""")
    conn.execute("""UPDATE production_data
                    SET metrage_total_fin = metrage_reel
                    WHERE operation_code = '89'
                      AND metrage_reel IS NOT NULL
                      AND metrage_total_fin IS NULL""")

    # Index composites : accélèrent les filtres par opérateur/dossier + date
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prod_operateur_date ON production_data(operateur,date_operation)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prod_dossier_date   ON production_data(no_dossier,date_operation)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prod_code_date      ON production_data(operation_code,date_operation)")

    existing_imp = {row[1] for row in conn.execute("PRAGMA table_info(imports)").fetchall()}
    if "file_path" not in existing_imp:
        conn.execute("ALTER TABLE imports ADD COLUMN file_path TEXT")

    existing_users = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    for col, sql in [
        ("telephone", "ALTER TABLE users ADD COLUMN telephone TEXT"),
        ("machine_id", "ALTER TABLE users ADD COLUMN machine_id INTEGER"),
        ("access_overrides", "ALTER TABLE users ADD COLUMN access_overrides TEXT"),
        ("identifiant", "ALTER TABLE users ADD COLUMN identifiant TEXT"),
    ]:
        if col not in existing_users:
            conn.execute(sql)

    # Générer identifiant pour les comptes existants si absent.
    def _slug(s: str) -> str:
        s = unicodedata.normalize("NFD", str(s or ""))
        s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
        s = s.lower().strip()
        s = re.sub(r"[^a-z0-9]+", " ", s)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _compute_identifiant(nom: str) -> str:
        parts = _slug(nom).split(" ")
        parts = [p for p in parts if p]
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        # "premier mot du champ nom et prenom" → token1.token2
        return f"{parts[0]}.{parts[1]}"

    try:
        rows = conn.execute(
            "SELECT id, nom, identifiant FROM users"
        ).fetchall()
        used = set()
        for r in rows:
            ident = str(r["identifiant"] or "").strip().lower()
            if ident:
                used.add(ident)
        for r in rows:
            cur = str(r["identifiant"] or "").strip()
            if cur:
                continue
            base = _compute_identifiant(str(r["nom"] or ""))
            if not base:
                continue
            cand = base
            i = 2
            while cand in used:
                cand = f"{base}{i}"
                i += 1
            conn.execute("UPDATE users SET identifiant=? WHERE id=?", (cand, int(r["id"])))
            used.add(cand)
        # Index unique (ignore vides / null)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_identifiant ON users(identifiant) WHERE identifiant IS NOT NULL AND identifiant != ''"
        )
    except Exception:
        # Ne jamais bloquer le démarrage sur une migration d'identifiants.
        pass

    # Tables devis — créées si absentes
    existing_tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    if "devis" not in existing_tables:
        conn.execute("""CREATE TABLE devis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL, client TEXT, date_devis TEXT,
            format_h REAL, format_v REAL, laize REAL, nb_couleurs INTEGER DEFAULT 0,
            temps_calage_mn REAL DEFAULT 0, metrage_calage_ml REAL DEFAULT 0,
            temps_production_mn REAL DEFAULT 0, metrage_production_ml REAL DEFAULT 0,
            vitesse_theorique REAL DEFAULT 0, qte_etiquettes REAL DEFAULT 0,
            gache REAL DEFAULT 0, statut TEXT DEFAULT 'en_attente',
            note TEXT, imported_at TEXT NOT NULL, imported_by TEXT
        )""")
    if "devis_dossiers" not in existing_tables:
        conn.execute("""CREATE TABLE devis_dossiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            devis_id INTEGER NOT NULL, no_dossier TEXT NOT NULL,
            FOREIGN KEY (devis_id) REFERENCES devis(id)
        )""")

    # Tables planning — créées si absentes
    existing_tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    if "machines" not in existing_tables:
        conn.execute("""CREATE TABLE machines (
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
        )""")
        conn.execute("INSERT OR IGNORE INTO machines (nom, code) VALUES ('Cohésio 1', 'C1')")

    # Machines par défaut (compat planning multi-machines)
    # Ne force pas les IDs : s'appuie sur nom/code uniques.
    for nom, code in [
        ("Cohésio 1", "C1"),
        ("Cohésio 2", "C2"),
        ("DSI", "DSI"),
        ("Repiquage", "REP"),
    ]:
        conn.execute("INSERT OR IGNORE INTO machines (nom, code) VALUES (?, ?)", (nom, code))

    if "planning_entries" not in existing_tables:
        conn.execute("""CREATE TABLE planning_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER NOT NULL,
            position INTEGER NOT NULL,
            reference TEXT NOT NULL,
            client TEXT DEFAULT '',
            description TEXT DEFAULT '',
            format_l REAL,
            format_h REAL,
            dos_rvgi TEXT,
            duree_heures REAL NOT NULL DEFAULT 8,
            statut TEXT NOT NULL DEFAULT 'attente',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (machine_id) REFERENCES machines(id)
        )""")

    if "planning_config" not in existing_tables:
        conn.execute("""CREATE TABLE planning_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER NOT NULL,
            semaine TEXT NOT NULL,
            samedi_travaille INTEGER DEFAULT 0,
            notes TEXT DEFAULT '',
            FOREIGN KEY (machine_id) REFERENCES machines(id),
            UNIQUE(machine_id, semaine)
        )""")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_planning_machine ON planning_entries(machine_id, position)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_planning_config_lookup ON planning_config(machine_id, semaine)")

    # Migration v1 -> v1.1 (standalone) : planning_entries stocke ref/client/description
    # Ne pas utiliser `existing_tables` ici : il est figé avant la création éventuelle de
    # planning_entries ; sinon la table est créée sans colonnes v1.2 et les ALTER ne s’exécutent jamais.
    if conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='planning_entries'"
    ).fetchone():
        pe_cols = {row[1] for row in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        if "dossier_id" in pe_cols:
            conn.execute("ALTER TABLE planning_entries RENAME TO planning_entries_old")
            conn.execute("""CREATE TABLE planning_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                reference TEXT NOT NULL,
                client TEXT DEFAULT '',
                description TEXT DEFAULT '',
                format_l REAL,
                format_h REAL,
                dos_rvgi TEXT,
                duree_heures REAL NOT NULL DEFAULT 8,
                statut TEXT NOT NULL DEFAULT 'attente',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (machine_id) REFERENCES machines(id)
            )""")

            # Best-effort : récupérer ref/client/description depuis dossiers si possible
            conn.execute("""
                INSERT INTO planning_entries
                    (id, machine_id, position, reference, client, description, format_l, format_h,
                     duree_heures, statut, notes, created_at, updated_at)
                SELECT
                    pe.id, pe.machine_id, pe.position,
                    COALESCE(d.reference, '') as reference,
                    COALESCE(d.client, '') as client,
                    COALESCE(d.description, '') as description,
                    pe.format_l, pe.format_h, pe.duree_heures, pe.statut, pe.notes, pe.created_at, pe.updated_at
                FROM planning_entries_old pe
                LEFT JOIN dossiers d ON d.id = pe.dossier_id
            """)
            conn.execute("DROP TABLE planning_entries_old")

        # Colonnes v1.2 (standalone enrichi)
        pe_cols = {row[1] for row in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        for col, sql in [
            ("dos_rvgi", "ALTER TABLE planning_entries ADD COLUMN dos_rvgi TEXT"),
            ("numero_of", "ALTER TABLE planning_entries ADD COLUMN numero_of TEXT"),
            ("ref_produit", "ALTER TABLE planning_entries ADD COLUMN ref_produit TEXT"),
            ("laize", "ALTER TABLE planning_entries ADD COLUMN laize REAL"),
            ("date_livraison", "ALTER TABLE planning_entries ADD COLUMN date_livraison TEXT"),
            ("commentaire", "ALTER TABLE planning_entries ADD COLUMN commentaire TEXT"),
            ("exigences_production", "ALTER TABLE planning_entries ADD COLUMN exigences_production TEXT"),
            ("planned_start", "ALTER TABLE planning_entries ADD COLUMN planned_start TEXT"),
            ("planned_end", "ALTER TABLE planning_entries ADD COLUMN planned_end TEXT"),
            ("statut_force", "ALTER TABLE planning_entries ADD COLUMN statut_force INTEGER DEFAULT 0"),
            # Rentabilité v2: groupement split + liaison devis/production
            ("group_id", "ALTER TABLE planning_entries ADD COLUMN group_id TEXT"),
            ("split_parent_id", "ALTER TABLE planning_entries ADD COLUMN split_parent_id INTEGER"),
            # Planning v2: flag "à placer au planning" (0=non, 1=oui — zébré dans liste+timeline)
            ("a_placer", "ALTER TABLE planning_entries ADD COLUMN a_placer INTEGER DEFAULT 0"),
            # Planning v2: destockage (todo/done — point gris dans le slot timeline)
            ("destockage", "ALTER TABLE planning_entries ADD COLUMN destockage TEXT DEFAULT 'todo'"),
            # Planning v3: statut réel issu de la saisie fabrication
            # reellement_en_attente | reellement_en_saisie | reellement_termine
            ("statut_reel", "ALTER TABLE planning_entries ADD COLUMN statut_reel TEXT DEFAULT 'reellement_en_attente'"),
            # Fin de créneau figée manuellement (resize timeline) — ne pas recalculer depuis la saisie prod
            ("planned_end_manual", "ALTER TABLE planning_entries ADD COLUMN planned_end_manual INTEGER DEFAULT 0"),
            # Traçabilité création/modification
            ("created_by", "ALTER TABLE planning_entries ADD COLUMN created_by TEXT"),
            ("updated_by", "ALTER TABLE planning_entries ADD COLUMN updated_by TEXT"),
        ]:
            if col not in pe_cols:
                conn.execute(sql)

        # Backfill group_id pour les entrées existantes (valeur stable et unique par ligne)
        try:
            conn.execute(
                "UPDATE planning_entries SET group_id=CAST(id AS TEXT) WHERE group_id IS NULL OR TRIM(group_id)=''"
            )
        except Exception:
            pass

        # Backfill statut_reel : les dossiers planning marqués "termine" sont réellement terminés
        try:
            conn.execute(
                """UPDATE planning_entries
                   SET statut_reel='reellement_termine'
                   WHERE statut='termine'
                     AND (statut_reel IS NULL OR statut_reel='reellement_en_attente')"""
            )
        except Exception:
            pass

    # Tables Rentabilité v2 (liens planning -> devis + no_dossier production)
    existing_tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    if "rent_links" not in existing_tables:
        conn.execute("""CREATE TABLE rent_links (
            planning_entry_id INTEGER PRIMARY KEY,
            devis_id INTEGER,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (planning_entry_id) REFERENCES planning_entries(id) ON DELETE CASCADE,
            FOREIGN KEY (devis_id) REFERENCES devis(id) ON DELETE SET NULL
        )""")
    if "rent_prod_links" not in existing_tables:
        conn.execute("""CREATE TABLE rent_prod_links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            planning_entry_id INTEGER NOT NULL,
            no_dossier TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (planning_entry_id) REFERENCES planning_entries(id) ON DELETE CASCADE,
            UNIQUE(planning_entry_id, no_dossier)
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rent_links_devis ON rent_links(devis_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_rent_prod_links_entry ON rent_prod_links(planning_entry_id)")

    # Jours fériés / jours off par machine (standalone planning)
    existing_tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    if "planning_holidays" not in existing_tables:
        conn.execute("""CREATE TABLE planning_holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER NOT NULL,
            date TEXT NOT NULL,              -- YYYY-MM-DD
            is_off INTEGER NOT NULL DEFAULT 1,
            label TEXT DEFAULT '',
            UNIQUE(machine_id, date),
            FOREIGN KEY (machine_id) REFERENCES machines(id)
        )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_planning_holidays_lookup ON planning_holidays(machine_id, date)")

    if "planning_day_worked" not in existing_tables:
        conn.execute("""CREATE TABLE planning_day_worked (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            is_worked INTEGER NOT NULL DEFAULT 0,
            UNIQUE(machine_id, date),
            FOREIGN KEY (machine_id) REFERENCES machines(id)
        )""")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pdw_lookup ON planning_day_worked(machine_id, date)"
    )

    if "planning_day_horaires" not in existing_tables:
        conn.execute("""CREATE TABLE planning_day_horaires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER NOT NULL,
            date TEXT NOT NULL,              -- YYYY-MM-DD
            heure_debut REAL NOT NULL,       -- fraction décimale (ex: 5.0 = 5h)
            heure_fin   REAL NOT NULL,       -- fraction décimale (ex: 13.0 = 13h)
            UNIQUE(machine_id, date),
            FOREIGN KEY (machine_id) REFERENCES machines(id)
        )""")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pdh_lookup ON planning_day_horaires(machine_id, date)"
    )

    if "planning_day_comments" not in existing_tables:
        conn.execute("""CREATE TABLE planning_day_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            comment TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(machine_id, date),
            FOREIGN KEY (machine_id) REFERENCES machines(id)
        )""")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pdc_lookup ON planning_day_comments(machine_id, date)"
    )

    # Tables MyStock
    existing_tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    if "produits" not in existing_tables:
        conn.execute("""CREATE TABLE produits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reference TEXT UNIQUE NOT NULL,
            designation TEXT NOT NULL,
            description TEXT,
            unite TEXT DEFAULT 'étiquette',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
    else:
        # Migration: anciens libellés vides/génériques → "étiquette"
        try:
            conn.execute(
                """UPDATE produits
                   SET unite='étiquette'
                   WHERE unite IS NULL
                      OR TRIM(COALESCE(unite,'')) = ''
                      OR LOWER(TRIM(unite)) IN ('unité','unite','unites','unités','u.','u')"""
            )
        except Exception:
            pass

    # Migration: unités obsolètes (forfait/mille/mille A4) → "étiquette"
    try:
        conn.execute(
            """UPDATE produits
               SET unite='étiquette', updated_at=datetime('now')
               WHERE LOWER(TRIM(COALESCE(unite,''))) IN ('forfait','mille','mille a4')"""
        )
    except Exception:
        pass

    # Migration: suppression du "s" final pour stocker les unités au singulier
    # (idempotent : après strip le mot ne se termine plus par "s")
    try:
        conn.execute(
            """UPDATE produits
               SET unite = SUBSTR(unite, 1, LENGTH(unite) - 1),
                   updated_at = datetime('now')
               WHERE LENGTH(TRIM(COALESCE(unite,''))) > 1
                 AND SUBSTR(TRIM(unite), -1) = 's'"""
        )
    except Exception:
        pass

    if "stock_emplacements" not in existing_tables:
        conn.execute("""CREATE TABLE stock_emplacements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produit_id INTEGER NOT NULL,
            emplacement TEXT NOT NULL,
            quantite REAL DEFAULT 0,
            updated_at TEXT NOT NULL,
            updated_by TEXT,
            FOREIGN KEY (produit_id) REFERENCES produits(id),
            UNIQUE(produit_id, emplacement)
        )""")

    if "mouvements_stock" not in existing_tables:
        conn.execute("""CREATE TABLE mouvements_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produit_id INTEGER NOT NULL,
            emplacement TEXT NOT NULL,
            type_mouvement TEXT NOT NULL,
            quantite REAL NOT NULL,
            quantite_avant REAL DEFAULT 0,
            quantite_apres REAL DEFAULT 0,
            note TEXT,
            created_at TEXT NOT NULL,
            created_by TEXT,
            FOREIGN KEY (produit_id) REFERENCES produits(id)
        )""")

    # MyStock v2 — lots FIFO + inventaires
    existing_tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}

    if "lots_stock" not in existing_tables:
        conn.execute("""CREATE TABLE lots_stock (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produit_id INTEGER NOT NULL,
            emplacement TEXT NOT NULL,
            quantite_initiale REAL NOT NULL,
            quantite_restante REAL DEFAULT 0,
            date_entree TEXT NOT NULL,
            note TEXT,
            created_by TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (produit_id) REFERENCES produits(id)
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lots_produit ON lots_stock(produit_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lots_empl ON lots_stock(emplacement)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_lots_date ON lots_stock(date_entree)")

        # Migration v2 : convertir stock_emplacements existants en lots
        rows = conn.execute(
            "SELECT produit_id, emplacement, quantite, updated_at, updated_by FROM stock_emplacements WHERE quantite > 0"
        ).fetchall()
        now = datetime.now().isoformat()
        for r in rows:
            conn.execute(
                """INSERT INTO lots_stock
                   (produit_id,emplacement,quantite_initiale,quantite_restante,date_entree,note,created_by,created_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (r["produit_id"], r["emplacement"], r["quantite"], r["quantite"],
                 r["updated_at"] or now, "Migration v2", r["updated_by"] or "system", now)
            )

    # Colonnes inventaire / commentaire sur stock_emplacements
    se_cols = {row[1] for row in conn.execute("PRAGMA table_info(stock_emplacements)").fetchall()}
    if "derniere_inventaire" not in se_cols:
        conn.execute("ALTER TABLE stock_emplacements ADD COLUMN derniere_inventaire TEXT")
    if "commentaire" not in se_cols:
        conn.execute("ALTER TABLE stock_emplacements ADD COLUMN commentaire TEXT")

    # Traçabilité mouvements MyStock : snapshot du nom (Nom Prénom) de l'auteur
    try:
        mvt_cols = {row[1] for row in conn.execute("PRAGMA table_info(mouvements_stock)").fetchall()}
        if "created_by_name" not in mvt_cols:
            conn.execute("ALTER TABLE mouvements_stock ADD COLUMN created_by_name TEXT")
        # Backfill (best-effort) : si created_by est un email connu, copier users.nom
        conn.execute(
            """UPDATE mouvements_stock
               SET created_by_name = (
                 SELECT u.nom FROM users u
                 WHERE LOWER(TRIM(COALESCE(u.email,''))) = LOWER(TRIM(COALESCE(mouvements_stock.created_by,'')))
                 LIMIT 1
               )
               WHERE (created_by_name IS NULL OR TRIM(COALESCE(created_by_name,'')) = '')
                 AND TRIM(COALESCE(created_by,'')) != ''"""
        )
    except Exception:
        pass

    # ── Messagerie interne (contact support → super admin) ───────────────
    existing_tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    if "messages" not in existing_tables:
        conn.execute(
            """CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_user_id INTEGER,
                from_email TEXT,
                from_name TEXT,
                to_email TEXT NOT NULL,
                subject TEXT,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                read_at TEXT,
                deleted INTEGER DEFAULT 0,
                FOREIGN KEY (from_user_id) REFERENCES users(id)
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_to_email ON messages(to_email)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_unread ON messages(to_email, read_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at)")

    # Tables MyCompta (Factor -> CW)
    existing_tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    if "compta_acheteurs" not in existing_tables:
        conn.execute("""CREATE TABLE compta_acheteurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_vendeur TEXT,
            identifiant TEXT NOT NULL,
            raison_sociale TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(code_vendeur, identifiant)
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_compta_acheteurs_rs ON compta_acheteurs(raison_sociale)")

    if "compta_comptes" not in existing_tables:
        conn.execute("""CREATE TABLE compta_comptes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            libelle_condense TEXT NOT NULL,
            libelle_key TEXT NOT NULL UNIQUE,
            numero_compte TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_compta_comptes_key ON compta_comptes(libelle_key)")

    if "compta_banques" not in existing_tables:
        conn.execute("""CREATE TABLE compta_banques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_vendeur TEXT NOT NULL UNIQUE,
            numero_compte TEXT NOT NULL,
            libelle TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_compta_banques_code ON compta_banques(code_vendeur)"
        )

    _migrate_emplacements_plan(conn)

    try:
        conn.execute("UPDATE machines SET nom='Cohésio 1' WHERE nom='Cohésion 1'")
    except sqlite3.Error:
        pass

    # Migration : colonne dernier_metrage sur machines
    existing_machines = {row[1] for row in conn.execute("PRAGMA table_info(machines)").fetchall()}
    if "dernier_metrage" not in existing_machines:
        conn.execute("ALTER TABLE machines ADD COLUMN dernier_metrage REAL")

    # Tables réception matière (bobines)
    if "stock_receptions" not in existing_tables:
        conn.execute("""CREATE TABLE stock_receptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            created_by TEXT,
            created_by_name TEXT,
            note TEXT,
            nb_bobines INTEGER DEFAULT 0
        )""")
    if "stock_reception_items" not in existing_tables:
        conn.execute("""CREATE TABLE stock_reception_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reception_id INTEGER NOT NULL,
            code_barre TEXT NOT NULL,
            scanned_at TEXT NOT NULL,
            FOREIGN KEY (reception_id) REFERENCES stock_receptions(id)
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_recp_items ON stock_reception_items(reception_id)")

    # Traçabilité matières utilisées en fabrication
    if "fab_matieres_utilisees" not in existing_tables:
        conn.execute("""CREATE TABLE fab_matieres_utilisees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER,
            machine_nom TEXT,
            operateur TEXT,
            no_dossier TEXT,
            code_barre TEXT NOT NULL,
            scanned_at TEXT NOT NULL
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fab_mat_dossier ON fab_matieres_utilisees(no_dossier)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fab_mat_machine ON fab_matieres_utilisees(machine_id, scanned_at)")

    _ensure_schema_migrations_table(conn)
    # Migration v3 : ajout colonnes fournisseur / certificat_fsc sur stock_receptions
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=3 LIMIT 1").fetchone():
        existing_sr = {row[1] for row in conn.execute("PRAGMA table_info(stock_receptions)").fetchall()}
        if "fournisseur" not in existing_sr:
            conn.execute("ALTER TABLE stock_receptions ADD COLUMN fournisseur TEXT")
        if "certificat_fsc" not in existing_sr:
            conn.execute("ALTER TABLE stock_receptions ADD COLUMN certificat_fsc TEXT")
        _record_schema_migration(conn, 3, "add_fournisseur_certificat_fsc_to_receptions")

    # Table fournisseurs FSC
    if "fournisseurs_fsc" not in existing_tables:
        conn.execute("""CREATE TABLE fournisseurs_fsc (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL UNIQUE,
            licence TEXT,
            certificat TEXT
        )""")
        # Insérer les fournisseurs par défaut
        default_fournisseurs = [
            ('Avery', 'FSC-C004451', 'CU-COC-807907'),
            ('Fedrigoni', 'FSC-C011937', 'FCBA-COC-000059'),
            ('Feys', 'FSC-C017070', 'SGSCH-COC-004366'),
            ('Burgo / Mosaico', 'FSC-C004657', 'SGSCH-COC-002122'),
            ('Foucherf', 'FSC-C215283', 'BV-COC-215283'),
            ('Frimpeks UK', 'FSC-C160714', 'INT-COC-002144'),
            ('Frimpeks Italy', 'FSC-C164660', 'INT-COC-001611'),
            ('Frimpeks Turkey', 'FSC-C129558', 'NEO-COC-129558'),
            ('Grand Ouest', 'FSC-C148933', 'IMO-COC-209345'),
            ('Guyenne', 'FSC-C114338', 'FCBA-COC-000352'),
            ('Itasa', 'FSC-C160893', 'AEN-COC-000369'),
            ('Kanzan', 'FSC-C007179', 'TUVDC-COC-100605'),
            ('Lefrancq', 'FSC-C135176', 'FCBA-COC-000478'),
            ('Likexin', 'FSC-C128270', 'ESTS-COC-242264'),
            ('Mitsubishi', 'FSC-C014541', 'SGSCH-COC-002664'),
            ('Rheno', 'FSC-C104291', 'CU-COC-815304'),
            ('Ricoh', 'FSC-C001858', 'IMO-COC-261828'),
            ('Sato', 'FSC-C207483', 'TUEV-COC-002274'),
            ('Shine', 'FSC-C210420', 'ESTS-COC-241843'),
            ('Suzhou', 'FSC-C140235', 'RR-COC-000252'),
            ('Techmay', 'FSC-C199493', 'FCBA-COC-000616'),
            ('Torrespapel', 'FSC-C011032', 'SGSCH-COC-003753'),
            ('UPM', 'FSC-C012530', 'SGSCH-COC-004879'),
            ('Xinzhu', 'FSC-C177953', 'SGSHK-COC-331526'),
        ]
        conn.executemany(
            "INSERT INTO fournisseurs_fsc (nom, licence, certificat) VALUES (?,?,?)",
            default_fournisseurs,
        )

    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=2 LIMIT 1").fetchone():
        conn.execute(
            "UPDATE users SET role=? WHERE LOWER(TRIM(email))=?",
            (ROLE_SUPERADMIN, SUPERADMIN_EMAIL.strip().lower()),
        )
        _record_schema_migration(conn, 2, "superadmin_eleconte")

    # Migration v4 : Planning RH Personnel
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=4 LIMIT 1").fetchone():
        existing_tables_v4 = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        if "rh_planning_postes" not in existing_tables_v4:
            conn.execute("""CREATE TABLE rh_planning_postes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                semaine     TEXT NOT NULL,
                machine_id  INTEGER,
                poste       TEXT NOT NULL,
                creneau     TEXT NOT NULL DEFAULT 'journee',
                created_by  TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(user_id, semaine),
                FOREIGN KEY (user_id)    REFERENCES users(id),
                FOREIGN KEY (machine_id) REFERENCES machines(id)
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rh_planning_semaine ON rh_planning_postes(semaine)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rh_planning_user   ON rh_planning_postes(user_id)")

        if "rh_conges" not in existing_tables_v4:
            conn.execute("""CREATE TABLE rh_conges (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                date_debut  TEXT NOT NULL,
                date_fin    TEXT NOT NULL,
                nb_jours    REAL NOT NULL,
                type_conge  TEXT NOT NULL DEFAULT 'CP',
                note        TEXT,
                statut      TEXT NOT NULL DEFAULT 'pose',
                created_by  TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rh_conges_user ON rh_conges(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rh_conges_dates ON rh_conges(date_debut, date_fin)")

        if "rh_conges_soldes" not in existing_tables_v4:
            conn.execute("""CREATE TABLE rh_conges_soldes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                annee       INTEGER NOT NULL,
                quota_cp    REAL DEFAULT 25,
                quota_rtt   REAL DEFAULT 0,
                note        TEXT,
                updated_by  TEXT,
                updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(user_id, annee),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )""")

        # Compte Manuel Lesaffre (configurateur planning RH — rôle direction)
        import bcrypt as _bcrypt
        _pwd = _bcrypt.hashpw("Lesaffre2026!".encode(), _bcrypt.gensalt()).decode()
        _now = datetime.now().isoformat()
        conn.execute(
            """INSERT OR IGNORE INTO users (email, nom, password_hash, role, actif, created_at)
               VALUES ('mlesaffre@sifa.pro', 'Manuel Lesaffre', ?, 'direction', 1, ?)""",
            (_pwd, _now)
        )

        conn.commit()
        _record_schema_migration(conn, 4, "planning_rh_tables_and_lesaffre")

    # Migration v5 : Désaffecter tout le personnel planning RH (nettoyage avant déploiement)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=5 LIMIT 1").fetchone():
        conn.execute("DELETE FROM rh_planning_postes")
        conn.commit()
        _record_schema_migration(conn, 5, "clear_rh_planning_assignments")

    # Migration v6 : Configurer les overrides d'accès pour les utilisateurs spécifiques
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=6 LIMIT 1").fetchone():
        # S'assurer que la colonne access_overrides existe
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "access_overrides" not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN access_overrides TEXT")
            conn.commit()
        
        # Liste des utilisateurs avec leurs overrides d'accès
        access_overrides_config = [
            {"email": "mlesaffre@sifa.pro", "overrides": {"planning_rh": True}}
        ]
        
        for config in access_overrides_config:
            user_row = conn.execute(
                "SELECT id, access_overrides FROM users WHERE LOWER(TRIM(email)) = ?",
                (config["email"].lower().strip(),)
            ).fetchone()
            
            if user_row:
                user_id = user_row[0]
                overrides_raw = user_row[1]
                
                # Parser les overrides existants
                try:
                    overrides = json.loads(overrides_raw) if overrides_raw and overrides_raw.strip() else {}
                except (json.JSONDecodeError, TypeError):
                    overrides = {}
                
                # Fusionner avec les nouveaux overrides
                for key, value in config["overrides"].items():
                    overrides[key] = value
                
                # Mettre à jour
                conn.execute(
                    "UPDATE users SET access_overrides = ? WHERE id = ?",
                    (json.dumps(overrides), user_id)
                )
                conn.commit()
        
        _record_schema_migration(conn, 6, "configure_user_access_overrides")

    # Migration v7 : Tables Gestion des Paies
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=7 LIMIT 1").fetchone():
        existing_tables_v7 = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

        if "paie_employes" not in existing_tables_v7:
            conn.execute("""CREATE TABLE paie_employes (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER UNIQUE,
                matricule     TEXT,
                contrat_type  TEXT DEFAULT 'CDI',
                date_debut    TEXT,
                date_fin      TEXT,
                nb_heures_base  REAL,
                taux_horaire    REAL,
                salaire_mensuel REAL,
                prime_anciennete REAL,
                mutuelle       INTEGER DEFAULT 0,
                avantage_voiture REAL,
                updated_at    TEXT,
                updated_by    TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_paie_employes_user ON paie_employes(user_id)")

        if "paie_variables" not in existing_tables_v7:
            conn.execute("""CREATE TABLE paie_variables (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                annee      INTEGER NOT NULL,
                mois       INTEGER NOT NULL,
                data       TEXT NOT NULL DEFAULT '{}',
                updated_at TEXT NOT NULL,
                updated_by TEXT,
                UNIQUE(user_id, annee, mois),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )""")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_paie_variables_period ON paie_variables(annee, mois)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_paie_variables_user   ON paie_variables(user_id)")

        conn.commit()
        _record_schema_migration(conn, 7, "paie_employes_et_variables")

    # Migration v8 : Tables annonces de mise à jour + acquittements utilisateurs
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=8 LIMIT 1").fetchone():
        conn.execute("""CREATE TABLE IF NOT EXISTS update_announcements (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            scope       TEXT NOT NULL,        -- 'planning', 'fabrication', 'global'
            titre       TEXT NOT NULL,
            message     TEXT NOT NULL,        -- HTML autorisé
            created_at  TEXT NOT NULL,
            created_by  TEXT DEFAULT 'système',
            active      INTEGER DEFAULT 1    -- 0 = archivé (ne plus afficher)
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS update_acknowledgements (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            announcement_id INTEGER NOT NULL,
            user_id         INTEGER NOT NULL,
            user_nom        TEXT,
            acknowledged_at TEXT NOT NULL,
            UNIQUE(announcement_id, user_id),
            FOREIGN KEY (announcement_id) REFERENCES update_announcements(id)
        )""")

        # ── Seed : annonces du 30 avril 2026 ─────────────────────────────────
        _planning_msg = (
            "<p style='margin-bottom:14px'>Plusieurs améliorations ont été déployées ce matin sur le planning.</p>"
            "<ul style='margin:10px 0;padding-left:20px;line-height:1.9'>"
            "<li><strong>Lisibilité de la liste</strong> — Les dossiers terminés sont masqués par défaut, à l'exception des deux derniers. Un bouton permet de les afficher en totalité si nécessaire. La position de défilement est conservée après chaque modification ou réordonnancement.</li>"
            "<li><strong>Timeline</strong> — Les slots <em>En attente</em> sont déplaçables par glisser-déposer directement sur la barre de temps. Survoler un slot et appuyer sur <kbd style='background:rgba(255,255,255,.12);padding:1px 5px;border-radius:4px;font-family:monospace;font-size:11px'>Entrée</kbd> ouvre sa fiche d'édition.</li>"
            "<li><strong>Paramètres semaine</strong> — Une icône ⚙ est disponible sur chaque en-tête de semaine pour configurer les jours travaillés et les horaires spécifiques, indépendamment des défauts machine.</li>"
            "<li><strong>Durée réelle</strong> — À la clôture d'un dossier, sa durée plannée est mise à jour automatiquement d'après les horodatages réels de production. Les durées s'affichent au format <em>5h15</em>.</li>"
            "<li><strong>Statut saisie</strong> — La liste et la timeline indiquent si un dossier est en cours de saisie ou réellement terminé côté opérateur.</li>"
            "</ul>"
        )
        _fabrication_msg = (
            "<p style='margin-bottom:14px'>Deux changements importants sont en vigueur dès aujourd'hui.</p>"
            "<ul style='margin:10px 0;padding-left:20px;line-height:1.9'>"
            "<li><strong>Renommage</strong> — «&nbsp;Début dossier&nbsp;» et «&nbsp;Fin dossier&nbsp;» s'appellent désormais <strong>Début de production</strong> et <strong>Fin de production</strong>.</li>"
            "<li><strong>Clôture de dossier</strong> — Lors d'une fin de production, il est obligatoire d'indiquer si le dossier est terminé ou s'il reprend. Cette information alimente directement le planning&nbsp;: ne pas la renseigner correctement faussera la visibilité de l'équipe sur les encours.</li>"
            "<li><strong>Durée plannée mise à jour automatiquement</strong> — À la clôture d'un dossier, la durée dans le planning est recalculée d'après le temps réel de production.</li>"
            "</ul>"
        )

        _seed_ts = "2026-04-30T00:00:00"
        conn.execute(
            "INSERT INTO update_announcements (scope,titre,message,created_at,created_by,active) VALUES (?,?,?,?,?,1)",
            ("planning", "Mise à jour du 30 avril 2026 — Planning de production", _planning_msg, _seed_ts, "système"),
        )
        conn.execute(
            "INSERT INTO update_announcements (scope,titre,message,created_at,created_by,active) VALUES (?,?,?,?,?,1)",
            ("fabrication", "Mise à jour du 30 avril 2026 — Saisie de production", _fabrication_msg, _seed_ts, "système"),
        )

        conn.commit()
        _record_schema_migration(conn, 8, "update_announcements_tables")

    # Migration v9 : Correctifs planning — statut_reel corrompu + dates erronées
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=9 LIMIT 1").fetchone():
        # Bug 1 : SNV 9931304 marqué "en saisie" par erreur opérateur
        conn.execute(
            """UPDATE planning_entries
               SET statut_reel = 'reellement_en_attente', updated_at = datetime('now')
               WHERE reference = '9931304'
                 AND statut_reel = 'reellement_en_saisie'"""
        )
        # Bug 2 : Nestlé Marconnelle (Marché 722) — planned_start erroné 30/04 au lieu de 04/05
        conn.execute(
            """UPDATE planning_entries
               SET planned_start = '2026-05-04T07:00:00',
                   planned_end   = datetime('2026-05-04T07:00:00', '+' || CAST(duree_heures AS INTEGER) || ' hours'),
                   updated_at    = datetime('now')
               WHERE reference LIKE '%Marché 722%'
                 AND statut = 'en_cours'"""
        )
        conn.commit()
        _record_schema_migration(conn, 9, "fix_corrupted_statut_reel_and_dates")

    # Migration v10 : traçabilité code-barre fournisseur (photo + texte)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=10 LIMIT 1").fetchone():
        fsc_cols = {r["name"] for r in conn.execute("PRAGMA table_info(fournisseurs_fsc)").fetchall()}
        if "traca_photo_url" not in fsc_cols:
            conn.execute("ALTER TABLE fournisseurs_fsc ADD COLUMN traca_photo_url TEXT")
        if "traca_explication" not in fsc_cols:
            conn.execute("ALTER TABLE fournisseurs_fsc ADD COLUMN traca_explication TEXT")
        if "traca_exemple_code" not in fsc_cols:
            conn.execute("ALTER TABLE fournisseurs_fsc ADD COLUMN traca_exemple_code TEXT")
        conn.commit()
        _record_schema_migration(conn, 10, "add_traca_barcode_to_fournisseurs")

    # Migration v11 : MyDevis — paramètres matière & base prix
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=11 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS matiere_params (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categorie TEXT NOT NULL,
                code TEXT NOT NULL,
                designation TEXT NOT NULL,
                fournisseur TEXT,
                poids_m2 REAL,
                prix_eur_m2 REAL,
                prix_usd_kg REAL,
                taux_change REAL DEFAULT 1.0,
                incidence_dollar REAL DEFAULT 1.0,
                transport_total REAL DEFAULT 0,
                appellation TEXT,
                grammage INTEGER,
                notes TEXT,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS matiere_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ref_interne INTEGER,
                designation TEXT NOT NULL,
                frontal TEXT,
                type_adhesion TEXT,
                adhesif TEXT,
                silicone TEXT,
                glassine TEXT,
                marqueur TEXT,
                prix_cohesio REAL,
                prix_rotoflex REAL,
                updated_at TEXT
            );
            CREATE TABLE IF NOT EXISTS matiere_config (
                cle TEXT PRIMARY KEY,
                valeur TEXT NOT NULL,
                updated_at TEXT
            );
            """
        )
        conn.execute(
            "INSERT OR IGNORE INTO matiere_config (cle, valeur, updated_at) VALUES ('marge_erreur', '5', datetime('now'))"
        )
        conn.execute(
            "INSERT OR IGNORE INTO matiere_config (cle, valeur, updated_at) VALUES ('taux_change_usd', '0.85', datetime('now'))"
        )
        conn.commit()
        _record_schema_migration(conn, 11, "matiere_params_base_config")

    # v12 — jours travaillés par affectation RH (bitmask Lun=bit0…Ven=bit4, Sam=bit5 ; 31=lun–ven, 32=sam)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=12 LIMIT 1").fetchone():
        try:
            conn.execute(
                "ALTER TABLE rh_planning_postes ADD COLUMN jours INTEGER NOT NULL DEFAULT 31"
            )
        except Exception:
            pass  # colonne déjà présente
        conn.commit()
        _record_schema_migration(conn, 12, "rh_planning_postes_jours")

    # v13 — MyExpé : suivi des départs (exportations)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=13 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS expe_departs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_enlevement TEXT NOT NULL,
                affreteurs TEXT,
                transporteur TEXT,
                client TEXT,
                code_postal_destination TEXT,
                ref_sifa TEXT,
                arc TEXT,
                no_cde_transport TEXT,
                no_bl TEXT,
                nb_palette REAL,
                poids_total_kg REAL,
                date_livraison TEXT,
                statut TEXT NOT NULL DEFAULT 'en_attente',
                created_at TEXT NOT NULL,
                created_by_email TEXT,
                validated_at TEXT,
                validated_by_email TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_expe_departs_statut_date
                ON expe_departs(statut, date_enlevement);
            CREATE INDEX IF NOT EXISTS idx_expe_departs_validated
                ON expe_departs(validated_at);
            """
        )
        conn.commit()
        _record_schema_migration(conn, 13, "expe_departs_suivi")

    # v14 — ordre des tuiles portail (préférence utilisateur)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=14 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "portal_apps_order" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN portal_apps_order TEXT")
        conn.commit()
        _record_schema_migration(conn, 14, "users_portal_apps_order")

    # v15 — base matière : supplément Rotoflex par ligne (calcul prix depuis paramètres)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=15 LIMIT 1").fetchone():
        mb_cols = {r["name"] for r in conn.execute("PRAGMA table_info(matiere_base)").fetchall()}
        if "rotoflex_supplement_eur_m2" not in mb_cols:
            conn.execute(
                "ALTER TABLE matiere_base ADD COLUMN rotoflex_supplement_eur_m2 REAL"
            )
        conn.execute(
            """INSERT OR IGNORE INTO matiere_config (cle, valeur, updated_at)
               VALUES ('supplement_rotoflex_eur_m2', '0.06', datetime('now'))"""
        )
        conn.commit()
        _record_schema_migration(conn, 15, "matiere_base_rotoflex_supplement")

    # v16 — MyDevis : matiere_params.code nullable + base matière groupée par famille
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=16 LIMIT 1").fetchone():
        try:
            # Recréer la table sans la contrainte NOT NULL sur code
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS matiere_params_new (
                    id               INTEGER PRIMARY KEY AUTOINCREMENT,
                    categorie        TEXT NOT NULL DEFAULT '',
                    code             TEXT,
                    designation      TEXT NOT NULL,
                    fournisseur      TEXT,
                    poids_m2         REAL,
                    prix_eur_m2      REAL,
                    prix_usd_kg      REAL,
                    taux_change      REAL DEFAULT 1.0,
                    incidence_dollar REAL DEFAULT 1.0,
                    transport_total  REAL DEFAULT 0,
                    appellation      TEXT,
                    grammage         INTEGER,
                    notes            TEXT,
                    updated_at       TEXT
                );
                INSERT INTO matiere_params_new SELECT * FROM matiere_params;
                DROP TABLE matiere_params;
                ALTER TABLE matiere_params_new RENAME TO matiere_params;
                """
            )
        except Exception:
            pass
        try:
            mb_cols = {r["name"] for r in conn.execute("PRAGMA table_info(matiere_base)").fetchall()}
            if "groupe" not in mb_cols:
                conn.execute("ALTER TABLE matiere_base ADD COLUMN groupe TEXT")
        except Exception:
            pass
        conn.commit()
        _record_schema_migration(conn, 16, "matiere_params_code_nullable_and_matiere_base_groupe")

    # v17 — base matière : liens directs vers matiere_params (IDs composants)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=17 LIMIT 1").fetchone():
        try:
            mb_cols = {r["name"] for r in conn.execute("PRAGMA table_info(matiere_base)").fetchall()}
            for col, sql in [
                (
                    "param_id_frontal",
                    "ALTER TABLE matiere_base ADD COLUMN param_id_frontal INTEGER REFERENCES matiere_params(id)",
                ),
                (
                    "param_id_adhesif",
                    "ALTER TABLE matiere_base ADD COLUMN param_id_adhesif INTEGER REFERENCES matiere_params(id)",
                ),
                (
                    "param_id_silicone",
                    "ALTER TABLE matiere_base ADD COLUMN param_id_silicone INTEGER REFERENCES matiere_params(id)",
                ),
                (
                    "param_id_glassine",
                    "ALTER TABLE matiere_base ADD COLUMN param_id_glassine INTEGER REFERENCES matiere_params(id)",
                ),
            ]:
                if col not in mb_cols:
                    try:
                        conn.execute(sql)
                    except Exception:
                        pass
        except Exception:
            pass
        conn.commit()
        _record_schema_migration(conn, 17, "matiere_base_param_ids")

    # v18 — Traça fabrication : liaison scans matières ↔ réceptions (fournisseur + certificat)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=18 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(fab_matieres_utilisees)").fetchall()}
        if "reception_id" not in cols:
            conn.execute("ALTER TABLE fab_matieres_utilisees ADD COLUMN reception_id INTEGER")
        if "liaison_mode" not in cols:
            # 'reception' | 'manual'
            conn.execute("ALTER TABLE fab_matieres_utilisees ADD COLUMN liaison_mode TEXT")
        if "fournisseur_manual" not in cols:
            conn.execute("ALTER TABLE fab_matieres_utilisees ADD COLUMN fournisseur_manual TEXT")
        if "certificat_fsc_manual" not in cols:
            conn.execute("ALTER TABLE fab_matieres_utilisees ADD COLUMN certificat_fsc_manual TEXT")
        _record_schema_migration(conn, 18, "fab_traca_link_receptions")

    # v19 — Profil utilisateur : adresse + date de naissance
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=19 LIMIT 1").fetchone():
        ucols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "adresse" not in ucols:
            conn.execute("ALTER TABLE users ADD COLUMN adresse TEXT")
        if "date_naissance" not in ucols:
            # ISO YYYY-MM-DD
            conn.execute("ALTER TABLE users ADD COLUMN date_naissance TEXT")
        _record_schema_migration(conn, 19, "users_adresse_date_naissance")

    # v20 — Planning : commentaires par jour (timeline)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=20 LIMIT 1").fetchone():
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='planning_day_comments'"
        ).fetchone():
            conn.execute("""CREATE TABLE planning_day_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                comment TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(machine_id, date),
                FOREIGN KEY (machine_id) REFERENCES machines(id)
            )""")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pdc_lookup ON planning_day_comments(machine_id, date)"
        )
        _record_schema_migration(conn, 20, "planning_day_comments")

    # v21 — Planning : date de fin manuelle (override saisie production)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=21 LIMIT 1").fetchone():
        pe_cols = {r["name"] for r in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        if "planned_end_manual" not in pe_cols:
            conn.execute(
                "ALTER TABLE planning_entries ADD COLUMN planned_end_manual INTEGER DEFAULT 0"
            )
        _record_schema_migration(conn, 21, "planning_planned_end_manual")

    # v22 — Machines : horaires paire/impaire (JSON) pour la timeline Cohésio 2 et similaires
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=22 LIMIT 1").fetchone():
        mcols = {r["name"] for r in conn.execute("PRAGMA table_info(machines)").fetchall()}
        if "horaires_parity" not in mcols:
            conn.execute("ALTER TABLE machines ADD COLUMN horaires_parity TEXT")
        _record_schema_migration(conn, 22, "machines_horaires_parity")

    # v23 — Référentiel codes opération (ex operations.json)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=23 LIMIT 1").fetchone():
        if not conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='operation_codes'"
        ).fetchone():
            conn.execute(
                """CREATE TABLE operation_codes (
                    code TEXT PRIMARY KEY,
                    severity TEXT NOT NULL,
                    label TEXT NOT NULL,
                    category TEXT NOT NULL,
                    required INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )"""
            )
        try:
            from app.services.operations_config import (
                seed_operation_codes_if_empty,
                upsert_operation_codes_from_json,
            )

            seed_operation_codes_if_empty(conn)
            upsert_operation_codes_from_json(conn, ["12", "58", "69", "80", "81"])
        except Exception:
            pass
        _record_schema_migration(conn, 23, "operation_codes")

    # v24 — Préférences thème utilisateur (palette, style, mode)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=24 LIMIT 1").fetchone():
        ucols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "theme_prefs" not in ucols:
            conn.execute("ALTER TABLE users ADD COLUMN theme_prefs TEXT")
        _record_schema_migration(conn, 24, "users_theme_prefs")

    # v25 — Planning : exigences de production par dossier
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=25 LIMIT 1").fetchone():
        pe_cols = {r["name"] for r in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        if "exigences_production" not in pe_cols:
            conn.execute("ALTER TABLE planning_entries ADD COLUMN exigences_production TEXT")
        _record_schema_migration(conn, 25, "planning_exigences_production")

    # v26 — Jours fériés nationaux 2026 (planning + calendrier)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=26 LIMIT 1").fetchone():
        feries_2026 = [
            ("2026-01-01", "Jour de l'an"),
            ("2026-04-06", "Lundi de Pâques"),
            ("2026-05-01", "Fête du Travail"),
            ("2026-05-08", "Victoire des Alliés 1945"),
            ("2026-05-14", "Jeudi de l'Ascension"),
            ("2026-05-25", "Lundi de Pentecôte"),
            ("2026-07-14", "Fête Nationale"),
            ("2026-08-15", "Assomption"),
            ("2026-11-01", "La Toussaint"),
            ("2026-11-11", "Armistice 1918"),
            ("2026-12-25", "Noël"),
        ]
        conn.execute("DELETE FROM planning_holidays")
        machine_ids = [
            int(r[0])
            for r in conn.execute("SELECT id FROM machines ORDER BY id").fetchall()
        ]
        for machine_id in machine_ids:
            for date_str, label in feries_2026:
                conn.execute(
                    """INSERT INTO planning_holidays (machine_id, date, is_off, label)
                       VALUES (?, ?, 1, ?)""",
                    (machine_id, date_str, label),
                )
        _record_schema_migration(conn, 26, "feries_nationaux_2026")

    # v27 — Plusieurs affectations RH par personne et par semaine (jours partiels multi-postes)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=27 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE rh_planning_postes_v27 (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                semaine     TEXT NOT NULL,
                machine_id  INTEGER,
                poste       TEXT NOT NULL,
                creneau     TEXT NOT NULL DEFAULT 'journee',
                jours       INTEGER NOT NULL DEFAULT 31,
                created_by  TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_id)    REFERENCES users(id),
                FOREIGN KEY (machine_id) REFERENCES machines(id)
            );
            INSERT INTO rh_planning_postes_v27
                (id, user_id, semaine, machine_id, poste, creneau, jours, created_by, created_at)
            SELECT id, user_id, semaine, machine_id, poste, creneau,
                   COALESCE(jours, 31), created_by, created_at
            FROM rh_planning_postes;
            DROP TABLE rh_planning_postes;
            ALTER TABLE rh_planning_postes_v27 RENAME TO rh_planning_postes;
            CREATE INDEX IF NOT EXISTS idx_rh_planning_semaine ON rh_planning_postes(semaine);
            CREATE INDEX IF NOT EXISTS idx_rh_planning_user   ON rh_planning_postes(user_id);
            """
        )
        conn.commit()
        _record_schema_migration(conn, 27, "rh_planning_multi_affectations_semaine")

    # v28 — Événements calendrier personnel (MyCalendrier)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=28 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cal_events_perso (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                titre TEXT NOT NULL,
                date_debut TEXT NOT NULL,
                date_fin TEXT NOT NULL,
                all_day INTEGER DEFAULT 0,
                note TEXT,
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_cal_events_perso_user ON cal_events_perso(user_id);
            CREATE INDEX IF NOT EXISTS idx_cal_events_perso_debut ON cal_events_perso(date_debut);
            """
        )
        conn.commit()
        _record_schema_migration(conn, 28, "cal_events_perso")

    # v29 — Journal d'audit (actions sensibles)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=29 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS audit_logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER,
                user_nom    TEXT,
                user_role   TEXT,
                action      TEXT NOT NULL,
                module      TEXT NOT NULL,
                objet       TEXT,
                detail      TEXT,
                ip          TEXT,
                created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_audit_module ON audit_logs(module);
            """
        )
        conn.commit()
        _record_schema_migration(conn, 29, "audit_logs")

    # v31 — FSC : flag certification requise sur les dossiers planning
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=31 LIMIT 1").fetchone():
        pe_cols = {r["name"] for r in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        if "fsc_requis" not in pe_cols:
            conn.execute(
                "ALTER TABLE planning_entries ADD COLUMN fsc_requis INTEGER DEFAULT 0"
            )
        if "fsc_type_requis" not in pe_cols:
            conn.execute(
                "ALTER TABLE planning_entries ADD COLUMN fsc_type_requis TEXT DEFAULT ''"
            )
        conn.commit()
        _record_schema_migration(conn, 31, "planning_entries_fsc_requis")

    # v32 — FSC : type de claim sur les réceptions de bobines
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=32 LIMIT 1").fetchone():
        sr_cols = {r["name"] for r in conn.execute("PRAGMA table_info(stock_receptions)").fetchall()}
        if "fsc_type_claim" not in sr_cols:
            conn.execute(
                "ALTER TABLE stock_receptions ADD COLUMN fsc_type_claim TEXT DEFAULT 'non_fsc'"
            )
        conn.commit()
        _record_schema_migration(conn, 32, "stock_receptions_fsc_type_claim")

    # v33 — FSC : champs alerte sur fab_matieres_utilisees
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=33 LIMIT 1").fetchone():
        fmu_cols = {
            r["name"] for r in conn.execute("PRAGMA table_info(fab_matieres_utilisees)").fetchall()
        }
        if "fsc_warning" not in fmu_cols:
            conn.execute(
                "ALTER TABLE fab_matieres_utilisees ADD COLUMN fsc_warning INTEGER DEFAULT 0"
            )
        if "fsc_warning_note" not in fmu_cols:
            conn.execute(
                "ALTER TABLE fab_matieres_utilisees ADD COLUMN fsc_warning_note TEXT"
            )
        conn.commit()
        _record_schema_migration(conn, 33, "fab_matieres_fsc_warning")

    # v34 — Photo de profil utilisateur
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=34 LIMIT 1").fetchone():
        ucols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "avatar_url" not in ucols:
            conn.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
        conn.commit()
        _record_schema_migration(conn, 34, "users_avatar_url")

    # v35 — Chat interne (DMs + canaux d'équipe)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=35 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_channels (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                type         TEXT    NOT NULL DEFAULT 'channel',
                name         TEXT    DEFAULT NULL,
                description  TEXT    DEFAULT NULL,
                created_by   INTEGER REFERENCES users(id),
                created_at   TEXT    NOT NULL,
                archived_at  TEXT    DEFAULT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_members (
                channel_id   INTEGER NOT NULL REFERENCES chat_channels(id),
                user_id      INTEGER NOT NULL REFERENCES users(id),
                joined_at    TEXT    NOT NULL,
                last_read_at TEXT    DEFAULT NULL,
                PRIMARY KEY (channel_id, user_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id   INTEGER NOT NULL REFERENCES chat_channels(id),
                user_id      INTEGER NOT NULL REFERENCES users(id),
                user_nom     TEXT    NOT NULL,
                body         TEXT    NOT NULL,
                created_at   TEXT    NOT NULL,
                deleted_at   TEXT    DEFAULT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_chat_msg_chan
            ON chat_messages(channel_id, created_at)
        """)
        conn.commit()
        _record_schema_migration(conn, 35, "chat_channels_messages")

    # v36 — Pièces jointes messagerie
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=36 LIMIT 1").fetchone():
        for col, typedef in (
            ("attachment_url", "TEXT"),
            ("attachment_name", "TEXT"),
            ("attachment_mime", "TEXT"),
            ("attachment_size", "INTEGER"),
        ):
            if col not in {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()}:
                conn.execute(f"ALTER TABLE chat_messages ADD COLUMN {col} {typedef}")
        conn.commit()
        _record_schema_migration(conn, 36, "chat_messages_attachments")

    # v37 — Réactions emoji sur les messages chat
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=37 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_reactions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id  INTEGER NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
                user_id     INTEGER NOT NULL,
                user_nom    TEXT    NOT NULL DEFAULT '',
                emoji       TEXT    NOT NULL,
                created_at  TEXT    NOT NULL,
                UNIQUE(message_id, user_id, emoji)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reactions_msg ON chat_reactions(message_id)"
        )
        conn.commit()
        _record_schema_migration(conn, 37, "chat_reactions")

    # v38 — Retirer des fériés planning les jours off erronés (18–22 mai 2026) ; calendrier = liste nationale
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=38 LIMIT 1").fetchone():
        conn.execute(
            "DELETE FROM planning_holidays WHERE date >= '2026-05-18' AND date <= '2026-05-22'"
        )
        _record_schema_migration(conn, 38, "cleanup_feries_planning_mai_2026")

    # v39 — MyExpé : référentiel transporteurs
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=39 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS expe_transporteurs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                taxe_carburant_pct REAL DEFAULT 0,
                contact_nom TEXT,
                contact_email TEXT,
                contact_tel TEXT,
                zone_france INTEGER DEFAULT 1,          -- 1 = oui
                zone_france_hors_paris INTEGER DEFAULT 0,
                zone_affretement INTEGER DEFAULT 0,     -- >6 palettes
                zone_messagerie INTEGER DEFAULT 0,      -- <6 palettes (ramasse)
                tarif_filename TEXT,                    -- nom du fichier uploadé
                tarif_url TEXT,                         -- chemin relatif de stockage
                actif INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_expe_transporteurs_actif
                ON expe_transporteurs(actif);
            """
        )
        conn.commit()
        _record_schema_migration(conn, 39, "expe_transporteurs")

    # v40 — Matières premières : référentiel
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=40 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS matieres_premieres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categorie TEXT NOT NULL CHECK(categorie IN ('mandrin','palette','adhesif','carton')),
                reference TEXT NOT NULL,
                designation TEXT NOT NULL,
                seuil_alerte REAL DEFAULT 0,
                actif INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                UNIQUE(categorie, reference)
            )
        """)
        conn.commit()
        _record_schema_migration(conn, 40, "matieres_premieres")

    # v41 — Matières premières : stock courant
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=41 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mp_stock (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matiere_id INTEGER NOT NULL UNIQUE REFERENCES matieres_premieres(id),
                quantite REAL DEFAULT 0,
                updated_at TEXT,
                updated_by_name TEXT
            )
        """)
        conn.commit()
        _record_schema_migration(conn, 41, "mp_stock")

    # v42 — Matières premières : historique mouvements
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=42 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mp_mouvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matiere_id INTEGER NOT NULL REFERENCES matieres_premieres(id),
                type_mouvement TEXT NOT NULL CHECK(type_mouvement IN ('entree','sortie','ajustement','transfert')),
                quantite REAL NOT NULL,
                quantite_avant REAL,
                quantite_apres REAL,
                ref_bl TEXT,
                note TEXT,
                emplacement_source TEXT,
                emplacement_dest TEXT,
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                created_by INTEGER,
                created_by_name TEXT
            )
        """)
        conn.commit()
        _record_schema_migration(conn, 42, "mp_mouvements")

    # v43 — MyCompta : codes de banque (code vendeur Factor → compte CAF)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=43 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS compta_banques (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code_vendeur TEXT NOT NULL UNIQUE,
                numero_compte TEXT NOT NULL,
                libelle TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_compta_banques_code ON compta_banques(code_vendeur)"
        )
        now = datetime.now().isoformat()
        for code, num in (("100", "512330000000"), ("98", "519320000000")):
            conn.execute(
                """INSERT OR IGNORE INTO compta_banques
                   (code_vendeur, numero_compte, libelle, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (code, num, f"Factor {code}", now, now),
            )
        conn.commit()
        _record_schema_migration(conn, 43, "compta_banques")

    # v44 — MyExpé : transporteurs historiques (Coupé, Ceva, Coquelle, Dimotrans)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=44 LIMIT 1").fetchone():
        from app.services.expe_transporteurs_seed import seed_expe_transporteurs_if_empty

        seed_expe_transporteurs_if_empty(conn)
        conn.commit()
        _record_schema_migration(conn, 44, "expe_transporteurs_seed")

    # v45 — MyAO : demandes
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=45 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ao_demandes (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                reference         TEXT NOT NULL UNIQUE,
                titre             TEXT NOT NULL,
                description       TEXT,
                date_creation     TEXT NOT NULL,
                date_limite       TEXT,
                statut            TEXT NOT NULL DEFAULT 'brouillon',
                created_by        INTEGER,
                responsable_email TEXT
            )
        """)
        conn.commit()
        _record_schema_migration(conn, 45, "ao_demandes")

    # v46 — MyAO : lignes
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=46 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ao_lignes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ao_id       INTEGER NOT NULL REFERENCES ao_demandes(id) ON DELETE CASCADE,
                ref_produit TEXT NOT NULL,
                designation TEXT NOT NULL,
                quantite    REAL NOT NULL,
                unite       TEXT DEFAULT 'unité',
                notes       TEXT,
                position    INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        _record_schema_migration(conn, 46, "ao_lignes")

    # v47 — MyAO : fournisseurs invités
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=47 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ao_fournisseurs (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                ao_id              INTEGER NOT NULL REFERENCES ao_demandes(id) ON DELETE CASCADE,
                nom_fournisseur    TEXT NOT NULL,
                email_contact      TEXT NOT NULL,
                token              TEXT NOT NULL UNIQUE,
                statut             TEXT NOT NULL DEFAULT 'invite',
                date_envoi         TEXT,
                date_ouverture     TEXT,
                date_reponse       TEXT,
                commentaire_global TEXT
            )
        """)
        conn.commit()
        _record_schema_migration(conn, 47, "ao_fournisseurs")

    # v48 — MyAO : réponses par ligne
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=48 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ao_reponses (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                ao_fournisseur_id  INTEGER NOT NULL REFERENCES ao_fournisseurs(id) ON DELETE CASCADE,
                ligne_id           INTEGER NOT NULL REFERENCES ao_lignes(id) ON DELETE CASCADE,
                prix_unitaire      REAL,
                delai_jours        INTEGER,
                commentaire        TEXT,
                UNIQUE(ao_fournisseur_id, ligne_id)
            )
        """)
        conn.commit()
        _record_schema_migration(conn, 48, "ao_reponses")

    # v49 — MyAO : messages portail
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=49 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ao_messages (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                ao_fournisseur_id INTEGER NOT NULL REFERENCES ao_fournisseurs(id) ON DELETE CASCADE,
                expediteur        TEXT NOT NULL,
                auteur_nom        TEXT,
                message           TEXT NOT NULL,
                date              TEXT NOT NULL,
                lu                INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        _record_schema_migration(conn, 49, "ao_messages")

    # v50 — MyAO : pièces jointes
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=50 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ao_pieces_jointes (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                ao_id             INTEGER REFERENCES ao_demandes(id) ON DELETE CASCADE,
                ao_fournisseur_id INTEGER REFERENCES ao_fournisseurs(id) ON DELETE CASCADE,
                filename          TEXT NOT NULL,
                stored_name       TEXT NOT NULL,
                taille_octets     INTEGER,
                uploaded_by       TEXT,
                date              TEXT NOT NULL
            )
        """)
        conn.commit()
        _record_schema_migration(conn, 50, "ao_pieces_jointes")

    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=51 LIMIT 1").fetchone():
        cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_channels)").fetchall()}
        if 'emoji' not in cols:
            conn.execute("ALTER TABLE chat_channels ADD COLUMN emoji TEXT DEFAULT NULL")
        conn.commit()
        _record_schema_migration(conn, 51, "chat_channels_emoji")

    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=52 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_mentions (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id        INTEGER NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
                channel_id        INTEGER NOT NULL,
                mentioned_user_id INTEGER,
                is_all            INTEGER NOT NULL DEFAULT 0,
                created_at        TEXT    NOT NULL,
                read_at           TEXT    DEFAULT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mentions_user ON chat_mentions(mentioned_user_id, read_at)"
        )
        conn.commit()
        _record_schema_migration(conn, 52, "chat_mentions")

    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=53 LIMIT 1").fetchone():
        cols = {r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if 'notif_asked_at' not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN notif_asked_at TEXT DEFAULT NULL")
        if 'notif_browser' not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN notif_browser INTEGER NOT NULL DEFAULT 0")
        conn.commit()
        _record_schema_migration(conn, 53, "users_notif_prefs")

    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=54 LIMIT 1").fetchone():
        cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()}
        if 'edited_at' not in cols:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN edited_at TEXT DEFAULT NULL")
        conn.commit()
        _record_schema_migration(conn, 54, "chat_messages_edited_at")

    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=55 LIMIT 1").fetchone():
        cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()}
        if 'pinned_at' not in cols:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN pinned_at TEXT DEFAULT NULL")
        if 'pinned_by' not in cols:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN pinned_by INTEGER DEFAULT NULL")
        conn.commit()
        _record_schema_migration(conn, 55, "chat_messages_pin")

    # v56 — Import OF PDF (MyProd)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=56 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS of_imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                of_numero TEXT,
                date_creation TEXT,
                delai_client TEXT,
                reference TEXT,
                machine TEXT,
                laize REAL,
                format TEXT,
                matiere TEXT,
                ref_matiere TEXT,
                glassine TEXT,
                ref_adhesif TEXT,
                qte_adhesif_g REAL,
                qte_adhesif_kg REAL,
                adhesif_label TEXT,
                qte_au_mille REAL,
                nb_levees INTEGER,
                qte_etiquettes INTEGER,
                qte_bobines REAL,
                metrage INTEGER,
                conditionnement TEXT,
                tolerance TEXT,
                cartons_type TEXT,
                nb_cartons INTEGER,
                mandrins_dia TEXT,
                mandrin_longueur REAL,
                nb_mandrins INTEGER,
                nb_tubes INTEGER,
                bobinettes_completes TEXT,
                outil_1_forme TEXT,
                outil_1_numero TEXT,
                outil_1_angle TEXT,
                outil_1_mag TEXT,
                outil_1_cp TEXT,
                outil_1_hauteur REAL,
                outil_1_fournisseur TEXT,
                outil_2_forme TEXT,
                outil_2_numero TEXT,
                outil_2_angle TEXT,
                outil_2_cp TEXT,
                outil_alt_forme TEXT,
                outil_alt_numero TEXT,
                outil_alt_angle TEXT,
                outil_alt_fournisseur TEXT,
                pdf_filename TEXT,
                date_import TEXT,
                imported_by TEXT,
                statut TEXT DEFAULT 'en_attente'
            );
            CREATE INDEX IF NOT EXISTS idx_of_imports_date ON of_imports(date_import);
            CREATE INDEX IF NOT EXISTS idx_of_imports_numero ON of_imports(of_numero);
            """
        )
        conn.commit()
        _record_schema_migration(conn, 56, "of_imports")

    # v57 — Post-its portail (desktop, par utilisateur)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=57 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS postits (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER NOT NULL,
              type TEXT NOT NULL CHECK(type IN ('today', 'someday')),
              title TEXT NOT NULL,
              pos_x INTEGER DEFAULT 100,
              pos_y INTEGER DEFAULT 100,
              width INTEGER DEFAULT 260,
              created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now')),
              FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS postit_tasks (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              postit_id INTEGER NOT NULL,
              text TEXT NOT NULL,
              done INTEGER DEFAULT 0,
              order_index INTEGER DEFAULT 0,
              FOREIGN KEY (postit_id) REFERENCES postits(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_postits_user ON postits(user_id);
            CREATE INDEX IF NOT EXISTS idx_postit_tasks_postit ON postit_tasks(postit_id);
            """
        )
        conn.commit()
        _record_schema_migration(conn, 57, "postits")

    # v58 — Annonces de mise à jour messagerie (chat interne)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=58 LIMIT 1").fetchone():
        _msg_chat_annonce = (
            '<div style="font-size:13px;line-height:1.7;color:var(--text2)">'
            '<div style="font-size:15px;font-weight:700;color:var(--text);margin-bottom:12px">'
            'Mise à jour — Messagerie</div>'
            '<div style="margin-bottom:10px;font-weight:600;color:var(--text);font-size:12px;'
            'text-transform:uppercase;letter-spacing:.5px">Nouveautés</div>'
            '<ul style="margin:0 0 14px 0;padding-left:18px">'
            '<li style="margin-bottom:5px">Envoi de GIFs — bouton + dans la barre de saisie, puis GIF.</li>'
            '<li style="margin-bottom:5px">Mentions — taper @ pour taguer un collègue. @tous pour tout le canal.</li>'
            '<li style="margin-bottom:5px">Notifications navigateur — demande d\'activation au premier usage.</li>'
            '<li style="margin-bottom:5px">Emoji de canal — les administrateurs peuvent personnaliser l\'icône depuis les réglages du canal.</li>'
            '<li style="margin-bottom:5px">Réactions emoji sur les messages.</li>'
            '<li style="margin-bottom:5px">Modification d\'un message (15 min, texte seul).</li>'
            '<li style="margin-bottom:5px">Épinglage de messages — bouton dans l\'en-tête du canal.</li>'
            '</ul>'
            '<div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border);'
            'font-size:11px;color:var(--muted);line-height:1.6">'
            'Dans l\'optique d\'améliorer constamment l\'outil, vos retours sont les bienvenus.<br>'
            'Merci de votre confiance.<br>'
            '<span style="color:var(--text2);font-weight:600">Eugène</span></div></div>'
        )
        _seed_ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        exists = conn.execute(
            "SELECT 1 FROM update_announcements WHERE scope=? AND titre=? LIMIT 1",
            ("messages", "Messagerie — GIFs, mentions et notifications"),
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO update_announcements (scope,titre,message,created_at,created_by,active) VALUES (?,?,?,?,?,1)",
                (
                    "messages",
                    "Messagerie — GIFs, mentions et notifications",
                    _msg_chat_annonce,
                    _seed_ts,
                    "système",
                ),
            )
        conn.commit()
        _record_schema_migration(conn, 58, "update_announcements_messages_chat")

    # v59 — Post-its visibles sur toutes les pages (option multi-page)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=59 LIMIT 1").fetchone():
        conn.execute(
            "ALTER TABLE postits ADD COLUMN multi_page INTEGER NOT NULL DEFAULT 0"
        )
        conn.commit()
        _record_schema_migration(conn, 59, "postits_multi_page")

    # v60 — Matières premières : piles (palettes) et palettes (cartons)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=60 LIMIT 1").fetchone():
        mp_cols = {
            r["name"]
            for r in conn.execute("PRAGMA table_info(matieres_premieres)").fetchall()
        }
        if "palettes_par_pile" not in mp_cols:
            conn.execute(
                "ALTER TABLE matieres_premieres ADD COLUMN palettes_par_pile REAL"
            )
        conn.execute(
            """
            UPDATE matieres_premieres
            SET palettes_par_pile = 1
            WHERE categorie = 'palette'
              AND (palettes_par_pile IS NULL OR palettes_par_pile <= 0)
            """
        )
        conn.commit()
        _record_schema_migration(conn, 60, "matieres_premieres_palettes_par_pile")

    # v61 — Post-its réduits en barre en bas de l'écran
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=61 LIMIT 1").fetchone():
        conn.execute(
            "ALTER TABLE postits ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0"
        )
        conn.commit()
        _record_schema_migration(conn, 61, "postits_hidden")

    # v62 — Post-its : couleur personnalisable (pastille)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=62 LIMIT 1").fetchone():
        conn.execute("ALTER TABLE postits ADD COLUMN color TEXT")
        conn.execute(
            "UPDATE postits SET color='#22d3ee' WHERE type='today' AND (color IS NULL OR color='')"
        )
        conn.execute(
            "UPDATE postits SET color='#fbbf24' WHERE type='someday' AND (color IS NULL OR color='')"
        )
        conn.commit()
        _record_schema_migration(conn, 62, "postits_color")

    # v63 — MyExpé : FK transporteur sur départs
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=63 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_departs)").fetchall()}
        if "transporteur_id" not in cols:
            conn.execute(
                "ALTER TABLE expe_departs ADD COLUMN transporteur_id INTEGER REFERENCES expe_transporteurs(id)"
            )
        conn.commit()
        _record_schema_migration(conn, 63, "expe_departs_transporteur_fk")

    # v64 — MyExpé : capacités transporteurs (comparateur)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=64 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_transporteurs)").fetchall()}
        for col, defn in [
            ("palette_max", "INTEGER"),
            ("poids_max_kg", "REAL"),
            ("accepte_poids", "INTEGER DEFAULT 1"),
            ("accepte_palette", "INTEGER DEFAULT 1"),
        ]:
            if col not in cols:
                conn.execute(f"ALTER TABLE expe_transporteurs ADD COLUMN {col} {defn}")
        conn.commit()
        _record_schema_migration(conn, 64, "expe_transporteurs_capacites")
        from app.services.expe_transporteurs_seed import update_expe_transporteurs_capacites

        update_expe_transporteurs_capacites(conn)
        conn.commit()

    # v65 — MyExpé : grilles tarifaires structurées
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=65 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS expe_tarifs (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                transporteur_id  INTEGER NOT NULL,
                type_envoi       TEXT NOT NULL,
                base_calcul      TEXT NOT NULL,
                zone_type        TEXT NOT NULL,
                zone_valeur      TEXT NOT NULL,
                tranche_min      REAL NOT NULL DEFAULT 0,
                tranche_max      REAL,
                prix             REAL NOT NULL,
                unite            TEXT NOT NULL,
                mini_perception  REAL,
                valid_from       TEXT,
                valid_to         TEXT,
                actif            INTEGER DEFAULT 0,
                source_filename  TEXT,
                created_at       TEXT,
                created_by_email TEXT,
                FOREIGN KEY (transporteur_id) REFERENCES expe_transporteurs(id)
            );
            CREATE INDEX IF NOT EXISTS idx_expe_tarifs_lookup
                ON expe_tarifs(transporteur_id, type_envoi, zone_type, zone_valeur, actif);

            CREATE TABLE IF NOT EXISTS expe_tarifs_frais (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                transporteur_id  INTEGER NOT NULL,
                libelle          TEXT NOT NULL,
                mode             TEXT NOT NULL,
                valeur           REAL NOT NULL,
                mini             REAL,
                applique_defaut  INTEGER DEFAULT 1,
                FOREIGN KEY (transporteur_id) REFERENCES expe_transporteurs(id)
            );
            """
        )
        conn.commit()
        _record_schema_migration(conn, 65, "expe_tarifs_schema")

    # v66 — MyExpé : demandes de devis (prospection parallèle)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=66 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS expe_demandes_devis (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                depart_id               INTEGER,
                poids_total_kg          REAL,
                nb_palette              REAL,
                code_postal_destination TEXT,
                type_envoi              TEXT,
                contraintes             TEXT,
                statut                  TEXT NOT NULL DEFAULT 'ouverte',
                created_at              TEXT NOT NULL,
                created_by_email        TEXT
            );

            CREATE TABLE IF NOT EXISTS expe_devis_reponses (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                demande_id       INTEGER NOT NULL,
                transporteur_id  INTEGER,
                nom_transporteur TEXT,
                prix             REAL,
                delai_jours      INTEGER,
                commentaire      TEXT,
                statut           TEXT NOT NULL DEFAULT 'envoyee',
                sent_at          TEXT,
                recu_at          TEXT,
                FOREIGN KEY (demande_id) REFERENCES expe_demandes_devis(id)
            );

            CREATE INDEX IF NOT EXISTS idx_devis_reponses_demande
                ON expe_devis_reponses(demande_id);
            """
        )
        conn.commit()
        _record_schema_migration(conn, 66, "expe_demandes_devis")

    # v67 — MyExpé : transporteurs prospects
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=67 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS expe_transporteurs_prospects (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                nom              TEXT NOT NULL,
                contact_nom      TEXT,
                contact_email    TEXT,
                contact_tel      TEXT,
                zone_couverte    TEXT,
                type_service     TEXT,
                capacite_max_pal INTEGER,
                statut_demarchage TEXT NOT NULL DEFAULT 'a_contacter',
                notes            TEXT,
                created_at       TEXT NOT NULL,
                updated_at       TEXT
            );
            """
        )
        conn.commit()
        _record_schema_migration(conn, 67, "expe_transporteurs_prospects")

    # v68 — MyExpé : délais carte France (base partagée, remplace localStorage)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=68 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS expe_delais (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                departement      TEXT NOT NULL,
                type_envoi       TEXT NOT NULL DEFAULT 'default',
                transporteur_id  INTEGER,
                delai_jours      INTEGER,
                zone_label       TEXT NOT NULL DEFAULT 'france',
                delai_texte      TEXT NOT NULL DEFAULT 'J+2',
                updated_at       TEXT,
                updated_by_email TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_expe_delais_unique
                ON expe_delais(departement, type_envoi, COALESCE(transporteur_id, -1));
            """
        )
        conn.commit()

        from app.web.expe_france_delais_data import DELAIS_FRANCE_DEFAULT
        from zoneinfo import ZoneInfo

        now = datetime.now(ZoneInfo("Europe/Paris")).strftime("%Y-%m-%dT%H:%M:%S")
        for dept, data in DELAIS_FRANCE_DEFAULT.items():
            delai_texte = data.get("delai", "J+2")
            zone_label = data.get("zone", "france")
            try:
                delai_jours = int(str(delai_texte).replace("J+", "").strip())
            except (ValueError, AttributeError):
                delai_jours = 2
            conn.execute(
                """
                INSERT OR IGNORE INTO expe_delais
                (departement, type_envoi, transporteur_id, delai_jours, zone_label, delai_texte, updated_at)
                VALUES (?, 'default', NULL, ?, ?, ?, ?)
                """,
                (dept, delai_jours, zone_label, delai_texte, now),
            )
        conn.commit()
        _record_schema_migration(conn, 68, "expe_delais")

    # v69 — MyAO : carnet fournisseurs récurrents
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=69 LIMIT 1").fetchone():
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ao_carnet_fournisseurs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nom         TEXT NOT NULL,
                email       TEXT NOT NULL,
                pays        TEXT,
                notes       TEXT,
                created_at  TEXT NOT NULL
            )
            """
        )
        conn.commit()
        _record_schema_migration(conn, 69, "ao_carnet_fournisseurs")

    # v70 — MyAO : catalogue produits récurrents
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=70 LIMIT 1").fetchone():
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ao_produits (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ref         TEXT NOT NULL,
                designation TEXT NOT NULL,
                unite       TEXT DEFAULT 'unité',
                notes       TEXT,
                created_at  TEXT NOT NULL
            )
            """
        )
        conn.commit()
        _record_schema_migration(conn, 70, "ao_produits")

    # v71 — Liaison OF → planning_entries
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=71 LIMIT 1").fetchone():
        pe_cols = {row[1] for row in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        if "of_import_id" not in pe_cols:
            conn.execute(
                "ALTER TABLE planning_entries ADD COLUMN of_import_id INTEGER"
            )
        conn.commit()
        _record_schema_migration(conn, 71, "planning_entries_of_import_link")

    # v72 — MyAO : carnet clients récurrents
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=72 LIMIT 1").fetchone():
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ao_carnet_clients (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nom         TEXT NOT NULL,
                email       TEXT NOT NULL,
                pays        TEXT,
                notes       TEXT,
                created_at  TEXT NOT NULL
            )
            """
        )
        conn.commit()
        _record_schema_migration(conn, 72, "ao_carnet_clients")

    # v73 — MyAO : fiche produit complète (JSON + client)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=73 LIMIT 1").fetchone():
        ap_cols = {row[1] for row in conn.execute("PRAGMA table_info(ao_produits)").fetchall()}
        if "client_id" not in ap_cols:
            conn.execute("ALTER TABLE ao_produits ADD COLUMN client_id INTEGER")
        if "fiche_json" not in ap_cols:
            conn.execute("ALTER TABLE ao_produits ADD COLUMN fiche_json TEXT")
        conn.commit()
        _record_schema_migration(conn, 73, "ao_produits_fiche")

    # v74 — Matières premières : frontal, glassine (+ couleur)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=74 LIMIT 1").fetchone():
        mp_cols = {row[1] for row in conn.execute("PRAGMA table_info(matieres_premieres)").fetchall()}
        if "couleur" not in mp_cols:
            conn.execute("ALTER TABLE matieres_premieres ADD COLUMN couleur TEXT")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS matieres_premieres_v74 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categorie TEXT NOT NULL,
                reference TEXT NOT NULL,
                designation TEXT NOT NULL,
                seuil_alerte REAL DEFAULT 0,
                actif INTEGER DEFAULT 1,
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                palettes_par_pile REAL,
                couleur TEXT,
                UNIQUE(categorie, reference)
            )
            """
        )
        old_cols = [r[1] for r in conn.execute("PRAGMA table_info(matieres_premieres)").fetchall()]
        sel = ["id", "categorie", "reference", "designation", "seuil_alerte", "actif", "created_at", "updated_at"]
        if "palettes_par_pile" in old_cols:
            sel.append("palettes_par_pile")
        else:
            sel.append("NULL AS palettes_par_pile")
        sel.append("couleur" if "couleur" in old_cols else "NULL AS couleur")
        conn.execute(
            f"INSERT INTO matieres_premieres_v74 ({', '.join(sel)}) "
            f"SELECT {', '.join(sel)} FROM matieres_premieres"
        )
        conn.execute("DROP TABLE matieres_premieres")
        conn.execute("ALTER TABLE matieres_premieres_v74 RENAME TO matieres_premieres")
        conn.commit()
        _record_schema_migration(conn, 74, "matieres_premieres_frontal_glassine")

    # v75 — MyAO : carnet fournisseurs — société et adresse
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=75 LIMIT 1").fetchone():
        cf_cols = {row[1] for row in conn.execute("PRAGMA table_info(ao_carnet_fournisseurs)").fetchall()}
        if "societe" not in cf_cols:
            conn.execute("ALTER TABLE ao_carnet_fournisseurs ADD COLUMN societe TEXT")
        if "adresse" not in cf_cols:
            conn.execute("ALTER TABLE ao_carnet_fournisseurs ADD COLUMN adresse TEXT")
        conn.commit()
        _record_schema_migration(conn, 75, "ao_carnet_fournisseurs_societe_adresse")

    # v77 — MyAO : référence produit unique (insensible à la casse)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=77 LIMIT 1").fetchone():
        dup = conn.execute(
            """
            SELECT LOWER(ref) FROM ao_produits
            GROUP BY LOWER(ref) HAVING COUNT(*) > 1 LIMIT 1
            """
        ).fetchone()
        if not dup:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_ao_produits_ref "
                "ON ao_produits(ref COLLATE NOCASE)"
            )
        conn.commit()
        _record_schema_migration(conn, 77, "ao_produits_ref_unique")

    # v76 — MyExpé : type de palette (réf. matières premières MyStock)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=76 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_departs)").fetchall()}
        if "type_palette_matiere_id" not in cols:
            conn.execute(
                "ALTER TABLE expe_departs ADD COLUMN type_palette_matiere_id INTEGER "
                "REFERENCES matieres_premieres(id)"
            )
        conn.commit()
        _record_schema_migration(conn, 76, "expe_departs_type_palette")

    # v78 — Calcul coûts matières (remplace Excel / schéma distinct de MyDevis matiere_*)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=78 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS mc_setting (
                key TEXT PRIMARY KEY NOT NULL,
                value_decimal REAL NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                updated_by INTEGER REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS mc_supplier (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                country TEXT,
                notes TEXT,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS mc_material_category (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE
                    CHECK(code IN ('FRONTAL', 'ADHESIF', 'SILICONE', 'GLASSINE', 'AUTRE')),
                label TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS mc_material (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                appellation_code TEXT NOT NULL,
                category_id INTEGER NOT NULL
                    REFERENCES mc_material_category(id),
                supplier_id INTEGER REFERENCES mc_supplier(id),
                weight_per_m2 REAL NOT NULL DEFAULT 0,
                weight_gsm INTEGER,
                price_currency TEXT NOT NULL DEFAULT 'EUR'
                    CHECK(price_currency IN ('EUR', 'USD')),
                unit_price REAL NOT NULL DEFAULT 0,
                price_basis TEXT NOT NULL DEFAULT 'PER_KG'
                    CHECK(price_basis IN ('PER_KG', 'PER_M2')),
                tax_incidence REAL NOT NULL DEFAULT 1.0,
                is_imported INTEGER NOT NULL DEFAULT 0,
                container_kg REAL,
                container_cost_usd REAL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS mc_material_price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                material_id INTEGER NOT NULL REFERENCES mc_material(id),
                unit_price REAL NOT NULL,
                price_currency TEXT NOT NULL
                    CHECK(price_currency IN ('EUR', 'USD')),
                tax_incidence REAL NOT NULL DEFAULT 1.0,
                effective_date TEXT NOT NULL,
                source TEXT,
                created_by INTEGER REFERENCES users(id),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS mc_product (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT NOT NULL,
                frontal_id INTEGER REFERENCES mc_material(id),
                adhesif_id INTEGER REFERENCES mc_material(id),
                silicone_id INTEGER REFERENCES mc_material(id),
                glassine_id INTEGER REFERENCES mc_material(id),
                custom_margin_eur_m2 REAL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS mc_product_extra_material (
                product_id INTEGER NOT NULL REFERENCES mc_product(id) ON DELETE CASCADE,
                material_id INTEGER NOT NULL REFERENCES mc_material(id),
                sort_order INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (product_id, material_id)
            );

            CREATE INDEX IF NOT EXISTS idx_mc_material_appellation
                ON mc_material(appellation_code);
            CREATE INDEX IF NOT EXISTS idx_mc_material_category
                ON mc_material(category_id);
            CREATE INDEX IF NOT EXISTS idx_mc_material_active
                ON mc_material(is_active);
            CREATE INDEX IF NOT EXISTS idx_mc_material_price_history_material
                ON mc_material_price_history(material_id, effective_date);
            CREATE UNIQUE INDEX IF NOT EXISTS idx_mc_product_code
                ON mc_product(code COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_mc_product_active
                ON mc_product(is_active);
            CREATE INDEX IF NOT EXISTS idx_mc_supplier_active
                ON mc_supplier(is_active);
            """
        )
        conn.executemany(
            "INSERT OR IGNORE INTO mc_material_category (code, label, sort_order) VALUES (?,?,?)",
            [
                ("FRONTAL", "Frontal", 1),
                ("ADHESIF", "Adhésif", 2),
                ("SILICONE", "Silicone", 3),
                ("GLASSINE", "Glassine", 4),
                ("AUTRE", "Autre", 5),
            ],
        )
        conn.executemany(
            "INSERT OR IGNORE INTO mc_setting (key, value_decimal) VALUES (?,?)",
            [
                ("eur_usd_rate", 0.85),
                ("default_container_cost_usd", 4000.0),
                ("default_container_kg", 26000.0),
                ("default_margin_eur_m2", 0.06),
            ],
        )
        conn.commit()
        _record_schema_migration(conn, 78, "mc_material_cost_schema")

    # v79 — Coûts matières : source du taux FX sur mc_setting
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=79 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(mc_setting)").fetchall()}
        if "source" not in cols:
            conn.execute("ALTER TABLE mc_setting ADD COLUMN source TEXT")
        conn.commit()
        _record_schema_migration(conn, 79, "mc_setting_fx_source")

    # v80 — Accès applicatif MyDevis (devis) → pricing
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=80 LIMIT 1").fetchone():
        for row in conn.execute(
            "SELECT id, access_overrides, portal_apps_order FROM users"
        ).fetchall():
            uid = row["id"]
            ao = row["access_overrides"]
            if ao:
                try:
                    o = json.loads(ao) if isinstance(ao, str) else ao
                except (json.JSONDecodeError, TypeError):
                    o = None
                if isinstance(o, dict) and "devis" in o:
                    if "pricing" not in o:
                        o["pricing"] = o["devis"]
                    del o["devis"]
                    conn.execute(
                        "UPDATE users SET access_overrides=? WHERE id=?",
                        (json.dumps(o, ensure_ascii=False), uid),
                    )
            po = row["portal_apps_order"]
            if po:
                try:
                    arr = json.loads(po) if isinstance(po, str) else po
                except (json.JSONDecodeError, TypeError):
                    arr = None
                if isinstance(arr, list):
                    new_arr = []
                    seen: set = set()
                    for x in arr:
                        if not isinstance(x, str):
                            continue
                        tid = "pricing" if x.strip() == "devis" else x.strip()
                        if tid and tid not in seen:
                            new_arr.append(tid)
                            seen.add(tid)
                    if new_arr != arr:
                        conn.execute(
                            "UPDATE users SET portal_apps_order=? WHERE id=?",
                            (json.dumps(new_arr, ensure_ascii=False), uid),
                        )
        conn.commit()
        _record_schema_migration(conn, 80, "app_access_devis_to_pricing")

    # v81 — Coûts matières : accès réservé Direction et super admin (retrait Administration)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=81 LIMIT 1").fetchone():
        from config import ROLE_DIRECTION, ROLE_SUPERADMIN

        allowed_roles = {ROLE_DIRECTION, ROLE_SUPERADMIN}
        for row in conn.execute("SELECT id, role, access_overrides FROM users").fetchall():
            if row["role"] in allowed_roles:
                continue
            ao = row["access_overrides"]
            if not ao:
                continue
            try:
                o = json.loads(ao) if isinstance(ao, str) else ao
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(o, dict):
                continue
            changed = False
            for key in ("pricing", "devis"):
                if key in o:
                    del o[key]
                    changed = True
            if not changed:
                continue
            new_ao = json.dumps(o, ensure_ascii=False) if o else None
            conn.execute(
                "UPDATE users SET access_overrides=? WHERE id=?",
                (new_ao, row["id"]),
            )
        conn.commit()
        _record_schema_migration(conn, 81, "pricing_access_direction_superadmin_only")

    # v82 — MyStock : produits finis (catalogue + mouvements)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=82 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS produits_finis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT NOT NULL UNIQUE,
                designation TEXT NOT NULL,
                unite TEXT DEFAULT 'pièces',
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS pf_mouvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT NOT NULL,
                designation TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('entree', 'sortie')),
                quantite REAL NOT NULL,
                unite TEXT DEFAULT 'pièces',
                emplacement TEXT NOT NULL,
                no_of TEXT,
                commentaire TEXT,
                user_login TEXT,
                date_mouvement TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_pf_mvt_ref ON pf_mouvements(reference);
            CREATE INDEX IF NOT EXISTS idx_pf_mvt_date ON pf_mouvements(date_mouvement DESC);
            CREATE INDEX IF NOT EXISTS idx_pf_mvt_empl ON pf_mouvements(emplacement);
            """
        )
        conn.commit()
        _record_schema_migration(conn, 82, "produits_finis_pf_mouvements")

    # v83 — MyAO : quotation, devise, unité et coef sur les réponses fournisseur
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=83 LIMIT 1").fetchone():
        ar_cols = {row[1] for row in conn.execute("PRAGMA table_info(ao_reponses)").fetchall()}
        if "quotation" not in ar_cols:
            conn.execute("ALTER TABLE ao_reponses ADD COLUMN quotation REAL")
        if "devise" not in ar_cols:
            conn.execute("ALTER TABLE ao_reponses ADD COLUMN devise TEXT DEFAULT 'EUR'")
        if "unite_quotation" not in ar_cols:
            conn.execute(
                "ALTER TABLE ao_reponses ADD COLUMN unite_quotation TEXT DEFAULT 'mille'"
            )
        if "coef" not in ar_cols:
            conn.execute("ALTER TABLE ao_reponses ADD COLUMN coef REAL DEFAULT 1.0")
        if "devise_prix_devis" not in ar_cols:
            conn.execute(
                "ALTER TABLE ao_reponses ADD COLUMN devise_prix_devis TEXT DEFAULT 'EUR'"
            )
        conn.execute(
            """UPDATE ao_reponses
               SET quotation = prix_unitaire
               WHERE quotation IS NULL AND prix_unitaire IS NOT NULL"""
        )
        conn.execute(
            """UPDATE ao_reponses SET coef = 1.0 WHERE coef IS NULL"""
        )
        conn.commit()
        _record_schema_migration(conn, 83, "ao_reponses_quotation_pricing")

    # v84 — planning_entries : département livraison et prise de RDV
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=84 LIMIT 1").fetchone():
        pe_cols = {row[1] for row in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        if "departement_livraison" not in pe_cols:
            conn.execute(
                "ALTER TABLE planning_entries ADD COLUMN departement_livraison TEXT DEFAULT ''"
            )
        if "prise_rdv" not in pe_cols:
            conn.execute(
                "ALTER TABLE planning_entries ADD COLUMN prise_rdv INTEGER DEFAULT 0"
            )
        conn.commit()
        _record_schema_migration(conn, 84, "planning_entries_dept_livraison_prise_rdv")

    # v85 — MyExpé : portail transporteur (réponses en ligne)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=85 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS expe_portal_transporteurs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                email           TEXT NOT NULL UNIQUE,
                token           TEXT NOT NULL UNIQUE,
                transporteur_id INTEGER,
                prospect_id     INTEGER,
                created_at      TEXT NOT NULL,
                last_opened_at  TEXT,
                last_opened_ip  TEXT,
                actif           INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (transporteur_id) REFERENCES expe_transporteurs(id),
                FOREIGN KEY (prospect_id) REFERENCES expe_transporteurs_prospects(id)
            );
            """
        )

        dr_cols = {row[1] for row in conn.execute("PRAGMA table_info(expe_devis_reponses)").fetchall()}
        if "destinataire_email" not in dr_cols:
            conn.execute("ALTER TABLE expe_devis_reponses ADD COLUMN destinataire_email TEXT")
        if "opened_at" not in dr_cols:
            conn.execute("ALTER TABLE expe_devis_reponses ADD COLUMN opened_at TEXT")
        if "opened_ip" not in dr_cols:
            conn.execute("ALTER TABLE expe_devis_reponses ADD COLUMN opened_ip TEXT")
        conn.commit()
        _record_schema_migration(conn, 85, "expe_portal_transporteurs")

    # v86 — MyStock Monitoring : réconciliation stocks PF ERP vs MySifa
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=86 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS reconciliation_snapshots (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at          TEXT NOT NULL,
                created_by_name     TEXT,
                source_filename     TEXT,
                nb_refs_erp         INTEGER DEFAULT 0,
                nb_refs_mysifa      INTEGER DEFAULT 0,
                nb_matched          INTEGER DEFAULT 0,
                nb_ecarts           INTEGER DEFAULT 0,
                nb_sans_corresp     INTEGER DEFAULT 0,
                nb_negatifs         INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS reconciliation_lines (
                id                      INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id             INTEGER NOT NULL,
                reference               TEXT NOT NULL,
                designation             TEXT,
                unite                   TEXT,
                stock_erp               REAL,
                stock_mysifa            REAL,
                ecart                   REAL,
                statut                  TEXT NOT NULL,
                erp_dernier_mvt_libelle TEXT,
                erp_dernier_mvt_date    TEXT,
                erp_dernier_mvt_qte     REAL,
                mysifa_date_fifo        TEXT,
                FOREIGN KEY (snapshot_id) REFERENCES reconciliation_snapshots(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_reconciliation_lines_snapshot
                ON reconciliation_lines(snapshot_id);
            CREATE INDEX IF NOT EXISTS idx_reconciliation_lines_snapshot_statut
                ON reconciliation_lines(snapshot_id, statut);
            """
        )
        conn.commit()
        _record_schema_migration(conn, 86, "reconciliation_snapshots_pf")

    # v87 — Tableaux de bord : référentiel créé par le superadmin
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=87 LIMIT 1").fetchone():
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS dashboards (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                titre       TEXT NOT NULL,
                description TEXT DEFAULT '',
                widget_type TEXT NOT NULL CHECK(widget_type IN ('stock_alerts','planning_summary','expe_today')),
                config_json TEXT NOT NULL DEFAULT '{}',
                actif       INTEGER NOT NULL DEFAULT 1,
                created_by_id INTEGER REFERENCES users(id),
                created_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                updated_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_dashboards_actif ON dashboards(actif);
        """)
        conn.commit()
        _record_schema_migration(conn, 87, "dashboards")

    # v88 — Tableaux de bord : association utilisateur ↔ dashboard
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=88 LIMIT 1").fetchone():
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS user_dashboards (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                dashboard_id INTEGER NOT NULL REFERENCES dashboards(id) ON DELETE CASCADE,
                pos_x        REAL NOT NULL DEFAULT 20,
                pos_y        REAL NOT NULL DEFAULT 80,
                minimized    INTEGER NOT NULL DEFAULT 0,
                added_at     TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                UNIQUE(user_id, dashboard_id)
            );
            CREATE INDEX IF NOT EXISTS idx_user_dashboards_user ON user_dashboards(user_id);
        """)
        conn.commit()
        _record_schema_migration(conn, 88, "user_dashboards")

    # v89 — Table des clés API (pont Access ↔ MySifa)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=89 LIMIT 1").fetchone():
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                key_prefix  TEXT NOT NULL,
                key_hash    TEXT NOT NULL UNIQUE,
                scopes      TEXT NOT NULL DEFAULT 'production:read,production:write',
                is_active   INTEGER NOT NULL DEFAULT 1,
                created_by  TEXT,
                created_at  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                last_used_at TEXT,
                revoked_at  TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON api_keys(key_hash);
            CREATE INDEX IF NOT EXISTS idx_api_keys_active ON api_keys(is_active);
        """)
        conn.commit()
        _record_schema_migration(conn, 89, "api_keys")

    _record_schema_migration(
        conn,
        SCHEMA_MIGRATION_VERSION_BASELINE,
        "mysifa_aggregate_migrations_v1",
    )


def create_default_admin():
    import bcrypt
    from config import DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_NOM, DEFAULT_ADMIN_PWD
    with get_db() as conn:
        pwd_hash = bcrypt.hashpw(DEFAULT_ADMIN_PWD.encode(), bcrypt.gensalt()).decode()
        now = datetime.now().isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO users (email,nom,password_hash,role,actif,created_at) VALUES (?,?,?,'direction',1,?)",
            (DEFAULT_ADMIN_EMAIL, DEFAULT_ADMIN_NOM, pwd_hash, now)
        )
        conn.commit()

# ─── Détection doublons ───────────────────────────────────────────
def is_duplicate(conn, operateur, date_operation, operation_code, no_dossier):
    row = conn.execute(
        """SELECT id FROM production_data
           WHERE operateur=? AND date_operation=? AND operation_code=?
             AND COALESCE(no_dossier,'')=COALESCE(?,'') LIMIT 1""",
        (operateur, date_operation, operation_code, no_dossier)
    ).fetchone()
    return row is not None


# ─── Helpers parsing ──────────────────────────────────────────────
def parse_french_number(val):
    if val is None:
        return 0
    s = str(val).strip()
    if not s:
        return 0
    s = s.replace('\u202f','').replace('\xa0','').replace(' ','').replace(',','.')
    try:
        return float(s)
    except ValueError:
        return 0


def parse_datetime(val):
    if not val:
        return None
    s = str(val).strip().rstrip('C').strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def fmt_duration(minutes):
    if minutes is None or minutes < 0:
        return "-"
    h = int(minutes) // 60
    m = int(minutes) % 60
    return f"{h}h {m:02d}min" if h > 0 else f"{m}min"


def parse_file(file_bytes, filename):
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "csv":
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            for sep in [";", ",", "\t"]:
                try:
                    df = pd.read_csv(io.BytesIO(file_bytes), encoding=encoding, sep=sep, dtype=str)
                    if len(df.columns) > 3:
                        return df
                except Exception:
                    continue
        return pd.read_csv(io.BytesIO(file_bytes), dtype=str)
    elif ext in ("xls", "xlsx", "xlsm"):
        return pd.read_excel(io.BytesIO(file_bytes), dtype=str)
    else:
        raise ValueError(f"Format non supporté: .{ext}")


COLUMN_MAP = {
    "opérateur": "operateur", "operateur": "operateur",
    "date et heure d'opération": "date_operation",
    "date et heure d'operation": "date_operation",
    "opération": "operation", "operation": "operation",
    "service": "service", "machine": "machine",
    "no dossier": "no_dossier", "n° dossier": "no_dossier",
    "client": "client",
    "désignation produit": "designation",
    "designation produit": "designation",
    "désignation produit ": "designation",
    "quantité à traiter": "quantite_a_traiter",
    "quantite a traiter": "quantite_a_traiter",
    "quantité traitée": "quantite_traitee",
    "quantite traitee": "quantite_traitee",
    "no cde": "no_cde",
    "date exp.p.": "date_exp", "date exp": "date_exp",
    "date liv.p.": "date_liv", "date liv": "date_liv",
    "type dossier": "type_dossier",
}


def map_columns(df):
    mapped = {}
    for col in df.columns:
        key = col.strip().lower()
        if key in COLUMN_MAP:
            mapped[col] = COLUMN_MAP[key]
    return mapped


init_db()
create_default_admin()

try:
    from config import refresh_operations_cache

    refresh_operations_cache()
except Exception:
    pass

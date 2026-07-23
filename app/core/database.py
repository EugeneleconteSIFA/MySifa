"""
SIFA â€” Database & helpers v0.5
Ajouts : colonnes traÃ§abilitÃ©, dÃ©tection doublons Ã  l'import
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
from config import DB_PATH, UPLOAD_DIR, ROLE_SUPERADMIN, ROLE_DIRECTION, SUPERADMIN_EMAIL, classify_operation, MIGRATIONS_DISABLED, ENV_NAME
from app.services.emplacements_plan import reload_emplacements_plan, sync_emplacements_plan_to_db

# Baselinage des migrations SQL dÃ©jÃ  regroupÃ©es dans _migrate (historique).
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
    """Applique les migrations manquantes (idempotent, une fois par process).

    Si MIGRATIONS_DISABLED=1 (env staging v1), ne joue AUCUNE migration : la DB
    est partagÃ©e avec la prod v2, qui en a la responsabilitÃ© exclusive. Le flag
    est posÃ© une fois pour toutes pour ne pas re-tenter Ã  chaque requÃªte.
    """
    global _schema_migrate_done
    if _schema_migrate_done:
        return
    with _schema_migrate_lock:
        if _schema_migrate_done:
            return
        if MIGRATIONS_DISABLED:
            print(f"[MySifa] _ensure_schema : migrations DÃ‰SACTIVÃ‰ES (ENV_NAME={ENV_NAME}). "
                  f"La DB n'est PAS modifiÃ©e par cette instance.")
            _schema_migrate_done = True
            return
        # DB fraÃ®che (client Kernse nouvellement provisionnÃ©, MySifa jamais
        # dÃ©marrÃ©) : les tables de base n'existent pas encore. _migrate()
        # tente des ALTER TABLE et crashe. On skip ici et on laisse `init_db()`
        # crÃ©er le schÃ©ma de base via son executescript, puis appeler _migrate
        # lui-mÃªme sur une DB peuplÃ©e. Le flag _schema_migrate_done reste
        # Ã  False pour que init_db puisse boucler.
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='production_data' LIMIT 1"
        ).fetchone()
        if not row:
            return
        _migrate(conn)
        conn.commit()
        _schema_migrate_done = True


def _register_udfs(conn: sqlite3.Connection) -> None:
    """
    Enregistre les fonctions Python appelables depuis SQL/triggers.

    `norm_ref_produit(s)` extrait la clÃ© produit normalisÃ©e "XXX/NNNN" d'une
    chaÃ®ne quelconque ("1013/0068 - COHESIO 1" â†’ "1013/0068"). UtilisÃ©e par
    les triggers qui maintiennent `planning_entries.ref_produit_norm` et
    `fiches_techniques.ref_produit_norm` Ã  jour automatiquement Ã  chaque
    insertion ou modification.
    """
    try:
        from app.services.fiche_ref_parser import normalize_ref_produit
    except Exception:
        return
    try:
        # deterministic=True permet Ã  SQLite de l'utiliser dans les index/triggers
        conn.create_function("norm_ref_produit", 1, normalize_ref_produit, deterministic=True)
    except TypeError:
        # Python < 3.8 ou SQLite trop ancien : pas de flag deterministic
        conn.create_function("norm_ref_produit", 1, normalize_ref_produit)


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
    # WAL : les lecteurs ne sont plus bloquÃ©s par les Ã©critures (mode persistant,
    # stockÃ© dans le fichier DB â€” le PRAGMA Ã  chaque connexion est sans coÃ»t).
    # synchronous=NORMAL : suffisant en WAL (fsync au checkpoint, pas Ã  chaque tx).
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.OperationalError:
        pass  # DB en lecture seule ou FS sans support WAL : on ne bloque pas
    _register_udfs(conn)
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
    """RÃ©fÃ©rentiel plan MyStock â€” crÃ©e la table si besoin, seed depuis CSV uniquement si vide.

    Les modifications manuelles (ajout/suppression via l'UI ParamÃ¨tres) sont prÃ©servÃ©es
    au redÃ©marrage. Le bouton 'Recharger depuis CSV' est le seul dÃ©clencheur d'un
    rechargement complet intentionnel.
    """
    conn.execute(
        """CREATE TABLE IF NOT EXISTS emplacements_plan (
            code TEXT PRIMARY KEY NOT NULL,
            imported_at TEXT NOT NULL
        )"""
    )
    count = conn.execute("SELECT COUNT(*) FROM emplacements_plan").fetchone()[0]
    if count == 0:
        # Table vide : seed initial depuis le CSV
        reload_emplacements_plan(conn)


def _migrate(conn):
    """Ajoute colonnes manquantes sur base existante sans tout recrÃ©er."""
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

    # Migration : recopie metrage_prevu â†’ metrage_total_debut et metrage_reel â†’ metrage_total_fin
    # pour les lignes fabrication dÃ©jÃ  existantes (exÃ©cution idempotente grÃ¢ce au WHERE IS NULL)
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

    # Index composites : accÃ©lÃ¨rent les filtres par opÃ©rateur/dossier + date
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

    # GÃ©nÃ©rer identifiant pour les comptes existants si absent.
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
        # "premier mot du champ nom et prenom" â†’ token1.token2
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
        # Ne jamais bloquer le dÃ©marrage sur une migration d'identifiants.
        pass

    # Tables devis â€” crÃ©Ã©es si absentes
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

    # Tables planning â€” crÃ©Ã©es si absentes
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
        conn.execute("INSERT OR IGNORE INTO machines (nom, code) VALUES ('CohÃ©sio 1', 'C1')")

    # Machines par dÃ©faut (compat planning multi-machines)
    # Ne force pas les IDs : s'appuie sur nom/code uniques.
    for nom, code in [
        ("CohÃ©sio 1", "C1"),
        ("CohÃ©sio 2", "C2"),
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
    # Ne pas utiliser `existing_tables` ici : il est figÃ© avant la crÃ©ation Ã©ventuelle de
    # planning_entries ; sinon la table est crÃ©Ã©e sans colonnes v1.2 et les ALTER ne sâ€™exÃ©cutent jamais.
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

            # Best-effort : rÃ©cupÃ©rer ref/client/description depuis dossiers si possible
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
            # RentabilitÃ© v2: groupement split + liaison devis/production
            ("group_id", "ALTER TABLE planning_entries ADD COLUMN group_id TEXT"),
            ("split_parent_id", "ALTER TABLE planning_entries ADD COLUMN split_parent_id INTEGER"),
            # Planning v2: flag "Ã  placer au planning" (0=non, 1=oui â€” zÃ©brÃ© dans liste+timeline)
            ("a_placer", "ALTER TABLE planning_entries ADD COLUMN a_placer INTEGER DEFAULT 0"),
            # Planning v2: destockage (todo/done â€” point gris dans le slot timeline)
            ("destockage", "ALTER TABLE planning_entries ADD COLUMN destockage TEXT DEFAULT 'todo'"),
            # Planning v3: statut rÃ©el issu de la saisie fabrication
            # reellement_en_attente | reellement_en_saisie | reellement_termine
            ("statut_reel", "ALTER TABLE planning_entries ADD COLUMN statut_reel TEXT DEFAULT 'reellement_en_attente'"),
            # Fin de crÃ©neau figÃ©e manuellement (resize timeline) â€” ne pas recalculer depuis la saisie prod
            ("planned_end_manual", "ALTER TABLE planning_entries ADD COLUMN planned_end_manual INTEGER DEFAULT 0"),
            # TraÃ§abilitÃ© crÃ©ation/modification
            ("created_by", "ALTER TABLE planning_entries ADD COLUMN created_by TEXT"),
            ("updated_by", "ALTER TABLE planning_entries ADD COLUMN updated_by TEXT"),
        ]:
            if col not in pe_cols:
                conn.execute(sql)

        # Backfill group_id pour les entrÃ©es existantes (valeur stable et unique par ligne)
        try:
            conn.execute(
                "UPDATE planning_entries SET group_id=CAST(id AS TEXT) WHERE group_id IS NULL OR TRIM(group_id)=''"
            )
        except Exception:
            pass

        # Backfill statut_reel : les dossiers planning marquÃ©s "termine" sont rÃ©ellement terminÃ©s
        try:
            conn.execute(
                """UPDATE planning_entries
                   SET statut_reel='reellement_termine'
                   WHERE statut='termine'
                     AND (statut_reel IS NULL OR statut_reel='reellement_en_attente')"""
            )
        except Exception:
            pass

    # Tables RentabilitÃ© v2 (liens planning -> devis + no_dossier production)
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

    # Jours fÃ©riÃ©s / jours off par machine (standalone planning)
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
            heure_debut REAL NOT NULL,       -- fraction dÃ©cimale (ex: 5.0 = 5h)
            heure_fin   REAL NOT NULL,       -- fraction dÃ©cimale (ex: 13.0 = 13h)
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
            unite TEXT DEFAULT 'Ã©tiquette',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")
    else:
        # Migration: anciens libellÃ©s vides/gÃ©nÃ©riques â†’ "Ã©tiquette"
        try:
            conn.execute(
                """UPDATE produits
                   SET unite='Ã©tiquette'
                   WHERE unite IS NULL
                      OR TRIM(COALESCE(unite,'')) = ''
                      OR LOWER(TRIM(unite)) IN ('unitÃ©','unite','unites','unitÃ©s','u.','u')"""
            )
        except Exception:
            pass

    # Migration: unitÃ©s obsolÃ¨tes (forfait/mille/mille A4) â†’ "Ã©tiquette"
    try:
        conn.execute(
            """UPDATE produits
               SET unite='Ã©tiquette', updated_at=datetime('now')
               WHERE LOWER(TRIM(COALESCE(unite,''))) IN ('forfait','mille','mille a4')"""
        )
    except Exception:
        pass

    # Migration: suppression du "s" final pour stocker les unitÃ©s au singulier
    # (idempotent : aprÃ¨s strip le mot ne se termine plus par "s")
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

    # MyStock v2 â€” lots FIFO + inventaires
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

    # TraÃ§abilitÃ© mouvements MyStock : snapshot du nom (Nom PrÃ©nom) de l'auteur
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

    # â”€â”€ Messagerie interne (contact support â†’ super admin) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
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
        conn.execute("UPDATE machines SET nom='CohÃ©sio 1' WHERE nom='CohÃ©sion 1'")
    except sqlite3.Error:
        pass

    # Migration : colonne dernier_metrage sur machines
    existing_machines = {row[1] for row in conn.execute("PRAGMA table_info(machines)").fetchall()}
    if "dernier_metrage" not in existing_machines:
        conn.execute("ALTER TABLE machines ADD COLUMN dernier_metrage REAL")

    # Tables rÃ©ception matiÃ¨re (bobines)
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

    # TraÃ§abilitÃ© matiÃ¨res utilisÃ©es en fabrication
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
        # InsÃ©rer les fournisseurs par dÃ©faut
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

        # Compte Manuel Lesaffre (configurateur planning RH â€” rÃ´le direction)
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

    # Migration v5 : DÃ©saffecter tout le personnel planning RH (nettoyage avant dÃ©ploiement)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=5 LIMIT 1").fetchone():
        conn.execute("DELETE FROM rh_planning_postes")
        conn.commit()
        _record_schema_migration(conn, 5, "clear_rh_planning_assignments")

    # Migration v6 : Configurer les overrides d'accÃ¨s pour les utilisateurs spÃ©cifiques
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=6 LIMIT 1").fetchone():
        # S'assurer que la colonne access_overrides existe
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "access_overrides" not in existing_columns:
            conn.execute("ALTER TABLE users ADD COLUMN access_overrides TEXT")
            conn.commit()
        
        # Liste des utilisateurs avec leurs overrides d'accÃ¨s
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
                
                # Mettre Ã  jour
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

    # Migration v8 : Tables annonces de mise Ã  jour + acquittements utilisateurs
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=8 LIMIT 1").fetchone():
        conn.execute("""CREATE TABLE IF NOT EXISTS update_announcements (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            scope       TEXT NOT NULL,        -- 'planning', 'fabrication', 'global'
            titre       TEXT NOT NULL,
            message     TEXT NOT NULL,        -- HTML autorisÃ©
            created_at  TEXT NOT NULL,
            created_by  TEXT DEFAULT 'systÃ¨me',
            active      INTEGER DEFAULT 1    -- 0 = archivÃ© (ne plus afficher)
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

        # â”€â”€ Seed : annonces du 30 avril 2026 â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        _planning_msg = (
            "<p style='margin-bottom:14px'>Plusieurs amÃ©liorations ont Ã©tÃ© dÃ©ployÃ©es ce matin sur le planning.</p>"
            "<ul style='margin:10px 0;padding-left:20px;line-height:1.9'>"
            "<li><strong>LisibilitÃ© de la liste</strong> â€” Les dossiers terminÃ©s sont masquÃ©s par dÃ©faut, Ã  l'exception des deux derniers. Un bouton permet de les afficher en totalitÃ© si nÃ©cessaire. La position de dÃ©filement est conservÃ©e aprÃ¨s chaque modification ou rÃ©ordonnancement.</li>"
            "<li><strong>Timeline</strong> â€” Les slots <em>En attente</em> sont dÃ©plaÃ§ables par glisser-dÃ©poser directement sur la barre de temps. Survoler un slot et appuyer sur <kbd style='background:rgba(255,255,255,.12);padding:1px 5px;border-radius:4px;font-family:monospace;font-size:11px'>EntrÃ©e</kbd> ouvre sa fiche d'Ã©dition.</li>"
            "<li><strong>ParamÃ¨tres semaine</strong> â€” Une icÃ´ne âš™ est disponible sur chaque en-tÃªte de semaine pour configurer les jours travaillÃ©s et les horaires spÃ©cifiques, indÃ©pendamment des dÃ©fauts machine.</li>"
            "<li><strong>DurÃ©e rÃ©elle</strong> â€” Ã€ la clÃ´ture d'un dossier, sa durÃ©e plannÃ©e est mise Ã  jour automatiquement d'aprÃ¨s les horodatages rÃ©els de production. Les durÃ©es s'affichent au format <em>5h15</em>.</li>"
            "<li><strong>Statut saisie</strong> â€” La liste et la timeline indiquent si un dossier est en cours de saisie ou rÃ©ellement terminÃ© cÃ´tÃ© opÃ©rateur.</li>"
            "</ul>"
        )
        _fabrication_msg = (
            "<p style='margin-bottom:14px'>Deux changements importants sont en vigueur dÃ¨s aujourd'hui.</p>"
            "<ul style='margin:10px 0;padding-left:20px;line-height:1.9'>"
            "<li><strong>Renommage</strong> â€” Â«&nbsp;DÃ©but dossier&nbsp;Â» et Â«&nbsp;Fin dossier&nbsp;Â» s'appellent dÃ©sormais <strong>DÃ©but de production</strong> et <strong>Fin de production</strong>.</li>"
            "<li><strong>ClÃ´ture de dossier</strong> â€” Lors d'une fin de production, il est obligatoire d'indiquer si le dossier est terminÃ© ou s'il reprend. Cette information alimente directement le planning&nbsp;: ne pas la renseigner correctement faussera la visibilitÃ© de l'Ã©quipe sur les encours.</li>"
            "<li><strong>DurÃ©e plannÃ©e mise Ã  jour automatiquement</strong> â€” Ã€ la clÃ´ture d'un dossier, la durÃ©e dans le planning est recalculÃ©e d'aprÃ¨s le temps rÃ©el de production.</li>"
            "</ul>"
        )

        _seed_ts = "2026-04-30T00:00:00"
        conn.execute(
            "INSERT INTO update_announcements (scope,titre,message,created_at,created_by,active) VALUES (?,?,?,?,?,1)",
            ("planning", "Mise Ã  jour du 30 avril 2026 â€” Planning de production", _planning_msg, _seed_ts, "systÃ¨me"),
        )
        conn.execute(
            "INSERT INTO update_announcements (scope,titre,message,created_at,created_by,active) VALUES (?,?,?,?,?,1)",
            ("fabrication", "Mise Ã  jour du 30 avril 2026 â€” Saisie de production", _fabrication_msg, _seed_ts, "systÃ¨me"),
        )

        conn.commit()
        _record_schema_migration(conn, 8, "update_announcements_tables")

    # Migration v9 : Correctifs planning â€” statut_reel corrompu + dates erronÃ©es
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=9 LIMIT 1").fetchone():
        # Bug 1 : SNV 9931304 marquÃ© "en saisie" par erreur opÃ©rateur
        conn.execute(
            """UPDATE planning_entries
               SET statut_reel = 'reellement_en_attente', updated_at = datetime('now')
               WHERE reference = '9931304'
                 AND statut_reel = 'reellement_en_saisie'"""
        )
        # Bug 2 : NestlÃ© Marconnelle (MarchÃ© 722) â€” planned_start erronÃ© 30/04 au lieu de 04/05
        conn.execute(
            """UPDATE planning_entries
               SET planned_start = '2026-05-04T07:00:00',
                   planned_end   = datetime('2026-05-04T07:00:00', '+' || CAST(duree_heures AS INTEGER) || ' hours'),
                   updated_at    = datetime('now')
               WHERE reference LIKE '%MarchÃ© 722%'
                 AND statut = 'en_cours'"""
        )
        conn.commit()
        _record_schema_migration(conn, 9, "fix_corrupted_statut_reel_and_dates")

    # Migration v10 : traÃ§abilitÃ© code-barre fournisseur (photo + texte)
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

    # Migration v11 : MyDevis â€” paramÃ¨tres matiÃ¨re & base prix
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

    # v12 â€” jours travaillÃ©s par affectation RH (bitmask Lun=bit0â€¦Ven=bit4, Sam=bit5 ; 31=lunâ€“ven, 32=sam)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=12 LIMIT 1").fetchone():
        try:
            conn.execute(
                "ALTER TABLE rh_planning_postes ADD COLUMN jours INTEGER NOT NULL DEFAULT 31"
            )
        except Exception:
            pass  # colonne dÃ©jÃ  prÃ©sente
        conn.commit()
        _record_schema_migration(conn, 12, "rh_planning_postes_jours")

    # v13 â€” MyExpÃ© : suivi des dÃ©parts (exportations)
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

    # v14 â€” ordre des tuiles portail (prÃ©fÃ©rence utilisateur)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=14 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "portal_apps_order" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN portal_apps_order TEXT")
        conn.commit()
        _record_schema_migration(conn, 14, "users_portal_apps_order")

    # v15 â€” base matiÃ¨re : supplÃ©ment Rotoflex par ligne (calcul prix depuis paramÃ¨tres)
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

    # v16 â€” MyDevis : matiere_params.code nullable + base matiÃ¨re groupÃ©e par famille
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=16 LIMIT 1").fetchone():
        try:
            # RecrÃ©er la table sans la contrainte NOT NULL sur code
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

    # v17 â€” base matiÃ¨re : liens directs vers matiere_params (IDs composants)
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

    # v18 â€” TraÃ§a fabrication : liaison scans matiÃ¨res â†” rÃ©ceptions (fournisseur + certificat)
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

    # v19 â€” Profil utilisateur : adresse + date de naissance
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=19 LIMIT 1").fetchone():
        ucols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "adresse" not in ucols:
            conn.execute("ALTER TABLE users ADD COLUMN adresse TEXT")
        if "date_naissance" not in ucols:
            # ISO YYYY-MM-DD
            conn.execute("ALTER TABLE users ADD COLUMN date_naissance TEXT")
        _record_schema_migration(conn, 19, "users_adresse_date_naissance")

    # v20 â€” Planning : commentaires par jour (timeline)
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

    # v21 â€” Planning : date de fin manuelle (override saisie production)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=21 LIMIT 1").fetchone():
        pe_cols = {r["name"] for r in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        if "planned_end_manual" not in pe_cols:
            conn.execute(
                "ALTER TABLE planning_entries ADD COLUMN planned_end_manual INTEGER DEFAULT 0"
            )
        _record_schema_migration(conn, 21, "planning_planned_end_manual")

    # v22 â€” Machines : horaires paire/impaire (JSON) pour la timeline CohÃ©sio 2 et similaires
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=22 LIMIT 1").fetchone():
        mcols = {r["name"] for r in conn.execute("PRAGMA table_info(machines)").fetchall()}
        if "horaires_parity" not in mcols:
            conn.execute("ALTER TABLE machines ADD COLUMN horaires_parity TEXT")
        _record_schema_migration(conn, 22, "machines_horaires_parity")

    # v23 â€” RÃ©fÃ©rentiel codes opÃ©ration (ex operations.json)
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

    # v24 â€” PrÃ©fÃ©rences thÃ¨me utilisateur (palette, style, mode)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=24 LIMIT 1").fetchone():
        ucols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "theme_prefs" not in ucols:
            conn.execute("ALTER TABLE users ADD COLUMN theme_prefs TEXT")
        _record_schema_migration(conn, 24, "users_theme_prefs")

    # v25 â€” Planning : exigences de production par dossier
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=25 LIMIT 1").fetchone():
        pe_cols = {r["name"] for r in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        if "exigences_production" not in pe_cols:
            conn.execute("ALTER TABLE planning_entries ADD COLUMN exigences_production TEXT")
        _record_schema_migration(conn, 25, "planning_exigences_production")

    # v26 â€” Jours fÃ©riÃ©s nationaux 2026 (planning + calendrier)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=26 LIMIT 1").fetchone():
        feries_2026 = [
            ("2026-01-01", "Jour de l'an"),
            ("2026-04-06", "Lundi de PÃ¢ques"),
            ("2026-05-01", "FÃªte du Travail"),
            ("2026-05-08", "Victoire des AlliÃ©s 1945"),
            ("2026-05-14", "Jeudi de l'Ascension"),
            ("2026-05-25", "Lundi de PentecÃ´te"),
            ("2026-07-14", "FÃªte Nationale"),
            ("2026-08-15", "Assomption"),
            ("2026-11-01", "La Toussaint"),
            ("2026-11-11", "Armistice 1918"),
            ("2026-12-25", "NoÃ«l"),
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

    # v27 â€” Plusieurs affectations RH par personne et par semaine (jours partiels multi-postes)
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

    # v28 â€” Ã‰vÃ©nements calendrier personnel (MyCalendrier)
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

    # v29 â€” Journal d'audit (actions sensibles)
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

    # v31 â€” FSC : flag certification requise sur les dossiers planning
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

    # v32 â€” FSC : type de claim sur les rÃ©ceptions de bobines
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=32 LIMIT 1").fetchone():
        sr_cols = {r["name"] for r in conn.execute("PRAGMA table_info(stock_receptions)").fetchall()}
        if "fsc_type_claim" not in sr_cols:
            conn.execute(
                "ALTER TABLE stock_receptions ADD COLUMN fsc_type_claim TEXT DEFAULT 'non_fsc'"
            )
        conn.commit()
        _record_schema_migration(conn, 32, "stock_receptions_fsc_type_claim")

    # v33 â€” FSC : champs alerte sur fab_matieres_utilisees
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

    # v34 â€” Photo de profil utilisateur
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=34 LIMIT 1").fetchone():
        ucols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "avatar_url" not in ucols:
            conn.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
        conn.commit()
        _record_schema_migration(conn, 34, "users_avatar_url")

    # v35 â€” Chat interne (DMs + canaux d'Ã©quipe)
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

    # v36 â€” PiÃ¨ces jointes messagerie
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

    # v37 â€” RÃ©actions emoji sur les messages chat
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

    # v38 â€” Retirer des fÃ©riÃ©s planning les jours off erronÃ©s (18â€“22 mai 2026) ; calendrier = liste nationale
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=38 LIMIT 1").fetchone():
        conn.execute(
            "DELETE FROM planning_holidays WHERE date >= '2026-05-18' AND date <= '2026-05-22'"
        )
        _record_schema_migration(conn, 38, "cleanup_feries_planning_mai_2026")

    # v39 â€” MyExpÃ© : rÃ©fÃ©rentiel transporteurs
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
                tarif_filename TEXT,                    -- nom du fichier uploadÃ©
                tarif_url TEXT,                         -- chemin relatif de stockage
                -- Colonnes ajoutÃ©es par migrations ultÃ©rieures â€” dupliquÃ©es
                -- ici pour que le seed initial (`seed_expe_transporteurs_if_empty`,
                -- appelÃ© dans la mÃªme migration que la CREATE TABLE) fonctionne
                -- sur une DB fraÃ®che Kernse. Les ALTER TABLE plus loin sont
                -- devenus des no-op grÃ¢ce au check `if col not in cols`.
                palette_max INTEGER,                    -- v64
                poids_max_kg REAL,                      -- v64
                accepte_poids INTEGER DEFAULT 1,        -- v64
                accepte_palette INTEGER DEFAULT 1,      -- v64
                couleur TEXT,                           -- v98
                contact_portail_url TEXT,               -- v127
                contact_emails TEXT,                    -- v127
                contact_tels TEXT,                      -- v155
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

    # v40 â€” MatiÃ¨res premiÃ¨res : rÃ©fÃ©rentiel
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

    # v41 â€” MatiÃ¨res premiÃ¨res : stock courant
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

    # v42 â€” MatiÃ¨res premiÃ¨res : historique mouvements
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

    # v43 â€” MyCompta : codes de banque (code vendeur Factor â†’ compte CAF)
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

    # v44 â€” MyExpÃ© : transporteurs historiques (CoupÃ©, Ceva, Coquelle, Dimotrans)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=44 LIMIT 1").fetchone():
        from app.services.expe_transporteurs_seed import seed_expe_transporteurs_if_empty

        seed_expe_transporteurs_if_empty(conn)
        conn.commit()
        _record_schema_migration(conn, 44, "expe_transporteurs_seed")

    # v45 â€” MyAO : demandes
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

    # v46 â€” MyAO : lignes
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=46 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ao_lignes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ao_id       INTEGER NOT NULL REFERENCES ao_demandes(id) ON DELETE CASCADE,
                ref_produit TEXT NOT NULL,
                designation TEXT NOT NULL,
                quantite    REAL NOT NULL,
                unite       TEXT DEFAULT 'unitÃ©',
                notes       TEXT,
                position    INTEGER DEFAULT 0
            )
        """)
        conn.commit()
        _record_schema_migration(conn, 46, "ao_lignes")

    # v47 â€” MyAO : fournisseurs invitÃ©s
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

    # v48 â€” MyAO : rÃ©ponses par ligne
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

    # v49 â€” MyAO : messages portail
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

    # v50 â€” MyAO : piÃ¨ces jointes
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

    # v56 â€” Import OF PDF (MyProd)
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

    # v57 â€” Post-its portail (desktop, par utilisateur)
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

    # v58 â€” Annonces de mise Ã  jour messagerie (chat interne)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=58 LIMIT 1").fetchone():
        _msg_chat_annonce = (
            '<div style="font-size:13px;line-height:1.7;color:var(--text2)">'
            '<div style="font-size:15px;font-weight:700;color:var(--text);margin-bottom:12px">'
            'Mise Ã  jour â€” Messagerie</div>'
            '<div style="margin-bottom:10px;font-weight:600;color:var(--text);font-size:12px;'
            'text-transform:uppercase;letter-spacing:.5px">NouveautÃ©s</div>'
            '<ul style="margin:0 0 14px 0;padding-left:18px">'
            '<li style="margin-bottom:5px">Envoi de GIFs â€” bouton + dans la barre de saisie, puis GIF.</li>'
            '<li style="margin-bottom:5px">Mentions â€” taper @ pour taguer un collÃ¨gue. @tous pour tout le canal.</li>'
            '<li style="margin-bottom:5px">Notifications navigateur â€” demande d\'activation au premier usage.</li>'
            '<li style="margin-bottom:5px">Emoji de canal â€” les administrateurs peuvent personnaliser l\'icÃ´ne depuis les rÃ©glages du canal.</li>'
            '<li style="margin-bottom:5px">RÃ©actions emoji sur les messages.</li>'
            '<li style="margin-bottom:5px">Modification d\'un message (15 min, texte seul).</li>'
            '<li style="margin-bottom:5px">Ã‰pinglage de messages â€” bouton dans l\'en-tÃªte du canal.</li>'
            '</ul>'
            '<div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border);'
            'font-size:11px;color:var(--muted);line-height:1.6">'
            'Dans l\'optique d\'amÃ©liorer constamment l\'outil, vos retours sont les bienvenus.<br>'
            'Merci de votre confiance.<br>'
            '<span style="color:var(--text2);font-weight:600">EugÃ¨ne</span></div></div>'
        )
        _seed_ts = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        exists = conn.execute(
            "SELECT 1 FROM update_announcements WHERE scope=? AND titre=? LIMIT 1",
            ("messages", "Messagerie â€” GIFs, mentions et notifications"),
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO update_announcements (scope,titre,message,created_at,created_by,active) VALUES (?,?,?,?,?,1)",
                (
                    "messages",
                    "Messagerie â€” GIFs, mentions et notifications",
                    _msg_chat_annonce,
                    _seed_ts,
                    "systÃ¨me",
                ),
            )
        conn.commit()
        _record_schema_migration(conn, 58, "update_announcements_messages_chat")

    # v59 â€” Post-its visibles sur toutes les pages (option multi-page)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=59 LIMIT 1").fetchone():
        conn.execute(
            "ALTER TABLE postits ADD COLUMN multi_page INTEGER NOT NULL DEFAULT 0"
        )
        conn.commit()
        _record_schema_migration(conn, 59, "postits_multi_page")

    # v60 â€” MatiÃ¨res premiÃ¨res : piles (palettes) et palettes (cartons)
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

    # v61 â€” Post-its rÃ©duits en barre en bas de l'Ã©cran
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=61 LIMIT 1").fetchone():
        conn.execute(
            "ALTER TABLE postits ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0"
        )
        conn.commit()
        _record_schema_migration(conn, 61, "postits_hidden")

    # v62 â€” Post-its : couleur personnalisable (pastille)
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

    # v63 â€” MyExpÃ© : FK transporteur sur dÃ©parts
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=63 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_departs)").fetchall()}
        if "transporteur_id" not in cols:
            conn.execute(
                "ALTER TABLE expe_departs ADD COLUMN transporteur_id INTEGER REFERENCES expe_transporteurs(id)"
            )
        conn.commit()
        _record_schema_migration(conn, 63, "expe_departs_transporteur_fk")

    # v64 â€” MyExpÃ© : capacitÃ©s transporteurs (comparateur)
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

    # v65 â€” MyExpÃ© : grilles tarifaires structurÃ©es
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

    # v66 â€” MyExpÃ© : demandes de devis (prospection parallÃ¨le)
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

    # v67 â€” MyExpÃ© : transporteurs prospects
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

    # v68 â€” MyExpÃ© : dÃ©lais carte France (base partagÃ©e, remplace localStorage)
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

    # v69 â€” MyAO : carnet fournisseurs rÃ©currents
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

    # v70 â€” MyAO : catalogue produits rÃ©currents
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=70 LIMIT 1").fetchone():
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ao_produits (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ref         TEXT NOT NULL,
                designation TEXT NOT NULL,
                unite       TEXT DEFAULT 'unitÃ©',
                notes       TEXT,
                created_at  TEXT NOT NULL
            )
            """
        )
        conn.commit()
        _record_schema_migration(conn, 70, "ao_produits")

    # v71 â€” Liaison OF â†’ planning_entries
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=71 LIMIT 1").fetchone():
        pe_cols = {row[1] for row in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        if "of_import_id" not in pe_cols:
            conn.execute(
                "ALTER TABLE planning_entries ADD COLUMN of_import_id INTEGER"
            )
        conn.commit()
        _record_schema_migration(conn, 71, "planning_entries_of_import_link")

    # v72 â€” MyAO : carnet clients rÃ©currents
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

    # v73 â€” MyAO : fiche produit complÃ¨te (JSON + client)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=73 LIMIT 1").fetchone():
        ap_cols = {row[1] for row in conn.execute("PRAGMA table_info(ao_produits)").fetchall()}
        if "client_id" not in ap_cols:
            conn.execute("ALTER TABLE ao_produits ADD COLUMN client_id INTEGER")
        if "fiche_json" not in ap_cols:
            conn.execute("ALTER TABLE ao_produits ADD COLUMN fiche_json TEXT")
        conn.commit()
        _record_schema_migration(conn, 73, "ao_produits_fiche")

    # v74 â€” MatiÃ¨res premiÃ¨res : frontal, glassine (+ couleur)
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

    # v75 â€” MyAO : carnet fournisseurs â€” sociÃ©tÃ© et adresse
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=75 LIMIT 1").fetchone():
        cf_cols = {row[1] for row in conn.execute("PRAGMA table_info(ao_carnet_fournisseurs)").fetchall()}
        if "societe" not in cf_cols:
            conn.execute("ALTER TABLE ao_carnet_fournisseurs ADD COLUMN societe TEXT")
        if "adresse" not in cf_cols:
            conn.execute("ALTER TABLE ao_carnet_fournisseurs ADD COLUMN adresse TEXT")
        conn.commit()
        _record_schema_migration(conn, 75, "ao_carnet_fournisseurs_societe_adresse")

    # v77 â€” MyAO : rÃ©fÃ©rence produit unique (insensible Ã  la casse)
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

    # v76 â€” MyExpÃ© : type de palette (rÃ©f. matiÃ¨res premiÃ¨res MyStock)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=76 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_departs)").fetchall()}
        if "type_palette_matiere_id" not in cols:
            conn.execute(
                "ALTER TABLE expe_departs ADD COLUMN type_palette_matiere_id INTEGER "
                "REFERENCES matieres_premieres(id)"
            )
        conn.commit()
        _record_schema_migration(conn, 76, "expe_departs_type_palette")

    # v78 â€” Calcul coÃ»ts matiÃ¨res (remplace Excel / schÃ©ma distinct de MyDevis matiere_*)
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
                ("ADHESIF", "AdhÃ©sif", 2),
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

    # v79 â€” CoÃ»ts matiÃ¨res : source du taux FX sur mc_setting
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=79 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(mc_setting)").fetchall()}
        if "source" not in cols:
            conn.execute("ALTER TABLE mc_setting ADD COLUMN source TEXT")
        conn.commit()
        _record_schema_migration(conn, 79, "mc_setting_fx_source")

    # v80 â€” AccÃ¨s applicatif MyDevis (devis) â†’ pricing
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

    # v81 â€” CoÃ»ts matiÃ¨res : accÃ¨s rÃ©servÃ© Direction et super admin (retrait Administration)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=81 LIMIT 1").fetchone():
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

    # v82 â€” MyStock : produits finis (catalogue + mouvements)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=82 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS produits_finis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT NOT NULL UNIQUE,
                designation TEXT NOT NULL,
                unite TEXT DEFAULT 'piÃ¨ces',
                created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS pf_mouvements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reference TEXT NOT NULL,
                designation TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('entree', 'sortie')),
                quantite REAL NOT NULL,
                unite TEXT DEFAULT 'piÃ¨ces',
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

    # v83 â€” MyAO : quotation, devise, unitÃ© et coef sur les rÃ©ponses fournisseur
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

    # v84 â€” planning_entries : dÃ©partement livraison et prise de RDV
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

    # v85 â€” MyExpÃ© : portail transporteur (rÃ©ponses en ligne)
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

    # v86 â€” MyStock Monitoring : rÃ©conciliation stocks PF ERP vs MySifa
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

    # v87 â€” Tableaux de bord : rÃ©fÃ©rentiel crÃ©Ã© par le superadmin
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

    # v88 â€” Tableaux de bord : association utilisateur â†” dashboard
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

    # v89 â€” Table des clÃ©s API (pont Access â†” MySifa)
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

    # v90 â€” Fiches techniques produits
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=90 LIMIT 1").fetchone():
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS fiches_techniques (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                reference    TEXT NOT NULL,
                designation  TEXT,
                client       TEXT,
                format       TEXT,
                laize        REAL,
                matiere      TEXT,
                adhesif      TEXT,
                nb_couleurs  INTEGER,
                conditionnement TEXT,
                notes        TEXT,
                source       TEXT DEFAULT 'manuel',
                date_import  TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                imported_by  TEXT
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_fiches_ref ON fiches_techniques(reference COLLATE NOCASE);
        """)
        conn.commit()
        _record_schema_migration(conn, 90, "fiches_techniques")

    # v91 â€” Humeur utilisateur (indicateur quotidien)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=91 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "humeur_active" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN humeur_active INTEGER NOT NULL DEFAULT 0")
        if "humeur_valeur" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN humeur_valeur TEXT")
        if "humeur_date" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN humeur_date TEXT")
        conn.commit()
        _record_schema_migration(conn, 91, "users_humeur")

    # v92 â€” MyBAT : gestion des Bons Ã€ Tirer
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=92 LIMIT 1").fetchone():
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bat_entries (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_client   TEXT NOT NULL,
                numero_article  TEXT NOT NULL,
                statut          TEXT NOT NULL DEFAULT 'a_faire',
                pdf_path        TEXT,
                notes           TEXT,
                created_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                updated_at      TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                created_by      INTEGER REFERENCES users(id),
                updated_by      INTEGER REFERENCES users(id),
                UNIQUE(numero_client, numero_article)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_bat_statut ON bat_entries(statut)"
        )
        conn.commit()
        _record_schema_migration(conn, 92, "bat_entries")

    # v93 â€” MyBAT : renommage numero_clientâ†’description + ajout delai_client
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=93 LIMIT 1").fetchone():
        try:
            conn.execute("ALTER TABLE bat_entries RENAME COLUMN numero_client TO description")
        except Exception:
            pass
        try:
            conn.execute("ALTER TABLE bat_entries ADD COLUMN delai_client TEXT")
        except Exception:
            pass
        conn.commit()
        _record_schema_migration(conn, 93, "bat_entries_v2")

    # v94 â€” fiches_techniques : colonnes Ã©tendues depuis Access
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=94 LIMIT 1").fetchone():
        cols_to_add = [
            # Ã‰tiquette
            ("eti_laize",          "REAL"),
            ("eti_longueur",       "REAL"),
            ("eti_rayons",         "REAL"),
            ("eti_perforations",   "TEXT"),
            # Module
            ("mod_laize",          "REAL"),
            ("mod_longueur",       "REAL"),
            ("mod_nb_front",       "INTEGER"),
            # Ã‰chenillage
            ("lateral_ext",        "REAL"),
            ("horizontal",         "REAL"),
            ("lateral_int",        "REAL"),
            # Outil 1
            ("outil1_forme",       "TEXT"),
            ("outil1_numero_sifa", "TEXT"),
            ("outil1_laize",       "REAL"),
            ("machine",            "TEXT"),
            ("outil1_epaisseur",   "REAL"),
            ("outil1_nb_dents",    "INTEGER"),
            ("outil1_nb_front",    "INTEGER"),
            ("outil1_nb_avance",   "INTEGER"),
            # Outil 2
            ("outil2_forme",       "TEXT"),
            ("outil2_numero_sifa", "TEXT"),
            ("outil2_epaisseur",   "REAL"),
            ("outil2_nb_dents",    "INTEGER"),
            ("outil2_nb_front",    "INTEGER"),
            ("outil2_nb_avance",   "INTEGER"),
            # Outil 3
            ("outil3_forme",       "TEXT"),
            ("outil3_numero_sifa", "TEXT"),
            ("outil3_epaisseur",   "REAL"),
            ("outil3_nb_dents",    "INTEGER"),
            ("outil3_nb_front",    "INTEGER"),
            ("outil3_nb_avance",   "INTEGER"),
            # MatiÃ¨re
            ("support",            "TEXT"),
            ("glassine",           "TEXT"),
            ("laize_optimale",     "REAL"),
            ("laize_optionnelle",  "REAL"),
            ("epaisseur",          "REAL"),
            ("qte_au_mille",       "REAL"),
            ("date_modif",         "TEXT"),
            # Impression
            ("nb_couleurs",        "INTEGER"),
            ("recto",              "INTEGER"),
            ("verso",              "INTEGER"),
            ("tete1_pantone",      "TEXT"),
            ("tete1_couleur",      "TEXT"),
            ("tete1_anilox",       "TEXT"),
            ("tete1_composition",  "TEXT"),
            ("tete2_pantone",      "TEXT"),
            ("tete2_couleur",      "TEXT"),
            ("tete2_anilox",       "TEXT"),
            ("tete2_composition",  "TEXT"),
            ("tete3_pantone",      "TEXT"),
            ("tete3_couleur",      "TEXT"),
            ("tete3_anilox",       "TEXT"),
            ("tete3_composition",  "TEXT"),
            ("remarque",           "TEXT"),
            # Conditionnement
            ("mandrin_dia",        "TEXT"),
            ("mandrin_longueur",   "REAL"),
            ("enroulement",        "TEXT"),
            ("nb_etiq_bobin",      "INTEGER"),
            ("dia_ext",            "REAL"),
            ("poids",              "REAL"),
            ("cales_sachets",      "TEXT"),
            ("cartons",            "TEXT"),
            ("nb_au_sol",          "INTEGER"),
            ("nb_etage",           "INTEGER"),
            ("nb_bobines_carton",  "INTEGER"),
            # Palettisation
            ("palette_type",              "TEXT"),
            ("palette_nb_cartons_sol",    "INTEGER"),
            ("palette_nb_cartons_hauteur","INTEGER"),
            ("palette_hauteur_max",       "REAL"),
            ("particularite",             "TEXT"),
        ]
        existing_cols = {r["name"] for r in conn.execute("PRAGMA table_info(fiches_techniques)").fetchall()}
        for col_name, col_type in cols_to_add:
            if col_name not in existing_cols:
                try:
                    conn.execute(f"ALTER TABLE fiches_techniques ADD COLUMN {col_name} {col_type}")
                except Exception:
                    pass
        conn.commit()
        _record_schema_migration(conn, 94, "fiches_techniques_extended")

    # v95 â€” MyStock : sessions d'inventaire par emplacement (outil inventaire v2)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=95 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS inventaires_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emplacement TEXT NOT NULL,
                operateur_email TEXT,
                operateur_nom TEXT,
                date_validation TEXT NOT NULL,
                nb_produits INTEGER DEFAULT 0,
                nb_modifications INTEGER DEFAULT 0,
                modifications_json TEXT
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_inv_sessions_empl ON inventaires_sessions(emplacement, date_validation DESC)"
        )
        conn.commit()
        _record_schema_migration(conn, 95, "inventaires_sessions")

    # v96 â€” expe_transporteurs : couleur personnalisÃ©e
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=96 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_transporteurs)").fetchall()}
        if "couleur" not in cols:
            conn.execute("ALTER TABLE expe_transporteurs ADD COLUMN couleur TEXT")
        conn.commit()
        _record_schema_migration(conn, 96, "expe_transporteurs_couleur")

    # v97 â€” MyStock : produits de nÃ©goce (type sur produits)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=97 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(produits)").fetchall()}
        if "type" not in cols:
            conn.execute("ALTER TABLE produits ADD COLUMN type TEXT NOT NULL DEFAULT 'fabrique'")
        conn.commit()
        _record_schema_migration(conn, 97, "produits_type_negoce")

    # v98 â€” Chat : reply, forward, soft-delete visible
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=98 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(chat_messages)").fetchall()}
        if "reply_to_id" not in cols:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN reply_to_id INTEGER DEFAULT NULL")
        if "is_forwarded" not in cols:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN is_forwarded INTEGER NOT NULL DEFAULT 0")
        if "forwarded_from_nom" not in cols:
            conn.execute("ALTER TABLE chat_messages ADD COLUMN forwarded_from_nom TEXT DEFAULT NULL")
        conn.commit()
        _record_schema_migration(conn, 98, "chat_messages_reply_forward")

    # v99 â€” MyExpÃ© : type_colis pour les envois sans palette (ex: vrac / UPS)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=99 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_departs)").fetchall()}
        if "type_colis" not in cols:
            conn.execute("ALTER TABLE expe_departs ADD COLUMN type_colis TEXT DEFAULT NULL")
        conn.commit()
        _record_schema_migration(conn, 99, "expe_departs_type_colis")

    # v100 â€” Notifications push (Web Push / VAPID)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=100 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                endpoint    TEXT NOT NULL UNIQUE,
                p256dh      TEXT NOT NULL,
                auth        TEXT NOT NULL,
                user_agent  TEXT,
                created_at  TEXT NOT NULL,
                last_used_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_push_subs_user ON push_subscriptions(user_id);
            """
        )
        conn.commit()
        _record_schema_migration(conn, 100, "push_subscriptions")

    # v101 â€” fiches_techniques + planning_entries : clÃ© produit normalisÃ©e
    # Permet la jointure planning_entries.ref_produit â†” fiches_techniques
    # sans dÃ©pendre du libellÃ© textuel ni de la variante (machine, laize,
    # conditionnement) saisie aprÃ¨s le tiret. Trois dimensions extraites du
    # libellÃ© historique des fiches : machine, laize_mm, conditionnement_norm.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=101 LIMIT 1").fetchone():
        ft_cols = {r["name"] for r in conn.execute("PRAGMA table_info(fiches_techniques)").fetchall()}
        if "ref_produit_norm" not in ft_cols:
            conn.execute("ALTER TABLE fiches_techniques ADD COLUMN ref_produit_norm TEXT")
        if "laize_mm" not in ft_cols:
            conn.execute("ALTER TABLE fiches_techniques ADD COLUMN laize_mm INTEGER")
        if "conditionnement_norm" not in ft_cols:
            conn.execute("ALTER TABLE fiches_techniques ADD COLUMN conditionnement_norm TEXT")
        # NB: la colonne `machine` existe dÃ©jÃ  depuis v94 â€” on la rÃ©utilise.

        pe_cols = {r["name"] for r in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        if "ref_produit_norm" not in pe_cols:
            conn.execute("ALTER TABLE planning_entries ADD COLUMN ref_produit_norm TEXT")

        # Backfill via le parser. Sans Ã©craser les valeurs renseignÃ©es Ã  la main
        # (machine, conditionnement) ; on remplit seulement les cases vides.
        try:
            from app.services.fiche_ref_parser import (
                parse_fiche_reference,
                normalize_ref_produit,
            )
        except Exception:
            parse_fiche_reference = None
            normalize_ref_produit = None

        if parse_fiche_reference is not None:
            rows = conn.execute(
                "SELECT id, reference, machine, laize, conditionnement "
                "FROM fiches_techniques"
            ).fetchall()
            for row in rows:
                parsed = parse_fiche_reference(row["reference"])
                updates = {}
                if parsed.get("ref_produit_norm"):
                    updates["ref_produit_norm"] = parsed["ref_produit_norm"]
                if parsed.get("machine") and not (row["machine"] or "").strip():
                    updates["machine"] = parsed["machine"]
                if parsed.get("laize_mm"):
                    updates["laize_mm"] = parsed["laize_mm"]
                if parsed.get("conditionnement_norm") and not (
                    (row["conditionnement"] or "").strip()
                ):
                    updates["conditionnement_norm"] = parsed["conditionnement_norm"]
                if updates:
                    conn.execute(
                        f"UPDATE fiches_techniques "
                        f"SET {', '.join(f'{k}=?' for k in updates)} WHERE id=?",
                        list(updates.values()) + [row["id"]],
                    )

        if normalize_ref_produit is not None:
            pe_rows = conn.execute(
                "SELECT id, ref_produit FROM planning_entries "
                "WHERE ref_produit IS NOT NULL AND TRIM(ref_produit) != ''"
            ).fetchall()
            for row in pe_rows:
                norm = normalize_ref_produit(row["ref_produit"])
                if norm:
                    conn.execute(
                        "UPDATE planning_entries SET ref_produit_norm=? WHERE id=?",
                        (norm, row["id"]),
                    )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_fiches_ref_produit_norm "
            "ON fiches_techniques(ref_produit_norm)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_planning_entries_ref_produit_norm "
            "ON planning_entries(ref_produit_norm)"
        )

        # Triggers : maintiennent ref_produit_norm Ã  jour automatiquement
        # Ã  chaque INSERT/UPDATE, sans devoir patcher tous les endpoints.
        # S'appuient sur la fonction Python `norm_ref_produit()` enregistrÃ©e
        # Ã  chaque ouverture de connexion (cf. _register_udfs).
        conn.executescript("""
            DROP TRIGGER IF EXISTS trg_pe_ref_produit_norm_ins;
            CREATE TRIGGER trg_pe_ref_produit_norm_ins
            AFTER INSERT ON planning_entries
            WHEN NEW.ref_produit IS NOT NULL AND TRIM(NEW.ref_produit) != ''
            BEGIN
                UPDATE planning_entries
                   SET ref_produit_norm = norm_ref_produit(NEW.ref_produit)
                 WHERE id = NEW.id
                   AND (ref_produit_norm IS NULL OR ref_produit_norm = '');
            END;

            DROP TRIGGER IF EXISTS trg_pe_ref_produit_norm_upd;
            CREATE TRIGGER trg_pe_ref_produit_norm_upd
            AFTER UPDATE OF ref_produit ON planning_entries
            BEGIN
                UPDATE planning_entries
                   SET ref_produit_norm = norm_ref_produit(NEW.ref_produit)
                 WHERE id = NEW.id;
            END;

            DROP TRIGGER IF EXISTS trg_ft_ref_produit_norm_ins;
            CREATE TRIGGER trg_ft_ref_produit_norm_ins
            AFTER INSERT ON fiches_techniques
            WHEN NEW.reference IS NOT NULL AND TRIM(NEW.reference) != ''
            BEGIN
                UPDATE fiches_techniques
                   SET ref_produit_norm = norm_ref_produit(NEW.reference)
                 WHERE id = NEW.id
                   AND (ref_produit_norm IS NULL OR ref_produit_norm = '');
            END;

            DROP TRIGGER IF EXISTS trg_ft_ref_produit_norm_upd;
            CREATE TRIGGER trg_ft_ref_produit_norm_upd
            AFTER UPDATE OF reference ON fiches_techniques
            BEGIN
                UPDATE fiches_techniques
                   SET ref_produit_norm = norm_ref_produit(NEW.reference)
                 WHERE id = NEW.id;
            END;
        """)
        conn.commit()
        _record_schema_migration(conn, 101, "fiches_techniques_ref_produit_norm")

    # v102 â€” MyStock : commentaires par produit dans les sessions d'inventaire
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=102 LIMIT 1").fetchone():
        existing = {r["name"] for r in conn.execute("PRAGMA table_info(inventaires_sessions)").fetchall()}
        if "commentaires_json" not in existing:
            try:
                conn.execute("ALTER TABLE inventaires_sessions ADD COLUMN commentaires_json TEXT")
            except Exception:
                pass
        conn.commit()
        _record_schema_migration(conn, 102, "inventaires_sessions_commentaires")

    # v103 â€” ParamÃ¨tres : rÃ©fÃ©rentiel Clients (ERP)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=103 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS clients (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                numero          INTEGER,
                code            TEXT,
                raison_sociale  TEXT NOT NULL,
                adresse1        TEXT,
                adresse2        TEXT,
                bp              TEXT,
                cp              TEXT,
                ville           TEXT,
                code_pays       TEXT,
                pays            TEXT,
                groupe          TEXT,
                siret           TEXT,
                rcs             TEXT,
                tva             TEXT,
                ean             TEXT,
                nif             TEXT,
                telephone       TEXT,
                telecopie       TEXT,
                email           TEXT,
                representant    TEXT,
                adv             TEXT,
                categorie1      TEXT,
                categorie2      TEXT,
                categorie3      TEXT,
                mode_livraison  TEXT,
                mode_reglement  TEXT,
                devise          TEXT,
                encours_autorise REAL,
                code_comptable  TEXT,
                etat            TEXT NOT NULL DEFAULT 'Normal',
                contact_nom     TEXT,
                contact_fonction TEXT,
                contact_email   TEXT,
                contact_tel     TEXT,
                notes           TEXT,
                date_creation   TEXT,
                date_modification TEXT,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_clients_code ON clients(code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_clients_raison ON clients(raison_sociale)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_clients_etat ON clients(etat)")
        conn.commit()
        _record_schema_migration(conn, 103, "clients_referentiel")

    # v104 â€” MyAO : langue prÃ©fÃ©rÃ©e des fournisseurs (FR/EN) pour les invitations
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=104 LIMIT 1").fetchone():
        af_cols = {row[1] for row in conn.execute("PRAGMA table_info(ao_fournisseurs)").fetchall()}
        if "langue" not in af_cols:
            try:
                conn.execute("ALTER TABLE ao_fournisseurs ADD COLUMN langue TEXT DEFAULT 'fr'")
            except Exception:
                pass
        carnet_cols = {row[1] for row in conn.execute("PRAGMA table_info(ao_carnet_fournisseurs)").fetchall()}
        if "langue" not in carnet_cols:
            try:
                conn.execute("ALTER TABLE ao_carnet_fournisseurs ADD COLUMN langue TEXT DEFAULT 'fr'")
            except Exception:
                pass
        conn.commit()
        _record_schema_migration(conn, 104, "ao_fournisseurs_langue")

    # v105 â€” MyBAT : table bat_pdfs (multi-PDF par entrÃ©e)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=105 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bat_pdfs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bat_id INTEGER NOT NULL REFERENCES bat_entries(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL,
                uploaded_at TEXT NOT NULL,
                uploaded_by INTEGER
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_bat_pdfs_bat ON bat_pdfs(bat_id)")
        # Migrer les pdf_path existants
        try:
            existing = conn.execute(
                "SELECT id, pdf_path, updated_at, updated_by FROM bat_entries WHERE pdf_path IS NOT NULL AND pdf_path != ''"
            ).fetchall()
            for row in existing:
                conn.execute(
                    "INSERT OR IGNORE INTO bat_pdfs (bat_id, filename, original_name, uploaded_at, uploaded_by) VALUES (?, ?, ?, ?, ?)",
                    (row[0], row[1], row[1], row[2] or datetime.now().strftime("%Y-%m-%dT%H:%M:%S"), row[3]),
                )
        except Exception:
            pass
        conn.commit()
        _record_schema_migration(conn, 105, "bat_pdfs_multi")

    # v106 â€” Module QualitÃ© : NC (non-conformitÃ©s), fichiers et messages
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=106 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nc_dossiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT NOT NULL UNIQUE,
                numero_ar TEXT,
                numero_historique TEXT,
                type_nc TEXT NOT NULL DEFAULT 'interne',
                gravite TEXT NOT NULL DEFAULT 'mineure',
                statut TEXT NOT NULL DEFAULT 'ouverte',
                titre TEXT NOT NULL,
                date_nc TEXT,
                service_concerne TEXT,
                emetteur_id INTEGER REFERENCES users(id),
                client_fournisseur TEXT,
                ref_client TEXT,
                no_dossier TEXT,
                descriptif_produit TEXT,
                quantite_concernee TEXT,
                description TEXT,
                services_impliques TEXT,
                analyse_causes TEXT,
                action_corrective TEXT,
                action_preventive TEXT,
                pilote_id INTEGER REFERENCES users(id),
                delai_cible TEXT,
                cout_estime REAL,
                date_cloture TEXT,
                validation_qualite_id INTEGER REFERENCES users(id),
                validation_qualite_at TEXT,
                validation_industrielle_id INTEGER REFERENCES users(id),
                validation_industrielle_at TEXT,
                created_at TEXT NOT NULL,
                created_by INTEGER REFERENCES users(id),
                updated_at TEXT NOT NULL,
                updated_by INTEGER REFERENCES users(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nc_statut ON nc_dossiers(statut)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nc_type ON nc_dossiers(type_nc)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nc_numero ON nc_dossiers(numero)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nc_dossier ON nc_dossiers(no_dossier)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nc_pilote ON nc_dossiers(pilote_id)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS nc_fichiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nc_id INTEGER NOT NULL REFERENCES nc_dossiers(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER,
                uploaded_at TEXT NOT NULL,
                uploaded_by INTEGER REFERENCES users(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nc_fichiers_nc ON nc_fichiers(nc_id)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS nc_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nc_id INTEGER NOT NULL REFERENCES nc_dossiers(id) ON DELETE CASCADE,
                author_id INTEGER REFERENCES users(id),
                body TEXT NOT NULL,
                attachment_id INTEGER REFERENCES nc_fichiers(id) ON DELETE SET NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nc_messages_nc ON nc_messages(nc_id, created_at)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS nc_message_reads (
                user_id INTEGER NOT NULL REFERENCES users(id),
                nc_id INTEGER NOT NULL REFERENCES nc_dossiers(id) ON DELETE CASCADE,
                last_read_message_id INTEGER,
                last_read_at TEXT NOT NULL,
                PRIMARY KEY (user_id, nc_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_nc_reads_user ON nc_message_reads(user_id)")

        conn.commit()
        _record_schema_migration(conn, 106, "qualite_non_conformites")

        # v107 â€” planning_entries : date de livraison imposÃ©e (affichage rouge dans la timeline)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=107 LIMIT 1").fetchone():
        pe_cols = {row[1] for row in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        if "date_livraison_imposee" not in pe_cols:
            conn.execute(
                "ALTER TABLE planning_entries ADD COLUMN date_livraison_imposee INTEGER DEFAULT 0"
            )
        conn.commit()
        _record_schema_migration(conn, 107, "planning_entries_date_livraison_imposee")

    # v109 â€” flag of_link_user_managed sur planning_entries
    # Ã‰vite que get_of_for_planning_entry re-crÃ©e automatiquement un lien
    # OF que l'utilisateur vient de retirer manuellement. Le flag est mis
    # Ã  1 par les endpoints POST/DELETE sur planning_of_links et
    # link-planning-of.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=109 LIMIT 1").fetchone():
        pe_cols = {row[1] for row in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        if "of_link_user_managed" not in pe_cols:
            conn.execute(
                "ALTER TABLE planning_entries ADD COLUMN of_link_user_managed INTEGER DEFAULT 0"
            )
        conn.commit()
        _record_schema_migration(conn, 109, "planning_entries_of_link_user_managed")

    # v108 â€” multi-OF par planning_entry : table de jonction planning_of_links
    # Un dossier de production peut Ãªtre liÃ© Ã  plusieurs OF (lots, plages,
    # reliquats). La colonne planning_entries.of_import_id reste maintenue
    # par triggers (= premier lien FIFO) pour la rÃ©trocompat du code existant ;
    # les nouvelles Ã©critures passent par planning_of_links.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=108 LIMIT 1").fetchone():
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS planning_of_links (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                planning_entry_id   INTEGER NOT NULL,
                of_import_id        INTEGER NOT NULL,
                position            INTEGER DEFAULT 0,
                created_by          TEXT,
                created_at          TEXT,
                UNIQUE(planning_entry_id, of_import_id),
                FOREIGN KEY (planning_entry_id) REFERENCES planning_entries(id) ON DELETE CASCADE,
                FOREIGN KEY (of_import_id)      REFERENCES of_imports(id)      ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_planning_of_links_planning
              ON planning_of_links(planning_entry_id);
            CREATE INDEX IF NOT EXISTS idx_planning_of_links_of
              ON planning_of_links(of_import_id);
            """
        )

        # Backfill : reprend les liens existants dans planning_entries.of_import_id
        now_iso = datetime.now().isoformat(timespec="seconds")
        conn.execute(
            """INSERT OR IGNORE INTO planning_of_links
               (planning_entry_id, of_import_id, position, created_by, created_at)
               SELECT id, of_import_id, 0, 'migration_v108', ?
               FROM planning_entries
               WHERE of_import_id IS NOT NULL""",
            (now_iso,),
        )

        # Triggers de synchronisation : la colonne of_import_id reflÃ¨te
        # automatiquement le premier lien (ordre position ASC, id ASC).
        # Permet au code legacy (page planning, traceabilitÃ©, saisie) de
        # continuer Ã  lire of_import_id sans rien savoir du multi.
        conn.executescript(
            """
            DROP TRIGGER IF EXISTS trg_planning_of_links_after_insert;
            CREATE TRIGGER trg_planning_of_links_after_insert
            AFTER INSERT ON planning_of_links
            BEGIN
                UPDATE planning_entries
                   SET of_import_id = (
                     SELECT of_import_id FROM planning_of_links
                     WHERE planning_entry_id = NEW.planning_entry_id
                     ORDER BY position ASC, id ASC
                     LIMIT 1
                   )
                 WHERE id = NEW.planning_entry_id;
            END;

            DROP TRIGGER IF EXISTS trg_planning_of_links_after_delete;
            CREATE TRIGGER trg_planning_of_links_after_delete
            AFTER DELETE ON planning_of_links
            BEGIN
                UPDATE planning_entries
                   SET of_import_id = (
                     SELECT of_import_id FROM planning_of_links
                     WHERE planning_entry_id = OLD.planning_entry_id
                     ORDER BY position ASC, id ASC
                     LIMIT 1
                   )
                 WHERE id = OLD.planning_entry_id;
            END;
            """
        )
        conn.commit()
        _record_schema_migration(conn, 108, "planning_of_links_multi")

    # v110 â€” flag valide sur planning_entries
    # Un dossier n'est plus zÃ©brÃ© (Â« Ã  placer / non finalisÃ© Â») que lorsqu'il est
    # Ã  la fois placÃ© (a_placer=0) ET validÃ© (valide=1). Les dossiers dÃ©jÃ  placÃ©s
    # avant cette migration sont considÃ©rÃ©s validÃ©s pour ne pas les faire basculer
    # en zÃ©brÃ© rÃ©troactivement ; les dossiers encore Â« Ã  placer Â» restent Ã  valider.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=110 LIMIT 1").fetchone():
        pe_cols = {row[1] for row in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        if "valide" not in pe_cols:
            conn.execute(
                "ALTER TABLE planning_entries ADD COLUMN valide INTEGER DEFAULT 0"
            )
        conn.execute(
            "UPDATE planning_entries SET valide=1 WHERE COALESCE(a_placer,0)=0"
        )
        conn.commit()
        _record_schema_migration(conn, 110, "planning_entries_valide")

    # v111 â€” MyExpÃ© : lien dÃ©part â†” dossier planning + suivi palettes Europe
    # - planning_entry_id : trace le dossier de production source quand un dÃ©part
    #   est crÃ©Ã© via le picker "Depuis un dossier" dans Ajouter dÃ©part.
    # - palette_europe (0/1) : marque ce dÃ©part comme expÃ©dition de palettes Europe
    #   (consignÃ©es). Auto Ã  1 si la rÃ©f MyStock palette a is_europe=1.
    # - palette_europe_statut : 'en_attente' (par dÃ©faut), 'retournee' ou 'perdue'.
    # - palette_europe_date_retour : YYYY-MM-DD, optionnelle.
    # - palette_europe_note : commentaire libre (raison de perte, nÂ° BL retourâ€¦).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=111 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_departs)").fetchall()}
        if "planning_entry_id" not in cols:
            conn.execute(
                "ALTER TABLE expe_departs ADD COLUMN planning_entry_id INTEGER "
                "REFERENCES planning_entries(id)"
            )
        if "palette_europe" not in cols:
            conn.execute(
                "ALTER TABLE expe_departs ADD COLUMN palette_europe INTEGER NOT NULL DEFAULT 0"
            )
        if "palette_europe_statut" not in cols:
            conn.execute(
                "ALTER TABLE expe_departs ADD COLUMN palette_europe_statut TEXT "
                "NOT NULL DEFAULT 'en_attente'"
            )
        if "palette_europe_date_retour" not in cols:
            conn.execute(
                "ALTER TABLE expe_departs ADD COLUMN palette_europe_date_retour TEXT"
            )
        if "palette_europe_note" not in cols:
            conn.execute(
                "ALTER TABLE expe_departs ADD COLUMN palette_europe_note TEXT"
            )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expe_departs_planning_entry "
            "ON expe_departs(planning_entry_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expe_departs_palette_europe "
            "ON expe_departs(palette_europe, palette_europe_statut)"
        )
        conn.commit()
        _record_schema_migration(conn, 111, "expe_departs_planning_link_palette_europe")

    # v112 â€” MyStock : flag is_europe sur matiÃ¨res premiÃ¨res catÃ©gorie palette
    # Marque les rÃ©fÃ©rences palette consignÃ©es (Europe) pour dÃ©tection auto dans MyExpÃ©.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=112 LIMIT 1").fetchone():
        mp_cols = {r["name"] for r in conn.execute("PRAGMA table_info(matieres_premieres)").fetchall()}
        if "is_europe" not in mp_cols:
            conn.execute(
                "ALTER TABLE matieres_premieres ADD COLUMN is_europe INTEGER NOT NULL DEFAULT 0"
            )
        # DÃ©tection auto initiale : rÃ©fÃ©rences dont la dÃ©signation ou la rÃ©f contient "europe"
        conn.execute(
            """UPDATE matieres_premieres
               SET is_europe = 1
               WHERE categorie = 'palette'
                 AND COALESCE(is_europe, 0) = 0
                 AND (
                   LOWER(COALESCE(reference, '')) LIKE '%europe%'
                   OR LOWER(COALESCE(designation, '')) LIKE '%europe%'
                   OR LOWER(COALESCE(reference, '')) LIKE '%eur%pal%'
                   OR LOWER(COALESCE(reference, '')) LIKE '%pal%eur%'
                 )"""
        )
        conn.commit()
        _record_schema_migration(conn, 112, "matieres_premieres_is_europe")

    # â”€â”€ Migration 113 : DSI + Repiquage passent en matin/aprem â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Les affectations existantes etaient en creneau='journee' ; on les deplace
    # par defaut sur 'matin' (l'utilisateur ajustera vers 'aprem' au cas par cas).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=113 LIMIT 1").fetchone():
        rows = conn.execute(
            "SELECT id, nom FROM machines WHERE actif = 1"
        ).fetchall()
        targets = []
        for r in rows:
            n = (r["nom"] or "").lower().strip()
            n = (n.replace("Ã©", "e").replace("Ã¨", "e").replace("Ãª", "e")
                  .replace("Ã ", "a").replace("Ã¢", "a")
                  .replace("Ã®", "i").replace("Ã´", "o"))
            if n == "dsi" or n.startswith("dsi ") or n.endswith(" dsi"):
                targets.append(r["id"])
            elif "repiquage" in n or n == "rep" or n.startswith("rep "):
                targets.append(r["id"])
        if targets:
            placeholders = ",".join(["?"] * len(targets))
            sql = (
                "UPDATE rh_planning_postes "
                "SET creneau = 'matin' "
                "WHERE machine_id IN (" + placeholders + ") "
                "AND creneau = 'journee'"
            )
            conn.execute(sql, targets)
            conn.commit()
        _record_schema_migration(conn, 113, "dsi_repiquage_creneau_matin")

    # -- Migration 114 : repiquage - parametrage carton + compteur ----------
    # - etiquettes_par_carton sur planning_entries (parametrage dossier)
    # - nb_cartons sur production_data (compte des cartons complets)
    # - table repiquage_carton_courant (etat carton en cours par dossier+operateur)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=114 LIMIT 1").fetchone():
        pe_cols = {r[1] for r in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
        if "etiquettes_par_carton" not in pe_cols:
            conn.execute(
                "ALTER TABLE planning_entries ADD COLUMN etiquettes_par_carton INTEGER"
            )
        pd_cols = {r[1] for r in conn.execute("PRAGMA table_info(production_data)").fetchall()}
        if "nb_cartons" not in pd_cols:
            conn.execute(
                "ALTER TABLE production_data ADD COLUMN nb_cartons INTEGER DEFAULT 0"
            )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS repiquage_carton_courant (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                no_dossier TEXT NOT NULL,
                operateur TEXT NOT NULL,
                nb_etiquettes INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                UNIQUE(no_dossier, operateur)
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rcc_dossier ON repiquage_carton_courant(no_dossier)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rcc_operateur ON repiquage_carton_courant(operateur)"
        )
        conn.commit()
        _record_schema_migration(conn, 114, "repiquage_carton_parametrage_compteur")

    # -- Migration 115 : fil de discussion par dossier (Repiquage) ------
    # Table partagee par opera, dysfonctionnement, observation, commentaire.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=115 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS repiquage_discussion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                no_dossier TEXT NOT NULL,
                user_id INTEGER,
                user_nom TEXT NOT NULL,
                type TEXT NOT NULL CHECK(type IN ('observation','dysfonctionnement','commentaire')),
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rep_disc_dossier ON repiquage_discussion(no_dossier)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_rep_disc_date ON repiquage_discussion(created_at)"
        )
        conn.commit()
        _record_schema_migration(conn, 115, "repiquage_discussion")

    # -- Migration 116 : module Qualite - Audits client ----------------
    # 6 tables : audit_dossiers, audit_auditeurs, audit_folders (arborescence
    # recursive via parent_id), audit_fichiers (folder_id NULL = racine),
    # audit_messages, audit_message_reads.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=116 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_dossiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT NOT NULL UNIQUE,
                client_id INTEGER REFERENCES clients(id) ON DELETE SET NULL,
                client_nom TEXT NOT NULL,
                date_audit TEXT NOT NULL,
                description TEXT NOT NULL,
                statut TEXT NOT NULL DEFAULT 'ouvert',
                date_cloture TEXT,
                created_at TEXT NOT NULL,
                created_by INTEGER REFERENCES users(id),
                updated_at TEXT NOT NULL,
                updated_by INTEGER REFERENCES users(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_statut ON audit_dossiers(statut)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_client ON audit_dossiers(client_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_date ON audit_dossiers(date_audit)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_auditeurs (
                audit_id INTEGER NOT NULL REFERENCES audit_dossiers(id) ON DELETE CASCADE,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                assigned_at TEXT NOT NULL,
                assigned_by INTEGER REFERENCES users(id),
                notified INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (audit_id, user_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_auditeurs_user ON audit_auditeurs(user_id)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_folders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id INTEGER NOT NULL REFERENCES audit_dossiers(id) ON DELETE CASCADE,
                parent_id INTEGER REFERENCES audit_folders(id) ON DELETE CASCADE,
                nom TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by INTEGER REFERENCES users(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_folders_audit ON audit_folders(audit_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_folders_parent ON audit_folders(parent_id)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_fichiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id INTEGER NOT NULL REFERENCES audit_dossiers(id) ON DELETE CASCADE,
                folder_id INTEGER REFERENCES audit_folders(id) ON DELETE SET NULL,
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER,
                uploaded_at TEXT NOT NULL,
                uploaded_by INTEGER REFERENCES users(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_fichiers_audit ON audit_fichiers(audit_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_fichiers_folder ON audit_fichiers(folder_id)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_id INTEGER NOT NULL REFERENCES audit_dossiers(id) ON DELETE CASCADE,
                author_id INTEGER REFERENCES users(id),
                body TEXT NOT NULL,
                attachment_id INTEGER REFERENCES audit_fichiers(id) ON DELETE SET NULL,
                created_at TEXT NOT NULL
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_messages_audit ON audit_messages(audit_id, created_at)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_message_reads (
                user_id INTEGER NOT NULL REFERENCES users(id),
                audit_id INTEGER NOT NULL REFERENCES audit_dossiers(id) ON DELETE CASCADE,
                last_read_message_id INTEGER,
                last_read_at TEXT NOT NULL,
                PRIMARY KEY (user_id, audit_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_reads_user ON audit_message_reads(user_id)")

        conn.commit()
        _record_schema_migration(conn, 116, "qualite_audits_client")

    # v117 - Z1 sortie de prod : lien dossier de production + suivi palettes
    # - mouvements_stock.no_dossier : trace le dossier de prod a l'origine de
    #   l'entree Z1 (pre-rempli pour fabrication, libre sinon).
    # - mouvement_palettes : journal des palettes utilisees a chaque mouvement
    #   Z1 (compteur par reference MP categorie 'palette'). Ne deduit PAS du
    #   stock MP : usage purement informatif/tracabilite.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=117 LIMIT 1").fetchone():
        ms_cols = {row[1] for row in conn.execute("PRAGMA table_info(mouvements_stock)").fetchall()}
        if "no_dossier" not in ms_cols:
            conn.execute("ALTER TABLE mouvements_stock ADD COLUMN no_dossier TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mvt_stock_dossier ON mouvements_stock(no_dossier)"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mouvement_palettes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mouvement_id INTEGER NOT NULL REFERENCES mouvements_stock(id) ON DELETE CASCADE,
                matiere_id INTEGER NOT NULL REFERENCES matieres_premieres(id),
                nombre INTEGER NOT NULL CHECK(nombre > 0),
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mvt_palettes_mvt ON mouvement_palettes(mouvement_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mvt_palettes_mat ON mouvement_palettes(matiere_id)"
        )
        conn.commit()
        _record_schema_migration(conn, 117, "z1_dossier_link_and_palettes")

    # v118 - MyStock : valorisation des matieres premieres
    # - mp_valorisation : prix unitaire courant par matiere (EUR / unite de gestion)
    # - mp_valorisation_historique : journal des changements de prix (qui, quand,
    #   avant/apres, note optionnelle). Pas de snapshot fige de valorisation.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=118 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mp_valorisation (
                matiere_id INTEGER PRIMARY KEY REFERENCES matieres_premieres(id) ON DELETE CASCADE,
                prix_unitaire REAL NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                updated_by_name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mp_valorisation_historique (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matiere_id INTEGER NOT NULL REFERENCES matieres_premieres(id) ON DELETE CASCADE,
                prix_avant REAL,
                prix_apres REAL NOT NULL,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                created_by INTEGER,
                created_by_name TEXT
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mp_valo_hist_mat ON mp_valorisation_historique(matiere_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mp_valo_hist_date ON mp_valorisation_historique(created_at DESC)"
        )
        conn.commit()
        _record_schema_migration(conn, 118, "mp_valorisation")

    # v119 - MyStock : matieres laizees (frontal / glassine / complexe)
    # - mp_laizes : referentiel des laizes (valeur_mm + label + ordre + actif),
    #   editable depuis /settings (super admin).
    # - matieres_premieres : nouvelles colonnes metres_lineaires_par_bobine
    #   et prix_eur_m2 (renseignees uniquement pour ces 3 categories).
    # - mp_matiere_laizes : liaison reference -> laizes valables.
    # - mp_stock_laize : stock par (matiere, laize). Le mp_stock global reste
    #   utilise pour les autres categories (mandrin / palette / adhesif /
    #   carton). Pour les matieres laizees, mp_stock.quantite est tenu a jour
    #   comme somme(mp_stock_laize) pour compatibilite avec les vues qui ne
    #   filtrent pas par laize.
    # - mp_mouvements : ajout laize_id (nullable pour les categories non laizees).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=119 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mp_laizes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                valeur_mm REAL NOT NULL UNIQUE,
                label TEXT NOT NULL,
                ordre INTEGER NOT NULL DEFAULT 0,
                actif INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
            )
        """)
        # Seed des 7 laizes par defaut
        default_laizes = [
            (333.0, "333 mm", 10),
            (430.0, "430 mm", 20),
            (470.0, "470 mm", 30),
            (510.0, "510 mm", 40),
            (530.0, "530 mm", 50),
            (550.0, "550 mm", 60),
            (570.0, "570 mm", 70),
        ]
        for val, lab, ordre in default_laizes:
            conn.execute(
                "INSERT OR IGNORE INTO mp_laizes (valeur_mm, label, ordre) VALUES (?, ?, ?)",
                (val, lab, ordre),
            )
        # Colonnes sur matieres_premieres
        mp_cols = {row[1] for row in conn.execute("PRAGMA table_info(matieres_premieres)").fetchall()}
        if "metres_lineaires_par_bobine" not in mp_cols:
            conn.execute(
                "ALTER TABLE matieres_premieres ADD COLUMN metres_lineaires_par_bobine REAL"
            )
        if "prix_eur_m2" not in mp_cols:
            conn.execute(
                "ALTER TABLE matieres_premieres ADD COLUMN prix_eur_m2 REAL"
            )
        # Liaison reference <-> laizes
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mp_matiere_laizes (
                matiere_id INTEGER NOT NULL REFERENCES matieres_premieres(id) ON DELETE CASCADE,
                laize_id INTEGER NOT NULL REFERENCES mp_laizes(id) ON DELETE RESTRICT,
                PRIMARY KEY (matiere_id, laize_id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mp_mat_laizes_lai ON mp_matiere_laizes(laize_id)"
        )
        # Stock par (matiere, laize)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS mp_stock_laize (
                matiere_id INTEGER NOT NULL REFERENCES matieres_premieres(id) ON DELETE CASCADE,
                laize_id INTEGER NOT NULL REFERENCES mp_laizes(id) ON DELETE RESTRICT,
                quantite REAL NOT NULL DEFAULT 0,
                updated_at TEXT,
                updated_by_name TEXT,
                PRIMARY KEY (matiere_id, laize_id)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mp_stock_laize_lai ON mp_stock_laize(laize_id)"
        )
        # Colonne laize_id sur mouvements
        mvt_cols = {row[1] for row in conn.execute("PRAGMA table_info(mp_mouvements)").fetchall()}
        if "laize_id" not in mvt_cols:
            conn.execute("ALTER TABLE mp_mouvements ADD COLUMN laize_id INTEGER REFERENCES mp_laizes(id)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mp_mvt_laize ON mp_mouvements(laize_id)"
        )
        conn.commit()
        _record_schema_migration(conn, 119, "mp_laizes_matieres_laizees")

    # v120 â€” MyExpÃ© : rÃ©fÃ©rence "YYYY-N" pour les demandes de devis
    if not conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version=120 LIMIT 1"
    ).fetchone():
        cols = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(expe_demandes_devis)"
            ).fetchall()
        }
        if "reference" not in cols:
            conn.execute(
                "ALTER TABLE expe_demandes_devis ADD COLUMN reference TEXT"
            )
        # Backfill : numÃ©ros sÃ©quentiels par annÃ©e (ordre chronologique).
        rows = conn.execute(
            "SELECT id, created_at FROM expe_demandes_devis "
            "WHERE reference IS NULL OR reference='' "
            "ORDER BY COALESCE(created_at,''), id"
        ).fetchall()
        # Compteurs initialisÃ©s Ã  partir des rÃ©fÃ©rences dÃ©jÃ  prÃ©sentes.
        counters: dict[str, int] = {}
        existing = conn.execute(
            "SELECT reference FROM expe_demandes_devis WHERE reference IS NOT NULL"
        ).fetchall()
        for r in existing:
            ref = (r[0] or "").strip()
            if "-" in ref:
                year_str, num_str = ref.split("-", 1)
                try:
                    n = int(num_str)
                    counters[year_str] = max(counters.get(year_str, 0), n)
                except ValueError:
                    pass
        for r in rows:
            created = r[1] or ""
            year = created[:4] if len(created) >= 4 else "1970"
            counters[year] = counters.get(year, 0) + 1
            ref = f"{year}-{counters[year]}"
            conn.execute(
                "UPDATE expe_demandes_devis SET reference=? WHERE id=?",
                (ref, r[0]),
            )
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "idx_expe_demandes_devis_reference "
            "ON expe_demandes_devis(reference) "
            "WHERE reference IS NOT NULL"
        )
        conn.commit()
        _record_schema_migration(conn, 120, "expe_demandes_devis_reference")

    # v121 - MyStock : valorisation des produits finis (et negoce)
    # - pf_valorisation : prix unitaire HT courant par produit + meta import Excel
    # - pf_valorisation_historique : journal des changements (qui, quand,
    #   avant/apres, source : edition manuelle | import xlsx).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=121 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pf_valorisation (
                produit_id INTEGER PRIMARY KEY REFERENCES produits(id) ON DELETE CASCADE,
                prix_unitaire_ht REAL NOT NULL DEFAULT 0,
                source_prix TEXT,
                statut TEXT,
                date_derniere_cmd TEXT,
                updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                updated_by INTEGER,
                updated_by_name TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS pf_valorisation_historique (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                produit_id INTEGER NOT NULL REFERENCES produits(id) ON DELETE CASCADE,
                prix_avant REAL,
                prix_apres REAL NOT NULL,
                source TEXT,
                note TEXT,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
                created_by INTEGER,
                created_by_name TEXT
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pf_valo_hist_prod ON pf_valorisation_historique(produit_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pf_valo_hist_date ON pf_valorisation_historique(created_at DESC)"
        )
        conn.commit()
        _record_schema_migration(conn, 121, "pf_valorisation")

    # v122 â€” MatiÃ¨res premiÃ¨res : catÃ©gorie "autre" + sous-section libre
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=122 LIMIT 1").fetchone():
        mp_cols = {row[1] for row in conn.execute("PRAGMA table_info(matieres_premieres)").fetchall()}
        if "sous_section" not in mp_cols:
            conn.execute("ALTER TABLE matieres_premieres ADD COLUMN sous_section TEXT")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mp_sous_section ON matieres_premieres(sous_section)"
        )
        conn.commit()
        _record_schema_migration(conn, 122, "matieres_premieres_autre_sous_section")

    # v123 â€” MatiÃ¨res premiÃ¨res : conditionnement unitaire pour cartons / adhÃ©sifs / mandrins
    # Analogue Ã  metres_lineaires_par_bobine pour les frontaux : permet de saisir le prix
    # Ã  l'unitÃ© d'achat (â‚¬/carton, â‚¬/tube, â‚¬/kg) tout en gardant le stock en palettes.
    # Valorisation = stock_palettes Ã— unites_par_palette Ã— prix_unitaire.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=123 LIMIT 1").fetchone():
        mp_cols = {row[1] for row in conn.execute("PRAGMA table_info(matieres_premieres)").fetchall()}
        if "unites_par_palette" not in mp_cols:
            conn.execute("ALTER TABLE matieres_premieres ADD COLUMN unites_par_palette REAL")
        conn.commit()
        _record_schema_migration(conn, 123, "matieres_premieres_unites_par_palette")

    # v124 â€” Valorisation MP : flag Â« prix saisi numÃ©riquement assimilÃ© USD Â».
    # Lorsque prix_en_usd = 1, le prix_unitaire stockÃ© est considÃ©rÃ© comme une valeur
    # exprimÃ©e en USD (mais portÃ©e par le champ EUR pour compatibilitÃ©). Le Â« prix rÃ©el Â»
    # affichÃ© cÃ´tÃ© direction/superadmin = prix_unitaire Ã— taux_eur_usd (paramÃ¨tre MyCouts).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=124 LIMIT 1").fetchone():
        valo_cols = {row[1] for row in conn.execute("PRAGMA table_info(mp_valorisation)").fetchall()}
        if "prix_en_usd" not in valo_cols:
            conn.execute(
                "ALTER TABLE mp_valorisation ADD COLUMN prix_en_usd INTEGER NOT NULL DEFAULT 0"
            )
        conn.commit()
        _record_schema_migration(conn, 124, "mp_valorisation_prix_en_usd")

    # v125 â€” Valorisation MP : flag Â« taxe d'importation Â» (multiplicatif avec USD).
    # Lorsque taxe_importation = 1, on applique au prix_unitaire le multiplicateur
    # (1 + import_tax_pct / 100), oÃ¹ import_tax_pct est le paramÃ¨tre MyCouts.
    # CombinÃ© avec prix_en_usd : prix_reel = prix Ã— taux_eur_usd Ã— (1 + taxe%).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=125 LIMIT 1").fetchone():
        valo_cols = {row[1] for row in conn.execute("PRAGMA table_info(mp_valorisation)").fetchall()}
        if "taxe_importation" not in valo_cols:
            conn.execute(
                "ALTER TABLE mp_valorisation ADD COLUMN taxe_importation INTEGER NOT NULL DEFAULT 0"
            )
        # Seed la nouvelle clÃ© mc_setting si la table existe (idempotent).
        try:
            conn.execute(
                "INSERT OR IGNORE INTO mc_setting (key, value_decimal) VALUES ('import_tax_pct', 0)"
            )
        except Exception:
            pass  # mc_setting peut ne pas exister sur les DB trÃ¨s anciennes
        conn.commit()
        _record_schema_migration(conn, 125, "mp_valorisation_taxe_importation")

    # v126 â€” Valorisation MP : flag Â« coÃ»t transport Â» (forfait additif).
    # Lorsque cout_transport_inclus = 1, on ajoute le forfait transport_cost_fixed_eur
    # (paramÃ¨tre MyCouts) UNE SEULE FOIS Ã  la valorisation de la rÃ©fÃ©rence, APRÃˆS les
    # multiplicateurs USD et taxe. Forfait peu importe la quantitÃ© en stock.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=126 LIMIT 1").fetchone():
        valo_cols = {row[1] for row in conn.execute("PRAGMA table_info(mp_valorisation)").fetchall()}
        if "cout_transport_inclus" not in valo_cols:
            conn.execute(
                "ALTER TABLE mp_valorisation ADD COLUMN cout_transport_inclus INTEGER NOT NULL DEFAULT 0"
            )
        try:
            conn.execute(
                "INSERT OR IGNORE INTO mc_setting (key, value_decimal) VALUES ('transport_cost_fixed_eur', 0)"
            )
        except Exception:
            pass
        conn.commit()
        _record_schema_migration(conn, 126, "mp_valorisation_cout_transport")

    # v127 â€” MyExpÃ© : transporteurs avec portail sÃ©parÃ© et emails multiples
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=127 LIMIT 1").fetchone():
        import json as _json
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_transporteurs)").fetchall()}
        if "contact_portail_url" not in cols:
            conn.execute("ALTER TABLE expe_transporteurs ADD COLUMN contact_portail_url TEXT")
        if "contact_emails" not in cols:
            conn.execute("ALTER TABLE expe_transporteurs ADD COLUMN contact_emails TEXT")
        # Backfill : contact_email = URL â†’ contact_portail_url ; sinon â†’ contact_emails JSON
        rows = conn.execute(
            "SELECT id, contact_email, contact_portail_url, contact_emails FROM expe_transporteurs"
        ).fetchall()
        for r in rows:
            old = (r["contact_email"] or "").strip()
            has_portail = bool((r["contact_portail_url"] or "").strip())
            has_emails = bool((r["contact_emails"] or "").strip())
            if not old or (has_portail and has_emails):
                continue
            new_portail = r["contact_portail_url"]
            new_emails = r["contact_emails"]
            low = old.lower()
            if low.startswith("http://") or low.startswith("https://"):
                if not has_portail:
                    new_portail = old
                if not has_emails:
                    new_emails = "[]"
            else:
                # Peut contenir plusieurs adresses sÃ©parÃ©es par , ou ;
                if not has_emails:
                    parts = []
                    for chunk in old.replace(";", ",").split(","):
                        v = chunk.strip()
                        if v and "@" in v:
                            parts.append(v)
                    new_emails = _json.dumps(parts, ensure_ascii=False)
            conn.execute(
                "UPDATE expe_transporteurs SET contact_portail_url=?, contact_emails=? WHERE id=?",
                (new_portail, new_emails, r["id"]),
            )
        conn.commit()
        _record_schema_migration(conn, 127, "expe_transporteurs_portail_emails")

    # v128 â€” Codes maintenance : migration localStorage â†’ table SQLite.
    # Permet la synchronisation v2 â†’ v1 et l'accÃ¨s depuis n'importe quel navigateur.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=128 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maintenance_codes (
                code TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                niveau INTEGER NOT NULL DEFAULT 1,
                categorie TEXT NOT NULL DEFAULT 'controles',
                periodique INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )"""
        )
        conn.commit()
        _record_schema_migration(conn, 128, "maintenance_codes_table")

    # v131 â€” Codes maintenance : rÃ©fÃ©rence mÃ©trage pour la catÃ©gorie "Suivi"
    # (piÃ¨ces d'usure). Texte libre comme intervalle (ex. "5000 m", "10 km").
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=131 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(maintenance_codes)").fetchall()}
        if "metrage_ref" not in cols:
            conn.execute("ALTER TABLE maintenance_codes ADD COLUMN metrage_ref TEXT")
        conn.commit()
        _record_schema_migration(conn, 131, "maintenance_codes_metrage_ref")

    # v130 â€” Demandes de devis transporteur : champ client + piÃ¨ce jointe.
    # Le client est renseignÃ© par l'utilisateur Ã  la crÃ©ation. La piÃ¨ce jointe
    # est un fichier uploadÃ© optionnellement, stockÃ© sous data/uploads/devis/.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=130 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_demandes_devis)").fetchall()}
        if "client" not in cols:
            conn.execute("ALTER TABLE expe_demandes_devis ADD COLUMN client TEXT")
        if "piece_jointe_path" not in cols:
            conn.execute("ALTER TABLE expe_demandes_devis ADD COLUMN piece_jointe_path TEXT")
        if "piece_jointe_filename" not in cols:
            conn.execute("ALTER TABLE expe_demandes_devis ADD COLUMN piece_jointe_filename TEXT")
        conn.commit()
        _record_schema_migration(conn, 130, "expe_demandes_devis_client_piece_jointe")

    # v129 â€” Codes maintenance : intervalle de temps pour les codes pÃ©riodiques.
    # Texte libre (ex. "Quotidien", "Hebdo", "30 jours", "1 mois", "6 mois").
    # IgnorÃ© cÃ´tÃ© UI quand periodique=0.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=129 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(maintenance_codes)").fetchall()}
        if "intervalle" not in cols:
            conn.execute("ALTER TABLE maintenance_codes ADD COLUMN intervalle TEXT")
        conn.commit()
        _record_schema_migration(conn, 129, "maintenance_codes_intervalle")


    # v132 â€” Alertes de maintenance : rÃ¨gles paramÃ©trables qui dÃ©clenchent un
    # message / formulaire pour les opÃ©rateurs sur leur Ã©cran. Une alerte stocke
    # ses paramÃ¨tres complets (dÃ©clencheur, cible, formulaire de validation) en
    # JSON dans `params`, ce qui Ã©vite d'avoir Ã  faire une migration de schÃ©ma Ã 
    # chaque Ã©volution du modÃ¨le de rÃ¨gles. `active` est Ã  0 Ã  la crÃ©ation :
    # l'admin doit activer explicitement chaque alerte via le toggle.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=132 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maintenance_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 0,
                params TEXT NOT NULL DEFAULT '{}',
                created_by TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT
            )"""
        )
        conn.commit()
        _record_schema_migration(conn, 132, "maintenance_alerts_table")

    # v133 â€” Alertes liÃ©es aux codes maintenance.
    # Chaque code "contrÃ´le non pÃ©riodique" doit avoir son alerte automatique.
    # La date de derniÃ¨re intervention du contrÃ´le = last_ack_at de l'alerte
    # (mise Ã  jour quand l'opÃ©rateur valide le formulaire).
    # linked_maint_code est UNIQUE quand non NULL pour Ã©viter d'avoir deux
    # alertes pour le mÃªme code (sÃ©curitÃ© contre les dÃ©syncs).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=133 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(maintenance_alerts)").fetchall()}
        if "linked_maint_code" not in cols:
            conn.execute("ALTER TABLE maintenance_alerts ADD COLUMN linked_maint_code TEXT")
        if "last_ack_at" not in cols:
            conn.execute("ALTER TABLE maintenance_alerts ADD COLUMN last_ack_at TEXT")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_maint_alerts_linked_code "
            "ON maintenance_alerts(linked_maint_code) WHERE linked_maint_code IS NOT NULL"
        )
        # Backfill : pour chaque contrÃ´le non pÃ©riodique existant, crÃ©er
        # l'alerte associÃ©e si elle n'existe pas dÃ©jÃ .
        now = datetime.now().isoformat()
        rows = conn.execute(
            "SELECT code, label FROM maintenance_codes "
            "WHERE categorie='controles' AND periodique=0"
        ).fetchall()
        for r in rows:
            code = r["code"]
            label = (r["label"] or "").strip()
            existing = conn.execute(
                "SELECT 1 FROM maintenance_alerts WHERE linked_maint_code=? LIMIT 1",
                (code,)
            ).fetchone()
            if existing:
                continue
            nom = f"ContrÃ´le : {code} â€“ {label}" if label else f"ContrÃ´le : {code}"
            nom = nom[:120]
            conn.execute(
                """INSERT INTO maintenance_alerts
                   (nom, active, params, created_by, created_at, updated_at, linked_maint_code)
                   VALUES (?, 0, '{}', 'auto:migration', ?, ?, ?)""",
                (nom, now, now, code)
            )
        conn.commit()
        _record_schema_migration(conn, 133, "maintenance_alerts_link_to_codes")

    # v134 â€” RÃ©glages globaux des alertes maintenance (singleton row).
    # Placement, taille et bloque-production s'appliquent Ã  TOUTES les alertes
    # actives. StockÃ©s Ã  part de chaque alerte pour qu'un changement global
    # prenne effet immÃ©diatement sans toucher au paramÃ©trage individuel.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=134 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maintenance_alert_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                placement TEXT NOT NULL DEFAULT 'center',
                size TEXT NOT NULL DEFAULT 'medium',
                block_production INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT,
                updated_by TEXT
            )"""
        )
        _now_134 = datetime.now().isoformat()
        conn.execute(
            """INSERT OR IGNORE INTO maintenance_alert_settings
               (id, placement, size, block_production, updated_at, updated_by)
               VALUES (1, 'top-right', 'medium', 0, ?, 'auto:migration')""",
            (_now_134,),
        )
        conn.commit()
        _record_schema_migration(conn, 134, "maintenance_alert_settings_singleton")

    # v135 â€” Comportement d'empilement des alertes maintenance.
    # 'stack'    : toutes les alertes actives sont affichÃ©es en pile
    # 'queue'    : une seule Ã  la fois, les autres attendent leur tour
    # 'replace'  : la derniÃ¨re alerte remplace celle dÃ©jÃ  affichÃ©e
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=135 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(maintenance_alert_settings)").fetchall()}
        if "stack_mode" not in cols:
            conn.execute(
                "ALTER TABLE maintenance_alert_settings ADD COLUMN stack_mode TEXT NOT NULL DEFAULT 'stack'"
            )
        conn.execute(
            "UPDATE maintenance_alert_settings SET stack_mode='stack' "
            "WHERE id=1 AND (stack_mode IS NULL OR stack_mode='')"
        )
        conn.commit()
        _record_schema_migration(conn, 135, "maintenance_alert_settings_stack_mode")

    # v136 â€” Historique des acquittements d'alertes maintenance.
    # Chaque entrÃ©e trace : qui (user_id, nom), quand (ack_at), sur quelle
    # machine, quel dossier en cours, les rÃ©ponses cochÃ©es/saisies par point
    # (JSON), et le commentaire libre. Permet l'audit qualitÃ© et le calcul
    # du compteur pÃ©riodique par machine.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=136 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maintenance_alert_acks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER NOT NULL,
                user_id INTEGER,
                user_nom TEXT,
                machine TEXT,
                no_dossier TEXT,
                ack_at TEXT NOT NULL,
                responses TEXT,
                comment TEXT,
                FOREIGN KEY (alert_id) REFERENCES maintenance_alerts(id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alert_acks_alert_machine "
            "ON maintenance_alert_acks(alert_id, machine, ack_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alert_acks_ack_at "
            "ON maintenance_alert_acks(ack_at DESC)"
        )
        conn.commit()
        _record_schema_migration(conn, 136, "maintenance_alert_acks_table")

    # v137 â€” Nouveaux dÃ©fauts des rÃ©glages d'alerte (UX) :
    #   placement = top-right, size = medium, block_production = 0, stack_mode = queue
    # On met Ã  jour le singleton uniquement s'il n'a jamais Ã©tÃ© personnalisÃ©
    # par un super admin (updated_by = 'auto:migration'). Les utilisateurs qui
    # ont dÃ©jÃ  configurÃ© leurs propres rÃ©glages ne sont pas Ã©crasÃ©s.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=137 LIMIT 1").fetchone():
        conn.execute(
            """UPDATE maintenance_alert_settings
               SET placement='top-right', size='medium',
                   block_production=0, stack_mode='queue'
               WHERE id=1 AND updated_by='auto:migration'"""
        )
        conn.commit()
        _record_schema_migration(conn, 137, "maintenance_alert_settings_new_defaults")

    # v138 â€” Espacement minimum entre alertes affichÃ©es Ã  l'opÃ©rateur.
    # min_gap_minutes = dÃ©lai de silence aprÃ¨s chaque acquittement pendant
    # lequel aucune autre alerte ne peut s'afficher sur cette machine. Ã‰vite
    # que l'opÃ©rateur soit inondÃ© quand plusieurs alertes deviennent dues
    # simultanÃ©ment (typiquement Ã  la reprise de production).
    # On force aussi stack_mode='queue' partout : c'est le seul mode qui a
    # du sens avec la nouvelle logique.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=138 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(maintenance_alert_settings)").fetchall()}
        if "min_gap_minutes" not in cols:
            conn.execute(
                "ALTER TABLE maintenance_alert_settings "
                "ADD COLUMN min_gap_minutes INTEGER NOT NULL DEFAULT 5"
            )
        conn.execute(
            "UPDATE maintenance_alert_settings SET min_gap_minutes=5 "
            "WHERE id=1 AND (min_gap_minutes IS NULL OR min_gap_minutes < 0)"
        )
        # Force stack_mode='queue' (seul mode UI dÃ©sormais)
        conn.execute(
            "UPDATE maintenance_alert_settings SET stack_mode='queue' WHERE id=1"
        )
        conn.commit()
        _record_schema_migration(conn, 138, "maintenance_alert_settings_min_gap")


    # v139 â€” Sondages dans la messagerie interne (chat_polls + options + votes)
    # RattachÃ©s Ã  un chat_messages (cascade delete). Vote 100% anonyme possible :
    # user_id/user_nom NULL, dÃ©dup via voter_hash = SHA256(poll_id || user_id || secret).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=139 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_polls (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id   INTEGER NOT NULL UNIQUE REFERENCES chat_messages(id) ON DELETE CASCADE,
                channel_id   INTEGER NOT NULL,
                question     TEXT    NOT NULL,
                multi_choice INTEGER NOT NULL DEFAULT 0,
                anonymous    INTEGER NOT NULL DEFAULT 0,
                closes_at    TEXT    DEFAULT NULL,
                closed_at    TEXT    DEFAULT NULL,
                created_by   INTEGER NOT NULL,
                created_at   TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_poll_options (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id  INTEGER NOT NULL REFERENCES chat_polls(id) ON DELETE CASCADE,
                position INTEGER NOT NULL,
                label    TEXT    NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_poll_options_poll ON chat_poll_options(poll_id)"
        )
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_poll_votes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id     INTEGER NOT NULL REFERENCES chat_polls(id) ON DELETE CASCADE,
                option_id   INTEGER NOT NULL REFERENCES chat_poll_options(id) ON DELETE CASCADE,
                user_id     INTEGER DEFAULT NULL,
                user_nom    TEXT    DEFAULT NULL,
                voter_hash  TEXT    DEFAULT NULL,
                voted_at    TEXT    NOT NULL
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_poll_votes_poll ON chat_poll_votes(poll_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_poll_votes_option ON chat_poll_votes(option_id)"
        )
        # UnicitÃ© vote nominatif (1 vote par option par user)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_poll_votes_user "
            "ON chat_poll_votes(poll_id, option_id, user_id) WHERE user_id IS NOT NULL"
        )
        # UnicitÃ© vote anonyme (1 vote par option par voter_hash)
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_poll_votes_hash "
            "ON chat_poll_votes(poll_id, option_id, voter_hash) WHERE voter_hash IS NOT NULL"
        )
        conn.commit()
        _record_schema_migration(conn, 139, "chat_polls")

    # v140 â€” MyCouts : nouvelles clÃ©s mc_setting Â« charge de production Â» et
    # Â« frais de stockage Â» (utilisÃ©es cÃ´tÃ© valorisation PF pour calculer
    # total_pf_avec_charges = total_pf * (1 + storage/100) / (1 - charge/100)).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=140 LIMIT 1").fetchone():
        try:
            conn.execute(
                "INSERT OR IGNORE INTO mc_setting (key, value_decimal) VALUES ('charge_production_pct', 0)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO mc_setting (key, value_decimal) VALUES ('storage_fees_pct', 0)"
            )
        except Exception:
            pass  # mc_setting peut ne pas exister sur les DB trÃ¨s anciennes
        conn.commit()
        _record_schema_migration(conn, 140, "mc_setting_charges_prod_stockage")

    # v141 â€” MyCouts + Logistique : coÃ»t demi-container (EUR) + quantitÃ©s mÂ² par
    # container (renseignÃ©es via /settings > Logistique > Importations, utilisÃ©es
    # pour afficher "soit X EUR/mÂ²" sous les 2 champs coÃ»t container du modal).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=141 LIMIT 1").fetchone():
        try:
            conn.execute(
                "INSERT OR IGNORE INTO mc_setting (key, value_decimal) VALUES ('default_half_container_cost_eur', 0)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO mc_setting (key, value_decimal) VALUES ('logistique_qte_m2_container_complet', 0)"
            )
            conn.execute(
                "INSERT OR IGNORE INTO mc_setting (key, value_decimal) VALUES ('logistique_qte_m2_demi_container', 0)"
            )
        except Exception:
            pass
        conn.commit()
        _record_schema_migration(conn, 141, "mc_setting_demi_container_qte_m2")

    # v142 â€” TraÃ§abilitÃ© clÃ´ture sondages : colonne closed_by (auteur du clic)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=142 LIMIT 1").fetchone():
        cols = {r[1] for r in conn.execute("PRAGMA table_info(chat_polls)").fetchall()}
        if "closed_by" not in cols:
            conn.execute("ALTER TABLE chat_polls ADD COLUMN closed_by INTEGER DEFAULT NULL")
        conn.commit()
        _record_schema_migration(conn, 142, "chat_polls_closed_by")


    # v143 - Qualite Referentiel RSE / Normes & Certifications
    # 4 tables :
    #   qualite_ref_fiches       : catalogue des normes/certifs (definition, position SIFA, details, statuts)
    #   qualite_ref_fichiers     : pieces jointes (certificats, attestations, FDS...)
    #   qualite_ref_questions    : questions clients type indexees pour l autocompletion
    #   qualite_ref_audit_liens  : jointure vers audit_dossiers (cas d usage passes)
    # + seed idempotent d une trentaine de fiches socle (slug unique)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=143 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS qualite_ref_fiches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT NOT NULL UNIQUE,
                nom TEXT NOT NULL,
                acronyme TEXT,
                categorie TEXT NOT NULL,
                definition TEXT NOT NULL,
                position_sifa TEXT NOT NULL DEFAULT '',
                details TEXT NOT NULL DEFAULT '',
                statut_sifa TEXT NOT NULL DEFAULT 'a_evaluer',
                statut_validation TEXT NOT NULL DEFAULT 'brouillon',
                source_url TEXT,
                tags TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                created_by INTEGER REFERENCES users(id),
                updated_at TEXT NOT NULL,
                updated_by INTEGER REFERENCES users(id),
                validated_at TEXT,
                validated_by INTEGER REFERENCES users(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qref_categorie ON qualite_ref_fiches(categorie)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qref_statut ON qualite_ref_fiches(statut_validation)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qref_nom ON qualite_ref_fiches(nom)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS qualite_ref_fichiers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fiche_id INTEGER NOT NULL REFERENCES qualite_ref_fiches(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER,
                uploaded_at TEXT NOT NULL,
                uploaded_by INTEGER REFERENCES users(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qref_fichiers_fiche ON qualite_ref_fichiers(fiche_id)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS qualite_ref_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fiche_id INTEGER NOT NULL REFERENCES qualite_ref_fiches(id) ON DELETE CASCADE,
                texte TEXT NOT NULL,
                created_at TEXT NOT NULL,
                created_by INTEGER REFERENCES users(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qref_questions_fiche ON qualite_ref_questions(fiche_id)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS qualite_ref_audit_liens (
                fiche_id INTEGER NOT NULL REFERENCES qualite_ref_fiches(id) ON DELETE CASCADE,
                audit_id INTEGER NOT NULL REFERENCES audit_dossiers(id) ON DELETE CASCADE,
                note TEXT,
                created_at TEXT NOT NULL,
                created_by INTEGER REFERENCES users(id),
                PRIMARY KEY (fiche_id, audit_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qref_audit_liens_audit ON qualite_ref_audit_liens(audit_id)")

        _now_iso = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        _seed_fiches = [
            ("reach", "REACH", "REACH", "environnement",
             "Reglement europeen sur l enregistrement, l evaluation, l autorisation et la restriction des substances chimiques.",
             "chimie,substances,ue,sve,svhc",
             "https://echa.europa.eu/regulations/reach/understanding-reach"),
            ("rohs", "RoHS", "RoHS", "environnement",
             "Directive europeenne limitant les substances dangereuses dans les equipements electriques et electroniques.",
             "plomb,mercure,cadmium,eee,ue",
             "https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en"),
            ("pop", "Polluants organiques persistants (POP)", "POP", "environnement",
             "Convention de Stockholm : substances chimiques a longue duree de vie, bioaccumulables et toxiques.",
             "stockholm,pcb,pesticides,persistant",
             "https://www.pops.int/"),
            ("cov-voc", "Composes organiques volatils (COV / VOC)", "COV/VOC", "environnement",
             "Substances chimiques qui s evaporent facilement a temperature ambiante ; concernees par les seuils d emissions.",
             "solvants,emissions,air,peintures,colles",
             ""),
            ("iso-14001", "ISO 14001", "ISO 14001", "environnement",
             "Norme internationale de systeme de management environnemental.",
             "sme,environnement,certification,iso",
             "https://www.iso.org/fr/iso-14001-environmental-management.html"),
            ("iso-50001", "ISO 50001", "ISO 50001", "environnement",
             "Norme internationale de management de l energie.",
             "energie,performance,iso",
             "https://www.iso.org/fr/iso-50001-energy-management.html"),
            ("emas", "EMAS", "EMAS", "environnement",
             "Systeme europeen de management environnemental et d audit, plus exigeant qu ISO 14001 (declaration publique).",
             "ue,environnement,declaration",
             "https://green-business.ec.europa.eu/eco-management-and-audit-scheme-emas_en"),
            ("pefc", "PEFC", "PEFC", "environnement",
             "Certification de gestion durable des forets (Programme for the Endorsement of Forest Certification).",
             "foret,bois,papier,carton,chaine-controle",
             "https://www.pefc.fr/"),
            ("fsc", "FSC", "FSC", "environnement",
             "Certification de gestion responsable des forets (Forest Stewardship Council).",
             "foret,bois,papier,carton,chaine-controle",
             "https://fr.fsc.org/"),
            ("ademe-acv", "Bilan Carbone / ACV", "Bilan Carbone", "environnement",
             "Methode ADEME d evaluation des emissions de gaz a effet de serre et analyse du cycle de vie produit.",
             "carbone,ges,ademe,scope-1-2-3,acv",
             "https://www.bilancarbone.ademe.fr/"),
            ("ghg-protocol", "GHG Protocol", "GHG", "environnement",
             "Standard international de comptabilite carbone couvrant les Scopes 1, 2 et 3.",
             "carbone,scope-1,scope-2,scope-3,ges",
             "https://ghgprotocol.org/"),
            ("ppwr", "PPWR", "PPWR", "environnement",
             "Reglement UE sur les emballages et dechets d emballages (successeur de la directive PPWD).",
             "emballage,recyclage,ue,pfas",
             "https://environment.ec.europa.eu/topics/waste-and-recycling/packaging-waste_en"),
            ("loi-agec", "Loi AGEC", "AGEC", "environnement",
             "Loi francaise anti-gaspillage pour une economie circulaire (2020).",
             "economie-circulaire,rep,recyclage,france",
             "https://www.ecologie.gouv.fr/loi-anti-gaspillage-economie-circulaire"),
            ("triman", "Triman", "Triman", "environnement",
             "Logo obligatoire d information au consommateur sur le tri des emballages en France.",
             "tri,emballage,consommateur,info-tri",
             "https://www.ademe.fr/"),
            ("csrd", "CSRD", "CSRD", "environnement",
             "Directive europeenne de reporting extra-financier (durabilite) pour les grandes entreprises.",
             "reporting,esrs,esg,ue,double-materialite",
             "https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en"),
            ("iso-26000", "ISO 26000", "ISO 26000", "social",
             "Norme d orientation sur la responsabilite societale des organisations (non certifiable).",
             "rse,societal,iso,orientation",
             "https://www.iso.org/fr/iso-26000-social-responsibility.html"),
            ("ecovadis", "Ecovadis", "Ecovadis", "social",
             "Plateforme d evaluation RSE des fournisseurs (score sur 100, 4 piliers : environnement, social, ethique, achats responsables).",
             "notation,fournisseur,rse,platine,or,argent,bronze",
             "https://ecovadis.com/fr/"),
            ("sedex-smeta", "Sedex / SMETA", "SMETA", "social",
             "Plateforme et methodologie d audit ethique de la chaine d approvisionnement.",
             "audit,ethique,fournisseur,4-piliers",
             "https://www.sedex.com/"),
            ("sapin-ii", "Loi Sapin II", "Sapin II", "social",
             "Loi francaise de lutte contre la corruption (2016) : cartographie des risques, alerte interne, code de conduite.",
             "anti-corruption,france,alerte,afa",
             "https://www.legifrance.gouv.fr/"),
            ("devoir-vigilance", "Devoir de vigilance", "Devoir vigilance", "social",
             "Loi francaise imposant aux grandes entreprises un plan de prevention des atteintes aux droits humains et a l environnement.",
             "droits-humains,vigilance,france,plan",
             ""),
            ("code-conduite-fournisseur", "Code de conduite fournisseur", "CCF", "social",
             "Charte engageant les fournisseurs sur des criteres ethiques, sociaux et environnementaux.",
             "fournisseur,charte,engagement",
             ""),
            ("modern-slavery-act", "Modern Slavery Act", "MSA", "social",
             "Loi britannique (2015) exigeant un rapport annuel sur les mesures anti-esclavage moderne.",
             "uk,esclavage,rapport,transparence",
             "https://www.legislation.gov.uk/ukpga/2015/30/contents"),
            ("conflict-minerals", "Conflict Minerals", "3TG", "social",
             "Reglementation sur l approvisionnement responsable en minerais 3TG : etain, tantale, tungstene, or.",
             "3tg,minerais,conflit,eu-2017-821",
             "https://policy.trade.ec.europa.eu/development-and-sustainability/conflict-minerals-regulation_en"),
            ("iso-9001", "ISO 9001", "ISO 9001", "tracabilite",
             "Norme internationale de management de la qualite.",
             "smq,qualite,iso,certification",
             "https://www.iso.org/fr/iso-9001-quality-management.html"),
            ("tracabilite-lot", "Tracabilite lot & origine", "Tracabilite", "tracabilite",
             "Capacite a identifier l origine et le parcours d un lot de production, de la matiere premiere au produit fini.",
             "lot,origine,parcours,mp,pf",
             ""),
            ("oeko-tex", "OEKO-TEX Standard 100", "OEKO-TEX", "tracabilite",
             "Certification textile garantissant l absence de substances nocives.",
             "textile,substances,certification",
             "https://www.oeko-tex.com/fr/"),
            ("gots", "GOTS", "GOTS", "tracabilite",
             "Standard textile bio (Global Organic Textile Standard) integrant criteres environnementaux et sociaux.",
             "textile,bio,coton,social",
             "https://global-standard.org/"),
            ("iso-45001", "ISO 45001", "ISO 45001", "securite",
             "Norme de management de la sante et securite au travail (remplace OHSAS 18001).",
             "sst,securite,sante,iso",
             "https://www.iso.org/fr/iso-45001-occupational-health-and-safety.html"),
            ("fds-sds", "Fiche de donnees de securite (FDS/SDS)", "FDS", "securite",
             "Document normalise en 16 sections decrivant les dangers, precautions et usages d un produit chimique.",
             "chimie,fds,sds,ghs,clp",
             "https://echa.europa.eu/fr/safety-data-sheets"),
            ("prop-65", "California Prop 65", "Prop 65", "securite",
             "Loi californienne d etiquetage des substances cancerigenes ou toxiques pour la reproduction.",
             "usa,californie,etiquetage,cmr",
             "https://oehha.ca.gov/proposition-65"),
            ("pbt-vpvb", "PBT / vPvB", "PBT", "securite",
             "Criteres d identification des substances persistantes, bioaccumulables et toxiques (annexe XIII de REACH).",
             "reach,persistant,bioaccumulable,toxique",
             ""),
        ]
        for slug, nom, acr, cat, definition, tags, source in _seed_fiches:
            conn.execute(
                """INSERT OR IGNORE INTO qualite_ref_fiches
                       (slug, nom, acronyme, categorie, definition, position_sifa, details,
                        statut_sifa, statut_validation, source_url, tags,
                        created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, '', '',
                           'a_evaluer', 'brouillon', ?, ?,
                           ?, ?)""",
                (slug, nom, acr, cat, definition, source, tags, _now_iso, _now_iso),
            )

        conn.commit()
        _record_schema_migration(conn, 143, "qualite_referentiel_rse")


    # v144 - Qualite Referentiel : enrichissement des fiches seedees
    # Remplit le champ details (3-4 actions concretes par fiche) + met a jour source_url.
    # UPDATE idempotent : ne touche PAS aux fiches deja editees manuellement (details != '').
    # Rejoue-able sans effet secondaire.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=144 LIMIT 1").fetchone():
        _now_iso_144 = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        _seed_details = [
            ("reach", "https://echa.europa.eu/candidate-list-table", """Actions concretes a mettre en place chez SIFA :
1. Recenser toutes les substances chimiques utilisees en production (colles, encres, solvants, additifs) et leur reference CAS.
2. Cross-checker chaque substance sur la Candidate List SVHC de l ECHA (mise a jour semestrielle).
3. Exiger de chaque fournisseur chimique une declaration REACH annuelle + notification si changement de formulation.
4. Tenir a jour un registre substances / fournisseurs / date de derniere verification, accessible en cas d audit client.

Ressources :
- Liste des substances candidates SVHC : https://echa.europa.eu/candidate-list-table
- Comprendre REACH : https://echa.europa.eu/regulations/reach/understanding-reach"""),
            ("rohs", "https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en", """Actions concretes a mettre en place chez SIFA :
1. Verifier si nos produits ou emballages contiennent des composants electriques/electroniques (EEE) : peu probable pour l activite standard.
2. Si applicable : collecter les declarations RoHS des fournisseurs concernes (10 substances restreintes).
3. Documenter le niveau de conformite par famille de produit.
4. Reponse type client si non applicable : "SIFA n est pas fabricant d equipements electriques ou electroniques. Nos matieres ne contiennent pas les substances restreintes RoHS."

Ressources :
- Directive officielle : https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en"""),
            ("pop", "https://www.pops.int/TheConvention/ThePOPs/ListingofPOPs/tabid/2509/Default.aspx", """Actions concretes a mettre en place chez SIFA :
1. Verifier que nos matieres premieres ne contiennent aucun POP liste (annexes A/B/C de la Convention de Stockholm).
2. Recoupement partiel avec REACH SVHC : si une substance est SVHC + POP, double alerte.
3. Reponse standard client : declaration ecrite sur demande, basee sur les FDS et declarations fournisseurs.

Ressources :
- Liste officielle des POP : https://www.pops.int/TheConvention/ThePOPs/ListingofPOPs/tabid/2509/Default.aspx
- Reglement UE 2019/1021 : https://eur-lex.europa.eu/eli/reg/2019/1021"""),
            ("cov-voc", "https://www.ademe.fr/", """Actions concretes a mettre en place chez SIFA :
1. Recenser toutes les colles, encres et solvants utilises et leur teneur en COV (via FDS section 9 et section 3).
2. Etablir un bilan annuel des emissions COV (kg / an) pour l ensemble du site.
3. Substituer progressivement vers des alternatives base eau ou faible COV quand la performance produit le permet.
4. Verifier le respect des VLEP (valeurs limites d exposition professionnelle) pour les operateurs exposes.

Ressources :
- Guide ADEME COV : https://librairie.ademe.fr/
- Fiches INRS solvants : https://www.inrs.fr/risques/cmr-agents-chimiques/ce-qu-il-faut-retenir.html"""),
            ("iso-14001", "https://www.iso.org/fr/iso-14001-environmental-management.html", """Actions concretes a mettre en place chez SIFA :
1. Rediger et faire signer la politique environnementale par la direction.
2. Identifier les aspects environnementaux significatifs : consommations (elec, eau, gaz), dechets (tonnages par filiere), rejets atmospheriques et aqueux.
3. Definir un plan de progres annuel avec 3-5 objectifs mesurables (ex : -10 % dechets non tries, -5 % kWh/unite).
4. Realiser une revue de direction annuelle formalisee (compte-rendu ecrit).
5. Certifier si demande client recurrente. Cout indicatif PME : 3 a 8 kâ‚¬ / an (Bureau Veritas, AFNOR, SGS).

Ressources :
- Norme officielle : https://www.iso.org/fr/iso-14001-environmental-management.html"""),
            ("iso-50001", "https://www.iso.org/fr/iso-50001-energy-management.html", """Actions concretes a mettre en place chez SIFA :
1. Mesurer la consommation energetique par ligne / atelier / poste (sous-comptage electrique).
2. Identifier les Usages Energetiques Significatifs (UES) : machines de production, compresseur, chauffage.
3. Definir un plan d amelioration : eclairage LED, variateurs de vitesse, isolation, recuperation de chaleur, arret sequentiel.
4. Suivre l indicateur kWh consommes / unite produite pour piloter la performance.
5. Certification pertinente si consommation > 1 GWh/an ou demande client explicite.

Ressources :
- Norme officielle : https://www.iso.org/fr/iso-50001-energy-management.html
- Aides ADEME : https://agirpourlatransition.ademe.fr/entreprises/"""),
            ("emas", "https://green-business.ec.europa.eu/eco-management-and-audit-scheme-emas_en", """Actions concretes a mettre en place chez SIFA :
1. Prerequis : demarche ISO 14001 deja en place, EMAS est une surcouche publique.
2. Rediger et publier une declaration environnementale accessible au public (site web, doc telechargeable).
3. Faire enregistrer le site aupres de la DREAL (autorite competente en France).
4. Verification externe annuelle par un verificateur accredite.
5. Marketing : logo EMAS utilisable sur communications, differenciant vs ISO 14001.

Ressources :
- Portail EMAS UE : https://green-business.ec.europa.eu/eco-management-and-audit-scheme-emas_en"""),
            ("pefc", "https://www.pefc.fr/", """Actions concretes a mettre en place chez SIFA :
1. Applicable uniquement si nous transformons du bois, papier, carton ou fibre cellulosique.
2. Certification Chaine de Controle (CoC) pour tracer la matiere PEFC de l entree au produit fini.
3. Documenter chaque lot MP avec sa certification amont (facture + declaration fournisseur PEFC).
4. Former les operateurs a la separation stricte des flux PEFC / non-PEFC pendant la production.
5. Audit externe annuel par un organisme accredite (Bureau Veritas, SGS, FCBA).

Ressources :
- PEFC France : https://www.pefc.fr/
- Recherche fournisseurs certifies : https://www.pefc.fr/rechercher-certifie-pefc"""),
            ("fsc", "https://fr.fsc.org/", """Actions concretes a mettre en place chez SIFA :
1. Meme logique que PEFC (norme concurrente) : certification Chaine de Controle FSC.
2. Determiner la variante requise par les clients : FSC 100 %, FSC Mix, FSC Recycled.
3. Certains secteurs (edition, luxe, cosmetique) exigent FSC specifiquement.
4. Documentation lot par lot + comptabilite matiere annuelle.
5. Auditeur externe annuel (SGS, Bureau Veritas, FCBA, ECOCERT).

Ressources :
- FSC France : https://fr.fsc.org/
- Recherche certifies : https://fr.fsc.org/fr-fr/annuaire"""),
            ("ademe-acv", "https://bilans-ges.ademe.fr/", """Actions concretes a mettre en place chez SIFA :
1. Realiser un Bilan Carbone Scope 1 + 2 chaque annee (obligatoire au-dela de 500 salaries, tres recommande en dessous).
2. Estimer le Scope 3 (achats, transport aval, dechets, deplacements domicile-travail) â€” souvent 70 % du total pour une PME industrielle.
3. Utiliser la Base Empreinte ADEME pour les facteurs d emission fiables et opposables.
4. Publier un plan de reduction sur 3 a 5 ans avec objectifs chiffres.
5. Reponse type client : partager le Bilan Carbone consolide et les initiatives de reduction.

Ressources :
- Base Empreinte : https://base-empreinte.ademe.fr/
- Bilan GES ADEME : https://bilans-ges.ademe.fr/"""),
            ("ghg-protocol", "https://ghgprotocol.org/", """Actions concretes a mettre en place chez SIFA :
1. Etendre le Bilan Carbone au format GHG Protocol si client international (US, UK, Asie) le demande.
2. Scope 1 : emissions directes (chaudiere gaz, camions internes, gaz refrigerants HFC).
3. Scope 2 : electricite achetee (facteur emission fournisseur ou grid moyen).
4. Scope 3 : upstream (achats de MP) + downstream (transport client, fin de vie). Le plus complexe mais souvent le plus lourd.
5. Verification par un tiers (assurance limited/reasonable) si le client l exige (SBTi, CDP).

Ressources :
- Standard officiel : https://ghgprotocol.org/
- SBTi (objectifs bases sur la science) : https://sciencebasedtargets.org/"""),
            ("ppwr", "https://environment.ec.europa.eu/topics/waste-and-recycling/packaging-waste_en", """Actions concretes a mettre en place chez SIFA :
1. Recenser tous les emballages livres au client (primaires, secondaires, tertiaires).
2. Objectif PPWR : reduire le poids et le volume, augmenter la part recyclee, favoriser le mono-materiau.
3. Verifier la recyclabilite (design for recycling) : eviter multi-couches non separables, encres migrantes, colles insolubles.
4. Suivre l entree en application : la plupart des articles s appliquent entre 2025 et 2030.
5. Anticiper les futures obligations sur le contenu recycle minimum (25-65 % selon type de plastique en 2030).

Ressources :
- Texte officiel UE : https://environment.ec.europa.eu/topics/waste-and-recycling/packaging-waste_en"""),
            ("loi-agec", "https://www.ecologie.gouv.fr/loi-anti-gaspillage-economie-circulaire", """Actions concretes a mettre en place chez SIFA :
1. Verifier notre adhesion aux eco-organismes REP applicables (Citeo pour emballages menagers, autres selon activite).
2. Payer la contribution REP annuelle (declaration en ligne + reglement).
3. Afficher le logo Triman + l Info-tri sur nos produits destines au consommateur final.
4. Interdire l usage de plastique a usage unique quand une alternative existe (obligation legale depuis 2021).
5. Documenter la fin de vie de nos produits pour les commerciaux (dossier RSE type).

Ressources :
- Loi AGEC : https://www.ecologie.gouv.fr/loi-anti-gaspillage-economie-circulaire
- Citeo (REP emballages) : https://www.citeo.com/"""),
            ("triman", "https://www.ecologie.gouv.fr/logo-triman-et-info-tri-signaletique-commune", """Actions concretes a mettre en place chez SIFA :
1. Verifier si nos produits sont destines au grand public (BtoC ou passage BtoB2C).
2. Ajouter le logo Triman + l Info-tri (couleur du bac) sur chaque emballage concerne.
3. Format : image visible, taille minimum 6 mm de hauteur, texte "Cet emballage se recycle".
4. Ne pas confondre avec le point vert (obsolete depuis 2017) â€” ne plus l apposer.
5. Sanction en cas d absence : jusqu a 15 000 â‚¬ par produit non conforme.

Ressources :
- Signaletique officielle : https://www.ecologie.gouv.fr/logo-triman-et-info-tri-signaletique-commune
- Info-Tri Citeo : https://www.citeo.com/info-tri"""),
            ("csrd", "https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en", """Actions concretes a mettre en place chez SIFA :
1. Verifier l assujettissement : seuils 250 salaries / 50 Mâ‚¬ CA / 25 Mâ‚¬ bilan (2 sur 3). SIFA probablement non assujetti direct.
2. MAIS nos clients grands comptes assujettis vont demander nos donnees ESG pour leur propre reporting.
3. Preparer un jeu minimal de datapoints ESRS pertinents : E1 (climat), E5 (economie circulaire), S1 (personnel), G1 (gouvernance).
4. Anticiper une augmentation forte des demandes clients CSRD des 2025.
5. Format standard : cle en main via Ecovadis ou reporting simplifie type "fiche RSE".

Ressources :
- CSRD officiel UE : https://finance.ec.europa.eu/capital-markets-union-and-financial-markets/company-reporting-and-auditing/company-reporting/corporate-sustainability-reporting_en
- Guide CSRD PME : https://www.efrag.org/"""),
            ("iso-26000", "https://www.iso.org/fr/iso-26000-social-responsibility.html", """Actions concretes a mettre en place chez SIFA :
1. Norme d orientation, NON certifiable â€” pas d audit ni de logo utilisable.
2. Utile comme cadre pour structurer la demarche RSE globale de SIFA.
3. 7 questions centrales a couvrir : gouvernance, droits humains, relations et conditions de travail, environnement, loyaute des pratiques, questions relatives aux consommateurs, communautes et developpement local.
4. Referencer ISO 26000 dans notre code de conduite interne et notre reporting RSE.
5. Peut servir de base pour preparer Ecovadis ou une certification ISO 14001/45001.

Ressources :
- Norme ISO 26000 : https://www.iso.org/fr/iso-26000-social-responsibility.html
- Guide AFNOR : https://normalisation.afnor.org/thematiques/iso-26000/"""),
            ("ecovadis", "https://ecovadis.com/fr/", """Actions concretes a mettre en place chez SIFA :
1. Preparer un dossier d evaluation Ecovadis (demandes recurrentes des grands comptes).
2. 4 piliers evalues : environnement, social et droits humains, ethique, achats responsables.
3. Objectif realiste PME : atteindre le medaille bronze (25-49) puis argent (50-64) en 2 ans.
4. Cout indicatif : ~500 a 2 000 â‚¬ / an selon taille (evaluation annuelle payante par la PME evaluee).
5. De plus en plus de clients (LVMH, L Oreal, Michelin, etc.) exigent un score Ecovadis minimum comme condition d achat.

Ressources :
- Portail Ecovadis : https://ecovadis.com/fr/
- Guide auto-evaluation : https://support.ecovadis.com/"""),
            ("sedex-smeta", "https://www.sedex.com/", """Actions concretes a mettre en place chez SIFA :
1. Alternative ou complement a Ecovadis, plus orientee audit sur site.
2. Inscription sur la plateforme Sedex + remplissage du SAQ (Self-Assessment Questionnaire).
3. Audit SMETA 4-piliers realise par un tiers accredite (Bureau Veritas, Intertek, SGS).
4. Duree : 1 a 2 jours sur site, cout indicatif : 2 a 5 kâ‚¬.
5. Rapport publie sur la plateforme, accessible aux clients membres qui le demandent.

Ressources :
- Sedex : https://www.sedex.com/
- Methodologie SMETA : https://www.sedex.com/our-services/smeta-audit/"""),
            ("sapin-ii", "https://www.agence-francaise-anticorruption.gouv.fr/", """Actions concretes a mettre en place chez SIFA :
1. Assujettissement direct si > 500 salaries et > 100 Mâ‚¬ CA â€” SIFA probablement en dessous.
2. Bonnes pratiques a adopter meme si non assujetti (attendu par les clients) :
3. Rediger un code de conduite anti-corruption + charte cadeaux et invitations.
4. Mettre en place un dispositif d alerte interne (canal confidentiel type Whispli ou boite email dediee).
5. Cartographier les risques de corruption par processus (achats, ventes, sous-traitance).
6. Formation annuelle des collaborateurs exposes (achats, commerciaux, direction).

Ressources :
- AFA : https://www.agence-francaise-anticorruption.gouv.fr/
- Referentiel AFA PME : https://www.agence-francaise-anticorruption.gouv.fr/fr/publications-outils"""),
            ("devoir-vigilance", "https://www.economie.gouv.fr/dgccrf/devoir-de-vigilance", """Actions concretes a mettre en place chez SIFA :
1. Non applicable direct a SIFA (seuil : 5 000 salaries en France ou 10 000 dans le monde).
2. MAIS repercussion via nos clients grands comptes assujettis (qui vont interroger la chaine d appro).
3. Preparer un plan de vigilance simplifie : cartographie des risques MP, code de conduite fournisseur, dispositif d alerte.
4. Reponse type client : "Nous n avons pas d obligation legale mais partageons ces valeurs, voici notre demarche."

Ressources :
- DGCCRF Devoir de vigilance : https://www.economie.gouv.fr/dgccrf/devoir-de-vigilance
- Loi nÂ° 2017-399 : https://www.legifrance.gouv.fr/loda/id/JORFTEXT000034290626/"""),
            ("code-conduite-fournisseur", "https://www.iso.org/fr/standard/63026.html", """Actions concretes a mettre en place chez SIFA :
1. Rediger un code de conduite fournisseur (2 a 3 pages maximum).
2. Points essentiels a couvrir : droits humains, travail des enfants, corruption, environnement, sante-securite au travail, respect des lois locales.
3. Faire signer le code aux fournisseurs strategiques (top 20 en CA) â€” condition d entree en relation commerciale.
4. Reviser le code annuellement, maintenir a jour la liste des signataires.
5. S appuyer sur le referentiel ISO 20400 (achats responsables) pour la structure.

Ressources :
- ISO 20400 (achats responsables) : https://www.iso.org/fr/standard/63026.html
- Modele code fournisseur : voir templates ObsAR ou Global Compact France"""),
            ("modern-slavery-act", "https://www.legislation.gov.uk/ukpga/2015/30/contents", """Actions concretes a mettre en place chez SIFA :
1. Loi britannique â€” concerne SIFA seulement si nous vendons au Royaume-Uni via une entite legale UK ou fournissons un client UK assujetti.
2. Sinon, non applicable directement mais une clause anti-esclavage moderne dans le code fournisseur est une bonne pratique.
3. Certains clients UK (retail, mode, distribution) exigent une declaration meme des fournisseurs non-UK.
4. Reponse type : declaration ecrite (1 page) confirmant l absence d esclavage moderne dans notre chaine d appro connue.

Ressources :
- Loi officielle : https://www.legislation.gov.uk/ukpga/2015/30/contents
- Guide UK gouvernement : https://www.gov.uk/government/publications/transparency-in-supply-chains-a-practical-guide"""),
            ("conflict-minerals", "https://policy.trade.ec.europa.eu/development-and-sustainability/conflict-minerals-regulation_en", """Actions concretes a mettre en place chez SIFA :
1. Concerne SIFA seulement si nous utilisons directement ou indirectement de l etain, du tantale, du tungstene ou de l or (composants electroniques, alliages, encres metalliques).
2. Verifier les FDS et declarations fournisseur pour identifier la presence eventuelle de ces 4 metaux.
3. Utiliser le template CMRT (Conflict Minerals Reporting Template) de la Responsible Minerals Initiative pour repondre aux clients.
4. Reponse type client si non applicable : declaration ecrite du non-usage des 3TG dans nos produits.

Ressources :
- Reglement UE : https://policy.trade.ec.europa.eu/development-and-sustainability/conflict-minerals-regulation_en
- Template CMRT : https://www.responsiblemineralsinitiative.org/"""),
            ("iso-9001", "https://www.iso.org/fr/iso-9001-quality-management.html", """Actions concretes a mettre en place chez SIFA :
1. Standard tres largement demande par les clients grands comptes â€” souvent bloquant pour rentrer en relation.
2. Systeme de management qualite documente : politique qualite, processus cartographies, procedures ecrites, indicateurs mesurables.
3. Revue de direction annuelle formalisee, audits internes semestriels, audit externe annuel.
4. Cout indicatif PME : 3 a 6 kâ‚¬ / an (Bureau Veritas, AFNOR, SGS, LRQA).
5. ROI evident : reduction des non-conformites, argument commercial fort, souvent en pack integre avec ISO 14001 / ISO 45001.

Ressources :
- Norme ISO 9001 : https://www.iso.org/fr/iso-9001-quality-management.html"""),
            ("tracabilite-lot", "", """Actions concretes a mettre en place chez SIFA :
1. Attribuer un NÂ° de lot unique a chaque matiere premiere entree en stock (deja fait via MyStock).
2. Lier chaque OF a ses lots MP consommes (fait via MyProd â€” saisie de production).
3. Conserver la trace en base pendant minimum 5 ans (10 ans pour l agroalimentaire et le medical).
4. En cas de rappel client : capacite a retrouver tous les OF impactes en moins d une heure via requete SQL sur mouvements_stock.no_dossier.
5. Realiser annuellement un exercice de mock-recall pour valider la chaine de tracabilite.

Ressources :
- ISO 22005 (tracabilite chaine agroalimentaire, applicable a d autres secteurs)"""),
            ("oeko-tex", "https://www.oeko-tex.com/fr/", """Actions concretes a mettre en place chez SIFA :
1. Concerne uniquement produits textiles, fibres, cuir ou accessoires textiles.
2. Si applicable : envoi d echantillons a un laboratoire OEKO-TEX (Testex, Hohenstein, Centexbel).
3. Certification valable 1 an, renouvelable â€” analyse chimique complete (colorants azoiques, phtalates, metaux lourds, etc.).
4. Cout indicatif : ~1 a 3 kâ‚¬ par article certifie.
5. Reponse standard client si non applicable : "SIFA ne fabrique pas de produits textiles, cette certification ne s applique pas a notre offre."

Ressources :
- Portail OEKO-TEX : https://www.oeko-tex.com/fr/
- Laboratoires accredites : https://www.oeko-tex.com/fr/institutes"""),
            ("gots", "https://global-standard.org/", """Actions concretes a mettre en place chez SIFA :
1. Certification textile bio (Global Organic Textile Standard) â€” pertinent uniquement si nous transformons coton bio, laine bio ou autres fibres bio certifiees.
2. Auditeur externe agree GOTS : ECOCERT, IMO-Control, Control Union.
3. Chaine de controle complete de la matiere premiere au produit fini (traceabilite lot par lot).
4. Interdit certains procedes chimiques : chlore, formaldehyde, colorants toxiques, OGM.
5. Volet social integre : conditions de travail equivalentes aux conventions OIT.

Ressources :
- GOTS officiel : https://global-standard.org/"""),
            ("iso-45001", "https://www.iso.org/fr/iso-45001-occupational-health-and-safety.html", """Actions concretes a mettre en place chez SIFA :
1. Systeme de management sante et securite au travail (norme qui remplace OHSAS 18001 depuis 2018).
2. Document Unique d Evaluation des Risques (DUER) obligatoire quel que soit l effectif â€” a mettre a jour annuellement.
3. Analyse systematique des accidents et presqu-accidents (arbre des causes).
4. Referent securite designe + CSE (Comite Social et Economique) actif.
5. Certification pertinente si demande client â€” souvent en pack systeme integre avec ISO 9001 et ISO 14001.

Ressources :
- Norme ISO 45001 : https://www.iso.org/fr/iso-45001-occupational-health-and-safety.html
- DUER (INRS) : https://www.inrs.fr/demarche/evaluation-risques-professionnels/document-unique.html"""),
            ("fds-sds", "https://echa.europa.eu/fr/safety-data-sheets", """Actions concretes a mettre en place chez SIFA :
1. Collecter la FDS de chaque produit chimique utilise (colles, encres, solvants, nettoyants, adjuvants).
2. Verifier la version : FDS obligatoirement au format REACH/CLP a 16 sections, en francais, datee de moins de 3 ans.
3. Rendre les FDS accessibles aux operateurs : classeur atelier plastifie + version numerique centralisee.
4. Reviser tous les 2 ans ou immediatement en cas de changement de formulation fournisseur.
5. Fournir les FDS au client final sur demande, en moins de 48h (obligation legale REACH article 31).

Ressources :
- Guide FDS ECHA : https://echa.europa.eu/fr/safety-data-sheets
- Format francais INRS : https://www.inrs.fr/publications/juridique/focus-juridiques/focus-fds.html"""),
            ("prop-65", "https://oehha.ca.gov/proposition-65", """Actions concretes a mettre en place chez SIFA :
1. Concerne SIFA seulement si nous vendons en Californie (direct ou via distributeur/marketplace US).
2. Verifier la presence eventuelle de substances de la Prop 65 List (~900 substances : plomb, phtalates, formaldehyde, BPA, etc.) dans nos produits.
3. Si presente : etiquette d avertissement obligatoire "WARNING: This product can expose you to chemicals including [nom substance] which is known to the State of California to cause cancer / birth defects."
4. Reponse type client US si absent : declaration ecrite de conformite ou d absence des substances listees.

Ressources :
- Liste officielle Prop 65 : https://oehha.ca.gov/proposition-65/proposition-65-list"""),
            ("pbt-vpvb", "https://echa.europa.eu/documents/10162/13628/pbt_evaluation_annex_xiii_reach_en.pdf", """Actions concretes a mettre en place chez SIFA :
1. Sous-critere REACH (annexe XIII) pour identifier les substances les plus preoccupantes : Persistantes, Bioaccumulables, Toxiques (PBT) ou tres Persistantes tres Bioaccumulables (vPvB).
2. Verifier via les FDS section 12 et les declarations fournisseur.
3. Peu de substances industrielles standards sont PBT/vPvB, mais certaines encres, colles et adjuvants specifiques peuvent l etre.
4. Reponse type client : "Nos matieres ne contiennent pas de substances PBT/vPvB identifiees dans nos FDS et declarations fournisseurs."

Ressources :
- Guide ECHA PBT/vPvB : https://echa.europa.eu/documents/10162/13628/pbt_evaluation_annex_xiii_reach_en.pdf"""),
        ]
        for slug, source_url, details in _seed_details:
            # Ne mettre a jour details que s il est vide (fiche non editee)
            conn.execute(
                "UPDATE qualite_ref_fiches SET details=?, updated_at=? WHERE slug=? AND (details IS NULL OR details='')",
                (details, _now_iso_144, slug),
            )
            # Mettre a jour source_url seulement si vide ET si on a une source
            if source_url:
                conn.execute(
                    "UPDATE qualite_ref_fiches SET source_url=?, updated_at=? WHERE slug=? AND (source_url IS NULL OR source_url='')",
                    (source_url, _now_iso_144, slug),
                )
        conn.commit()
        _record_schema_migration(conn, 144, "qualite_ref_details_v1")

    # v145 - Qualite Referentiel : questions clients type + reponses
    # Ajoute 2 a 4 paires Q/R par fiche seedee :
    #   - append d une section 'Questions type et reponses' au champ details
    #     (uniquement si le bloc n est pas deja present)
    #   - insertion des questions courtes dans qualite_ref_questions
    #     (pour alimenter la recherche et l auto-completion)
    # Idempotente via schema_migrations version=145 + verifs anti-doublons.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=145 LIMIT 1").fetchone():
        _now_iso_145 = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        _seed_qa = [
            ("reach", [
                ("Vos produits sont-ils conformes au reglement REACH ?",
                 "Oui. SIFA verifie annuellement chaque substance chimique utilisee (colles, encres, solvants) contre la Candidate List SVHC de l ECHA et exige une declaration REACH de nos fournisseurs."),
                ("Vos produits contiennent-ils des SVHC au-dessus de 0,1 % ?",
                 "Selon nos declarations fournisseurs et FDS a jour, aucun SVHC n est present au-dessus du seuil de 0,1 % dans nos produits standard. Confirmation ecrite disponible sur demande."),
                ("Pouvez-vous fournir une declaration de conformite REACH ?",
                 "Oui, sur simple demande. Delai indicatif : 48h ouvres."),
                ("Comment gerez-vous les mises a jour de la Candidate List ?",
                 "Nous verifions la Candidate List a chaque mise a jour semestrielle de l ECHA et actualisons notre registre substances / fournisseurs en consequence."),
            ]),
            ("rohs", [
                ("Vos produits sont-ils conformes RoHS ?",
                 "SIFA ne fabrique pas d equipements electriques ou electroniques (EEE), la directive RoHS ne nous concerne pas directement. Nos matieres premieres ne contiennent pas les 10 substances restreintes RoHS."),
                ("Fournissez-vous une declaration RoHS ?",
                 "Sur demande, nous emettons une lettre de conformite basee sur les declarations de nos fournisseurs et l usage de nos produits."),
                ("Utilisez-vous du plomb, mercure, cadmium ou chrome hexavalent ?",
                 "Non, aucune de ces substances n est presente dans nos formulations ou emballages standard."),
            ]),
            ("pop", [
                ("Vos produits contiennent-ils des polluants organiques persistants ?",
                 "Non. Nous verifions que nos matieres premieres ne contiennent aucun POP liste dans les annexes A/B/C de la Convention de Stockholm et le Reglement UE 2019/1021."),
                ("Pouvez-vous fournir une declaration ecrite POP ?",
                 "Oui, sur demande. Delai indicatif : 48h ouvres."),
                ("Comment verifiez-vous l absence de POP dans vos matieres ?",
                 "Cross-check des FDS et declarations fournisseurs avec la liste officielle des POP + recouvrement avec la Candidate List SVHC."),
            ]),
            ("cov-voc", [
                ("Quelle est la teneur en COV de vos produits ?",
                 "La teneur en COV varie selon la formulation. Les valeurs precises figurent en section 9 des FDS de chaque produit. Nos formulations base eau presentent une teneur COV inferieure a 5 %."),
                ("Publiez-vous un bilan annuel des emissions COV ?",
                 "Oui, nous mesurons annuellement nos emissions COV globales pour le suivi reglementaire. Synthese partageable sur demande."),
                ("Proposez-vous des alternatives faible COV ?",
                 "Oui, une part croissante de notre offre utilise des base eau ou des formulations a faible COV. Nous consulter pour le detail par gamme."),
            ]),
            ("iso-14001", [
                ("Etes-vous certifies ISO 14001 ?",
                 "[A completer selon statut SIFA : preciser oui/non, organisme certificateur et annee d obtention.]"),
                ("Avez-vous une politique environnementale ecrite ?",
                 "Oui, notre politique environnementale est signee par la direction et disponible sur demande. Elle couvre nos engagements sur consommations, dechets et rejets."),
                ("Quels indicateurs environnementaux suivez-vous ?",
                 "Suivi annuel des consommations energie / eau, des tonnages de dechets par filiere et des rejets atmospheriques significatifs."),
            ]),
            ("iso-50001", [
                ("Etes-vous certifies ISO 50001 ?",
                 "[A completer selon statut SIFA. Reponse par defaut : non certifies mais suivi actif de la consommation energetique avec plan d amelioration continue.]"),
                ("Avez-vous un plan de reduction energetique ?",
                 "Oui, plan pluriannuel : eclairage LED, variateurs de vitesse, isolation, recuperation de chaleur, arret sequentiel des equipements."),
                ("Suivez-vous un indicateur kWh par unite produite ?",
                 "Oui, indicateur mensuel par ligne de production. Historique disponible sur demande."),
            ]),
            ("emas", [
                ("Etes-vous enregistres EMAS ?",
                 "Non. EMAS exige une declaration environnementale publique et un enregistrement DREAL. Nous privilegions actuellement le referentiel ISO 14001."),
                ("Publiez-vous une declaration environnementale ?",
                 "Nous ne publions pas de declaration EMAS formelle. Notre reporting environnemental interne est partageable sur demande sous accord de confidentialite."),
            ]),
            ("pefc", [
                ("Vos produits sont-ils certifies PEFC ?",
                 "[A completer selon statut : si applicable, NÂ° certificat PEFC chaine de controle + annee d obtention. Sinon : non applicable a notre activite.]"),
                ("Pouvez-vous fournir un certificat PEFC par lot ?",
                 "Oui, sur demande nous fournissons la tracabilite PEFC lot par lot avec le certificat CoC correspondant."),
                ("Utilisez-vous du bois issu de forets certifiees ?",
                 "Nos matieres cellulosiques proviennent de fournisseurs certifies PEFC (ou FSC selon disponibilite et demande client)."),
            ]),
            ("fsc", [
                ("Vos produits sont-ils certifies FSC ?",
                 "[A completer selon statut : si applicable, NÂ° certificat FSC chaine de controle + variantes disponibles (100 %, Mix, Recycled).]"),
                ("Quelle difference entre FSC 100 %, FSC Mix et FSC Recycled ?",
                 "FSC 100 % : matiere integralement issue de forets certifiees FSC. FSC Mix : melange forets FSC + matiere recyclee + matiere controlee. FSC Recycled : 100 % recycle. La variante est precisee sur chaque commande."),
                ("Pouvez-vous fournir un certificat FSC par livraison ?",
                 "Oui, mention FSC + numero de certificat portee sur le bon de livraison et la facture."),
            ]),
            ("ademe-acv", [
                ("Realisez-vous un Bilan Carbone annuel ?",
                 "Oui, Bilan Carbone Scope 1 + 2 annuel selon methodologie ADEME. Estimation Scope 3 en cours de deploiement."),
                ("Quel est votre plan de reduction des emissions ?",
                 "Plan pluriannuel : optimisation energetique, decarbonation transport, achat d electricite verte, choix fournisseurs. Objectif chiffre communicable sur demande."),
                ("Pouvez-vous fournir votre bilan Scope 3 ?",
                 "Estimation Scope 3 en construction (achats, transport aval, dechets, fin de vie). Precision croissante annee apres annee."),
            ]),
            ("ghg-protocol", [
                ("Votre reporting carbone est-il compatible GHG Protocol ?",
                 "Oui, notre Bilan Carbone suit une methodologie compatible avec le standard GHG Protocol (Scope 1, 2, 3)."),
                ("Vos donnees Scope 3 sont-elles verifiees par un tiers ?",
                 "Verification tiers non systematique. Nous pouvons l organiser sur demande client si assurance limited ou reasonable requise (CDP, SBTi)."),
                ("Avez-vous des objectifs valides SBTi ?",
                 "Pas de validation SBTi a ce stade. Objectifs internes de reduction disponibles sur demande."),
            ]),
            ("ppwr", [
                ("Vos emballages sont-ils recyclables ?",
                 "Oui, emballages concus pour la recyclabilite : privilege du mono-materiau, absence de couches non-separables, encres non-migrantes."),
                ("Quel pourcentage de contenu recycle dans vos emballages plastiques ?",
                 "Taux variable selon la gamme. Integration progressive des objectifs PPWR (25-65 % selon type de plastique en 2030) dans notre roadmap R&D."),
                ("Anticipez-vous les nouvelles obligations PPWR 2025-2030 ?",
                 "Oui, veille reglementaire active. Chaque article est evalue pour identifier les evolutions produit necessaires avant les echeances applicables."),
            ]),
            ("loi-agec", [
                ("Etes-vous adherents a un eco-organisme REP ?",
                 "Oui, adhesion Citeo (emballages menagers) et paiement de la contribution REP annuelle. Autres filieres REP selon activite."),
                ("Affichez-vous le Triman sur vos emballages consommateur ?",
                 "Oui, sur les produits destines au grand public le logo Triman + Info-Tri est affiche conformement a la loi AGEC."),
                ("Comment gerez-vous l interdiction plastique a usage unique ?",
                 "Substitution active vers des alternatives compatibles quand la performance produit le permet."),
            ]),
            ("triman", [
                ("Vos emballages portent-ils le logo Triman ?",
                 "Oui, sur tous nos produits destines au grand public, avec l Info-Tri correspondant a la couleur du bac."),
                ("Le format du Triman est-il conforme aux exigences AGEC ?",
                 "Oui : image visible, taille minimum 6 mm, texte 'Cet emballage se recycle' avec les consignes de tri par materiau."),
                ("Fournissez-vous les visuels Triman aux clients ?",
                 "Oui, sur demande nous partageons les visuels haute definition et les specifications techniques."),
            ]),
            ("csrd", [
                ("Etes-vous concernes par la CSRD ?",
                 "SIFA n est pas assujettie directement (seuils non atteints). Nous preparons un jeu de donnees ESG pour repondre aux demandes de nos clients grands comptes assujettis."),
                ("Pouvez-vous nous fournir des datapoints ESRS ?",
                 "Oui, pour les principaux datapoints pertinents (E1 climat, E5 economie circulaire, S1 personnel, G1 gouvernance). Fiche synthese sur demande."),
                ("Serez-vous prets pour repondre a nos exigences CSRD 2025 ?",
                 "Oui, notre demarche est structuree pour repondre progressivement aux demandes clients au fil de l entree en vigueur de la CSRD."),
            ]),
            ("iso-26000", [
                ("Appliquez-vous les principes ISO 26000 ?",
                 "Oui, ISO 26000 sert de cadre a notre demarche RSE. Nous couvrons les 7 questions centrales : gouvernance, droits humains, relations de travail, environnement, loyaute, consommateurs, communautes."),
                ("Avez-vous un code de conduite RSE ?",
                 "Oui, code de conduite interne structure autour des 7 questions centrales ISO 26000. Disponible sur demande."),
                ("ISO 26000 est-elle certifiable ?",
                 "Non, ISO 26000 est une norme d orientation non certifiable. Nous nous appuyons dessus pour structurer notre demarche et repondre a Ecovadis / SMETA."),
            ]),
            ("ecovadis", [
                ("Etes-vous evalues Ecovadis ?",
                 "[A completer selon score reel : oui, medaille bronze / argent / or / platine avec score X/100 en annee. Ou : evaluation en cours, resultat attendu date.]"),
                ("Pouvez-vous partager votre scorecard Ecovadis ?",
                 "Oui, scorecard disponible via la plateforme Ecovadis a votre demande (autorisation de partage a activer cote SIFA)."),
                ("Renouvelez-vous votre evaluation annuellement ?",
                 "Oui, evaluation Ecovadis renouvelee chaque annee pour maintenir la certification a jour."),
            ]),
            ("sedex-smeta", [
                ("Etes-vous inscrits sur la plateforme Sedex ?",
                 "[A completer selon statut : oui, membre Sedex depuis annee, SAQ a jour, rapport SMETA disponible. Ou : non, nous privilegions Ecovadis.]"),
                ("Avez-vous passe un audit SMETA sur site ?",
                 "[Si applicable : oui, dernier audit SMETA 4-piliers realise en date par auditeur. Rapport accessible via Sedex.]"),
                ("Les resultats SMETA sont-ils partageables ?",
                 "Oui, via activation de partage sur la plateforme Sedex avec votre societe."),
            ]),
            ("sapin-ii", [
                ("Etes-vous assujettis a la loi Sapin II ?",
                 "Non, SIFA n atteint pas les seuils Sapin II (500 salaries + 100 Mâ‚¬ CA). Nous appliquons neanmoins les bonnes pratiques anti-corruption."),
                ("Avez-vous un code de conduite anti-corruption ?",
                 "Oui, code de conduite anti-corruption + charte cadeaux formalises. Signature par les collaborateurs concernes."),
                ("Avez-vous un dispositif d alerte interne ?",
                 "Oui, canal d alerte confidentiel accessible aux collaborateurs et parties prenantes. Contact disponible sur demande."),
            ]),
            ("devoir-vigilance", [
                ("Etes-vous soumis au devoir de vigilance ?",
                 "Non, SIFA n atteint pas le seuil legal (5 000 salaries en France ou 10 000 monde). Nous partageons neanmoins les valeurs de cette loi."),
                ("Avez-vous un plan de vigilance ?",
                 "Oui, plan de vigilance simplifie : cartographie des risques MP, code de conduite fournisseur, dispositif d alerte interne. Disponible sur demande."),
                ("Comment surveillez-vous votre chaine d approvisionnement ?",
                 "Evaluation annuelle de nos fournisseurs strategiques (top 20) sur criteres RSE + signature du code de conduite fournisseur SIFA."),
            ]),
            ("code-conduite-fournisseur", [
                ("Avez-vous un code de conduite fournisseur ?",
                 "Oui, code de conduite fournisseur SIFA (2-3 pages) signe par nos fournisseurs strategiques. Reference ISO 20400."),
                ("Quels sont les engagements exiges de vos fournisseurs ?",
                 "Droits humains, absence de travail des enfants, anti-corruption, respect environnemental, sante-securite au travail, respect des lois locales."),
                ("Pouvons-nous consulter votre code ?",
                 "Oui, transmission sur demande. Le code est revise annuellement."),
            ]),
            ("modern-slavery-act", [
                ("Etes-vous concernes par le Modern Slavery Act ?",
                 "Applicable si vente au Royaume-Uni via une entite UK. Sinon, non applicable direct. La clause anti-esclavage moderne est integree a notre code de conduite fournisseur."),
                ("Pouvez-vous emettre une declaration Modern Slavery ?",
                 "Oui, declaration ecrite (1 page) confirmant l absence d esclavage moderne connu dans notre chaine d approvisionnement. Delai : 5 jours ouvres."),
                ("Comment auditez-vous vos fournisseurs sur ce point ?",
                 "Evaluation annuelle top 20 fournisseurs + signature obligatoire du code de conduite SIFA (clauses anti-esclavage explicitement incluses)."),
            ]),
            ("conflict-minerals", [
                ("Utilisez-vous des mineraux de conflit (3TG) ?",
                 "SIFA n utilise pas directement d etain, tantale, tungstene ou or dans ses formulations standard. Verification realisee via FDS et declarations fournisseurs."),
                ("Fournissez-vous un CMRT ?",
                 "Oui, sur demande nous emettons un Conflict Minerals Reporting Template (CMRT) selon le format RMI."),
                ("Vos fournisseurs sont-ils certifies pour les 3TG ?",
                 "Pour les rares cas concernes, les fournisseurs doivent attester d un sourcing responsable via smelter validation ou certification equivalente."),
            ]),
            ("iso-9001", [
                ("Etes-vous certifies ISO 9001 ?",
                 "[A completer selon statut SIFA : oui, certifies par organisme depuis annee, NÂ° certificat. Ou : non certifies mais SMQ equivalent applique.]"),
                ("Puis-je consulter votre certificat ?",
                 "Oui, copie du certificat en cours de validite fournie sur simple demande."),
                ("Quelle est votre date d audit annuel ?",
                 "Audit externe annuel realise en [mois]. Prochain audit prevu en [date] â€” dates precises communicables sur demande."),
            ]),
            ("tracabilite-lot", [
                ("Etes-vous capable de tracer un lot fini vers ses matieres premieres ?",
                 "Oui, chaque OF est lie a ses lots MP consommes dans notre systeme (MyProd). Tracabilite lot par lot conservee 5 ans minimum."),
                ("En cas de rappel, en combien de temps identifiez-vous les lots concernes ?",
                 "Moins d une heure. Recherche via reference lot ou OF, extraction complete des livraisons impactees."),
                ("Combien de temps conservez-vous les enregistrements de tracabilite ?",
                 "Minimum 5 ans en base active (10 ans pour agroalimentaire et medical). Archivage securise au-dela."),
                ("Realisez-vous des exercices de mock-recall ?",
                 "Oui, exercice annuel de mock-recall pour valider la chaine de tracabilite de bout en bout."),
            ]),
            ("oeko-tex", [
                ("Vos produits sont-ils certifies OEKO-TEX Standard 100 ?",
                 "SIFA ne fabrique pas de produits textiles en standard, cette certification ne s applique pas a notre offre courante. Pour toute demande specifique, nous consulter."),
                ("Utilisez-vous des matieres OEKO-TEX certifiees ?",
                 "Selon la gamme et la demande client, matieres OEKO-TEX approvisionnables sur commande specifique."),
            ]),
            ("gots", [
                ("Vos produits sont-ils certifies GOTS ?",
                 "SIFA ne fabrique pas de produits textiles bio en standard. Sur demande specifique, sourcing GOTS possible pour projets dedies."),
                ("Utilisez-vous du coton bio certifie ?",
                 "Non en standard. Sourcing possible pour projets specifiques via fournisseurs certifies GOTS."),
            ]),
            ("iso-45001", [
                ("Etes-vous certifies ISO 45001 ?",
                 "[A completer selon statut : oui, certifies depuis annee. Ou : non certifies mais SMS equivalent applique.]"),
                ("Avez-vous un DUER a jour ?",
                 "Oui, Document Unique d Evaluation des Risques mis a jour annuellement. Consultation sur demande sous confidentialite."),
                ("Quel est votre taux de frequence des accidents (TF) ?",
                 "Indicateur suivi mensuellement. Donnee agregee annuelle disponible sur demande."),
                ("Avez-vous un CSE et un referent securite ?",
                 "Oui, CSE actif et referent securite designe. Reunions mensuelles avec compte-rendu."),
            ]),
            ("fds-sds", [
                ("Fournissez-vous les FDS de vos produits ?",
                 "Oui, FDS au format REACH/CLP (16 sections) en francais, transmises sur demande. Delai : 24-48h ouvres."),
                ("Vos FDS sont-elles a jour ?",
                 "Oui, revision tous les 2 ans ou immediatement en cas de changement de formulation fournisseur."),
                ("Vos operateurs ont-ils acces aux FDS ?",
                 "Oui, classeur atelier plastifie + version numerique centralisee accessible en permanence."),
                ("Pouvons-nous recevoir les FDS de tous vos produits en une fois ?",
                 "Oui, envoi groupe possible sous format PDF ou lien de partage."),
            ]),
            ("prop-65", [
                ("Vos produits sont-ils conformes California Prop 65 ?",
                 "Nos produits standard ne contiennent pas de substances de la Prop 65 List au-dessus des seuils Safe Harbor. Verification lot par lot pour les commandes destinees a la Californie."),
                ("Vos produits necessitent-ils un etiquetage Prop 65 ?",
                 "Non en standard. Si presence identifiee, etiquette d avertissement 'WARNING' appliquee conformement a la reglementation."),
                ("Pouvez-vous fournir une declaration de non-usage des substances Prop 65 ?",
                 "Oui, sur demande pour les livraisons destinees a la Californie."),
            ]),
            ("pbt-vpvb", [
                ("Vos produits contiennent-ils des substances PBT ou vPvB ?",
                 "Non, aucune substance PBT ou vPvB identifiee dans nos matieres premieres selon les FDS et declarations fournisseurs."),
                ("Comment verifiez-vous l absence de PBT/vPvB ?",
                 "Verification via FDS section 12 (ecotoxicologie) et declarations fournisseurs. Cross-check avec la Candidate List SVHC de l ECHA."),
                ("Pouvez-vous fournir une declaration ecrite ?",
                 "Oui, sur demande. Delai : 48h ouvres."),
            ]),
        ]
        _qa_marker = "Questions type et reponses :"
        for slug, qa_list in _seed_qa:
            row = conn.execute("SELECT id, details FROM qualite_ref_fiches WHERE slug=?", (slug,)).fetchone()
            if not row:
                continue
            fid = row["id"]
            cur_details = row["details"] or ""
            if _qa_marker not in cur_details:
                block_lines = [_qa_marker, ""]
                for q, r in qa_list:
                    block_lines.append("Q : " + q)
                    block_lines.append("R : " + r)
                    block_lines.append("")
                separator = "\n\n---\n\n" if cur_details.strip() else ""
                new_details = cur_details + separator + "\n".join(block_lines).rstrip()
                conn.execute(
                    "UPDATE qualite_ref_fiches SET details=?, updated_at=? WHERE id=?",
                    (new_details, _now_iso_145, fid),
                )
            for q, _r in qa_list:
                exist = conn.execute(
                    "SELECT 1 FROM qualite_ref_questions WHERE fiche_id=? AND texte=?",
                    (fid, q),
                ).fetchone()
                if not exist:
                    conn.execute(
                        "INSERT INTO qualite_ref_questions (fiche_id, texte, created_at) VALUES (?, ?, ?)",
                        (fid, q, _now_iso_145),
                    )
        conn.commit()
        _record_schema_migration(conn, 145, "qualite_ref_qa_v1")

    # v146 - Qualite Referentiel : refactor Q/R en accordeon
    # - Ajoute une colonne 'reponse' TEXT DEFAULT '' a qualite_ref_questions
    # - Populate les reponses depuis le seed pour les questions inserees en v145
    # - Nettoie le champ 'details' en retirant le bloc 'Questions type et reponses'
    #   (les reponses vivent maintenant sur chaque question, affichees en accordeon)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=146 LIMIT 1").fetchone():
        _now_iso_146 = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

        # 1) Ajouter la colonne reponse si elle n existe pas
        cols = {r[1] for r in conn.execute("PRAGMA table_info(qualite_ref_questions)").fetchall()}
        if "reponse" not in cols:
            conn.execute("ALTER TABLE qualite_ref_questions ADD COLUMN reponse TEXT NOT NULL DEFAULT ''")

        # 2) Populate les reponses pour les questions seedees
        _seed_qa146 = [
            ("reach", [
                ("Vos produits sont-ils conformes au reglement REACH ?", "Oui. SIFA verifie annuellement chaque substance chimique utilisee (colles, encres, solvants) contre la Candidate List SVHC de l ECHA et exige une declaration REACH de nos fournisseurs."),
                ("Vos produits contiennent-ils des SVHC au-dessus de 0,1 % ?", "Selon nos declarations fournisseurs et FDS a jour, aucun SVHC n est present au-dessus du seuil de 0,1 % dans nos produits standard. Confirmation ecrite disponible sur demande."),
                ("Pouvez-vous fournir une declaration de conformite REACH ?", "Oui, sur simple demande. Delai indicatif : 48h ouvres."),
                ("Comment gerez-vous les mises a jour de la Candidate List ?", "Nous verifions la Candidate List a chaque mise a jour semestrielle de l ECHA et actualisons notre registre substances / fournisseurs en consequence."),
            ]),
            ("rohs", [
                ("Vos produits sont-ils conformes RoHS ?", "SIFA ne fabrique pas d equipements electriques ou electroniques (EEE), la directive RoHS ne nous concerne pas directement. Nos matieres premieres ne contiennent pas les 10 substances restreintes RoHS."),
                ("Fournissez-vous une declaration RoHS ?", "Sur demande, nous emettons une lettre de conformite basee sur les declarations de nos fournisseurs et l usage de nos produits."),
                ("Utilisez-vous du plomb, mercure, cadmium ou chrome hexavalent ?", "Non, aucune de ces substances n est presente dans nos formulations ou emballages standard."),
            ]),
            ("pop", [
                ("Vos produits contiennent-ils des polluants organiques persistants ?", "Non. Nous verifions que nos matieres premieres ne contiennent aucun POP liste dans les annexes A/B/C de la Convention de Stockholm et le Reglement UE 2019/1021."),
                ("Pouvez-vous fournir une declaration ecrite POP ?", "Oui, sur demande. Delai indicatif : 48h ouvres."),
                ("Comment verifiez-vous l absence de POP dans vos matieres ?", "Cross-check des FDS et declarations fournisseurs avec la liste officielle des POP + recouvrement avec la Candidate List SVHC."),
            ]),
            ("cov-voc", [
                ("Quelle est la teneur en COV de vos produits ?", "La teneur en COV varie selon la formulation. Les valeurs precises figurent en section 9 des FDS de chaque produit. Nos formulations base eau presentent une teneur COV inferieure a 5 %."),
                ("Publiez-vous un bilan annuel des emissions COV ?", "Oui, nous mesurons annuellement nos emissions COV globales pour le suivi reglementaire. Synthese partageable sur demande."),
                ("Proposez-vous des alternatives faible COV ?", "Oui, une part croissante de notre offre utilise des base eau ou des formulations a faible COV. Nous consulter pour le detail par gamme."),
            ]),
            ("iso-14001", [
                ("Etes-vous certifies ISO 14001 ?", "[A completer selon statut SIFA : preciser oui/non, organisme certificateur et annee d obtention.]"),
                ("Avez-vous une politique environnementale ecrite ?", "Oui, notre politique environnementale est signee par la direction et disponible sur demande. Elle couvre nos engagements sur consommations, dechets et rejets."),
                ("Quels indicateurs environnementaux suivez-vous ?", "Suivi annuel des consommations energie / eau, des tonnages de dechets par filiere et des rejets atmospheriques significatifs."),
            ]),
            ("iso-50001", [
                ("Etes-vous certifies ISO 50001 ?", "[A completer selon statut SIFA. Reponse par defaut : non certifies mais suivi actif de la consommation energetique avec plan d amelioration continue.]"),
                ("Avez-vous un plan de reduction energetique ?", "Oui, plan pluriannuel : eclairage LED, variateurs de vitesse, isolation, recuperation de chaleur, arret sequentiel des equipements."),
                ("Suivez-vous un indicateur kWh par unite produite ?", "Oui, indicateur mensuel par ligne de production. Historique disponible sur demande."),
            ]),
            ("emas", [
                ("Etes-vous enregistres EMAS ?", "Non. EMAS exige une declaration environnementale publique et un enregistrement DREAL. Nous privilegions actuellement le referentiel ISO 14001."),
                ("Publiez-vous une declaration environnementale ?", "Nous ne publions pas de declaration EMAS formelle. Notre reporting environnemental interne est partageable sur demande sous accord de confidentialite."),
            ]),
            ("pefc", [
                ("Vos produits sont-ils certifies PEFC ?", "[A completer selon statut : si applicable, NÂ° certificat PEFC chaine de controle + annee d obtention. Sinon : non applicable a notre activite.]"),
                ("Pouvez-vous fournir un certificat PEFC par lot ?", "Oui, sur demande nous fournissons la tracabilite PEFC lot par lot avec le certificat CoC correspondant."),
                ("Utilisez-vous du bois issu de forets certifiees ?", "Nos matieres cellulosiques proviennent de fournisseurs certifies PEFC (ou FSC selon disponibilite et demande client)."),
            ]),
            ("fsc", [
                ("Vos produits sont-ils certifies FSC ?", "[A completer selon statut : si applicable, NÂ° certificat FSC chaine de controle + variantes disponibles (100 %, Mix, Recycled).]"),
                ("Quelle difference entre FSC 100 %, FSC Mix et FSC Recycled ?", "FSC 100 % : matiere integralement issue de forets certifiees FSC. FSC Mix : melange forets FSC + matiere recyclee + matiere controlee. FSC Recycled : 100 % recycle. La variante est precisee sur chaque commande."),
                ("Pouvez-vous fournir un certificat FSC par livraison ?", "Oui, mention FSC + numero de certificat portee sur le bon de livraison et la facture."),
            ]),
            ("ademe-acv", [
                ("Realisez-vous un Bilan Carbone annuel ?", "Oui, Bilan Carbone Scope 1 + 2 annuel selon methodologie ADEME. Estimation Scope 3 en cours de deploiement."),
                ("Quel est votre plan de reduction des emissions ?", "Plan pluriannuel : optimisation energetique, decarbonation transport, achat d electricite verte, choix fournisseurs. Objectif chiffre communicable sur demande."),
                ("Pouvez-vous fournir votre bilan Scope 3 ?", "Estimation Scope 3 en construction (achats, transport aval, dechets, fin de vie). Precision croissante annee apres annee."),
            ]),
            ("ghg-protocol", [
                ("Votre reporting carbone est-il compatible GHG Protocol ?", "Oui, notre Bilan Carbone suit une methodologie compatible avec le standard GHG Protocol (Scope 1, 2, 3)."),
                ("Vos donnees Scope 3 sont-elles verifiees par un tiers ?", "Verification tiers non systematique. Nous pouvons l organiser sur demande client si assurance limited ou reasonable requise (CDP, SBTi)."),
                ("Avez-vous des objectifs valides SBTi ?", "Pas de validation SBTi a ce stade. Objectifs internes de reduction disponibles sur demande."),
            ]),
            ("ppwr", [
                ("Vos emballages sont-ils recyclables ?", "Oui, emballages concus pour la recyclabilite : privilege du mono-materiau, absence de couches non-separables, encres non-migrantes."),
                ("Quel pourcentage de contenu recycle dans vos emballages plastiques ?", "Taux variable selon la gamme. Integration progressive des objectifs PPWR (25-65 % selon type de plastique en 2030) dans notre roadmap R&D."),
                ("Anticipez-vous les nouvelles obligations PPWR 2025-2030 ?", "Oui, veille reglementaire active. Chaque article est evalue pour identifier les evolutions produit necessaires avant les echeances applicables."),
            ]),
            ("loi-agec", [
                ("Etes-vous adherents a un eco-organisme REP ?", "Oui, adhesion Citeo (emballages menagers) et paiement de la contribution REP annuelle. Autres filieres REP selon activite."),
                ("Affichez-vous le Triman sur vos emballages consommateur ?", "Oui, sur les produits destines au grand public le logo Triman + Info-Tri est affiche conformement a la loi AGEC."),
                ("Comment gerez-vous l interdiction plastique a usage unique ?", "Substitution active vers des alternatives compatibles quand la performance produit le permet."),
            ]),
            ("triman", [
                ("Vos emballages portent-ils le logo Triman ?", "Oui, sur tous nos produits destines au grand public, avec l Info-Tri correspondant a la couleur du bac."),
                ("Le format du Triman est-il conforme aux exigences AGEC ?", "Oui : image visible, taille minimum 6 mm, texte 'Cet emballage se recycle' avec les consignes de tri par materiau."),
                ("Fournissez-vous les visuels Triman aux clients ?", "Oui, sur demande nous partageons les visuels haute definition et les specifications techniques."),
            ]),
            ("csrd", [
                ("Etes-vous concernes par la CSRD ?", "SIFA n est pas assujettie directement (seuils non atteints). Nous preparons un jeu de donnees ESG pour repondre aux demandes de nos clients grands comptes assujettis."),
                ("Pouvez-vous nous fournir des datapoints ESRS ?", "Oui, pour les principaux datapoints pertinents (E1 climat, E5 economie circulaire, S1 personnel, G1 gouvernance). Fiche synthese sur demande."),
                ("Serez-vous prets pour repondre a nos exigences CSRD 2025 ?", "Oui, notre demarche est structuree pour repondre progressivement aux demandes clients au fil de l entree en vigueur de la CSRD."),
            ]),
            ("iso-26000", [
                ("Appliquez-vous les principes ISO 26000 ?", "Oui, ISO 26000 sert de cadre a notre demarche RSE. Nous couvrons les 7 questions centrales : gouvernance, droits humains, relations de travail, environnement, loyaute, consommateurs, communautes."),
                ("Avez-vous un code de conduite RSE ?", "Oui, code de conduite interne structure autour des 7 questions centrales ISO 26000. Disponible sur demande."),
                ("ISO 26000 est-elle certifiable ?", "Non, ISO 26000 est une norme d orientation non certifiable. Nous nous appuyons dessus pour structurer notre demarche et repondre a Ecovadis / SMETA."),
            ]),
            ("ecovadis", [
                ("Etes-vous evalues Ecovadis ?", "[A completer selon score reel : oui, medaille bronze / argent / or / platine avec score X/100 en annee. Ou : evaluation en cours, resultat attendu date.]"),
                ("Pouvez-vous partager votre scorecard Ecovadis ?", "Oui, scorecard disponible via la plateforme Ecovadis a votre demande (autorisation de partage a activer cote SIFA)."),
                ("Renouvelez-vous votre evaluation annuellement ?", "Oui, evaluation Ecovadis renouvelee chaque annee pour maintenir la certification a jour."),
            ]),
            ("sedex-smeta", [
                ("Etes-vous inscrits sur la plateforme Sedex ?", "[A completer selon statut : oui, membre Sedex depuis annee, SAQ a jour, rapport SMETA disponible. Ou : non, nous privilegions Ecovadis.]"),
                ("Avez-vous passe un audit SMETA sur site ?", "[Si applicable : oui, dernier audit SMETA 4-piliers realise en date par auditeur. Rapport accessible via Sedex.]"),
                ("Les resultats SMETA sont-ils partageables ?", "Oui, via activation de partage sur la plateforme Sedex avec votre societe."),
            ]),
            ("sapin-ii", [
                ("Etes-vous assujettis a la loi Sapin II ?", "Non, SIFA n atteint pas les seuils Sapin II (500 salaries + 100 Mâ‚¬ CA). Nous appliquons neanmoins les bonnes pratiques anti-corruption."),
                ("Avez-vous un code de conduite anti-corruption ?", "Oui, code de conduite anti-corruption + charte cadeaux formalises. Signature par les collaborateurs concernes."),
                ("Avez-vous un dispositif d alerte interne ?", "Oui, canal d alerte confidentiel accessible aux collaborateurs et parties prenantes. Contact disponible sur demande."),
            ]),
            ("devoir-vigilance", [
                ("Etes-vous soumis au devoir de vigilance ?", "Non, SIFA n atteint pas le seuil legal (5 000 salaries en France ou 10 000 monde). Nous partageons neanmoins les valeurs de cette loi."),
                ("Avez-vous un plan de vigilance ?", "Oui, plan de vigilance simplifie : cartographie des risques MP, code de conduite fournisseur, dispositif d alerte interne. Disponible sur demande."),
                ("Comment surveillez-vous votre chaine d approvisionnement ?", "Evaluation annuelle de nos fournisseurs strategiques (top 20) sur criteres RSE + signature du code de conduite fournisseur SIFA."),
            ]),
            ("code-conduite-fournisseur", [
                ("Avez-vous un code de conduite fournisseur ?", "Oui, code de conduite fournisseur SIFA (2-3 pages) signe par nos fournisseurs strategiques. Reference ISO 20400."),
                ("Quels sont les engagements exiges de vos fournisseurs ?", "Droits humains, absence de travail des enfants, anti-corruption, respect environnemental, sante-securite au travail, respect des lois locales."),
                ("Pouvons-nous consulter votre code ?", "Oui, transmission sur demande. Le code est revise annuellement."),
            ]),
            ("modern-slavery-act", [
                ("Etes-vous concernes par le Modern Slavery Act ?", "Applicable si vente au Royaume-Uni via une entite UK. Sinon, non applicable direct. La clause anti-esclavage moderne est integree a notre code de conduite fournisseur."),
                ("Pouvez-vous emettre une declaration Modern Slavery ?", "Oui, declaration ecrite (1 page) confirmant l absence d esclavage moderne connu dans notre chaine d approvisionnement. Delai : 5 jours ouvres."),
                ("Comment auditez-vous vos fournisseurs sur ce point ?", "Evaluation annuelle top 20 fournisseurs + signature obligatoire du code de conduite SIFA (clauses anti-esclavage explicitement incluses)."),
            ]),
            ("conflict-minerals", [
                ("Utilisez-vous des mineraux de conflit (3TG) ?", "SIFA n utilise pas directement d etain, tantale, tungstene ou or dans ses formulations standard. Verification realisee via FDS et declarations fournisseurs."),
                ("Fournissez-vous un CMRT ?", "Oui, sur demande nous emettons un Conflict Minerals Reporting Template (CMRT) selon le format RMI."),
                ("Vos fournisseurs sont-ils certifies pour les 3TG ?", "Pour les rares cas concernes, les fournisseurs doivent attester d un sourcing responsable via smelter validation ou certification equivalente."),
            ]),
            ("iso-9001", [
                ("Etes-vous certifies ISO 9001 ?", "[A completer selon statut SIFA : oui, certifies par organisme depuis annee, NÂ° certificat. Ou : non certifies mais SMQ equivalent applique.]"),
                ("Puis-je consulter votre certificat ?", "Oui, copie du certificat en cours de validite fournie sur simple demande."),
                ("Quelle est votre date d audit annuel ?", "Audit externe annuel realise en [mois]. Prochain audit prevu en [date] â€” dates precises communicables sur demande."),
            ]),
            ("tracabilite-lot", [
                ("Etes-vous capable de tracer un lot fini vers ses matieres premieres ?", "Oui, chaque OF est lie a ses lots MP consommes dans notre systeme (MyProd). Tracabilite lot par lot conservee 5 ans minimum."),
                ("En cas de rappel, en combien de temps identifiez-vous les lots concernes ?", "Moins d une heure. Recherche via reference lot ou OF, extraction complete des livraisons impactees."),
                ("Combien de temps conservez-vous les enregistrements de tracabilite ?", "Minimum 5 ans en base active (10 ans pour agroalimentaire et medical). Archivage securise au-dela."),
                ("Realisez-vous des exercices de mock-recall ?", "Oui, exercice annuel de mock-recall pour valider la chaine de tracabilite de bout en bout."),
            ]),
            ("oeko-tex", [
                ("Vos produits sont-ils certifies OEKO-TEX Standard 100 ?", "SIFA ne fabrique pas de produits textiles en standard, cette certification ne s applique pas a notre offre courante. Pour toute demande specifique, nous consulter."),
                ("Utilisez-vous des matieres OEKO-TEX certifiees ?", "Selon la gamme et la demande client, matieres OEKO-TEX approvisionnables sur commande specifique."),
            ]),
            ("gots", [
                ("Vos produits sont-ils certifies GOTS ?", "SIFA ne fabrique pas de produits textiles bio en standard. Sur demande specifique, sourcing GOTS possible pour projets dedies."),
                ("Utilisez-vous du coton bio certifie ?", "Non en standard. Sourcing possible pour projets specifiques via fournisseurs certifies GOTS."),
            ]),
            ("iso-45001", [
                ("Etes-vous certifies ISO 45001 ?", "[A completer selon statut : oui, certifies depuis annee. Ou : non certifies mais SMS equivalent applique.]"),
                ("Avez-vous un DUER a jour ?", "Oui, Document Unique d Evaluation des Risques mis a jour annuellement. Consultation sur demande sous confidentialite."),
                ("Quel est votre taux de frequence des accidents (TF) ?", "Indicateur suivi mensuellement. Donnee agregee annuelle disponible sur demande."),
                ("Avez-vous un CSE et un referent securite ?", "Oui, CSE actif et referent securite designe. Reunions mensuelles avec compte-rendu."),
            ]),
            ("fds-sds", [
                ("Fournissez-vous les FDS de vos produits ?", "Oui, FDS au format REACH/CLP (16 sections) en francais, transmises sur demande. Delai : 24-48h ouvres."),
                ("Vos FDS sont-elles a jour ?", "Oui, revision tous les 2 ans ou immediatement en cas de changement de formulation fournisseur."),
                ("Vos operateurs ont-ils acces aux FDS ?", "Oui, classeur atelier plastifie + version numerique centralisee accessible en permanence."),
                ("Pouvons-nous recevoir les FDS de tous vos produits en une fois ?", "Oui, envoi groupe possible sous format PDF ou lien de partage."),
            ]),
            ("prop-65", [
                ("Vos produits sont-ils conformes California Prop 65 ?", "Nos produits standard ne contiennent pas de substances de la Prop 65 List au-dessus des seuils Safe Harbor. Verification lot par lot pour les commandes destinees a la Californie."),
                ("Vos produits necessitent-ils un etiquetage Prop 65 ?", "Non en standard. Si presence identifiee, etiquette d avertissement 'WARNING' appliquee conformement a la reglementation."),
                ("Pouvez-vous fournir une declaration de non-usage des substances Prop 65 ?", "Oui, sur demande pour les livraisons destinees a la Californie."),
            ]),
            ("pbt-vpvb", [
                ("Vos produits contiennent-ils des substances PBT ou vPvB ?", "Non, aucune substance PBT ou vPvB identifiee dans nos matieres premieres selon les FDS et declarations fournisseurs."),
                ("Comment verifiez-vous l absence de PBT/vPvB ?", "Verification via FDS section 12 (ecotoxicologie) et declarations fournisseurs. Cross-check avec la Candidate List SVHC de l ECHA."),
                ("Pouvez-vous fournir une declaration ecrite ?", "Oui, sur demande. Delai : 48h ouvres."),
            ]),
        ]
        for slug, qa_list in _seed_qa146:
            row = conn.execute("SELECT id FROM qualite_ref_fiches WHERE slug=?", (slug,)).fetchone()
            if not row:
                continue
            fid = row["id"]
            for q_texte, r_texte in qa_list:
                # UPDATE : ne remplit reponse que si actuellement vide (respecte les editions manuelles)
                conn.execute(
                    "UPDATE qualite_ref_questions SET reponse=? WHERE fiche_id=? AND texte=? AND (reponse IS NULL OR reponse='')",
                    (r_texte, fid, q_texte),
                )

        # 3) Nettoyer le bloc 'Questions type et reponses' du champ details
        # (les reponses vivent maintenant dans qualite_ref_questions.reponse)
        _marker_qa = "Questions type et reponses :"
        rows = conn.execute(
            "SELECT id, details FROM qualite_ref_fiches WHERE details LIKE ?",
            ("%" + _marker_qa + "%",),
        ).fetchall()
        for r in rows:
            d = r["details"] or ""
            idx = d.find(_marker_qa)
            if idx < 0:
                continue
            # Chercher le separateur '---' qui precede le bloc Q/R
            before = d[:idx]
            # Retirer le separateur \n---\n en fin de before, s il est present
            import re as _re146
            cleaned = _re146.sub(r"\n*-+\n*\Z", "", before).rstrip()
            conn.execute(
                "UPDATE qualite_ref_fiches SET details=?, updated_at=? WHERE id=?",
                (cleaned, _now_iso_146, r["id"]),
            )

        conn.commit()
        _record_schema_migration(conn, 146, "qualite_ref_qa_accordion")

    # v147 â€” Prix mÂ² distinct par laize pour les matiÃ¨res bobines (frontal/glassine/complexe).
    # Ajoute un flag prix_par_laize sur matieres_premieres (0=prix unique matiÃ¨re, 1=prix par laize)
    # et une colonne prix_eur_m2 sur mp_matiere_laizes pour stocker le prix distinct par laize.
    if not conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version=147 LIMIT 1"
    ).fetchone():
        mp_cols = {row[1] for row in conn.execute("PRAGMA table_info(matieres_premieres)").fetchall()}
        if "prix_par_laize" not in mp_cols:
            conn.execute(
                "ALTER TABLE matieres_premieres ADD COLUMN prix_par_laize INTEGER NOT NULL DEFAULT 0"
            )
        ml_cols = {row[1] for row in conn.execute("PRAGMA table_info(mp_matiere_laizes)").fetchall()}
        if "prix_eur_m2" not in ml_cols:
            conn.execute(
                "ALTER TABLE mp_matiere_laizes ADD COLUMN prix_eur_m2 REAL"
            )
        conn.commit()
        _record_schema_migration(conn, 147, "mp_prix_par_laize")

    # v148 â€” Prix â‚¬/mÂ² sur chaque mouvement d'entrÃ©e matiÃ¨re premiÃ¨re.
    # Permet de tracer le prix payÃ© Ã  chaque rÃ©ception pour les bobines et de calculer
    # un PMP (prix moyen pondÃ©rÃ©) automatique. NULL pour les mouvements sans prix connu.
    if not conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version=148 LIMIT 1"
    ).fetchone():
        mvt_cols = {row[1] for row in conn.execute("PRAGMA table_info(mp_mouvements)").fetchall()}
        if "prix_eur_m2" not in mvt_cols:
            conn.execute(
                "ALTER TABLE mp_mouvements ADD COLUMN prix_eur_m2 REAL"
            )
        conn.commit()
        _record_schema_migration(conn, 148, "mp_mouvements_prix_eur_m2")

    # v149 - MyProd x MyStock : tracabilite mouvement matiere -> dossier de prod.
    # - mp_mouvements.no_dossier   : dossier de production a l'origine du mouvement
    # - mp_mouvements.machine      : machine concernee (snapshot pour timeline)
    # - mp_mouvements.client       : client (snapshot pour timeline)
    # - mp_mouvements.designation  : designation dossier (snapshot pour timeline)
    # + index no_dossier pour l'endpoint unifie /api/fabrication/saisies-jour
    if not conn.execute(
        "SELECT 1 FROM schema_migrations WHERE version=150 LIMIT 1"
    ).fetchone():
        mvt_cols = {row[1] for row in conn.execute("PRAGMA table_info(mp_mouvements)").fetchall()}
        for col, sql in (
            ("no_dossier",  "ALTER TABLE mp_mouvements ADD COLUMN no_dossier TEXT"),
            ("machine",     "ALTER TABLE mp_mouvements ADD COLUMN machine TEXT"),
            ("client",      "ALTER TABLE mp_mouvements ADD COLUMN client TEXT"),
            ("designation", "ALTER TABLE mp_mouvements ADD COLUMN designation TEXT"),
        ):
            if col not in mvt_cols:
                conn.execute(sql)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mp_mvt_dossier ON mp_mouvements(no_dossier)"
        )
        conn.commit()
        _record_schema_migration(conn, 150, "mp_mouvements_dossier_link")

    # v149 - Documents maintenance : pieces jointes attachees a chaque code
    # (contrÃ´le ou intervention). Fichiers stockes sur disque sous
    # data/uploads/maintenance_docs/{code}/, metadata en base.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=149 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maintenance_docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                filename TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                size_bytes INTEGER,
                content_type TEXT,
                uploaded_by TEXT,
                uploaded_at TEXT NOT NULL,
                FOREIGN KEY (code) REFERENCES maintenance_codes(code) ON DELETE CASCADE
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_maint_docs_code ON maintenance_docs(code)")
        conn.commit()
        _record_schema_migration(conn, 149, "maintenance_docs_table")

    # v151 - Coffre RH : matricule sur users (matching bulletins par nom fichier)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=151 LIMIT 1").fetchone():
        cols_u = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "matricule" not in cols_u:
            conn.execute("ALTER TABLE users ADD COLUMN matricule TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_users_matricule ON users(matricule)")
        conn.commit()
        _record_schema_migration(conn, 151, "users_matricule")

    # v152 - Coffre RH : table documents_rh (bulletins de paie, contrats, attestations)
    # Stockage fichiers sur disque sous data/uploads/coffre_rh/{user_id}/, metadata en base.
    # Chaque doc a un type, une annee, un mois, un hash SHA256 pour detecter les modifs.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=152 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS documents_rh (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employe_user_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                annee INTEGER,
                mois INTEGER,
                libelle TEXT,
                fichier_path TEXT NOT NULL,
                fichier_nom TEXT,
                taille_bytes INTEGER,
                hash_sha256 TEXT,
                uploaded_by_user_id INTEGER,
                uploaded_by_nom TEXT,
                uploaded_at TEXT NOT NULL,
                distribue_at TEXT,
                consulte_at TEXT,
                visible_salarie INTEGER DEFAULT 1,
                deleted_at TEXT,
                deleted_by_nom TEXT,
                FOREIGN KEY (employe_user_id) REFERENCES users(id) ON DELETE CASCADE
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_docrh_user ON documents_rh(employe_user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_docrh_type ON documents_rh(type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_docrh_periode ON documents_rh(annee, mois)")
        conn.commit()
        _record_schema_migration(conn, 152, "documents_rh_table")

    # v153 - Coffre RH : table notes_de_frais (workflow salarie -> compta)
    # Statuts : brouillon, soumise, validee, payee, refusee.
    # Categorisation libre (champ texte). Justificatif optionnel.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=153 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS notes_de_frais (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employe_user_id INTEGER NOT NULL,
                date_frais TEXT NOT NULL,
                categorie TEXT,
                montant_ttc REAL NOT NULL DEFAULT 0,
                montant_tva REAL,
                description TEXT,
                justificatif_path TEXT,
                justificatif_nom TEXT,
                statut TEXT NOT NULL DEFAULT 'brouillon',
                created_at TEXT NOT NULL,
                soumise_at TEXT,
                validee_at TEXT,
                validee_by_user_id INTEGER,
                validee_by_nom TEXT,
                payee_at TEXT,
                payee_by_user_id INTEGER,
                payee_by_nom TEXT,
                motif_refus TEXT,
                note_interne TEXT,
                deleted_at TEXT,
                FOREIGN KEY (employe_user_id) REFERENCES users(id) ON DELETE CASCADE
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ndf_user ON notes_de_frais(employe_user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ndf_statut ON notes_de_frais(statut)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ndf_date ON notes_de_frais(date_frais)")
        conn.commit()
        _record_schema_migration(conn, 153, "notes_de_frais_table")

    # v154 - Coffre RH : journal d'acces (RGPD - trace consultation/download/print).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=154 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS documents_rh_access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                user_id INTEGER,
                user_nom TEXT,
                action TEXT NOT NULL,
                ip TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents_rh(id) ON DELETE CASCADE
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_docrh_log_doc ON documents_rh_access_log(document_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_docrh_log_user ON documents_rh_access_log(user_id)")
        conn.commit()
        _record_schema_migration(conn, 154, "documents_rh_access_log_table")

    # v155 â€” TÃ¢ches de maintenance assignÃ©es : une ligne = une occurrence
    # concrÃ¨te d'une opÃ©ration de maintenance (contrÃ´le ou intervention) Ã 
    # rÃ©aliser sur une machine, Ã  une date donnÃ©e, par un opÃ©rateur donnÃ©.
    # L'admin maintenance (LoÃ¯c) crÃ©e ces tÃ¢ches depuis la vue Planning et les
    # assigne aux opÃ©rateurs. Les opÃ©rateurs (rÃ´le `fabrication`) les
    # voient dans leur vue Â« Mes tÃ¢ches Â»
    # et les complÃ¨tent en fin de journÃ©e (durÃ©e rÃ©elle, piÃ¨ces changÃ©es,
    # observations, photos, statut final).
    #
    # `source` distingue les tÃ¢ches planifiÃ©es Ã  l'avance (`planifie`, cas
    # standard) des interventions non planifiÃ©es dÃ©clarÃ©es Ã  la volÃ©e par un
    # opÃ©rateur (`non_planifie`, ex. panne machine survenue en cours de session).
    #
    # `statut` suit le cycle de vie : a_faire â†’ en_cours â†’ termine (ou reporte
    # si l'opÃ©rateur ne peut pas la faire aujourd'hui).
    #
    # FK sur `maintenance_codes(code)` sans ON DELETE CASCADE : si un code est
    # supprimÃ© cÃ´tÃ© paramÃ¨tres, la contrainte empÃªchera la suppression tant que
    # des tÃ¢ches y font rÃ©fÃ©rence (Ã  condition que PRAGMA foreign_keys=ON), ce
    # qui protÃ¨ge l'historique. Ã€ terme on ajoutera plutÃ´t un flag `archived`
    # sur maintenance_codes pour dÃ©sactiver un code sans casser l'historique.
    #
    # `operator_id` est nullable : permet de crÃ©er une tÃ¢che non encore
    # assignÃ©e dans le planning (poche Ã  distribuer).
    #
    # NumÃ©ro v155 (et pas v151 comme initialement prÃ©vu) car les slots 151-154
    # ont Ã©tÃ© pris par les migrations RH (users_matricule, documents_rh_table,
    # notes_de_frais_table, documents_rh_access_log_table) mergÃ©es entre-temps.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=155 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maintenance_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_prevue TEXT NOT NULL,
                code TEXT NOT NULL,
                machine TEXT NOT NULL,
                operator_id INTEGER,
                statut TEXT NOT NULL DEFAULT 'a_faire',
                source TEXT NOT NULL DEFAULT 'planifie',
                duree_reelle_min INTEGER,
                pieces_changees TEXT,
                observations TEXT,
                photos_json TEXT,
                created_by INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                done_at TEXT,
                FOREIGN KEY (code) REFERENCES maintenance_codes(code),
                FOREIGN KEY (operator_id) REFERENCES users(id),
                FOREIGN KEY (created_by) REFERENCES users(id)
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_maint_tasks_op_date "
            "ON maintenance_tasks(operator_id, date_prevue)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_maint_tasks_date_machine "
            "ON maintenance_tasks(date_prevue, machine)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_maint_tasks_code "
            "ON maintenance_tasks(code)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_maint_tasks_statut "
            "ON maintenance_tasks(statut)"
        )
        conn.commit()
        _record_schema_migration(conn, 155, "maintenance_tasks_table")

    # v156 â€” MyExpÃ© : transporteurs avec numÃ©ros de tÃ©lÃ©phone multiples (numÃ©ro + service).
    # Ajoute contact_tels TEXT (JSON list de {numero, service}). Backfill depuis
    # contact_tel legacy : soit une string simple, soit plusieurs sÃ©parÃ©es par , ; ou saut de ligne.
    # NumÃ©ro v156 (initialement prÃ©vue en v155, renumÃ©rotÃ©e au merge staging pour ne pas
    # entrer en collision avec maintenance_tasks_table de LoÃ¯c, mergÃ©e le mÃªme jour).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=156 LIMIT 1").fetchone():
        import json as _json
        import re as _re
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_transporteurs)").fetchall()}
        if "contact_tels" not in cols:
            conn.execute("ALTER TABLE expe_transporteurs ADD COLUMN contact_tels TEXT")
        # Backfill : contact_tel legacy -> contact_tels JSON
        rows = conn.execute(
            "SELECT id, contact_tel, contact_tels FROM expe_transporteurs"
        ).fetchall()
        for r in rows:
            has_tels = bool((r["contact_tels"] or "").strip())
            if has_tels:
                continue
            old = (r["contact_tel"] or "").strip()
            if not old:
                conn.execute(
                    "UPDATE expe_transporteurs SET contact_tels=? WHERE id=?",
                    ("[]", r["id"]),
                )
                continue
            parts = []
            for chunk in _re.split(r"[,;\n\r\t]+", old):
                v = chunk.strip()
                if v:
                    parts.append({"numero": v, "service": ""})
            conn.execute(
                "UPDATE expe_transporteurs SET contact_tels=? WHERE id=?",
                (_json.dumps(parts, ensure_ascii=False), r["id"]),
            )
        conn.commit()
        _record_schema_migration(conn, 156, "expe_transporteurs_contact_tels")

    # v157 â€” CrÃ©neaux horaires sur les tÃ¢ches de maintenance : ajoute
    # heure_debut / heure_fin nullable Ã  maintenance_tasks. Les tÃ¢ches crÃ©Ã©es
    # depuis le calendrier admin (vues mois/semaine/jour) auront des crÃ©neaux
    # explicites ; les tÃ¢ches libres crÃ©Ã©es par un opÃ©rateur en cours de
    # session laissent ces champs vides.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=157 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(maintenance_tasks)").fetchall()}
        if "heure_debut" not in cols:
            conn.execute("ALTER TABLE maintenance_tasks ADD COLUMN heure_debut TEXT")
        if "heure_fin" not in cols:
            conn.execute("ALTER TABLE maintenance_tasks ADD COLUMN heure_fin TEXT")
        conn.commit()
        _record_schema_migration(conn, 157, "maintenance_tasks_time_slots")

    # v158 â€” Refonte du modÃ¨le Maintenance : passe d'un modÃ¨le plat
    # (1 maintenance_tasks = 1 op + 1 opÃ©rateur) Ã  un modÃ¨le 3-tables plus
    # riche :
    #   maintenance_events           : le crÃ©neau (machine, date, heures, source)
    #   maintenance_event_ops        : les N opÃ©rations d'un crÃ©neau (statut/saisie
    #                                  partagÃ©s par tout le groupe)
    #   maintenance_event_operators  : les M opÃ©rateurs assignÃ©s au crÃ©neau
    #
    # `updated_by` sur maintenance_event_ops assure la traÃ§abilitÃ© : on sait
    # quel membre du groupe a rempli / modifiÃ© quoi.
    #
    # La table `maintenance_tasks` (v155 + v157) devient obsolÃ¨te et est
    # supprimÃ©e : les rares tÃ¢ches dÃ©jÃ  crÃ©Ã©es en dev sont jetÃ©es.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=158 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maintenance_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine TEXT NOT NULL,
                date_prevue TEXT NOT NULL,
                heure_debut TEXT,
                heure_fin TEXT,
                source TEXT NOT NULL DEFAULT 'planifie',
                created_by INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_maint_events_date_machine "
            "ON maintenance_events(date_prevue, machine)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_maint_events_source "
            "ON maintenance_events(source)"
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maintenance_event_ops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                statut TEXT NOT NULL DEFAULT 'a_faire',
                duree_reelle_min INTEGER,
                pieces_changees TEXT,
                observations TEXT,
                photos_json TEXT,
                done_at TEXT,
                done_by INTEGER,
                updated_by INTEGER,
                updated_at TEXT,
                FOREIGN KEY (event_id) REFERENCES maintenance_events(id) ON DELETE CASCADE,
                FOREIGN KEY (code) REFERENCES maintenance_codes(code),
                FOREIGN KEY (done_by) REFERENCES users(id),
                FOREIGN KEY (updated_by) REFERENCES users(id),
                UNIQUE (event_id, code)
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_maint_event_ops_event "
            "ON maintenance_event_ops(event_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_maint_event_ops_code "
            "ON maintenance_event_ops(code)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_maint_event_ops_statut "
            "ON maintenance_event_ops(statut)"
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maintenance_event_operators (
                event_id INTEGER NOT NULL,
                operator_id INTEGER NOT NULL,
                PRIMARY KEY (event_id, operator_id),
                FOREIGN KEY (event_id) REFERENCES maintenance_events(id) ON DELETE CASCADE,
                FOREIGN KEY (operator_id) REFERENCES users(id)
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_maint_event_operators_op "
            "ON maintenance_event_operators(operator_id)"
        )
        # Suppression de l'ancienne table maintenance_tasks (v155 / v157).
        conn.execute("DROP TABLE IF EXISTS maintenance_tasks")
        conn.commit()
        _record_schema_migration(conn, 158, "maintenance_events_refonte")
    # v159 â€” Module MyLearning : e-learning avec habilitation progressive.
    # 7 tables couvrant catalogue formations, modules vidÃ©o YouTube,
    # quiz de validation, mapping formation â†’ permissions, progression
    # utilisateur, habilitations obtenues et parcours d'accueil par rÃ´le.
    # Voir app/core/permissions.py pour la liste des permission_code.
    #
    # Note importante : les ON DELETE CASCADE ci-dessous sont inactifs
    # tant que get_db() n'active pas PRAGMA foreign_keys=ON (cf. Ã©tape 3
    # admin CRUD : la suppression d'une formation devra explicitement
    # supprimer les modules, quiz, permissions, progression et habilitations
    # associÃ©s en Python, ou activer foreign_keys ponctuellement).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=159 LIMIT 1").fetchone():
        conn.executescript("""
            -- Catalogue des parcours de formation. Un parcours = un poste.
            CREATE TABLE IF NOT EXISTS formations (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                code         TEXT UNIQUE NOT NULL,       -- ex: 'operateur_cohesio'
                titre        TEXT NOT NULL,
                description  TEXT,
                role_cible   TEXT,                        -- rÃ´le mÃ©tier libre (ex: 'OpÃ©rateur CohÃ©sio')
                ordre        INTEGER DEFAULT 100,
                actif        INTEGER DEFAULT 1,
                cree_le      TEXT NOT NULL,
                maj_le       TEXT
            );

            -- Modules d'un parcours (chapitres vidÃ©o).
            CREATE TABLE IF NOT EXISTS formation_modules (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                formation_id INTEGER NOT NULL,
                ordre        INTEGER DEFAULT 100,
                titre        TEXT NOT NULL,
                description  TEXT,
                youtube_id   TEXT NOT NULL,               -- ID de la vidÃ©o YouTube (ex: 'dQw4w9WgXcQ')
                duree_sec    INTEGER DEFAULT 0,
                actif        INTEGER DEFAULT 1,
                cree_le      TEXT NOT NULL,
                FOREIGN KEY (formation_id) REFERENCES formations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_formation_modules_formation
                ON formation_modules(formation_id, ordre);

            -- Questions du quiz de fin de module. choix_json est un tableau
            -- JSON de chaÃ®nes (ex: ["Choix A","Choix B","Choix C","Choix D"]).
            CREATE TABLE IF NOT EXISTS formation_quiz (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id      INTEGER NOT NULL,
                ordre          INTEGER DEFAULT 100,
                question       TEXT NOT NULL,
                choix_json     TEXT NOT NULL,             -- JSON array
                bonne_reponse  INTEGER NOT NULL,          -- index 0-based dans choix_json
                explication    TEXT,
                FOREIGN KEY (module_id) REFERENCES formation_modules(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_formation_quiz_module
                ON formation_quiz(module_id, ordre);

            -- Mapping formation â†’ permissions dÃ©bloquÃ©es Ã  la validation.
            -- Une formation peut dÃ©bloquer plusieurs permissions (ex: le
            -- parcours "OpÃ©rateur CohÃ©sio" donne prod.saisie_operateur ET
            -- prod.suppression_saisie).
            CREATE TABLE IF NOT EXISTS formation_permissions (
                formation_id     INTEGER NOT NULL,
                permission_code  TEXT NOT NULL,
                PRIMARY KEY (formation_id, permission_code),
                FOREIGN KEY (formation_id) REFERENCES formations(id) ON DELETE CASCADE
            );

            -- Progression utilisateur module par module.
            -- pct_vu : 0-100 (%). quiz_score : 0-100 (%) ou NULL si pas de quiz.
            -- valide_le : timestamp ISO si module validÃ© (visionnage + quiz OK).
            CREATE TABLE IF NOT EXISTS user_progression (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                module_id  INTEGER NOT NULL,
                pct_vu     INTEGER DEFAULT 0,
                quiz_score INTEGER,
                valide_le  TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, module_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (module_id) REFERENCES formation_modules(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_user_progression_user
                ON user_progression(user_id);

            -- Cache dÃ©normalisÃ© des habilitations (permissions obtenues).
            -- AlimentÃ© quand tous les modules d'une formation sont validÃ©s.
            -- UtilisÃ© pour des lookup O(1) au moment du guard require_habilitation.
            CREATE TABLE IF NOT EXISTS user_habilitations (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                permission_code TEXT NOT NULL,
                formation_id    INTEGER NOT NULL,
                obtenu_le       TEXT NOT NULL,
                UNIQUE(user_id, permission_code),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (formation_id) REFERENCES formations(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_user_habilitations_user
                ON user_habilitations(user_id, permission_code);

            -- Parcours d'accueil obligatoire par rÃ´le.
            -- Ã€ la crÃ©ation d'un compte, le rÃ´le dÃ©termine 1..N parcours
            -- Ã  valider avant d'accÃ©der pleinement Ã  l'app.
            CREATE TABLE IF NOT EXISTS role_parcours_defaut (
                role         TEXT NOT NULL,
                formation_id INTEGER NOT NULL,
                PRIMARY KEY (role, formation_id),
                FOREIGN KEY (formation_id) REFERENCES formations(id) ON DELETE CASCADE
            );
        """)
        conn.commit()
        _record_schema_migration(conn, 159, "mylearning_module")

    # v160 â€” MyLearning step 2 : refonte du schÃ©ma modules pour supporter
    # plusieurs vidÃ©os par module + sÃ©paration stricte tracking vidÃ©o vs
    # validation module.
    #
    # Changements par rapport Ã  v159 :
    #   - formation_modules perd `youtube_id` et `duree_sec` (ces champs
    #     appartiennent dÃ©sormais Ã  formation_videos, N vidÃ©os par module).
    #   - Nouvelle table `formation_videos` (module_id, ordre, titre,
    #     youtube_id, duree_sec).
    #   - `user_progression` (v159) devient obsolÃ¨te â€” remplacÃ©e par :
    #       * user_video_progression : pct_vu par vidÃ©o (granulaire)
    #       * user_module_validation : quiz_score + valide_le par module
    #
    # Comme aucun contenu MyLearning n'a Ã©tÃ© crÃ©Ã© entre v159 et v160
    # (l'Ã©cran admin n'existait pas encore Ã  l'Ã©tape 1), le DROP + CREATE
    # est safe : aucune donnÃ©e perdue en prod comme en staging.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=160 LIMIT 1").fetchone():
        conn.executescript("""
            -- Purge des tables v159 qui changent de structure.
            DROP TABLE IF EXISTS formation_quiz;
            DROP TABLE IF EXISTS user_progression;
            DROP TABLE IF EXISTS formation_modules;

            -- Nouveau formation_modules (sans youtube_id / duree_sec).
            CREATE TABLE formation_modules (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                formation_id INTEGER NOT NULL,
                ordre        INTEGER DEFAULT 100,
                titre        TEXT NOT NULL,
                description  TEXT,
                actif        INTEGER DEFAULT 1,
                cree_le      TEXT NOT NULL,
                FOREIGN KEY (formation_id) REFERENCES formations(id) ON DELETE CASCADE
            );
            CREATE INDEX idx_formation_modules_formation_v2
                ON formation_modules(formation_id, ordre);

            -- VidÃ©os d'un module (N vidÃ©os possibles, ordonnÃ©es).
            CREATE TABLE formation_videos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id   INTEGER NOT NULL,
                ordre       INTEGER DEFAULT 100,
                titre       TEXT NOT NULL,
                youtube_id  TEXT NOT NULL,               -- 11 caractÃ¨res YouTube
                duree_sec   INTEGER DEFAULT 0,
                cree_le     TEXT NOT NULL,
                FOREIGN KEY (module_id) REFERENCES formation_modules(id) ON DELETE CASCADE
            );
            CREATE INDEX idx_formation_videos_module
                ON formation_videos(module_id, ordre);

            -- Quiz : questions QCM 4 choix, 1 bonne rÃ©ponse.
            -- Contrainte mÃ©tier (cÃ´tÃ© API) : au moins 1 question par module.
            CREATE TABLE formation_quiz (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                module_id      INTEGER NOT NULL,
                ordre          INTEGER DEFAULT 100,
                question       TEXT NOT NULL,
                choix_json     TEXT NOT NULL,             -- JSON array (gÃ©nÃ©ralement 4 choix)
                bonne_reponse  INTEGER NOT NULL,          -- index 0-based dans choix_json
                explication    TEXT,
                FOREIGN KEY (module_id) REFERENCES formation_modules(id) ON DELETE CASCADE
            );
            CREATE INDEX idx_formation_quiz_module_v2
                ON formation_quiz(module_id, ordre);

            -- Progression utilisateur au niveau vidÃ©o (granulaire).
            CREATE TABLE user_video_progression (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                video_id   INTEGER NOT NULL,
                pct_vu     INTEGER DEFAULT 0,             -- 0-100
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, video_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (video_id) REFERENCES formation_videos(id) ON DELETE CASCADE
            );
            CREATE INDEX idx_user_video_prog_user
                ON user_video_progression(user_id);

            -- Validation d'un module (quiz rÃ©ussi + toutes vidÃ©os vues).
            -- quiz_score : 0-100 (% de bonnes rÃ©ponses).
            -- valide_le : timestamp ISO si module validÃ©, NULL sinon.
            CREATE TABLE user_module_validation (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                module_id  INTEGER NOT NULL,
                quiz_score INTEGER,
                valide_le  TEXT,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, module_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (module_id) REFERENCES formation_modules(id) ON DELETE CASCADE
            );
            CREATE INDEX idx_user_module_valid_user
                ON user_module_validation(user_id);
        """)
        conn.commit()
        _record_schema_migration(conn, 160, "mylearning_videos_split")

    # â”€â”€â”€ v161 â€” MyTraduction : cache des traductions DeepL â”€â”€â”€â”€â”€â”€â”€â”€â”€
    #
    # Table de cache pour Ã©viter de repayer 2Ã— la mÃªme traduction (quota
    # DeepL Free = 500k car/mois). ClÃ© = hash(text + source_lang + target_lang
    # + formality). Les entrÃ©es ne sont jamais purgÃ©es automatiquement â€” un
    # mÃªme texte donne toujours la mÃªme traduction, autant garder le cache.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=161 LIMIT 1").fetchone():
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS translations_cache (
                hash         TEXT PRIMARY KEY,
                source_lang  TEXT,
                target_lang  TEXT NOT NULL,
                formality    TEXT,
                translated   TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                hit_count    INTEGER NOT NULL DEFAULT 1
            );
            CREATE INDEX IF NOT EXISTS idx_translations_cache_created
                ON translations_cache(created_at);

            -- Log d'utilisation par utilisateur (pour compteur mensuel + stats)
            CREATE TABLE IF NOT EXISTS translations_usage (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER,
                chars_count  INTEGER NOT NULL,
                cached       INTEGER NOT NULL DEFAULT 0,
                source_lang  TEXT,
                target_lang  TEXT NOT NULL,
                created_at   TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
            );
            CREATE INDEX IF NOT EXISTS idx_translations_usage_created
                ON translations_usage(created_at);
            CREATE INDEX IF NOT EXISTS idx_translations_usage_user
                ON translations_usage(user_id, created_at);
        """)
        conn.commit()
        _record_schema_migration(conn, 161, "mytraduction_cache")

    # v162 â€” Maintenance : opÃ©rations multi-machines dans un mÃªme crÃ©neau.
    # Un crÃ©neau (maintenance_events) peut dÃ©sormais contenir des opÃ©rations
    # rattachÃ©es Ã  des machines diffÃ©rentes. Chaque opÃ©ration stocke sa/ses
    # machines dans `maintenance_event_ops.machines_csv` (CSV, sÃ©parateur " Â· ").
    # `maintenance_events.machine` reste renseignÃ© en rÃ©sumÃ© (CSV) pour la
    # rÃ©trocompatibilitÃ© (palette calendrier, filtres, non_planifie).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=162 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(maintenance_event_ops)").fetchall()}
        if "machines_csv" not in cols:
            conn.execute("ALTER TABLE maintenance_event_ops ADD COLUMN machines_csv TEXT")
        # Backfill : pour chaque op existante sans machines_csv, on hÃ©rite de
        # la machine de son event (comportement d'avant la refonte).
        conn.execute("""
            UPDATE maintenance_event_ops
            SET machines_csv = (
                SELECT machine FROM maintenance_events WHERE id = maintenance_event_ops.event_id
            )
            WHERE machines_csv IS NULL OR machines_csv = ''
        """)
        conn.commit()
        _record_schema_migration(conn, 162, "maintenance_event_ops_machines_csv")

    # v163 â€” Maintenance : modÃ¨les de session (Â« templates Â»).
    # Un modÃ¨le = un ensemble prÃ©dÃ©fini d'opÃ©rations avec leurs machines,
    # qu'un admin peut instancier rapidement en tant que crÃ©neau. Les modifs
    # d'un modÃ¨le resynchronisent les crÃ©neaux futurs qui en dÃ©pendent
    # (Ã©crasement des ops locales).
    #
    # `maintenance_events.template_id` (nullable) trace la provenance d'un
    # crÃ©neau et pilote la resync. Sur suppression d'un modÃ¨le, ON DELETE
    # CASCADE cÃ´tÃ© events est INACTIF (foreign_keys pas activÃ©es globalement) :
    # la cascade est faite cÃ´tÃ© application dans le router.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=163 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maintenance_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_by INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                FOREIGN KEY (created_by) REFERENCES users(id)
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS maintenance_template_ops (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                machines_csv TEXT,
                FOREIGN KEY (template_id) REFERENCES maintenance_templates(id) ON DELETE CASCADE,
                FOREIGN KEY (code) REFERENCES maintenance_codes(code),
                UNIQUE (template_id, code)
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_maint_template_ops_template "
            "ON maintenance_template_ops(template_id)"
        )
        # Colonne template_id sur les crÃ©neaux (nullable = crÃ©neau autonome).
        cols_ev = {r["name"] for r in conn.execute("PRAGMA table_info(maintenance_events)").fetchall()}
        if "template_id" not in cols_ev:
            conn.execute("ALTER TABLE maintenance_events ADD COLUMN template_id INTEGER")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_maint_events_template "
            "ON maintenance_events(template_id)"
        )
        conn.commit()
        _record_schema_migration(conn, 163, "maintenance_templates")

    # v164 â€” Alertes maintenance : bouton "Fermer l'alerte" configurable.
    # Ajoute une colonne `dismissed` (0/1) sur maintenance_alert_acks. Les
    # rows dismissed=1 sont invisibles dans l'historique des contrÃ´les mais
    # servent Ã  dÃ©bloquer la logique event (l'alerte ne re-fire qu'au prochain
    # 89). Aucun log_action, aucune trace visible â†’ l'opÃ©rateur peut esquiver
    # une alerte non pertinente sans polluer la qualitÃ©.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=164 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(maintenance_alert_acks)").fetchall()}
        if "dismissed" not in cols:
            conn.execute("ALTER TABLE maintenance_alert_acks ADD COLUMN dismissed INTEGER NOT NULL DEFAULT 0")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_alert_acks_dismissed "
            "ON maintenance_alert_acks(dismissed, ack_at DESC)"
        )
        conn.commit()
        _record_schema_migration(conn, 164, "maintenance_alert_acks_dismissed")

    # v166 â€” QualitÃ© : split rÃ´le administration + traÃ§abilitÃ© de prise en connaissance des NC par service.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=166 LIMIT 1").fetchone():
        conn.execute(
            "UPDATE users SET role='administration_ventes' WHERE role='administration'"
        )
        ucols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "nc_service_override" not in ucols:
            conn.execute("ALTER TABLE users ADD COLUMN nc_service_override TEXT")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS nc_service_acknowledgments (
                nc_id INTEGER NOT NULL REFERENCES nc_dossiers(id) ON DELETE CASCADE,
                service TEXT NOT NULL,
                user_id INTEGER REFERENCES users(id),
                ack_at TEXT NOT NULL,
                PRIMARY KEY (nc_id, service)
            )
        """)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_nc_ack_service ON nc_service_acknowledgments(service)"
        )
        conn.commit()
        _record_schema_migration(conn, 166, "qualite_split_admin_role_and_nc_ack")

    # v167 â€” Fournisseurs : flag has_fsc (les existants restent certifiÃ©s)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=167 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(fournisseurs_fsc)").fetchall()}
        if "has_fsc" not in cols:
            try:
                conn.execute("ALTER TABLE fournisseurs_fsc ADD COLUMN has_fsc INTEGER NOT NULL DEFAULT 1")
            except Exception:
                pass
        conn.commit()
        _record_schema_migration(conn, 167, "fournisseurs_has_fsc_flag")

    # v168 â€” Liaison fournisseurs â†” (matiÃ¨re premiÃ¨re, laize)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=168 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS matiere_laize_fournisseurs (
                matiere_id     INTEGER NOT NULL,
                laize_id       INTEGER NOT NULL,
                fournisseur_id INTEGER NOT NULL,
                created_at     TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (matiere_id, laize_id, fournisseur_id),
                FOREIGN KEY (matiere_id)     REFERENCES matieres_premieres(id) ON DELETE CASCADE,
                FOREIGN KEY (fournisseur_id) REFERENCES fournisseurs_fsc(id)    ON DELETE CASCADE
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mlf_matiere ON matiere_laize_fournisseurs(matiere_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_mlf_fournisseur ON matiere_laize_fournisseurs(fournisseur_id)")
        conn.commit()
        _record_schema_migration(conn, 168, "matiere_laize_fournisseurs_link")

    # v169 â€” NumÃ©ro de lot sur les rÃ©ceptions matiÃ¨re
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=169 LIMIT 1").fetchone():
        sr_cols = {r["name"] for r in conn.execute("PRAGMA table_info(stock_receptions)").fetchall()}
        if "lot_numero" not in sr_cols:
            conn.execute("ALTER TABLE stock_receptions ADD COLUMN lot_numero TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_receptions_lot ON stock_receptions(lot_numero)")
        conn.commit()
        _record_schema_migration(conn, 169, "stock_receptions_lot_numero")

    # v170 â€” Inventaire matiÃ¨re : sessions + intervalle configurable par matiÃ¨re
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=170 LIMIT 1").fetchone():
        mp_cols = {r["name"] for r in conn.execute("PRAGMA table_info(matieres_premieres)").fetchall()}
        if "intervalle_inventaire_jours" not in mp_cols:
            conn.execute(
                "ALTER TABLE matieres_premieres ADD COLUMN intervalle_inventaire_jours INTEGER DEFAULT 180"
            )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS inventaires_matieres (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                matiere_id INTEGER NOT NULL REFERENCES matieres_premieres(id) ON DELETE CASCADE,
                laize_id INTEGER,
                quantite_avant REAL NOT NULL DEFAULT 0,
                quantite_comptee REAL NOT NULL DEFAULT 0,
                ecart REAL NOT NULL DEFAULT 0,
                commentaire TEXT,
                operateur_email TEXT,
                operateur_nom TEXT,
                date_validation TEXT NOT NULL,
                mouvement_id INTEGER REFERENCES mp_mouvements(id) ON DELETE SET NULL
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_inv_mat_matiere ON inventaires_matieres(matiere_id, date_validation DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_inv_mat_laize ON inventaires_matieres(matiere_id, laize_id, date_validation DESC)"
        )
        conn.commit()
        _record_schema_migration(conn, 170, "inventaires_matieres")

    # v171 â€” Module impression cloud (agents, imprimantes, templates, jobs)
    # Permet d'imprimer depuis le SaaS vers des imprimantes du LAN usine via un
    # agent local (Raspberry Pi ou PC) qui poll les jobs et les envoie en TCP:9100.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=171 LIMIT 1").fetchone():
        conn.execute("""CREATE TABLE IF NOT EXISTS print_agents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            token_hash TEXT NOT NULL UNIQUE,
            actif INTEGER NOT NULL DEFAULT 1,
            last_heartbeat TEXT,
            last_ip TEXT,
            created_at TEXT NOT NULL,
            note TEXT
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_print_agents_actif ON print_agents(actif)")
        conn.execute("""CREATE TABLE IF NOT EXISTS imprimantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            poste TEXT,
            agent_id INTEGER REFERENCES print_agents(id) ON DELETE SET NULL,
            ip_locale TEXT NOT NULL,
            port INTEGER NOT NULL DEFAULT 9100,
            langage TEXT NOT NULL DEFAULT 'zpl',
            largeur_mm INTEGER NOT NULL DEFAULT 102,
            hauteur_mm INTEGER NOT NULL DEFAULT 152,
            dpi INTEGER NOT NULL DEFAULT 203,
            actif INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            created_by TEXT,
            note TEXT
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_imprimantes_agent ON imprimantes(agent_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_imprimantes_actif ON imprimantes(actif)")
        conn.execute("""CREATE TABLE IF NOT EXISTS imprimante_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imprimante_id INTEGER NOT NULL REFERENCES imprimantes(id) ON DELETE CASCADE,
            usage_key TEXT NOT NULL,
            nom TEXT NOT NULL,
            contenu TEXT NOT NULL,
            actif INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL,
            updated_by TEXT
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_impr_tpl_imp_usage ON imprimante_templates(imprimante_id, usage_key)")
        conn.execute("""CREATE TABLE IF NOT EXISTS print_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            imprimante_id INTEGER NOT NULL REFERENCES imprimantes(id) ON DELETE CASCADE,
            agent_id INTEGER REFERENCES print_agents(id) ON DELETE SET NULL,
            usage_key TEXT,
            template_id INTEGER REFERENCES imprimante_templates(id) ON DELETE SET NULL,
            payload BLOB NOT NULL,
            payload_langage TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            created_by TEXT,
            picked_at TEXT,
            ack_at TEXT,
            erreur TEXT,
            tentatives INTEGER NOT NULL DEFAULT 0,
            data_json TEXT
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_print_jobs_status ON print_jobs(status, agent_id, imprimante_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_print_jobs_created ON print_jobs(created_at DESC)")
        conn.execute("""CREATE TABLE IF NOT EXISTS user_printer_defaults (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            usage_key TEXT NOT NULL,
            imprimante_id INTEGER NOT NULL REFERENCES imprimantes(id) ON DELETE CASCADE,
            updated_at TEXT NOT NULL,
            UNIQUE(user_email, usage_key)
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_user_printer_def_user ON user_printer_defaults(user_email)")
        conn.commit()
        _record_schema_migration(conn, 171, "print_module_tables")

    # v172 â€” MyBAT : ajout colonne fiche_technique ('a_faire' | 'fait')
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=172 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(bat_entries)").fetchall()}
        if "fiche_technique" not in cols:
            conn.execute(
                "ALTER TABLE bat_entries ADD COLUMN fiche_technique TEXT NOT NULL DEFAULT 'a_faire'"
            )
        conn.commit()
        _record_schema_migration(conn, 172, "bat_entries_fiche_technique")

    # v173 â€” MyQualitÃ© : Ressources Fournisseurs (certificats par fournisseur,
    # liens N-N vers fiches du rÃ©fÃ©rentiel RSE, log annonces d'expiration).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=173 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS qualite_fournisseur_certificats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fournisseur_id INTEGER NOT NULL REFERENCES fournisseurs_fsc(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                original_name TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER,
                titre TEXT NOT NULL DEFAULT '',
                date_emission TEXT,
                date_expiration TEXT,
                commentaire TEXT NOT NULL DEFAULT '',
                uploaded_at TEXT NOT NULL,
                uploaded_by INTEGER REFERENCES users(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qfc_four ON qualite_fournisseur_certificats(fournisseur_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qfc_exp ON qualite_fournisseur_certificats(date_expiration)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS qualite_fournisseur_certificat_fiches (
                certificat_id INTEGER NOT NULL REFERENCES qualite_fournisseur_certificats(id) ON DELETE CASCADE,
                fiche_id INTEGER NOT NULL REFERENCES qualite_ref_fiches(id) ON DELETE CASCADE,
                PRIMARY KEY (certificat_id, fiche_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qfcf_fiche ON qualite_fournisseur_certificat_fiches(fiche_id)")
        # Log d'annonces d'expiration dÃ©jÃ  Ã©mises : un enregistrement par (certificat, bucket).
        # bucket parmi : 'expired', 'j30', 'j60' â€” Ã©vite de spammer plusieurs fois la mÃªme alerte.
        conn.execute("""
            CREATE TABLE IF NOT EXISTS qualite_cert_expiration_annonces (
                certificat_id INTEGER NOT NULL REFERENCES qualite_fournisseur_certificats(id) ON DELETE CASCADE,
                bucket TEXT NOT NULL,
                annonce_at TEXT NOT NULL,
                PRIMARY KEY (certificat_id, bucket)
            )
        """)
        conn.commit()
        _record_schema_migration(conn, 173, "qualite_ressources_fournisseurs")

    # v174 â€” MyQualitÃ© : extension Audit avec matrice fournisseurs Ã— certifications.
    # audit_fournisseurs : fournisseurs impliquÃ©s dans l'audit (N-N avec fournisseurs_fsc).
    # audit_certifications_demandees : certifications demandÃ©es par le client (N-N avec fiches).
    # audit_matrice_overrides : override manuel du statut d'une case (fournisseur Ã— fiche)
    #   pour marquer 'na', 'demande_envoyee', etc. quand l'auto-dÃ©duction ne suffit pas.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=174 LIMIT 1").fetchone():
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_fournisseurs (
                audit_id INTEGER NOT NULL REFERENCES audit_dossiers(id) ON DELETE CASCADE,
                fournisseur_id INTEGER NOT NULL REFERENCES fournisseurs_fsc(id) ON DELETE CASCADE,
                added_at TEXT NOT NULL,
                added_by INTEGER REFERENCES users(id),
                PRIMARY KEY (audit_id, fournisseur_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_af_four ON audit_fournisseurs(fournisseur_id)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_certifications_demandees (
                audit_id INTEGER NOT NULL REFERENCES audit_dossiers(id) ON DELETE CASCADE,
                fiche_id INTEGER NOT NULL REFERENCES qualite_ref_fiches(id) ON DELETE CASCADE,
                added_at TEXT NOT NULL,
                added_by INTEGER REFERENCES users(id),
                PRIMARY KEY (audit_id, fiche_id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_acd_fiche ON audit_certifications_demandees(fiche_id)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_matrice_overrides (
                audit_id INTEGER NOT NULL REFERENCES audit_dossiers(id) ON DELETE CASCADE,
                fournisseur_id INTEGER NOT NULL REFERENCES fournisseurs_fsc(id) ON DELETE CASCADE,
                fiche_id INTEGER NOT NULL REFERENCES qualite_ref_fiches(id) ON DELETE CASCADE,
                statut TEXT NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL,
                updated_by INTEGER REFERENCES users(id),
                PRIMARY KEY (audit_id, fournisseur_id, fiche_id)
            )
        """)
        conn.commit()
        _record_schema_migration(conn, 174, "qualite_audit_matrice_fournisseurs_certifs")

    # Migration 175 â€” MyMaintenance : les crÃ©neaux (planifie) peuvent avoir un
    # nom libre pour identifier une session ("Nettoyage matinal", "Grande rÃ©vision").
    # Colonne nullable, pas de valeur par dÃ©faut : les crÃ©neaux existants restent
    # sans nom, le frontend affiche l'horaire par dÃ©faut.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=175 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(maintenance_events)").fetchall()}
        if "nom" not in cols:
            conn.execute("ALTER TABLE maintenance_events ADD COLUMN nom TEXT")
        conn.commit()
        _record_schema_migration(conn, 175, "maintenance_events_nom")

    # Migration 176 â€” Planning prod : flag "journÃ©e entiÃ¨re" (00:00 â†’ 23:59).
    # Peut Ãªtre activÃ© Ã  trois niveaux : override journalier, config semaine,
    # default machine. Le flag est prioritaire sur les heures stockÃ©es : quand
    # actif, getWhForDate() renvoie 0-24 pour ce jour. RÃ©tro-compatible : les
    # entrÃ©es existantes ont journee_entiere=0 (comportement inchangÃ©).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=176 LIMIT 1").fetchone():
        cols_m = {r["name"] for r in conn.execute("PRAGMA table_info(machines)").fetchall()}
        if "journee_entiere" not in cols_m:
            conn.execute("ALTER TABLE machines ADD COLUMN journee_entiere INTEGER DEFAULT 0")
        cols_pc = {r["name"] for r in conn.execute("PRAGMA table_info(planning_config)").fetchall()}
        if "journee_entiere" not in cols_pc:
            conn.execute("ALTER TABLE planning_config ADD COLUMN journee_entiere INTEGER DEFAULT 0")
        cols_pdh = {r["name"] for r in conn.execute("PRAGMA table_info(planning_day_horaires)").fetchall()}
        if "journee_entiere" not in cols_pdh:
            conn.execute("ALTER TABLE planning_day_horaires ADD COLUMN journee_entiere INTEGER DEFAULT 0")
        conn.commit()
        _record_schema_migration(conn, 176, "planning_journee_entiere_flag")

    # Migration 177 â€” Planning RH : configuration des Ã©quipes par machine
    # (matin/aprem/nuit + mode alternance). Alimente le bouton rÃ©glages du
    # planning RH ; les crÃ©neaux affichÃ©s sont dÃ©sormais lus en base plutÃ´t
    # que codÃ©s dans planning_rh_page.py. Une machine sans ligne dans cette
    # table utilise les dÃ©fauts codÃ©s cÃ´tÃ© frontend (compat).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=177 LIMIT 1").fetchone():
        existing = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        if "rh_machine_config" not in existing:
            conn.execute("""CREATE TABLE rh_machine_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                machine_id INTEGER NOT NULL UNIQUE,
                matin_actif INTEGER NOT NULL DEFAULT 1,
                matin_debut TEXT NOT NULL DEFAULT '05:00',
                matin_fin   TEXT NOT NULL DEFAULT '13:00',
                aprem_actif INTEGER NOT NULL DEFAULT 1,
                aprem_debut TEXT NOT NULL DEFAULT '13:00',
                aprem_fin   TEXT NOT NULL DEFAULT '21:00',
                nuit_actif  INTEGER NOT NULL DEFAULT 0,
                nuit_debut  TEXT NOT NULL DEFAULT '21:00',
                nuit_fin    TEXT NOT NULL DEFAULT '05:00',
                mode_alternance TEXT NOT NULL DEFAULT 'identique',  -- 'identique' | 'alterne'
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (machine_id) REFERENCES machines(id)
            )""")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_rh_machine_config_mid ON rh_machine_config(machine_id)"
            )
        conn.commit()
        _record_schema_migration(conn, 177, "rh_machine_config")

    # v178 â€” Codes maintenance : scinde la catÃ©gorie "interventions" en deux
    # nouvelles catÃ©gories "entretien" et "remplacements". Les deux gardent
    # exactement les mÃªmes propriÃ©tÃ©s que l'ancienne "interventions"
    # (apparition dans la section Maintenance, saisie dans une session, etc.).
    # Migration des donnÃ©es existantes : tous les codes "interventions" (et
    # les legacy "suivi") sont dÃ©placÃ©s vers "entretien" par dÃ©faut. L'admin
    # peut ensuite reclasser certains codes vers "remplacements" via
    # ParamÃ¨tres â†’ Maintenance.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=178 LIMIT 1").fetchone():
        conn.execute(
            "UPDATE maintenance_codes SET categorie='entretien' "
            "WHERE categorie IN ('interventions', 'suivi')"
        )
        conn.commit()
        _record_schema_migration(conn, 178, "maintenance_codes_split_interventions")

    # Migration 179 â€” MyMaintenance : validation indÃ©pendante par (op, machine).
    # Avant : une op multi-machines = 1 ligne dans maintenance_event_ops avec
    # machines_csv = "Coh1 Â· Coh2" et 1 statut partagÃ© â†’ marquer termine sur
    # une machine hidden la task des 2.
    # AprÃ¨s : split en N lignes (une par machine), chacune avec son statut,
    # durÃ©e, commentaires, done_at, done_by indÃ©pendants.
    # Change aussi la contrainte UNIQUE(event_id, code) -> UNIQUE(event_id, code, machines_csv)
    # pour permettre le mÃªme code sur plusieurs machines dans un crÃ©neau.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=179 LIMIT 1").fetchone():
        # 1. Nouvelle table avec contrainte ajustÃ©e
        conn.execute("""CREATE TABLE IF NOT EXISTS maintenance_event_ops_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            machines_csv TEXT,
            statut TEXT NOT NULL DEFAULT 'a_faire',
            duree_reelle_min INTEGER,
            pieces_changees TEXT,
            observations TEXT,
            photos_json TEXT,
            done_at TEXT,
            done_by INTEGER,
            updated_by INTEGER,
            updated_at TEXT,
            FOREIGN KEY (event_id) REFERENCES maintenance_events(id) ON DELETE CASCADE,
            FOREIGN KEY (code) REFERENCES maintenance_codes(code),
            FOREIGN KEY (done_by) REFERENCES users(id),
            FOREIGN KEY (updated_by) REFERENCES users(id),
            UNIQUE (event_id, code, machines_csv)
        )""")

        # 2. Backfill : split chaque row par machine
        SEP = " Â· "  # meme separateur que _MACHINES_SEP cote router
        rows = conn.execute(
            """SELECT o.id, o.event_id, o.code, o.machines_csv, o.statut,
                      o.duree_reelle_min, o.pieces_changees, o.observations,
                      o.photos_json, o.done_at, o.done_by, o.updated_by, o.updated_at,
                      e.machine AS ev_machine
               FROM maintenance_event_ops o
               JOIN maintenance_events e ON e.id = o.event_id"""
        ).fetchall()
        for r in rows:
            base = (r["machines_csv"] or "").strip() or (r["ev_machine"] or "").strip()
            machines = [p.strip() for p in base.split(SEP) if p.strip()] if base else [None]
            for m in (machines or [None]):
                m_csv = m if m else None
                try:
                    conn.execute(
                        """INSERT INTO maintenance_event_ops_new
                           (event_id, code, machines_csv, statut, duree_reelle_min,
                            pieces_changees, observations, photos_json, done_at,
                            done_by, updated_by, updated_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (r["event_id"], r["code"], m_csv, r["statut"],
                         r["duree_reelle_min"], r["pieces_changees"], r["observations"],
                         r["photos_json"], r["done_at"], r["done_by"],
                         r["updated_by"], r["updated_at"]),
                    )
                except Exception:
                    # Doublon (event_id, code, machines_csv) ignorÃ© par prudence.
                    pass

        # 3. Bascule ancienne <-> nouvelle
        conn.execute("DROP TABLE maintenance_event_ops")
        conn.execute("ALTER TABLE maintenance_event_ops_new RENAME TO maintenance_event_ops")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_maint_event_ops_event  ON maintenance_event_ops(event_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_maint_event_ops_code   ON maintenance_event_ops(code)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_maint_event_ops_statut ON maintenance_event_ops(statut)")

        conn.commit()
        _record_schema_migration(conn, 179, "maintenance_event_ops_split_per_machine")

    # Migration 180 â€” Fournisseurs : notion de groupe (multi-branches).
    # Ajoute deux colonnes texte libres sur fournisseurs_fsc :
    #   - groupe : nom du groupe parent (ex: "Fedrigoni"). NULL si independant.
    #   - branche : nom de la branche/division dans le groupe (ex: "Italy").
    # Ajoute une colonne groupe_ref sur qualite_fournisseur_certificats :
    #   NULL = certif attache a la branche (fournisseur_id).
    #   valeur = nom du groupe â†’ certif partage entre toutes les branches du groupe.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=180 LIMIT 1").fetchone():
        cols_four = {r[1] for r in conn.execute("PRAGMA table_info(fournisseurs_fsc)").fetchall()}
        if "groupe" not in cols_four:
            conn.execute("ALTER TABLE fournisseurs_fsc ADD COLUMN groupe TEXT")
        if "branche" not in cols_four:
            conn.execute("ALTER TABLE fournisseurs_fsc ADD COLUMN branche TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fournisseurs_groupe ON fournisseurs_fsc(groupe)")

        cols_cert = {r[1] for r in conn.execute("PRAGMA table_info(qualite_fournisseur_certificats)").fetchall()}
        if "groupe_ref" not in cols_cert:
            conn.execute("ALTER TABLE qualite_fournisseur_certificats ADD COLUMN groupe_ref TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_qualite_cert_groupe_ref ON qualite_fournisseur_certificats(groupe_ref)")

        conn.commit()
        _record_schema_migration(conn, 180, "fournisseurs_groupe_branche")

    # Migration 181 â€” Guides in-app : suivi lecture des tutos MyQualite (et
    # autres modules a venir). Table de progression par (utilisateur, guide).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=181 LIMIT 1").fetchone():
        conn.execute("""CREATE TABLE IF NOT EXISTS user_guide_progress (
            user_id INTEGER NOT NULL,
            guide_key TEXT NOT NULL,
            total_steps INTEGER NOT NULL DEFAULT 0,
            steps_seen_bitmap INTEGER NOT NULL DEFAULT 0,
            total_time_ms INTEGER NOT NULL DEFAULT 0,
            open_count INTEGER NOT NULL DEFAULT 0,
            opened_at TEXT,
            completed_at TEXT,
            acknowledged_at TEXT,
            reset_at TEXT,
            reset_by INTEGER,
            PRIMARY KEY (user_id, guide_key),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (reset_by) REFERENCES users(id)
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ugp_user ON user_guide_progress(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ugp_guide ON user_guide_progress(guide_key)")
        conn.commit()
        _record_schema_migration(conn, 181, "user_guide_progress")

    # Migration 183 â€” MyExpÃ© : lier un dÃ©part au devis retenu qui l'a genere.
    # Corrige le 500 sur POST /api/expe/devis/reponses/{id}/retenir qui inserait
    # deux colonnes inexistantes (source_devis_reponse_id, source_devis_demande_id)
    # dans expe_departs. La 182 est deja reservee cote staging pour
    # maintenance_codes_libre_and_usage_count.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=183 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_departs)").fetchall()}
        if "source_devis_reponse_id" not in cols:
            conn.execute(
                "ALTER TABLE expe_departs ADD COLUMN source_devis_reponse_id INTEGER "
                "REFERENCES expe_devis_reponses(id)"
            )
        if "source_devis_demande_id" not in cols:
            conn.execute(
                "ALTER TABLE expe_departs ADD COLUMN source_devis_demande_id INTEGER "
                "REFERENCES expe_demandes_devis(id)"
            )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expe_departs_source_devis_reponse "
            "ON expe_departs(source_devis_reponse_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expe_departs_source_devis_demande "
            "ON expe_departs(source_devis_demande_id)"
        )
        conn.commit()
        _record_schema_migration(conn, 183, "expe_departs_source_devis_link")

    # Migration 184 â€” MyMaintenance : nettoyage one-shot des crÃ©neaux planifie
    # crÃ©Ã©s historiquement par des opÃ©rateurs via l'ancien flow "Nouvelle tÃ¢che"
    # (feature retirÃ©e). DÃ©sormais seul l'admin peut crÃ©er des crÃ©neaux planifie.
    # CASCADE via FK : supprime aussi les ops rattachÃ©es et les operators.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=184 LIMIT 1").fetchone():
        conn.execute(
            """DELETE FROM maintenance_events
               WHERE source = 'planifie'
               AND created_by IN (SELECT id FROM users WHERE role = 'fabrication')"""
        )
        conn.commit()
        _record_schema_migration(conn, 184, "cleanup_operator_planifie_creneaux")

    # Migration 185 â€” MyMaintenance : consignes admin par op planifiÃ©e.
    # L'admin peut ajouter des instructions/dÃ©tails textuels sur chaque op
    # d'un crÃ©neau. Nullable, pas de valeur par dÃ©faut. Le champ est propre
    # Ã  chaque row (une op sur Coh1 et la mÃªme sur Coh2 = 2 rows = 2 champs
    # consignes indÃ©pendants). Visibles cÃ´tÃ© opÃ©rateur (icÃ´ne i + panneau)
    # et dans l'historique admin.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=185 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(maintenance_event_ops)").fetchall()}
        if "consignes" not in cols:
            conn.execute("ALTER TABLE maintenance_event_ops ADD COLUMN consignes TEXT")
        conn.commit()
        _record_schema_migration(conn, 185, "maintenance_event_ops_consignes")

    # Migration 186 â€” SystÃ¨me de gestion des accÃ¨s database-driven.
    # Deux tables : role_access_defaults (rÃ©fÃ©rentiel rÃ´le Ã— app Ã— module,
    # modifiable dans ParamÃ¨tres) et user_access_overrides (surcharges par
    # utilisateur, mÃªme granularitÃ©). Niveau 4 valeurs : none / read / write
    # / admin (ordinal, admin >= write >= read >= none). module_id = '_app'
    # = accÃ¨s gÃ©nÃ©ral Ã  l'appli, sinon nom d'onglet (sous-module).
    # Seed depuis default_app_access_for_role (aucune rÃ©gression). La colonne
    # legacy users.access_overrides (JSON) est copiÃ©e vers user_access_overrides
    # puis conservÃ©e en fallback ; sera droppÃ©e dans une migration ultÃ©rieure.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=186 LIMIT 1").fetchone():
        conn.execute(
            "CREATE TABLE IF NOT EXISTS role_access_defaults ("
            "role TEXT NOT NULL, app_id TEXT NOT NULL, "
            "module_id TEXT NOT NULL DEFAULT '_app', "
            "level TEXT NOT NULL DEFAULT 'none', "
            "updated_at TEXT, updated_by TEXT, "
            "PRIMARY KEY (role, app_id, module_id))"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rad_lookup ON role_access_defaults(role, app_id)")
        conn.execute(
            "CREATE TABLE IF NOT EXISTS user_access_overrides ("
            "user_id INTEGER NOT NULL, app_id TEXT NOT NULL, "
            "module_id TEXT NOT NULL DEFAULT '_app', "
            "level TEXT NOT NULL DEFAULT 'none', "
            "updated_at TEXT, updated_by TEXT, "
            "PRIMARY KEY (user_id, app_id, module_id), "
            "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_uao_lookup ON user_access_overrides(user_id, app_id)")

        from config import (
            ASSIGNABLE_ROLES as _AR,
            ROLE_SUPERADMIN as _SA,
            ROLE_COMMERCIAL as _C,
            ROLE_DIRECTION as _D,
            ROLES_ADMINISTRATION_ALL as _RAA,
            default_app_access_for_role as _daafr,
        )
        now184 = datetime.now().isoformat()
        _APP_IDS_184 = ["prod", "planning", "planning_rh", "stock", "compta",
                        "expe", "pricing", "fabrication", "qualite", "settings"]

        def _seed_lvl_184(role, app_id, legacy):
            if role == _SA:
                return "admin"
            if app_id == "qualite":
                if role in ({_D} | _RAA):
                    return "write"
                if role == _C:
                    return "read"
                return "none"
            return "write" if legacy.get(app_id) else "none"

        for role in list(_AR) + [_SA]:
            legacy = _daafr(role)
            for app_id in _APP_IDS_184:
                conn.execute(
                    "INSERT OR IGNORE INTO role_access_defaults "
                    "(role, app_id, module_id, level, updated_at, updated_by) "
                    "VALUES (?, ?, '_app', ?, ?, 'seed_v184')",
                    (role, app_id, _seed_lvl_184(role, app_id, legacy), now184),
                )

        rows184 = conn.execute(
            "SELECT id, access_overrides FROM users "
            "WHERE access_overrides IS NOT NULL AND access_overrides != ''"
        ).fetchall()
        for r in rows184:
            raw = r["access_overrides"]
            try:
                data = json.loads(raw) if isinstance(raw, str) else raw
            except (json.JSONDecodeError, TypeError):
                continue
            if not isinstance(data, dict):
                continue
            for app_id, val in data.items():
                if not isinstance(val, bool):
                    continue
                key = "pricing" if app_id == "devis" else app_id
                if key not in _APP_IDS_184:
                    continue
                conn.execute(
                    "INSERT OR IGNORE INTO user_access_overrides "
                    "(user_id, app_id, module_id, level, updated_at, updated_by) "
                    "VALUES (?, ?, '_app', ?, ?, 'migration_v184')",
                    (r["id"], key, "write" if val else "none", now184),
                )

        conn.commit()
        _record_schema_migration(conn, 186, "access_control_tables_and_seed")

    # Migration 187 - Fondation MyStock <-> /pricing (CoÃ»ts matiÃ¨res).
    #
    # Contexte : deux tables dÃ©crivent aujourd'hui la mÃªme chose de deux faÃ§ons :
    #   - `mc_material` (module /pricing, alimentÃ© par import Excel)
    #   - `matieres_premieres` + `mp_valorisation` (MyStock, vÃ©ritÃ© opÃ©rationnelle)
    # Objectif : faire de MyStock la source unique du prix et des caractÃ©ristiques
    # matiÃ¨re, et transformer /pricing en outil direction (dashboard + Ã©dition
    # inline avec synchronisation bidirectionnelle).
    #
    # Cette migration pose UNIQUEMENT la fondation :
    #   1. Enrichit `matieres_premieres` avec les 8 champs manquants cÃ´tÃ© pricing
    #      engine (poids, base tarifaire, rÃ´le produit, container import, taxe,
    #      flag import) - tous nullable, aucun dÃ©faut cassant.
    #   2. Ajoute `matieres_premieres.mc_material_id` (FK nullable) pour tracer
    #      l'appairage entre les deux mondes.
    #   3. Backfille `pricing_role` depuis la catÃ©gorie MyStock (frontal ->
    #      frontal, adhesif -> adhesif, glassine -> glassine, complexe -> autre).
    #   4. Backfille `mc_material_id` par match nom case-insensitive ou
    #      appellation_code == reference ; pour chaque match, copie les
    #      caractÃ©ristiques depuis mc_material (weight_per_m2, weight_gsm,
    #      price_basis, is_imported, container_kg, container_cost_usd,
    #      tax_incidence) vers matieres_premieres.
    #
    # Aucune donnÃ©e n'est effacÃ©e ni Ã©crasÃ©e : les lignes matieres_premieres
    # sans match restent inchangÃ©es, les mc_material continuent d'Ãªtre lues
    # par /pricing exactement comme avant. La sync bidirectionnelle et le
    # remplacement de mc_material par une vue seront des migrations sÃ©parÃ©es.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=187 LIMIT 1").fetchone():
        mp_cols = {row[1] for row in conn.execute("PRAGMA table_info(matieres_premieres)").fetchall()}
        _mp_add = [
            ("weight_per_m2",       "REAL"),
            ("weight_gsm",          "INTEGER"),
            ("price_basis",         "TEXT DEFAULT 'PER_KG'"),
            ("pricing_role",        "TEXT"),
            ("container_kg",        "REAL"),
            ("container_cost_usd",  "REAL"),
            ("tax_incidence",       "REAL DEFAULT 1.0"),
            ("is_imported",         "INTEGER DEFAULT 0"),
            ("mc_material_id",      "INTEGER REFERENCES mc_material(id)"),
        ]
        for col, ddl in _mp_add:
            if col not in mp_cols:
                conn.execute(f"ALTER TABLE matieres_premieres ADD COLUMN {col} {ddl}")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mp_mc_material_id "
            "ON matieres_premieres(mc_material_id)"
        )

        # Backfill pricing_role depuis la catÃ©gorie MyStock (idempotent : ne
        # touche que les lignes oÃ¹ pricing_role est vide).
        _role_map = {
            "frontal":  "frontal",
            "adhesif":  "adhesif",
            "silicone": "silicone",
            "glassine": "glassine",
            "complexe": "autre",
        }
        for cat, role in _role_map.items():
            conn.execute(
                "UPDATE matieres_premieres SET pricing_role=? "
                "WHERE (pricing_role IS NULL OR pricing_role='') "
                "AND LOWER(TRIM(COALESCE(categorie,'')))=?",
                (role, cat),
            )

        # Backfill mc_material_id : match nom, puis appellation_code, puis
        # copie les caractÃ©ristiques pricing depuis mc_material. Uniquement
        # si la table mc_material existe (v78+).
        try:
            has_mc = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='mc_material' LIMIT 1"
            ).fetchone()
        except Exception:
            has_mc = None
        if has_mc:
            # Passe 1 : appellation_code == reference (le plus fiable).
            conn.execute(
                "UPDATE matieres_premieres AS mp "
                "SET mc_material_id = ("
                "  SELECT m.id FROM mc_material m "
                "  WHERE LOWER(TRIM(COALESCE(m.appellation_code,''))) = "
                "        LOWER(TRIM(COALESCE(mp.reference,''))) "
                "  AND TRIM(COALESCE(m.appellation_code,'')) != '' "
                "  LIMIT 1) "
                "WHERE mp.mc_material_id IS NULL"
            )
            # Passe 2 : name == designation (fallback).
            conn.execute(
                "UPDATE matieres_premieres AS mp "
                "SET mc_material_id = ("
                "  SELECT m.id FROM mc_material m "
                "  WHERE LOWER(TRIM(COALESCE(m.name,''))) = "
                "        LOWER(TRIM(COALESCE(mp.designation,''))) "
                "  LIMIT 1) "
                "WHERE mp.mc_material_id IS NULL"
            )

            # Copie des caractÃ©ristiques pricing depuis mc_material vers
            # matieres_premieres pour chaque ligne appairÃ©e. On ne remplace
            # jamais une valeur dÃ©jÃ  saisie cÃ´tÃ© MyStock (COALESCE garde
            # l'existant).
            _copy_map = [
                ("weight_per_m2",      "m.weight_per_m2"),
                ("weight_gsm",         "m.weight_gsm"),
                ("price_basis",        "m.price_basis"),
                ("is_imported",        "m.is_imported"),
                ("container_kg",       "m.container_kg"),
                ("container_cost_usd", "m.container_cost_usd"),
                ("tax_incidence",      "m.tax_incidence"),
            ]
            for col, expr in _copy_map:
                conn.execute(
                    f"UPDATE matieres_premieres AS mp "
                    f"SET {col} = COALESCE(mp.{col}, ("
                    f"  SELECT {expr} FROM mc_material m WHERE m.id = mp.mc_material_id"
                    f")) "
                    f"WHERE mp.mc_material_id IS NOT NULL"
                )

        conn.commit()
        _record_schema_migration(conn, 187, "mp_pricing_bridge")

    # Migration 188 â€” MyMaintenance : purge one-shot des ops et operators
    # orphelins. Bug historique : le PRAGMA foreign_keys n'est pas activÃ© sur
    # get_db(), donc les DELETE sur maintenance_events ne CASCADE pas â†’ chaque
    # suppression de crÃ©neau laissait des rows dans maintenance_event_ops et
    # maintenance_event_operators avec un event_id pointant vers un event qui
    # n'existe plus. Rows invisibles dans l'UI (les JOIN les excluent) mais
    # prÃ©sentes physiquement en DB.
    # Le fix v2.2.11 ajoute des DELETE explicites dans delete_event pour ne
    # plus crÃ©er de nouveaux orphelins. Cette migration nettoie le passif.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=188 LIMIT 1").fetchone():
        conn.execute(
            """DELETE FROM maintenance_event_ops
               WHERE event_id NOT IN (SELECT id FROM maintenance_events)"""
        )
        conn.execute(
            """DELETE FROM maintenance_event_operators
               WHERE event_id NOT IN (SELECT id FROM maintenance_events)"""
        )
        conn.commit()
        _record_schema_migration(conn, 188, "cleanup_orphan_maintenance_event_ops")

    # Migration 189 â€” Retire le systÃ¨me d'alertes automatiques liÃ©es aux
    # contrÃ´les non pÃ©riodiques (v2.2.15 + fix v2.2.16). L'alerte utile
    # ("Inspection des produits finis", historiquement liÃ©e au code '01')
    # devient une alerte classique manuelle qui conserve toutes ses acks.
    #
    # Actions (idempotentes via garde schema_migrations 189) :
    #   a. Trouve l'alerte cible par linked_maint_code='01' (chemin
    #      canonique) ou fallback LIKE fuzzy sur le nom. Rename propre
    #      â†’ "Inspection des produits finis". DÃ©tache + rebadge manual.
    #   b. GARDE-FOU STRICT : ne DELETE les autres alertes auto QUE si
    #      l'alerte cible a Ã©tÃ© trouvÃ©e et sÃ©curisÃ©e. Sinon aucun delete.
    #      (Ã‰vite le bug v2.2.15 oÃ¹ qpf_id=None â†’ id != -1 balayait tout.)
    #   c. Convertit les codes categorie='controles' et periodique=0 en
    #      periodique=1 avec intervalle='â€”' si vide.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=189 LIMIT 1").fetchone():
        _now_189 = datetime.now().isoformat()
        # a. Trouve l'alerte cible â€” chemin canonique via linked_maint_code
        qpf = conn.execute(
            "SELECT id, nom FROM maintenance_alerts "
            "WHERE linked_maint_code='01' LIMIT 1"
        ).fetchone()
        # Fallback : LIKE fuzzy sur les libellÃ©s plausibles
        if qpf is None:
            qpf = conn.execute(
                """SELECT id, nom FROM maintenance_alerts
                   WHERE LOWER(nom) LIKE '%inspection%produits%finis%'
                      OR LOWER(nom) LIKE '%inspection%produits%finaux%'
                      OR LOWER(nom) LIKE '%qualit%produits%finis%'
                      OR LOWER(nom) LIKE '%contr%le%produits%finis%'
                   ORDER BY id ASC LIMIT 1"""
            ).fetchone()
        qpf_id = qpf["id"] if qpf else None
        if qpf_id is not None:
            conn.execute(
                """UPDATE maintenance_alerts
                   SET nom='Inspection des produits finis',
                       linked_maint_code=NULL,
                       created_by='manual',
                       updated_at=?
                   WHERE id=?""",
                (_now_189, qpf_id)
            )
        # b. GARDE-FOU STRICT : DELETE des autres alertes auto SEULEMENT
        # si l'alerte cible a Ã©tÃ© positivement identifiÃ©e et sÃ©curisÃ©e.
        # Sinon on s'abstient (prÃ©serve la donnÃ©e en cas de renommage
        # inattendu â€” l'admin peut nettoyer manuellement plus tard).
        if qpf_id is not None:
            orphan_ids = [r["id"] for r in conn.execute(
                "SELECT id FROM maintenance_alerts "
                "WHERE linked_maint_code IS NOT NULL"
            ).fetchall()]
            if orphan_ids:
                ph = ",".join(["?"] * len(orphan_ids))
                # CASCADE FK inactif sur SQLite â†’ purge manuelle des acks
                conn.execute(
                    f"DELETE FROM maintenance_alert_acks WHERE alert_id IN ({ph})",
                    orphan_ids,
                )
                conn.execute(
                    f"DELETE FROM maintenance_alerts WHERE id IN ({ph})",
                    orphan_ids,
                )
        # c. Convertit les codes non-pÃ©riodiques en pÃ©riodiques
        # (safe : aucune perte de donnÃ©es, juste normalisation du flag)
        conn.execute(
            """UPDATE maintenance_codes
               SET periodique=1,
                   intervalle=COALESCE(NULLIF(TRIM(intervalle),''), 'â€”'),
                   updated_at=?
               WHERE categorie='controles' AND periodique=0""",
            (_now_189,)
        )
        conn.commit()
        _record_schema_migration(conn, 189, "remove_auto_control_alerts_system")

    # Migration 190 â€” Retire le concept de pÃ©riodicitÃ© (v2.2.17).
    # Tous les codes maintenance sont dÃ©sormais considÃ©rÃ©s comme pÃ©riodiques
    # cÃ´tÃ© modÃ¨le mÃ©tier. La colonne `periodique` reste en DB pour compat
    # (aucun DROP COLUMN, rÃ©versible), mais elle est forcÃ©e Ã  1 partout et
    # cachÃ©e de l'UI (formulaire + tableau).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=190 LIMIT 1").fetchone():
        conn.execute(
            "UPDATE maintenance_codes SET periodique=1, updated_at=? WHERE periodique=0",
            (datetime.now().isoformat(),)
        )
        conn.commit()
        _record_schema_migration(conn, 190, "force_all_maintenance_codes_periodic")

    # v191 -- Enrichissement fournisseurs_fsc : contacts, adresse, langue, tags
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=191 LIMIT 1").fetchone():
        ff_cols = {r[1] for r in conn.execute("PRAGMA table_info(fournisseurs_fsc)").fetchall()}
        _ff_add = [
            ("adresse",         "TEXT"),
            ("code_postal",     "TEXT"),
            ("ville",           "TEXT"),
            ("pays",            "TEXT DEFAULT 'FR'"),
            ("langue_default",  "TEXT DEFAULT 'fr'"),
            ("tags",            "TEXT"),
            ("notes",           "TEXT"),
            ("actif",           "INTEGER NOT NULL DEFAULT 1"),
            ("updated_at",      "TEXT"),
        ]
        for col, ddl in _ff_add:
            if col not in ff_cols:
                conn.execute(f"ALTER TABLE fournisseurs_fsc ADD COLUMN {col} {ddl}")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fournisseurs_fsc_actif ON fournisseurs_fsc(actif)")
        conn.commit()
        _record_schema_migration(conn, 191, "fournisseurs_fsc_contacts_infos")

    # v192 -- Table fournisseur_contacts (N contacts par fournisseur)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=192 LIMIT 1").fetchone():
        conn.execute("""CREATE TABLE IF NOT EXISTS fournisseur_contacts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fournisseur_id  INTEGER NOT NULL REFERENCES fournisseurs_fsc(id) ON DELETE CASCADE,
            nom             TEXT NOT NULL,
            fonction        TEXT,
            emails          TEXT,
            tels            TEXT,
            langue          TEXT DEFAULT 'fr',
            is_principal    INTEGER NOT NULL DEFAULT 0,
            actif           INTEGER NOT NULL DEFAULT 1,
            notes           TEXT,
            created_at      TEXT NOT NULL,
            updated_at      TEXT
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fournisseur_contacts_fournisseur ON fournisseur_contacts(fournisseur_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fournisseur_contacts_principal ON fournisseur_contacts(fournisseur_id, is_principal)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_fournisseur_contacts_actif ON fournisseur_contacts(actif)")
        conn.commit()
        _record_schema_migration(conn, 192, "fournisseur_contacts")

    # v193 -- ao_fournisseurs : FKs optionnels vers fournisseurs_fsc + fournisseur_contacts
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=193 LIMIT 1").fetchone():
        af_cols = {r[1] for r in conn.execute("PRAGMA table_info(ao_fournisseurs)").fetchall()}
        if "fournisseur_id" not in af_cols:
            conn.execute("ALTER TABLE ao_fournisseurs ADD COLUMN fournisseur_id INTEGER")
        if "fournisseur_contact_id" not in af_cols:
            conn.execute("ALTER TABLE ao_fournisseurs ADD COLUMN fournisseur_contact_id INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ao_fournisseurs_fournisseur ON ao_fournisseurs(fournisseur_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ao_fournisseurs_contact ON ao_fournisseurs(fournisseur_contact_id)")
        conn.commit()
        _record_schema_migration(conn, 193, "ao_fournisseurs_fks")

    # v194 -- ao_demandes : cloture + fournisseur retenu
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=194 LIMIT 1").fetchone():
        aod_cols = {r[1] for r in conn.execute("PRAGMA table_info(ao_demandes)").fetchall()}
        if "fournisseur_retenu_id" not in aod_cols:
            conn.execute("ALTER TABLE ao_demandes ADD COLUMN fournisseur_retenu_id INTEGER")
        if "date_cloture" not in aod_cols:
            conn.execute("ALTER TABLE ao_demandes ADD COLUMN date_cloture TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ao_demandes_retenu ON ao_demandes(fournisseur_retenu_id)")
        conn.commit()
        _record_schema_migration(conn, 194, "ao_demandes_cloture_retention")
    # Migration 195 â€” Backfill usage_count des codes libres (v2.2.37 fix).
    # NOTE : renumÃ©rotÃ©e 191 â†’ 194 â†’ 195 (v2.2.40) car staging accumule des
    # migrations en parallÃ¨le (fournisseurs_fsc_contacts_infos, ao_demandes...).
    # Le compteur `usage_count` sur maintenance_codes (libre=1) n'est
    # historiquement peuplÃ© que par la fonction merge. Depuis v2.2.37 il est
    # aussi incrÃ©mentÃ© Ã  chaque INSERT d'op avec un code LIB-*, mais les
    # donnÃ©es antÃ©rieures ont un compteur Ã  0. Cette migration re-calcule
    # usage_count Ã  partir du vrai nombre d'ops enregistrÃ©es.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=195 LIMIT 1").fetchone():
        conn.execute(
            """UPDATE maintenance_codes
               SET usage_count = COALESCE((
                     SELECT COUNT(*) FROM maintenance_event_ops
                     WHERE maintenance_event_ops.code = maintenance_codes.code
                   ), 0)
               WHERE libre = 1"""
        )
        conn.commit()
        _record_schema_migration(conn, 195, "backfill_libres_usage_count")

    # v195 — Impression : support imprimantes Windows locales (USB / LPT).
    # Jusqu'ici, les imprimantes etaient forcement atteignables en TCP:9100. Ajoute
    # `type_connexion` = 'tcp_ip' | 'windows_local' + `nom_queue_windows` pour
    # cibler une queue installee sur le PC hote (le driver Windows gere USB/LPT/etc).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=195 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(imprimantes)").fetchall()}
        if "type_connexion" not in cols:
            conn.execute("ALTER TABLE imprimantes ADD COLUMN type_connexion TEXT NOT NULL DEFAULT 'tcp_ip'")
        if "nom_queue_windows" not in cols:
            conn.execute("ALTER TABLE imprimantes ADD COLUMN nom_queue_windows TEXT")
        conn.commit()
        _record_schema_migration(conn, 195, "imprimantes_type_connexion_windows_local")

    # v196 -- MyExpe (devis transporteurs) : type de palette sur les demandes,
    # commentaire + fichier joint lors de la retenue d'une offre. Colonnes
    # nullable, seedees a NULL pour ne rien casser en prod.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=196 LIMIT 1").fetchone():
        d_cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_demandes_devis)").fetchall()}
        if "type_palette" not in d_cols:
            conn.execute("ALTER TABLE expe_demandes_devis ADD COLUMN type_palette TEXT")
        r_cols = {r["name"] for r in conn.execute("PRAGMA table_info(expe_devis_reponses)").fetchall()}
        if "retention_comment" not in r_cols:
            conn.execute("ALTER TABLE expe_devis_reponses ADD COLUMN retention_comment TEXT")
        if "retention_file_path" not in r_cols:
            conn.execute("ALTER TABLE expe_devis_reponses ADD COLUMN retention_file_path TEXT")
        if "retention_file_filename" not in r_cols:
            conn.execute("ALTER TABLE expe_devis_reponses ADD COLUMN retention_file_filename TEXT")
        conn.commit()
        _record_schema_migration(conn, 196, "expe_devis_type_palette_and_retention_file")

    # v197 -- ao_demandes.prix_transport_pct (0..100, ecrase le prix vente par (1+pct/100))
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=197 LIMIT 1").fetchone():
        cols = {r[1] for r in conn.execute("PRAGMA table_info(ao_demandes)").fetchall()}
        if "prix_transport_pct" not in cols:
            conn.execute("ALTER TABLE ao_demandes ADD COLUMN prix_transport_pct REAL NOT NULL DEFAULT 0")
        conn.commit()
        _record_schema_migration(conn, 197, "ao_demandes_prix_transport_pct")

    # v198 -- MyStock Valorisation "figer a une date passee" : perf indexes.
    # Les endpoints /api/stock/valorisation?date=... et /api/stock/valorisation/pf?date=...
    # reconstituent le stock a une date via des CTE ROW_NUMBER() OVER (PARTITION BY ...
    # ORDER BY created_at) sur mp_mouvements / mouvements_stock, avec un WHERE
    # created_at > ?. Sans index sur created_at ni sur la cle de partition, chaque
    # snapshot fait un full-scan + tri en memoire. Idem pour les snapshots de prix
    # historises (mp_valorisation_historique / pf_valorisation_historique) qui prennent
    # le dernier prix_apres <= date par matiere/produit.
    # Impact : chargement multi-secondes de la valorisation figee -> quasi-instantane
    # sur des tables volumineuses.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=198 LIMIT 1").fetchone():
        # mp_mouvements : filtre created_at > ? + partition (matiere_id, laize_id).
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mp_mvt_created_at ON mp_mouvements(created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mp_mvt_snapshot "
            "ON mp_mouvements(matiere_id, laize_id, created_at, id)"
        )
        # mouvements_stock : filtre created_at > ? + partition (produit_id, emplacement).
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mvt_stock_created_at ON mouvements_stock(created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mvt_stock_snapshot "
            "ON mouvements_stock(produit_id, emplacement, created_at, id)"
        )
        # mp_valorisation_historique : le dernier prix <= date par matiere.
        # (idx_mp_valo_hist_mat existe deja mais couvre juste matiere_id -- pas la
        #  partie tri.)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mp_valo_hist_snapshot "
            "ON mp_valorisation_historique(matiere_id, created_at, id)"
        )
        # pf_valorisation_historique : idem par produit.
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pf_valo_hist_snapshot "
            "ON pf_valorisation_historique(produit_id, created_at, id)"
        )
        # ANALYZE : force le planner a reevaluer ses stats sur ces tables volumineuses.
        # Sans ca, les nouveaux index peuvent etre ignores tant qu'il n'y a pas eu
        # de VACUUM/ANALYZE spontane.
        try:
            conn.execute("ANALYZE mp_mouvements")
            conn.execute("ANALYZE mouvements_stock")
            conn.execute("ANALYZE mp_valorisation_historique")
            conn.execute("ANALYZE pf_valorisation_historique")
        except sqlite3.Error:
            pass
        conn.commit()
        _record_schema_migration(conn, 198, "valorisation_snapshot_perf_indexes")


    # v199 -- ao_reponses.unite_manuel (badge "manuel" quand l'interne modifie l'unite)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=199 LIMIT 1").fetchone():
        cols = {r[1] for r in conn.execute("PRAGMA table_info(ao_reponses)").fetchall()}
        if "unite_manuel" not in cols:
            conn.execute("ALTER TABLE ao_reponses ADD COLUMN unite_manuel INTEGER NOT NULL DEFAULT 0")
        conn.commit()
        _record_schema_migration(conn, 199, "ao_reponses_unite_manuel")


    # v200 -- ao_pieces_jointes.vu_par_fournisseur (bulle notif docs sur portail)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=200 LIMIT 1").fetchone():
        cols = {r[1] for r in conn.execute("PRAGMA table_info(ao_pieces_jointes)").fetchall()}
        if "vu_par_fournisseur" not in cols:
            conn.execute("ALTER TABLE ao_pieces_jointes ADD COLUMN vu_par_fournisseur INTEGER NOT NULL DEFAULT 0")
        conn.commit()
        _record_schema_migration(conn, 200, "ao_pieces_jointes_vu_par_fournisseur")


    # v201 -- ao_demandes.deleted_at (soft-delete pour corbeille)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=201 LIMIT 1").fetchone():
        cols = {r[1] for r in conn.execute("PRAGMA table_info(ao_demandes)").fetchall()}
        if "deleted_at" not in cols:
            conn.execute("ALTER TABLE ao_demandes ADD COLUMN deleted_at TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ao_demandes_deleted_at ON ao_demandes(deleted_at)")
        conn.commit()
        _record_schema_migration(conn, 201, "ao_demandes_deleted_at")


    # v202 -- ao_reponses.unite_quotation_original (preserve l'unite fournisseur pour pricing)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=202 LIMIT 1").fetchone():
        cols = {r[1] for r in conn.execute("PRAGMA table_info(ao_reponses)").fetchall()}
        if "unite_quotation_original" not in cols:
            conn.execute("ALTER TABLE ao_reponses ADD COLUMN unite_quotation_original TEXT")
            # Backfill : l'unite deja saisie est consideree comme originale
            conn.execute("UPDATE ao_reponses SET unite_quotation_original = unite_quotation WHERE unite_quotation_original IS NULL AND unite_quotation IS NOT NULL")
        conn.commit()
        _record_schema_migration(conn, 202, "ao_reponses_unite_quotation_original")



    # v203 -- stock_reception_items lie a matiere_id / laize_id (reception structuree)
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=203 LIMIT 1").fetchone():
        cols = {r[1] for r in conn.execute("PRAGMA table_info(stock_reception_items)").fetchall()}
        if "matiere_id" not in cols:
            conn.execute("ALTER TABLE stock_reception_items ADD COLUMN matiere_id INTEGER")
        if "laize_id" not in cols:
            conn.execute("ALTER TABLE stock_reception_items ADD COLUMN laize_id INTEGER")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_recp_items_matiere ON stock_reception_items(matiere_id, laize_id)")
        conn.commit()
        _record_schema_migration(conn, 203, "stock_reception_items_matiere_laize")

    # Migration 204 : MyQualité — Certifications SIFA (Déclarations UE, etc.)
    #   - fournisseurs_fsc.pays_origine : origine géographique de la fabrication
    #     (utilisé dans la section 3 de la Déclaration UE de Conformité)
    #   - qualite_sifa_doc_templates : catalogue des templates de documents officiels
    #     SIFA (aujourd'hui : Déclaration UE de Conformité). Extensible.
    #   - qualite_sifa_doc_versions : une ligne par version générée pour un client.
    #     Reliée à un audit_dossiers si le client a un audit ouvert, sinon nom libre.
    #     Le PDF est stocké sur disque, chemin dans pdf_path.
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=204 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(fournisseurs_fsc)").fetchall()}
        if "pays_origine" not in cols:
            conn.execute("ALTER TABLE fournisseurs_fsc ADD COLUMN pays_origine TEXT")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS qualite_sifa_doc_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                titre TEXT NOT NULL,
                sous_titre TEXT,
                description TEXT,
                ref_prefix TEXT NOT NULL DEFAULT 'SIFA-DoC',
                validite_mois INTEGER NOT NULL DEFAULT 12,
                actif INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS qualite_sifa_doc_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id INTEGER NOT NULL REFERENCES qualite_sifa_doc_templates(id) ON DELETE CASCADE,
                audit_id INTEGER REFERENCES audit_dossiers(id) ON DELETE SET NULL,
                client_nom TEXT NOT NULL,
                client_slug TEXT NOT NULL,
                fournisseurs_ids_json TEXT NOT NULL DEFAULT '[]',
                ref_document TEXT NOT NULL,
                date_emission TEXT NOT NULL,
                validite_mois INTEGER NOT NULL DEFAULT 12,
                pdf_path TEXT,
                notes TEXT,
                created_by INTEGER REFERENCES users(id),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                deleted_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sifa_doc_versions_template ON qualite_sifa_doc_versions(template_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sifa_doc_versions_audit ON qualite_sifa_doc_versions(audit_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sifa_doc_versions_client_slug ON qualite_sifa_doc_versions(client_slug)")

        from datetime import datetime as _dt204
        _now204 = _dt204.now().isoformat()
        conn.execute(
            "INSERT OR IGNORE INTO qualite_sifa_doc_templates "
            "(code, titre, sous_titre, description, ref_prefix, validite_mois, actif, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ('declaration_ue',
             'Déclaration UE de Conformité',
             'EU Declaration of Conformity (DoC)',
             "Déclaration de conformité aux règlements REACH, Proposition 65, métaux lourds "
             "(94/62/CE), PFAS, bisphénols, PPWR. Une version est établie par client, listant "
             "les fournisseurs de matière retenus pour ce client et leur origine géographique.",
             'SIFA-DoC',
             12,
             1,
             _now204)
        )

        conn.commit()
        _record_schema_migration(conn, 204, "sifa_certifications_declaration_ue")

    # Migration 205 : sections_overrides_json sur qualite_sifa_doc_versions.
    # Permet de personnaliser à la génération : exclure ou éditer certaines
    # sections du template pour un client donné (JSON: {sec_id: {include, custom_body}}).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=205 LIMIT 1").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(qualite_sifa_doc_versions)").fetchall()}
        if "sections_overrides_json" not in cols:
            conn.execute("ALTER TABLE qualite_sifa_doc_versions ADD COLUMN sections_overrides_json TEXT")
        conn.commit()
        _record_schema_migration(conn, 205, "sifa_doc_versions_sections_overrides")




    # v2.3.12 — Migration placement et size des réglages globaux vers chaque
    # alerte existante. Après cette migration, chaque alerte porte ses propres
    # valeurs (défaut top-right + medium si le singleton n'existe pas).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=205 LIMIT 1").fetchone():
        try:
            import json as _json_mig
            # Lire le singleton actuel
            row = conn.execute(
                "SELECT placement, size FROM maintenance_alert_settings WHERE id=1 LIMIT 1"
            ).fetchone()
            _default_placement = "top-right"
            _default_size = "medium"
            if row:
                _default_placement = row["placement"] or "top-right"
                _default_size = row["size"] or "medium"
            # Parcourir toutes les alertes et injecter les valeurs si absentes
            alerts = conn.execute(
                "SELECT id, params FROM maintenance_alerts"
            ).fetchall()
            for a in alerts:
                try:
                    p = _json_mig.loads(a["params"] or "{}")
                except Exception:
                    p = {}
                changed = False
                if not p.get("placement"):
                    p["placement"] = _default_placement
                    changed = True
                if not p.get("size"):
                    p["size"] = _default_size
                    changed = True
                if changed:
                    conn.execute(
                        "UPDATE maintenance_alerts SET params=?, updated_at=datetime('now') WHERE id=?",
                        (_json_mig.dumps(p, ensure_ascii=False), a["id"]),
                    )
            conn.commit()
        except Exception:
            pass
        _record_schema_migration(conn, 205, "alerts_placement_size_per_alert")


    # Migration 206 — Séries pour lignes d'AO.
    # Un produit d'un AO peut être décliné en plusieurs séries (même produit, légère
    # différence — souvent une variation d'impression). La somme des quantités des
    # séries d'une ligne doit égaler la quantité de la ligne mère (contrainte
    # applicative, pas de trigger SQL pour rester simple).
    #
    # ao_reponses.serie_id (nullable) : permet à un fournisseur de coter une série
    # spécifiquement. NULL = cotation au niveau ligne (comportement historique).
    if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=206 LIMIT 1").fetchone():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS ao_lignes_series (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ligne_id    INTEGER NOT NULL,
                position    INTEGER NOT NULL DEFAULT 0,
                libelle     TEXT NOT NULL,
                quantite    REAL NOT NULL DEFAULT 0,
                notes       TEXT,
                created_at  TEXT NOT NULL,
                FOREIGN KEY (ligne_id) REFERENCES ao_lignes(id) ON DELETE CASCADE
            )"""
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_ao_lignes_series_ligne ON ao_lignes_series(ligne_id)"
        )
        # Ajout colonne serie_id sur ao_reponses (nullable — cotation par ligne par défaut)
        ar_cols = {row[1] for row in conn.execute("PRAGMA table_info(ao_reponses)").fetchall()}
        if "serie_id" not in ar_cols:
            conn.execute("ALTER TABLE ao_reponses ADD COLUMN serie_id INTEGER")
        conn.commit()
        _record_schema_migration(conn, 206, "ao_lignes_series")


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

# â”€â”€â”€ DÃ©tection doublons â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def is_duplicate(conn, operateur, date_operation, operation_code, no_dossier):
    row = conn.execute(
        """SELECT id FROM production_data
           WHERE operateur=? AND date_operation=? AND operation_code=?
             AND COALESCE(no_dossier,'')=COALESCE(?,'') LIMIT 1""",
        (operateur, date_operation, operation_code, no_dossier)
    ).fetchone()
    return row is not None


# â”€â”€â”€ Helpers parsing â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def parse_french_number(val):
    if val is None:
        return 0
    s = str(val).strip()
    if not s:
        return 0
    s = s.replace(' ','').replace('Â ','').replace('â€¯','').replace(',','.')
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
        raise ValueError(f"Format non supportÃ©: .{ext}")


COLUMN_MAP = {
    "opÃ©rateur": "operateur", "operateur": "operateur",
    "date et heure d'opÃ©ration": "date_operation",
    "date et heure d'operation": "date_operation",
    "opÃ©ration": "operation", "operation": "operation",
    "service": "service", "machine": "machine",
    "no dossier": "no_dossier", "nÂ° dossier": "no_dossier",
    "client": "client",
    "dÃ©signation produit": "designation",
    "designation produit": "designation",
    "dÃ©signation produit ": "designation",
    "quantitÃ© Ã  traiter": "quantite_a_traiter",
    "quantite a traiter": "quantite_a_traiter",
    "quantitÃ© traitÃ©e": "quantite_traitee",
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

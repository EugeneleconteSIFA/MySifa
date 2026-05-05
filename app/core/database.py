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


@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=5)
    conn.row_factory = sqlite3.Row
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
        import json
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

    # v12 — jours travaillés par affectation RH (bitmask Lun=bit0…Ven=bit4, 31=semaine entière)
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

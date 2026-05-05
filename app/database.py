"""
SIFA — Database & helpers v0.5
Ajouts : colonnes traçabilité, détection doublons à l'import
"""
import sqlite3
import pandas as pd
import io
import json
import os
import csv
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from config import DB_PATH, UPLOAD_DIR, classify_operation


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


def _parse_emplacements_plan_csv(csv_path: Path):
    """Grille CSV : ligne 1 = lettres de colonne (A,B,…), cellule = suffixe numérique → code {Lettre}{cellule} (ex. A133)."""
    if not csv_path.is_file():
        return []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if len(rows) < 2:
        return []
    headers = []
    for h in rows[0]:
        t = (h or "").strip().upper()
        if t:
            headers.append(t)
    ncols = len(headers)
    codes = []
    for row in rows[1:]:
        for i in range(ncols):
            if i >= len(row):
                continue
            cell = (row[i] or "").strip()
            if not cell:
                continue
            codes.append(f"{headers[i]}{cell}".upper())
    return sorted(set(codes))


def _migrate_emplacements_plan(conn):
    """Référentiel d'emplacements physically plan (MyStock recherche + fiches vides)."""
    conn.execute(
        """CREATE TABLE IF NOT EXISTS emplacements_plan (
            code TEXT PRIMARY KEY NOT NULL,
            imported_at TEXT NOT NULL
        )"""
    )
    csv_path = Path(__file__).resolve().parent / "data" / "emplacements_plan.csv"
    codes = _parse_emplacements_plan_csv(csv_path)
    if not codes:
        return
    now = datetime.now().isoformat()
    conn.execute("DELETE FROM emplacements_plan")
    conn.executemany(
        "INSERT INTO emplacements_plan (code, imported_at) VALUES (?, ?)",
        [(c, now) for c in codes],
    )


def _migrate(conn):
    """Ajoute colonnes manquantes sur base existante sans tout recréer."""
    existing_pd = {row[1] for row in conn.execute("PRAGMA table_info(production_data)").fetchall()}
    for col, sql in [
        ("est_manuel",    "ALTER TABLE production_data ADD COLUMN est_manuel INTEGER DEFAULT 0"),
        ("modifie_par",   "ALTER TABLE production_data ADD COLUMN modifie_par TEXT"),
        ("modifie_le",    "ALTER TABLE production_data ADD COLUMN modifie_le TEXT"),
        ("modifie_note",  "ALTER TABLE production_data ADD COLUMN modifie_note TEXT"),
        ("commentaire",   "ALTER TABLE production_data ADD COLUMN commentaire TEXT"),
        ("metrage_prevu", "ALTER TABLE production_data ADD COLUMN metrage_prevu REAL"),
        ("metrage_reel",  "ALTER TABLE production_data ADD COLUMN metrage_reel REAL"),
    ]:
        if col not in existing_pd:
            conn.execute(sql)

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
    ]:
        if col not in existing_users:
            conn.execute(sql)

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
            ("numero_of", "ALTER TABLE planning_entries ADD COLUMN numero_of TEXT"),
            ("ref_produit", "ALTER TABLE planning_entries ADD COLUMN ref_produit TEXT"),
            ("laize", "ALTER TABLE planning_entries ADD COLUMN laize REAL"),
            ("date_livraison", "ALTER TABLE planning_entries ADD COLUMN date_livraison TEXT"),
            ("commentaire", "ALTER TABLE planning_entries ADD COLUMN commentaire TEXT"),
            ("planned_start", "ALTER TABLE planning_entries ADD COLUMN planned_start TEXT"),
            ("planned_end", "ALTER TABLE planning_entries ADD COLUMN planned_end TEXT"),
            ("statut_force", "ALTER TABLE planning_entries ADD COLUMN statut_force INTEGER DEFAULT 0"),
        ]:
            if col not in pe_cols:
                conn.execute(sql)

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
            unite TEXT DEFAULT 'unité',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )""")

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

    _migrate_emplacements_plan(conn)

    try:
        conn.execute("UPDATE machines SET nom='Cohésio 1' WHERE nom='Cohésion 1'")
    except sqlite3.Error:
        pass


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

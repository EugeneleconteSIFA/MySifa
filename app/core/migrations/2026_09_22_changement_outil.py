"""Changement d'outil : quel outil sort, quel outil entre, et à quel métrage.

Le constat (22/09/2026)
-----------------------
« 60 - Changement Plaque » ne dit que l'heure. Sur les douze derniers mois,
les quatre codes de changement d'outil (59, 60, 74, 75) totalisent une
centaine de saisies dont aucune ne permet de répondre à la seule question
qu'on se pose ensuite : quelle plaque a tourné, et sur combien de mètres.
Sans le numéro de l'outil sortant et celui de l'outil entrant, impossible de
rattacher une casse ou une dérive de qualité à un outil précis ; sans le
compteur machine au moment du changement, impossible de compter les mètres
qu'un outil a faits depuis sa dernière pose.

Ce que la migration installe
----------------------------
`outil_types`   — les natures d'outil montables. Ce n'est pas une constante
    du code : l'atelier en ajoutera (anilox, couteaux…) sans passer par une
    release. Seedée avec les quatre natures qui ont déjà un code opération.

`outils`        — le référentiel lui-même, un numéro par ligne et par nature.
    Unique sur (type_cle, numero). Un outil ne se supprime pas, il se
    désactive : les saisies passées pointent dessus. `a_valider` marque les
    numéros créés au poste par un conducteur qui ne trouvait pas le sien
    dans la liste — l'atelier n'est jamais bloqué, l'administrateur relit
    après coup.

`operation_codes.outil_type` — c'est CE lien qui décide si un code déclenche
    la saisie d'un changement d'outil, pas une liste de codes en dur dans le
    front ou le back. Seedé 60 → plaque, 59 → contre-partie, 74 → magnétique,
    75 → cliché ; modifiable dans Paramètres › Opérations.

`production_data.metrage_compteur` — le relevé du compteur machine au moment
    du changement. Colonne à part, JAMAIS metrage_prevu / metrage_reel :
    ces deux-là sont lus sans filtre de code par la rentabilité, le planning
    et les stats de dossier, où ils signifient « compteur au début / à la fin
    du dossier ». Y écrire le relevé d'un code 60 fausserait les vitesses.

`production_data.outil_avant_id` / `outil_apres_id` — l'outil démonté et
    l'outil monté, par identifiant : le numéro reste lisible même renommé.

Seed du référentiel plaques : les numéros d'outil déjà connus des fiches
techniques (`outil1/2/3_numero_sifa` dont la forme est une plaque ou une
spéciale). Les trois autres natures démarrent vides — elles n'ont aucune
source, l'atelier les remplira à la première pose.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

NOM = "changement_outil_referentiel"

# Natures d'outil seedées. (cle, label, label_pluriel, ordre)
TYPES_SEED = [
    ("plaque",        "Plaque",        "Plaques",         10),
    ("contre_partie", "Contre-partie", "Contre-parties",  20),
    ("magnetique",    "Magnétique",    "Magnétiques",     30),
    ("cliche",        "Cliché",        "Clichés",         40),
]

# Rattachement code opération → nature d'outil. Posé seulement si le code
# existe et n'a pas déjà une nature (l'administrateur reste maître).
CODES_SEED = {
    "59": "contre_partie",
    "60": "plaque",
    "74": "magnetique",
    "75": "cliche",
}

# Formes de fiche technique qui désignent un outil de découpe montable à la
# place d'une plaque. Comparaison sans accent ni casse, sur le début du mot.
# « Sheeter » en est volontairement absent : c'est un autre poste.
FORMES_PLAQUE = ("plaque", "special", "spéciale", "spécial", "speciale")


def _tables(conn: sqlite3.Connection) -> set:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def _sans_accent(txt: str) -> str:
    out = str(txt or "").strip().lower()
    for a, b in (("é", "e"), ("è", "e"), ("ê", "e"), ("à", "a"), ("ç", "c")):
        out = out.replace(a, b)
    return out


def _est_forme_plaque(forme: str) -> bool:
    f = _sans_accent(forme)
    if not f:
        return False
    return any(f.startswith(_sans_accent(p)) for p in FORMES_PLAQUE)


def appliquer(conn: sqlite3.Connection) -> None:
    maintenant = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # ── 1. Natures d'outil ───────────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS outil_types (
            cle           TEXT PRIMARY KEY,
            label         TEXT    NOT NULL,
            label_pluriel TEXT,
            ordre         INTEGER NOT NULL DEFAULT 0,
            actif         INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT,
            updated_at    TEXT
        )
    """)
    n_types = 0
    for cle, label, pluriel, ordre in TYPES_SEED:
        cur = conn.execute(
            """INSERT OR IGNORE INTO outil_types
               (cle, label, label_pluriel, ordre, actif, created_at)
               VALUES (?,?,?,?,1,?)""",
            (cle, label, pluriel, ordre, maintenant),
        )
        n_types += cur.rowcount or 0

    # ── 2. Référentiel des outils ────────────────────────────────────────
    conn.execute("""
        CREATE TABLE IF NOT EXISTS outils (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            type_cle   TEXT    NOT NULL,
            numero     TEXT    NOT NULL,
            label      TEXT,
            actif      INTEGER NOT NULL DEFAULT 1,
            a_valider  INTEGER NOT NULL DEFAULT 0,
            cree_par   TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_outils_type_numero "
        "ON outils(type_cle, numero)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_outils_type_actif ON outils(type_cle, actif)"
    )

    # ── 3. Le code opération porte la nature d'outil ─────────────────────
    if "operation_codes" in _tables(conn):
        if "outil_type" not in _colonnes(conn, "operation_codes"):
            conn.execute("ALTER TABLE operation_codes ADD COLUMN outil_type TEXT")
        for code, type_cle in CODES_SEED.items():
            conn.execute(
                """UPDATE operation_codes
                   SET outil_type = ?, updated_at = ?
                   WHERE code = ? AND COALESCE(outil_type, '') = ''""",
                (type_cle, maintenant, code),
            )

    # ── 4. Colonnes de saisie ────────────────────────────────────────────
    cols_pd = _colonnes(conn, "production_data")
    for nom, ddl in (
        ("metrage_compteur", "ALTER TABLE production_data ADD COLUMN metrage_compteur REAL"),
        ("outil_avant_id",   "ALTER TABLE production_data ADD COLUMN outil_avant_id INTEGER"),
        ("outil_apres_id",   "ALTER TABLE production_data ADD COLUMN outil_apres_id INTEGER"),
    ):
        if nom not in cols_pd:
            conn.execute(ddl)

    # ── 5. Seed des plaques depuis les fiches techniques ─────────────────
    n_outils = 0
    if "fiches_techniques" in _tables(conn):
        cols_ft = _colonnes(conn, "fiches_techniques")
        paires = [
            (f"outil{i}_forme", f"outil{i}_numero_sifa")
            for i in (1, 2, 3)
            if f"outil{i}_forme" in cols_ft and f"outil{i}_numero_sifa" in cols_ft
        ]
        vus = {}
        for col_forme, col_num in paires:
            rows = conn.execute(
                f"""SELECT DISTINCT TRIM({col_forme}) AS forme, TRIM({col_num}) AS numero
                    FROM fiches_techniques
                    WHERE COALESCE(TRIM({col_num}), '') <> ''"""
            ).fetchall()
            for r in rows:
                numero = (r["numero"] if hasattr(r, "keys") else r[1]) or ""
                forme = (r["forme"] if hasattr(r, "keys") else r[0]) or ""
                numero = str(numero).strip()
                if not numero or numero == "0" or not _est_forme_plaque(forme):
                    continue
                vus.setdefault(numero, str(forme).strip())
        for numero, forme in sorted(vus.items()):
            cur = conn.execute(
                """INSERT OR IGNORE INTO outils
                   (type_cle, numero, label, actif, a_valider, cree_par, created_at)
                   VALUES ('plaque', ?, ?, 1, 0, 'migration', ?)""",
                (numero, forme or None, maintenant),
            )
            n_outils += cur.rowcount or 0

    conn.commit()
    print(
        f"[MySifa] migration {NOM} : {n_types} nature(s) d'outil seedée(s), "
        f"{n_outils} plaque(s) reprise(s) des fiches techniques."
    )

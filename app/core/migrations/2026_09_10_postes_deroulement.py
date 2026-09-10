"""Postes de déroulement par machine, et règles de reconnaissance des bobines.

Le constat qui a ouvert le chantier (10/09/2026)
------------------------------------------------
Sur 39 fins de production sans aucun code matière scanné, 19 réponses disent
« Bobine déjà scannée sur un dossier précédent » et 16 se contentent d'un point.
Aucun code-barres n'a jamais été scanné sur deux dossiers. La raison est
mécanique : une Cohésio a un poste de déroulement FRONTAL et un poste GLASSINE,
chacun à deux places (la seconde bobine prend le relais sans arrêter la
machine), et au changement de dossier on garde presque toujours la glassine,
parfois aussi le frontal. Un scan rattaché au seul dossier perd donc la bobine
dès le dossier suivant.

Pour suivre ce qui est MONTÉ sur une machine, il faut d'abord savoir quels
postes elle a. C'est une donnée d'atelier, pas une constante : elle vit ici.

Deux tables
-----------
`machine_postes_deroulement`  — une ligne par (machine, poste) avec son nombre
    de places. Seedée à 2 places frontal + 2 places glassine pour chaque
    machine qui consomme de la matière (`sans_matiere_premiere = 0`) ; le
    repiquage n'en reçoit aucune. Tout se corrige dans Paramètres › Machines.

`fournisseur_regles_code`     — pour un fournisseur qui livre plusieurs
    natures de bobines, le PRÉFIXE du code-barres qui désigne chacune. Le
    motif le plus long gagne ; un motif vide vaut « tout autre code ». Relevé
    atelier : chez Likexin, un code commençant par G est une glassine, tout le
    reste est un frontal. C'est la seule règle seedée, et seulement si la fiche
    fournisseur existe — une autre instance démarre avec une table vide.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

NOM = "postes_deroulement"


def _tables(conn: sqlite3.Connection) -> set:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def appliquer(conn: sqlite3.Connection) -> None:
    maintenant = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS machine_postes_deroulement (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id  INTEGER NOT NULL,
            poste       TEXT    NOT NULL,            -- 'frontal' | 'glassine'
            places      INTEGER NOT NULL DEFAULT 2,
            actif       INTEGER NOT NULL DEFAULT 1,
            updated_at  TEXT,
            updated_by  TEXT,
            UNIQUE(machine_id, poste)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fournisseur_regles_code (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            fournisseur_id  INTEGER NOT NULL,
            motif           TEXT    NOT NULL DEFAULT '',   -- préfixe ; '' = tout autre code
            categorie       TEXT    NOT NULL,              -- 'frontal' | 'complexe' | 'glassine'
            note            TEXT,
            actif           INTEGER NOT NULL DEFAULT 1,
            created_at      TEXT    NOT NULL,
            updated_at      TEXT,
            updated_by      TEXT,
            UNIQUE(fournisseur_id, motif)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_fourn_regles_code_f "
        "ON fournisseur_regles_code(fournisseur_id, actif)"
    )
    conn.commit()

    n_postes = 0
    if "machines" in _tables(conn):
        cols = _colonnes(conn, "machines")
        filtre = "WHERE COALESCE(sans_matiere_premiere,0)=0" if "sans_matiere_premiere" in cols else ""
        for m in conn.execute("SELECT id FROM machines %s" % filtre).fetchall():
            for poste in ("frontal", "glassine"):
                cur = conn.execute(
                    """INSERT OR IGNORE INTO machine_postes_deroulement
                       (machine_id, poste, places, actif, updated_at, updated_by)
                       VALUES (?,?,2,1,?,'migration')""",
                    (int(m[0]), poste, maintenant),
                )
                n_postes += cur.rowcount or 0

    n_regles = 0
    if "fournisseurs_fsc" in _tables(conn):
        f = conn.execute(
            "SELECT id FROM fournisseurs_fsc WHERE lower(trim(nom))='likexin' LIMIT 1"
        ).fetchone()
        if f:
            for motif, categorie, note in (
                ("G", "glassine", "Relevé atelier : les codes G sont des glassines."),
                ("", "frontal", "Relevé atelier : tout autre code est un frontal."),
            ):
                cur = conn.execute(
                    """INSERT OR IGNORE INTO fournisseur_regles_code
                       (fournisseur_id, motif, categorie, note, actif, created_at, updated_by)
                       VALUES (?,?,?,?,1,?,'migration')""",
                    (int(f[0]), motif, categorie, note, maintenant),
                )
                n_regles += cur.rowcount or 0
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n_postes} poste(s), {n_regles} règle(s) de code seedé(s).")

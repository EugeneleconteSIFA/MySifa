"""
MyExpé — note de confiance transporteur (A → F).

Trois objets :

* `expe_avis_thematiques` — référentiel des sujets sur lesquels on juge un
  transporteur. Éditable dans MyExpé › Référentiel : rien de métier n'est codé
  en dur, et le poids de chaque thématique se règle sans toucher au code (une
  marchandise cassée ne pèse pas comme un retard d'une heure).
* `expe_transporteur_avis` — un enregistrement par avis émis sur une
  expédition, et par ajustement manuel de la note. Les deux vivent dans la même
  table parce qu'ils apparaissent dans le même historique : un ajustement sans
  trace serait une note qui bouge sans raison lisible.
* quatre colonnes de cache sur `expe_transporteurs` — la note est recalculée à
  chaque écriture d'avis, pas à chaque lecture, parce qu'elle est lue partout
  (liste, comparateur, zones) et écrite rarement.

Le seed des thématiques est idempotent : `INSERT OR IGNORE` sur `code`.
"""

NOM = "expe_notes_transporteurs"


_THEMATIQUES = [
    # (code, libellé, sens, poids, ordre)
    ("ponctualite", "Ponctualité (enlèvement et livraison)", "les_deux", 1.0, 10),
    ("etat_marchandise", "État de la marchandise (casse, humidité)", "les_deux", 1.5, 20),
    ("perte_colis", "Colis perdu ou égaré", "alerte", 2.0, 30),
    ("respect_consignes", "Respect des consignes de livraison", "les_deux", 1.0, 40),
    ("facturation", "Facturation conforme au prix annoncé", "les_deux", 1.2, 50),
    ("palettes_europe", "Palettes Europe (retour, litige)", "les_deux", 0.8, 60),
    ("reactivite", "Réactivité commerciale", "les_deux", 0.8, 70),
    ("communication", "Communication et suivi d'expédition", "les_deux", 0.8, 80),
    ("documents", "Documents de transport (BL, émargement)", "les_deux", 0.8, 90),
    ("depannage", "Dépannage sur un envoi urgent", "appreciation", 1.0, 100),
]


def _colonnes(conn, table: str) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expe_avis_thematiques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            libelle TEXT NOT NULL,
            sens TEXT NOT NULL DEFAULT 'les_deux',
            poids REAL NOT NULL DEFAULT 1.0,
            ordre INTEGER NOT NULL DEFAULT 100,
            actif INTEGER NOT NULL DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expe_transporteur_avis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transporteur_id INTEGER NOT NULL,
            depart_id INTEGER,
            type TEXT NOT NULL DEFAULT 'avis',
            sens TEXT NOT NULL DEFAULT 'appreciation',
            note REAL,
            thematique_id INTEGER,
            commentaire TEXT,
            ajustement REAL,
            depart_ref TEXT,
            auteur_email TEXT,
            auteur_nom TEXT,
            created_at TEXT,
            updated_at TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_expe_avis_trp "
        "ON expe_transporteur_avis(transporteur_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_expe_avis_depart "
        "ON expe_transporteur_avis(depart_id)"
    )

    cols = _colonnes(conn, "expe_transporteurs")
    for nom_col, decl in (
        ("note_valeur", "REAL"),
        ("note_lettre", "TEXT"),
        ("note_nb_avis", "INTEGER NOT NULL DEFAULT 0"),
        ("note_maj_le", "TEXT"),
    ):
        if nom_col not in cols:
            conn.execute(
                f"ALTER TABLE expe_transporteurs ADD COLUMN {nom_col} {decl}"
            )

    ajoutes = 0
    for code, libelle, sens, poids, ordre in _THEMATIQUES:
        cur = conn.execute(
            """INSERT OR IGNORE INTO expe_avis_thematiques
               (code, libelle, sens, poids, ordre, actif, created_at)
               VALUES (?,?,?,?,?,1,datetime('now'))""",
            (code, libelle, sens, poids, ordre),
        )
        ajoutes += cur.rowcount or 0

    conn.commit()
    print(f"[MySifa] migration {NOM} : {ajoutes} thematique(s) d'avis seedee(s).")

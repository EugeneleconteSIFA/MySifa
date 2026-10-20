"""Révision d'une demande de tarif transport après envoi (MyExpé).

Une demande partie chez les transporteurs était figée : corriger un poids ou un
code postal obligeait à la clôturer, la dupliquer et tout renvoyer, ce qui
changeait la référence et dispersait les offres sur deux demandes. On garde
désormais la même demande, qui passe en révision suivante :

- `expe_demandes_devis.revision` : 0 tant que la demande n'a jamais été
  modifiée après envoi, puis 1, 2… à chaque modification qui demande un
  nouveau chiffrage. `revise_le` date la dernière ;
- `expe_devis_reponses.revision_offre` : révision sur laquelle le
  transporteur a chiffré. Une offre dont la révision est inférieure à celle
  de la demande est « à confirmer » — elle reste visible, mais elle porte sur
  des données qui ont changé ;
- `expe_devis_revisions` : une ligne par modification après envoi (champs
  avant / après, renvoi ou simple information, message, nombre d'emails).
  C'est ce que le portail montre au transporteur et ce que l'historique
  interne relit.

Les offres existantes reçoivent `revision_offre = 0`, ce qui est exact : aucune
demande n'a pu être révisée avant cette migration.
"""

NOM = "expe_devis_revisions"


def appliquer(conn):
    cols_d = {r[1] for r in conn.execute("PRAGMA table_info(expe_demandes_devis)").fetchall()}
    cols_r = {r[1] for r in conn.execute("PRAGMA table_info(expe_devis_reponses)").fetchall()}
    if not cols_d or not cols_r:
        # Tables pas encore créées : `_migrate()` les crée avant les
        # migrations fichier, ce cas ne se produit que sur une base vide.
        return
    if "revision" not in cols_d:
        conn.execute(
            "ALTER TABLE expe_demandes_devis ADD COLUMN revision INTEGER NOT NULL DEFAULT 0"
        )
    if "revise_le" not in cols_d:
        conn.execute("ALTER TABLE expe_demandes_devis ADD COLUMN revise_le TEXT")
    if "revision_offre" not in cols_r:
        conn.execute(
            "ALTER TABLE expe_devis_reponses ADD COLUMN revision_offre INTEGER NOT NULL DEFAULT 0"
        )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS expe_devis_revisions (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            demande_id       INTEGER NOT NULL,
            revision         INTEGER NOT NULL,
            rechiffrage      INTEGER NOT NULL DEFAULT 0,
            changements      TEXT NOT NULL,
            message          TEXT,
            nb_envoyes       INTEGER NOT NULL DEFAULT 0,
            nb_echecs        INTEGER NOT NULL DEFAULT 0,
            created_at       TEXT NOT NULL,
            created_by_email TEXT,
            FOREIGN KEY (demande_id) REFERENCES expe_demandes_devis(id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_expe_devis_revisions_demande "
        "ON expe_devis_revisions(demande_id)"
    )
    conn.commit()

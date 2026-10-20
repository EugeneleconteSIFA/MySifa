"""
MyQualité › Formulaires : outil de création de formulaires.

Un formulaire est un questionnaire libre (sections, questions) construit dans
l'éditeur de MyQualité ou proposé par l'IA, puis envoyé à des fournisseurs, au
personnel ou à des clients (envoi et réponses : lot suivant, sur le modèle
d'EUDR).

qualite_formulaires : le formulaire en cours d'édition. `schema_json` est le
  brouillon, modifiable à tout moment.
qualite_formulaires_versions : une ligne par publication, jamais modifiée.
  Un envoi pointe vers une version : une réponse reste lisible avec les
  questions telles qu'elles étaient le jour où elle a été donnée.
"""

NOM = "qualite_formulaires"


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS qualite_formulaires (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            titre             TEXT NOT NULL,
            description       TEXT NOT NULL DEFAULT '',
            statut            TEXT NOT NULL DEFAULT 'brouillon',
            schema_json       TEXT NOT NULL DEFAULT '{}',
            version_courante  INTEGER NOT NULL DEFAULT 0,
            cree_par          TEXT,
            cree_le           TEXT NOT NULL,
            modifie_par       TEXT,
            modifie_le        TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS qualite_formulaires_versions (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            formulaire_id  INTEGER NOT NULL,
            numero         INTEGER NOT NULL,
            titre          TEXT NOT NULL,
            schema_json    TEXT NOT NULL,
            publie_par     TEXT,
            publie_le      TEXT NOT NULL,
            UNIQUE (formulaire_id, numero),
            FOREIGN KEY (formulaire_id) REFERENCES qualite_formulaires(id)
        )
        """
    )
    conn.commit()

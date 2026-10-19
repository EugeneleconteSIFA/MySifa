"""
MyQualité — questionnaire EUDR : lien commun.

En plus des liens personnels (un par fournisseur et par adresse), un lien
commun peut être collé dans un email adressé à plusieurs fournisseurs, ou
transmis par un distributeur à ses usines. Celui qui répond indique sa
société sur la page d'accueil ; la réponse n'appartient encore à aucune fiche.

eudr_liens_communs : un lien par usage (libellé libre), désactivable.
eudr_reponses_commun : les réponses reçues par un lien commun, en attente de
  rattachement. Le rattachement à une fiche fournisseur crée la vraie réponse
  dans eudr_reponses (source 'lien_commun') et garde ici la trace de qui l'a
  rattachée et quand.
"""

NOM = "qualite_eudr_lien_commun"
DEPEND = ["qualite_eudr_questionnaire"]


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS eudr_liens_communs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            token       TEXT NOT NULL UNIQUE,
            libelle     TEXT NOT NULL,
            langue      TEXT NOT NULL DEFAULT 'en',
            actif       INTEGER NOT NULL DEFAULT 1,
            cree_par    TEXT,
            created_at  TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS eudr_reponses_commun (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            lien_id                 INTEGER NOT NULL,
            donnees                 TEXT NOT NULL,
            repondant_societe       TEXT,
            repondant_nom           TEXT,
            repondant_email         TEXT,
            ip                      TEXT,
            created_at              TEXT NOT NULL,
            rattache_fournisseur_id INTEGER,
            reponse_id              INTEGER,
            rattache_par            TEXT,
            rattache_le             TEXT,
            FOREIGN KEY (lien_id) REFERENCES eudr_liens_communs(id)
        )
        """
    )
    conn.commit()

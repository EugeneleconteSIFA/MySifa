"""
Historique des prix au niveau de la déclinaison.

`mp_valorisation_historique` trace les prix au niveau de la MATIÈRE : elle ne
sait pas dire quelle laize ni quel grammage a bougé, ni depuis quel écran. Avec
deux applications qui écrivent le même prix — la valorisation MyStock et la
fiche Coûts matières — il faut pouvoir répondre à « qui a changé quoi, où ».

On garde les deux valeurs :

- `prix` : ce qu'on paie au fournisseur, dans sa devise et sa base ;
- `sous_total` : ce même prix augmenté du transport et des taxes, c'est-à-dire
  la valeur affichée par la valorisation MyStock.

Les deux, parce qu'un changement de paramétrage (transport, taxes) déplace le
sous-total sans toucher au prix d'achat : sans la seconde colonne, l'historique
montrerait un prix immobile et une valorisation qui bouge.
"""

NOM = "mp_prix_historique_declinaison"
DEPEND = ["mp_declinaison_parametrage_prix"]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS mp_prix_historique (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            declinaison_id  INTEGER NOT NULL
                            REFERENCES mp_matiere_declinaison(id) ON DELETE CASCADE,
            matiere_id      INTEGER,
            fournisseur_id  INTEGER,
            prix_avant      REAL,
            prix_apres      REAL,
            sous_total_avant REAL,
            sous_total_apres REAL,
            -- Écran d'où vient la modification : « Coûts matières — fiche
            -- matière », « MyStock — valorisation », « PMP entrée en stock »…
            origine         TEXT,
            note            TEXT,
            created_at      TEXT NOT NULL
                            DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
            created_by      INTEGER,
            created_by_name TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_mph_decl
            ON mp_prix_historique(declinaison_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_mph_date
            ON mp_prix_historique(created_at DESC);
        """
    )
    conn.commit()

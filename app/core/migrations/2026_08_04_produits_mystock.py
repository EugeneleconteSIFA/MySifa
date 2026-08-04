"""
Produits devisés à partir des matières MyStock.

La base « Coûts matières » a ses produits (`mc_product`), composés de fiches
`mc_material`. Comme cette base est destinée à disparaître, il faut son
équivalent côté MyStock : un produit composé de DÉCLINAISONS — une laize précise
d'un frontal, un grammage précis d'un adhésif.

Deux tables plutôt que quatre colonnes de rôles : un produit peut porter autant
de composants que nécessaire, et le rôle n'est qu'une étiquette. Les quatre rôles
usuels (frontal, adhésif, silicone, glassine) restent des emplacements uniques,
les autres matières s'ajoutent librement.
"""

NOM = "mp_produits_mystock"
DEPEND = ["mp_declinaison_parametrage_prix"]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS mp_produit (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            code              TEXT NOT NULL,
            designation       TEXT NOT NULL,
            -- Marge propre au produit, en % du prix de revient. NULL = marge
            -- par défaut des paramètres globaux.
            custom_margin_pct REAL,
            actif             INTEGER NOT NULL DEFAULT 1,
            note              TEXT,
            created_at        TEXT NOT NULL
                              DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
            updated_at        TEXT NOT NULL
                              DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
            updated_by_name   TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mp_produit_code
            ON mp_produit(code COLLATE NOCASE);

        CREATE TABLE IF NOT EXISTS mp_produit_composant (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            produit_id     INTEGER NOT NULL
                           REFERENCES mp_produit(id) ON DELETE CASCADE,
            declinaison_id INTEGER NOT NULL
                           REFERENCES mp_matiere_declinaison(id) ON DELETE CASCADE,
            -- FRONTAL, ADHESIF, SILICONE, GLASSINE ou AUTRE.
            role           TEXT NOT NULL DEFAULT 'AUTRE',
            ordre          INTEGER NOT NULL DEFAULT 0
        );
        -- Une même déclinaison ne peut pas entrer deux fois dans un produit :
        -- son coût serait compté en double sans que ça se voie.
        CREATE UNIQUE INDEX IF NOT EXISTS idx_mppc_unique
            ON mp_produit_composant(produit_id, declinaison_id);
        CREATE INDEX IF NOT EXISTS idx_mppc_produit
            ON mp_produit_composant(produit_id);
        """
    )
    conn.commit()

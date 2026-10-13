"""Annulation d'une reception RVGI integree par erreur.

Annuler rend la ligne a la file « Depuis l'ERP » : la ligne quitte
`erp_reception_integree` et le stock est repris par un mouvement de sortie. Mais
`integrer_tout` tourne apres chaque reconstruction du miroir : sans trace, la
ligne annulee rentrerait en stock toute seule a la synchro suivante. Cette
table garde la trace, et la ligne n'entre plus qu'a la main.
"""

NOM = "reception_rvgi_annulee"


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS erp_reception_annulee (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            lif_id          INTEGER NOT NULL,
            matiere_id      INTEGER,
            laize_id        INTEGER,
            quantite        REAL,
            unite           TEXT,
            regime          TEXT,
            integre_at      TEXT,
            integre_par     TEXT,
            mouvement_id    INTEGER,
            annule_at       TEXT NOT NULL,
            annule_par      TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_era_lif ON erp_reception_annulee(lif_id);
        """
    )
    conn.commit()

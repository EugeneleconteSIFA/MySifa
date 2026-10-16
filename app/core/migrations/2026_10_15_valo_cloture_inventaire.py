"""
Clôture d'inventaire de la valorisation MyStock.

L'inventaire physique du 01/10/2026 et les prix revus ensuite (cartons, encres,
matières) ont été saisis après le 30/09, alors qu'ils décrivent le stock du
30/09 au soir. La valorisation figée à une date ne lit que la date de saisie :
elle ne pouvait pas les prendre en compte.

- valo_clotures : une ligne par date de clôture, avec la date limite jusqu'à
  laquelle un prix saisi vaut pour cette clôture.
- valo_cloture_mouvements : les mouvements de stock (MP ou PF) saisis après la
  clôture mais rattachés à elle. Un mouvement ne se rattache qu'à une clôture.
"""

NOM = "valo_cloture_inventaire"


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS valo_clotures (
               date_cloture     TEXT PRIMARY KEY,
               date_limite_prix TEXT,
               updated_at       TEXT,
               updated_by_name  TEXT
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS valo_cloture_mouvements (
               source        TEXT NOT NULL,
               mouvement_id  INTEGER NOT NULL,
               date_cloture  TEXT NOT NULL,
               created_at    TEXT,
               PRIMARY KEY (source, mouvement_id)
           )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_valo_cloture_mvts_date "
        "ON valo_cloture_mouvements(date_cloture)"
    )
    conn.commit()

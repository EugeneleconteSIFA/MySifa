"""
Mandrins : longueur du tube acheté + perte de coupe globale.

Un mandrin s'achète en tube (« Tube 1500x76 » : 1500 mm de long, diamètre 76)
qu'on redécoupe ensuite à la laize du module. Deux données manquaient pour
chiffrer le besoin :

- `matieres_premieres.longueur_tube_mm` : la longueur du tube acheté, portée
  par la référence matière — c'est elle qui fait foi, pas la chaîne de la
  fiche technique, qui n'est qu'un libellé de saisie ;
- `stock_config.mandrin_perte_coupe_pct` : la perte de coupe appliquée à
  cette longueur (chutes de fin de tube), réglable dans Paramètres.

`stock_config` est une table clé/valeur générique pour MyStock : les réglages
d'atelier vivent en base et s'éditent dans Paramètres, jamais en dur dans le
code.
"""

NOM = "mandrin_longueur_tube_et_perte_coupe"


def appliquer(conn):
    cols = {r["name"] for r in conn.execute(
        "PRAGMA table_info(matieres_premieres)").fetchall()}
    if "longueur_tube_mm" not in cols:
        conn.execute(
            "ALTER TABLE matieres_premieres ADD COLUMN longueur_tube_mm REAL")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_config (
            cle        TEXT PRIMARY KEY,
            valeur     TEXT NOT NULL,
            updated_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
            updated_by INTEGER
        )
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO stock_config (cle, valeur) "
        "VALUES ('mandrin_perte_coupe_pct', '10')"
    )
    conn.commit()
    print("[MySifa] migration mandrin_longueur_tube_et_perte_coupe : "
          "colonne longueur_tube_mm + table stock_config prêtes.")

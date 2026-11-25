"""
ADV : une règle de mise en forme peut colorer une AUTRE colonne que celle de
sa condition, ou toute la ligne, et choisir son rendu.

- `appliquer` : vide = la colonne de la condition (comportement d'origine),
  `ligne` = toute la ligne, sinon la clé de la colonne à colorer
  (« si Expédition avant aujourd'hui, colorer Client en rouge ») ;
- `rendu` : `fond` (pastille teintée, d'origine) ou `texte` (texte coloré seul).

Le ton accepte aussi les teintes de la palette élargie (`rouge-2`, `vert-1`…),
voir ADV_MEF_TEINTES dans config.py. Les anciens tons restent valides.
"""

NOM = "adv_mef_appliquer"
DEPEND = ["adv_mises_en_forme"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(adv_mises_en_forme)").fetchall()}
    if "appliquer" not in cols:
        conn.execute("ALTER TABLE adv_mises_en_forme ADD COLUMN appliquer TEXT NOT NULL DEFAULT ''")
    if "rendu" not in cols:
        conn.execute("ALTER TABLE adv_mises_en_forme ADD COLUMN rendu TEXT NOT NULL DEFAULT 'fond'")
    conn.commit()

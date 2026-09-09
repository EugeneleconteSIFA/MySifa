"""
Import automatique des devis depuis le partage réseau — traçabilité minimale.

Un devis déposé par l'agent entre en base sans qu'un humain l'ait relu. C'est
un choix assumé : la saisie manuelle de centaines de devis n'aurait jamais
lieu, et un devis lu automatiquement vaut mieux qu'un devis absent. Mais il
faut alors pouvoir distinguer, dans la liste, ce qui a été vu de ce qui ne
l'a pas été, et ce qui mérite un coup d'œil de ce qui tient debout tout seul.

D'où trois colonnes :

- `empreinte` : sha-256 du fichier, en index unique. C'est elle qui rend
  l'agent rejouable — un devis renommé, recopié ou déplacé d'un dossier
  d'année à l'autre reste le même document et n'entre pas deux fois. La même
  garantie que pour les scans d'OF, et pour la même raison : le dossier source
  appartient à quelqu'un d'autre, on n'y range rien.
- `source` : `manuel` (déposé dans MyProd) ou `agent` (ramassé sur le partage).
  Sans elle, impossible de savoir si un chiffre a été confirmé par quelqu'un.
- `a_verifier` : posé par le serveur quand la lecture laisse un doute — champ
  clé introuvable, ou contrôle de cohérence en défaut. C'est ce drapeau qui
  dirige le regard vers les quelques devis à reprendre au lieu de laisser
  relire les centaines qui vont bien.
"""

NOM = "devis_import_agent"
DEPEND = ["devis_extraction_ia_indicateurs"]


_COLONNES = [
    ("empreinte", "TEXT"),
    ("source", "TEXT"),
    ("a_verifier", "INTEGER DEFAULT 0"),
    ("chemin_origine", "TEXT"),
]


def appliquer(conn):
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "devis" not in tables:
        print("[MySifa] migration devis_import_agent : table devis absente, rien à faire.")
        return

    cols = {r[1] for r in conn.execute("PRAGMA table_info(devis)").fetchall()}
    ajoutees = 0
    for nom, typ in _COLONNES:
        if nom not in cols:
            conn.execute(f"ALTER TABLE devis ADD COLUMN {nom} {typ}")
            ajoutees += 1

    # Index unique sur l'empreinte : c'est le garde-fou anti-doublon de
    # l'agent. SQLite autorise plusieurs NULL dans un index unique, donc les
    # devis déjà en base (sans empreinte) ne se gênent pas entre eux.
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_devis_empreinte "
        "ON devis(empreinte) WHERE empreinte IS NOT NULL"
    )

    # Tout ce qui existait avant l'agent a été déposé à la main.
    repris = conn.execute(
        "UPDATE devis SET source='manuel' WHERE source IS NULL OR source=''"
    ).rowcount

    conn.commit()
    print(
        f"[MySifa] migration devis_import_agent : {ajoutees} colonne(s) ajoutée(s), "
        f"{repris} devis marqué(s) « manuel »."
    )

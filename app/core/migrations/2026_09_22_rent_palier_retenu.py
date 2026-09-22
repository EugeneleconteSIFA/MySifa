"""
Le palier de quantité retenu pour comparer un dossier à son devis.

Un devis chiffre souvent plusieurs quantités — la moitié des réserves levées
à l'import portent sur ce point, et dans près d'un cas sur deux les deux
paliers sont dans un rapport de un à deux. Le classeur ne calcule les temps
que pour l'un d'eux, pas forcément celui du dossier : comparer la production
réelle à ces temps-là donne un écart faux, parfois d'un facteur dix.

Le palier retenu vit sur la LIAISON, pas sur le devis. Un même devis sert
plusieurs dossiers — une première série puis un réassort — et chacun a sa
quantité. Le poser sur `devis` ferait mentir la lecture du fichier pour tous
les autres dossiers dès qu'un seul serait recalé.

- `qte_retenue` : la quantité sur laquelle les temps devisés sont ramenés.
  Elle ne vaut pas forcément un palier : entre deux paliers, on proratise sur
  la quantité exacte de l'OF.
- `palier_rang` : le rang du palier d'origine (1, 2, 3…), pour dire d'où
  vient le chiffre. NULL quand la quantité ne tombe sur aucun palier.
- `palier_valide_at` / `palier_valide_par` : tant que c'est vide, le recalage
  n'est qu'une proposition et les calculs gardent le palier du classeur.
  Même règle que le rattachement lui-même : la machine propose, l'humain
  tranche.
"""

NOM = "rent_palier_retenu"
DEPEND = ["rent_liens_origine_validation"]


_COLONNES = [
    ("qte_retenue", "REAL"),
    ("palier_rang", "INTEGER"),
    ("palier_valide_at", "TEXT"),
    ("palier_valide_par", "TEXT"),
]


def appliquer(conn):
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "rent_links" not in tables:
        print("[MySifa] migration rent_palier_retenu : table rent_links absente, rien à faire.")
        return

    cols = {r[1] for r in conn.execute("PRAGMA table_info(rent_links)").fetchall()}
    ajoutees = 0
    for nom, typ in _COLONNES:
        if nom not in cols:
            conn.execute(f"ALTER TABLE rent_links ADD COLUMN {nom} {typ}")
            ajoutees += 1
    conn.commit()
    print(f"[MySifa] migration rent_palier_retenu : {ajoutees} colonne(s) ajoutée(s). "
          "Les liaisons existantes gardent le palier du classeur tant qu'aucun "
          "recalage n'est confirmé.")

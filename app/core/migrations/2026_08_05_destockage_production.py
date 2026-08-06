"""
Déstockage matière à la clôture d'une production.

Quand une production est réellement terminée, la matière consommée doit sortir
du stock. Jusqu'ici le bouton « À destocker » ne faisait que changer un statut :
le stock, lui, ne bougeait pas — il fallait ressaisir les sorties à la main,
donc on ne les saisissait pas.

Trois colonnes suffisent à rattacher un mouvement de stock à sa production :

- `planning_entry_id` : le dossier qui a consommé la matière ;
- `no_dossier` : son libellé, pour que l'historique reste lisible même si le
  dossier est supprimé du planning ;
- `annule_mouvement_id` : la contre-passation. Annuler un déstockage n'efface
  rien, cela écrit le mouvement inverse en le rattachant à l'original. Les deux
  écritures restent visibles, ce qui est la seule façon honnête de raconter
  qu'on s'est trompé.
"""

NOM = "destockage_production_mouvements"

_COLONNES = (
    ("planning_entry_id", "INTEGER"),
    ("no_dossier", "TEXT"),
    ("annule_mouvement_id", "INTEGER"),
)


def appliquer(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(mp_mouvements)").fetchall()}
    if not cols:
        return  # table absente sur cette base (harnais de test) : rien à faire
    for nom, typ in _COLONNES:
        if nom not in cols:
            conn.execute(f"ALTER TABLE mp_mouvements ADD COLUMN {nom} {typ}")
    # L'historique d'un dossier se lit dossier par dossier : sans index, la
    # modale de déstockage scanne toute la table à chaque ouverture.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_mp_mouvements_planning "
        "ON mp_mouvements(planning_entry_id)"
    )
    conn.commit()
    print("[MySifa] migration destockage_production_mouvements : "
          "mp_mouvements rattachable à un dossier de production.")

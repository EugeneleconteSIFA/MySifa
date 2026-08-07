"""
La photo du carnet doit inclure ce qui est déjà produit.

`carnet_snapshots` ne photographiait que les dossiers en attente ou en cours —
53 sur 295 au 7 août 2026. C'est le bon périmètre pour répondre à « que
reste-t-il à approvisionner », et exactement le mauvais pour calibrer une
prévision.

Le modèle vise :

    p(k) = volume visible k mois avant M ÷ volume FINAL de M

Le dénominateur est le total qui aura été destiné au mois M. Or à mesure que M
approche, ses dossiers passent en « terminé » et sortaient de la photo : la
série d'un mois montait puis retombait à zéro le mois venu. Le volume final
n'était donc jamais enregistré, et p(k) se serait calculé sur du bruit — ce
qu'on aurait découvert en novembre, avec trois mois de série à jeter.

D'où deux quantités au lieu d'une :

- `quantite`        : tout ce qui vise ce mois, quel que soit le statut. C'est
                      le dénominateur, celui qui converge vers le volume final.
- `quantite_active` : la part encore à produire, seule grandeur utile pour
                      l'approvisionnement du jour.

`nb_dossiers` suit la même logique et reçoit `nb_dossiers_actifs` en regard.

Migration séparée plutôt que correction de `carnet_snapshots` : celle-ci est
déjà passée sur staging, son `NOM` est enregistré, et la modifier sur place
signifierait qu'elle ne rejoue jamais là où elle a déjà tourné.
"""

NOM = "carnet_snapshot_total"
DEPEND = ["carnet_snapshots"]

_COLONNES = (
    ("quantite_active", "REAL NOT NULL DEFAULT 0"),
    ("nb_dossiers_actifs", "INTEGER NOT NULL DEFAULT 0"),
)


def appliquer(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(carnet_snapshots)").fetchall()}
    if not cols:
        return  # table absente : la migration carnet_snapshots n'a rien créé ici
    for nom, ddl in _COLONNES:
        if nom not in cols:
            conn.execute(f"ALTER TABLE carnet_snapshots ADD COLUMN {nom} {ddl}")

    # Les photos déjà prises ne contenaient QUE des dossiers actifs : leur
    # `quantite` est donc en réalité une `quantite_active`, et leur total est
    # incomplet. On recopie pour que la colonne soit juste, mais ces lignes
    # restent inutilisables comme dénominateur — elles datent d'avant le
    # correctif et il n'y a rien à reconstituer.
    n = conn.execute(
        "UPDATE carnet_snapshots SET quantite_active = quantite, "
        "nb_dossiers_actifs = nb_dossiers WHERE quantite_active = 0"
    ).rowcount
    conn.commit()
    print(f"[MySifa] migration carnet_snapshot_total : la photo du carnet couvre "
          f"désormais tous les statuts ({n} ligne(s) antérieure(s) recopiée(s) — "
          f"elles ne comptaient que les dossiers actifs).")

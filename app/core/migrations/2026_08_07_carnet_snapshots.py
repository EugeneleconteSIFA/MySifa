"""
Photo quotidienne du carnet de commandes.

Prévoir la consommation matière à 3-4 mois ne consiste pas à extrapoler une
courbe : sur cet horizon, une bonne partie du besoin est déjà connue — les
dossiers au planning livrés dans la fenêtre. Ce qui reste à estimer, c'est le
REMPLISSAGE : combien un mois va encore gagner de dossiers d'ici sa
réalisation.

    prévision(M+k) = besoin_connu(M+k) ÷ p(k)

p(k) est la part du volume final déjà visible k mois à l'avance. Elle se
mesure — mais uniquement si l'on sait ce que le carnet contenait à une date
passée. Or `planning_entries` ne garde que le présent : au 7 août 2026, ses
295 dossiers avaient tous été créés dans les quatre mois précédents. Un
dossier terminé quitte la fenêtre, et avec lui la trace de ce qu'il pesait.

Le diagnostic (`scripts/diag_previsions_matieres.py`) est donc formel : p(k)
n'est pas calculable rétroactivement, et aucune requête ne changera cela. La
seule issue est de commencer à photographier le carnet, et d'attendre. Trois
mois d'instantanés suffisent à calibrer M+1 à M+3.

Cette table est donc inutile aujourd'hui et le restera jusqu'à l'automne.
C'est exactement pourquoi elle doit exister maintenant : chaque jour sans
photo est un point de calibration définitivement perdu.

Granularité : une ligne par (jour, mois de livraison visé, matière, nature du
besoin). On stocke le besoin CALCULÉ, pas les dossiers — c'est la grandeur
qu'on cherchera à prédire, et elle survit à la suppression d'un dossier.
"""

NOM = "carnet_snapshots"


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS carnet_snapshots (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            -- Jour de la photo, 'AAAA-MM-JJ'.
            snapshot_le     TEXT    NOT NULL,
            -- Mois de livraison visé, 'AAAA-MM'. C'est l'axe des prévisions.
            mois_livraison  TEXT    NOT NULL,
            -- Matière de MyStock. NULL = besoin non rattaché à une référence :
            -- on le garde quand même, sinon la somme des lignes ne fait plus
            -- le total du carnet et l'écart passe pour de la prévision.
            matiere_id      INTEGER,
            -- support / glassine / adhesif / mandrin / carton / palette.
            kind            TEXT    NOT NULL,
            unite           TEXT,
            quantite        REAL    NOT NULL DEFAULT 0,
            nb_dossiers     INTEGER NOT NULL DEFAULT 0,
            -- Dossiers dont le besoin n'a pas pu être chiffré ce jour-là
            -- (métrage absent, fiche non rapprochée). Sans ce compteur, un
            -- carnet mal renseigné se lit comme un carnet vide.
            nb_incalculables INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    # Une seule ligne par jour et par combinaison : la capture est rejouable
    # dans la journée sans dupliquer. COALESCE sur matiere_id car NULL n'est
    # jamais égal à NULL dans un index unique SQLite.
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_carnet_snap_unique "
        "ON carnet_snapshots(snapshot_le, mois_livraison, COALESCE(matiere_id, -1), kind)"
    )
    # Lecture type de la calibration : toute l'histoire d'un mois de livraison.
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_carnet_snap_mois "
        "ON carnet_snapshots(mois_livraison, snapshot_le)"
    )
    conn.commit()
    print("[MySifa] migration carnet_snapshots : le carnet de commandes est "
          "désormais photographié chaque jour (calibration exploitable sous 3 mois).")

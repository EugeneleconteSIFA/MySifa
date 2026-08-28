"""
Retrait de la reprise de navigation du portail.

La barre « Reprendre où j'en étais » a été livrée puis abandonnée le même jour :
le rendu ne convainquait pas. La table qu'elle alimentait n'a donc jamais servi
à autre chose, et on la retire plutôt que de la laisser grossir en silence.

La colonne `users.portal_apps_favoris`, créée par la même migration d'origine,
reste : les favoris de tuiles, eux, sont bien en service.
"""

NOM = "portail_recents_retire"
DEPEND = ["portail_volets_favoris_recents"]


def appliquer(conn):
    conn.executescript(
        """
        DROP INDEX IF EXISTS ix_portail_recents_user_cle;
        DROP INDEX IF EXISTS ix_portail_recents_user_date;
        DROP TABLE IF EXISTS portail_recents;
        """
    )
    conn.commit()

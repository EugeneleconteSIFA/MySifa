"""
Réglage des boutons flottants par application (messagerie, post-it, assistant
IA, calculette, capture, tâche rapide…), tenu par le superadmin dans
Paramètres › Audit › Widgets et tableaux de bord.

Une ligne = un couple (application, bouton) réglé à la main. Sans ligne, le
défaut du code s'applique (app/services/boutons_flottants.py : tout activé,
sauf la bulle de messagerie sur la page Messagerie). Aucun seed : la table
vide reproduit exactement le défaut.
"""

NOM = "boutons_flottants_reglages"


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS boutons_flottants_reglages (
               appli      TEXT NOT NULL,
               bouton     TEXT NOT NULL,
               actif      INTEGER NOT NULL DEFAULT 1,
               updated_at TEXT,
               updated_by TEXT,
               PRIMARY KEY (appli, bouton)
           )"""
    )
    conn.commit()

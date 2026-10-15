"""
Mémorise les rattachements devis ↔ planning refusés à l'écran.

Le moteur tourne désormais tout seul (ouverture de l'onglet Rentabilité,
arrivée d'un devis). Sans mémoire des refus, « Rejeter » ne servait à rien :
la proposition revenait au passage suivant, identique. Une ligne ici dit
« ce devis n'est pas celui de ce dossier » ; le moteur cherche alors le
suivant, et ne repropose jamais ce couple.
"""

NOM = "rent_rejets_rattachement"
DEPEND = ["rent_liens_origine_validation"]


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rent_rejets (
             planning_entry_id INTEGER NOT NULL,
             devis_id          INTEGER NOT NULL,
             rejete_par        TEXT,
             rejete_at         TEXT,
             PRIMARY KEY (planning_entry_id, devis_id)
           )"""
    )
    conn.commit()

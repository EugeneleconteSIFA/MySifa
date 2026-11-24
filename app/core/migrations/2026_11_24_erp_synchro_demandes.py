"""
ERP : demandes de mise à jour du miroir RVGI, faites depuis MySifa.

Le VPS ne voit pas le réseau SIFA : c'est un poste du réseau qui exporte RVGI
et POUSSE le miroir (scripts/sync_rvgi.ps1). Un bouton « Mettre à jour
maintenant » ne peut donc pas aller chercher les données ; il dépose une
demande ici, que le poste relève toutes les deux minutes
(POST /api/bridge/erp/demande/prendre) avant de lancer une synchro complète.
La fin de l'import du miroir clôt la demande.

statut : en_attente → prise → terminee | echec
"""

NOM = "erp_synchro_demandes"


def appliquer(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS erp_synchro_demandes (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            demande_le   TEXT NOT NULL,
            demande_par  TEXT,
            statut       TEXT NOT NULL DEFAULT 'en_attente',
            prise_le     TEXT,
            fin_le       TEXT,
            message      TEXT
        )
    """)
    conn.commit()

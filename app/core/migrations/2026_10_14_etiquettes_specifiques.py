"""
MyPrint — étiquettes spécifiques (éditeur façon BarTender / CodeSoft).

  etiq_dossiers         classement libre, en pratique un dossier par client
  etiq_modeles          une étiquette : format (mm, dpi) + mise en page JSON
                        (éléments placés et variables). Le ZPL n'est jamais
                        stocké comme source : il se régénère depuis le JSON,
                        ce qui permet d'éditer à la main ou par l'IA la même
                        description.
  etiq_compteurs        dernier numéro émis par compteur. Un SSCC ne doit
                        jamais sortir deux fois : la clé d'un compteur SSCC est
                        l'extension + le préfixe GS1, partagée par toutes les
                        étiquettes qui l'utilisent.
  etiq_impressions      historique : copie de la mise en page, plages émises,
                        ZPL envoyé. Sert à la réimpression à l'identique.
  etiq_demandes         « demander un nouveau format », traité par le super
  etiq_demande_pieces   admin ; pièces jointes (photo, PDF, cahier des charges).
"""

NOM = "etiquettes_specifiques"


def appliquer(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS etiq_dossiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        description TEXT,
        archive INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        created_by TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS etiq_modeles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dossier_id INTEGER NOT NULL REFERENCES etiq_dossiers(id),
        nom TEXT NOT NULL,
        description TEXT,
        largeur_mm REAL NOT NULL DEFAULT 100,
        hauteur_mm REAL NOT NULL DEFAULT 150,
        dpi INTEGER NOT NULL DEFAULT 203,
        layout_json TEXT NOT NULL DEFAULT '{}',
        duplique_de INTEGER,
        demande_id INTEGER,
        archive INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        created_by TEXT,
        updated_at TEXT,
        updated_by TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_etiq_modeles_dossier ON etiq_modeles(dossier_id, archive)")
    conn.execute("""CREATE TABLE IF NOT EXISTS etiq_compteurs (
        cle TEXT PRIMARY KEY,
        dernier INTEGER NOT NULL,
        updated_at TEXT NOT NULL,
        updated_by TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS etiq_impressions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        modele_id INTEGER NOT NULL REFERENCES etiq_modeles(id),
        imprimante_id INTEGER,
        quantite INTEGER NOT NULL,
        exemplaires INTEGER NOT NULL DEFAULT 1,
        valeurs_json TEXT,
        plages_json TEXT,
        layout_json TEXT NOT NULL,
        zpl TEXT NOT NULL,
        job_id INTEGER,
        reimpression_de INTEGER,
        created_at TEXT NOT NULL,
        created_by TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_etiq_impressions_modele ON etiq_impressions(modele_id, created_at DESC)")
    conn.execute("""CREATE TABLE IF NOT EXISTS etiq_demandes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dossier_id INTEGER,
        client TEXT,
        titre TEXT NOT NULL,
        description TEXT NOT NULL,
        largeur_mm REAL,
        hauteur_mm REAL,
        statut TEXT NOT NULL DEFAULT 'nouvelle',
        modele_id INTEGER,
        reponse TEXT,
        created_at TEXT NOT NULL,
        created_by TEXT,
        traite_at TEXT,
        traite_par TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_etiq_demandes_statut ON etiq_demandes(statut, created_at DESC)")
    conn.execute("""CREATE TABLE IF NOT EXISTS etiq_demande_pieces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        demande_id INTEGER NOT NULL REFERENCES etiq_demandes(id) ON DELETE CASCADE,
        filename TEXT NOT NULL,
        original_name TEXT NOT NULL,
        mime_type TEXT,
        taille INTEGER,
        created_at TEXT NOT NULL
    )""")
    conn.commit()

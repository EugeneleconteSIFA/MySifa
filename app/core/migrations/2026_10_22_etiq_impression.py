"""
MyTools › Étiquettes — chaîne d'impression (profils d'imprimante, journal).

Profils : la table `imprimantes` (Paramètres › Imprimantes) reste l'unique
référentiel des imprimantes. Elle reçoit les réglages d'impression qui lui
manquaient pour piloter une étiquette au point près :

  decalage_x_mm, decalage_y_mm   décalage de toute l'étiquette (mm, ±)
  vitesse                        pouces par seconde (NULL = réglage de l'imprimante)
  contraste                      ZPL 0-30, EPL / TSPL 0-15 (NULL = réglage de l'imprimante)
  ecart_mm                       intervalle entre deux étiquettes (EPL, TSPL)
  mode_envoi                     auto | reseau | agent | navigateur | fichier | pdf
  rfid                           1 = module RFID : l'EPC est encodé avec l'étiquette (ZPL)

Journal : `etiq_journal_impression`, une ligne par impression lancée depuis
MyTools (modèle vectoriel, rendu d'un poste traça ou réimpression) : qui,
quand, quel modèle, combien, sur quelle imprimante, les données imprimées
(pour réimprimer la même série) et la vérification par scan du code imprimé
(avec la note ISO A à F quand un vérificateur est branché).

Règles d'impression automatique : `etiq_regles_auto`, par machine (id en
base) et par code d'opération saisi (fin de production 89, ou tout autre code
de operations.json) : modèle approuvé, imprimante, nombre d'exemplaires.

Parc : `etiq_parc_etat`, dernier état relevé de chaque imprimante réseau
(~HS, ~HQES, compteur), pour la vue d'ensemble.
"""

NOM = "etiq_impression_profils_journal"


def _colonnes(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn):
    cols = _colonnes(conn, "imprimantes")
    if cols:
        ajouts = [
            ("decalage_x_mm", "REAL NOT NULL DEFAULT 0"),
            ("decalage_y_mm", "REAL NOT NULL DEFAULT 0"),
            ("vitesse", "INTEGER"),
            ("contraste", "INTEGER"),
            ("ecart_mm", "REAL NOT NULL DEFAULT 2"),
            ("mode_envoi", "TEXT NOT NULL DEFAULT 'auto'"),
            ("rfid", "INTEGER NOT NULL DEFAULT 0"),
        ]
        for nom, decl in ajouts:
            if nom not in cols:
                conn.execute(f"ALTER TABLE imprimantes ADD COLUMN {nom} {decl}")

    conn.execute("""CREATE TABLE IF NOT EXISTS etiq_journal_impression (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT NOT NULL,
        created_by TEXT,
        created_by_nom TEXT,
        source TEXT NOT NULL DEFAULT 'modele',
        modele_id INTEGER,
        modele_nom TEXT,
        imprimante_id INTEGER,
        imprimante_nom TEXT,
        langage TEXT,
        mode_envoi TEXT,
        etiquettes INTEGER NOT NULL DEFAULT 1,
        exemplaires INTEGER NOT NULL DEFAULT 1,
        resume TEXT,
        donnees_json TEXT,
        modele_json TEXT,
        contenu BLOB,
        attendu_json TEXT,
        statut TEXT NOT NULL DEFAULT 'prepare',
        erreur TEXT,
        job_id INTEGER,
        reimpression_de INTEGER,
        verif_statut TEXT,
        verif_lu TEXT,
        verif_detail TEXT,
        verif_at TEXT,
        verif_par TEXT,
        verif_note TEXT,
        origine TEXT
    )""")
    cols_j = _colonnes(conn, "etiq_journal_impression")
    for nom in ("verif_note", "origine"):
        if nom not in cols_j:
            conn.execute(f"ALTER TABLE etiq_journal_impression ADD COLUMN {nom} TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_etiq_journal_date ON etiq_journal_impression(created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_etiq_journal_modele ON etiq_journal_impression(modele_id, created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_etiq_journal_imprimante ON etiq_journal_impression(imprimante_id, created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_etiq_journal_source ON etiq_journal_impression(source, statut)")

    conn.execute("""CREATE TABLE IF NOT EXISTS etiq_regles_auto (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        machine_id INTEGER NOT NULL,
        operation_code TEXT NOT NULL DEFAULT '89',
        modele_id INTEGER NOT NULL,
        imprimante_id INTEGER NOT NULL,
        exemplaires INTEGER NOT NULL DEFAULT 1,
        fin_dossier_seulement INTEGER NOT NULL DEFAULT 0,
        actif INTEGER NOT NULL DEFAULT 1,
        note TEXT,
        created_at TEXT NOT NULL,
        created_by TEXT,
        updated_at TEXT,
        updated_by TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_etiq_regles_machine ON etiq_regles_auto(machine_id, operation_code, actif)")

    conn.execute("""CREATE TABLE IF NOT EXISTS etiq_parc_etat (
        imprimante_id INTEGER PRIMARY KEY,
        vu_le TEXT NOT NULL,
        en_ligne INTEGER NOT NULL DEFAULT 0,
        etat_json TEXT
    )""")
    conn.commit()

"""
Étiquettes spécifiques — bibliothèque et versions (niveau BarTender).

  etiq_modeles.usage      catégorie d'usage (bobine, palette, carton,
                          échantillon, expédition — ETIQ_USAGES de config.py)
  etiq_modeles.client     client de l'étiquette (texte libre ou raison sociale
                          de la table clients), en plus du dossier
  etiq_modeles.version    numéro de la version enregistrée, +1 à chaque
                          enregistrement qui change la mise en page ou le format
  etiq_modeles_versions   copie de chaque version remplacée : on peut revoir
                          l'historique et revenir à une version antérieure

Les compteurs restent dans etiq_compteurs (dernier numéro par modèle et par
variable) : rien à ajouter pour la reprise au dernier numéro.
"""

NOM = "etiq_bibliotheque_versions"
DEPEND = ["etiquettes_specifiques"]


def _colonnes(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn):
    cols = _colonnes(conn, "etiq_modeles")
    if "usage" not in cols:
        conn.execute("ALTER TABLE etiq_modeles ADD COLUMN usage TEXT NOT NULL DEFAULT ''")
    if "client" not in cols:
        conn.execute("ALTER TABLE etiq_modeles ADD COLUMN client TEXT NOT NULL DEFAULT ''")
    if "version" not in cols:
        conn.execute("ALTER TABLE etiq_modeles ADD COLUMN version INTEGER NOT NULL DEFAULT 1")
    conn.execute("""CREATE TABLE IF NOT EXISTS etiq_modeles_versions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        modele_id INTEGER NOT NULL REFERENCES etiq_modeles(id),
        version INTEGER NOT NULL,
        nom TEXT,
        largeur_mm REAL NOT NULL,
        hauteur_mm REAL NOT NULL,
        dpi INTEGER NOT NULL,
        layout_json TEXT NOT NULL,
        motif TEXT,
        created_at TEXT NOT NULL,
        created_by TEXT,
        UNIQUE(modele_id, version)
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_etiq_versions_modele ON etiq_modeles_versions(modele_id, version DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_etiq_modeles_usage ON etiq_modeles(usage, archive)")
    conn.commit()

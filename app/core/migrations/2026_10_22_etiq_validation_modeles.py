"""
Étiquettes spécifiques — validation des modèles avant production.

Un modèle modifié doit être approuvé (rôles qualité) avant que la modification
parte à l'impression ; d'ici là, la production imprime la dernière version
approuvée.

  etiq_modeles.statut_validation   brouillon | a_approuver | approuve
  etiq_modeles.version_approuvee   numéro de version imprimé en production
  etiq_modeles.approuve_par / _le  dernière approbation
  etiq_approbations                historique : demande, approbation, refus

Reprise : les étiquettes déjà en service sont approuvées dans leur version
actuelle — sans quoi plus aucune ne s'imprimerait au déploiement.
"""

NOM = "etiq_validation_modeles"
DEPEND = ["etiq_bibliotheque_versions"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(etiq_modeles)").fetchall()}
    neuf = "statut_validation" not in cols
    for col, ddl in (("statut_validation", "TEXT NOT NULL DEFAULT 'brouillon'"),
                     ("version_approuvee", "INTEGER"),
                     ("approuve_par", "TEXT"),
                     ("approuve_le", "TEXT")):
        if col not in cols:
            conn.execute(f"ALTER TABLE etiq_modeles ADD COLUMN {col} {ddl}")
    conn.execute("""CREATE TABLE IF NOT EXISTS etiq_approbations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        modele_id INTEGER NOT NULL REFERENCES etiq_modeles(id),
        version INTEGER NOT NULL,
        action TEXT NOT NULL,
        commentaire TEXT,
        par TEXT,
        le TEXT NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_etiq_approbations_modele ON etiq_approbations(modele_id, le DESC)")
    n = 0
    if neuf:
        n = conn.execute(
            "UPDATE etiq_modeles SET statut_validation='approuve', version_approuvee=COALESCE(version,1),"
            " approuve_par='reprise', approuve_le=COALESCE(updated_at, created_at) WHERE archive=0").rowcount
        conn.execute(
            "INSERT INTO etiq_approbations (modele_id,version,action,commentaire,par,le)"
            " SELECT id, COALESCE(version,1), 'approuve', 'Étiquette en service avant la validation des modèles',"
            " 'reprise', COALESCE(updated_at, created_at) FROM etiq_modeles WHERE archive=0")
    conn.commit()
    if n:
        print(f"[MySifa] migration {NOM} : {n} étiquette(s) en service approuvée(s) dans leur version actuelle.")

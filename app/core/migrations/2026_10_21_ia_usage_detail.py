"""
Usage IA plus précis : d'où vient chaque appel, et son détail technique.

Paramètres › Usage IA ne disait que la fonction (« Assistant IA », « Alertes
maintenance ») : impossible de savoir depuis quel écran, avec quel modèle
demandé, combien de fichiers joints, ni pourquoi un appel a échoué.

  application     appli de la page d'origine (MyTools, MyQualité…), ou
                  « Automatique » pour une tâche de fond
  ecran           écran de cette appli (Étiquettes › Spécifiques…)
  page            adresse de la page d'origine (chemin + paramètres)
  api             route appelée (/api/print/specifiques/ia/depuis-photo)
  modele_demande  modèle choisi ; `modele` reste celui qui a répondu
                  (différent quand le repli serveur a joué)
  nb_fichiers     pièces jointes envoyées au modèle
  fin_raison      stop_reason du dernier appel (end_turn, max_tokens, refusal…)
  erreur          message de l'échec, tronqué
"""

NOM = "ia_usage_detail"
DEPEND = ["ia_usage"]

_COLONNES = (
    ("application", "TEXT"),
    ("ecran", "TEXT"),
    ("page", "TEXT"),
    ("api", "TEXT"),
    ("modele_demande", "TEXT"),
    ("nb_fichiers", "INTEGER NOT NULL DEFAULT 0"),
    ("fin_raison", "TEXT"),
    ("erreur", "TEXT"),
)


def appliquer(conn):
    existantes = {r[1] for r in conn.execute("PRAGMA table_info(ia_usage)").fetchall()}
    for nom, type_sql in _COLONNES:
        if nom not in existantes:
            conn.execute(f"ALTER TABLE ia_usage ADD COLUMN {nom} {type_sql}")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ia_usage_application ON ia_usage(application, cree_le)")
    conn.commit()

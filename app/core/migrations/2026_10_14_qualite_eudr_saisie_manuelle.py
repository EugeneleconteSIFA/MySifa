"""
MyQualité — questionnaire EUDR : réponse saisie à la main.

Certains fournisseurs répondent par courrier plutôt que par le formulaire
(Avery, 13/10/2026). La qualité enregistre alors la réponse elle-même :
rôle, périmètre, transmission, commentaire et pièce jointe (le courrier).

  source          'portail' (le fournisseur) ou 'manuel' (MyQualité)
  saisi_par       email de l'utilisateur qui a saisi, pour 'manuel'
  piece_*         pièce jointe : nom sur disque, nom d'origine, type MIME

Une saisie manuelle se rattache à une demande inactive créée pour elle :
`eudr_reponses.demande_id` reste renseigné, aucun lien n'est émis.
"""

NOM = "qualite_eudr_saisie_manuelle"
DEPEND = ["qualite_eudr_questionnaire"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(eudr_reponses)").fetchall()}
    if "source" not in cols:
        conn.execute("ALTER TABLE eudr_reponses ADD COLUMN source TEXT NOT NULL DEFAULT 'portail'")
    for col in ("saisi_par", "piece_filename", "piece_original", "piece_mime"):
        if col not in cols:
            conn.execute(f"ALTER TABLE eudr_reponses ADD COLUMN {col} TEXT")
    conn.commit()

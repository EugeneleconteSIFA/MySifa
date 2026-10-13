"""
MyQualité — questionnaire EUDR : société et téléphone du répondant.

La page d'accueil du questionnaire demande la raison sociale de l'entreprise
qui répond et les coordonnées complètes de la personne : la fiche fournisseur
MySifa ne suffit pas (filiale, groupe, distributeur qui répond pour l'usine).
"""

NOM = "qualite_eudr_repondant"
DEPEND = ["qualite_eudr_questionnaire"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(eudr_reponses)").fetchall()}
    for col in ("repondant_societe", "repondant_tel"):
        if col not in cols:
            conn.execute(f"ALTER TABLE eudr_reponses ADD COLUMN {col} TEXT")
    conn.commit()

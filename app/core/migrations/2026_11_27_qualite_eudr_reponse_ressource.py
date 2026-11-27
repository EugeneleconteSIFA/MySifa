"""
MyQualité — questionnaire EUDR : chaque réponse devient un document fournisseur.

Une réponse reçue par le formulaire (lien personnel ou lien commun rattaché)
est mise en PDF et déposée dans Ressources fournisseurs, sur la fiche du
fournisseur qui a répondu, liée à la fiche EUDR du référentiel RSE.

  certificat_id   document créé dans `qualite_fournisseur_certificats` ;
                  NULL tant que la réponse n'a pas été classée. Une saisie
                  manuelle n'en a jamais : son courrier est déjà la pièce.

Les réponses antérieures ne sont pas converties ici : elles se classent depuis
l'onglet EUDR (bouton « Classer les réponses »), qui génère les PDF.
"""

NOM = "qualite_eudr_reponse_ressource"
DEPEND = ["qualite_eudr_saisie_manuelle"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(eudr_reponses)").fetchall()}
    if "certificat_id" not in cols:
        conn.execute("ALTER TABLE eudr_reponses ADD COLUMN certificat_id INTEGER")
    conn.commit()

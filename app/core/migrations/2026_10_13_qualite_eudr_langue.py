"""
MyQualité — questionnaire EUDR : langue de la demande.

Le questionnaire part en anglais, en français ou en espagnol. La langue est
choisie à l'envoi (préremplie depuis le contact du fournisseur), sert à
l'email et au formulaire, et se met à jour quand le fournisseur change de
langue sur la page : la relance suivante part dans la langue qu'il a choisie.
"""

NOM = "qualite_eudr_langue"
DEPEND = ["qualite_eudr_questionnaire"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(eudr_demandes)").fetchall()}
    if "langue" not in cols:
        conn.execute("ALTER TABLE eudr_demandes ADD COLUMN langue TEXT NOT NULL DEFAULT 'en'")
    conn.commit()

"""
Date d'arrivée des employés suivis dans l'Outil RH (MyCompta).

L'Outil RH sert au suivi des nouveaux employés : la date d'arrivée est saisie
à la création du compte depuis l'onglet, modifiable ensuite. Format
AAAA-MM-JJ. Vide pour les employés ajoutés avant cette colonne.
"""

NOM = "rh_outil_date_arrivee"
DEPEND = ["rh_outil_membres"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(rh_outil_membres)").fetchall()}
    if "date_arrivee" not in cols:
        conn.execute("ALTER TABLE rh_outil_membres ADD COLUMN date_arrivee TEXT")
    conn.commit()

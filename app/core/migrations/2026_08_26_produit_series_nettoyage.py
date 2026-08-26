"""Poste « nettoyage » dans les series produit.

Le code 67 (vidange four colle) etait compte en calage par `timings.py`, les
codes 61 et 77 n'etaient comptes nulle part : la repartition par categorie
mentait dans les deux sens. Le nettoyage devient un poste a part entiere, il
lui faut sa colonne.

La colonne reste NULL sur les series deja materialisees : leur `temps_calage`
porte encore l'ancien decoupage. Un rattrapage `refaire=1` les reecrit avec la
nouvelle repartition — on ne le declenche pas ici, ce serait plusieurs minutes
de calcul au demarrage de l'application.
"""

NOM = "produit_series_temps_nettoyage"
DEPEND = ["produit_memoire_tables"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(produit_series)")}
    if not cols:
        return
    if "temps_nettoyage_min" not in cols:
        conn.execute("ALTER TABLE produit_series ADD COLUMN temps_nettoyage_min REAL")
        conn.commit()
        print("[MySifa] migration produit_series_temps_nettoyage : colonne ajoutee.")

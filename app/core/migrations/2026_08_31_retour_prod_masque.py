"""
Retour de prod : masquer une remontee hors sujet.

Toutes les remontees d'atelier ne parlent pas de la qualite de la production.
« 10h », « 5h25 », un mot laisse a l'equipe suivante : ce sont des saisies
legitimes, mais elles n'ont rien a faire dans une feuille qu'on lit pour savoir
ce qui a coince. Les valider serait mentir — elles n'ont pas ete traitees, il
n'y avait rien a traiter.

D'ou un etat distinct : masque. La remontee sort de la liste principale et reste
consultable derriere un bouton. Rien n'est efface : une remontee jugee hors
sujet un jour peut se reveler utile le lendemain.

Migration separee de `retour_prod_suivi` plutot qu'ajoutee dedans : une
migration deja passee en production ne rejoue pas, et son NOM ne doit jamais
changer.
"""

NOM = "retour_prod_masque"
DEPEND = ["retour_prod_suivi"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(retour_prod_ecrits)").fetchall()}
    if "masque" not in cols:
        conn.execute("ALTER TABLE retour_prod_ecrits ADD COLUMN masque INTEGER NOT NULL DEFAULT 0")
        conn.execute("ALTER TABLE retour_prod_ecrits ADD COLUMN masque_par TEXT")
        conn.execute("ALTER TABLE retour_prod_ecrits ADD COLUMN masque_le TEXT")
        print("[MySifa] migration retour_prod_masque : colonnes de masquage ajoutees.")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_retour_prod_ecrits_masque "
        "ON retour_prod_ecrits(masque)"
    )
    conn.commit()

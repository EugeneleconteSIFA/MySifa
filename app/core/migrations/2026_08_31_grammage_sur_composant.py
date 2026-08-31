"""
Le grammage passe de la matière au composant du produit.

Jusqu'ici, le poids au m² qui convertit un prix au kilo en coût au m² vivait sur
la DÉCLINAISON de matière (`mp_matiere_declinaison.grammage_gsm` / `perte_pct`).
C'était une confusion : un adhésif ne s'achète pas plus cher en 22 g/m² qu'en
17 — le prix est au kilo, point. Ce qui change d'un produit à l'autre, c'est la
QUANTITÉ posée, et cette quantité appartient au produit, pas à la matière.

La matière porte donc désormais ce qu'on paie ; le composant du produit porte ce
qu'on consomme.

Cette migration ne change AUCUN coût le jour où elle passe : chaque composant
hérite du grammage et de la perte de la déclinaison qu'il pointe. Les chiffres
sont identiques, ils ont juste changé de propriétaire — c'est ce qui permet de
déployer sans recalculer un catalogue entier à la main.

Les colonnes côté déclinaison sont LAISSÉES EN PLACE : elles identifient encore
le grammage d'une déclinaison d'adhésif, et les supprimer ici rendrait le retour
en arrière impossible. Elles cesseront simplement d'entrer dans le calcul.
"""

NOM = "mp_grammage_sur_composant"
DEPEND = ["mp_produits_mystock"]


def _colonnes(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def appliquer(conn):
    cols = _colonnes(conn, "mp_produit_composant")

    if "grammage_gsm" not in cols:
        conn.execute("ALTER TABLE mp_produit_composant ADD COLUMN grammage_gsm REAL")
    if "perte_pct" not in cols:
        conn.execute("ALTER TABLE mp_produit_composant ADD COLUMN perte_pct REAL")

    # Reprise : chaque composant hérite de ce que portait sa déclinaison. On ne
    # touche qu'aux composants encore vides, pour que la migration puisse être
    # rejouée sans écraser une saisie faite entre-temps.
    n = conn.execute(
        """UPDATE mp_produit_composant
              SET grammage_gsm = (
                    SELECT d.grammage_gsm FROM mp_matiere_declinaison d
                     WHERE d.id = mp_produit_composant.declinaison_id),
                  perte_pct = (
                    SELECT d.perte_pct FROM mp_matiere_declinaison d
                     WHERE d.id = mp_produit_composant.declinaison_id)
            WHERE grammage_gsm IS NULL AND perte_pct IS NULL
              AND EXISTS (
                    SELECT 1 FROM mp_matiere_declinaison d
                     WHERE d.id = mp_produit_composant.declinaison_id
                       AND (d.grammage_gsm IS NOT NULL OR d.perte_pct IS NOT NULL))"""
    ).rowcount
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} composant(s) ont repris le grammage de leur matiere.")

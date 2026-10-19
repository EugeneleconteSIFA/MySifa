"""
MyProd › Erreurs & Qualité : quelles catégories d'écart comptent dans « À traiter ».

Certaines catégories (quantité produite loin de l'OF, par exemple) sont
utiles à consulter mais ne demandent pas toujours d'action : elles gonflaient
la pastille jusqu'à la rendre muette. Le réglage dit, catégorie par
catégorie, si ses écarts entrent dans le compteur (pastilles de l'onglet, de
la tuile MyProd, notification). Une catégorie absente de la table compte : le
défaut reste « tout compte », et une règle ajoutée demain comptera sans rien
faire.
"""

NOM = "prod_ecarts_comptage"
DEPEND = ["prod_ecarts"]


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS prod_ecarts_reglages (
               regle      TEXT PRIMARY KEY,
               compte     INTEGER NOT NULL DEFAULT 1,
               updated_at TEXT,
               updated_by TEXT
           )"""
    )
    conn.commit()
    print(f"[MySifa] migration {NOM} : table prod_ecarts_reglages prête.")

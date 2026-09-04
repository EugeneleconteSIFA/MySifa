"""
Gel H-48 des dossiers dont le camion est deja reserve.

La contrainte transport du 02/09/2026 refuse un geste qui ferait rater un
enlevement. Elle laisse passer tout le reste : tant que le camion est
theoriquement tenable, un dossier peut glisser autant de fois qu'on veut, et
personne n'a jamais eu a signer ce glissement. C'est ce vide qui permettait au
commerce d'annoncer des delais que la production rattrapait en repoussant les
dossiers du voisin.

Le gel ferme ce vide sans rien interdire : passe l'entree dans la fenetre
(`gel_heures` avant l'heure limite du camion), tout geste qui repousse la fin
de production d'un dossier concerne demande une confirmation ecrite, motif a
l'appui, journalisee.

Deux parametres, dans la table cle/valeur deja creee par
`transport_planning_params` : l'interrupteur et la largeur de la fenetre.
L'heure limite (11 h) et le rattachement aux departs sont ceux de la regle
transport — le gel ne definit pas ses propres horaires.
"""

NOM = "gel_transport_params"
DEPEND = ["transport_planning_params"]

SEED_PARAMS = [
    # Interrupteur du gel seul. A 0, le planning se comporte comme avant le
    # 04/09/2026 : la contrainte transport reste, la confirmation disparait.
    ("gel_actif", "1"),
    # Largeur de la fenetre de gel, en heures avant l'heure limite du camion.
    # 48 h = la regle demandee par SIFA (H-48 de la livraison 11 h).
    ("gel_heures", "48"),
]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS transport_planning_params (
            cle    TEXT PRIMARY KEY NOT NULL,
            valeur TEXT NOT NULL
        );
        """
    )
    for cle, valeur in SEED_PARAMS:
        conn.execute(
            "INSERT OR IGNORE INTO transport_planning_params (cle, valeur) VALUES (?,?)",
            (cle, valeur),
        )
    conn.commit()
    n = conn.execute(
        "SELECT COUNT(*) FROM transport_planning_params WHERE cle IN ('gel_actif','gel_heures')"
    ).fetchone()[0]
    print(f"[MySifa] migration gel_transport : {n} parametre(s) de gel en place.")

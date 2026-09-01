"""
Postes qui ne sont pas des machines de production.

Un point de production compte un metrage, une cadence, des arrets. Le
repiquage n'a rien de tout ca : c'est un atelier, on y surimprime des
etiquettes deja fabriquees. Ses saisies ne portent ni code de debut ni code de
fin de dossier — ces codes y sont deja masques dans l'onglet Saisies — donc pas
de cycle, pas de compteur, pas de metrage. Sur la frise d'une reunion, son slot
s'etalait sur toute la periode en un seul bloc qui n'apprenait rien.

C'est une propriete du poste, pas une exception dans le code : la colonne se
coche dans Parametres -> Machines, exactement comme `sans_matiere_premiere`
posee par la migration `postes_sans_matiere_premiere`. Un autre atelier pourra
la porter demain sans qu'on touche au calcul, et le repiquage pourra la perdre
le jour ou il aura un vrai cycle.

Ce que la propriete fait : le poste est DECOCHE par defaut dans le perimetre
d'un point de production. Il n'est pas supprime — sa pastille reste dans le
selecteur, un clic le ramene. On ne cache pas une machine, on arrete de la
compter par defaut.

Le repiquage est coche d'office : c'est le cas connu au moment de la migration.
"""

NOM = "postes_hors_production"


def appliquer(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(machines)").fetchall()}
    if not cols:
        return  # table absente sur cette base (harnais de test) : rien a faire
    if "hors_production" not in cols:
        conn.execute(
            "ALTER TABLE machines ADD COLUMN hors_production INTEGER NOT NULL DEFAULT 0"
        )
    # LIKE plutot qu'egalite : le poste peut s'appeler « Repiquage 1 » ou
    # « Atelier repiquage » selon la saisie. Rien d'autre ne contient ce mot.
    cur = conn.execute(
        "UPDATE machines SET hors_production = 1 "
        "WHERE LOWER(COALESCE(nom, '')) LIKE '%repiquage%' "
        "  AND COALESCE(hors_production, 0) = 0"
    )
    conn.commit()
    print(f"[MySifa] migration postes_hors_production : "
          f"{cur.rowcount} poste(s) marque(s) hors production.")

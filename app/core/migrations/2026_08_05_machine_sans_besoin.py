"""
Postes du planning qui n'appellent pas de matière première.

Toutes les lignes du planning ne sont pas des machines de production. Le
repiquage est un atelier : on y surimprime des étiquettes déjà fabriquées. Le
dossier ne consomme donc ni frontal, ni glassine, ni adhésif — cette matière-là
a déjà été consommée en amont, la compter une seconde fois serait un doublon.

En revanche il consomme bien du conditionnement : les étiquettes repiquées sont
rembobinées sur des mandrins et emballées en cartons, puis palettisées. Ces
besoins-là restent calculés normalement.

C'est une propriété du poste, pas une exception dans le code : la colonne se
coche dans Paramètres → Machines, et un autre atelier pourra la porter demain
sans qu'on touche au calcul.

Le repiquage est coché d'office : c'est le cas connu au moment de la migration.
Un simple décochage le fait revenir dans le calcul complet.
"""

NOM = "postes_sans_matiere_premiere"


def appliquer(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(machines)").fetchall()}
    if not cols:
        return  # table absente sur cette base (harnais de test) : rien à faire
    if "sans_matiere_premiere" not in cols:
        conn.execute(
            "ALTER TABLE machines ADD COLUMN sans_matiere_premiere INTEGER NOT NULL DEFAULT 0"
        )
    # LIKE plutôt qu'égalité : le poste peut s'appeler « Repiquage 1 » ou
    # « Atelier repiquage » selon la saisie. Rien d'autre ne contient ce mot.
    cur = conn.execute(
        "UPDATE machines SET sans_matiere_premiere = 1 "
        "WHERE LOWER(COALESCE(nom, '')) LIKE '%repiquage%'"
    )
    conn.commit()
    print("[MySifa] migration postes_sans_matiere_premiere : colonne prête, "
          f"{cur.rowcount} poste(s) « repiquage » sans besoin frontal/glassine/adhésif.")

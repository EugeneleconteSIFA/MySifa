"""
Regroupement des types d'article RVGI en familles MySifa.

RVGI type chaque ligne d'achat dans `cdf_ligne.type` : 18 valeurs relevees sur
les receptions, dont les libelles se lisent dans `fic_para` (bloc
150000 + (type - 2) * 100). Ces 18 valeurs repondent a « quelle matiere »,
pas a « quelle nature d'achat » : pour savoir d'un coup d'oeil si une ligne
de reception est de la matiere, de la sous-traitance ou de l'outillage, il
faut les regrouper.

Le regroupement est une decision MySifa, pas une donnee de l'ERP : il vit
donc ici, en base, editable depuis Parametres. Un type absent de la table
n'a pas de famille et s'affiche sans — on ne devine pas a la place de
l'utilisateur, et la page le signale pour qu'il tranche.

Le decoupage seede est celui arrete avec Eugene le 02/09/2026 : les pieces
Cohesio et les cliches vont avec l'outil de decoupe, les encres avec les
consommables.
"""

NOM = "erp_type_famille"

# (code du type sur cdf_ligne, famille, libelle de secours)
#
# Le libelle de secours ne sert que si `fic_para` est absent du miroir. Les
# types 1 et 2 n'ont AUCUN bloc dans `fic_para` : ce ne sont pas des matieres.
# Verifie sur les donnees le 02/09/2026 — les 3 832 lignes de type 1 sont dans
# `fic_art` a 3 825, les 1 367 lignes de type 2 sont dans `out_dec` a 1 367.
SEED = [
    (1,  "sous_traitance", "Article (sous-traitance)"),
    (2,  "outillage",      "Outil de decoupe"),
    (3,  "matiere",        "Complexes"),
    (4,  "matiere",        "Glassines"),
    (5,  "matiere",        "Velins"),
    (6,  "matiere",        "Couches"),
    (7,  "matiere",        "Thermiques"),
    (8,  "matiere",        "Synthetiques"),
    (9,  "matiere",        "Adhesifs"),
    (10, "consommable",    "Encres"),
    (11, "outillage",      "Cliches"),
    (15, "consommable",    "Mandrins"),
    (16, "consommable",    "Emballage"),
    (17, "consommable",    "Divers"),
    (18, "consommable",    "Boites"),
    (19, "consommable",    "Cartons"),
    (20, "consommable",    "Palettes"),
    (21, "outillage",      "Pieces Cohesio"),
]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS erp_type_famille (
            type_code       INTEGER PRIMARY KEY NOT NULL,
            famille         TEXT NOT NULL,
            libelle_secours TEXT,
            updated_at      TEXT,
            updated_by_name TEXT
        );
        """
    )
    for code, famille, libelle in SEED:
        conn.execute(
            "INSERT OR IGNORE INTO erp_type_famille "
            "(type_code, famille, libelle_secours) VALUES (?,?,?)",
            (code, famille, libelle),
        )
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM erp_type_famille").fetchone()[0]
    print(f"[MySifa] migration erp_type_famille : {n} type(s) classe(s).")

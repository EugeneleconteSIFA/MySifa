"""
Trois réglages de matière revus : taxes en %, marge optionnelle, grammage + perte.

1. **Taxes** — le champ était un multiplicateur (1,065 = +6,5 %). Personne ne
   pense en multiplicateur : il devient un pourcentage (6,5). Conversion en
   place, `tax_incidence` reste en base mais n'est plus lu par le calcul.

2. **Marge** — une matière peut désormais être exclue de l'assiette de marge :
   elle compte dans le prix de revient, mais on ne marge pas dessus. Coché par
   défaut, comme avant.

3. **Grammage et perte** — on saisit un grammage en g/m² et une perte en %, plus
   un poids en kg/m². Le poids reste calculé et rangé dans `weight_per_m2`, que
   le moteur lit déjà.

Reprise : la perte des matières existantes est mise à **0**, pas à 9 %. Le
grammage repris est celui qui donnait le poids actuel — appliquer 9 % de perte
d'un coup aurait renchéri toutes les matières de 9 % sans que personne ne l'ait
demandé. Les 9 % ne valent que pour les nouvelles matières.
"""

NOM = "mc_taxe_pct_marge_grammage"
DEPEND = ["mp_declinaison_parametrage_prix"]

_COLONNES = (
    # Taxes d'importation en % du sous-total d'achat.
    ("taxe_pct", "REAL NOT NULL DEFAULT 0"),
    # La matière entre-t-elle dans l'assiette de marge ?
    ("applique_marge", "INTEGER NOT NULL DEFAULT 1"),
    # Grammage saisi, en g/m².
    ("grammage_gsm", "REAL NOT NULL DEFAULT 0"),
    # Perte en %, appliquée au grammage pour obtenir le poids retenu.
    ("perte_pct", "REAL NOT NULL DEFAULT 9"),
)

_TABLES = ("mc_material", "mp_matiere_declinaison")


def appliquer(conn):
    for table in _TABLES:
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if not cols:
            continue  # table absente sur cette base : rien à faire
        for nom, ddl in _COLONNES:
            if nom not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {nom} {ddl}")

        # Multiplicateur -> pourcentage : 1,065 devient 6,5 ; 0,95 devient -5.
        if "tax_incidence" in cols:
            conn.execute(
                f"""UPDATE {table}
                       SET taxe_pct = ROUND((COALESCE(tax_incidence, 1) - 1) * 100, 4)"""
            )

        # Le grammage repris est celui qui redonne exactement le poids actuel,
        # avec une perte nulle : aucun prix ne bouge à la migration. On vérifie
        # les colonnes source — la reprise est un confort, elle ne doit pas
        # empêcher la migration de passer sur une base plus ancienne.
        if not {"weight_per_m2", "weight_gsm"} <= cols:
            continue
        conn.execute(
            f"""UPDATE {table} SET
                    grammage_gsm = CASE
                        WHEN COALESCE(weight_per_m2, 0) > 0 THEN ROUND(weight_per_m2 * 1000, 4)
                        ELSE COALESCE(weight_gsm, 0)
                    END,
                    perte_pct = 0"""
        )

    conn.commit()

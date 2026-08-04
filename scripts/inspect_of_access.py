"""
Inspection de la base Access des OF — diagnostic métrage / adhésif
------------------------------------------------------------------
Objectif : identifier quelles colonnes de [t_of] portent réellement le
métrage, la quantité au mille et les quantités d'adhésif, en comparant
les valeurs stockées à celles imprimées sur un OF connu.

Le script ne modifie RIEN : il ne fait que des SELECT.

Utilisation :
    pip install pyodbc
    python inspect_of_access.py                 # OF de référence 9931953
    python inspect_of_access.py 9932014         # un autre OF

Sortie : affichage console + fichier rapport_access_of.txt à côté du script.
"""

import sys
import pyodbc
from pathlib import Path

# ── Configuration ────────────────────────────────────────────────────
ACCESS_DB_PATH = r"\\IDEFIX\sifa_pub\Fiches techniques Access\of.mdb"
TABLE          = "t_of"
OF_DEFAUT      = "9931953"

CONN_STR = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    f"DBQ={ACCESS_DB_PATH};"
)

# Valeurs lues sur l'impression papier de l'OF 9931953.
# Elles servent à repérer automatiquement la colonne qui les porte.
VALEURS_IMPRIMEES = {
    "Quantité étiq. (théorique)": 201300,
    "Quantité bobines":           366.0,
    "Métrage":                    10226,
    "Quantité au mille":          50.8,
    "Laize":                      333,
    "Nb de levées":               122,
    "Cartons":                    21,
    "Mandrins":                   366,
    "Tubes":                      27,
    "Long. mandrin":              103,
    "Nb étiq. / bobine":          550,
}

sortie = []


def log(txt=""):
    print(txt)
    sortie.append(str(txt))


def sep(titre):
    log("")
    log("=" * 78)
    log(titre)
    log("=" * 78)


def main():
    numero = sys.argv[1] if len(sys.argv) > 1 else OF_DEFAUT

    log(f"Base   : {ACCESS_DB_PATH}")
    log(f"Table  : {TABLE}")
    log(f"OF ref : {numero}")

    conn = pyodbc.connect(CONN_STR)
    cur = conn.cursor()

    # ── 1. Toutes les tables de la base ──────────────────────────────
    sep("1. TABLES DE LA BASE")
    tables = [
        r.table_name for r in cur.tables(tableType="TABLE")
        if not r.table_name.startswith("MSys")
    ]
    for t in tables:
        try:
            n = cur.execute(f"SELECT COUNT(*) FROM [{t}]").fetchval()
        except Exception:
            n = "?"
        log(f"  {t:<40} {n} ligne(s)")

    vues = [r.table_name for r in cur.tables(tableType="VIEW")]
    if vues:
        log("")
        log("  Requêtes enregistrées (vues) :")
        for v in vues:
            log(f"    {v}")

    # ── 2. Colonnes de t_of ──────────────────────────────────────────
    sep(f"2. COLONNES DE [{TABLE}]")
    cols = list(cur.columns(table=TABLE))
    log(f"{len(cols)} colonne(s)")
    log("")
    log(f"  {'#':<4}{'NOM':<34}{'TYPE':<18}{'TAILLE':<9}NULL")
    log("  " + "-" * 72)
    noms = []
    for i, c in enumerate(cols, 1):
        noms.append(c.column_name)
        log(f"  {i:<4}{c.column_name:<34}{str(c.type_name):<18}"
            f"{str(c.column_size):<9}{'oui' if c.nullable else 'non'}")

    # ── 3. La ligne complète de l'OF de référence ────────────────────
    sep(f"3. CONTENU COMPLET DE L'OF {numero}")
    liste = ", ".join(f"[{n}]" for n in noms)
    cur.execute(f"SELECT {liste} FROM [{TABLE}] WHERE [numero_of] = ?", (numero,))
    row = cur.fetchone()

    if row is None:
        log(f"  Aucun OF {numero} trouvé (essayer sans zéro initial, ou en numérique).")
        cur.execute(f"SELECT TOP 5 [numero_of] FROM [{TABLE}] ORDER BY [id_of] DESC")
        log("  5 derniers numero_of en base : "
            + ", ".join(str(r[0]) for r in cur.fetchall()))
    else:
        valeurs = dict(zip(noms, row))
        for n in noms:
            v = valeurs[n]
            marque = "" if v not in (None, "", 0) else "        <-- vide"
            log(f"  {n:<34} = {repr(v)}{marque}")

        # ── 4. Rapprochement avec l'impression papier ────────────────
        sep("4. RAPPROCHEMENT AVEC L'IMPRESSION PAPIER")
        for libelle, attendu in VALEURS_IMPRIMEES.items():
            trouvees = []
            for n, v in valeurs.items():
                try:
                    if v is not None and abs(float(v) - float(attendu)) < 0.51:
                        trouvees.append(n)
                except (TypeError, ValueError):
                    continue
            if trouvees:
                log(f"  {libelle:<30} = {attendu:<10} -> {', '.join(trouvees)}")
            else:
                log(f"  {libelle:<30} = {attendu:<10} -> AUCUNE COLONNE "
                    f"(champ calculé dans l'état, ou stocké ailleurs)")

    # ── 5. Taux de remplissage des colonnes numériques ───────────────
    sep("5. TAUX DE REMPLISSAGE (500 derniers OF)")
    log("  Une colonne vide à 100 % n'est jamais saisie -> inutile de la lire.")
    log("")
    total = cur.execute(
        f"SELECT COUNT(*) FROM (SELECT TOP 500 [id_of] FROM [{TABLE}] "
        f"ORDER BY [id_of] DESC)").fetchval()
    for n in noms:
        try:
            rempli = cur.execute(
                f"SELECT COUNT(*) FROM (SELECT TOP 500 [{n}] FROM [{TABLE}] "
                f"ORDER BY [id_of] DESC) WHERE [{n}] IS NOT NULL "
                f"AND [{n}] <> 0"
            ).fetchval()
        except Exception:
            try:
                rempli = cur.execute(
                    f"SELECT COUNT(*) FROM (SELECT TOP 500 [{n}] FROM [{TABLE}] "
                    f"ORDER BY [id_of] DESC) WHERE [{n}] IS NOT NULL "
                    f"AND [{n}] <> ''"
                ).fetchval()
            except Exception:
                rempli = "?"
        if isinstance(rempli, int) and total:
            pct = round(100 * rempli / total)
            barre = "#" * (pct // 5)
            log(f"  {n:<34} {pct:>3} %  {barre}")
        else:
            log(f"  {n:<34}   ?")

    conn.close()

    chemin = Path(__file__).with_name("rapport_access_of.txt")
    chemin.write_text("\n".join(sortie), encoding="utf-8")
    log("")
    log(f"Rapport écrit dans : {chemin}")


if __name__ == "__main__":
    try:
        main()
    except pyodbc.Error as e:
        print("Erreur ODBC :", e)
        print("Si le pilote est introuvable : Python 64 bits exige un Access "
              "Database Engine 64 bits (et inversement).")

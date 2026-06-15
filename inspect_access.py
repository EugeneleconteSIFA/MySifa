"""Diag mapping Access ↔ MySifa pour les champs Étiquette / Module / Échenillage.

Liste les vraies colonnes de la table Access et lit les valeurs pour la fiche
1289/0009 (ou autre via argument). Utile pour confirmer si le mapping
etilaize/modlaize du script de sync est correct ou inversé.

Usage :
    python inspect_access.py
    python inspect_access.py 1289/0009

Dépend de : pip install pyodbc
"""
import sys
import pyodbc

ACCESS_DB_PATH = r"\\IDEFIX\sifa_pub\Fiches techniques Access\sifa_fiches_techniques.mdb"
CONN_STR = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    rf"DBQ={ACCESS_DB_PATH};"
)

REF_CIBLE = sys.argv[1] if len(sys.argv) > 1 else "1289/0009"


def main():
    print(f"Connexion à : {ACCESS_DB_PATH}")
    conn = pyodbc.connect(CONN_STR)
    cur = conn.cursor()

    # 1. Toutes les colonnes
    print("\n=== Colonnes de la table fiches_techniques ===")
    cols = []
    for row in cur.columns(table="fiches_techniques"):
        cols.append(row.column_name)
        print(f"  {row.column_name:30s}  ({row.type_name})")

    # 2. Cible : trouve les colonnes qui matchent les noms qu'on cherche
    print("\n=== Colonnes qui ressemblent à étiquette/module/échenillage ===")
    for c in cols:
        cl = c.lower()
        if any(k in cl for k in ("eti", "mod", "front", "rayon", "perf",
                                  "lai", "long", "later", "horiz")):
            print(f"  {c}")

    # 3. Valeurs pour la fiche cible
    print(f"\n=== Valeurs pour reference contenant '{REF_CIBLE}' ===")
    try:
        cur.execute(
            """SELECT [reference], [etilaize], [etilong], [etirayon], [etiperfo],
                      [modlaize], [modlong], [nbfront],
                      [lateral_ext], [horizontal], [lateral_int]
               FROM [fiches_techniques]
               WHERE [reference] LIKE ?""",
            (f"%{REF_CIBLE}%",),
        )
        rows = cur.fetchall()
        if not rows:
            print(f"  Aucune fiche trouvée avec ref contenant '{REF_CIBLE}'")
        for r in rows:
            print(f"\n  ref          : {r[0]}")
            print(f"  ÉTIQUETTE :")
            print(f"    etilaize   = {r[1]}")
            print(f"    etilong    = {r[2]}")
            print(f"    etirayon   = {r[3]}")
            print(f"    etiperfo   = {r[4]}")
            print(f"  MODULE :")
            print(f"    modlaize   = {r[5]}")
            print(f"    modlong    = {r[6]}")
            print(f"    nbfront    = {r[7]}")
            print(f"  ÉCHENILLAGE :")
            print(f"    lateral_ext = {r[8]}")
            print(f"    horizontal  = {r[9]}")
            print(f"    lateral_int = {r[10]}")
    except Exception as e:
        print(f"  Erreur SELECT : {e}")

    conn.close()


if __name__ == "__main__":
    main()

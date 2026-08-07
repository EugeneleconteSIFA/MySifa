#!/usr/bin/env python3
"""MySifa — état de confiance des OF et des fiches techniques.

À quoi ça répond
────────────────
Le déstockage de production ne part que de documents validés. Reste la
question qu'aucun écran ne pose : les chiffres validés sont-ils toujours ceux
qui ont servi — ou qui vont servir — au calcul ?

Le script lit, sans rien écrire :

  1. Combien de documents sont validés, et combien portent une protection
     champ par champ (valeurs saisies à la main, opposables à Access).
  2. Les validations tombées d'elles-mêmes parce qu'un chiffre a bougé : ce
     sont les documents à relire en priorité, ils bloquent un déstockage.
  3. Les changements postérieurs à une validation encore affichée comme
     acquise. En régime normal la liste est vide — le service dévalide. Une
     ligne ici signale un chemin d'écriture qui contourne
     app/services/documents_verite.py, donc un trou à boucher.
  4. Les dossiers DÉJÀ déstockés dont l'OF ou la fiche a changé depuis. Le
     stock a été mouvementé sur des valeurs qui ne sont plus celles affichées :
     c'est là qu'il faut aller regarder avant de suspecter un inventaire.

Sur les données antérieures au 7 août 2026, les points 3 et 4 ne peuvent rien
dire : le journal n'existait pas et les modifications d'Access ne laissaient
aucune trace. C'est une limite du passé, pas du script.

Usage
─────
    python scripts/audit_documents_validation.py
    python scripts/audit_documents_validation.py --db /chemin/production.db
    python scripts/audit_documents_validation.py --limite 50
"""
import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _defaut_db() -> str:
    try:
        from config import DB_PATH
        return DB_PATH
    except Exception:
        return os.path.join("data", "production.db")


def _table_existe(conn, nom) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nom,)
    ).fetchone() is not None


def _titre(txt):
    print("\n" + txt)
    print("─" * len(txt))


def compter(conn, table, libelle):
    tot = conn.execute(f"SELECT COUNT(*) c FROM {table}").fetchone()["c"]
    val = conn.execute(
        f"SELECT COUNT(*) c FROM {table} WHERE COALESCE(valide,0)=1").fetchone()["c"]
    prot = conn.execute(
        f"SELECT COUNT(*) c FROM {table} "
        f"WHERE champs_manuels IS NOT NULL AND TRIM(champs_manuels) NOT IN ('','[]')"
    ).fetchone()["c"]
    print(f"  {libelle:<20} {tot:>6} au total  |  {val:>6} validé(s)  "
          f"|  {prot:>6} avec des valeurs saisies à la main")


def validations_tombees(conn, table, cle, libelle, limite):
    rows = conn.execute(
        f"""SELECT id, {cle} AS ref, invalide_at, invalide_motif
            FROM {table}
            WHERE COALESCE(valide,0)=0 AND invalide_motif IS NOT NULL
            ORDER BY invalide_at DESC LIMIT ?""",
        (limite,),
    ).fetchall()
    if not rows:
        print(f"  {libelle} : aucune validation retirée automatiquement.")
        return 0
    print(f"  {libelle} — {len(rows)} à relire :")
    for r in rows:
        quand = (r["invalide_at"] or "")[:16].replace("T", " ")
        print(f"    · {r['ref'] or '?':<22} {quand}  {r['invalide_motif']}")
    return len(rows)


def changements_sous_validation(conn, table, cle, libelle, limite):
    """Un document TOUJOURS validé alors qu'une valeur a changé après coup.

    Ne doit jamais rien renvoyer : appliquer_maj dévalide. Une ligne ici est un
    chemin d'écriture qui court-circuite le service — à corriger, pas à relire.
    """
    rows = conn.execute(
        f"""SELECT d.id, d.{cle} AS ref, h.champ, h.avant, h.apres,
                   h.origine, h.at
            FROM {table} d
            JOIN documents_valeurs_historique h
              ON h.table_nom=? AND h.doc_id=d.id AND h.refuse=0
            WHERE COALESCE(d.valide,0)=1
              AND d.valide_at IS NOT NULL
              AND h.at > d.valide_at
            ORDER BY h.at DESC LIMIT ?""",
        (table, limite),
    ).fetchall()
    if not rows:
        print(f"  {libelle} : aucun — la dévalidation automatique fait son travail.")
        return 0
    print(f"  {libelle} — {len(rows)} ANOMALIE(S) : validé malgré un changement postérieur")
    for r in rows:
        print(f"    · {r['ref'] or '?':<22} {r['champ']} : {r['avant']} → {r['apres']} "
              f"({r['origine']}, {(r['at'] or '')[:16].replace('T', ' ')})")
    return len(rows)


def destockages_sur_chiffres_perimes(conn, limite):
    """Dossiers déstockés dont un document a bougé APRÈS le mouvement.

    Le mouvement porte désormais l'OF et la fiche qui l'ont calculé ; le
    journal porte les changements. Le croisement des deux dit si le stock a été
    mouvementé sur des valeurs qui ne sont plus affichées nulle part.
    """
    rows = conn.execute(
        """SELECT m.id AS mvt_id, m.no_dossier, m.created_at AS quand,
                  h.table_nom, h.champ, h.avant, h.apres, h.origine, h.at
           FROM mp_mouvements m
           JOIN documents_valeurs_historique h
             ON h.refuse = 0
            AND ((h.table_nom='of_imports'       AND h.doc_id = m.of_import_id)
              OR (h.table_nom='fiches_techniques' AND h.doc_id = m.fiche_id))
           WHERE m.planning_entry_id IS NOT NULL
             AND m.created_at IS NOT NULL
             AND h.at > m.created_at
           ORDER BY h.at DESC LIMIT ?""",
        (limite,),
    ).fetchall()
    if not rows:
        print("  Aucun. Les déstockages enregistrés reposent sur des documents "
              "inchangés depuis.")
        return 0
    print(f"  {len(rows)} mouvement(s) dont un document a changé depuis :")
    for r in rows:
        quoi = "OF" if r["table_nom"] == "of_imports" else "fiche"
        print(f"    · dossier {r['no_dossier'] or '?':<16} déstocké le "
              f"{(r['quand'] or '')[:16].replace('T', ' ')} — {quoi} {r['champ']} : "
              f"{r['avant']} → {r['apres']} ({r['origine']}, "
              f"{(r['at'] or '')[:16].replace('T', ' ')})")
    return len(rows)


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=_defaut_db(), help="chemin de la base SQLite")
    ap.add_argument("--limite", type=int, default=25,
                    help="nombre de lignes détaillées par section (défaut 25)")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"Base introuvable : {args.db}")
        return 2
    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    print(f"Base : {args.db}  (lecture seule)")

    cols = {r["name"] for r in conn.execute("PRAGMA table_info(of_imports)")}
    if "champs_manuels" not in cols:
        print("\nLa migration `documents_source_verite` n'est pas appliquée sur "
              "cette base — démarrer MySifa une fois, puis relancer ce script.")
        return 1

    _titre("1. Volumes")
    compter(conn, "of_imports", "Ordres de fabrication")
    compter(conn, "fiches_techniques", "Fiches techniques")

    _titre("2. Validations retirées automatiquement — à relire")
    n2 = validations_tombees(conn, "of_imports", "of_numero", "OF", args.limite)
    n2 += validations_tombees(conn, "fiches_techniques", "reference",
                              "Fiches techniques", args.limite)

    _titre("3. Documents validés malgré un changement postérieur (ne devrait rien donner)")
    if _table_existe(conn, "documents_valeurs_historique"):
        n3 = changements_sous_validation(conn, "of_imports", "of_numero", "OF", args.limite)
        n3 += changements_sous_validation(conn, "fiches_techniques", "reference",
                                          "Fiches techniques", args.limite)
    else:
        print("  Journal absent.")
        n3 = 0

    _titre("4. Déstockages calculés sur des documents modifiés depuis")
    mcols = {r["name"] for r in conn.execute("PRAGMA table_info(mp_mouvements)")}
    if {"of_import_id", "fiche_id"} <= mcols and _table_existe(
            conn, "documents_valeurs_historique"):
        n4 = destockages_sur_chiffres_perimes(conn, args.limite)
    else:
        print("  Colonnes de rattachement absentes.")
        n4 = 0

    _titre("Bilan")
    print(f"  À relire avant déstockage        : {n2}")
    print(f"  Anomalies de dévalidation        : {n3}"
          + ("   ← chemin d'écriture à corriger" if n3 else ""))
    print(f"  Déstockages à vérifier           : {n4}"
          + ("   ← comparer avec l'inventaire" if n4 else ""))
    print("\n  Rappel : rien de tout cela ne remonte avant le 7 août 2026 — "
          "le journal n'existait pas.")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

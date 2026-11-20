"""
Reprise : relit les postes en euros de tous les devis déjà importés.

Les devis entrés avant la lecture du chiffrage n'ont que le socle (temps,
métrages). Ce script rouvre le classeur conservé à l'import, lit ses postes en
euros, puis rejoue le calcul du classeur avec le moteur de rentabilité : c'est
le contrôle qui prouve que le moteur retrouve la marge et le coût horaire de
chaque devis, et qui signale les classeurs mal lus.

Simulation par défaut (rien n'est écrit). `--appliquer` enregistre.

    python3 scripts/devis_chiffrage_reprise.py
    python3 scripts/devis_chiffrage_reprise.py --appliquer
    python3 scripts/devis_chiffrage_reprise.py --detail      (liste les écarts)
"""
import sys
import os
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database                      # d'abord, toujours (voir CLAUDE.md)
from database import get_db
from app.services import devis_chiffrage, rentabilite_parametres
from app.services.rentabilite_calcul import controler_devis


def main() -> int:
    appliquer = "--appliquer" in sys.argv
    detail = "--detail" in sys.argv
    bilan = Counter()
    echecs = Counter()
    lignes_detail = []

    with get_db() as conn:
        if not devis_chiffrage.table_presente(conn):
            print("Table devis_chiffrage absente : lancer l'application une fois pour migrer.")
            return 1
        tolerance = rentabilite_parametres.lire(conn)["tolerance_controle_pct"]
        devis = conn.execute(
            "SELECT id, filename, laize, fichier_chemin FROM devis ORDER BY id"
        ).fetchall()
        for d in devis:
            chemin = devis_chiffrage.chemin_fichier(d["fichier_chemin"])
            if not chemin:
                bilan["sans fichier"] += 1
                continue
            try:
                with open(chemin, "rb") as f:
                    lecture = devis_chiffrage.lire_chiffrage(f.read(), d["filename"] or chemin)
            except Exception as e:
                bilan["illisible"] += 1
                lignes_detail.append(f"#{d['id']} illisible : {e}")
                continue
            v = lecture["valeurs"]
            if v.get("prix_vente") is None:
                bilan["sans prix de vente"] += 1
                continue
            bilan["lus"] += 1
            if appliquer:
                devis_chiffrage.enregistrer(conn, d["id"], lecture)
            controles = controler_devis(v, d["laize"] or None, tolerance)
            faux = [c for c in controles if not c["ok"]]
            if faux:
                bilan["contrôle en écart"] += 1
                for c in faux:
                    echecs[c["controle"]] += 1
                    lignes_detail.append(
                        f"#{d['id']} {c['controle']} : lu {c['lu']} / recalculé "
                        f"{c['recalcule']} ({c['ecart_pct']} %) — {d['filename']}")
            else:
                bilan["contrôle juste"] += 1
        if appliquer:
            conn.commit()

    print(f"{len(devis)} devis en base — {'ÉCRITURE' if appliquer else 'simulation'}")
    for k, n in bilan.most_common():
        print(f"  {k:<22} {n}")
    if echecs:
        print("Contrôles en écart :")
        for k, n in echecs.most_common():
            print(f"  {n:>4} × {k}")
    if detail:
        print("\n".join(lignes_detail))
    return 0


if __name__ == "__main__":
    sys.exit(main())

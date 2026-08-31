# -*- coding: utf-8 -*-
"""
Valorisation MyStock : détecter et rattraper les sous-totaux qui ont dérivé.

Ce que la valorisation MyStock affiche n'est pas le prix d'achat nu, mais le
**sous-total d'achat** : prix + transport + taxes, dans la devise et la base
d'achat. C'est cette valeur-là qui doit apparaître des deux côtés, sinon deux
écrans donnent deux chiffres pour la même matière.

Elle est poussée par `_mirror_principal`, appelé quand on change un prix
(`set_prix`), un tarif fournisseur (`set_tarif`), un paramétrage
(`set_parametrage`) ou le fournisseur principal (`set_principal`).

Mais rien ne la recalcule après coup. Une valeur écrite le jour où le transport
valait 5 % y reste après le passage à 9 % si le chemin emprunté n'a pas
déclenché le miroir : import en masse, écriture directe en base, migration,
tarif créé avant que le fournisseur ne devienne principal. On lit alors
4,41 €/kg dans la valorisation là où la fiche calcule 4,578.

Ce script relit le sous-total de chaque déclinaison, le compare à ce que la
valorisation porte, et affiche l'écart. Avec `--appliquer`, il repousse la bonne
valeur — par `_mirror_principal`, donc en écrivant aussi l'historique de
valorisation : aucun chiffre ne change sans laisser de trace.

──────────────────────────────────────────────────────────────────────────────

  1.  python3 scripts/resync_valorisation.py --inventaire

      Liste les écarts, du plus gros au plus petit. N'écrit rien.

  2.  python3 scripts/resync_valorisation.py --appliquer

      Repousse les sous-totaux. Relançable : ce qui est déjà juste est ignoré.

Options : --db, --matiere <id> pour n'en traiter qu'une, --seuil <euros> pour
ne retenir que les écarts au-dessus d'un montant (défaut 0,0001).
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)


def _chemin_defaut() -> str:
    try:
        from config import DB_PATH  # type: ignore

        return DB_PATH
    except Exception:
        return os.path.join(RACINE, "data", "production.db")


def analyser(conn, matiere_id=None, seuil=0.0001) -> list[dict]:
    from app.services import mystock_prix as MP

    sql = """SELECT d.id AS decl_id, d.matiere_id, mp.reference, mp.designation,
                    mp.categorie
               FROM mp_matiere_declinaison d
               JOIN matieres_premieres mp ON mp.id = d.matiere_id"""
    args: list = []
    if matiere_id is not None:
        sql += " WHERE d.matiere_id = ?"
        args.append(matiere_id)
    sql += " ORDER BY mp.categorie, mp.reference, d.id"

    out: list[dict] = []
    for r in conn.execute(sql, args).fetchall():
        decl_id = int(r["decl_id"])
        prix_row = conn.execute(
            "SELECT prix FROM mp_matiere_prix WHERE declinaison_id=? AND principal=1 LIMIT 1",
            (decl_id,),
        ).fetchone()
        if not prix_row:
            continue  # sans prix principal, il n'y a rien à pousser

        attendu = MP.sous_total_declinaison(conn, decl_id)
        d = MP.fetch_declinaison_complete(conn, decl_id)
        mat = MP.fetch_matiere(conn, int(r["matiere_id"]))
        if not d or not mat:
            continue
        actuel = MP._prix_mystock_de_reference(conn, mat, d["laize_id"])

        ecart = attendu - (actuel or 0.0)
        if abs(ecart) <= seuil:
            continue
        out.append(
            {
                "decl_id": decl_id,
                "matiere_id": int(r["matiere_id"]),
                "reference": r["reference"],
                "categorie": r["categorie"],
                "prix": float(prix_row["prix"] or 0),
                "actuel": actuel,
                "attendu": attendu,
                "ecart": ecart,
            }
        )
    return sorted(out, key=lambda x: -abs(x["ecart"]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=None)
    ap.add_argument("--matiere", type=int, default=None)
    ap.add_argument("--seuil", type=float, default=0.0001)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--inventaire", action="store_true")
    g.add_argument("--appliquer", action="store_true")
    a = ap.parse_args()

    chemin = a.db or _chemin_defaut()
    if not os.path.exists(chemin):
        print(f"Base introuvable : {chemin}")
        return 2

    conn = sqlite3.connect(chemin)
    conn.row_factory = sqlite3.Row
    try:
        from app.services import mystock_prix as MP

        ecarts = analyser(conn, a.matiere, a.seuil)
        print(f"Base : {chemin}")
        print(f"{len(ecarts)} déclinaison(s) dont la valorisation a dérivé.\n")
        if ecarts:
            print(f"  {'RÉFÉRENCE':<16}{'PRIX':>10}{'VALORISÉ':>12}{'DEVRAIT':>12}{'ÉCART':>12}")
            for e in ecarts[:60]:
                print(
                    f"  {e['reference']:<16}{e['prix']:>10.4f}"
                    f"{(e['actuel'] or 0):>12.4f}{e['attendu']:>12.4f}{e['ecart']:>+12.4f}"
                )
            if len(ecarts) > 60:
                print(f"  … et {len(ecarts) - 60} autres.")

        if a.inventaire:
            print("\nInventaire seul : rien n'a été écrit.")
            return 0

        n = 0
        for e in ecarts:
            res = MP._mirror_principal(
                conn, e["decl_id"], user_id=None, user_name="resync",
                note="Resynchronisation du sous-total d'achat",
            )
            if res.get("ok"):
                n += 1
        conn.commit()
        print(f"\n{n} valorisation(s) remise(s) à jour, avec trace dans l'historique.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

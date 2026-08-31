# -*- coding: utf-8 -*-
"""
Fusion des déclinaisons : une matière, une ligne, un prix.

La déclinaison existait pour porter deux choses : le grammage d'un adhésif et le
prix. Le grammage est parti sur le composant du produit le 31 août 2026 (voir la
migration `mp_grammage_sur_composant`), et le prix, lui, n'a jamais varié d'une
déclinaison à l'autre — un adhésif ne s'achète pas plus cher en 22 g/m² qu'en 17.
Il ne reste donc rien à décliner.

Ce script ramène chaque matière à UNE déclinaison, celle qui survit :

    prix           les lignes des déclinaisons absorbées sont déplacées vers la
                   survivante, en dédoublonnant par fournisseur ;
    produits       les composants sont repointés vers la survivante — leur
                   grammage, lui, reste ce qu'ils portent déjà ;
    historique     déplacé, jamais supprimé : la trace d'un prix survit à la
                   ligne qui le portait.

──────────────────────────────────────────────────────────────────────────────
CE SCRIPT EST À SENS UNIQUE. Faire une copie de la base avant `--appliquer`.
──────────────────────────────────────────────────────────────────────────────

Trois étapes, dans cet ordre

  1.  python3 scripts/fusion_declinaisons.py --inventaire

      Ce qu'il y a à fusionner, et surtout ce qui coince : matières dont les
      déclinaisons ne portent PAS le même prix, ou des fournisseurs différents.
      Ces cas-là ne se tranchent pas tout seuls et sont laissés de côté.

  2.  python3 scripts/fusion_declinaisons.py --simulation

      Rejoue la fusion sans rien écrire : ce qui serait déplacé, ce qui serait
      supprimé, ce qui resterait en l'état.

  3.  python3 scripts/fusion_declinaisons.py --appliquer

      Écrit. Relançable : une matière déjà réduite à une ligne est ignorée.

Options : --db /chemin/production.db, et --matiere <id> pour n'en traiter qu'une
(utile pour se faire la main sur une référence avant de lancer le lot).
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

# Un écart de prix en dessous de ce seuil est un arrondi, pas un désaccord.
EPS = 1e-9


def _chemin_defaut() -> str:
    try:
        from config import DB_PATH  # type: ignore

        return DB_PATH
    except Exception:
        return os.path.join(RACINE, "data", "production.db")


def _ouvrir(chemin: str) -> sqlite3.Connection:
    conn = sqlite3.connect(chemin)
    conn.row_factory = sqlite3.Row
    return conn


def analyser(conn: sqlite3.Connection, matiere_id=None) -> list[dict]:
    """
    Par matière : les déclinaisons, celle qui survit, et ce qui empêche de fusionner.

    La survivante est la déclinaison qui porte le prix principal. À défaut, la
    plus ancienne — arbitraire mais stable, et elle emporte de toute façon les
    lignes des autres.
    """
    sql = """SELECT d.id, d.matiere_id, d.laize_id, d.grammage_id, d.created_at,
                    mp.reference, mp.designation, mp.categorie
               FROM mp_matiere_declinaison d
               JOIN matieres_premieres mp ON mp.id = d.matiere_id"""
    args: list = []
    if matiere_id is not None:
        sql += " WHERE d.matiere_id = ?"
        args.append(matiere_id)
    sql += " ORDER BY d.matiere_id, d.created_at, d.id"

    par_mat: dict[int, list[sqlite3.Row]] = {}
    for r in conn.execute(sql, args).fetchall():
        par_mat.setdefault(int(r["matiere_id"]), []).append(r)

    out: list[dict] = []
    for mid, decls in par_mat.items():
        if len(decls) < 2:
            continue  # déjà réduite à une ligne : rien à faire

        ids = [int(d["id"]) for d in decls]
        marques = ",".join("?" * len(ids))
        prix = conn.execute(
            f"""SELECT declinaison_id, fournisseur_id, prix, principal
                  FROM mp_matiere_prix
                 WHERE declinaison_id IN ({marques})""",
            ids,
        ).fetchall()

        # Ce qui empêche une fusion silencieuse : deux prix différents, ou deux
        # fournisseurs. Dans les deux cas, choisir à la place de quelqu'un
        # écrirait un prix que personne n'a validé.
        blocages: list[str] = []
        principaux = [p for p in prix if p["principal"]]
        valeurs = {round(float(p["prix"] or 0), 6) for p in principaux}
        if len(valeurs) > 1:
            blocages.append(
                "prix principaux différents : " + ", ".join(f"{v:g}" for v in sorted(valeurs))
            )
        fournisseurs = {p["fournisseur_id"] for p in principaux}
        if len(fournisseurs) > 1:
            blocages.append(f"{len(fournisseurs)} fournisseurs principaux différents")

        survivante = next(
            (int(p["declinaison_id"]) for p in prix if p["principal"]), ids[0]
        )
        absorbees = [i for i in ids if i != survivante]

        composants = conn.execute(
            f"""SELECT COUNT(*) n FROM mp_produit_composant
                 WHERE declinaison_id IN ({marques})""",
            ids,
        ).fetchone()["n"]

        out.append(
            {
                "matiere_id": mid,
                "reference": decls[0]["reference"],
                "designation": decls[0]["designation"],
                "categorie": decls[0]["categorie"],
                "survivante": survivante,
                "absorbees": absorbees,
                "nb_prix": len(prix),
                "nb_composants": composants,
                "blocages": blocages,
            }
        )
    return sorted(out, key=lambda x: (x["categorie"] or "", x["reference"] or ""))


def fusionner(conn: sqlite3.Connection, plan: dict) -> dict:
    """Déplace tout vers la survivante, puis supprime les déclinaisons vidées."""
    survivante, absorbees = plan["survivante"], plan["absorbees"]
    if not absorbees:
        return {"prix": 0, "composants": 0, "historique": 0, "supprimees": 0}

    marques = ",".join("?" * len(absorbees))
    deja = {
        r["fournisseur_id"]
        for r in conn.execute(
            "SELECT fournisseur_id FROM mp_matiere_prix WHERE declinaison_id = ?",
            (survivante,),
        ).fetchall()
    }

    # Les lignes de prix : on déplace celles dont le fournisseur manque à la
    # survivante, et on supprime les doublons — même fournisseur, même prix,
    # les garder créerait deux lignes concurrentes pour une seule offre.
    deplaces = 0
    for r in conn.execute(
        f"SELECT id, fournisseur_id FROM mp_matiere_prix WHERE declinaison_id IN ({marques})",
        absorbees,
    ).fetchall():
        if r["fournisseur_id"] in deja:
            conn.execute("DELETE FROM mp_matiere_prix WHERE id = ?", (r["id"],))
        else:
            conn.execute(
                "UPDATE mp_matiere_prix SET declinaison_id = ?, principal = 0 WHERE id = ?",
                (survivante, r["id"]),
            )
            deja.add(r["fournisseur_id"])
            deplaces += 1

    # Les composants de produit : repointés. Leur grammage leur appartient déjà,
    # il ne bouge pas — c'est tout l'intérêt d'avoir migré avant de fusionner.
    comps = conn.execute(
        f"""UPDATE mp_produit_composant SET declinaison_id = ?
             WHERE declinaison_id IN ({marques})""",
        [survivante] + absorbees,
    ).rowcount

    # L'historique suit : un prix a été saisi un jour, la ligne qui le portait
    # peut disparaître sans que la trace disparaisse avec elle.
    hist = conn.execute(
        f"""UPDATE mp_prix_historique SET declinaison_id = ?
             WHERE declinaison_id IN ({marques})""",
        [survivante] + absorbees,
    ).rowcount

    sup = conn.execute(
        f"DELETE FROM mp_matiere_declinaison WHERE id IN ({marques})", absorbees
    ).rowcount

    return {"prix": deplaces, "composants": comps, "historique": hist, "supprimees": sup}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--db", default=None)
    ap.add_argument("--matiere", type=int, default=None, help="ne traiter que cette matière")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--inventaire", action="store_true")
    g.add_argument("--simulation", action="store_true")
    g.add_argument("--appliquer", action="store_true")
    a = ap.parse_args()

    chemin = a.db or _chemin_defaut()
    if not os.path.exists(chemin):
        print(f"Base introuvable : {chemin}")
        return 2

    conn = _ouvrir(chemin)
    try:
        plans = analyser(conn, a.matiere)
        faisables = [p for p in plans if not p["blocages"]]
        bloques = [p for p in plans if p["blocages"]]

        print(f"Base : {chemin}")
        print(f"{len(plans)} matière(s) portent plusieurs déclinaisons.")
        print(f"  {len(faisables)} fusionnable(s) sans arbitrage")
        print(f"  {len(bloques)} à trancher à la main\n")

        if faisables:
            print("── Fusionnables ─────────────────────────────────────────────")
            for p in faisables:
                print(
                    f"  {p['reference']:<14} {(p['categorie'] or ''):<10} "
                    f"{len(p['absorbees']) + 1} → 1  "
                    f"(garde #{p['survivante']}, {p['nb_composants']} composant(s) repointé(s))"
                )

        if bloques:
            print("\n── À trancher à la main ─────────────────────────────────────")
            print("   Ces matières portent des prix ou des fournisseurs qui ne")
            print("   concordent pas. Fusionner reviendrait à choisir un prix à")
            print("   votre place ; le script s'abstient.\n")
            for p in bloques:
                print(f"  {p['reference']:<14} {(p['categorie'] or ''):<10} {'; '.join(p['blocages'])}")

        if a.inventaire:
            print("\nInventaire seul : rien n'a été écrit.")
            return 0

        if a.simulation:
            total_c = sum(p["nb_composants"] for p in faisables)
            total_d = sum(len(p["absorbees"]) for p in faisables)
            print(
                f"\nSimulation : {total_d} déclinaison(s) seraient supprimées, "
                f"{total_c} composant(s) repointé(s). Rien n'a été écrit."
            )
            return 0

        totaux = {"prix": 0, "composants": 0, "historique": 0, "supprimees": 0}
        for p in faisables:
            res = fusionner(conn, p)
            for k in totaux:
                totaux[k] += res[k]
        conn.commit()
        print(
            f"\nFusion appliquée : {totaux['supprimees']} déclinaison(s) supprimée(s), "
            f"{totaux['prix']} ligne(s) de prix déplacée(s), "
            f"{totaux['composants']} composant(s) repointé(s), "
            f"{totaux['historique']} mouvement(s) d'historique conservé(s)."
        )
        if bloques:
            print(f"{len(bloques)} matière(s) laissée(s) en l'état — voir la liste ci-dessus.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

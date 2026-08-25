#!/usr/bin/env python3
"""MySifa — le besoin calculé colle-t-il aux sorties réelles ?

Pourquoi ce script existe
─────────────────────────
La vue Tendance affiche un besoin CALCULÉ (métrage des OF × fiches
techniques). RVGI, lui, enregistre les sorties RÉELLES de stock. Les deux
doivent se rejoindre, à la chute et au calage près. Quand ils divergent, il
faut savoir de combien, sur quel mois et sur quelle matière — pas
approximativement, en lisant une courbe.

Ce script sort les mêmes chiffres que l'écran, en texte, mois par mois et
matière par matière, sur les DEUX axes de temps :

  production — le mois où le dossier passe en machine (la matière doit être
               là), c'est l'axe par défaut de l'écran
  livraison  — le mois promis au client

RVGI date ses sorties au moment où la bobine quitte le stock : c'est donc de
l'axe production qu'il doit être le plus proche. L'écart entre les deux
colonnes mesure exactement ce que le choix d'axe déplace.

Il affiche aussi les jours ouvrés par mois : un août à 9 jours ne se compare
pas à un juillet à 22, et c'est souvent là que se loge un écart qu'on croyait
inexplicable.

Lecture seule. Aucune écriture, aucune table créée.

Usage
─────
    python scripts/diag_besoin.py
    python scripts/diag_besoin.py --kind support --debut 2026-04 --fin 2026-08
    python scripts/diag_besoin.py --kind glassine
    python scripts/diag_besoin.py --db app/data/production.db
"""
import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KINDS = ("support", "glassine", "adhesif", "mandrin", "carton", "palette")


def _defaut_db() -> str:
    try:
        from config import DB_PATH
        return DB_PATH
    except Exception:
        return os.path.join("app", "data", "production.db")


def _mois_entre(debut: str, fin: str) -> list:
    an, mo = int(debut[:4]), int(debut[5:7])
    out = []
    while f"{an:04d}-{mo:02d}" <= fin:
        out.append(f"{an:04d}-{mo:02d}")
        mo += 1
        if mo > 12:
            mo, an = 1, an + 1
    return out


def _fmt(v) -> str:
    if v is None:
        return "       —"
    if v == 0:
        return "       —"
    return f"{round(v / 1000):>7,}k".replace(",", " ")


def collecter(conn, axe: str, kind: str, mois: list) -> dict:
    """{libellé matière: {mois: quantité}} pour un axe et une nature donnés."""
    from app.services.carnet_snapshot import agreger
    from app.routers.besoins_matieres import _agreger_of_orphelins

    cumul, _vus, _va, _dos = agreger(conn, axe)
    cumul_of, _vof = _agreger_of_orphelins(conn, mois[0], axe)

    par = defaultdict(lambda: defaultdict(float))
    for src in (cumul, cumul_of):
        for (mo, _mid, k), agg in src.items():
            if k != kind or mo not in mois:
                continue
            lbl = (agg.get("ref") or agg.get("designation")
                   or agg.get("source_value") or "Non associée")
            par[lbl][mo] += agg["q"]
    return par


def afficher(titre, par, mois, unite=""):
    print("\n" + titre)
    print("─" * min(len(titre), 78))
    if not par:
        print("  (aucune matière sur cette période)")
        return
    print(f"  {'matière':<30}" + "".join(f"{m[5:]}/{m[2:4]:<3}" for m in mois)
          + f"{'TOTAL':>10}")
    tot_col = defaultdict(float)
    for lbl in sorted(par, key=lambda k: -sum(par[k].values())):
        ligne = f"  {lbl[:29]:<30}"
        for m in mois:
            v = par[lbl].get(m, 0)
            tot_col[m] += v
            ligne += _fmt(v)
        ligne += _fmt(sum(par[lbl].values()))
        print(ligne)
    print(f"  {'TOTAL':<30}" + "".join(_fmt(tot_col[m]) for m in mois)
          + _fmt(sum(tot_col.values())))


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=_defaut_db())
    ap.add_argument("--kind", default="support", choices=KINDS,
                    help="Nature de matière (défaut : support = frontal)")
    ap.add_argument("--debut", default="2026-04", metavar="AAAA-MM")
    ap.add_argument("--fin", default="2026-08", metavar="AAAA-MM")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"Base introuvable : {args.db}")
        return 2

    from app.core.database import get_db
    from app.routers.besoins_matieres import _jours_ouvres

    mois = _mois_entre(args.debut, args.fin)
    print(f"Base : {args.db}  (lecture seule)")
    print(f"Nature : {args.kind}   Période : {args.debut} → {args.fin}")

    with get_db() as conn:
        jours = _jours_ouvres(conn, mois)
        prod = collecter(conn, "production", args.kind, mois)
        livr = collecter(conn, "livraison", args.kind, mois)

    print("\nJours ouvrés (au moins une machine tourne)")
    print("─" * 42)
    print("  " + "".join(f"{m[5:]}/{m[2:4]:<3}" for m in mois))
    print("  " + "".join(f"{jours.get(m, '?'):>8}" for m in mois))
    if jours and min(jours.values()) < 12:
        creux = [m for m, n in jours.items() if n < 12]
        print(f"  ⚠ {', '.join(creux)} : moins de 12 jours ouvrés — fermeture.")
        print("    Un besoin élevé sur un de ces mois est une incohérence de")
        print("    planning, pas une consommation : la matière ne peut pas")
        print("    être consommée un jour où l'usine est fermée.")
    elif not jours:
        print("  (planning_day_worked / planning_holidays vides : non mesurable)")

    afficher("AXE PRODUCTION — le mois où la matière doit être en stock",
             prod, mois)
    afficher("AXE LIVRAISON — le mois promis au client", livr, mois)

    tp = sum(sum(v.values()) for v in prod.values())
    tl = sum(sum(v.values()) for v in livr.values())
    print("\nÉcart entre les deux axes")
    print("─" * 42)
    print(f"  production : {_fmt(tp).strip()}     livraison : {_fmt(tl).strip()}")
    if tp:
        print(f"  écart : {(tl / tp - 1) * 100:+.1f} % — c'est ce que déplace le")
        print("  seul choix de datation, à données identiques.")
    print("\nÀ comparer au total RVGI de la même période et de la même nature.")
    print("Un besoin CALCULÉ légèrement supérieur aux sorties réelles est")
    print("attendu (chutes, calages) ; l'inverse signale un besoin sous-évalué.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

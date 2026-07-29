#!/usr/bin/env python3
"""
fix_stock_timezones.py
──────────────────────
Rattrape le décalage UTC → Europe/Paris sur les horodatages du stock écrits
AVANT le correctif `_now_paris()` de `app/routers/stock.py`.

Contexte
────────
`app/routers/stock.py` (et `app/services/ai_data.py`) écrivaient leurs
horodatages avec un `datetime.now()` nu. Le serveur tourne en UTC alors que
toute l'application stocke des datetimes *naïfs en heure de Paris*
(convention CLAUDE.md). Résultat : une entrée Z1 saisie à 16h38 est en base
à 14h38, et s'affiche à 14h38.

Le correctif de code règle le problème pour les nouvelles lignes. Ce script
rattrape les lignes déjà en base.

Colonnes corrigées (écrites uniquement par du code qui était en UTC) :
    • mouvements_stock.created_at
    • lots_stock.created_at

Colonnes VOLONTAIREMENT exclues — elles sont écrites à la fois par
`stock.py` (ex-UTC) et par `fabrication.py` (déjà en heure de Paris). Les
décaler corromprait les lignes correctes, et ce sont des « dernière mise à
jour » jamais affichés en historique :
    • stock_emplacements.updated_at
    • mouvement_palettes.created_at
    • mp_stock.updated_at / mp_stock_laize.updated_at
    • produits.created_at / produits.updated_at

Également exclu : `lots_stock.date_entree`, qui ne contient qu'une date
(`%Y-%m-%d`). L'heure d'origine est perdue, donc la conversion est
indécidable — l'écart ne concerne de toute façon que les saisies faites
entre 22h et minuit.

Le décalage est calculé ligne par ligne via `zoneinfo`, ce qui gère
correctement le passage heure d'été (CEST +2) / heure d'hiver (CET +1).

Usage
─────
    # 1. Prévisualisation, aucune écriture (À FAIRE EN PREMIER)
    python3 scripts/fix_stock_timezones.py --dry-run

    # 2. Application réelle (demande confirmation, écrit une sauvegarde CSV)
    python3 scripts/fix_stock_timezones.py

    # Base non standard
    python3 scripts/fix_stock_timezones.py --db /chemin/vers/production.db

    # Borne explicite : ne corriger que les lignes antérieures à cette date.
    # Par défaut = maintenant. À renseigner si le script est lancé
    # longtemps après la mise en production du correctif.
    python3 scripts/fix_stock_timezones.py --cutoff 2026-07-28T18:00:00

IMPORTANT : lancer ce script APRÈS avoir déployé le correctif de
`app/routers/stock.py`, et UNE SEULE FOIS. Un second passage décalerait à
nouveau les mêmes lignes. Le script refuse de tourner deux fois (garde-fou
par fichier de sauvegarde) sauf `--force`.
"""

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_UTC = timezone.utc
_PARIS = ZoneInfo("Europe/Paris")

# (table, colonne) à corriger.
CIBLES = (
    ("mouvements_stock", "created_at"),
    ("lots_stock", "created_at"),
)

FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%d %H:%M",
)

MARQUEUR = "tz_fix_stock_applique.txt"


def parse_dt(val):
    """Parse une chaîne d'horodatage en datetime naïf. None si illisible."""
    if not val:
        return None
    s = str(val).strip()
    if not s:
        return None
    for fmt in FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def utc_naive_to_paris(dt):
    """Considère dt comme UTC naïf et renvoie l'équivalent naïf heure de Paris.

    Gère automatiquement CEST (+2, été) et CET (+1, hiver).
    """
    return dt.replace(tzinfo=_UTC).astimezone(_PARIS).replace(tzinfo=None)


def format_comme_origine(origine, dt):
    """Réécrit dt dans le même format que la valeur d'origine."""
    if "T" in origine:
        sep = "T"
    else:
        sep = " "
    if "." in origine:
        return dt.strftime("%Y-%m-%d" + sep + "%H:%M:%S.%f")
    if origine.count(":") == 1:
        return dt.strftime("%Y-%m-%d" + sep + "%H:%M")
    return dt.strftime("%Y-%m-%d" + sep + "%H:%M:%S")


def table_existe(conn, table):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return row is not None


def collecter(conn, table, colonne, cutoff):
    """Renvoie la liste des corrections à appliquer pour une table/colonne."""
    if not table_existe(conn, table):
        print("  [!] table '%s' ABSENTE de cette base" % table)
        return None, 0, 0

    rows = conn.execute(
        "SELECT id, %s AS val FROM %s ORDER BY id" % (colonne, table)
    ).fetchall()

    corrections = []
    illisibles = 0
    hors_bornes = 0

    for row in rows:
        dt = parse_dt(row["val"])
        if dt is None:
            illisibles += 1
            continue
        if dt >= cutoff:
            # Écrite après le correctif : déjà en heure de Paris.
            hors_bornes += 1
            continue
        corrige = utc_naive_to_paris(dt)
        if corrige - dt == timedelta(0):
            hors_bornes += 1
            continue
        corrections.append(
            {
                "id": row["id"],
                "avant": str(row["val"]),
                "apres": format_comme_origine(str(row["val"]), corrige),
                "delta_h": (corrige - dt).total_seconds() / 3600,
            }
        )

    return corrections, illisibles, hors_bornes


def main():
    parser = argparse.ArgumentParser(
        description="Rattrapage fuseau horaire UTC → Europe/Paris sur les tables de stock"
    )
    parser.add_argument(
        "--db",
        default=os.getenv("DB_PATH", os.path.join("data", "production.db")),
        help="Chemin de la base (défaut : $DB_PATH ou data/production.db)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Affiche les corrections sans rien écrire"
    )
    parser.add_argument(
        "--cutoff",
        metavar="DATETIME",
        help="Ne corriger que les lignes strictement antérieures à cette date "
        "(ISO, heure de Paris). Défaut : maintenant.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Passe outre le garde-fou anti-double-passage",
    )
    args = parser.parse_args()

    if not os.path.exists(args.db):
        print("[ERREUR] base introuvable : %s" % args.db)
        sys.exit(1)

    if args.cutoff:
        cutoff = parse_dt(args.cutoff)
        if cutoff is None:
            print("[ERREUR] --cutoff : format non reconnu '%s'" % args.cutoff)
            sys.exit(1)
    else:
        cutoff = datetime.now(_PARIS).replace(tzinfo=None)

    if os.path.exists(MARQUEUR) and not args.dry_run and not args.force:
        print("[STOP] '%s' existe : le rattrapage a déjà été appliqué." % MARQUEUR)
        print("       Un second passage décalerait les lignes une deuxième fois.")
        print("       Utilise --force si tu sais ce que tu fais.")
        sys.exit(1)

    print("Base    : %s" % args.db)
    print("Cutoff  : %s (les lignes postérieures sont considérées déjà correctes)" % cutoff.strftime("%Y-%m-%dT%H:%M:%S"))
    print()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    plan = []
    absentes = 0
    for table, colonne in CIBLES:
        print("Analyse de %s.%s ..." % (table, colonne))
        corrections, illisibles, hors_bornes = collecter(conn, table, colonne, cutoff)
        if corrections is None:
            absentes += 1
            continue
        print(
            "  à corriger : %-6d   déjà correctes/ignorées : %-6d   illisibles : %d"
            % (len(corrections), hors_bornes, illisibles)
        )
        if corrections:
            plan.append((table, colonne, corrections))

    if absentes == len(CIBLES):
        conn.close()
        print("\n[ERREUR] aucune des tables cibles n'existe dans '%s'." % args.db)
        print("         Ce n'est pas la base applicative — le script s'arrete sans rien faire.")
        print("         Sur le VPS la base est dans app/data/, pas data/ :")
        print("             grep DB_PATH .env")
        print("             python3 scripts/fix_stock_timezones.py --dry-run --db app/data/production.db")
        sys.exit(1)

    total = sum(len(c) for _, _, c in plan)
    if not total:
        print("\nRien à corriger.")
        conn.close()
        return

    print("\nTotal à corriger : %d ligne(s)" % total)

    for table, colonne, corrections in plan:
        print("\n%s.%s — aperçu (5 plus anciennes / 5 plus récentes) :" % (table, colonne))
        print("  %8s  %-21s  %-21s  %6s" % ("ID", "Avant", "Après", "Δ"))
        print("  " + "-" * 62)
        apercu = corrections[:5]
        if len(corrections) > 10:
            apercu = corrections[:5] + [None] + corrections[-5:]
        elif len(corrections) > 5:
            apercu = corrections[:5] + [None] + corrections[5:]
        for c in apercu:
            if c is None:
                print("  %8s  %s" % ("...", "(%d lignes intermédiaires)" % (len(corrections) - 10)))
                continue
            print(
                "  %8d  %-21s  %-21s  %+5.1fh"
                % (c["id"], c["avant"], c["apres"], c["delta_h"])
            )

    if args.dry_run:
        print("\n[DRY-RUN] Aucune modification appliquée.")
        conn.close()
        return

    rep = input("\nAppliquer %d correction(s) ? [oui/non] : " % total).strip().lower()
    if rep not in ("oui", "o", "yes", "y"):
        print("Annulé.")
        conn.close()
        return

    horodatage = datetime.now(_PARIS).strftime("%Y%m%d_%H%M%S")
    backup = "tz_fix_stock_backup_%s.csv" % horodatage
    with open(backup, "w", encoding="utf-8") as f:
        f.write("table,colonne,id,valeur_originale,valeur_corrigee\n")
        for table, colonne, corrections in plan:
            for c in corrections:
                f.write(
                    "%s,%s,%s,%s,%s\n"
                    % (table, colonne, c["id"], c["avant"], c["apres"])
                )
    print("\nSauvegarde des valeurs originales → %s" % backup)

    applique = 0
    try:
        for table, colonne, corrections in plan:
            conn.executemany(
                "UPDATE %s SET %s=? WHERE id=?" % (table, colonne),
                [(c["apres"], c["id"]) for c in corrections],
            )
            applique += len(corrections)
        conn.commit()
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        conn.close()
        print("\n[ERREUR] rien n'a été appliqué (rollback) : %s" % exc)
        print("         les valeurs d'origine restent dans %s" % backup)
        sys.exit(1)

    conn.close()

    with open(MARQUEUR, "w", encoding="utf-8") as f:
        f.write(
            "Rattrapage fuseau stock appliqué le %s\n"
            "Base      : %s\n"
            "Cutoff    : %s\n"
            "Lignes    : %d\n"
            "Sauvegarde: %s\n"
            % (
                datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S"),
                args.db,
                cutoff.strftime("%Y-%m-%dT%H:%M:%S"),
                applique,
                backup,
            )
        )

    print("\n✓ %d ligne(s) corrigée(s)." % applique)
    print("  Marqueur anti-double-passage écrit → %s" % MARQUEUR)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
fix_production_timezones.py
───────────────────────────
Corrige le décalage horaire UTC → Europe/Paris sur les saisies de production
entrées manuellement (import_id IS NULL, service = 'fabrication').

Les saisies importées (import_id IS NOT NULL) ne sont PAS modifiées.

Usage :
    # Prévisualisation (aucune écriture) :
    python3 scripts/fix_production_timezones.py --dry-run

    # Application réelle :
    python3 scripts/fix_production_timezones.py

    # Limiter à une période donnée :
    python3 scripts/fix_production_timezones.py --before 2026-04-20T14:00:00
"""

import sqlite3
import sys
import argparse
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

DB_PATH  = "production.db"
_UTC     = timezone.utc
_PARIS   = ZoneInfo("Europe/Paris")
FORMATS  = (
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%Y-%m-%d",
)


def parse_dt(val: str) -> datetime | None:
    """Parse une chaîne de date en datetime naïf (sans TZ)."""
    if not val:
        return None
    s = str(val).strip().rstrip("C").strip()
    for fmt in FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def utc_naive_to_paris(dt: datetime) -> datetime:
    """
    Considère dt comme UTC naïf, le convertit en heure locale Paris.
    Gère automatiquement l'heure d'été (CEST +2) et l'heure d'hiver (CET +1).
    """
    dt_utc = dt.replace(tzinfo=_UTC)
    dt_paris = dt_utc.astimezone(_PARIS)
    return dt_paris.replace(tzinfo=None)   # retourne naïf en heure locale Paris


def main():
    parser = argparse.ArgumentParser(description="Correction fuseau horaire saisies prod")
    parser.add_argument("--dry-run", action="store_true",
                        help="Affiche les modifications sans les appliquer")
    parser.add_argument("--before", metavar="DATETIME",
                        help="Ne corriger que les saisies avant cette date (format ISO)")
    parser.add_argument("--db", default=DB_PATH, help=f"Chemin DB (défaut: {DB_PATH})")
    args = parser.parse_args()

    limit_dt = None
    if args.before:
        limit_dt = parse_dt(args.before)
        if not limit_dt:
            print(f"[ERREUR] --before : format non reconnu '{args.before}'")
            sys.exit(1)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    # Saisies manuelles de production (import_id IS NULL + service fabrication)
    rows = conn.execute(
        """SELECT id, date_operation
           FROM production_data
           WHERE import_id IS NULL
             AND service = 'fabrication'
           ORDER BY id""",
    ).fetchall()

    if not rows:
        print("Aucune saisie manuelle de fabrication trouvée.")
        conn.close()
        return

    corrections = []
    skipped_parse = 0
    skipped_limit = 0

    for row in rows:
        dt = parse_dt(row["date_operation"])
        if dt is None:
            skipped_parse += 1
            continue
        if limit_dt and dt >= limit_dt:
            skipped_limit += 1
            continue

        dt_corrige = utc_naive_to_paris(dt)
        delta = dt_corrige - dt
        # Si delta == 0 (p.ex. timestamp déjà corrigé ou en zone neutre) on ignore
        if delta == timedelta(0):
            skipped_limit += 1
            continue

        corrections.append({
            "id": row["id"],
            "avant": dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "apres": dt_corrige.strftime("%Y-%m-%dT%H:%M:%S"),
            "delta_h": delta.total_seconds() / 3600,
        })

    print(f"\nSaisies analysées      : {len(rows)}")
    print(f"Parse échoué           : {skipped_parse}")
    print(f"Ignorées (limite/nul)  : {skipped_limit}")
    print(f"À corriger             : {len(corrections)}")

    if not corrections:
        print("\nRien à corriger.")
        conn.close()
        return

    # Aperçu des 10 premières lignes
    print("\nAperçu (max 10 premières lignes) :")
    print(f"  {'ID':>6}  {'Avant':>20}  {'Après':>20}  {'Δ':>6}")
    print("  " + "-" * 58)
    for c in corrections[:10]:
        print(f"  {c['id']:>6}  {c['avant']:>20}  {c['apres']:>20}  {c['delta_h']:>+5.1f}h")
    if len(corrections) > 10:
        print(f"  ... et {len(corrections) - 10} autres lignes")

    if args.dry_run:
        print("\n[DRY-RUN] Aucune modification appliquée.")
        conn.close()
        return

    # Confirmation
    rep = input(f"\nAppliquer {len(corrections)} corrections ? [oui/non] : ").strip().lower()
    if rep not in ("oui", "o", "yes", "y"):
        print("Annulé.")
        conn.close()
        return

    # Sauvegarde légère : log des valeurs originales dans un fichier texte
    backup_path = f"tz_fix_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(backup_path, "w") as f:
        f.write("id,date_operation_originale\n")
        for c in corrections:
            f.write(f"{c['id']},{c['avant']}\n")
    print(f"\nSauvegarde des valeurs originales → {backup_path}")

    # Application
    updated = 0
    for c in corrections:
        conn.execute(
            "UPDATE production_data SET date_operation=? WHERE id=?",
            (c["apres"], c["id"]),
        )
        updated += 1

    conn.commit()
    conn.close()
    print(f"\n✓ {updated} saisies corrigées.")


if __name__ == "__main__":
    main()

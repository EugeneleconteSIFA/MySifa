#!/usr/bin/env python3
"""Import du fichier matière Excel dans matiere_params et matiere_base.

Usage (depuis la racine du projet sur le VPS) :
    python3 scripts/import_matiere_xlsx.py "data/Prix matière première support adhésif  CORRECTION au 08-04-2026 (2).xlsx"

Options :
    --replace    Vide les tables avant l'import (par défaut : ajout/mise à jour)
    --dry-run    Affiche ce qui serait importé sans toucher à la DB
"""

import argparse
import io
import os
import sys
from datetime import datetime
from pathlib import Path

# --- path setup ---
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import pandas as pd
except ImportError:
    sys.exit("pandas manquant — pip install pandas openpyxl --break-system-packages")

try:
    import openpyxl  # noqa: F401
except ImportError:
    sys.exit("openpyxl manquant — pip install openpyxl --break-system-packages")


def main():
    parser = argparse.ArgumentParser(description="Import matière Excel → SQLite")
    parser.add_argument("fichier", help="Chemin vers le .xlsx")
    parser.add_argument("--replace", action="store_true", help="Vider les tables avant import")
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans écriture DB")
    args = parser.parse_args()

    xlsx_path = Path(args.fichier)
    if not xlsx_path.exists():
        # Essai depuis la racine du projet
        xlsx_path = ROOT / args.fichier
    if not xlsx_path.exists():
        sys.exit(f"Fichier introuvable : {args.fichier}")

    print(f"Lecture : {xlsx_path.name}")
    try:
        sheets = pd.read_excel(str(xlsx_path), sheet_name=None, engine="openpyxl")
    except Exception as e:
        sys.exit(f"Erreur lecture Excel : {e}")

    print(f"Feuilles trouvées : {list(sheets.keys())}")

    from app.routers.matiere_prix import (
        _find_sheet,
        _import_sifa_base,
        _import_sifa_parametres,
        _is_sifa_matiere_workbook,
        _sheet_key_parametres_sifa,
        _sifa_apply_workbook_config,
    )
    from app.core.database import get_db

    is_sifa = _is_sifa_matiere_workbook(sheets)
    print(f"Format SIFA détecté : {is_sifa}")

    sk_p = _sheet_key_parametres_sifa(sheets)
    sh_b = _find_sheet(sheets, "Base_matières", "Base_matieres", "Base matières")

    if not sk_p:
        sys.exit("Feuille Parametres introuvable dans le fichier Excel.")

    print(f"  → Feuille params : {sk_p!r} ({len(sheets[sk_p])} lignes)")
    if sh_b:
        print(f"  → Feuille base   : {sh_b!r} ({len(sheets[sh_b])} lignes)")
    else:
        print("  ⚠  Feuille Base_matières non trouvée — seuls les params seront importés.")

    if args.dry_run:
        print("\n[DRY-RUN] Simulation terminée — aucune modification DB.")
        return

    now = datetime.now().isoformat()

    with get_db() as conn:
        before_p = conn.execute("SELECT COUNT(*) FROM matiere_params").fetchone()[0]
        before_b = conn.execute("SELECT COUNT(*) FROM matiere_base").fetchone()[0]
        print(f"\nAvant import — matiere_params:{before_p}  matiere_base:{before_b}")

        if args.replace:
            print("Suppression des données existantes (--replace)…")
            conn.execute("DELETE FROM matiere_base")
            conn.execute("DELETE FROM matiere_params")

        _sifa_apply_workbook_config(conn, sheets[sk_p], now)
        n_p, e_p = _import_sifa_parametres(conn, sheets[sk_p], now)

        n_b, e_b = 0, []
        if sh_b:
            n_b, e_b = _import_sifa_base(conn, sheets[sh_b], now)

        conn.commit()

        after_p = conn.execute("SELECT COUNT(*) FROM matiere_params").fetchone()[0]
        after_b = conn.execute("SELECT COUNT(*) FROM matiere_base").fetchone()[0]

    print(f"Après import  — matiere_params:{after_p}  matiere_base:{after_b}")
    print(f"Importés      — params:{n_p}  base:{n_b}")

    all_errors = e_p + e_b
    if all_errors:
        print(f"\n{len(all_errors)} avertissement(s) :")
        for err in all_errors[:20]:
            print(f"  • {err}")
        if len(all_errors) > 20:
            print(f"  … et {len(all_errors) - 20} autre(s).")
    else:
        print("Import terminé sans erreur.")


if __name__ == "__main__":
    main()

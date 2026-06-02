"""
Script one-shot — Suppression des dossiers planning créés par access_bridge
===========================================================================
Usage (depuis la racine du projet) :

    python scripts/remove_bridge_planning_entries.py          # dry-run (aucune suppression)
    python scripts/remove_bridge_planning_entries.py --apply  # suppression effective

Le script ne supprime que les entrées statut='attente'.
Les entrées 'en_cours' ou 'terminé' sont signalées mais JAMAIS supprimées
automatiquement — elles nécessitent une décision manuelle.
"""
import sys
import os

# Rendre config et database importables depuis la racine
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db  # shim → app/core/database.py

DRY_RUN = "--apply" not in sys.argv

CREATED_BY = "access_bridge"

def main():
    mode = "DRY-RUN" if DRY_RUN else "APPLY"
    print(f"\n=== remove_bridge_planning_entries [{mode}] ===\n")

    with get_db() as conn:
        rows = conn.execute(
            """SELECT pe.id, pe.reference, pe.statut, pe.created_at, m.nom AS machine
               FROM planning_entries pe
               LEFT JOIN machines m ON m.id = pe.machine_id
               WHERE pe.created_by = ?
               ORDER BY pe.created_at DESC""",
            (CREATED_BY,)
        ).fetchall()

    if not rows:
        print("Aucune entrée 'created_by=access_bridge' trouvée dans planning_entries.")
        print("Rien à faire.\n")
        return

    print(f"{len(rows)} entrée(s) trouvée(s) avec created_by='{CREATED_BY}' :\n")

    deletable = []
    locked    = []

    for r in rows:
        tag = f"  [{r['statut']:10s}]  id={r['id']:>5}  machine={r['machine'] or '?':12s}  ref={r['reference'] or '?'}  créé={r['created_at'] or '?'}"
        if r["statut"] in ("en_cours", "termine"):
            locked.append(r)
            print(f"  BLOQUÉ  {tag}")
        else:
            deletable.append(r)
            print(f"  À SUPPR {tag}")

    print()

    if locked:
        print(f"ATTENTION : {len(locked)} entrée(s) verrouillée(s) (en_cours / terminé).")
        print("  → Ces entrées ne seront PAS supprimées. Traitez-les manuellement dans le planning.\n")

    if not deletable:
        print("Aucune entrée supprimable (toutes verrouillées).\n")
        return

    print(f"{len(deletable)} entrée(s) supprimable(s) (statut=attente).")

    if DRY_RUN:
        print("\nMode DRY-RUN — aucune modification effectuée.")
        print("Relancez avec --apply pour supprimer.\n")
        return

    # Suppression effective
    ids = [r["id"] for r in deletable]
    placeholders = ",".join("?" * len(ids))
    with get_db() as conn:
        conn.execute(
            f"DELETE FROM planning_entries WHERE id IN ({placeholders})",
            ids
        )
        conn.commit()

    print(f"\n{len(ids)} entrée(s) supprimée(s) du planning.\n")
    if locked:
        print(f"Rappel : {len(locked)} entrée(s) verrouillée(s) non traitée(s).\n")

if __name__ == "__main__":
    main()

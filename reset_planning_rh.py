"""
reset_planning_rh.py — Vide la table rh_planning_postes (affectations de test).
Usage : python reset_planning_rh.py [--dry-run]
"""
import sqlite3
import sys
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "production.db")

dry_run = "--dry-run" in sys.argv

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    """SELECT p.id, u.nom, p.semaine, p.poste, p.creneau
       FROM rh_planning_postes p
       JOIN users u ON u.id = p.user_id
       ORDER BY p.semaine, u.nom"""
).fetchall()

if not rows:
    print("Aucune affectation en base — rien à supprimer.")
    conn.close()
    sys.exit(0)

print(f"{'[DRY-RUN] ' if dry_run else ''}Affectations trouvées ({len(rows)}) :")
print(f"{'ID':<6} {'Nom':<25} {'Semaine':<10} {'Poste':<15} {'Créneau'}")
print("-" * 70)
for r in rows:
    print(f"{r['id']:<6} {r['nom']:<25} {r['semaine']:<10} {r['poste']:<15} {r['creneau']}")

if dry_run:
    print("\n[DRY-RUN] Aucune suppression effectuée. Relancez sans --dry-run pour supprimer.")
    conn.close()
    sys.exit(0)

confirm = input(f"\nSupprimer ces {len(rows)} affectation(s) ? [oui/non] : ").strip().lower()
if confirm != "oui":
    print("Annulé.")
    conn.close()
    sys.exit(0)

conn.execute("DELETE FROM rh_planning_postes")
conn.commit()
print(f"✓ {len(rows)} affectation(s) supprimée(s).")
conn.close()

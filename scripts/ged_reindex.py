#!/usr/bin/env python3
"""Reindexation complete de la GED qualite (MyQualite > Certifications SIFA).

A lancer depuis la racine du projet :
    python3 scripts/ged_reindex.py            # ne retraite que les 'pending'/'error'
    python3 scripts/ged_reindex.py --all      # retraite tout, y compris les 'ok'
    python3 scripts/ged_reindex.py --status   # etat de l'index, sans rien modifier

A quoi ca sert :
- apres une modification du parseur (app/services/ged_extract.py)
- apres une restauration de base ou une copie d'environnement
- le jour ou on branchera un OCR : il suffira de relancer sur les 'skipped'

Le script est idempotent et peut tourner pendant que l'application tourne.
"""
from __future__ import annotations

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db          # noqa: E402
from app.services.ged_extract import extract_text  # noqa: E402


def _fts_available(conn) -> bool:
    try:
        conn.execute("SELECT 1 FROM qualite_ged_fts LIMIT 1").fetchone()
        return True
    except Exception:
        return False


def status():
    with get_db() as conn:
        rows = conn.execute(
            "SELECT index_status, COUNT(*) AS n FROM qualite_ged_files "
            "WHERE deleted_at IS NULL GROUP BY index_status"
        ).fetchall()
        total = sum(r["n"] for r in rows)
        print(f"Documents actifs : {total}")
        for r in rows:
            print(f"  {r['index_status']:<10} {r['n']}")
        print(f"FTS5 : {'disponible' if _fts_available(conn) else 'INDISPONIBLE (repli LIKE)'}")


def reindex(all_files: bool):
    with get_db() as conn:
        has_fts = _fts_available(conn)
        sql = ("SELECT f.id, f.nom, f.description, f.tags, f.ext, "
               "       (SELECT v.storage_path FROM qualite_ged_file_versions v "
               "         WHERE v.file_id=f.id AND v.is_current=1 LIMIT 1) AS path "
               "  FROM qualite_ged_files f WHERE f.deleted_at IS NULL")
        if not all_files:
            sql += " AND f.index_status <> 'ok'"
        rows = conn.execute(sql).fetchall()

        print(f"{len(rows)} document(s) a traiter"
              f"{'' if all_files else ' (statut different de ok)'}...")
        stats = {"ok": 0, "skipped": 0, "error": 0, "absent": 0}

        for i, r in enumerate(rows, 1):
            path = r["path"]
            if not path or not os.path.exists(path):
                conn.execute("UPDATE qualite_ged_files SET index_status='error' WHERE id=?",
                             (r["id"],))
                stats["absent"] += 1
                continue
            txt, st = extract_text(path, r["ext"])
            conn.execute(
                "UPDATE qualite_ged_files SET contenu_txt=?, index_status=? WHERE id=?",
                (txt, st, r["id"]),
            )
            if has_fts:
                try:
                    conn.execute("DELETE FROM qualite_ged_fts WHERE rowid=?", (r["id"],))
                    conn.execute(
                        "INSERT INTO qualite_ged_fts (rowid, nom, description, tags, contenu) "
                        "VALUES (?,?,?,?,?)",
                        (r["id"], r["nom"] or "", r["description"] or "",
                         r["tags"] or "", txt or ""),
                    )
                except Exception as e:
                    print(f"  ! FTS id={r['id']} : {e}")
            stats[st] = stats.get(st, 0) + 1
            if i % 25 == 0:
                conn.commit()
                print(f"  {i}/{len(rows)}...")

        conn.commit()

    print("Termine.")
    for k, v in stats.items():
        if v:
            print(f"  {k:<8} {v}")
    if stats.get("skipped"):
        print("\nLes documents 'skipped' n'ont pas de couche texte (PDF scanne, image,")
        print("format non supporte). Ils restent trouvables par leur nom et leurs tags.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Reindexation de la GED qualite")
    ap.add_argument("--all", action="store_true", help="retraiter aussi les documents deja indexes")
    ap.add_argument("--status", action="store_true", help="afficher l'etat de l'index et sortir")
    a = ap.parse_args()
    if a.status:
        status()
    else:
        reindex(a.all)
        print()
        status()

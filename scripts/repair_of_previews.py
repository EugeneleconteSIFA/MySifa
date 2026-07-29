#!/usr/bin/env python3
"""MySifa — réparation des aperçus d'OF désynchronisés.

Contexte
────────
Jusqu'au correctif, l'import d'un PDF d'OF :
  1. créait systématiquement une NOUVELLE ligne dans of_imports, même si le
     numéro existait déjà (empilement de doublons) ;
  2. ne mettait à jour que planning_entries.of_import_id, sans toucher à
     planning_of_links.

Le slot du planning lit of_import_id (quantité correcte) tandis que le panneau
OF lit planning_of_links ORDER BY position (aperçu figé sur le plus ancien
import). D'où le symptôme : bonne quantité dans le slot, mauvais aperçu.

Ce script remet les deux en phase et fusionne les doublons.

Deux OF ne sont considérés comme identiques que si leur numéro COMPLET est le
même, à la casse et aux espaces près : « 9932056 » et « Reliquat 9932056 »
restent deux OF distincts et ne sont jamais fusionnés.

Usage
─────
    python scripts/repair_of_previews.py --dry-run      # simulation (défaut)
    python scripts/repair_of_previews.py --apply        # applique
    python scripts/repair_of_previews.py --apply --of 9932056   # un seul OF

Sans --apply, AUCUNE écriture n'est faite.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from config import DB_PATH, UPLOAD_DIR
except Exception:  # exécution hors arborescence applicative
    DB_PATH = os.getenv("DB_PATH", "data/production.db")
    UPLOAD_DIR = os.getenv("UPLOAD_DIR", "data/uploads")

OF_UPLOAD_DIR = os.path.join(UPLOAD_DIR, "of")

# La racine 99XXXXX ne sert QUE de pré-filtre SQL (ramener les quelques lignes
# candidates). L'égalité réelle entre deux OF est décidée par norm().
_RACINE_RE = re.compile(r"\b(99\d{5})\b")


def racine(num) -> str | None:
    m = _RACINE_RE.search(str(num or ""))
    return m.group(1) if m else None


def norm(num) -> str:
    """Clé de comparaison d'un numéro d'OF : casse et espaces neutralisés."""
    return re.sub(r"\s+", " ", str(num or "").strip()).lower()


def _ts(date_import) -> float:
    s = str(date_import or "")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt).timestamp()
        except ValueError:
            continue
    return 0.0


def _archive_pdf(pdf_filename) -> None:
    """Déplace le PDF d'un OF fusionné dans of/_archive/ (jamais de suppression)."""
    if not pdf_filename:
        return
    src = os.path.join(OF_UPLOAD_DIR, pdf_filename)
    if not os.path.isfile(src):
        return
    dst_dir = os.path.join(OF_UPLOAD_DIR, "_archive")
    os.makedirs(dst_dir, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.move(src, os.path.join(dst_dir, f"{stamp}__{pdf_filename}"))


def _best_first(rows: list) -> list:
    """Trie des lignes of_imports : PDF réel d'abord, puis import le plus récent.

    Deux tris stables successifs — le second (clé la plus forte) l'emporte.
    """
    out = list(rows)
    out.sort(key=lambda r: _ts(r["date_import"]), reverse=True)
    out.sort(key=lambda r: 0 if (r["pdf_filename"] or "").strip() else 1)
    return out


def _candidates_for(conn, numero: str) -> list:
    """Lignes of_imports portant exactement le même numéro d'OF que `numero`."""
    key = norm(numero)
    rac = racine(numero)
    if rac:
        rows = conn.execute(
            """SELECT id, of_numero, pdf_filename, qte_etiquettes, date_import
               FROM of_imports
               WHERE of_numero LIKE ?
                  OR LOWER(TRIM(of_numero)) = LOWER(TRIM(?))""",
            ("%" + rac + "%", numero),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT id, of_numero, pdf_filename, qte_etiquettes, date_import
               FROM of_imports
               WHERE LOWER(TRIM(of_numero)) = LOWER(TRIM(?))""",
            (numero,),
        ).fetchall()
    return [r for r in rows if norm(r["of_numero"]) == key]


# ─────────────────────────────────────────────────────────────────────────────
# Étape 1 — fusion des doublons (même numéro complet, à la casse/espaces près)
#
# On garde la ligne « gagnante » : celle qui a un PDF, la plus récemment
# importée. Les liens planning des perdantes sont reportés sur la gagnante,
# puis les lignes perdantes sont supprimées et leur PDF archivé.
# ─────────────────────────────────────────────────────────────────────────────

def merge_duplicates(conn, apply: bool, only_of: str | None) -> tuple[list[str], set[int]]:
    log: list[str] = []
    removed: set[int] = set()
    rows = conn.execute(
        "SELECT id, of_numero, pdf_filename, date_import, qte_etiquettes, imported_by "
        "FROM of_imports"
    ).fetchall()

    groups: dict[str, list[sqlite3.Row]] = {}
    for r in rows:
        key = norm(r["of_numero"])
        if not key:
            continue
        if only_of and racine(r["of_numero"]) != only_of and only_of not in key:
            continue
        groups.setdefault(key, []).append(r)

    for key, grp in sorted(groups.items()):
        if len(grp) < 2:
            continue
        ordered = _best_first(grp)
        winner, losers = ordered[0], ordered[1:]
        removed.update(int(l["id"]) for l in losers)
        log.append(
            f"[doublon] «{winner['of_numero']}» : {len(grp)} lignes → "
            f"conserve id={winner['id']} "
            f"(pdf={winner['pdf_filename'] or '—'}, qte={winner['qte_etiquettes']}), "
            f"supprime {[int(l['id']) for l in losers]}"
        )
        if not apply:
            continue
        for loser in losers:
            conn.execute(
                "UPDATE OR IGNORE planning_of_links SET of_import_id = ? WHERE of_import_id = ?",
                (winner["id"], loser["id"]),
            )
            conn.execute("DELETE FROM planning_of_links WHERE of_import_id = ?", (loser["id"],))
            conn.execute(
                "UPDATE planning_entries SET of_import_id = ? WHERE of_import_id = ?",
                (winner["id"], loser["id"]),
            )
            _archive_pdf(loser["pdf_filename"])
            conn.execute("DELETE FROM of_imports WHERE id = ?", (loser["id"],))
    return log, removed


# ─────────────────────────────────────────────────────────────────────────────
# Étape 2 — réalignement slot / aperçu
#
# Pour chaque dossier planning, on s'assure que le lien en position 0 de
# planning_of_links est bien celui que le slot affiche
# (planning_entries.of_import_id), et que cet OF est le meilleur candidat
# (PDF présent, import le plus récent) parmi ceux portant le même numéro.
#
# `ignore_ids` : en simulation, les lignes que l'étape 1 s'apprête à supprimer
# ne sont pas encore parties de la base — on les exclut pour que le dry-run
# annonce le même résultat que le --apply.
# ─────────────────────────────────────────────────────────────────────────────

def realign_links(conn, apply: bool, only_of: str | None,
                  ignore_ids: set[int] | None = None) -> list[str]:
    log: list[str] = []
    ignore_ids = ignore_ids or set()
    entries = conn.execute(
        """SELECT pe.id, pe.numero_of, pe.of_import_id
           FROM planning_entries pe
           WHERE TRIM(COALESCE(pe.numero_of,'')) != ''"""
    ).fetchall()

    for e in entries:
        if only_of and racine(e["numero_of"]) != only_of and only_of not in norm(e["numero_of"]):
            continue

        matches = [r for r in _candidates_for(conn, e["numero_of"])
                   if int(r["id"]) not in ignore_ids]
        if not matches:
            continue
        best = _best_first(matches)[0]

        links = conn.execute(
            "SELECT of_import_id, position, id FROM planning_of_links "
            "WHERE planning_entry_id = ? ORDER BY position ASC, id ASC",
            (e["id"],),
        ).fetchall()
        head = links[0]["of_import_id"] if links else None

        if head == best["id"] and e["of_import_id"] == best["id"]:
            continue

        log.append(
            f"[dossier {e['id']}] numero_of=«{e['numero_of']}» : "
            f"slot→{e['of_import_id']}, aperçu→{head} ⇒ "
            f"OF actif = {best['id']} "
            f"(pdf={best['pdf_filename'] or '—'}, qte={best['qte_etiquettes']})"
        )
        if not apply:
            continue

        conn.execute(
            "UPDATE planning_of_links SET position = position + 1 "
            "WHERE planning_entry_id = ? AND of_import_id != ?",
            (e["id"], best["id"]),
        )
        cur = conn.execute(
            "UPDATE planning_of_links SET position = 0 "
            "WHERE planning_entry_id = ? AND of_import_id = ?",
            (e["id"], best["id"]),
        )
        if cur.rowcount == 0:
            conn.execute(
                "INSERT INTO planning_of_links "
                "(planning_entry_id, of_import_id, position, created_by, created_at) "
                "VALUES (?, ?, 0, 'repair_of_previews', ?)",
                (e["id"], best["id"], datetime.now().isoformat(timespec="seconds")),
            )
        conn.execute(
            "UPDATE planning_entries SET of_import_id = ? WHERE id = ?",
            (best["id"], e["id"]),
        )
    return log


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true", help="applique les corrections")
    ap.add_argument("--dry-run", action="store_true", help="simulation (défaut)")
    ap.add_argument("--of", default=None, help="limiter à un numéro racine (ex. 9932056)")
    ap.add_argument("--db", default=DB_PATH, help=f"chemin base SQLite (défaut {DB_PATH})")
    args = ap.parse_args()

    apply = bool(args.apply) and not args.dry_run
    if not os.path.isfile(args.db):
        print(f"Base introuvable : {args.db}", file=sys.stderr)
        return 2

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")

    print(f"Base    : {args.db}")
    print(f"Mode    : {'APPLICATION' if apply else 'SIMULATION (--apply pour écrire)'}")
    if args.of:
        print(f"Filtre  : OF {args.of}")
    print()

    dup_log, removed = merge_duplicates(conn, apply, args.of)
    print(f"── Doublons ({len(dup_log)}) ──")
    for line in dup_log or ["  aucun"]:
        print(f"  {line}")
    print()

    # En simulation les perdantes existent encore : on les ignore pour que le
    # dry-run décrive exactement ce que fera le --apply.
    link_log = realign_links(conn, apply, args.of, ignore_ids=set() if apply else removed)
    print(f"── Dossiers désynchronisés ({len(link_log)}) ──")
    for line in link_log or ["  aucun"]:
        print(f"  {line}")

    if apply:
        conn.commit()
        print("\n✓ Corrections appliquées.")
    else:
        conn.rollback()
        print("\nAucune écriture (simulation). Relancer avec --apply pour appliquer.")
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

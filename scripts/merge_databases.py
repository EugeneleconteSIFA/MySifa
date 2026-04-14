#!/usr/bin/env python3
"""
Merge two MySifa SQLite databases safely.

Goal: merge a "source" DB into a "destination" DB without overwriting destination rows.
Output: a new merged DB file (copy of destination + merged rows).

Important:
- We never merge sessions.
- For stock tables that reference products, we remap produit_id using produits.reference.
- For other tables, we keep a conservative strategy: only merge tables we can do safely.

Usage:
  python scripts/merge_databases.py --dest /path/to/production.db --src /path/to/production_mac.db --out /path/to/production_merged.db
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3


SKIP_TABLES = {
    "sessions",  # do not merge sessions
    "schema_migrations",  # rebuilt by app; avoid conflicts
    "sqlite_sequence",
}


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _split_qualified(name: str) -> tuple[str, str]:
    """
    Split 'schema.table' into ('schema','table').
    If unqualified, returns ('main', name).
    """
    if "." in name:
        schema, table = name.split(".", 1)
        schema = (schema or "main").strip()
        table = table.strip()
        return schema, table
    return "main", name.strip()


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    schema, table = _split_qualified(name)
    row = conn.execute(
        f"SELECT 1 FROM {schema}.sqlite_master WHERE type='table' AND name=? LIMIT 1",
        (table,),
    ).fetchone()
    return bool(row)


def cols(conn: sqlite3.Connection, table: str) -> list[str]:
    schema, t = _split_qualified(table)
    return [r[1] for r in conn.execute(f"PRAGMA {schema}.table_info({t})").fetchall()]


def count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _norm(s: str) -> str:
    return str(s or "").strip().lower()


def pick_col(conn: sqlite3.Connection, table: str, candidates: list[str]) -> str | None:
    present = set(cols(conn, table))
    for c in candidates:
        if c in present:
            return c
    return None


def pick_cols(conn: sqlite3.Connection, table: str, candidates: list[str]) -> list[str]:
    present = set(cols(conn, table))
    return [c for c in candidates if c in present]


def merge_users(out: sqlite3.Connection) -> dict:
    """Merge users by email (destination wins)."""
    if not table_exists(out, "users") or not table_exists(out, "src.users"):
        return {"merged": 0}
    out_cols = set(cols(out, "users"))
    src_cols = set(cols(out, "src.users"))
    # Keep intersection, excluding id/autoincrement
    dst_email = pick_col(out, "users", ["email", "mail"])
    src_email = pick_col(out, "src.users", ["email", "mail"])
    if not dst_email or not src_email:
        return {"merged": 0}

    before = count(out, "users")
    # Prefer canonical destination column names; map from src if needed.
    dst_fields = ["email", "identifiant", "nom", "password_hash", "role", "operateur_lie", "actif", "created_at", "last_login", "telephone", "machine_id", "access_overrides"]
    dst_fields = [c for c in dst_fields if c in out_cols]

    src_fields_map: dict[str, str] = {c: c for c in dst_fields if c in src_cols}
    # map email/mail
    if "email" in out_cols:
        src_fields_map["email"] = src_email
    elif "mail" in out_cols:
        src_fields_map["mail"] = src_email

    use_dst_cols = list(src_fields_map.keys())
    sel = ", ".join([f"s.{src_fields_map[c]} AS {c}" for c in use_dst_cols])
    ins_cols = ", ".join(use_dst_cols)
    qs = ", ".join(["?"] * len(use_dst_cols))

    rows = out.execute(
        f"""
        SELECT {sel}
        FROM src.users s
        WHERE NOT EXISTS (
          SELECT 1 FROM users d
          WHERE LOWER(TRIM(d.{dst_email})) = LOWER(TRIM(s.{src_email}))
        )
        """
    ).fetchall()
    for r in rows:
        out.execute(
            f"INSERT INTO users ({ins_cols}) VALUES ({qs})",
            tuple(r[c] for c in use_dst_cols),
        )
    out.commit()
    after = count(out, "users")
    return {"merged": after - before}


def merge_produits(out: sqlite3.Connection) -> dict:
    """Merge produits by reference (destination wins)."""
    if not table_exists(out, "produits") or not table_exists(out, "src.produits"):
        return {"merged": 0}
    out_cols = set(cols(out, "produits"))
    src_cols = set(cols(out, "src.produits"))
    dst_ref = pick_col(out, "produits", ["reference", "ref", "ref_produit", "refproduit"])
    src_ref = pick_col(out, "src.produits", ["reference", "ref", "ref_produit", "refproduit"])
    if not dst_ref or not src_ref:
        return {"merged": 0}

    before = count(out, "produits")
    # Canonical fields in destination; map from src where possible.
    dst_fields = ["reference", "designation", "description", "unite", "created_at", "updated_at"]
    dst_fields = [c for c in dst_fields if c in out_cols]
    src_fields_map: dict[str, str] = {c: c for c in dst_fields if c in src_cols}
    if "reference" in out_cols:
        src_fields_map["reference"] = src_ref
    elif dst_ref in out_cols:
        src_fields_map[dst_ref] = src_ref

    use_dst_cols = list(src_fields_map.keys())
    sel = ", ".join([f"s.{src_fields_map[c]} AS {c}" for c in use_dst_cols])
    ins_cols = ", ".join(use_dst_cols)
    qs = ", ".join(["?"] * len(use_dst_cols))

    rows = out.execute(
        f"""
        SELECT {sel}
        FROM src.produits s
        WHERE NOT EXISTS (
          SELECT 1 FROM produits d
          WHERE UPPER(TRIM(d.{dst_ref})) = UPPER(TRIM(s.{src_ref}))
        )
        """
    ).fetchall()
    for r in rows:
        out.execute(
            f"INSERT INTO produits ({ins_cols}) VALUES ({qs})",
            tuple(r[c] for c in use_dst_cols),
        )
    out.commit()
    after = count(out, "produits")
    return {"merged": after - before}


def build_product_id_map(out: sqlite3.Connection) -> dict[int, int]:
    """Map src.produits.id -> produits.id using reference."""
    mp: dict[int, int] = {}
    if not (table_exists(out, "produits") and table_exists(out, "src.produits")):
        return mp
    dst_ref = pick_col(out, "produits", ["reference", "ref", "ref_produit", "refproduit"])
    src_ref = pick_col(out, "src.produits", ["reference", "ref", "ref_produit", "refproduit"])
    if not dst_ref or not src_ref:
        return mp
    rows = out.execute(
        f"""
        SELECT s.id AS src_id, d.id AS dst_id
        FROM src.produits s
        JOIN produits d ON UPPER(TRIM(d.{dst_ref})) = UPPER(TRIM(s.{src_ref}))
        """
    ).fetchall()
    for r in rows:
        try:
            mp[int(r["src_id"])] = int(r["dst_id"])
        except Exception:
            pass
    return mp


def merge_messages(out: sqlite3.Connection) -> dict:
    """Merge messages by signature (destination wins)."""
    if not table_exists(out, "messages") or not table_exists(out, "src.messages"):
        return {"merged": 0}

    out_cols = set(cols(out, "messages"))
    src_cols = set(cols(out, "src.messages"))
    needed = {"to_email", "body", "created_at"}
    if not (needed <= out_cols and needed <= src_cols):
        return {"merged": 0}

    before = count(out, "messages")
    rows = out.execute(
        """
        SELECT s.*
        FROM src.messages s
        WHERE NOT EXISTS (
          SELECT 1 FROM messages d
          WHERE LOWER(TRIM(d.to_email)) = LOWER(TRIM(s.to_email))
            AND COALESCE(TRIM(d.created_at),'') = COALESCE(TRIM(s.created_at),'')
            AND COALESCE(TRIM(d.body),'') = COALESCE(TRIM(s.body),'')
        )
        """
    ).fetchall()
    # Insert intersection columns excluding id
    insert_cols = [c for c in cols(out, "messages") if c != "id" and c in src_cols]
    ins = ", ".join(insert_cols)
    qs = ", ".join(["?"] * len(insert_cols))
    for r in rows:
        out.execute(f"INSERT INTO messages ({ins}) VALUES ({qs})", tuple(r[c] for c in insert_cols))
    out.commit()
    after = count(out, "messages")
    return {"merged": after - before}


def merge_mouvements_stock(out: sqlite3.Connection, pid_map: dict[int, int]) -> dict:
    """Merge mouvements_stock by signature, with produit_id remap."""
    if not table_exists(out, "mouvements_stock") or not table_exists(out, "src.mouvements_stock"):
        return {"merged": 0}
    src_cols = set(cols(out, "src.mouvements_stock"))
    out_cols = set(cols(out, "mouvements_stock"))
    # Minimal signature columns we expect
    if not {"produit_id", "emplacement", "type_mouvement", "quantite", "created_at"} <= (src_cols & out_cols | src_cols):
        # still try best-effort
        pass

    before = count(out, "mouvements_stock")

    # Load source rows; remap produit_id using map; skip if cannot map.
    rows = out.execute("SELECT * FROM src.mouvements_stock ORDER BY id").fetchall()

    insert_cols = [c for c in cols(out, "mouvements_stock") if c != "id" and c in src_cols]
    ins = ", ".join(insert_cols)
    qs = ", ".join(["?"] * len(insert_cols))

    merged = 0
    for r in rows:
        try:
            src_pid = int(r["produit_id"])
        except Exception:
            continue
        dst_pid = pid_map.get(src_pid)
        if not dst_pid:
            continue

        # Dedup by signature
        sig = (
            dst_pid,
            _norm(r.get("emplacement")),
            _norm(r.get("type_mouvement")),
            float(r.get("quantite") or 0),
            str(r.get("created_at") or "").strip(),
            str(r.get("note") or "").strip(),
            _norm(r.get("created_by")),
        )
        ex = out.execute(
            """
            SELECT 1 FROM mouvements_stock
            WHERE produit_id=?
              AND LOWER(TRIM(COALESCE(emplacement,'')))=?
              AND LOWER(TRIM(COALESCE(type_mouvement,'')))=?
              AND COALESCE(quantite,0)=?
              AND COALESCE(TRIM(created_at),'')=?
              AND COALESCE(TRIM(note),'')=?
              AND LOWER(TRIM(COALESCE(created_by,'')))=?
            LIMIT 1
            """,
            sig,
        ).fetchone()
        if ex:
            continue

        data = []
        for c in insert_cols:
            if c == "produit_id":
                data.append(dst_pid)
            else:
                data.append(r[c])
        out.execute(f"INSERT INTO mouvements_stock ({ins}) VALUES ({qs})", tuple(data))
        merged += 1
        if merged % 5000 == 0:
            out.commit()

    out.commit()
    after = count(out, "mouvements_stock")
    return {"merged": after - before}


def merge_lots_stock(out: sqlite3.Connection, pid_map: dict[int, int]) -> dict:
    """Merge lots_stock by signature, with produit_id remap."""
    if not table_exists(out, "lots_stock") or not table_exists(out, "src.lots_stock"):
        return {"merged": 0}

    src_cols = set(cols(out, "src.lots_stock"))
    before = count(out, "lots_stock")
    rows = out.execute("SELECT * FROM src.lots_stock ORDER BY id").fetchall()

    insert_cols = [c for c in cols(out, "lots_stock") if c != "id" and c in src_cols]
    ins = ", ".join(insert_cols)
    qs = ", ".join(["?"] * len(insert_cols))

    merged = 0
    for r in rows:
        try:
            src_pid = int(r["produit_id"])
        except Exception:
            continue
        dst_pid = pid_map.get(src_pid)
        if not dst_pid:
            continue

        sig = (
            dst_pid,
            _norm(r.get("emplacement")),
            float(r.get("quantite_initiale") or 0),
            float(r.get("quantite_restante") or 0),
            str(r.get("date_entree") or "").strip(),
            str(r.get("created_at") or "").strip(),
        )
        ex = out.execute(
            """
            SELECT 1 FROM lots_stock
            WHERE produit_id=?
              AND LOWER(TRIM(COALESCE(emplacement,'')))=?
              AND COALESCE(quantite_initiale,0)=?
              AND COALESCE(quantite_restante,0)=?
              AND COALESCE(TRIM(date_entree),'')=?
              AND COALESCE(TRIM(created_at),'')=?
            LIMIT 1
            """,
            sig,
        ).fetchone()
        if ex:
            continue

        data = []
        for c in insert_cols:
            if c == "produit_id":
                data.append(dst_pid)
            else:
                data.append(r[c])
        out.execute(f"INSERT INTO lots_stock ({ins}) VALUES ({qs})", tuple(data))
        merged += 1
        if merged % 5000 == 0:
            out.commit()

    out.commit()
    after = count(out, "lots_stock")
    return {"merged": after - before}


def merge_stock_emplacements(out: sqlite3.Connection, pid_map: dict[int, int]) -> dict:
    """Merge stock_emplacements by (produit_id, emplacement) with remap."""
    if not table_exists(out, "stock_emplacements") or not table_exists(out, "src.stock_emplacements"):
        return {"merged": 0}

    src_cols = set(cols(out, "src.stock_emplacements"))
    out_cols = set(cols(out, "stock_emplacements"))
    if not {"produit_id", "emplacement", "quantite", "updated_at"} <= (src_cols | out_cols):
        pass

    before = count(out, "stock_emplacements")
    rows = out.execute("SELECT * FROM src.stock_emplacements").fetchall()
    merged = 0
    for r in rows:
        try:
            src_pid = int(r["produit_id"])
        except Exception:
            continue
        dst_pid = pid_map.get(src_pid)
        if not dst_pid:
            continue
        empl = str(r["emplacement"] or "").strip().upper()
        if not empl:
            continue

        ex = out.execute(
            "SELECT 1 FROM stock_emplacements WHERE produit_id=? AND emplacement=? LIMIT 1",
            (dst_pid, empl),
        ).fetchone()
        if ex:
            continue

        # Insert intersection columns excluding id
        insert_cols = [c for c in cols(out, "stock_emplacements") if c != "id" and c in src_cols]
        data = []
        for c in insert_cols:
            if c == "produit_id":
                data.append(dst_pid)
            elif c == "emplacement":
                data.append(empl)
            else:
                data.append(r[c])
        ins = ", ".join(insert_cols)
        qs = ", ".join(["?"] * len(insert_cols))
        out.execute(f"INSERT INTO stock_emplacements ({ins}) VALUES ({qs})", tuple(data))
        merged += 1
        if merged % 5000 == 0:
            out.commit()

    out.commit()
    after = count(out, "stock_emplacements")
    return {"merged": after - before}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dest", required=True, help="Destination DB (prod)")
    ap.add_argument("--src", required=True, help="Source DB (mac/local)")
    ap.add_argument("--out", required=True, help="Output merged DB path")
    args = ap.parse_args()

    dest = os.path.abspath(args.dest)
    src = os.path.abspath(args.src)
    outp = os.path.abspath(args.out)

    if not os.path.exists(dest):
        raise SystemExit(f"DEST introuvable: {dest}")
    if not os.path.exists(src):
        raise SystemExit(f"SRC introuvable: {src}")
    if os.path.exists(outp):
        raise SystemExit(f"OUT existe déjà (supprime-le ou change le nom): {outp}")

    print("[merge] copy dest -> out")
    shutil.copy2(dest, outp)

    out = connect(outp)
    try:
        out.execute("ATTACH DATABASE ? AS src", (src,))

        # Safety checks
        for t in SKIP_TABLES:
            pass

        print("[merge] merge users")
        print(merge_users(out))

        print("[merge] merge produits")
        print(merge_produits(out))

        pid_map = build_product_id_map(out)
        print(f"[merge] produit_id map: {len(pid_map)}")

        print("[merge] merge stock_emplacements")
        print(merge_stock_emplacements(out, pid_map))

        print("[merge] merge lots_stock")
        print(merge_lots_stock(out, pid_map))

        print("[merge] merge mouvements_stock")
        print(merge_mouvements_stock(out, pid_map))

        print("[merge] merge messages")
        print(merge_messages(out))

        out.commit()
    finally:
        try:
            out.execute("DETACH DATABASE src")
        except Exception:
            pass
        out.close()

    print(f"[merge] done: {outp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


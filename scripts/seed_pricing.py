#!/usr/bin/env python3
"""
Import seed — Coûts matières (mc_*) depuis JSON export Excel.

Usage:
  python scripts/seed_pricing.py --dry-run
  python scripts/seed_pricing.py
  python scripts/seed_pricing.py --json data/uploads/excel-data-export-fixed.json

Idempotent : upsert matières (name + appellation_code), produits (code).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DB_PATH  # noqa: E402

_NOW = "strftime('%Y-%m-%dT%H:%M:%S','now','localtime')"

# Alias produit → matière (export corrigé)
PRODUCT_REF_ALIASES = {
    "sans silicone": "Sans silicone",
    "sans silcone": "Sans silicone",
    "glassine 58 g chinois": "Glassine 58 g chinois LK",
    "jet d'encre": "1393299 - papier jet d'encre mat 70g",
}

CATEGORY_CODE_MAP = {
    "S": "SILICONE",
    "GLS": "GLASSINE",
    "GL": "GLASSINE",
    "VB": "FRONTAL",
    "CO": "FRONTAL",
    "COU": "FRONTAL",
    "COUCHE": "FRONTAL",
    "TP": "FRONTAL",
    "THP": "FRONTAL",
    "THS": "FRONTAL",
    "PPM": "FRONTAL",
    "PP": "FRONTAL",
    "E": "ADHESIF",
    "P": "ADHESIF",
}

FRONTAL_CODES = frozenset({"VB", "CO", "TP", "THP", "THS", "PPM", "PP", "COU", "COUCHE"})
ADHESIF_CODES = frozenset({"E", "P"})


@dataclass
class Recap:
    suppliers_upserted: int = 0
    materials_inserted: int = 0
    materials_updated: int = 0
    materials_skipped: int = 0
    products_inserted: int = 0
    products_updated: int = 0
    unmapped: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    dry_run: bool = False


def _norm(s: Any) -> str:
    t = str(s or "").strip().lower()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"\s+", " ", t)
    return t


def load_json(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    if '""' in raw[:40]:
        raw = raw.replace('""', '"')
    return json.loads(raw)


def resolve_category(m: dict) -> str:
    cat = (m.get("category_code") or m.get("category") or "").strip().upper()
    if cat in {"FRONTAL", "ADHESIF", "SILICONE", "GLASSINE", "AUTRE"}:
        return cat
    app = (m.get("appellation_code") or "").strip().upper()
    if app in CATEGORY_CODE_MAP:
        return CATEGORY_CODE_MAP[app]
    if cat in CATEGORY_CODE_MAP:
        return CATEGORY_CODE_MAP[cat]
    if cat in FRONTAL_CODES or cat.startswith("TH"):
        return "FRONTAL"
    if cat in ADHESIF_CODES:
        return "ADHESIF"
    if cat == "S":
        return "SILICONE"
    if cat.startswith("GLS") or cat == "GL":
        return "GLASSINE"
    return "AUTRE"


def resolve_appellation_code(m: dict, name: str) -> str:
    """appellation_code NOT NULL en base — dérive une valeur si l'export Excel l'a omise."""
    app = m.get("appellation_code")
    if app is not None and str(app).strip():
        return str(app).strip()[:64]
    notes = (m.get("notes") or "").strip()
    mo = re.search(r"Code interne:\s*(\S+)", notes, re.I)
    if mo:
        return mo.group(1)[:64]
    cat = (m.get("category_code") or "").strip().upper()
    if cat and len(cat) <= 16:
        slug = re.sub(r"[^\w]+", "-", name.strip(), flags=re.UNICODE).strip("-")
        if slug:
            return f"{cat}-{slug}"[:64]
    return (name.strip() or "N/A")[:64]


def should_skip_material(m: dict) -> bool:
    name = (m.get("name") or "").strip()
    if not name:
        return True
    # Titres de section Excel (ex. « 1 - Frontaux »), pas les codes article (ex. « 1393299 - … »)
    if re.match(r"^\d{1,2}\s*[-–—]\s", name):
        return True
    if re.match(r"^Sans\s+\S+$", name, re.I) and _norm(name) != _norm("Sans silicone"):
        return True
    return False


def detect_imported(m: dict) -> bool:
    if bool(m.get("is_imported")):
        return True
    for key in ("transport_per_m2", "transport_usd_total", "transport_total", "transport_usd_per_kg"):
        v = m.get(key)
        if v is not None:
            try:
                if float(v) > 0:
                    return True
            except (TypeError, ValueError):
                pass
    name = (m.get("name") or "").lower()
    if "chine" in name or "chinois" in name:
        return True
    sup = (m.get("supplier") or m.get("supplier_name") or "").lower()
    if "chine" in sup:
        return True
    return False


def resolve_price_currency(m: dict) -> str:
    if m.get("price_per_kg_usd") is not None:
        try:
            if float(m["price_per_kg_usd"]) > 0:
                return "USD"
        except (TypeError, ValueError):
            pass
    cur = (m.get("price_currency") or "EUR").strip().upper()
    return "USD" if cur == "USD" else "EUR"


def resolve_price_basis(m: dict) -> str:
    basis = (m.get("price_basis") or "").strip().upper()
    if basis in {"PER_KG", "PER_M2"}:
        return basis
    if m.get("price_eur_per_m2") is not None and m.get("unit_price") == m.get("price_eur_per_m2"):
        return "PER_M2"
    return "PER_KG"


def _float(v: Any, default: float = 0.0) -> float:
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _int_or_none(v: Any) -> Optional[int]:
    if v is None or v == "":
        return None
    try:
        return int(round(float(v)))
    except (TypeError, ValueError):
        return None


def ensure_category_ids(conn) -> dict[str, int]:
    rows = conn.execute("SELECT id, code FROM mc_material_category").fetchall()
    return {r["code"]: int(r["id"]) for r in rows}


def upsert_supplier(conn, name: str, dry_run: bool) -> Optional[int]:
    name = name.strip()
    if not name:
        return None
    row = conn.execute(
        "SELECT id FROM mc_supplier WHERE lower(trim(name))=lower(trim(?)) LIMIT 1",
        (name,),
    ).fetchone()
    if row:
        return int(row["id"])
    if dry_run:
        return -1
    cur = conn.execute(
        f"INSERT INTO mc_supplier (name, is_active, created_at, updated_at) VALUES (?,?,{_NOW},{_NOW})",
        (name, 1),
    )
    return int(cur.lastrowid)


def find_material_row(conn, name: str, appellation_code: Optional[str]) -> Optional[Any]:
    app = (appellation_code or "").strip() or None
    if app:
        row = conn.execute(
            """SELECT id FROM mc_material
               WHERE lower(trim(name))=lower(trim(?))
                 AND coalesce(trim(appellation_code),'')=coalesce(trim(?),'')
               LIMIT 1""",
            (name, app),
        ).fetchone()
        if row:
            return row
    return conn.execute(
        "SELECT id FROM mc_material WHERE lower(trim(name))=lower(trim(?)) LIMIT 1",
        (name,),
    ).fetchone()


def upsert_material(conn, payload: dict, dry_run: bool, recap: Recap) -> Optional[int]:
    existing = find_material_row(conn, payload["name"], payload.get("appellation_code"))
    if existing:
        mid = int(existing["id"])
        if dry_run:
            recap.materials_updated += 1
            return mid
        conn.execute(
            """UPDATE mc_material SET
                category_id=?, supplier_id=?, weight_per_m2=?, weight_gsm=?,
                price_currency=?, unit_price=?, price_basis=?, tax_incidence=?,
                is_imported=?, container_kg=?, container_cost_usd=?, is_active=1,
                updated_at=strftime('%Y-%m-%dT%H:%M:%S','now','localtime')
               WHERE id=?""",
            (
                payload["category_id"],
                payload.get("supplier_id"),
                payload["weight_per_m2"],
                payload.get("weight_gsm"),
                payload["price_currency"],
                payload["unit_price"],
                payload["price_basis"],
                payload["tax_incidence"],
                1 if payload["is_imported"] else 0,
                payload.get("container_kg"),
                payload.get("container_cost_usd"),
                mid,
            ),
        )
        recap.materials_updated += 1
        return mid

    if dry_run:
        recap.materials_inserted += 1
        return -1
    cur = conn.execute(
        f"""INSERT INTO mc_material (
            name, appellation_code, category_id, supplier_id, weight_per_m2, weight_gsm,
            price_currency, unit_price, price_basis, tax_incidence, is_imported,
            container_kg, container_cost_usd, is_active, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1,{_NOW},{_NOW})""",
        (
            payload["name"],
            payload.get("appellation_code"),
            payload["category_id"],
            payload.get("supplier_id"),
            payload["weight_per_m2"],
            payload.get("weight_gsm"),
            payload["price_currency"],
            payload["unit_price"],
            payload["price_basis"],
            payload["tax_incidence"],
            1 if payload["is_imported"] else 0,
            payload.get("container_kg"),
            payload.get("container_cost_usd"),
        ),
    )
    recap.materials_inserted += 1
    return int(cur.lastrowid)


class MaterialIndex:
    def __init__(self) -> None:
        self.by_norm_name: dict[str, list[int]] = {}
        self.by_norm_app: dict[str, list[int]] = {}
        self.names: dict[int, str] = {}

    def add(self, mid: int, name: str, app: Optional[str]) -> None:
        self.names[mid] = name
        nk = _norm(name)
        self.by_norm_name.setdefault(nk, []).append(mid)
        if app:
            na = _norm(app)
            self.by_norm_app.setdefault(na, []).append(mid)

    def match(self, ref: Optional[str], conn) -> tuple[Optional[int], str]:
        if not ref or not str(ref).strip():
            return None, ""
        raw = str(ref).strip()
        alias = PRODUCT_REF_ALIASES.get(_norm(raw))
        if alias:
            raw = alias

        nk = _norm(raw)
        if nk in self.by_norm_name:
            ids = self.by_norm_name[nk]
            if len(ids) == 1:
                return ids[0], ""
            return None, f"ambigu nom « {raw} » ({len(ids)} matières)"

        if nk in self.by_norm_app:
            ids = self.by_norm_app[nk]
            if len(ids) == 1:
                return ids[0], ""
            return None, f"ambigu appellation « {raw} »"

        # sous-chaîne appellation dans nom
        candidates: list[int] = []
        for mid, name in self.names.items():
            if nk in _norm(name) or _norm(name) in nk:
                candidates.append(mid)
        if len(candidates) == 1:
            return candidates[0], ""

        # fuzzy
        best_id: Optional[int] = None
        best_score = 0.0
        for mid, name in self.names.items():
            score = SequenceMatcher(None, nk, _norm(name)).ratio()
            if score > best_score:
                best_score = score
                best_id = mid
        if best_id is not None and best_score >= 0.82:
            return best_id, ""

        return None, f"non trouvé « {raw} »"


def upsert_product(
    conn,
    *,
    code: str,
    name: str,
    frontal_id,
    adhesif_id,
    silicone_id,
    glassine_id,
    custom_margin,
    dry_run: bool,
    recap: Recap,
) -> None:
    row = conn.execute(
        "SELECT id FROM mc_product WHERE lower(trim(code))=lower(trim(?)) LIMIT 1",
        (code,),
    ).fetchone()
    if row:
        pid = int(row["id"])
        if dry_run:
            recap.products_updated += 1
            return
        conn.execute(
            """UPDATE mc_product SET name=?, frontal_id=?, adhesif_id=?, silicone_id=?, glassine_id=?,
               custom_margin_eur_m2=?, is_active=1,
               updated_at=strftime('%Y-%m-%dT%H:%M:%S','now','localtime') WHERE id=?""",
            (name, frontal_id, adhesif_id, silicone_id, glassine_id, custom_margin, pid),
        )
        recap.products_updated += 1
        return

    if dry_run:
        recap.products_inserted += 1
        return
    conn.execute(
        f"""INSERT INTO mc_product (
            code, name, frontal_id, adhesif_id, silicone_id, glassine_id,
            custom_margin_eur_m2, is_active, created_at, updated_at
        ) VALUES (?,?,?,?,?,?,?,1,{_NOW},{_NOW})""",
        (code, name, frontal_id, adhesif_id, silicone_id, glassine_id, custom_margin),
    )
    recap.products_inserted += 1


def apply_settings(conn, settings: dict, dry_run: bool) -> None:
    mapping = {
        "eur_usd_rate": settings.get("eur_usd_rate"),
        "default_container_cost_usd": settings.get("default_container_cost_usd")
        or settings.get("container_cost_usd"),
        "default_container_kg": settings.get("default_container_kg") or settings.get("container_kg"),
        "default_margin_eur_m2": settings.get("default_margin_eur_m2"),
    }
    for key, val in mapping.items():
        if val is None:
            continue
        if dry_run:
            continue
        conn.execute(
            """INSERT INTO mc_setting (key, value_decimal, updated_at)
               VALUES (?,?,strftime('%Y-%m-%dT%H:%M:%S','now','localtime'))
               ON CONFLICT(key) DO UPDATE SET value_decimal=excluded.value_decimal, updated_at=excluded.updated_at""",
            (key, float(val)),
        )


def run_seed(json_path: Path, dry_run: bool) -> Recap:
    from database import get_db

    data = load_json(json_path)
    recap = Recap(dry_run=dry_run)

    with get_db() as conn:
        conn.execute("BEGIN")
        try:
            cat_ids = ensure_category_ids(conn)
            apply_settings(conn, data.get("settings") or {}, dry_run)

            supplier_ids: dict[str, int] = {}
            seen_sup: set[str] = set()
            for s in data.get("suppliers") or []:
                sname = (s.get("name") or s.get("supplier") or "").strip()
                if not sname:
                    continue
                nk = _norm(sname)
                if nk in seen_sup:
                    continue
                seen_sup.add(nk)
                sid = upsert_supplier(conn, sname, dry_run)
                if sid is not None:
                    supplier_ids[nk] = sid
                    recap.suppliers_upserted += 1
            for m in data.get("materials") or []:
                sname = (m.get("supplier") or m.get("supplier_name") or "").strip()
                if sname and _norm(sname) not in supplier_ids:
                    nk = _norm(sname)
                    if nk not in seen_sup:
                        seen_sup.add(nk)
                        sid = upsert_supplier(conn, sname, dry_run)
                        if sid is not None:
                            supplier_ids[nk] = sid
                            recap.suppliers_upserted += 1

            index = MaterialIndex()
            pending_index: list[tuple[str, Optional[str]]] = []
            for m in data.get("materials") or []:
                if should_skip_material(m):
                    recap.materials_skipped += 1
                    continue

                name = (m.get("name") or "").strip()
                app = resolve_appellation_code(m, name)

                cat_code = resolve_category(m)
                cat_id = cat_ids.get(cat_code) or cat_ids.get("AUTRE")

                sup_name = (m.get("supplier") or m.get("supplier_name") or "").strip()
                sup_id = supplier_ids.get(_norm(sup_name)) if sup_name else None

                weight_m2 = m.get("weight_per_m2")
                gsm = m.get("weight_gsm")
                if weight_m2 is None and gsm is not None:
                    weight_m2 = float(gsm) / 1000.0
                weight_m2 = _float(weight_m2, 0.0)

                payload = {
                    "name": name,
                    "appellation_code": app,
                    "category_id": cat_id,
                    "supplier_id": sup_id if sup_id and sup_id > 0 else None,
                    "weight_per_m2": weight_m2,
                    "weight_gsm": _int_or_none(gsm),
                    "price_currency": resolve_price_currency(m),
                    "unit_price": _float(m.get("unit_price")),
                    "price_basis": resolve_price_basis(m),
                    "tax_incidence": _float(m.get("tax_incidence"), 1.0),
                    "is_imported": detect_imported(m),
                    "container_kg": m.get("container_kg"),
                    "container_cost_usd": m.get("container_cost_usd"),
                }

                mid = upsert_material(conn, payload, dry_run, recap)
                if mid and mid > 0:
                    index.add(mid, name, app)
                elif dry_run:
                    pending_index.append((name, app))

            if dry_run:
                index = MaterialIndex()
                for row in conn.execute(
                    "SELECT id, name, appellation_code FROM mc_material WHERE is_active=1"
                ).fetchall():
                    index.add(int(row["id"]), row["name"], row["appellation_code"])
                fake_id = -1
                for name, app in pending_index:
                    index.add(fake_id, name, app)
                    fake_id -= 1
            else:
                for row in conn.execute(
                    "SELECT id, name, appellation_code FROM mc_material WHERE is_active=1"
                ).fetchall():
                    if int(row["id"]) not in index.names:
                        index.add(int(row["id"]), row["name"], row["appellation_code"])

            for p in data.get("products") or []:
                code = (p.get("code") or "").strip()
                if not code:
                    recap.warnings.append("Produit sans code ignoré")
                    continue
                pname = (p.get("name") or code).strip()
                unmapped_notes: list[str] = []

                def map_comp(field_json: str, label: str) -> Optional[int]:
                    ref = p.get(field_json)
                    if not ref:
                        return None
                    mid, err = index.match(ref, conn)
                    if err:
                        recap.unmapped.append(f"Produit {code} — {label}: {err}")
                        unmapped_notes.append(f"{label}: {ref}")
                        return None
                    return mid

                frontal_id = map_comp("frontal_name", "frontal")
                adhesif_id = map_comp("adhesif_name", "adhésif")
                silicone_id = map_comp("silicone_name", "silicone")
                glassine_id = map_comp("glassine_name", "glassine")

                if unmapped_notes:
                    pname = f"{pname} [À mapper: {', '.join(unmapped_notes)}]"

                margin = p.get("custom_margin_eur_m2")
                margin_f = float(margin) if margin is not None else None

                upsert_product(
                    conn,
                    code=code,
                    name=pname[:255],
                    frontal_id=frontal_id,
                    adhesif_id=adhesif_id,
                    silicone_id=silicone_id,
                    glassine_id=glassine_id,
                    custom_margin=margin_f,
                    dry_run=dry_run,
                    recap=recap,
                )

            if dry_run:
                conn.rollback()
            else:
                conn.commit()
        except Exception:
            conn.rollback()
            raise

    return recap


def print_recap(recap: Recap, json_path: Path) -> None:
    mode = "DRY-RUN" if recap.dry_run else "IMPORT"
    print(f"\n=== {mode} — {json_path.name} ===")
    print(f"DB: {DB_PATH}")
    print(f"Fournisseurs (upsert): {recap.suppliers_upserted}")
    print(f"Matières insérées:       {recap.materials_inserted}")
    print(f"Matières mises à jour:   {recap.materials_updated}")
    print(f"Matières ignorées:       {recap.materials_skipped}")
    print(f"Produits insérés:        {recap.products_inserted}")
    print(f"Produits mis à jour:     {recap.products_updated}")
    print(f"Composants non mappés:   {len(recap.unmapped)}")
    if recap.unmapped:
        print("\nDétail non mappés / ambigus:")
        for line in recap.unmapped:
            print(f"  · {line}")
    if recap.warnings:
        print("\nAvertissements:")
        for w in recap.warnings:
            print(f"  · {w}")
    if recap.dry_run:
        print("\nAucune écriture en base. Relancez sans --dry-run pour importer.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed mc_* depuis export JSON Excel")
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        help="Chemin JSON (défaut: data/uploads/excel-data-export-fixed.json ou excel-data-export.json)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans écriture")
    args = parser.parse_args()

    if args.json:
        json_path = args.json
    else:
        fixed = ROOT / "data" / "uploads" / "excel-data-export-fixed.json"
        fallback = ROOT / "data" / "uploads" / "excel-data-export.json"
        json_path = fixed if fixed.is_file() else fallback

    if not json_path.is_file():
        print(f"Fichier introuvable: {json_path}", file=sys.stderr)
        sys.exit(1)

    recap = run_seed(json_path, dry_run=args.dry_run)
    print_recap(recap, json_path)


if __name__ == "__main__":
    main()

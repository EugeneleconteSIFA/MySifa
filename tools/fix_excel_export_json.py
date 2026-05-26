#!/usr/bin/env python3
"""Corrige excel-data-export.json et écrit la version dans data/uploads/."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = Path(r"c:\Users\eleconte\Downloads\excel-data-export.json")
OUT = ROOT / "data" / "uploads" / "excel-data-export.json"


def load_source() -> dict:
    raw = SRC.read_text(encoding="utf-8")
    if '""' in raw[:20]:
        raw = raw.replace('""', '"')
    return json.loads(raw)


def merge_suppliers(data: dict) -> None:
    suppliers = data["suppliers"]
    seen: dict[str, dict] = {}
    for s in suppliers:
        key = (s.get("name") or "").strip().lower()
        if key not in seen:
            seen[key] = s
    data["suppliers"] = list(seen.values())
    # Canonique LKn (pas Lkn)
    for s in data["suppliers"]:
        if (s.get("name") or "").lower() == "lkn":
            s["name"] = "LKn"


def fix_materials(data: dict) -> list[str]:
    changes: list[str] = []
    names = {(m.get("name") or "") for m in data["materials"]}

    for m in data["materials"]:
        if (m.get("supplier_name") or "").lower() == "lkn":
            m["supplier_name"] = "LKn"
            changes.append("supplier_name Lkn -> LKn sur matiere")

        if m.get("name") == "Glassine 58 g sil./Itasa KS2 (E)" and m.get("price_basis") == "PER_KG":
            m["price_basis"] = "PER_M2"
            changes.append("Glassine KS2: price_basis PER_KG -> PER_M2")

    if "Sans silicone" not in names:
        data["materials"].append(
            {
                "name": "Sans silicone",
                "appellation_code": None,
                "category": "SILICONE",
                "supplier_name": None,
                "weight_per_m2": 0,
                "weight_gsm": None,
                "price_currency": "EUR",
                "unit_price": 0,
                "price_basis": "PER_M2",
                "tax_incidence": 1,
                "is_imported": False,
                "container_kg": None,
                "container_cost_usd": None,
                "is_active": True,
                "notes": "Matière virtuelle — pas de couche silicone",
            }
        )
        changes.append("Ajout matiere virtuelle Sans silicone")

    # Alias glassine chinois courte → LK
    alias = "Glassine 58 g chinois"
    target = "Glassine 58 g chinois LK"
    if target in names and alias not in names:
        for m in data["materials"]:
            if m.get("name") == target:
                clone = dict(m)
                clone["name"] = alias
                clone["notes"] = (clone.get("notes") or "") + " (alias export)"
                data["materials"].append(clone)
                changes.append(f"Alias matiere {alias} (meme prix que LK)")
                break

    return changes


PRODUCT_REF_MAP = {
    "sans silicone": "Sans silicone",
    "Sans Silicone": "Sans silicone",
    "Glassine 58 g chinois": "Glassine 58 g chinois LK",
    "Jet d'encre": "1393299 - papier jet d'encre mat 70g",
}


def _find_material(data: dict, name: str) -> dict | None:
    for m in data["materials"]:
        if m.get("name") == name:
            return m
    return None


def _clone_material(template: dict, name: str, **overrides) -> dict:
    m = dict(template)
    m.update(overrides)
    m["name"] = name
    notes = overrides.get("notes") or m.get("notes") or ""
    m["notes"] = (notes + " — ajout correction export").strip(" —")
    return m


def add_missing_materials(data: dict) -> list[str]:
    changes: list[str] = []
    names = {m.get("name") for m in data["materials"]}
    to_add: list[dict] = []

    if "2021/19" not in names:
        t = _find_material(data, "2028Y/19")
        if t:
            to_add.append(
                _clone_material(
                    t,
                    "2021/19",
                    appellation_code="2021",
                    notes="Code interne: 2021",
                )
            )
            changes.append("Ajout adhésif 2021/19 (clone 2028Y/19)")

    if "2021/20" not in names:
        t = _find_material(data, "2028Y/22")
        if t:
            to_add.append(
                _clone_material(
                    t,
                    "2021/20",
                    appellation_code="2021",
                    notes="Code interne: 2021",
                )
            )
            changes.append("Ajout adhésif 2021/20 (clone 2028Y/22)")

    if "Foliset 100 µ" not in names:
        t = _find_material(data, "Foliset 120 µ")
        if t:
            price = round(float(t["unit_price"]) * 100 / 120, 4)
            to_add.append(
                _clone_material(
                    t,
                    "Foliset 100 µ",
                    appellation_code="100",
                    unit_price=price,
                    notes="Code interne: 100",
                )
            )
            changes.append("Ajout frontal Foliset 100 µ (dérivé 120 µ)")

    if "Thermique protégé KLRB 46B bicolore" not in names:
        t = _find_material(data, "Thermique protégé 105 g")
        if t:
            to_add.append(
                _clone_material(
                    t,
                    "Thermique protégé KLRB 46B bicolore",
                    appellation_code="46B",
                    unit_price=0.06,
                    notes="Prix estimé export — à valider",
                )
            )
            changes.append("Ajout frontal KLRB 46B (prix estimé)")

    if "Glassine 60 g siliconée /MONDI" not in names:
        t = _find_material(data, "Glassine 58 g sil./Itasa Prix en Baisse")
        if t:
            to_add.append(
                _clone_material(
                    t,
                    "Glassine 60 g siliconée /MONDI",
                    weight_gsm=60,
                    unit_price=0.16,
                    supplier_name=None,
                    notes="Prix estimé export — à valider",
                )
            )
            changes.append("Ajout glassine MONDI 60 g (prix estimé)")

    data["materials"].extend(to_add)
    return changes


def fix_products(data: dict, material_names: set[str]) -> list[str]:
    changes: list[str] = []
    for p in data["products"]:
        for field in ("frontal_name", "adhesif_name", "silicone_name", "glassine_name"):
            val = p.get(field)
            if not val:
                continue
            mapped = PRODUCT_REF_MAP.get(val, val)
            if mapped != val:
                p[field] = mapped
                changes.append(f"Produit {p.get('code')}: {field} {val!r} -> {mapped!r}")

        # adhesif_name = code adhésif → nom matière si le code existe tel quel
        an = p.get("adhesif_name")
        if an and an not in material_names and "/" in an:
            if an in material_names:
                pass
            elif re.match(r"^\d{4}/\d{2}$", an):
                # ex. 2021/19 — chercher variante Y
                prefix = an.split("/")[0]
                candidates = [n for n in material_names if n.startswith(prefix)]
                if len(candidates) == 1:
                    p["adhesif_name"] = candidates[0]
                    changes.append(f"Produit {p.get('code')}: adhesif {an} → {candidates[0]}")

    return changes


def add_product_ids(data: dict) -> None:
    """Clé stable pour import : code + hash court du name."""
    for i, p in enumerate(data["products"]):
        base = p.get("code") or "?"
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", (p.get("name") or str(i)))[:40].strip("-")
        p["import_id"] = f"{base}-{slug}" if slug else f"{base}-{i}"


def main() -> None:
    data = load_source()
    log: list[str] = []

    merge_suppliers(data)
    log.append("Fournisseurs fusionnés (doublon LKn/Lkn)")

    log.extend(fix_materials(data))
    log.extend(add_missing_materials(data))
    material_names = {m.get("name") for m in data["materials"]}
    log.extend(fix_products(data, material_names))
    add_product_ids(data)

    meta = data.setdefault("_meta", {})
    meta["corrected_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seen_corr: set[str] = set()
    unique_log = []
    for item in ["JSON: guillemets doubles échappés corrigés", *log]:
        if item not in seen_corr:
            seen_corr.add(item)
            unique_log.append(item)
    meta["corrections"] = unique_log

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # validation
    json.loads(OUT.read_text(encoding="utf-8"))
    print(f"OK -> {OUT}")
    print(f"  suppliers: {len(data['suppliers'])}")
    print(f"  materials: {len(data['materials'])}")
    print(f"  products:  {len(data['products'])}")
    for line in log:
        print(f"  · {line}")


if __name__ == "__main__":
    main()

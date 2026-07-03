"""Accès SQLite — module coûts matières (mc_*)."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from app.models.material_cost import MC_SETTING_DEFAULTS, MC_SETTING_KEYS
from app.services.pricing.errors import PricingError
from app.services.pricing.types import PricingMaterial, PricingProduct, PricingSettings

_NOW_SQL = "strftime('%Y-%m-%dT%H:%M:%S','now','localtime')"


def _dec(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _bool(v: Any) -> bool:
    return bool(v) if v is not None else False


def ensure_settings_rows(conn: sqlite3.Connection) -> None:
    for key, val in MC_SETTING_DEFAULTS.items():
        conn.execute(
            "INSERT OR IGNORE INTO mc_setting (key, value_decimal) VALUES (?,?)",
            (key, float(val)),
        )


def load_pricing_settings(conn: sqlite3.Connection) -> PricingSettings:
    ensure_settings_rows(conn)
    # Construction dynamique des placeholders (MC_SETTING_KEYS peut évoluer).
    keys = tuple(MC_SETTING_KEYS)
    placeholders = ",".join("?" for _ in keys)
    rows = conn.execute(
        f"SELECT key, value_decimal FROM mc_setting WHERE key IN ({placeholders})",
        keys,
    ).fetchall()
    data = {r["key"]: _dec(r["value_decimal"]) for r in rows}
    # Clés optionnelles (default 0 si absentes) — pas bloquantes pour le calcul pricing.
    optional = {
        "import_tax_pct",
        "transport_cost_fixed_eur",
        "charge_production_pct",
        "storage_fees_pct",
        "default_half_container_cost_eur",
        "logistique_qte_m2_container_complet",
        "logistique_qte_m2_demi_container",
    }
    required = {k for k in MC_SETTING_KEYS if k not in optional}
    missing = [k for k in required if k not in data]
    if missing:
        raise PricingError(f"Paramètres incomplets en base : {', '.join(missing)}.")
    return PricingSettings(
        eur_usd_rate=data["eur_usd_rate"],
        default_container_cost_usd=data["default_container_cost_usd"],
        default_container_kg=data["default_container_kg"],
        default_margin_eur_m2=data["default_margin_eur_m2"],
        import_tax_pct=data.get("import_tax_pct", Decimal("0")),
        transport_cost_fixed_eur=data.get("transport_cost_fixed_eur", Decimal("0")),
        charge_production_pct=data.get("charge_production_pct", Decimal("0")),
        storage_fees_pct=data.get("storage_fees_pct", Decimal("0")),
        default_half_container_cost_eur=data.get("default_half_container_cost_eur", Decimal("0")),
        logistique_qte_m2_container_complet=data.get("logistique_qte_m2_container_complet", Decimal("0")),
        logistique_qte_m2_demi_container=data.get("logistique_qte_m2_demi_container", Decimal("0")),
    )


def load_settings_response(conn: sqlite3.Connection) -> dict[str, Any]:
    ensure_settings_rows(conn)
    rows = conn.execute(
        "SELECT key, value_decimal, updated_at, source FROM mc_setting"
    ).fetchall()
    by_key = {r["key"]: r for r in rows}
    out: dict[str, Any] = {}
    for key in MC_SETTING_KEYS:
        row = by_key.get(key)
        if row:
            out[key] = float(row["value_decimal"])
    fx = by_key.get("eur_usd_rate")
    out["eur_usd_rate_updated_at"] = fx["updated_at"] if fx else None
    out["eur_usd_rate_source"] = fx["source"] if fx else None
    return out


def update_settings(
    conn: sqlite3.Connection,
    *,
    patch: dict[str, Decimal],
    updated_by: Optional[int] = None,
    source: Optional[str] = None,
) -> dict[str, Any]:
    # Garantit que toutes les lignes existent (les nouvelles clés ajoutées après
    # coup — ex. charge_production_pct — ne sont sinon jamais créées et l'UPDATE
    # ci-dessous n'affecterait aucune ligne, avec valeur perdue au retour.
    ensure_settings_rows(conn)
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    for key, val in patch.items():
        if key not in MC_SETTING_KEYS:
            continue
        src = source if key == "eur_usd_rate" and source else None
        conn.execute(
            f"""UPDATE mc_setting SET value_decimal=?, updated_at=?, updated_by=?, source=?
                WHERE key=?""",
            (float(val), now, updated_by, src, key),
        )
    conn.commit()
    return load_settings_response(conn)


def row_to_pricing_material(row: sqlite3.Row) -> PricingMaterial:
    return PricingMaterial(
        id=int(row["id"]),
        name=row["name"],
        unit_price=_dec(row["unit_price"]),
        weight_per_m2=_dec(row["weight_per_m2"]),
        price_currency=row["price_currency"],
        price_basis=row["price_basis"],
        tax_incidence=_dec(row["tax_incidence"]),
        is_imported=_bool(row["is_imported"]),
        container_kg=_dec(row["container_kg"]) if row["container_kg"] is not None else None,
        container_cost_usd=_dec(row["container_cost_usd"])
        if row["container_cost_usd"] is not None
        else None,
    )


def material_row_to_dict(row: sqlite3.Row, *, category_code: str) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "appellation_code": row["appellation_code"],
        "category_id": row["category_id"],
        "category_code": category_code,
        "supplier_id": row["supplier_id"],
        "weight_per_m2": float(row["weight_per_m2"]),
        "weight_gsm": row["weight_gsm"],
        "price_currency": row["price_currency"],
        "unit_price": float(row["unit_price"]),
        "price_basis": row["price_basis"],
        "tax_incidence": float(row["tax_incidence"]),
        "is_imported": _bool(row["is_imported"]),
        "container_kg": float(row["container_kg"]) if row["container_kg"] is not None else None,
        "container_cost_usd": float(row["container_cost_usd"])
        if row["container_cost_usd"] is not None
        else None,
        "is_active": _bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_category_id_by_code(conn: sqlite3.Connection, code: str) -> Optional[int]:
    row = conn.execute(
        "SELECT id FROM mc_material_category WHERE code=? LIMIT 1", (code,)
    ).fetchone()
    return int(row["id"]) if row else None


def get_category_map(conn: sqlite3.Connection) -> dict[int, str]:
    rows = conn.execute("SELECT id, code FROM mc_material_category").fetchall()
    return {int(r["id"]): r["code"] for r in rows}


def fetch_material(conn: sqlite3.Connection, material_id: int, *, active_only: bool = False) -> Optional[sqlite3.Row]:
    sql = """
        SELECT m.*, c.code AS category_code
        FROM mc_material m
        JOIN mc_material_category c ON c.id = m.category_id
        WHERE m.id=?
    """
    if active_only:
        sql += " AND m.is_active=1"
    return conn.execute(sql, (material_id,)).fetchone()


def fetch_materials_map(
    conn: sqlite3.Connection, ids: set[int], *, require_active: bool = False
) -> dict[int, PricingMaterial]:
    if not ids:
        return {}
    placeholders = ",".join("?" * len(ids))
    sql = f"SELECT * FROM mc_material WHERE id IN ({placeholders})"
    if require_active:
        sql += " AND is_active=1"
    rows = conn.execute(sql, list(ids)).fetchall()
    found = {int(r["id"]): row_to_pricing_material(r) for r in rows}
    if require_active and len(found) != len(ids):
        missing = ids - set(found.keys())
        raise PricingError(f"Matière(s) inactive(s) ou introuvable(s) : {sorted(missing)}.")
    return found


def assert_materials_active_for_product(conn: sqlite3.Connection, mat_ids: list[Optional[int]]) -> None:
    ids = {int(i) for i in mat_ids if i is not None}
    if not ids:
        return
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT id, is_active FROM mc_material WHERE id IN ({placeholders})",
        list(ids),
    ).fetchall()
    by_id = {int(r["id"]): _bool(r["is_active"]) for r in rows}
    for mid in ids:
        if mid not in by_id:
            raise PricingError(f"Matière introuvable (id={mid}).")
        if not by_id[mid]:
            raise PricingError(f"Matière inactive (id={mid}) — calcul impossible.")


def load_product_extra_ids(conn: sqlite3.Connection, product_id: int) -> list[int]:
    rows = conn.execute(
        """SELECT material_id FROM mc_product_extra_material
           WHERE product_id=? ORDER BY sort_order, material_id""",
        (product_id,),
    ).fetchall()
    return [int(r["material_id"]) for r in rows]


def set_product_extras(conn: sqlite3.Connection, product_id: int, material_ids: list[int]) -> None:
    conn.execute("DELETE FROM mc_product_extra_material WHERE product_id=?", (product_id,))
    for i, mid in enumerate(material_ids):
        conn.execute(
            """INSERT INTO mc_product_extra_material (product_id, material_id, sort_order)
               VALUES (?,?,?)""",
            (product_id, mid, i),
        )


def insert_price_history(
    conn: sqlite3.Connection,
    *,
    material_id: int,
    unit_price: Decimal,
    price_currency: str,
    tax_incidence: Decimal,
    effective_date: str,
    source: Optional[str],
    created_by: Optional[int],
) -> None:
    conn.execute(
        """INSERT INTO mc_material_price_history
           (material_id, unit_price, price_currency, tax_incidence, effective_date, source, created_by)
           VALUES (?,?,?,?,?,?,?)""",
        (
            material_id,
            float(unit_price),
            price_currency,
            float(tax_incidence),
            effective_date,
            source,
            created_by,
        ),
    )


def product_row_to_pricing_product(row: sqlite3.Row, extra_ids: list[int]) -> PricingProduct:
    return PricingProduct(
        id=int(row["id"]),
        code=row["code"],
        name=row["name"],
        frontal_id=row["frontal_id"],
        adhesif_id=row["adhesif_id"],
        silicone_id=row["silicone_id"],
        glassine_id=row["glassine_id"],
        extra_material_ids=tuple(extra_ids),
        custom_margin_eur_m2=_dec(row["custom_margin_eur_m2"])
        if row["custom_margin_eur_m2"] is not None
        else None,
    )

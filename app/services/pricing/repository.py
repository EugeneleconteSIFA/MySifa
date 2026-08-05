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


def _bool_defaut_vrai(v: Any) -> bool:
    """Colonne absente ou NULL = vrai : la marge s'applique sauf mention contraire."""
    return True if v is None else bool(v)


def _col(row: sqlite3.Row, name: str, default: Any = None) -> Any:
    """Lecture tolérante d'une colonne : None si absente du SELECT (compat migrations)."""
    try:
        return row[name]
    except (IndexError, KeyError):
        return default


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
        "default_margin_eur_m2",
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
        default_margin_pct=data["default_margin_pct"],
        default_margin_eur_m2=data.get("default_margin_eur_m2", Decimal("0")),
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


def row_to_pricing_material(
    row: sqlite3.Row, *, mystock: Optional[dict[str, Any]] = None
) -> PricingMaterial:
    """`mystock` (issu de mystock_price_for_row) prend le pas sur le prix local."""
    return PricingMaterial(
        id=int(row["id"]),
        name=row["name"],
        unit_price=_dec(mystock["unit_price"]) if mystock else _dec(row["unit_price"]),
        weight_per_m2=_dec(row["weight_per_m2"]),
        price_currency=mystock["price_currency"] if mystock else row["price_currency"],
        price_basis=mystock["price_basis"] if mystock else row["price_basis"],
        taxe_pct=_dec(_col(row, "taxe_pct")),
        is_imported=_bool(row["is_imported"]),
        applique_marge=_bool_defaut_vrai(_col(row, "applique_marge")),
        transport_mode=(_col(row, "transport_mode") or "AMOUNT"),
        transport_unit_price=_dec(_col(row, "transport_unit_price")),
        transport_pct=_dec(_col(row, "transport_pct")),
        container_kg=_dec(row["container_kg"]) if row["container_kg"] is not None else None,
        container_cost_usd=_dec(row["container_cost_usd"])
        if row["container_cost_usd"] is not None
        else None,
    )


def material_row_to_dict(
    row: sqlite3.Row, *, category_code: str, mystock: Optional[dict[str, Any]] = None
) -> dict[str, Any]:
    return {
        "mystock": {
            "matiere_id": mystock["matiere_id"],
            "declinaison_id": mystock["declinaison_id"],
            "reference": mystock["reference"],
            "categorie": mystock["categorie"],
            "unit_price": float(mystock["unit_price"]),
            "price_currency": mystock["price_currency"],
            "price_basis": mystock["price_basis"],
            "detail": mystock["detail"],
        }
        if mystock
        else None,
        "id": row["id"],
        "name": row["name"],
        "appellation_code": row["appellation_code"],
        "category_id": row["category_id"],
        "category_code": category_code,
        "supplier_id": row["supplier_id"],
        "fournisseur_fsc_id": _col(row, "fournisseur_fsc_id"),
        "fournisseur_nom": _col(row, "fournisseur_nom"),
        "weight_per_m2": float(row["weight_per_m2"]),
        "weight_gsm": row["weight_gsm"],
        "grammage_gsm": float(_col(row, "grammage_gsm") or 0),
        "perte_pct": float(_col(row, "perte_pct") or 0),
        "price_currency": row["price_currency"],
        "unit_price": float(row["unit_price"]),
        "price_basis": row["price_basis"],
        "taxe_pct": float(_col(row, "taxe_pct") or 0),
        "is_imported": _bool(row["is_imported"]),
        "applique_marge": _bool_defaut_vrai(_col(row, "applique_marge")),
        "transport_mode": _col(row, "transport_mode") or "AMOUNT",
        "transport_unit_price": float(_col(row, "transport_unit_price") or 0),
        "transport_pct": float(_col(row, "transport_pct") or 0),
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


# Colonnes MyStock jointes à toute lecture de matière : quand une matière est
# appairée, c'est SON prix qui fait foi (choix produit — une seule valeur, rangée
# côté MyStock). Voir mystock_price_for_row ci-dessous.
# Une matière Coûts matières est pilotée par la DÉCLINAISON MyStock qui lui est
# appairée (une laize d'un frontal, un grammage d'un adhésif…). Le prix retenu
# est celui de son fournisseur principal.
MYSTOCK_JOIN = """
    LEFT JOIN mp_matiere_declinaison msd ON msd.mc_material_id = m.id
    LEFT JOIN matieres_premieres mp      ON mp.id = msd.matiere_id
    LEFT JOIN mp_laizes msl              ON msl.id = msd.laize_id
    LEFT JOIN mp_grammages msg           ON msg.id = msd.grammage_id
"""
MYSTOCK_COLS = """
    msd.id                         AS ms_decl_id,
    mp.id                          AS ms_id,
    mp.categorie                   AS ms_categorie,
    mp.reference                   AS ms_reference,
    msl.valeur_mm                  AS ms_laize_mm,
    msl.label                      AS ms_laize_label,
    msg.valeur_gsm                 AS ms_gsm
"""

_MS_LAIZEES = frozenset({"frontal", "glassine", "complexe"})


def mystock_price_for_row(conn: sqlite3.Connection, row: sqlite3.Row) -> Optional[dict[str, Any]]:
    """
    Prix MyStock d'une matière appairée, exprimé dans l'unité du moteur de calcul.
    Retourne None si aucune déclinaison n'est appairée ou si son fournisseur
    principal n'a pas de prix.
    """
    decl_id = _col(row, "ms_decl_id")
    if decl_id is None:
        return None
    prix_row = conn.execute(
        "SELECT prix FROM mp_matiere_prix WHERE declinaison_id=? AND principal=1 LIMIT 1",
        (int(decl_id),),
    ).fetchone()
    if not prix_row:
        return None
    try:
        prix = float(prix_row["prix"] or 0)
    except (TypeError, ValueError):
        return None
    if prix <= 0:
        return None
    cat = (_col(row, "ms_categorie") or "").strip().lower()
    laizee = cat in _MS_LAIZEES
    if _col(row, "ms_laize_mm") is not None:
        detail = _col(row, "ms_laize_label") or f"laize {int(float(_col(row, 'ms_laize_mm')))} mm"
    elif _col(row, "ms_gsm") is not None:
        detail = f"grammage {float(_col(row, 'ms_gsm')):g} g/m²"
    else:
        detail = None
    return {
        "matiere_id": int(_col(row, "ms_id")),
        "declinaison_id": int(decl_id),
        "reference": _col(row, "ms_reference"),
        "categorie": _col(row, "ms_categorie"),
        "unit_price": Decimal(str(round(prix, 6))),
        "price_currency": "EUR",
        "price_basis": "PER_M2" if laizee else "PER_KG",
        "detail": detail,
    }


def declinaison_to_pricing_material(param: dict) -> PricingMaterial:
    """
    Une déclinaison MyStock paramétrée, vue par le moteur de calcul.

    Le prix vient du fournisseur principal, les réglages de la déclinaison
    elle-même : plus besoin d'une fiche mc_material pour deviser une matière.
    """
    return PricingMaterial(
        id=int(param["declinaison_id"]),
        # « Toutes déclinaisons » n'apprend rien : sur une matière qui ne se
        # décline pas, le nom se limite à sa référence.
        name=(
            f'{param["reference"]} — {param["libelle"]}'
            if param.get("libelle") and param["libelle"] != "Toutes déclinaisons"
            else str(param["reference"])
        ),
        unit_price=_dec(param.get("unit_price")),
        weight_per_m2=_dec(param.get("weight_per_m2")),
        price_currency=param.get("price_currency") or "EUR",
        price_basis=param.get("price_basis") or "PER_KG",
        taxe_pct=_dec(param.get("taxe_pct")),
        is_imported=bool(param.get("is_imported")),
        applique_marge=_bool_defaut_vrai(param.get("applique_marge")),
        transport_mode=param.get("transport_mode") or "AMOUNT",
        transport_unit_price=_dec(param.get("transport_unit_price")),
        transport_pct=_dec(param.get("transport_pct")),
    )


def fetch_material(conn: sqlite3.Connection, material_id: int, *, active_only: bool = False) -> Optional[sqlite3.Row]:
    sql = f"""
        SELECT m.*, c.code AS category_code, f.nom AS fournisseur_nom, {MYSTOCK_COLS}
        FROM mc_material m
        JOIN mc_material_category c ON c.id = m.category_id
        LEFT JOIN fournisseurs_fsc f ON f.id = m.fournisseur_fsc_id
        {MYSTOCK_JOIN}
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
    sql = f"""SELECT m.*, {MYSTOCK_COLS}
                FROM mc_material m {MYSTOCK_JOIN}
               WHERE m.id IN ({placeholders})"""
    if require_active:
        sql += " AND m.is_active=1"
    rows = conn.execute(sql, list(ids)).fetchall()
    found = {
        int(r["id"]): row_to_pricing_material(r, mystock=mystock_price_for_row(conn, r))
        for r in rows
    }
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
    taxe_pct: Decimal,
    effective_date: str,
    source: Optional[str],
    created_by: Optional[int],
) -> None:
    conn.execute(
        """INSERT INTO mc_material_price_history
           -- La colonne s'appelle encore tax_incidence : elle porte désormais un
           -- POURCENTAGE (6 = +6 %), pas un multiplicateur.
           (material_id, unit_price, price_currency, tax_incidence, effective_date, source, created_by)
           VALUES (?,?,?,?,?,?,?)""",
        (
            material_id,
            float(unit_price),
            price_currency,
            float(taxe_pct),
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
        custom_margin_pct=_dec(_col(row, "custom_margin_pct"))
        if _col(row, "custom_margin_pct") is not None
        else None,
    )

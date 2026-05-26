"""MySifa — API Calcul des coûts matières (/api/pricing)."""

from __future__ import annotations

import io
import re
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from config import ROLES_ADMIN
from database import get_db
from app.services.auth_service import get_current_user
from app.services.pricing import (
    PricingError,
    compute_material_price_per_m2,
    compute_product_cost,
)
from app.services.pricing.repository import (
    assert_materials_active_for_product,
    ensure_settings_rows,
    fetch_material,
    fetch_materials_map,
    insert_price_history,
    load_pricing_settings,
    load_product_extra_ids,
    load_settings_response,
    material_row_to_dict,
    product_row_to_pricing_product,
    row_to_pricing_material,
    set_product_extras,
    update_settings,
)
from app.services.pricing.schemas import (
    MaterialBreakdownOut,
    MaterialComputedOut,
    MaterialPreviewIn,
    McMaterialCategoryOut,
    McMaterialCreate,
    McMaterialOut,
    McMaterialPriceHistoryOut,
    McMaterialUpdate,
    McProductCreate,
    McProductOut,
    McProductUpdate,
    McSupplierCreate,
    McSupplierOut,
    McSupplierUpdate,
    PricingDashboardOut,
    PricingDashboardProductRow,
    PricingFxRefreshOut,
    PricingSettingsOut,
    PricingSettingsPatch,
    ProductComponentOut,
    ProductCostOut,
    ProductPreviewIn,
)
from app.services.pricing.export_pdf import build_product_pdf
from app.services.pricing.export_xlsx import build_products_workbook
from app.services.pricing.types import PricingProduct

router = APIRouter(tags=["pricing"])

_FX_API_URL = "https://api.exchangerate.host/latest"
_FX_SOURCE = "exchangerate.host"


def _require_read(request: Request) -> dict:
    return get_current_user(request)


def _require_write(request: Request) -> dict:
    user = get_current_user(request)
    if user.get("role") not in ROLES_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Écriture réservée à la Direction et l'Administration.",
        )
    return user


def _pricing_error(exc: PricingError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


def _computed_out(mat_row, settings) -> MaterialComputedOut:
    pm = row_to_pricing_material(mat_row)
    try:
        res = compute_material_price_per_m2(pm, settings)
    except PricingError as e:
        raise _pricing_error(e) from e
    b = res.breakdown
    return MaterialComputedOut(
        price_eur_per_m2=res.price_eur_per_m2,
        breakdown=MaterialBreakdownOut(
            raw=b.raw,
            transport=b.transport,
            fx=b.fx,
            tax_uplift=b.tax_uplift,
        ),
    )


def _material_out(row, *, settings=None, with_computed: bool = False) -> McMaterialOut:
    d = material_row_to_dict(row, category_code=row["category_code"])
    computed = _computed_out(row, settings) if with_computed and settings else None
    return McMaterialOut(**d, computed=computed)


def _collect_product_material_ids(
    frontal_id, adhesif_id, silicone_id, glassine_id, extra_ids
) -> set[int]:
    ids: set[int] = set()
    for x in (frontal_id, adhesif_id, silicone_id, glassine_id):
        if x is not None:
            ids.add(int(x))
    ids.update(int(i) for i in (extra_ids or []))
    return ids


def _build_product_cost(conn, row, extra_ids: list[int], settings) -> ProductCostOut:
    assert_materials_active_for_product(
        conn,
        [row["frontal_id"], row["adhesif_id"], row["silicone_id"], row["glassine_id"], *extra_ids],
    )
    product = product_row_to_pricing_product(row, extra_ids)
    mat_ids = _collect_product_material_ids(
        product.frontal_id,
        product.adhesif_id,
        product.silicone_id,
        product.glassine_id,
        list(product.extra_material_ids),
    )
    mats = fetch_materials_map(conn, mat_ids, require_active=True)
    try:
        result = compute_product_cost(product, mats, settings)
    except PricingError as e:
        raise _pricing_error(e) from e

    components: list[ProductComponentOut] = []
    for c in result.components:
        breakdown = None
        pm = mats.get(c.material_id)
        if pm:
            comp = compute_material_price_per_m2(pm, settings)
            b = comp.breakdown
            breakdown = MaterialBreakdownOut(
                raw=b.raw, transport=b.transport, fx=b.fx, tax_uplift=b.tax_uplift
            )
        components.append(
            ProductComponentOut(
                material_id=c.material_id,
                name=c.name,
                role=c.role,
                price_eur_per_m2=c.price_eur_per_m2,
                share_pct=c.share_pct,
                breakdown=breakdown,
            )
        )
    return ProductCostOut(
        total_eur_per_m2=result.total_eur_per_m2,
        margin_eur_m2=result.margin_eur_m2,
        sell_price_eur_m2=result.sell_price_eur_m2,
        components=components,
    )


def _product_out(conn, row, *, with_cost: bool = False) -> McProductOut:
    extra_ids = load_product_extra_ids(conn, int(row["id"]))
    settings = load_pricing_settings(conn) if with_cost else None
    cost = _build_product_cost(conn, row, extra_ids, settings) if with_cost and settings else None
    return McProductOut(
        id=row["id"],
        code=row["code"],
        name=row["name"],
        frontal_id=row["frontal_id"],
        adhesif_id=row["adhesif_id"],
        silicone_id=row["silicone_id"],
        glassine_id=row["glassine_id"],
        extra_material_ids=extra_ids,
        custom_margin_eur_m2=float(row["custom_margin_eur_m2"])
        if row["custom_margin_eur_m2"] is not None
        else None,
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        cost=cost,
    )


def _parse_product_ids_param(ids: Optional[str]) -> list[int]:
    if not ids or not str(ids).strip():
        return []
    out: list[int] = []
    for part in re.split(r"[,;\s]+", str(ids).strip()):
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Identifiant produit invalide : {part}")
    return out


def _load_materials_export_map(conn, material_ids: set[int], settings) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for mid in material_ids:
        row = fetch_material(conn, mid)
        if not row:
            continue
        m = _material_out(row, settings=settings, with_computed=True)
        out[mid] = m.model_dump()
    return out


def _load_products_export_payload(
    conn, product_ids: list[int]
) -> tuple[list[dict[str, Any]], dict[int, dict]]:
    if not product_ids:
        return [], {}
    settings = load_pricing_settings(conn)
    placeholders = ",".join("?" * len(product_ids))
    rows = conn.execute(
        f"SELECT * FROM mc_product WHERE id IN ({placeholders}) ORDER BY code COLLATE NOCASE",
        product_ids,
    ).fetchall()
    if not rows:
        return [], {}

    products: list[dict[str, Any]] = []
    mat_ids: set[int] = set()
    for row in rows:
        extra = load_product_extra_ids(conn, int(row["id"]))
        try:
            pout = _product_out(conn, row, with_cost=True)
        except PricingError as e:
            raise _pricing_error(e) from e
        pd = pout.model_dump()
        products.append(pd)
        for key in ("frontal_id", "adhesif_id", "silicone_id", "glassine_id"):
            if pd.get(key):
                mat_ids.add(int(pd[key]))
        for mid in pd.get("extra_material_ids") or []:
            mat_ids.add(int(mid))

    materials_map = _load_materials_export_map(conn, mat_ids, settings)
    return products, materials_map


# ─── Dashboard & référentiels ────────────────────────────────────────────────


@router.get("/api/pricing/categories")
def list_material_categories(request: Request):
    _require_read(request)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id, code, label, sort_order FROM mc_material_category ORDER BY sort_order"
        ).fetchall()
    return {
        "categories": [
            McMaterialCategoryOut(
                id=r["id"], code=r["code"], label=r["label"], sort_order=r["sort_order"]
            )
            for r in rows
        ]
    }


@router.get("/api/pricing/dashboard", response_model=PricingDashboardOut)
def pricing_dashboard(request: Request):
    _require_read(request)
    with get_db() as conn:
        n_mat = conn.execute(
            "SELECT COUNT(*) AS c FROM mc_material WHERE is_active=1"
        ).fetchone()["c"]
        n_prod = conn.execute(
            "SELECT COUNT(*) AS c FROM mc_product WHERE is_active=1"
        ).fetchone()["c"]
        settings_data = load_settings_response(conn)
        settings = load_pricing_settings(conn)
        rows = conn.execute("SELECT * FROM mc_product WHERE is_active=1").fetchall()
        ranked: list[tuple[Decimal, PricingDashboardProductRow]] = []
        sell_sum = Decimal("0")
        sell_n = 0
        for row in rows:
            try:
                extra = load_product_extra_ids(conn, int(row["id"]))
                cost = _build_product_cost(conn, row, extra, settings)
            except HTTPException:
                continue
            sell_sum += cost.sell_price_eur_m2
            sell_n += 1
            ranked.append(
                (
                    cost.total_eur_per_m2,
                    PricingDashboardProductRow(
                        id=row["id"],
                        code=row["code"],
                        name=row["name"],
                        total_eur_per_m2=cost.total_eur_per_m2,
                        sell_price_eur_per_m2=cost.sell_price_eur_m2,
                    ),
                )
            )
        ranked.sort(key=lambda x: x[0], reverse=True)
        top = [r[1] for r in ranked[:10]]
        avg_sell = (sell_sum / sell_n).quantize(Decimal("0.0001")) if sell_n else None
    return PricingDashboardOut(
        materials_active=int(n_mat),
        products_active=int(n_prod),
        eur_usd_rate=Decimal(str(settings_data["eur_usd_rate"])),
        eur_usd_rate_updated_at=settings_data.get("eur_usd_rate_updated_at"),
        eur_usd_rate_source=settings_data.get("eur_usd_rate_source"),
        avg_sell_price_eur_m2=avg_sell,
        top_products=top,
    )


@router.post("/api/pricing/materials/preview", response_model=MaterialComputedOut)
def preview_material_price(request: Request, body: MaterialPreviewIn):
    _require_read(request)
    with get_db() as conn:
        settings = load_pricing_settings(conn)
    from app.services.pricing.types import PricingMaterial

    pm = PricingMaterial(
        id=0,
        name="preview",
        unit_price=body.unit_price,
        weight_per_m2=body.weight_per_m2,
        price_currency=body.price_currency,
        price_basis=body.price_basis,
        tax_incidence=body.tax_incidence,
        is_imported=body.is_imported,
        container_kg=body.container_kg,
        container_cost_usd=body.container_cost_usd,
    )
    try:
        res = compute_material_price_per_m2(pm, settings)
    except PricingError as e:
        raise _pricing_error(e) from e
    b = res.breakdown
    return MaterialComputedOut(
        price_eur_per_m2=res.price_eur_per_m2,
        breakdown=MaterialBreakdownOut(
            raw=b.raw, transport=b.transport, fx=b.fx, tax_uplift=b.tax_uplift
        ),
    )


# ─── Settings ────────────────────────────────────────────────────────────────


@router.get("/api/pricing/settings", response_model=PricingSettingsOut)
def get_pricing_settings(request: Request):
    _require_read(request)
    with get_db() as conn:
        data = load_settings_response(conn)
    return PricingSettingsOut(**data)


@router.patch("/api/pricing/settings", response_model=PricingSettingsOut)
def patch_pricing_settings(request: Request, body: PricingSettingsPatch):
    user = _require_write(request)
    patch = body.model_dump(exclude_unset=True)
    if not patch:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour.")
    dec_patch = {k: Decimal(str(v)) for k, v in patch.items()}
    with get_db() as conn:
        data = update_settings(conn, patch=dec_patch, updated_by=user.get("id"))
    return PricingSettingsOut(**data)


@router.post("/api/pricing/settings/refresh-fx", response_model=PricingFxRefreshOut)
async def refresh_fx_rate(request: Request):
    user = _require_write(request)
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(_FX_API_URL, params={"base": "USD", "symbols": "EUR"})
        r.raise_for_status()
        payload = r.json()
        rates = payload.get("rates") or {}
        eur = rates.get("EUR")
        if eur is None:
            raise HTTPException(
                status_code=502,
                detail="Réponse taux FX invalide — EUR absent.",
            )
        rate = Decimal(str(eur))
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Impossible de récupérer le taux EUR/USD ({exc}).",
        ) from exc

    if rate <= 0:
        raise HTTPException(status_code=502, detail="Taux EUR/USD invalide.")

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    with get_db() as conn:
        ensure_settings_rows(conn)
        conn.execute(
            """UPDATE mc_setting SET value_decimal=?, updated_at=?, updated_by=?, source=?
               WHERE key='eur_usd_rate'""",
            (float(rate), now, user.get("id"), _FX_SOURCE),
        )
        conn.commit()
        data = load_settings_response(conn)

    return PricingFxRefreshOut(
        eur_usd_rate=rate,
        eur_usd_rate_updated_at=data["eur_usd_rate_updated_at"] or now,
        eur_usd_rate_source=_FX_SOURCE,
    )


# ─── Suppliers ─────────────────────────────────────────────────────────────────


@router.get("/api/pricing/suppliers")
def list_suppliers(
    request: Request,
    q: Optional[str] = Query(None),
    active_only: bool = Query(True),
):
    _require_read(request)
    sql = "SELECT * FROM mc_supplier WHERE 1=1"
    args: list[Any] = []
    if active_only:
        sql += " AND is_active=1"
    if q and q.strip():
        sql += " AND (name LIKE ? OR IFNULL(country,'') LIKE ?)"
        pat = f"%{q.strip()}%"
        args.extend([pat, pat])
    sql += " ORDER BY name COLLATE NOCASE"
    with get_db() as conn:
        rows = conn.execute(sql, args).fetchall()
    return {
        "suppliers": [
            McSupplierOut(
                id=r["id"],
                name=r["name"],
                country=r["country"],
                notes=r["notes"],
                is_active=bool(r["is_active"]),
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]
    }


@router.get("/api/pricing/suppliers/{supplier_id}", response_model=McSupplierOut)
def get_supplier(request: Request, supplier_id: int):
    _require_read(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM mc_supplier WHERE id=?", (supplier_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
    return McSupplierOut(
        id=row["id"],
        name=row["name"],
        country=row["country"],
        notes=row["notes"],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.post("/api/pricing/suppliers", response_model=McSupplierOut, status_code=201)
def create_supplier(request: Request, body: McSupplierCreate):
    _require_write(request)
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO mc_supplier (name, country, notes, is_active)
               VALUES (?,?,?,1)""",
            (body.name.strip(), body.country, body.notes),
        )
        conn.commit()
        sid = cur.lastrowid
        row = conn.execute("SELECT * FROM mc_supplier WHERE id=?", (sid,)).fetchone()
    return McSupplierOut(
        id=row["id"],
        name=row["name"],
        country=row["country"],
        notes=row["notes"],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.patch("/api/pricing/suppliers/{supplier_id}", response_model=McSupplierOut)
def patch_supplier(request: Request, supplier_id: int, body: McSupplierUpdate):
    _require_write(request)
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour.")
    with get_db() as conn:
        row = conn.execute("SELECT id FROM mc_supplier WHERE id=?", (supplier_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
        sets = []
        args: list[Any] = []
        for k, v in data.items():
            sets.append(f"{k}=?")
            args.append(1 if k == "is_active" and v is not None else v)
        sets.append("updated_at=strftime('%Y-%m-%dT%H:%M:%S','now','localtime')")
        args.append(supplier_id)
        conn.execute(f"UPDATE mc_supplier SET {', '.join(sets)} WHERE id=?", args)
        conn.commit()
        row = conn.execute("SELECT * FROM mc_supplier WHERE id=?", (supplier_id,)).fetchone()
    return McSupplierOut(
        id=row["id"],
        name=row["name"],
        country=row["country"],
        notes=row["notes"],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


@router.delete("/api/pricing/suppliers/{supplier_id}")
def delete_supplier(request: Request, supplier_id: int):
    _require_write(request)
    with get_db() as conn:
        row = conn.execute("SELECT id FROM mc_supplier WHERE id=?", (supplier_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
        conn.execute(
            """UPDATE mc_supplier SET is_active=0,
               updated_at=strftime('%Y-%m-%dT%H:%M:%S','now','localtime') WHERE id=?""",
            (supplier_id,),
        )
        conn.commit()
    return {"ok": True}


# ─── Materials ─────────────────────────────────────────────────────────────────


@router.get("/api/pricing/materials")
def list_materials(
    request: Request,
    category: Optional[str] = Query(None, description="Code catégorie FRONTAL, ADHESIF, …"),
    supplier_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
    active_only: bool = Query(True),
    with_computed: bool = Query(False),
):
    _require_read(request)
    sql = """
        SELECT m.*, c.code AS category_code
        FROM mc_material m
        JOIN mc_material_category c ON c.id = m.category_id
        WHERE 1=1
    """
    args: list[Any] = []
    if active_only:
        sql += " AND m.is_active=1"
    if category and category.strip():
        sql += " AND c.code=?"
        args.append(category.strip().upper())
    if supplier_id is not None:
        sql += " AND m.supplier_id=?"
        args.append(supplier_id)
    if q and q.strip():
        sql += " AND (m.name LIKE ? OR m.appellation_code LIKE ?)"
        pat = f"%{q.strip()}%"
        args.extend([pat, pat])
    sql += " ORDER BY m.name COLLATE NOCASE"
    with get_db() as conn:
        settings = load_pricing_settings(conn) if with_computed else None
        rows = conn.execute(sql, args).fetchall()
        items = [_material_out(r, settings=settings, with_computed=with_computed) for r in rows]
    return {"materials": items}


@router.get("/api/pricing/materials/{material_id}", response_model=McMaterialOut)
def get_material(request: Request, material_id: int):
    _require_read(request)
    with get_db() as conn:
        row = fetch_material(conn, material_id)
        if not row:
            raise HTTPException(status_code=404, detail="Matière introuvable.")
        settings = load_pricing_settings(conn)
        return _material_out(row, settings=settings, with_computed=True)


@router.post("/api/pricing/materials", response_model=McMaterialOut, status_code=201)
def create_material(request: Request, body: McMaterialCreate):
    user = _require_write(request)
    with get_db() as conn:
        cat = conn.execute(
            "SELECT code FROM mc_material_category WHERE id=?", (body.category_id,)
        ).fetchone()
        if not cat:
            raise HTTPException(status_code=400, detail="Catégorie invalide.")
        cur = conn.execute(
            """INSERT INTO mc_material (
                name, appellation_code, category_id, supplier_id, weight_per_m2, weight_gsm,
                price_currency, unit_price, price_basis, tax_incidence, is_imported,
                container_kg, container_cost_usd, is_active
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
            (
                body.name.strip(),
                body.appellation_code.strip(),
                body.category_id,
                body.supplier_id,
                float(body.weight_per_m2),
                body.weight_gsm,
                body.price_currency,
                float(body.unit_price),
                body.price_basis,
                float(body.tax_incidence),
                1 if body.is_imported else 0,
                float(body.container_kg) if body.container_kg is not None else None,
                float(body.container_cost_usd) if body.container_cost_usd is not None else None,
            ),
        )
        mid = cur.lastrowid
        insert_price_history(
            conn,
            material_id=mid,
            unit_price=body.unit_price,
            price_currency=body.price_currency,
            tax_incidence=body.tax_incidence,
            effective_date=date.today().isoformat(),
            source=body.price_history_source or "Création",
            created_by=user.get("id"),
        )
        conn.commit()
        row = fetch_material(conn, mid)
        settings = load_pricing_settings(conn)
        return _material_out(row, settings=settings, with_computed=True)


@router.patch("/api/pricing/materials/{material_id}", response_model=McMaterialOut)
def patch_material(request: Request, material_id: int, body: McMaterialUpdate):
    user = _require_write(request)
    data = body.model_dump(exclude_unset=True)
    history_source = data.pop("price_history_source", None)
    if not data:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour.")

    with get_db() as conn:
        row = fetch_material(conn, material_id)
        if not row:
            raise HTTPException(status_code=404, detail="Matière introuvable.")

        price_fields = {"unit_price", "price_currency", "tax_incidence"}
        price_changed = bool(price_fields & set(data.keys()))

        sets = []
        args: list[Any] = []
        for k, v in data.items():
            if k == "is_imported":
                sets.append(f"{k}=?")
                args.append(1 if v else 0)
            elif k == "is_active":
                sets.append(f"{k}=?")
                args.append(1 if v else 0)
            elif k in ("weight_per_m2", "unit_price", "tax_incidence", "container_kg", "container_cost_usd"):
                sets.append(f"{k}=?")
                args.append(float(v) if v is not None else None)
            else:
                sets.append(f"{k}=?")
                args.append(v.strip() if isinstance(v, str) else v)
        sets.append("updated_at=strftime('%Y-%m-%dT%H:%M:%S','now','localtime')")
        args.append(material_id)
        conn.execute(f"UPDATE mc_material SET {', '.join(sets)} WHERE id=?", args)

        if price_changed:
            new = conn.execute("SELECT * FROM mc_material WHERE id=?", (material_id,)).fetchone()
            insert_price_history(
                conn,
                material_id=material_id,
                unit_price=Decimal(str(new["unit_price"])),
                price_currency=new["price_currency"],
                tax_incidence=Decimal(str(new["tax_incidence"])),
                effective_date=date.today().isoformat(),
                source=history_source or "MAJ prix",
                created_by=user.get("id"),
            )
        conn.commit()
        row = fetch_material(conn, material_id)
        settings = load_pricing_settings(conn)
        return _material_out(row, settings=settings, with_computed=True)


@router.delete("/api/pricing/materials/{material_id}")
def delete_material(request: Request, material_id: int):
    _require_write(request)
    with get_db() as conn:
        row = conn.execute("SELECT id FROM mc_material WHERE id=?", (material_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Matière introuvable.")
        conn.execute(
            """UPDATE mc_material SET is_active=0,
               updated_at=strftime('%Y-%m-%dT%H:%M:%S','now','localtime') WHERE id=?""",
            (material_id,),
        )
        conn.commit()
    return {"ok": True}


@router.get("/api/pricing/materials/{material_id}/history")
def material_price_history(request: Request, material_id: int):
    _require_read(request)
    with get_db() as conn:
        if not conn.execute("SELECT 1 FROM mc_material WHERE id=?", (material_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Matière introuvable.")
        rows = conn.execute(
            """SELECT * FROM mc_material_price_history
               WHERE material_id=? ORDER BY effective_date DESC, id DESC""",
            (material_id,),
        ).fetchall()
    return {
        "history": [
            McMaterialPriceHistoryOut(
                id=r["id"],
                material_id=r["material_id"],
                unit_price=Decimal(str(r["unit_price"])),
                price_currency=r["price_currency"],
                tax_incidence=Decimal(str(r["tax_incidence"])),
                effective_date=r["effective_date"],
                source=r["source"],
                created_by=r["created_by"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
    }


# ─── Products ──────────────────────────────────────────────────────────────────


@router.get("/api/pricing/products")
def list_products(
    request: Request,
    q: Optional[str] = Query(None),
    active_only: bool = Query(True),
    with_cost: bool = Query(True),
):
    _require_read(request)
    sql = "SELECT * FROM mc_product WHERE 1=1"
    args: list[Any] = []
    if active_only:
        sql += " AND is_active=1"
    if q and q.strip():
        sql += " AND (code LIKE ? OR name LIKE ?)"
        pat = f"%{q.strip()}%"
        args.extend([pat, pat])
    sql += " ORDER BY code COLLATE NOCASE"
    with get_db() as conn:
        rows = conn.execute(sql, args).fetchall()
        items: list[McProductOut] = []
        for r in rows:
            try:
                items.append(_product_out(conn, r, with_cost=with_cost))
            except (HTTPException, PricingError):
                if with_cost:
                    items.append(_product_out(conn, r, with_cost=False))
                else:
                    raise
    return {"products": items}


@router.get("/api/pricing/products/export.xlsx")
def export_products_xlsx(request: Request, ids: Optional[str] = Query(None)):
    """Export Excel — onglets Produits + Matières utilisées."""
    _require_read(request)
    product_ids = _parse_product_ids_param(ids)
    if not product_ids:
        raise HTTPException(
            status_code=400,
            detail="Paramètre ids requis (ex. ?ids=1,2,3).",
        )
    with get_db() as conn:
        products, materials_map = _load_products_export_payload(conn, product_ids)
    if not products:
        raise HTTPException(status_code=404, detail="Aucun produit trouvé pour cet export.")
    try:
        xlsx_bytes = build_products_workbook(products, materials_map)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Export Excel impossible : {exc}") from exc
    filename = f"produits-couts-{datetime.now().strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        io.BytesIO(xlsx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/api/pricing/products/{product_id}/export/pdf")
def export_product_pdf(request: Request, product_id: int):
    """Fiche produit PDF (reportlab)."""
    _require_read(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM mc_product WHERE id=?", (product_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Produit introuvable.")
        try:
            pout = _product_out(conn, row, with_cost=True)
        except PricingError as e:
            raise _pricing_error(e) from e
    cost = pout.cost
    if not cost:
        raise HTTPException(status_code=422, detail="Calcul du coût impossible pour ce produit.")
    try:
        pdf_bytes = build_product_pdf(
            code=pout.code,
            name=pout.name,
            components=[c.model_dump() for c in cost.components],
            total_eur_per_m2=cost.total_eur_per_m2,
            margin_eur_m2=cost.margin_eur_m2,
            sell_price_eur_m2=cost.sell_price_eur_m2,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Génération PDF impossible : {exc}") from exc
    safe_code = re.sub(r"[^\w\-]+", "_", pout.code or "produit")[:40]
    filename = f"fiche-{safe_code}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/pricing/products/{product_id}", response_model=McProductOut)
def get_product(request: Request, product_id: int):
    _require_read(request)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM mc_product WHERE id=?", (product_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Produit introuvable.")
        try:
            return _product_out(conn, row, with_cost=True)
        except PricingError as e:
            raise _pricing_error(e) from e


@router.post("/api/pricing/products", response_model=McProductOut, status_code=201)
def create_product(request: Request, body: McProductCreate):
    _require_write(request)
    with get_db() as conn:
        assert_materials_active_for_product(
            conn,
            [body.frontal_id, body.adhesif_id, body.silicone_id, body.glassine_id, *body.extra_material_ids],
        )
        try:
            cur = conn.execute(
                """INSERT INTO mc_product (
                    code, name, frontal_id, adhesif_id, silicone_id, glassine_id,
                    custom_margin_eur_m2, is_active
                ) VALUES (?,?,?,?,?,?,?,1)""",
                (
                    body.code.strip(),
                    body.name.strip(),
                    body.frontal_id,
                    body.adhesif_id,
                    body.silicone_id,
                    body.glassine_id,
                    float(body.custom_margin_eur_m2) if body.custom_margin_eur_m2 is not None else None,
                ),
            )
            pid = cur.lastrowid
            set_product_extras(conn, pid, body.extra_material_ids)
            conn.commit()
            row = conn.execute("SELECT * FROM mc_product WHERE id=?", (pid,)).fetchone()
            return _product_out(conn, row, with_cost=True)
        except PricingError as e:
            raise _pricing_error(e) from e
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="Code produit déjà utilisé.") from None


@router.patch("/api/pricing/products/{product_id}", response_model=McProductOut)
def patch_product(request: Request, product_id: int, body: McProductUpdate):
    _require_write(request)
    data = body.model_dump(exclude_unset=True)
    extra_ids = data.pop("extra_material_ids", None)
    if not data and extra_ids is None:
        raise HTTPException(status_code=400, detail="Aucun champ à mettre à jour.")

    with get_db() as conn:
        row = conn.execute("SELECT * FROM mc_product WHERE id=?", (product_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Produit introuvable.")

        merged_ids = [
            data.get("frontal_id", row["frontal_id"]),
            data.get("adhesif_id", row["adhesif_id"]),
            data.get("silicone_id", row["silicone_id"]),
            data.get("glassine_id", row["glassine_id"]),
        ]
        if extra_ids is not None:
            merged_ids.extend(extra_ids)
        else:
            merged_ids.extend(load_product_extra_ids(conn, product_id))
        assert_materials_active_for_product(conn, merged_ids)

        if data:
            sets = []
            args: list[Any] = []
            for k, v in data.items():
                if k == "is_active":
                    sets.append(f"{k}=?")
                    args.append(1 if v else 0)
                elif k == "custom_margin_eur_m2":
                    sets.append(f"{k}=?")
                    args.append(float(v) if v is not None else None)
                elif k in ("code", "name"):
                    sets.append(f"{k}=?")
                    args.append(v.strip())
                else:
                    sets.append(f"{k}=?")
                    args.append(v)
            sets.append("updated_at=strftime('%Y-%m-%dT%H:%M:%S','now','localtime')")
            args.append(product_id)
            conn.execute(f"UPDATE mc_product SET {', '.join(sets)} WHERE id=?", args)
        if extra_ids is not None:
            set_product_extras(conn, product_id, extra_ids)
        conn.commit()
        row = conn.execute("SELECT * FROM mc_product WHERE id=?", (product_id,)).fetchone()
        try:
            return _product_out(conn, row, with_cost=True)
        except PricingError as e:
            raise _pricing_error(e) from e


@router.delete("/api/pricing/products/{product_id}")
def delete_product(request: Request, product_id: int):
    _require_write(request)
    with get_db() as conn:
        row = conn.execute("SELECT id FROM mc_product WHERE id=?", (product_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Produit introuvable.")
        conn.execute(
            """UPDATE mc_product SET is_active=0,
               updated_at=strftime('%Y-%m-%dT%H:%M:%S','now','localtime') WHERE id=?""",
            (product_id,),
        )
        conn.commit()
    return {"ok": True}


@router.post("/api/pricing/products/preview", response_model=ProductCostOut)
def preview_product_cost(request: Request, body: ProductPreviewIn):
    _require_read(request)
    with get_db() as conn:
        assert_materials_active_for_product(
            conn,
            [
                body.frontal_id,
                body.adhesif_id,
                body.silicone_id,
                body.glassine_id,
                *body.extra_material_ids,
            ],
        )
        settings = load_pricing_settings(conn)
        product = PricingProduct(
            id=0,
            code="PREVIEW",
            name="Preview",
            frontal_id=body.frontal_id,
            adhesif_id=body.adhesif_id,
            silicone_id=body.silicone_id,
            glassine_id=body.glassine_id,
            extra_material_ids=tuple(body.extra_material_ids),
            custom_margin_eur_m2=body.custom_margin_eur_m2,
        )
        mat_ids = _collect_product_material_ids(
            body.frontal_id,
            body.adhesif_id,
            body.silicone_id,
            body.glassine_id,
            body.extra_material_ids,
        )
        mats = fetch_materials_map(conn, mat_ids, require_active=True)
        try:
            result = compute_product_cost(product, mats, settings)
        except PricingError as e:
            raise _pricing_error(e) from e

        components: list[ProductComponentOut] = []
        for c in result.components:
            pm = mats[c.material_id]
            comp = compute_material_price_per_m2(pm, settings)
            b = comp.breakdown
            components.append(
                ProductComponentOut(
                    material_id=c.material_id,
                    name=c.name,
                    role=c.role,
                    price_eur_per_m2=c.price_eur_per_m2,
                    share_pct=c.share_pct,
                    breakdown=MaterialBreakdownOut(
                        raw=b.raw,
                        transport=b.transport,
                        fx=b.fx,
                        tax_uplift=b.tax_uplift,
                    ),
                )
            )
        return ProductCostOut(
            total_eur_per_m2=result.total_eur_per_m2,
            margin_eur_m2=result.margin_eur_m2,
            sell_price_eur_m2=result.sell_price_eur_m2,
            components=components,
        )

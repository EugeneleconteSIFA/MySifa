"""MySifa — API Calcul des coûts matières (/api/pricing)."""

from __future__ import annotations

import io
import re
import sqlite3
from datetime import date, datetime, timedelta as _dt_timedelta
from decimal import Decimal
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Body, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from config import ROLES_PRICING_WRITE
from database import get_db
from app.services.auth_service import get_current_user, user_has_app_access
from app.services.pricing import (
    PricingError,
    compute_material_price_per_m2,
    compute_product_cost,
)
from app.services.pricing.repository import (
    MYSTOCK_COLS,
    MYSTOCK_JOIN,
    mystock_price_for_row,
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
    CategoryVariationOut,
    MaterialMoverOut,
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
from app.services import pricing_bridge
from app.services import mystock_prix

router = APIRouter(tags=["pricing"])

_FX_API_URL = "https://api.exchangerate.host/latest"
_FX_SOURCE = "exchangerate.host"


def _require_read(request: Request) -> dict:
    user = get_current_user(request)
    if not user_has_app_access(user, "pricing"):
        raise HTTPException(status_code=403, detail="Accès Coûts matières requis")
    return user


def _require_write(request: Request) -> dict:
    user = _require_read(request)
    if user.get("role") not in ROLES_PRICING_WRITE:
        raise HTTPException(
            status_code=403,
            detail="Écriture réservée à la Direction.",
        )
    return user


def _pricing_error(exc: PricingError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


def _row_get(row, name: str, default=None):
    """Lecture tolérante d'une colonne sqlite3.Row (compat pré-migration 223)."""
    try:
        return row[name]
    except (IndexError, KeyError):
        return default


def _breakdown_out(b) -> MaterialBreakdownOut:
    """Décomposition enrichie — alimente le tableau récap de la fiche matière."""
    return MaterialBreakdownOut(
        raw=b.raw,
        transport=b.transport,
        fx=b.fx,
        tax_uplift=b.tax_uplift,
        currency=getattr(b, "currency", "EUR"),
        price_basis=getattr(b, "price_basis", "PER_KG"),
        fx_rate=getattr(b, "fx_rate", Decimal("1")),
        weight_per_m2=getattr(b, "weight_per_m2", Decimal("0")),
        unit_price_src=getattr(b, "unit_price_src", Decimal("0")),
        transport_src=getattr(b, "transport_src", Decimal("0")),
        subtotal_src=getattr(b, "subtotal_src", Decimal("0")),
        subtotal_eur=getattr(b, "subtotal_eur", Decimal("0")),
        transport_eur_m2=getattr(b, "transport_eur_m2", Decimal("0")),
        transport_pct_effective=getattr(b, "transport_pct_effective", Decimal("0")),
    )


def _material_computed(pm, settings) -> MaterialComputedOut:
    """Prix calculé + marge par défaut + valeur de transport proposée."""
    try:
        res = compute_material_price_per_m2(pm, settings)
    except PricingError as e:
        raise _pricing_error(e) from e
    margin_pct = getattr(settings, "default_margin_pct", Decimal("0")) or Decimal("0")
    margin = (res.price_eur_per_m2 * margin_pct / Decimal("100")).quantize(Decimal("0.0001"))
    return MaterialComputedOut(
        price_eur_per_m2=res.price_eur_per_m2,
        breakdown=_breakdown_out(res.breakdown),
        margin_pct=margin_pct,
        margin_eur_m2=margin,
        sell_price_eur_m2=res.price_eur_per_m2 + margin,
    )


def _computed_out(mat_row, settings, mystock=None) -> MaterialComputedOut:
    return _material_computed(row_to_pricing_material(mat_row, mystock=mystock), settings)


def _material_out(row, *, conn=None, settings=None, with_computed: bool = False) -> McMaterialOut:
    # Matière appairée : c'est le prix MyStock qui fait foi, pas la copie locale.
    ms = mystock_price_for_row(conn, row) if conn is not None else None
    d = material_row_to_dict(row, category_code=row["category_code"], mystock=ms)
    computed = _computed_out(row, settings, ms) if with_computed and settings else None
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
            breakdown = _breakdown_out(comp.breakdown)
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
        margin_pct=result.margin_pct,
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
        custom_margin_pct=float(row["custom_margin_pct"])
        if _row_get(row, "custom_margin_pct") is not None
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
        m = _material_out(row, conn=conn, settings=settings, with_computed=True)
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
            except PricingError:
                # Matière inactive / introuvable : on ignore ce produit du dashboard
                # plutôt que faire crasher toute la page.
                continue
            except Exception as _dash_exc:
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    "pricing_dashboard : produit id=%s ignoré (%s: %s)",
                    row["id"], type(_dash_exc).__name__, _dash_exc,
                )
                continue
            except PricingError:
                # Matière inactive / introuvable : on ignore ce produit du dashboard
                # plutôt que faire crasher toute la page.
                continue
            except Exception as _dash_exc:
                # Filet ultime : données incohérentes (sync mp<->mc défectueuse etc.)
                # ne doivent pas casser le dashboard direction.
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    "pricing_dashboard : produit id=%s ignoré (%s: %s)",
                    row["id"], type(_dash_exc).__name__, _dash_exc,
                )
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
        variations, movers = _compute_dashboard_kpis(conn)
    return PricingDashboardOut(
        materials_active=int(n_mat),
        products_active=int(n_prod),
        eur_usd_rate=Decimal(str(settings_data["eur_usd_rate"])),
        eur_usd_rate_updated_at=settings_data.get("eur_usd_rate_updated_at"),
        eur_usd_rate_source=settings_data.get("eur_usd_rate_source"),
        avg_sell_price_eur_m2=avg_sell,
        top_products=top,
        variations_by_category=variations,
        recent_movers=movers,
    )


def _compute_dashboard_kpis(conn) -> tuple[list, list]:
    """KPI direction : prix moyen par catégorie + variation 30j + top movers."""
    from collections import defaultdict

    cat_rows = conn.execute(
        "SELECT c.code, c.label, m.id, m.unit_price, m.price_basis "
        "FROM mc_material m "
        "JOIN mc_material_category c ON c.id = m.category_id "
        "WHERE m.is_active = 1 AND m.unit_price > 0"
    ).fetchall()

    by_cat: dict = defaultdict(
        lambda: {"label": "", "prices": [], "basis_counts": defaultdict(int)}
    )
    for r in cat_rows:
        code = r["code"]
        by_cat[code]["label"] = r["label"]
        by_cat[code]["prices"].append(float(r["unit_price"]))
        by_cat[code]["basis_counts"][r["price_basis"] or "PER_KG"] += 1

    thirty_days_ago = (date.today() - _dt_timedelta(days=30)).isoformat()
    hist_rows = conn.execute(
        "SELECT h.material_id, h.unit_price, h.effective_date, "
        "       m.name, c.code AS category_code "
        "FROM mc_material_price_history h "
        "JOIN mc_material m ON m.id = h.material_id "
        "JOIN mc_material_category c ON c.id = m.category_id "
        "WHERE h.effective_date <= ? AND m.is_active = 1 "
        "ORDER BY h.material_id, h.effective_date DESC",
        (thirty_days_ago,),
    ).fetchall()

    latest_old: dict = {}
    for h in hist_rows:
        mid = int(h["material_id"])
        if mid not in latest_old:
            latest_old[mid] = {
                "old_price": float(h["unit_price"]),
                "effective_date": h["effective_date"],
                "name": h["name"],
                "category_code": h["category_code"],
            }

    current_prices: dict = {int(r["id"]): float(r["unit_price"]) for r in cat_rows}

    movers = []
    variations_by_cat = defaultdict(list)
    for mid, old in latest_old.items():
        new = current_prices.get(mid)
        if new is None or old["old_price"] <= 0:
            continue
        pct = (new - old["old_price"]) / old["old_price"] * 100.0
        variations_by_cat[old["category_code"]].append(pct)
        # N'ajoute pas aux movers si variation < 0.01% (bruit de calcul).
        if abs(pct) < 0.01:
            continue
        try:
            eff = datetime.strptime(old["effective_date"][:10], "%Y-%m-%d").date()
            days = max(0, (date.today() - eff).days)
        except (ValueError, TypeError):
            days = 30
        movers.append((
            abs(pct),
            MaterialMoverOut(
                id=mid,
                name=old["name"],
                category_code=old["category_code"],
                old_price=Decimal(str(round(old["old_price"], 4))),
                new_price=Decimal(str(round(new, 4))),
                variation_pct=Decimal(str(round(pct, 2))),
                days_ago=days,
            ),
        ))

    variations = []
    for code, data in by_cat.items():
        prices = data["prices"]
        avg = sum(prices) / len(prices) if prices else None
        dom_basis = None
        if data["basis_counts"]:
            dom_basis = max(data["basis_counts"].items(), key=lambda x: x[1])[0]
        var_pcts = variations_by_cat.get(code, [])
        avg_var = sum(var_pcts) / len(var_pcts) if var_pcts else None
        variations.append(CategoryVariationOut(
            code=code,
            label=data["label"] or code,
            count_materials=len(prices),
            avg_price_eur_per_kg_or_m2=Decimal(str(round(avg, 4))) if avg is not None else None,
            price_basis_dominant=dom_basis,
            variation_pct_30d=Decimal(str(round(avg_var, 2))) if avg_var is not None else None,
        ))
    variations.sort(key=lambda v: v.code)

    movers.sort(key=lambda t: -t[0])
    top_movers = [m for _, m in movers[:10]]

    return variations, top_movers


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
        transport_mode=body.transport_mode,
        transport_unit_price=body.transport_unit_price,
        transport_pct=body.transport_pct,
        container_kg=body.container_kg,
        container_cost_usd=body.container_cost_usd,
    )
    return _material_computed(pm, settings)


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
    sql = f"""
        SELECT m.*, c.code AS category_code, f.nom AS fournisseur_nom, {MYSTOCK_COLS}
        FROM mc_material m
        JOIN mc_material_category c ON c.id = m.category_id
        LEFT JOIN fournisseurs_fsc f ON f.id = m.fournisseur_fsc_id
        {MYSTOCK_JOIN}
        WHERE 1=1
    """
    args: list[Any] = []
    if active_only:
        sql += " AND m.is_active=1"
    if category and category.strip():
        sql += " AND c.code=?"
        args.append(category.strip().upper())
    if supplier_id is not None:
        # Le sélecteur de la liste porte désormais sur l'annuaire entreprise ;
        # on accepte encore l'ancien identifiant pour les matières non rattachées.
        sql += " AND (m.fournisseur_fsc_id=? OR (m.fournisseur_fsc_id IS NULL AND m.supplier_id=?))"
        args.extend([supplier_id, supplier_id])
    if q and q.strip():
        sql += " AND (m.name LIKE ? OR m.appellation_code LIKE ?)"
        pat = f"%{q.strip()}%"
        args.extend([pat, pat])
    sql += " ORDER BY m.name COLLATE NOCASE"
    with get_db() as conn:
        settings = load_pricing_settings(conn) if with_computed else None
        rows = conn.execute(sql, args).fetchall()
        items = [_material_out(r, conn=conn, settings=settings, with_computed=with_computed) for r in rows]
    return {"materials": items}


@router.get("/api/pricing/materials/{material_id}", response_model=McMaterialOut)
def get_material(request: Request, material_id: int):
    _require_read(request)
    with get_db() as conn:
        row = fetch_material(conn, material_id)
        if not row:
            raise HTTPException(status_code=404, detail="Matière introuvable.")
        settings = load_pricing_settings(conn)
        return _material_out(row, conn=conn, settings=settings, with_computed=True)


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
                name, appellation_code, category_id, supplier_id, fournisseur_fsc_id,
                weight_per_m2, weight_gsm,
                price_currency, unit_price, price_basis, tax_incidence, is_imported,
                transport_mode, transport_unit_price, transport_pct,
                container_kg, container_cost_usd, is_active
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
            (
                body.name.strip(),
                body.appellation_code.strip(),
                body.category_id,
                body.supplier_id,
                body.fournisseur_fsc_id,
                float(body.weight_per_m2),
                body.weight_gsm,
                body.price_currency,
                float(body.unit_price),
                body.price_basis,
                float(body.tax_incidence),
                1 if body.is_imported else 0,
                body.transport_mode or "AMOUNT",
                float(body.transport_unit_price or 0),
                float(body.transport_pct or 0),
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
        return _material_out(row, conn=conn, settings=settings, with_computed=True)


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
            elif k in (
                "weight_per_m2",
                "unit_price",
                "tax_incidence",
                "transport_unit_price",
                "transport_pct",
                "container_kg",
                "container_cost_usd",
            ):
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
        # Plus de recopie vers MyStock : une matière appairée n'a plus de prix
        # propre — celui de MyStock est lu au moment du calcul. Le prix
        # local reste en base pour les matières non appairées uniquement.
        row = fetch_material(conn, material_id)
        settings = load_pricing_settings(conn)
        return _material_out(row, conn=conn, settings=settings, with_computed=True)


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
                    custom_margin_pct, is_active
                ) VALUES (?,?,?,?,?,?,?,1)""",
                (
                    body.code.strip(),
                    body.name.strip(),
                    body.frontal_id,
                    body.adhesif_id,
                    body.silicone_id,
                    body.glassine_id,
                    float(body.custom_margin_pct) if body.custom_margin_pct is not None else None,
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
                elif k == "custom_margin_pct":
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
            custom_margin_pct=body.custom_margin_pct,
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
                    breakdown=_breakdown_out(b),
                )
            )
        return ProductCostOut(
            total_eur_per_m2=result.total_eur_per_m2,
            margin_pct=result.margin_pct,
            margin_eur_m2=result.margin_eur_m2,
            sell_price_eur_m2=result.sell_price_eur_m2,
            components=components,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Annuaire fournisseurs de l'entreprise (fournisseurs_fsc)
#
# Coûts matières n'a plus d'annuaire à lui : il choisit dans celui de
# l'entreprise, le même que la qualité et le FSC. La table mc_supplier reste en
# base pour l'historique, avec la correspondance établie en migration 226.
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/api/pricing/fournisseurs")
def list_fournisseurs_entreprise(request: Request):
    """Annuaire fournisseurs de l'entreprise, pour tous les sélecteurs de /pricing."""
    _require_read(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT id, nom, COALESCE(has_fsc, 0) AS has_fsc, pays, actif
                 FROM fournisseurs_fsc
                ORDER BY nom COLLATE NOCASE ASC"""
        ).fetchall()
    return {
        "fournisseurs": [
            {
                "id": int(r["id"]),
                "nom": r["nom"],
                "has_fsc": bool(r["has_fsc"]),
                "pays": r["pays"],
                "actif": bool(r["actif"]) if r["actif"] is not None else True,
            }
            for r in rows
        ]
    }


@router.get("/api/pricing/fournisseurs/rapprochement")
def rapprochement_fournisseurs(request: Request):
    """
    État du rapprochement entre l'ancien annuaire de Coûts matières et celui de
    l'entreprise : ce qui a trouvé son jumeau, et ce qui reste à trancher.
    """
    _require_read(request)
    with get_db() as conn:
        rows = conn.execute(
            """SELECT s.id, s.name, s.fournisseur_fsc_id, f.nom AS fsc_nom,
                      (SELECT COUNT(*) FROM mc_material m WHERE m.supplier_id = s.id)
                        AS nb_matieres
                 FROM mc_supplier s
                 LEFT JOIN fournisseurs_fsc f ON f.id = s.fournisseur_fsc_id
                ORDER BY s.name COLLATE NOCASE ASC"""
        ).fetchall()
    apparies, orphelins = [], []
    for r in rows:
        item = {
            "mc_supplier_id": int(r["id"]),
            "nom": r["name"],
            "nb_matieres": int(r["nb_matieres"] or 0),
            "fournisseur_id": int(r["fournisseur_fsc_id"])
            if r["fournisseur_fsc_id"] is not None
            else None,
            "fournisseur_nom": r["fsc_nom"],
        }
        (apparies if item["fournisseur_id"] else orphelins).append(item)
    return {
        "apparies": apparies,
        "orphelins": orphelins,
        "nb_apparies": len(apparies),
        "nb_orphelins": len(orphelins),
    }


@router.post("/api/pricing/fournisseurs/rapprochement")
def set_rapprochement_fournisseur(request: Request, body: dict = Body(...)):
    """Rattache manuellement un ancien fournisseur à celui de l'annuaire entreprise."""
    _require_write(request)
    try:
        mc_id = int(body.get("mc_supplier_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="mc_supplier_id requis") from None
    raw = body.get("fournisseur_id")
    fid = None
    if raw not in (None, "", 0):
        try:
            fid = int(raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="fournisseur_id invalide") from None
    with get_db() as conn:
        if fid is not None and not conn.execute(
            "SELECT 1 FROM fournisseurs_fsc WHERE id=?", (fid,)
        ).fetchone():
            raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
        conn.execute("UPDATE mc_supplier SET fournisseur_fsc_id=? WHERE id=?", (fid, mc_id))
        # Les matières encore sans fournisseur d'entreprise héritent du rattachement.
        conn.execute(
            """UPDATE mc_material SET fournisseur_fsc_id=?
                WHERE supplier_id=? AND fournisseur_fsc_id IS NULL""",
            (fid, mc_id),
        )
        conn.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
# Matières MyStock — vue et écriture des prix par fournisseur
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/api/pricing/mystock/materials")
def list_mystock_materials(
    request: Request,
    q: Optional[str] = None,
    categorie: Optional[str] = None,
    active_only: bool = Query(True),
):
    """Une ligne par matière MyStock devisable, avec ses déclinaisons et prix."""
    _require_read(request)
    with get_db() as conn:
        materials = mystock_prix.list_materials(
            conn, q=q, categorie=categorie, actives_only=active_only
        )
        # Coût au m² de chaque déclinaison : c'est la colonne qui rend la liste
        # utile, sinon il faut ouvrir chaque fiche pour savoir ce que la matière
        # coûte réellement.
        from app.services.pricing.repository import declinaison_to_pricing_material

        reglages = load_pricing_settings(conn)
        for m in materials:
            for d in m.get("declinaisons", []):
                d["cout_eur_m2"] = None
                if not d.get("unit_price"):
                    continue
                try:
                    d["cout_eur_m2"] = float(
                        compute_material_price_per_m2(
                            declinaison_to_pricing_material(
                                {**d, "declinaison_id": d["id"],
                                 "reference": m["reference"], "libelle": d["libelle"]}
                            ),
                            reglages,
                        ).price_eur_per_m2
                    )
                except PricingError:
                    # Réglages incomplets : la fiche le dira, la liste ne doit
                    # pas tomber pour autant.
                    pass
        cats = sorted(
            r["categorie"]
            for r in conn.execute(
                "SELECT DISTINCT categorie FROM matieres_premieres"
            ).fetchall()
            if (r["categorie"] or "").strip().lower() in mystock_prix.CATEGORIES_VISIBLES
        )
        return {
            "materials": materials,
            "categories": cats,
            "laizes": mystock_prix.list_laizes(conn),
            "grammages": mystock_prix.list_grammages(conn),
        }


def _decl_id(body: dict) -> int:
    try:
        return int(body.get("declinaison_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="declinaison_id requis") from None


def _opt_int(body: dict, key: str) -> Optional[int]:
    raw = body.get(key)
    if raw in (None, "", 0, "0"):
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"{key} invalide") from None


@router.post("/api/pricing/mystock/declinaisons")
def add_mystock_declinaison(request: Request, body: dict = Body(...)):
    """Ajoute une laize (frontal, glassine, complexe) ou un grammage (adhésif)."""
    _require_write(request)
    try:
        matiere_id = int(body.get("matiere_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="matiere_id requis") from None
    gsm = body.get("valeur_gsm")
    with get_db() as conn:
        res = mystock_prix.add_declinaison(
            conn,
            matiere_id=matiere_id,
            laize_id=_opt_int(body, "laize_id"),
            valeur_gsm=float(gsm) if gsm not in (None, "") else None,
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("reason", "Ajout refusé"))
        conn.commit()
    return res


@router.post("/api/pricing/mystock/declinaisons/valeur")
def set_mystock_declinaison_valeur(request: Request, body: dict = Body(...)):
    """Change le grammage (ou la laize) d'une déclinaison, saisi dans sa ligne."""
    _require_write(request)
    gsm = body.get("valeur_gsm")
    with get_db() as conn:
        res = mystock_prix.set_declinaison_valeur(
            conn,
            declinaison_id=_decl_id(body),
            laize_id=_opt_int(body, "laize_id"),
            valeur_gsm=float(gsm) if gsm not in (None, "") else None,
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("reason", "Modification refusée"))
        conn.commit()
    return res


@router.post("/api/pricing/mystock/prix/dupliquer")
def dupliquer_mystock_ligne(request: Request, body: dict = Body(...)):
    """Duplique une ligne de prix sur la même déclinaison, sans fournisseur."""
    _require_write(request)
    with get_db() as conn:
        res = mystock_prix.dupliquer_ligne(
            conn,
            declinaison_id=_decl_id(body),
            fournisseur_id=_opt_int(body, "fournisseur_id"),
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("reason", "Duplication refusée"))
        conn.commit()
    return res


@router.delete("/api/pricing/mystock/declinaisons/{declinaison_id}")
def delete_mystock_declinaison(request: Request, declinaison_id: int):
    """Retire une déclinaison et les prix qui lui sont rattachés."""
    _require_write(request)
    with get_db() as conn:
        res = mystock_prix.delete_declinaison(conn, declinaison_id)
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("reason", "Suppression refusée"))
        conn.commit()
    return res


@router.post("/api/pricing/mystock/appairage")
def set_mystock_appairage(request: Request, body: dict = Body(...)):
    """Appaire une déclinaison à une matière Coûts matières, ou la détache."""
    _require_write(request)
    with get_db() as conn:
        res = mystock_prix.set_appairage(
            conn,
            declinaison_id=_decl_id(body),
            mc_material_id=_opt_int(body, "mc_material_id"),
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("reason", "Appairage refusé"))
        conn.commit()
    return res


@router.post("/api/pricing/mystock/prix")
def set_mystock_prix(request: Request, body: dict = Body(...)):
    """Fixe le prix d'un fournisseur sur une déclinaison (et son miroir si principal)."""
    user = _require_write(request)
    try:
        prix = float(body.get("prix"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="prix invalide") from None
    with get_db() as conn:
        res = mystock_prix.set_prix(
            conn,
            declinaison_id=_decl_id(body),
            fournisseur_id=_opt_int(body, "fournisseur_id"),
            prix=prix,
            user_id=user.get("id"),
            user_name=user.get("nom"),
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("reason", "Modification refusée"))
        conn.commit()
    return res


@router.post("/api/pricing/mystock/fournisseur")
def set_mystock_fournisseur(request: Request, body: dict = Body(...)):
    """Change le fournisseur d'une ligne de prix, sans lui faire perdre son statut."""
    _require_write(request)
    with get_db() as conn:
        res = mystock_prix.set_fournisseur(
            conn,
            declinaison_id=_decl_id(body),
            fournisseur_id=_opt_int(body, "fournisseur_id"),
            nouveau_fournisseur_id=_opt_int(body, "nouveau_fournisseur_id"),
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("reason", "Modification refusée"))
        conn.commit()
    return res


@router.post("/api/pricing/mystock/principal")
def set_mystock_principal(request: Request, body: dict = Body(...)):
    """Désigne le fournisseur dont le prix fait foi pour cette déclinaison."""
    user = _require_write(request)
    with get_db() as conn:
        res = mystock_prix.set_principal(
            conn,
            declinaison_id=_decl_id(body),
            fournisseur_id=_opt_int(body, "fournisseur_id"),
            user_id=user.get("id"),
            user_name=user.get("nom"),
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("reason", "Modification refusée"))
        conn.commit()
    return res


@router.delete("/api/pricing/mystock/prix")
def delete_mystock_prix(request: Request, body: dict = Body(...)):
    """Retire un fournisseur d'une déclinaison."""
    _require_write(request)
    with get_db() as conn:
        res = mystock_prix.delete_ligne(
            conn,
            declinaison_id=_decl_id(body),
            fournisseur_id=_opt_int(body, "fournisseur_id"),
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("reason", "Suppression refusée"))
        conn.commit()
    return res


def _cout_declinaison(conn, param: dict) -> MaterialComputedOut:
    """Coût au m² d'une déclinaison, à partir de ses propres réglages."""
    from app.services.pricing.repository import declinaison_to_pricing_material

    return _material_computed(
        declinaison_to_pricing_material(param), load_pricing_settings(conn)
    )


@router.get("/api/pricing/mystock/declinaisons/{declinaison_id}/parametrage")
def get_mystock_parametrage(request: Request, declinaison_id: int):
    """
    Fiche d'une déclinaison MyStock : identité, prix d'achat par fournisseur,
    réglages de calcul et coût de revient au m². C'est l'équivalent d'une fiche
    de la base Coûts matières, mais pilotée par MyStock.
    """
    _require_read(request)
    with get_db() as conn:
        param = mystock_prix.parametrage(conn, declinaison_id)
        if not param:
            raise HTTPException(status_code=404, detail="Déclinaison introuvable.")
        param["computed"] = _cout_declinaison(conn, param)
    return param


@router.patch("/api/pricing/mystock/declinaisons/{declinaison_id}/parametrage")
def patch_mystock_parametrage(request: Request, declinaison_id: int, body: dict = Body(...)):
    """Enregistre les réglages de calcul d'une déclinaison."""
    user = _require_write(request)
    with get_db() as conn:
        res = mystock_prix.set_parametrage(
            conn,
            declinaison_id=declinaison_id,
            patch=body,
            user_name=user.get("nom"),
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("reason", "Modification refusée"))
        conn.commit()
        param = res["parametrage"]
        param["computed"] = _cout_declinaison(conn, param)
    return param


@router.get("/api/pricing/mystock/candidats/{declinaison_id}")
def mystock_candidats(request: Request, declinaison_id: int):
    """
    Matières Coûts matières proposées pour appairer une déclinaison, les plus
    probables d'abord : appellation identique à la référence MyStock, puis nom
    proche, puis le reste. Celles déjà pilotées par une autre déclinaison sont
    signalées.
    """
    _require_read(request)
    with get_db() as conn:
        d = mystock_prix.fetch_declinaison(conn, declinaison_id)
        if not d:
            raise HTTPException(status_code=404, detail="Déclinaison introuvable.")
        ref = (d["reference"] or "").strip().lower()
        des = (d["designation"] or "").strip().lower()
        rows = conn.execute(
            """SELECT m.id, m.name, m.appellation_code, c.code AS category_code,
                      m.unit_price, m.price_basis, m.price_currency,
                      (SELECT dd.id FROM mp_matiere_declinaison dd
                        WHERE dd.mc_material_id = m.id LIMIT 1) AS deja_pilotee
                 FROM mc_material m
                 JOIN mc_material_category c ON c.id = m.category_id
                WHERE m.is_active = 1"""
        ).fetchall()
        out = []
        for r in rows:
            app = (r["appellation_code"] or "").strip().lower()
            name = (r["name"] or "").strip().lower()
            score = 0
            if ref and app and ref == app:
                score += 100
            elif ref and app and (ref in app or app in ref):
                score += 40
            if des and name and des == name:
                score += 30
            elif des and name and (des in name or name in des):
                score += 15
            out.append(
                {
                    "id": int(r["id"]),
                    "name": r["name"],
                    "appellation_code": r["appellation_code"],
                    "category_code": r["category_code"],
                    "unit_price": float(r["unit_price"] or 0),
                    "price_basis": r["price_basis"],
                    "price_currency": r["price_currency"],
                    "deja_pilotee": r["deja_pilotee"] is not None,
                    "score": score,
                }
            )
        out.sort(key=lambda x: (-x["score"], (x["name"] or "").lower()))
    return {"candidats": out}


# ─────────────────────────────────────────────────────────────────────────────
# Bridge MyStock <-> /pricing : appairage manuel + listes orphelines
# (Round 2 — cf. app/services/pricing_bridge.py pour la logique)
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/api/pricing/bridge/orphans")
def bridge_orphans(request: Request):
    """
    Retourne :
      - `mp` : matières MyStock actives ayant un pricing_role mais non
               appairées à un mc_material (à appairer côté direction).
      - `mc` : matières mc_material actives non référencées par aucun mp.
    Utilisé par l'écran de rapprochement dans Paramètres.
    """
    _require_read(request)
    with get_db() as conn:
        return {
            "mp": pricing_bridge.list_orphaned_mp(conn),
            "mc": pricing_bridge.list_orphaned_mc(conn),
        }


@router.get("/api/pricing/bridge/suggest/{mp_id}")
def bridge_suggest(request: Request, mp_id: int):
    """
    Propositions de mc_material pour appairer une matière MyStock donnée.
    Trié par pertinence : match exact appellation, puis nom, puis catégorie.
    """
    _require_read(request)
    with get_db() as conn:
        return {"suggestions": pricing_bridge.suggest_matches(conn, mp_id, limit=500)}


@router.post("/api/pricing/bridge/link")
def bridge_link(request: Request, body: dict = Body(...)):
    """
    Appaire une matieres_premieres à un mc_material.
    Body : { mp_id: int, mc_id: int }

    Copie automatiquement les caractéristiques pricing (poids, base,
    container, taxe, import) depuis mc_material vers matieres_premieres
    sans écraser les valeurs déjà saisies côté MyStock.
    """
    _require_write(request)
    try:
        mp_id = int(body.get("mp_id"))
        mc_id = int(body.get("mc_id"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="mp_id et mc_id entiers requis")
    with get_db() as conn:
        result = pricing_bridge.link_matiere(conn, mp_id, mc_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail=result.get("reason", "Appairage impossible"))
        conn.commit()
        # Sync immédiate : pousse le prix côté qui a la valeur la plus récente.
        # On tente les deux sens ; celui qui n'a rien à faire retournera
        # {synced: False, reason: 'prix identique'} — silencieux.
        # Rien à recopier : l'appairage suffit, le prix MyStock devient
        # immédiatement celui utilisé par les calculs de Coûts matières.
    return result


@router.delete("/api/pricing/bridge/link/{mp_id}")
def bridge_unlink(request: Request, mp_id: int):
    """Casse le lien d'une matière MyStock avec son mc_material."""
    _require_write(request)
    with get_db() as conn:
        result = pricing_bridge.unlink_matiere(conn, mp_id)
        if not result.get("ok"):
            raise HTTPException(status_code=404, detail="Matière introuvable ou non appairée")
        conn.commit()
    return result

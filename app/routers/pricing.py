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
from app.services import mystock_prix, mystock_produits

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
        taxes_src=getattr(b, "taxes_src", Decimal("0")),
        taxe_pct=getattr(b, "taxe_pct", Decimal("0")),
    )


def _poids_retenu(grammage_gsm, perte_pct) -> float:
    """Poids au m² (kg) = grammage majoré de la perte. Voir mystock_prix.poids_retenu."""
    g = float(grammage_gsm or 0)
    p = float(perte_pct or 0)
    return round(g * (1 + p / 100.0) / 1000.0, 6)


def _material_computed(pm, settings) -> MaterialComputedOut:
    """Prix calculé + marge par défaut + valeur de transport proposée."""
    try:
        res = compute_material_price_per_m2(pm, settings)
    except PricingError as e:
        raise _pricing_error(e) from e
    # Une matière exclue de l'assiette de marge n'affiche pas de marge : sinon la
    # fiche annoncerait un prix de vente que le produit n'appliquera jamais.
    margin_pct = getattr(settings, "default_margin_pct", Decimal("0")) or Decimal("0")
    if not getattr(pm, "applique_marge", True):
        margin_pct = Decimal("0")
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


# ─── Référentiels ────────────────────────────────────────────────────────────


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
        taxe_pct=body.taxe_pct,
        is_imported=body.is_imported,
        applique_marge=body.applique_marge,
        transport_mode=body.transport_mode,
        transport_unit_price=body.transport_unit_price,
        transport_pct=body.transport_pct,
        transport_cout=body.transport_cout,
        transport_quantite=body.transport_quantite,
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
                weight_per_m2, weight_gsm, grammage_gsm, perte_pct,
                price_currency, unit_price, price_basis, taxe_pct, is_imported,
                applique_marge, transport_mode, transport_unit_price, transport_pct,
                transport_cout, transport_quantite,
                container_kg, container_cost_usd, is_active
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)""",
            (
                body.name.strip(),
                body.appellation_code.strip(),
                body.category_id,
                body.supplier_id,
                body.fournisseur_fsc_id,
                # Le poids découle du grammage et de la perte, il n'est jamais saisi.
                _poids_retenu(body.grammage_gsm, body.perte_pct),
                int(body.grammage_gsm) if body.grammage_gsm else None,
                float(body.grammage_gsm or 0),
                float(body.perte_pct or 0),
                body.price_currency,
                float(body.unit_price),
                body.price_basis,
                float(body.taxe_pct or 0),
                1 if body.is_imported else 0,
                1 if body.applique_marge else 0,
                body.transport_mode or "AMOUNT",
                float(body.transport_unit_price or 0),
                float(body.transport_pct or 0),
                float(body.transport_cout or 0),
                float(body.transport_quantite or 0),
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
            taxe_pct=body.taxe_pct,
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

        price_fields = {"unit_price", "price_currency", "taxe_pct"}
        price_changed = bool(price_fields & set(data.keys()))

        sets = []
        args: list[Any] = []
        for k, v in data.items():
            if k in ("is_imported", "is_active", "applique_marge"):
                sets.append(f"{k}=?")
                args.append(1 if v else 0)
            elif k in (
                "weight_per_m2",
                "unit_price",
                "taxe_pct",
                "grammage_gsm",
                "perte_pct",
                "transport_unit_price",
                "transport_pct",
                "transport_cout",
                "transport_quantite",
                "container_kg",
                "container_cost_usd",
            ):
                sets.append(f"{k}=?")
                args.append(float(v) if v is not None else None)
            else:
                sets.append(f"{k}=?")
                args.append(v.strip() if isinstance(v, str) else v)
        # Poids et grammage suivent la saisie : on les recalcule à partir de ce
        # que la fiche affiche, jamais depuis une valeur envoyée séparément.
        if "grammage_gsm" in data or "perte_pct" in data:
            g = data.get("grammage_gsm", row["grammage_gsm"])
            pe = data.get("perte_pct", row["perte_pct"])
            sets.append("weight_per_m2=?")
            args.append(_poids_retenu(g, pe))
            sets.append("weight_gsm=?")
            args.append(int(float(g)) if float(g or 0) > 0 else None)
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
                taxe_pct=Decimal(str(new["taxe_pct"])),
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
                taxe_pct=Decimal(str(r["tax_incidence"])),
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
        # La devise d'achat vit sur le fournisseur depuis la migration
        # `mc_tarif_fournisseur`. `COALESCE` plutôt qu'une colonne nue : sur une
        # base non migrée elle n'existe pas, et l'annuaire doit répondre quand
        # même.
        devises = mystock_prix.devises_fournisseurs(conn)
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
                "price_currency": devises.get(int(r["id"]), "EUR"),
            }
            for r in rows
        ]
    }


# ─────────────────────────────────────────────────────────────────────────────
# Tarifs fournisseurs
# ─────────────────────────────────────────────────────────────────────────────
# Un tarif ne dépend ni de la laize ni du grammage : il dépend de chez qui on
# achète et de ce qu'on lui achète. La devise se règle au fournisseur, le reste
# — base de prix, transport, taxes — au couple (fournisseur, matière).


@router.get("/api/pricing/tarifs/fournisseurs")
def list_tarifs_fournisseurs(request: Request):
    """
    L'annuaire vu sous l'angle des coûts : qui vend quoi, à quelle devise, et
    combien de ses matières attendent encore un tarif.
    """
    _require_read(request)
    with get_db() as conn:
        devises = mystock_prix.devises_fournisseurs(conn)
        dispo = mystock_prix.tarifs_disponibles(conn)
        rows = conn.execute(
            """SELECT f.id, f.nom, COALESCE(f.has_fsc,0) AS has_fsc, f.pays, f.actif,
                      COUNT(DISTINCT d.matiere_id)  AS nb_matieres,
                      COUNT(DISTINCT p.declinaison_id) AS nb_declinaisons,
                      SUM(CASE WHEN p.principal=1 THEN 1 ELSE 0 END) AS nb_principal
                 FROM fournisseurs_fsc f
                 LEFT JOIN mp_matiere_prix p ON p.fournisseur_id = f.id
                 LEFT JOIN mp_matiere_declinaison d ON d.id = p.declinaison_id
                GROUP BY f.id
                ORDER BY f.nom COLLATE NOCASE ASC"""
        ).fetchall()
        poses = {}
        if dispo:
            poses = {
                int(r["fournisseur_id"]): int(r["n"])
                for r in conn.execute(
                    """SELECT fournisseur_id, COUNT(*) AS n
                         FROM mc_tarif_fournisseur GROUP BY fournisseur_id"""
                ).fetchall()
            }
    return {
        "tarifs_disponibles": dispo,
        "fournisseurs": [
            {
                "id": int(r["id"]),
                "nom": r["nom"],
                "has_fsc": bool(r["has_fsc"]),
                "pays": r["pays"],
                "actif": bool(r["actif"]) if r["actif"] is not None else True,
                "price_currency": devises.get(int(r["id"]), "EUR"),
                "nb_matieres": int(r["nb_matieres"] or 0),
                "nb_declinaisons": int(r["nb_declinaisons"] or 0),
                "nb_principal": int(r["nb_principal"] or 0),
                "nb_tarifs": poses.get(int(r["id"]), 0),
            }
            for r in rows
        ],
    }


@router.get("/api/pricing/tarifs/fournisseur/{fournisseur_id}")
def tarifs_fournisseur(request: Request, fournisseur_id: int):
    """La fiche tarif d'un fournisseur : sa devise, et une ligne par matière."""
    _require_read(request)
    with get_db() as conn:
        f = conn.execute(
            "SELECT id, nom, pays FROM fournisseurs_fsc WHERE id=?", (fournisseur_id,)
        ).fetchone()
        if not f:
            raise HTTPException(404, "Fournisseur introuvable.")
        devises = mystock_prix.devises_fournisseurs(conn)
        return {
            "fournisseur": {
                "id": int(f["id"]),
                "nom": f["nom"],
                "pays": f["pays"],
                "price_currency": devises.get(int(f["id"]), "EUR"),
            },
            "tarifs_disponibles": mystock_prix.tarifs_disponibles(conn),
            "matieres": mystock_prix.tarifs_du_fournisseur(conn, fournisseur_id),
        }


@router.get("/api/pricing/tarifs/matiere/{matiere_id}")
def tarifs_matiere(request: Request, matiere_id: int):
    """La vue symétrique : les fournisseurs d'une matière et leurs tarifs."""
    _require_read(request)
    with get_db() as conn:
        mat = conn.execute(
            "SELECT id, reference, designation, categorie FROM matieres_premieres WHERE id=?",
            (matiere_id,),
        ).fetchone()
        if not mat:
            raise HTTPException(404, "Matière introuvable.")
        return {
            "matiere_id": int(mat["id"]),
            "reference": mat["reference"],
            "designation": mat["designation"],
            "categorie": mat["categorie"],
            "tarifs_disponibles": mystock_prix.tarifs_disponibles(conn),
            "fournisseurs": mystock_prix.fournisseurs_de_la_matiere(conn, matiere_id),
        }


@router.patch("/api/pricing/tarifs/fournisseur/{fournisseur_id}/devise")
async def maj_devise_fournisseur(request: Request, fournisseur_id: int):
    """La devise d'achat d'un fournisseur — elle vaut pour tout ce qu'il vend."""
    _require_write(request)
    body = await request.json()
    with get_db() as conn:
        r = mystock_prix.set_devise_fournisseur(
            conn, fournisseur_id=fournisseur_id, devise=body.get("price_currency")
        )
        if not r.get("ok"):
            raise HTTPException(400, r.get("reason") or "Devise refusée.")
        conn.commit()
    return r


@router.patch("/api/pricing/tarifs/{fournisseur_id}/{matiere_id}")
async def maj_tarif(request: Request, fournisseur_id: int, matiere_id: int):
    """
    Le tarif d'un fournisseur pour une matière.

    La réponse dit combien de déclinaisons en ont vu leur sous-total bouger :
    changer un transport ne touche aucun prix d'achat, mais déplace tout ce que
    la valorisation MyStock affiche là où ce fournisseur fait foi.
    """
    user = _require_write(request)
    body = await request.json()
    with get_db() as conn:
        r = mystock_prix.set_tarif(
            conn,
            fournisseur_id=fournisseur_id,
            matiere_id=matiere_id,
            patch=body,
            user_id=user.get("id"),
            user_name=(user.get("nom") or user.get("email") or "").strip() or None,
        )
        if not r.get("ok"):
            raise HTTPException(400, r.get("reason") or "Tarif refusé.")
        conn.commit()
    return r


@router.get("/api/pricing/tarifs/{fournisseur_id}/{matiere_id}/propager")
def perimetre_propagation(request: Request, fournisseur_id: int, matiere_id: int):
    """
    Ce qu'un « appliquer aux autres matières » toucherait, avant de le faire.

    L'écran a besoin du chiffre pour poser une question honnête : « appliquer à
    7 matières ? » se refuse en connaissance de cause, « appliquer partout ? »
    non.
    """
    _require_read(request)
    with get_db() as conn:
        perimetre = mystock_prix.cibles_propagation(
            conn, fournisseur_id=fournisseur_id, matiere_id=matiere_id
        )
        if perimetre is None:
            raise HTTPException(404, "Matière introuvable.")
        perimetre["tarifs_disponibles"] = mystock_prix.tarifs_disponibles(conn)
    return perimetre


@router.post("/api/pricing/tarifs/{fournisseur_id}/{matiere_id}/propager")
async def propager_tarif_transport(request: Request, fournisseur_id: int, matiere_id: int):
    """
    Recopie le transport et les taxes de ce tarif sur les autres matières de la
    même catégorie achetées à ce fournisseur.

    Le corps peut porter les valeurs affichées à l'écran (elles viennent d'être
    saisies) ; sans corps, c'est le tarif enregistré qui se propage.
    """
    user = _require_write(request)
    try:
        body = await request.json()
    except Exception:
        body = {}
    with get_db() as conn:
        r = mystock_prix.propager_transport(
            conn,
            fournisseur_id=fournisseur_id,
            matiere_id=matiere_id,
            patch=body if isinstance(body, dict) else None,
            user_id=user.get("id"),
            user_name=(user.get("nom") or user.get("email") or "").strip() or None,
        )
        if not r.get("ok"):
            raise HTTPException(400, r.get("reason") or "Propagation refusée.")
        conn.commit()
    return r


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
        #
        # Et un coût par LIGNE fournisseur, calculé avec les mêmes réglages et le
        # prix de cette ligne-là. Sans lui, un deuxième fournisseur ne servait à
        # rien : on voyait deux prix d'achat, jamais les deux coûts au m² — et
        # c'est le coût au m² qui tranche, pas le prix au kilo (grammage, perte,
        # transport et taxes ne se comparent pas à l'œil).
        #
        # Le calcul est pur — Decimal, aucun accès base : le refaire par ligne ne
        # coûte rien.
        from app.services.pricing.repository import declinaison_to_pricing_material

        reglages = load_pricing_settings(conn)

        def _cout_m2(base: dict, prix: Any) -> Optional[float]:
            if not prix:
                return None
            try:
                return float(
                    compute_material_price_per_m2(
                        declinaison_to_pricing_material({**base, "unit_price": prix}),
                        reglages,
                    ).price_eur_per_m2
                )
            except PricingError:
                # Réglages incomplets : la fiche le dira, la liste ne doit pas
                # tomber pour autant.
                return None

        for m in materials:
            for d in m.get("declinaisons", []):
                base = {
                    **d,
                    "declinaison_id": d["id"],
                    "reference": m["reference"],
                    "libelle": d["libelle"],
                }
                d["cout_eur_m2"] = _cout_m2(base, d.get("unit_price"))
                for ligne in d.get("lignes", []):
                    # La ligne apporte le tarif de SON fournisseur (devise, base
                    # de prix, transport, taxes). Le calquer sur la déclinaison
                    # reviendrait à comparer deux fournisseurs avec le transport
                    # d'un seul — c'était le défaut qu'on corrige.
                    ligne["cout_eur_m2"] = _cout_m2({**base, **ligne}, ligne.get("prix"))
            # « Réglées » veut dire chiffrées : une déclinaison dont on sait
            # sortir un coût au m². `nb_parametrees` comptait autre chose — les
            # fiches ouvertes et enregistrées à la main — si bien qu'une
            # déclinaison affichant son coût pouvait être annoncée non réglée.
            m["nb_chiffrees"] = sum(
                1 for d in m.get("declinaisons", []) if d.get("cout_eur_m2")
            )
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


@router.post("/api/pricing/mystock/declinaisons/deriver")
def deriver_mystock_declinaison(request: Request, body: dict = Body(...)):
    """Nouvelle déclinaison reprenant tous les réglages d'une autre, sauf sa valeur."""
    user = _require_write(request)
    with get_db() as conn:
        res = mystock_prix.deriver_declinaison(
            conn, declinaison_id=_decl_id(body), user_name=user.get("nom")
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("reason", "Création refusée"))
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


@router.post("/api/pricing/mystock/prix-matiere")
def set_mystock_prix_matiere(request: Request, body: dict = Body(...)):
    """Fixe le prix d'achat d'une matière — donc de toutes ses déclinaisons.

    C'est le geste de la liste des matières : ni la laize ni le grammage ne
    changent le prix à l'unité, une seule saisie suffit. Le détail par
    déclinaison reste accessible sur la fiche, pour les cas où un fournisseur
    diffère d'une laize à l'autre.
    """
    user = _require_write(request)
    try:
        prix = float(body.get("prix"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="prix invalide") from None
    matiere_id = _opt_int(body, "matiere_id")
    if not matiere_id:
        raise HTTPException(status_code=400, detail="matiere_id manquant")
    with get_db() as conn:
        res = mystock_prix.set_prix_matiere(
            conn,
            matiere_id=matiere_id,
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
        param["historique"] = mystock_prix.historique_prix(conn, declinaison_id)
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
        param["historique"] = mystock_prix.historique_prix(conn, declinaison_id)
    return param


# ─── Produits devisés à partir des matières MyStock ──────────────────────────


def _cout_produit_mystock(conn, produit: dict, reglages) -> Optional[ProductCostOut]:
    """Prix de revient d'un produit MyStock, au même format que ceux de la base CM."""
    if not produit.get("composants"):
        return None
    try:
        res = mystock_produits.cout_produit(conn, produit, reglages)
    except PricingError:
        # Une déclinaison mal réglée ne doit pas faire tomber la liste entière :
        # le produit s'affiche sans coût, la fiche dira pourquoi.
        return None
    return ProductCostOut(
        total_eur_per_m2=res.total_eur_per_m2,
        margin_pct=res.margin_pct,
        margin_eur_m2=res.margin_eur_m2,
        sell_price_eur_m2=res.sell_price_eur_m2,
        components=[
            ProductComponentOut(
                material_id=c.material_id,
                name=c.name,
                role=c.role,
                price_eur_per_m2=c.price_eur_per_m2,
                share_pct=c.share_pct,
            )
            for c in res.components
        ],
    )


@router.get("/api/pricing/mystock/declinaisons")
def list_mystock_declinaisons(request: Request):
    """
    Toutes les déclinaisons devisables, à plat : de quoi remplir les sélecteurs
    d'un produit sans redemander la liste des matières.
    """
    _require_read(request)
    with get_db() as conn:
        materials = mystock_prix.list_materials(conn, actives_only=True)
        reglages = load_pricing_settings(conn)
        from app.services.pricing.repository import declinaison_to_pricing_material

        out = []
        for m in materials:
            for d in m.get("declinaisons", []):
                cout = None
                if d.get("unit_price"):
                    try:
                        cout = float(
                            compute_material_price_per_m2(
                                declinaison_to_pricing_material(
                                    {**d, "declinaison_id": d["id"],
                                     "reference": m["reference"], "libelle": d["libelle"]}
                                ),
                                reglages,
                            ).price_eur_per_m2
                        )
                    except PricingError:
                        pass
                out.append({
                    "id": d["id"],
                    "matiere_id": m["id"],
                    "categorie": m["categorie"],
                    "reference": m["reference"],
                    "designation": m["designation"],
                    "libelle": d["libelle"],
                    "parametre": d["parametre"],
                    "unit_price": d["unit_price"],
                    "cout_eur_m2": cout,
                    # Les leviers du coût, exposés en clair.
                    #
                    # Le prix d'achat d'une matière ne dépend ni de la laize ni
                    # du grammage : on l'achète au m² ou au kilo. Le COÛT D'UN
                    # PRODUIT, lui, dépend du grammage — une matière payée au
                    # kilo coûte au m² son prix multiplié par son poids au m²,
                    # et ce poids EST le grammage majoré de la perte. Changer
                    # de grammage change donc le prix de revient du produit
                    # sans que le prix d'achat ait bougé d'un centime.
                    #
                    # La laize, elle, n'entre dans aucun de ces calculs : un m²
                    # est un m². Ce qu'elle fait varier, c'est la QUANTITÉ
                    # consommée par une commande, chiffrée par Besoins
                    # matières. On l'expose quand même, pour que l'écran puisse
                    # le dire au lieu de laisser chercher.
                    "price_basis": d.get("price_basis"),
                    "price_currency": d.get("price_currency"),
                    "grammage_gsm": d.get("grammage_gsm"),
                    "perte_pct": d.get("perte_pct"),
                    "weight_per_m2": d.get("weight_per_m2"),
                    "laize_mm": d.get("laize_mm"),
                    "unite": m.get("unite"),
                })
    return {"declinaisons": out}


@router.get("/api/pricing/mystock/produits")
def list_mystock_produits(
    request: Request,
    q: Optional[str] = None,
    active_only: bool = Query(True),
    with_cost: bool = Query(True),
):
    _require_read(request)
    with get_db() as conn:
        produits = mystock_produits.list_produits(conn, q=q, actifs_only=active_only)
        if with_cost:
            reglages = load_pricing_settings(conn)
            for p in produits:
                p["cost"] = _cout_produit_mystock(conn, p, reglages)
    return {"produits": produits}


@router.get("/api/pricing/mystock/produits/{produit_id}")
def get_mystock_produit(request: Request, produit_id: int):
    _require_read(request)
    with get_db() as conn:
        p = mystock_produits.get_produit(conn, produit_id)
        if not p:
            raise HTTPException(status_code=404, detail="Produit introuvable.")
        p["cost"] = _cout_produit_mystock(conn, p, load_pricing_settings(conn))
    return p


@router.post("/api/pricing/mystock/produits")
def create_mystock_produit(request: Request, body: dict = Body(...)):
    user = _require_write(request)
    with get_db() as conn:
        res = mystock_produits.creer_produit(
            conn,
            code=body.get("code", ""),
            designation=body.get("designation", ""),
            composants=body.get("composants"),
            custom_margin_pct=body.get("custom_margin_pct"),
            note=body.get("note"),
            user_name=user.get("nom"),
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("reason", "Création refusée"))
        conn.commit()
        p = res["produit"]
        p["cost"] = _cout_produit_mystock(conn, p, load_pricing_settings(conn))
    return p


@router.patch("/api/pricing/mystock/produits/{produit_id}")
def update_mystock_produit(request: Request, produit_id: int, body: dict = Body(...)):
    user = _require_write(request)
    with get_db() as conn:
        res = mystock_produits.modifier_produit(
            conn, produit_id, patch=body, user_name=user.get("nom")
        )
        if not res.get("ok"):
            raise HTTPException(status_code=400, detail=res.get("reason", "Modification refusée"))
        conn.commit()
        p = res["produit"]
        p["cost"] = _cout_produit_mystock(conn, p, load_pricing_settings(conn))
    return p


@router.delete("/api/pricing/mystock/produits/{produit_id}")
def delete_mystock_produit(request: Request, produit_id: int):
    _require_write(request)
    with get_db() as conn:
        res = mystock_produits.supprimer_produit(conn, produit_id)
        if not res.get("ok"):
            raise HTTPException(status_code=404, detail=res.get("reason", "Produit introuvable"))
        conn.commit()
    return res


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

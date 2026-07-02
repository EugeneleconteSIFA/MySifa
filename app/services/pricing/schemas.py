"""Schémas Pydantic — API /api/pricing."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.material_cost import MC_SETTING_KEYS, MaterialCategoryCode, PriceBasis, PriceCurrency

# ─── Settings ────────────────────────────────────────────────────────────────


class PricingSettingsOut(BaseModel):
    eur_usd_rate: Decimal
    default_container_cost_usd: Decimal
    default_container_kg: Decimal
    default_margin_eur_m2: Decimal
    import_tax_pct: Decimal = Decimal("0")
    transport_cost_fixed_eur: Decimal = Decimal("0")
    charge_production_pct: Decimal = Decimal("0")
    storage_fees_pct: Decimal = Decimal("0")
    eur_usd_rate_updated_at: Optional[str] = None
    eur_usd_rate_source: Optional[str] = None


class PricingSettingsPatch(BaseModel):
    eur_usd_rate: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    default_container_cost_usd: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    default_container_kg: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    default_margin_eur_m2: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    import_tax_pct: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    transport_cost_fixed_eur: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    charge_production_pct: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    storage_fees_pct: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)


class PricingFxRefreshOut(BaseModel):
    eur_usd_rate: Decimal
    eur_usd_rate_updated_at: str
    eur_usd_rate_source: str


# ─── Supplier ────────────────────────────────────────────────────────────────


class McSupplierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    created_at: str
    updated_at: str


class McSupplierCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    country: Optional[str] = Field(None, max_length=120)
    notes: Optional[str] = Field(None, max_length=4000)


class McSupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    country: Optional[str] = Field(None, max_length=120)
    notes: Optional[str] = Field(None, max_length=4000)
    is_active: Optional[bool] = None


# ─── Material ────────────────────────────────────────────────────────────────


class MaterialBreakdownOut(BaseModel):
    raw: Decimal
    transport: Decimal
    fx: Decimal
    tax_uplift: Decimal


class MaterialComputedOut(BaseModel):
    price_eur_per_m2: Decimal
    breakdown: MaterialBreakdownOut


class McMaterialOut(BaseModel):
    id: int
    name: str
    appellation_code: str
    category_id: int
    category_code: MaterialCategoryCode
    supplier_id: Optional[int] = None
    weight_per_m2: Decimal
    weight_gsm: Optional[int] = None
    price_currency: PriceCurrency
    unit_price: Decimal
    price_basis: PriceBasis
    tax_incidence: Decimal
    is_imported: bool
    container_kg: Optional[Decimal] = None
    container_cost_usd: Optional[Decimal] = None
    is_active: bool
    created_at: str
    updated_at: str
    computed: Optional[MaterialComputedOut] = None


class McMaterialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    appellation_code: str = Field(..., min_length=1, max_length=64)
    category_id: int
    supplier_id: Optional[int] = None
    weight_per_m2: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    weight_gsm: Optional[int] = Field(None, ge=0, le=99999)
    price_currency: PriceCurrency = "EUR"
    unit_price: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    price_basis: PriceBasis = "PER_KG"
    tax_incidence: Decimal = Field(default=Decimal("1"), decimal_places=4, max_digits=12)
    is_imported: bool = False
    container_kg: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    container_cost_usd: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    price_history_source: Optional[str] = Field(None, max_length=500)


class McMaterialUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    appellation_code: Optional[str] = Field(None, min_length=1, max_length=64)
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    weight_per_m2: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    weight_gsm: Optional[int] = Field(None, ge=0, le=99999)
    price_currency: Optional[PriceCurrency] = None
    unit_price: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    price_basis: Optional[PriceBasis] = None
    tax_incidence: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    is_imported: Optional[bool] = None
    container_kg: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    container_cost_usd: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    is_active: Optional[bool] = None
    price_history_source: Optional[str] = Field(None, max_length=500)


class McMaterialPriceHistoryOut(BaseModel):
    id: int
    material_id: int
    unit_price: Decimal
    price_currency: PriceCurrency
    tax_incidence: Decimal
    effective_date: str
    source: Optional[str] = None
    created_by: Optional[int] = None
    created_at: str


# ─── Product ─────────────────────────────────────────────────────────────────


class ProductComponentOut(BaseModel):
    material_id: int
    name: str
    role: str
    price_eur_per_m2: Decimal
    share_pct: Decimal
    breakdown: Optional[MaterialBreakdownOut] = None


class ProductCostOut(BaseModel):
    total_eur_per_m2: Decimal
    margin_eur_m2: Decimal
    sell_price_eur_m2: Decimal
    components: list[ProductComponentOut]


class McProductOut(BaseModel):
    id: int
    code: str
    name: str
    frontal_id: Optional[int] = None
    adhesif_id: Optional[int] = None
    silicone_id: Optional[int] = None
    glassine_id: Optional[int] = None
    extra_material_ids: list[int] = Field(default_factory=list)
    custom_margin_eur_m2: Optional[Decimal] = None
    is_active: bool
    created_at: str
    updated_at: str
    cost: Optional[ProductCostOut] = None


class McProductCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    frontal_id: Optional[int] = None
    adhesif_id: Optional[int] = None
    silicone_id: Optional[int] = None
    glassine_id: Optional[int] = None
    extra_material_ids: list[int] = Field(default_factory=list)
    custom_margin_eur_m2: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)


class McProductUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=64)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    frontal_id: Optional[int] = None
    adhesif_id: Optional[int] = None
    silicone_id: Optional[int] = None
    glassine_id: Optional[int] = None
    extra_material_ids: Optional[list[int]] = None
    custom_margin_eur_m2: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    is_active: Optional[bool] = None


class ProductPreviewIn(BaseModel):
    frontal_id: Optional[int] = None
    adhesif_id: Optional[int] = None
    silicone_id: Optional[int] = None
    glassine_id: Optional[int] = None
    extra_material_ids: list[int] = Field(default_factory=list)
    custom_margin_eur_m2: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)


class MaterialPreviewIn(BaseModel):
    """Preview prix €/m² sans persistance (formulaire matière)."""

    unit_price: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    weight_per_m2: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    price_currency: PriceCurrency = "EUR"
    price_basis: PriceBasis = "PER_KG"
    tax_incidence: Decimal = Field(default=Decimal("1"), decimal_places=4, max_digits=12)
    is_imported: bool = False
    container_kg: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    container_cost_usd: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)


class PricingDashboardProductRow(BaseModel):
    id: int
    code: str
    name: str
    total_eur_per_m2: Decimal
    sell_price_eur_per_m2: Decimal


class PricingDashboardOut(BaseModel):
    materials_active: int
    products_active: int
    eur_usd_rate: Decimal
    eur_usd_rate_updated_at: Optional[str] = None
    eur_usd_rate_source: Optional[str] = None
    avg_sell_price_eur_m2: Optional[Decimal] = None
    top_products: list[PricingDashboardProductRow]


class McMaterialCategoryOut(BaseModel):
    id: int
    code: MaterialCategoryCode
    label: str
    sort_order: int


# Garde-fou import settings keys
_PRICING_SETTING_KEYS = tuple(MC_SETTING_KEYS)

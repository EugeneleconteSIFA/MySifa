"""
MySifa — Calcul des coûts matières (schéma v78).

Tables SQLite : mc_setting, mc_supplier, mc_material_category, mc_material,
mc_material_price_history, mc_product, mc_product_extra_material.

Pas d'ORM : ces modèles servent de contrat API / validation (Pydantic).
L'historique des prix est inséré côté applicatif lors des MAJ de mc_material.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ─── Enums (miroir CHECK SQLite) ─────────────────────────────────────────────

MaterialCategoryCode = Literal["FRONTAL", "ADHESIF", "SILICONE", "GLASSINE", "AUTRE"]
PriceCurrency = Literal["EUR", "USD"]
PriceBasis = Literal["PER_KG", "PER_M2"]

# ─── Settings (singleton key/value) ────────────────────────────────────────────

MC_SETTING_KEYS = frozenset(
    {
        "eur_usd_rate",
        "default_container_cost_usd",
        "default_container_kg",
        "default_margin_eur_m2",
        "import_tax_pct",
    }
)

MC_SETTING_DEFAULTS: dict[str, Decimal] = {
    "eur_usd_rate": Decimal("0.85"),
    "default_container_cost_usd": Decimal("4000"),
    "default_container_kg": Decimal("26000"),
    "default_margin_eur_m2": Decimal("0.06"),
    "import_tax_pct": Decimal("0"),
}


class McDecimalModel(BaseModel):
    """Base : décimaux métier en Decimal (précision 12,4 côté validation)."""

    model_config = ConfigDict(from_attributes=True)

    @staticmethod
    def _quantize_decimal(v: Decimal) -> Decimal:
        return v.quantize(Decimal("0.0001"))


class McSetting(BaseModel):
    key: str
    value_decimal: Decimal = Field(..., decimal_places=4, max_digits=12)
    updated_at: Optional[datetime] = None
    updated_by: Optional[int] = None

    @field_validator("key")
    @classmethod
    def key_must_be_known(cls, v: str) -> str:
        if v not in MC_SETTING_KEYS:
            raise ValueError(f"Clé de paramètre inconnue : {v}")
        return v


class McSettingUpdate(BaseModel):
    value_decimal: Decimal = Field(..., decimal_places=4, max_digits=12)


# ─── Supplier ────────────────────────────────────────────────────────────────


class McSupplierBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    country: Optional[str] = Field(None, max_length=120)
    notes: Optional[str] = Field(None, max_length=4000)
    is_active: bool = True


class McSupplierCreate(McSupplierBase):
    pass


class McSupplierUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    country: Optional[str] = Field(None, max_length=120)
    notes: Optional[str] = Field(None, max_length=4000)
    is_active: Optional[bool] = None


class McSupplier(McSupplierBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


# ─── Material category ───────────────────────────────────────────────────────


class McMaterialCategory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: MaterialCategoryCode
    label: str
    sort_order: int = 0


# ─── Material ────────────────────────────────────────────────────────────────


class McMaterialBase(BaseModel):
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
    is_active: bool = True


class McMaterialCreate(McMaterialBase):
    pass


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
    price_history_source: Optional[str] = Field(
        None,
        max_length=500,
        description="Libellé source pour mc_material_price_history si le prix change.",
    )


class McMaterial(McMaterialBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


# ─── Material price history ──────────────────────────────────────────────────


class McMaterialPriceHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    material_id: int
    unit_price: Decimal = Field(..., decimal_places=4, max_digits=12)
    price_currency: PriceCurrency
    tax_incidence: Decimal = Field(default=Decimal("1"), decimal_places=4, max_digits=12)
    effective_date: date
    source: Optional[str] = Field(None, max_length=500)
    created_by: Optional[int] = None
    created_at: datetime


class McMaterialPriceHistoryCreate(BaseModel):
    material_id: int
    unit_price: Decimal = Field(..., decimal_places=4, max_digits=12)
    price_currency: PriceCurrency
    tax_incidence: Decimal = Field(default=Decimal("1"), decimal_places=4, max_digits=12)
    effective_date: date
    source: Optional[str] = Field(None, max_length=500)


# ─── Product ─────────────────────────────────────────────────────────────────


class McProductBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=255)
    frontal_id: Optional[int] = None
    adhesif_id: Optional[int] = None
    silicone_id: Optional[int] = None
    glassine_id: Optional[int] = None
    extra_material_ids: list[int] = Field(default_factory=list)
    custom_margin_eur_m2: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    is_active: bool = True


class McProductCreate(McProductBase):
    pass


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


class McProduct(McProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


# ─── Calcul (lecture seule, pour phase API ultérieure) ─────────────────────────


class McProductCostBreakdown(BaseModel):
    """Résultat de calcul €/m² — sans persistance."""

    product_id: int
    product_code: str
    margin_eur_m2: Decimal
    components_eur_m2: dict[str, Decimal]
    total_before_margin_eur_m2: Decimal
    total_eur_m2: Decimal

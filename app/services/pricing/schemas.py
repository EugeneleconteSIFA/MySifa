"""Schémas Pydantic — API /api/pricing."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.material_cost import (
    MC_SETTING_KEYS,
    MaterialCategoryCode,
    PriceBasis,
    PriceCurrency,
    TransportMode,
)

# ─── Settings ────────────────────────────────────────────────────────────────


class PricingSettingsOut(BaseModel):
    eur_usd_rate: Decimal
    default_container_cost_usd: Decimal
    default_container_kg: Decimal
    default_margin_pct: Decimal
    default_margin_eur_m2: Decimal = Decimal("0")
    import_tax_pct: Decimal = Decimal("0")
    transport_cost_fixed_eur: Decimal = Decimal("0")
    charge_production_pct: Decimal = Decimal("0")
    storage_fees_pct: Decimal = Decimal("0")
    default_half_container_cost_eur: Decimal = Decimal("0")
    logistique_qte_m2_container_complet: Decimal = Decimal("0")
    logistique_qte_m2_demi_container: Decimal = Decimal("0")
    eur_usd_rate_updated_at: Optional[str] = None
    eur_usd_rate_source: Optional[str] = None


class PricingSettingsPatch(BaseModel):
    eur_usd_rate: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    default_container_cost_usd: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    default_container_kg: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    default_margin_pct: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    default_margin_eur_m2: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    import_tax_pct: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    transport_cost_fixed_eur: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    charge_production_pct: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    storage_fees_pct: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    default_half_container_cost_eur: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    logistique_qte_m2_container_complet: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    logistique_qte_m2_demi_container: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)


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
    """raw + transport + fx + tax_uplift = price_eur_per_m2 (raw/transport en devise d'achat)."""

    raw: Decimal
    transport: Decimal
    fx: Decimal
    tax_uplift: Decimal
    currency: PriceCurrency = "EUR"
    price_basis: PriceBasis = "PER_KG"
    fx_rate: Decimal = Decimal("1")
    weight_per_m2: Decimal = Decimal("0")
    unit_price_src: Decimal = Decimal("0")
    transport_src: Decimal = Decimal("0")
    subtotal_src: Decimal = Decimal("0")
    subtotal_eur: Decimal = Decimal("0")
    transport_eur_m2: Decimal = Decimal("0")
    transport_pct_effective: Decimal = Decimal("0")
    taxes_src: Decimal = Decimal("0")
    taxe_pct: Decimal = Decimal("0")


class MaterialComputedOut(BaseModel):
    price_eur_per_m2: Decimal
    breakdown: MaterialBreakdownOut
    # Marge par défaut appliquée si la matière est vendue telle quelle.
    margin_pct: Decimal = Decimal("0")
    margin_eur_m2: Decimal = Decimal("0")
    sell_price_eur_m2: Decimal = Decimal("0")


class MaterialMystockOut(BaseModel):
    """Prix piloté par MyStock quand la matière y est appairée."""

    matiere_id: int
    declinaison_id: Optional[int] = None
    reference: Optional[str] = None
    categorie: Optional[str] = None
    unit_price: Decimal
    price_currency: PriceCurrency = "EUR"
    price_basis: PriceBasis = "PER_M2"
    detail: Optional[str] = None


class McMaterialOut(BaseModel):
    id: int
    name: str
    appellation_code: str
    category_id: int
    category_code: MaterialCategoryCode
    supplier_id: Optional[int] = None
    fournisseur_fsc_id: Optional[int] = None
    fournisseur_nom: Optional[str] = None
    weight_per_m2: Decimal
    weight_gsm: Optional[int] = None
    price_currency: PriceCurrency
    unit_price: Decimal
    price_basis: PriceBasis
    # Taxes d'importation en % du sous-total d'achat (6 = +6 %).
    taxe_pct: Decimal = Decimal("0")
    is_imported: bool
    # La matière entre-t-elle dans l'assiette de marge ?
    applique_marge: bool = True
    # Grammage saisi (g/m²) et perte (%) : weight_per_m2 en découle.
    grammage_gsm: Decimal = Decimal("0")
    perte_pct: Decimal = Decimal("0")
    transport_mode: TransportMode = "AMOUNT"
    transport_unit_price: Decimal = Decimal("0")
    transport_pct: Decimal = Decimal("0")
    transport_cout: Decimal = Decimal("0")
    transport_quantite: Decimal = Decimal("0")
    container_kg: Optional[Decimal] = None
    container_cost_usd: Optional[Decimal] = None
    is_active: bool
    created_at: str
    updated_at: str
    mystock: Optional[MaterialMystockOut] = None
    computed: Optional[MaterialComputedOut] = None


class McMaterialCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    appellation_code: str = Field(..., min_length=1, max_length=64)
    category_id: int
    supplier_id: Optional[int] = None
    fournisseur_fsc_id: Optional[int] = None
    weight_per_m2: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    weight_gsm: Optional[int] = Field(None, ge=0, le=99999)
    price_currency: PriceCurrency = "EUR"
    unit_price: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    price_basis: PriceBasis = "PER_KG"
    taxe_pct: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    is_imported: bool = False
    applique_marge: bool = True
    grammage_gsm: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    perte_pct: Decimal = Field(default=Decimal("9"), decimal_places=4, max_digits=12)
    transport_mode: TransportMode = "AMOUNT"
    transport_unit_price: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    transport_pct: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    transport_cout: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=14)
    transport_quantite: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=14)
    container_kg: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    container_cost_usd: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    price_history_source: Optional[str] = Field(None, max_length=500)


class McMaterialUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    appellation_code: Optional[str] = Field(None, min_length=1, max_length=64)
    category_id: Optional[int] = None
    supplier_id: Optional[int] = None
    fournisseur_fsc_id: Optional[int] = None
    weight_per_m2: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    weight_gsm: Optional[int] = Field(None, ge=0, le=99999)
    price_currency: Optional[PriceCurrency] = None
    unit_price: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    price_basis: Optional[PriceBasis] = None
    taxe_pct: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    is_imported: Optional[bool] = None
    applique_marge: Optional[bool] = None
    grammage_gsm: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    perte_pct: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    transport_mode: Optional[TransportMode] = None
    transport_unit_price: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    transport_pct: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    transport_cout: Optional[Decimal] = Field(None, decimal_places=4, max_digits=14)
    transport_quantite: Optional[Decimal] = Field(None, decimal_places=4, max_digits=14)
    container_kg: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    container_cost_usd: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    is_active: Optional[bool] = None
    price_history_source: Optional[str] = Field(None, max_length=500)


class McMaterialPriceHistoryOut(BaseModel):
    id: int
    material_id: int
    unit_price: Decimal
    price_currency: PriceCurrency
    # Pourcentage de taxes en vigueur à la date de l'enregistrement.
    taxe_pct: Decimal
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
    margin_pct: Decimal = Decimal("0")
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
    custom_margin_pct: Optional[Decimal] = None
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
    custom_margin_pct: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)


class McProductUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=1, max_length=64)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    frontal_id: Optional[int] = None
    adhesif_id: Optional[int] = None
    silicone_id: Optional[int] = None
    glassine_id: Optional[int] = None
    extra_material_ids: Optional[list[int]] = None
    custom_margin_pct: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    is_active: Optional[bool] = None


class ProductPreviewIn(BaseModel):
    frontal_id: Optional[int] = None
    adhesif_id: Optional[int] = None
    silicone_id: Optional[int] = None
    glassine_id: Optional[int] = None
    extra_material_ids: list[int] = Field(default_factory=list)
    custom_margin_pct: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)


class MaterialPreviewIn(BaseModel):
    """Preview prix €/m² sans persistance (formulaire matière)."""

    unit_price: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    weight_per_m2: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    price_currency: PriceCurrency = "EUR"
    price_basis: PriceBasis = "PER_KG"
    taxe_pct: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    is_imported: bool = False
    applique_marge: bool = True
    transport_mode: TransportMode = "AMOUNT"
    transport_unit_price: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    transport_pct: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=12)
    transport_cout: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=14)
    transport_quantite: Decimal = Field(default=Decimal("0"), decimal_places=4, max_digits=14)
    container_kg: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    container_cost_usd: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)
    # Taux USD → EUR d'essai : le panneau Paramètres recalcule la fiche pendant
    # qu'on tape le taux, sans rien enregistrer. Absent, c'est celui de la base
    # qui s'applique — « Appliquer » reste seul à graver un taux pour toutes les
    # matières.
    eur_usd_rate: Optional[Decimal] = Field(None, decimal_places=4, max_digits=12)


class McMaterialCategoryOut(BaseModel):
    id: int
    code: MaterialCategoryCode
    label: str
    sort_order: int


# Garde-fou import settings keys
_PRICING_SETTING_KEYS = tuple(MC_SETTING_KEYS)

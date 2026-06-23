"""Types d'entrée / sortie du moteur pricing (sans Pydantic — pur Python)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Optional

PriceCurrency = Literal["EUR", "USD"]
PriceBasis = Literal["PER_KG", "PER_M2"]


@dataclass(frozen=True)
class PricingSettings:
    """Paramètres globaux (mc_setting)."""

    eur_usd_rate: Decimal
    default_container_cost_usd: Decimal
    default_container_kg: Decimal
    default_margin_eur_m2: Decimal
    # Taxe d'importation appliquée à la valorisation MP quand le flag est coché sur
    # une référence (multiplicatif : prix × (1 + import_tax_pct / 100)). 0 par défaut.
    import_tax_pct: Decimal = Decimal("0")
    # Forfait transport (€) ajouté UNE SEULE FOIS à la valorisation d'une référence
    # quand le flag cout_transport_inclus est coché, APRÈS les multiplicateurs USD/taxe.
    transport_cost_fixed_eur: Decimal = Decimal("0")


@dataclass(frozen=True)
class PricingMaterial:
    """Matière — champs nécessaires au calcul uniquement."""

    id: int
    name: str
    unit_price: Decimal
    weight_per_m2: Decimal
    price_currency: PriceCurrency
    price_basis: PriceBasis
    tax_incidence: Decimal = Decimal("1")
    is_imported: bool = False
    container_kg: Optional[Decimal] = None
    container_cost_usd: Optional[Decimal] = None


@dataclass(frozen=True)
class PricingProduct:
    """Produit fini — composition et marge optionnelle."""

    id: int
    code: str
    name: str
    frontal_id: Optional[int] = None
    adhesif_id: Optional[int] = None
    silicone_id: Optional[int] = None
    glassine_id: Optional[int] = None
    extra_material_ids: tuple[int, ...] = ()
    custom_margin_eur_m2: Optional[Decimal] = None


@dataclass(frozen=True)
class MaterialPriceBreakdown:
    """Décomposition €/m² avant taxe : raw + transport + fx + tax_uplift = price_eur_per_m2."""

    raw: Decimal
    transport: Decimal
    fx: Decimal
    tax_uplift: Decimal


@dataclass(frozen=True)
class MaterialPriceResult:
    price_eur_per_m2: Decimal
    breakdown: MaterialPriceBreakdown


@dataclass(frozen=True)
class ProductComponentCost:
    material_id: int
    name: str
    role: str
    price_eur_per_m2: Decimal
    share_pct: Decimal


@dataclass(frozen=True)
class ProductCostResult:
    total_eur_per_m2: Decimal
    components: tuple[ProductComponentCost, ...]
    margin_eur_m2: Decimal
    sell_price_eur_m2: Decimal

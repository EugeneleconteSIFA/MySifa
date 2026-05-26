"""
Calcul pur des coûts matières €/m².

Aucun accès DB ni HTTP — entrées typées, sorties arrondies à 4 décimales.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Mapping, Optional

from app.services.pricing.errors import PricingError
from app.services.pricing.settings import validate_pricing_settings
from app.services.pricing.types import (
    MaterialPriceBreakdown,
    MaterialPriceResult,
    PricingMaterial,
    PricingProduct,
    PricingSettings,
    ProductComponentCost,
    ProductCostResult,
)

Q4 = Decimal("0.0001")
Q2 = Decimal("0.01")
_ZERO = Decimal("0")
_ONE = Decimal("1")

_COMPONENT_ROLES: tuple[tuple[str, str], ...] = (
    ("frontal_id", "frontal"),
    ("adhesif_id", "adhesif"),
    ("silicone_id", "silicone"),
    ("glassine_id", "glassine"),
)


def _q4(value: Decimal) -> Decimal:
    return value.quantize(Q4, rounding=ROUND_HALF_UP)


def _q2(value: Decimal) -> Decimal:
    return value.quantize(Q2, rounding=ROUND_HALF_UP)


def _tax_uplift(pre_tax: Decimal, tax_incidence: Decimal) -> Decimal:
    if tax_incidence <= _ONE:
        return _ZERO
    return pre_tax * (tax_incidence - _ONE)


def _transport_usd_per_kg(material: PricingMaterial, settings: PricingSettings) -> Decimal:
    container_cost = (
        material.container_cost_usd
        if material.container_cost_usd is not None
        else settings.default_container_cost_usd
    )
    container_kg = (
        material.container_kg if material.container_kg is not None else settings.default_container_kg
    )
    if container_kg <= 0:
        raise PricingError(
            f"container_kg invalide pour la matière « {material.name} » (id={material.id})."
        )
    return container_cost / container_kg


def compute_material_price_per_m2(
    material: PricingMaterial,
    settings: PricingSettings | Mapping[str, Any] | None,
) -> MaterialPriceResult:
    """
    Prix €/m² d'une matière avec décomposition traçable.

    breakdown.raw + breakdown.transport + breakdown.fx + breakdown.tax_uplift
    = price_eur_per_m2 (à 4 décimales près).
    """
    s = validate_pricing_settings(settings)

    if material.weight_per_m2 < 0:
        raise PricingError(f"Poids au m² invalide pour « {material.name} ».")
    if material.unit_price < 0:
        raise PricingError(f"Prix unitaire invalide pour « {material.name} ».")
    if material.tax_incidence <= 0:
        raise PricingError(f"tax_incidence invalide pour « {material.name} ».")

    tax = material.tax_incidence
    w = material.weight_per_m2
    rate = s.eur_usd_rate

    raw = _ZERO
    transport = _ZERO
    fx = _ZERO

    transport_usd_kg = _ZERO
    if material.is_imported and material.price_basis == "PER_KG":
        transport_usd_kg = _transport_usd_per_kg(material, s)

    if material.price_basis == "PER_KG":
        if material.price_currency == "USD":
            raw_usd_per_m2 = material.unit_price * w
            transport_usd_per_m2 = transport_usd_kg * w
            raw = raw_usd_per_m2 * rate
            transport = transport_usd_per_m2 * rate
        else:
            # EUR/kg — transport import converti en EUR/kg si applicable
            transport_eur_per_kg = transport_usd_kg * rate if material.is_imported else _ZERO
            raw = material.unit_price * w
            transport = transport_eur_per_kg * w

    elif material.price_basis == "PER_M2":
        if material.price_currency == "USD":
            raw_usd = material.unit_price
            if material.is_imported:
                transport = transport_usd_kg * w * rate
            fx = raw_usd * rate
            raw = _ZERO
        else:
            raw = material.unit_price
            if material.is_imported:
                transport = transport_usd_kg * w * rate
    else:
        raise PricingError(f"price_basis inconnu pour « {material.name} ».")

    pre_tax = raw + transport + fx
    uplift = _tax_uplift(pre_tax, tax)
    total = pre_tax * tax

    breakdown = MaterialPriceBreakdown(
        raw=_q4(raw),
        transport=_q4(transport),
        fx=_q4(fx),
        tax_uplift=_q4(uplift),
    )
    price = _q4(total)

    # Cohérence : somme des lignes = total (après quantize)
    parts_sum = _q4(breakdown.raw + breakdown.transport + breakdown.fx + breakdown.tax_uplift)
    if parts_sum != price:
        # Ajustement résiduel d'arrondi sur tax_uplift
        delta = price - parts_sum
        breakdown = MaterialPriceBreakdown(
            raw=breakdown.raw,
            transport=breakdown.transport,
            fx=breakdown.fx,
            tax_uplift=_q4(breakdown.tax_uplift + delta),
        )

    return MaterialPriceResult(price_eur_per_m2=price, breakdown=breakdown)


def compute_product_cost(
    product: PricingProduct,
    materials_map: Mapping[int, PricingMaterial],
    settings: PricingSettings | Mapping[str, Any] | None,
) -> ProductCostResult:
    """
    Coût €/m² d'un produit = somme des composants + marge de vente.
    Les composants sans FK (ex. silicone absent) sont ignorés.
    """
    s = validate_pricing_settings(settings)

    components: list[ProductComponentCost] = []
    total = _ZERO

    for field_name, role in _COMPONENT_ROLES:
        mat_id = getattr(product, field_name)
        if mat_id is None:
            continue
        mat = materials_map.get(mat_id)
        if mat is None:
            raise PricingError(
                f"Matière introuvable (id={mat_id}) pour le produit « {product.code} » ({role})."
            )
        result = compute_material_price_per_m2(mat, s)
        total += result.price_eur_per_m2
        components.append(
            ProductComponentCost(
                material_id=mat.id,
                name=mat.name,
                role=role,
                price_eur_per_m2=result.price_eur_per_m2,
                share_pct=_ZERO,  # recalculé après total
            )
        )

    for idx, mat_id in enumerate(product.extra_material_ids):
        mat = materials_map.get(mat_id)
        if mat is None:
            raise PricingError(
                f"Matière extra introuvable (id={mat_id}) pour le produit « {product.code} »."
            )
        result = compute_material_price_per_m2(mat, s)
        total += result.price_eur_per_m2
        role = f"extra_{idx + 1}"
        components.append(
            ProductComponentCost(
                material_id=mat.id,
                name=mat.name,
                role=role,
                price_eur_per_m2=result.price_eur_per_m2,
                share_pct=_ZERO,
            )
        )

    total_q = _q4(total)
    margin = (
        product.custom_margin_eur_m2
        if product.custom_margin_eur_m2 is not None
        else s.default_margin_eur_m2
    )
    margin_q = _q4(margin)
    sell = _q4(total_q + margin_q)

    if total_q > 0:
        finalized = []
        for c in components:
            pct = _q2((c.price_eur_per_m2 / total_q) * Decimal("100"))
            finalized.append(
                ProductComponentCost(
                    material_id=c.material_id,
                    name=c.name,
                    role=c.role,
                    price_eur_per_m2=c.price_eur_per_m2,
                    share_pct=pct,
                )
            )
        components = finalized
    else:
        components = [
            ProductComponentCost(
                material_id=c.material_id,
                name=c.name,
                role=c.role,
                price_eur_per_m2=c.price_eur_per_m2,
                share_pct=_ZERO,
            )
            for c in components
        ]

    return ProductCostResult(
        total_eur_per_m2=total_q,
        components=tuple(components),
        margin_eur_m2=margin_q,
        sell_price_eur_m2=sell,
    )

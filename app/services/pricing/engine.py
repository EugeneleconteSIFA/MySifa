"""
Calcul pur des coûts matières €/m².

Aucun accès DB ni HTTP — entrées typées, sorties arrondies à 4 décimales.

Formule (v223) :

    prix de revient €/m² = (prix d'achat + transport) × taux de change × incidence taxes

Le transport est saisi sur la matière, dans la DEVISE et la BASE d'achat
(USD/kg si l'achat est en USD/kg, €/m² si l'achat est en €/m²). La calculette
conteneur (coût USD ÷ masse kg × poids) ne sert qu'à PROPOSER une valeur —
elle n'intervient plus dans le calcul.
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
_HUNDRED = Decimal("100")

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


def _fx_rate(material: PricingMaterial, settings: PricingSettings) -> Decimal:
    """Taux appliqué au prix d'achat : 1 en EUR, taux USD→EUR en USD."""
    return settings.eur_usd_rate if material.price_currency == "USD" else _ONE


def suggest_transport_unit_price(
    material: PricingMaterial,
    settings: PricingSettings | Mapping[str, Any] | None,
) -> Optional[Decimal]:
    """
    Valeur de transport proposée par la calculette conteneur, exprimée dans la
    devise et la base d'achat de la matière (donc directement reportable dans le
    champ « transport »). Retourne None si la calculette n'est pas exploitable.
    """
    s = validate_pricing_settings(settings)
    cost_usd = (
        material.container_cost_usd
        if material.container_cost_usd is not None
        else s.default_container_cost_usd
    )
    kg = material.container_kg if material.container_kg is not None else s.default_container_kg
    if kg is None or kg <= 0 or cost_usd is None or cost_usd < 0:
        return None
    usd_per_kg = cost_usd / kg
    # Conversion vers la devise d'achat
    per_kg = usd_per_kg if material.price_currency == "USD" else usd_per_kg * s.eur_usd_rate
    if material.price_basis == "PER_KG":
        return _q4(per_kg)
    if material.price_basis == "PER_M2":
        if material.weight_per_m2 <= 0:
            return None
        return _q4(per_kg * material.weight_per_m2)
    return None


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
    if material.transport_unit_price is not None and material.transport_unit_price < 0:
        raise PricingError(f"Transport invalide pour « {material.name} ».")

    tax = material.tax_incidence
    w = material.weight_per_m2
    rate = _fx_rate(material, s)

    if material.price_basis == "PER_KG":
        # Le prix est au kilo : on passe au m² via le poids. Un poids nul donne un
        # prix nul — on ne lève pas (sinon toute la liste matières tomberait en 422
        # à cause d'une seule référence incomplète) ; l'UI signale le poids manquant.
        factor = w
    elif material.price_basis == "PER_M2":
        factor = _ONE
    else:
        raise PricingError(f"price_basis inconnu pour « {material.name} ».")

    unit_src = material.unit_price
    transport_src = (
        material.transport_unit_price
        if (material.is_imported and material.transport_unit_price)
        else _ZERO
    )

    raw = unit_src * factor
    transport = transport_src * factor
    subtotal_src = raw + transport
    fx = subtotal_src * (rate - _ONE)
    subtotal_eur = subtotal_src * rate
    uplift = subtotal_eur * (tax - _ONE)
    total = subtotal_eur * tax

    breakdown = MaterialPriceBreakdown(
        raw=_q4(raw),
        transport=_q4(transport),
        fx=_q4(fx),
        tax_uplift=_q4(uplift),
        currency=material.price_currency,
        price_basis=material.price_basis,
        fx_rate=_q4(rate),
        weight_per_m2=_q4(w),
        unit_price_src=_q4(unit_src),
        transport_src=_q4(transport_src),
        subtotal_src=_q4(subtotal_src),
        subtotal_eur=_q4(subtotal_eur),
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
            currency=breakdown.currency,
            price_basis=breakdown.price_basis,
            fx_rate=breakdown.fx_rate,
            weight_per_m2=breakdown.weight_per_m2,
            unit_price_src=breakdown.unit_price_src,
            transport_src=breakdown.transport_src,
            subtotal_src=breakdown.subtotal_src,
            subtotal_eur=breakdown.subtotal_eur,
        )

    return MaterialPriceResult(price_eur_per_m2=price, breakdown=breakdown)


def compute_product_cost(
    product: PricingProduct,
    materials_map: Mapping[int, PricingMaterial],
    settings: PricingSettings | Mapping[str, Any] | None,
) -> ProductCostResult:
    """
    Coût €/m² d'un produit = somme des composants + marge de vente.
    La marge est un POURCENTAGE du prix de revient calculé.
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
    margin_pct = (
        product.custom_margin_pct
        if product.custom_margin_pct is not None
        else s.default_margin_pct
    )
    if margin_pct is None:
        margin_pct = _ZERO
    if margin_pct < 0:
        raise PricingError(f"Marge négative pour le produit « {product.code} ».")
    margin_pct_q = _q4(margin_pct)
    margin_q = _q4(total_q * margin_pct_q / _HUNDRED)
    sell = _q4(total_q + margin_q)

    if total_q > 0:
        finalized = []
        for c in components:
            pct = _q2((c.price_eur_per_m2 / total_q) * _HUNDRED)
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
        margin_pct=margin_pct_q,
        margin_eur_m2=margin_q,
        sell_price_eur_m2=sell,
    )

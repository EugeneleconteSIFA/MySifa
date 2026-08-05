"""
Calcul pur des coûts matières €/m².

Aucun accès DB ni HTTP — entrées typées, sorties arrondies à 4 décimales.

Formule :

    prix de revient €/m² = (prix d'achat + transport + taxes) × taux de change

Les taxes sont un POURCENTAGE du sous-total d'achat (6 = +6 %). Elles ne
s'appliquent qu'aux matières importées : une taxe d'importation sur une matière
locale n'aurait pas de sens, et le champ n'est visible que dans l'encadré import.

Les appliquer avant le change plutôt qu'après ne change pas le résultat (une
suite de multiplications), mais donne une lecture directe : ce qu'on paie au
fournisseur, dans sa devise, puis une seule conversion.

Le transport est saisi sur la matière, au choix :
  - mode AMOUNT : un montant dans la DEVISE et la BASE d'achat (USD/kg si l'achat
    est en USD/kg, €/m² si l'achat est en €/m²) ;
  - mode PCT       : un pourcentage du prix d'achat ;
  - mode CONTENEUR : le coût d'un conteneur divisé par ce qu'il transporte ;
  - mode FORFAIT   : un forfait de commande divisé par la quantité commandée.
Il n'est pris en compte que si la matière est marquée importée.
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


def _transport_unit(material: PricingMaterial) -> Decimal:
    """
    Transport ramené à l'unité d'achat (par kg ou par m² selon la base), exprimé
    dans la devise d'achat. Nul si la matière n'est pas marquée importée.
    """
    if not material.is_imported:
        return _ZERO
    mode = material.transport_mode or "AMOUNT"
    if mode == "PCT":
        pct = material.transport_pct or _ZERO
        return material.unit_price * pct / _HUNDRED
    if mode in ("CONTENEUR", "FORFAIT"):
        # Un coût global réparti sur une quantité. Sans quantité, on ne divise
        # pas par zéro : le transport vaut zéro et la fiche le montre.
        quantite = material.transport_quantite or _ZERO
        if quantite <= _ZERO:
            return _ZERO
        return (material.transport_cout or _ZERO) / quantite
    return material.transport_unit_price or _ZERO


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
    if material.taxe_pct is not None and material.taxe_pct < -100:
        raise PricingError(f"Taxe (%) invalide pour « {material.name} ».")
    if material.transport_unit_price is not None and material.transport_unit_price < 0:
        raise PricingError(f"Transport invalide pour « {material.name} ».")
    if material.transport_pct is not None and material.transport_pct < 0:
        raise PricingError(f"Transport (%) invalide pour « {material.name} ».")

    # Une taxe d'importation ne s'applique qu'à une matière importée.
    taxe_pct = (material.taxe_pct or _ZERO) if material.is_imported else _ZERO
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
    transport_src = _transport_unit(material)
    transport_pct_eff = (
        (transport_src / unit_src * _HUNDRED) if unit_src > 0 else _ZERO
    )

    raw = unit_src * factor
    transport = transport_src * factor
    achat_src = raw + transport
    taxes_src = achat_src * taxe_pct / _HUNDRED
    subtotal_src = achat_src + taxes_src
    fx = subtotal_src * (rate - _ONE)
    subtotal_eur = subtotal_src * rate
    uplift = taxes_src * rate
    total = subtotal_eur

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
        transport_eur_m2=_q4(transport * rate),
        transport_pct_effective=_q4(transport_pct_eff),
        taxes_src=_q4(taxes_src),
        taxe_pct=_q4(taxe_pct),
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
            transport_eur_m2=breakdown.transport_eur_m2,
            transport_pct_effective=breakdown.transport_pct_effective,
            taxes_src=breakdown.taxes_src,
            taxe_pct=breakdown.taxe_pct,
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
    # Assiette de marge : seules les matières marquées « marge appliquée » y
    # entrent. Le prix de revient, lui, reste la somme de tout.
    base_marge = _ZERO

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
        if mat.applique_marge:
            base_marge += result.price_eur_per_m2
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
        if mat.applique_marge:
            base_marge += result.price_eur_per_m2
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
    margin_q = _q4(_q4(base_marge) * margin_pct_q / _HUNDRED)
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

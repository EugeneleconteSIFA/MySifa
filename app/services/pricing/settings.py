"""Validation des paramètres globaux."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping, Optional

from app.services.pricing.errors import PricingError
from app.services.pricing.types import PricingSettings

_REQUIRED_KEYS = (
    "eur_usd_rate",
    "default_container_cost_usd",
    "default_container_kg",
    "default_margin_eur_m2",
)
# Clés optionnelles (présentes mais non bloquantes — default appliqué si absent).
_OPTIONAL_KEYS = (
    "import_tax_pct",
    "transport_cost_fixed_eur",
    "charge_production_pct",
    "storage_fees_pct",
    "default_half_container_cost_eur",
    "logistique_qte_m2_container_complet",
    "logistique_qte_m2_demi_container",
)


def _to_decimal(value: Any, field: str) -> Decimal:
    if value is None:
        raise PricingError(f"Paramètre manquant : {field}.")
    if isinstance(value, Decimal):
        d = value
    else:
        try:
            d = Decimal(str(value))
        except Exception as exc:
            raise PricingError(f"Paramètre invalide : {field} (valeur non numérique).") from exc
    return d


def validate_pricing_settings(
    settings: Optional[PricingSettings | Mapping[str, Any]],
) -> PricingSettings:
    """Valide et normalise les paramètres. Lève PricingError si incomplet ou incohérent."""
    if settings is None:
        raise PricingError(
            "Paramètres de calcul manquants — renseigner eur_usd_rate, "
            "default_container_cost_usd, default_container_kg et default_margin_eur_m2."
        )

    if isinstance(settings, PricingSettings):
        s = settings
    elif isinstance(settings, Mapping):
        missing = [k for k in _REQUIRED_KEYS if k not in settings or settings[k] is None]
        if missing:
            raise PricingError(
                "Paramètres de calcul incomplets — clés manquantes : "
                + ", ".join(missing)
                + "."
            )
        tax_raw = settings.get("import_tax_pct")
        transp_raw = settings.get("transport_cost_fixed_eur")
        charge_raw = settings.get("charge_production_pct")
        storage_raw = settings.get("storage_fees_pct")
        half_raw = settings.get("default_half_container_cost_eur")
        qte_full_raw = settings.get("logistique_qte_m2_container_complet")
        qte_half_raw = settings.get("logistique_qte_m2_demi_container")
        s = PricingSettings(
            eur_usd_rate=_to_decimal(settings["eur_usd_rate"], "eur_usd_rate"),
            default_container_cost_usd=_to_decimal(
                settings["default_container_cost_usd"], "default_container_cost_usd"
            ),
            default_container_kg=_to_decimal(settings["default_container_kg"], "default_container_kg"),
            default_margin_eur_m2=_to_decimal(
                settings["default_margin_eur_m2"], "default_margin_eur_m2"
            ),
            import_tax_pct=_to_decimal(tax_raw, "import_tax_pct") if tax_raw is not None else Decimal("0"),
            transport_cost_fixed_eur=_to_decimal(transp_raw, "transport_cost_fixed_eur") if transp_raw is not None else Decimal("0"),
            charge_production_pct=_to_decimal(charge_raw, "charge_production_pct") if charge_raw is not None else Decimal("0"),
            storage_fees_pct=_to_decimal(storage_raw, "storage_fees_pct") if storage_raw is not None else Decimal("0"),
            default_half_container_cost_eur=_to_decimal(half_raw, "default_half_container_cost_eur") if half_raw is not None else Decimal("0"),
            logistique_qte_m2_container_complet=_to_decimal(qte_full_raw, "logistique_qte_m2_container_complet") if qte_full_raw is not None else Decimal("0"),
            logistique_qte_m2_demi_container=_to_decimal(qte_half_raw, "logistique_qte_m2_demi_container") if qte_half_raw is not None else Decimal("0"),
        )
    else:
        raise PricingError("Paramètres de calcul : type non supporté.")

    if s.eur_usd_rate <= 0:
        raise PricingError("eur_usd_rate doit être strictement positif.")
    if s.default_container_cost_usd < 0:
        raise PricingError("default_container_cost_usd ne peut pas être négatif.")
    if s.default_container_kg <= 0:
        raise PricingError("default_container_kg doit être strictement positif.")
    if s.default_margin_eur_m2 < 0:
        raise PricingError("default_margin_eur_m2 ne peut pas être négatif.")
    if s.import_tax_pct < 0:
        raise PricingError("import_tax_pct ne peut pas être négatif.")
    if s.import_tax_pct > 1000:
        raise PricingError("import_tax_pct doit être inférieur à 1000 %.")
    if s.transport_cost_fixed_eur < 0:
        raise PricingError("transport_cost_fixed_eur ne peut pas être négatif.")
    if s.charge_production_pct < 0:
        raise PricingError("charge_production_pct ne peut pas être négatif.")
    if s.charge_production_pct >= 100:
        raise PricingError("charge_production_pct doit être strictement inférieur à 100 %.")
    if s.storage_fees_pct < 0:
        raise PricingError("storage_fees_pct ne peut pas être négatif.")
    if s.storage_fees_pct > 1000:
        raise PricingError("storage_fees_pct doit être inférieur à 1000 %.")
    if s.default_half_container_cost_eur < 0:
        raise PricingError("default_half_container_cost_eur ne peut pas être négatif.")
    if s.logistique_qte_m2_container_complet < 0:
        raise PricingError("logistique_qte_m2_container_complet ne peut pas être négatif.")
    if s.logistique_qte_m2_demi_container < 0:
        raise PricingError("logistique_qte_m2_demi_container ne peut pas être négatif.")

    return s

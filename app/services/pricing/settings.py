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

    return s

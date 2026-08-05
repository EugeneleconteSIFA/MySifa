"""Types d'entrée / sortie du moteur pricing (sans Pydantic — pur Python)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Optional

PriceCurrency = Literal["EUR", "USD"]
PriceBasis = Literal["PER_KG", "PER_M2"]
# Mode de saisie du transport : montant dans la devise/base d'achat, ou
# pourcentage du prix d'achat.
# AMOUNT    : montant à l'unité d'achat (€/kg ou €/m²)
# PCT       : pourcentage du prix d'achat
# CONTENEUR : coût d'un conteneur ÷ quantité qu'il transporte
# FORFAIT   : forfait de commande ÷ quantité commandée
TransportMode = Literal["AMOUNT", "PCT", "CONTENEUR", "FORFAIT"]


@dataclass(frozen=True)
class PricingSettings:
    """Paramètres globaux (mc_setting)."""

    eur_usd_rate: Decimal
    default_container_cost_usd: Decimal
    default_container_kg: Decimal
    # Marge par défaut, en % du prix de revient calculé (v223 — remplace
    # default_margin_eur_m2 qui était un montant absolu en €/m²).
    default_margin_pct: Decimal
    # Taxe d'importation appliquée à la valorisation MP quand le flag est coché sur
    # une référence (multiplicatif : prix × (1 + import_tax_pct / 100)). 0 par défaut.
    import_tax_pct: Decimal = Decimal("0")
    # Forfait transport (€) ajouté UNE SEULE FOIS à la valorisation d'une référence
    # quand le flag cout_transport_inclus est coché, APRÈS les multiplicateurs USD/taxe.
    transport_cost_fixed_eur: Decimal = Decimal("0")
    # Charge de production (%) — appliquée à la valorisation PF en mode
    # « avec charges » : valo_pf_avec = valo_pf * (1 + storage) / (1 - charge/100).
    charge_production_pct: Decimal = Decimal("0")
    # Frais de stockage (%) — appliqués à la valorisation PF en mode « avec charges ».
    storage_fees_pct: Decimal = Decimal("0")
    # Coût du demi-container (EUR) — info affichée, pas utilisé par le pricing engine.
    default_half_container_cost_eur: Decimal = Decimal("0")
    # Quantités m² de matière par container (renseignées via /settings > Logistique).
    logistique_qte_m2_container_complet: Decimal = Decimal("0")
    logistique_qte_m2_demi_container: Decimal = Decimal("0")
    # Legacy — conservé pour compatibilité de lecture, plus utilisé par le moteur.
    default_margin_eur_m2: Decimal = Decimal("0")


@dataclass(frozen=True)
class PricingMaterial:
    """Matière — champs nécessaires au calcul uniquement."""

    id: int
    name: str
    unit_price: Decimal
    weight_per_m2: Decimal
    price_currency: PriceCurrency
    price_basis: PriceBasis
    # Taxes d'importation, en POURCENTAGE du sous-total d'achat (6 = +6 %).
    # Ignorées si la matière n'est pas importée.
    taxe_pct: Decimal = Decimal("0")
    is_imported: bool = False
    # Une matière peut être exclue de l'assiette de marge : elle entre dans le
    # prix de revient mais on ne cherche pas à marger dessus (refacturation
    # à l'euro près, matière fournie par le client…).
    applique_marge: bool = True
    # Mode de saisie du transport (ignoré si is_imported est faux).
    transport_mode: TransportMode = "AMOUNT"
    # Mode AMOUNT : transport dans la DEVISE et la BASE d'achat (USD/kg si l'achat
    # est en USD/kg, €/m² si l'achat est en €/m²).
    transport_unit_price: Decimal = Decimal("0")
    # Mode PCT : transport = prix d'achat × transport_pct / 100.
    transport_pct: Decimal = Decimal("0")
    # Modes CONTENEUR et FORFAIT : un coût réparti sur une quantité.
    transport_cout: Decimal = Decimal("0")
    transport_quantite: Decimal = Decimal("0")
    # Legacy conteneur — conservé en base, plus utilisé ni affiché.
    container_kg: Optional[Decimal] = None
    container_cost_usd: Optional[Decimal] = None


@dataclass(frozen=True)
class PricingProduct:
    """Produit fini — composition et marge optionnelle (en % du prix de revient)."""

    id: int
    code: str
    name: str
    frontal_id: Optional[int] = None
    adhesif_id: Optional[int] = None
    silicone_id: Optional[int] = None
    glassine_id: Optional[int] = None
    extra_material_ids: tuple[int, ...] = ()
    custom_margin_pct: Optional[Decimal] = None


@dataclass(frozen=True)
class MaterialPriceBreakdown:
    """
    Décomposition du prix €/m².

    Invariant : raw + transport + fx + tax_uplift = price_eur_per_m2.

    - raw       : prix d'achat ramené au m², exprimé dans la devise d'achat
    - transport : transport ramené au m², exprimé dans la devise d'achat
    - fx        : impact du change (0 si l'achat est déjà en EUR)
    - tax_uplift: impact des taxes d'importation, en EUR (négatif si taxe < 0)

    Les champs suffixés _src sont les valeurs saisies (devise et base d'achat),
    conservées pour l'affichage du tableau récapitulatif.
    """

    raw: Decimal
    transport: Decimal
    fx: Decimal
    tax_uplift: Decimal
    currency: str = "EUR"
    price_basis: str = "PER_KG"
    fx_rate: Decimal = Decimal("1")
    weight_per_m2: Decimal = Decimal("0")
    unit_price_src: Decimal = Decimal("0")
    transport_src: Decimal = Decimal("0")
    subtotal_src: Decimal = Decimal("0")
    subtotal_eur: Decimal = Decimal("0")
    # Transport ramené en €/m² (après poids et change) — affichage.
    transport_eur_m2: Decimal = Decimal("0")
    # Transport en % du prix d'achat, quel que soit le mode de saisie.
    transport_pct_effective: Decimal = Decimal("0")
    # Taxes dans la devise et la base d'achat, et le taux retenu.
    taxes_src: Decimal = Decimal("0")
    taxe_pct: Decimal = Decimal("0")


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
    margin_pct: Decimal
    margin_eur_m2: Decimal
    sell_price_eur_m2: Decimal

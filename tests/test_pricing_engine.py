"""Tests unitaires — moteur pricing (pur, sans I/O)."""

from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.pricing import (
    PricingError,
    PricingMaterial,
    PricingProduct,
    PricingSettings,
    compute_material_price_per_m2,
    compute_product_cost,
)

D = Decimal


def _settings(**overrides) -> PricingSettings:
    base = dict(
        eur_usd_rate=D("0.85"),
        default_container_cost_usd=D("4000"),
        default_container_kg=D("26000"),
        default_margin_pct=D("6"),
    )
    base.update(overrides)
    return PricingSettings(**base)


def _breakdown_sum(result) -> Decimal:
    b = result.breakdown
    return b.raw + b.transport + b.fx + b.tax_uplift


class TestComputeMaterialPricePerM2(unittest.TestCase):
    def test_local_eur_per_kg_simple(self):
        mat = PricingMaterial(
            id=1,
            name="Frontal local",
            unit_price=D("2"),
            weight_per_m2=D("0.1"),
            price_currency="EUR",
            price_basis="PER_KG",
            taxe_pct=D("0"),
            is_imported=False,
        )
        res = compute_material_price_per_m2(mat, _settings())
        self.assertEqual(res.price_eur_per_m2, D("0.2000"))
        self.assertEqual(res.breakdown.raw, D("0.2000"))
        self.assertEqual(res.breakdown.transport, D("0"))
        self.assertEqual(res.breakdown.fx, D("0"))
        self.assertEqual(res.breakdown.tax_uplift, D("0"))
        self.assertEqual(_breakdown_sum(res), res.price_eur_per_m2)

    def test_imported_usd_per_kg_with_transport(self):
        """(prix + transport) x poids x taux — transport saisi en USD/kg."""
        mat = PricingMaterial(
            id=2,
            name="Adhésif import",
            unit_price=D("3"),
            weight_per_m2=D("0.05"),
            price_currency="USD",
            price_basis="PER_KG",
            taxe_pct=D("0"),
            is_imported=True,
            transport_unit_price=D("0.1538"),
        )
        s = _settings()
        expected = (D("3") + D("0.1538")) * D("0.05") * s.eur_usd_rate
        res = compute_material_price_per_m2(mat, s)
        self.assertEqual(res.price_eur_per_m2, expected.quantize(D("0.0001")))
        self.assertGreater(res.breakdown.transport, D("0"))
        self.assertGreater(res.breakdown.raw, D("0"))
        self.assertLess(res.breakdown.fx, D("0"))  # taux < 1 : le change réduit le prix
        self.assertEqual(_breakdown_sum(res), res.price_eur_per_m2)

    def test_transport_ignored_when_not_imported(self):
        mat = PricingMaterial(
            id=21,
            name="Non importée",
            unit_price=D("3"),
            weight_per_m2=D("0.05"),
            price_currency="EUR",
            price_basis="PER_KG",
            is_imported=False,
            transport_unit_price=D("1"),
        )
        res = compute_material_price_per_m2(mat, _settings())
        self.assertEqual(res.breakdown.transport, D("0"))
        self.assertEqual(res.price_eur_per_m2, D("0.1500"))

    def test_imported_eur_per_m2_with_transport(self):
        """Cas de la matière chinoise facturée au m² : le transport doit compter."""
        mat = PricingMaterial(
            id=22,
            name="Rouleau imprimé",
            unit_price=D("4.0183"),
            weight_per_m2=D("0"),
            price_currency="EUR",
            price_basis="PER_M2",
            taxe_pct=D("-5"),
            is_imported=True,
            transport_unit_price=D("0.25"),
        )
        res = compute_material_price_per_m2(mat, _settings())
        expected = (D("4.0183") + D("0.25")) * D("0.95")
        self.assertEqual(res.price_eur_per_m2, expected.quantize(D("0.0001")))
        self.assertEqual(res.breakdown.transport, D("0.2500"))
        self.assertLess(res.breakdown.tax_uplift, D("0"))
        self.assertEqual(_breakdown_sum(res), res.price_eur_per_m2)

    def test_taxe_en_pourcentage(self):
        """6,5 se lit +6,5 % — plus de multiplicateur à traduire dans sa tête."""
        mat = PricingMaterial(
            id=3,
            name="Glassine taxée",
            unit_price=D("1.5"),
            weight_per_m2=D("0.08"),
            price_currency="EUR",
            price_basis="PER_KG",
            taxe_pct=D("6.5"),
            is_imported=True,
        )
        res = compute_material_price_per_m2(mat, _settings())
        pre = D("1.5") * D("0.08")
        self.assertEqual(res.price_eur_per_m2, (pre * D("1.065")).quantize(D("0.0001")))
        self.assertEqual(res.breakdown.tax_uplift, (pre * D("0.065")).quantize(D("0.0001")))
        self.assertEqual(_breakdown_sum(res), res.price_eur_per_m2)

    def test_transport_en_pourcentage(self):
        """Mode PCT : transport = prix d'achat x %."""
        mat = PricingMaterial(
            id=24,
            name="Import au %",
            unit_price=D("4.0183"),
            weight_per_m2=D("0"),
            price_currency="EUR",
            price_basis="PER_M2",
            is_imported=True,
            transport_mode="PCT",
            transport_pct=D("6"),
            transport_unit_price=D("999"),  # ignoré en mode PCT
        )
        res = compute_material_price_per_m2(mat, _settings())
        expected_transport = (D("4.0183") * D("6") / D("100")).quantize(D("0.0001"))
        self.assertEqual(res.breakdown.transport_src, expected_transport)
        self.assertEqual(res.breakdown.transport_pct_effective, D("6.0000"))
        self.assertEqual(
            res.price_eur_per_m2, (D("4.0183") + expected_transport).quantize(D("0.0001"))
        )
        self.assertEqual(_breakdown_sum(res), res.price_eur_per_m2)

    def test_transport_pct_sur_achat_usd_au_kilo(self):
        """Mode PCT en USD/kg : le % porte sur le prix au kilo, puis poids et change."""
        mat = PricingMaterial(
            id=25,
            name="USD au kilo",
            unit_price=D("2"),
            weight_per_m2=D("0.05"),
            price_currency="USD",
            price_basis="PER_KG",
            is_imported=True,
            transport_mode="PCT",
            transport_pct=D("10"),
        )
        s = _settings()
        res = compute_material_price_per_m2(mat, s)
        self.assertEqual(res.breakdown.transport_src, D("0.2000"))
        expected = (D("2") + D("0.2")) * D("0.05") * s.eur_usd_rate
        self.assertEqual(res.price_eur_per_m2, expected.quantize(D("0.0001")))
        # transport ramené en euros au m² : 0,2 x 0,05 x 0,85
        self.assertEqual(
            res.breakdown.transport_eur_m2,
            (D("0.2") * D("0.05") * s.eur_usd_rate).quantize(D("0.0001")),
        )
        self.assertEqual(res.breakdown.transport_pct_effective, D("10.0000"))

    def test_transport_pct_ignore_si_non_importee(self):
        mat = PricingMaterial(
            id=26,
            name="Locale",
            unit_price=D("2"),
            weight_per_m2=D("0.05"),
            price_currency="EUR",
            price_basis="PER_KG",
            is_imported=False,
            transport_mode="PCT",
            transport_pct=D("10"),
        )
        res = compute_material_price_per_m2(mat, _settings())
        self.assertEqual(res.breakdown.transport_src, D("0"))
        self.assertEqual(res.price_eur_per_m2, D("0.1000"))

    def test_usd_per_m2_rare(self):
        mat = PricingMaterial(
            id=4,
            name="Film USD/m2",
            unit_price=D("1.2"),
            weight_per_m2=D("0.02"),
            price_currency="USD",
            price_basis="PER_M2",
            taxe_pct=D("0"),
            is_imported=False,
        )
        res = compute_material_price_per_m2(mat, _settings())
        self.assertEqual(res.price_eur_per_m2, (D("1.2") * D("0.85")).quantize(D("0.0001")))
        # raw reste en devise d'achat, fx porte l'écart de change (0,85 - 1) x 1,2
        self.assertEqual(res.breakdown.raw, D("1.2000"))
        self.assertEqual(res.breakdown.fx, D("-0.1800"))
        self.assertEqual(_breakdown_sum(res), res.price_eur_per_m2)

    def test_taxe_uniquement_si_importee(self):
        """Une taxe d'importation ne s'applique qu'à une matière importée."""
        base = dict(
            id=20,
            name="Frontal taxé",
            unit_price=D("2"),
            weight_per_m2=D("0.1"),
            price_currency="EUR",
            price_basis="PER_KG",
            taxe_pct=D("10"),
        )
        locale = compute_material_price_per_m2(
            PricingMaterial(**base, is_imported=False), _settings()
        )
        importee = compute_material_price_per_m2(
            PricingMaterial(**base, is_imported=True), _settings()
        )
        self.assertEqual(locale.price_eur_per_m2, D("0.2000"))
        self.assertEqual(importee.price_eur_per_m2, D("0.2200"))
        self.assertEqual(locale.breakdown.tax_uplift, D("0"))
        self.assertEqual(importee.breakdown.tax_uplift, D("0.0200"))

    def test_taxe_avant_le_change(self):
        """Taxes puis change, ou l'inverse : même résultat, lecture plus simple."""
        mat = PricingMaterial(
            id=21,
            name="Import USD taxé",
            unit_price=D("10"),
            weight_per_m2=D("0.1"),
            price_currency="USD",
            price_basis="PER_KG",
            taxe_pct=D("6"),
            is_imported=True,
        )
        s = _settings()
        res = compute_material_price_per_m2(mat, s)
        attendu = (D("10") * D("1.06") * D("0.1") * s.eur_usd_rate).quantize(D("0.0001"))
        self.assertEqual(res.price_eur_per_m2, attendu)
        self.assertEqual(res.breakdown.taxe_pct, D("6.0000"))
        self.assertGreater(res.breakdown.taxes_src, D("0"))

    def test_missing_settings_raises(self):
        mat = PricingMaterial(
            id=5,
            name="X",
            unit_price=D("1"),
            weight_per_m2=D("0.1"),
            price_currency="EUR",
            price_basis="PER_KG",
        )
        with self.assertRaises(PricingError) as ctx:
            compute_material_price_per_m2(mat, None)
        self.assertIn("manquants", str(ctx.exception).lower())

    def test_incomplete_settings_mapping_raises(self):
        mat = PricingMaterial(
            id=6,
            name="Y",
            unit_price=D("1"),
            weight_per_m2=D("0.1"),
            price_currency="EUR",
            price_basis="PER_KG",
        )
        with self.assertRaises(PricingError) as ctx:
            compute_material_price_per_m2(mat, {"eur_usd_rate": "0.85"})
        self.assertIn("incomplets", str(ctx.exception).lower())


class TestComputeProductCost(unittest.TestCase):
    def _four_materials(self):
        return {
            1: PricingMaterial(
                id=1,
                name="Frontal",
                unit_price=D("2"),
                weight_per_m2=D("0.10"),
                price_currency="EUR",
                price_basis="PER_KG",
                taxe_pct=D("0"),
            ),
            2: PricingMaterial(
                id=2,
                name="Adhésif",
                unit_price=D("1"),
                weight_per_m2=D("0.05"),
                price_currency="EUR",
                price_basis="PER_KG",
                taxe_pct=D("0"),
            ),
            3: PricingMaterial(
                id=3,
                name="Silicone",
                unit_price=D("0.5"),
                weight_per_m2=D("0.02"),
                price_currency="EUR",
                price_basis="PER_KG",
                taxe_pct=D("0"),
            ),
            4: PricingMaterial(
                id=4,
                name="Glassine",
                unit_price=D("0.8"),
                weight_per_m2=D("0.09"),
                price_currency="EUR",
                price_basis="PER_KG",
                taxe_pct=D("0"),
            ),
        }

    def test_product_four_components(self):
        mats = self._four_materials()
        product = PricingProduct(
            id=10,
            code="1012",
            name="Produit test",
            frontal_id=1,
            adhesif_id=2,
            silicone_id=3,
            glassine_id=4,
        )
        s = _settings()
        res = compute_product_cost(product, mats, s)

        expected_total = sum(
            compute_material_price_per_m2(m, s).price_eur_per_m2 for m in mats.values()
        ).quantize(D("0.0001"))
        self.assertEqual(res.total_eur_per_m2, expected_total)
        self.assertEqual(len(res.components), 4)
        expected_margin = (expected_total * s.default_margin_pct / D("100")).quantize(D("0.0001"))
        self.assertEqual(res.margin_pct, D("6.0000"))
        self.assertEqual(res.margin_eur_m2, expected_margin)
        self.assertEqual(res.sell_price_eur_m2, (expected_total + expected_margin).quantize(D("0.0001")))
        share_sum = sum(c.share_pct for c in res.components)
        self.assertEqual(share_sum, D("100.00"))

    def test_product_without_silicone(self):
        mats = self._four_materials()
        product = PricingProduct(
            id=11,
            code="1013",
            name="Sans silicone",
            frontal_id=1,
            adhesif_id=2,
            silicone_id=None,
            glassine_id=4,
        )
        s = _settings()
        res = compute_product_cost(product, mats, s)
        self.assertEqual(len(res.components), 3)
        roles = {c.role for c in res.components}
        self.assertNotIn("silicone", roles)
        partial = (
            compute_material_price_per_m2(mats[1], s).price_eur_per_m2
            + compute_material_price_per_m2(mats[2], s).price_eur_per_m2
            + compute_material_price_per_m2(mats[4], s).price_eur_per_m2
        ).quantize(D("0.0001"))
        self.assertEqual(res.total_eur_per_m2, partial)

    def test_matiere_hors_assiette_de_marge(self):
        """Une matière exclue entre dans le prix de revient, pas dans la marge."""
        mats = self._four_materials()
        mats[3] = PricingMaterial(
            id=3,
            name="Silicone refacturé",
            unit_price=D("0.5"),
            weight_per_m2=D("0.02"),
            price_currency="EUR",
            price_basis="PER_KG",
            taxe_pct=D("0"),
            applique_marge=False,
        )
        product = PricingProduct(
            id=13, code="1015", name="Avec refacturation",
            frontal_id=1, adhesif_id=2, silicone_id=3, glassine_id=4,
        )
        s = _settings()
        res = compute_product_cost(product, mats, s)
        total = sum(
            compute_material_price_per_m2(m, s).price_eur_per_m2 for m in mats.values()
        ).quantize(D("0.0001"))
        hors = compute_material_price_per_m2(mats[3], s).price_eur_per_m2
        self.assertEqual(res.total_eur_per_m2, total)
        # La marge ne porte que sur les trois autres matières.
        attendu = ((total - hors) * s.default_margin_pct / D("100")).quantize(D("0.0001"))
        self.assertEqual(res.margin_eur_m2, attendu)
        self.assertEqual(res.sell_price_eur_m2, (total + attendu).quantize(D("0.0001")))

    def test_custom_margin(self):
        mats = self._four_materials()
        product = PricingProduct(
            id=12,
            code="1014",
            name="Marge custom",
            frontal_id=1,
            adhesif_id=2,
            glassine_id=4,
            custom_margin_pct=D("12"),
        )
        s = _settings()
        res = compute_product_cost(product, mats, s)
        self.assertEqual(res.margin_pct, D("12.0000"))
        self.assertEqual(
            res.margin_eur_m2,
            (res.total_eur_per_m2 * D("12") / D("100")).quantize(D("0.0001")),
        )


if __name__ == "__main__":
    unittest.main()

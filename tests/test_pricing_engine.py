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
        default_margin_eur_m2=D("0.06"),
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
            tax_incidence=D("1"),
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
        mat = PricingMaterial(
            id=2,
            name="Adhésif import",
            unit_price=D("3"),
            weight_per_m2=D("0.05"),
            price_currency="USD",
            price_basis="PER_KG",
            tax_incidence=D("1"),
            is_imported=True,
        )
        s = _settings()
        transport_usd_kg = s.default_container_cost_usd / s.default_container_kg
        expected_pre = (D("3") + transport_usd_kg) * D("0.05") * s.eur_usd_rate
        res = compute_material_price_per_m2(mat, s)
        self.assertEqual(res.price_eur_per_m2, expected_pre.quantize(D("0.0001")))
        self.assertGreater(res.breakdown.transport, D("0"))
        self.assertGreater(res.breakdown.raw, D("0"))
        self.assertEqual(res.breakdown.fx, D("0"))
        self.assertEqual(_breakdown_sum(res), res.price_eur_per_m2)

    def test_tax_incidence_above_one(self):
        mat = PricingMaterial(
            id=3,
            name="Glassine taxée",
            unit_price=D("1.5"),
            weight_per_m2=D("0.08"),
            price_currency="EUR",
            price_basis="PER_KG",
            tax_incidence=D("1.065"),
            is_imported=False,
        )
        res = compute_material_price_per_m2(mat, _settings())
        pre = D("1.5") * D("0.08")
        self.assertEqual(res.price_eur_per_m2, (pre * D("1.065")).quantize(D("0.0001")))
        self.assertEqual(res.breakdown.tax_uplift, (pre * D("0.065")).quantize(D("0.0001")))
        self.assertEqual(_breakdown_sum(res), res.price_eur_per_m2)

    def test_usd_per_m2_rare(self):
        mat = PricingMaterial(
            id=4,
            name="Film USD/m2",
            unit_price=D("1.2"),
            weight_per_m2=D("0.02"),
            price_currency="USD",
            price_basis="PER_M2",
            tax_incidence=D("1"),
            is_imported=False,
        )
        res = compute_material_price_per_m2(mat, _settings())
        self.assertEqual(res.price_eur_per_m2, (D("1.2") * D("0.85")).quantize(D("0.0001")))
        self.assertEqual(res.breakdown.fx, D("1.0200"))
        self.assertEqual(_breakdown_sum(res), res.price_eur_per_m2)

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
                tax_incidence=D("1"),
            ),
            2: PricingMaterial(
                id=2,
                name="Adhésif",
                unit_price=D("1"),
                weight_per_m2=D("0.05"),
                price_currency="EUR",
                price_basis="PER_KG",
                tax_incidence=D("1"),
            ),
            3: PricingMaterial(
                id=3,
                name="Silicone",
                unit_price=D("0.5"),
                weight_per_m2=D("0.02"),
                price_currency="EUR",
                price_basis="PER_KG",
                tax_incidence=D("1"),
            ),
            4: PricingMaterial(
                id=4,
                name="Glassine",
                unit_price=D("0.8"),
                weight_per_m2=D("0.09"),
                price_currency="EUR",
                price_basis="PER_KG",
                tax_incidence=D("1"),
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
        self.assertEqual(res.margin_eur_m2, s.default_margin_eur_m2)
        self.assertEqual(res.sell_price_eur_m2, (expected_total + s.default_margin_eur_m2).quantize(D("0.0001")))
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

    def test_custom_margin(self):
        mats = self._four_materials()
        product = PricingProduct(
            id=12,
            code="1014",
            name="Marge custom",
            frontal_id=1,
            adhesif_id=2,
            glassine_id=4,
            custom_margin_eur_m2=D("0.12"),
        )
        res = compute_product_cost(product, mats, _settings())
        self.assertEqual(res.margin_eur_m2, D("0.1200"))


if __name__ == "__main__":
    unittest.main()

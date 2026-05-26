"""Tests d'intégration API — module Coûts matières (/api/pricing).

Couvre les scénarios E2E métier (création matière USD, produit 4 composants,
changement taux FX, export PDF) et l'audit des permissions d'écriture.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

_test_tmp = tempfile.mkdtemp(prefix="mysifa_pricing_api_")
_test_db = os.path.join(_test_tmp, "test.db")
os.environ["DB_PATH"] = _test_db

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Schéma complet requis pour les migrations — copie isolée de la base locale
_src_db = ROOT / "data" / "production.db"
if _src_db.is_file():
    import shutil

    shutil.copy2(_src_db, _test_db)

from app.services.pricing import (  # noqa: E402
    PricingMaterial,
    PricingSettings,
    compute_material_price_per_m2,
    compute_product_cost,
)
from app.services.pricing.types import PricingProduct  # noqa: E402

D = Decimal


def _settings() -> PricingSettings:
    return PricingSettings(
        eur_usd_rate=D("0.85"),
        default_container_cost_usd=D("4000"),
        default_container_kg=D("26000"),
        default_margin_eur_m2=D("0.06"),
    )


def _pricing_client(role: str = "direction"):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.routers.pricing import router

    app = FastAPI()
    app.include_router(router)
    user = {"id": 1, "email": "u@test", "nom": "Test", "role": role}
    patcher = patch("app.routers.pricing.get_current_user", return_value=user)
    patcher.start()
    client = TestClient(app)
    return client, patcher


class TestPricingPermissions(unittest.TestCase):
    """Un utilisateur sans rôle admin ne peut pas écrire sur /api/pricing."""

    READ_ONLY_ROLES = ("fabrication", "logistique", "commercial", "expedition")

    @classmethod
    def setUpClass(cls):
        from database import get_db

        with get_db() as conn:
            for uid, role in (
                (1, "direction"),
                (2, "fabrication"),
                (3, "logistique"),
            ):
                conn.execute(
                    "INSERT OR IGNORE INTO users (id, email, nom, password_hash, role, actif, created_at) "
                    "VALUES (?,?,?,?,?,1,'2026-01-01')",
                    (uid, f"{role}@test", role.capitalize(), "x", role),
                )
            conn.commit()

    def _assert_write_forbidden(self, client, method: str, path: str, json_body=None):
        if method == "POST":
            r = client.post(path, json=json_body or {})
        elif method == "PATCH":
            r = client.patch(path, json=json_body or {})
        elif method == "DELETE":
            r = client.delete(path)
        else:
            raise ValueError(method)
        self.assertEqual(r.status_code, 403, f"{method} {path} → {r.status_code} {r.text}")

    def test_fabrication_cannot_write(self):
        client, patcher = _pricing_client("fabrication")
        try:
            self._assert_write_forbidden(
                client,
                "POST",
                "/api/pricing/materials",
                {
                    "name": "X",
                    "appellation_code": "X",
                    "category_id": 1,
                    "unit_price": 1,
                    "weight_per_m2": 0.1,
                },
            )
            self._assert_write_forbidden(
                client, "PATCH", "/api/pricing/settings", {"eur_usd_rate": 0.9}
            )
            self._assert_write_forbidden(client, "POST", "/api/pricing/suppliers", {"name": "F"})
            self._assert_write_forbidden(
                client, "POST", "/api/pricing/products", {"code": "T", "name": "T"}
            )
            self._assert_write_forbidden(client, "DELETE", "/api/pricing/materials/1")
            self._assert_write_forbidden(client, "DELETE", "/api/pricing/products/1")
            self._assert_write_forbidden(
                client, "POST", "/api/pricing/settings/refresh-fx"
            )
        finally:
            patcher.stop()

    def test_fabrication_can_read(self):
        client, patcher = _pricing_client("fabrication")
        try:
            r = client.get("/api/pricing/materials")
            self.assertEqual(r.status_code, 200)
            r2 = client.get("/api/pricing/settings")
            self.assertEqual(r2.status_code, 200)
        finally:
            patcher.stop()

    def test_direction_can_write(self):
        client, patcher = _pricing_client("direction")
        try:
            r = client.patch("/api/pricing/settings", json={"eur_usd_rate": 0.85})
            self.assertEqual(r.status_code, 200)
        finally:
            patcher.stop()


class TestPricingE2EFlows(unittest.TestCase):
    """Parcours métier complets via API (équivalent E2E sans navigateur)."""

    @classmethod
    def setUpClass(cls):
        from database import get_db

        with get_db() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (id, email, nom, password_hash, role, actif, created_at) "
                "VALUES (1, 'dir@test', 'Direction', 'x', 'direction', 1, '2026-01-01')"
            )
            conn.execute("DELETE FROM mc_product_extra_material")
            conn.execute("DELETE FROM mc_material_price_history")
            conn.execute("DELETE FROM mc_product")
            conn.execute("DELETE FROM mc_material")
            conn.execute("DELETE FROM mc_supplier")
            conn.commit()
            cls.cat_ids = {
                r["code"]: int(r["id"])
                for r in conn.execute("SELECT id, code FROM mc_material_category").fetchall()
            }

    def setUp(self):
        self.client, self._patcher = _pricing_client("direction")

    def tearDown(self):
        self._patcher.stop()

    def test_imported_usd_material_computed_price(self):
        """Matière importée USD/kg → prix €/m² calculé cohérent avec le moteur."""
        body = {
            "name": "Adhésif import E2E",
            "appellation_code": "E2E-USD",
            "category_id": self.cat_ids["ADHESIF"],
            "weight_per_m2": 0.05,
            "price_currency": "USD",
            "unit_price": 3,
            "price_basis": "PER_KG",
            "tax_incidence": 1,
            "is_imported": True,
        }
        r = self.client.post("/api/pricing/materials", json=body)
        self.assertEqual(r.status_code, 201, r.text)
        data = r.json()
        self.assertIn("computed", data)
        got = Decimal(str(data["computed"]["price_eur_per_m2"]))
        pm = PricingMaterial(
            id=data["id"],
            name=body["name"],
            unit_price=D("3"),
            weight_per_m2=D("0.05"),
            price_currency="USD",
            price_basis="PER_KG",
            tax_incidence=D("1"),
            is_imported=True,
        )
        s_json = self.client.get("/api/pricing/settings").json()
        live_settings = PricingSettings(
            eur_usd_rate=Decimal(str(s_json["eur_usd_rate"])),
            default_container_cost_usd=Decimal(str(s_json["default_container_cost_usd"])),
            default_container_kg=Decimal(str(s_json["default_container_kg"])),
            default_margin_eur_m2=Decimal(str(s_json["default_margin_eur_m2"])),
        )
        expected = compute_material_price_per_m2(pm, live_settings).price_eur_per_m2
        self.assertEqual(got, expected)

    def test_product_four_components_breakdown(self):
        """Produit avec 4 composants → breakdown à 4 lignes, parts ≈ 100 %."""
        mats = []
        specs = [
            ("FRONTAL", "F-E2E", 2.0, 0.10),
            ("ADHESIF", "A-E2E", 1.0, 0.05),
            ("SILICONE", "S-E2E", 0.5, 0.02),
            ("GLASSINE", "G-E2E", 0.8, 0.09),
        ]
        for cat, app, price, w in specs:
            r = self.client.post(
                "/api/pricing/materials",
                json={
                    "name": f"Matière {app}",
                    "appellation_code": app,
                    "category_id": self.cat_ids[cat],
                    "weight_per_m2": w,
                    "price_currency": "EUR",
                    "unit_price": price,
                    "price_basis": "PER_KG",
                    "tax_incidence": 1,
                    "is_imported": False,
                },
            )
            self.assertEqual(r.status_code, 201, r.text)
            mats.append(r.json())

        r = self.client.post(
            "/api/pricing/products",
            json={
                "code": "E2E-4COMP",
                "name": "Produit E2E quatre composants",
                "frontal_id": mats[0]["id"],
                "adhesif_id": mats[1]["id"],
                "silicone_id": mats[2]["id"],
                "glassine_id": mats[3]["id"],
            },
        )
        self.assertEqual(r.status_code, 201, r.text)
        prod = r.json()
        cost = prod.get("cost")
        self.assertIsNotNone(cost)
        self.assertEqual(len(cost["components"]), 4)
        share_sum = sum(Decimal(str(c["share_pct"])) for c in cost["components"])
        self.assertEqual(share_sum, D("100.00"))

        pmap = {
            mats[0]["id"]: PricingMaterial(
                id=mats[0]["id"],
                name="f",
                unit_price=D("2"),
                weight_per_m2=D("0.10"),
                price_currency="EUR",
                price_basis="PER_KG",
                tax_incidence=D("1"),
            ),
            mats[1]["id"]: PricingMaterial(
                id=mats[1]["id"],
                name="a",
                unit_price=D("1"),
                weight_per_m2=D("0.05"),
                price_currency="EUR",
                price_basis="PER_KG",
                tax_incidence=D("1"),
            ),
            mats[2]["id"]: PricingMaterial(
                id=mats[2]["id"],
                name="s",
                unit_price=D("0.5"),
                weight_per_m2=D("0.02"),
                price_currency="EUR",
                price_basis="PER_KG",
                tax_incidence=D("1"),
            ),
            mats[3]["id"]: PricingMaterial(
                id=mats[3]["id"],
                name="g",
                unit_price=D("0.8"),
                weight_per_m2=D("0.09"),
                price_currency="EUR",
                price_basis="PER_KG",
                tax_incidence=D("1"),
            ),
        }
        expected = compute_product_cost(
            PricingProduct(
                id=prod["id"],
                code="E2E-4COMP",
                name="x",
                frontal_id=mats[0]["id"],
                adhesif_id=mats[1]["id"],
                silicone_id=mats[2]["id"],
                glassine_id=mats[3]["id"],
            ),
            pmap,
            _settings(),
        )
        self.assertEqual(
            Decimal(str(cost["total_eur_per_m2"])),
            expected.total_eur_per_m2,
        )

    def test_fx_rate_change_updates_product_cost(self):
        """Modifier eur_usd_rate → le coût d'un produit avec matière USD change."""
        r = self.client.post(
            "/api/pricing/materials",
            json={
                "name": "Film USD FX",
                "appellation_code": "USD-FX",
                "category_id": self.cat_ids["FRONTAL"],
                "weight_per_m2": 0.05,
                "price_currency": "USD",
                "unit_price": 4,
                "price_basis": "PER_KG",
                "tax_incidence": 1,
                "is_imported": False,
            },
        )
        self.assertEqual(r.status_code, 201)
        mid = r.json()["id"]

        r = self.client.post(
            "/api/pricing/products",
            json={
                "code": "E2E-FX",
                "name": "Produit FX",
                "frontal_id": mid,
            },
        )
        self.assertEqual(r.status_code, 201)
        pid = r.json()["id"]
        total_before = Decimal(str(r.json()["cost"]["total_eur_per_m2"]))

        self.client.patch("/api/pricing/settings", json={"eur_usd_rate": 0.75})
        r2 = self.client.get(f"/api/pricing/products/{pid}")
        self.assertEqual(r2.status_code, 200)
        total_after = Decimal(str(r2.json()["cost"]["total_eur_per_m2"]))
        self.assertNotEqual(total_before, total_after)
        self.assertLess(total_after, total_before)

        pm = PricingMaterial(
            id=mid,
            name="x",
            unit_price=D("4"),
            weight_per_m2=D("0.05"),
            price_currency="USD",
            price_basis="PER_KG",
            tax_incidence=D("1"),
            is_imported=False,
        )
        s2 = PricingSettings(
            eur_usd_rate=D("0.75"),
            default_container_cost_usd=D("4000"),
            default_container_kg=D("26000"),
            default_margin_eur_m2=D("0.06"),
        )
        expected_after = compute_material_price_per_m2(pm, s2).price_eur_per_m2
        self.assertEqual(total_after, expected_after)

    def test_export_product_pdf_non_empty(self):
        """Export PDF → fichier non vide, en-tête %PDF."""
        r = self.client.post(
            "/api/pricing/materials",
            json={
                "name": "Pour PDF",
                "appellation_code": "PDF1",
                "category_id": self.cat_ids["FRONTAL"],
                "weight_per_m2": 0.1,
                "price_currency": "EUR",
                "unit_price": 2,
                "price_basis": "PER_KG",
                "tax_incidence": 1,
            },
        )
        mid = r.json()["id"]
        r = self.client.post(
            "/api/pricing/products",
            json={"code": "E2E-PDF", "name": "PDF test", "frontal_id": mid},
        )
        pid = r.json()["id"]
        r = self.client.post(f"/api/pricing/products/{pid}/export/pdf")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("application/pdf", r.headers.get("content-type", ""))
        body = r.content
        self.assertGreater(len(body), 200)
        self.assertTrue(body.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()

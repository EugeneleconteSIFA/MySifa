"""Tests calculs prix MyAO."""
from app.services.ao_pricing import (
    calc_prix_au_mille,
    calc_prix_calcule,
    calc_prix_vente,
    convert_amount,
    enrich_reponse_pricing,
)


def test_prix_au_mille_par_bobine():
    assert calc_prix_au_mille(50.0, "bobine", 1000) == 50.0


def test_prix_au_mille_par_mille():
    assert calc_prix_au_mille(42.5, "mille", None) == 42.5


def test_prix_calcule_par_mille():
    assert calc_prix_calcule(10.0, "mille", 50000, None) == 500.0


def test_prix_calcule_par_bobine():
    assert calc_prix_calcule(25.0, "bobine", 10000, 1000) == 250.0


def test_prix_vente_avec_coef():
    assert calc_prix_vente(40.0, "EUR", 1.5, "EUR", 0.92) == 60.0


def test_convert_usd_to_eur():
    assert convert_amount(100.0, "USD", "EUR", 0.9) == 90.0


def test_enrich_reponse():
    ctx = {
        "etiquettes_par_bobine": 1000,
        "quantite_etiquettes": 10000,
    }
    out = enrich_reponse_pricing(
        {"quotation": 30.0, "unite_quotation": "bobine", "devise": "EUR", "coef": 2.0},
        ctx,
        eur_usd_rate=0.92,
    )
    assert out["prix_au_mille"] == 30.0
    assert out["prix_calcule"] == 300.0
    assert out["prix_vente"] == 60.0

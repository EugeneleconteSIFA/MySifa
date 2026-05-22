"""Seed idempotent du référentiel MyExpé — transporteurs historiques (comparateur / contacts)."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

_PARIS = ZoneInfo("Europe/Paris")

# Données alignées sur EXPE_DEFAULT_CONTACTS + règles comparateur MyExpé
EXPE_TRANSPORTEURS_SEED: list[dict[str, Any]] = [
    {
        "nom": "Coupé",
        "taxe_carburant_pct": 12.8,
        "contact_nom": "Portail Coupé",
        "contact_email": "https://coupe.station-chargeur.com/coupe/",
        "contact_tel": None,
        "zone_france": 1,
        "zone_france_hors_paris": 0,
        "zone_affretement": 0,
        "zone_messagerie": 1,
    },
    {
        "nom": "Ceva",
        "taxe_carburant_pct": 12.8,
        "contact_nom": "Portail Ceva/Gefco",
        "contact_email": "https://connect.gefco.net/psc-portal/login.html#LogIn",
        "contact_tel": None,
        "zone_france": 1,
        "zone_france_hors_paris": 0,
        "zone_affretement": 0,
        "zone_messagerie": 1,
    },
    {
        "nom": "Coquelle",
        "taxe_carburant_pct": 12.8,
        "contact_nom": None,
        "contact_email": "eugeneleconte@outlook.com",
        "contact_tel": None,
        "zone_france": 1,
        "zone_france_hors_paris": 0,
        "zone_affretement": 1,
        "zone_messagerie": 0,
    },
    {
        "nom": "Dimotrans",
        "taxe_carburant_pct": 12.8,
        "contact_nom": None,
        "contact_email": "eugeneleconte@outlook.com",
        "contact_tel": None,
        "zone_france": 1,
        "zone_france_hors_paris": 0,
        "zone_affretement": 1,
        "zone_messagerie": 0,
    },
]


def seed_expe_transporteurs_if_empty(conn) -> int:
    """Insère les transporteurs par défaut si la table est vide. Retourne le nombre inséré."""
    row = conn.execute("SELECT COUNT(*) AS n FROM expe_transporteurs").fetchone()
    if row and int(row["n"] or 0) > 0:
        return 0
    now = datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")
    inserted = 0
    for item in EXPE_TRANSPORTEURS_SEED:
        conn.execute(
            """INSERT INTO expe_transporteurs (
                nom, taxe_carburant_pct, contact_nom, contact_email, contact_tel,
                zone_france, zone_france_hors_paris, zone_affretement, zone_messagerie,
                actif, created_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                item["nom"],
                item["taxe_carburant_pct"],
                item.get("contact_nom"),
                item.get("contact_email"),
                item.get("contact_tel"),
                item.get("zone_france", 1),
                item.get("zone_france_hors_paris", 0),
                item.get("zone_affretement", 0),
                item.get("zone_messagerie", 0),
                1,
                now,
            ),
        )
        inserted += 1
    return inserted

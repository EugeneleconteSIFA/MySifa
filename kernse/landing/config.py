"""
Kernse-landing — configuration du site public.

App FastAPI minimaliste (aucune DB) qui sert la landing publique. Ne
partage aucun état avec kernse-admin — les rare données dynamiques (nb
de clients, cas clients, tarifs) sont lues depuis platform_settings via
une lecture SQLite en read-only (fichier partagé sur le VPS).
"""
from __future__ import annotations

import os
from pathlib import Path


APP_TITLE   = "Kernse — Pilotage d'atelier"
APP_VERSION = "0.1.0"

BASE_DIR    = Path(__file__).resolve().parent

ENV_NAME    = os.getenv("KERNSE_ENV", "v2").strip().lower()
IS_STAGING  = ENV_NAME == "v1"

HOST = os.getenv("KERNSE_LANDING_HOST", "0.0.0.0")
PORT = int(os.getenv("KERNSE_LANDING_PORT", "8103" if IS_STAGING else "8101"))

# URL de la démo — pointe vers un client provisionné manuellement.
DEMO_URL = os.getenv("KERNSE_DEMO_URL", "https://demo.kernse.fr")

# Email de contact affiché sur la landing.
CONTACT_EMAIL = os.getenv("KERNSE_LANDING_CONTACT", "contact@kernse.fr")

# Chemin READ-ONLY vers la DB plateforme (pour les stats publiques
# éventuelles). Optionnel — si absent, la landing tourne sans data.
PLATFORM_DB_READONLY = os.getenv("KERNSE_PLATFORM_DB_PATH", "")

TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR    = BASE_DIR / "static"

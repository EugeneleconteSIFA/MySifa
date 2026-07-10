"""
Kernse-admin — configuration de l'app console plateforme.

Cette app tourne UNIQUEMENT sur admin.kernse.fr (prod) et admin-v1.kernse.fr
(test). Elle n'est jamais exposée directement à un utilisateur d'instance
client. Auth : allowlist superadmin plateforme + 2FA (à venir).
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path


APP_TITLE     = "Kernse Admin"
APP_VERSION   = "0.1.0"

BASE_DIR      = Path(__file__).resolve().parent
DATA_DIR      = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PLATFORM_DB_PATH = Path(os.getenv(
    "KERNSE_PLATFORM_DB_PATH",
    str(DATA_DIR / "platform.db"),
))

# Environnement (test = v1, prod = v2). Détermine le bandeau et le port par défaut.
ENV_NAME   = os.getenv("KERNSE_ENV", "v2").strip().lower()
IS_STAGING = ENV_NAME == "v1"

HOST = os.getenv("KERNSE_ADMIN_HOST", "0.0.0.0")
PORT = int(os.getenv("KERNSE_ADMIN_PORT", "8104" if IS_STAGING else "8102"))

# Auth superadmin plateforme : voir kernse/shared/auth/. Les comptes sont
# créés dans la table `superadmins` (mot de passe hashé + 2FA TOTP
# optionnelle). Le premier compte est bootstrapé depuis
# KERNSE_BOOTSTRAP_EMAIL + KERNSE_BOOTSTRAP_PASSWORD si aucun superadmin
# n'existe encore. L'ajout ou le retrait d'un superadmin est audité.

SECRET_KEY    = os.getenv("KERNSE_ADMIN_SECRET_KEY", secrets.token_hex(32))
SESSION_HOURS = 4
COOKIE_NAME   = "kernse_admin_token"

# Domaine public (utilisé pour les liens et la validation CORS).
PUBLIC_BASE_URL = os.getenv(
    "KERNSE_ADMIN_PUBLIC_URL",
    "https://admin-v1.kernse.fr" if IS_STAGING else "https://admin.kernse.fr",
)

# Politique promotion — à ajuster quand la flotte grossira.
MAX_MASS_PROMOTE_DURATION_SECONDS = int(os.getenv("KERNSE_MAX_MASS_PROMOTE", "1800"))
PROMOTE_SHELL_TIMEOUT_SECONDS     = int(os.getenv("KERNSE_PROMOTE_TIMEOUT", "180"))

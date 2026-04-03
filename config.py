"""
SIFA — Configuration & constantes v0.6
"""
import os
import re
import json
import secrets

# ─── Chemins ──────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
DB_PATH    = os.getenv("DB_PATH", os.path.join(DATA_DIR, "production.db"))
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")

os.makedirs(DATA_DIR,   exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ─── App ──────────────────────────────────────────────────────────
APP_VERSION = "0.6.1"
# Titre API / OpenAPI
APP_TITLE = "MySifa"
# Onglet navigateur & SEO (injecté dans frontend/html.py)
APP_PAGE_TITLE = "MySifa — Portail interne SIFA"
APP_META_DESCRIPTION = (
    "Portail interne SIFA : production, stocks, planning et outils métier."
)
# Couleur barre d’état mobile (thème sombre par défaut)
THEME_COLOR_META = "#0a0e17"
# Page planning (/planning) — titre d’onglet
APP_PLANNING_PAGE_TITLE = "Planning — MySifa"
HOST        = "0.0.0.0"
PORT        = 8000

# ─── Sécurité ─────────────────────────────────────────────────────
SECRET_KEY    = os.getenv("SECRET_KEY", secrets.token_hex(32))
SESSION_HOURS = 6
COOKIE_NAME   = "sifa_token"

# ─── Rôles ────────────────────────────────────────────────────────
# direction     : accès total (même droits qu'administration pour l'instant)
# administration: gestion complète sauf rien de plus que direction
# fabrication   : lecture seule sur ses propres données
ROLE_DIRECTION      = "direction"
ROLE_ADMINISTRATION = "administration"
ROLE_FABRICATION    = "fabrication"
ROLE_LOGISTIQUE     = "logistique"

# Rôles ayant accès aux fonctions d'administration
ROLES_ADMIN = {ROLE_DIRECTION, ROLE_ADMINISTRATION}
ROLES_STOCK = {ROLE_DIRECTION, ROLE_ADMINISTRATION, ROLE_LOGISTIQUE}
ROLES_PROD  = {ROLE_DIRECTION, ROLE_ADMINISTRATION, ROLE_FABRICATION}

# Admin par défaut
DEFAULT_ADMIN_EMAIL = "admin@sifa.fr"
DEFAULT_ADMIN_NOM   = "Administrateur"
DEFAULT_ADMIN_PWD   = "Admin1234!"

# ─── Codes opérations ─────────────────────────────────────────────
CODE_ARRIVEE    = "86"
CODE_DEPART     = "87"
CODE_DEBUT_DOS  = "01"
CODE_FIN_DOS    = "89"
CODE_CALAGE     = "02"
CODE_PRODUCTION = "03"
CODE_REPRISE    = "88"

# ─── Classification opérations ────────────────────────────────────
def load_operations():
    path = os.path.join(BASE_DIR, "operations.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

OPERATION_SEVERITY = load_operations()

def classify_operation(op_str):
    if not op_str:
        return {"code": "", "label": str(op_str), "severity": "info", "category": "autre"}
    op_clean = str(op_str).strip()
    match = re.match(r'^(\d+)', op_clean)
    if match:
        code = match.group(1)
        info = OPERATION_SEVERITY.get(code, {"severity": "info", "label": op_clean, "category": "autre"})
        return {"code": code, **info}
    return {"code": "", "label": op_clean, "severity": "info", "category": "autre"}

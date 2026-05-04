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
# Une seule base applicative : défaut data/production.db. Surcharge : variable d'environnement DB_PATH.
# Sauvegarde : copier ce fichier + data/uploads/ ; optionnel : operations.json, data/emplacements_plan.csv
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

# ─── Support (email) ───────────────────────────────────────────────
# Objectif: permettre au front d’envoyer un message au support via un endpoint FastAPI.
# Configuration SMTP via variables d’environnement (prod).
SUPPORT_TO_EMAIL = os.getenv("SUPPORT_TO_EMAIL", "eleconte@sifa.pro")
SUPPORT_EMAIL_PROVIDER = os.getenv("SUPPORT_EMAIL_PROVIDER", "graph")  # graph | smtp
SUPPORT_EMAIL_DISABLED = os.getenv("SUPPORT_EMAIL_DISABLED", "0") in {"1", "true", "True", "yes", "YES"}

# ─── Support (Microsoft Graph) ─────────────────────────────────────
# Envoi sans SMTP (recommandé quand SMTP AUTH est désactivé sur le tenant).
MS_TENANT_ID = os.getenv("MS_TENANT_ID", "")
MS_CLIENT_ID = os.getenv("MS_CLIENT_ID", "")
MS_CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET", "")
MS_SENDER_UPN = os.getenv("MS_SENDER_UPN", "")  # ex: eleconte@sifa.pro (mailbox autorisée à envoyer)

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")  # ex: "MySifa <no-reply@mysifa.com>"
SMTP_TLS = os.getenv("SMTP_TLS", "1") not in {"0", "false", "False", "no", "NO"}
SUPPORT_EMAIL_DEBUG = os.getenv("SUPPORT_EMAIL_DEBUG", "0") in {"1", "true", "True", "yes", "YES"}

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
ROLE_COMPTABILITE   = "comptabilite"
ROLE_EXPEDITION     = "expedition"
ROLE_COMMERCIAL     = "commercial"
ROLE_SUPERADMIN     = "superadmin"

# Compte technique : seul cet email peut porter le rôle superadmin (contrôlé côté API).
SUPERADMIN_EMAIL = "eleconte@sifa.pro"

# Rôles ayant accès aux fonctions d'administration (imports, dossiers, stats, etc.)
ROLES_ADMIN = {ROLE_DIRECTION, ROLE_ADMINISTRATION, ROLE_SUPERADMIN}
ROLES_STOCK = {ROLE_DIRECTION, ROLE_ADMINISTRATION, ROLE_LOGISTIQUE, ROLE_COMMERCIAL, ROLE_SUPERADMIN}
ROLES_PROD  = {ROLE_DIRECTION, ROLE_ADMINISTRATION, ROLE_FABRICATION, ROLE_COMMERCIAL, ROLE_SUPERADMIN}
ROLES_COMPTA = {ROLE_DIRECTION, ROLE_COMPTABILITE, ROLE_SUPERADMIN}
ROLES_EXPE  = {ROLE_DIRECTION, ROLE_ADMINISTRATION, ROLE_EXPEDITION, ROLE_SUPERADMIN}
ROLES_DEVIS = {ROLE_DIRECTION, ROLE_SUPERADMIN}
ROLES_PLANNING_VIEW = {ROLE_DIRECTION, ROLE_ADMINISTRATION, ROLE_FABRICATION, ROLE_COMMERCIAL, ROLE_SUPERADMIN}
ROLES_SETTINGS = {ROLE_SUPERADMIN}

# Applications dont l'accès peut être surchargé par utilisateur (hors Paramètres : réservé au rôle super admin).
ACCESS_OVERRIDABLE_APPS = frozenset({"prod", "planning", "planning_rh", "stock", "compta", "expe", "devis"})

# Rôles assignables lors de la création / édition d'utilisateurs (hors super admin).
ASSIGNABLE_ROLES = frozenset(
    {
        ROLE_FABRICATION,
        ROLE_ADMINISTRATION,
        ROLE_DIRECTION,
        ROLE_LOGISTIQUE,
        ROLE_COMPTABILITE,
        ROLE_EXPEDITION,
        ROLE_COMMERCIAL,
    }
)


ROLES_FABRICATION_APP = {ROLE_FABRICATION, ROLE_DIRECTION, ROLE_ADMINISTRATION, ROLE_SUPERADMIN}

# Planning RH (Personnel)
ROLES_PLANNING_RH_VIEW  = {ROLE_DIRECTION, ROLE_FABRICATION, ROLE_LOGISTIQUE, ROLE_SUPERADMIN}
ROLES_PLANNING_RH_EDIT  = {ROLE_DIRECTION, ROLE_SUPERADMIN}
ROLES_PLANNING_RH_STAFF = {ROLE_FABRICATION, ROLE_LOGISTIQUE}


def default_app_access_for_role(role: str) -> dict:
    """Accès applications issus du seul rôle (avant surcharges utilisateur)."""
    if role == ROLE_SUPERADMIN:
        return {
            "prod": True,
            "planning": True,
            "stock": True,
            "compta": True,
            "expe": True,
            "devis": True,
            "fabrication": True,
            "settings": True,
            "planning_rh": True,
        }
    return {
        "prod": role in ROLES_PROD,
        "planning": role in ROLES_PLANNING_VIEW,
        "stock": role in ROLES_STOCK,
        "compta": role in ROLES_COMPTA,
        "expe": role in ROLES_EXPE,
        "devis": role in ROLES_DEVIS,
        "fabrication": role in ROLES_FABRICATION_APP,
        "settings": role in ROLES_SETTINGS,
        "planning_rh": role in ROLES_PLANNING_RH_VIEW,
    }

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
_ALLOWED_SEVERITY = frozenset({"info", "attention", "critique"})


def validate_operations_config(data: object) -> None:
    """Lève ValueError si la structure de operations.json est invalide."""
    if not isinstance(data, dict) or len(data) == 0:
        raise ValueError("operations.json doit être un objet JSON non vide.")
    for code, entry in data.items():
        ck = str(code).strip()
        if not ck or not re.match(r"^\d+$", ck):
            raise ValueError(f"operations.json : clé de code invalide « {code} ».")
        if not isinstance(entry, dict):
            raise ValueError(f"operations.json : l'entrée « {ck} » doit être un objet.")
        for k in ("severity", "label", "category"):
            if k not in entry:
                raise ValueError(f"operations.json : « {ck} » manque le champ « {k} ».")
            if not isinstance(entry[k], str):
                raise ValueError(f"operations.json : « {ck} ».{k} doit être une chaîne.")
        if entry["severity"] not in _ALLOWED_SEVERITY:
            raise ValueError(
                f"operations.json : « {ck} ».severity invalide (« {entry['severity']} »)."
            )


def load_operations():
    path = os.path.join(BASE_DIR, "operations.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as e:
        raise RuntimeError(f"Fichier manquant : {path}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON invalide : {path} — {e}") from e
    try:
        validate_operations_config(data)
    except ValueError as e:
        raise RuntimeError(f"operations.json : {e}") from e
    return data


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

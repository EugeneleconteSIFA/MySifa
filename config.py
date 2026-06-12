"""
SIFA — Configuration & constantes v0.6
"""
import os
import re
from pathlib import Path

# Charge .env à la racine du projet (local + VPS) avant lecture des variables.
_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.is_file():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        pass
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
APP_VERSION = "0.7.5"
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
PORT        = int(os.getenv("PORT", 8000))

# ─── Environnement (v1 staging / v2 prod) ────────────────────────────
# ENV_NAME : "v2" (prod, défaut) ou "v1" (staging). Les deux instances tournent
# côte à côte sur le VPS (v2:8000, v1:8002) et partagent la même DB.
# Toute valeur autre que "v1" est traitée comme prod (sécurité par défaut).
ENV_NAME = os.getenv("ENV_NAME", "v2").strip().lower()
IS_STAGING = (ENV_NAME == "v1")

# MIGRATIONS_DISABLED : désactive les migrations de schéma au boot. Obligatoire
# sur v1 pour ne pas modifier la DB partagée avec la prod. Valeur par défaut :
# désactivé sur v1, actif sur v2.
_migrations_default = "1" if IS_STAGING else "0"
MIGRATIONS_DISABLED = os.getenv("MIGRATIONS_DISABLED", _migrations_default) in {"1", "true", "True", "yes", "YES"}

# ─── Feature flags ────────────────────────────────────────────────
# PROD_STANDALONE : sert /prod depuis app/web/prod_page.py (page standalone) plutôt
# que depuis le monolithe html.py via render_frontend_html("prod"). La migration
# Phase 2 a sorti tout le code MyProd vers static/mysifa_prod_core.{js,css}.
# Activé par défaut depuis la phase 2m (juin 2026). Pour repasser temporairement
# au rendu via le monolithe (rollback debug), mettre PROD_STANDALONE=0 dans .env.
# Sera retiré complètement en phase 2n (suppression du code Prod du monolithe).
PROD_STANDALONE = os.getenv("PROD_STANDALONE", "1") in {"1", "true", "True", "yes", "YES"}

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

SMTP_HOST      = os.getenv("SMTP_HOST", "")
SMTP_PORT      = int(os.getenv("SMTP_PORT", 587))
SMTP_USER      = os.getenv("SMTP_USER", "")
SMTP_PASS      = os.getenv("SMTP_PASS", "")
SMTP_FROM      = os.getenv("SMTP_FROM", "noreply@mysifa.fr")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "MySifa")
SMTP_TLS       = os.getenv("SMTP_TLS", "1") not in {"0", "false", "False", "no", "NO"}
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
ROLES_STOCK = {ROLE_DIRECTION, ROLE_ADMINISTRATION, ROLE_LOGISTIQUE, ROLE_EXPEDITION, ROLE_COMMERCIAL, ROLE_FABRICATION, ROLE_SUPERADMIN}

# MyStock — zone « Au sol - à expédier » : stock prêt à expédier (code technique, affiché « Au sol - à expédier »)
STOCK_EMPLACEMENT_AU_SOL = "Z0"
STOCK_EMPLACEMENT_AU_SOL_LABEL = "Au sol - à expédier"
STOCK_EMPLACEMENT_SORTIE_PROD = "Z1"
STOCK_EMPLACEMENT_SORTIE_PROD_LABEL = "En attente - sortie de prod"
ROLES_PROD  = {ROLE_DIRECTION, ROLE_ADMINISTRATION, ROLE_FABRICATION, ROLE_EXPEDITION, ROLE_COMMERCIAL, ROLE_SUPERADMIN}
ROLES_COMPTA = {ROLE_DIRECTION, ROLE_COMPTABILITE, ROLE_SUPERADMIN}
ROLES_EXPE = {ROLE_DIRECTION, ROLE_ADMINISTRATION, ROLE_EXPEDITION, ROLE_LOGISTIQUE, ROLE_COMMERCIAL, ROLE_SUPERADMIN}
ROLES_EXPE_WRITE = {ROLE_DIRECTION, ROLE_ADMINISTRATION, ROLE_EXPEDITION, ROLE_SUPERADMIN}
# Tuile portail « Coûts matières » (/pricing) — Direction et super admin uniquement
ROLES_PRICING = {ROLE_DIRECTION, ROLE_SUPERADMIN}
ROLES_PRICING_WRITE = ROLES_PRICING
ROLES_DEVIS = ROLES_PRICING  # alias rétrocompat
ROLES_PLANNING_VIEW = {
    ROLE_DIRECTION,
    ROLE_ADMINISTRATION,
    ROLE_FABRICATION,
    ROLE_EXPEDITION,
    ROLE_COMMERCIAL,
    ROLE_COMPTABILITE,
    ROLE_LOGISTIQUE,
    ROLE_SUPERADMIN,
}
# MyProd : tuile portail pour la compta et la logistique, accès limité au planning production (lecture seule côté UI/API).
ROLES_PROD_COMPTA_PLANNING = {ROLE_COMPTABILITE, ROLE_LOGISTIQUE}
ROLES_SETTINGS = {ROLE_SUPERADMIN}

# Applications dont l'accès peut être surchargé par utilisateur (hors Paramètres : réservé au rôle super admin).
ACCESS_OVERRIDABLE_APPS = frozenset({"prod", "planning", "planning_rh", "stock", "compta", "expe", "pricing"})

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
ROLES_PLANNING_RH_VIEW  = {
    ROLE_DIRECTION,
    ROLE_ADMINISTRATION,
    ROLE_FABRICATION,
    ROLE_LOGISTIQUE,
    ROLE_EXPEDITION,
    ROLE_COMPTABILITE,
    ROLE_SUPERADMIN,
}
ROLES_PLANNING_RH_EDIT  = {ROLE_DIRECTION, ROLE_SUPERADMIN}
ROLES_PLANNING_RH_STAFF = {ROLE_FABRICATION, ROLE_LOGISTIQUE}

# Profils utilisateurs exclus du planning RH (comparaison sur nom normalisé : trim + minuscules).
PLANNING_RH_EXCLUDED_NOMS = frozenset({"logistique sifa"})


def default_app_access_for_role(role: str) -> dict:
    """Accès applications issus du seul rôle (avant surcharges utilisateur)."""
    if role == ROLE_SUPERADMIN:
        return {
            "prod": True,
            "planning": True,
            "stock": True,
            "compta": True,
            "expe": True,
            "pricing": True,
            "fabrication": True,
            "settings": True,
            "planning_rh": True,
        }
    return {
        "prod": role in ROLES_PROD or role in ROLES_PROD_COMPTA_PLANNING,
        "planning": role in ROLES_PLANNING_VIEW,
        "stock": role in ROLES_STOCK,
        "compta": role in ROLES_COMPTA,
        "expe": role in ROLES_EXPE,
        "pricing": role in ROLES_PRICING,
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

# Ensemble complet des codes traités comme du temps de calage
# (02 calage, 10-12 réglages, 58-60 préparations, 67 vidange, 74-75 essais)
CODES_CALAGE: frozenset[str] = frozenset({
    "02", "10", "11", "12", "58", "59", "60", "67", "74", "75"
})

# ─── Classification opérations ────────────────────────────────────
_ALLOWED_SEVERITY = frozenset({"info", "attention", "critique"})


# ─── Jours fériés nationaux (France métropolitaine) ───────────────
# Source MyCalendrier (calendrier « Jours fériés ») — distinct des jours off planning machine.
FERIES_NATIONAUX_FR: dict[int, list[tuple[str, str]]] = {
    2025: [
        ("2025-01-01", "Jour de l'an"),
        ("2025-04-21", "Lundi de Pâques"),
        ("2025-05-01", "Fête du Travail"),
        ("2025-05-08", "Victoire des Alliés 1945"),
        ("2025-05-29", "Jeudi de l'Ascension"),
        ("2025-06-09", "Lundi de Pentecôte"),
        ("2025-07-14", "Fête Nationale"),
        ("2025-08-15", "Assomption"),
        ("2025-11-01", "La Toussaint"),
        ("2025-11-11", "Armistice 1918"),
        ("2025-12-25", "Noël"),
    ],
    2026: [
        ("2026-01-01", "Jour de l'an"),
        ("2026-04-06", "Lundi de Pâques"),
        ("2026-05-01", "Fête du Travail"),
        ("2026-05-08", "Victoire des Alliés 1945"),
        ("2026-05-14", "Jeudi de l'Ascension"),
        ("2026-05-25", "Lundi de Pentecôte"),
        ("2026-07-14", "Fête Nationale"),
        ("2026-08-15", "Assomption"),
        ("2026-11-01", "La Toussaint"),
        ("2026-11-11", "Armistice 1918"),
        ("2026-12-25", "Noël"),
    ],
}


def national_holidays_between(date_debut: str, date_fin: str) -> list[tuple[str, str]]:
    """Jours fériés nationaux entre deux dates YYYY-MM-DD (inclus)."""
    from datetime import date as _date

    d0 = _date.fromisoformat(str(date_debut)[:10])
    d1 = _date.fromisoformat(str(date_fin)[:10])
    out: list[tuple[str, str]] = []
    for year in range(d0.year, d1.year + 1):
        for ds, label in FERIES_NATIONAUX_FR.get(year, []):
            d = _date.fromisoformat(ds)
            if d0 <= d <= d1:
                out.append((ds, label))
    return out


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
    """Charge le référentiel (SQLite prioritaire, repli operations.json)."""
    try:
        from app.services.operations_config import load_operations_dict

        return load_operations_dict()
    except Exception:
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


def refresh_operations_cache():
    """Recharge OPERATION_SEVERITY après modification en base."""
    global OPERATION_SEVERITY
    OPERATION_SEVERITY = load_operations()
    return OPERATION_SEVERITY


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


# URL de base (pour construire les liens dans les emails)
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
# Domaine public prod (liens portail / emails) — surcharge via PUBLIC_BASE_URL ou BASE_URL
PUBLIC_BASE_URL_DEFAULT = "https://www.mysifa.com"


def public_base_url() -> str:
    """URL absolue pour liens emails et portail (jamais localhost si non configuré)."""
    raw = (
        os.getenv("PUBLIC_BASE_URL")
        or os.getenv("BASE_URL")
        or PUBLIC_BASE_URL_DEFAULT
    ).strip().rstrip("/")
    low = raw.lower()
    if not raw or "localhost" in low or "127.0.0.1" in low:
        return PUBLIC_BASE_URL_DEFAULT.rstrip("/")
    return raw

# ─── Chat (GIPHY) ─────────────────────────────────────────────────
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY", "")

# ─── MyExpé — parsing grilles tarifaires (IA) ───────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

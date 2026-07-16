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
# Racine des assets uploadés et servis via /uploads/* (chat, avatars, traca).
# Distincte de UPLOAD_DIR (qui reste sur data/uploads/ pour les imports métier).
# Surcharge via UPLOADS_ROOT : permet à v1 (staging) de partager le même dossier
# que v2 (prod), comme c'est déjà le cas pour la DB. Évite les 404 sur les pièces
# jointes du chat quand un message est envoyé depuis l'autre instance.
UPLOADS_ROOT = os.getenv("UPLOADS_ROOT", os.path.join(BASE_DIR, "uploads"))

os.makedirs(DATA_DIR,   exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(UPLOADS_ROOT, exist_ok=True)

# ─── App ──────────────────────────────────────────────────────────
APP_VERSION = "2.0.5"

# ─── Branding paramétrable — règle #1 CLAUDE.md (SIFA = défaut) ────
# Ces variables permettent à une instance client Kernse de rebrander toute
# l'app sans modifier une seule ligne de code. Elles sont lues par
# `app/web/login_assets.py`, `html.py`, tous les rendus HTML de la sidebar,
# du portail et des footers. Défaut : « MySifa » / « SIFA » (comportement
# historique inchangé pour la prod SIFA).

# Nom affiché en wordmark, titres, footers.
APP_NAME = os.getenv("APP_NAME", "MySifa")

# Indice de coupure du wordmark pour l'affichage bicolore. Ex. :
#   "MySifa" + APP_SPLIT=2 → "My" (couleur principale) + "Sifa" (accent)
#   "Kernse" + APP_SPLIT=1 → "K"  + "ernse"
_APP_SPLIT_RAW = int(os.getenv("APP_SPLIT", "2"))
APP_SPLIT       = max(1, min(_APP_SPLIT_RAW, max(1, len(APP_NAME) - 1)))
APP_NAME_PREFIX = APP_NAME[:APP_SPLIT]
APP_NAME_SUFFIX = APP_NAME[APP_SPLIT:]

# Nom de l'organisation propriétaire de l'instance (utilisé dans le footer,
# les emails, la meta description).
APP_ORG_NAME = os.getenv("APP_ORG_NAME", "SIFA")

# Sous-titre du login et du portail.
APP_TAGLINE = os.getenv(
    "APP_TAGLINE",
    "Portail interne — Production, stocks et outils métier",
)

# Petit texte sous « Connexion » (« Accès réservé au personnel SIFA »).
APP_LOGIN_HINT = os.getenv(
    "APP_LOGIN_HINT",
    f"Accès réservé au personnel {APP_ORG_NAME}",
)

# Grand titre affiché sur la login DA Kernse (KERNSE_THEME=1 uniquement).
# Ex. « Bienvenue. » suivi de « Portail interne Kernse. » — split en 2 lignes
# pour la mise en page grande typo Poppins de la maquette.
APP_WELCOME_TITLE = os.getenv("APP_WELCOME_TITLE", "Bienvenue.")
APP_WELCOME_SUB = os.getenv(
    "APP_WELCOME_SUB",
    f"Portail interne {APP_NAME}.",
)

# Tagline riche multi-ligne pour la login DA Kernse (au-dessus de la card).
# APP_TAGLINE reste utilisée pour le sous-titre court MySifa historique.
APP_TAGLINE_RICH = os.getenv(
    "APP_TAGLINE_RICH",
    "Production, stocks, planning, comptabilité, appels d'offre — "
    "tous les outils métier au même endroit, avec la palette de "
    "commandes ⌘K pour aller vite.",
)

# Texte affiché à côté du point vert dans le footer login DA Kernse.
APP_STATUS_TEXT = os.getenv("APP_STATUS_TEXT", "Service opérationnel")

# Titre API / OpenAPI. Par défaut = APP_NAME.
APP_TITLE = os.getenv("APP_TITLE", APP_NAME)

# Onglet navigateur & SEO.
APP_PAGE_TITLE = os.getenv(
    "APP_PAGE_TITLE",
    f"{APP_NAME} — Portail interne {APP_ORG_NAME}",
)
APP_META_DESCRIPTION = os.getenv(
    "APP_META_DESCRIPTION",
    f"Portail interne {APP_ORG_NAME} : production, stocks, planning et outils métier.",
)

# Thème visuel : dark cyan MySifa (défaut) ou clair navy/orange Kernse.
# Active via KERNSE_THEME=1 dans le .env de l'instance client.
KERNSE_THEME = os.getenv("KERNSE_THEME", "0") in {"1", "true", "True", "yes", "YES"}

# Couleur barre d'état mobile (dérivée du thème actif).
THEME_COLOR_META = os.getenv(
    "THEME_COLOR_META",
    "#f6f4ef" if KERNSE_THEME else "#0a0e17",
)

# Page planning (/planning) — titre d'onglet.
APP_PLANNING_PAGE_TITLE = os.getenv(
    "APP_PLANNING_PAGE_TITLE",
    f"Planning — {APP_NAME}",
)

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

# MAINTENANCE_OPEN_BETA : ouvre l'accès du module Maintenance aux opérateurs
# (rôle `fabrication`) pendant la phase de test. Quand désactivé (0, défaut),
# seuls les rôles admin (superadmin, direction, administration) peuvent y
# entrer. Passer à 1 dans le .env pour laisser les opérateurs tester leur
# vue « Mes tâches » sur v1 avant la promotion en prod. Les endpoints API
# vérifient ce flag côté serveur — inutile de patcher la sidebar seule.
MAINTENANCE_OPEN_BETA = os.getenv("MAINTENANCE_OPEN_BETA", "0") in {"1", "true", "True", "yes", "YES"}

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
# direction              : accès total (même droits qu'administration pour l'instant)
# administration_ventes  : gestion complète côté ADV (ex-rôle "administration", split juillet 2026)
# administration_technique : mêmes droits que administration_ventes pour l'instant, entité distincte
# fabrication            : lecture seule sur ses propres données
ROLE_DIRECTION                = "direction"
# Rôle historique conservé comme alias pour la compatibilité (imports, code externe).
# En base, tous les users basculent en `administration_ventes` via la migration v163.
# Le super admin déplace ensuite manuellement ceux qui doivent être `administration_technique`.
ROLE_ADMINISTRATION           = "administration"
ROLE_ADMINISTRATION_VENTES    = "administration_ventes"
ROLE_ADMINISTRATION_TECHNIQUE = "administration_technique"
ROLE_FABRICATION              = "fabrication"
ROLE_LOGISTIQUE               = "logistique"
ROLE_COMPTABILITE             = "comptabilite"
ROLE_EXPEDITION               = "expedition"
ROLE_COMMERCIAL               = "commercial"
ROLE_SUPERADMIN               = "superadmin"

# Sous-ensemble « famille administration » : les deux rôles issus du split partagent
# strictement les mêmes droits sur MySifa (juillet 2026). Utiliser ce set partout où
# le rôle `administration` était référencé auparavant, plutôt que de dupliquer.
ROLES_ADMINISTRATION_ALL = {
    ROLE_ADMINISTRATION,            # legacy, si un user n'a pas encore été migré
    ROLE_ADMINISTRATION_VENTES,
    ROLE_ADMINISTRATION_TECHNIQUE,
}

# Compte technique : seul cet email peut porter le rôle superadmin (contrôlé côté API).
SUPERADMIN_EMAIL = "eleconte@sifa.pro"

# Rôles ayant accès aux fonctions d'administration (imports, dossiers, stats, etc.)
ROLES_ADMIN = {ROLE_DIRECTION, ROLE_SUPERADMIN} | ROLES_ADMINISTRATION_ALL
ROLES_STOCK = {ROLE_DIRECTION, ROLE_LOGISTIQUE, ROLE_EXPEDITION, ROLE_COMMERCIAL, ROLE_FABRICATION, ROLE_SUPERADMIN} | ROLES_ADMINISTRATION_ALL

# MyStock — zone « Au sol - à expédier » : stock prêt à expédier (code technique, affiché « Au sol - à expédier »)
STOCK_EMPLACEMENT_AU_SOL = "Z0"
STOCK_EMPLACEMENT_AU_SOL_LABEL = "Au sol - à expédier"
STOCK_EMPLACEMENT_SORTIE_PROD = "Z1"
STOCK_EMPLACEMENT_SORTIE_PROD_LABEL = "En attente - sortie de prod"
ROLES_PROD  = {ROLE_DIRECTION, ROLE_FABRICATION, ROLE_EXPEDITION, ROLE_COMMERCIAL, ROLE_SUPERADMIN} | ROLES_ADMINISTRATION_ALL
ROLES_COMPTA = {ROLE_DIRECTION, ROLE_COMPTABILITE, ROLE_SUPERADMIN}
ROLES_EXPE = {ROLE_DIRECTION, ROLE_EXPEDITION, ROLE_LOGISTIQUE, ROLE_COMMERCIAL, ROLE_SUPERADMIN} | ROLES_ADMINISTRATION_ALL
ROLES_EXPE_WRITE = {ROLE_DIRECTION, ROLE_EXPEDITION, ROLE_SUPERADMIN} | ROLES_ADMINISTRATION_ALL
# Tuile portail « Coûts matières » (/pricing) — Direction et super admin uniquement
ROLES_PRICING = {ROLE_DIRECTION, ROLE_SUPERADMIN}
ROLES_PRICING_WRITE = ROLES_PRICING
ROLES_DEVIS = ROLES_PRICING  # alias rétrocompat
ROLES_PLANNING_VIEW = {
    ROLE_DIRECTION,
    ROLE_FABRICATION,
    ROLE_EXPEDITION,
    ROLE_COMMERCIAL,
    ROLE_COMPTABILITE,
    ROLE_LOGISTIQUE,
    ROLE_SUPERADMIN,
} | ROLES_ADMINISTRATION_ALL
# MyProd : tuile portail pour la compta et la logistique, accès limité au planning production (lecture seule côté UI/API).
ROLES_PROD_COMPTA_PLANNING = {ROLE_COMPTABILITE, ROLE_LOGISTIQUE}
ROLES_SETTINGS = {ROLE_SUPERADMIN}

# Applications dont l'accès peut être surchargé par utilisateur (hors Paramètres : réservé au rôle super admin).
ACCESS_OVERRIDABLE_APPS = frozenset({"prod", "planning", "planning_rh", "stock", "compta", "expe", "pricing"})

# Rôles assignables lors de la création / édition d'utilisateurs (hors super admin).
# Le rôle legacy `administration` n'est plus proposé : le super admin choisit désormais
# explicitement entre `administration_ventes` et `administration_technique`.
ASSIGNABLE_ROLES = frozenset(
    {
        ROLE_FABRICATION,
        ROLE_ADMINISTRATION_VENTES,
        ROLE_ADMINISTRATION_TECHNIQUE,
        ROLE_DIRECTION,
        ROLE_LOGISTIQUE,
        ROLE_COMPTABILITE,
        ROLE_EXPEDITION,
        ROLE_COMMERCIAL,
    }
)


ROLES_FABRICATION_APP = {ROLE_FABRICATION, ROLE_DIRECTION, ROLE_SUPERADMIN} | ROLES_ADMINISTRATION_ALL

# ─── Non-conformités : services d'ack ────────────────────────────
# Services qui doivent prendre connaissance d'une NC. Un seul user du service suffit
# à valider pour tout le service (cf. app/routers/qualite.py). Ordre = ordre d'affichage
# dans le tableau et la légende. Voir aussi CSS pill--{key} dans app/web/settings_page.py.
# Le service `encadrement_atelier` n'est PAS un rôle applicatif : il est attribué via
# le flag users.nc_service_override='encadrement_atelier' (indépendant du rôle métier).
NC_ACK_SERVICES = [
    {"key": "administration_ventes",    "label": "Administration des ventes",              "color": "#a78bfa"},
    {"key": "administration_technique", "label": "Administration technique",               "color": "#6366f1"},
    {"key": "encadrement_atelier",      "label": "Chef d'équipe atelier / Resp. technique","color": "#14b8a6"},
    {"key": "expedition",               "label": "Expédition",                             "color": "#f97316"},
    {"key": "commercial",               "label": "Commerciale",                            "color": "#ca8a04"},
]
NC_ACK_SERVICE_KEYS = frozenset(s["key"] for s in NC_ACK_SERVICES)

def nc_service_for_role(role, nc_service_override=None):
    """Retourne la clé du service NC associée à un user.
    - Si `nc_service_override` est renseigné et fait partie des services NC connus, il gagne.
    - Sinon, mapping direct depuis le rôle métier (aucun service pour direction / superadmin
      / comptabilite / logistique / fabrication — ces rôles ne sont pas concernés par l'ack).
    """
    if nc_service_override and nc_service_override in NC_ACK_SERVICE_KEYS:
        return nc_service_override
    mapping = {
        ROLE_ADMINISTRATION:           "administration_ventes",   # legacy → défaut ventes
        ROLE_ADMINISTRATION_VENTES:    "administration_ventes",
        ROLE_ADMINISTRATION_TECHNIQUE: "administration_technique",
        ROLE_EXPEDITION:               "expedition",
        ROLE_COMMERCIAL:               "commercial",
    }
    return mapping.get(role)

# Champs de nc_dossiers dont la modification remet à zéro les acks de tous les services
# (pertinent quand le contenu de fond change et doit être relu). Voir app/routers/qualite.py.
NC_ACK_RESET_FIELDS = frozenset({
    "titre", "description", "analyse_causes",
    "action_corrective", "action_preventive",
    "gravite", "quantite_concernee",
})

# Planning RH (Personnel)
# -- Deux vues distinctes --
#   * ATELIER : planning postes + conges du personnel fabrication / logistique.
#     Vue historique -- inchangee. Editable par direction / superadmin (+ overrides).
#   * RH      : gestion des conges / soldes de TOUS les employes actifs.
#     Nouvelle vue -- utilisee par comptabilite / direction / superadmin (edition).
ROLES_PLANNING_RH_ATELIER_VIEW = {
    ROLE_DIRECTION,
    ROLE_FABRICATION,
    ROLE_LOGISTIQUE,
    ROLE_EXPEDITION,
    ROLE_SUPERADMIN,
} | ROLES_ADMINISTRATION_ALL
ROLES_PLANNING_RH_ATELIER_EDIT = {ROLE_DIRECTION, ROLE_SUPERADMIN}
ROLES_PLANNING_RH_HR_VIEW = {ROLE_COMPTABILITE, ROLE_DIRECTION, ROLE_SUPERADMIN}
ROLES_PLANNING_RH_HR_EDIT = {ROLE_COMPTABILITE, ROLE_DIRECTION, ROLE_SUPERADMIN}
# Aliases historiques -- union des deux vues pour l'acces a l'application.
ROLES_PLANNING_RH_VIEW  = ROLES_PLANNING_RH_ATELIER_VIEW | ROLES_PLANNING_RH_HR_VIEW
ROLES_PLANNING_RH_EDIT  = ROLES_PLANNING_RH_ATELIER_EDIT | ROLES_PLANNING_RH_HR_EDIT
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

# ─── MyTradu

# ─── MyTraduction (DeepL) ─────────────────────────────────────────
# Clé API DeepL — obtenue sur https://www.deepl.com/pro-api
# Le suffixe ":fx" indique la Free API (500k caractères/mois).
# Sans suffixe = Pro API (URL différente, quota selon plan).
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")
# URL API DeepL — Free ou Pro (surchargée par .env si besoin)
DEEPL_API_URL = os.getenv(
    "DEEPL_API_URL",
    "https://api-free.deepl.com/v2" if DEEPL_API_KEY.endswith(":fx") else "https://api.deepl.com/v2",
)

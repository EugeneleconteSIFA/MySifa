"""
SIFA â€” Configuration & constantes v0.6
"""
import os
import re
from pathlib import Path

# Charge .env Ã  la racine du projet (local + VPS) avant lecture des variables.
_env_file = Path(__file__).resolve().parent / ".env"
if _env_file.is_file():
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        pass
import json
import secrets

# â”€â”€â”€ Chemins â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
DATA_DIR   = os.path.join(BASE_DIR, "data")
# Une seule base applicative : dÃ©faut data/production.db. Surcharge : variable d'environnement DB_PATH.
# Sauvegarde : copier ce fichier + data/uploads/ ; optionnel : operations.json, data/emplacements_plan.csv
DB_PATH    = os.getenv("DB_PATH", os.path.join(DATA_DIR, "production.db"))
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
# Racine des assets uploadÃ©s et servis via /uploads/* (chat, avatars, traca).
# Distincte de UPLOAD_DIR (qui reste sur data/uploads/ pour les imports mÃ©tier).
# Surcharge via UPLOADS_ROOT : permet Ã  v1 (staging) de partager le mÃªme dossier
# que v2 (prod), comme c'est dÃ©jÃ  le cas pour la DB. Ã‰vite les 404 sur les piÃ¨ces
# jointes du chat quand un message est envoyÃ© depuis l'autre instance.
UPLOADS_ROOT = os.getenv("UPLOADS_ROOT", os.path.join(BASE_DIR, "uploads"))

os.makedirs(DATA_DIR,   exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(UPLOADS_ROOT, exist_ok=True)

# â”€â”€â”€ App â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
APP_VERSION = "2.4.7"

# â”€â”€â”€ Branding paramÃ©trable â€” rÃ¨gle #1 CLAUDE.md (SIFA = dÃ©faut) â”€â”€â”€â”€
# Ces variables permettent Ã  une instance client Kernse de rebrander toute
# l'app sans modifier une seule ligne de code. Elles sont lues par
# `app/web/login_assets.py`, `html.py`, tous les rendus HTML de la sidebar,
# du portail et des footers. DÃ©faut : Â« MySifa Â» / Â« SIFA Â» (comportement
# historique inchangÃ© pour la prod SIFA).

# Nom affichÃ© en wordmark, titres, footers.
APP_NAME = os.getenv("APP_NAME", "MySifa")

# Seuil (ms) au-dela duquel une requete HTTP est loggee comme lente
# (middleware log_slow_requests dans main.py). 0 = desactive.
SLOW_REQUEST_MS = int(os.getenv("SLOW_REQUEST_MS", "500"))

# Indice de coupure du wordmark pour l'affichage bicolore. Ex. :
#   "MySifa" + APP_SPLIT=2 â†’ "My" (couleur principale) + "Sifa" (accent)
#   "Kernse" + APP_SPLIT=1 â†’ "K"  + "ernse"
_APP_SPLIT_RAW = int(os.getenv("APP_SPLIT", "2"))
APP_SPLIT       = max(1, min(_APP_SPLIT_RAW, max(1, len(APP_NAME) - 1)))
APP_NAME_PREFIX = APP_NAME[:APP_SPLIT]
APP_NAME_SUFFIX = APP_NAME[APP_SPLIT:]

# Nom de l'organisation propriÃ©taire de l'instance (utilisÃ© dans le footer,
# les emails, la meta description).
APP_ORG_NAME = os.getenv("APP_ORG_NAME", "SIFA")

# Sous-titre du login et du portail.
APP_TAGLINE = os.getenv(
    "APP_TAGLINE",
    "Portail interne â€” Production, stocks et outils mÃ©tier",
)

# Petit texte sous Â« Connexion Â» (Â« AccÃ¨s rÃ©servÃ© au personnel SIFA Â»).
APP_LOGIN_HINT = os.getenv(
    "APP_LOGIN_HINT",
    f"AccÃ¨s rÃ©servÃ© au personnel {APP_ORG_NAME}",
)

# Grand titre affichÃ© sur la login DA Kernse (KERNSE_THEME=1 uniquement).
# Ex. Â« Bienvenue. Â» suivi de Â« Portail interne Kernse. Â» â€” split en 2 lignes
# pour la mise en page grande typo Poppins de la maquette.
APP_WELCOME_TITLE = os.getenv("APP_WELCOME_TITLE", "Bienvenue.")
APP_WELCOME_SUB = os.getenv(
    "APP_WELCOME_SUB",
    f"Portail interne {APP_NAME}.",
)

# Tagline riche multi-ligne pour la login DA Kernse (au-dessus de la card).
# APP_TAGLINE reste utilisÃ©e pour le sous-titre court MySifa historique.
APP_TAGLINE_RICH = os.getenv(
    "APP_TAGLINE_RICH",
    "Production, stocks, planning, comptabilitÃ©, appels d'offre â€” "
    "tous les outils mÃ©tier au mÃªme endroit, avec la palette de "
    "commandes âŒ˜K pour aller vite.",
)

# Texte affichÃ© Ã  cÃ´tÃ© du point vert dans le footer login DA Kernse.
APP_STATUS_TEXT = os.getenv("APP_STATUS_TEXT", "Service opÃ©rationnel")

# Titre API / OpenAPI. Par dÃ©faut = APP_NAME.
APP_TITLE = os.getenv("APP_TITLE", APP_NAME)

# Onglet navigateur & SEO.
APP_PAGE_TITLE = os.getenv(
    "APP_PAGE_TITLE",
    f"{APP_NAME} â€” Portail interne {APP_ORG_NAME}",
)
APP_META_DESCRIPTION = os.getenv(
    "APP_META_DESCRIPTION",
    f"Portail interne {APP_ORG_NAME} : production, stocks, planning et outils mÃ©tier.",
)

# ThÃ¨me visuel : dark cyan MySifa (dÃ©faut) ou clair navy/orange Kernse.
# Active via KERNSE_THEME=1 dans le .env de l'instance client.
KERNSE_THEME = os.getenv("KERNSE_THEME", "0") in {"1", "true", "True", "yes", "YES"}

# Couleur barre d'Ã©tat mobile (dÃ©rivÃ©e du thÃ¨me actif).
THEME_COLOR_META = os.getenv(
    "THEME_COLOR_META",
    "#f6f4ef" if KERNSE_THEME else "#0a0e17",
)

# Page planning (/planning) â€” titre d'onglet.
APP_PLANNING_PAGE_TITLE = os.getenv(
    "APP_PLANNING_PAGE_TITLE",
    f"Planning â€” {APP_NAME}",
)

HOST        = "0.0.0.0"
PORT        = int(os.getenv("PORT", 8000))

# â”€â”€â”€ Environnement (v1 staging / v2 prod) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# ENV_NAME : "v2" (prod, dÃ©faut) ou "v1" (staging). Les deux instances tournent
# cÃ´te Ã  cÃ´te sur le VPS (v2:8000, v1:8002) et partagent la mÃªme DB.
# Toute valeur autre que "v1" est traitÃ©e comme prod (sÃ©curitÃ© par dÃ©faut).
ENV_NAME = os.getenv("ENV_NAME", "v2").strip().lower()
IS_STAGING = (ENV_NAME == "v1")

# MIGRATIONS_DISABLED : dÃ©sactive les migrations de schÃ©ma au boot. Obligatoire
# sur v1 pour ne pas modifier la DB partagÃ©e avec la prod. Valeur par dÃ©faut :
# dÃ©sactivÃ© sur v1, actif sur v2.
_migrations_default = "1" if IS_STAGING else "0"
MIGRATIONS_DISABLED = os.getenv("MIGRATIONS_DISABLED", _migrations_default) in {"1", "true", "True", "yes", "YES"}

# â”€â”€â”€ Feature flags â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PROD_STANDALONE : sert /prod depuis app/web/prod_page.py (page standalone) plutÃ´t
# que depuis le monolithe html.py via render_frontend_html("prod"). La migration
# Phase 2 a sorti tout le code MyProd vers static/mysifa_prod_core.{js,css}.
# ActivÃ© par dÃ©faut depuis la phase 2m (juin 2026). Pour repasser temporairement
# au rendu via le monolithe (rollback debug), mettre PROD_STANDALONE=0 dans .env.
# Sera retirÃ© complÃ¨tement en phase 2n (suppression du code Prod du monolithe).
PROD_STANDALONE = os.getenv("PROD_STANDALONE", "1") in {"1", "true", "True", "yes", "YES"}

# MAINTENANCE_OPEN_BETA : ouvre l'accÃ¨s du module Maintenance aux opÃ©rateurs
# (rÃ´le `fabrication`) pendant la phase de test. Quand dÃ©sactivÃ© (0, dÃ©faut),
# seuls les rÃ´les admin (superadmin, direction, administration) peuvent y
# entrer. Passer Ã  1 dans le .env pour laisser les opÃ©rateurs tester leur
# vue Â« Mes tÃ¢ches Â» sur v1 avant la promotion en prod. Les endpoints API
# vÃ©rifient ce flag cÃ´tÃ© serveur â€” inutile de patcher la sidebar seule.
MAINTENANCE_OPEN_BETA = os.getenv("MAINTENANCE_OPEN_BETA", "0") in {"1", "true", "True", "yes", "YES"}

# â”€â”€â”€ Support (email) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Objectif: permettre au front dâ€™envoyer un message au support via un endpoint FastAPI.
# Configuration SMTP via variables dâ€™environnement (prod).
SUPPORT_TO_EMAIL = os.getenv("SUPPORT_TO_EMAIL", "eleconte@sifa.pro")
SUPPORT_EMAIL_PROVIDER = os.getenv("SUPPORT_EMAIL_PROVIDER", "graph")  # graph | smtp
SUPPORT_EMAIL_DISABLED = os.getenv("SUPPORT_EMAIL_DISABLED", "0") in {"1", "true", "True", "yes", "YES"}

# â”€â”€â”€ Support (Microsoft Graph) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Envoi sans SMTP (recommandÃ© quand SMTP AUTH est dÃ©sactivÃ© sur le tenant).
MS_TENANT_ID = os.getenv("MS_TENANT_ID", "")
MS_CLIENT_ID = os.getenv("MS_CLIENT_ID", "")
MS_CLIENT_SECRET = os.getenv("MS_CLIENT_SECRET", "")
MS_SENDER_UPN = os.getenv("MS_SENDER_UPN", "")  # ex: eleconte@sifa.pro (mailbox autorisÃ©e Ã  envoyer)

SMTP_HOST      = os.getenv("SMTP_HOST", "")
SMTP_PORT      = int(os.getenv("SMTP_PORT", 587))
SMTP_USER      = os.getenv("SMTP_USER", "")
SMTP_PASS      = os.getenv("SMTP_PASS", "")
SMTP_FROM      = os.getenv("SMTP_FROM", "noreply@mysifa.fr")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "MySifa")
SMTP_TLS       = os.getenv("SMTP_TLS", "1") not in {"0", "false", "False", "no", "NO"}
SUPPORT_EMAIL_DEBUG = os.getenv("SUPPORT_EMAIL_DEBUG", "0") in {"1", "true", "True", "yes", "YES"}

# â”€â”€â”€ SÃ©curitÃ© â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
SECRET_KEY    = os.getenv("SECRET_KEY", secrets.token_hex(32))
SESSION_HOURS = 6
COOKIE_NAME   = "sifa_token"

# â”€â”€â”€ RÃ´les â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# direction              : accÃ¨s total (mÃªme droits qu'administration pour l'instant)
# administration_ventes  : gestion complÃ¨te cÃ´tÃ© ADV (ex-rÃ´le "administration", split juillet 2026)
# administration_technique : mÃªmes droits que administration_ventes pour l'instant, entitÃ© distincte
# fabrication            : lecture seule sur ses propres donnÃ©es
ROLE_DIRECTION                = "direction"
# RÃ´le historique conservÃ© comme alias pour la compatibilitÃ© (imports, code externe).
# En base, tous les users basculent en `administration_ventes` via la migration v163.
# Le super admin dÃ©place ensuite manuellement ceux qui doivent Ãªtre `administration_technique`.
ROLE_ADMINISTRATION           = "administration"
ROLE_ADMINISTRATION_VENTES    = "administration_ventes"
ROLE_ADMINISTRATION_TECHNIQUE = "administration_technique"
ROLE_FABRICATION              = "fabrication"
ROLE_LOGISTIQUE               = "logistique"
ROLE_COMPTABILITE             = "comptabilite"
ROLE_EXPEDITION               = "expedition"
ROLE_COMMERCIAL               = "commercial"
ROLE_SUPERADMIN               = "superadmin"

# Sous-ensemble Â« famille administration Â» : les deux rÃ´les issus du split partagent
# strictement les mÃªmes droits sur MySifa (juillet 2026). Utiliser ce set partout oÃ¹
# le rÃ´le `administration` Ã©tait rÃ©fÃ©rencÃ© auparavant, plutÃ´t que de dupliquer.
ROLES_ADMINISTRATION_ALL = {
    ROLE_ADMINISTRATION,            # legacy, si un user n'a pas encore Ã©tÃ© migrÃ©
    ROLE_ADMINISTRATION_VENTES,
    ROLE_ADMINISTRATION_TECHNIQUE,
}

# Compte technique : seul cet email peut porter le rÃ´le superadmin (contrÃ´lÃ© cÃ´tÃ© API).
SUPERADMIN_EMAIL = "eleconte@sifa.pro"

# RÃ´les ayant accÃ¨s aux fonctions d'administration (imports, dossiers, stats, etc.)
ROLES_ADMIN = {ROLE_DIRECTION, ROLE_SUPERADMIN} | ROLES_ADMINISTRATION_ALL
ROLES_STOCK = {ROLE_DIRECTION, ROLE_LOGISTIQUE, ROLE_EXPEDITION, ROLE_COMMERCIAL, ROLE_FABRICATION, ROLE_SUPERADMIN} | ROLES_ADMINISTRATION_ALL

# MyStock â€” zone Â« Au sol - Ã  expÃ©dier Â» : stock prÃªt Ã  expÃ©dier (code technique, affichÃ© Â« Au sol - Ã  expÃ©dier Â»)
STOCK_EMPLACEMENT_AU_SOL = "Z0"
STOCK_EMPLACEMENT_AU_SOL_LABEL = "Au sol - Ã  expÃ©dier"
STOCK_EMPLACEMENT_SORTIE_PROD = "Z1"
STOCK_EMPLACEMENT_SORTIE_PROD_LABEL = "En attente - sortie de prod"
ROLES_PROD  = {ROLE_DIRECTION, ROLE_FABRICATION, ROLE_EXPEDITION, ROLE_COMMERCIAL, ROLE_SUPERADMIN} | ROLES_ADMINISTRATION_ALL
ROLES_COMPTA = {ROLE_DIRECTION, ROLE_COMPTABILITE, ROLE_SUPERADMIN}
ROLES_EXPE = {ROLE_DIRECTION, ROLE_EXPEDITION, ROLE_LOGISTIQUE, ROLE_COMMERCIAL, ROLE_SUPERADMIN} | ROLES_ADMINISTRATION_ALL
ROLES_EXPE_WRITE = {ROLE_DIRECTION, ROLE_EXPEDITION, ROLE_SUPERADMIN} | ROLES_ADMINISTRATION_ALL
# Tuile portail Â« CoÃ»ts matiÃ¨res Â» (/pricing) â€” Direction et super admin uniquement
ROLES_PRICING = {ROLE_DIRECTION, ROLE_SUPERADMIN}
ROLES_PRICING_WRITE = ROLES_PRICING
ROLES_DEVIS = ROLES_PRICING  # alias rÃ©trocompat
ROLES_PLANNING_VIEW = {
    ROLE_DIRECTION,
    ROLE_FABRICATION,
    ROLE_EXPEDITION,
    ROLE_COMMERCIAL,
    ROLE_COMPTABILITE,
    ROLE_LOGISTIQUE,
    ROLE_SUPERADMIN,
} | ROLES_ADMINISTRATION_ALL
# MyProd : tuile portail pour la compta et la logistique, accÃ¨s limitÃ© au planning production (lecture seule cÃ´tÃ© UI/API).
ROLES_PROD_COMPTA_PLANNING = {ROLE_COMPTABILITE, ROLE_LOGISTIQUE}
# â”€â”€â”€ AccÃ¨s aux sections de ParamÃ¨tres â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Chaque section peut Ãªtre ouverte indÃ©pendamment aux rÃ´les listÃ©s.
# Direction et superadmin voient tout ; les rÃ´les techniques (admin
# technique, admin ventes, comptabilitÃ©) voient un sous-ensemble.

# Sections rÃ©servÃ©es direction + superadmin uniquement.
ROLES_SETTINGS_ACCESS        = {ROLE_DIRECTION, ROLE_SUPERADMIN}
ROLES_SETTINGS_COMMUNICATION = {ROLE_DIRECTION, ROLE_SUPERADMIN}
ROLES_SETTINGS_AUDIT_FULL    = {ROLE_DIRECTION, ROLE_SUPERADMIN}
ROLES_SETTINGS_PRINT_FULL    = {ROLE_DIRECTION, ROLE_SUPERADMIN}

# Fabrication + Logistique : direction, superadmin, administration technique.
ROLES_SETTINGS_FABRICATION = {ROLE_DIRECTION, ROLE_SUPERADMIN, ROLE_ADMINISTRATION_TECHNIQUE}
ROLES_SETTINGS_LOGISTIQUE  = {ROLE_DIRECTION, ROLE_SUPERADMIN, ROLE_ADMINISTRATION_TECHNIQUE}

# Contacts : les 3 rÃ´les administration + comptabilitÃ©.
ROLES_SETTINGS_CONTACTS = {ROLE_DIRECTION, ROLE_SUPERADMIN, ROLE_COMPTABILITE} | ROLES_ADMINISTRATION_ALL

# Imprimantes + Registre FSC : mÃªmes rÃ´les que Contacts. RegroupÃ©s dans une
# section Â« Outils Â» cÃ´tÃ© UI pour les rÃ´les techniques (direction/superadmin
# les voient depuis Impression & dÃ©ploiement / Audit & qualitÃ©).
ROLES_SETTINGS_PRINTERS = {ROLE_DIRECTION, ROLE_SUPERADMIN, ROLE_COMPTABILITE} | ROLES_ADMINISTRATION_ALL
ROLES_SETTINGS_FSC      = {ROLE_DIRECTION, ROLE_SUPERADMIN, ROLE_COMPTABILITE} | ROLES_ADMINISTRATION_ALL

# Union : rÃ´les autorisÃ©s Ã  ouvrir /settings (au moins une section accessible).
ROLES_SETTINGS = (
    ROLES_SETTINGS_ACCESS
    | ROLES_SETTINGS_COMMUNICATION
    | ROLES_SETTINGS_AUDIT_FULL
    | ROLES_SETTINGS_PRINT_FULL
    | ROLES_SETTINGS_FABRICATION
    | ROLES_SETTINGS_LOGISTIQUE
    | ROLES_SETTINGS_CONTACTS
    | ROLES_SETTINGS_PRINTERS
    | ROLES_SETTINGS_FSC
)

# Applications dont l'accÃ¨s peut Ãªtre surchargÃ© par utilisateur (hors ParamÃ¨tres : accÃ¨s gÃ©rÃ© par ROLES_SETTINGS_*).
ACCESS_OVERRIDABLE_APPS = frozenset({"prod", "planning", "planning_rh", "stock", "compta", "expe", "pricing"})

# â”€â”€â”€ ContrÃ´le d'accÃ¨s database-driven (migration 184) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# 4 niveaux ordinaux â€” admin >= write >= read >= none. UtilisÃ© partout oÃ¹ le
# code testait auparavant `role in ROLES_STOCK` etc. Voir user_can() dans
# services/auth_service.py. La granularitÃ© est (app, module) : module_id
# vaut '_app' pour l'accÃ¨s gÃ©nÃ©ral Ã  l'appli, sinon nom d'onglet.
ACCESS_LEVELS = ("none", "read", "write", "admin")
LEVEL_ORDER = {"none": 0, "read": 1, "write": 2, "admin": 3}
LEVEL_LABELS = {
    "none": "Aucun accÃ¨s",
    "read": "Lecture",
    "write": "Ã‰criture",
    "admin": "Admin (actions sensibles)",
}

# Catalogue des applications et de leurs sous-modules (onglets). Ã‰ditÃ© ici,
# lu partout : matrice d'accÃ¨s, rÃ©fÃ©rentiel rÃ´les, endpoints ParamÃ¨tres,
# helper user_can. Ordre = ordre d'affichage dans la matrice. `modules` vide
# = une seule vue, pas de granularitÃ© de sous-module possible.
APPS_CATALOG = [
    {"id": "prod", "label": "MyProd", "modules": [
        {"id": "production", "label": "Production"},
        {"id": "traceabilite", "label": "TraÃ§abilitÃ©"},
        {"id": "rentabilite", "label": "RentabilitÃ©"},
        {"id": "of", "label": "Fiches + OF"},
    ]},
    {"id": "planning", "label": "Planning machine", "modules": []},
    {"id": "planning_rh", "label": "Planning RH", "modules": [
        {"id": "atelier", "label": "Planning atelier"},
        {"id": "conges", "label": "CongÃ©s / RH"},
    ]},
    {"id": "stock", "label": "MyStock", "modules": [
        {"id": "dashboard", "label": "Tableau de bord"},
        {"id": "produits-finis", "label": "Produits finis"},
        {"id": "matieres", "label": "MatiÃ¨res premiÃ¨res"},
        {"id": "inventaire", "label": "Inventaire produit"},
        {"id": "matieres-inventaire", "label": "Inventaire matiÃ¨re"},
        {"id": "reception", "label": "RÃ©ception matiÃ¨re"},
        {"id": "traca", "label": "Ã‰tiquettes traÃ§a"},
        {"id": "historique", "label": "Historique mouvements"},
        {"id": "plan-entrepot", "label": "Plan entrepÃ´t"},
        {"id": "negoce", "label": "Produits de nÃ©goce"},
        {"id": "referentiel", "label": "RÃ©fÃ©rentiel"},
        {"id": "monitoring", "label": "Monitoring"},
        {"id": "valorisation", "label": "Valorisation"},
    ]},
    {"id": "compta", "label": "MyCompta", "modules": [
        {"id": "factor", "label": "Factor"},
        {"id": "acheteurs", "label": "Acheteurs"},
        {"id": "comptes", "label": "Comptes"},
        {"id": "banques", "label": "Banques"},
        {"id": "cession", "label": "Cession"},
        {"id": "paie", "label": "Paie"},
    ]},
    {"id": "expe", "label": "MyExpÃ©", "modules": [
        {"id": "suivi_departs", "label": "DÃ©parts"},
        {"id": "palettes_europe", "label": "Palettes Europe"},
        {"id": "comparateur", "label": "Comparateur tarifs"},
        {"id": "devis", "label": "Devis transporteurs"},
        {"id": "poids", "label": "Calcul poids"},
        {"id": "transporteurs", "label": "Transporteurs"},
        {"id": "prospects", "label": "Prospects"},
    ]},
    {"id": "pricing", "label": "Pricing", "modules": []},
    {"id": "fabrication", "label": "Fabrication (opÃ©rateurs)", "modules": []},
    {"id": "qualite", "label": "MyQualitÃ©", "modules": [
        {"id": "list", "label": "Non-conformitÃ©s"},
        {"id": "audits-list", "label": "Audits"},
        {"id": "ressources-list", "label": "Ressources"},
        {"id": "ref-list", "label": "RÃ©fÃ©rentiel"},
    ]},
    {"id": "settings", "label": "ParamÃ¨tres", "modules": []},
]

# Index de recherche rapide : {app_id: {module_id: label}}
_APP_MODULE_INDEX = {}
for _a in APPS_CATALOG:
    _APP_MODULE_INDEX[_a["id"]] = {"_app": _a["label"]}
    for _m in _a.get("modules", []):
        _APP_MODULE_INDEX[_a["id"]][_m["id"]] = _m["label"]


def app_module_label(app_id: str, module_id: str = "_app") -> str:
    """Label lisible d'un couple (app, module) â€” fallback sur l'id si inconnu."""
    return _APP_MODULE_INDEX.get(app_id, {}).get(module_id) or module_id


def is_known_app_module(app_id: str, module_id: str = "_app") -> bool:
    """True si (app, module) est rÃ©fÃ©rencÃ© dans APPS_CATALOG."""
    return module_id in _APP_MODULE_INDEX.get(app_id, {})

# RÃ´les assignables lors de la crÃ©ation / Ã©dition d'utilisateurs (hors super admin).
# Le rÃ´le legacy `administration` n'est plus proposÃ© : le super admin choisit dÃ©sormais
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

# â”€â”€â”€ Non-conformitÃ©s : services d'ack â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Services qui doivent prendre connaissance d'une NC. Un seul user du service suffit
# Ã  valider pour tout le service (cf. app/routers/qualite.py). Ordre = ordre d'affichage
# dans le tableau et la lÃ©gende. Voir aussi CSS pill--{key} dans app/web/settings_page.py.
# Le service `encadrement_atelier` n'est PAS un rÃ´le applicatif : il est attribuÃ© via
# le flag users.nc_service_override='encadrement_atelier' (indÃ©pendant du rÃ´le mÃ©tier).
NC_ACK_SERVICES = [
    {"key": "administration_ventes",    "label": "Administration des ventes",              "color": "#a78bfa"},
    {"key": "administration_technique", "label": "Administration technique",               "color": "#6366f1"},
    {"key": "encadrement_atelier",      "label": "Chef d'Ã©quipe atelier / Resp. technique","color": "#14b8a6"},
    {"key": "expedition",               "label": "ExpÃ©dition",                             "color": "#f97316"},
    {"key": "commercial",               "label": "Commerciale",                            "color": "#ca8a04"},
]
NC_ACK_SERVICE_KEYS = frozenset(s["key"] for s in NC_ACK_SERVICES)

def nc_service_for_role(role, nc_service_override=None):
    """Retourne la clÃ© du service NC associÃ©e Ã  un user.
    - Si `nc_service_override` est renseignÃ© et fait partie des services NC connus, il gagne.
    - Sinon, mapping direct depuis le rÃ´le mÃ©tier (aucun service pour direction / superadmin
      / comptabilite / logistique / fabrication â€” ces rÃ´les ne sont pas concernÃ©s par l'ack).
    """
    if nc_service_override and nc_service_override in NC_ACK_SERVICE_KEYS:
        return nc_service_override
    mapping = {
        ROLE_ADMINISTRATION:           "administration_ventes",   # legacy â†’ dÃ©faut ventes
        ROLE_ADMINISTRATION_VENTES:    "administration_ventes",
        ROLE_ADMINISTRATION_TECHNIQUE: "administration_technique",
        ROLE_EXPEDITION:               "expedition",
        ROLE_COMMERCIAL:               "commercial",
    }
    return mapping.get(role)

# Champs de nc_dossiers dont la modification remet Ã  zÃ©ro les acks de tous les services
# (pertinent quand le contenu de fond change et doit Ãªtre relu). Voir app/routers/qualite.py.
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

# Profils utilisateurs exclus du planning RH (comparaison sur nom normalisÃ© : trim + minuscules).
PLANNING_RH_EXCLUDED_NOMS = frozenset({"logistique sifa"})


def default_app_access_for_role(role: str) -> dict:
    """AccÃ¨s applications issus du seul rÃ´le (avant surcharges utilisateur)."""
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

# Admin par dÃ©faut
DEFAULT_ADMIN_EMAIL = "admin@sifa.fr"
DEFAULT_ADMIN_NOM   = "Administrateur"
DEFAULT_ADMIN_PWD   = "Admin1234!"

# â”€â”€â”€ Codes opÃ©rations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
CODE_ARRIVEE    = "86"
CODE_DEPART     = "87"
CODE_DEBUT_DOS  = "01"
CODE_FIN_DOS    = "89"
CODE_CALAGE     = "02"
CODE_PRODUCTION = "03"
CODE_REPRISE    = "88"

# Ensemble complet des codes traitÃ©s comme du temps de calage
# (02 calage, 10-12 rÃ©glages, 58-60 prÃ©parations, 67 vidange, 74-75 essais)
CODES_CALAGE: frozenset[str] = frozenset({
    "02", "10", "11", "12", "58", "59", "60", "67", "74", "75"
})

# â”€â”€â”€ Classification opÃ©rations â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_ALLOWED_SEVERITY = frozenset({"info", "attention", "critique"})


# â”€â”€â”€ Jours fÃ©riÃ©s nationaux (France mÃ©tropolitaine) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Source MyCalendrier (calendrier Â« Jours fÃ©riÃ©s Â») â€” distinct des jours off planning machine.
FERIES_NATIONAUX_FR: dict[int, list[tuple[str, str]]] = {
    2025: [
        ("2025-01-01", "Jour de l'an"),
        ("2025-04-21", "Lundi de PÃ¢ques"),
        ("2025-05-01", "FÃªte du Travail"),
        ("2025-05-08", "Victoire des AlliÃ©s 1945"),
        ("2025-05-29", "Jeudi de l'Ascension"),
        ("2025-06-09", "Lundi de PentecÃ´te"),
        ("2025-07-14", "FÃªte Nationale"),
        ("2025-08-15", "Assomption"),
        ("2025-11-01", "La Toussaint"),
        ("2025-11-11", "Armistice 1918"),
        ("2025-12-25", "NoÃ«l"),
    ],
    2026: [
        ("2026-01-01", "Jour de l'an"),
        ("2026-04-06", "Lundi de PÃ¢ques"),
        ("2026-05-01", "FÃªte du Travail"),
        ("2026-05-08", "Victoire des AlliÃ©s 1945"),
        ("2026-05-14", "Jeudi de l'Ascension"),
        ("2026-05-25", "Lundi de PentecÃ´te"),
        ("2026-07-14", "FÃªte Nationale"),
        ("2026-08-15", "Assomption"),
        ("2026-11-01", "La Toussaint"),
        ("2026-11-11", "Armistice 1918"),
        ("2026-12-25", "NoÃ«l"),
    ],
}


def national_holidays_between(date_debut: str, date_fin: str) -> list[tuple[str, str]]:
    """Jours fÃ©riÃ©s nationaux entre deux dates YYYY-MM-DD (inclus)."""
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
    """LÃ¨ve ValueError si la structure de operations.json est invalide."""
    if not isinstance(data, dict) or len(data) == 0:
        raise ValueError("operations.json doit Ãªtre un objet JSON non vide.")
    for code, entry in data.items():
        ck = str(code).strip()
        if not ck or not re.match(r"^\d+$", ck):
            raise ValueError(f"operations.json : clÃ© de code invalide Â« {code} Â».")
        if not isinstance(entry, dict):
            raise ValueError(f"operations.json : l'entrÃ©e Â« {ck} Â» doit Ãªtre un objet.")
        for k in ("severity", "label", "category"):
            if k not in entry:
                raise ValueError(f"operations.json : Â« {ck} Â» manque le champ Â« {k} Â».")
            if not isinstance(entry[k], str):
                raise ValueError(f"operations.json : Â« {ck} Â».{k} doit Ãªtre une chaÃ®ne.")
        if entry["severity"] not in _ALLOWED_SEVERITY:
            raise ValueError(
                f"operations.json : Â« {ck} Â».severity invalide (Â« {entry['severity']} Â»)."
            )


def load_operations():
    """Charge le rÃ©fÃ©rentiel (SQLite prioritaire, repli operations.json)."""
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
            raise RuntimeError(f"JSON invalide : {path} â€” {e}") from e
        try:
            validate_operations_config(data)
        except ValueError as e:
            raise RuntimeError(f"operations.json : {e}") from e
        return data


def refresh_operations_cache():
    """Recharge OPERATION_SEVERITY aprÃ¨s modification en base."""
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
# Domaine public prod (liens portail / emails) â€” surcharge via PUBLIC_BASE_URL ou BASE_URL
PUBLIC_BASE_URL_DEFAULT = "https://www.mysifa.com"


def public_base_url() -> str:
    """URL absolue pour liens emails et portail (jamais localhost si non configurÃ©)."""
    raw = (
        os.getenv("PUBLIC_BASE_URL")
        or os.getenv("BASE_URL")
        or PUBLIC_BASE_URL_DEFAULT
    ).strip().rstrip("/")
    low = raw.lower()
    if not raw or "localhost" in low or "127.0.0.1" in low:
        return PUBLIC_BASE_URL_DEFAULT.rstrip("/")
    return raw

# â”€â”€â”€ Chat (GIPHY) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
GIPHY_API_KEY = os.getenv("GIPHY_API_KEY", "")

# â”€â”€â”€ MyExpÃ© â€” parsing grilles tarifaires (IA) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# â”€â”€â”€ MyTradu

# â”€â”€â”€ MyTraduction (DeepL) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# ClÃ© API DeepL â€” obtenue sur https://www.deepl.com/pro-api
# Le suffixe ":fx" indique la Free API (500k caractÃ¨res/mois).
# Sans suffixe = Pro API (URL diffÃ©rente, quota selon plan).
DEEPL_API_KEY = os.getenv("DEEPL_API_KEY", "")
# URL API DeepL â€” Free ou Pro (surchargÃ©e par .env si besoin)
DEEPL_API_URL = os.getenv(
    "DEEPL_API_URL",
    "https://api-free.deepl.com/v2" if DEEPL_API_KEY.endswith(":fx") else "https://api.deepl.com/v2",
)

"""MySifa — Taxonomie du journal des actions.

Pourquoi ce fichier
-------------------
Le journal (Paramètres › Journal des actions) reposait sur deux listes écrites
en dur dans la page : 8 modules et 7 actions. Le code, lui, en émettait déjà 15
et 17. Résultat : les actions AO, produits et maintenance n'étaient filtrables
nulle part et s'affichaient en brut. Et surtout, seuls 7 routers sur 65
appelaient `log_action` — l'écrasante majorité des gestes faits dans MySifa
n'entrait jamais dans le journal.

Ce module est la source de vérité unique de la taxonomie. Il sert :

- au middleware d'audit, pour ranger une requête HTTP dans un module et lui
  donner un verbe d'action ;
- à l'API `/api/settings/audit/facets`, pour habiller de libellés français les
  valeurs réellement présentes en base ;
- à la page Paramètres, qui ne connaît plus aucune liste en dur.

Ajouter un module ou une action se fait ICI, une seule fois. Les listes
déroulantes du journal suivent d'elles-mêmes, puisqu'elles se construisent à
partir de ce qui existe en base.
"""
from __future__ import annotations

import unicodedata
from typing import Optional

# ─── Modules ────────────────────────────────────────────────────────
# La clé est ce qui est stocké en base (colonne `module`). Les clés déjà
# présentes en production (planning, fabrication, stock, expe, rh, settings,
# auth, portal, ao, produits, maintenance_*) sont conservées telles quelles :
# les renommer rendrait l'historique illisible.
MODULE_LABELS: dict[str, str] = {
    "ai": "Assistant IA",
    "alerts": "Alertes",
    "ao": "MyAO",
    "arret_seuils": "Seuils d'arrêt",
    "auth": "Authentification",
    "bat": "BAT étiquette",
    "besoins": "Besoins matières",
    "bridge": "Passerelle API",
    "calendrier": "MyCalendrier",
    "chat": "Discussions",
    "clients": "Clients",
    "coffre": "Coffre-fort",
    "compta": "Comptabilité",
    "dashboards": "Tableaux de bord",
    "db": "Base de données",
    "dossiers": "Dossiers",
    "erp": "ERP / RVGI",
    "expe": "MyExpé",
    "fabrication": "Fabrication",
    "fsc": "FSC",
    "guides": "Guides in-app",
    "imports": "Imports",
    "learning": "Formations",
    "maintenance": "Maintenance",
    "mcp": "Serveur MCP",
    "maintenance_alerts": "Maintenance · alertes",
    "maintenance_codes": "Maintenance · codes",
    "maintenance_docs": "Maintenance · documents",
    "maintenance_libres": "Maintenance · opérations libres",
    "maintenance_usure_pieces": "Maintenance · pièces d'usure",
    "matieres_prix": "Coûts matières",
    "messages": "Messagerie",
    "of": "OF & fiches techniques",
    "paie": "Paie",
    "planning": "Planning",
    "portal": "Portail public",
    "postit": "Post-it",
    "pricing": "Chiffrage",
    "print": "MyPrint",
    "produits": "Mémoire produit",
    "profil": "Profil utilisateur",
    "push": "Notifications push",
    "qualite": "MyQualité",
    "qualite_ged": "MyQualité · GED",
    "rapports_prod": "Retour de prod",
    "reconciliation": "Rapprochement",
    "rentabilite": "Rentabilité",
    "reunions": "Points de production",
    "rh": "Planning RH",
    "rh_coffre": "Coffre RH",
    "saisies": "Saisies de production",
    "settings": "Paramètres",
    "stock": "MyStock",
    "support": "Support",
    "taches": "Tâches",
    "traca": "Traçabilité",
    "autre": "Autre",
}

# ─── Actions ────────────────────────────────────────────────────────
ACTION_LABELS: dict[str, str] = {
    "ACK": "Accusé de lecture",
    "ARCHIVE": "Archivage",
    "ASSIGN": "Affectation",
    "CANCEL": "Annulation",
    "CLOSE": "Clôture",
    "COMMENT": "Commentaire",
    "CREATE": "Création",
    "DELETE": "Suppression",
    "DENIED": "Accès refusé",
    "DEPLOY": "Mise en production",
    "DUPLICATE": "Duplication",
    "EXPORT": "Export",
    "IMPERSONATE": "Simulation de rôle",
    "IMPORT": "Import",
    "INVENTAIRE": "Inventaire",
    "LINK": "Rattachement",
    "LOGIN": "Connexion",
    "LOGOUT": "Déconnexion",
    "MERGE": "Fusion",
    "MOVE": "Déplacement",
    "PRINT": "Impression",
    "REORDER": "Réorganisation",
    "RESET": "Réinitialisation",
    "RESTORE": "Restauration",
    "SAISIE": "Saisie atelier",
    "SEARCH": "Recherche",
    "SEND": "Envoi",
    "SYNC": "Synchronisation",
    "UNLINK": "Détachement",
    "UPDATE": "Modification",
    "UPLOAD": "Dépôt de fichier",
    "VALIDATE": "Validation",
    "VALIDATE_DUP": "Validation doublon",
}

# Couleurs : noms de variables CSS du design system, jamais de valeur en dur.
ACTION_COLORS: dict[str, str] = {
    "CREATE": "var(--ok)",
    "UPDATE": "var(--accent)",
    "DELETE": "var(--danger)",
    "DENIED": "var(--danger)",
    "CANCEL": "var(--danger)",
    "VALIDATE": "var(--warn)",
    "VALIDATE_DUP": "var(--warn)",
    "IMPERSONATE": "var(--warn)",
    "DEPLOY": "var(--warn)",
    "SAISIE": "var(--accent)",
    "SEARCH": "var(--accent)",
    "SEND": "var(--accent)",
    "SYNC": "var(--accent)",
    "IMPORT": "var(--ok)",
    "UPLOAD": "var(--ok)",
    "DUPLICATE": "var(--ok)",
    "RESTORE": "var(--ok)",
    "COMMENT": "var(--text2)",
    "ASSIGN": "var(--text2)",
    "LINK": "var(--text2)",
    "UNLINK": "var(--text2)",
    "REORDER": "var(--text2)",
    "MOVE": "var(--text2)",
    "EXPORT": "var(--text2)",
    "PRINT": "var(--text2)",
    "LOGIN": "var(--text2)",
    "MERGE": "var(--text2)",
    "INVENTAIRE": "var(--text2)",
    "CLOSE": "var(--muted)",
    "ARCHIVE": "var(--muted)",
    "LOGOUT": "var(--muted)",
    "RESET": "var(--muted)",
    "ACK": "var(--muted)",
}
DEFAULT_ACTION_COLOR = "var(--text2)"

# ─── Chemin → module ────────────────────────────────────────────────
# Le middleware ne voit qu'une URL. Ce tableau la range dans un module.
# L'ordre d'écriture n'a pas d'importance : la résolution teste les préfixes
# du plus long au plus court, donc `/api/stock/besoins-matieres` l'emporte
# toujours sur `/api/stock`.
PATH_MODULES: dict[str, str] = {
    "/api/ai": "ai",
    "/api/alerts": "alerts",
    "/api/ao": "ao",
    "/api/arret-seuils": "arret_seuils",
    "/api/auth": "auth",
    "/api/bat": "bat",
    "/api/bridge": "bridge",
    "/api/calendrier": "calendrier",
    "/calendrier/invitation": "calendrier",
    "/api/chat": "chat",
    "/api/clients": "clients",
    "/api/coffre": "coffre",
    "/api/compta": "compta",
    "/api/dashboards": "dashboards",
    "/api/db": "db",
    "/api/dossiers": "dossiers",
    "/api/erp": "erp",
    "/api/rvgi": "erp",
    "/api/rvgi-tiers": "erp",
    "/api/sync-db-v1": "erp",
    "/api/expe": "expe",
    "/api/fabrication": "fabrication",
    "/api/fsc": "fsc",
    "/api/guides": "guides",
    "/api/import": "imports",
    "/api/imports": "imports",
    "/api/learning": "learning",
    "/api/maintenance": "maintenance",
    "/api/matiere": "matieres_prix",
    "/api/messages": "messages",
    "/api/of": "of",
    "/api/fiches-techniques": "of",
    "/api/admin/backfill-ref-produit-norm": "of",
    "/api/admin/dossiers-sans-of": "of",
    "/api/admin/link-planning-of": "of",
    "/api/admin/of-link-pending": "of",
    "/api/admin/planning-of-links": "of",
    "/api/admin/relink-of": "of",
    "/api/admin/mp_laizes": "stock",
    "/api/paie": "paie",
    "/api/perf": "profil",
    "/api/planning": "planning",
    "/api/portail": "portal",
    "/api/portal": "portal",
    "/portail": "portal",
    "/api/postits": "postit",
    "/api/pricing": "pricing",
    "/api/print": "print",
    "/api/produits": "produits",
    "/api/profil": "profil",
    "/api/impersonate": "auth",
    "/api/users": "auth",
    "/api/push": "push",
    "/api/qualite/ged": "qualite_ged",
    "/api/qualite": "qualite",
    "/api/rapports-prod": "rapports_prod",
    "/api/reconciliation": "reconciliation",
    "/api/rentabilite": "rentabilite",
    "/api/reunions": "reunions",
    "/api/rh": "rh",
    "/api/rh-coffre": "rh_coffre",
    "/api/saisies": "saisies",
    "/api/settings": "settings",
    "/api/fournisseurs": "settings",
    "/api/updates": "settings",
    "/api/promote": "settings",
    "/api/stock/besoins-matieres": "besoins",
    "/api/stock/destockage": "besoins",
    "/api/stock-compare": "stock",
    "/api/stock": "stock",
    "/api/support": "support",
    "/api/taches": "taches",
    "/api/traca": "traca",
}

# Trié une fois pour toutes : le préfixe le plus spécifique gagne.
_PATH_MODULES_SORTED: list[tuple[str, str]] = sorted(
    PATH_MODULES.items(), key=lambda kv: len(kv[0]), reverse=True
)

# ─── Segment d'URL → action ─────────────────────────────────────────
# Lu depuis la FIN du chemin : `/api/qualite/documents/12/valider` donne
# VALIDATE et non UPLOAD, parce que le dernier segment parlant l'emporte.
SEGMENT_ACTIONS: dict[str, str] = {
    "ack": "ACK",
    "accuser": "ACK",
    "annuler": "CANCEL",
    "annulation": "CANCEL",
    "archiver": "ARCHIVE",
    "archive": "ARCHIVE",
    "assigner": "ASSIGN",
    "assignation": "ASSIGN",
    "cloturer": "CLOSE",
    "cloture": "CLOSE",
    "solder": "CLOSE",
    "terminer": "CLOSE",
    "commentaire": "COMMENT",
    "commentaires": "COMMENT",
    "deplacer": "MOVE",
    "deplacer-lot": "MOVE",
    "dupliquer": "DUPLICATE",
    "copier": "DUPLICATE",
    "envoyer": "SEND",
    "envoi": "SEND",
    "relance": "SEND",
    "relancer": "SEND",
    "notifier": "SEND",
    "export": "EXPORT",
    "exporter": "EXPORT",
    "export-modifiees": "EXPORT",
    "fusion": "MERGE",
    "fusionner": "MERGE",
    "merge": "MERGE",
    "impersonate": "IMPERSONATE",
    "import": "IMPORT",
    "importer": "IMPORT",
    "import-excel": "IMPORT",
    "import-from-data": "IMPORT",
    "inventaire": "INVENTAIRE",
    "inventaire-v2": "INVENTAIRE",
    "label": "PRINT",
    "imprimer": "PRINT",
    "pdf": "PRINT",
    "lier": "LINK",
    "link": "LINK",
    "relink": "LINK",
    "rattacher": "LINK",
    "rattachement": "LINK",
    "rattachements": "LINK",
    "delier": "UNLINK",
    "detacher": "UNLINK",
    "login": "LOGIN",
    "connexion": "LOGIN",
    "logout": "LOGOUT",
    "deconnexion": "LOGOUT",
    "miroir": "SYNC",
    "synchroniser": "SYNC",
    "sync": "SYNC",
    "mouvement": "SAISIE",
    "mouvements": "SAISIE",
    "saisie": "SAISIE",
    "saisie-stock": "SAISIE",
    "saisies": "SAISIE",
    "scan": "SAISIE",
    "pointage": "SAISIE",
    "ordre": "REORDER",
    "reorder": "REORDER",
    "reordonner": "REORDER",
    "promote": "DEPLOY",
    "promotion": "DEPLOY",
    "reset": "RESET",
    "reinitialiser": "RESET",
    "seed-defaults": "RESET",
    "restaurer": "RESTORE",
    "restore": "RESTORE",
    "reactiver": "RESTORE",
    "recherche": "SEARCH",
    "rechercher": "SEARCH",
    "search": "SEARCH",
    "upload": "UPLOAD",
    "televerser": "UPLOAD",
    "pieces-jointes": "UPLOAD",
    "valider": "VALIDATE",
    "validation": "VALIDATE",
    "validate": "VALIDATE",
    "definitif": "VALIDATE",
}

_METHOD_ACTIONS = {"POST": "CREATE", "PUT": "UPDATE", "PATCH": "UPDATE", "DELETE": "DELETE"}

# ─── Bruit technique — jamais journalisé ────────────────────────────
# Ces appels sont émis par la machine, pas par un humain : les journaliser
# noierait le journal sous des milliers de lignes sans auteur ni intention.
SKIP_PREFIXES: tuple[str, ...] = (
    "/api/guides/heartbeat",
    "/api/print/agent/heartbeat",
    "/api/print/agent/jobs",
    "/api/print/preview",
    "/api/perf",
    "/api/push/subscribe",
    "/api/push/unsubscribe",
    "/api/translate",
    "/api/alerts",
    "/api/ai",
    "/api/health",
    "/healthz",
    # Le serveur MCP ne fait que lire : le journal trace ce qui change, pas ce
    # qu'on regarde, et journaliser chaque `initialize` / `tools/list` noierait
    # l'ecran. Ce qui compte — quel outil, quelle requete SQL — est ecrit
    # explicitement par le routeur via log_action(module="mcp").
    "/mcp",
    "/api/filters",
    "/static/",
    "/uploads/",
)

# Modules où l'action est journalisée mais JAMAIS son contenu : le corps de
# la requête y transporte des messages personnels, des documents RH ou des
# éléments de paie. Tracer qui a fait quoi, sans recopier quoi que ce soit.
BODY_BLIND_MODULES: frozenset[str] = frozenset(
    {"chat", "messages", "coffre", "rh_coffre", "paie", "ai"}
)

# Clés dont la valeur ne doit jamais atterrir dans le journal.
SENSITIVE_KEYS: tuple[str, ...] = (
    "password", "mot_de_passe", "mdp", "pwd", "token", "secret", "cle", "api_key",
    "apikey", "cookie", "session", "hash", "authorization", "signature",
)


def _sans_accent(txt: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn"
    )


def module_label(module: str) -> str:
    return MODULE_LABELS.get((module or "").lower(), module or "—")


def action_label(action: str) -> str:
    return ACTION_LABELS.get((action or "").upper(), action or "—")


def action_color(action: str) -> str:
    return ACTION_COLORS.get((action or "").upper(), DEFAULT_ACTION_COLOR)


def is_skipped(path: str) -> bool:
    p = (path or "").lower()
    return any(p.startswith(pref) for pref in SKIP_PREFIXES)


def resolve_module(path: str) -> str:
    """Range une URL dans un module du journal."""
    p = (path or "").lower().rstrip("/")
    for prefix, module in _PATH_MODULES_SORTED:
        if p == prefix or p.startswith(prefix + "/"):
            return module
    return "autre"


def resolve_action(method: str, path: str) -> str:
    """Verbe d'action déduit de la méthode HTTP et du chemin.

    Un DELETE est toujours une suppression — aucun mot-clé d'URL ne le
    requalifie, sinon `DELETE /taches/12/commentaires/3` passerait pour un
    commentaire alors qu'il en efface un.
    """
    m = (method or "").upper()
    if m == "DELETE":
        return "DELETE"
    segments = [s for s in (path or "").split("/") if s]
    for seg in reversed(segments):
        if seg.isdigit() or seg.startswith("{"):
            continue
        hit = SEGMENT_ACTIONS.get(_sans_accent(seg.lower()))
        if hit:
            return hit
    return _METHOD_ACTIONS.get(m, m or "UPDATE")


def redact(value):
    """Retire des données toute valeur portant une clé sensible."""
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            kl = _sans_accent(str(k).lower())
            if any(s in kl for s in SENSITIVE_KEYS):
                out[k] = "***"
            else:
                out[k] = redact(v)
        return out
    if isinstance(value, list):
        return [redact(v) for v in value[:20]]
    if isinstance(value, str) and len(value) > 300:
        return value[:300] + "…"
    return value


METHODES_ECRITURE = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def parcourir_routes(objet, prefixe: str = "", _profondeur: int = 0):
    """Enumere `(methodes, chemin)` pour toutes les routes d'une application.

    Pourquoi ce n'est pas un simple `for route in app.routes` : selon la
    version de FastAPI, `include_router` ne range pas les routes au meme
    endroit. Jusqu'a la 0.115 (celle epinglee en production) il aplatit tout
    dans `app.routes` ; a partir de la 0.140 il pose un routeur paresseux qui
    garde ses routes dans `original_router` et son prefixe dans
    `include_context`. Une couverture qui ne connaitrait qu'une seule de ces
    deux formes annoncerait « 4 routes » sur l'autre — un ecran de couverture
    qui ment est pire que pas d'ecran du tout.

    On descend donc sur ce que l'objet expose, sans dependre d'un nom de
    classe interne.
    """
    if _profondeur > 8:
        return

    methodes = getattr(objet, "methods", None)
    chemin = getattr(objet, "path", None)
    if methodes and chemin is not None:
        yield {str(m).upper() for m in methodes}, prefixe + chemin
        return

    # FastAPI >= 0.140 : inclusion paresseuse.
    inclus = getattr(objet, "original_router", None)
    if inclus is not None:
        contexte = getattr(objet, "include_context", None)
        yield from parcourir_routes(
            inclus,
            prefixe + (getattr(contexte, "prefix", "") or ""),
            _profondeur + 1,
        )
        return

    enfants = getattr(objet, "routes", None)
    if enfants:
        base = prefixe + (chemin or "")
        for enfant in enfants:
            yield from parcourir_routes(enfant, base, _profondeur + 1)


def routes_ecriture(app):
    """Les `(methode, chemin)` d'ecriture de l'application, doublons compris."""
    for methodes, chemin in parcourir_routes(app):
        for methode in sorted(methodes & METHODES_ECRITURE):
            yield methode, chemin


def humaniser_endpoint(nom: Optional[str]) -> str:
    """`creer_tache_commentaire` → `Creer tache commentaire`."""
    if not nom:
        return ""
    return nom.replace("_", " ").strip().capitalize()

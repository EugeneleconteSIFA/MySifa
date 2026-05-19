"""MySifa — Contexte et utilitaires pour l'agent IA."""
from __future__ import annotations
from datetime import datetime
import zoneinfo

PARIS = zoneinfo.ZoneInfo("Europe/Paris")

# Accès IA restreint au superadmin uniquement pour l'instant.
# Pour ouvrir à d'autres rôles plus tard, ajouter les entrées ici.
ROLE_SCOPE: dict[str, list[str]] = {
    "superadmin": ["production", "planning", "stock", "expe", "rh", "paie", "admin"],
    "direction": ["production", "planning", "stock", "expe", "rh", "paie", "admin"],
    "administration": ["production", "planning", "stock", "expe", "rh", "paie", "admin"],
}

READ_TOOL_NAMES: list[str] = [
    "production_detail",
    "planning_detail",
    "stock_search",
    "expe_detail",
]

ACTION_TOOL_NAMES: list[str] = [
    "planning_close_dossier",
    "stock_adjust",
]

ALL_TOOL_NAMES: list[str] = READ_TOOL_NAMES + ACTION_TOOL_NAMES

BRIEF_ROLES = frozenset({"superadmin", "direction"})
ANOMALY_ROLES = frozenset({"superadmin", "direction"})


def get_user_scope(role: str) -> list[str]:
    return ROLE_SCOPE.get(role, [])


def get_tools_for_role(role: str) -> list[str]:
    """Outils autorisés pour le rôle. Étendre ici pour ouvrir à d'autres rôles."""
    if role == "superadmin":
        return list(ALL_TOOL_NAMES)
    if role == "direction":
        return list(ALL_TOOL_NAMES)
    if role == "administration":
        return list(ACTION_TOOL_NAMES)
    return []

def _load_sifa_context() -> str:
    """Charge le fichier SIFA_CONTEXT.md depuis la racine du projet."""
    import pathlib
    ctx_path = pathlib.Path(__file__).resolve().parents[2] / "SIFA_CONTEXT.md"
    try:
        return ctx_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def _role_access_note(role: str, scope: list[str]) -> str:
    scope_desc = ", ".join(scope) if scope else "aucun module"
    lines = [f"Tu ne peux accéder qu'aux données suivantes : {scope_desc}."]
    if role == "fabrication":
        lines.append(
            "Accès limité à vos propres saisies de production et à la machine qui vous est assignée."
        )
    elif role == "direction":
        lines.append(
            "Vous disposez d'une vue consolidée sur tous les modules listés ci-dessus."
        )
    return "\n".join(lines)


def build_system_prompt(user: dict, module_actif: str | None = None) -> str:
    now = datetime.now(PARIS)
    role = user.get("role", "")
    nom = user.get("nom", "Utilisateur")
    scope = get_user_scope(role)
    date_str = now.strftime("%A %d %B %Y, %H:%M")
    access_note = _role_access_note(role, scope)
    sifa_context = _load_sifa_context()

    return f"""Tu es l'assistant intégré de MySifa, l'outil de gestion de production de SIFA.
Tu réponds uniquement en français. Sois direct, factuel, concis.

{sifa_context}

---
Utilisateur connecté : {nom} — rôle : {role}
Date et heure : {date_str} (heure de Paris)
Module actif : {module_actif or "portail"}

{access_note}

Règles strictes :
- Respecte strictement le périmètre ci-dessus ; ne demande jamais d'accéder à d'autres données.
- Tu ne modifies rien sans confirmation explicite (sauf actions de lecture).
- Si une information manque, pose une question courte.
- Réponses courtes (3-6 lignes max sauf tableau/liste demandé explicitement).
- Ne jamais inventer de données. Si tu ne sais pas, dis-le clairement.
- Ton professionnel et direct — pas de formules commerciales.
"""

"""Helpers HTML pour l'encadré profil sidebar (rendu serveur)."""
from __future__ import annotations

import html as html_mod

_ROLE_LABELS = {
    "direction": "Direction",
    "administration": "Administration",
    "fabrication": "Fabrication",
    "logistique": "Logistique",
    "comptabilite": "Comptabilité",
    "expedition": "Expédition",
    "commercial": "Commercial",
    "superadmin": "Super admin",
}


def _esc(s: str) -> str:
    return html_mod.escape(str(s or ""), quote=True)


def user_chip_sidebar_html(
    *,
    nom: str,
    role_label: str,
    avatar_url: str = "",
    profil_link: bool = True,
    chip_class: str = "user-chip",
) -> str:
    """HTML interne du chip sidebar (photo + nom/service + lien profil)."""
    nom_e = _esc(nom)
    role_e = _esc(role_label)
    url = (avatar_url or "").strip()
    edit_svg = (
        '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>'
        '<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>'
        "</svg>"
    )
    profil = (
        f'<div class="uc-profil">{edit_svg} Mon profil</div>' if profil_link else ""
    )
    if url:
        body = (
            f'<div class="uc-top">'
            f'<img class="uc-avatar" src="{_esc(url)}" alt="">'
            f'<div class="uc-info">'
            f'<div class="uc-name">{nom_e}</div>'
            f'<div class="uc-role">{role_e}</div>'
            f"</div></div>{profil}"
        )
    else:
        body = (
            f'<div class="uc-name">{nom_e}</div>'
            f'<div class="uc-role">{role_e}</div>{profil}"
        )
    return f'<div class="{chip_class}">{body}</div>'


def role_label_for_user(user: dict) -> str:
    role = user.get("role") or ""
    return _ROLE_LABELS.get(role, role)

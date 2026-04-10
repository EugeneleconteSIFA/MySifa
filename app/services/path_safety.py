"""Contrôle des chemins fichiers (évite traversée de répertoires hors zone autorisée)."""
from __future__ import annotations

import os


def path_is_under_directory(candidate: str, allowed_root: str) -> bool:
    """True si ``candidate`` est résolu sous ``allowed_root`` (même répertoire autorisé)."""
    if not candidate or not allowed_root:
        return False
    try:
        cand = os.path.realpath(candidate)
        root = os.path.realpath(allowed_root)
        if cand == root:
            return True
        if not root.endswith(os.sep):
            root = root + os.sep
        return cand.startswith(root)
    except (OSError, ValueError):
        return False


def safe_upload_dest(allowed_root: str, filename: str, prefix: str) -> str:
    """Construit un chemin sous ``allowed_root`` : base du nom de fichier uniquement + préfixe."""
    base = os.path.basename(filename or "unknown").replace("\x00", "").strip() or "unknown"
    return os.path.normpath(os.path.join(allowed_root, f"{prefix}_{base}"))

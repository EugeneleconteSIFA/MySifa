"""Compatibility shim.

Ce module reste à la racine pour ne pas casser les imports existants.
L'implémentation réelle est dans `app/core/database.py`.
"""

from app.core.database import *  # noqa: F401,F403

"""Compatibility shim.

Ce module reste à l'ancien emplacement pour ne pas casser les imports existants.
L'implémentation réelle est dans `app/routers/auth.py`.
"""

from app.routers.auth import *  # noqa: F401,F403


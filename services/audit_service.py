"""Compatibility shim.

Ce module reste à l'ancien emplacement pour ne pas casser les imports existants.
L'implémentation réelle est dans `app/services/audit_service.py`.
"""

from app.services.audit_service import *  # noqa: F401,F403

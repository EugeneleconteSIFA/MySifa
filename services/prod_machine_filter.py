"""Compatibility shim.

Ce module reste à l'ancien emplacement pour ne pas casser les imports existants.
L'implémentation réelle est dans `app/services/prod_machine_filter.py`.
"""

from app.services.prod_machine_filter import *  # noqa: F401,F403

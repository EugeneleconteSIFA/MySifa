"""Compatibility shim.

L'implémentation réelle est dans `app/routers/stock.py`.
(Ne pas redéclarer `router` ici : cela supprimait des routes comme `/api/stock/fournisseurs`.)
"""

from app.routers.stock import *  # noqa: F401,F403

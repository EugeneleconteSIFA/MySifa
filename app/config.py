"""Compat shim — ne pas utiliser directement.

Historique: `app/config.py` est une ancienne copie incomplète. Certains environnements
peuvent toutefois résoudre `import config` vers ce fichier selon le `sys.path`,
ce qui casse l'app (ex: `ROLES_PRICING` manquant).

Ce module relaie donc *toutes* les constantes depuis le `config.py` racine.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_root_config():
    root_path = Path(__file__).resolve().parent.parent / "config.py"
    spec = importlib.util.spec_from_file_location("_mysifa_root_config", str(root_path))
    if spec is None or spec.loader is None:
        raise RuntimeError("Impossible de charger le config.py racine")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_root = _load_root_config()

# Exporter toutes les variables "publiques" (sauf dunders) dans ce module.
for _k, _v in vars(_root).items():
    if _k.startswith("__"):
        continue
    globals()[_k] = _v


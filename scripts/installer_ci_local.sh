#!/usr/bin/env bash
#
# MySifa — installe l'environnement Python complet de la CI locale.
#
# Pourquoi. Le Python du poste n'a ni FastAPI ni reportlab (ou un pydantic trop
# ancien) : scripts/ci_local.sh ignorait alors une bonne partie des tests, et
# les rouges ne se voyaient qu'une fois poussés sur staging (22/10/2026). Cet
# environnement reprend requirements.txt, comme la CI GitHub ; ci_local.sh le
# prend en priorité dès qu'il existe.
#
# Il vit dans .venv-ci/ à la racine du dépôt (ignoré par git). À relancer
# après une modification de requirements.txt.
#
#     scripts/installer_ci_local.sh

set -e
cd "$(dirname "$0")/.."

PY=""
for c in python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; sys.exit(sys.version_info < (3, 10))" 2>/dev/null; then
        PY="$c"; break
    fi
done
if [ -z "$PY" ]; then
    echo "Python 3.10 ou plus récent introuvable."
    exit 1
fi

echo "→ Environnement .venv-ci avec $($PY --version)"
"$PY" -m venv .venv-ci
.venv-ci/bin/python -m pip install -q --upgrade pip
# cryptography se compile sinon depuis ses sources, ce qui demande Rust : le
# paquet précompilé suffit.
.venv-ci/bin/python -m pip install -q --only-binary=cryptography -r requirements.txt
.venv-ci/bin/python -c "import fastapi, reportlab; print('→ Prêt : FastAPI', fastapi.__version__)"

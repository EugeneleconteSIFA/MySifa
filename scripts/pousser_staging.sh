#!/usr/bin/env bash
#
# MySifa — envoie la branche feature courante vers staging, tests compris.
#
#     scripts/pousser_staging.sh 'message_du_commit'
#
# 1. Commit de ce qui est en cours sur la branche feature, push de la branche.
# 2. Fusion avec staging SANS changer de branche (git merge-tree) : ni l'index
#    ni le dossier de travail ne bougent, donc plus de « fatal: stash failed »
#    quand un éditeur lit le dépôt au même moment (21/10/2026).
# 3. La CI locale (scripts/ci_local.sh) tourne sur le résultat EXACT de la
#    fusion, dans un dossier temporaire : c'est ce commit-là que staging
#    recevra, avec les changements des autres. Avant, le push partait en
#    --no-verify et les rouges ne se voyaient que dans l'onglet Actions.
# 4. Vert : push vers staging. Rouge : rien n'est poussé sur staging, la
#    branche feature reste en place, la sortie dit quel test casse.
#
# Un vrai conflit avec staging arrête tout à l'étape 2.
# Exception, en connaissance de cause : MYSIFA_SANS_TESTS=1 saute l'étape 3.
# Essai à blanc : MYSIFA_ESSAI=1 fusionne et teste sans commit ni push.

set -u
msg=${1:-}
if [ -z "$msg" ]; then echo "Usage : scripts/pousser_staging.sh 'message'"; exit 1; fi

racine=$(git rev-parse --show-toplevel) || exit 1
cd "$racine"
branche=$(git branch --show-current)
echo "→ Dépôt : $(basename "$racine")"
echo "→ Branche : $branche"
case "$branche" in
    feature/*|feat/*) ;;
    *) echo "Pas sur une branche feature (actuellement : $branche). Bascule dessus avant."; exit 1 ;;
esac

echo "→ Changements :"
git status --short
essai=${MYSIFA_ESSAI:-}
if [ -z "$essai" ]; then
    if [ -n "$(git status --porcelain)" ]; then
        git add . && git commit -q -m "$msg" || exit 1
    fi
    git push -q --no-verify -u origin "$branche" || exit 1
fi

echo "→ Fusion avec staging (sans changer de branche)"
git fetch -q origin staging || exit 1
if ! tree=$(git merge-tree --write-tree origin/staging "$branche"); then
    echo "Conflit avec staging — rien n'est poussé. Fichiers :"
    printf '%s\n' "$tree" | sed -n '2,20p'
    exit 1
fi
fusion=$(git commit-tree "$tree" -p origin/staging -p "$branche" -m "$msg") || exit 1

if [ "${MYSIFA_SANS_TESTS:-}" != "1" ]; then
    dossier=$(mktemp -d "${TMPDIR:-/tmp}/mysifa-ci.XXXXXX")
    git worktree add -q --detach "$dossier" "$fusion" || exit 1
    echo "→ CI locale sur le résultat de la fusion (quelques minutes)"
    # L'environnement complet vit dans le dépôt, pas dans le dossier temporaire.
    py=""
    [ -x "$racine/.venv-ci/bin/python" ] && py="$racine/.venv-ci/bin/python"
    [ -z "$py" ] && echo "  (pas de .venv-ci : lancer scripts/installer_ci_local.sh pour jouer tous les tests)"
    PY_CMD="$py" bash "$dossier/scripts/ci_local.sh"
    code=$?
    git worktree remove --force "$dossier" >/dev/null 2>&1 || true
    if [ $code -ne 0 ]; then
        echo
        echo "CI locale rouge — staging n'a pas été modifié."
        [ -z "$essai" ] && echo "La branche $branche est poussée : corriger, puis relancer ce script."
        exit 1
    fi
fi

if [ -n "$essai" ]; then echo "→ Essai : CI locale verte, rien n'a été poussé."; exit 0; fi
git push -q --no-verify origin "$fusion":refs/heads/staging || exit 1
echo "→ staging sur GitHub : $(git ls-remote origin refs/heads/staging | cut -c1-8)"
echo "→ Sur : $(git branch --show-current)"

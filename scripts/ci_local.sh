#!/usr/bin/env bash
#
# Rejoue EXACTEMENT les etapes de .github/workflows/ci.yml, en local.
#
# Pourquoi ce script existe. Le 27/08/2026, la CI a ete livree "verte" alors que
# seuls les TESTS avaient ete verifies — pas les etapes de syntaxe du workflow
# lui-meme. Premier push : rouge, sur un fichier JS mort et casse
# (app/tmp_planning.js) que personne n'avait ouvert depuis des mois.
#
# La lecon n'est pas "mieux relire" : c'est qu'un workflow qu'on ne peut pas
# rejouer en local se verifie en production, une fois sur deux, en public.
#
# Usage : scripts/ci_local.sh
# Code de sortie : 0 si tout passe, 1 sinon.

set -uo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=.

echec=0
titre() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

titre "Syntaxe Python"
if python3 -m compileall -q app config.py main.py database.py tests scripts tools; then
    echo "  ok"
else
    echo "  KO"; echec=1
fi

titre "Syntaxe JavaScript"
n=0
while IFS= read -r f; do
    node --check "$f" >/dev/null 2>&1 || { echo "  KO  $f"; n=$((n+1)); }
done < <(find static app -name '*.js' -not -path '*/node_modules/*' -not -name '*.min.js')
if [[ $n -eq 0 ]]; then echo "  ok  ($(find static app -name '*.js' -not -path '*/node_modules/*' -not -name '*.min.js' | wc -l | tr -d ' ') fichiers)"; else echec=1; fi

titre "Marqueurs de conflit"
if git --no-optional-locks grep -nE '^(<<<<<<<|>>>>>>>|\|\|\|\|\|\|\|)' -- '*.py' '*.js' '*.css' >/dev/null 2>&1; then
    git --no-optional-locks grep -nE '^(<<<<<<<|>>>>>>>|\|\|\|\|\|\|\|)' -- '*.py' '*.js' '*.css'
    echo "  KO"; echec=1
else
    echo "  ok"
fi

titre "Tests"
# En local, FastAPI n'est pas toujours installe dans le python courant. Un test
# qui ne peut pas importer ses dependances n'est pas un test rouge : le signaler
# comme tel ferait ignorer les vrais echecs.
if python3 -c "import fastapi" 2>/dev/null; then DEPS=1; else DEPS=0
    echo "  (FastAPI absent de ce python : les tests qui en dependent sont ignores)"
fi
QUARANTAINE=$(grep -oE '^test_[a-z0-9_]+\.py' tests/CI_QUARANTAINE.txt 2>/dev/null || true)
if [ -n "$QUARANTAINE" ]; then
    echo "  en quarantaine (tests/CI_QUARANTAINE.txt) :"
    echo "$QUARANTAINE" | sed 's/^/    - /'
fi
for t in tests/test_*.py; do
    nom=$(basename "$t")
    if echo "$QUARANTAINE" | grep -qx "$nom"; then continue; fi
    printf '  %-42s ' "$nom"
    # `</dev/null` : sans lui, un test qui lit stdin attend au clavier et bloque
    # indefiniment en local. Sur GitHub Actions il n'y a pas de TTY, donc le
    # symptome n'apparait qu'ici — c'est exactement le genre d'ecart qui fait
    # qu'on ne relance jamais la CI en local.
    # Pas de $( ) ici : la substitution de commande attend la fermeture du tube,
    # donc un test qui laisse un processus enfant derriere lui bloque la boucle
    # meme apres que `timeout` a tue le parent. Constate sur
    # test_mystock_declinaisons le 27/08/2026 : plus de deux minutes sans rendre
    # la main, timeout compris. Un fichier temporaire n'a pas ce probleme.
    timeout -k 5 120 python3 "$t" </dev/null >/tmp/mysifa_ci_test.log 2>&1
    code=$?
    sortie=$(cat /tmp/mysifa_ci_test.log 2>/dev/null)
    if [[ $code -eq 0 ]]; then
        echo "ok"
    elif [[ $DEPS -eq 0 && "$sortie" == *"No module named"* ]]; then
        echo "ignore (dependance absente)"
    else
        echo "KO"; echec=1
    fi
done

printf '\n'
if [[ $echec -ne 0 ]]; then echo "CI LOCALE : ECHEC"; exit 1; fi
echo "CI LOCALE : TOUT EST VERT"

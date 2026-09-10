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
# Chemin absolu du script AVANT le cd : les travailleurs le rappellent.
SELF="$(cd "$(dirname "$0")" && pwd)/$(basename "$0")"
cd "$(dirname "$0")/.."
export PYTHONPATH=.

# Parallelisme. En serie, la suite prenait plus de deux minutes a chaque push
# sur staging (10/09/2026 : « c'est un peu trop long ») — le genre de delai qui
# fait sortir `--no-verify`. Les tests sont independants (base :memory: ou
# fichier temporaire propre a chacun) : on les lance par paquets, et on affiche
# les resultats dans l'ordre alphabetique, comme avant.
# `getconf` existe sur macOS et Linux ; `nproc` seulement sur Linux.
JOBS=${CI_JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}
[ "$JOBS" -gt 8 ] 2>/dev/null && JOBS=8
[ "$JOBS" -lt 1 ] 2>/dev/null && JOBS=1

# `timeout` est un outil GNU : il n'existe pas sur macOS (sauf coreutils via
# Homebrew, sous le nom `gtimeout`). Sans ce repli, chaque test sortait en 127
# « command not found » et TOUS s'affichaient KO sur le Mac (10/09/2026), ce qui
# ressemble a une catastrophe et n'est qu'un outil absent. perl est livre avec
# macOS : `alarm` survit a `exec` et tue le test au bout du delai.
avec_delai() {
    delai=$1; shift
    if command -v timeout >/dev/null 2>&1; then
        timeout -k 5 "$delai" "$@"
    elif command -v gtimeout >/dev/null 2>&1; then
        gtimeout -k 5 "$delai" "$@"
    else
        perl -e 'alarm shift @ARGV; exec @ARGV or exit 127' "$delai" "$@"
    fi
}

# Travailleur : `ci_local.sh --un <test> <dossier>` joue UN test et depose sa
# sortie et son code dans le dossier. Appele par xargs -P plus bas.
# `</dev/null` : sans lui, un test qui lit stdin attend au clavier et bloque
# indefiniment en local. Pas de $( ) autour du test : la substitution attend la
# fermeture du tube, et un test qui laisse un enfant derriere lui bloquait la
# boucle meme apres le timeout (test_mystock_declinaisons, 27/08/2026).
if [ "${1:-}" = "--un" ]; then
    t=$2; dossier=$3; nom=$(basename "$t")
    avec_delai 120 python3 "$t" </dev/null >"$dossier/$nom.log" 2>&1
    echo $? >"$dossier/$nom.code"
    exit 0
fi
if [ "${1:-}" = "--js" ]; then
    node --check "$2" >/dev/null 2>&1 || echo "  KO  $2"
    exit 0
fi

echec=0
titre() { printf '\n\033[1m== %s\033[0m\n' "$1"; }

titre "Syntaxe Python"
if python3 -m compileall -q -j 0 app config.py main.py database.py tests scripts tools; then
    echo "  ok"
else
    echo "  KO"; echec=1
fi

titre "Syntaxe JavaScript"
js_ko=$(find static app -name '*.js' -not -path '*/node_modules/*' -not -name '*.min.js' -print0 \
    | xargs -0 -n 1 -P "$JOBS" bash "$SELF" --js)
n=$(printf '%s' "$js_ko" | grep -c 'KO' || true)
[ -n "$js_ko" ] && printf '%s\n' "$js_ko"
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
# Un dossier temporaire propre a ce lancement : un chemin fixe dans /tmp
# appartient au premier utilisateur qui l'a cree, et les lancements suivants
# sous un autre compte echouaient en "Permission denied" sur TOUS les tests.
DOSSIER=$(mktemp -d "${TMPDIR:-/tmp}/mysifa_ci.XXXXXX")
trap 'rm -rf "$DOSSIER"' EXIT
debut=$(date +%s)
for t in tests/test_*.py; do
    nom=$(basename "$t")
    if echo "$QUARANTAINE" | grep -qx "$nom"; then continue; fi
    printf '%s\n' "$t"
done | xargs -I{} -P "$JOBS" bash "$SELF" --un {} "$DOSSIER" 2>/dev/null || true

for t in tests/test_*.py; do
    nom=$(basename "$t")
    if echo "$QUARANTAINE" | grep -qx "$nom"; then continue; fi
    printf '  %-42s ' "$nom"
    code=$(cat "$DOSSIER/$nom.code" 2>/dev/null || echo 127)
    sortie=$(cat "$DOSSIER/$nom.log" 2>/dev/null)
    if [[ $code -eq 0 ]]; then
        echo "ok"
    elif [[ $DEPS -eq 0 && "$sortie" == *"No module named"* ]]; then
        echo "ignore (dependance absente)"
    else
        echo "KO"; echec=1
        # Les dernieres lignes du test : sans elles, un KO local oblige a
        # relancer le test a la main juste pour savoir de quoi il s'agit.
        tail -n 4 "$DOSSIER/$nom.log" 2>/dev/null | sed 's/^/      | /'
    fi
done
echo "  ($(( $(date +%s) - debut )) s, $JOBS en parallele)"

printf '\n'
if [[ $echec -ne 0 ]]; then echo "CI LOCALE : ECHEC"; exit 1; fi
echo "CI LOCALE : TOUT EST VERT"

#!/usr/bin/env bash
#
# Test de fumee : les pages cles repondent-elles ?
#
# Pourquoi ce script existe. `/healthz` verifie que la base repond — c'est
# necessaire, et tres insuffisant. Une erreur d'import dans un router, une
# fonction de rendu qui leve, un middleware casse : l'application demarre,
# `/healthz` dit "ok", et chaque page renvoie un 500. Le rollback automatique
# ne se declenche pas, parce que rien ne lui dit que quelque chose ne va pas.
#
# Ce script comble ce trou. Il ne demande pas d'etre authentifie : une page
# protegee qui redirige vers le login (302) ou refuse (401/403) est une page
# qui FONCTIONNE. Ce qu'on refuse, c'est le 5xx et l'absence de reponse.
#
# Usage :
#     scripts/fumee.sh [base_url]        # defaut : http://localhost:8000
#
# Code de sortie : 0 si tout repond, 1 sinon (avec le detail sur stderr).

set -uo pipefail

BASE="${1:-http://localhost:8000}"
DELAI="${FUMEE_TIMEOUT:-8}"

# Les routes qui, si elles tombent, rendent l'outil inutilisable. Une par
# module : on cherche l'erreur d'import ou de rendu, pas la couverture.
ROUTES=(
  "/healthz"
  "/"
  "/prod"
  "/planning"
  "/stock"
  "/expe"
  "/fabrication"
  "/qualite"
  "/maintenance"
  "/settings"
  "/taches"
  "/calendrier"
)

echec=0
echo "Test de fumee sur ${BASE}"

for route in "${ROUTES[@]}"; do
    code=$(curl -s -o /dev/null -w '%{http_code}' \
                --max-time "$DELAI" "${BASE}${route}" 2>/dev/null)

    case "$code" in
        2??|3??|401|403|404)
            printf '  ok   %-16s %s\n' "$route" "$code"
            ;;
        000)
            printf '  KO   %-16s pas de reponse (timeout %ss)\n' "$route" "$DELAI" >&2
            echec=1
            ;;
        *)
            printf '  KO   %-16s %s\n' "$route" "$code" >&2
            echec=1
            ;;
    esac
done

# `/healthz` doit en plus dire explicitement que la base repond.
corps=$(curl -sf --max-time "$DELAI" "${BASE}/healthz" 2>/dev/null || true)
if [[ "$corps" != *'"status":"ok"'* ]]; then
    echo "  KO   /healthz ne confirme pas la base : ${corps:-aucune reponse}" >&2
    echec=1
else
    printf '  ok   %-16s la base repond\n' "/healthz"
fi

if [[ "$echec" -ne 0 ]]; then
    echo "Test de fumee ECHOUE." >&2
    exit 1
fi
echo "Test de fumee : toutes les routes repondent."
exit 0

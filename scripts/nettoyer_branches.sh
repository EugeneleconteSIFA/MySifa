#!/usr/bin/env bash
#
# Ménage des branches du dépôt MySifa.
#
# Supprime les branches distantes déjà fusionnées dans `staging` et sans
# activité depuis un certain nombre de jours. C'est la contrepartie au terminal
# de la vue « Santé du dépôt » (Paramètres → Promouvoir), qui les signale mais
# ne touche jamais au dépôt.
#
# Par défaut le script NE SUPPRIME RIEN : il liste ce qu'il ferait.
# Il faut `--appliquer` pour que la suppression parte.
#
#   ./scripts/nettoyer_branches.sh                  # simulation (défaut)
#   ./scripts/nettoyer_branches.sh --appliquer      # supprime, avec confirmation
#   ./scripts/nettoyer_branches.sh --jours 30       # seuil de dormance
#   ./scripts/nettoyer_branches.sh --local          # nettoie aussi les branches locales
#   ./scripts/nettoyer_branches.sh --sans-fetch     # travaille sur les refs déjà en cache
#   ./scripts/nettoyer_branches.sh --appliquer --force   # sans confirmation (cron)
#
# Sécurités :
#   - `main`, `staging` et la branche courante ne sont jamais touchées ;
#   - une branche NON fusionnée dans staging n'est jamais proposée, quel que
#     soit son âge — elle est seulement signalée en fin de rapport ;
#   - avant toute suppression, le SHA de chaque branche est écrit dans un
#     journal sous `.git/` : une branche supprimée par erreur se restaure avec
#     `git push origin <sha>:refs/heads/<nom>`.

set -euo pipefail

REMOTE="origin"
BASE="origin/staging"
JOURS=14
APPLIQUER=0
FORCE=0
LOCAL=0
FETCH=1
PROTEGEES="main staging"

while [ $# -gt 0 ]; do
  case "$1" in
    --appliquer) APPLIQUER=1 ;;
    --force)     FORCE=1 ;;
    --local)     LOCAL=1 ;;
    --sans-fetch) FETCH=0 ;;
    --jours)     JOURS="${2:-14}"; shift ;;
    --base)      BASE="${2:-origin/staging}"; shift ;;
    -h|--help)   sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Option inconnue : $1 (voir --help)" >&2; exit 2 ;;
  esac
  shift
done

cd "$(git rev-parse --show-toplevel)"

COURANTE="$(git rev-parse --abbrev-ref HEAD)"
MAINTENANT="$(date +%s)"
HORODATAGE="$(date +%Y-%m-%d_%H%M%S)"
JOURNAL=".git/nettoyage-branches-${HORODATAGE}.txt"
# Le journal s'accumule en mémoire : une simulation ne doit laisser aucune
# trace sur le disque, pas même un fichier temporaire à nettoyer après coup.
JOURNAL_LIGNES=""

est_protegee() {
  local nom="$1"
  [ "$nom" = "$COURANTE" ] && return 0
  for p in $PROTEGEES; do [ "$nom" = "$p" ] && return 0; done
  return 1
}

echo "Ménage des branches — dépôt $(basename "$PWD")"
echo "  base de comparaison : $BASE"
echo "  seuil de dormance   : $JOURS jour(s)"
echo "  branche courante    : $COURANTE (protégée)"
echo

if [ "$FETCH" -eq 1 ]; then
  echo "→ Rafraîchissement des références distantes…"
  git fetch "$REMOTE" --prune --quiet
  echo
fi

# ── Branches distantes fusionnées et dormantes ────────────────────────────────
A_SUPPRIMER=""
NB=0
printf '%-48s %-12s %-6s %s\n' "BRANCHE" "DERNIER" "ÂGE" "SHA"
printf '%-48s %-12s %-6s %s\n' "------------------------------------------------" "------------" "------" "-------"

while IFS='|' read -r ref date_courte date_unix sha; do
  [ -z "${ref:-}" ] && continue
  case "$ref" in *"/HEAD"|"$REMOTE") continue ;; esac
  nom="${ref#"$REMOTE"/}"
  [ -z "$nom" ] && continue
  est_protegee "$nom" && continue
  age=$(( (MAINTENANT - date_unix) / 86400 ))
  [ "$age" -lt "$JOURS" ] && continue
  printf '%-48s %-12s %4s j  %s\n' "$nom" "$date_courte" "$age" "${sha:0:8}"
  A_SUPPRIMER="$A_SUPPRIMER $nom"
  NB=$((NB + 1))
  JOURNAL_LIGNES="${JOURNAL_LIGNES}${nom}\t${sha}\t${date_courte}\n"
done <<EOF
$(git branch -r --merged "$BASE" \
    --format='%(refname:short)|%(committerdate:short)|%(committerdate:unix)|%(objectname)')
EOF

echo
if [ "$NB" -eq 0 ]; then
  echo "Rien à supprimer : aucune branche fusionnée dans $BASE et dormante depuis $JOURS jour(s)."
else
  echo "$NB branche(s) distante(s) fusionnée(s) dans $BASE et dormante(s)."
fi

# ── Branches non fusionnées et anciennes : signalées, jamais supprimées ───────
echo
echo "→ Branches NON fusionnées dans $BASE et sans activité depuis $JOURS jour(s) :"
ORPHELINES=0
while IFS='|' read -r ref date_courte date_unix; do
  [ -z "${ref:-}" ] && continue
  case "$ref" in *"/HEAD"|"$REMOTE") continue ;; esac
  nom="${ref#"$REMOTE"/}"
  est_protegee "$nom" && continue
  age=$(( (MAINTENANT - date_unix) / 86400 ))
  [ "$age" -lt "$JOURS" ] && continue
  printf '   %-45s %s (%s j)\n' "$nom" "$date_courte" "$age"
  ORPHELINES=$((ORPHELINES + 1))
done <<EOF
$(git branch -r --no-merged "$BASE" \
    --format='%(refname:short)|%(committerdate:short)|%(committerdate:unix)')
EOF
[ "$ORPHELINES" -eq 0 ] && echo "   (aucune)"
echo "   Ces branches portent du travail jamais fusionné : à relire avant de décider."

# ── Passage à l'acte ──────────────────────────────────────────────────────────
echo
if [ "$NB" -eq 0 ]; then
  exit 0
fi

if [ "$APPLIQUER" -eq 0 ]; then
  echo "SIMULATION — rien n'a été supprimé."
  echo "Relance avec --appliquer pour supprimer ces $NB branche(s)."
  exit 0
fi

if [ "$FORCE" -eq 0 ]; then
  printf 'Supprimer ces %s branche(s) sur %s ? [oui/non] ' "$NB" "$REMOTE"
  read -r reponse
  case "$reponse" in
    oui|OUI|o|O|y|yes) ;;
    *) echo "Annulé."; exit 0 ;;
  esac
fi

{
  echo "# Branches supprimées le $(date '+%Y-%m-%d %H:%M:%S')"
  echo "# Restauration : git push $REMOTE <sha>:refs/heads/<nom>"
  echo "# nom<TAB>sha<TAB>date du dernier commit"
  printf '%b' "$JOURNAL_LIGNES"
} > "$JOURNAL"
echo "Journal de restauration écrit dans $JOURNAL"
echo

# Par paquets de 20 : une ligne de commande de 50 branches finit par gêner
# certains serveurs, et un paquet qui échoue n'emporte pas les autres.
LOT=""
COMPTE=0
for b in $A_SUPPRIMER; do
  LOT="$LOT $b"
  COMPTE=$((COMPTE + 1))
  if [ "$COMPTE" -ge 20 ]; then
    # shellcheck disable=SC2086
    git push "$REMOTE" --delete $LOT
    LOT=""
    COMPTE=0
  fi
done
if [ -n "$LOT" ]; then
  # shellcheck disable=SC2086
  git push "$REMOTE" --delete $LOT
fi

[ "$FETCH" -eq 1 ] && git fetch "$REMOTE" --prune --quiet
echo
echo "$NB branche(s) distante(s) supprimée(s)."

# ── Branches locales ──────────────────────────────────────────────────────────
if [ "$LOCAL" -eq 1 ]; then
  echo
  echo "→ Branches locales fusionnées dans $BASE :"
  LOCALES=""
  while read -r nom; do
    [ -z "${nom:-}" ] && continue
    est_protegee "$nom" && continue
    echo "   $nom"
    LOCALES="$LOCALES $nom"
  done <<EOF
$(git branch --merged "$BASE" --format='%(refname:short)')
EOF
  if [ -n "$LOCALES" ]; then
    # -d et non -D : git refuse toute branche qui porterait du travail non
    # fusionné, même si la liste ci-dessus la croit propre.
    # shellcheck disable=SC2086
    git branch -d $LOCALES
  else
    echo "   (aucune)"
  fi
fi

echo
echo "Terminé. Rouvre Paramètres → Promouvoir → Santé du dépôt pour voir la note remonter."

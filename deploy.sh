#!/bin/bash
# Déploiement MySifa : push GitHub → pull VPS (+ options --db, --uploads, --widget)
#
# Dossiers (surcharge possible via variables d'environnement) :
#   MYSIFA_SOURCE  — dépôt git utilisé pour commit/push (défaut : auto-détection)
#   MYSIFA_WORKDIR — copie de travail à synchroniser vers SOURCE avant deploy
#                    (défaut : ce dossier Google Drive si différent du dépôt git)
#
# Exemples :
#   ./deploy.sh
#   MYSIFA_WORKDIR="$PWD" ./deploy.sh          # sync Google Drive → git puis deploy
#   MYSIFA_SOURCE=~/Documents/GitHub/MySifa ./deploy.sh
#   ./deploy.sh --db                           # transfert DB local → VPS (attention)
#   ./deploy.sh --uploads                      # sync data/uploads
#   ./deploy.sh --widget                       # upload DMG/EXE widget (scp)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# --- VPS ---
VPS_USER="${VPS_USER:-root}"
VPS_IP="${VPS_IP:-168.231.85.64}"
VPS_PATH="${VPS_PATH:-/home/sifa/production-saas}"

# --- Chemins locaux (relatifs à LOCAL_SOURCE après cd) ---
LOCAL_DB="data/production.db"
LOCAL_UPLOADS="data/uploads"
LOCAL_UPLOADS_TRACA="uploads"

# --- Chemins distants (structure VPS : code à la racine, DB dans app/data/) ---
REMOTE_DB="$VPS_PATH/app/data/production.db"
REMOTE_UPLOADS="$VPS_PATH/app/data/uploads"
REMOTE_UPLOADS_TRACA="$VPS_PATH/uploads"

# Dépôt git par défaut (historique)
MYSIFA_SOURCE_DEFAULT="${HOME}/Documents/GitHub/MySifa"
# Copie Google Drive / Forge (nouveau dossier de travail)
MYSIFA_WORKDIR_DEFAULT="${HOME}/Library/CloudStorage/GoogleDrive-eugeneleconte@outlook.com/My Drive/Forge/Forge Saas/MySifa"

_has_flag() {
  local flag="$1"
  shift
  for a in "$@"; do
    [[ "$a" == "$flag" ]] && return 0
  done
  return 1
}

_resolve_git_root() {
  local dir="$1"
  if git -C "$dir" rev-parse --show-toplevel &>/dev/null 2>&1; then
    git -C "$dir" rev-parse --show-toplevel
    return 0
  fi
  return 1
}

# Déterminer LOCAL_SOURCE (dépôt git)
if [[ -n "${MYSIFA_SOURCE:-}" ]]; then
  LOCAL_SOURCE="$(cd "$MYSIFA_SOURCE" && pwd)"
elif _resolve_git_root "$SCRIPT_DIR"; then
  LOCAL_SOURCE="$(_resolve_git_root "$SCRIPT_DIR")"
elif [[ -d "$MYSIFA_SOURCE_DEFAULT/.git" ]]; then
  LOCAL_SOURCE="$(cd "$MYSIFA_SOURCE_DEFAULT" && pwd)"
else
  echo ""
  echo "Erreur : aucun dépôt git MySifa trouvé."
  echo "  - Exécutez deploy.sh depuis le clone git, ou"
  echo "  - export MYSIFA_SOURCE=~/Documents/GitHub/MySifa"
  echo "  - ou initialisez git dans ce dossier."
  echo ""
  exit 1
fi

# Dossier de travail (optionnel) : sync vers LOCAL_SOURCE avant deploy
WORKDIR=""
if [[ -n "${MYSIFA_WORKDIR:-}" ]]; then
  WORKDIR="$(cd "$MYSIFA_WORKDIR" && pwd)"
elif [[ -d "$MYSIFA_WORKDIR_DEFAULT" ]]; then
  WORKDIR="$(cd "$MYSIFA_WORKDIR_DEFAULT" && pwd)"
fi

_sync_workdir_to_source() {
  local src="$1" dest="$2"
  if [[ "$src" == "$dest" ]]; then
    return 0
  fi
  if [[ ! -d "$src" ]]; then
    echo "Attention : dossier de travail introuvable ($src), sync ignorée."
    return 0
  fi
  echo ""
  echo "Sync copie de travail → dépôt git..."
  echo "  depuis : $src"
  echo "  vers   : $dest"
  rsync -a --delete \
    --exclude '.git/' \
    --exclude 'venv/' \
    --exclude '__pycache__/' \
    --exclude '.DS_Store' \
    --exclude 'myprod-widget/node_modules/' \
    --exclude 'myprod-widget/dist/' \
    --exclude 'data/production.db' \
    --exclude 'data/*.bak' \
    --exclude 'data/*.backup' \
    --exclude 'data/production.db.*' \
    --exclude 'mysifa.db' \
    --exclude 'production.db' \
    "$src/" "$dest/"
  echo "Sync terminée."
}

# Supprime node_modules / builds widget du dépôt git (jamais versionnés ; DMG/EXE conservés pour --widget)
_clean_widget_artifacts() {
  local root="${1:-.}"
  echo ""
  echo "Nettoyage artefacts widget (hors Git)..."
  rm -rf "$root/myprod-widget/node_modules"
  local dist="$root/myprod-widget/dist"
  if [[ -d "$dist" ]]; then
    shopt -s nullglob
    for item in "$dist"/*; do
      [[ -e "$item" ]] || continue
      case "${item##*/}" in
        *.dmg|*.exe) ;;
        *) rm -rf "$item" ;;
      esac
    done
    shopt -u nullglob 2>/dev/null || true
  fi
}

echo "Déploiement MySifa"
echo "  dépôt git : $LOCAL_SOURCE"
if [[ -n "$WORKDIR" && "$WORKDIR" != "$LOCAL_SOURCE" ]]; then
  echo "  copie travail : $WORKDIR"
fi

if [[ -n "$WORKDIR" && "$WORKDIR" != "$LOCAL_SOURCE" ]]; then
  _sync_workdir_to_source "$WORKDIR" "$LOCAL_SOURCE"
fi

cd "$LOCAL_SOURCE"
echo "  répertoire courant : $(pwd)"

_clean_widget_artifacts "$LOCAL_SOURCE"

# 0. Sécurité : refuser seulement si des artefacts widget sont déjà indexés (git add)
if command -v rg &>/dev/null; then
  if git diff --cached --name-only 2>/dev/null | rg -q '^myprod-widget/(node_modules|dist)/'; then
    echo ""
    echo "Refus du déploiement : artefacts myprod-widget indexés dans Git."
    git diff --cached --name-only | rg '^myprod-widget/' || true
    exit 1
  fi
fi

# 1. Push du code vers GitHub
echo ""
echo "Push du code..."
git add .
git commit -m "deploy $(date '+%Y-%m-%d %H:%M')" || true
git push origin main

# 2. Sur le VPS : pull + redémarrage
echo ""
echo "Mise à jour VPS..."
if ! ssh -o BatchMode=no -o ConnectTimeout=15 "$VPS_USER@$VPS_IP" "
  set -e
  cd $VPS_PATH
  git fetch --all
  git reset --hard origin/main
  chown -R sifa:sifa $VPS_PATH
  systemctl restart mysifa
  systemctl status mysifa --no-pager -l
"; then
  echo ""
  echo "Échec SSH / mise à jour VPS — le code GitHub est à jour, le serveur ne l'est pas."
  echo "Relancer manuellement :"
  echo "  ssh $VPS_USER@$VPS_IP"
  echo "  cd $VPS_PATH && git fetch --all && git reset --hard origin/main && chown -R sifa:sifa . && systemctl restart mysifa"
  echo "Installateurs widget : ./deploy.sh --widget"
  exit 1
fi

# 2b. Upload optionnel des installateurs natifs widget (DMG/EXE) sans Git
if _has_flag "--widget" "$@"; then
  echo ""
  echo "Upload des installateurs widget (DMG/EXE)..."
  if ls myprod-widget/dist/*.dmg >/dev/null 2>&1; then
    LATEST_DMG=$(ls -t myprod-widget/dist/*.dmg | head -n 1)
    echo "DMG: $LATEST_DMG"
    ssh "$VPS_USER@$VPS_IP" "mkdir -p $VPS_PATH/myprod-widget/dist"
    scp "$LATEST_DMG" "$VPS_USER@$VPS_IP:$VPS_PATH/myprod-widget/dist/"
    echo "DMG uploadé."
  else
    echo "Aucun DMG dans myprod-widget/dist/"
  fi
  if ls myprod-widget/dist/*.exe >/dev/null 2>&1; then
    LATEST_EXE=$(ls -t myprod-widget/dist/*.exe | head -n 1)
    echo "EXE: $LATEST_EXE"
    ssh "$VPS_USER@$VPS_IP" "mkdir -p $VPS_PATH/myprod-widget/dist"
    scp "$LATEST_EXE" "$VPS_USER@$VPS_IP:$VPS_PATH/myprod-widget/dist/"
    echo "EXE uploadé."
  fi
fi

# 3. Transfert DB (seulement si --db)
if _has_flag "--db" "$@"; then
  if [[ ! -f "$LOCAL_DB" ]]; then
    echo "Erreur : $LOCAL_DB introuvable dans $LOCAL_SOURCE"
    exit 1
  fi
  echo ""
  echo "Transfert de la base de données..."
  echo "  local  : $LOCAL_SOURCE/$LOCAL_DB"
  echo "  distant: $REMOTE_DB"
  read -r -p "Confirmer l'écrasement de la DB VPS ? (oui/non) " confirm
  if [[ "$confirm" != "oui" ]]; then
    echo "Transfert DB annulé."
    exit 1
  fi
  scp "$LOCAL_DB" "$VPS_USER@$VPS_IP:$REMOTE_DB"
  echo "DB transférée."
  echo ""
  echo "Redémarrage du service (post-DB)..."
  ssh "$VPS_USER@$VPS_IP" "systemctl restart mysifa && systemctl status mysifa --no-pager -l"
fi

# 4. Transfert uploads (seulement si --uploads)
if _has_flag "--uploads" "$@"; then
  echo ""
  echo "Transfert des uploads (imports CSV/XLSX)..."
  if [[ -d "$LOCAL_UPLOADS" ]]; then
    ssh "$VPS_USER@$VPS_IP" "mkdir -p $REMOTE_UPLOADS"
    rsync -az "$LOCAL_UPLOADS/" "$VPS_USER@$VPS_IP:$REMOTE_UPLOADS/"
    echo "data/uploads synchronisé."
  else
    echo "Attention : $LOCAL_UPLOADS absent, ignoré."
  fi
  if [[ -d "$LOCAL_UPLOADS_TRACA" ]]; then
    ssh "$VPS_USER@$VPS_IP" "mkdir -p $REMOTE_UPLOADS_TRACA/traca"
    rsync -az "$LOCAL_UPLOADS_TRACA/" "$VPS_USER@$VPS_IP:$REMOTE_UPLOADS_TRACA/"
    echo "uploads/ (tracabilité) synchronisé."
  fi
fi

echo ""
echo "Déploiement terminé."

#!/bin/bash

VPS_USER="root"
VPS_IP="168.231.85.64"   # ← à remplacer
VPS_PATH="/home/sifa/production-saas"
LOCAL_DB="data/production.db"
# IMPORTANT: le service systemd lance depuis $VPS_PATH et la config par défaut lit `data/production.db`.
# Donc on copie la DB au même endroit, sauf si ton .env VPS surcharge DB_PATH.
REMOTE_DB="$VPS_PATH/app/data/production.db"
LOCAL_UPLOADS="data/uploads"
REMOTE_UPLOADS="$VPS_PATH/data/uploads"

echo "🚀 Déploiement MySifa..."

# 1. Push du code vers GitHub
echo "\n📦 Push du code..."
git add -A
git commit -m "deploy $(date '+%Y-%m-%d %H:%M')" || true
git push origin main

# 2. Sur le VPS : pull + redémarrage
echo "\n🖥️  Mise à jour VPS..."
ssh $VPS_USER@$VPS_IP "
  cd $VPS_PATH &&
  git fetch --all &&
  git reset --hard origin/main &&
  chown -R sifa:sifa $VPS_PATH &&
  systemctl restart mysifa &&
  systemctl status mysifa --no-pager -l
"

# 3. Transfert DB (seulement si --db passé en argument)
if [[ "$1" == "--db" ]]; then
  echo "\n🗄️  Transfert de la base de données..."
  scp $LOCAL_DB $VPS_USER@$VPS_IP:$REMOTE_DB
  echo "✅ DB transférée."
  # Redémarrage après transfert pour que le service lise la nouvelle DB
  echo "\n🔄 Redémarrage du service (post-DB)..."
  ssh $VPS_USER@$VPS_IP "systemctl restart mysifa && systemctl status mysifa --no-pager -l"
fi

# 4. Transfert uploads (seulement si --uploads passé en argument)
if [[ "$1" == "--uploads" || "$2" == "--uploads" ]]; then
  echo "\n📎 Transfert des uploads (CSV/XLSX importés)..."
  rsync -az --delete "$LOCAL_UPLOADS/" "$VPS_USER@$VPS_IP:$REMOTE_UPLOADS/"
  echo "✅ Uploads transférés."
fi

echo "\n✅ Déploiement terminé."

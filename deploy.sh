#!/bin/bash

VPS_USER="sifa"
VPS_IP="168.231.85.64"   # ← à remplacer
VPS_PATH="/home/sifa/production-saas"
LOCAL_DB="data/production.db"
REMOTE_DB="$VPS_PATH/app/data/production.db"

echo "🚀 Déploiement MySifa..."

# 1. Push du code vers GitHub
echo "\n📦 Push du code..."
git add -A && git commit -m "deploy $(date '+%Y-%m-%d %H:%M')" && git push origin main

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
fi

echo "\n✅ Déploiement terminé."

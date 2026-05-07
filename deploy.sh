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

# 0. Sécurité : ne jamais commiter les artefacts Electron / node_modules
# NOTE: on tolère la présence locale de dist/*.dmg et dist/*.exe (upload via scp),
#       mais on refuse toute tentative de les commiter/pusher.
if git status --porcelain | rg -q '^(A |M |\\?\\?)\\s+myprod-widget/node_modules/'; then
  echo ""
  echo "⛔ Refus du déploiement : des artefacts myprod-widget sont présents (node_modules/dist)."
  echo "   Nettoyez-les (ou ignorez-les) avant de déployer."
  echo ""
  git status --porcelain | rg 'myprod-widget/(node_modules|dist)/' || true
  exit 1
fi

if git status --porcelain | rg -q '^(A |M |\\?\\?)\\s+myprod-widget/dist/'; then
  # Autoriser uniquement les DMG/EXE en dist, mais ils ne doivent pas être commités.
  if git status --porcelain | rg -q '^(A |M |\\?\\?)\\s+myprod-widget/dist/(?!.*\\.(dmg|exe)$)'; then
    echo ""
    echo "⛔ Refus du déploiement : fichiers inattendus dans myprod-widget/dist/."
    echo "   Gardez uniquement des .dmg / .exe dans dist/ (upload séparé), ou supprimez dist/."
    echo ""
    git status --porcelain | rg 'myprod-widget/dist/' || true
    exit 1
  fi
fi

# 1. Push du code vers GitHub
echo "\n📦 Push du code..."
# Ne pas faire git add -A (risque d'embarquer des artefacts locaux)
git add .
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

# 2b. Upload optionnel des installateurs natifs widget (DMG/EXE) sans Git
if [[ "$1" == "--widget" || "$2" == "--widget" || "$3" == "--widget" ]]; then
  echo "\n🧩 Upload des installateurs widget (DMG/EXE)..."
  # macOS DMG
  if ls myprod-widget/dist/*.dmg >/dev/null 2>&1; then
    LATEST_DMG=$(ls -t myprod-widget/dist/*.dmg | head -n 1)
    echo "→ DMG: $LATEST_DMG"
    ssh $VPS_USER@$VPS_IP "mkdir -p $VPS_PATH/myprod-widget/dist"
    scp "$LATEST_DMG" $VPS_USER@$VPS_IP:$VPS_PATH/myprod-widget/dist/
    echo "✅ DMG uploadé."
  else
    echo "→ Aucun DMG trouvé dans myprod-widget/dist/"
  fi
  # Windows EXE (si besoin plus tard)
  if ls myprod-widget/dist/*.exe >/dev/null 2>&1; then
    LATEST_EXE=$(ls -t myprod-widget/dist/*.exe | head -n 1)
    echo "→ EXE: $LATEST_EXE"
    ssh $VPS_USER@$VPS_IP "mkdir -p $VPS_PATH/myprod-widget/dist"
    scp "$LATEST_EXE" $VPS_USER@$VPS_IP:$VPS_PATH/myprod-widget/dist/
    echo "✅ EXE uploadé."
  fi
fi

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

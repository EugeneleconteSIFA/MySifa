#!/bin/bash
# promote_v2.sh — Promotion staging v1 → production v2
#
# Étapes :
#  1. Backup DB
#  2. Capture HEAD actuel (pour rollback)
#  3. git pull origin main
#  4. Bump version patch (APP_VERSION dans config.py)
#  5. Commit + push du bump
#  6. systemctl restart mysifa
#  7. Healthcheck /healthz (15s timeout) → ROLLBACK auto si KO
#  8. Annonce de release dans update_announcements (si NOTES fourni)
#
# Usage :
#  ./scripts/promote_v2.sh ["Notes de release en HTML"]
#
# À exécuter depuis /home/sifa/production-saas en tant que root (systemctl).
# Le bouton /settings appelle ce script via sudo.

set -euo pipefail

# ─── Config ──────────────────────────────────────────────────────────
V2_PATH="/home/sifa/production-saas"
DB_PATH="${V2_PATH}/app/data/production.db"
BACKUP_DIR="${V2_PATH}/data/backups"
HEALTHZ_URL="http://localhost:8000/healthz"
HEALTHZ_TIMEOUT=15
SERVICE_NAME="mysifa"
GIT_USER="promote-bot"
GIT_EMAIL="promote@sifa.local"

NOTES="${1:-}"

# ─── Helpers ─────────────────────────────────────────────────────────
log()  { printf "[%s] %s\n" "$(date '+%H:%M:%S')" "$*"; }
fail() { log "ERREUR: $*"; exit 1; }

cd "$V2_PATH" || fail "V2_PATH introuvable : $V2_PATH"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="${BACKUP_DIR}/promote_${TIMESTAMP}.db"

# ─── 1. Backup DB ────────────────────────────────────────────────────
log "1/8 Backup DB → ${BACKUP_FILE}"
cp "$DB_PATH" "$BACKUP_FILE"

# ─── 2. Capture HEAD pour rollback ───────────────────────────────────
log "2/8 Capture HEAD actuel"
PREV_HEAD=$(git rev-parse HEAD)
log "    HEAD avant promotion : ${PREV_HEAD:0:7}"

# ─── 3. git pull origin main ─────────────────────────────────────────
log "3/8 git fetch + reset --hard origin/main"
git fetch --all --quiet
git reset --hard origin/main --quiet
NEW_HEAD=$(git rev-parse HEAD)
log "    HEAD après pull : ${NEW_HEAD:0:7}"

if [[ "$PREV_HEAD" == "$NEW_HEAD" ]]; then
    log "Aucun changement à promouvoir (HEAD inchangé). Sortie."
    exit 0
fi

# ─── 4. Bump version patch dans config.py ────────────────────────────
log "4/8 Bump version (APP_VERSION dans config.py)"
CURRENT_VERSION=$(grep -E '^APP_VERSION\s*=' config.py | head -1 | sed -E 's/.*"([0-9]+\.[0-9]+\.[0-9]+)".*/\1/')
[[ -z "$CURRENT_VERSION" ]] && fail "APP_VERSION introuvable dans config.py"
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
NEW_PATCH=$((PATCH + 1))
NEW_VERSION="${MAJOR}.${MINOR}.${NEW_PATCH}"
sed -i -E "s/^APP_VERSION\s*=.*/APP_VERSION = \"${NEW_VERSION}\"/" config.py
log "    ${CURRENT_VERSION} → ${NEW_VERSION}"

# ─── 5. Commit + push du bump ────────────────────────────────────────
log "5/8 Commit + push du bump de version"
git add config.py
git -c "user.name=${GIT_USER}" -c "user.email=${GIT_EMAIL}" \
    commit -m "chore: bump v${CURRENT_VERSION} → v${NEW_VERSION}" --quiet
git push origin main --quiet || log "    ATTENTION : push échoué (le bump est local). Continuer."

# ─── 6. Restart v2 ───────────────────────────────────────────────────
log "6/8 Restart ${SERVICE_NAME}"
systemctl restart "$SERVICE_NAME"

# ─── 7. Healthcheck + rollback auto si KO ────────────────────────────
log "7/8 Healthcheck ${HEALTHZ_URL} (timeout ${HEALTHZ_TIMEOUT}s)"
HEALTHZ_OK=0
for i in $(seq 1 $HEALTHZ_TIMEOUT); do
    sleep 1
    if curl -sf "$HEALTHZ_URL" 2>/dev/null | grep -q '"status":"ok"'; then
        HEALTHZ_OK=1
        log "    OK après ${i}s"
        break
    fi
done

if [[ "$HEALTHZ_OK" != "1" ]]; then
    log "    KO après ${HEALTHZ_TIMEOUT}s — ROLLBACK AUTOMATIQUE"
    log "    Restore DB depuis ${BACKUP_FILE}"
    cp "$BACKUP_FILE" "$DB_PATH"
    log "    git reset --hard ${PREV_HEAD:0:7}"
    git reset --hard "$PREV_HEAD" --quiet
    # On force push pour annuler le commit de bump déjà poussé
    git push --force origin main --quiet || log "    ATTENTION : force-push échoué"
    log "    Restart ${SERVICE_NAME}"
    systemctl restart "$SERVICE_NAME"

    # Annonce d'échec
    sqlite3 "$DB_PATH" <<SQL_END
INSERT INTO update_announcements (scope, titre, message, created_at, created_by, active)
VALUES (
  'global',
  'Promotion annulée',
  '<div style="color:var(--danger)">Tentative de promotion v${CURRENT_VERSION} → v${NEW_VERSION} échouée (healthcheck KO). État précédent restauré automatiquement.</div>',
  datetime('now'),
  'promote-bot',
  1
);
SQL_END

    fail "Promotion annulée — état restauré à ${PREV_HEAD:0:7}"
fi

# ─── 8. Annonce de release (si notes fournies) ───────────────────────
if [[ -n "$NOTES" ]]; then
    log "8/8 Annonce de release v${NEW_VERSION}"
    # Construire le HTML de l'annonce selon le template MySifa
    MESSAGE_HTML=$(cat <<HTML_END
<div style="font-size:13px;line-height:1.7;color:var(--text2)">
  <div style="font-size:15px;font-weight:700;color:var(--text);margin-bottom:12px">Mise à jour — v${NEW_VERSION}</div>
  <div style="margin-bottom:10px;font-weight:600;color:var(--text);font-size:12px;text-transform:uppercase;letter-spacing:.5px">Notes</div>
  <div style="margin:0 0 14px 0">${NOTES}</div>
  <div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border);font-size:11px;color:var(--muted);line-height:1.6">
    Dans l'optique d'améliorer constamment l'outil, vos retours sont les bienvenus.<br>
    Merci de votre confiance.<br>
    <span style="color:var(--text2);font-weight:600">Eugène</span>
  </div>
</div>
HTML_END
)
    # Échapper les apostrophes pour SQL
    MESSAGE_ESCAPED="${MESSAGE_HTML//\'/\'\'}"
    sqlite3 "$DB_PATH" <<SQL_END
INSERT INTO update_announcements (scope, titre, message, created_at, created_by, active)
VALUES (
  'global',
  'Mise à jour — v${NEW_VERSION}',
  '${MESSAGE_ESCAPED}',
  datetime('now'),
  'promote-bot',
  1
);
SQL_END
else
    log "8/8 Pas de notes fournies — annonce ignorée"
fi

log ""
log "==> Promotion réussie : v${CURRENT_VERSION} → v${NEW_VERSION}"
exit 0

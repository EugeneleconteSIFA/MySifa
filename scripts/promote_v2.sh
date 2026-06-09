#!/bin/bash
# promote_v2.sh — Promotion staging v1 → production v2
#
# Étapes :
#  1. Backup DB
#  2. Capture HEAD actuel (pour rollback)
#  3. git pull origin main
#  4. chown sifa (pour que mysifa.service tourne avec les bonnes perms)
#  5. systemctl restart mysifa
#  6. Healthcheck /healthz (15s timeout) → ROLLBACK auto si KO
#  7. Annonce de release dans update_announcements (si NOTES fourni)
#
# Usage :
#  sudo ./scripts/promote_v2.sh ["Notes de release en HTML"]
#
# Le bouton /settings sur v1 appelle ce script via sudo.
# Sudoers : sifa peut exécuter ce script sans mot de passe.

set -uo pipefail

# ─── Config ──────────────────────────────────────────────────────────
V2_PATH="/home/sifa/production-saas"
DB_PATH="${V2_PATH}/app/data/production.db"
BACKUP_DIR="${V2_PATH}/data/backups"
HEALTHZ_URL="http://localhost:8000/healthz"
HEALTHZ_TIMEOUT=15
SERVICE_NAME="mysifa"
APP_USER="sifa"

NOTES="${1:-}"

# ─── Helpers ─────────────────────────────────────────────────────────
log()  { printf "[%s] %s\n" "$(date '+%H:%M:%S')" "$*"; }
fail() { log "ERREUR: $*"; exit 1; }

cd "$V2_PATH" || fail "V2_PATH introuvable : $V2_PATH"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="${BACKUP_DIR}/promote_${TIMESTAMP}.db"

# ─── 1. Backup DB ────────────────────────────────────────────────────
log "1/7 Backup DB"
if [[ ! -f "$DB_PATH" ]]; then
    fail "DB introuvable : $DB_PATH"
fi
cp "$DB_PATH" "$BACKUP_FILE" || fail "Backup DB échoué"
log "    OK : $(basename "$BACKUP_FILE")"

# ─── 2. Capture HEAD pour rollback ───────────────────────────────────
log "2/7 Capture HEAD v2 actuel"
PREV_HEAD=$(git rev-parse HEAD) || fail "git rev-parse HEAD KO"
log "    HEAD avant : ${PREV_HEAD:0:7}"

# ─── 3. git pull origin main ─────────────────────────────────────────
log "3/7 git fetch + reset --hard origin/main"
git fetch --all --quiet || fail "git fetch KO"
git reset --hard origin/main --quiet || fail "git reset KO"
NEW_HEAD=$(git rev-parse HEAD)
log "    HEAD après : ${NEW_HEAD:0:7}"

if [[ "$PREV_HEAD" == "$NEW_HEAD" ]]; then
    log "Aucun changement à promouvoir. Sortie."
    exit 0
fi

# Lire la version pour les logs (informative)
NEW_VERSION=$(grep -E '^APP_VERSION\s*=' config.py | head -1 | sed -E 's/.*"([^"]+)".*/\1/' || echo "?")

# ─── 4. chown au user applicatif ─────────────────────────────────────
log "4/7 chown -R ${APP_USER}:${APP_USER}"
chown -R "${APP_USER}:${APP_USER}" "$V2_PATH" || log "    chown a échoué (non-bloquant)"

# ─── 5. Restart v2 ───────────────────────────────────────────────────
log "5/7 systemctl restart ${SERVICE_NAME}"
systemctl restart "$SERVICE_NAME" || fail "systemctl restart KO"

# ─── 6. Healthcheck + rollback auto si KO ────────────────────────────
log "6/7 Healthcheck ${HEALTHZ_URL} (timeout ${HEALTHZ_TIMEOUT}s)"
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
    log "    Restore DB depuis $(basename "$BACKUP_FILE")"
    cp "$BACKUP_FILE" "$DB_PATH"
    chown "${APP_USER}:${APP_USER}" "$DB_PATH"
    log "    git reset --hard ${PREV_HEAD:0:7}"
    git reset --hard "$PREV_HEAD" --quiet
    chown -R "${APP_USER}:${APP_USER}" "$V2_PATH"
    log "    Restart ${SERVICE_NAME}"
    systemctl restart "$SERVICE_NAME"
    sleep 3

    # Annonce d'échec
    PREV_VERSION=$(grep -E '^APP_VERSION\s*=' config.py | head -1 | sed -E 's/.*"([^"]+)".*/\1/' || echo "?")
    sqlite3 "$DB_PATH" <<SQL_END 2>/dev/null || log "    Annonce d'échec non postée (sqlite KO)"
INSERT INTO update_announcements (scope, titre, message, created_at, created_by, active)
VALUES (
  'global',
  'Promotion annulée',
  '<div style="color:var(--danger);font-size:13px;line-height:1.6">Tentative de promotion vers v${NEW_VERSION} échouée (healthcheck KO). État restauré à v${PREV_VERSION} (commit ${PREV_HEAD:0:7}).</div>',
  datetime('now'),
  'promote-bot',
  1
);
SQL_END

    fail "Promotion annulée — état restauré à ${PREV_HEAD:0:7} (v${PREV_VERSION})"
fi

# ─── 7. Annonce de release (si notes fournies) ───────────────────────
if [[ -n "$NOTES" ]]; then
    log "7/7 Annonce de release v${NEW_VERSION}"
    # Construire le HTML de l'annonce selon le template MySifa
    MESSAGE_HTML="<div style=\"font-size:13px;line-height:1.7;color:var(--text2)\">"
    MESSAGE_HTML+="<div style=\"font-size:15px;font-weight:700;color:var(--text);margin-bottom:12px\">Mise à jour — v${NEW_VERSION}</div>"
    MESSAGE_HTML+="<div style=\"margin-bottom:10px;font-weight:600;color:var(--text);font-size:12px;text-transform:uppercase;letter-spacing:.5px\">Notes</div>"
    MESSAGE_HTML+="<div style=\"margin:0 0 14px 0\">${NOTES}</div>"
    MESSAGE_HTML+="<div style=\"margin-top:14px;padding-top:12px;border-top:1px solid var(--border);font-size:11px;color:var(--muted);line-height:1.6\">"
    MESSAGE_HTML+="Dans l'optique d'améliorer constamment l'outil, vos retours sont les bienvenus.<br>"
    MESSAGE_HTML+="Merci de votre confiance.<br>"
    MESSAGE_HTML+="<span style=\"color:var(--text2);font-weight:600\">Eugène</span></div></div>"
    # Échapper les apostrophes pour SQL
    MESSAGE_ESCAPED="${MESSAGE_HTML//\'/\'\'}"
    sqlite3 "$DB_PATH" <<SQL_END 2>/dev/null || log "    Annonce non postée (sqlite KO)"
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
    log "7/7 Pas de notes fournies — annonce ignorée"
fi

log ""
log "==> Promotion réussie : ${PREV_HEAD:0:7} → ${NEW_HEAD:0:7} (v${NEW_VERSION})"
exit 0

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
#  8. Enregistrement dans promotion_history (toujours — succès, rollback, échec)
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

# Le script est lancé par l'API en root (sudo -n). Les opérations git doivent
# tourner sous le user sifa qui détient la clé SSH GitHub
# (/home/sifa/.ssh/id_ed25519). On force aussi HOME via -H : sinon sudo garde
# HOME=/root et ssh ne trouve pas la clé.
gits() {
    sudo -u "${APP_USER}" -H git \
        -c user.name="promote-bot" \
        -c user.email="promote-bot@mysifa.com" \
        "$@"
}

# ─── Historique des promotions ───────────────────────────────────────
# record_promotion <statut> <message>
#   statut : success | rollback | failed
#
# Écrit une ligne dans promotion_history (DB v2) : c'est la trace réelle des
# mises à jour, affichée dans Paramètres › Déploiement › Historique.
# Best-effort — ne doit JAMAIS faire échouer une promotion par ailleurs réussie.
# Les valeurs transitent par l'environnement et sont insérées en paramètres liés
# (jamais d'interpolation SQL) : les sujets de commit et les notes HTML peuvent
# contenir des apostrophes sans rien casser.
# Le CREATE TABLE IF NOT EXISTS rend le script autonome : il fonctionne même si
# la DB v2 n'a pas encore été bootée par un code contenant la migration
# (typiquement sur le chemin de rollback, où l'ancien code est restauré).
record_promotion() {
    PH_DB="$DB_PATH" \
    PH_STATUT="$1" \
    PH_MESSAGE="$2" \
    PH_STARTED="${STARTED_AT:-}" \
    PH_VAVANT="${VERSION_AVANT:-}" \
    PH_VAPRES="${NEW_VERSION:-}" \
    PH_HAVANT="${PREV_HEAD:-}" \
    PH_HAPRES="${NEW_HEAD:-}" \
    PH_NOTES="${NOTES:-}" \
    PH_COMMITS="${COMMITS_RAW:-}" \
    python3 - <<'PYEOF' 2>/dev/null || log "    Historique non enregistre (python/sqlite KO)"
import json, os, sqlite3
from datetime import datetime

commits = []
for line in (os.environ.get("PH_COMMITS") or "").splitlines():
    if not line.strip():
        continue
    parts = line.split("|", 3)
    if len(parts) == 4:
        commits.append({
            "hash": parts[0], "author": parts[1],
            "date": parts[2], "subject": parts[3],
        })

now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
con = sqlite3.connect(os.environ["PH_DB"], timeout=10)
con.execute("""
    CREATE TABLE IF NOT EXISTS promotion_history (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at     TEXT NOT NULL,
        finished_at    TEXT,
        statut         TEXT NOT NULL DEFAULT 'success',
        version_avant  TEXT,
        version_apres  TEXT,
        head_avant     TEXT,
        head_apres     TEXT,
        commits_count  INTEGER NOT NULL DEFAULT 0,
        commits        TEXT,
        notes          TEXT,
        declencheur    TEXT DEFAULT 'promote-bot',
        message        TEXT
    )
""")
con.execute(
    """INSERT INTO promotion_history
       (started_at, finished_at, statut, version_avant, version_apres,
        head_avant, head_apres, commits_count, commits, notes,
        declencheur, message)
       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
    (
        os.environ.get("PH_STARTED") or now,
        now,
        os.environ.get("PH_STATUT") or "success",
        os.environ.get("PH_VAVANT") or None,
        os.environ.get("PH_VAPRES") or None,
        (os.environ.get("PH_HAVANT") or "")[:40] or None,
        (os.environ.get("PH_HAPRES") or "")[:40] or None,
        len(commits),
        json.dumps(commits, ensure_ascii=False),
        os.environ.get("PH_NOTES") or None,
        "promote-bot",
        os.environ.get("PH_MESSAGE") or None,
    ),
)
con.commit()
con.close()
PYEOF
}

cd "$V2_PATH" || fail "V2_PATH introuvable : $V2_PATH"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="${BACKUP_DIR}/promote_${TIMESTAMP}.db"
STARTED_AT=$(date '+%Y-%m-%dT%H:%M:%S')
COMMITS_RAW=""

# ─── 1. Backup DB ────────────────────────────────────────────────────
log "1/7 Backup DB"
if [[ ! -f "$DB_PATH" ]]; then
    fail "DB introuvable : $DB_PATH"
fi
cp "$DB_PATH" "$BACKUP_FILE" || fail "Backup DB échoué"
log "    OK : $(basename "$BACKUP_FILE")"

# ─── 2. Capture HEAD pour rollback ───────────────────────────────────
log "2/7 Capture HEAD v2 actuel"
PREV_HEAD=$(gits rev-parse HEAD) || fail "git rev-parse HEAD KO"
# Version en place AVANT la promotion — lue ici, car config.py sera écrasé par
# le reset de l'étape 3 (sert à afficher « v2.4.17 → v2.4.18 » dans l'historique).
VERSION_AVANT=$(grep -E '^APP_VERSION\s*=' config.py | head -1 | sed -E 's/.*"([^"]+)".*/\1/' || echo "?")
log "    HEAD avant : ${PREV_HEAD:0:7} (v${VERSION_AVANT})"

# ─── 3. Merge staging → main puis reset v2 sur origin/main ───────────
log "3/7 git fetch + merge staging→main + reset v2"
gits fetch --all --quiet || fail "git fetch KO"

# 3a. Si staging contient des commits non présents sur main, on merge sur origin
DIFF_COUNT=$(gits rev-list --count origin/main..origin/staging 2>/dev/null || echo "0")
if [[ "$DIFF_COUNT" -gt 0 ]]; then
    log "    $DIFF_COUNT commit(s) sur staging à intégrer dans main"

    # Aligner main local sur origin/main, puis merger origin/staging
    gits checkout main --quiet 2>/dev/null || gits checkout -B main origin/main --quiet
    gits reset --hard origin/main --quiet || fail "reset main local KO"

    if ! gits merge origin/staging --no-ff -m "promote: merge staging into main" --quiet; then
        log "    CONFLIT — git merge --abort"
        gits merge --abort 2>/dev/null
        gits reset --hard "$PREV_HEAD" --quiet
        record_promotion "failed" "Conflit de merge staging -> main"
        fail "Conflit de merge staging → main. À résoudre en local."
    fi

    if ! gits push origin main --quiet; then
        log "    git push origin main KO — rollback"
        gits reset --hard origin/main --quiet
        record_promotion "failed" "Push origin/main refuse"
        fail "Push origin/main refusé (droits ?)."
    fi

    log "    origin/main aligné avec origin/staging"
else
    log "    Rien à merger (staging déjà inclus dans main)"
fi

# 3b. Reset v2 sur origin/main (qui contient maintenant staging)
gits reset --hard origin/main --quiet || fail "git reset KO"
NEW_HEAD=$(gits rev-parse HEAD)
log "    HEAD après : ${NEW_HEAD:0:7}"

if [[ "$PREV_HEAD" == "$NEW_HEAD" ]]; then
    log "Aucun changement à promouvoir. Sortie."
    exit 0
fi

# Lire la version pour les logs (informative)
NEW_VERSION=$(grep -E '^APP_VERSION\s*=' config.py | head -1 | sed -E 's/.*"([^"]+)".*/\1/' || echo "?")

# Figer la liste des commits réellement embarqués dans cette release.
# --no-merges : on écarte le commit de merge « promote: merge staging into main »,
# qui n'apporte aucune information pour un lecteur humain.
COMMITS_RAW=$(gits log "${PREV_HEAD}..${NEW_HEAD}" --no-merges \
    --pretty=format:'%h|%an|%ad|%s' --date=format:'%Y-%m-%d %H:%M' 2>/dev/null || echo "")

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
    gits reset --hard "$PREV_HEAD" --quiet
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

    record_promotion "rollback" "Healthcheck KO apres ${HEALTHZ_TIMEOUT}s — etat restaure a ${PREV_HEAD:0:7} (v${PREV_VERSION})"
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

# ─── 8. Historique de la release ─────────────────────────────────────
log "8/8 Enregistrement dans l'historique des mises à jour"
record_promotion "success" ""

log ""
log "==> Promotion réussie : ${PREV_HEAD:0:7} → ${NEW_HEAD:0:7} (v${NEW_VERSION})"
exit 0

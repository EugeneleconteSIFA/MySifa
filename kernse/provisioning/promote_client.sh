#!/usr/bin/env bash
# =====================================================================
# Kernse — Promotion d'une instance client vers un git ref.
#
# Usage : promote_client.sh <slug> <git_ref> [notes]
#
# Actions (dans l'ordre) :
#   1. Backup DB client (sqlite3 .backup — live-safe)
#   2. Capture HEAD actuel (fallback si tout casse)
#   3. git fetch + git checkout <git_ref> dans le dossier de l'instance
#   4. chown récursif de l'instance
#   5. systemctl restart kernse-client-<slug>
#   6. Healthcheck curl https://<slug>.kernse.fr/healthz (15s timeout)
#   7. Si KO → restore DB backup + git reset HEAD précédent + restart
#              + log rollback + JSON "rolled_back":true
#   8. Sortie : JSON en dernière ligne pour parsing Python.
#
# Sécurité : ce script s'exécute sous sudo, uniquement invoqué par le
# service `promotion_service.py`. Les arguments sont validés côté Python
# (whitelist regex sur slug et git_ref) avant d'arriver ici.
#
# Note : ce script est un SQUELETTE — les chemins VPS réels seront ajustés
# quand l'infra Kernse sera provisionnée. Les commandes systemctl / nginx
# supposent que le pattern d'instance est :
#     /home/kernse/instances/<slug>/
#     systemd unit : kernse-client-<slug>.service
#     healthcheck  : https://<slug>.kernse.fr/healthz
# =====================================================================

set -euo pipefail

SLUG="${1:?slug requis}"
GIT_REF="${2:?git_ref requis}"
NOTES="${3:-}"

# Validation défensive (redondante avec le Python mais sécurité en profondeur)
if ! [[ "$SLUG" =~ ^[a-z0-9](-?[a-z0-9]){1,39}$ ]]; then
    printf '{"ok":false,"error":"slug invalide","slug":"%s"}\n' "$SLUG"
    exit 2
fi
if ! [[ "$GIT_REF" =~ ^([a-fA-F0-9]{4,40}|v?[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.-]+)?)$ ]]; then
    printf '{"ok":false,"error":"git_ref invalide","git_ref":"%s"}\n' "$GIT_REF"
    exit 2
fi

INSTANCES_ROOT="${KERNSE_INSTANCES_ROOT:-/home/kernse/instances}"
BACKUP_ROOT="${KERNSE_BACKUP_ROOT:-/home/kernse/backups}"
INSTANCE_DIR="$INSTANCES_ROOT/$SLUG"
DB_PATH="$INSTANCE_DIR/app/data/production.db"
SERVICE="kernse-client-$SLUG"
HEALTH_URL="https://$SLUG.kernse.fr/healthz"

STAMP="$(date -u +'%Y%m%dT%H%M%SZ')"
BACKUP_DIR="$BACKUP_ROOT/$SLUG"
BACKUP_FILE="$BACKUP_DIR/prepromote-$STAMP.db"

# --- Sanity : instance existe ---
if [[ ! -d "$INSTANCE_DIR" ]]; then
    printf '{"ok":false,"error":"instance introuvable","slug":"%s","path":"%s"}\n' "$SLUG" "$INSTANCE_DIR"
    exit 3
fi

mkdir -p "$BACKUP_DIR"

# --- 1. Backup DB live-safe ---
if [[ -f "$DB_PATH" ]]; then
    if ! sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'" 2>/tmp/km-promote-err.$$; then
        printf '{"ok":false,"error":"backup DB KO","stderr":%s}\n' \
            "$(python3 -c 'import json,sys;print(json.dumps(open("/tmp/km-promote-err.'$$'").read()[:400]))')"
        rm -f /tmp/km-promote-err.$$
        exit 4
    fi
fi

# --- 2. Capture HEAD précédent ---
PREV_HEAD="$(git -C "$INSTANCE_DIR" rev-parse HEAD 2>/dev/null || echo unknown)"

# --- 3. Fetch + checkout ---
CHECKOUT_LOG="$(mktemp -t km-promote-checkout.XXXXXX)"
if ! git -C "$INSTANCE_DIR" fetch --all --quiet > "$CHECKOUT_LOG" 2>&1; then
    ERR="$(head -c 400 "$CHECKOUT_LOG")"
    rm -f "$CHECKOUT_LOG"
    printf '{"ok":false,"error":"git fetch KO","stderr":%s}\n' \
        "$(python3 -c "import json,sys;print(json.dumps(sys.argv[1]))" "$ERR")"
    exit 5
fi

if ! git -C "$INSTANCE_DIR" checkout --quiet "$GIT_REF" > "$CHECKOUT_LOG" 2>&1; then
    ERR="$(head -c 400 "$CHECKOUT_LOG")"
    rm -f "$CHECKOUT_LOG"
    printf '{"ok":false,"error":"git checkout KO","git_ref":"%s","stderr":%s}\n' \
        "$GIT_REF" \
        "$(python3 -c "import json,sys;print(json.dumps(sys.argv[1]))" "$ERR")"
    exit 6
fi
rm -f "$CHECKOUT_LOG"

# --- 4. Ownership ---
chown -R kernse:kernse "$INSTANCE_DIR" 2>/dev/null || true

# --- 5. Restart service ---
if ! systemctl restart "$SERVICE" 2>/tmp/km-promote-svc.$$; then
    ERR="$(head -c 400 /tmp/km-promote-svc.$$)"
    rm -f /tmp/km-promote-svc.$$
    # tentative rollback
    git -C "$INSTANCE_DIR" reset --hard "$PREV_HEAD" >/dev/null 2>&1 || true
    systemctl restart "$SERVICE" >/dev/null 2>&1 || true
    printf '{"ok":false,"rolled_back":true,"error":"restart KO","final_ref":"%s","stderr":%s}\n' \
        "$PREV_HEAD" \
        "$(python3 -c "import json,sys;print(json.dumps(sys.argv[1]))" "$ERR")"
    exit 7
fi
rm -f /tmp/km-promote-svc.$$

# --- 6. Healthcheck ---
HEALTH_OK=0
for i in 1 2 3 4 5; do
    if curl --silent --show-error --max-time 3 --fail "$HEALTH_URL" >/dev/null 2>&1; then
        HEALTH_OK=1
        break
    fi
    sleep 2
done

if [[ "$HEALTH_OK" != "1" ]]; then
    # --- 7. Rollback ---
    if [[ -f "$BACKUP_FILE" ]]; then
        cp "$BACKUP_FILE" "$DB_PATH" 2>/dev/null || true
        chown kernse:kernse "$DB_PATH" 2>/dev/null || true
    fi
    git -C "$INSTANCE_DIR" reset --hard "$PREV_HEAD" >/dev/null 2>&1 || true
    systemctl restart "$SERVICE" >/dev/null 2>&1 || true
    printf '{"ok":false,"rolled_back":true,"healthcheck_ok":false,"from_ref":"%s","attempted_ref":"%s","final_ref":"%s","backup":"%s"}\n' \
        "$PREV_HEAD" "$GIT_REF" "$PREV_HEAD" "$BACKUP_FILE"
    exit 8
fi

NEW_HEAD="$(git -C "$INSTANCE_DIR" rev-parse --short HEAD)"

# --- 8. Sortie succès ---
printf '{"ok":true,"healthcheck_ok":true,"rolled_back":false,"from_ref":"%s","final_ref":"%s","backup":"%s","notes":%s}\n' \
    "$PREV_HEAD" "$NEW_HEAD" "$BACKUP_FILE" \
    "$(python3 -c "import json,sys;print(json.dumps(sys.argv[1]))" "$NOTES")"

exit 0

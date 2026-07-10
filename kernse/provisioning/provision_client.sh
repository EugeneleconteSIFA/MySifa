#!/usr/bin/env bash
# =====================================================================
# Kernse — Provisionne une nouvelle instance client.
#
# Usage : provision_client.sh <slug> <subdomain> <port> [starter_kit]
#
# Actions :
#   1. Sanity check : slug/port/subdomain valides, dossier pas déjà là
#   2. Crée /home/kernse/instances/<slug>/
#   3. Git clone du repo métier + checkout du ref plateforme actuel
#   4. Crée venv, installe requirements.txt
#   5. Crée data/production.db vide + migrations
#   6. Applique le starter kit si fourni (JSON de kernse/seeds/starter_kits/)
#   7. Génère systemd unit depuis templates/kernse-client.service.tmpl
#   8. Génère nginx vhost depuis templates/kernse-client.nginx.tmpl
#   9. certbot pour l'HTTPS (mode webroot)
#  10. systemctl daemon-reload + enable + start
#  11. Healthcheck curl https://<subdomain>/healthz
#  12. Sortie : JSON en dernière ligne (parsé côté Python)
#
# Note : SQUELETTE — les chemins exacts, l'utilisateur système
# (`kernse`), l'emplacement du repo métier et le mode certbot seront
# ajustés au premier vrai provisioning sur le VPS.
# =====================================================================

set -euo pipefail

SLUG="${1:?slug requis}"
SUBDOMAIN="${2:?subdomain requis}"
PORT="${3:?port requis}"
STARTER_KIT="${4:-}"

# --- Validation défensive (redondante avec le Python — sécurité en profondeur) ---
if ! [[ "$SLUG" =~ ^[a-z0-9](-?[a-z0-9]){1,39}$ ]]; then
    printf '{"ok":false,"error":"slug invalide","slug":"%s"}\n' "$SLUG"; exit 2
fi
if ! [[ "$SUBDOMAIN" =~ ^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)+$ ]]; then
    printf '{"ok":false,"error":"subdomain invalide","subdomain":"%s"}\n' "$SUBDOMAIN"; exit 2
fi
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [[ "$PORT" -lt 8200 ]] || [[ "$PORT" -gt 9999 ]]; then
    printf '{"ok":false,"error":"port invalide","port":"%s"}\n' "$PORT"; exit 2
fi
if [[ -n "$STARTER_KIT" ]] && ! [[ "$STARTER_KIT" =~ ^[a-z_]{2,32}$ ]]; then
    printf '{"ok":false,"error":"starter_kit invalide","starter_kit":"%s"}\n' "$STARTER_KIT"; exit 2
fi

INSTANCES_ROOT="${KERNSE_INSTANCES_ROOT:-/home/kernse/instances}"
REPO_URL="${KERNSE_METIER_REPO_URL:-https://github.com/EugeneleconteSIFA/MySifa.git}"
BRANCH="${KERNSE_METIER_BRANCH:-main}"
TEMPLATES_DIR="${KERNSE_TEMPLATES_DIR:-/opt/kernse/kernse/provisioning/templates}"
STARTER_KITS_DIR="${KERNSE_STARTER_KITS_DIR:-/opt/kernse/kernse/seeds/starter_kits}"
NGINX_SITES="${KERNSE_NGINX_SITES:-/etc/nginx/sites-available}"
NGINX_ENABLED="${KERNSE_NGINX_ENABLED:-/etc/nginx/sites-enabled}"
SYSTEMD_DIR="${KERNSE_SYSTEMD_DIR:-/etc/systemd/system}"

INSTANCE_DIR="$INSTANCES_ROOT/$SLUG"
DB_PATH="$INSTANCE_DIR/app/data/production.db"
SERVICE="kernse-client-$SLUG"
UNIT_FILE="$SYSTEMD_DIR/$SERVICE.service"
NGINX_CONF="$NGINX_SITES/$SERVICE.conf"

# --- Existence check ---
if [[ -e "$INSTANCE_DIR" ]]; then
    printf '{"ok":false,"error":"instance déjà existante","slug":"%s"}\n' "$SLUG"; exit 3
fi

mkdir -p "$INSTANCE_DIR"

# --- Clone du code métier ---
if ! git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$INSTANCE_DIR" >/tmp/kp-clone.$$ 2>&1; then
    ERR="$(head -c 400 /tmp/kp-clone.$$)"; rm -f /tmp/kp-clone.$$
    rm -rf "$INSTANCE_DIR"
    printf '{"ok":false,"error":"git clone KO","stderr":%s}\n' \
        "$(python3 -c "import json,sys;print(json.dumps(sys.argv[1]))" "$ERR")"
    exit 4
fi
rm -f /tmp/kp-clone.$$

# --- Venv + requirements ---
python3 -m venv "$INSTANCE_DIR/.venv"
if ! "$INSTANCE_DIR/.venv/bin/pip" install --quiet -r "$INSTANCE_DIR/requirements.txt" >/tmp/kp-pip.$$ 2>&1; then
    ERR="$(head -c 400 /tmp/kp-pip.$$)"; rm -f /tmp/kp-pip.$$
    rm -rf "$INSTANCE_DIR"
    printf '{"ok":false,"error":"pip install KO","stderr":%s}\n' \
        "$(python3 -c "import json,sys;print(json.dumps(sys.argv[1]))" "$ERR")"
    exit 5
fi
rm -f /tmp/kp-pip.$$

# --- DB init (l'app métier crée sa DB au premier boot via _migrate()) ---
mkdir -p "$INSTANCE_DIR/app/data"

# --- Starter kit (seed initial des machines/opérations) ---
if [[ -n "$STARTER_KIT" ]]; then
    KIT_FILE="$STARTER_KITS_DIR/$STARTER_KIT.json"
    if [[ -f "$KIT_FILE" ]]; then
        cp "$KIT_FILE" "$INSTANCE_DIR/app/data/starter_kit.json"
    fi
fi

# --- systemd unit ---
if [[ ! -f "$TEMPLATES_DIR/kernse-client.service.tmpl" ]]; then
    printf '{"ok":false,"error":"template systemd manquant","path":"%s"}\n' "$TEMPLATES_DIR/kernse-client.service.tmpl"
    rm -rf "$INSTANCE_DIR"
    exit 6
fi

APP_NAME="${KERNSE_DEFAULT_APP_NAME:-Kernse}"
sed \
    -e "s|__SLUG__|$SLUG|g" \
    -e "s|__PORT__|$PORT|g" \
    -e "s|__APP_NAME__|$APP_NAME|g" \
    -e "s|__INSTANCE_DIR__|$INSTANCE_DIR|g" \
    -e "s|__DB_PATH__|$DB_PATH|g" \
    "$TEMPLATES_DIR/kernse-client.service.tmpl" > "$UNIT_FILE"

# --- nginx vhost ---
sed \
    -e "s|__SLUG__|$SLUG|g" \
    -e "s|__SUBDOMAIN__|$SUBDOMAIN|g" \
    -e "s|__PORT__|$PORT|g" \
    "$TEMPLATES_DIR/kernse-client.nginx.tmpl" > "$NGINX_CONF"

ln -sf "$NGINX_CONF" "$NGINX_ENABLED/$SERVICE.conf"

# --- Reload systemd + start ---
systemctl daemon-reload
systemctl enable --now "$SERVICE" 2>/tmp/kp-svc.$$ || {
    ERR="$(head -c 400 /tmp/kp-svc.$$)"; rm -f /tmp/kp-svc.$$
    printf '{"ok":false,"error":"systemctl KO","stderr":%s}\n' \
        "$(python3 -c "import json,sys;print(json.dumps(sys.argv[1]))" "$ERR")"
    exit 7
}
rm -f /tmp/kp-svc.$$

# --- Ownership ---
chown -R kernse:kernse "$INSTANCE_DIR" 2>/dev/null || true

# --- Reload nginx (avant certbot) — sert du HTTP en attendant ---
nginx -t >/dev/null 2>&1 && systemctl reload nginx

# --- certbot (mode standalone n'est pas idéal — préférer webroot) ---
# Décommenter quand le vhost HTTP renvoie 200 sur /.well-known/acme-challenge :
# certbot --nginx -n --agree-tos --email admin@kernse.fr -d "$SUBDOMAIN" >/dev/null 2>&1 || true

# --- Healthcheck (via HTTP local pour éviter le TLS pas encore prêt) ---
HEALTH_OK=0
for i in 1 2 3 4 5; do
    if curl --silent --show-error --max-time 3 --fail "http://127.0.0.1:$PORT/healthz" >/dev/null 2>&1; then
        HEALTH_OK=1; break
    fi
    sleep 2
done

if [[ "$HEALTH_OK" != "1" ]]; then
    printf '{"ok":false,"error":"healthcheck KO","slug":"%s","service":"%s"}\n' "$SLUG" "$SERVICE"
    exit 8
fi

# --- Sortie succès ---
NEW_HEAD="$(git -C "$INSTANCE_DIR" rev-parse --short HEAD 2>/dev/null || echo unknown)"
printf '{"ok":true,"slug":"%s","subdomain":"%s","port":%s,"service":"%s","deployed_ref":"%s","starter_kit":"%s"}\n' \
    "$SLUG" "$SUBDOMAIN" "$PORT" "$SERVICE" "$NEW_HEAD" "$STARTER_KIT"

exit 0

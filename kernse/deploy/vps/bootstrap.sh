#!/usr/bin/env bash
# =====================================================================
# Kernse — Bootstrap complet de la plateforme sur le VPS.
#
# Idempotent : peut être relancé sans dégâts. Les étapes déjà faites
# sont détectées et sautées.
#
# À lancer en root (sudo) depuis n'importe où :
#   curl -O https://raw.githubusercontent.com/EugeneleconteSIFA/MySifa/staging/kernse/deploy/vps/bootstrap.sh
#   chmod +x bootstrap.sh
#   sudo ./bootstrap.sh
#
# OU depuis un checkout local :
#   sudo bash kernse/deploy/vps/bootstrap.sh
#
# Étapes :
#   1.  Création user `kernse` + dossiers /home/kernse/{platform,platform-v1,env,instances,backups,venv}
#   2.  Clone du repo dans platform/ (branche main) et platform-v1/ (staging)
#   3.  Création du venv Python + installation kernse/requirements.txt
#   4.  Init des DB plateforme (via kernse.shared.db.schema)
#   5.  Copie des env files templates dans /home/kernse/env/ (si absents)
#   6.  Copie des 4 unit systemd + reload
#   7.  Copie du sudoers snippet + visudo check
#   8.  Copie des 4 vhosts nginx (mais NON ENABLED — HTTPS pas encore prêt)
#   9.  Prompt : lance certbot ? (si non, à faire manuellement plus tard)
#  10.  Activation nginx + reload
#  11.  Enable + start des 4 services
#  12.  Healthcheck des 4 endpoints /healthz
#
# Le mot de passe superadmin bootstrap est demandé interactivement
# (masqué). Il DOIT être changé au premier login via la console.
# =====================================================================

set -euo pipefail

if [[ "$EUID" -ne 0 ]]; then
    echo "Erreur : ce script doit être lancé en root (sudo)."
    exit 1
fi

REPO_URL="${KERNSE_REPO_URL:-https://github.com/EugeneleconteSIFA/MySifa.git}"
BRANCH_V2="${KERNSE_BRANCH_V2:-main}"
BRANCH_V1="${KERNSE_BRANCH_V1:-staging}"
KERNSE_HOME="/home/kernse"
DEPLOY_SRC="$(cd "$(dirname "$0")" && pwd)"

echo "==> Kernse bootstrap : sources = $DEPLOY_SRC"

# --- 1. User kernse ---
if ! id kernse &>/dev/null; then
    echo "==> Création utilisateur kernse"
    useradd --create-home --shell /bin/bash --home-dir "$KERNSE_HOME" kernse
else
    echo "==> Utilisateur kernse existe déjà — OK"
fi

# --- 2. Arborescence ---
echo "==> Création arborescence $KERNSE_HOME"
sudo -u kernse mkdir -p \
    "$KERNSE_HOME/env" \
    "$KERNSE_HOME/instances" \
    "$KERNSE_HOME/backups/platform" \
    "$KERNSE_HOME/backups/clients" \
    "$KERNSE_HOME/backups/v1-db-rotation"
chown -R kernse:kernse "$KERNSE_HOME"

# --- 3. Clones ---
if [[ ! -d "$KERNSE_HOME/platform/.git" ]]; then
    echo "==> Clone repo → $KERNSE_HOME/platform (branche $BRANCH_V2)"
    sudo -u kernse git clone --branch "$BRANCH_V2" "$REPO_URL" "$KERNSE_HOME/platform"
else
    echo "==> $KERNSE_HOME/platform existe — pull uniquement"
    sudo -u kernse git -C "$KERNSE_HOME/platform" pull --ff-only
fi

if [[ ! -d "$KERNSE_HOME/platform-v1/.git" ]]; then
    echo "==> Clone repo → $KERNSE_HOME/platform-v1 (branche $BRANCH_V1)"
    sudo -u kernse git clone --branch "$BRANCH_V1" "$REPO_URL" "$KERNSE_HOME/platform-v1"
else
    echo "==> $KERNSE_HOME/platform-v1 existe — pull uniquement"
    sudo -u kernse git -C "$KERNSE_HOME/platform-v1" pull --ff-only
fi

# --- 4. Venv + deps ---
if [[ ! -d "$KERNSE_HOME/venv" ]]; then
    echo "==> Création venv Python"
    sudo -u kernse python3 -m venv "$KERNSE_HOME/venv"
fi
echo "==> Installation des dépendances Kernse"
sudo -u kernse "$KERNSE_HOME/venv/bin/pip" install --quiet --upgrade pip
sudo -u kernse "$KERNSE_HOME/venv/bin/pip" install --quiet -r "$KERNSE_HOME/platform/kernse/requirements.txt"

# --- 5. Env files ---
echo "==> Copie des env files templates (si absents)"
for name in kernse-admin-v2 kernse-admin-v1 kernse-landing-v2 kernse-landing-v1; do
    TARGET="$KERNSE_HOME/env/$name.env"
    if [[ ! -f "$TARGET" ]]; then
        cp "$DEPLOY_SRC/env/$name.env.example" "$TARGET"
        chown kernse:kernse "$TARGET"
        chmod 600 "$TARGET"
        echo "    créé : $TARGET (à éditer manuellement pour remplir les secrets)"
    else
        echo "    existe : $TARGET — inchangé"
    fi
done

# --- 5.b Prompt bootstrap superadmin ---
echo ""
read -p "==> Voulez-vous définir MAINTENANT le mot de passe superadmin bootstrap ? [O/n] " ANSWER
if [[ ! "$ANSWER" =~ ^[Nn] ]]; then
    read -p "    Email superadmin (défaut: eleconte@sifa.pro) : " EMAIL
    EMAIL="${EMAIL:-eleconte@sifa.pro}"
    read -sp "    Mot de passe (min 12 caractères) : " PWD; echo ""
    if [[ ${#PWD} -lt 12 ]]; then
        echo "    Mot de passe < 12 caractères — passage. À définir dans les env files avant le boot."
    else
        SECRET_V2=$(openssl rand -hex 32)
        SECRET_V1=$(openssl rand -hex 32)
        sed -i "s|^KERNSE_BOOTSTRAP_EMAIL=.*|KERNSE_BOOTSTRAP_EMAIL=$EMAIL|" "$KERNSE_HOME/env/kernse-admin-v2.env"
        sed -i "s|^KERNSE_BOOTSTRAP_PASSWORD=.*|KERNSE_BOOTSTRAP_PASSWORD=$PWD|"   "$KERNSE_HOME/env/kernse-admin-v2.env"
        sed -i "s|^KERNSE_ADMIN_SECRET_KEY=.*|KERNSE_ADMIN_SECRET_KEY=$SECRET_V2|" "$KERNSE_HOME/env/kernse-admin-v2.env"
        sed -i "s|^KERNSE_BOOTSTRAP_EMAIL=.*|KERNSE_BOOTSTRAP_EMAIL=$EMAIL|" "$KERNSE_HOME/env/kernse-admin-v1.env"
        sed -i "s|^KERNSE_BOOTSTRAP_PASSWORD=.*|KERNSE_BOOTSTRAP_PASSWORD=$PWD|"   "$KERNSE_HOME/env/kernse-admin-v1.env"
        sed -i "s|^KERNSE_ADMIN_SECRET_KEY=.*|KERNSE_ADMIN_SECRET_KEY=$SECRET_V1|" "$KERNSE_HOME/env/kernse-admin-v1.env"
        echo "    env files mis à jour (email + password + secret 32 octets)."
    fi
fi

# --- 6. systemd units ---
echo "==> Copie des unit files systemd"
for unit in kernse-landing-v2 kernse-landing-v1 kernse-admin-v2 kernse-admin-v1; do
    cp "$DEPLOY_SRC/systemd/$unit.service" "/etc/systemd/system/$unit.service"
    chmod 644 "/etc/systemd/system/$unit.service"
done
systemctl daemon-reload

# --- 7. Sudoers ---
echo "==> Copie du sudoers snippet"
cp "$DEPLOY_SRC/sudoers/kernse-admin" /etc/sudoers.d/kernse-admin
chmod 440 /etc/sudoers.d/kernse-admin
if ! visudo -c -q 2>/dev/null; then
    echo "    ERREUR visudo — le fichier /etc/sudoers.d/kernse-admin a un problème. Retrait."
    rm -f /etc/sudoers.d/kernse-admin
    exit 2
fi
echo "    visudo OK"

# --- 8. Vhosts nginx ---
echo "==> Copie des vhosts nginx (non enabled — certbot d'abord)"
for vhost in www.kernse.fr v1.kernse.fr admin.kernse.fr admin-v1.kernse.fr; do
    cp "$DEPLOY_SRC/nginx/$vhost.conf" "/etc/nginx/sites-available/$vhost.conf"
done

# --- 9. Certbot ---
echo ""
read -p "==> Lancer certbot maintenant pour émettre les certificats HTTPS ? [O/n] " ANSWER
if [[ ! "$ANSWER" =~ ^[Nn] ]]; then
    if ! command -v certbot &>/dev/null; then
        echo "    certbot non installé — apt install certbot python3-certbot-nginx"
        apt-get install -y certbot python3-certbot-nginx
    fi

    # Active d'abord un vhost HTTP-only temporaire pour chaque domaine
    # (nginx doit répondre sur port 80 pour que certbot valide).
    mkdir -p /var/www/certbot
    for vhost in www.kernse.fr v1.kernse.fr admin.kernse.fr admin-v1.kernse.fr; do
        # Enable le vhost — mais nginx va râler tant qu'il n'y a pas de certif.
        # Astuce : on crée un vhost HTTP-only le temps de certbot.
        cat > "/etc/nginx/sites-enabled/$vhost-http-only.conf" << TMPEOF
server {
    listen 80;
    server_name $vhost;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 200 "OK — bootstrap Kernse en cours"; add_header Content-Type text/plain; }
}
TMPEOF
    done
    nginx -t && systemctl reload nginx

    for vhost in www.kernse.fr v1.kernse.fr admin.kernse.fr admin-v1.kernse.fr; do
        echo "    certbot pour $vhost"
        certbot certonly --webroot -w /var/www/certbot -d "$vhost" -n --agree-tos --email eleconte@sifa.pro --no-eff-email || {
            echo "    ⚠  certbot $vhost KO — vérifie DNS + retry manuel"
        }
    done

    # Nettoyage des vhosts HTTP-only, activation des vrais vhosts HTTPS
    for vhost in www.kernse.fr v1.kernse.fr admin.kernse.fr admin-v1.kernse.fr; do
        rm -f "/etc/nginx/sites-enabled/$vhost-http-only.conf"
        ln -sf "/etc/nginx/sites-available/$vhost.conf" "/etc/nginx/sites-enabled/$vhost.conf"
    done
    nginx -t && systemctl reload nginx
else
    echo "    ⚠  Certbot non lancé — les vhosts nginx ne sont PAS enabled tant que les certificats manquent."
    echo "       Pour reprendre :"
    echo "       sudo certbot certonly --webroot -w /var/www/certbot -d www.kernse.fr -d v1.kernse.fr -d admin.kernse.fr -d admin-v1.kernse.fr --agree-tos --email eleconte@sifa.pro"
    echo "       sudo ln -sf /etc/nginx/sites-available/{www,v1,admin,admin-v1}.kernse.fr.conf /etc/nginx/sites-enabled/"
    echo "       sudo systemctl reload nginx"
fi

# --- 10 + 11. Enable + start ---
echo "==> Activation + démarrage des 4 services Kernse"
for svc in kernse-landing-v2 kernse-landing-v1 kernse-admin-v2 kernse-admin-v1; do
    systemctl enable "$svc" >/dev/null 2>&1
    systemctl restart "$svc"
done
sleep 3

# --- 12. Healthcheck ---
echo ""
echo "==> Healthcheck des 4 services"
for pair in "kernse-landing-v2:8101" "kernse-landing-v1:8103" "kernse-admin-v2:8102" "kernse-admin-v1:8104"; do
    svc="${pair%%:*}"
    port="${pair##*:}"
    if curl -fs --max-time 3 "http://127.0.0.1:$port/healthz" >/dev/null; then
        echo "    ✓ $svc (port $port) UP"
    else
        echo "    ✗ $svc (port $port) KO — journalctl -eu $svc"
    fi
done

echo ""
echo "==========================================================="
echo "Kernse — bootstrap terminé."
echo ""
echo "URLs (une fois les vhosts HTTPS enabled) :"
echo "    https://www.kernse.fr        — landing publique"
echo "    https://v1.kernse.fr         — landing staging"
echo "    https://admin.kernse.fr      — console prod (session cookie + 2FA TOTP)"
echo "    https://admin-v1.kernse.fr   — console staging"
echo ""
echo "Premier login superadmin :"
echo "    1. Va sur https://admin.kernse.fr/login"
echo "    2. Email + mot de passe (ceux définis dans /home/kernse/env/kernse-admin-v2.env)"
echo "    3. Active la 2FA : https://admin.kernse.fr/2fa/setup"
echo "    4. Retire les 2 lignes KERNSE_BOOTSTRAP_* du env file"
echo "    5. sudo systemctl restart kernse-admin-v2"
echo "==========================================================="

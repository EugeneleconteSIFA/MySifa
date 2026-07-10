# Déploiement Kernse — VPS

Ce dossier contient tout ce qu'il faut pour installer Kernse sur un VPS
Debian/Ubuntu. Deux façons de procéder :

- **Automatisée** : `sudo bash bootstrap.sh` (recommandé la première fois).
- **Manuelle** : suivre la marche à suivre plus bas si tu veux garder la main.

## Pré-requis

- VPS avec un accès `sudo`, Debian 11+ ou Ubuntu 22.04+.
- DNS déjà configuré (records A) pour :
  - `www.kernse.fr`
  - `v1.kernse.fr`
  - `admin.kernse.fr`
  - `admin-v1.kernse.fr`
  - `demo.kernse.fr` (pour la démo, à ajouter avant le premier client)
  - `@` (kernse.fr sans sous-domaine — landing de secours ou redirect vers www)
- Packages : `git`, `python3-venv`, `nginx`, `certbot`, `python3-certbot-nginx`,
  `sqlite3`, `openssl`, `curl`.
  ```bash
  sudo apt update && sudo apt install -y git python3-venv python3-pip \
      nginx certbot python3-certbot-nginx sqlite3 openssl curl
  ```

## Layout sur le VPS

```
/home/kernse/                              # nouveau user système
├── platform/                              # clone du repo (branche main)
├── platform-v1/                           # clone du repo (branche staging)
├── env/                                   # env files (chmod 600, owner kernse)
│   ├── kernse-admin-v2.env                # secrets superadmin + Stripe (à venir)
│   ├── kernse-admin-v1.env
│   ├── kernse-landing-v2.env
│   └── kernse-landing-v1.env
├── venv/                                  # venv Python partagé pour Kernse
├── instances/                             # instances clients (créées par provision_client.sh)
│   ├── demo/
│   └── ...
└── backups/
    ├── platform/                          # sauvegardes des DB plateforme
    ├── clients/<slug>/                    # sauvegardes DB par client
    └── v1-db-rotation/                    # rotation pré-resync
```

Attention : `/home/sifa/` (existant, MySifa SIFA) est **intouché**. Kernse est
strictement isolé sous `/home/kernse/`.

## Marche à suivre — automatisée

Depuis un checkout local du repo (branche `main` ou `staging`) :

```bash
# 1. Clone temporaire OU repo déjà présent
git clone https://github.com/EugeneleconteSIFA/MySifa.git /tmp/mysifa
cd /tmp/mysifa/kernse/deploy/vps

# 2. Bootstrap
sudo bash bootstrap.sh
```

Le script :
1. Crée l'utilisateur `kernse` et l'arborescence.
2. Clone le repo dans `/home/kernse/platform/` (main) et `platform-v1/` (staging).
3. Crée le venv et installe `kernse/requirements.txt`.
4. Copie les env files (à éditer ensuite).
5. Te demande interactivement le mot de passe superadmin bootstrap.
6. Installe les 4 unit systemd + sudoers snippet.
7. Copie les vhosts nginx.
8. Te demande de lancer certbot (recommandé : oui).
9. Enable + start les 4 services.
10. Healthcheck et affiche les URLs.

Durée : environ 3-5 minutes (dépend de la vitesse de certbot).

## Marche à suivre — manuelle

Si tu préfères tout faire à la main pour comprendre chaque étape :

### 1. Créer l'utilisateur système

```bash
sudo useradd --create-home --shell /bin/bash --home-dir /home/kernse kernse
```

### 2. Créer l'arborescence

```bash
sudo -u kernse mkdir -p \
    /home/kernse/env \
    /home/kernse/instances \
    /home/kernse/backups/{platform,clients,v1-db-rotation}
```

### 3. Cloner le code

```bash
sudo -u kernse git clone -b main    https://github.com/EugeneleconteSIFA/MySifa.git /home/kernse/platform
sudo -u kernse git clone -b staging https://github.com/EugeneleconteSIFA/MySifa.git /home/kernse/platform-v1
```

### 4. Venv Python + deps

```bash
sudo -u kernse python3 -m venv /home/kernse/venv
sudo -u kernse /home/kernse/venv/bin/pip install --upgrade pip
sudo -u kernse /home/kernse/venv/bin/pip install -r /home/kernse/platform/kernse/requirements.txt
```

### 5. Env files

```bash
cd /home/kernse/platform/kernse/deploy/vps
sudo cp env/kernse-admin-v2.env.example    /home/kernse/env/kernse-admin-v2.env
sudo cp env/kernse-admin-v1.env.example    /home/kernse/env/kernse-admin-v1.env
sudo cp env/kernse-landing-v2.env.example  /home/kernse/env/kernse-landing-v2.env
sudo cp env/kernse-landing-v1.env.example  /home/kernse/env/kernse-landing-v1.env
sudo chown -R kernse:kernse /home/kernse/env
sudo chmod 600 /home/kernse/env/*.env
```

Éditer chaque `.env` pour remplir les vraies valeurs (mot de passe
bootstrap, `KERNSE_ADMIN_SECRET_KEY` généré avec `openssl rand -hex 32`).

### 6. Systemd

```bash
cd /home/kernse/platform/kernse/deploy/vps/systemd
sudo cp *.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 7. Sudoers (obligatoire — sinon kernse-admin ne peut pas provisionner)

```bash
sudo cp /home/kernse/platform/kernse/deploy/vps/sudoers/kernse-admin /etc/sudoers.d/kernse-admin
sudo chmod 440 /etc/sudoers.d/kernse-admin
sudo visudo -c    # doit dire "parsed OK"
```

### 8. Nginx (vhosts d'abord en HTTP-only pour certbot)

```bash
cd /home/kernse/platform/kernse/deploy/vps/nginx
sudo cp *.conf /etc/nginx/sites-available/
```

**Ne pas activer les liens `sites-enabled` tant que les certificats
n'existent pas** — nginx refusera de démarrer sans les `.pem`.

Pour permettre à certbot de valider les domaines, active un vhost
HTTP-only temporaire pour chaque sous-domaine (ou utilise le mode
`--nginx` de certbot qui s'en charge). Le `bootstrap.sh` le fait
automatiquement.

### 9. Certbot

```bash
sudo mkdir -p /var/www/certbot
sudo certbot certonly --webroot -w /var/www/certbot \
    -d www.kernse.fr -d v1.kernse.fr -d admin.kernse.fr -d admin-v1.kernse.fr \
    --agree-tos --email eleconte@sifa.pro --no-eff-email
```

### 10. Activer les vhosts HTTPS

```bash
cd /etc/nginx/sites-enabled
sudo ln -sf ../sites-available/www.kernse.fr.conf .
sudo ln -sf ../sites-available/v1.kernse.fr.conf .
sudo ln -sf ../sites-available/admin.kernse.fr.conf .
sudo ln -sf ../sites-available/admin-v1.kernse.fr.conf .
sudo nginx -t && sudo systemctl reload nginx
```

### 11. Démarrer les services Kernse

```bash
sudo systemctl enable --now kernse-landing-v2 kernse-landing-v1 kernse-admin-v2 kernse-admin-v1
```

### 12. Healthcheck

```bash
for port in 8101 8103 8102 8104; do
    echo -n "port $port : "
    curl -fs http://127.0.0.1:$port/healthz && echo ""
done
```

Attendu : 4 lignes `{"status":"ok","env":"v2","version":"0.1.0"}` (ou v1).

## Premier login superadmin

1. Ouvre `https://admin.kernse.fr/login`
2. Email + mot de passe (ceux du `.env`)
3. Tu es redirigé sur `/admin` (2FA pas encore active)
4. Active la 2FA : `/2fa/setup` — scanne le QR ou tape le secret dans
   Google Authenticator / Authy / 1Password
5. **Retire les 2 lignes `KERNSE_BOOTSTRAP_*`** du `.env`
6. `sudo systemctl restart kernse-admin-v2`

À partir de là, la 2FA est obligatoire à chaque login.

## Créer la démo (`demo.kernse.fr`)

Une fois la console fonctionnelle :

1. Ajoute un record DNS A `demo` → IP du VPS.
2. Depuis `admin.kernse.fr/admin` (ou en cURL) :
   ```bash
   curl -X POST https://admin.kernse.fr/api/v1/clients \
        -H "Content-Type: application/json" \
        -H "Cookie: kernse_admin_sid=<ta_session>" \
        -d '{"slug":"demo","company_name":"Kernse Démo","subdomain":"demo.kernse.fr","plan":"atelier","contact_email":"demo@kernse.fr"}'
   ```
3. Provisionne physiquement :
   ```bash
   curl -X POST https://admin.kernse.fr/api/v1/provision/client/<client_id> \
        -H "Content-Type: application/json" \
        -H "Cookie: kernse_admin_sid=<ta_session>" \
        -d '{"starter_kit":"imprimerie"}'
   ```
4. certbot pour `demo.kernse.fr` (le script provision_client.sh a une
   étape certbot désactivée par défaut — à activer quand tu es prêt).

## Debug

- **kernse-admin ne démarre pas** :
  ```bash
  journalctl -eu kernse-admin-v2
  ```
- **nginx refuse de reload** :
  ```bash
  sudo nginx -t   # affiche l'erreur exacte
  ```
- **certbot échoue** : vérifie que le DNS pointe bien vers le VPS et que
  le port 80 est bien exposé côté firewall.
- **Bootstrap superadmin non créé** : vérifie
  `journalctl -eu kernse-admin-v2 | grep -i bootstrap` — le message
  `[kernse-admin] Superadmin bootstrap créé` doit apparaître au 1er boot.

## Mise à jour du code Kernse plateforme

Pour promouvoir une nouvelle version du code Kernse (landing + admin,
pas les instances clients) :

```bash
# staging → prend les derniers changements de la branche staging
sudo -u kernse git -C /home/kernse/platform-v1 pull --ff-only
sudo systemctl restart kernse-landing-v1 kernse-admin-v1

# prod → prend les derniers changements de la branche main
sudo -u kernse git -C /home/kernse/platform    pull --ff-only
sudo systemctl restart kernse-landing-v2 kernse-admin-v2
```

Les instances clients ont leur propre cycle (bouton « Promouvoir » dans
la console).

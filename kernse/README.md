# kernse/

Dossier de travail du produit SaaS commercial **Kernse**, extrait de MySifa
pour être vendu aux TPE/PME industrielles.

**Avant de coder quoi que ce soit dans ce dossier, lire `CLAUDE.md`.**

## Architecture — trois apps FastAPI distinctes, un seul repo

Kernse évite toute app monolithique. Chaque surface est une app FastAPI
indépendante avec son propre `main.py`, son propre service systemd, son
propre port. Elles partagent uniquement le dossier `shared/` (modèles
Pydantic, helpers DB, auth) — jamais d'import direct entre apps.

| App | Path | Domaine | Port prod / test | Rôle |
|---|---|---|---|---|
| `kernse-landing` | `landing/` | `www.kernse.fr` / `v1.kernse.fr` | 8101 / 8103 | Site public (FastAPI + Jinja2, aucune DB, aucune auth) |
| `kernse-admin`   | `admin/`   | `admin.kernse.fr` / `admin-v1.kernse.fr` | 8102 / 8104 | Console plateforme (auth superadmin allowlist, DB plateforme SQLite) |
| Instances clients | `/app/` (code MySifa) | `<client>.kernse.fr` | 8200+ | Une app FastAPI + une SQLite par client, code métier commun avec SIFA |

## Structure

```
kernse/
├── CLAUDE.md               règles Kernse
├── README.md               ce fichier
├── landing/                app FastAPI landing publique
│   ├── main.py             entrée uvicorn
│   ├── config.py
│   ├── routers/pages.py    /, /contact, /demo, /mentions-legales, /cgv
│   ├── templates/*.j2      Jinja2
│   └── static/landing.css  design system Kernse
├── admin/                  app FastAPI console plateforme
│   ├── main.py             entrée uvicorn
│   ├── config.py
│   ├── routers/
│   │   ├── clients.py      /api/v1/clients (CRUD)
│   │   ├── promotion.py    /api/v1/promotion/* (promouvoir, épingle)
│   │   └── audit.py        /api/v1/audit (journal)
│   ├── services/
│   │   └── promotion_service.py  moteur de promotion (individuelle + masse)
│   ├── web/console_page.py console HTML (liste clients + boutons)
│   └── data/platform.db    DB plateforme SQLite (générée au boot)
├── shared/                 code partagé landing + admin
│   ├── auth/               (à implémenter) session cookie + 2FA superadmin
│   ├── models/client.py    Pydantic (Client, PromotionResult, ...)
│   └── db/
│       ├── schema.py       migrations + init platform.db
│       └── database.py     get_platform_db, log_audit, list_active_clients
├── provisioning/
│   ├── promote_client.sh   déploiement + healthcheck + rollback auto
│   ├── provision_client.sh (à écrire) provisionne une nouvelle instance
│   └── templates/          systemd .service + nginx vhost (à écrire)
├── seeds/starter_kits/     imprimerie.json, usinage.json, plasturgie.json...
└── docs/
    ├── incidents/          postmortems
    ├── archives/           anciennes docs
    └── email-setup.md      (à écrire) guide DNS pour clients
```

## Logique de promotion

Deux types de promotion, tous deux passent par `admin/services/promotion_service.py` :

- **Promotion individuelle** (`POST /api/v1/promotion/client/{id}`) : promeut
  un client vers un `git_ref`. **Pose une épingle automatiquement**
  (`pin_after=True` par défaut). Le client est ensuite protégé des
  promotions de masse. Passer `pin_after=false` si on veut juste synchroniser
  sans sortir le client de la flotte.
- **Promotion de masse** (`POST /api/v1/promotion/all`) : promeut TOUS les
  clients **actifs ET non-épinglés**. Les épinglés sont volontairement
  ignorés (retournés dans `skipped_pinned`). Les suspendus aussi
  (`skipped_suspended`).
- **Détacher l'épingle** (`POST /api/v1/promotion/client/{id}/unpin`) :
  remet le client dans la flotte pour les promotions de masse suivantes.

Toutes les actions sont tracées dans `audit_log` (colonnes `before_json` /
`after_json` — RGPD-friendly).

## Déploiement (référence — non-cassant pour SIFA existant)

Sur le VPS :
- `mysifa` (existant, prod SIFA, port 8000) : inchangé, reste à `www.mysifa.com`.
- `mysifa-v1` (existant, staging SIFA, port 8002) : inchangé.
- `kernse-landing-v2` (nouveau, port 8101) : `www.kernse.fr`.
- `kernse-admin-v2` (nouveau, port 8102) : `admin.kernse.fr` (accès IP allowlist recommandé).
- `kernse-landing-v1` (nouveau, port 8103) : `v1.kernse.fr` (bandeau rouge).
- `kernse-admin-v1` (nouveau, port 8104) : `admin-v1.kernse.fr`.
- Instances clients : `<slug>.kernse.fr`, ports 8200+, une DB SQLite chacune.

Les unit files systemd et vhosts nginx seront ajoutés dans
`provisioning/templates/` au fur et à mesure.

## Nettoyage

Les dossiers `app_OLD_DELETE_ME/`, `scripts_OLD_DELETE_ME/`,
`static_OLD_DELETE_ME/` sont des reliquats de la première structure
non-monolithique. Ils sont vides (juste un `.gitkeep`) et doivent être
supprimés depuis PowerShell (`Remove-Item -Recurse -Force`) — le sandbox
Linux n'a pas les droits pour les enlever.

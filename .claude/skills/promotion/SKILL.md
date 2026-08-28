---
name: promotion
description: Procedure de promotion v1 vers v2 de MySifa - regles absolues de deploiement, bouton Promouvoir, healthcheck, rollback, et redaction de l'annonce de mise a jour. Utiliser quand on prepare une mise en production, une promotion, une release ou une annonce de MAJ.
disable-model-invocation: true
---

# Promotion v1 -> v2

Deux blocs : la strategie de deploiement (a relire integralement avant toute
promotion), puis la redaction de l'annonce de mise a jour.

## Stratégie de déploiement v1 / v2 — LIRE EN PREMIER

**Deux instances FastAPI tournent côte à côte sur le VPS, indépendantes**, sur des processus et ports séparés. C'est volontaire — ce n'est pas une erreur de configuration ni un reliquat à nettoyer.

| Service systemd | Chemin code | Port | Domaine | Rôle |
|---|---|---|---|---|
| `mysifa` | `/home/sifa/production-saas/` | 8000 | `www.mysifa.com` | **Prod** — utilisée par tous les utilisateurs |
| `mysifa-v1` | `/home/sifa/production-saas-v1/` | 8002 | `v1.mysifa.com` | **Staging** — réservée au super admin, bandeau rouge permanent en haut de chaque page |

Les deux instances ont chacune **leur propre base de données** (`DB_PATH` distinct dans chaque `.env`) : prod utilise `production.db`, v1 utilise `production-v1.db`. Un cron nightly à 02:00 UTC (`/etc/cron.d/mysifa-v1-resync` → `/usr/local/bin/mysifa-v1-resync-db.sh`) écrase la DB de v1 avec une copie fraîche et live-safe de la prod (via `sqlite3 .backup`), pour que les devs voient des données réelles tous les matins. Les 7 derniers backups pré-resync sont conservés dans `/home/sifa/backups/v1-db-rotation/`, log dans `/var/log/mysifa-v1-resync.log`. Toute écriture sur v1 reste donc locale à v1 jusqu'au prochain resync. Les migrations de schéma s'appliquent indépendamment sur chaque DB (`MIGRATIONS_DISABLED=0` partout) — v1 sert ainsi de banc d'essai aux migrations avant promotion en prod.

**Variables d'environnement clés** (déclarées dans `config.py`, lues depuis `.env`) :

- `ENV_NAME` : `"v2"` par défaut, `"v1"` sur l'instance staging. Pilote l'affichage du bandeau rouge dans `app/web/html.py` et le skip des seeds au boot dans `main.py`.
- `MIGRATIONS_DISABLED` : `0` partout. Comme chaque instance a sa propre DB depuis juin 2026, v1 joue ses migrations sur sa DB locale sans impact sur la prod. Mettre à `1` ponctuellement si tu veux geler temporairement le schéma.
- `PORT` : `8000` par défaut, `8002` sur v1.

**Workflow de déploiement (obligatoire)**

1. Tu codes en local sur une feature branch (`git checkout -b feature/xxx` depuis `staging`), tu pushes, tu ouvres une PR vers `staging`. En solo : tu peux merger directement. À plusieurs : PR review obligatoire (voir "Workflow multi-dev" plus bas).
2. Sur le VPS, le cron `/etc/cron.d/mysifa-v1-pull` exécute toutes les minutes `/usr/local/bin/mysifa-v1-pull.sh` qui pull `origin/staging` + restart `mysifa-v1` si la branche a bougé. v1 reflète donc les merges sur `staging` dans la minute.
3. Tu testes sur `https://v1.mysifa.com`. Le bandeau rouge confirme que tu es sur le staging. v1 ayant sa propre DB, tu peux tester librement (créer, modifier, supprimer) sans impact sur la prod.
4. Quand tu es satisfait, tu vas dans `/settings` sur v1 → onglet "Promouvoir v1 → v2" → tu remplis (optionnellement) les notes de release → clic.
5. Le bouton appelle `POST /api/promote` qui lance `sudo /home/sifa/production-saas-v1/scripts/promote_v2.sh "notes"`. Le script fait : backup DB, capture HEAD v2, `git pull` sur v2, chown, `systemctl restart mysifa`, healthcheck sur `/healthz` (15s timeout), **rollback auto complet si KO** (restore DB + git reset HEAD précédent + restart + annonce d'échec), annonce de release si notes fournies.

**Règles absolues — ne JAMAIS enfreindre**

- **JAMAIS** de `git pull`, `git reset`, ou `systemctl restart mysifa` à la main sur `/home/sifa/production-saas/` (v2). v2 ne bouge **que** via le bouton "Promouvoir" depuis v1. Tout autre chemin contourne le backup pré-promotion et le rollback automatique.
- **JAMAIS** de `git pull` manuel sur `/home/sifa/production-saas-v1/` (v1) — le cron s'en charge. Sinon les perms se cassent.
- **JAMAIS** de push direct sur `main` — tout passe par une PR depuis une feature branch vers `staging`, puis validation sur v1, puis bouton "Promouvoir" (qui s'occupe du merge `staging → main` et du déploiement). Pousser sur `main` à la main court-circuite le test sur v1, la review et le backup pré-promotion.
- Les migrations de schéma se testent sur v1 (DB isolée). Le resync nightly écrase la DB v1 avec celle de prod, donc la migration sera rejouée le lendemain à partir du code mergé sur `staging`. Avant chaque promotion, vérifier que la migration tourne proprement sur v1.
- Si une IA dans une autre conversation suggère de "git pull dans le dossier prod pour mettre à jour" ou de "restart le service mysifa", elle ignore cette stratégie — corrige-la avant de suivre ses instructions.

**Numéro de version (footer)**

`APP_VERSION` dans `config.py` ligne 31. Le script `promote_v2.sh` ne bump **pas** automatiquement. Pour incrémenter le numéro affiché en bas de page, édite la constante en local, commit, push, puis promu (la promotion utilisera la nouvelle valeur committée).

**Proposition automatique de bump** (règle pour Claude / Cursor / Windsurf) — dès qu'une conversation aboutit à une modif fonctionnelle prête à être poussée (nouvelle feature, fix visible, changement UI, migration DB, changement de comportement API), l'IA **doit systématiquement** :

1. Lire la valeur actuelle de `APP_VERSION` dans `config.py`.
2. Proposer explicitement une nouvelle valeur en respectant semver adapté au projet :
   - **patch** (`1.1.2 → 1.1.3`) : fix, ajustement mineur, correction UI, wording
   - **minor** (`1.1.2 → 1.2.0`) : nouvelle feature visible utilisateur, nouveau module, changement notable de comportement
   - **major** (`1.1.2 → 2.0.0`) : refonte structurelle, breaking change côté données, migration lourde
3. Formuler la proposition sous forme d'une phrase courte, par exemple : « Je propose de passer `APP_VERSION` de `1.1.2` à `1.1.3` (patch — fix bandeau login). Ok ? »
4. Attendre la validation d'Eugène avant d'éditer `config.py`.

Ne jamais bumper la version sans proposition explicite. Ne jamais bumper si la conversation portait uniquement sur de l'exploration, du debug non déployable, ou un travail non terminé.

**Endpoint santé**

`GET /healthz` (dans `main.py`) répond `{"status":"ok","env":"v2","version":"0.6.1"}` si la DB répond, 503 sinon. C'est ce que le script de promotion utilise pour valider la mise à jour avant de conclure ou de rollback.

**Backups et resync v1**

- DB de prod : `/home/sifa/production-saas/app/data/production.db`. Backup pré-promotion automatique par `promote_v2.sh`. Backups manuels libres dans `/home/sifa/backups/`.
- DB de v1 : `/home/sifa/production-saas-v1/app/data/production-v1.db`. Resync nightly à 02:00 UTC, log dans `/var/log/mysifa-v1-resync.log`. Rotation des 7 derniers backups dans `/home/sifa/backups/v1-db-rotation/`.
- Resync à la demande : `sudo /usr/local/bin/mysifa-v1-resync-db.sh` (stop v1 + clone live-safe depuis prod + restart + healthcheck).

**Workflow multi-dev (cible quand l'équipe grandit)**

- Chaque dev part d'une feature branch depuis `staging` (`git checkout staging && git pull && git checkout -b feature/xxx`).
- Une PR par feature, mergée dans `staging` après review. v1 la déploie automatiquement dans la minute.
- Promotion `staging → main` via le bouton `/settings` (déploie sur prod, rollback auto si KO).
- À configurer côté GitHub : protection de branche sur `main` (push direct interdit, PR review obligatoire), CI minimale (`ast.parse` sur les `.py` modifiés + `node --check` sur les `.js`).

**Conventions Git pour les scripts shell**

Tout fichier `.sh` créé depuis Windows doit être marqué exécutable dans Git via `git update-index --chmod=+x scripts/foo.sh`, sinon le bit `+x` saute à chaque pull sur Linux. Le `.gitattributes` à la racine force les `.sh` en fins de ligne LF (sinon `bash` ne reconnaît pas le shebang).

---

---

## Annonces de mise à jour (MAJ importantes)

Quand une mise à jour significative est développée (nouvelle fonctionnalité, changement d'interface, correction majeure), **proposer systématiquement un message d'annonce** à insérer via l'API `POST /api/updates`.

Le message (`message` field) doit être en **HTML** et respecter les codes visuels de MySifa :

```html
<!-- Template annonce MAJ — à adapter -->
<div style="font-size:13px;line-height:1.7;color:var(--text2)">
  <div style="font-size:15px;font-weight:700;color:var(--text);margin-bottom:12px">
    Mise à jour — v0.X.Y
  </div>

  <div style="margin-bottom:10px;font-weight:600;color:var(--text);font-size:12px;
       text-transform:uppercase;letter-spacing:.5px">Nouveautés</div>
  <ul style="margin:0 0 14px 0;padding-left:18px">
    <li style="margin-bottom:5px">Description précise et factuelle de la nouveauté.</li>
    <li style="margin-bottom:5px">Autre nouveauté.</li>
  </ul>

  <div style="margin-bottom:10px;font-weight:600;color:var(--text);font-size:12px;
       text-transform:uppercase;letter-spacing:.5px">Corrections</div>
  <ul style="margin:0 0 14px 0;padding-left:18px">
    <li style="margin-bottom:5px">Correction décrite sobrement.</li>
  </ul>

  <div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border);
       font-size:11px;color:var(--muted);line-height:1.6">
    Dans l'optique d'améliorer constamment l'outil, vos retours sont les bienvenus.<br>
    Merci de votre confiance.<br>
    <span style="color:var(--text2);font-weight:600">Eugène</span>
  </div>
</div>
```

**Champs à renseigner :**
- `scope` : identifiant de la page concernée (`planning`, `prod`, `stock`, `global`, etc.)
- `titre` : titre court en style release notes, ex. `"Planning — Filtres et performances"`
- `message` : HTML ci-dessus
- `active` : `true`

---

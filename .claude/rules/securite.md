---
paths:
  - "app/routers/auth*.py"
  - "app/core/**/*.py"
  - "app/routers/settings.py"
  - "config.py"
  - ".env.example"
---
## Sécurité, secrets & audit trail

Ces règles s'appliquent dès le premier client Kernse payé, mais elles sont
utilisables tout de suite pour SIFA (aucune régression).

**Secrets — jamais dans le repo git**

- Toute clé (Stripe, Microsoft Graph client secret, Anthropic, DeepL, SMTP,
  etc.) vit dans `.env` sur le VPS. `.gitignore` bloque `.env`.
- `.env.example` (versionné) liste toutes les variables attendues avec des
  valeurs placeholder — jamais de vraie clé, jamais de vraie URL de webhook.
- Rotation semestrielle des secrets sensibles, documentée dans
  `docs/archives/rotations-YYYY.md` (date, portée, qui).
- Les secrets clients Kernse (clés Stripe par instance, si un jour on les
  isole) sont provisionnés par un script hors-repo, jamais tapés à la main.

**Anti-fuite — règles absolues**

- Ne jamais logger un token, un mot de passe (même hashé), une session, une
  clé API, un numéro de carte. Filtrer avant `logger.info`.
- Les endpoints ne renvoient jamais un secret dans la réponse, y compris à
  la création (ex. pas de réponse « voici la clé qu'on vient de générer,
  gardez-la précieusement » — on force un `GET /me/api-keys` séparé qui
  affiche les 4 derniers caractères seulement).
- Les erreurs d'authentification ne révèlent pas si un email existe :
  message générique « identifiants invalides », même sur un mauvais mot de
  passe pour un compte existant.
- Les uploads ne servent jamais de contenu exécutable (`text/html`,
  `application/javascript`) — servis avec `Content-Disposition: attachment`.

**Audit trail — table `audit_log`**

Obligatoire dès qu'une donnée sensible est modifiée : utilisateurs
(création, changement de rôle, désactivation), rôles/permissions,
paramètres plateforme, paramètres entreprise, factures/paiements, données
personnelles RGPD, suspensions/résiliations d'instance.

- Colonnes : `id`, `at` (UTC ISO), `user_id`, `user_email`, `ip`, `action`
  (verbe court), `entity_type`, `entity_id`, `before` (JSON), `after`
  (JSON).
- Rétention 12 mois minimum, 24 mois pour la facturation (obligation
  comptable).
- Consultable via la console plateforme (filtres : par client, par
  utilisateur, par action, par date).
- Écriture dans le même transaction que la modif — jamais d'audit
  « best-effort » qu'on peut oublier de committer.

**Auth — durcissement pour clients payants**

- Politique mot de passe : 12 caractères min, complexité, blocklist des
  mots de passe compromis (haveibeenpwned k-anonymity).
- 2FA obligatoire pour les rôles `superadmin` et `direction` dès qu'il y a
  des clients payants sur la plateforme (délai de grâce : 30 jours après
  activation d'une organisation).
- SSO Azure AD (OIDC) implémentable pour les clients qui le demandent —
  le maquettage existe déjà côté login.

---

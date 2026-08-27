---
paths:
  - "app/routers/**/*.py"
  - "main.py"
---
## API versioning & compat descendante

Aujourd'hui (SIFA seul) : les endpoints sous `/api/*` peuvent bouger
librement — un seul consommateur, contrôlable. Cette liberté prend fin
**au premier client payé Kernse**.

**Règle Kernse — à appliquer dès qu'on commence à écrire des routes
publiques pour Kernse**

- Toute nouvelle route publique (utilisée par un front qu'on ne contrôle
  pas totalement, un partenaire, un intégrateur, un webhook Stripe) est
  préfixée `/api/v1/`. Les routes internes (`/healthz`, `/platform/admin/*`,
  `/api/internal/*`) restent hors versioning.
- Chaque route publique a un schéma Pydantic explicite en entrée et en
  sortie. Ne jamais renvoyer un objet DB brut avec tous ses champs. Ne
  jamais ajouter un champ **obligatoire** à un endpoint existant sans
  bump de version.

**Deprecation — 6 mois minimum**

Avant de retirer une route `/api/v1/` :

1. Ajouter `/api/v2/xxx` avec le nouveau contrat.
2. Marquer `/api/v1/xxx` comme dépréciée : header HTTP `Deprecation: true`,
   `Sunset: <date>`, plus une entrée dans `docs/api/deprecations.md`.
3. Attendre 6 mois minimum entre la publication de v2 et le retrait de
   v1.
4. Prévenir chaque client par email : une fois au démarrage de la
   période de déprecation, une fois 1 mois avant le retrait.

**Compatibilité côté client**

- Les instances Kernse supportent les 2 dernières versions majeures
  d'API en parallèle. La console plateforme affiche par instance quelle
  version le front consomme (`X-Api-Version` request header ou
  détection au niveau du reverse proxy).
- Le front interne (portail Kernse) migre vers la nouvelle version
  d'API dans le mois qui suit sa publication — pas en même temps qu'un
  autre chantier.

---

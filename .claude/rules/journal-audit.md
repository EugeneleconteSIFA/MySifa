---
paths:
  - "app/core/audit_taxonomy.py"
  - "app/core/audit_middleware.py"
  - "app/services/audit_service.py"
  - "app/routers/**/*.py"
---
## Journal des actions (Paramètres › Journal)

**Deux chemins alimentent `audit_logs`, et ils ne se marchent pas dessus.**

1. L'appel explicite `log_action(...)` dans un router. C'est le meilleur : il
   nomme l'objet métier (« Dossier REF-4521 · Cohésio 1 ») et décrit l'avant /
   après. À poser dès qu'on sait écrire mieux qu'un chemin d'URL.
2. Le middleware `app/core/audit_middleware.py`, qui journalise
   automatiquement **toute écriture aboutie** (POST / PUT / PATCH / DELETE) et
   se tait dès qu'un appel explicite a déjà écrit pour la même requête.

Conséquence pratique : **il n'y a plus rien à faire pour qu'un nouvel endpoint
entre dans le journal.** Écrire un `log_action` reste un progrès (l'objet
devient parlant), jamais une obligation.

**Le dédoublonnage passe par un compteur de contexte** (`ouvrir_contexte()` /
`_marquer_appel()` dans `audit_service`). Il tient parce que le middleware est
un middleware ASGI pur : un `BaseHTTPMiddleware` exécuterait le handler dans
une autre tâche et le compteur ne remonterait pas. Ne pas le convertir.

**Ce qui n'entre pas dans le journal, volontairement :**

- les lectures (GET) — le journal trace ce qui change, pas ce qu'on regarde ;
- les 401 : une session expirée n'est pas un événement d'audit. Les 403, si —
  un refus de permission est précisément ce qu'on vient y chercher ;
- le bruit machine listé dans `SKIP_PREFIXES` (heartbeats, agent MyPrint,
  relevés de fluidité, abonnements push) ;
- le **contenu** des requêtes des modules de `BODY_BLIND_MODULES` (discussions,
  messagerie, coffre, coffre RH, paie). L'action est tracée, jamais la donnée ;
- toute valeur dont la clé ressemble à un mot de passe, un jeton ou une clé —
  filtrée partout par `redact()`.

**Ajouter un module ou une action se fait dans `app/core/audit_taxonomy.py`,
nulle part ailleurs.** La page Paramètres ne connaît plus aucune liste en dur :
ses deux filtres se construisent depuis `/api/settings/audit/facets`, qui croise
les valeurs réellement présentes en base avec les libellés de la taxonomie. Un
module apparaît donc dans le filtre le jour de sa première action, sans qu'on
touche au front.

Une clé de module déjà partie en production **ne se renomme pas** : l'historique
serait rangé sous un nom que plus personne ne filtre. On ajoute, on ne rebaptise
pas.

**Le test `tests/test_audit_journal.py` verrouille l'essentiel** : aucune route
d'écriture du dépôt ne tombe dans le module fourre-tout `autre`, chaque module
et chaque action ont un libellé français, et un endpoint qui journalise
lui-même n'écrit pas deux lignes. Il balaie les décorateurs des routers — donc
un nouveau router sans entrée dans `PATH_MODULES` le fait échouer tout de suite.

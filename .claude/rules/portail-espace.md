---
paths:
  - "app/routers/portail_espace.py"
  - "app/services/portail_espace.py"
  - "app/web/portail_espace_page.py"
  - "app/routers/*portail*.py"
  - "app/web/*portail*.py"
  - "app/routers/qualite_formulaires.py"
  - "app/services/qualite_formulaires*.py"
---
## Espace SIFA — le portail unique des destinataires externes

Décision du 20/10/2026 : **tout ce qu'un tiers reçoit de SIFA** (formulaire,
appel d'offres, demande de devis, questionnaire, document à signer…) **se
retrouve au même endroit : son Espace SIFA**, `/portail/{jeton}`.

- **Un Espace par adresse email** (`portail_espaces`, en minuscules). C'est la
  seule clé commune à tous les modules : un fournisseur, un client, un
  transporteur ou une personne du personnel y sont des adresses comme les autres.
- **Lien personnel seul, sans code** (arbitrage d'Eugène, même niveau que le
  portail transporteurs). Le pied de page et les emails disent que le lien est
  personnel.
- **Marque SIFA**, jamais MySifa (`APP_ORG_NAME`, règle « Marque côté
  transporteur ») : `email_mysifa_layout(..., marque=APP_ORG_NAME)`.
- Le jeton se lit par `portail_espace.lire_par_token`, sous la limite par IP
  des portails (`_check_rate_limit` de `expe_portail.py`). Une visite d'un
  utilisateur MySifa connecté (`_visiteur_interne`) ne marque ni accès ni
  ouverture.

### Ce qui y est aujourd'hui

| Module | Dans l'Espace | État |
|---|---|---|
| Formulaires (MyQualité) | natif : rempli dans l'Espace | fait (20/10/2026) |
| Appels d'offres MyAO | carte → `/portail/ao/{token}` | à intégrer |
| Devis transport + taxe carburant | carte → `/portail/expe/{token}` | à intégrer |
| Questionnaire EUDR | carte → `/portail/eudr/{token}` | à intégrer |

Les cartes sont lues par `portail_espace.contenu()`, **un `try` par module** :
une table absente retire sa carte, jamais l'Espace. Les anciens liens envoyés
par chaque module restent valables.

### Ajouter un nouvel envoi externe

1. Pas de nouvelle page `/portail/<module>/{jeton}` : l'élément vit dans
   l'Espace. Créer l'Espace du destinataire par `portail_espace.espace_pour(conn,
   email, nom)` au moment de l'envoi.
2. Ajouter un lecteur dans `contenu()` qui rend des éléments
   `{module, titre, detail, echeance, envoye_le, a_traiter, statut, …}` —
   `a_traiter` décide de la section « À traiter » / « Déjà traité ».
3. Le lien de l'email mène à l'Espace, avec un paramètre qui ouvre l'élément
   (`?formulaire=<id>` pour un formulaire).
4. Un élément natif se rend dans `portail_espace_page.py` ; pour un
   questionnaire, réutiliser le moteur `static/mysifa_formulaire.js` plutôt
   qu'écrire un formulaire HTML de plus.

Intégrer MyAO, les devis et EUDR à l'Espace (pages natives au lieu des cartes)
reste à faire, module par module.

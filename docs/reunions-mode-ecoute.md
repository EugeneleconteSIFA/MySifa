# Réunions — espace commun et mode écoute

Spec de travail, novembre 2026. Lots 1 à 3 codés le 2026-11-05, branche
`feature/reunions-ecoute` — pas encore testés sur v1 (voir « Implémentation »
en fin de document).

## Objectif

1. Sortir les réunions du seul périmètre production : un espace « Réunions »
   commun (direction, commercial, qualité, RH…), dont les points de production
   deviennent un type parmi d'autres.
2. Un **mode écoute** : MySifa enregistre la réunion, la transcrit sur le VPS,
   et propose un brief (notes, décisions, actions, participants) qu'un humain
   valide avant enregistrement.
3. Un accès en un clic, y compris depuis un téléphone posé sur la table.

## Décisions validées

| Sujet | Décision |
|---|---|
| Structure | Espace commun avec des types de réunion — pas de module séparé |
| Transcription | L'audio reste sur le VPS : transcription locale, aucun prestataire |
| Écriture du brief | Toujours une proposition, jamais un enregistrement automatique |

## Structuration du brief — retenu : réutiliser la brique de l'éditeur PDF

L'audio reste sur le VPS ; le **texte** de la transcription part chez
Anthropic pour être structuré, comme le font déjà les documents de
MyTools › Éditeur PDF (`app/services/pdf_ia.py`). Retenu par Eugène le
2026-11-05 en s'appuyant sur ce précédent.

`reunion_ecoute_ia.py` reprend le patron de `pdf_ia.py` à l'identique, au
lieu d'en inventer un :

- `_client()` sur `ANTHROPIC_API_KEY`, erreur affichable si absente ;
- un `_appel()` avec `output_config.format` (schéma JSON du brief), repli
  serveur sur refus (`fallbacks: "default"`), contrôle de `stop_reason`
  (`refusal`, `max_tokens`) ;
- `ia_usage.noter(reponse, "reunion")` pour le suivi de consommation ;
- modèle dans `config.py` : `REUNION_IA_MODELE = os.getenv(..., PDF_IA_MODELE)`.

Seule différence : le contenu envoyé est un bloc texte, pas un document PDF.
On ne fabrique pas un PDF juste pour passer par `pdf_ia`. Si les deux services
finissent par dupliquer `_client()` / `_appel()`, factoriser dans un
`ia_claude.py` commun au lot 3.

En option : un drapeau `structuration_ia` sur le type de réunion, pour
désactiver la structuration sur Direction ou RH (transcription brute seule).

## Modèle de données

Toutes les évolutions passent par des migrations fichier
(`app/core/migrations/`). La logique dépend d'attributs du type, jamais de son
nom : pas de `if type == "Production"`.

### `reunion_types` — référentiel, éditable dans Paramètres

| Colonne | Rôle |
|---|---|
| `id`, `libelle`, `ordre`, `actif` | Base du référentiel |
| `chiffres_prod` | 1 = machine, période et chiffres de prod recalculés (comportement actuel) |
| `visibilite_defaut` | `participants`, `roles` ou `tous` |
| `roles_defaut` | Liste de rôles quand `visibilite_defaut = roles` |
| `structuration_ia` | Si l'option C est retenue |

Seed (`INSERT OR IGNORE`) : Production (`chiffres_prod = 1`, `tous`),
Direction (`participants`), Commercial, Qualité, RH (`participants`).

### `reunions` — colonnes ajoutées

- `type_id` → toutes les réunions existantes reprises sur le type Production.
- `visibilite`, `roles_visibles` — initialisées depuis le type, modifiables.
- `decisions TEXT NOT NULL DEFAULT ''` — séparées des notes pour être
  retrouvables.
- `machine`, `date_debut`, `date_fin` restent ; ils ne s'affichent que si le
  type a `chiffres_prod = 1`. Pour les autres types, `date_debut = date_fin`
  = jour de la réunion.

### `reunion_ecoutes` — un enregistrement

| Colonne | Rôle |
|---|---|
| `id`, `reunion_id` (nullable tant que la réunion n'est pas rattachée) | |
| `statut` | `enregistrement` → `a_transcrire` → `transcription` → `a_structurer` → `proposition` → `validee` ; ou `erreur`, `abandonnee` |
| `demarre_le`, `demarre_par`, `arrete_le`, `duree_s` | |
| `nb_morceaux` | Contrôle de complétude à l'arrêt |
| `transcription TEXT` | Purgée à `purge_le` |
| `proposition TEXT` | JSON du brief proposé |
| `purge_le` | Date de purge de la transcription (rétention réglable) |
| `erreur` | Message factuel si échec |

L'audio n'est jamais en base : fichiers dans `data/ecoute/<id>/`, supprimés
dès la transcription terminée. `data/ecoute/` dans `.gitignore`.

### Actions

`reunion_actions` reste la liste unique (déjà découplée des réunions par
`reunion_actions_sans_reunion`). L'onglet Actions de MyProd filtre sur le type
Production ; l'espace Réunions affiche toutes les actions visibles par
l'utilisateur.

## Parcours

1. **Démarrer.** Bouton « Écouter » dans la barre du haut, sur toutes les
   pages. Un clic : demande d'accès au micro, puis l'enregistrement démarre.
   Aucune saisie préalable. Bandeau fixe « Écoute en cours · 12:34 · Arrêter ».
2. **Pendant.** Le bandeau suit l'utilisateur de page en page. Sur téléphone :
   écran maintenu allumé (Wake Lock) et message « Ne verrouillez pas
   l'écran », iOS coupant le micro au verrouillage.
3. **Arrêter.** Une modal courte : type (pré-rempli au dernier utilisé),
   titre facultatif, rattacher à une réunion existante ou en créer une.
   Message : « Transcription en cours — le brief sera prêt dans ~N min. »
4. **Notification** quand la proposition est prête (messagerie interne).
5. **Valider.** Écran en deux colonnes : proposition à gauche (notes,
   décisions, actions avec responsable et échéance, participants
   rapprochés des comptes MySifa), transcription à droite pour vérifier.
   Chaque action se garde, se corrige ou se retire. « Valider le brief »
   écrit dans `reunions` et `reunion_actions`.
6. **Envoyer** (facultatif) : le brief validé par email aux participants
   internes.

## Chaîne technique

### Capture (navigateur)

- `MediaRecorder` en Opus/WebM, morceaux de 30 s numérotés.
- `POST /api/reunions/ecoutes/{id}/morceaux/{n}` ; en cas de coupure réseau,
  les morceaux attendent dans IndexedDB et repartent dans l'ordre.
- À l'arrêt, le serveur compare `nb_morceaux` reçu et annoncé ; un manque
  est signalé sur l'écran de validation, pas masqué.

### Transcription (VPS)

- **Processus séparé**, pas dans le worker FastAPI : un service systemd
  `mysifa-transcription` en `nice 19`, qui dépile les écoutes
  `a_transcrire` une par une. Une saisie opérateur ne doit jamais ralentir
  à cause d'une réunion.
- prod et v1 partagent le même CPU : **un seul job de transcription à la fois
  sur le VPS** (verrou fichier commun aux deux instances).
- faster-whisper, quantification int8, modèle choisi par
  `TRANSCRIPTION_MODELE` dans `config.py` (`os.getenv`). ffmpeg assemble les
  morceaux. Langue forcée à `fr`.
- Traitement **différé**, pas en direct : le brief arrive après la réunion.

### Structuration (lot 3)

- Service `app/services/reunion_ecoute_ia.py`, sur le patron de `pdf_ia.py`
  (voir plus haut), sortie structurée au schéma du brief.
- Contexte fourni : liste des utilisateurs actifs (pour rapprocher les noms
  prononcés), références dossier citées résolues en base.
- Les responsables sont **déduits des noms prononcés** : la transcription ne
  sait pas qui parle. D'où la validation humaine obligatoire.

## Dimensionnement — à mesurer avant de coder (lot 0)

Les specs du VPS (cœurs, RAM) ne sont pas dans le dépôt. Lot 0 : script
`tools/bench_transcription.py` lancé sur le VPS avec 10 min d'audio de réunion
réelle, pour 2 ou 3 modèles. Mesures : durée de transcription, CPU, RAM pic,
qualité lue à l'œil sur le vocabulaire SIFA (noms de machines, clients).

Critère d'acceptation proposé : **une réunion d'1 h transcrite en moins
d'1 h 30**, sans que les temps de réponse de MySifa ne bougent pendant ce
temps. Si aucun modèle n'y arrive avec une qualité correcte, il faudra un VPS
plus costaud ou revoir la décision sur la transcription — à savoir avant le
lot 2, pas après.

### Résultats du 2026-11-05 (audio synthétique, 10 min)

VPS : 2 cœurs, 7,8 Go de RAM. Bench à 1 thread, beam 5, int8, VAD, nice 19.

| Modèle | Facteur | 1 h de réunion | RAM pic | `/healthz` méd. / max |
|---|---|---|---|---|
| small | 0,70 | 42 min | 1,3 Go | 18 / 269 ms |
| medium | 1,44 | 1 h 26 | 3,1 Go | 18 / 326 ms |
| large-v3-turbo | 1,04 | 1 h 02 | 1,7 Go | 19 / 356 ms |

Référence au repos : 16 / 46 ms (un premier passage avait relevé 38 / 419 ms).

- Les trois modèles tiennent l'objectif de vitesse sur un seul cœur.
- La médiane de `/healthz` ne bouge pas. Les pointes montent à environ 300 ms,
  du même ordre que celles déjà relevées au repos.
- `large-v3-turbo` est le candidat par défaut : rapide, avec une RAM
  raisonnable. `medium` est plus lent et plus lourd, sans raison de le
  préférer.
- **La qualité ne peut pas se juger sur cet audio.** Les voix de synthèse
  macOS (Eddy, Flo, Jacques) sont trop artificielles. Les trois modèles se
  trompent aux mêmes endroits : « mercredi matin » donne « McCready Martin »
  partout, la référence dossier est illisible partout, et des mots anglais
  apparaissent alors que la langue est forcée en français. Quand l'erreur est
  la même quel que soit le modèle, c'est l'audio qui est en cause, pas le
  modèle. Turbo restitue quand même les phrases simples à l'identique
  (expédition, récapitulatif final).
- Prochain passage : 10 min de vraie voix enregistrée au téléphone, avec
  turbo et small seulement.

## Visibilité

- Une réunion est visible par : son créateur, ses participants, les rôles
  listés si `visibilite = roles`, tout le monde si `tous`.
- Le filtre s'applique côté serveur à **toutes** les routes : liste,
  détail, recherche, actions, widget. Jamais uniquement dans le JS.
- `superadmin` voit tout (cohérent avec l'existant).

## Garde-fous

- Bandeau visible pendant toute l'écoute ; arrêt possible à tout moment.
- Les participants sont informés de l'enregistrement (rappel affiché au
  démarrage : « Prévenez les participants que la réunion est enregistrée. »).
- Audio supprimé dès la transcription terminée, y compris en cas d'erreur
  après 24 h.
- Transcription purgée à `purge_le` (rétention réglable dans Paramètres,
  défaut 30 jours). Seul le brief validé reste.
- Journal d'audit : démarrage, arrêt, validation, suppression, changement de
  visibilité.

## Lots

| Lot | Contenu | Livrable testable sur v1 |
|---|---|---|
| 0 | Bench transcription sur le VPS | Tableau modèle / durée / qualité |
| 1 | `reunion_types`, visibilité, `decisions`, espace Réunions commun, CRUD types dans Paramètres | Créer une réunion Direction visible des seuls participants |
| 2 | Bouton Écouter, capture, worker de transcription, écran transcription | Enregistrer 5 min, lire la transcription |
| 3 | Structuration Claude, écran de validation | Brief proposé, validé, actions créées |
| 4 | Recherche plein texte, widget d'accueil, envoi email | Retrouver une décision par mot-clé |

Le lot 1 a de la valeur seul, même si l'écoute ne voit jamais le jour.

## Questions ouvertes

- Drapeau `structuration_ia` par type : utile, ou structuration partout ?
- Rétention de la transcription : 30 jours par défaut, ou moins ?
- Nom dans la navigation : « Réunions » remplace « Points de production » ;
  la route `/reunions` ne change pas.

## Implémentation (2026-11-05)

Ce qui a changé par rapport à la spec ci-dessus, et pourquoi :

- **Enregistrement sur sa propre page** (`/reunions/ecoute`) et non dans un
  bandeau qui suit l'utilisateur : MySifa recharge la page à chaque changement
  d'appli, et un `MediaRecorder` meurt avec la page. Le bouton flottant
  « Écouter » (toutes les pages, réglable dans Paramètres › Widgets › Boutons
  flottants) ouvre cette page dans un onglet à part sur ordinateur, à la place
  sur téléphone.
- **Pas de service systemd à installer** : `main.py` (`_boucle_ecoutes`, sur
  prod ET v1) lance chaque minute, s'il y a du travail,
  `tools/transcription_worker.py` en sous-processus `nice -n 19`. Le verrou
  `TRANSCRIPTION_VERROU` garantit une seule transcription à la fois sur le VPS.
  Un redémarrage pendant une transcription la fait repartir (trois fois au plus).
- **Pas de ffmpeg** : les morceaux MediaRecorder se concatènent tels quels,
  faster-whisper (PyAV) lit le fichier obtenu.
- **Écoute laissée ouverte** (onglet fermé) : arrêtée d'office après
  `ECOUTE_SILENCE_MIN` sans nouveau morceau, ce qui est arrivé part en
  transcription. Une écoute ne « reprend » pas : un second enregistrement
  ne se recolle pas au premier.
- **Notification** : push au lanceur quand le brief est prêt ou en erreur.
- **Visibilité** : une écoute n'est visible que de qui l'a lancée jusqu'à sa
  validation. Modifier une réunion : créateur, participants, superadmin.
  Changer sa visibilité ou la supprimer : créateur et superadmin.
- **Chiffres de prod** : l'espace Réunions ne les affiche pas encore ; ils
  restent servis par l'API aux rôles de production pour les types
  `chiffres_prod`. L'onglet Actions de MyProd est inchangé, filtré par la
  visibilité des réunions.
- Rétention de la transcription : `ECOUTE_RETENTION_JOURS` (`.env`, 30 jours),
  pas encore réglable dans Paramètres.

| Pièce | Fichier |
|---|---|
| Migrations | `app/core/migrations/2026_11_05_reunions_types_visibilite.py`, `2026_11_05_reunion_ecoutes.py` |
| Types, visibilité | `app/services/reunion.py` (`peut_voir`, `types`, `enregistrer_type`) |
| Cycle d'une écoute | `app/services/reunion_ecoute.py` |
| Transcription | `app/services/transcription.py`, `tools/transcription_worker.py` |
| Brief Claude | `app/services/reunion_ecoute_ia.py` (fonction IA « reunion ») |
| API | `app/routers/reunions.py`, `app/routers/reunions_ecoute.py` |
| Pages | `app/web/reunions_page.py`, `static/mysifa_reunions_espace.js/.css`, `static/mysifa_ecoute.js` |
| Bouton flottant | `static/mysifa_ecoute_fab.js` |
| Paramètres | Communication › Types de réunion, `static/settings_reunion_types.js` |
| Tests | `tests/test_reunion_ecoute.py` |

### Mise en route sur le VPS (avant le premier test sur v1)

1. Installer la transcription dans le venv de chaque instance :
   `venv/bin/pip install -r tools/requirements-transcription.txt`.
   Sans elle, l'application tourne, et une écoute passe en erreur avec ce
   message.
2. Premier passage : le modèle (~1,6 Go) se télécharge dans le cache Hugging
   Face de l'utilisateur du service. Compter quelques minutes de plus.
3. `ANTHROPIC_API_KEY` est déjà dans `.env` (Éditeur PDF) : rien à ajouter.
4. Le micro exige HTTPS : v1.mysifa.com convient, une adresse IP non.

### Reste à faire

- Lot 0 bis : qualité de transcription sur une vraie voix (bench avec un
  enregistrement de téléphone).
- Lot 4 : recherche plein texte, bloc d'accueil (`data-bloc`), envoi du brief
  par email, guide in-app.
- Afficher les chiffres de production d'une réunion `chiffres_prod` dans l'espace.

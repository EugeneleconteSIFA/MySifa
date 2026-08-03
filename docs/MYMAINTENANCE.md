# MyMaintenance — Documentation du module

> **Document de travail — squelette à compléter.**
> Auteur : Eugène Leconte · Créé le : 2026-08-03 · Dernière mise à jour : `[date]` · Version du module documentée : `[vX.Y.Z]`

---

## Comment utiliser ce squelette

- Les blocs en **`> 🖊️`** sont des questions-guides : elles ne doivent pas rester dans le document final, elles sont là pour t'aider à savoir quoi écrire. Supprime-les au fur et à mesure.
- Les `[...]` sont des trous à remplir.
- Les tableaux d'inventaire (tables, endpoints, migrations) sont pré-remplis **uniquement avec les noms extraits du code** — les colonnes de description sont vides, c'est toi qui les remplis.
- Tu n'es pas obligé de suivre l'ordre. Les chapitres 3 (vocabulaire), 12 (données) et 14 (règles métier) sont les plus structurants : les remplir en premier rend le reste beaucoup plus facile.
- Une section que tu ne veux pas traiter : supprime-la plutôt que de la laisser vide. Une doc avec des trous se fait moins confiance qu'une doc plus courte.
- Quand c'est rempli, je le transforme en page HTML autonome navigable (sommaire, recherche, diagrammes rendus).

**Convention de statut** — mets un marqueur en tête de chaque section pendant la rédaction :
`🔴 vide` · `🟡 brouillon` · `🟢 relu`

---

# Sommaire

**Partie 1 — Guide d'utilisation** (lecteurs : opérateurs et admin maintenance SIFA)
1. À quoi sert MyMaintenance
2. Les rôles et les accès
3. Le vocabulaire du module
4. Les écrans
5. Le cycle de vie d'une intervention
6. Gérer les codes maintenance
7. Les modèles récurrents
8. Les alertes opérateur
9. L'historique
10. Cas particuliers et questions fréquentes

**Partie 2 — Référence technique** (lecteurs : toi, futurs devs, agents IA)
11. Architecture
12. Modèle de données
13. Référence API
14. Règles métier non évidentes
15. Permissions
16. Couplages avec les autres modules
17. Frontend

**Partie 3 — Histoire et décisions**
18. Chronologie
19. Décisions structurantes
20. Dette connue et pièges

**Annexes**
- A. Glossaire
- B. Inventaire des migrations
- C. Configuration et variables d'environnement

---
---

# PARTIE 1 — GUIDE D'UTILISATION

---

## 1. À quoi sert MyMaintenance

`[statut]`

> 🖊️ **À écrire :** en 5-10 lignes, sans jargon.
> - Quel problème concret se posait chez SIFA avant ce module ? (papier ? Excel ? rien ?)
> - Qu'est-ce qu'on peut faire aujourd'hui qu'on ne pouvait pas faire avant ?
> - Qu'est-ce que le module ne fait **pas** (périmètre exclu) — c'est souvent la phrase la plus utile du document.

**Le problème**
[...]

**Ce que le module apporte**
[...]

**Ce qui reste hors périmètre**
[...]

---

## 2. Les rôles et les accès

`[statut]`

> 🖊️ **À écrire :** le code distingue deux rôles maintenance — `admin` (rôles admin de l'app) et `operator` (rôle fabrication). Tout autre rôle reçoit un 403.
> - Qui est admin maintenance chez SIFA, concrètement ? Combien de personnes ?
> - Qu'est-ce qu'un opérateur peut faire de son propre chef, et qu'est-ce qui lui est refusé ?
> - Le flag `MAINTENANCE_OPEN_BETA` : à quoi il servait, où il en est aujourd'hui, est-ce qu'on peut le retirer ?

| Rôle dans l'app | Rôle maintenance | Ce qu'il peut faire | Ce qu'il ne peut pas faire |
|---|---|---|---|
| `[rôles admin]` | `admin` | [...] | [...] |
| `[rôle fabrication]` | `operator` | [...] | [...] |
| Autres | *aucun accès* | — | — |

**Le cas particulier de l'opérateur affecté**
> 🖊️ Un opérateur peut gérer certains créneaux sans être admin (il y a une fonction dédiée pour ça dans le code). Décris la règle en langage clair : dans quelles conditions un opérateur peut modifier un créneau ?

[...]

---

## 3. Le vocabulaire du module

`[statut]` — **chapitre pivot, à remplir en premier**

> 🖊️ **À écrire :** une définition courte par terme, telle que tu l'expliquerais à un opérateur qui découvre l'écran. C'est ce chapitre qui rend tout le reste lisible — si un terme est flou ici, il sera flou partout.

| Terme | Définition en une phrase | Détails / pièges |
|---|---|---|
| **Code maintenance** | [...] | [...] |
| **Niveau** (1, 2, 3…) | [...] | [...] |
| **Catégorie** : Contrôles | [...] | [...] |
| **Catégorie** : Suivi | [...] | [...] |
| **Catégorie** : Pièces d'usure | [...] | [...] |
| **Code périodique** | [...] | [...] |
| **Intervalle** | [...] | [...] |
| **Métrage de référence** | [...] | [...] |
| **Code libre** | [...] | [...] |
| **Créneau** (event) | [...] | [...] |
| **Opération** (event_op) | [...] | [...] |
| **Modèle** (template) | [...] | [...] |
| **Alerte** | [...] | [...] |
| **Accusé de réception (ack)** | [...] | [...] |
| **Non-conformité** | [...] | [...] |
| **Calage / Après calage** | [...] | [...] |
| `[autres termes à ajouter]` | [...] | [...] |

> 🖊️ **Question à trancher ici :** quelle est exactement la différence entre un *code libre* et un *code maintenance* ? Le code prévoit de promouvoir un code libre en code réel, de le fusionner, de le rattacher — donc les deux coexistent. Explique le workflow : qui crée quoi, quand, et pourquoi ce mécanisme existe.

[...]

---

## 4. Les écrans

`[statut]`

> 🖊️ **À écrire :** pour chaque écran — à qui il s'adresse, ce qu'on y voit, ce qu'on y fait, les pièges d'usage.
> Les vues identifiées dans le code sont listées ci-dessous. Corrige les noms si l'intitulé affiché diffère.
> Prévois un emplacement de capture d'écran par section (je les intégrerai à l'HTML si tu me les fournis).

### 4.1 Accueil (`maintenance`)
`[capture]`
- **Pour qui :** [...]
- **Ce qu'on y voit :** [...]
- **Ce qu'on y fait :** [...]
- **Filtres disponibles :** [...]
- **Pièges :** [...]

### 4.2 Planning (`planning`)
`[capture]`
- **Pour qui :** [...]
- **Ce qu'on y voit :** [...] *(vue calendrier semaine ?)*
- **Ce qu'on y fait :** [...] *(le code gère le glisser-déposer des créneaux et le regroupement des créneaux simultanés — explique le comportement attendu)*
- **Pièges :** [...] *(que se passe-t-il si on déplace un créneau dans le passé ? un créneau déjà réalisé ?)*

### 4.3 Opérations (`operations`)
`[capture]`
- **Pour qui :** [...]
- **Ce qu'on y voit :** [...]
- **Ce qu'on y fait :** [...]
- **Sous-onglets :** [...]

### 4.4 Contrôles (`controles`)
`[capture]`
- **Pour qui :** [...]
- **En quoi c'est différent de l'écran Opérations :** [...]
- **Sous-onglets :** [...]

### 4.5 Planning personnel opérateur (`op-planning`)
`[capture]`
- **Pour qui :** [...]
- **Ce qu'on y voit :** [...] *(aujourd'hui + 30 jours groupés par date, d'après l'historique git — confirme)*
- **Pièges :** [...]

### 4.6 Mes tâches (`op-tasks`)
`[capture]`
- **Pour qui :** [...]
- **En quoi c'est différent du Planning personnel :** [...]

### 4.7 Page `/my-maintenance`
> 🖊️ Il existe une route `/my-maintenance` distincte de `/maintenance`. À quoi sert-elle ? Est-ce une PWA / un point d'entrée mobile ? Est-elle encore utilisée ?

[...]

---

## 5. Le cycle de vie d'une intervention

`[statut]`

> 🖊️ **À écrire :** le parcours nominal, puis les branches. Décris-le en phrases, je le convertirai en diagramme.
> Les statuts d'opération repérés dans le code : `a_faire`, `termine`, `invalidee`. Confirme s'il en existe d'autres.

**Parcours nominal**
1. [...]
2. [...]
3. [...]

**Les branches**

| Situation | Ce qui se passe | Qui peut le faire | Réversible ? |
|---|---|---|---|
| Opération réalisée | [...] | [...] | [...] |
| Opération non planifiée (créée après coup) | [...] | [...] | [...] |
| Opération invalidée | [...] | [...] | [...] |
| Opération remise à zéro (`reset`) | [...] | [...] | [...] |
| Opération revalidée | [...] | [...] | [...] |
| Créneau supprimé | [...] | [...] | [...] |
| Créneau restauré | [...] | [...] | [...] |
| Créneau supprimé définitivement | [...] | [...] | [...] |

> 🖊️ **Question à trancher :** quelle est la différence de sens entre *invalider* et *supprimer* une opération ? Dans quel cas métier on utilise l'un plutôt que l'autre ? C'est probablement la distinction la moins évidente du module pour un nouvel utilisateur.

[...]

**Ce qui est saisi à la réalisation**
> 🖊️ Le modèle stocke : durée réelle, pièces changées, observations, photos, consignes. Pour chacun : obligatoire ou non, qui le remplit, à quoi ça sert ensuite.

| Champ | Obligatoire ? | Qui le remplit | Usage en aval |
|---|---|---|---|
| Durée réelle | [...] | [...] | [...] |
| Pièces changées | [...] | [...] | [...] |
| Observations | [...] | [...] | [...] |
| Photos | [...] | [...] | [...] |
| Consignes | [...] | [...] | [...] |

---

## 6. Gérer les codes maintenance

`[statut]`

> 🖊️ **À écrire :** le mode d'emploi côté admin.

**Créer un code** — [...]

**Les champs et comment les choisir**

| Champ | Comment le renseigner | Conséquence si mal renseigné |
|---|---|---|
| Code | [...] | [...] |
| Libellé | [...] | [...] |
| Niveau | [...] | [...] |
| Catégorie | [...] | [...] |
| Périodique (oui/non) | [...] | [...] |
| Intervalle | [...] | [...] |
| Métrage de référence | [...] | [...] |

**Import en masse** — [...]
> 🖊️ Un endpoint `bulk-import` existe. Format attendu ? Qui s'en sert ? Fréquence ?

**Documents joints à un code** — [...]
> 🖊️ Types de fichiers, taille, où ils sont stockés, qui peut les consulter, lien avec la GED s'il y en a un.

**Supprimer un code** — [...]
> 🖊️ Que devient l'historique des interventions faites sous ce code ?

**Les codes libres : créer, fusionner, rattacher, promouvoir** — [...]
> 🖊️ Décris le workflow complet, c'est un sous-système à part entière.

---

## 7. Les modèles récurrents

`[statut]`

> 🖊️ **À écrire :** c'est la fonctionnalité la plus puissante et la plus piégeuse du module.

**À quoi sert un modèle** — [...]

**Construire un modèle** — [...]

**La règle de récurrence**
> 🖊️ Quelles fréquences sont possibles ? Comment la prochaine occurrence est-elle calculée ? Jusqu'à quand les occurrences sont-elles générées à l'avance ?

[...]

**Générer maintenant** — [...]

**Modifier un modèle qui a déjà des occurrences futures** ⚠️
> 🖊️ **Le chapitre le plus important de la partie 1.** Le code calcule un « impact de resynchronisation » avant de propager. Explique en langage utilisateur :
> - Qu'est-ce qui est propagé aux occurrences futures et qu'est-ce qui ne l'est pas ?
> - Que devient une occurrence qu'on avait modifiée à la main (divergence) ?
> - Les occurrences passées sont-elles touchées ?
> - Que montre l'écran d'impact avant validation, et comment le lire ?

[...]

**Supprimer un modèle** — [...]
> 🖊️ Que deviennent les créneaux déjà générés ?

**Transformer un créneau existant en modèle** — [...]

---

## 8. Les alertes opérateur

`[statut]`

> 🖊️ **À écrire :** c'est le sous-système le plus retouché d'après l'historique git, et celui que les utilisateurs comprennent le moins. Prends le temps.

**Le principe en trois phrases** — [...]

**Ce que l'opérateur voit** — [...]
`[capture]`

**Les déclencheurs**
> 🖊️ Liste chaque type de déclencheur, en langage métier : sur quel événement de production l'alerte apparaît. Les notions repérées dans le code : déclenchement après calage, alertes périodiques adossées aux codes de saisie production, alertes liées à un code maintenance.

| Déclencheur | Quand l'alerte apparaît | Exemple concret chez SIFA |
|---|---|---|
| [...] | [...] | [...] |

**Le formulaire de validation** — [...]
> 🖊️ Questions configurables, questions obligatoires, types de réponse, notion de non-conformité. Comment un admin le construit.

**Bloquer la production** — [...]
> 🖊️ Qu'est-ce qui est bloqué exactement, pour qui, et comment on débloque.

**Le délai entre alertes** — [...]
> 🖊️ Réglage global ou par alerte ? À quoi il sert (éviter le harcèlement de l'opérateur ?). Valeur retenue chez SIFA et pourquoi.

**Empilement de plusieurs alertes** — [...]

**Accusés de réception et non-conformités : les relire** — [...]
> 🖊️ Où on les consulte, qui les traite, quelle suite est donnée à une non-conformité.

**Désactiver une alerte / toutes les alertes** — [...]
> 🖊️ Il existe un `disable-all`. Cas d'usage prévu ? Qui a le droit ? C'est réversible comment ?

---

## 9. L'historique

`[statut]`

> 🖊️ **À écrire :** deux historiques distincts existent dans l'interface — « Historique des créneaux » et « Historique des saisies ». Explique la différence, sinon personne ne saura lequel ouvrir.

**Historique des créneaux** — [...]

**Historique des saisies** — [...]

**Les filtres** — [...]

**Ce qu'on peut faire depuis l'historique** — [...]
> 🖊️ Le code permet d'invalider ou de supprimer définitivement depuis l'historique. Qui, quand, avec quelles précautions.

**Combien de temps on garde** — [...]

---

## 10. Cas particuliers et questions fréquentes

`[statut]`

> 🖊️ **À écrire :** au fil de l'eau, à chaque fois qu'un utilisateur te pose une question. C'est la section qui grossit toute seule et qui économise le plus de temps. Démarre avec les 5 questions qu'on t'a déjà posées.

**Q : [...]**
R : [...]

**Q : [...]**
R : [...]

---
---

# PARTIE 2 — RÉFÉRENCE TECHNIQUE

---

## 11. Architecture

`[statut]`

> 🖊️ **À écrire :** la carte du territoire. Un dev qui arrive doit savoir en 5 minutes quel fichier ouvrir pour quelle question.

**Les fichiers du module**

| Fichier | Lignes | Responsabilité | À ouvrir quand… |
|---|---|---|---|
| `app/web/maintenance_page.py` | ~14 000 | [...] | [...] |
| `app/routers/maintenance_events.py` | ~2 100 | [...] | [...] |
| `static/mysifa_maint_form.js` | ~1 000 | [...] | [...] |
| `app/services/maint_op_merge.py` | ~95 | [...] | [...] |
| `app/core/database.py` (section maintenance) | — | [...] | [...] |
| `app/routers/settings.py` (parties maintenance) | — | [...] | [...] |
| `[autres fichiers à ajouter]` | | | |

**Le schéma d'ensemble**
> 🖊️ Décris en phrases le trajet d'une requête, de l'écran à la base et retour. Je le transformerai en diagramme.

[...]

**Pourquoi la page est un monolithe**
> 🖊️ 14 000 lignes de HTML+JS dans un fichier Python. C'est un choix (vitesse de dev, pas de build front) ou un héritage ? Écris-le honnêtement : c'est ce qui évitera à un futur dev de « corriger » ce qui n'est pas un bug.

[...]

**Le formulaire d'alerte partagé avec Settings**
> 🖊️ L'historique git montre une extraction en module JS partagé pour mettre fin aux divergences entre `settings_page.py` et `maintenance_page.py`. Explique le contrat : qui consomme quoi, ce qu'il ne faut surtout pas dupliquer à nouveau.

[...]

---

## 12. Modèle de données

`[statut]` — **à remplir en priorité**

> 🖊️ **À écrire :** pour chaque table — à quoi elle sert en une phrase, puis colonne par colonne le sens métier (pas le type SQL, il est dans le code). Insiste sur les champs JSON : c'est là que se cache la logique.

**Vue d'ensemble des relations**
> 🖊️ Décris les cardinalités en phrases, je génère le diagramme.

[...]

### 12.1 `maintenance_codes`
**Rôle :** [...]
**Clé :** [...]

| Colonne | Sens métier | Valeurs possibles | Notes |
|---|---|---|---|
| `code` | [...] | [...] | [...] |
| `label` | [...] | [...] | [...] |
| `niveau` | [...] | [...] | [...] |
| `categorie` | [...] | `controles`, `suivi`, `[compléter]` | [...] |
| `periodique` | [...] | 0 / 1 | [...] |
| `intervalle` | [...] | texte libre | [...] |
| `metrage_ref` | [...] | texte libre | [...] |
| `[colonnes ajoutées après v128 — à compléter]` | | | |

### 12.2 `maintenance_events`
**Rôle :** [...]

| Colonne | Sens métier | Valeurs possibles | Notes |
|---|---|---|---|
| `machine` | [...] | [...] | [...] |
| `date_prevue` | [...] | [...] | [...] |
| `heure_debut` / `heure_fin` | [...] | [...] | [...] |
| `source` | [...] | `planifie`, `[autres ?]` | [...] |
| `nom` *(v175)* | [...] | [...] | [...] |
| `template_id` | [...] | [...] | [...] |
| `deleted_at` | [...] | [...] | soft-delete — [...] |
| `[à compléter]` | | | |

### 12.3 `maintenance_event_ops`
**Rôle :** [...]
> 🖊️ Contrainte d'unicité `(event_id, code)` à l'origine, puis découpage par machine en v179. Explique ce que ce découpage a changé.

| Colonne | Sens métier | Valeurs possibles | Notes |
|---|---|---|---|
| `statut` | [...] | `a_faire`, `termine`, `invalidee` | [...] |
| `duree_reelle_min` | [...] | [...] | [...] |
| `pieces_changees` | [...] | [...] | [...] |
| `observations` | [...] | [...] | [...] |
| `photos_json` | [...] | **JSON — détailler la structure** | [...] |
| `machines_csv` *(v162)* | [...] | [...] | [...] |
| `consignes` *(v185)* | [...] | [...] | [...] |
| `done_at` / `done_by` / `updated_by` | [...] | [...] | [...] |

### 12.4 `maintenance_event_operators`
**Rôle :** [...]

### 12.5 `maintenance_templates`
**Rôle :** [...]

### 12.6 `maintenance_template_ops`
**Rôle :** [...]
> 🖊️ `machines_csv` ici aussi — même sémantique que dans `event_ops` ou différente ?

### 12.7 `maintenance_alerts`
**Rôle :** [...]

> 🖊️ ⚠️ **Le champ `params` (JSON) porte toute la logique des règles d'alerte** — le schéma SQL ne dit rien de ce qu'il y a dedans. C'est le point le plus critique de tout le document technique : sans cette section, personne ne peut reprendre le code des alertes. Documente chaque clé.

**Structure de `params` :**

```json
{
  "[clé]": "[type — sens — valeurs possibles — valeur par défaut]"
}
```

| Clé | Type | Sens | Défaut | Introduite en |
|---|---|---|---|---|
| [...] | [...] | [...] | [...] | [...] |

### 12.8 `maintenance_alert_settings`
**Rôle :** [...] *(table singleton d'après les migrations)*
> 🖊️ Réglages globaux : mode d'empilement, délai minimum entre alertes, valeurs par défaut. Un par un.

### 12.9 `maintenance_alert_acks`
**Rôle :** [...]
> 🖊️ Structure des réponses au formulaire, marquage des non-conformités, champ `dismissed` (v164) : différence entre *acquitter* et *écarter*.

### 12.10 `maintenance_docs`
**Rôle :** [...]
> 🖊️ Stockage physique des fichiers : où, nommage, sécurisation du nom de fichier, purge.

### 12.11 Tables mortes
> 🖊️ `maintenance_tasks` (v155/v157) a été supprimée par la refonte v158, et `maintenance_event_ops_new` est une table de transition de migration. Note-le pour éviter qu'un futur dev les prenne pour du courant.

[...]

---

## 13. Référence API

`[statut]`

> 🖊️ **À écrire :** 61 routes recensées, listées ci-dessous par domaine. Pour chacune : ce qu'elle fait, ses paramètres notables, qui y a accès, et surtout **ses effets de bord** (une route qui touche autre chose que son objet principal doit le dire).
> Les routes triviales peuvent se contenter d'une ligne. Concentre l'effort sur celles qui ont de la logique.

**Convention :** toutes les routes sont préfixées `/api/maintenance` sauf mention contraire. Accès : `A` = admin maintenance, `O` = opérateur, `A+O` = les deux.

### 13.1 Pages

| Route | Ce qu'elle fait | Accès |
|---|---|---|
| `GET /maintenance` | [...] | [...] |
| `GET /my-maintenance` | [...] | [...] |

### 13.2 Codes

| Route | Ce qu'elle fait | Accès | Effets de bord |
|---|---|---|---|
| `GET /codes` | [...] | [...] | [...] |
| `POST /codes` | [...] | [...] | [...] |
| `PUT /codes/{code}` | [...] | [...] | [...] |
| `DELETE /codes/{code}` | [...] | [...] | [...] |
| `POST /codes/bulk-import` | [...] | [...] | [...] |
| `GET /codes/{code}/docs` | [...] | [...] | [...] |
| `POST /codes/{code}/docs` | [...] | [...] | [...] |
| `GET /docs/{doc_id}/download` | [...] | [...] | [...] |
| `DELETE /docs/{doc_id}` | [...] | [...] | [...] |

### 13.3 Codes libres

| Route | Ce qu'elle fait | Accès | Effets de bord |
|---|---|---|---|
| `GET /codes/libres` | [...] | [...] | [...] |
| `GET /codes/libres/autocomplete` | [...] | [...] | [...] |
| `POST /codes/libres` | [...] | [...] | [...] |
| `PATCH /codes/libres/{code}` | [...] | [...] | [...] |
| `DELETE /codes/libres/{code}` | [...] | [...] | [...] |
| `POST /codes/libres/merge` | [...] | [...] | [...] |
| `POST /codes/libres/{code}/attach` | [...] | [...] | [...] |
| `POST /codes/libres/{code}/promote` | [...] | [...] | [...] |

### 13.4 Créneaux (events)

| Route | Ce qu'elle fait | Accès | Effets de bord |
|---|---|---|---|
| `GET /events` | [...] | [...] | [...] |
| `GET /events/deleted` | [...] | [...] | [...] |
| `GET /events/{id}` | [...] | [...] | [...] |
| `POST /events` | [...] | [...] | [...] |
| `PATCH /events/{id}` | [...] | [...] | [...] |
| `DELETE /events/{id}` | [...] | [...] | ⚠️ jeton de confirmation — [...] |
| `POST /events/{id}/restore` | [...] | [...] | [...] |
| `POST /events/{id}/save-as-template` | [...] | [...] | [...] |

### 13.5 Opérations d'un créneau

| Route | Ce qu'elle fait | Accès | Effets de bord |
|---|---|---|---|
| `POST /events/{id}/ops` | [...] | [...] | [...] |
| `PATCH /events/{id}/ops/{op_id}` | [...] | [...] | [...] |
| `DELETE /events/{id}/ops/{op_id}` | [...] | [...] | [...] |
| `POST /events/{id}/ops/{op_id}/reset` | [...] | [...] | [...] |
| `POST /events/{id}/ops/{op_id}/invalidate` | [...] | [...] | [...] |
| `POST /events/{id}/ops/{op_id}/revalidate` | [...] | [...] | [...] |

### 13.6 Opérateurs

| Route | Ce qu'elle fait | Accès | Effets de bord |
|---|---|---|---|
| `GET /operators` | [...] | [...] | [...] |
| `GET /operators/on-shift` | [...] | [...] | ⚠️ dépend du planning RH — [...] |
| `POST /events/{id}/operators` | [...] | [...] | [...] |
| `DELETE /events/{id}/operators/{op_id}` | [...] | [...] | [...] |
| `GET /my-tasks` | [...] | [...] | [...] |

### 13.7 Modèles récurrents

| Route | Ce qu'elle fait | Accès | Effets de bord |
|---|---|---|---|
| `GET /templates` | [...] | [...] | [...] |
| `GET /templates/{id}` | [...] | [...] | [...] |
| `POST /templates` | [...] | [...] | [...] |
| `PATCH /templates/{id}` | [...] | [...] | ⚠️ resync des occurrences futures — [...] |
| `DELETE /templates/{id}` | [...] | [...] | [...] |
| `GET /templates/{id}/resync-impact` | [...] | [...] | [...] |
| `POST /templates/{id}/generate-now` | [...] | [...] | [...] |

### 13.8 Alertes

| Route | Ce qu'elle fait | Accès | Effets de bord |
|---|---|---|---|
| `GET /alerts` | [...] | [...] | [...] |
| `GET /alerts/active` | [...] | [...] | [...] |
| `GET /alerts/blocking-for-machine` | [...] | [...] | ⚠️ appelée par MyProd — [...] |
| `POST /alerts` | [...] | [...] | [...] |
| `PATCH /alerts/{id}` | [...] | [...] | [...] |
| `DELETE /alerts/{id}` | [...] | [...] | [...] |
| `POST /alerts/disable-all` | [...] | [...] | [...] |
| `POST /alerts/{id}/ack` | [...] | [...] | [...] |
| `POST /alerts/{id}/dismiss` | [...] | [...] | [...] |
| `GET /alert-acks` | [...] | [...] | [...] |
| `DELETE /alert-acks/{ack_id}` | [...] | [...] | [...] |
| `GET /alert-settings` | [...] | [...] | [...] |
| `PUT /alert-settings` | [...] | [...] | [...] |

### 13.9 Pièces d'usure

| Route | Ce qu'elle fait | Accès | Effets de bord |
|---|---|---|---|
| `GET /wearparts/last` | [...] | [...] | [...] |
| `POST /wearparts/info` | [...] | [...] | [...] |

### 13.10 Historique

| Route | Ce qu'elle fait | Accès | Effets de bord |
|---|---|---|---|
| `GET /history` | [...] | [...] | [...] |

---

## 14. Règles métier non évidentes

`[statut]` — **le chapitre à plus forte valeur**

> 🖊️ **À écrire :** tout ce qu'un dev ne devinera pas en lisant le code, et tout ce qui t'a coûté un bug. Format libre, mais pour chaque règle : **ce qu'elle fait / pourquoi elle existe / ce qui casse si on la retire**.

### 14.1 Calcul de la prochaine occurrence d'un modèle
**Ce que ça fait :** [...]
**Pourquoi :** [...]
**Ce qui casse si on y touche :** [...]

### 14.2 Génération des occurrences sur horizon, et le throttle
> 🖊️ Horizon par défaut (90 jours ?), déclencheur de la génération, mécanisme d'anti-rejeu, invalidation du throttle. Pourquoi un throttle était nécessaire.

[...]

### 14.3 Divergence modèle ↔ créneau, et resynchronisation
> 🖊️ Comment la divergence est détectée, ce qui est comparé, quels créneaux sont exclus de la resync, ce que renvoie l'analyse d'impact. C'est la mécanique la plus subtile du module.

[...]

### 14.4 Recalcul de la machine d'un créneau
> 🖊️ Pourquoi la machine d'un créneau est *recalculée* à partir de ses opérations plutôt que simplement stockée. Quand le recalcul est déclenché.

[...]

### 14.5 Le moteur de déclenchement des alertes
> 🖊️ Le cœur du sujet. À documenter :
> - les codes de saisie production qui font foi (`03`, `88` maintiennent le chrono ; `01` en a été exclu ; `89` intervient dans le calage) — explique le rôle exact de chacun
> - le déclenchement « après calage » et son délai configurable
> - la périodicité des alertes et le délai minimum entre deux
> - le mode d'empilement quand plusieurs alertes tombent en même temps
> - le blocage de production : qui appelle quoi, à quel moment

[...]

### 14.6 Suppression douce, restauration, suppression définitive
> 🖊️ Le jeton de confirmation sur `DELETE /events/{id}` : à quoi il sert, comment il est produit, ce qui se passe sans lui.

[...]

### 14.7 Fusion d'opérations (`maint_op_merge`)
> 🖊️ Petit fichier, mais isolé en service — donc il porte une règle. Laquelle, et pourquoi elle ne vit pas dans le routeur.

[...]

### 14.8 Gestion du temps et des fuseaux
> 🖊️ Le code a une fonction dédiée pour « maintenant en heure de Paris ». Explique la convention : qu'est-ce qui est stocké en local, qu'est-ce qui est en ISO/UTC, et où sont les pièges (le repo garde des traces de corrections de fuseau).

[...]

### 14.9 `[autres règles à ajouter]`

---

## 15. Permissions

`[statut]`

> 🖊️ **À écrire :** la matrice complète. Un tableau vaut mieux qu'un paragraphe ici.

| Action | Admin | Opérateur affecté | Opérateur non affecté | Autre rôle |
|---|---|---|---|---|
| Voir le module | [...] | [...] | [...] | ✗ |
| Créer un créneau | [...] | [...] | [...] | ✗ |
| Modifier un créneau | [...] | [...] | [...] | ✗ |
| Supprimer un créneau | [...] | [...] | [...] | ✗ |
| Saisir la réalisation d'une opération | [...] | [...] | [...] | ✗ |
| Invalider / revalider | [...] | [...] | [...] | ✗ |
| Gérer les codes | [...] | [...] | [...] | ✗ |
| Gérer les modèles | [...] | [...] | [...] | ✗ |
| Gérer les alertes | [...] | [...] | [...] | ✗ |
| Acquitter une alerte | [...] | [...] | [...] | ✗ |
| Consulter l'historique complet | [...] | [...] | [...] | ✗ |

**Le mécanisme dans le code** — [...]
> 🖊️ Où se décide l'accès, quelle fonction appeler quand on ajoute un endpoint, quel code HTTP est renvoyé.

---

## 16. Couplages avec les autres modules

`[statut]`

> 🖊️ **À écrire :** la section qui évite les régressions. Pour chaque couplage : le sens de la dépendance, le point de contact précis, et ce qui casse.

| Module | Sens | Point de contact | Ce qui casse si on modifie | Précaution |
|---|---|---|---|---|
| MyProd | [...] | [...] | [...] | [...] |
| Planning RH | [...] | [...] *(opérateurs en poste)* | [...] | [...] |
| Settings | [...] | [...] *(formulaire d'alerte partagé)* | [...] | [...] |
| Utilisateurs / rôles | [...] | [...] | [...] | [...] |
| GED / documents | [...] | [...] | [...] | [...] |
| `[autres]` | | | | |

---

## 17. Frontend

`[statut]`

> 🖊️ **À écrire :** de quoi permettre à quelqu'un d'ouvrir `maintenance_page.py` sans se noyer.

**Organisation du fichier** — [...]
> 🖊️ Quelles zones se succèdent dans les 14 000 lignes (styles, gabarit HTML, blocs JS par vue…). Une carte approximative avec des repères de ligne suffit.

**L'état côté client** — [...]
> 🖊️ Où vit l'état, comment il est rafraîchi, ce qui est mis en cache (le code a des caches pour les pièces d'usure et les détails d'opérations) et comment on l'invalide.

**Conventions de nommage** — [...]
> 🖊️ Le préfixe `_` sur les fonctions internes, le préfixe `maint-` sur les classes CSS, les clés de persistance des sous-onglets (`maint_*_v`).

**Le calendrier de la vue Planning** — [...]
> 🖊️ Glisser-déposer, regroupement des créneaux simultanés, navigation inter-semaines, squelettes de chargement. Les pièges connus.

**Le module de formulaire partagé** — [...]

**Cache-busting des assets** — [...]

---
---

# PARTIE 3 — HISTOIRE ET DÉCISIONS

---

## 18. Chronologie

`[statut]`

> 🖊️ **À écrire :** les étapes, pas les commits. Une ligne par étape marquante, dans l'ordre. Objectif : qu'on comprenne la trajectoire du module en 2 minutes.
> Repères trouvés dans l'historique git, à confirmer et compléter — les dates sont à remplir par toi.

| Période | Version | Étape | Ce que ça a changé |
|---|---|---|---|
| [...] | — | Création du module : codes maintenance | [...] |
| [...] | — | Introduction des alertes | [...] |
| [...] | — | Documents joints aux codes | [...] |
| [...] | — | Première version des tâches (`maintenance_tasks`) | [...] |
| [...] | v2.2.7x | Refonte du planning personnel opérateur | [...] |
| [...] | v2.2.76→82 | Itérations sur l'événement « après calage » | [...] |
| [...] | v2.2.84 | Ouverture par défaut aux opérateurs | [...] |
| [...] | v2.2.85→88 | Questions obligatoires, blocage de production | [...] |
| [...] | — | **Refonte majeure : créneaux + opérations** *(migration v158)* | [...] |
| [...] | — | Modèles récurrents | [...] |
| [...] | v2.4.14 | Extraction du formulaire d'alerte en module partagé | [...] |
| [...] | v2.4.15 | Nettoyage des lignes orphelines dans Settings | [...] |
| [...] | — | Découpage des opérations par machine | [...] |
| [...] | — | Bande de statut, pastilles de retard, regroupement | [...] |
| `[à compléter]` | | | |

---

## 19. Décisions structurantes

`[statut]`

> 🖊️ **À écrire :** une fiche par décision, format court. C'est ce qui manque toujours dans une doc et qui a le plus de valeur dans deux ans — y compris pour toi.
> Duplique le bloc ci-dessous autant de fois que nécessaire.

### D-01 · [Titre de la décision]
- **Contexte :** [qu'est-ce qui posait problème]
- **Options envisagées :** [...]
- **Décision :** [...]
- **Conséquences :** [ce que ça a permis, ce que ça a coûté]
- **Reviendrait-on dessus ?** [...]

### D-02 · [Titre]
- **Contexte :** [...]
- **Options envisagées :** [...]
- **Décision :** [...]
- **Conséquences :** [...]
- **Reviendrait-on dessus ?** [...]

> 🖊️ **Candidats identifiés dans l'historique, à traiter en priorité :**
> - Abandonner `maintenance_tasks` pour le modèle créneau + opérations (v158)
> - Stocker les règles d'alerte en JSON dans `params` plutôt qu'en colonnes (évite une migration par évolution — mais au prix de quoi ?)
> - Générer les occurrences récurrentes à l'avance plutôt qu'à la volée
> - Extraire le formulaire d'alerte en module JS partagé
> - Ouvrir le module aux opérateurs par défaut
> - Découper les opérations par machine
> - Garder la page en un seul fichier Python

---

## 20. Dette connue et pièges

`[statut]`

> 🖊️ **À écrire :** sois franc, ce document est pour toi et pour quelqu'un qui reprendra le code. Pour chaque point : gravité, ce que ça empêche, ce qu'il faudrait faire.

| # | Point de dette | Gravité | Impact concret | Piste de résolution |
|---|---|---|---|---|
| 1 | `maintenance_page.py` fait ~14 000 lignes | [...] | [...] | [...] |
| 2 | Les `ON DELETE CASCADE` sont inactifs tant que `PRAGMA foreign_keys=ON` n'est pas activé | [...] | [...] | [...] |
| 3 | La logique des alertes vit dans un champ JSON non validé par un schéma | [...] | [...] | [...] |
| 4 | `[à compléter]` | | | |

**Zones à ne pas toucher sans précaution**
> 🖊️ La liste courte : « si tu modifies X, relis d'abord le chapitre Y et teste Z ».

- [...]

**Ce qui n'est pas couvert par des tests**
- [...]

---
---

# ANNEXES

## A. Glossaire

> 🖊️ Reprends les termes du chapitre 3 en une ligne chacun, par ordre alphabétique. Utile pour un lecteur qui arrive en cours de document.

| Terme | Définition |
|---|---|
| [...] | [...] |

---

## B. Inventaire des migrations

> 🖊️ Extrait du code — complète la colonne « Ce que ça a changé » pour les migrations structurantes. Les migrations purement additives peuvent rester vides.

| Version | Identifiant | Ce que ça a changé |
|---|---|---|
| 128 | `maintenance_codes_table` | [...] |
| 129 | `maintenance_codes_intervalle` | [...] |
| 131 | `maintenance_codes_metrage_ref` | [...] |
| 132 | `maintenance_alerts_table` | [...] |
| 133 | `maintenance_alerts_link_to_codes` | [...] |
| 134 | `maintenance_alert_settings_singleton` | [...] |
| 135 | `maintenance_alert_settings_stack_mode` | [...] |
| 136 | `maintenance_alert_acks_table` | [...] |
| 137 | `maintenance_alert_settings_new_defaults` | [...] |
| 138 | `maintenance_alert_settings_min_gap` | [...] |
| 149 | `maintenance_docs_table` | [...] |
| 155 | `maintenance_tasks_table` | *(table supprimée en v158)* |
| 157 | `maintenance_tasks_time_slots` | *(table supprimée en v158)* |
| **158** | `maintenance_events_refonte` | ⚠️ [...] |
| 162 | `maintenance_event_ops_machines_csv` | [...] |
| 163 | `maintenance_templates` | [...] |
| 164 | `maintenance_alert_acks_dismissed` | [...] |
| 175 | `maintenance_events_nom` | [...] |
| 178 | `maintenance_codes_split_interventions` | [...] |
| 179 | `maintenance_event_ops_split_per_machine` | [...] |
| 185 | `maintenance_event_ops_consignes` | [...] |

---

## C. Configuration et variables d'environnement

> 🖊️ Tout ce qui change le comportement du module sans toucher au code.

| Variable / réglage | Où | Valeurs | Effet | Valeur en production |
|---|---|---|---|---|
| `MAINTENANCE_OPEN_BETA` | `config.py` | `0` / `1` | [...] | [...] |
| `[réglages en base — alert_settings]` | [...] | [...] | [...] | [...] |
| `[à compléter]` | | | | |

---

*Fin du squelette. Une fois rempli — même partiellement — je le convertis en page HTML autonome navigable.*

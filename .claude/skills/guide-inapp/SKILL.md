---
name: guide-inapp
description: Cree ou met a jour un guide in-app (tuto par onglet) dans MySifa. Contient la structure imposee des etapes, les mockups SVG et les quatre points de branchement. Utiliser des qu'on ajoute une app ou un onglet a MySifa, ou qu'on parle de tuto, de guide, d'onboarding d'un ecran.
argument-hint: "[module] [onglet]"
---
## Guides in-app (tutos par onglet) — obligatoire pour chaque nouvelle app ou nouvel onglet

MySifa embarque un système de guides in-app qui explique chaque module à
l'utilisateur au sein même de l'interface. Le premier module équipé est
Qualité (voir `app/web/qualite_page.py`) — il sert de référence pour tous
les modules à venir.

**Règle absolue — pas de nouvelle app ni de nouvel onglet sans guide.**

Toute nouvelle application (au sens module — MyProd, MyStock, MyExpé…) et
tout nouvel onglet fonctionnel à l'intérieur d'un module doit être livré
avec son guide in-app. Sans guide, le PR n'est pas considéré comme fini,
au même titre qu'une page sans version mobile ou qu'un endpoint sans
gestion d'erreur.

**Règle proactive — proposer un guide quand il n'y en a pas.**

Si Eugène demande une modification sur un onglet existant qui n'a pas
encore de guide, l'IA doit systématiquement, **une fois le vrai travail
terminé**, proposer d'en ajouter un. Une ligne suffit à la fin de la
réponse : « Cet onglet n'a pas encore de guide in-app. Je te propose d'en
ajouter un — 4 à 6 étapes avec illustrations SVG et bullets par service.
Ok ? ». Ne pas attendre qu'Eugène le demande. Ne pas noyer la proposition
dans un paragraphe. Ne pas la formuler avant d'avoir fait le travail
demandé.

**Structure d'un guide**

Un guide est un dict de la forme `{ 'clé-guide': { steps: [...] } }`
retourné par une fonction locale au module (aujourd'hui `_qualiteGuides()`
dans `qualite_page.py`). Chaque `step` a la forme :

```javascript
{
  icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">…</svg>',
  title: 'Titre court de l\'étape',
  body: '<p>HTML autorisé : <strong>gras</strong>, <span class="qguide-tag">tag</span>.</p>',
  illu: '<svg viewBox="0 0 340 150">… mini-mockup de la page …</svg>',
  extra: '<p>Contenu optionnel affiché sous l\'illustration</p>'  // facultatif
}
```

- **Étape 1 (obligatoire)** — introduction courte à la page + bullets
  « Ce que vous avez à faire » adaptés au rôle courant. Titre = nom de
  l'onglet. Les bullets sont déclinés par service dans un dict du type
  `QUALITE_TASKS_BY_SERVICE = { direction: [...], administration: [...],
  fabrication: [...], commercial: [...] }`. La 1ère slide sélectionne le
  jeu de bullets en fonction de `S.userRole` (injecté par le template via
  `__USER_ROLE__`). Pour `superadmin` et `direction`, on affiche toutes
  les sections empilées.
- **Étapes 2 à N** — viser **4 à 6 étapes au total** (l'étape 1 comprise).
  Chacune couvre un aspect fonctionnel majeur : structure de données,
  action clé, workflow, alertes, astuces. Le `body` est court (2 à 4
  lignes maximum), factuel. L'`icon` est un SVG stroke
  (`stroke="currentColor"`, `stroke-width="1.6"` ou `"1.8"`) — jamais un
  emoji.

**Illustrations SVG — mini-mockups fidèles de la page**

Chaque étape porte une `illu` : un SVG placé sous le texte qui montre
visuellement l'élément de la page dont parle l'étape. Ce n'est **pas** une
icône décorative — un utilisateur qui regarde l'illustration doit
reconnaître le composant réel (grille de cartes, carte groupe, modal
radio, bandeau alertes, header page détail, etc.). Les illustrations du
module Qualité sont regroupées dans le dict `QUALITE_MOCKUPS` et servent
de modèle.

Contraintes techniques :

- `viewBox` typique : `0 0 340 150` (ajustable selon le composant).
- Couleurs : **uniquement** les variables CSS du design system —
  `var(--card)`, `var(--border)`, `var(--accent)`, `var(--accent-bg)`,
  `var(--text)`, `var(--text2)`, `var(--muted)`, `var(--ok)`,
  `var(--warn)`, `var(--danger)`, `var(--bg)`. Seule exception tolérée :
  `#fff` pour du texte posé sur un fond `var(--accent)` déjà saturé.
- Pas de couleur codée en dur. Pas d'`<image>` externe. Pas de police
  externe — laisser hériter la police système.

**Comment brancher un nouveau guide (4 points, pas plus)**

1. **Ajouter une entrée** dans le dict `_qualiteGuides()` (ou son
   équivalent pour un autre module — `settings_page.py`, `stock_page.py`,
   `planning_page.py` etc. n'ont pas encore leur propre dictionnaire de
   guides ; le jour où le premier guide y sera ajouté, dupliquer le
   pattern de `qualite_page.py`).
2. **Mapper la vue au guide** dans `VIEW_TO_GUIDE = { 'nom-de-vue':
   'clé-guide' }` pour l'auto-open lors du `setView(...)`. Une fois le
   guide acknowledged par un utilisateur, il ne se rouvre plus
   automatiquement — il reste accessible via le bouton `?`.
3. **Ajouter le bouton `?`** (icône livre ouvert) dans le header de la
   vue :
   ```html
   <button type="button" class="qual-help-btn" data-guide="ma-cle"
           onclick="openGuide('ma-cle')">…</button>
   ```
   Le badge pulse `.unread` s'affiche automatiquement tant que le guide
   n'a pas été acked.
4. **Mettre à jour `_FMT_GUIDES`** dans `settings_page.py` avec le label
   lisible du nouveau guide, pour qu'il apparaisse joliment dans la
   table admin des Formations (`/settings` → onglet « Formations &
   guides »).

**Contenu — règles éditoriales**

- **Pas d'emojis** (règle générale MySifa).
- Ton **direct, factuel, professionnel** — pas de « Bienvenue ! », pas de
  « Découvrez notre super module ».
- Les bullets par service dans l'étape 1 sont **précis et actionnables** :
  « Saisir les certificats matière reçus des fournisseurs », pas
  « Utiliser le module Qualité ».
- Le `body` d'une étape tient en 2 à 4 lignes. Si ça déborde, l'étape
  n'est pas assez ciblée — la découper.
- Les illustrations sont des **mini-mockups fidèles** de la page, pas des
  icônes abstraites.

**Pièges à éviter (retours d'expérience)**

Cinq bugs concrets rencontrés en construisant le premier guide, qu'il faut
éviter dans les modules suivants :

1. **`main.py` : import + `include_router` obligatoires.** L'import
   `from app.routers.guides import router as guides_api_router` **ne
   suffit pas**. Il faut aussi `app.include_router(guides_api_router)`
   sinon toutes les routes `/api/guides/*` renvoient un 404 silencieux
   côté front (aucune trace côté serveur, aucun message côté client).
   Vérifier les deux points à chaque nouveau router.

2. **Contenu JS entre `<script src="…">` et `</script>` : ignoré.**
   Un tag `<script>` avec attribut `src` ne peut pas contenir de code
   inline — le browser charge le fichier externe et ignore tout ce qu'il
   y a entre les balises. Si un patch insère des fonctions à cet
   endroit-là par erreur, elles ne seront jamais définies et un
   `ReferenceError` remontera quand elles seront appelées. Injecter le
   code inline **avant** ou **après** le tag `<script src=…>`, dans son
   propre bloc `<script>…</script>`.

3. **Le helper `api()` change selon le module.** Dans
   `qualite_page.py`, `api(path, opts)` retourne l'objet `Response` de
   `fetch` — le front doit tester `if (!r.ok)` puis appeler
   `await r.json()`. Dans `settings_page.py`, `api(path, opts)` retourne
   déjà **le JSON parsé** et **throw sur HTTP != 2xx** — le front doit
   faire `_var = await api(...)` dans un `try/catch`. Copier-coller un
   pattern d'un module à l'autre sans lire les 4 lignes de `async
   function api(...)` provoque un « erreur chargement » alors que le
   serveur renvoie 200. Vérifier `api()` à chaque changement de module.

4. **La table `users` n'a pas de colonne `prenom`.** Elle a `id`, `nom`
   (nom complet), `email`, `role`, `password_hash`, `operateur_lie`,
   `actif`, `created_at`, `last_login`. Un `SELECT ..., prenom, ...`
   fait planter la requête SQL en 500. Utiliser `nom` seul dans le
   backend, et côté front construire l'affichage en défensif
   (``${u.prenom||''} ${u.nom||''}``.trim() supporte les 2 formats).

5. **Ack robuste — envoyer bitmap ET total_steps depuis le front.** Les
   `heartbeats` du suivi de progression sont *fire-and-forget* (POST
   asynchrones sans `await`). Ils peuvent arriver au serveur **après**
   l'appel `/ack`. Pour éviter cette race condition, le front envoie
   toujours dans le body de `/ack` : `{guide_key, client_bitmap,
   client_total_steps}`. Le serveur fait `merged = server_bitmap |
   client_bmp` et fait confiance au `client_total_steps` (auto-heal
   d'une éventuelle row DB avec un `total_steps` stale d'une ancienne
   version du guide). Reproduire ce pattern pour tout nouveau système
   de progression : bitmap + total côté front, fusion côté serveur.

**Infra existante — rien à re-écrire**

Le système est complet côté infra ; ajouter un guide ne demande que du
contenu (steps + illustrations SVG + entrée dans le mapping). Rien à
brancher côté backend, rien à ajouter en DB. Ce qui existe déjà :

- **Migration DB 181** — table `user_guide_progress` (`user_id`,
  `guide_key`, `total_steps`, `steps_seen_bitmap`, `total_time_ms`,
  `open_count`, `opened_at`, `completed_at`, `acknowledged_at`,
  `reset_at`, `reset_by`). Une ligne par (utilisateur, guide).
- **Router `app/routers/guides.py`** — `GET /api/guides/progress`,
  `POST /api/guides/open`, `POST /api/guides/heartbeat`,
  `POST /api/guides/ack`, plus `GET /api/guides/admin/overview` et
  `POST /api/guides/admin/reset` (gated `superadmin | direction`).
- **Frontend générique** — modal avec transitions horizontales
  (`from-left` / `from-right` / `to-left` / `to-right`), barre de
  progression, dots cliquables, boutons Précédent / Suivant, et bouton
  « J'ai compris — clôturer » **désactivé tant que toutes les étapes
  n'ont pas été vues** (bitmap complet). Auto-open à la 1ère visite,
  jamais de re-open automatique après acknowledgement.
- **Admin `/settings` → « Formations & guides »** (groupe Audit &
  qualité) — tableau `Utilisateur × Guide` avec statut, étapes vues,
  temps passé, dates, et bouton Reset pour repasser un utilisateur à
  zéro sur un guide.

---

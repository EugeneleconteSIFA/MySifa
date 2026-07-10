# Kernse — Instructions pour Claude / Cursor / Windsurf

> Ce fichier ne remplace pas `/CLAUDE.md` à la racine (MySifa) — il le **complète**
> pour tout ce qui se passe dans le dossier `kernse/`. Toute règle non redéfinie
> ici reste celle de MySifa (workflow git, DB, écriture fichiers Windows, ton
> éditorial, etc.).

## Contexte projet

**Kernse** est le nom commercial du produit SaaS qu'on est en train d'extraire de
MySifa pour le vendre à des TPE/PME industrielles (ateliers, fabricants, sous-
traitants, façonniers — verticale imprimerie/façonnage en niche d'attaque).
MySifa reste **l'instance SIFA** de ce même produit, avec ses valeurs métier par
défaut. Le code applicatif est unique — c'est le paramétrage qui différencie une
instance SIFA d'une instance client Kernse.

**Rôle du dossier `kernse/`** : c'est ici qu'on construit tout ce qui n'existe
pas encore dans MySifa et qui est **spécifique à la commercialisation** :
socle SaaS multi-instances, console plateforme, provisioning, onboarding client,
seed de la démo, design system Kernse, landing publique. Aucune logique
métier existante n'est dupliquée depuis `app/` — quand on veut la rendre
paramétrable, on modifie `app/` directement (SIFA reste défaut, cf. règle #1
plus bas).

**Frontière stricte** :

| Où | Quoi |
|---|---|
| `/app/`, `/main.py`, `/config.py` (racine MySifa) | Code métier partagé, modifié pour devenir paramétrable ; SIFA garde ses valeurs par défaut |
| `/kernse/app/` | Nouveau code Kernse (console plateforme, provisioning, onboarding, seeds) — pas de duplication du métier |
| `/kernse/static/` | Design system Kernse : `kernse.css` (tokens globaux), assets branding, favicons |
| `/kernse/landing/` | Site vitrine `kernse.com` (statique ou template FastAPI dédié) |
| `/kernse/seeds/` | `seed_demo_db.py` + jeux d'opérations/machines par métier (imprimerie, usinage, plasturgie, assemblage, découpe) |
| `/kernse/scripts/` | Provisioning d'instance client (systemd + nginx + certbot + DB vierge), backup par client, mises à jour de flotte |
| `/kernse/docs/` | Docs produit, cas clients, argumentaires commerciaux |

---

## Architecture — trois apps FastAPI distinctes

Pour éviter tout monolithe, Kernse s'organise en **trois apps FastAPI
indépendantes** au sein du même repo. Chaque app a son propre `main.py`,
son propre service systemd, son propre port, sa propre auth. Elles
partagent uniquement `kernse/shared/` (modèles Pydantic, helpers DB) —
jamais d'import d'une app vers une autre.

| App | Path | Domaine (prod / test) | Port (prod / test) | Rôle |
|---|---|---|---|---|
| `kernse-landing` | `kernse/landing/` | `www.kernse.fr` / `v1.kernse.fr` | 8101 / 8103 | Site public marketing. FastAPI + Jinja2. **Aucune** DB, aucune auth. |
| `kernse-admin`   | `kernse/admin/`   | `admin.kernse.fr` / `admin-v1.kernse.fr` | 8102 / 8104 | Console plateforme (superadmin uniquement). Allowlist stricte + 2FA à venir. |
| Instances clients | `/app/` (code MySifa métier) | `<slug>.kernse.fr` | 8200+ | Une app FastAPI + une SQLite par client. Même code que SIFA (paramétrable). |

**Règles absolues** :

- Une app ne peut jamais importer les routers ou services d'une autre app.
  Elles ne partagent que `kernse/shared/`.
- Chaque app a son propre `config.py` (variables d'env dédiées, ports
  distincts).
- Les tables DB plateforme (`clients`, `audit_log`, `platform_settings`,
  `clients_archived`) sont accessibles **uniquement** depuis
  `kernse-admin`. `kernse-landing` peut lire `platform_settings` en
  read-only si nécessaire, mais ne modifie jamais.
- Les instances clients ne connaissent pas la DB plateforme. Elles
  utilisent leur propre SQLite locale (`/home/kernse/instances/<slug>/app/data/production.db`).

## Logique de promotion — épingle par défaut

Une décision structurante validée avec Eugène :

- **Promotion individuelle** = épingle automatique (`pinned=1`). Le client
  est protégé des futures promotions de masse tant que son épingle n'est
  pas explicitement détachée.
- **Promotion de masse** = ne touche jamais les clients épinglés ni les
  suspendus. Les retours API listent explicitement les épinglés ignorés
  (`skipped_pinned`).
- **Détacher l'épingle** = geste explicite du superadmin plateforme. Re-
  inclut le client dans les futures promotions de masse.

Cette règle garantit à un client individuellement promu qu'aucune
action de masse ne modifie son instance sans un geste explicite.

L'implémentation vit dans `kernse/admin/services/promotion_service.py`.
Toute route qui déclenche une promotion (individuelle, masse, unpin)
doit passer par ce service — jamais d'appel direct au shell depuis un
router.

## Règle absolue #1 — Paramétrable dès l'écriture, SIFA reste défaut

**Ceci est la règle la plus importante de tout le repo côté commercialisation.**
Elle s'applique à tout nouveau code, dans `kernse/` comme dans `app/`. Elle
s'applique aussi aux modifs de code existant dès qu'on touche à une valeur
métier.

### Le principe

Aucune donnée qui décrit une entreprise cliente n'est écrite en dur dans le
code. Machines, opérations, terminologie, transporteurs, structure de coûts,
calendrier, rôles, plans d'emplacement, taux horaires : **tout vit en base et
s'édite dans Paramètres**. Le code lit un référentiel, il ne le contient pas.

### Le pattern à suivre — `APP_NAME` est le modèle

Le refactor branding a défini le pattern :

1. On introduit une variable / une table de config qui a une **valeur par
   défaut = valeur SIFA actuelle**. Aucune rupture pour la prod.
2. Le code métier lit **toujours** cette valeur (jamais la constante SIFA en
   dur).
3. La démo Kernse et les futurs clients surchargent la valeur via `.env` (pour
   les scalaires) ou via un seed (pour les référentiels).

**Concrètement, sur une nouvelle feature :**

- **Scalaire** (nom, URL, seuil, couleur d'accent) → variable dans `config.py`
  avec `os.getenv("XXX", "<valeur SIFA>")`.
- **Petit référentiel figé** (liste de statuts, sévérités, codes techniques
  structurants) → constante Python dans `config.py`, mais toujours lue via une
  fonction et jamais interpolée en dur dans un template HTML.
- **Référentiel métier** (machines, opérations, transporteurs, types de NC,
  postes de coût, jours de fermeture) → table SQLite créée par migration,
  seedée avec les valeurs SIFA, exposée par un CRUD dans Paramètres.

### Anti-patterns interdits

- Écrire `"Cohésio 1"`, `"Repiquage"`, `"Errepi"`, `"Bunsch"`, `"SIFA"` ou tout
  autre nom propre SIFA en dur dans un router, une page ou un composant JS.
- Coder un `if machine == "Cohésio 1":` — la logique métier ne dépend jamais
  d'une chaîne d'identifiant machine. Elle dépend d'attributs (`type`,
  `capacite`, `taux_horaire`) qui sont eux-mêmes en base.
- Injecter `"eleconte@sifa.pro"`, `"admin@sifa.fr"`, `"mysifa.com"`,
  `"sifa.pro"` dans un template envoyé à l'utilisateur final. Ces valeurs
  existent dans `config.py` (via env), et sont lues par le code — pas d'exception.
- Ajouter un nouveau template email qui commence par « Bonjour, SIFA vous
  informe... » — c'est `APP_TITLE` qu'on interpole, pas une chaîne littérale.
- Écrire une migration qui remplit une nouvelle table avec des valeurs SIFA
  sans conditionner ce seed à `ENV_NAME` ou à un flag « pas d'écrasement si
  déjà rempli ». Un client Kernse démarre avec **une table vide** que
  l'onboarding remplit, pas avec les codes SIFA à effacer.

### Comment détecter qu'une valeur est SIFA-spécifique

Question test : « Un client imprimerie de Lille qui installe Kernse demain
matin, cette valeur a-t-elle un sens pour lui ? »

- Réponse « oui, universellement » (ex. code opération technique interne,
  format ISO d'une date) → constante en dur OK.
- Réponse « non, ça ne concerne que SIFA » → **paramètre obligatoire**.
- Doute → paramètre obligatoire par défaut (on préfère un paramètre inutile à
  une constante à refactoriser plus tard).

### Où va quoi — deux étages de paramétrage

| Étage | Table / fichier | Qui édite | Exemples |
|---|---|---|---|
| **Plateforme** (Kernse en tant qu'éditeur) | `platform_settings` (nouvelle table) + `.env` du VPS | Toi (superadmin plateforme) | Nom de marque global, URL de la landing, clé Stripe, catalogue des plans, catalogue des jeux de départ métier |
| **Entreprise** (le client) | `client_settings`, tables métier (`machines`, `operations`, `transporteurs`, `nc_types`, `postes_cout`...) | Le superadmin de l'organisation cliente | Machines de l'atelier, codes opérations retenus, transporteurs utilisés, taux horaires, jours fériés/fermetures, terminologie (« dossier » ou « OF » ou « commande »), rôles renommés |

Un utilisateur classique ne voit ni l'un ni l'autre — il utilise les valeurs
choisies par le superadmin de son organisation.

### Cas particulier : les modules verticaux (imprimerie / façonnage)

`MyBAT`, `MyPrint`, `Appels d'offre` sont des modules « verticale imprimerie ».
Ils **ne sont pas** SIFA-spécifiques (le vocabulaire BAT / gaufrage / traits de
coupe est celui du métier, pas de SIFA) mais ils **ne sont pas génériques non
plus**. Règle : marqués `module_optional=True` et `vertical="imprimerie"` dans
le catalogue de modules ; désactivés par défaut sur un plan Kernse Atelier
générique, activables via un pack vertical.

---

## Positionnement dans le workflow existant

**Instances qui tournent aujourd'hui** (voir `/CLAUDE.md` racine pour le détail) :

| Instance | Rôle vis-à-vis de Kernse |
|---|---|
| `mysifa` (prod, port 8000, `www.mysifa.com`) | Reste sur son domaine tant que SIFA n'est pas prêt à basculer visuellement. Devient une instance Kernse comme les autres à terme (même code, même design system). |
| `mysifa-v1` (staging, port 8002, `v1.mysifa.com`) | Continue son rôle de banc d'essai des migrations, exactement comme aujourd'hui. Toute évolution Kernse passe d'abord par v1. |
| `mysifa-demo` (à créer, cadré dans `docs/demo.md`) | **L'instance vitrine Kernse.** Nom d'entreprise fictif, jeu d'opérations et de machines non-SIFA, DA Kernse à 100 %. Sert de démo commerciale et de banc d'essai à la généralisation métier. |
| Instances clients (à venir) | Une instance FastAPI + une DB SQLite par client, provisionnée depuis un script de `kernse/scripts/`. Isolation stricte pour les 12 premiers mois (cf. brainstorm feuille 4). |

**Workflow de déploiement inchangé** : feature branch depuis `staging` → PR →
merge sur `staging` → v1 se met à jour dans la minute via cron → validation
manuelle → bouton « Promouvoir v1 → v2 ». Rien de spécifique Kernse ici — les
règles du `/CLAUDE.md` racine s'appliquent telles quelles.

**Numéro de version** : `APP_VERSION` dans `config.py` (racine) reste la source
de vérité pour toutes les instances Kernse. On ne fork pas la version par
instance — c'est le même code partout, c'est le paramétrage qui change.

---

## Design system Kernse

**Ne pas confondre avec le design system MySifa** (dark cyan `#22d3ee`) qui vit
dans les CSS existants. Le design system Kernse s'applique dans `kernse/`
et sera porté progressivement dans le reste de l'app (chantier C du brainstorm).
Tant que le portage n'est pas fait, une page MySifa peut coexister avec une
page Kernse dans la même session utilisateur — c'est attendu.

### Tokens de couleur

```css
:root {
  /* Navy — texte principal, headers, callouts sérieux */
  --navy:      #182444;
  --navy-2:    #26314f;
  --navy-3:    #3a4568;

  /* Orange Kernse — accent, badges, CTA */
  --orange:    #F2652B;
  --orange-2:  #f37d4d;
  --orange-bg: #fce4d6;
  --orange-line: #f4b596;

  /* Fond crème — DA propre à Kernse (rupture avec le dark cyan MySifa) */
  --bg:        #f6f4ef;
  --surf:      #ffffff;
  --surf-2:    #faf7f1;

  /* Encre */
  --ink:       #182444;
  --ink-2:     #4e5872;
  --muted:     #8b91a4;

  /* Structure */
  --line:      #e6e2d7;

  /* Statuts */
  --green:     #1f9d57; --green-bg:  #e3f3ea;
  --amber:     #bf7d12; --amber-bg:  #f6ecd6;
  --red:       #cf3b32; --red-bg:    #f7e2e0;
  --violet:    #6c5ce7; --violet-bg: #ece9fc;

  /* Rayons et ombre — plus doux que MySifa (r=10px) */
  --r:         18px;
  --r-sm:      12px;
  --shadow:    0 1px 2px rgba(24,36,68,.05), 0 12px 32px rgba(24,36,68,.08);
}
```

**Règle absolue Kernse** : jamais de couleur codée en dur dans un composant.
Toujours une variable CSS. Si un besoin nouveau apparaît (statut, catégorie),
on ajoute un token dans `kernse.css`, on ne l'inline pas.

### Typographie

- **Sans (UI, texte)** : `'Inter Tight', system-ui, sans-serif`
- **Brand (H1/H2, wordmark)** : `'Poppins', var(--sans)` — poids 900, letter-spacing négatif (-0.8px à -1.5px)
- **Mono (chiffres, KPI, meta)** : `'JetBrains Mono', ui-monospace, monospace` — souvent en poids 800, avec `font-feature-settings:'tnum' 1`

Tailles courantes :
- Labels : 10-11px, uppercase, letter-spacing 0.5-1.2px, poids 800
- Corps : 13px, line-height 1.55
- H2/H3 : 15-19px
- H1 : 29px
- KPI grand format : 26px+, mono, orange

### Wordmark et logo

Le wordmark Kernse s'écrit `K<em>ernse</em>` en HTML, où `<em>` porte la couleur
orange (`--orange`) et un `margin-left:-3px`. Le `K` initial est en navy dans
un carré `--navy` blanc, radius 8px. Le kit complet (favicons, variantes) est
dans `kernse/static/branding/` (à créer dans une prochaine étape).

Ne jamais afficher « Kernse » dans un template sans passer par
`APP_TITLE` / `APP_NAME` — même sur les pages Kernse. La logique de rebrand
doit rester unique : c'est config.py + html.py qui décident du wordmark
affiché.

### Composants — tokens

```css
/* Card */
.card {
  background: var(--surf);
  border: 1px solid var(--line);
  border-radius: var(--r);
  box-shadow: var(--shadow);
  padding: 14px 16px;
}

/* Tag (statut, catégorie) */
.tag {
  display: inline-block;
  font-size: 10px; font-weight: 800;
  text-transform: uppercase; letter-spacing: .5px;
  padding: 2px 8px; border-radius: 999px;
}
.tag-ok     { background: var(--green-bg);  color: var(--green); }
.tag-warn   { background: var(--amber-bg);  color: var(--amber); }
.tag-danger { background: var(--red-bg);    color: var(--red); }
.tag-accent { background: var(--orange-bg); color: var(--orange); }
.tag-navy   { background: var(--navy);      color: #fff; }
.tag-violet { background: var(--violet-bg); color: var(--violet); }

/* Callout */
.callout {
  border-left: 3px solid var(--orange);
  background: var(--orange-bg);
  border-radius: 0 var(--r-sm) var(--r-sm) 0;
  padding: 10px 14px;
  color: var(--ink-2);
}
.callout b { color: var(--ink); }
```

### Table de mapping MySifa → Kernse (pour le futur re-skin)

| Rôle | MySifa (dark cyan) | Kernse (clair navy/orange) |
|---|---|---|
| Fond page | `--bg: #0a0e17` | `--bg: #f6f4ef` |
| Fond surface | `--card: #111827` | `--surf: #ffffff` |
| Bordure | `--border: #1e293b` | `--line: #e6e2d7` |
| Texte principal | `--text: #f1f5f9` | `--ink: #182444` |
| Texte secondaire | `--text2: #cbd5e1` | `--ink-2: #4e5872` |
| Texte discret | `--muted: #94a3b8` | `--muted: #8b91a4` |
| Accent principal | `--accent: #22d3ee` (cyan) | `--orange: #F2652B` |
| Accent fond | `--accent-bg: rgba(34,211,238,.12)` | `--orange-bg: #fce4d6` |
| Succès | `--success: #34d399` | `--green: #1f9d57` |
| Avertissement | `--warn: #fbbf24` | `--amber: #bf7d12` |
| Danger | `--danger: #f87171` | `--red: #cf3b32` |
| Police UI | `'Segoe UI', system-ui` | `'Inter Tight', system-ui` |
| Rayon composants | 10-12px | 12-18px |

Cette table est **la référence** pour la migration du reste de l'app. Ne pas
inventer de nouveaux tokens Kernse en cours de refactor : si un composant
MySifa utilise une couleur qui n'a pas d'équivalent dans la table, ajouter le
token dans `kernse.css` **avant** de l'utiliser.

### Thème light Kernse

Kernse est nativement clair. La question « faut-il un thème dark Kernse ? »
n'est pas tranchée. Par défaut, ne **pas** en implémenter — attendre un
retour utilisateur explicite. Les instances qui veulent un thème dark
utilisent MySifa (dark) tant que le portage n'est pas fini.

---

## Terminologie produit — Kernse-neutre

Kernse s'adresse à des ateliers de tous horizons. Les mots « dossier »,
« ordre de fabrication », « OF », « commande », « travail » désignent tous la
même chose selon la culture de l'entreprise. Règle :

- **Dans le code** : on garde `no_dossier`, `planning_entries`, `production_data`
  (compat schéma DB) — c'est de la nomenclature interne, invisible pour
  l'utilisateur.
- **Dans l'UI** : jamais de mot métier en dur. Un dictionnaire léger de 2-3
  lexiques prédéfinis (« Dossiers » SIFA / « OF » / « Commandes ») que le
  client choisit à l'onboarding et qui pilote les labels des pages.
- **Dans les messages système / erreurs / toasts** : idem — on lit le lexique
  du client, on ne concatène pas « le dossier XXX est... ».

Le lexique par défaut d'une nouvelle instance client Kernse est le lexique
« OF » (le plus neutre en France industrielle). SIFA garde « Dossiers ».

---

## Onboarding & seeds

Un client TPE n'a ni DSI ni chef de projet. Objectif : **atelier configuré
en 15 minutes** par le patron seul. Toute nouvelle feature qui introduit une
donnée métier doit fournir en même temps un **seed de démarrage** et un
**écran d'édition** dans Paramètres.

### Jeux de départ par métier

Dans `kernse/seeds/starter_kits/` (à créer) :

- `imprimerie.json` : codes opérations (calage, tirage, séchage, coupe,
  reliure), machines type (offset, numérique, façonnage), lexique BAT.
- `usinage.json` : opérations (préparation, tournage, fraisage, contrôle),
  machines (tour, fraiseuse, CN).
- `plasturgie.json` : opérations (démarrage moule, injection, contrôle
  visuel), machines (presses).
- `assemblage.json` : opérations (préparation, montage, contrôle, emballage).
- `decoupe.json` : opérations (calage lame, découpe, contrôle épaisseur).

À l'onboarding, le patron choisit son métier — le seed remplit `machines`,
`operations`, `nc_types` avec des exemples cohérents qu'il peut ensuite
supprimer / renommer / compléter. **Jamais** de valeurs SIFA dans ces seeds :
ce sont des exemples génériques du métier.

### Assistant de démarrage

5 étapes, dans l'ordre : entreprise + logo → ressources (machines) →
opérations (choix d'un starter kit + retouche) → équipe + rôles →
import CSV (clients, produits, stock). Chaque étape a un état sauvegardable
et peut être reprise plus tard. Écrire les composants dans
`kernse/app/onboarding/`.

---

## Multi-tenant — stratégie assumée

**Décision structurante n° 1 du brainstorm (feuille 4) :** stratégie 1 —
une instance FastAPI + une SQLite par client — pour les 12 premiers mois.

Conséquences pour le code Kernse :

- Le code métier reste mono-tenant. **Ne pas** ajouter de colonne
  `organization_id` partout — c'est la stratégie 2 (multi-tenant en base
  partagée), qu'on ne fait **pas** pour l'instant.
- Le provisioning d'un nouveau client = un script `kernse/scripts/provision_client.sh`
  qui crée : dossier `/home/kernse/instances/<client>/`, service systemd,
  vhost nginx + certbot, DB vierge, superadmin initial, envoi d'email de
  bienvenue.
- Toute écriture inter-clients (statistiques agrégées, monitoring) passe par
  la **console plateforme** (voir plus bas), qui lit chaque DB séparément —
  jamais de JOIN cross-DB.

Le jour où on bascule vers du multi-tenant en base partagée (stratégie 3
hybride évoquée dans le brainstorm), on refactore `get_db()` pour résoudre
la DB par sous-domaine — le reste du code n'a pas à changer si on a bien
respecté la règle #1 (aucune donnée métier en dur).

---

## Console plateforme

À créer dans `kernse/app/platform/`. C'est **l'outil du superadmin
plateforme** (toi), pas de l'utilisateur final. Endpoints sous `/platform/*`
(pas `/settings/*`, qui reste l'admin d'organisation).

Fonctionnalités v1 (cf. brainstorm feuille 4) :

- Liste des instances clients (nom, plan, version déployée, dernier
  healthcheck, dernière connexion superadmin client).
- Provisionner / suspendre une instance (déclenche un script shell).
- Voir la version de code déployée par instance (`APP_VERSION` du process).
- Santé des instances (`/healthz` par client, alerte si KO).
- Usage (nombre d'utilisateurs actifs 30 jours, dossiers créés, stock lu) —
  agrégé pour piloter le pricing.

**Authentification console** : indépendante de l'auth cliente. La console
tourne sur un domaine séparé (`admin.kernse.com`) avec une auth
superadmin plateforme (email allowlist + 2FA obligatoire).

---

## Écriture de fichiers — règles Windows héritées

**Ces règles sont identiques à celles de `/CLAUDE.md` racine et s'appliquent
aussi dans `kernse/`.** Résumé opérationnel :

- **Fichiers > 1 Ko** : utiliser `cat > /sessions/<session>/mnt/MySifa/kernse/<path> << 'EOF'`
  via le shell sandbox, jamais `Write` ou `Edit`. Le drive réseau Windows
  tronque silencieusement.
- **Modifs chirurgicales** : `python3 -c "open('...').read().replace(...)"`
  ou `sed`. Toujours vérifier après avec `wc -l`, `tail -5`, et
  `python3 -c "import ast; ast.parse(open('<path>').read())"` pour du Python.
- **Comptage `\x00`** : `python3 -c "print(open('<path>','rb').read().count(b'\x00'))"`
  doit renvoyer 0.
- **Balance CSS `{` / `}`** : dans un fichier CSS, compter les accolades pour
  détecter une troncature qui passerait sous le radar.

Se référer au `/CLAUDE.md` racine (section « Outils — écriture de fichiers »
et « git : la troncature frappe aussi les commandes git côté Windows »)
pour le détail complet, y compris le cas des conflits git côté Windows et
PowerShell vs bash.

---

## Ton et style éditorial — précisions Kernse

Toutes les règles du `/CLAUDE.md` racine s'appliquent : pas d'emojis, ton
direct, messages factuels. **Précisions Kernse** :

- La landing publique et les argumentaires commerciaux (`kernse/docs/`,
  `kernse/landing/`) suivent la brand voice « Forge » (skill `forge-style`) :
  direct, factuel, humain, ancré local. **Pas** de langage agence
  (« solutions innovantes », « unlock your potential », « ROI significatif »).
- Le mot « Kernse » ne s'utilise **jamais** dans un message adressé à un
  utilisateur d'une instance cliente — c'est le nom que voit le patron qui
  achète, pas son opérateur. Sur l'atelier, l'utilisateur voit le nom de son
  entreprise ou le nom de marque qu'il a configuré.
- Copie interne (docs, notes brainstorm, README de dossier) : direct, sec,
  factuel — pas de storytelling. Le brainstorm principal
  (`brainstorm-kernse.html`) donne le ton.

---

## Points d'attention critiques (Kernse)

1. **Toujours vérifier qu'une nouvelle donnée métier a une porte de sortie de
   paramétrage.** Avant de merger une PR qui ajoute une valeur métier :
   « est-ce que je peux, en tant que superadmin d'une organisation cliente,
   changer cette valeur sans toucher au code ? ». Si non, la PR n'est pas
   prête.

2. **Aucun SELECT / INSERT dans `platform_settings` depuis le code métier.**
   Les tables plateforme sont lues uniquement par la console plateforme et
   les scripts de provisioning. Le code métier lit `client_settings`.

3. **Le seed d'une instance neuve démarre vide.** Un client Kernse qui vient
   d'être provisionné n'a **aucune** machine, **aucune** opération, **aucun**
   utilisateur (sauf le superadmin d'organisation créé par le provisioning).
   Les jeux de démarrage par métier sont proposés à l'onboarding, pas
   auto-appliqués.

4. **La démo Kernse (`mysifa-demo`) est un banc d'essai de la
   généralisation.** Si une fonctionnalité fonctionne sur la démo (qui n'est
   pas SIFA), c'est la preuve que la généralisation est bien faite. Toute
   nouvelle feature paramétrable doit être testée d'abord sur v1 avec les
   valeurs SIFA, puis sur la démo avec un jeu de valeurs différent.

5. **Ne jamais coder « en dur » de logique commerciale (plans, tarifs).**
   Le catalogue des plans (Kernse Atelier, Kernse Usine, pack imprimerie,
   pack RH) vit dans `platform_settings`, pas dans le code. Un nouveau plan
   se crée dans la console plateforme, pas dans un fichier Python.

6. **Frontière stricte code / branding.** `kernse/static/kernse.css` définit
   les tokens ; les pages métier dans `app/web/` importent ces tokens.
   Jamais de couleur codée dans une page métier, jamais de règle métier
   dans `kernse.css`.

---

## Ce qui reste dans MySifa/ — frontière stricte

Pour éviter la duplication et la dérive, voici ce qui **ne va PAS** dans
`kernse/` :

- Les routers et pages métier existants (`app/routers/`, `app/web/`) — on les
  modifie sur place pour les rendre paramétrables, on ne les recopie pas.
- Les migrations DB — toutes les migrations vivent dans
  `app/core/database.py`, y compris celles qui créent les tables
  paramètre-client (`machines`, `operations`, etc.).
- `config.py` — reste à la racine, c'est la source unique de vérité pour
  toutes les instances.
- Les scripts one-shot d'import, de repair, de backup existant — restent
  dans `/scripts/` et `/tools/` racine.

`kernse/` accueille **uniquement** le code neuf spécifique à la
commercialisation SaaS : console plateforme, provisioning, onboarding, seeds
métier, design system, landing publique.

---

## Règles racine qui s'appliquent aussi ici

Le `/CLAUDE.md` racine (MySifa) définit des règles commerciales et
opérationnelles qui s'appliquent intégralement à `kernse/`. Ne pas
dupliquer, se référer au fichier racine. Précisions Kernse :

- **Sécurité, secrets & audit trail** : tous les nouveaux scripts de
  provisioning (`kernse/scripts/*`) doivent aller chercher leurs
  secrets dans `.env` du VPS, jamais en argument de ligne de commande
  (visible dans `ps`). La console plateforme (`kernse/app/platform/`)
  est le seul endroit qui consomme et affiche l'audit log — pas de
  fuite d'audit dans les instances clientes.

- **Cycle de vie client** : le script `kernse/scripts/purge_client.sh`
  est le seul chemin de suppression définitive d'une instance. Il ne
  s'exécute que depuis la console plateforme, avec double confirmation
  et audit trail. Toute demande RGPD entrante passe par un endpoint
  dédié dans `kernse/app/platform/rgpd/`.

- **API versioning** : les routes publiques Kernse (utilisées par un
  front, un partenaire, un webhook Stripe) sont préfixées `/api/v1/`
  dès leur création — pas d'exception pour « on est encore en beta ».
  Les routes de la console plateforme (`/platform/*`) restent hors
  versioning tant qu'elles ne sont pas consommées hors du repo.

- **Emails transactionnels & SLA** : le guide de configuration DNS
  livré au client vit dans `kernse/docs/email-setup.md`. Les templates
  d'email paramétrables vivent dans `kernse/app/email_templates/`
  (Jinja2 avec variables `client_settings.branding_email_*`). Les
  playbooks incident vivent dans `kernse/docs/incidents/`.

- **Propreté du repo & DB** : les archives commerciales (anciennes
  landings, brainstorms périmés, plaquettes obsolètes) vont dans
  `kernse/docs/archives/`. Aucun brouillon à la racine de `kernse/`.
  Les tables spécifiques Kernse (`clients`, `platform_settings`,
  `clients_archived`, `audit_log`) suivent le même régime de VACUUM +
  purge que les tables métier.

---

## En cas de doute

- **Doute paramétrable / en dur** → paramétrable (règle #1).
- **Doute `kernse/` / `app/`** → si c'est une modif d'un module métier
  existant, `app/`. Si c'est du code neuf pour la commercialisation, `kernse/`.
- **Doute design MySifa / Kernse** → si tu touches à une page qui vit
  encore dans la DA MySifa (dark cyan), respecte la DA MySifa. Si tu crées
  une page dans `kernse/`, DA Kernse (clair navy/orange).
- **Doute général** → demander à Eugène plutôt qu'inventer une convention.

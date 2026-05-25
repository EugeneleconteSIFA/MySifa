# Roadmap MyExpé — Optimisation & automatisation des expéditions

Document de planification. À coder ensuite avec Cursor. Respecter les conventions de `CLAUDE.md` (objet d'état `S`, fonction `api()`, `escHtml`/`escAttr`, `showToast`, migrations numérotées dans `_migrate()`, variables CSS, terminologie métier, sans emojis).

---

## 1. Contexte & objectif

La collègue qui gère les transports passe d'un temps plein à un mi-temps (matins uniquement). Objectif : rendre MyExpé suffisamment outillé pour qu'une demi-journée suffise à piloter les expéditions, sans perte de qualité ni de marge. Pas de deadline dure — on vise l'outil idéal et on le construit proprement.

**Volumes (base de dimensionnement) :** 30 à 50 envois / semaine, dont 5 à 10 en affrètement. Site d'expédition : Roubaix (59).

**Lecture stratégique — deux mondes distincts :**

| Type d'envoi | Volume/sem | Tarification | Outil qui rentabilise |
|---|---|---|---|
| Messagerie / ramasse (< 6 palettes) | ≈ 25-40 | Grille (poids × zone) | **Comparateur de prix** |
| Affrètement (> 6 palettes) | ≈ 5-10 | Spot / au coup par coup, souvent urgent | **Prospection parallèle** |

Le comparateur sert le gros du volume récurrent ; la prospection sert les coups urgents et la mise en concurrence ponctuelle. Les deux se complètent.

---

## 2. État des lieux (mai 2026)

| Brique | État actuel | Verdict |
|---|---|---|
| Départs (`expe_departs`) | CRUD + validation (en_attente → valide), recherche, index. Migration v13. | En prod, solide |
| Transporteurs (`expe_transporteurs`) | CRUD, zones (flags), taxe carburant, contact, upload fichier tarif. Migration v39, seed v44. | En prod, solide |
| Carte France des délais | SVG data-driven, recherche CP/ville (geo.api.gouv.fr), mode édition, coloration par zone | Très abouti **mais délais en `localStorage`** (par navigateur, non partagé) |
| Comparateur | `static/transport_comparateur.jsx` existe mais non intégré. Aucune API, aucune logique. | **Stub à construire** |
| Tarifs transporteurs | Stockés comme **fichiers uploadés** (PDF/Excel/images) | **Non exploitables automatiquement** — c'est le nœud |
| Prospection | Seul un `mailto:` "Demande de tarif SIFA" mono-transporteur | À construire |

**Transporteurs seedés (v44) :** Coupé (max 5 pal.), Ceva (max 4 pal.), Coquelle (max 33 pal.), Dimotrans (max 28 pal.). DSV est cité mais absent du seed → non intégré pour l'instant (décision du 25/05/2026).

---

## 3. Principes directeurs

- **Une seule source de vérité, en base.** On supprime toute logique métier en `localStorage` (les délais notamment) : les données doivent être partagées entre tous les utilisateurs et auditables.
- **Human-in-the-loop sur tout ce qui touche au prix.** Aucune grille tarifaire extraite automatiquement (skill ou IA) ne devient « active » pour le comparateur sans validation humaine. Une erreur de tarif = une erreur d'argent.
- **Le comparateur ne décide pas seul.** Il classe par prix mais affiche aussi le délai et l'éligibilité, parce que « le moins cher » n'est pas toujours le bon choix pour un envoi urgent.
- **Réutiliser l'existant.** La carte des délais, les zones transporteurs, le `mailto` RFQ et le modèle `expe_departs` sont de bonnes fondations — on les étend, on ne les remplace pas.
- **Conventions MySifa strictes.** Migrations numérotées et idempotentes, seeds `INSERT OR IGNORE`, focus searchbar préservé, toasts (jamais `alert()`), variables CSS, ton factuel sans emojis.

---

## 4. Dette technique à corriger au passage

Ces trois points bloquent ou fragilisent les chantiers à venir. À traiter dans le Chantier 0.

1. **`expe_departs.transporteur` est un champ TEXTE**, pas une clé étrangère vers `expe_transporteurs.id`. Conséquence : impossible de relier proprement un départ à ses tarifs/zones. → Ajouter `transporteur_id INTEGER` (FK), conserver le texte en libellé d'affichage pour la rétrocompat.
2. **Les capacités sont codées en dur en JS** (`EXPE_TRP_META` dans `expe_assets.py` : `palMax`, `poids`, `palette`). → Migrer ces métadonnées en colonnes de `expe_transporteurs` pour qu'elles soient éditables et exploitables côté serveur (moteur comparateur).
3. **Les délais carte sont en `localStorage`** (clé `mysifa_expe_delais_v2`). → Migrer vers une table `expe_delais` (Chantier 3).

---

## 5. Chantier 0 — Fondation : tarifs structurés

> **Prérequis absolu du comparateur.** Tant que les tarifs sont des PDF, rien ne se compare. Ce chantier transforme les grilles en données.

### 5.1 Modèle de données

Nouvelle table `expe_tarifs` (lignes tarifaires normalisées) :

```sql
CREATE TABLE IF NOT EXISTS expe_tarifs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transporteur_id INTEGER NOT NULL,
    type_envoi      TEXT NOT NULL,          -- 'messagerie' | 'ramasse' | 'affretement'
    zone            TEXT NOT NULL,          -- code département '59', ou libellé zone 'IDF' / 'NATIONAL'
    poids_min       REAL NOT NULL DEFAULT 0,-- borne basse de la tranche (kg)
    poids_max       REAL,                   -- borne haute (NULL = illimité)
    prix            REAL NOT NULL,          -- montant unitaire
    unite           TEXT NOT NULL,          -- 'forfait' | 'au_100kg' | 'au_kg' | 'par_palette' | 'par_tonne'
    mini_perception REAL,                   -- forfait minimum de perception (mini de fret)
    valid_from      TEXT,                   -- début de validité
    valid_to        TEXT,                   -- fin de validité (NULL = en cours)
    actif           INTEGER DEFAULT 0,      -- 0 = brouillon importé, 1 = validé et utilisable
    source_filename TEXT,                   -- fichier d'origine
    created_at      TEXT,
    created_by_email TEXT,
    FOREIGN KEY (transporteur_id) REFERENCES expe_transporteurs(id)
);
CREATE INDEX IF NOT EXISTS idx_expe_tarifs_lookup
    ON expe_tarifs(transporteur_id, type_envoi, zone, actif);
```

Colonnes à ajouter sur `expe_transporteurs` (frais qui s'appliquent par-dessus la grille) :

```
taxe_carburant_pct   REAL   -- existe déjà
taxe_securite_pct    REAL   -- taxe sûreté/sécurité (souvent un %)
frais_dossier        REAL   -- frais fixes par expédition
palette_max          INTEGER-- migré depuis EXPE_TRP_META.palMax
accepte_poids        INTEGER-- migré depuis EXPE_TRP_META.poids
accepte_palette      INTEGER-- migré depuis EXPE_TRP_META.palette
```

> Note conventions : numéroter ces migrations à partir du prochain numéro libre dans `_migrate()` (au 25/05/2026 la dernière est ≥ v59 — vérifier le max avant d'assigner). Une migration par changement logique.

### 5.2 Skill d'import tarifaire (Cowork) — `import-tarif-transporteur`

Skill réutilisable qui prend la grille d'un transporteur (Excel ou PDF) et produit un fichier CSV/JSON **normalisé au schéma `expe_tarifs`** ci-dessus, prêt à importer.

Le skill encode la connaissance des grilles de transport françaises pour fiabiliser l'extraction :
- tranches de poids (0-9, 10-19, … 100-499 au 100 kg, 500-999, 1000-1999, lots/affrètement) ;
- prix « au 100 kg » vs forfait vs par palette ;
- « mini de perception » / mini de fret ;
- zones par département depuis Roubaix (59), regroupements éventuels (IDF, national) ;
- distinction messagerie / ramasse / affrètement.

Livrable du skill : un CSV avec une ligne = une cellule de grille (transporteur, type_envoi, zone, poids_min, poids_max, prix, unite, mini_perception), importable via un endpoint d'upload CSV → `expe_tarifs` (en `actif=0`, à valider).

> C'est l'outil « batch » : tu déposes les grilles, le skill les normalise, tu importes. Idéal pour la mise en route (digitaliser les 4-5 grilles existantes).

### 5.3 Parsing direct dans MySifa via clé API Anthropic — réponse à ta question

**Oui, c'est faisable**, et c'est la version « self-service » du skill (même schéma cible, donc on mutualise le prompt d'extraction).

Principe :
- Ajouter `ANTHROPIC_API_KEY` dans `.env` (**jamais exposée au frontend** — appel serveur uniquement).
- Nouvel endpoint `POST /transporteurs/{id}/tarif/parse` : lit le fichier tarif déjà uploadé, l'envoie à l'API Anthropic avec un prompt d'extraction structurée renvoyant du JSON conforme à `expe_tarifs`. Pour un Excel, convertir d'abord en CSV/texte ; pour un PDF, l'envoyer en document.
- La réponse JSON est insérée en `actif=0`, puis affichée dans un **écran de validation** (tableau éditable) ; rien n'est utilisé par le comparateur tant que l'utilisateur n'a pas passé les lignes en `actif=1`.

Garde-fous :
- **Human-in-the-loop obligatoire** avant activation (cf. principe directeur).
- Clé serveur uniquement, jamais dans le HTML/JS rendu.
- Coût négligeable (quelques centimes par grille), mais limiter le nombre d'appels (un parse manuel déclenché par bouton, pas en boucle).
- Historiser le fichier source + la date de parsing.

> Recommandation : construire d'abord 5.1 (schéma) + 5.2 (skill) pour valider que le format de sortie est bon sur tes vraies grilles, puis brancher 5.3 (endpoint) en réutilisant le même prompt. Le skill sert aussi de « spécification vivante » du prompt.

---

## 6. Chantier 1 — Comparateur de prix (priorité #1)

### 6.1 Moteur de calcul

Entrée : un envoi `{ poids_total_kg, nb_palette, code_postal_destination, type_envoi }`.

Algorithme (côté serveur) :
1. Déduire le **département** depuis le code postal (2 premiers caractères, gérer Corse 2A/2B et DOM 97x).
2. **Filtrer les transporteurs éligibles** : `actif=1` ; zone du type d'envoi cochée (`zone_messagerie` / `zone_affretement` / `zone_france` / `zone_france_hors_paris`) ; `nb_palette <= palette_max` ; type accepté (poids/palette).
3. Pour chaque éligible, **trouver la ligne tarifaire** `expe_tarifs` correspondante (`actif=1`, `type_envoi`, `zone` = département ou groupe de zones, `poids_total_kg` dans `[poids_min, poids_max)`).
4. **Calculer le prix de base** selon `unite` :
   - `au_100kg` → `prix * poids_total_kg / 100`
   - `par_palette` → `prix * nb_palette`
   - `au_kg` → `prix * poids_total_kg`
   - `forfait` → `prix`
   - appliquer `max(base, mini_perception)`.
5. **Ajouter les frais** : `base * (1 + taxe_carburant_pct/100) * (1 + taxe_securite_pct/100) + frais_dossier`.
6. **Croiser le délai** depuis `expe_delais` (Chantier 3 ; fallback sur la donnée carte actuelle en attendant).
7. **Trier par prix croissant**, marquer le moins cher, exposer aussi un tri par délai.

Les transporteurs non éligibles sont renvoyés séparément avec la **raison** (« hors zone », « > 5 palettes », « pas de grille pour ce poids ») — utile pour repérer les trous de tarif.

### 6.2 Endpoint

`POST /expe/comparateur` → `{ eligibles: [{ transporteur, prix_ht, detail_calcul, delai_jours }], non_eligibles: [{ transporteur, raison }] }`.

### 6.3 UI

- Formulaire d'envoi (poids, palettes, CP, type) → tableau classé par prix.
- Badge « moins cher », colonne délai (J+N), colonne éligibilité.
- Détail du calcul au survol/clic (base, carburant, mini de perception) — la transparence évite les mauvaises surprises sur facture.
- **Bouton « Comparer » directement sur une ligne de `expe_departs`** : pré-remplit le formulaire depuis le départ (poids, palettes, CP) — c'est le geste quotidien le plus fréquent.

---

## 7. Chantier 2 — Prospection parallèle (priorité #2)

Couvre tes réponses **4a** (générer + envoyer + centraliser) et **4c** (élargir la base).

### 7.1 Modèle de données

```sql
CREATE TABLE IF NOT EXISTS expe_demandes_devis (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    depart_id   INTEGER,                 -- lien optionnel vers expe_departs
    poids_total_kg REAL, nb_palette REAL,
    code_postal_destination TEXT, type_envoi TEXT,
    contraintes TEXT,                    -- délai souhaité, contraintes particulières
    statut      TEXT,                    -- 'ouverte' | 'cloturee'
    created_at  TEXT, created_by_email TEXT
);

CREATE TABLE IF NOT EXISTS expe_devis_reponses (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    demande_id  INTEGER NOT NULL,
    transporteur_id INTEGER,
    prix        REAL, delai_jours INTEGER, commentaire TEXT,
    statut      TEXT,                    -- 'envoyee' | 'recue' | 'retenue' | 'refusee'
    sent_at     TEXT, recu_at TEXT,
    FOREIGN KEY (demande_id) REFERENCES expe_demandes_devis(id)
);
```

### 7.2 Envoi parallèle

- À partir d'un envoi, sélectionner N transporteurs éligibles (filtre zone/capacité, comme le comparateur) **et/ou** des prospects (cf. 7.4).
- Générer un **RFQ standardisé** (réutiliser et industrialiser le gabarit `mailto` « Demande de tarif SIFA » déjà présent) : objet + corps pré-remplis avec poids, palettes, destination, délai souhaité.
- Envoi par **SMTP serveur au nom de l'utilisateur connecté** (`From` / `Reply-To` = email de session, depuis `S.user`), avec **`expeditions@sifa.pro` systématiquement en copie (CC)** pour que la boîte partagée garde une trace de toutes les demandes — quel que soit l'utilisateur qui les envoie. Une ligne `expe_devis_reponses` par transporteur en `statut='envoyee'`.

### 7.3 Centralisation des réponses

- Écran « Demande #X » listant les transporteurs sollicités et l'état de chaque réponse.
- **V1 retenue — saisie manuelle** du prix/délai reçu, puis comparaison côte à côte et bouton « Retenir » → peut créer/mettre à jour le départ avec le transporteur choisi.
- V2 (option) — **parsing assisté des emails de réponse** : au lieu de ressaisir prix et délai, MySifa lit automatiquement l'email de réponse du transporteur et en extrait prix / délai / conditions pour pré-remplir la comparaison (même brique IA qu'en 5.3). Nécessite un accès en lecture à `expeditions@sifa.pro` (IMAP ou transfert dédié). Non prioritaire.

### 7.4 Élargir la base transporteurs (sourcing — réponse 4c)

- **Vraie base de prospects entretenue** dans MySifa (table dédiée `expe_transporteurs_prospects`) : transporteurs candidats avec zone(s) couverte(s), type (messagerie/affrètement), capacité, contact, **statut de démarchage** (`a_contacter` / `en_discussion` / `reference` / `ecarte`) et notes. Un prospect passé en `reference` peut être promu en transporteur actif (`expe_transporteurs`).
- Vue « Trouver un transporteur » filtrable par zone + type + capacité, couvrant transporteurs actifs **et** prospects, pour les cas où aucun historique ne dessert le besoin (ex. affrètement urgent vers une zone mal couverte).
- **DSV** : non intégré pour l'instant (décision du 25/05/2026).

---

## 8. Chantier 3 — Carte des délais industrialisée (priorité #3)

Le widget est déjà excellent ; il faut le fiabiliser et l'enrichir.

### 8.1 Migration `localStorage` → base

```sql
CREATE TABLE IF NOT EXISTS expe_delais (
    departement     TEXT NOT NULL,       -- '01'..'95', '2A','2B','971'..
    type_envoi      TEXT NOT NULL,       -- 'messagerie' | 'ramasse' | 'affretement' | 'default'
    transporteur_id INTEGER,             -- NULL = délai générique
    delai_jours     INTEGER,             -- J+N depuis Roubaix (59)
    zone_label      TEXT,                -- pour la coloration carte
    updated_at      TEXT, updated_by_email TEXT,
    PRIMARY KEY (departement, type_envoi, transporteur_id)
);
```

- Seed initial depuis `expe_france_delais_data.py` (défauts existants).
- Le mode édition de la carte écrit désormais en base (endpoint `PUT /expe/delais`), plus en `localStorage` → délais partagés et audités.
- Restreindre l'écriture aux rôles déjà autorisés (`superadmin`, `direction`, `administration`, `expedition` — cf. `expeCanWrite`).

### 8.2 Délais par type d'envoi et par transporteur

- Aujourd'hui la coloration distingue déjà messagerie / affrètement / France / hors Paris. On rend les **délais** eux aussi dépendants du type d'envoi et, à terme, du transporteur.
- Croisement avec le comparateur (Chantier 1) : afficher le délai réel à côté du prix de chaque transporteur.

---

## 9. Chantier 4 — Automatisations du quotidien

Couvre tes réponses **3b** (suivi & relances) et **3c** (planning ramasses) — les deux postes les plus chronophages après le choix du transporteur.

### 9.1 Suivi & relances de livraison (3b)

- Étendre `expe_departs` d'un statut de livraison (`expediee`, `livree`, `retard`, `litige`) et d'une `date_livraison_reelle`.
- Vue « En transit » : départs validés non encore livrés, triés par date prévue, avec alerte visuelle sur les retards (au-delà du J+N attendu).
- Relances : génération d'un email de relance pré-rempli au transporteur (réutilise la brique SMTP du Chantier 2). Tâche planifiée quotidienne optionnelle qui signale les livraisons en retard.

### 9.2 Planning des ramasses (3c)

- Vue calendrier/semaine des enlèvements (`date_enlevement` existe déjà sur `expe_departs`), regroupés par transporteur et par créneau.
- Objectif : coordonner les ramasses d'un coup d'œil, regrouper les enlèvements d'un même transporteur le même jour.

---

## 10. Chantier 5 (option, plus tard) — Contrôle des factures transport

Non prioritaire (tu n'as pas coché 3d), mais à garder en réserve : rapprochement automatique facture transporteur ↔ tarif négocié + devis retenu, pour détecter les écarts de facturation. Devient quasi gratuit une fois `expe_tarifs` en place.

---

## 11. Séquencement recommandé & dimensionnement

| Ordre | Chantier | Dépend de | Taille | Valeur |
|---|---|---|---|---|
| 1 | **0 — Tarifs structurés** (schéma + skill + parsing API) | — | L | Débloque tout |
| 2 | **1 — Comparateur** | 0 | M | Couvre le gros du volume |
| 3 | **3.1 — Délais en base** | — (parallélisable) | S | Fiabilise + alimente le comparateur |
| 4 | **2 — Prospection parallèle** | base SMTP | M-L | Couvre l'affrètement urgent |
| 5 | **3.2 — Délais par type/transporteur** | 3.1 | S | Enrichit |
| 6 | **4 — Automatisations (suivi, ramasses)** | — | M | Gain quotidien |
| 7 | **5 — Contrôle factures** (option) | 0 | S | Bonus marge |

Tailles indicatives : S ≈ une session, M ≈ quelques sessions, L ≈ chantier à étapes.

> Le chemin critique est **0 → 1**. Tout le reste peut avancer en parallèle. Démarrer par digitaliser les 4-5 grilles existantes (skill 5.2) donne immédiatement de la matière pour tester le comparateur.

---

## 12. Décisions arbitrées (25/05/2026)

1. **SMTP** — Tranché : l'email part **au nom de l'utilisateur connecté** (`From` / `Reply-To` = email de session), avec **`expeditions@sifa.pro` toujours en copie** pour la traçabilité dans la boîte partagée.
2. **Structure des grilles** — En attente : Eugène fournit des modèles de grilles tarifaires. Le champ `zone` de `expe_tarifs` et le skill d'import seront calibrés sur ces formats réels (département individuel vs grandes zones vs couples origine-destination).
3. **Réponses aux devis** — Tranché : **saisie manuelle en V1**. Le parsing email automatique (V2) reste une option ultérieure (cf. §7.3).
4. **DSV** — Tranché : **non intégré pour l'instant**.
5. **Sourcing** — Tranché : **vraie base de prospects entretenue** dans MySifa, avec statut de démarchage et promotion possible en transporteur actif (cf. §7.4).

---

## 13. Annexe — Proposition d'annonce MAJ (à publier au fil des livraisons)

À insérer via `POST /api/updates` (scope `expe`) quand un chantier est livré, en suivant le template de `CLAUDE.md`. Exemple pour la livraison du comparateur :

- Titre : `Expéditions — Comparateur de prix`
- Nouveautés : choix du transporteur le moins cher en quelques secondes (taxe carburant et mini de perception inclus) ; comparaison directe depuis une ligne de départ ; affichage du délai à côté du prix.
- Corrections : délais de livraison désormais partagés entre tous les postes (fin du stockage local par navigateur).

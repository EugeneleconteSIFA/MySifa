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

> Schéma **calibré sur 4 grilles réelles** (CEVA, TRANSBENELUX, compte 100346, DSV XPress) — voir l'Annexe B pour le détail des formats observés.

Nouvelle table `expe_tarifs` (lignes tarifaires normalisées) :

```sql
CREATE TABLE IF NOT EXISTS expe_tarifs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transporteur_id INTEGER NOT NULL,
    type_envoi      TEXT NOT NULL,          -- 'messagerie' | 'ramasse' | 'affretement' | 'express_intl'
    base_calcul     TEXT NOT NULL,          -- AXE de la grille : 'poids' (kg) | 'palette' (nb) | 'metre_plancher' (ML)
    zone_type       TEXT NOT NULL,          -- 'departement' | 'code_postal' | 'zone_intl' | 'pays'
    zone_valeur     TEXT NOT NULL,          -- '59' | '59200' | '7' (zone intl) | 'DE'
    tranche_min     REAL NOT NULL DEFAULT 0,-- borne basse (dans l'unité de base_calcul)
    tranche_max     REAL,                   -- borne haute (NULL = illimité)
    prix            REAL NOT NULL,
    unite           TEXT NOT NULL,          -- 'forfait' (= total de la tranche) | 'au_100kg' | 'au_kg'
    mini_perception REAL,                   -- mini de perception / mini de fret
    valid_from      TEXT,
    valid_to        TEXT,                   -- NULL = en cours
    actif           INTEGER DEFAULT 0,      -- 0 = brouillon importé, 1 = validé et utilisable
    source_filename TEXT,
    created_at      TEXT,
    created_by_email TEXT,
    FOREIGN KEY (transporteur_id) REFERENCES expe_transporteurs(id)
);
CREATE INDEX IF NOT EXISTS idx_expe_tarifs_lookup
    ON expe_tarifs(transporteur_id, type_envoi, zone_type, zone_valeur, actif);
```

> Le couple `base_calcul` + `tranche_min/max` remplace `poids_min/max` : une grille palette s'indexe sur le **nombre de palettes** (TRANSBENELUX : 1 à 18), une grille messagerie sur le **poids**. Pour les grilles palette/mètre plancher, `unite='forfait'` et le prix lu EST le total (ex. 2 palettes ≠ 2 × le prix d'1 palette).

Nouvelle table `expe_tarifs_frais` (frais annexes par transporteur — les grilles CEVA en comptent une douzaine) :

```sql
CREATE TABLE IF NOT EXISTS expe_tarifs_frais (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    transporteur_id INTEGER NOT NULL,
    libelle         TEXT NOT NULL,          -- 'Gasoil', 'Taxe sûreté/sécurité', 'Prise de RDV', 'Ville excentrée'...
    mode            TEXT NOT NULL,          -- 'pct_transport' | 'forfait_expedition' | 'par_palette'
    valeur          REAL NOT NULL,
    mini            REAL,                   -- minimum de facturation éventuel
    applique_defaut INTEGER DEFAULT 1,      -- 1 = inclus auto dans le comparateur ; 0 = option à cocher
    FOREIGN KEY (transporteur_id) REFERENCES expe_transporteurs(id)
);
```

Colonnes à ajouter sur `expe_transporteurs` (limites de service, migrées depuis `EXPE_TRP_META` codé en JS) :

```
palette_max          INTEGER-- nb max de palettes (Coupé 5, Ceva 4, Coquelle 33, Dimotrans 28)
poids_max_kg         REAL   -- plafond de poids du service (ex. CEVA messagerie : 2000 kg)
accepte_poids        INTEGER-- migré depuis EXPE_TRP_META.poids
accepte_palette      INTEGER-- migré depuis EXPE_TRP_META.palette
```

> `taxe_carburant_pct` existe déjà sur `expe_transporteurs` mais est désormais doublonné par une ligne `Gasoil` dans `expe_tarifs_frais` — choisir l'un des deux à la migration (recommandé : tout passer en `expe_tarifs_frais` pour homogénéiser, et garder `taxe_carburant_pct` en lecture seule le temps de la bascule).
>
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
3. Pour chaque éligible, **trouver la ligne tarifaire** `expe_tarifs` correspondante : `actif=1`, `type_envoi`, résolution de zone **du plus précis au plus large** (`code_postal` exact → `departement` → `zone_intl`/`pays`), et valeur de la `base_calcul` (poids en kg, nb de palettes, ou mètre plancher) dans `[tranche_min, tranche_max)`.
4. **Calculer le prix de base** selon `unite` :
   - `forfait` → `prix` (le prix EST le total de la tranche — grilles palette / mètre plancher, et tranches messagerie ≤ 100 kg)
   - `au_100kg` → `prix * poids_total_kg / 100` (tranches messagerie > 100 kg)
   - `au_kg` → `prix * poids_total_kg`
   - puis `max(base, mini_perception)`.
5. **Ajouter les frais** depuis `expe_tarifs_frais` : appliquer le gasoil (`pct_transport`) puis les frais `applique_defaut=1` (sûreté/sécurité…), chacun avec son `mini`. Les frais optionnels (prise de RDV, ville excentrée, hayon…) sont proposés en cases à cocher dans l'UI.
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

---

## 14. Annexe B — Formats de grilles tarifaires observés (4 exemples réels)

Analysés le 25/05/2026 à partir des fichiers fournis. Sert de référence pour le skill d'import (5.2) et le parsing in-app (5.3). Origine d'expédition commune : **59 Roubaix / Tourcoing**.

### B.1 Compte 100346 — « SIFA 010126 - P U » (xlsx, 2 feuilles)

- **Feuille POIDS** (messagerie) : colonne A = `(NN) DÉPARTEMENT`, colonne B = n° département. Ligne d'en-tête « DE / A » = tranches de poids : 0-10, 10-20, … 90-100 (unité **Forfait**), puis 100-250, 250-500, 500-1000 (unité **Prx/100Kg**). Une cellule = un prix.
- **Feuille PALETTE** : mêmes départements en lignes, colonnes = 1 à 5 palettes, unité **Forfait** (le prix est le total pour N palettes).
- Corse (20) = lignes vides → pas de tarif (à gérer comme « non desservi »).
- → `zone_type='departement'`, `base_calcul='poids'` (feuille 1) et `'palette'` (feuille 2).

### B.2 CEVA Logistics — « TARIFS GN et PAL » (xlsx, 4 feuilles)

- **Tarifs Messagerie Poids** : colonne « Département / zone Code Postal » → **certaines zones sont au code postal, pas au département**. Tranches forfait 1-10…91-100, puis **Prix au 100 kg** de 101-200 jusqu'à 1001-1500 kg. ~2200 lignes.
- **Tarifs Palettes (SmartPal)** : par département, 1-4 palettes, avec équivalence **mètre plancher** (0,4 / 0,8 / 1,2 / 1,6 m). Norme : 1 à 6 palettes, poids max 800 kg/palette, hauteur max 2 m.
- **Conditions commerciales** : nombreux frais annexes → alimentent `expe_tarifs_frais` : Technic (date impérative) 25 % min 12 €, Dynamic (délai garanti) 30 % min 15 €, 2ᵉ présentation 60 % min 25 €, ville excentrée/montagne forfait 16 € + 12 €/palette, prise de RDV 6 €, **taxe sûreté/sécurité 1,90 €/expédition**, My CO2tribution 0,63 €, centres urbains 6,50 €, frais de mesure 9 €, enlèvement ponctuel 28 €, retour 30 €. Norme messagerie : ≤ 5 palettes et 2000 kg.
- → `zone_type` mixte (`departement` + `code_postal`), `base_calcul='poids'` et `'palette'`, + `expe_tarifs_frais` riche.

### B.3 TRANSBENELUX — « SIFA VERS FRANCE 2026 » (xlsx)

- Unité de tarif **MP (mètre plancher)**. Lignes = départements (FR01…), colonnes = **1 à 18 palettes** 80×120 (avec plage de mètres plancher associée). Couvre la zone affrètement (> 6 palettes).
- Codes de lecture : FO = forfaitaire, PU = prix unitaire, PP = payant pour.
- → `zone_type='departement'`, `base_calcul='palette'` (ou `'metre_plancher'`), `unite='forfait'`.

### B.4 DSV XPress — « DSV_SIFA_26618 » (pdf, 16 pages) — hors périmètre actuel

- Produit **express international** : zones 1-15 (mapping pays → zone), prix au poids par paliers de 0,5 kg (documents / marchandises), + table de **délais de livraison par pays**.
- → `type_envoi='express_intl'`, `zone_type='zone_intl'`/`'pays'`, `base_calcul='poids'`. Documenté pour mémoire ; **non intégré pour l'instant** (décision §12).

### Conclusions pour l'import

1. Le skill doit détecter l'**axe** de chaque feuille (poids / palette / mètre plancher) et le **type de zone** (département vs code postal vs zone-pays).
2. Les tranches sont à **bornes variables** d'un transporteur à l'autre → toujours extraire les bornes réelles depuis les lignes d'en-tête « DE / A », ne jamais présumer un découpage fixe.
3. Distinguer dans une même grille les tranches **forfait** (≤ 100 kg, ou par palette) des tranches **au 100 kg** (> 100 kg).
4. Extraire les **frais annexes** depuis les feuilles « Conditions » vers `expe_tarifs_frais`.
5. Toujours passer par une **validation humaine** avant `actif=1` (cf. principe directeur).

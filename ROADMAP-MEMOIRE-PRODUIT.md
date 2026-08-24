# MyProd — Mémoire produit

> Une référence produit qui repasse en fabrication doit arriver avec tout ce
> qu'on a appris les fois précédentes.

---

## 1. Ce que c'est — et ce que ce n'est pas

Ce n'est **pas un module de plus**. C'est **un seul objet** — la référence
produit — rendu accessible depuis les endroits où les gens travaillent déjà.

```
                    ┌─────────────────────────────┐
                    │   LA RÉFÉRENCE PRODUIT      │
                    │        1013/0068            │
                    ├─────────────────────────────┤
                    │  Séries      (calculé)      │
                    │  Documents   (OF scannés)   │
                    │  Savoirs     (saisi)        │
                    └──────────────┬──────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
   ┌─────┴──────┐         ┌────────┴────────┐       ┌────────┴────────┐
   │ SAISIEPROD │         │ MyProd          │       │ MyProd          │
   │            │         │ Fiches + OF     │       │ Fiche produit   │
   │ bouton     │         │ (existant,      │       │ (vue complète)  │
   │ Historique │         │  enrichi)       │       │                 │
   │ opérateur  │         │ atelier/méthodes│       │ tout le monde   │
   └────────────┘         └─────────────────┘       └─────────────────┘
```

**Le point de bascule** : les notes de production existent déjà — elles sont
manuscrites sur les OF papier que ton collègue scanne en fin de dossier. Ce
n'est pas un corpus à créer, c'est un corpus à brancher. La saisie numérique
(commentaires, savoirs) vient **compléter** ce flux, pas le remplacer.

---

## 2. Décisions actées

| Sujet | Décision |
|---|---|
| **Clé produit** | La référence portée par la fiche technique rattachée au dossier — `ref_produit_norm` (`XXX/NNNN`). Machine, laize et conditionnement sont des attributs de la **série**, jamais de la clé. |
| **Savoirs** | Saisie libre par l'opérateur, publiés immédiatement. Pas de circuit de validation. |
| **Restitution Saisieprod** | Un **bouton « Historique »**, visible **uniquement** si la référence a déjà été produite. Aucune modale, aucun blocage, aucun accusé de lecture. |
| **Fiches + OF** | On **enrichit l'onglet existant**, on ne crée pas un second endroit où chercher la même chose. |
| **Scans d'OF terminés** | Arrivent dans un **dossier réseau** (scan-to-folder), **un PDF = un OF**. |
| **Annotations manuscrites** | **Consultables, sans plus.** Pas de lecture automatique, pas d'extraction IA. Le scan s'ouvre, on lit. |
| **Priorités** | Rattachement d'abord, puis la fiche produit, puis le bouton Saisieprod, puis les scans, puis les savoirs. Le chiffrage vient en dernier. |

---

## 3. Les trois portes

### Porte 1 — Saisieprod : le bouton « Historique »

**Qui :** l'opérateur, en calage ou en cours de production.
**Quand :** à tout moment, sur le dossier en cours.
**Condition d'affichage :** le bouton **n'existe pas** si la référence n'a jamais
été produite. Pas de bouton grisé, pas de « aucun historique » — rien. Sa seule
présence est l'information : *« ce produit est déjà passé »*.

**Ce qu'il ouvre** (panneau, pas modale bloquante) :

```
1013/0068 — ÉTIQUETTE LOGISTIQUE          4 productions
─────────────────────────────────────────────────────────
Dernière : 12/03/2026 · Cohésio 2 · DUPONT
  calage 47 mn · 12 400 m · 118 m/mn
  arrêts : 54 Problème Impressions (32 mn)
  [OF scanné]

Avant : 08/11/2025 · Cohésio 2 · MARTIN
  calage 39 mn · 9 800 m · 121 m/mn
  [OF scanné]

+ 2 productions plus anciennes            [tout voir]
─────────────────────────────────────────────────────────
NOTES
« Contre-partie à régler 2/10e plus bas, sinon casse
  échenillage en fin de bobine. »  — DUPONT, 12/03/2026
                                            [+ ajouter]
```

Le bouton compte peu de lignes de code : la condition d'affichage est un
`COUNT(*)` sur `produit_series` pour la référence du dossier en cours, déjà
chargée par `/api/fabrication/dossier-en-cours`.

### Porte 2 — MyProd › Fiches + OF : l'existant, enrichi

L'onglet **OF** liste déjà tous les OF importés, cherchables par référence :
c'est **déjà** l'historique des dossiers d'une même référence. On ne le double
pas, on le complète :

- une colonne **« Réf. produit »** (aujourd'hui implicite dans le libellé) ;
- un **regroupement / filtre par référence produit** — voir les 4 OF de
  `1013/0068` d'un coup plutôt que de les chercher à la main ;
- sur chaque ligne : pastille **scan disponible** et pastille **notes** ;
- un lien **« Fiche produit »** qui ouvre la vue complète (porte 3).

Idem sur l'onglet **Fiches techniques** : la fiche pointe vers sa fiche produit.

### Porte 3 — MyProd › Fiche produit : la vue complète

Nouvelle page, atteinte depuis les portes 1 et 2 (jamais un onglet de plus dans
la barre principale — c'est une **vue de détail**, pas une section).

- **Identité** — depuis la fiche technique : format, laize, support, couleurs,
  machines vues, clients.
- **Séries** — tableau + courbes : calage, vitesse, gâche, arrêts par série.
  On voit la dérive, pas juste le dernier chiffre.
- **Documents** — les OF terminés scannés, du plus récent au plus ancien.
- **Savoirs** — les notes saisies, épinglées en tête.
- **Matières et outillages** réellement employés, NC liées.

---

## 4. Ce qui existe déjà — et qu'on ne refait pas

| Brique | Où | Ce qu'elle donne |
|---|---|---|
| `normalize_ref_produit()` / `parse_fiche_reference()` | `app/services/fiche_ref_parser.py` | `"1013/0068 - COHESIO 2 - L570"` → clé + machine + laize + conditionnement |
| `planning_entries.ref_produit_norm` | triggers `trg_pe_ref_produit_norm_*` | la clé produit du dossier, maintenue automatiquement |
| `fiches_techniques.ref_produit_norm` | triggers `trg_ft_ref_produit_norm_*` | la clé produit de la fiche |
| `POST /api/admin/backfill-ref-produit-norm` | `of_import.py` l. 1096 | **le backfill existe déjà**, avec `dry_run` |
| `compute_dossier_times()` / `stats_dossier()` | `app/services/dossier_stats.py` | calage / prod / arrêt, métrage, étiquettes, vitesse — par dossier |
| `OPERATION_SEVERITY` | `config.py` + `operations.json` | catégorisation des codes (`arret`, `calage`, `appro`…) |
| `print_agents` (token + heartbeat) | migration `print_agents` | **le patron d'agent local** réutilisable tel quel pour le dossier de scans |
| `/api/bridge/*` | `app/routers/api_bridge.py` | l'authentification poste → serveur, déjà éprouvée avec Access |

**La jointure produit ↔ production existe déjà :**

```
production_data.no_dossier → planning_entries.reference
                           → planning_entries.ref_produit_norm
                           → fiches_techniques.ref_produit_norm
```

Le chantier consiste à **matérialiser** cette chaîne, pas à l'inventer.

---

## 5. Modèle de données

Trois tables, trois migrations (`app/core/migrations/AAAA_MM_JJ_sujet.py`).

### 5.1 `produit_series` — l'historique factuel

Un enregistrement = une production passée. Snapshot **figé** à la clôture : on ne
recalcule pas le passé, sinon un changement de règle réécrit l'histoire.

```sql
CREATE TABLE IF NOT EXISTS produit_series (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  ref_produit_norm     TEXT NOT NULL,
  no_dossier           TEXT NOT NULL,
  planning_entry_id    INTEGER,
  of_import_id         INTEGER,
  fiche_id             INTEGER,

  machine              TEXT,
  laize_mm             INTEGER,
  conditionnement_norm TEXT,
  format               TEXT,
  matiere              TEXT,
  ref_adhesif          TEXT,

  client               TEXT,
  designation          TEXT,
  operateurs           TEXT,      -- JSON
  date_debut           TEXT,
  date_fin             TEXT,

  temps_calage_min     REAL,
  temps_prod_min       REAL,
  temps_arret_min      REAL,
  metrage_m            REAL,
  etiquettes           REAL,
  vitesse_m_min        REAL,
  vitesse_avec_calage  REAL,
  gache_pct            REAL,

  arrets_par_code      TEXT,      -- JSON {"54":32,"66":18} minutes
  outillage            TEXT,      -- JSON snapshot of_imports.outil_*
  matieres_consommees  TEXT,      -- JSON depuis fab_matieres_utilisees
  nb_nc                INTEGER DEFAULT 0,

  cloture_le           TEXT NOT NULL,
  cloture_par          TEXT,
  UNIQUE(no_dossier)
);
CREATE INDEX idx_prod_series_ref  ON produit_series(ref_produit_norm, date_fin DESC);
CREATE INDEX idx_prod_series_mach ON produit_series(ref_produit_norm, machine);
```

Déclenchement au code 89, plus un job de rattrapage idempotent.
`UNIQUE(no_dossier)` rend l'opération rejouable sans doublon.

### 5.2 `produit_documents` — les OF terminés scannés

```sql
CREATE TABLE IF NOT EXISTS produit_documents (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  ref_produit_norm  TEXT,             -- NULL tant que non rattaché
  no_dossier        TEXT,
  of_numero         TEXT,             -- lu sur le scan ou saisi
  of_import_id      INTEGER,
  type              TEXT NOT NULL DEFAULT 'of_termine',
  fichier           TEXT NOT NULL,    -- nom dans data/uploads/of_scans/
  fichier_origine   TEXT,             -- nom du fichier déposé par le copieur
  nb_pages          INTEGER,
  taille_octets     INTEGER,
  statut            TEXT NOT NULL DEFAULT 'a_rattacher',  -- a_rattacher|rattache|ecarte
  rattache_par      TEXT,
  rattache_le       TEXT,
  importe_le        TEXT NOT NULL,
  importe_par       TEXT,             -- 'agent:scan-atelier' ou un login
  UNIQUE(fichier)
);
CREATE INDEX idx_prod_docs_ref    ON produit_documents(ref_produit_norm, importe_le DESC);
CREATE INDEX idx_prod_docs_statut ON produit_documents(statut);
```

### 5.3 `produit_savoirs` — le qualitatif

```sql
CREATE TABLE IF NOT EXISTS produit_savoirs (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  ref_produit_norm  TEXT NOT NULL,
  type              TEXT NOT NULL,   -- reglage|piege|defaut|matiere|outillage|controle|autre
  texte             TEXT NOT NULL,
  machine           TEXT,            -- NULL = vaut pour toutes
  laize_mm          INTEGER,
  no_dossier_source TEXT,
  epingle           INTEGER DEFAULT 0,
  obsolete          INTEGER DEFAULT 0,
  utile_count       INTEGER DEFAULT 0,
  auteur            TEXT NOT NULL,
  created_at        TEXT NOT NULL,
  updated_at        TEXT,
  updated_par       TEXT
);
CREATE INDEX idx_prod_savoirs_ref ON produit_savoirs(ref_produit_norm, obsolete, epingle DESC, created_at DESC);

CREATE TABLE IF NOT EXISTS produit_savoirs_utile (
  savoir_id  INTEGER NOT NULL,
  user_login TEXT NOT NULL,
  created_at TEXT NOT NULL,
  PRIMARY KEY (savoir_id, user_login)
);
```

**Publication immédiate — les garde-fous qui vont avec.** Sans validation, la
qualité doit s'auto-réguler :

- auteur et date **toujours** affichés — un conseil anonyme n'engage personne ;
- édition et suppression par l'auteur à tout moment, par les admins toujours ;
- `obsolete` plutôt que la suppression : « ce réglage ne vaut plus depuis le
  changement d'outil » se lit, une note effacée ne se lit pas ;
- tri : épinglés, puis les plus « utiles », puis les plus récents ;
- avertissement de doublon à la saisie si un savoir du même type existe déjà.

---

## 6. Ingestion des OF terminés scannés

**Le circuit retenu** — il ne demande **rien** de nouveau à ton collègue : il
continue de scanner comme aujourd'hui.

```
copieur → dossier réseau → agent local → POST /api/bridge/of-scan → produit_documents
                                                                          │
                                              rattaché au dossier / à la référence
                                                                          │
                                                    visible dans les 3 portes
```

- **Agent local**, calqué sur `print_agents` : token, heartbeat, surveillance
  d'un répertoire. Il envoie chaque nouveau PDF puis le déplace dans un
  sous-dossier `_envoyes/` — jamais de suppression, jamais de double envoi
  (l'`UNIQUE(fichier)` côté serveur est le second filet).
- **Un PDF = un OF**, donc aucun découpage à faire.

### Le point technique à trancher : lire le numéro d'OF

Un OF papier scanné est une **image**. `pdfplumber` n'en extraira aucun texte —
le rattachement automatique ne peut donc pas fonctionner tel quel. Trois voies,
par ordre de préférence :

1. **Activer l'OCR du copieur** (« PDF consultable / searchable PDF » — présent
   sur la quasi-totalité des multifonctions récents). Le numéro d'OF est
   **imprimé**, pas manuscrit : il s'OCRise sans difficulté, et le PDF devient
   lisible par `pdfplumber` comme un OF importé. **C'est la voie à privilégier —
   un réglage sur le copieur, zéro ligne de code.** À noter : ça ne contredit
   pas ton choix sur les annotations — on lit un numéro imprimé, on ne cherche
   pas à interpréter une écriture manuscrite.
2. **Le nom de fichier porte le numéro** — saisi au pupitre du copieur ou
   renommé. Fonctionne, mais repose sur une discipline humaine à chaque scan.
3. **File de rattachement manuel** — de toute façon nécessaire comme filet :
   une vue dans MyProd listant les scans en `statut='a_rattacher'`, avec aperçu
   côte à côte et un champ de recherche d'OF. Deux clics par document.

> À vérifier avant de coder : sortir un scan d'exemple du dossier réseau et
> tester `pdfplumber` dessus. Si du texte remonte, l'OCR est déjà actif et la
> voie 1 est acquise.

---

## 7. Chantiers, dans l'ordre

### C0 — Fiabiliser dossier → produit *(prérequis absolu)*

Le pivot existe, mais il n'est renseigné que là où la cascade a fonctionné. Les
onglets « Mappings à valider » et « Dossiers sans OF » sont la preuve que ce
n'est pas partout. **Une mémoire produit alimentée par 60 % des dossiers est une
mémoire qui ment.**

1. Rejouer `POST /api/admin/backfill-ref-produit-norm?dry_run=1` et lire le bilan.
2. Script de mesure : sur l'historique complet, quelle part des `production_data`
   est rattachable à un `ref_produit_norm` ? Sortie par mois et par machine.
3. Outil de rattrapage dans MyProd pour les dossiers orphelins.
4. **Indicateur permanent** du taux de rattachement, pour que la dérive se voie.

> **Livrable de sortie : le chiffre.** Combien de références ont au moins 2
> séries ? C'est lui qui dit si le module est structurant ou cosmétique — et à
> quelle échelle dimensionner la suite.

### C1 — Fiche produit calculée

Migration `produit_series`, service de matérialisation, job de rattrapage sur
l'historique, page fiche produit (identité, séries, courbes), et les liens
depuis l'onglet Fiches + OF (colonne réf. produit, filtre par référence).
**Rien à saisir pour personne** — valeur immédiate, adoption sans effort.

### C2 — Bouton « Historique » dans Saisieprod

Petit chantier, gros effet : c'est lui qui fait passer C1 de « tableau de bord
qu'on regarde une fois » à « outil d'atelier ». Condition d'affichage stricte,
panneau non bloquant, bouton « + ajouter une note » qui prépare C4.

### C3 — Scans d'OF terminés

Migration `produit_documents`, endpoint bridge, agent local, file de
rattachement manuel, affichage dans les trois portes. **Débloque le stock de
notes papier déjà existant** — c'est la seule brique qui apporte du contenu sans
demander à quiconque de changer ses habitudes.

### C4 — Savoirs

Migrations `produit_savoirs` + `produit_savoirs_utile`, CRUD, saisie depuis le
panneau Saisieprod et depuis la fiche produit, et **file de promotion** : les
`production_data.commentaire` et `annule_motif` jamais promus, transformables en
savoir en un clic (texte pré-rempli, éditable, référence déduite du dossier).

### C5 — Détection cyclique *(différé)*

À la clôture d'une série, comparaison factuelle aux précédentes de la même
référence : « calage 2,4× la médiane des 5 dernières », « code 54 présent sur 3
des 4 dernières séries », « vitesse en baisse continue ». Affiché sur la fiche
produit, proposé en un clic comme savoir. Réutilise l'infrastructure d'alerting
existante.

### C6 — Alimentation du chiffrage *(différé)*

Remplacer, dans le devis, calage et vitesse théoriques par les **médianes
réelles** des N dernières séries. ROI le plus direct du module, mais il exige un
historique propre : il vient après, jamais avant.

---

## 8. Endpoints envisagés

```
GET    /api/produits                              liste + filtres
GET    /api/produits/{ref}                        identité + agrégats
GET    /api/produits/{ref}/series                 historique détaillé
GET    /api/produits/{ref}/documents              scans rattachés
GET    /api/produits/{ref}/savoirs                notes triées
POST   /api/produits/{ref}/savoirs                création
PUT    /api/produits/savoirs/{id}                 édition (auteur ou admin)
POST   /api/produits/savoirs/{id}/utile           « ça m'a servi »
POST   /api/produits/savoirs/{id}/obsolete        périmer

GET    /api/fabrication/dossier-en-cours          → + a_historique, nb_series, nb_savoirs
GET    /api/fabrication/dossier/{no}/historique   le panneau Saisieprod

POST   /api/bridge/of-scan                        dépôt d'un scan par l'agent
GET    /api/produits/documents/a-rattacher        file de rattachement
POST   /api/produits/documents/{id}/rattacher     rattachement manuel
GET    /api/produits/documents/{id}/pdf           consultation

GET    /api/produits/rattachement                 taux de couverture (C0)
```

Router dédié `app/routers/produits_memoire.py`. Côté front :
`static/mysifa_prod_core.js` pour la fiche produit et l'enrichissement de
Fiches + OF, et le shell Saisieprod pour le bouton Historique.

---

## 9. Points de vigilance

- **Ne jamais bloquer une saisie de production** pour un motif de mémoire
  produit. Le module est un service, pas un contrôle.
- **Le bouton Historique n'apparaît que s'il y a un historique.** Un bouton
  toujours présent qui ouvre « aucune donnée » détruit sa propre crédibilité en
  trois ouvertures.
- **Snapshot figé** : `produit_series` ne se recalcule pas. Un changement de
  règle de calcul crée une colonne, il ne réécrit pas l'histoire.
- **Les scans ne sont jamais supprimés** — `statut='ecarte'` pour un document
  illisible ou hors sujet, jamais un `DELETE`.
- **Guide in-app obligatoire** pour la fiche produit et pour le panneau
  Saisieprod (convention CLAUDE.md).
- **`APP_VERSION` n'est pas touchée** — le collaborateur s'en charge sur staging.
- **Migrations** : un fichier par sujet, `NOM` définitif, `DEPEND` explicite,
  rejouables.

---

## 11. État de l'implémentation — 24 août 2026

Chantiers **C0 à C4 codés**, hors rattrapage de l'historique (à lancer sur la
base de production). C5 et C6 restent différés comme prévu.

### Fichiers créés

| Fichier | Rôle |
|---|---|
| `app/core/migrations/2026_08_24_produit_memoire.py` | `NOM = produit_memoire_tables` — les 4 tables, rejouable |
| `app/services/produit_memoire.py` | résolution dossier → référence, matérialisation figée, rattrapage, agrégats, taux de rattachement |
| `app/routers/produits_memoire.py` | 21 routes `/api/produits/*` + `/api/bridge/of-scan` |
| `static/mysifa_produit_memoire.js` | front partagé — panneau historique, fiche produit, liste, file de rattachement |
| `scripts/agent_scan_of.py` | agent local qui surveille le dossier réseau de scans |
| `tests/test_produit_memoire.py` | 30 contrôles, tous verts |

### Fichiers modifiés

| Fichier | Modification |
|---|---|
| `main.py` | import + `include_router` |
| `app/routers/fabrication.py` | matérialisation au code 89 (best-effort) ; `historique_produit` dans `/session` et `/dossier-en-cours` |
| `app/web/fabrication_page.py` | bouton « Historique » conditionnel + chargement du script |
| `app/web/prod_page.py` | chargement du script |
| `static/mysifa_prod_core.js` | tuiles Produits et Scans à rattacher, bouton « Produit » sur les lignes OF et fiches, guide `myprod-produits` |
| `app/web/settings_page.py` | sélecteur de portée sur la création de clé API |

### Le point qui aurait bloqué

La création de clé API n'envoyait **jamais** de `scopes` : toute clé recevait
`of:read,of:write` par défaut, et le scope `scan:write` aurait été
impossible à accorder — l'agent de scans n'aurait jamais pu s'authentifier.
Un sélecteur de portée a donc été ajouté au formulaire.

### Mise en service

1. **Redémarrer le service** — la migration s'applique seule au démarrage.
2. **Rattraper l'historique** : `POST /api/produits/rattrapage` (superadmin).
   Puis lire `GET /api/produits/rattachement` — **c'est le chiffre du
   chantier 0.** S'il est bas, traiter « Mappings à valider » et « Dossiers
   sans OF » avant d'aller plus loin.
3. **Activer l'OCR du copieur** (« PDF consultable / searchable PDF »). Sans
   OCR le numéro d'OF n'est pas lisible et chaque scan part en file de
   rattachement manuel — ça marche, mais c'est deux clics par document.
4. **Créer une clé API** dans Paramètres, portée « Agent de scans ».
5. **Lancer l'agent** sur un poste ayant accès au partage :

   ```
   python agent_scan_of.py --dossier "\\serveur\scans\OF" ^
                           --url https://www.mysifa.com ^
                           --cle msk_xxxxxxxx
   ```

   Option `--une-passe` pour le planificateur de tâches Windows plutôt qu'un
   service résident. L'agent déplace les fichiers envoyés dans `_envoyes/` et
   les échecs dans `_echecs/` — **il ne supprime jamais rien.**

### Vérifications passées

- 30 contrôles fonctionnels verts (`tests/test_produit_memoire.py`) : trigger
  `ref_produit_norm`, résolution et non-résolution, matérialisation rejouable
  sans doublon, rattrapage idempotent, aperçu absent sur un dossier non
  rattaché, détection d'un arrêt récurrent, péremption d'un savoir, taux de
  rattachement, normalisation de référence.
- `import main` complet, **21 routes** enregistrées, ordre de déclaration
  vérifié : `/api/produits/1013/0068` résout bien vers `{ref:path}` avec la
  référence à slash intacte, sans intercepter les routes spécifiques.
- `node --check` sur les deux fichiers JS et sur tous les blocs inline de
  `fabrication_page.py` et `settings_page.py`.
- Aucun octet nul dans les fichiers écrits (contrôle de troncature du mount).

### Reste à faire

- Lancer le rattrapage et lire le taux (chantier 0, sur la base réelle).
- C5 — détection cyclique automatique.
- C6 — alimentation du chiffrage par les médianes réelles.
- Rien n'est commité : tout est en working tree, aucune commande git n'a été
  exécutée depuis le mount.

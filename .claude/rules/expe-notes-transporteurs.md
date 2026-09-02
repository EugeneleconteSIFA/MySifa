---
paths:
  - "app/services/expe_notes.py"
  - "app/routers/expe_departs.py"
  - "app/web/expe_notes_assets.py"
---
## MyExpé — note de confiance transporteur (A → F)

### Ce qui produit la note

Un avis est émis depuis une ligne de départ (bouton rouge « signaler », bouton
vert « apprécier »), avec une note sur 10 par demi-étoiles, une thématique et
un commentaire. Le bouton n'impose pas la note : il oriente le curseur, bas
pour un incident, haut pour une satisfaction. L'utilisateur ajuste.

La note est la **moyenne pondérée** des avis, plus les ajustements manuels.
Tout transporteur part de `NOTE_DEPART` (5/10, soit C), qui entre dans la
moyenne avec le poids d'un avis :

```
note = (NOTE_DEPART × 1  +  Σ(note_i × poids_thématique_i × poids_ancienneté_i))
       / (1 + Σ(poids_i))
       + Σ(ajustements manuels)          borné à [0, 10]
```

- **Poids de thématique** : colonne `poids` de `expe_avis_thematiques`,
  éditable dans MyExpé › Référentiel › Transporteurs, section « Thématiques
  d'avis ». Rien n'est codé en dur, ni la liste ni les poids.
- **Poids d'ancienneté**, par paliers (et non en continu : un palier se lit
  dans l'historique, une exponentielle non) — ≤ 6 mois : 1 ; ≤ 12 mois : 0,75 ;
  ≤ 24 mois : 0,5 ; au-delà : 0,25.
- **Ajustement manuel** : ±3 points cumulés au maximum, motif obligatoire,
  tracé dans le même historique que les avis. Il **s'ajoute**, il n'écrase
  pas — écraser ferait du mécanisme d'avis une décoration.

### Règles à ne pas contourner

- **Tout le monde part de 5/10.** Décidé le 31/08/2026, contre le premier jet
  qui n'affichait aucune note tant qu'aucun avis n'existait : la colonne du
  référentiel restait vide sur toute sa hauteur et le comparateur n'avait rien
  à montrer. La note de départ **pèse comme un avis**, ce qui a deux effets
  voulus : le premier avis déplace la note de moitié au lieu de la faire
  basculer d'un bout à l'autre, et l'influence de la note de départ tombe
  d'elle-même à 1/(n+1).
- **La note de départ n'est jamais un avis** : `nb_avis` reste à 0, le retour
  porte `par_defaut: true`, et l'écran dit « note de départ » — jamais un
  nombre d'avis inventé. Le badge est alors en pointillés.
- **Moins de 3 avis ⇒ note provisoire**, signalée comme telle dans la fiche.
  Zéro avis n'est pas « provisoire », c'est « par défaut » : deux états
  distincts.
- Seuils de lettre, **centrés sur la note de départ** — C est la bande neutre
  et la plus large, et 5/10 tombe dedans avec de la marge des deux côtés :
  A ≥ 8,5 · B ≥ 7 · C ≥ 4,5 · D ≥ 3 · E ≥ 1,5 · F en dessous.
  Libellés : A « À utiliser en priorité » … F « À éviter ».
  **Déplacer ces bornes sans déplacer `NOTE_DEPART` ferait démarrer tout le
  monde à « À surveiller »** — le contraire de ce qu'une note de départ veut
  dire. Les deux se règlent ensemble.
- Les constantes JS `EXPE_AJUST_MAX`, `EXPE_NOTE_SEUIL_FIABILITE` et
  `EXPE_NOTE_DEPART` (`expe_notes_assets.py`) doublent volontairement le
  serveur pour l'affichage. Les changer d'un seul côté produit un écran qui
  ment. Les seuils de lettre, eux, ne sont **pas** dupliqués : la lettre vient
  toujours du serveur.
- La note s'affiche partout où l'on choisit un transporteur : liste du
  référentiel, cartes du comparateur (éligibles **et** non éligibles), écran
  Zone géographique. Le comparateur reste trié **par prix** — la note informe
  la décision, elle ne la prend pas.
- La note est **mise en cache** sur `expe_transporteurs`
  (`note_valeur`, `note_lettre`, `note_nb_avis`, `note_maj_le`) et réécrite à
  chaque écriture d'avis, jamais à la lecture : elle est lue partout, écrite
  rarement. Modifier le poids d'une thématique déclenche
  `recalculer_toutes()`.

### Zone géographique

`/expe` › Référentiel › Zone géographique : on saisit une ville ou un code
postal, on obtient les transporteurs à prioriser sur la **région**.

```
score = note de confiance 50 %  +  expérience sur la région 50 %

expérience = Σ (chaque transport × poids de récence)
             rapportée au transporteur le plus actif de la région
```

- **La zone de classement est la région, pas le département** (02/09/2026).
  Découpé en 101 morceaux, l'historique fabriquait des zones à un ou deux
  départs où le premier transporteur croisé passait « le meilleur ». Une région
  regroupe assez de départs pour qu'un classement veuille dire quelque chose, et
  reste plus fine que la France entière. Le référentiel des 18 régions (13
  métropolitaines + 5 DOM) vit dans `app/services/expe_regions.py`, en dur : il
  n'a pas bougé depuis 2016, et une table de plus se désynchroniserait du SVG.
- **Récence d'un transport**, par paliers comme l'ancienneté des avis, mais avec
  un premier palier plus court — ≤ 3 mois : 1 ; ≤ 6 mois : 0,75 ; ≤ 12 mois :
  0,5 ; ≤ 24 mois : 0,25 ; au-delà : 0,1. Un transport sans date lisible tombe
  au palier le plus faible plutôt que d'être ignoré : il a bien eu lieu.
- L'expérience est **relative** : elle est divisée par celle du mieux-disant de
  la région. Sur une région où personne n'a beaucoup roulé, celui qui a roulé le
  plus prend quand même les points — c'est un classement, pas une note absolue.
- **Conséquence assumée du 50/50** : un transporteur moins bien noté mais
  nettement plus actif récemment peut passer devant un mieux noté. Les deux
  poids sont `POIDS_NOTE` et `POIDS_EXPERIENCE` (`expe_notes.py`) et font 1 : les
  déplacer se fait des deux côtés à la fois, et le test
  `tests/test_expe_notes.py` verrouille l'arbitrage tel qu'il est réglé.
- Un transporteur sans avis apporte 0,5 au score de note : c'est
  mécaniquement `NOTE_DEPART / 10`, pas une exception dans le code.
- Le score s'affiche sur 100, avec sa composition en toutes lettres dans
  l'écran — un « 73 pts » sans légende ne veut rien dire pour qui n'a pas
  écrit la formule.
- Hors zone déclarée, le score est multiplié par 0,4 ; le transporteur reste
  affiché, signalé « hors zone ».
- Un transporteur **jamais utilisé** sur la zone n'est pas écarté : il descend
  en bas de liste avec la mention « jamais utilisé ici ». Sinon le classement
  ne fait que reconduire les habitudes, et un bon transporteur n'a jamais sa
  première chance.
- La présence d'une grille tarifaire est **affichée, pas comptée** : une grille
  absente ne dit rien de la qualité du service. Une grille sur un seul
  département de la région suffit à l'afficher.
- Le **délai indicatif** reste départemental : il n'apparaît que si la
  destination vient d'une ville ou d'un code postal. Un clic sur la carte donne
  la région seule — pas de département, donc pas de délai, plutôt qu'un délai
  pris au hasard dans la région.
- Le référentiel de villes est celui des **clients** (`clients.cp` /
  `clients.ville`) : ce sont exactement les destinations vers lesquelles SIFA
  expédie. Un code postal non répertorié reste accepté — il suffit à retrouver
  la région.
- La carte ne colorie qu'une région **déjà livrée**. Une région neutre n'a aucun
  départ enregistré : mieux vaut un blanc qu'une recommandation inventée.
- `carte_zones()` fait **une seule passe** sur `expe_departs` pour toutes les
  régions. Ne pas repasser à un balayage par zone.
- **Le type d'envoi vaut « Affrètement » par défaut**, et le bouton Rechercher
  recharge la carte avec ce type en même temps qu'il interroge la région. Sans
  ce rechargement, on lit un classement en affrètement sur une carte coloriée
  pour un autre type — deux réponses différentes à l'écran, dont une fausse.
- **Le détail d'un transporteur se déplie ligne par ligne** (clic sur l'entête),
  et le premier du classement s'ouvre tout seul à chaque interrogation : c'est la
  réponse à la question que pose l'écran, elle ne doit pas coûter un clic. Le
  détail montre d'où viennent les points (`points_note`, `points_experience`,
  `experience`, `experience_max`, renvoyés par `_classer`). Ces deux moitiés sont
  données AVANT la pénalité hors zone, et l'écran affiche la pénalité sur une
  ligne à part (« × 0,4 → … ») : une addition qui ne retombe pas sur le score de
  l'entête ferait passer une règle du barème pour une erreur de calcul.
- **La carte des régions n'est pas dessinée à la main.**
  `app/web/expe_france_regions.svg` est l'union géométrique des départements de
  `expe_france_departments.svg`, produite par
  `tools/build_expe_france_regions.py` (shapely). Les deux cartes restent donc
  superposables au pixel près, et la carte des départements continue de servir
  au widget des délais, qui se règle bien département par département. Retoucher
  le SVG des régions à la main, c'est créer une deuxième source de vérité qui
  divergera au premier ajustement de l'autre.

### Marque côté transporteur

Tout ce qu'un transporteur reçoit ou consulte porte **SIFA**, jamais MySifa :
email de demande de tarif (en-tête, pied, footer), email de confirmation,
portail (titre d'onglet, en-tête, pied). L'enveloppe `email_mysifa_layout()`
prend un paramètre `marque` pour ça — `"MySifa"` par défaut pour l'interne,
`"SIFA"` pour les tiers. Le nom de la plateforme reste interne : docstrings,
clés `localStorage`, chemins d'assets et URL du portail ne changent pas.

L'email de demande de tarif dit explicitement, en trois étapes numérotées, que
la réponse se saisit **sur le portail**. Il ne dit PAS qu'une réponse par email
ne sera pas traitée : la phrase a existé une journée et a été retirée le
31/08/2026 — elle sonnait procédurière et abîmait la relation de proximité avec
le transporteur. Ne pas la réintroduire : les trois étapes suffisent à indiquer
le bon chemin.

### Cellule d'actions des tableaux de départs

La cellule (`.expe-dep-actions-cell`) est une rangée de blocs, lue en
**colonnes** à gauche et en ligne à droite :

```
[signaler] [dupliquer]     [comparateur][devis][supprimer]
[valoriser][modifier]                     [   Valider   ]
```

Les gestes qui vont par deux sont empilés l'un sous l'autre — signaler /
valoriser, dupliquer / modifier : la pile les désigne comme une paire sans
avoir besoin d'un séparateur. Le bloc de droite garde les actions isolées sur
sa première ligne, et le bouton de validation dessous.

La cellule est en `width:max-content; margin-left:auto` : elle se cale sur son
contenu et reste collée à droite au lieu de s'étaler sur toute la colonne. Les
boutons font 32 × 32 avec une icône de 16 px ; la colonne « Actions » vaut
15 % au suivi, 12 % à l'historique — vérifié sans débordement de 1280 à
1920 px, ligne à 83 px.

**L'infobulle ne peut pas être un `::after`.** Le tableau vit dans
`.expe-departs-tbl-wrap`, en `overflow-x:auto` : un pseudo-élément y est rogné
dès qu'il dépasse un bord, et c'est exactement ce qui coupait les libellés à
droite et sous la dernière ligne. `expeTipShow()` pose donc un nœud unique
`.expe-tip` sur `<body>` en `position:fixed`, bascule au-dessus ou en dessous
selon la place, et se recadre horizontalement dans la fenêtre. Le `title`
natif est déplacé vers `data-tip` au premier survol pour ne pas faire doublon.
Ne pas revenir à un `::after` : le conteneur le rognera de nouveau.

Un bouton ajouté oblige à revérifier ces largeurs, et les boutons d'avis
portent `expe-dep-ab` en plus de leur propre classe — c'est elle qui déclenche
l'infobulle et donne la métrique commune.

### Accès ERP de l'expédition, et préremplissage par l'ARC

`ROLES_ERP` (config.py) = `ROLES_ADMIN` + `expedition`. C'est le périmètre de
`/erp`, de `/api/erp` et de `/api/rvgi` — y compris le `require_admin` local
de `app/routers/rvgi.py`, qui porte ce nom pour ne pas toucher ses quinze
appels mais applique bien `ROLES_ERP`. L'expédition y a été ajoutée le
31/08/2026 : sans lecture du miroir, un expéditeur saisit un numéro de BL que
rien ne rattache à sa commande — c'est le lien de traçabilité qui se perd.
Le miroir est ouvert en `mode=ro`, donc élargir ce périmètre ne donne aucun
droit d'écriture sur RVGI.

Les trois endroits à tenir alignés quand ce périmètre bouge : `ROLES_ERP`,
le volet `erp` de `portail_volets.py` (`_ERP_LARGE`), et le test de rôle en
dur du bouton ERP dans `portal_assets.py`. Le menu par service vit dans
`erp_catalogue.MENU_SERVICE` — l'expédition n'y voit que livraisons,
commandes, colisage et clients : ni factures, ni prix, ni échéances.

**Préremplissage par l'ARC** — `GET /api/rvgi/commande?numero=` renvoie
l'entête de `cde_entete` réduite à ce qu'un départ sait utiliser. Trois règles
qui ne se devinent pas :

- l'adresse retenue est celle de **livraison** (`lrs`/`lcp`/`lville`), pas
  celle de facturation — un départ va chez le destinataire ; on retombe sur
  la facturation seulement si la commande n'a pas d'adresse de livraison ;
- la recherche compare `numero` **en entier**, jamais avec un CAST en texte :
  la colonne est un integer indexé, et le CAST fait passer la requête de 1 ms
  à 24 ms — sur un appel émis à chaque frappe ;
- côté écran, on ne remplit **que les champs vides**. Écraser une saisie
  manuelle serait pire que ne rien faire : l'expéditeur a parfois une bonne
  raison de déroger à l'adresse de la commande. Le résumé sous le champ dit
  ce qui a été complété, et ne répète ni le numéro ni la date, déjà à
  l'écran.

« Commande inconnue » n'est pas une erreur : la route répond 200 avec
`trouve: false`, et l'écran reste utilisable pour un départ hors commande.

### Comparateur — le piège déjà tombé une fois

`renderTransporteurs()` préserve le focus et le curseur de **tout** champ
focalisé portant un id, et `loadTransporteurs()` passe par elle pour ses deux
render(). Ne pas revenir à une liste blanche de champs : c'est ce qui vidait
le formulaire du comparateur pendant la frappe, parce que l'onglet charge la
liste des transporteurs en arrivant. Toute saisie du comparateur est recopiée
dans `S.comparateur_form`, et ses résultats dans `S.comparateur_resultats` —
un render() global ne doit jamais faire disparaître une comparaison lancée.

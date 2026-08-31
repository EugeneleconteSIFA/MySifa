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
postal, on obtient les transporteurs à prioriser sur le département.

```
score = note 55 %  +  expérience sur la zone 30 %  +  fraîcheur 15 %
```

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
  absente ne dit rien de la qualité du service.
- Le référentiel de villes est celui des **clients** (`clients.cp` /
  `clients.ville`) : ce sont exactement les destinations vers lesquelles SIFA
  expédie. Un code postal non répertorié reste accepté — seul le département
  compte.
- La carte ne colorie qu'un département **déjà livré**. Un département neutre
  n'a aucun départ enregistré : mieux vaut un blanc qu'une recommandation
  inventée.
- `carte_zones()` fait **une seule passe** sur `expe_departs` pour les 101
  départements. Ne pas repasser à un balayage par département.

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

### Comparateur — le piège déjà tombé une fois

`renderTransporteurs()` préserve le focus et le curseur de **tout** champ
focalisé portant un id, et `loadTransporteurs()` passe par elle pour ses deux
render(). Ne pas revenir à une liste blanche de champs : c'est ce qui vidait
le formulaire du comparateur pendant la frappe, parce que l'onglet charge la
liste des transporteurs en arrivant. Toute saisie du comparateur est recopiée
dans `S.comparateur_form`, et ses résultats dans `S.comparateur_resultats` —
un render() global ne doit jamais faire disparaître une comparaison lancée.

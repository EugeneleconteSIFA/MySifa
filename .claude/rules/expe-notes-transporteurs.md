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

La note est la **moyenne pondérée** des avis, plus les ajustements manuels :

```
note = Σ(note_i × poids_thématique_i × poids_ancienneté_i) / Σ(poids_i)
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

- **Aucun avis ⇒ aucune note.** Pas de C par défaut : ce serait affirmer
  quelque chose qu'on ne sait pas, et faire remonter un inconnu dans les
  classements. Le badge affiche un tiret.
- **Un ajustement seul ne fabrique pas de note** — il n'y a rien à ajuster.
- **Moins de 3 avis ⇒ note provisoire**, signalée comme telle dans la fiche.
- Seuils de lettre, à ne pas déplacer sans arbitrage :
  A ≥ 9 · B ≥ 8 · C ≥ 6,5 · D ≥ 5 · E ≥ 3,5 · F en dessous.
  Libellés : A « À utiliser en priorité » … F « À éviter ».
- Les constantes JS `EXPE_AJUST_MAX` et `EXPE_NOTE_SEUIL_FIABILITE`
  (`expe_notes_assets.py`) doublent volontairement le serveur pour l'affichage.
  Les changer d'un seul côté produit un écran qui ment.
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

- Sans note, le score de note vaut 0,5 — ni bien ni mal.
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
la réponse se saisit **sur le portail** et qu'un retour par email ne peut pas
être traité. Sans cette phrase, la moitié des transporteurs répondent dans le
fil : le tarif n'entre jamais dans le comparateur et il faut le ressaisir.

### Comparateur — le piège déjà tombé une fois

`renderTransporteurs()` préserve le focus et le curseur de **tout** champ
focalisé portant un id, et `loadTransporteurs()` passe par elle pour ses deux
render(). Ne pas revenir à une liste blanche de champs : c'est ce qui vidait
le formulaire du comparateur pendant la frappe, parce que l'onglet charge la
liste des transporteurs en arrivant. Toute saisie du comparateur est recopiée
dans `S.comparateur_form`, et ses résultats dans `S.comparateur_resultats` —
un render() global ne doit jamais faire disparaître une comparaison lancée.

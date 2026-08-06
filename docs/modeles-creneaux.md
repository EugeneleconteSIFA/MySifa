# Modèles de créneau — comportement de référence

> MyMaintenance › Planning. État au 3 août 2026 (v2.6.1).
> Ce document décrit ce qui se passe quand on touche à un modèle, et pourquoi.

## 1. Deux façons d'être lié à un modèle

Tout repose sur deux champs de `maintenance_events` :

| Champ | Posé par | Signification |
|---|---|---|
| `template_id` | la génération de récurrence | le créneau appartient à la série d'un modèle |
| `template_origin_date` | la génération de récurrence | date théorique du créneau dans la série — **immuable** |

**Occurrence de récurrence** : les deux champs sont renseignés. Créée
automatiquement côté serveur. C'est une copie vivante du modèle.

**Créneau composé à la main** : aucun des deux. Même si un modèle a été importé
depuis la liste des opérations. L'import est un **raccourci de saisie** : il
recopie des opérations dans le formulaire, sans créer le moindre lien. Le
créneau est autonome à vie.

`template_origin_date` est ce qui permet de distinguer un créneau *déplacé*
(`date_prevue` ≠ `template_origin_date`) d'un créneau resté à sa place.

## 2. Importer un modèle dans un créneau

- Accessible depuis l'en-tête « Opérations à effectuer » de la modale créneau.
- **Cumulable** : plusieurs modèles peuvent être importés dans le même créneau.
- **Fusionne** : une opération déjà présente n'est pas dupliquée. Ses machines
  sont **unies**, ses consignes concaténées si elles diffèrent.
- **N'écrase jamais** : l'import ajoute, il ne remplace pas. Pour repartir de
  zéro, supprimer les lignes avec l'icône corbeille.
- Ne reprend **que** les opérations, leurs machines et leurs consignes. Ni les
  horaires, ni les opérateurs par défaut du modèle.
- Le picker grise les opérations déjà présentes dans le créneau (« — déjà dans
  le créneau »), pour éviter de remplir une ligne qui serait fusionnée ensuite.

## 3. Modifier un modèle : deux dimensions étanches

Un modèle porte deux dimensions **indépendantes**. Une modification ne franchit
jamais la frontière.

| Dimension | Contenu | Ce qu'elle peut modifier dans un créneau |
|---|---|---|
| **Contenu** | les opérations du modèle | uniquement les opérations |
| **Planification** | règle de récurrence + horaires | uniquement la date et les horaires |

### Modifier les opérations

- Les occurrences de récurrence **futures** voient leurs opérations remplacées
  par celles du modèle.
- **Aucune date ne bouge.** Un créneau déplacé reste où il est ; un créneau
  supprimé ne réapparaît pas.
- Les créneaux composés à la main ne sont **jamais** concernés.

### Modifier la règle de récurrence

- Les occurrences futures sont **déplacées** vers les dates de la nouvelle
  règle, appariées dans l'ordre (la 1re du lundi devient la 1re du mardi).
- **Le contenu est conservé** : opérations, personnalisations, avancement saisi
  par les opérateurs. Il n'y a plus de purge/régénération.
- `template_origin_date` est réaligné sur la nouvelle date, sinon la génération
  — qui dédoublonne dessus — recréerait un doublon à chaque date cible.
- Les occurrences manquantes sont créées, celles en trop supprimées.

### Modifier le nom ou la description

Aucun effet sur les créneaux.

## 4. La confirmation avant enregistrement

Elle n'apparaît que si des créneaux seraient **réellement** affectés, et ne
liste que la population concernée par la dimension modifiée :

| Dimension modifiée | Créneaux listés |
|---|---|
| Opérations | ceux dont la liste d'opérations a divergé du modèle |
| Récurrence | ceux déplacés à la main (leur position serait écrasée) |
| Les deux | les deux listes, en sections séparées |

**Case cochée = préservé.** Le défaut protège ce qui a été modifié à la main ;
il faut décocher explicitement pour écraser.

Les créneaux conformes au modèle, ou restés à leur place théorique, ne sont pas
listés : les traiter ne change rien pour eux.

Une divergence d'opérations est signalée avec son motif : opération ajoutée,
opération du modèle retirée, machines modifiées, ou **opération déjà
effectuée** (encadré rouge — la resynchronisation détruirait statut, auteur et
horodatage de réalisation).

### Créneau préservé lors d'un changement de règle

Il ne bouge pas, mais son `template_origin_date` est réaligné sur la date cible
qu'il occupe : il **consomme sa place** dans la série. Sans cela, la génération
verrait la date libre et créerait une occurrence à côté de lui.

Conséquence voulue : il reste marqué « déplacé à la main » et réapparaîtra dans
la confirmation au prochain changement de règle.

## 5. Désactiver la récurrence / supprimer le modèle

- **Désactiver la récurrence** : les occurrences futures de la récurrence sont
  supprimées.
- **Supprimer le modèle** : idem ; les créneaux passés sont conservés et
  détachés (`template_id` → NULL).

Depuis la v2.7.2, ces deux opérations filtrent sur `template_id` **et**
`template_origin_date IS NOT NULL` : seules les occurrences réellement générées
par la récurrence sont emportées. Un créneau composé à la main ayant hérité
d'une étiquette `template_id` (avant la v2.6.1) survit et se retrouve
simplement détaché.

Les compteurs de la carte du modèle (« N créneaux créés », « N supprimées ») et
le panneau de restauration comptent la même population — sinon la modale de
suppression annoncerait plus de créneaux qu'elle n'en supprime.

## 6. Ce qui n'est jamais touché

- Les créneaux **passés** — tous les filtres portent sur `date_prevue >= aujourd'hui`.
- Les créneaux **composés à la main**, quel que soit le nombre de modèles importés.
- Lors d'une modification d'opérations : les **dates, horaires et source** d'une
  occurrence.

## 7. Limites connues

- **Appariement positionnel** : si une occurrence est supprimée au milieu de la
  série puis que la règle change, le décalage se propage — la 4e occurrence
  restante prend la 4e date théorique, pas la 5e.
- **Conversion hebdomadaire → mensuel** : l'invariant « une occurrence par
  période » ne garde qu'un créneau par mois, les trois autres disparaissent
  sans avertissement dédié.
- Les **interventions libres** (décrites à la main) ne sont pas dédupliquées :
  elles se distinguent par leur titre, pas par un code.

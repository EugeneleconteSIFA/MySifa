# Portail — sous-menus des applications

Ce document sert à **choisir** ce qui apparaît dans le sous-menu de chaque
tuile du portail. Il liste, pour chaque module, ce qui est proposé aujourd'hui
et ce qui est disponible sans rien développer de plus.

Le catalogue à modifier : `app/services/portail_volets.py`, dictionnaire
`VOLETS_TUILES`. Une entrée s'écrit :

```python
_entree("cle_unique", "Libellé affiché", "/url", "nom-icone", "sous-titre optionnel",
        roles=_ADMIN)   # roles facultatif : sans lui, tout le monde la voit
```

Après modification : `PYTHONPATH=. python3 tests/test_portail_volets.py`. Le test
refuse une URL qui n'existe pas, une ancre qui ne correspond à aucun onglet réel,
et une icône absente du jeu SVG — c'est le garde-fou contre le raccourci qui
n'emmène nulle part.

**Règle de fond** : une destination n'est utilisable dans un menu que si la page
sait s'ouvrir dessus **par son URL**. Les vues qui ne s'atteignent qu'au clic
dans la page ne peuvent pas être des entrées — elles sont listées quand même,
en fin de section, parce qu'il suffit souvent de quelques lignes pour les rendre
adressables.

---

## MyProd — `/prod`

**Au menu aujourd'hui** : Suivi de production, Traçabilité, Ordres de fabrication,
Fiches techniques, Scans d'OF, Rentabilité *(admin)*, Planning production,
Production + expédition.

| Disponible | URL |
|---|---|
| Production | `/prod?page=production` |
| Traçabilité | `/prod?page=traceabilite` |
| Ordres de fabrication | `/prod?page=of` |
| Fiches techniques | `/prod?page=fiches` |
| Scans d'OF | `/prod?page=scans` |
| Rentabilité (admin) | `/prod?page=rentabilite` |
| Vue d'ensemble production | `/prod?page=production#kpis` |
| Saisies | `/prod?page=production#saisies` |
| Erreurs & qualité | `/prod?page=production#erreurs` |
| Rapport hebdo | `/prod?page=production#rapport` |
| Mappings à valider | `/prod?page=of#pending` |
| Dossiers sans OF | `/prod?page=of#sansof` |
| Planning : production | `/planning?vue=prod` |
| Planning : expédition | `/planning?vue=expe` |
| Planning : production + expédition | `/planning?vue=prod_expe` |

Non adressables : le menu d'accueil MyProd, les sous-onglets de « Fiches
techniques » (liste / non reliées).

## MyStock — `/stock`

**Au menu aujourd'hui** : Tableau de bord, Produits finis, Inventaire produit,
Historique mouvements, Matières premières, Besoins matières, Réception matière,
Étiquettes traçabilité, Plan entrepôt, Valorisation *(admin)*.

| Disponible | URL |
|---|---|
| Tableau de bord | `/stock?tab=dashboard` |
| Matières premières | `/stock?tab=matieres` |
| Réception matière | `/stock?tab=reception` |
| Inventaire matière | `/stock?tab=matieres-inventaire` |
| Besoins matières | `/stock?tab=besoins-matieres` |
| Produits finis | `/stock?tab=produits-finis` |
| Produits de négoce | `/stock?tab=negoce` |
| Référentiel | `/stock?tab=referentiel` |
| Inventaire produit | `/stock?tab=inventaire` |
| Monitoring (admin) | `/stock?tab=monitoring` |
| Valorisation (admin) | `/stock?tab=valorisation` |
| Historique mouvements | `/stock?tab=historique` |
| Étiquettes traça | `/stock?tab=traca` |
| Plan entrepôt | `/stock?tab=plan-entrepot` |
| Production (rôle fabrication) | `/stock?tab=production` |

Besoins matières accepte en plus une sous-vue : `&vue=echeance|matiere|dossier|tendance|passes`.
Non adressable : le menu d'accueil MyStock.

## MyExpé — `/expe`

**Au menu aujourd'hui** : Départs, Palettes Europe, Calcul poids, Comparateur
tarifs, Devis transporteurs, Transporteurs, Prospects — soit la totalité.

| Disponible | URL |
|---|---|
| Départs | `/expe#suivi_departs` |
| Palettes Europe | `/expe#palettes_europe` |
| Calcul poids | `/expe#poids` |
| Comparateur tarifs | `/expe#comparateur` |
| Devis transporteurs | `/expe#devis` |
| Transporteurs | `/expe#transporteurs` |
| Prospects | `/expe#prospects` |

Non adressables : les sous-onglets de Départs — « Départs programmés » et
« Historique départs ». Deux lignes dans `expe_assets.py` suffiraient à les
rendre adressables si tu veux « Historique départs » au menu.

## Saisie Prod — `/fabrication`

**Au menu aujourd'hui** : Saisie opérateur, Traçabilité, Stock, Fiches et OF.

| Disponible | URL |
|---|---|
| Saisie | `/fabrication#saisie` |
| Traça | `/fabrication#traca` |
| Stock | `/fabrication#stats` |
| Fiches et OF | `/fabrication#of` |
| Imprimer (admin) | `/fabrication#print` |

## MyQualité — `/qualite`

**Au menu aujourd'hui** : Non-conformités, Audits client, Ressources
fournisseurs, Certifications SIFA, Référentiel RSE — soit la totalité.

| Disponible | URL |
|---|---|
| Non-conformités | `/qualite#list` |
| Audits client | `/qualite#audits-list` |
| Ressources fournisseurs | `/qualite#ressources-list` |
| Certifications SIFA | `/qualite#sifa-docs-list` |
| Référentiel RSE | `/qualite#ref-list` |
| Menu d'accueil | `/qualite#menu` |

## Coûts matières — `/pricing`

**Au menu aujourd'hui** : Matières, Produits, Fournisseurs, Marges & paramètres.

| Disponible | URL |
|---|---|
| Matières | `/pricing/materials` |
| Produits | `/pricing/products` |
| Fournisseurs | `/pricing/fournisseurs` |
| Paramètres | `/pricing/settings` |

Attention : `/pricing/mystock` a bien une route serveur, mais côté client
`parseRoute` (`static/pricing_app.js`) le laisse retomber sur « Matières » —
il n'y a donc pas d'entrée « Produits MyStock » au menu. Pour en avoir une, il
faut d'abord donner une vue de liste à cette route.

## Maintenance — `/maintenance`

**Au menu aujourd'hui** : Planning des interventions, Contrôles, Opérations.

| Disponible | URL |
|---|---|
| Suivi machine | `/maintenance#maintenance` |
| Planning | `/maintenance#planning` |
| Contrôles | `/maintenance#controles` |
| Opérations | `/maintenance#operations` |
| Mes tâches (opérateur) | `/maintenance#op-tasks` |
| Planning du jour (opérateur) | `/maintenance#op-planning` |

## Planning RH — `/planning-rh`, Mon coffre — `/coffre`, Coffre RH — `/rh/coffre`

| Disponible | URL |
|---|---|
| Planning du personnel | `/planning-rh#planning` |
| Congés | `/planning-rh#conges` |
| Mes bulletins | `/coffre#bulletins` |
| Mes documents | `/coffre#documents` |
| Mes notes de frais | `/coffre#ndf` |
| Dépôt des bulletins | `/rh/coffre#bulletins` |
| Notes de frais à valider | `/rh/coffre#ndf` |

## MyPrint

Pas de page propre : les étiquettes vivent dans `/stock?tab=traca`, les
imprimantes dans `/settings#printers`. C'est ce que le menu propose.

---

## Les modules sans sous-menu possible aujourd'hui

Ces pages n'ont **aucune vue atteignable par URL** : leur onglet est choisi au
clic, ou restauré depuis le `localStorage`. Le portail ne peut donc proposer que
la page elle-même — et un volet à une seule entrée n'apporte rien, ils n'en ont
pas.

| Module | Vues existantes (clic seul) | Ce qu'il faudrait |
|---|---|---|
| **MyCompta** `/compta` | Factor, Acheteurs, Comptes, Banques, Cession, Gestion des paies | lire un `#hash` au chargement |
| **MyAO** `/ao` | Appel d'offre, Produits, Fournisseurs | idem |
| **MyBAT** `/bat` | écran unique, pas d'onglets | rien à faire |
| **Messagerie** `/messages` | pas d'onglets (`?channel=<id>` ouvre une conversation) | rien à faire |
| **Calendrier** `/calendrier` | Mois, Semaine, Jour, Agenda — mémorisés en localStorage | lire un `#hash` |
| **Explorateur BDD** `/db` | Données, Schéma | lire un `#hash` |
| **MyPaie** `/paie` | écran unique protégé par mot de passe | rien à faire |

Le modèle le plus court du dépôt est `app/web/reports_page.py` (4 lignes :
`REPORTS_VALID_TABS`, `_readReportsTab()`, application au démarrage, écoute de
`hashchange`). Le plus complet est `app/web/coffre_page.py`, qui accepte en plus
`?tab=` en secours. Compter une heure par module, guides in-app non compris.

Mon avis sur l'ordre, si tu veux les traiter : **MyCompta** d'abord (six vues,
c'est le module où l'on tape le plus souvent dans un onglet précis), puis
**MyAO** (trois sections), puis le **Calendrier** (quatre vues, mais le
localStorage rend déjà le service). MyBAT, MyPaie et la Messagerie n'ont rien à
gagner.

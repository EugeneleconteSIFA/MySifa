# Nouvel ERP SIFA — erp.mysifa.com

> Document vivant. Mis à jour à chaque lot livré ou décision prise.
> Dernière mise à jour : 14/10/2026.

## Cap

Remplacer RVGI par un ERP développé dans MySifa et servi sur
`erp.mysifa.com`. Le problème n°1 de RVGI est l'interface ; le n°2,
l'expérience (ressaisies, ruptures de chaîne).

L'ERP se construit **de fond en comble, sans données réelles**, testé en
local. Il n'est déployé et essayé par Eugène qu'une fois **tous** les modules
développés. La reprise des données RVGI vient ensuite, en une fois.

## Décisions

| # | Date | Décision | Conséquence |
|---|---|---|---|
| D1 | 14/10 | **On remplace RVGI**, on ne l'habille pas | L'ERP devient la source de vérité ; RVGI s'éteint après la reprise |
| D2 | 14/10 | **Le code vit dans MySifa**, routé par sous-domaine | Même app FastAPI, même base, mêmes comptes. Les liens dossier / OF / stock / expé sont natifs |
| D3 | 14/10 | Premier module : **Ventes** | Devis → commande → BL → facture → échéance |
| D4 | 14/10 | Utilisateurs cibles : ADV, direction, achats/logistique, comptabilité | Écrans conçus par métier, pas par table |
| D5 | 14/10 | **Superadmin seul**, aucune donnée réelle | Pas de lecture du miroir RVGI pour construire ; jeux de données de démonstration générés |
| D6 | 14/10 | **Un seul déploiement**, quand tous les modules sont faits | Développement et tests en local (`erp.localhost`) ; pas de vhost ni de certificat avant la fin |

## Principes non négociables

1. **Rigueur des liens.** Chaque pièce connaît ses pièces amont et aval
   (devis → commande → OF → BL → facture → règlement ; CDF → réception →
   facture fournisseur). Un lien est une clé étrangère, jamais un numéro
   recopié. Chaque lien a son test.
2. **Numérotation légale continue.** Factures et avoirs : séquence continue,
   sans trou, figée à l'émission. La séquence est un référentiel ; son point
   de départ se règlera à la reprise.
3. **Une pièce émise ne se modifie pas, elle s'annule par une autre pièce.**
   Facture → avoir. Journal d'audit sur tout le reste.
4. **Montants en centimes entiers**, quantités en entiers d'unité de base
   (millièmes si besoin). TVA calculée selon une règle unique et testée.
   Jamais de `REAL` pour un montant.
5. **Le stock est un journal de mouvements**, jamais un compteur qu'on écrase.
   Une quantité en stock est la somme de ses mouvements.
6. **Rien de SIFA en dur** (CLAUDE.md) : séquences, conditions de paiement,
   TVA, dépôts, unités, familles → référentiels en base, éditables dans
   Paramètres de l'ERP.
7. **Interface clavier d'abord.** Tabulation, raccourcis, autocomplétion :
   aucune saisie courante n'exige la souris.
8. **Pensé pour la reprise.** Chaque table métier porte une colonne d'origine
   (`origine`, `origine_ref`) pour accueillir l'historique RVGI sans
   collision de numéros.

## Architecture

```
erp.mysifa.com ─┐                          ┌─ app/web/erp2/        coque (page.py)
                ├─ nginx ─ FastAPI MySifa ─┼─ static/erp/          design system + écrans (JS/CSS)
www.mysifa.com ─┘  (middleware Host)       ├─ app/routers/erp2_*   API ERP
                                           ├─ app/services/gc/     logique métier
                                           └─ production.db        tables gc_*
```

- **Routage** : `router_hote_erp` (main.py). Sur un Host de `ERP2_HOSTS`
  (config.py), toute page est servie sous `/_erp` ; `/api`, `/static`,
  `/uploads` restent communs. Sur `www`, `/_erp` répond 404.
- **Session** : cookie propre à `erp.mysifa.com` (connexion dédiée sur
  l'ERP, mêmes comptes). Pas de cookie partagé avec `www` : évite la
  collision de `sifa_token` entre prod et v1.
- **Accès** : `ROLES_ERP2` (config.py) = superadmin.
- **Tables** : préfixe `gc_` dans `production.db`, pour ne pas les confondre
  avec les tables `erp_*` qui décrivent le miroir RVGI. Une migration fichier
  par lot.
- **Code mergé au fil de l'eau sur `staging`, invisible** : sans vhost
  nginx, aucun nom ne mène à l'ERP sur le VPS. Pas de branche longue qui
  diverge de 6 mois.
- **Dev local** : `.claude/launch.json` → `http://erp.localhost:8010`.

## Lots

Statuts : ☐ à faire · ◐ en cours · ✓ fait

### Lot 0 — Socle ✓

| | Tâche |
|---|---|
| ✓ | DNS `erp.mysifa.com` → VPS 168.231.85.64 |
| ✓ | Middleware Host, préfixe `/_erp` invisible hors sous-domaine |
| ✓ | Connexion ERP, accès superadmin, refus des autres rôles |
| ✓ | Coque : navigation par domaine, routage par chemin, thème, mobile |
| ✓ | Tests `tests/test_erp2_hote.py` |

### Lot 1 — Design system ERP

L'interface est la raison du projet : ce lot se fait avant tout écran métier,
à partir des captures de RVGI.

| | Tâche |
|---|---|
| ☐ | **Grille** : tri, filtres colonne, colonnes réordonnables, totaux, export, navigation clavier, 10 000+ lignes fluides |
| ☐ | **Fiche** (client, article…) : en-tête + sections + onglets liés |
| ☐ | **Pièce** (devis, commande, BL, facture) : en-tête, saisie de lignes au clavier, totaux live, statut, pièces liées amont/aval |
| ☐ | Champs : autocomplétion tiers / article, montant, quantité + unité, date, référentiel |
| ☐ | Recherche globale (Ctrl K), onglets de pièces ouvertes, toasts |
| ☐ | Page de démonstration des composants, validée par Eugène |

### Lot 2 — Fichiers de base et paramètres

| | Tâche |
|---|---|
| ☐ | Référentiels : TVA, unités, conditions et modes de paiement, devises, pays, dépôts, familles, séquences de numérotation |
| ☐ | Tiers : clients (adresses de livraison / facturation, contacts, conditions), fournisseurs |
| ☐ | Articles : produits finis, matières, prestations ; unités de stock / vente / achat et conversions |
| ☐ | Tarifs : prix de vente par client et palier, prix d'achat par fournisseur |
| ☐ | Générateur de données de démonstration (rejouable, remet à zéro) |

### Lot 3 — Ventes

| | Tâche |
|---|---|
| ☐ | Devis : saisie, variantes de quantité, PDF, envoi, transformation en commande |
| ☐ | Marchés : contrat cadre, appels de livraison, suivi du consommé |
| ☐ | Commandes : saisie, ARC PDF, reliquats, statut En cours / partielle / soldée |
| ☐ | Livraisons (BL) : depuis commande(s), colisage, reliquats, PDF |
| ☐ | Factures et avoirs : depuis BL(s), mentions obligatoires, séquence continue, PDF |
| ☐ | Tableau de bord ventes : carnet, retards, facturable |

### Lot 4 — Achats

| | Tâche |
|---|---|
| ☐ | Appels d'offres / demandes de prix |
| ☐ | Commandes fournisseur : saisie, PDF, envoi |
| ☐ | Réceptions : contre CDF, écarts, lots |
| ☐ | Factures fournisseur : rapprochement commande / réception / facture |

### Lot 5 — Stocks matières et produits finis

| | Tâche |
|---|---|
| ☐ | Journal de mouvements unique (entrée, sortie, transfert, inventaire, ajustement) |
| ☐ | Stock MP : par article, dépôt, lot / bobine |
| ☐ | Stock PF : par article, dépôt, lot |
| ☐ | Inventaire, valorisation (PMP ou dernier prix — à décider) |
| ☐ | Mouvements automatiques : réception (+MP), sortie fabrication (−MP), déclaration (+PF), BL (−PF) |

### Lot 6 — Production

| | Tâche |
|---|---|
| ☐ | Ordres de fabrication depuis la commande : nomenclature, gamme, besoins matières |
| ☐ | Déclarations de production et consommations |
| ☐ | Lien avec MyProd / planning existants (à décider : Q8) |

### Lot 7 — Comptabilité

| | Tâche |
|---|---|
| ☐ | Échéances clients et fournisseurs |
| ☐ | Règlements, lettrage, relances |
| ☐ | Journaux et export comptable (format du logiciel compta : Q1) |
| ☐ | Facturation électronique : réception obligatoire depuis le 01/09/2026, émission pour les PME au 01/09/2027 ; plateforme agréée (Q4) |

### Lot 8 — Recette, reprise, déploiement

| | Tâche |
|---|---|
| ☐ | Recette complète de bout en bout sur données de démonstration |
| ☐ | Script de reprise miroir RVGI → `gc_*`, rejouable, avec rapport d'écarts (pièces, CA par mois, encours, stock) |
| ☐ | DNS `erp-v1.mysifa.com`, vhost nginx + certificat, essai d'Eugène sur v1 |
| ☐ | Promotion, bascule, gel de RVGI |

## Questions ouvertes

| # | Question | Bloque |
|---|---|---|
| Q1 | Quel logiciel de comptabilité reçoit les écritures, sous quel format ? | Lot 7 |
| Q2 | Une seule société, ou plusieurs ? | Lot 2 |
| Q3 | Format des numéros devis / commande / BL / facture : on garde ceux de RVGI ? | Lot 2 |
| Q4 | Plateforme agréée de facturation électronique : choisie ? | Lot 7 |
| Q5 | Captures des écrans RVGI les plus utilisés, et ce qui agace le plus | Lot 1 |
| Q6 | Valorisation du stock : PMP, dernier prix d'achat, prix standard ? | Lot 5 |
| Q7 | Gestion par lot / bobine en MP : obligatoire (FSC) ? | Lot 5 |
| Q8 | Production : l'ERP reprend-il le rôle de MyProd / planning, ou s'appuie-t-il sur eux ? | Lot 6 |

## Journal

| Date | Événement |
|---|---|
| 14/10/2026 | DNS `erp.mysifa.com` créé. Décisions D1–D6. Lot 0 livré (socle, connexion, coque) |

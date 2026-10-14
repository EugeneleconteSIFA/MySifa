# Nouvel ERP SIFA — erp.mysifa.com

> Document vivant. Mis à jour à chaque lot livré ou décision prise.
> Dernière mise à jour : 14/10/2026.

## Cap

Remplacer RVGI, module par module, par un ERP développé dans MySifa et servi
sur `erp.mysifa.com`. Le problème n°1 de RVGI est l'interface ; le n°2,
l'expérience (ressaisies, ruptures de chaîne). Les données de RVGI, elles,
sont saines et seront reprises.

## Décisions prises (14/10/2026)

| # | Décision | Conséquence |
|---|---|---|
| D1 | **On remplace RVGI**, on ne l'habille pas | Le nouvel ERP devient source de vérité module par module. Jusqu'à la bascule d'un module, RVGI reste maître sur ce module et le miroir sert de référence |
| D2 | **Le code vit dans MySifa**, routé par sous-domaine | Même app FastAPI, même base, mêmes rôles. Les liens dossier / OF / stock / expé sont natifs, pas des ponts |
| D3 | **Premier module : Ventes** | Devis → commande → BL → facture → échéance |
| D4 | Utilisateurs cibles : ADV, direction, achats/logistique, comptabilité | Les écrans se conçoivent par métier, pas par table |

## Principes non négociables

1. **Une bascule par module, jamais de double saisie durable.** Un module est
   soit lu depuis RVGI (miroir), soit maître dans le nouvel ERP. La période de
   recouvrement (run parallèle) est datée et courte.
2. **Reprise d'historique intégrale.** À la bascule, tout l'historique du
   module est repris depuis le miroir, avec ses numéros d'origine. Un client
   ne doit pas voir changer un numéro de commande ou de facture.
3. **Numérotation légale continue.** Factures et avoirs : séquence continue,
   sans trou, non modifiable après émission. La séquence reprend là où RVGI
   s'arrête.
4. **Une pièce émise ne se modifie pas, elle s'annule par une autre pièce.**
   Facture → avoir. Pas d'`UPDATE` sur une pièce validée ; journal d'audit
   sur tout le reste.
5. **Montants en centimes entiers**, TVA calculée selon une règle unique et
   testée. Jamais de `REAL` pour un montant.
6. **Rien de SIFA en dur** (CLAUDE.md) : séquences, conditions de paiement,
   taux de TVA, dépôts, unités → référentiels en base, éditables.
7. **Interface clavier d'abord.** L'ADV saisit des dizaines de lignes par
   jour : tabulation, raccourcis, autocomplétion, aucune action qui exige la
   souris.

## Architecture

```
erp.mysifa.com  ─┐                          ┌─ app/web/erp2/*       pages ERP
                 ├─ nginx ─ FastAPI MySifa ─┼─ app/routers/erp2_*   API ERP (écriture)
www.mysifa.com  ─┘   (middleware Host)      ├─ production.db        tables gc_*
                                            └─ erp_mirror.db        RVGI, lecture seule
```

- **Routage par Host** : un middleware sert l'arborescence ERP quand
  `Host = erp.mysifa.com` (ou son équivalent staging). `www` continue de servir
  MySifa ; l'actuel `/erp` (miroir) reste en place tant qu'il sert.
- **Session partagée** : cookie posé sur `.mysifa.com`. Piège : `www` et `v1`
  partageraient alors le même cookie `sifa_token` → **le nom du cookie doit
  dépendre de l'instance** (`sifa_token` en prod, `sifa_token_v1` en staging)
  avant d'élargir le domaine.
- **Staging** : il faut un sous-domaine ERP pointant sur v1 (port 8002), par
  ex. `erp-v1.mysifa.com`. On développe et on teste là, on promeut comme le
  reste.
- **Tables** : préfixe `gc_` (gestion commerciale) dans `production.db`, pour
  ne pas les confondre avec les tables `erp_*` existantes qui décrivent le
  miroir. Une migration fichier par lot.
- **Code** : `app/web/erp2/`, `app/routers/erp2_*.py`, `app/services/gc/`.
  Le moteur générique du miroir (`erp_mirror.py`, `erp_catalogue.py`) est
  réutilisé pour les écrans de consultation.
- **Le miroir RVGI ne disparaît pas à la première bascule** : il reste la
  source des modules non basculés et l'archive de référence pour contrôler la
  reprise.

## Lots

Statuts : ☐ à faire · ◐ en cours · ✓ fait

### Lot 0 — Socle technique

| | Tâche |
|---|---|
| ✓ | DNS `erp.mysifa.com` → VPS 168.231.85.64 (14/10/2026) |
| ☐ | DNS `erp-v1.mysifa.com` → VPS (staging) |
| ☐ | vhost nginx + certificat pour les deux noms |
| ☐ | Cookie de session nommé par instance, puis domaine `.mysifa.com` |
| ☐ | Middleware Host → arborescence ERP ; `public_base_url()` côté ERP |
| ☐ | Accès par module ERP : lecture / saisie / validation |
| ☐ | Page d'accueil ERP servie, authentifiée, sur v1 |

### Lot 1 — Design system ERP

L'interface est la raison du projet : ce lot se fait avant tout écran métier,
à partir des captures de RVGI.

| | Tâche |
|---|---|
| ☐ | Coque : navigation par domaine, recherche globale (Ctrl K), fil d'Ariane, onglets de pièces ouvertes |
| ☐ | **Grille** : tri, filtres colonne, colonnes réordonnables, totaux, export, navigation clavier, 10 000+ lignes fluides |
| ☐ | **Fiche** (client, article…) : en-tête + sections + onglets liés |
| ☐ | **Pièce** (devis, commande, BL, facture) : en-tête, saisie de lignes au clavier, totaux live, statut, pièces liées amont/aval |
| ☐ | Champs : autocomplétion tiers / article, montant, quantité + unité, date, sélecteur de référentiel |
| ☐ | Maquettes validées par Eugène sur 3 écrans réels avant de coder les autres |

### Lot 2 — Ventes en consultation (sur le miroir)

Valeur immédiate et sans risque : les utilisateurs travaillent sur la nouvelle
interface avec les vraies données pendant qu'on construit la saisie.

| | Tâche |
|---|---|
| ☐ | Clients, articles, prix de vente (fiches + listes) |
| ☐ | Devis, commandes, BL, factures, échéances (listes + pièces + liens) |
| ☐ | Tableaux de bord ADV et direction repris dans la nouvelle coque |
| ☐ | Retours ADV → ajustements du design system |

### Lot 3 — Ventes en saisie (staging, données de test)

| | Tâche |
|---|---|
| ☐ | Modèle `gc_*` : tiers, articles, tarifs, pièces, lignes, liens, séquences, statuts |
| ☐ | Référentiels : TVA, conditions et modes de paiement, unités, dépôts, transporteurs |
| ☐ | Devis → commande (transformation, ARC PDF, envoi mail) |
| ☐ | Commande → OF / dossier MySifa (lien natif, plus de numéro retapé) |
| ☐ | BL depuis la commande ou le départ MyExpé, reliquats |
| ☐ | Facture depuis BL(s), avoir, PDF conforme (mentions obligatoires) |
| ☐ | Échéances et suivi des règlements |
| ☐ | Export comptable (format du logiciel compta à confirmer) |
| ☐ | Tests : totaux / TVA, séquences sans trou, immutabilité des pièces émises |

### Lot 4 — Bascule Ventes

| | Tâche |
|---|---|
| ☐ | Script de reprise miroir → `gc_*`, rejouable, avec rapport d'écarts (nb pièces, CA par mois, encours) |
| ☐ | Contrôle : CA par année identique au centime à RVGI |
| ☐ | Run parallèle daté (2 à 4 semaines) |
| ☐ | Date de bascule, gel de la saisie Ventes dans RVGI |
| ☐ | Clients et articles deviennent maîtres dans l'ERP ; ce que RVGI lit encore est documenté |

### Lots suivants (ordre indicatif)

| Lot | Module | Notes |
|---|---|---|
| 5 | Achats | CDF → réception → facture fournisseur ; la réception est déjà dans MyStock |
| 6 | Stock | Fusion avec MyStock : un seul stock, plus de réconciliation |
| 7 | Comptabilité clients/fournisseurs | Règlements, relances, lettrage |
| 8 | Facturation électronique | Réception obligatoire depuis le 01/09/2026, émission pour les PME au 01/09/2027 : plateforme agréée à choisir |
| 9 | Extinction RVGI | Plus aucun module maître, miroir figé en archive |

## Questions ouvertes

| # | Question | Bloque |
|---|---|---|
| Q1 | Quel logiciel de comptabilité reçoit les écritures, sous quel format ? | Lot 3 |
| Q2 | Une seule société (`gen_soc`), ou plusieurs ? | Lot 3 |
| Q3 | Format des numéros devis / commande / BL / facture dans RVGI — on les garde ? | Lot 3 |
| Q4 | Plateforme agréée de facturation électronique choisie ? Comment SIFA reçoit ses factures fournisseurs depuis le 01/09/2026 ? | Lot 8 |
| Q5 | Qui à l'ADV valide les maquettes ? | Lot 1 |
| Q6 | Captures des écrans RVGI Ventes les plus utilisés, et ce qui agace le plus | Lot 1 |
| Q7 | La règle « MyERP est un miroir » (`.claude/rules/erp-rvgi.md`) vise `/erp` ; le nouvel ERP aura sa propre règle | Lot 0 |

## Journal

| Date | Événement |
|---|---|
| 14/10/2026 | DNS `erp.mysifa.com` créé. Décisions D1–D4. Roadmap initiale |

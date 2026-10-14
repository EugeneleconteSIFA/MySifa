# Nouvel ERP SIFA — erp.mysifa.com

> Document vivant. Mis à jour à chaque lot livré ou décision prise.
> Dernière mise à jour : 14/10/2026 (fin d'après-midi).
> Captures RVGI attendues : [captures-erp-existant.md](captures-erp-existant.md).

## Cap

Remplacer RVGI par un ERP développé dans MySifa et servi sur
`erp.mysifa.com`. Le problème n°1 de RVGI est l'interface ; le n°2,
l'expérience (ressaisies, ruptures de chaîne).

L'ERP se construit **de fond en comble**, avec un petit jeu de données fictives
mais une vraie base, une vraie API et de vraies règles (D9). Il n'est mis en
service qu'une fois **tous** les modules développés. La reprise des données
RVGI vient ensuite, en une fois.

## Décisions

| # | Date | Décision | Conséquence |
|---|---|---|---|
| D1 | 14/10 | **On remplace RVGI**, on ne l'habille pas | L'ERP devient la source de vérité ; RVGI s'éteint après la reprise |
| D2 | 14/10 | **Le code vit dans MySifa**, routé par sous-domaine | Même app FastAPI, même base, mêmes comptes. Les liens dossier / OF / stock / expé sont natifs |
| D3 | 14/10 | Premier module : **Ventes** | Devis → commande → BL → facture → échéance |
| D4 | 14/10 | Utilisateurs cibles : ADV, direction, achats/logistique, comptabilité | Écrans conçus par métier, pas par table |
| D5 | 14/10 | **Superadmin seul**, aucune donnée réelle | Pas de lecture du miroir RVGI pour construire |
| D6 | 14/10 | **Pas de mise en service** avant que tous les modules soient faits | Ventes, devis, marchés, achats, stocks MP et PF, production, compta |
| D7 | 14/10 | **Eugène teste sur `erp.mysifa.com`**, branché sur l'instance v1 (port 8002) | Le code part sur `staging` au fil de l'eau ; le cron de v1 le déploie |
| D8 | 14/10 | **DA de MySifa** : jetons de couleur, Segoe UI, sidebar commune | Favicon : l'icône MyS, fond cyan, S noir |
| D9 | 14/10 | **Reproduire l'ERP « en vrai » avec très peu de lignes** | Jeu de démonstration en base (`origine='demo'`), passé par le moteur de pièces ; réinitialisable dans Paramètres › Démonstration |
| D10 | 14/10 | **Chantier ERP isolé dans un worktree** `../MySifa-erp` (branche `feature/erp-roadmap`) | Une autre session travaille dans le dossier principal : plus de collision de branche ni de fichiers |
| D11 | 14/10 | **D'abord la parité avec RVGI**, la traçabilité ensuite | Lots, bobines, traçabilité et gestion de stock avancée restent dans MySifa (www) ; ils entreront dans l'ERP une fois RVGI reproduit. Q6, Q7, Q9 en attente |

## Principes non négociables

1. **Rigueur des liens.** Chaque ligne de pièce connaît sa ligne amont
   (`ligne_amont_id`). Reliquats, « livré », « facturé », états des pièces
   amont et pièces liées s'en déduisent. Jamais un numéro recopié.
2. **Numérotation légale continue.** Le numéro est pris à la validation, dans
   la transaction : un refus le rend, il n'y a pas de trou.
3. **Une pièce émise ne se modifie pas.** Brouillon modifiable ; validée en
   lecture seule ; facture → avoir ; autres pièces annulables tant qu'aucune
   pièce aval active n'en dépend, stock contrepassé.
4. **Entiers partout** : centimes, millièmes de quantité, points de base. Prix
   pour `base_prix` unités (au mille pour l'étiquette). Une règle d'arrondi,
   dans `calculs.py`, copiée dans `ERP.calc` pour l'affichage et testée.
5. **Le stock est un journal de mouvements** (`gc_mouvements`). BL = sortie,
   réception = entrée, inventaire = écart avec le théorique.
6. **Rien de SIFA en dur** : TVA, conditions, modes, unités, familles, dépôts,
   numérotation, société → Paramètres de l'ERP.
7. **Clavier d'abord** : Entrée enchaîne les cellules et crée la ligne suivante,
   Ctrl+S enregistre, Ctrl+K cherche partout, flèches dans les listes.
8. **Pensé pour la reprise** : `origine` / `origine_ref` sur tiers, articles,
   pièces, règlements.

## Architecture (en place)

| Couche | Fichiers |
|---|---|
| Routage par Host | `main.py` → `router_hote_erp` ; `config.py` → `ERP2_HOSTS`, `ERP2_PREFIXE`, `ROLES_ERP2` |
| Pages | `app/web/erp2/page.py` (connexion, coque), `app/web/erp2/impression.py` (A4) |
| API | `app/routers/erp2_api.py` (`/api/erp2/*`, superadmin, une transaction par écriture) |
| Métier | `app/services/gc/` : `calculs.py`, `pieces.py`, `fichiers.py`, `compta.py`, `export_compta.py`, `demo.py` |
| Base | migrations `gc_socle`, `gc_reglements`, `gc_production`, `gc_marches`, `gc_comptes` (tables `gc_*` dans `production.db`) |
| Interface | `static/erp/` : `erp.js` (coque, routage, recherche), `erp_ui.js` (composants), `erp_grille.js`, `erp_pieces.js`, `erp_fichiers.js`, `erp_gestion.js`, `erp_compta.js`, `erp.css`, `erp_ecrans.css` |
| Tests | `tests/test_gc_pieces.py` (calculs, chaîne complète, refus, annulation, achats, règlements, OF, marchés, duplication, stock négatif), `tests/test_gc_export.py` (FEC), `tests/test_erp2_hote.py` |
| Dev local | worktree `../MySifa-erp`, base de dev propre, `http://erp.localhost:8010` |

## Ce qui marche aujourd'hui (14/10/2026)

- **Marchés** : contrat cadre (quantité, prix, fin du marché), appels = commandes
  liées, reste à appeler, refus d'appel sur un marché échu.
- **Production** : ordre de fabrication lancé depuis une commande (produits
  finis seulement), consommations matière (sortie de stock, lot), déclarations
  de production (entrée PF, lot), états lancé / en production / terminé.
- **Ventes** : devis → commande → BL (livraisons partielles, reliquats,
  « solder » un reliquat) → facture (regroupement de plusieurs BL) → avoir
  (plafonné au facturé). États calculés : envoyé / accepté, à livrer / livrée
  en partie / livrée, à facturer / facturé, émise / réglée.
- **Achats** : commande fournisseur → réception (entrée en stock, partielle) →
  facture fournisseur.
- **Prix** : tarif du tiers par palier, puis tarif général, puis fiche ; prix
  au mille ; remise ligne et remise de pied ; régime de TVA du tiers (UE,
  export) prioritaire sur le taux de l'article. Un prix convenu ne bouge plus
  quand la quantité change.
- **Stocks** : état par article et dépôt, journal des mouvements, inventaire et
  ajustement.
- **Compta** : échéances (conditions : jours, fin de mois, le N du mois),
  encaissements et paiements avec lettrage, factures réglées en partie / réglées,
  export FEC (journaux ventes, achats, banque) avec plan de comptes paramétrable
  et contrôle d'équilibre.
- **Pièces** : duplication, alerte à la validation d'un BL qui passe le stock
  sous zéro.
- **Fichiers** : clients, fournisseurs (adresses multiples, contacts,
  conditions, blocage), articles (nature, famille, unité, base de prix, tarifs).
- **Impression** : devis, ARC, BL, facture, avoir, bon de commande en A4, avec
  les mentions légales de facture.
- **Paramètres** : société, numérotation, TVA, conditions et modes de
  paiement, unités, familles, dépôts, démonstration.
- **Accueil** : devis en attente, commandes à livrer et en retard, BL à
  facturer, échéances en retard, commandes fournisseur à recevoir, CA de l'année.

## Lots

Statuts : ☐ à faire · ◐ en cours · ✓ fait

| Lot | Contenu | État |
|---|---|---|
| 0 | Socle : sous-domaine, connexion, coque, DA, favicon | ✓ |
| 1 | Design system : grille, fiche, pièce, champs, autocomplétion, fenêtres, recherche | ✓ — reste colonnes déplaçables / redimensionnables |
| 2 | Fichiers de base et paramètres | ✓ |
| 3 | Ventes : devis, marchés, commandes, BL, factures, avoirs, impression | ✓ — reste devis multi-quantités, envoi par mail (à confirmer avec la capture RVGI des marchés) |
| 4 | Achats : commandes, réceptions, factures fournisseur | ✓ — reste rapprochement facture / réception avec écarts de prix, appels d'offres |
| 5 | Stocks MP et PF | ◐ — reste lots / bobines (Q7), valorisation (Q6), transferts |
| 6 | Production | ◐ — OF, consommations, déclarations faits ; reste nomenclature / besoins matières, lien MyProd (Q8) |
| 7 | Comptabilité | ◐ — échéances, règlements, FEC faits ; reste relances, format du logiciel compta (Q1), facturation électronique |
| 8 | Recette, reprise RVGI, mise en service | ☐ |

### Prochaines étapes, dans l'ordre (parité RVGI d'abord, D11)

1. ✓ **Appels d'offre** fournisseurs (demande de prix → commande fournisseur).
2. ✓ **Contacts** : l'annuaire de tous les interlocuteurs.
3. ✓ **Statistiques et palmarès** (« hits parades ») : CA par client, par article, par mois, par représentant.
4. ✓ **Envoi des pièces par e-mail** (PDF joint, destinataires d'après la fiche client, historique des envois).
5. **Achats** : unité d'achat (m²) et de conditionnement (ML) avec laize, « N bobines de X soit Y ML ».
6. **Reprise** : script miroir RVGI → `gc_*` rejouable, avec rapport d'écarts.
7. Après la mise en service : traçabilité, lots et bobines, gestion de stock (D11).

## Questions ouvertes

| # | Question | Bloque |
|---|---|---|
| Q1 | Quel logiciel de comptabilité reçoit les écritures, sous quel format ? | Export comptable |
| Q2 | Une seule société, ou plusieurs ? | Reprise |
| Q3 | Format des numéros devis / commande / BL / facture : on garde ceux de RVGI ? | Paramètres › Numérotation (réglable) |
| Q4 | Plateforme agréée de facturation électronique : choisie ? | Facturation électronique |
| Q5 | Captures des écrans RVGI les plus utilisés | Ergonomie, marchés |
| Q6 | Valorisation du stock : PMP, dernier prix d'achat, prix standard ? | Stock |
| Q7 | Gestion par lot / bobine en MP : obligatoire (FSC) ? | Stock |
| Q8 | Production : l'ERP reprend-il MyProd / planning, ou s'appuie-t-il dessus ? | Production |
| Q9 | Un BL peut-il faire passer le stock PF sous zéro (blocage, alerte, rien) ? | Stock |
| Q10 | Les services (calage, cliché) passent-ils par le BL, ou se facturent-ils directement depuis la commande ? | Ventes |

## Journal

| Date | Événement |
|---|---|
| 14/10/2026 | DNS `erp.mysifa.com`, vhost sur v1. Décisions D1–D10. Lot 0 (socle), lot 1 (design system), lot 2 (fichiers), lot 3 (ventes), lot 4 (achats), stock de base, échéances et règlements, impression A4, jeu de démonstration |
| 14/10/2026 | Ordres de fabrication, marchés, duplication, alerte de stock négatif, export FEC. 17 tests métier |
| 14/10/2026 | Captures RVGI reçues : tableaux de bord par ligne, champs RVGI (dates d'expédition, origine, laboratoire, réf. client, transporteur, représentant, escompte, acompte, colisage BL), numérotation RVGI, relances clients, transferts de dépôt. Questions C1–C7 dans captures-erp-existant.md |
| 14/10/2026 | Réponses C1–C4 : type de ligne (sans facture, à stocker), BAT exigé en création / modification, quantité à fabriquer calculée. PDF RVGI reçus : impression refaite sur le modèle SIFA, numérotation des factures et achats. Allégation FSC calculée des consommations (affiche atelier) |

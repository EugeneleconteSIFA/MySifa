# Captures de l'ERP existant (RVGI) à fournir

> Tenu à jour par Claude au fil des lots. Une capture = une fenêtre RVGI
> entière, avec ses onglets ; quand une fiche a plusieurs onglets, une capture
> par onglet. Ajoute en une phrase **ce qui te gêne** et **ce que l'ADV y fait
> le plus souvent** : c'est ce qui oriente l'interface.

Priorité : **P1** bloque le lot en cours · **P2** le lot suivant · **P3** plus tard.

## Reçues le 14/10/2026 — et ce qui en a été tiré

| Capture | Repris dans l'ERP |
|---|---|
| TDB Commandes (liste par ligne) | Vue « Par ligne » : dates d'expédition et de livraison prévues en rouge si dépassées, laboratoire, position, origine, situation OF, reste, panneau de détail en bas |
| Commande client : en-tête, fiche ligne | Contact, mode de livraison (transporteurs MyExpé), jours et date d'expédition, franco, escompte, acompte, représentant et commission ; par ligne : dates, origine, laboratoire, réf. produit client, nombre de livraisons, livraison chez |
| Consultation BL, TDB Livraisons | Récépissé, colis, palettes, poids, emballage ; vue par ligne des BL |
| TDB Devis, consultation devis | Vue par ligne, date de validité en rouge ; numéro AAMM + 3 chiffres (compteur mensuel) |
| TDB Marchés, consultation marché | Dates d'ouverture et de fermeture, appelé / reste |
| Menu principal | Navigation : contacts, devis, marchés, commandes, livraisons, facturation, comptabilités, stocks PF, colisage, ordonnancement, production, appels d'offre, achats, réceptions, stocks matières, contrôles |
| Numérotation observée | Commandes et BL : compteur continu sur 7 chiffres (99xxxxx) ; devis AAMMNNN ; marchés : compteur simple ; factures AAMM + 4 chiffres ; commandes et factures d'achat : compteur simple |
| PDF : ordre d'expédition, BL, facture, commande d'achat, réception, facture d'achat | Impression refaite sur ce modèle : adresses (facturation barrée sur BL et ordre d'expédition), cartouche Date / Client / Page, « suivie par », V/Réf commande et produit, unité de vente, rappel commande / BL, commandé / déjà livré / livré / reliquat, pied de BL, origine et nature, règlement et échéance, TVA sur les débits, affacturage, pénalités, réserve de propriété |
| Affiche FSC « Quelle allégation pour ce dossier » | Allégation calculée des matières consommées par l'OF (la plus basse l'emporte, non FSC et Controlled Wood → non FSC, film / colle / encre ignorés), imprimée sur BL et facture avec le certificat, alerte si un produit vendu certifié ne l'est pas |

## Questions soulevées par ces captures

| # | Question |
|---|---|
| C1 | ✓ Laboratoire = gestion des BAT. Création / modification exigent un BAT validé (module BAT de MySifa, rattaché à l'article) |
| C2 | ✓ À livrer et facturer · à livrer sans facture · à stocker |
| C3 | ~~Colonnes C.C., I.L., I.S., I.F.~~ — abandonnées (réponse du 14/10 : « je ne sais plus ») |
| C4 | ✓ Souvent du stock, en général un bug : la quantité à fabriquer est calculée (reste − stock − déjà produit), jamais saisie |
| C5 | **Unité de vente « 11 — Mille »** : la liste des unités de vente utilisées |
| C6 | **Colisage** : étape entre stock PF et livraison — que s'y saisit-il ? |
| C7 | **Code AN** (code client / code article, ex. 1153 / 0003) : l'article est-il toujours propre à un client ? |

## Encore à fournir

| ✓ | Prio | Écran | Ce que je dois voir |
|---|---|---|---|
| ☐ | P1 | **Facturation** : l'écran de facturation (le PDF est reçu) | Comment on part des BL |
| ☐ | P2 | **PDF** d'un devis et d'une confirmation de commande envoyée au client | Mise en page |
| ☐ | P1 | **Fiche client**, chaque onglet | Adresses multiples, contacts, conditions, tarifs, encours |
| ☐ | P1 | **Fiche article produit fini**, chaque onglet | Format, unités, conditionnement, prix, liens outil / fiche technique |
| ☐ | P2 | **Colisage** | Voir C6 |
| ☐ | P2 | **Ordonnancement** et **Production** | Ce qui est encore utilisé (le module est abandonné depuis avril 2026) |
| ☐ | P2 | **Achats**, **Réceptions**, **Stocks matières** | Commande fournisseur, réception contre commande, bobines |
| ☐ | P2 | **Comptabilités** : l'export et un fichier exemple | Format attendu par le logiciel comptable |
| ☐ | P2 | **Paramètres** : conditions de paiement, positions fiscales, unités | Listes complètes |
| ☐ | P3 | **Contrôles**, **Appels d'offre**, **Hits parades**, **Statistiques** | Ce que la direction y regarde |
| ☐ | P3 | **Contacts** | Fiche contact |

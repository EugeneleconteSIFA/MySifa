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
| Numérotation observée | Commandes et BL : compteur continu sur 7 chiffres (99xxxxx) ; devis AAMMNNN ; marchés : compteur simple |

## Questions soulevées par ces captures

| # | Question |
|---|---|
| C1 | **Laboratoire** : quelles valeurs existent (Renouvellement, Création… autres ?) et à quoi sert ce champ au quotidien ? |
| C2 | **Type de ligne** « À livrer et facturer » : quelles autres valeurs (à facturer seulement, à livrer seulement, échantillon…) ? |
| C3 | Colonnes **C.C., I.L., I.S., I.F.** (commandes) et **E.C.D., E.I.L., E.I.S., E.I.F., L.C.D…** (devis, marchés) : que signifient-elles ? |
| C4 | **Quantité à fabriquer** différente de la quantité commandée (ex. 1 232 000 pour 1 200 000) : marge de gâche ? règle de calcul ? |
| C5 | **Unité de vente « 11 — Mille »** : la liste des unités de vente utilisées |
| C6 | **Colisage** : étape entre stock PF et livraison — que s'y saisit-il ? |
| C7 | **Code AN** (code client / code article, ex. 1153 / 0003) : l'article est-il toujours propre à un client ? |

## Encore à fournir

| ✓ | Prio | Écran | Ce que je dois voir |
|---|---|---|---|
| ☐ | P1 | **Facturation** : l'écran de facturation et un **PDF de facture** | Comment on part des BL, les mentions, la mise en page |
| ☐ | P1 | **PDF** d'un ARC, d'un BL et d'un devis | Mise en page, mentions |
| ☐ | P1 | **Fiche client**, chaque onglet | Adresses multiples, contacts, conditions, tarifs, encours |
| ☐ | P1 | **Fiche article produit fini**, chaque onglet | Format, unités, conditionnement, prix, liens outil / fiche technique |
| ☐ | P2 | **Colisage** | Voir C6 |
| ☐ | P2 | **Ordonnancement** et **Production** | Ce qui est encore utilisé (le module est abandonné depuis avril 2026) |
| ☐ | P2 | **Achats**, **Réceptions**, **Stocks matières** | Commande fournisseur, réception contre commande, bobines |
| ☐ | P2 | **Comptabilités** : l'export et un fichier exemple | Format attendu par le logiciel comptable |
| ☐ | P2 | **Paramètres** : conditions de paiement, positions fiscales, unités | Listes complètes |
| ☐ | P3 | **Contrôles**, **Appels d'offre**, **Hits parades**, **Statistiques** | Ce que la direction y regarde |
| ☐ | P3 | **Contacts** | Fiche contact |

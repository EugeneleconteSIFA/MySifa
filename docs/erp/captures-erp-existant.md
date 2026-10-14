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
| Fiche client : principal, interlocuteurs, adresses, banques | Fiche client en onglets : code court, groupe, état, identifiants, ADV, catégories, langue, désignation interne / client, BAT à chaque commande, mode de facturation, factor, en compte, escompte, franco, marges de devis, compte de tiers ; interlocuteurs avec service et documents reçus automatiquement (devis, ARC, BL, facture, relance) ; adresses principale / facturation / livraison avec raison sociale, téléphone, e-mail, SIRET ; banques |
| Matières (liste et fiche), TDB stock produits et matières, TDB facturation, fiche facture | Fiche matière : libellés techniques, adhésif, protecteur, film, synthétique, épaisseur ; stock matières par laize (code 3), stock mini / maxi en rouge ; stock produits par client ; TDB facturation complet ; compte comptable par article. Cahier des charges = notes par étape de la chaîne (réponse du 14/10) |
| Fiche produit, liste des produits | Code 3, désignation sur plusieurs lignes, couleur, poids, sous-famille, gamme, cliché, EAN, unités d'achat / de conditionnement / de vente, taxe écologique, code douane, prix de stock, stock mini / maxi, zone, références client 1 à 3, libellé client ; liste avec format, sous-famille, réf. client |
| Facture (consultation) | Situation « à éditer » / « éditée », « à transférer » / « transférée » en comptabilité |
| Affiche FSC « Quelle allégation pour ce dossier » | Allégation calculée des matières consommées par l'OF (la plus basse l'emporte, non FSC et Controlled Wood → non FSC, film / colle / encre ignorés), imprimée sur BL et facture avec le certificat, alerte si un produit vendu certifié ne l'est pas |

## Questions soulevées par ces captures

| # | Question |
|---|---|
| C1 | ✓ Laboratoire = gestion des BAT. Création / modification exigent un BAT validé (module BAT de MySifa, rattaché à l'article) |
| C2 | ✓ À livrer et facturer · à livrer sans facture · à stocker |
| C3 | ~~Colonnes C.C., I.L., I.S., I.F.~~ — abandonnées (réponse du 14/10 : « je ne sais plus ») |
| C4 | ✓ Souvent du stock, en général un bug : la quantité à fabriquer est calculée (reste − stock − déjà produit), jamais saisie |
| C5 | ✓ L'unité de vente change selon le client : elle suit l'article, qui appartient au client (C7) |
| C6 | ✓ Colisage : ne sert à rien chez SIFA — pas repris |
| C7 | ✓ Oui : un produit fini appartient à un client, code « code client / rang », et une pièce de vente n'accepte que les produits de son client |

## Encore à fournir

| ✓ | Prio | Écran | Ce que je dois voir |
|---|---|---|---|
| ✓ | P1 | **Facturation** : TDB et fiche facture reçus (14/10) | Colonnes échéance, remise, TVA, escompte, règlement, encaissement, représentant, saisie par |
| ☐ | P2 | **PDF** d'un devis et d'une confirmation de commande envoyée au client | Mise en page |
| ☐ | P2 | Fiche client : onglets **Livraison**, **Stockage**, **Facturation** (nomenclature : sans objet ; pas d'onglet Tarifs dans RVGI ; cahiers des charges faits) | Ce qu'ils contiennent |
| ☐ | P2 | **Ordonnancement** et **Production** | Ce qui est encore utilisé (le module est abandonné depuis avril 2026) |
| ☐ | P2 | **Achats**, **Réceptions**, **Stocks matières** | Commande fournisseur, réception contre commande, bobines |
| ☐ | P2 | **Comptabilités** : l'export et un fichier exemple | Format attendu par le logiciel comptable |
| ☐ | P2 | **Paramètres** : conditions de paiement, positions fiscales, unités | Listes complètes |
| ☐ | P3 | **Contrôles**, **Appels d'offre**, **Hits parades**, **Statistiques** | Ce que la direction y regarde |
| ☐ | P3 | **Contacts** | Fiche contact |

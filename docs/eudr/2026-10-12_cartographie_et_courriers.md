# EUDR — cartographie fournisseurs et courriers types

Préparé le 12/10/2026. Source : factures fournisseurs RVGI du 01/10/2025 au 12/10/2026
(familles matière 1 à 6), croisées avec la fiche fournisseur MySifa (pays, FSC).

## 1. Constat principal

Environ **2,3 M€ sur 3,4 M€** d'achats de matière papier viennent de **hors UE**
(Chine, Royaume-Uni). Sur ces flux, SIFA n'est pas un opérateur en aval : c'est
**SIFA qui met le papier sur le marché de l'UE**, donc SIFA doit déposer elle-même
une déclaration de diligence raisonnée (DDS) dans TRACES, avec la géolocalisation
des parcelles d'origine du bois — sauf si un importateur établi dans l'UE fait
l'import pour notre compte (à vérifier sur les déclarations en douane).

Pour les fournisseurs établis dans l'UE, l'obligation se limite à collecter et
conserver leurs numéros de référence DDS, puis à les transmettre au client.

## 2. Cartographie (12 derniers mois, HT)

### A. Import hors UE — SIFA probablement opérateur (DDS à déposer)

| Fournisseur | Pays | Achats HT | Ce qui est acheté | Dans le périmètre | FSC |
|---|---|---:|---|---|---|
| Shenzhen Likexin | CN | 1 776 k€ | Thermique et vélin 70 g, glassine, étiquettes finies, PP synthétique | Papier : oui · PP : non | C128270 |
| Suzhou Piaozhihua | CN | 430 k€ | Glassine jaune siliconée (support) | Oui | C140235 |
| Frimpeks | GB | 50 k€ | Thermique, vélin, couché, un peu de PP | Papier : oui | C160714 |
| Rifo Package | CN | 45 k€ | BOPP | Non (plastique) | — |
| Xinzhu | CN | 4 k€ | Étiquettes, PP thermique | À trier | C177953 |

### B. Fournisseurs UE — collecter les numéros de référence DDS

| Fournisseur | Pays | Achats HT | Ce qui est acheté | FSC |
|---|---|---:|---|---|
| Kanzan | DE | 347 k€ | Thermique | C007179 |
| QRT Graphique | FR | 195 k€ | Étiquettes finies sous-traitées | aucun |
| Burgo / Mosaico | IT | 135 k€ | Vélin, couché | C004657 |
| Itasa | ES | 113 k€ | Glassine siliconée | C145439 |
| Rheno | FR | 71 k€ | Jet d'encre 70 g | C104291 (expire le 18/12/2026) |
| Avery Dennison | FR | 50 k€ | PP, PE (films) | C004451 |
| Torraspapel | ES | 46 k€ | Thermique | C011032 |
| Grand Ouest Étiquettes | FR | 35 k€ | Étiquettes finies | C148933 |
| UPM | FI | 33 k€ | PET, PP (films) | C012530 |
| Arconvert / Fedrigoni | ES | 27 k€ | Thermique, vélin (+ PP) | oui |
| Guyenne | FR | 20 k€ | Papier fluo | C114338 |
| Cévennes Étiquettes | FR | 9 k€ | Étiquettes finies | aucun |
| Lefrancq | FR | 7 k€ | Étiquettes finies | C135176 |
| Sodinor, Techmay, E&P Consult, Diatecx, Aster | FR/BE | < 6 k€ chacun | Divers | — |

Hors périmètre probable : films 100 % plastique (PP, PE, PET, BOPP, vinyle).
Une étiquette PP sur support glassine contient toutefois du papier : à confirmer
avec le code douanier retenu.

Emballages (cartons, tubes, mandrins, palettes) : exclus s'ils servent uniquement
à protéger ou à transporter le produit. Pas d'action pour l'instant.

### Points à vérifier en interne
- Le pays du fournisseur dans RVGI (`fpays`) vaut « France » pour tous : il n'est
  pas fiable. Le pays retenu ici vient de la fiche MySifa.
- Importateur de référence pour Likexin et Suzhou : SIFA en direct, ou un
  transitaire / une entité UE ?
- Taille de SIFA : PME. Échéance au 30/06/2027 si « petite entreprise » au sens de la directive 2013/34, soit 2 critères sur 3 : 50 salariés au plus, CA ≤ 15 M€, bilan ≤ 7,5 M€ (seuils relevés en 2023, à confirmer avec l'expert-comptable), sinon 30/12/2026 pour une moyenne entreprise.
- Il manque l'email EUDR de la plupart des fournisseurs dans MySifa.

## 3. Courrier fournisseurs UE (EN)

Subject: EU Deforestation Regulation (EU) 2023/1115 — compliance information

Dear Sir or Madam,

As part of the application of Regulation (EU) 2023/1115 on deforestation-free
products, we are setting up the traceability of the materials we buy from you.

For the products you deliver to us, please let us know:

1. Which products fall under the EUDR, with their CN code (chapter 48 in particular).
2. Your role (operator or downstream operator) and the date from which you will
   file due diligence statements.
3. How you will send us the reference number and verification number of each
   statement: delivery note, invoice, EDI or portal. Our preference is one
   reference per delivery, printed on the delivery note.
4. A contact person for EUDR matters.

We would appreciate your reply by 15 November 2026.

Best regards,

## 4. Courrier fournisseurs hors UE (EN)

Subject: EU Deforestation Regulation (EU) 2023/1115 — information required

Dear Sir or Madam,

From 30 December 2026, paper products imported into the European Union must be
covered by a due diligence statement filed by the operator placing them on the EU
market. For the goods you ship to us, we will act as that operator.

To file these statements, we need for each shipment:

1. The HS code of each product.
2. The species of wood (scientific and common name) used in the pulp.
3. The country of harvest and the geolocation of the plots of land where the
   wood was harvested (GPS points or polygons, in GeoJSON format if possible).
4. The date or period of harvest.
5. Evidence that the wood is deforestation-free after 31 December 2020 and
   legally harvested (certificates, chain-of-custody documents, mill declarations).
6. If your pulp comes from a supplier that already filed an EU due diligence
   statement, its reference number.

FSC certification is helpful but does not replace this information.

Please confirm by 15 November 2026 whether you can provide this data, and in which
format. Without it, we will not be able to import the corresponding products after
30 December 2026.

Best regards,

## 5. Réponse type aux clients

Objet : Règlement EUDR — position de SIFA

Madame, Monsieur,

Vous nous interrogez sur notre conformité au règlement (UE) 2023/1115 (EUDR).

- Nos étiquettes en papier (chapitre 48 de la nomenclature) entrent dans le
  périmètre du règlement. Nos étiquettes sur film synthétique (PP, PE, PET)
  n'y entrent pas.
- Le règlement s'applique aux moyennes entreprises à partir du 30 décembre 2026 et aux petites entreprises à partir du 30 juin 2027. [Garder la date applicable à SIFA.]
- Nous collectons auprès de nos fournisseurs de papier les numéros de référence
  de leurs déclarations de diligence raisonnée. Pour la matière que nous
  importons, nous déposerons nous-mêmes les déclarations.
- À partir de la date d'application, nous indiquerons sur nos documents de livraison les
  numéros de référence correspondant aux produits livrés.

Nous revenons vers vous avec le format de transmission retenu dans les
prochaines semaines.

Cordialement,

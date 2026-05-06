# Business Model — Studio SaaS sur mesure pour PME/TPE

> Version 1.0 — Mai 2026 · Eugène Leconte

---

## 1. Positionnement

**Le problème :**  
Les PME et TPE industrielles accumulent des outils disparates — Excel, petits logiciels, fichiers partagés, Google Sheets — en parallèle de leur ERP. Résultat : les équipes jonglent entre 4 à 8 outils différents, les données se perdent, les process restent dans les têtes.

**La solution :**  
Un outil interne sur mesure, pensé pour les équipes qui l'utilisent, complémentaire à l'ERP existant. Un seul endroit pour tout ce que l'ERP ne couvre pas.

**La preuve :**  
MySIFA — outil déployé chez SIFA (Loos, 59), utilisé quotidiennement par les opérateurs, responsables de production et direction. Remplace Excel de suivi de production, planning papier, fichier de stock, suivi RH et paie. Zéro friction d'adoption.

**Différenciateur :**  
Pas une agence, pas un éditeur de logiciel générique. Un développeur indépendant qui comprend le métier avant de coder — et qui reste disponible après la livraison.

---

## 2. Segments clients

### Cible principale
- **PME industrielles / artisans** : industrie, transformation, fabrication, logistique
- 10 à 150 salariés
- Région Hauts-de-France (priorité Métropole Lilloise), extension nationale possible à partir de 2027
- Disposent d'un ERP (Sage, Cegid, SAP B1, AS400…) mais souffrent de la friction entre l'ERP et les pratiques terrain

### Cible secondaire
- TPE de services (cabinets, petites structures) avec des process manuels non numérisés
- Entreprises ayant déjà subi un échec d'un outil trop complexe ou trop générique

### Critères d'exclusion (ne pas prospecter)
- Startups tech (veulent du SaaS grand public)
- Grands comptes (cycles longs, appels d'offres)
- Secteurs non maîtrisés (santé, finance réglementée)

---

## 3. Proposition de valeur

| Pour qui | Le problème | Notre réponse |
|---|---|---|
| Opérateurs | Jonglent entre Excel et ERP | Un seul outil, pensé pour leur usage quotidien |
| Responsables | Données éparpillées, pas de vue globale | Tableau de bord consolidé, temps réel |
| Direction | Outils coûteux ou inadaptés | Tarif PME, outil 100% ajusté à leur contexte |
| DSI / Gérant | Maintenance difficile | Outil simple, hébergé, maintenu, évolutif |

**Phrase de positionnement :**  
> "Votre ERP fait ce qu'il sait faire. On s'occupe du reste."

**Alternative :**  
> "Un seul outil, fabriqué pour vos équipes."

---

## 4. Modèle de revenus et pricing

### Structure recommandée : Forfait + Abonnement mensuel

#### A. Mise en place (one-shot)

| Niveau | Contexte | Fourchette |
|---|---|---|
| Starter | 1-2 modules, < 30 utilisateurs, process simple | 2 500€ – 4 000€ HT |
| Standard | 3-5 modules, 30-100 utilisateurs, workflows métier | 4 000€ – 7 000€ HT |
| Sur mesure | Intégration ERP, > 100 utilisateurs, logique complexe | 7 000€ – 15 000€ HT |

> Le forfait couvre : audit des besoins, conception, développement, déploiement, formation initiale.

#### B. Abonnement mensuel (SaaS)

| Offre | Contenu | Tarif |
|---|---|---|
| Essentiel | Hébergement VPS dédié, mises à jour de sécurité, support email 48h | 150€ HT/mois |
| Suivi | Essentiel + corrections de bugs, petites évolutions (≤ 2h/mois), support prioritaire | 280€ HT/mois |
| Partenaire | Suivi + évolutions régulières (≤ 6h/mois), réunion mensuelle, roadmap partagée | 490€ HT/mois |

> L'abonnement est la colonne vertébrale du modèle. C'est ce qui permet de passer à temps plein.

#### C. Développements additionnels (régie)
- Tarif : **650€ HT / jour** (≈ 85€/h)
- Facturation sur devis, hors forfait abonnement

---

## 5. Projections financières

### Hypothèses
- Durée de vie client : 3 ans minimum
- Abonnement moyen : 280€/mois
- Setup moyen : 5 000€ HT
- Churn annuel : < 10%

### Trajectoire

| Période | Clients actifs | Récurrent mensuel | Objectif |
|---|---|---|---|
| T4 2025 | 1 (MySIFA) | ~280€ | Validation modèle |
| T2 2026 | 4-6 | ~1 400€ | Premières références |
| T4 2026 | 8-12 | ~2 800-3 400€ | Passage à mi-temps possible |
| T2 2027 | 15-18 | ~4 200-5 000€ | **Passage à 100% indépendant** |
| 2028 | 30 | ~8 400€ | Objectif cible |

> À 30 clients à 280€/mois : **8 400€/mois de récurrent**, avant prestations ponctuelles.  
> Ajouté aux setups (~2-3/an à 5 000€) : **revenus annuels > 110 000€ HT** à l'horizon 2028.

---

## 6. Business Model Canvas

```
┌─────────────────────────────────────────────────────────────────────┐
│  PARTENAIRES CLÉS         │  ACTIVITÉS CLÉS          │  PROPOSITION │
│                           │                          │  DE VALEUR   │
│  · Hébergeurs VPS         │  · Audit besoins         │              │
│    (OVH, Hetzner)         │  · Développement         │  Un seul     │
│  · Comptables /           │  · Déploiement           │  outil fait  │
│    juristes locaux        │  · Maintenance           │  pour vos    │
│  · Réseau CCI Lille       │  · Support client        │  équipes     │
│  · Intégrateurs ERP       │                          │              │
│                           ├──────────────────────────┤              │
│                           │  RESSOURCES CLÉS         │              │
│                           │                          │              │
│                           │  · Compétences full-     │              │
│                           │    stack (FastAPI/JS)    │              │
│                           │  · Référence MySIFA      │              │
│                           │  · Réseau local Lille    │              │
├──────────────────────────────────────────────────────┤              │
│  RELATIONS CLIENTS        │  CANAUX                  │              │
│                           │                          │              │
│  · Relation directe       │  · Bouche-à-oreille      │              │
│    et personnelle         │  · LinkedIn (Hauts-de-F) │              │
│  · Référent unique        │  · CCI / réseaux PME     │              │
│  · Disponibilité          │  · Prospection directe   │              │
│    garantie               │  · Cas client MySIFA     │              │
├───────────────────────────┴──────────────────────────┴──────────────┤
│  STRUCTURE DE COÛTS                    │  FLUX DE REVENUS           │
│                                        │                            │
│  · Hébergement VPS (< 50€/client/mois) │  · Forfait mise en place   │
│  · Outils de développement (~100€/mois)│    (2 500 – 15 000€)       │
│  · Comptabilité / assurance RC pro     │  · Abonnement mensuel      │
│  · Temps (ressource principale)        │    (150 – 490€/mois)       │
│                                        │  · Régie (650€/j)          │
└────────────────────────────────────────┴────────────────────────────┘
```

---

## 7. Risques et mitigation

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Client principal MySIFA se retire | Faible | Élevé | Diversifier à 4+ clients avant fin 2026 |
| Temps de vente trop long (PME frileuses) | Moyen | Moyen | One pager + pilote à tarif réduit |
| Capacité limitée (solo) | Élevé | Moyen | Limiter à 8-10 clients actifs simultanément, prioriser Partenaire |
| Concurrence agences web | Faible | Faible | Positionnement métier, pas agence généraliste |
| Évolution technologique | Faible | Faible | Stack simple et éprouvée (Python/JS), pas de dépendance vendor |

---

## 8. Jalons clés

- **Juin 2026** : 1er client hors MySIFA signé
- **Décembre 2026** : 6-8 clients, récurrent > 2 000€/mois
- **Juillet 2027** : Passage à 100% indépendant
- **Décembre 2027** : 15-20 clients, récurrent > 4 500€/mois
- **2028** : 30 clients, récurrent > 8 000€/mois, potentiel recrutement 1er collaborateur

---

*Document de travail — confidentiel*

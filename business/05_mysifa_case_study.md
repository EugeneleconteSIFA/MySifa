# Étude de cas — MySIFA

> Document de référence pour la prospection · Confidentiel  
> Eugène Leconte — Mai 2026

---

## Contexte client

**Entreprise :** SIFA  
**Secteur :** Industrie (fabrication)  
**Localisation :** Loos, Métropole lilloise (59)  
**Taille :** PME — opérateurs, responsables de production, direction, administration  
**Situation avant :** Outils dispersés, données fragmentées, aucune vue consolidée

---

## Le problème de départ

SIFA utilisait un ensemble d'outils non connectés pour gérer leur activité quotidienne :

- **Planning de production** : fichier Excel partagé, mis à jour manuellement, souvent en conflit de versions
- **Suivi des stocks** : autre fichier Excel, sans historique de mouvements
- **Planning RH** : tableau papier ou fichier Word
- **Saisie de production** : opérateurs saisissaient dans différents endroits selon les postes
- **Suivi des expéditions** : notes manuscrites et emails
- **Préparation de la paie** : collecte manuelle des éléments variables

**Résultat :** Perte de données, doublons, saisies oubliées, responsables sans visibilité temps réel, direction sans tableau de bord fiable.

---

## La solution déployée

### MySIFA — outil interne sur mesure

Déployé sur le VPS de SIFA, accessible depuis tous les postes et mobiles via navigateur.

**Modules en production :**

| Module | Route | Utilisateurs principaux |
|---|---|---|
| Saisie de production | `/prod` | Opérateurs |
| Planning machine | `/planning` | Responsables de production |
| Gestion des stocks | `/stock` | Logistique, responsables |
| Suivi comptable | `/compta` | Administration |
| Gestion des expéditions | `/expe` | Logistique |
| Planning RH | `/planning-rh` | RH, direction |
| Module paie | `/paie` | Administration |
| Paramètres | `/settings` | Super admin |

**Stack technique :** Python 3 / FastAPI · JavaScript vanilla · SQLite · VPS Linux  
**Authentification :** Sessions cookie, durée 6h, rôles par module  
**Hébergement :** VPS dédié SIFA, accès HTTPS

---

## Ce qui a changé

### Avant MySIFA

- 6 à 8 outils différents selon le service
- Données non consolidées entre services
- Aucune traçabilité des saisies de production
- Planning machine sur Excel — conflits fréquents
- Aucun tableau de bord de production en temps réel
- Préparation de paie : collecte manuelle longue

### Avec MySIFA

- Un seul outil pour tous les services
- Données centralisées, accessibles en temps réel
- Chaque opération horodatée et tracée
- Planning machine collaboratif, mis à jour en direct
- Direction : vision globale production / stock / équipes
- Préparation de paie : automatisée depuis les saisies

---

## Points de différenciation

**Adoption** : L'outil a été conçu avec les utilisateurs finaux — les opérateurs ont été consultés dès la phase de conception. Résultat : adoption naturelle, sans formation lourde.

**Simplicité** : Interface claire, sombre, lisible en atelier. Pas de menu complexe. Chaque action accessible en 2-3 clics.

**Fiabilité** : En production depuis plusieurs mois, aucune interruption. Base de données SQLite robuste, backups automatiques.

**Évolutivité** : Modules ajoutés progressivement selon les besoins. Architecture pensée pour être étendue.

---

## Témoignage (à solliciter)

> "Avant, chaque service avait son fichier. Personne ne savait vraiment où on en était. Maintenant tout le monde voit la même chose."
>  
> — [Responsable de production SIFA] *(à confirmer avec accord du client)*

---

## Ce que ce cas démontre

1. **Le modèle fonctionne** — une PME industrielle peut adopter un outil sur mesure sans résistance, si l'outil est bien pensé
2. **Le périmètre est large** — 8 modules couvrant toute l'activité, développés et maintenus par une seule personne
3. **Le coût est maîtrisé** — tarif PME, hébergement dédié, maintenance incluse dans l'abonnement
4. **La preuve est réelle** — pas une démo, pas un prototype. Un outil en production, utilisé tous les jours

---

## À retenir pour la prospection

MySIFA est votre argument numéro 1. Toute PME industrielle qui vous dira "on a notre ERP mais on a plein de fichiers Excel à côté" est votre prospect idéal. MySIFA prouve que le problème est soluble — et que vous savez le résoudre.

**Ne montrez pas des slides d'abord. Montrez MySIFA.**  
Demandez-leur d'abord de décrire leur organisation actuelle. Puis montrez ce que vous avez fait pour SIFA. Laissez la preuve parler.

---

*Document confidentiel — ne pas diffuser sans autorisation*

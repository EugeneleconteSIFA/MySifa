# MySifa — Roadmap

*Dernière mise à jour : mai 2026*

---

## 1. Fiabilité & infrastructure

Ce qui ne peut pas attendre.

- [ ] **Backup automatique de la DB** — cron quotidien vers un bucket S3 ou second disque. La base a déjà été corrompue deux fois ; c'est la priorité absolue.
- [ ] **Monitoring VPS** — uptime + alertes sur erreurs 500. Ne plus apprendre une panne par un opérateur.
- [ ] **Secrets dans `.env`** — aucun identifiant ou clé en dur dans le code.
- [ ] **Logs structurés** — erreurs applicatives centralisées (Sentry ou équivalent léger).

---

## 2. Dashboard direction

Il n'existe pas de vue synthétique pour la direction. Les données sont dans la DB, personne ne les voit agrégées.

- [ ] Route `/dashboard` accessible aux rôles `direction` et `superadmin`
- [ ] KPIs affichés : production du jour vs objectif, machines en cours / à l'arrêt, dossiers en retard, mouvements stock récents
- [ ] Lisible en 10 secondes, sans fouiller les modules

---

## 3. Exports

Les données restent aujourd'hui prisonnières de l'outil.

- [ ] Export Excel : rapport de production hebdomadaire, récap planning, état du stock
- [ ] Export PDF : rapport de production, fiche dossier
- [ ] Accessible depuis chaque module concerné, pas depuis un menu global

---

## 4. Notifications & alertes

L'outil est 100 % pull (on va voir). Il faut du push.

- [ ] Notification système via le widget tray quand une machine passe à l'arrêt inattendu
- [ ] Alerte quand un dossier dépasse son délai prévu
- [ ] Alerte quand un stock passe sous un seuil configuré
- [ ] Notification ciblée par rôle (logistique, fabrication, direction)

---

## 5. MyStock — manques à combler

Module le moins abouti par rapport à l'usage réel.

- [ ] Alertes seuil de stock bas configurables par article
- [ ] Historique des mouvements par emplacement
- [ ] Valorisation du stock (coût unitaire × quantité)

---

## 6. Traçabilité

- [ ] Table `audit_log` : user / action / objet / timestamp sur toutes les actions sensibles (modification dossier, clôture, changement planning, modifications stock)
- [ ] Consultable par `superadmin` depuis les Paramètres

---

## 7. Messagerie contextuelle

Pas de chat général — des échanges liés à des objets métier.

- [ ] Fil de commentaires attaché à un dossier (MyProd / Planning)
- [ ] Annotations sur le planning machine
- [ ] Alerte adressée à un utilisateur spécifique depuis n'importe quel module
- [ ] Notifications in-app pour les messages reçus

---

## 8. Agent IA — plan d'implémentation

### Phase 1 — Socle *(2-3 jours)*

- [ ] Ajouter `ANTHROPIC_API_KEY` dans `.env` et `config.py`
- [ ] Ajouter `anthropic` dans `requirements.txt`
- [ ] Créer `app/routers/ai.py` — route `POST /api/ai/chat`
- [ ] Créer `app/services/ai_context.py` — construit le contexte envoyé à Claude (rôle utilisateur, module actif, données pertinentes)
- [ ] Test basique sans données DB

### Phase 2 — Accès aux données *(3-4 jours)*

Requêtes en lecture seule uniquement. Aucun `UPDATE` ni `INSERT` déclenché par l'agent.

- [ ] Production du jour / semaine / par machine
- [ ] Dossiers en cours, en retard, clôturés
- [ ] État des stocks, alertes seuil bas
- [ ] Planning machine et RH sur une période
- [ ] `DataFetcher` dans `ai_context.py` : reçoit une intention, exécute la bonne requête

> Règle : Claude reçoit des données structurées, jamais un accès direct à la DB ni des requêtes SQL libres.

### Phase 3 — Interface chat *(2-3 jours)*

- [ ] Widget flottant en bas à droite du portail (toutes pages)
- [ ] Panel latéral ou modal sans quitter la page en cours
- [ ] Historique de session en mémoire (pas de persistance DB en phase 1)
- [ ] Design system MySifa : `--card`, `--border`, `--accent`
- [ ] `Ctrl+Enter` pour envoyer

### Phase 4 — Droits par rôle *(1-2 jours)*

Le contexte envoyé à Claude est filtré côté serveur selon le rôle — non contournable.

| Rôle | Périmètre agent |
|---|---|
| `fabrication` | Ses dossiers, sa machine, sa production |
| `logistique` | Stock, mouvements, emplacements |
| `direction` | Tout — KPIs, synthèses, comparatifs |
| `superadmin` | Tout + infos techniques |

### Phase 5 — Capacités avancées *(ongoing)*

- [ ] Détection d'anomalies proactive — cadence en chute, dossier bloqué, stock critique — sans qu'on interroge
- [ ] Actions avec confirmation — l'agent propose, l'utilisateur confirme, le backend exécute
- [ ] Brief quotidien automatique par rôle (direction, logistique, fabrication)
- [ ] Historique des conversations persisté en DB par utilisateur

---

## 9. Widget desktop — finaliser

- [ ] Rebuild Windows signé (`npm run build:win`) avec les nouvelles icônes
- [ ] Distribution via installeur NSIS à jour
- [ ] Mise à jour automatique via `electron-updater`

---

## 10. Dette technique

- [ ] Tests automatisés sur les routes critiques (auth, saisie production, planning)
- [ ] Script de déploiement propre depuis git (pas de copier-coller manuel)
- [ ] Revue des imports `config` — tout doit venir de `config.py` racine, jamais de `app/config.py`

---

## 11. MyCalendrier — améliorations

### Accès & rôles

- [ ] **Ouvrir au-delà du superadmin** — actuellement `require_superadmin` bloque l'accès. Étendre aux rôles `direction`, `administration`, `rh` avec leur périmètre naturel. Un responsable logistique n'a pas besoin de voir la paie, un opérateur fabrication n'a pas besoin des congés de tout le monde.
- [ ] **Filtrage des données par rôle côté API** — le endpoint `/api/calendrier/events` renvoie tout à quiconque y a accès. Filtrer les congés et anniversaires selon le périmètre de l'utilisateur connecté.

### Création & édition d'événements

- [ ] **Créer un événement en cliquant sur un jour vide** — aujourd'hui rien ne se passe. Un clic sur une case vide devrait ouvrir un formulaire rapide : titre, calendrier cible, plage horaire.
- [ ] **Calendrier "personnel" / notes** — un flux libre par utilisateur pour ses propres rappels et rendez-vous, non liés aux modules MySifa. Stocké en DB, visible uniquement par l'utilisateur.
- [ ] **Modifier un événement depuis la popup** — ajouter un bouton "Modifier" dans la popup qui ouvre le module source directement sur l'objet concerné (dossier planning, départ expé, congé RH).

### Navigation & ergonomie

- [ ] **Vue agenda** — liste chronologique des événements à venir sur 7 / 14 / 30 jours. Plus rapide à consulter que la grille pour un briefing matinal.
- [ ] **Mini-calendrier de navigation** — widget compact en sidebar pour sauter directement à une date sans naviguer mois par mois.
- [ ] **Numéros de semaine** — afficher le numéro de semaine ISO en tête de chaque ligne (vue mois) et en en-tête (vue semaine). Indispensable en contexte industriel.
- [ ] **Raccourcis clavier** — `T` = aujourd'hui, `←` / `→` = période précédente/suivante, `M` / `W` / `D` = changer de vue.
- [ ] **Persistance de la vue active** — mémoriser la dernière vue utilisée (mois/semaine/jour) entre sessions.

### Recherche & filtres

- [ ] **Recherche plein texte** — champ de recherche pour filtrer les événements visibles par titre, client, référence. Résultats surlignés dans la grille.
- [ ] **Filtre par plage de dates** — sélectionner une période précise au lieu de naviguer semaine par semaine.

### Enrichissement des flux existants

- [ ] **Congés — afficher le statut** — distinguer visuellement "posé" vs "validé" avec une couleur ou un style différent sur les événements congés.
- [ ] **Expéditions — afficher le statut** — différencier "en attente" et "validé" sur les créneaux expéditions.
- [ ] **Anniversaires — afficher l'âge** — dans la popup, indiquer l'âge atteint cette année.
- [ ] **Jours fériés — afficher en fond de cellule** — plutôt qu'un événement qui prend de la place, griser le fond du jour avec le label en filigrane.

### Export & partage

- [ ] **Export iCal (.ics)** — générer un fichier iCal de la période visible, importable dans Google Calendar, Outlook ou Apple Calendar.
- [ ] **Abonnement live (webcal://)** — URL d'abonnement par calendrier pour que la direction ou les responsables aient les événements MySifa dans leur calendrier personnel en temps réel.
- [ ] **Impression / PDF** — vue mois ou semaine imprimable, propre, pour affichage ou archivage.

### Mobile

- [ ] **Vue agenda par défaut sur mobile** — la grille mois/semaine est illisible sur téléphone. Basculer automatiquement sur une liste chronologique sur petits écrans.
- [ ] **Swipe gauche/droite** — navigation entre périodes au toucher.

---

## 12. Planning machine — améliorations

### Visibilité & navigation

- [ ] **Vue multi-machines** — afficher Cohésio 1, Cohésio 2, DSI et Repiquage côte à côte sur une même timeline. Aujourd'hui on navigue machine par machine ; la charge globale de l'atelier n'est visible nulle part.
- [ ] **Indicateur de charge journalier** — barre de capacité par colonne jour (heures planifiées / heures disponibles). Permet de voir d'un coup d'œil les jours surchargés ou sous-utilisés.
- [ ] **Aller à aujourd'hui** — bouton fixe pour recentrer la vue sur la date courante, quelle que soit la navigation précédente.
- [ ] **Vue agenda** — liste chronologique des dossiers à venir sur 7/14/30 jours, sans la grille timeline. Utile pour les responsables qui veulent un briefing rapide sans manipuler la timeline.

### Planification

- [ ] **Détection de conflits visuels** — surligner les slots qui se chevauchent sur la même machine. Aujourd'hui deux dossiers peuvent se superposer sans alerte.
- [ ] **Dossiers récurrents / templates** — créer un modèle de dossier réutilisable (même client, même opération, durée fixe) et l'instancier en un clic. Évite la re-saisie manuelle pour les séries.
- [ ] **Glisser-déposer inter-machines** — déplacer un slot d'une machine à une autre directement depuis la vue multi-machines.
- [ ] **Contraintes horaires par machine** — afficher visuellement les plages de travail réelles (horaires Cohésio 2 pairs/impairs déjà en DB, pas encore matérialisés sur la grille).

### Lien planning ↔ production

- [ ] **Indicateur d'avancement sur le slot** — afficher sur chaque slot timeline le % de production réelle (heures saisies dans MyProd / durée planifiée). Un slot vert = terminé, orange = en cours, gris = pas commencé.
- [ ] **Alerte dérive** — signal visuel quand un dossier en cours dépasse sa date de fin planifiée sans être clôturé.
- [ ] **Lien direct slot → saisies** — cliquer sur un slot ouvre le détail des saisies de production associées (MyProd), sans changer de page.

### Planning RH — intégration

- [ ] **Disponibilité opérateurs sur la timeline machine** — afficher en bas de chaque colonne jour les opérateurs disponibles (issus de Planning RH). Permet de croiser charge machine et charge humaine.
- [ ] **Alerte sous-effectif** — signaler visuellement les jours où des dossiers sont planifiés mais aucun opérateur n'est disponible.

### Export & partage

- [ ] **Export PDF du planning** — générer un PDF hebdomadaire propre, imprimable, pour affichage en atelier ou transmission. Format paysage, une machine par page.
- [ ] **Export iCal** — permettre l'abonnement au planning depuis Google Calendar, Outlook ou Apple Calendar. Chaque dossier planifié devient un événement.

### UX & ergonomie

- [ ] **Filtres persistants** — les filtres actifs (statut, client, machine) sont mémorisés entre sessions. Aujourd'hui ils se réinitialisent à chaque rechargement.
- [ ] **Historique des modifications** — log des déplacements, créations et suppressions de slots, consultable par admin (qui a bougé quoi, quand).
- [ ] **Raccourcis clavier** — `←` / `→` pour naviguer entre semaines, `T` pour revenir à aujourd'hui, `N` pour créer un nouveau dossier.
- [ ] **Amélioration mobile** — la timeline est difficilement utilisable sur téléphone. Proposer une vue liste simplifiée sur petits écrans plutôt que la grille horizontale.

---

## Ce qui n'est pas prioritaire

- Migration SQLite → PostgreSQL (SQLite tient pour un seul client)
- 2FA (overkill en interne sur réseau local)
- Module Paie (sensible, mieux géré par un logiciel dédié)
- Messagerie générale type Slack (les équipes ont déjà leurs outils)

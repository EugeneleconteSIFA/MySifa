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

### 1.5 Déploiement sans interruption (zero-downtime + rollback)
**Effort : 2–3 jours · Impact : critique**

Aujourd'hui, toute mise à jour modifie directement la version en production. Un crash pendant un déploiement impacte les utilisateurs en temps réel.

**Architecture cible sur le VPS**

```
/home/sifa/
├── production-saas-v1/   (version active)
├── production-saas-v2/   (nouvelle version en préparation)
└── current -> production-saas-v1  (lien symbolique — Nginx et systemd pointent ici)
```

`DB_PATH` dans `.env` pointe toujours vers le même fichier physique (`data/production.db`), indépendamment de la version active. Les deux versions partagent la même base sans jamais la déplacer.

**Workflow de déploiement**

1. Cloner le dépôt dans `production-saas-v2/`
2. Installer les dépendances : `pip install -r requirements.txt`
3. Lancer les migrations DB (`_migrate()` est idempotent)
4. Tester sur le port 8001 : `uvicorn main:app --port 8001`
5. Si OK → basculer : `ln -sfn /home/sifa/production-saas-v2 /home/sifa/current`
6. Recharger le service : `systemctl reload mysifa`

**Rollback immédiat en cas de problème**

```bash
ln -sfn /home/sifa/production-saas-v1 /home/sifa/current
systemctl reload mysifa
```

Retour à l'ancienne version en 5 secondes, sans toucher à la DB.

**Environnement de staging (étape suivante)**

- Sous-domaine `staging.mysifa.com` → même VPS, port différent, même DB en lecture ou DB de test dédiée
- Tester chaque mise à jour sur staging avant de basculer le lien symbolique en production
- Workflow : `dev → staging → tests → production`

**Script `tools/deploy.sh`** à créer :
```bash
#!/bin/bash
# Usage : ./tools/deploy.sh v2
VERSION=$1
DEPLOY_DIR="/home/sifa/production-saas-$VERSION"
git clone ... $DEPLOY_DIR
cd $DEPLOY_DIR && pip install -r requirements.txt --quiet
# Migrations
python -c "from app.core.database import _migrate; _migrate()"
# Bascule
ln -sfn $DEPLOY_DIR /home/sifa/current
systemctl reload mysifa
echo "Déployé : $VERSION"
```

---

## 2. Présence permanente au bureau

Objectif : MySifa est l'onglet qu'on ne ferme jamais. Point de départ naturel de chaque journée. Les leviers ci-dessous sont ordonnés par impact / effort.

---

### 2.1 Favicon badge dynamique
**Effort : 1–2 jours · Impact : élevé**

Le principe : l'onglet MySifa affiche un compteur rouge en temps réel (pattern Gmail) quand des actions sont en attente. Les utilisateurs gardent l'onglet visible pour surveiller le chiffre.

**Ce qui déclenche le badge :**
- Messages non lus dans la messagerie interne (`S.msgUnread` existe déjà)
- Dossiers en attente de validation (direction, administration)
- Alertes stock critique (MyStock, seuil configurable)

**Implémentation — `app/static/favicon-badge.js`**

Créer une fonction `updateFaviconBadge(count)` :
1. Créer un canvas 32×32px
2. Dessiner le favicon de base (lettre "M" en `#f1f5f9` sur fond `#0a0e17`, border-radius 6px)
3. Si `count > 0` : cercle `#f87171` de 12px en haut à droite, chiffre blanc centré (`font: bold 9px system-ui`), texte "9+" si count > 9
4. `document.querySelector('link[rel="icon"]').href = canvas.toDataURL()`

**Endpoint API — `GET /api/alerts/count`** dans `app/routers/` :
- Auth cookie `sifa_token` (pattern standard)
- Retourne `{ total: N, detail: { messages: N, validations: N, stock: N } }`
- Requêtes légères, aucune jointure lourde — lecture directe sur `production.db`
- Si l'utilisateur est sur la page source (ex. sur `/messages`), le compteur messages n'est pas inclus dans le total

**Déclenchement dans le JS frontend (`app/web/html.py`) :**
- Au chargement initial de l'app
- `setInterval` toutes les 60 secondes
- Immédiatement après toute action susceptible de modifier le compte (envoi message, validation dossier, etc.)

**Contraintes :**
- Badge à 0 → favicon standard, aucun cercle rouge
- Fonctionne sur Chrome, Edge, Firefox desktop
- Fonctionne aussi dans la fenêtre PWA (point 2.2)

---

### 2.2 PWA desktop (Progressive Web App)
**Effort : 2–3 jours · Impact : élevé**

Le principe : MySifa s'installe comme une vraie application Windows/Mac depuis Chrome ou Edge — icône dans la barre des tâches, fenêtre standalone sans chrome navigateur, survit à la fermeture du navigateur.

**a) `app/static/manifest.json`** — servi à `/manifest.json` via FastAPI (route statique) :
```json
{
  "name": "MySifa",
  "short_name": "MySifa",
  "description": "Portail interne — Production, stocks et outils métier",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0a0e17",
  "theme_color": "#0a0e17",
  "orientation": "any",
  "icons": [
    { "src": "/static/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/static/icons/icon-512.png", "sizes": "512x512", "type": "image/png" },
    { "src": "/static/icons/icon-maskable-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

**b) Icônes PNG** à créer dans `app/static/icons/` :
- `icon-192.png` : 192×192px — fond `#0a0e17`, texte "My**Sifa**" (Sifa en `#22d3ee`), police Segoe UI bold
- `icon-512.png` : 512×512px, même style, proportions identiques
- `icon-maskable-512.png` : 512×512px, safe area 40% du bord (contenu dans les 60% centraux)

**c) `app/static/sw.js`** — Service Worker minimal :
- Stratégie **Cache First** pour `/static/**` (CSS, JS, icons) → chargement instantané
- Stratégie **Network First** pour les appels API (`/api/**`) → données toujours fraîches
- Pas d'offline complet requis — juste la coque de l'app pour éviter l'écran blanc
- Version du cache à incrémenter à chaque déploiement (`const CACHE = 'mysifa-v1'`)

**d) `<head>` HTML** — ajouter dans `app/web/html.py` (dans la chaîne `_BASE_HTML`) :
```html
<link rel="manifest" href="/manifest.json">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="MySifa">
<link rel="apple-touch-icon" href="/static/icons/icon-192.png">
```

**e) Enregistrement du service worker** — dans le JS frontend, au démarrage de l'app :
```javascript
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}
```

**Comportement attendu :**
- Chrome/Edge affiche une icône d'installation dans la barre d'adresse dès la première visite
- Une fois installé : MySifa apparaît dans les apps Windows/Mac, s'ouvre en fenêtre standalone
- Sur mobile : icône sur l'écran d'accueil, plein écran sans barre navigateur
- Le favicon badge (point 2.1) fonctionne dans la fenêtre PWA

---

### 2.3 Dashboard "début de journée" par rôle
**Effort : 1 semaine**

- [ ] Route `/dashboard` accessible selon le rôle
- [ ] Direction : KPIs production semaine, alertes retard, départs prévus
- [ ] Administration : absences du jour, planning RH, dossiers à valider
- [ ] Comptabilité : dossiers à facturer, pièces manquantes
- [ ] Rafraîchissement automatique toutes les 2 minutes, aucune navigation requise

---

### 2.4 Notifications navigateur (Web Push)
**Effort : 3–4 jours** *(nécessite le service worker du point 2.2)*

- [ ] Notification push quand un dossier passe en retard
- [ ] Notification quand une validation est requise (direction / administration)
- [ ] Notification quand un seuil de stock critique est franchi
- [ ] Opt-in explicite par utilisateur, géré depuis les Paramètres
- [ ] Backend : endpoint VAPID + `app/services/push_notifications.py`

---

### 2.5 Raccourcis clavier globaux
**Effort : 1 jour**

- [ ] `G` + `P` → Planning · `G` + `S` → Stock · `G` + `M` → MyProd · `G` + `C` → Compta
- [ ] `?` → afficher la liste des raccourcis (modal)
- [ ] Listener `keydown` global, désactivé quand le focus est dans un champ texte
- [ ] Pattern identique à Gmail / Linear

---

### 2.6 Sessions longues sur postes fixes
**Effort : 1 jour**

- [ ] Checkbox "Rester connecté" sur l'écran de login
- [ ] Si coché : cookie longue durée 14 jours ; sinon : 6h actuelles
- [ ] Pour les postes partagés, maintenir le comportement 6h par défaut

---

### 2.7 Saisie rapide depuis le portail
**Effort : 2 jours**

- [ ] Bouton "Saisie rapide" sur le portail → modal pré-rempli avec le dernier dossier en cours de l'opérateur
- [ ] Objectif : 2 clics pour enregistrer une action sans naviguer dans MyProd

---

## 3. Dashboard direction

Il n'existe pas de vue synthétique pour la direction. Les données sont dans la DB, personne ne les voit agrégées.

- [ ] Route `/dashboard` accessible aux rôles `direction` et `superadmin`
- [ ] KPIs affichés : production du jour vs objectif, machines en cours / à l'arrêt, dossiers en retard, mouvements stock récents
- [ ] Lisible en 10 secondes, sans fouiller les modules

---

## 4. Exports

Les données restent aujourd'hui prisonnières de l'outil.

- [ ] Export Excel : rapport de production hebdomadaire, récap planning, état du stock
- [ ] Export PDF : rapport de production, fiche dossier
- [ ] Accessible depuis chaque module concerné, pas depuis un menu global

---

## 5. Notifications & alertes

L'outil est 100 % pull (on va voir). Il faut du push.

- [ ] Notification système via le widget tray quand une machine passe à l'arrêt inattendu
- [ ] Alerte quand un dossier dépasse son délai prévu
- [ ] Alerte quand un stock passe sous un seuil configuré
- [ ] Notification ciblée par rôle (logistique, fabrication, direction)

---

## 6. MyStock — manques à combler

Module le moins abouti par rapport à l'usage réel.

- [ ] Alertes seuil de stock bas configurables par article
- [ ] Historique des mouvements par emplacement
- [ ] Valorisation du stock (coût unitaire × quantité)

---

## 7. Traçabilité

- [ ] Table `audit_log` : user / action / objet / timestamp sur toutes les actions sensibles (modification dossier, clôture, changement planning, modifications stock)
- [ ] Consultable par `superadmin` depuis les Paramètres

---

## 8. Messagerie contextuelle

Pas de chat général — des échanges liés à des objets métier.

- [ ] Fil de commentaires attaché à un dossier (MyProd / Planning)
- [ ] Annotations sur le planning machine
- [ ] Alerte adressée à un utilisateur spécifique depuis n'importe quel module
- [ ] Notifications in-app pour les messages reçus

---

## 9. Agent IA ✓

> Livré et opérationnel — mai 2026. Accessible superadmin uniquement pour l'instant.
> Stack : SDK Anthropic officiel, widget intégré au design system MySifa, contexte SIFA injecté automatiquement.

- [x] Nettoyage du prototype existant (chat.py, chatbot_widget.js)
- [x] Socle backend — `app/routers/ai.py`, `app/services/ai_context.py`
- [x] Data fetcher en lecture seule — production, planning, stock, expé, RH
- [x] Widget chat intégré au portail — design system MySifa, bouton waveform
- [x] Droits par rôle — superadmin uniquement, architecture prête pour extension
- [x] `SIFA_CONTEXT.md` — contexte métier injecté dans le system prompt
- [x] SDK installé sur le VPS (`anthropic 0.103.0`)

### Prochaines étapes agent IA

- [ ] Ouverture aux rôles `direction` et `administration` — modifier `ROLE_SCOPE` dans `ai_context.py`
- [ ] Détection d'anomalies proactive — cadence en chute, dossier bloqué, stock critique
- [ ] Actions avec confirmation — l'agent propose, l'utilisateur clique "Confirmer", le backend exécute
- [ ] Brief quotidien automatique par rôle
- [ ] Historique des conversations persisté en DB

---

## 10. Widget desktop — finaliser

- [ ] Rebuild Windows signé (`npm run build:win`) avec les nouvelles icônes
- [ ] Distribution via installeur NSIS à jour
- [ ] Mise à jour automatique via `electron-updater`

---

## 11. Dette technique

- [ ] Tests automatisés sur les routes critiques (auth, saisie production, planning)
- [ ] Script de déploiement propre depuis git (pas de copier-coller manuel)
- [ ] Revue des imports `config` — tout doit venir de `config.py` racine, jamais de `app/config.py`

---

## 12. MyCalendrier — améliorations

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

## 13. Planning machine — améliorations

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

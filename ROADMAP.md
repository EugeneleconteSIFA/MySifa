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

## Ce qui n'est pas prioritaire

- Migration SQLite → PostgreSQL (SQLite tient pour un seul client)
- 2FA (overkill en interne sur réseau local)
- Module Paie (sensible, mieux géré par un logiciel dédié)
- Messagerie générale type Slack (les équipes ont déjà leurs outils)

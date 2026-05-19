# Cursor Prompts — MyCalendrier

Prompts à coller directement dans Cursor, dans l'ordre recommandé.
Chaque prompt est autonome — Cursor a tout le contexte nécessaire dedans.

---

## Prompt 1 — Accès & filtrage par rôle

```
Contexte projet : MySifa est une app FastAPI + SQLite. Le frontend est du HTML/JS vanilla généré en chaînes Python dans app/web/. La source de vérité config est config.py à la racine.

Fichiers concernés :
- app/web/calendrier_page.py (page HTML+JS, ~829 lignes)
- app/routers/calendrier.py (API événements, ~517 lignes)
- services/auth_service.py (fonctions auth existantes)

Tâche : Étendre l'accès à MyCalendrier au-delà du superadmin.

1. Dans app/web/calendrier_page.py, fonction calendrier_page() :
   - Remplacer le check is_superadmin() par une liste de rôles autorisés : superadmin, direction, administration, rh (si ce rôle existe, sinon ignorer).
   - Passer le rôle de l'utilisateur connecté dans le HTML via une variable JS (ex: const USER_ROLE = "direction";) pour que le JS puisse adapter l'interface.

2. Dans app/routers/calendrier.py, endpoint GET /api/calendrier/events :
   - Remplacer require_superadmin() par une vérification qui accepte les rôles autorisés ci-dessus.
   - Appliquer un filtrage des données selon le rôle :
     * direction → tout voir
     * administration → congés, anniversaires, fériés, paie, expéditions (pas les machines production)
     * autres rôles autorisés → congés et fériés uniquement
   - Le filtrage se fait sur le paramètre `calendriers` reçu : supprimer silencieusement les calendriers non autorisés pour le rôle, sans erreur 403.

3. Dans app/web/calendrier_page.py, côté JS :
   - Masquer les toggles de calendriers non accessibles selon USER_ROLE (ne pas les afficher dans la sidebar, ne pas les inclure dans activeCalList()).

Conventions MySifa à respecter :
- Imports de config depuis config (racine), jamais app.config
- Ne jamais modifier DB_PATH
- Design system : variables CSS --bg, --card, --border, --accent, --text, --text2, --muted
- Toasts via showToast(msg, type) — pas d'alert()
- Tout nouveau texte : ton factuel, pas de majuscules décoratives
```

---

## Prompt 2 — Numéros de semaine + jours fériés en fond de cellule

```
Contexte projet : MySifa, FastAPI + SQLite. Frontend HTML/JS vanilla dans app/web/calendrier_page.py (~829 lignes). Design system : variables CSS --bg, --card, --border, --accent, --text, --muted.

Fichiers concernés :
- app/web/calendrier_page.py uniquement

Tâche A — Numéros de semaine ISO dans la vue mois :
- Dans la fonction renderMonth(), ajouter une première colonne "n° semaine" à gauche de chaque ligne de la grille.
- Le numéro de semaine ISO (lundi = début de semaine) se calcule avec la fonction getISOWeek(date) à créer : retourne le numéro 1-53.
- Style de la cellule semaine : fond transparent, texte var(--muted), font-size 11px, font-family monospace, text-align center, non cliquable.
- Adapter le grid-template-columns de la grille mois pour ajouter cette colonne de ~28px en tête.

Tâche B — Jours fériés en fond de cellule (vue mois + vue semaine) :
- Actuellement les jours fériés apparaissent comme des événements qui prennent de la place. Les retirer de la liste des événements positionnés et les afficher en fond de cellule à la place.
- Vue mois : si un jour est férié, ajouter class "cal-day--ferie" à la cellule .cal-day. CSS : background légèrement teinté (rgba de --danger, 0.07), et afficher le label du jour férié en bas de cellule en font-size 10px, color var(--danger), opacity 0.7, truncated.
- Vue semaine et vue jour : même principe sur les colonnes jour concernées — fond légèrement teinté, label en bas.
- Les événements "feries" ne doivent PLUS apparaître dans les fonctions de rendu normales (éviter le double affichage). Créer une map JS feries : { "YYYY-MM-DD": "label" } construite à partir de S.events filtrés sur calendrier === 'feries'.

Conventions : variables CSS uniquement, pas de couleurs codées en dur. Tester que le thème light (body.light) reste cohérent.
```

---

## Prompt 3 — Vue agenda

```
Contexte projet : MySifa, FastAPI + SQLite. Frontend HTML/JS vanilla dans app/web/calendrier_page.py (~829 lignes).

État actuel : 3 vues existent — 'month', 'week', 'day' — gérées par S.view et la fonction setView(v). La fonction renderCalendar() dispatch selon S.view. Les événements sont dans S.events.

Fichiers concernés :
- app/web/calendrier_page.py uniquement

Tâche : Ajouter une vue 'agenda' (liste chronologique des 30 prochains jours).

1. Ajouter le bouton "Agenda" dans la toolbar .cal-view-tabs (après "Jour") et dans la sidebar nav.

2. Dans getPeriod() : si S.view === 'agenda', retourner { start: aujourd'hui, end: aujourd'hui + 29 jours, title: "30 prochains jours" }.

3. Créer la fonction renderAgenda(p) :
   - Grouper S.events visibles (evVisible()) par date, triés chronologiquement.
   - Pour chaque jour de la période (30 jours) qui a au moins un événement : afficher un bloc avec :
     * En-tête du jour : date longue fr-FR (ex "Lundi 3 juin 2026"), numéro de semaine ISO, badge "Aujourd'hui" si applicable. Style : font-weight 600, color var(--text), border-bottom 1px solid var(--border), margin-bottom 8px.
     * Liste des événements du jour : même pill/chip que dans renderMonth() — fond calSlotStyle(cal), titre truncated, heure si pas all_day.
   - Les jours sans événement sont omis (pas de ligne vide).
   - Si aucun événement sur 30 jours : message "Aucun événement à venir." centré, color var(--muted).

4. Dans renderCalendar() : ajouter le cas 'agenda' → renderAgenda(p).

5. Dans shiftAnchor() : pour la vue 'agenda', avancer/reculer de 30 jours.

6. Cliquer sur un événement dans la vue agenda → openPop(ev, el) (déjà existant).

Style général de la vue agenda : pas de grille, layout vertical, fond var(--bg), padding 16px. Chaque bloc jour : card légère (background var(--card), border 1px solid var(--border), border-radius 10px, padding 12px, margin-bottom 12px).
```

---

## Prompt 4 — Création d'événements personnels

```
Contexte projet : MySifa, FastAPI + SQLite. Backend FastAPI dans app/routers/. Frontend HTML/JS vanilla dans app/web/calendrier_page.py (~829 lignes). DB dans data/production.db. Migrations numérotées dans app/core/database.py via la table schema_migrations.

Fichiers concernés :
- app/core/database.py (ajouter migration)
- app/routers/calendrier.py (nouvelles routes CRUD)
- app/web/calendrier_page.py (UI création + affichage)
- app/static/mysifa_calendar.js (ajouter 'perso' dans CAL_DEFS)

Tâche : Calendrier personnel — chaque utilisateur peut créer ses propres événements.

--- PARTIE 1 : DB ---
Dans app/core/database.py, ajouter une migration numérotée (vérifier le dernier numéro existant) :
```sql
CREATE TABLE IF NOT EXISTS cal_events_perso (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    titre TEXT NOT NULL,
    date_debut TEXT NOT NULL,  -- YYYY-MM-DDTHH:MM
    date_fin TEXT NOT NULL,    -- YYYY-MM-DDTHH:MM
    all_day INTEGER DEFAULT 0,
    note TEXT,
    created_at TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%S','now','localtime')),
    FOREIGN KEY(user_id) REFERENCES users(id)
)
```

--- PARTIE 2 : API ---
Dans app/routers/calendrier.py, ajouter 3 routes (accessibles à tous les rôles autorisés, pas seulement superadmin) :
- POST /api/calendrier/events/perso → créer un événement (body: titre, date_debut, date_fin, all_day, note). Lier à l'user_id de la session.
- DELETE /api/calendrier/events/perso/{id} → supprimer (vérifier que l'event appartient à l'utilisateur connecté).
- Modifier GET /api/calendrier/events : si 'perso' est dans la liste des calendriers demandés, ajouter les événements perso de l'utilisateur connecté. Format identique aux autres events (id: "perso-{id}", calendrier: "perso").

--- PARTIE 3 : Frontend ---
Dans app/static/mysifa_calendar.js :
- Ajouter { id: 'perso', label: 'Personnel', color: '#f97316' } dans CAL_DEFS.
- Ajouter 'perso' dans VALID_CALENDARS et DEFAULT_CALENDARS dans calendrier.py.

Dans app/web/calendrier_page.py :
- Clic sur une cellule vide (jour en vue mois, créneau horaire en vue semaine/jour) → ouvrir une modale de création.
- Modale de création : champ titre (required), toggle all_day, date_debut + date_fin (pré-remplis avec le jour cliqué), champ note (optionnel). Bouton "Créer" → POST /api/calendrier/events/perso → fetchEvents() → fermer modale → showToast("Événement créé.", "success").
- Dans la popup openPop() d'un event perso : ajouter un bouton "Supprimer" → DELETE /api/calendrier/events/perso/{id} → fetchEvents() → closePop() → showToast("Événement supprimé.", "success").

Style modale : identique aux autres modales MySifa — fond var(--card), border var(--border), border-radius 12px, backdrop blur. Injecter dans document.getElementById("mroot") ou dans un div modal dédié.
Conventions : escHtml() sur toute interpolation utilisateur, pas d'alert(), showToast() pour les retours.
```

---

## Prompt 5 — Raccourcis clavier, persistance vue, mini-calendrier

```
Contexte projet : MySifa, FastAPI + SQLite. Frontend HTML/JS vanilla dans app/web/calendrier_page.py (~829 lignes). État global dans l'objet S = { view, anchor, events, ... }.

Fichiers concernés :
- app/web/calendrier_page.py uniquement

Tâche A — Raccourcis clavier :
Ajouter un écouteur document.addEventListener('keydown', ...) qui ignore les événements si le focus est dans un input/textarea.
Raccourcis :
- T → setView actuel conservé, anchor = new Date() (aujourd'hui), fetchEvents()
- ArrowLeft → shiftAnchor(-1)
- ArrowRight → shiftAnchor(1)
- M → setView('month')
- W → setView('week')
- D → setView('day')
- A → setView('agenda') (si la vue agenda a été ajoutée)
- Escape → closePop() si une popup est ouverte

Ajouter un tooltip discret dans la toolbar (icône ? ou texte "Raccourcis") qui affiche au hover la liste des raccourcis. Style : position absolute, fond var(--card), border var(--border), border-radius 8px, font-size 12px, z-index 200.

Tâche B — Persistance de la vue active :
- À chaque appel setView(v), sauvegarder dans localStorage : localStorage.setItem('mysifa_cal_view', v)
- Au chargement (DOMContentLoaded), lire localStorage.getItem('mysifa_cal_view') et initialiser S.view avec cette valeur si elle est valide ('month', 'week', 'day', 'agenda'). Sinon fallback 'month'.

Tâche C — Mini-calendrier de navigation (sidebar) :
Ajouter dans la sidebar, entre les toggles calendriers et le .sidebar-bottom, un mini-calendrier de navigation.
- Affiche le mois de S.anchor : grille 7 colonnes (L M M J V S D), jours du mois.
- Le jour aujourd'hui est surligné (background var(--accent), color var(--bg), border-radius 50%).
- Le jour/la semaine actuellement affichée est indiquée (background var(--accent-bg)).
- Cliquer sur un jour → S.anchor = ce jour, fetchEvents(), renderCalendar().
- Flèches ← → en haut du mini-calendrier pour changer le mois affiché indépendamment de la vue principale.
- Style compact : cellules 24px × 24px, font-size 11px, font-family monospace pour l'alignement.
- Le mini-calendrier se re-render à chaque fetchEvents() et chaque setView().
```

---

## Prompt 6 — Export iCal + impression PDF

```
Contexte projet : MySifa, FastAPI + SQLite. Backend FastAPI dans app/routers/calendrier.py. Frontend HTML/JS vanilla dans app/web/calendrier_page.py (~829 lignes).

Fichiers concernés :
- app/routers/calendrier.py (nouvelle route export)
- app/web/calendrier_page.py (bouton export + print CSS)

Tâche A — Export iCal (.ics) :
Dans app/routers/calendrier.py, ajouter la route :
GET /api/calendrier/export.ics?date_debut=YYYY-MM-DD&date_fin=YYYY-MM-DD&calendriers=...

- Mêmes paramètres que /api/calendrier/events.
- Même logique de récupération des événements (réutiliser le code existant).
- Générer un fichier .ics valide (RFC 5545) :
  * En-tête : BEGIN:VCALENDAR, VERSION:2.0, PRODID:-//MySifa//MyCalendrier//FR, CALSCALE:GREGORIAN, METHOD:PUBLISH
  * Pour chaque événement : BEGIN:VEVENT, UID:{id}@mysifa, DTSTART, DTEND, SUMMARY:{titre}, DESCRIPTION:{meta en JSON lisible}, END:VEVENT
  * Pour les événements all_day : DTSTART;VALUE=DATE:YYYYMMDD, DTEND;VALUE=DATE:YYYYMMDD
  * Pour les événements horaires : DTSTART:YYYYMMDDTHHmmss, DTEND:YYYYMMDDTHHmmss
  * Pied : END:VCALENDAR
- Retourner une Response avec Content-Type: text/calendar; charset=utf-8 et Content-Disposition: attachment; filename="mysifa-calendrier.ics"
- Même contrôle d'accès que /api/calendrier/events.

Dans app/web/calendrier_page.py :
- Ajouter un bouton "Exporter .ics" dans la .cal-toolbar (style .cal-btn, à côté des boutons de navigation).
- Au clic : construire l'URL /api/calendrier/export.ics avec les paramètres de la période courante (getPeriod()) et les calendriers actifs (activeCalList()), puis déclencher le téléchargement via window.location.href = url.

Tâche B — Impression :
- Ajouter un bouton "Imprimer" dans la .cal-toolbar.
- Au clic : appeler window.print().
- Ajouter un bloc @media print dans le CSS de calendrier_page.py :
  * Masquer : .sidebar, .cal-toolbar, .mobile-topbar, les boutons, les toggles, .cal-pop
  * Afficher uniquement .cal-body en pleine largeur
  * Forcer fond blanc, texte noir, border visible sur les cellules
  * Ajouter le titre de la période (cal-title) en en-tête de page
  * page-break-inside: avoid sur les cellules de la grille mois
```

---

## Prompt 7 — Mobile : vue agenda automatique + swipe

```
Contexte projet : MySifa, FastAPI + SQLite. Frontend HTML/JS vanilla dans app/web/calendrier_page.py (~829 lignes). L'état global est dans S = { view, anchor, ... }. setView(v) change la vue et rerend.

Fichiers concernés :
- app/web/calendrier_page.py uniquement

Tâche A — Vue agenda par défaut sur mobile :
- Au chargement (DOMContentLoaded), détecter si l'écran est mobile : window.innerWidth < 768.
- Si mobile ET qu'aucune vue n'est sauvegardée en localStorage, initialiser S.view = 'agenda' au lieu de 'month'.
- Masquer les boutons de vue "Mois" et "Semaine" sur mobile (display:none via CSS @media max-width:767px) — trop complexes sur petit écran.
- Sur mobile, la .cal-toolbar affiche uniquement : bouton Précédent, titre période, bouton Suivant, bouton Aujourd'hui. Les view-tabs sont masqués.
- Le .sidebar est remplacé par le comportement mobile existant (burger menu).

Tâche B — Swipe gauche/droite pour naviguer entre périodes :
Sur le conteneur #cal-body, ajouter des listeners touch :
- touchstart : enregistrer S._touchStartX = event.touches[0].clientX
- touchend : calculer delta = event.changedTouches[0].clientX - S._touchStartX
  * delta < -50 → shiftAnchor(+1) (swipe vers gauche = période suivante)
  * delta > +50 → shiftAnchor(-1) (swipe vers droite = période précédente)
  * Ignorer si delta < 50px (éviter les faux positifs au scroll vertical)
- Ne pas interférer avec le scroll vertical : utiliser { passive: true } sur touchstart.

Tâche C — CSS mobile :
Vérifier et corriger les points suivants dans @media (max-width: 767px) :
- La vue agenda doit prendre toute la largeur disponible, padding 12px.
- Les pills d'événements dans la vue agenda doivent être lisibles (min-height 32px, font-size 13px).
- Les popups openPop() doivent apparaître en bas de l'écran (position fixed, bottom 0, left 0, right 0, border-radius 12px 12px 0 0, max-height 60vh, overflow-y auto) plutôt qu'en position absolue flottante.
```

---

## Ordre d'exécution recommandé

1. Prompt 1 — Accès & rôles *(débloque l'outil pour les bons utilisateurs)*
2. Prompt 2 — Numéros de semaine + fériés en fond *(amélioration visuelle rapide)*
3. Prompt 3 — Vue agenda *(nouvelle vue, base du mobile)*
4. Prompt 5 — Raccourcis + persistance + mini-calendrier *(UX, pas de DB)*
5. Prompt 4 — Événements personnels *(migration DB + CRUD complet)*
6. Prompt 6 — Export iCal + impression *(utilitaire, indépendant)*
7. Prompt 7 — Mobile *(finalisation, dépend de la vue agenda)*

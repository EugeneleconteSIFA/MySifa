# MySifa — Prompts Cursor : Module MyAO (Appels d'offre)

> Exécuter ces 6 prompts dans l'ordre. Chacun suppose que le précédent est terminé et commité.

---

## PROMPT 1 — Infrastructure email (SMTP)

```
Tu travailles sur MySifa, une application FastAPI + SQLite.
Le point d'entrée est main.py à la racine. La config centrale est config.py (racine) — c'est la source de vérité, ne jamais importer depuis app/config.py.

MySifa n'envoie pas encore d'emails. Il faut créer l'infrastructure email.

### 1. config.py (racine)

Ajouter à la fin, après les variables existantes :

```python
# Email SMTP
SMTP_HOST     = os.getenv("SMTP_HOST", "")
SMTP_PORT     = int(os.getenv("SMTP_PORT", 587))
SMTP_USER     = os.getenv("SMTP_USER", "")
SMTP_PASS     = os.getenv("SMTP_PASS", "")
SMTP_FROM     = os.getenv("SMTP_FROM", "noreply@mysifa.fr")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "MySifa")

# URL de base (pour construire les liens dans les emails)
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
```

### 2. app/services/email_service.py (créer)

Implémenter :

```python
def send_email(
    to: str | list[str],
    subject: str,
    html_body: str,
    reply_to: str = None
) -> bool:
```

Règles :
- Utiliser smtplib + ssl + email.mime.multipart.MIMEMultipart + email.mime.text.MIMEText
- STARTTLS sur le port configuré (587 par défaut)
- Retourner True si envoi OK, False sinon — logger l'erreur, ne jamais lever d'exception vers l'appelant
- Si SMTP_HOST est vide, logger un warning "Email non configuré" et retourner False proprement
- Chaque appel ouvre et ferme sa propre connexion SMTP (thread-safe)
- `to` peut être une string ou une liste de strings

### 3. .env.example (créer s'il n'existe pas, sinon ajouter)

```
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASS=motdepasse
SMTP_FROM=noreply@mysifa.fr
SMTP_FROM_NAME=MySifa
BASE_URL=https://mysifa.mondomaine.fr
```

### Contraintes
- Ne jamais modifier .env réel
- Ne jamais modifier DB_PATH ni la logique existante
- Importer config depuis `config` (racine), jamais `app.config`
```

---

## PROMPT 2 — Base de données : tables MyAO

```
Tu travailles sur MySifa (FastAPI + SQLite).
Les migrations sont dans app/core/database.py, fonction _migrate(), versionnées via la table schema_migrations.
Pattern de migration existant : `if not conn.execute("SELECT 1 FROM schema_migrations WHERE version=N LIMIT 1").fetchone():`

Trouver le numéro de version courant (lire _migrate()) et incrémenter à partir de là.
Ajouter 6 nouvelles migrations numérotées, une par table.

### Tables à créer

**ao_demandes**
```sql
CREATE TABLE ao_demandes (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  reference         TEXT NOT NULL UNIQUE,        -- ex: AO-2025-001
  titre             TEXT NOT NULL,
  description       TEXT,
  date_creation     TEXT NOT NULL,               -- ISO 8601, heure Paris
  date_limite       TEXT,                        -- date limite de réponse
  statut            TEXT NOT NULL DEFAULT 'brouillon',  -- brouillon | envoyee | cloturee
  created_by        INTEGER,                     -- user id MySifa
  responsable_email TEXT                         -- destinataire des accusés de réception
)
```

**ao_lignes**
```sql
CREATE TABLE ao_lignes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  ao_id       INTEGER NOT NULL REFERENCES ao_demandes(id) ON DELETE CASCADE,
  ref_produit TEXT NOT NULL,
  designation TEXT NOT NULL,
  quantite    REAL NOT NULL,
  unite       TEXT DEFAULT 'unité',
  notes       TEXT,
  position    INTEGER DEFAULT 0
)
```

**ao_fournisseurs**
```sql
CREATE TABLE ao_fournisseurs (
  id               INTEGER PRIMARY KEY AUTOINCREMENT,
  ao_id            INTEGER NOT NULL REFERENCES ao_demandes(id) ON DELETE CASCADE,
  nom_fournisseur  TEXT NOT NULL,
  email_contact    TEXT NOT NULL,
  token            TEXT NOT NULL UNIQUE,   -- UUID v4, lien d'accès portail
  statut           TEXT NOT NULL DEFAULT 'invite',  -- invite | ouvert | repondu | decline
  date_envoi       TEXT,
  date_ouverture   TEXT,
  date_reponse     TEXT,
  commentaire_global TEXT
)
```

**ao_reponses**
```sql
CREATE TABLE ao_reponses (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  ao_fournisseur_id  INTEGER NOT NULL REFERENCES ao_fournisseurs(id) ON DELETE CASCADE,
  ligne_id           INTEGER NOT NULL REFERENCES ao_lignes(id) ON DELETE CASCADE,
  prix_unitaire      REAL,
  delai_jours        INTEGER,
  commentaire        TEXT,
  UNIQUE(ao_fournisseur_id, ligne_id)
)
```

**ao_messages**
```sql
CREATE TABLE ao_messages (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  ao_fournisseur_id INTEGER NOT NULL REFERENCES ao_fournisseurs(id) ON DELETE CASCADE,
  expediteur        TEXT NOT NULL,   -- 'interne' | 'fournisseur'
  auteur_nom        TEXT,
  message           TEXT NOT NULL,
  date              TEXT NOT NULL,
  lu                INTEGER DEFAULT 0
)
```

**ao_pieces_jointes**
```sql
CREATE TABLE ao_pieces_jointes (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  ao_id             INTEGER REFERENCES ao_demandes(id) ON DELETE CASCADE,
  ao_fournisseur_id INTEGER REFERENCES ao_fournisseurs(id) ON DELETE CASCADE,
  filename          TEXT NOT NULL,
  stored_name       TEXT NOT NULL,   -- UUID4 + extension originale
  taille_octets     INTEGER,
  uploaded_by       TEXT,            -- 'interne' | nom fournisseur
  date              TEXT NOT NULL
)
```

### Contraintes
- Pattern exact : une migration numérotée par table, avec le guard SELECT FROM schema_migrations
- Ne jamais recréer une table existante (IF NOT EXISTS)
- Ne jamais modifier DB_PATH ni les tables existantes
- Appeler _migrate() depuis le point d'entrée existant (ne pas changer la logique d'initialisation)
```

---

## PROMPT 3 — Backend : routes internes MyAO

```
Tu travailles sur MySifa (FastAPI + SQLite).
Créer app/routers/ao.py et l'enregistrer dans main.py.
Auth : cookie sifa_token — utiliser exactement le même pattern que les autres routers (lire app/routers/fabrication.py pour le pattern get_current_user / session).
Importer config depuis `config` (racine).

Ce router gère le module MyAO côté interne (utilisateurs MySifa authentifiés).
Rôles autorisés : superadmin, direction, administration, commercial.

---

### Génération de référence AO

Fonction interne `_gen_reference(conn) -> str` :
- Format : AO-{YYYY}-{seq 3 chiffres} ex: AO-2025-007
- seq = COUNT des AO créés cette année + 1
- Garantir l'unicité (retry si collision)

---

### Routes à implémenter

#### Liste et création
- GET /api/ao
  Retourne : liste [{id, reference, titre, statut, date_creation, date_limite, nb_fournisseurs, nb_reponses}]
  nb_fournisseurs = COUNT(ao_fournisseurs WHERE ao_id)
  nb_reponses = COUNT(ao_fournisseurs WHERE ao_id AND statut='repondu')

- POST /api/ao
  Body : {titre, description, date_limite, responsable_email}
  Génère reference via _gen_reference()
  date_creation = maintenant heure Paris
  statut = 'brouillon'
  Retourne l'AO créé complet

#### Détail
- GET /api/ao/{ao_id}
  Retourne : ao + lignes[] + fournisseurs[] (avec statut) + résumé (nb_reponses)

- PUT /api/ao/{ao_id}
  Body : {titre, description, date_limite, responsable_email}
  Uniquement si statut = 'brouillon', sinon 400

- PATCH /api/ao/{ao_id}/cloturer
  statut → 'cloturee'
  Uniquement si statut = 'envoyee', sinon 400

#### Lignes
- POST /api/ao/{ao_id}/lignes
  Body : {ref_produit, designation, quantite, unite, notes}
  position = MAX(position)+1 dans l'AO
  Uniquement si statut = 'brouillon'

- PUT /api/ao/{ao_id}/lignes/{ligne_id}
  Body : {ref_produit, designation, quantite, unite, notes}
  Uniquement si statut = 'brouillon'

- DELETE /api/ao/{ao_id}/lignes/{ligne_id}
  Uniquement si statut = 'brouillon'

#### Fournisseurs
- POST /api/ao/{ao_id}/fournisseurs
  Body : {nom_fournisseur, email_contact}
  Générer token = str(uuid.uuid4())
  Ne pas envoyer l'email ici
  Retourner le fournisseur créé avec son token

- DELETE /api/ao/{ao_id}/fournisseurs/{fourni_id}
  Uniquement si statut fournisseur != 'repondu', sinon 400 avec message explicite

#### Envoi
- POST /api/ao/{ao_id}/envoyer
  Pour chaque fournisseur avec statut = 'invite' ET date_envoi IS NULL :
    - Construire lien : {BASE_URL}/portail/ao/{token}
    - Appeler send_email() depuis app.services.email_service
    - Email : objet = "[MySifa] Demande de prix — {reference} — {titre}"
    - Corps HTML : voir template dans prompt 6
    - Si envoi OK → date_envoi = maintenant, statut = 'invite' (inchangé)
    - Logger les KO sans bloquer les autres
  Mettre statut AO → 'envoyee'
  Retourner : {envoyes: N, erreurs: M}

#### Pièces jointes
- POST /api/ao/{ao_id}/pieces-jointes
  Multipart/form-data, champ "file"
  Stocker dans data/uploads/ao/{ao_id}/
  stored_name = str(uuid.uuid4()) + extension originale (lowercase)
  Insérer dans ao_pieces_jointes (ao_id=ao_id, uploaded_by='interne')

- GET /api/ao/{ao_id}/pieces-jointes
  Retourne liste des PJ de l'AO

- DELETE /api/ao/{ao_id}/pieces-jointes/{pj_id}
  Supprimer fichier sur disque + enregistrement DB

- GET /api/ao/{ao_id}/pieces-jointes/{pj_id}/download
  FileResponse avec le bon filename d'origine

#### Messagerie
- GET /api/ao/{ao_id}/fournisseurs/{fourni_id}/messages
  Retourne liste messages triés par date ASC
  Marquer lu=1 sur tous les messages expediteur='fournisseur' non lus

- POST /api/ao/{ao_id}/fournisseurs/{fourni_id}/messages
  Body : {message}
  Insérer (expediteur='interne', auteur_nom=nom de l'user connecté)
  Envoyer email au fournisseur :
    Objet : "[MySifa] Nouveau message — {reference}"
    Corps : "Vous avez reçu un message concernant l'appel d'offre {reference}.\n\n{message}\n\nAccéder à la demande : {BASE_URL}/portail/ao/{token}"

#### Comparaison des prix
- GET /api/ao/{ao_id}/comparaison
  Retourne :
  {
    lignes: [
      {
        id, ref_produit, designation, quantite, unite,
        reponses: [
          {fourni_id, nom_fournisseur, prix_unitaire, delai_jours, commentaire}
        ],
        prix_min, prix_max, prix_moyen   -- calculés côté serveur, null si aucune réponse
      }
    ],
    fournisseurs: [{id, nom_fournisseur, statut}]
  }
```

---

## PROMPT 4 — Backend : portail fournisseur (routes publiques)

```
Tu travailles sur MySifa (FastAPI + SQLite).
Créer app/routers/ao_portail.py et l'enregistrer dans main.py.

Ces routes sont PUBLIQUES : pas de cookie sifa_token.
La sécurité repose uniquement sur le token UUID dans l'URL.
Importer config depuis `config` (racine).

---

### Helper interne

```python
def _get_fourni_or_404(token: str, conn) -> dict:
    """Retourne (ao, fournisseur) ou lève HTTPException 404."""
```

Vérifier que le token existe dans ao_fournisseurs.
Retourner aussi l'ao_demande associé.
Lever HTTPException(404) si token inconnu.

---

### Routes HTML

- GET /portail/ao/{token}
  Retourne la page HTML du portail fournisseur (depuis app/web/ao_portail_page.py, à créer au prompt 6)
  Si premier accès (date_ouverture IS NULL) : mettre ao_fournisseurs.statut → 'ouvert', date_ouverture = maintenant
  Si token invalide : retourner page HTML 404 sobre (pas de crash JSON)

---

### Routes API JSON (préfixe /api/portail)

- GET /api/portail/ao/{token}
  Retourne :
  {
    ao: {id, reference, titre, description, date_limite, statut},
    fournisseur: {id, nom_fournisseur, statut, commentaire_global},
    lignes: [{id, ref_produit, designation, quantite, unite, notes, position}],
    reponses: [{ligne_id, prix_unitaire, delai_jours, commentaire}],
    pj_ao: [{id, filename, taille_octets}],
    pj_fournisseur: [{id, filename, taille_octets}],
    cloture: bool   -- true si ao.statut = 'cloturee'
  }
  Un fournisseur ne voit PAS les réponses des autres fournisseurs.

- POST /api/portail/ao/{token}/repondre
  Si ao.statut = 'cloturee' → 403 "Cet appel d'offre est clôturé."
  Body : {lignes: [{ligne_id, prix_unitaire, delai_jours, commentaire}], commentaire_global}
  UPSERT dans ao_reponses : INSERT OR REPLACE INTO ao_reponses(ao_fournisseur_id, ligne_id, prix_unitaire, delai_jours, commentaire)
  Mettre ao_fournisseurs : statut='repondu', date_reponse=maintenant, commentaire_global
  Envoyer email d'accusé de réception au ao_demandes.responsable_email :
    Objet : "[MySifa] Réponse reçue — {reference} — {nom_fournisseur}"
    Corps HTML :
      "Le fournisseur {nom_fournisseur} a soumis une offre pour {reference} — {titre}."
      Tableau récap : ref_produit | designation | qté | prix proposé | délai
      "Connectez-vous à MySifa pour consulter la comparaison."
  Retourner {ok: true}

- GET /api/portail/ao/{token}/messages
  Retourne liste messages triés ASC

- POST /api/portail/ao/{token}/messages
  Si ao.statut = 'cloturee' → 403
  Body : {message}
  Insérer (expediteur='fournisseur', auteur_nom=nom_fournisseur, lu=0)
  Envoyer email au responsable_email :
    Objet : "[MySifa] Message de {nom_fournisseur} — {reference}"
    Corps : "{nom_fournisseur} vous a envoyé un message :\n\n{message}\n\nLien : {BASE_URL}/portail/ao/{token}"
  Retourner {ok: true, message: {...}}

- POST /api/portail/ao/{token}/pieces-jointes
  Si ao.statut = 'cloturee' → 403
  Multipart/form-data, champ "file"
  Stocker dans data/uploads/ao/{ao_id}/fournisseurs/{fourni_id}/
  Insérer dans ao_pieces_jointes (ao_fournisseur_id=fourni_id, uploaded_by=nom_fournisseur)
  Retourner {ok: true, pj: {...}}

- GET /api/portail/ao/{token}/pieces-jointes/{pj_id}/download
  Vérifier que la PJ appartient à cet AO (ao_id correspond)
  FileResponse

- GET /api/portail/ao/{token}/pj-ao/{pj_id}/download
  PJ de l'AO (visibles par le fournisseur)
  Vérifier que la PJ appartient au même AO que le token
  FileResponse

### Sécurité
- Rate limit basique en mémoire : dict IP → nb tentatives token invalide
  Si > 10 tentatives invalides par IP sur la dernière heure → 429 "Trop de tentatives."
  (Un simple dict module-level suffit, pas besoin de Redis)
```

---

## PROMPT 5 — Frontend : page interne MyAO

```
Tu travailles sur MySifa (FastAPI + SQLite + HTML/CSS/JS vanilla).
Créer app/web/ao_page.py.

Conventions obligatoires (lire CLAUDE.md pour les détails) :
- Design system : variables CSS --bg, --card, --border, --text, --text2, --muted, --accent, --accent-bg, --success, --warn, --danger
- Police : 'Segoe UI', system-ui, sans-serif
- Sidebar identique à html.py (copier fidèlement, ajouter le lien /ao actif)
- Topbar mobile standard
- Pas de couleurs codées en dur
- Pas d'emojis dans les icônes fonctionnelles (SVG inline)
- Toasts via showToast(message, type) — pas d'alert()
- État central dans objet S — pas de variables globales séparées
- Préserver scroll et focus lors des re-renders (pattern CLAUDE.md)
- escHtml() et escAttr() sur toutes les données utilisateur interpolées dans le HTML

La page est accessible à GET /ao.
Rôles autorisés : superadmin, direction, administration, commercial.

---

### Structure générale

```
[Sidebar standard, lien /ao actif]
[Topbar mobile standard]
[Zone principale]
  → Vue LISTE (défaut)
  → Vue DÉTAIL (chargée via JS sans rechargement de page)
```

---

### Vue LISTE

Header :
- Titre "Appels d'offre"
- Bouton "+ Nouvel appel d'offre" → ouvre modal de création

Filtres :
- Tabs : Tous | Brouillon | Envoyée | Clôturée

Tableau des AO :
- Colonnes : Référence | Titre | Statut | Date limite | Fournisseurs | Réponses | Actions
- Statut = badge coloré : brouillon=--muted, envoyée=--warn, clôturée=--success
- Actions : bouton "Voir" → charge la vue détail
- Si liste vide : état vide (texte + sous-texte)

Modal "Nouvel appel d'offre" :
- Champs : Titre (requis), Description (textarea), Date limite (date input), Email responsable (requis)
- Boutons : Annuler / Créer
- POST /api/ao → recharger la liste

---

### Vue DÉTAIL

Breadcrumb : "Appels d'offre > {reference} — {titre}"
Bouton retour liste.

Header : référence | titre | badge statut | date limite | responsable

Boutons d'action (selon statut) :
- Si brouillon : "Envoyer aux fournisseurs" (actif seulement si >= 1 ligne ET >= 1 fournisseur)
- Si envoyée : "Clôturer l'AO"
- Toujours : "Retour liste"

Confirmation avant "Envoyer aux fournisseurs" : modal "Cette action enverra les emails aux X fournisseurs. Confirmer ?"

Onglets :

**1. Lignes**
Si brouillon : bouton "+ Ajouter une ligne"
Tableau : position | ref_produit | designation | quantite + unite | notes | actions (modifier, supprimer)
Modal ajout/modification : ref_produit, designation, quantite, unite, notes
Supprimer : confirmation inline

**2. Fournisseurs**
Bouton "+ Ajouter un fournisseur" (si statut != cloturee)
Tableau : Nom | Email | Statut | Date envoi | Date réponse | Actions
Statut badges : invite=--muted, ouvert=--warn, repondu=--success
Actions par fournisseur :
  - "Copier lien portail" → navigator.clipboard.writeText(lien) + toast
  - "Messagerie" → charge l'onglet messagerie avec ce fournisseur présélectionné
  - "Supprimer" (si pas répondu)

**3. Comparaison des prix**
GET /api/ao/{ao_id}/comparaison
Tableau :
  - Colonne 1 : Ref | Désignation | Qté
  - Colonnes suivantes : une par fournisseur (nom en en-tête + badge statut)
  - Cellule = prix_unitaire (formaté €) + délai en jours
  - Prix le plus bas de chaque ligne : fond --accent-bg + texte --accent
  - "—" si le fournisseur n'a pas répondu sur cette ligne
  - Ligne de résumé : prix min / max / moyen par article

**4. Messagerie**
Dropdown : sélectionner un fournisseur
Afficher historique messages en bulles :
  - Interne : bulle droite, fond --accent-bg
  - Fournisseur : bulle gauche, fond --card, border --border
  - Afficher auteur + date
Champ textarea + bouton "Envoyer"
Polling : toutes les 30s, GET messages si onglet actif

**5. Documents**
Liste PJ de l'AO (nom, taille, date, télécharger, supprimer)
Bouton "Ajouter un document" → input file, POST multipart
Taille max affichée : 10 Mo (validation côté client)

---

### JavaScript

État S :
```javascript
const S = {
  view: 'list',      // 'list' | 'detail'
  tab: 'lignes',     // onglet actif en vue détail
  aos: [],           // liste des AO
  filtre: 'tous',
  ao: null,          // AO en cours
  comparaison: null,
  messages_fourni: null,  // id fournisseur sélectionné pour messagerie
  polling: null      // setInterval handle
}
```

Fonctions : render(), renderList(), renderDetail(), renderLignes(), renderFournisseurs(),
renderComparaison(), renderMessagerie(), renderDocuments()

- api(path, options) : fetch avec credentials: 'include' et Content-Type JSON
- showToast(msg, type) : copier l'implémentation existante de html.py
- Préserver scroll position avant/après re-render

---

### Enregistrement dans main.py

Importer ao_page depuis app.web.ao_page.
Ajouter route GET /ao retournant la page HTML.
Ajouter le lien /ao dans la sidebar de html.py pour les rôles autorisés (icône SVG : document avec lignes, ex. clipboard-list).
```

---

## PROMPT 6 — Frontend : portail fournisseur public

```
Tu travailles sur MySifa (FastAPI + SQLite + HTML/CSS/JS vanilla).
Créer app/web/ao_portail_page.py.

Cette page est publique : pas de sidebar MySifa, pas de cookie d'auth.
Elle est servie sur /portail/ao/{token} (le token est injecté dans le HTML par Python).
Elle doit fonctionner pour des tiers sans compte MySifa.

---

### Design

Sobre, responsive, professionnel.
Même variables CSS que MySifa (--bg, --card, --border, --text, etc.).
Pas de sidebar. Pas d'emojis.
Structure centrée, max-width 860px.

Layout :
```
[En-tête : "MySifa — Portail fournisseur" | référence AO]
[Bandeau info : titre | date limite | statut]
[Onglets : Demande de prix | Messagerie | Documents]
[Contenu onglet]
[Pied : "Ce lien est personnel et confidentiel. Ne pas transmettre."]
```

---

### Onglet "Demande de prix"

Si AO non clôturé :
- Tableau : ref_produit | désignation | qté + unité | Prix unitaire (€) input | Délai (jours) input | Commentaire ligne input
- Champ textarea "Commentaire général sur votre offre"
- Bouton "Soumettre mon offre"
- Si déjà répondu : pré-remplir tous les champs avec les réponses existantes + message sobre
  "Vous avez déjà soumis une offre. Vous pouvez la modifier jusqu'à la date limite."
- Validation : au moins un prix_unitaire renseigné

Si AO clôturé :
- Message : "Cet appel d'offre est clôturé. Les réponses ne sont plus acceptées."
- Afficher les réponses soumises en lecture seule

---

### Onglet "Messagerie"

Historique des messages en bulles :
- "SIFA" (interne) : bulle gauche, fond --card avec bordure
- Nom du fournisseur : bulle droite, fond --accent-bg
- Afficher auteur + date formatée

Champ textarea + bouton "Envoyer"
Désactiver l'envoi si AO clôturé.
Polling : GET /api/portail/ao/{token}/messages toutes les 30 secondes.

---

### Onglet "Documents"

Section "Documents fournis par SIFA" :
- Liste des PJ de l'AO (nom, taille)
- Bouton télécharger → /api/portail/ao/{token}/pj-ao/{pj_id}/download

Section "Vos documents joints" (si AO non clôturé) :
- Liste de vos PJ déjà uploadées
- Input file + bouton "Joindre un document"
- Upload via FormData POST /api/portail/ao/{token}/pieces-jointes

---

### JavaScript

TOKEN = valeur injectée en Python dans le HTML sous forme de constante JS :
```javascript
const TOKEN = "{{ token }}";  // valeur échappée en Python
```

État S :
```javascript
const S = {
  tab: 'offre',
  data: null,   // données GET /api/portail/ao/{TOKEN}
  polling: null
}
```

Au chargement :
1. GET /api/portail/ao/{TOKEN} → stocker S.data, render()
2. Pré-remplir les champs avec les réponses existantes si disponibles
3. Démarrer polling messagerie

Fonctions : render(), renderOffre(), renderMessagerie(), renderDocuments()

- api(path, options) : fetch sans credentials (public)
- showToast(msg, type) : implémentation locale dans la page

---

### Templates email (dans app/services/email_service.py)

Créer deux fonctions :

**1. email_invitation_ao(ao, fournisseur, lien_portail) -> tuple[str, str]**
Retourne (sujet, corps_html).

Sujet : "[MySifa] Demande de prix — {reference} — {titre}"

Corps HTML :
```html
<div style="font-family:'Segoe UI',system-ui,sans-serif;max-width:600px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden">
  <div style="background:#0a0e17;padding:24px 32px">
    <div style="font-size:20px;font-weight:700;color:#22d3ee;letter-spacing:-0.5px">MySifa</div>
    <div style="font-size:13px;color:#94a3b8;margin-top:4px">Demande de prix</div>
  </div>
  <div style="padding:32px">
    <p style="margin:0 0 16px;font-size:14px;color:#0f172a">Bonjour {nom_fournisseur},</p>
    <p style="margin:0 0 24px;font-size:14px;color:#475569;line-height:1.6">
      Vous êtes invité à soumettre une offre pour la demande de prix <strong>{reference}</strong> — {titre}.
    </p>
    [Tableau des lignes : ref | désignation | quantité — style sobre]
    [Si date_limite : "Date limite de réponse : {date_limite formatée}"]
    <div style="margin:32px 0;text-align:center">
      <a href="{lien_portail}" style="background:#22d3ee;color:#0a0e17;font-weight:700;font-size:14px;padding:14px 28px;border-radius:10px;text-decoration:none;display:inline-block">
        Accéder à la demande de prix
      </a>
    </div>
    <p style="margin:0;font-size:12px;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:16px;line-height:1.6">
      Ce lien est personnel et sécurisé. Ne le partagez pas.<br>
      MySifa — {BASE_URL}
    </p>
  </div>
</div>
```

**2. email_accuse_reception(ao, fournisseur, lignes, reponses) -> tuple[str, str]**
Retourne (sujet, corps_html).

Sujet : "[MySifa] Réponse reçue — {reference} — {nom_fournisseur}"

Corps :
- "Le fournisseur {nom_fournisseur} a soumis une offre pour {reference}."
- Tableau : ref | désignation | qté | prix proposé | délai
- "Connectez-vous à MySifa pour consulter la comparaison des prix."

Utiliser ces deux fonctions dans ao.py (envoi) et ao_portail.py (accusé de réception).

---

### Enregistrement dans main.py

La route GET /portail/ao/{token} est déjà dans ao_portail.py (prompt 4).
Vérifier que ao_portail_page.py exporte bien la fonction get_portail_html(token, ao, fournisseur).
```

---

## Ordre d'exécution recommandé

| # | Prompt | Durée estimée |
|---|---|---|
| 1 | Infrastructure email | ~15 min |
| 2 | Tables DB | ~20 min |
| 3 | Backend interne | ~45 min |
| 4 | Backend portail | ~30 min |
| 5 | Frontend interne | ~60 min |
| 6 | Frontend portail + emails | ~45 min |

## Tests manuels à faire après chaque prompt

**Après prompt 1** : lancer `python -c "from app.services.email_service import send_email; print(send_email('test@test.com','test','<b>ok</b>'))"` — doit retourner False sans crasher si SMTP non configuré.

**Après prompt 2** : lancer l'app, vérifier que les tables existent dans production.db via `sqlite3 data/production.db ".tables"`.

**Après prompt 3** : tester via curl ou le navigateur les routes GET /api/ao (doit retourner []).

**Après prompt 4** : créer un AO + fournisseur en brouillon, récupérer le token, accéder à /api/portail/ao/{token}.

**Après prompts 5 et 6** : tester le flux complet : créer AO → ajouter lignes → ajouter fournisseur → envoyer → accéder au portail via le lien → soumettre une offre → vérifier l'email d'accusé de réception.

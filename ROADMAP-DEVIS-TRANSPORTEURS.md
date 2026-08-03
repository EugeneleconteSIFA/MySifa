# MyExpé — Devis transporteurs : ce que MyAO fait de mieux

Analyse comparative des deux modules de demande de prix. Ils font la même chose
— on sollicite N destinataires, ils répondent, on compare, on attribue — mais
MyAO a trois ans d'avance sur le cycle de vie et la communication.

Ce document liste les écarts, dans l'ordre où ils valent la peine d'être
comblés. Chaque proposition indique le fichier concerné et une estimation.

**Déjà livré dans ce lot** (ne figure plus dans les propositions) : le pixel de
suivi d'ouverture d'email, le journal d'événements, la timeline par
destinataire et la colonne « Engagement ».

---

## Ce que MyExpé fait déjà mieux — à ne pas casser

Avant d'aligner quoi que ce soit, quatre choses qui existent côté MyExpé et pas
côté MyAO. Toute refonte doit les préserver :

| Fonction | Où |
|---|---|
| Comparateur tarifaire automatique sur grilles importées | `expe_departs.py` — `_calculer_comparateur` |
| Création automatique du départ à la retenue d'une offre | `expe_departs.py` — `retenir_reponse_devis` |
| `reply-to` utilisateur + CC service sur tous les emails | `expe_departs.py` — `EXPE_DEVIS_CC` |
| Séparation des droits lecture / écriture | `_require_expe` vs `_require_expe_write` |

MyAO n'a aucun de ces quatre points. La convergence doit se faire dans les deux
sens.

---

## Priorité 1 — Les trous qui coûtent aujourd'hui

### 1.1 Aucune garde serveur sur une demande clôturée

**Le problème.** L'interface masque les boutons quand `statut !== 'ouverte'`
(`expe_assets.py`), mais le serveur, lui, accepte tout : `POST
/devis/demandes/{id}/envoyer` et `POST /devis/reponses/{id}/retenir`
fonctionnent sur une demande déjà clôturée. Un onglet resté ouvert, un
double-clic, un rappel de page en cache — et on renvoie une demande de tarif sur
une affaire déjà attribuée, ou on crée un second départ pour le même transport.

MyAO a un décorateur pour ça : `_require_brouillon` (`ao.py`), plus
`_require_not_cloture` côté portail qui renvoie un 403 propre au fournisseur.

**Ce qu'il faut faire.** Un helper `_require_demande_ouverte(conn, demande_id)`
appelé en tête de `envoyer_rfq`, `retenir_reponse_devis` et
`saisir_reponse_devis`. Même chose côté portail transporteur sur `repondre`.

**Coût** : une demi-journée. **Fichier** : `app/routers/expe_departs.py`,
`app/routers/expe_portail.py`.

> C'est le seul point de cette liste qui est un défaut, pas un manque. À traiter
> en premier même si le reste attend.

---

### 1.2 Personne n'est prévenu quand un transporteur répond

**Le problème.** Le portail transporteur envoie bien un accusé au créateur de la
demande (`expe_portail.py` — `email_expe_reponse_recue`), mais une réponse
saisie en interne ne notifie rien, et il n'existe aucune alerte « toutes les
réponses sont arrivées, tu peux trancher ». En pratique on retourne voir la page
à la main.

MyAO fait la même chose en mieux : accusé au responsable avec le récap chiffré
(`ao_portail.py`).

**Ce qu'il faut faire.** Deux ajouts :

- Une notification interne MySifa (pas seulement un email) à la réception d'une
  offre — le module notifications existe déjà.
- Un compteur « 3 / 5 réponses reçues » dans l'en-tête du détail, pas seulement
  dans la liste.

**Coût** : une journée. **Fichier** : `app/routers/expe_portail.py`,
`app/web/expe_assets.py`.

---

### 1.3 Pas de date limite de réponse

**Le problème.** `expe_demandes_devis` n'a aucune colonne de deadline. On
demande un prix « pour demain » dans le champ contraintes, en texte libre, et
rien ne le rappelle — ni au transporteur sur son portail, ni à nous.

MyAO a `date_limite`, affichée en liste, en détail, dans le portail fournisseur
et dans l'export PDF.

**Ce qu'il faut faire.** Colonne `date_limite TEXT`, affichée :
- en pastille sur la carte de la liste, rouge quand elle est dépassée ;
- en tête du portail transporteur (« Réponse attendue avant le … ») ;
- comme critère de tri par défaut des demandes ouvertes.

Ne pas bloquer la réponse après la date : MyAO ne le fait pas non plus, et un
prix en retard vaut mieux que pas de prix.

**Coût** : une demi-journée. **Fichiers** : migration + `expe_departs.py` +
`expe_assets.py` + `expe_portail_page.py`.

---

### 1.4 Aucune relance

**Le problème.** Le tracking livré dans ce lot rend le silence visible — chip
gris « Pas d'ouverture détectée », « il y a 4 j ». Mais il n'y a rien pour agir
dessus : pas de bouton relancer, pas de message au transporteur.

MyAO n'a pas de relance automatique non plus, mais il a la messagerie : un
message interne part par email avec son propre pixel de contexte `msg`, et la
fenêtre anti-préchargement se recale sur la date de la relance.

**Ce qu'il faut faire.** Un bouton « Relancer » par destinataire, sur les lignes
`envoyee` / `ouvert` sans prix. Il renvoie l'email avec le lien portail et un
message court optionnel. Le contexte pixel `rel` est **déjà prévu** dans
`expe_evenements.CONTEXTES` — il n'y a rien à changer au modèle.

**Coût** : une journée. **Fichier** : `app/routers/expe_departs.py`,
`app/services/email_service.py`, `app/web/expe_assets.py`.

---

## Priorité 2 — Ce qui fait gagner du temps tous les jours

### 2.1 Dupliquer une demande passée

MyAO copie lignes, séries, fournisseurs sélectionnés et pièces jointes
optionnelles vers un nouveau brouillon (`ao.py` — `dupliquer_ao`). MyExpé n'a
rien : `grep dupliquer` sur le module devis ne renvoie aucune occurrence.

Or les demandes de tarif se répètent : même client, même destination, même
gabarit, un mois plus tard. Aujourd'hui on ressaisit tout.

**Proposition.** Bouton « Dupliquer » sur la carte et dans le détail. Copie
l'entête et pré-coche les mêmes transporteurs, sans copier les réponses.

**Coût** : une demi-journée.

---

### 2.2 Le client est un champ texte libre

`expe_demandes_devis.client` est du texte, saisi à la main, sans lien avec la
table `clients` qui existe pourtant. Conséquence : « SATO », « Sato » et « SATO
SA » sont trois clients pour tout regroupement, et on ne peut pas répondre à
« combien de demandes de tarif pour ce client cette année ».

MyAO a un picker avec recherche dès 2 lettres et création à la volée
(`ao.py:414`, `ao_page.py:1118`).

**Proposition.** A minima un `<datalist>` alimenté par les clients existants —
une heure de travail, et 90 % du bénéfice. Le vrai rattachement par
`client_id` peut attendre.

**Coût** : une heure pour le datalist, deux jours pour la FK.

---

### 2.3 Statut brouillon et modification après création

Aujourd'hui une demande naît directement `ouverte` et devient immuable : il
n'existe aucune route `PUT /devis/demandes/{id}`. Une coquille dans le poids ou
le code postal oblige à supprimer et recréer — ce qui perd la référence
`2026-15` et les réponses déjà reçues.

**Proposition.** `PUT` sur les champs d'entête, autorisé tant qu'aucun envoi
n'est parti (`sent_at IS NULL` partout). Le statut brouillon complet de MyAO est
sans doute superflu ici : une demande de tarif transport se crée et part dans la
minute.

**Coût** : une demi-journée.

---

### 2.4 Une seule pièce jointe, écrasée sans prévenir

`piece_jointe_path` / `piece_jointe_filename` sont deux colonnes : le second
upload écrase le premier, silencieusement. MyAO a une table dédiée avec liste,
téléchargement et suppression.

**Proposition.** Table `expe_devis_pieces_jointes` sur le modèle
`ao_pieces_jointes`. Rendre les pièces jointes accessibles depuis le **portail
transporteur** — aujourd'hui le téléchargement est protégé par
`get_current_user`, donc réservé à l'interne : un transporteur ne peut pas
consulter le plan de chargement qu'on lui a préparé.

**Coût** : une journée.

---

### 2.5 Le transporteur ne peut rien joindre à sa réponse

`expe_devis_reponses` n'a aucune colonne de pièce jointe côté transporteur. Un
transporteur qui veut envoyer sa cotation en PDF, ou une photo de contrainte
d'accès, doit répondre par mail à côté du portail — et cette réponse-là n'entre
jamais dans le comparatif.

MyAO gère l'upload depuis le portail (`ao_portail.py` — `upload_portail_pj`).

**Coût** : une journée.

---

## Priorité 3 — Confort et exploitation

### 3.1 L'i18n existe mais n'est jamais activé

`app/services/expe_email_i18n.py` contient des packs FR et EN complets. Mais
`expe_transporteurs` n'a pas de colonne `langue`, et
`email_expe_rfq_transport` n'en reçoit jamais : le mail part systématiquement
bilingue, les deux versions empilées. Pour un transporteur belge ou néerlandais
c'est du bruit, et pour un français aussi.

MyAO stocke la langue par destinataire (`ao_fournisseurs.langue`) et n'envoie
que celle-là.

**Proposition.** Colonne `langue` sur `expe_transporteurs` (défaut `fr`),
sélecteur dans la fiche transporteur, passage au générateur d'email. Le travail
de traduction est déjà fait — il ne manque que le câblage.

**Coût** : une demi-journée. Rapport bénéfice / effort excellent.

---

### 3.2 Aucun export

Ni PDF, ni Excel, ni impression. MyAO exporte un PDF complet de l'AO
(`ao.py` — `export_ao_pdf`, reportlab) : infos, lignes, invités, réponses par
destinataire.

Pour MyExpé le besoin est plus simple : un tableau comparatif imprimable des
offres reçues, à joindre au dossier ou à faire viser.

**Coût** : une journée.

---

### 3.3 Audit quasi inexistant

Sur tout le cycle devis, il n'y a qu'un seul `log_action` : à la retenue. Ni la
création, ni l'envoi, ni la saisie d'une réponse, ni la clôture, ni la
suppression ne laissent de trace. MyAO journalise create, delete, restore,
duplicate et export.

C'est peu coûteux et ça se voit le jour où on cherche qui a envoyé quoi.

**Coût** : deux heures.

---

### 3.4 Suppression physique irréversible

`DELETE /devis/demandes/{id}` efface la demande et ses réponses en cascade, sans
confirmation serveur et sans nettoyer les pièces jointes sur disque. MyAO a une
corbeille : `deleted_at`, restauration, purge définitive avec nettoyage disque.

**Proposition.** A minima : colonne `deleted_at` et filtre par défaut. La purge
peut rester manuelle.

**Coût** : une demi-journée.

---

### 3.5 Détails du comparatif

Trois emprunts directs à `comparaison_ao` :

- **Écart % vs meilleure offre** — aujourd'hui le meilleur prix est en gras,
  mais on ne voit pas si le deuxième est à 3 % ou à 40 %.
- **Min / max / moyenne** sur la ligne — MyAO les calcule serveur
  (`prix_min`, `prix_max`, `prix_moyen`).
- **Dates envoi / ouverture / réponse par destinataire** — elles sont en base
  (`sent_at`, `opened_at`, `recu_at`) mais aucune n'est affichée dans le
  tableau. Le suivi livré dans ce lot en montre une partie ; les dates brutes
  restent utiles.

**Coût** : une demi-journée l'ensemble.

---

### 3.6 Détails de sélection des destinataires

- **Retirer un destinataire d'une demande** — aucune route ne le permet. Un
  email saisi de travers reste sur la demande jusqu'à sa suppression.
- **Copier le lien portail** en un clic, par destinataire — MyAO l'a
  (`btn-copy`), utile quand un transporteur dit ne pas avoir reçu le mail.
- **`transporteur_extras`** est accepté par l'API `envoyer_rfq` mais **aucune
  interface ne l'alimente** : le champ est mort. Soit on ajoute le champ
  « destinataire ponctuel » dans le modal d'envoi, soit on retire le code.

**Coût** : une demi-journée l'ensemble.

---

## Deux angles morts repérés au passage, hors périmètre

1. **Fuite de `token_pixel` côté MyAO.** `PUT
   /api/ao/{ao_id}/fournisseurs/{fourni_id}` (`ao.py:3105`) fait `SELECT *` puis
   renvoie la ligne telle quelle, sans le `d.pop("token_pixel", None)` présent
   aux deux autres endroits. Le token de suivi sort dans cette réponse. Un
   `pop` à ajouter.

2. **`.tl-main` sans règle CSS** dans `ao_page.py` : la classe est posée sur la
   colonne texte de la timeline mais n'a pas de `flex:1`. Côté MyExpé la règle
   est présente (`.expe-tl-main`).

---

## Ordre de bataille proposé

| Lot | Contenu | Charge |
|---|---|---|
| **A** | 1.1 gardes serveur + 3.3 audit | 1 jour |
| **B** | 1.3 date limite + 1.4 relance + 3.1 langue par transporteur | 2 jours |
| **C** | 1.2 notifications + 2.1 duplication + 2.3 édition | 2 jours |
| **D** | 2.4 + 2.5 pièces jointes des deux côtés | 2 jours |
| **E** | 3.2 export + 3.5 comparatif + 3.6 destinataires | 2 jours |

Le lot A est le seul à traiter en priorité absolue : il corrige un défaut, le
reste comble des manques.

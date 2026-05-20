# Cursor Prompts — Enrichissement Agent IA

Enrichissement du data fetcher `app/services/ai_data.py` pour couvrir production,
logistique, traçabilité, expéditions, planning et planning RH en profondeur.

4 prompts à exécuter dans l'ordre.

---

## Bloc contexte commun (coller avant chaque prompt)

```
Projet MySifa — FastAPI + SQLite. Point d'entrée : main.py.
DB via `from database import get_db`. Migrations dans app/core/database.py.

Tables clés et colonnes utiles :

production_data :
  id, operateur, date_operation ("%Y-%m-%dT%H:%M:%S" heure Paris),
  operation_code, machine, no_dossier, client, designation,
  metrage_prevu (REAL), metrage_reel (REAL), duree_heures (REAL),
  commentaire, est_manuel, modifie_le

planning_entries :
  id, machine_id, position, reference, client, description,
  format_l, format_h, duree_heures (REAL), statut (attente|en_cours|termine),
  statut_reel, notes, planned_start, planned_end, date_livraison,
  commentaire, exigences_production, numero_of, ref_produit, laize,
  fsc_requis, fsc_type_requis, created_at, updated_at

machines :
  id, nom, code, actif

produits :
  id, reference, designation, unite

stock_emplacements :
  id, produit_id, emplacement, quantite, updated_at, updated_by, commentaire

mouvements_stock :
  id, produit_id, emplacement, type_mouvement (entree|sortie|transfert|ajustement),
  quantite, quantite_avant, quantite_apres, note, created_at, created_by_name

expe_departs :
  id, date_enlevement, transporteur, client, ref_sifa, no_bl,
  nb_palette (REAL), poids_total_kg (REAL), statut (en_attente|valide|annule),
  created_at, validated_at, validated_by_email

rh_conges :
  id, user_id, date_debut, date_fin, nb_jours (REAL),
  type_conge (CP|RTT|maladie|…), statut (pose|valide|refuse), note

rh_planning_postes :
  id, user_id, semaine (ex: "2026-W21"), machine_id, poste, creneau, jours (bitmask)

users :
  id, nom, email, role, operateur_lie, actif

Design system CSS : --bg, --card, --border, --text, --text2, --muted,
  --accent (#22d3ee), --accent-bg, --ok (#34d399), --warn (#fbbf24), --danger (#f87171)
```

---

## Prompt 1 — Production enrichie

```
Fichier à modifier : app/services/ai_data.py

Ajouter 3 nouveaux outils en lecture seule dans la liste TOOLS et leurs handlers
dans _handle_tool_call(). Chaque outil suit le même pattern que les outils existants.

─── OUTIL 1 : production_operators ───
Nom         : production_operators
Description : Synthèse de production par opérateur sur une période donnée.
              Retourne les métrages réels, durées et nombre de saisies par opérateur.
Paramètres  :
  - jours (integer, défaut 7) : période en jours glissants
  - machine_nom (string, optionnel) : filtrer sur une machine (LIKE)

Requête SQL à utiliser :
```sql
SELECT
    p.operateur,
    COUNT(*) AS nb_saisies,
    ROUND(SUM(COALESCE(p.metrage_reel, 0)), 1) AS metrage_total,
    ROUND(SUM(COALESCE(p.duree_heures, 0)), 2) AS heures_total,
    p.machine
FROM production_data p
WHERE date(p.date_operation) >= date('now', '-' || ? || ' days')
  AND p.operateur IS NOT NULL AND p.operateur != ''
  AND (? = '' OR LOWER(p.machine) LIKE LOWER('%' || ? || '%'))
GROUP BY p.operateur, p.machine
ORDER BY metrage_total DESC
```

Retour formaté (texte) :
"Production par opérateur — {jours} derniers jours{filtre machine} :
• {operateur} ({machine}) : {nb_saisies} saisies, {metrage_total} m, {heures_total} h"

─── OUTIL 2 : dossier_detail ───
Nom         : dossier_detail
Description : Fiche complète d'un dossier/OF : données planning + toutes les saisies
              de production associées. Outil central pour répondre à "où en est le dossier X".
Paramètres  :
  - query (string, requis) : numéro OF, référence dossier ou nom client (LIKE)

Requêtes SQL à utiliser (2 requêtes séparées) :

Requête planning :
```sql
SELECT pe.*, m.nom AS machine_nom
FROM planning_entries pe
LEFT JOIN machines m ON pe.machine_id = m.id
WHERE pe.reference LIKE '%' || ? || '%'
   OR pe.numero_of LIKE '%' || ? || '%'
   OR pe.client LIKE '%' || ? || '%'
ORDER BY pe.updated_at DESC
LIMIT 5
```

Requête production (pour chaque dossier trouvé, utiliser pe.reference) :
```sql
SELECT
    p.date_operation, p.operateur, p.operation_code, p.machine,
    p.metrage_prevu, p.metrage_reel, p.duree_heures, p.commentaire
FROM production_data p
WHERE p.no_dossier = ?
ORDER BY p.date_operation ASC
```

Retour formaté (texte) :
"Dossier {reference} — {client}
  Machine : {machine_nom} | Statut : {statut} | Statut réel : {statut_reel}
  Format : {format_l}×{format_h} mm | Durée planifiée : {duree_heures} h
  Date livraison : {date_livraison} | Début planifié : {planned_start}
  Fin planifiée : {planned_end}
  Notes : {notes}

  Saisies de production ({n} enregistrements) :
  - {date_operation} — {operateur} — op.{operation_code} — {metrage_reel}/{metrage_prevu} m — {duree_heures} h
  [...]
  Métrage total réel : {sum metrage_reel} m / {sum metrage_prevu} m prévu"

Si aucun dossier trouvé : "Aucun dossier trouvé pour « {query} »."

─── OUTIL 3 : production_late_dossiers ───
Nom         : production_late_dossiers
Description : Liste les dossiers en retard — planned_end dépassé, statut non terminé.
              Aussi les dossiers en cours sans saisie récente (>24h).
Paramètres  : aucun

Requête dossiers en retard :
```sql
SELECT pe.reference, pe.client, pe.statut, pe.statut_reel,
       pe.planned_end, pe.date_livraison, pe.duree_heures, m.nom AS machine_nom
FROM planning_entries pe
LEFT JOIN machines m ON pe.machine_id = m.id
WHERE pe.statut != 'termine'
  AND pe.planned_end IS NOT NULL AND pe.planned_end != ''
  AND pe.planned_end < datetime('now', 'localtime')
ORDER BY pe.planned_end ASC
LIMIT 15
```

Requête dossiers en cours sans saisie récente :
```sql
SELECT pe.reference, pe.client, m.nom AS machine_nom,
       MAX(p.date_operation) AS derniere_saisie
FROM planning_entries pe
LEFT JOIN machines m ON pe.machine_id = m.id
LEFT JOIN production_data p ON p.no_dossier = pe.reference
WHERE pe.statut = 'en_cours'
GROUP BY pe.id
HAVING derniere_saisie IS NULL OR derniere_saisie < datetime('now', 'localtime', '-24 hours')
ORDER BY derniere_saisie ASC NULLS FIRST
LIMIT 10
```

Retour formaté :
"Dossiers en retard ({n}) :
• {reference} — {client} — {machine_nom} — fin prévue {planned_end} — statut : {statut_reel}

Dossiers en cours sans saisie depuis >24h ({n}) :
• {reference} — {client} — {machine_nom} — dernière saisie : {derniere_saisie}"
```

---

## Prompt 2 — Stock & logistique enrichis

```
Fichier à modifier : app/services/ai_data.py

Ajouter 3 nouveaux outils en lecture seule.

─── OUTIL 1 : stock_movements ───
Nom         : stock_movements
Description : Historique des mouvements de stock pour un produit ou un emplacement.
Paramètres  :
  - query (string, requis) : référence produit, désignation ou emplacement (LIKE)
  - jours (integer, défaut 30) : période en jours glissants

Requête SQL :
```sql
SELECT
    p.reference, p.designation,
    ms.type_mouvement, ms.quantite, ms.quantite_avant, ms.quantite_apres,
    ms.emplacement, ms.note, ms.created_at, ms.created_by_name
FROM mouvements_stock ms
JOIN produits p ON ms.produit_id = p.id
WHERE date(ms.created_at) >= date('now', '-' || ? || ' days')
  AND (
    LOWER(p.reference)   LIKE LOWER('%' || ? || '%') OR
    LOWER(p.designation) LIKE LOWER('%' || ? || '%') OR
    LOWER(ms.emplacement) LIKE LOWER('%' || ? || '%')
  )
ORDER BY ms.created_at DESC
LIMIT 30
```

Retour formaté :
"Mouvements stock — {query} — {jours} derniers jours ({n} résultats) :
• {created_at} — {type_mouvement} — {reference} ({designation}) — {emplacement}
  Qté : {quantite} ({quantite_avant} → {quantite_apres}) — par {created_by_name}
  Note : {note}"

─── OUTIL 2 : stock_inventory_by_aisle ───
Nom         : stock_inventory_by_aisle
Description : Inventaire du stock organisé par allée (A, B, C, D).
              Utile pour la logistique — "qu'est-ce qu'on a en allée B ?".
Paramètres  :
  - aisle (string, optionnel) : lettre d'allée (A, B, C ou D)

Requête SQL :
```sql
SELECT
    p.reference, p.designation, p.unite,
    se.emplacement, se.quantite, se.updated_at, se.updated_by, se.commentaire
FROM stock_emplacements se
JOIN produits p ON se.produit_id = p.id
WHERE se.quantite > 0
  AND (? = '' OR UPPER(SUBSTR(se.emplacement, 1, 1)) = UPPER(?))
ORDER BY se.emplacement ASC
```

Retour formaté :
"Inventaire{filtre allée} ({n} articles) :

Allée A :
  {emplacement} — {reference} — {designation} — {quantite} {unite}
  [...]
Allée B :
  [...]"

Grouper les résultats par première lettre de l'emplacement dans le texte de retour.

─── OUTIL 3 : expe_history ───
Nom         : expe_history
Description : Historique des expéditions passées (validées) avec stats.
              Complément à expe_detail qui ne couvre que le futur.
Paramètres  :
  - jours (integer, défaut 30) : période en jours glissants
  - client (string, optionnel) : filtrer par client (LIKE)

Requête SQL :
```sql
SELECT
    ed.date_enlevement, ed.client, ed.transporteur,
    ed.nb_palette, ed.poids_total_kg, ed.ref_sifa, ed.no_bl,
    ed.statut, ed.validated_by_email, ed.validated_at
FROM expe_departs ed
WHERE date(ed.date_enlevement) >= date('now', '-' || ? || ' days')
  AND date(ed.date_enlevement) < date('now')
  AND (? = '' OR LOWER(ed.client) LIKE LOWER('%' || ? || '%'))
ORDER BY ed.date_enlevement DESC
LIMIT 30
```

Ajouter aussi une requête de stats sur la même période :
```sql
SELECT
    COUNT(*) AS nb_departs,
    SUM(COALESCE(nb_palette, 0)) AS total_palettes,
    ROUND(SUM(COALESCE(poids_total_kg, 0)), 0) AS total_poids_kg,
    COUNT(DISTINCT client) AS nb_clients
FROM expe_departs
WHERE date(date_enlevement) >= date('now', '-' || ? || ' days')
  AND date(date_enlevement) < date('now')
  AND statut = 'valide'
  AND (? = '' OR LOWER(client) LIKE LOWER('%' || ? || '%'))
```

Retour formaté :
"Expéditions passées — {jours} derniers jours{filtre client} :
Synthèse : {nb_departs} départs, {total_palettes} palettes, {total_poids_kg} kg, {nb_clients} clients

Détail :
• {date_enlevement} — {client} — {transporteur}
  {nb_palette} pal. / {poids_total_kg} kg — Réf : {ref_sifa} — BL : {no_bl}
  Statut : {statut} — Validé par : {validated_by_email}"
```

---

## Prompt 3 — Planning RH enrichi

```
Fichier à modifier : app/services/ai_data.py

Ajouter 2 nouveaux outils en lecture seule.

─── OUTIL 1 : rh_presence_today ───
Nom         : rh_presence_today
Description : Qui est présent aujourd'hui et cette semaine. Croise les postes planifiés
              et les absences pour donner une vue claire de l'effectif disponible.
Paramètres  : aucun

Calcul du numéro de semaine ISO courant en Python :
```python
from datetime import date
today = date.today()
iso_year, iso_week, iso_weekday = today.isocalendar()
semaine_courante = f"{iso_year}-W{iso_week:02d}"
```

Requête postes semaine courante :
```sql
SELECT
    u.nom, u.operateur_lie, rpp.poste, rpp.creneau, rpp.jours,
    m.nom AS machine_nom
FROM rh_planning_postes rpp
JOIN users u ON rpp.user_id = u.id
LEFT JOIN machines m ON rpp.machine_id = m.id
WHERE rpp.semaine = ?
  AND u.actif = 1
ORDER BY u.nom ASC
```

Requête absences aujourd'hui :
```sql
SELECT u.nom, rc.type_conge, rc.date_debut, rc.date_fin, rc.nb_jours, rc.statut
FROM rh_conges rc
JOIN users u ON rc.user_id = u.id
WHERE rc.statut IN ('pose', 'valide')
  AND date(rc.date_debut) <= date('now', 'localtime')
  AND date(rc.date_fin)   >= date('now', 'localtime')
ORDER BY u.nom
```

Pour le bitmask `jours` : bit 0 = lundi, bit 1 = mardi, … bit 4 = vendredi.
Calculer si le jour courant (iso_weekday - 1) est dans le bitmask.

Retour formaté :
"Effectif — {date du jour} (semaine {semaine_courante}) :

Absents aujourd'hui ({n}) :
• {nom} — {type_conge} ({date_debut} → {date_fin})

Postes planifiés cette semaine ({n}) :
• {nom} ({operateur_lie}) — {poste} — {machine_nom} — {creneau}"

─── OUTIL 2 : rh_absences_period ───
Nom         : rh_absences_period
Description : Absences et congés sur une période donnée, avec comptage par type.
              Utile pour anticiper les sous-effectifs et planifier.
Paramètres  :
  - jours (integer, défaut 14) : période en jours à venir

Requête absences à venir :
```sql
SELECT
    u.nom, u.role, rc.type_conge,
    rc.date_debut, rc.date_fin, rc.nb_jours, rc.statut, rc.note
FROM rh_conges rc
JOIN users u ON rc.user_id = u.id
WHERE rc.statut IN ('pose', 'valide')
  AND date(rc.date_fin)   >= date('now', 'localtime')
  AND date(rc.date_debut) <= date('now', 'localtime', '+' || ? || ' days')
ORDER BY rc.date_debut ASC
```

Requête stats par type sur la même période :
```sql
SELECT type_conge, COUNT(*) AS nb, SUM(nb_jours) AS total_jours
FROM rh_conges
WHERE statut IN ('pose', 'valide')
  AND date(date_fin)   >= date('now', 'localtime')
  AND date(date_debut) <= date('now', 'localtime', '+' || ? || ' days')
GROUP BY type_conge
```

Retour formaté :
"Absences — {jours} prochains jours ({n} personnes concernées) :

Par type : CP : {n} salariés ({j} j) | RTT : … | Maladie : …

Détail :
• {nom} ({role}) — {type_conge} — du {date_debut} au {date_fin} ({nb_jours} j) — {statut}"
```

---

## Prompt 4 — Contexte auto enrichi (snapshot de démarrage)

```
Fichier à modifier : app/services/ai_context.py

Améliorer la fonction fetch_context_for_role() pour enrichir le contexte
injecté automatiquement dans le system prompt. Modifier ou compléter les blocs
existants selon les rôles.

─── BLOC 1 : _production_today — enrichir ───
Requête actuelle : comptage par machine.
Nouvelle requête (remplacer) :
```sql
SELECT
    p.machine,
    COUNT(*) AS nb_saisies,
    COUNT(DISTINCT p.operateur) AS nb_operateurs,
    ROUND(SUM(COALESCE(p.metrage_reel, 0)), 1) AS metrage_total,
    ROUND(SUM(COALESCE(p.duree_heures, 0)), 2) AS heures_total
FROM production_data p
WHERE date(p.date_operation) = date('now', 'localtime')
GROUP BY p.machine
ORDER BY metrage_total DESC
```

Nouveau format retourné :
"Production aujourd'hui :
• {machine} — {nb_saisies} saisies, {nb_operateurs} opérateur(s), {metrage_total} m, {heures_total} h"

─── BLOC 2 : _planning_status — enrichir ───
Requête actuelle : comptage statuts par machine.
Ajouter à la fin du texte retourné le nombre de dossiers avec planned_end dépassé :
```sql
SELECT COUNT(*) FROM planning_entries
WHERE statut != 'termine'
  AND planned_end IS NOT NULL AND planned_end != ''
  AND planned_end < datetime('now', 'localtime')
```
Ajouter ligne : "Dossiers en retard : {n}" dans le texte _planning_status.

─── BLOC 3 : Ajouter _rh_today pour les rôles direction et superadmin ───
Ce bloc n'existe pas encore. L'ajouter dans fetch_context_for_role() pour
les rôles "superadmin" et "direction".

Requête :
```sql
SELECT u.nom, rc.type_conge, rc.date_debut, rc.date_fin
FROM rh_conges rc
JOIN users u ON rc.user_id = u.id
WHERE rc.statut IN ('pose', 'valide')
  AND date(rc.date_debut) <= date('now', 'localtime')
  AND date(rc.date_fin)   >= date('now', 'localtime')
ORDER BY u.nom
```

Texte retourné :
"Absents aujourd'hui : {n}
• {nom} — {type_conge} ({date_debut} → {date_fin})"
Si 0 absent : "Absents aujourd'hui : aucun"

─── BLOC 4 : Ajouter _stock_movements_today pour superadmin et direction ───
Ce bloc n'existe pas encore. L'ajouter dans fetch_context_for_role().

Requête :
```sql
SELECT COUNT(*) AS nb_mouvements,
       SUM(CASE WHEN type_mouvement='entree' THEN 1 ELSE 0 END) AS nb_entrees,
       SUM(CASE WHEN type_mouvement='sortie' THEN 1 ELSE 0 END) AS nb_sorties
FROM mouvements_stock
WHERE date(created_at) = date('now', 'localtime')
```

Texte retourné :
"Mouvements stock aujourd'hui : {nb_mouvements} ({nb_entrees} entrées, {nb_sorties} sorties)"
Si 0 : ne pas inclure ce bloc.

─── AMÉLIORATION : system prompt — reformuler la liste des outils ───
Dans ai_context.py, dans la section qui liste les outils disponibles dans le
system prompt, ajouter les 5 nouveaux outils avec leur description courte :
- production_operators : "synthèse de production par opérateur"
- dossier_detail : "fiche complète d'un dossier (planning + saisies)"
- production_late_dossiers : "dossiers en retard ou sans saisie récente"
- stock_movements : "historique des mouvements de stock"
- stock_inventory_by_aisle : "inventaire par allée d'entrepôt"
- expe_history : "historique des expéditions passées"
- rh_presence_today : "présence et postes planifiés aujourd'hui"
- rh_absences_period : "absences à venir sur une période"
```

---

## Ce que ces prompts génèrent — résumé

**Prompt 1 — Production enrichie :**
- L'agent peut répondre à "qui a le plus produit cette semaine", "montre-moi toutes les saisies du dossier REF-4521", "quels dossiers sont en retard sur Cohésio 1"

**Prompt 2 — Stock & logistique :**
- L'agent peut répondre à "quels sont les mouvements sur la référence X ce mois", "qu'est-ce qu'on a en allée B", "combien de palettes on a expédiées ce mois chez client Y"

**Prompt 3 — Planning RH :**
- L'agent peut répondre à "qui est absent aujourd'hui", "qui est planifié sur DSI cette semaine", "combien de CP posés dans les 2 prochaines semaines"

**Prompt 4 — Contexte auto :**
- Dès l'ouverture du chat, la direction et le superadmin voient les absences du jour, les mouvements de stock, le nombre de dossiers en retard — sans avoir à poser la question.

---

## Ordre d'exécution

1. **Prompt 1** — production_operators, dossier_detail, production_late_dossiers
2. **Prompt 2** — stock_movements, stock_inventory_by_aisle, expe_history
3. **Prompt 3** — rh_presence_today, rh_absences_period
4. **Prompt 4** — enrichissement du contexte auto (snapshot de démarrage)

Chaque prompt est indépendant — ils peuvent être envoyés à Cursor séparément
sans redémarrage intermédiaire. Un seul redémarrage suffit à la fin.

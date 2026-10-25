"""
Questions d'alerte identifiées, et photo du questionnaire sur chaque validation.

Les réponses d'une validation sont rangées sous le numéro de leur question.
Depuis que des questionnaires ont changé (« Inspection des produits finis » :
7 questions jusqu'au 09/10/2026, 4 ensuite), les anciennes réponses
s'affichaient sous les nouvelles questions, décalées.

1. Chaque question des alertes existantes reçoit un identifiant stable.
2. `maintenance_alert_acks.questionnaire` garde la photo des questions qu'a
   vues l'opérateur. Pour les validations passées : le questionnaire actuel
   quand leurs réponses s'y lisent sans contradiction, sinon un questionnaire
   reconstitué sans libellés (« Question 1 »…), que l'historique range à part
   comme « ancien formulaire ».

Rejouable : une question qui a déjà son identifiant le garde, une validation
qui a déjà sa photo n'est pas retouchée. Sur v1, la copie nocturne de la base
de prod rejoue la reprise tant que prod n'a pas reçu cette version.
"""

import json

from app.services.alertes_questionnaire import (
    attribuer_ids, compatible, items_de_params, photo, photo_deduite,
)

NOM = "alertes_questionnaire_photo"


def appliquer(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if not {"maintenance_alerts", "maintenance_alert_acks"} <= tables:
        print(f"[MySifa] migration {NOM} : tables absentes, rien à faire.")
        return

    cols = {r[1] for r in conn.execute("PRAGMA table_info(maintenance_alert_acks)").fetchall()}
    if "questionnaire" not in cols:
        conn.execute("ALTER TABLE maintenance_alert_acks ADD COLUMN questionnaire TEXT")

    questions = {}
    alertes_maj = 0
    for r in conn.execute("SELECT id, params FROM maintenance_alerts").fetchall():
        try:
            params = json.loads(r[1] or "{}")
        except (TypeError, ValueError):
            continue
        if not isinstance(params, dict):
            continue
        items = items_de_params(params)
        if items and any(not it.get("id") for it in items):
            attribuer_ids(items, [])
            params.setdefault("checklist", {})["items"] = items
            conn.execute("UPDATE maintenance_alerts SET params = ? WHERE id = ?",
                         (json.dumps(params, ensure_ascii=False), r[0]))
            alertes_maj += 1
        questions[r[0]] = items

    lisibles = anciennes = 0
    for r in conn.execute(
        "SELECT id, alert_id, responses FROM maintenance_alert_acks WHERE questionnaire IS NULL"
    ).fetchall():
        try:
            responses = json.loads(r[2] or "{}")
        except (TypeError, ValueError):
            responses = {}
        if not isinstance(responses, dict):
            responses = {}
        items = questions.get(r[1]) or []
        if compatible(items, responses):
            figee = photo(items)
            lisibles += 1
        else:
            figee = json.dumps(photo_deduite(responses), ensure_ascii=False)
            anciennes += 1
        conn.execute("UPDATE maintenance_alert_acks SET questionnaire = ? WHERE id = ?", (figee, r[0]))

    conn.commit()
    print(f"[MySifa] migration {NOM} : {alertes_maj} alerte(s) identifiée(s), "
          f"{lisibles} validation(s) rattachée(s) au questionnaire actuel, "
          f"{anciennes} rangée(s) en ancien formulaire.")

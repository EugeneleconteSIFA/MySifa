"""
Purge des créneaux « constat » laissés par un enregistrement d'opération échoué.

Le problème
-----------
« Enregistrer une opération » procède en deux requêtes : `POST /events` crée un
créneau `non_planifie` à la date de l'intervention, puis
`PATCH /events/{id}/ops/{op_id}` solde l'opération en `termine`.

Depuis v2.7.0, un garde-fou refusait de solder une opération jamais saisie sur
un créneau passé — sans distinguer le planning du constat. Sur une date passée,
le POST réussissait donc et le PATCH échouait. Résultat : un créneau vide restait
en base, visible dans le planning sous « NON PLANIFIÉ », absent de l'historique,
et chaque nouvelle tentative en ajoutait un. `delete_event` refusant par ailleurs
toute suppression d'un créneau passé, ces lignes n'étaient effaçables par
personne depuis l'interface.

v2.7.2 corrige les deux causes (garde-fou aligné sur la règle de create_event,
et création rendue atomique côté client). Cette migration solde le passif.

Ce qui est supprimé — et ce qui ne l'est pas
--------------------------------------------
Uniquement les créneaux réunissant TOUTES ces conditions :
  - source `non_planifie` (un constat, jamais du planning) ;
  - date passée ;
  - aucune opération soldée (ni `termine`, ni `invalidee`) ;
  - aucune observation, durée ni pièce changée saisie sur ses opérations.

Autrement dit : des coquilles vides. Dès qu'une saisie existe, le créneau est
conservé, y compris partiellement rempli. Le détail est journalisé avant
suppression.
"""

NOM = "creneaux_constats_orphelins"


def appliquer(conn):
    cols = {r["name"] for r in conn.execute(
        "PRAGMA table_info(maintenance_events)").fetchall()}
    if not cols:
        return  # table absente (harnais de test)

    # Le jour même n'est jamais concerné : une saisie peut encore arriver.
    aujourdhui = conn.execute("SELECT date('now', 'localtime') AS d").fetchone()["d"]

    candidats = conn.execute(
        """SELECT e.id, e.machine, e.date_prevue, e.created_at,
                  COUNT(o.id) AS n_ops
           FROM maintenance_events e
           LEFT JOIN maintenance_event_ops o ON o.event_id = e.id
           WHERE e.source = 'non_planifie'
             AND e.date_prevue < ?
             AND NOT EXISTS (
                   SELECT 1 FROM maintenance_event_ops x
                   WHERE x.event_id = e.id
                     AND (x.statut IN ('termine', 'invalidee')
                          OR COALESCE(x.observations, '')     <> ''
                          OR COALESCE(x.pieces_changees, '')  <> ''
                          OR x.duree_reelle_min IS NOT NULL
                          OR x.done_at IS NOT NULL)
                 )
           GROUP BY e.id
           ORDER BY e.date_prevue, e.id""",
        (aujourdhui,),
    ).fetchall()

    if not candidats:
        print(f"[MySifa] migration {NOM} : aucun créneau orphelin.")
        return

    ids = [r["id"] for r in candidats]
    print(f"[MySifa] migration {NOM} : {len(ids)} créneau(x) constat vide(s) à purger.")
    for r in candidats:
        codes = [x["code"] for x in conn.execute(
            "SELECT code FROM maintenance_event_ops WHERE event_id=? ORDER BY id",
            (r["id"],)).fetchall()]
        print(f"[MySifa]   PURGE event_id={r['id']} date={r['date_prevue']} "
              f"machine={r['machine']} ops={codes} cree_le={r['created_at']}")

    marques = ",".join("?" * len(ids))
    # Suppressions explicites : PRAGMA foreign_keys n'est pas actif sur
    # get_db(), les ON DELETE CASCADE déclarés ne s'exécuteraient pas.
    conn.execute(f"DELETE FROM maintenance_event_ops WHERE event_id IN ({marques})", ids)
    try:
        conn.execute(f"DELETE FROM maintenance_event_operators WHERE event_id IN ({marques})", ids)
    except Exception:
        pass
    conn.execute(f"DELETE FROM maintenance_events WHERE id IN ({marques})", ids)
    conn.commit()
    print(f"[MySifa] migration {NOM} : {len(ids)} créneau(x) supprimé(s).")

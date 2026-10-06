"""
Sous-tâches sans assigné : reprise des assignés de leur tâche mère.

L'ajout rapide de sous-tâche (détail d'une tâche) n'envoyait aucun assigné :
toutes les sous-tâches créées ainsi comptaient dans « Non assignées » alors
que la mère était bien attribuée. Depuis le 06/10/2026, `create_tache` fait
hériter une sous-tâche des assignés de sa mère quand aucun choix n'est fourni ;
cette migration applique la même règle aux sous-tâches déjà en base.

Seules les sous-tâches qui n'ont AUCUN assigné sont touchées : une sous-tâche
attribuée à la main garde son attribution. `INSERT OR IGNORE` sur la clé
(tache_id, user_id) rend la reprise rejouable.
"""

NOM = "taches_sous_taches_assignes_herites"


def appliquer(conn):
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
            " AND name IN ('taches','taches_assignes')"
        ).fetchall()
    }
    if tables != {"taches", "taches_assignes"}:
        return
    cibles = conn.execute(
        """SELECT COUNT(*) FROM taches s
            WHERE s.parent_id IS NOT NULL AND s.deleted_at IS NULL
              AND NOT EXISTS (SELECT 1 FROM taches_assignes a WHERE a.tache_id=s.id)
              AND EXISTS (SELECT 1 FROM taches_assignes p WHERE p.tache_id=s.parent_id)"""
    ).fetchone()[0]
    if cibles:
        conn.execute(
            """INSERT OR IGNORE INTO taches_assignes (tache_id,user_id,assigne_at,assigne_par)
               SELECT s.id, p.user_id, p.assigne_at, p.assigne_par
                 FROM taches s
                 JOIN taches_assignes p ON p.tache_id = s.parent_id
                WHERE s.parent_id IS NOT NULL AND s.deleted_at IS NULL
                  AND NOT EXISTS (SELECT 1 FROM taches_assignes a WHERE a.tache_id=s.id)"""
        )
    conn.commit()
    print(f"[MySifa] migration taches_sous_taches_assignes_herites : "
          f"{cibles} sous-tâche(s) reprise(s).")

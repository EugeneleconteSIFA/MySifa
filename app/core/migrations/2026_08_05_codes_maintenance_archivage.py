"""
Archivage des codes de maintenance, au lieu d'une suppression qui laissait
l'historique orphelin.

Le problème
-----------
`DELETE /api/maintenance/codes/{code}` ne supprimait que la ligne du catalogue.
Les saisies de `maintenance_event_ops` survivaient, parce que la clé étrangère
qui les rattache au code est inerte : `get_db()` n'active jamais
`PRAGMA foreign_keys=ON` (c'est écrit dans database.py, et la migration 188 a
déjà nettoyé le même passif sur `event_id`).

L'historique, lui, résout le libellé à la volée :
`LEFT JOIN maintenance_codes c ON c.code = o.code`, puis `type = c.label`.
Une saisie orpheline s'affichait donc avec son code brut (« MEC-04 »), et le
jour où le même identifiant était recréé pour une autre opération, toutes les
vieilles saisies ressortaient sous le nouveau nom. L'historique racontait une
intervention qui n'avait jamais eu lieu.

Ce que fait cette migration
---------------------------
1. Ajoute `maintenance_codes.archived_at`. Un code encore utilisé n'est plus
   supprimé mais archivé : il sort du catalogue, son libellé continue de
   résoudre dans l'historique, et l'identifiant reste pris — donc plus personne
   ne peut le recycler pour une opération différente.
2. Purge les saisies déjà orphelines. Choix explicite d'Eugène : ces lignes
   pointent vers des codes supprimés avant le correctif, plus personne ne sait
   ce qu'elles désignent. Le détail est journalisé AVANT suppression, pour
   qu'un `grep` dans les logs de déploiement permette de les reconstituer si
   besoin.

La purge ne touche que les lignes dont le code est absent du catalogue. Les
codes libres (LIB-*) présents dans `maintenance_codes` ne sont pas concernés.
"""

NOM = "codes_maintenance_archivage"


def appliquer(conn):
    cols = {r["name"] for r in conn.execute(
        "PRAGMA table_info(maintenance_codes)").fetchall()}
    if not cols:
        return  # table absente (harnais de test) : rien à faire

    # ── 1. Colonne d'archivage ────────────────────────────────────────────
    if "archived_at" not in cols:
        conn.execute("ALTER TABLE maintenance_codes ADD COLUMN archived_at TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_maint_codes_archived "
        "ON maintenance_codes(archived_at)"
    )

    # ── 2. Purge du passif orphelin ───────────────────────────────────────
    ops_cols = {r["name"] for r in conn.execute(
        "PRAGMA table_info(maintenance_event_ops)").fetchall()}
    if not ops_cols:
        conn.commit()
        return

    orphelines = conn.execute(
        """SELECT o.id, o.event_id, o.code, o.statut, o.done_at,
                  COALESCE(o.observations, '') AS observations,
                  COALESCE(e.machine, '')      AS machine,
                  COALESCE(e.date_prevue, '')  AS date_prevue
           FROM maintenance_event_ops o
           LEFT JOIN maintenance_events e ON e.id = o.event_id
           WHERE o.code NOT IN (SELECT code FROM maintenance_codes)
           ORDER BY o.code, o.id"""
    ).fetchall()

    if orphelines:
        # Journalisation avant destruction : c'est la seule trace qui restera.
        print(f"[MySifa] migration {NOM} : {len(orphelines)} saisie(s) "
              f"orpheline(s) à purger.")
        for r in orphelines:
            print(f"[MySifa]   PURGE op_id={r['id']} event_id={r['event_id']} "
                  f"code={r['code']} statut={r['statut']} "
                  f"machine={r['machine']} date={r['done_at'] or r['date_prevue']} "
                  f"obs={r['observations'][:120]!r}")
        conn.execute(
            "DELETE FROM maintenance_event_ops "
            "WHERE code NOT IN (SELECT code FROM maintenance_codes)"
        )

    # Mêmes orphelins possibles côté modèles de créneau : eux ne portent
    # aucune donnée saisie, on les retire sans journaliser le détail.
    tpl_cols = {r["name"] for r in conn.execute(
        "PRAGMA table_info(maintenance_template_ops)").fetchall()}
    n_tpl = 0
    if tpl_cols:
        cur = conn.execute(
            "DELETE FROM maintenance_template_ops "
            "WHERE code NOT IN (SELECT code FROM maintenance_codes)"
        )
        n_tpl = cur.rowcount or 0

    # Et côté documents attachés, dont le ON DELETE CASCADE est tout aussi
    # inerte que la clé étrangère des saisies.
    doc_cols = {r["name"] for r in conn.execute(
        "PRAGMA table_info(maintenance_docs)").fetchall()}
    n_docs = 0
    if doc_cols:
        cur = conn.execute(
            "DELETE FROM maintenance_docs "
            "WHERE code NOT IN (SELECT code FROM maintenance_codes)"
        )
        n_docs = cur.rowcount or 0

    conn.commit()
    print(f"[MySifa] migration {NOM} : colonne archived_at prête, "
          f"{len(orphelines)} saisie(s), {n_tpl} ligne(s) de modèle et "
          f"{n_docs} document(s) orphelins purgés.")

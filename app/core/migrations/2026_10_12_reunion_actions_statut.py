"""
Points de production : une action a un statut, plus seulement une case.

Une case cochee dit « fait » ou « pas fait ». Le suivi des actions a besoin de
plus : ce qui n'est pas encore entame, ce qui avance, ce qui bloque sur
quelqu'un d'autre, ce qui est fini. Quatre statuts : a_faire, en_cours,
en_attente, termine.

`fait` reste en place et suit le statut (fait = 1 si et seulement si termine) :
la liste des reunions, l'impression et les comptes « restantes » le lisent
encore, et un onglet ouvert avant la mise a jour continue de fonctionner.

Reprise : une action deja cochee passe en `termine`, les autres en `a_faire`.
"""

NOM = "reunion_actions_statut"
DEPEND = ["reunions_prod"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(reunion_actions)").fetchall()}
    if not cols:
        return  # table absente sur cette base : rien a faire
    if "statut" not in cols:
        conn.execute(
            "ALTER TABLE reunion_actions ADD COLUMN statut TEXT NOT NULL DEFAULT 'a_faire'"
        )
    cur = conn.execute(
        "UPDATE reunion_actions SET statut = 'termine' "
        "WHERE COALESCE(fait, 0) = 1 AND statut <> 'termine'"
    )
    conn.commit()
    print(f"[MySifa] migration reunion_actions_statut : "
          f"{cur.rowcount} action(s) reprise(s) en termine.")

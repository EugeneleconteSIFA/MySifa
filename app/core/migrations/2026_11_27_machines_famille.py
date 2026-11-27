"""
Famille de machines : des machines que les mêmes conducteurs conduisent.

« Passer la main » propose, après les conducteurs planifiés sur la machine,
les autres conducteurs de la même famille (poste `conducteur` au Planning RH).
Le type de poste ne suffit pas : la DSI est une machine d'impression comme les
Cohésio, mais ses conducteurs ne reprennent pas une Cohésio (décision
d'Eugène du 27/11/2026).

Seed SIFA : Cohésio 1 et Cohésio 2 (codes C1, C2) forment la famille
« Cohésio ». Modifiable ensuite dans Paramètres › Machines. Une machine sans
famille n'a pour conducteurs que les siens.
"""

NOM = "machines_famille"

FAMILLES_SIFA = (("C1", "Cohésio"), ("C2", "Cohésio"))


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(machines)").fetchall()}
    if "famille" not in cols:
        conn.execute("ALTER TABLE machines ADD COLUMN famille TEXT")
    n = 0
    for code, famille in FAMILLES_SIFA:
        cur = conn.execute(
            "UPDATE machines SET famille=? WHERE code=? AND (famille IS NULL OR trim(famille)='')",
            (famille, code),
        )
        n += cur.rowcount or 0
    conn.commit()
    print(f"[MySifa] migration machines_famille : {n} machine(s) rangée(s) dans une famille.")

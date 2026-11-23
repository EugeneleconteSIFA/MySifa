"""
Machines : un TYPE de poste, au lieu de reconnaître le repiquage à son nom.

Le code reconnaissait la machine de repiquage à son nom (« Repiquage »,
« rep », « rep … ») à une trentaine d'endroits. La règle du projet est que la
logique métier dépend d'un attribut en base, jamais d'un identifiant de
machine : `machines.type` vaut `impression` (défaut) ou `repiquage`, se règle
dans Paramètres › Machines, et le serveur le lit par
`app/services/machines_type.py`.

Reprise : les machines que l'ancienne règle de nom reconnaissait passent en
`repiquage` — même périmètre qu'avant, rien ne change à l'écran.
"""

NOM = "machines_type"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(machines)").fetchall()}
    if not cols:
        return
    if "type" not in cols:
        conn.execute("ALTER TABLE machines ADD COLUMN type TEXT NOT NULL DEFAULT 'impression'")
    code = "lower(trim(COALESCE(code,'')))" if "code" in cols else "''"
    n = conn.execute(
        "UPDATE machines SET type='repiquage' "
        "WHERE COALESCE(type,'impression')='impression' AND ("
        " lower(trim(COALESCE(nom,''))) LIKE 'repiquage%' "
        " OR lower(trim(COALESCE(nom,''))) = 'rep' "
        " OR lower(trim(COALESCE(nom,''))) LIKE 'rep %' "
        " OR " + code + " = 'rep')"
    ).rowcount
    conn.commit()
    print(f"[MySifa] migration machines_type : {n} machine(s) de repiquage typée(s).")

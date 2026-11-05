"""
Réunions : un espace commun, des types de réunion, une visibilité.

Les réunions n'étaient que des points de production. La direction, le
commercial, la qualité ou les RH tiennent aussi des réunions, avec leurs
notes, leurs décisions et leurs actions : elles vivent désormais au même
endroit, rangées par type.

`reunion_types` est un référentiel édité dans Paramètres. La logique lit ses
ATTRIBUTS, jamais son libellé :

  - `visibilite_defaut` : qui voit une réunion de ce type — `participants`
    (créateur et participants), `roles` (les rôles de `roles_defaut`) ou
    `tous` ;
  - `chiffres_prod` : la réunion regarde une plage de dates et des machines
    (comportement historique des points de production) ;
  - `structuration_ia` : le brief d'une écoute est proposé par Claude. À 0,
    seule la transcription brute est produite, rien ne quitte le serveur.

Chaque réunion reprend la visibilité de son type à la création ; elle se règle
ensuite réunion par réunion (`visibilite`, `roles_visibles`). `decisions` est
séparé des notes pour qu'une décision se retrouve.

Reprise : les réunions déjà tenues passent sur le type Production, visibles
des rôles qui y avaient accès (ceux de ROLES_PROD le 2026-11-05).
"""

NOM = "reunions_types_visibilite"
DEPEND = ["reunions_prod"]

# Valeurs SIFA de départ, éditables ensuite. (libellé, ordre, chiffres_prod,
# visibilité, rôles, structuration IA)
_ROLES_PROD = ("direction,fabrication,expedition,commercial,administration,"
               "administration_ventes,administration_technique")
_SEED = (
    ("Production", 1, 1, "roles", _ROLES_PROD, 1),
    ("Direction", 2, 0, "participants", "", 1),
    ("Commercial", 3, 0, "tous", "", 1),
    ("Qualité", 4, 0, "tous", "", 1),
    ("RH", 5, 0, "participants", "", 1),
)


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS reunion_types (
               id                INTEGER PRIMARY KEY AUTOINCREMENT,
               libelle           TEXT NOT NULL UNIQUE,
               ordre             INTEGER NOT NULL DEFAULT 0,
               actif             INTEGER NOT NULL DEFAULT 1,
               chiffres_prod     INTEGER NOT NULL DEFAULT 0,
               visibilite_defaut TEXT NOT NULL DEFAULT 'participants',
               roles_defaut      TEXT NOT NULL DEFAULT '',
               structuration_ia  INTEGER NOT NULL DEFAULT 1,
               created_at        TEXT,
               updated_at        TEXT
           )"""
    )
    for lib, ordre, prod, vis, roles, ia in _SEED:
        conn.execute(
            """INSERT OR IGNORE INTO reunion_types
                   (libelle, ordre, chiffres_prod, visibilite_defaut, roles_defaut,
                    structuration_ia, created_at)
               VALUES (?,?,?,?,?,?,datetime('now'))""",
            (lib, ordre, prod, vis, roles, ia),
        )

    cols = {r[1] for r in conn.execute("PRAGMA table_info(reunions)").fetchall()}
    if not cols:
        conn.commit()
        return  # table absente sur cette base : le référentiel suffit
    if "type_id" not in cols:
        conn.execute("ALTER TABLE reunions ADD COLUMN type_id INTEGER")
    if "visibilite" not in cols:
        conn.execute("ALTER TABLE reunions ADD COLUMN visibilite TEXT NOT NULL DEFAULT 'participants'")
    if "roles_visibles" not in cols:
        conn.execute("ALTER TABLE reunions ADD COLUMN roles_visibles TEXT NOT NULL DEFAULT ''")
    if "decisions" not in cols:
        conn.execute("ALTER TABLE reunions ADD COLUMN decisions TEXT NOT NULL DEFAULT ''")
    if "ouverte_par_id" not in cols:
        conn.execute("ALTER TABLE reunions ADD COLUMN ouverte_par_id INTEGER")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_reunions_type ON reunions(type_id, date_debut DESC)")

    prod = conn.execute("SELECT id FROM reunion_types WHERE libelle='Production'").fetchone()
    n = 0
    if prod:
        cur = conn.execute(
            "UPDATE reunions SET type_id=?, visibilite='roles', roles_visibles=? WHERE type_id IS NULL",
            (prod[0], _ROLES_PROD),
        )
        n = cur.rowcount
    conn.commit()
    print(f"[MySifa] migration reunions_types_visibilite : référentiel en place, "
          f"{n} réunion(s) reprise(s) sur le type Production.")

"""
Donne une provenance et un état de validation aux liaisons devis ↔ planning.

`rent_links` ne portait que le couple (entrée de planning, devis). Suffisant
tant que toutes les liaisons étaient faites à la main : une liaison existait
ou non, et si elle existait c'est qu'un humain l'avait posée.

Le rapprochement automatique casse cette équivalence. Une liaison proposée par
le moteur n'a pas la même valeur qu'une liaison décidée par quelqu'un, et une
comparaison devis/réel bâtie sur une proposition non relue vaut ce que vaut la
proposition. Il faut donc pouvoir distinguer les deux — c'est ce que la vue
Pilotage affiche en vert et en orange.

- `origine`   : 'manuel' (quelqu'un l'a posée) ou 'auto' (le moteur l'a proposée)
- `valide_at` : posé dès qu'un humain a confirmé. Une liaison manuelle naît
                validée ; une proposition attend.
- `score` / `motif` : ce que le moteur a trouvé, pour qu'on puisse juger la
                proposition sans rouvrir le devis. Une proposition sans motif
                lisible serait un ordre, pas une aide.

Reprise de l'existant : tout ce qui est déjà en base a été posé à la main, donc
`origine='manuel'` et `valide_at = updated_at`. Les marquer « à confirmer »
ferait passer en orange des liaisons que personne n'a besoin de revoir.
"""

NOM = "rent_liens_origine_validation"


def _colonnes(conn, table: str) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def appliquer(conn):
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "rent_links" not in tables:
        print("[MySifa] migration rent_liens_origine : table rent_links absente.")
        return

    existantes = _colonnes(conn, "rent_links")
    ajouts = [
        ("origine", "TEXT"),
        ("score", "REAL"),
        ("motif", "TEXT"),
        ("valide_par", "TEXT"),
        ("valide_at", "TEXT"),
    ]
    ajoutees = []
    for nom, typ in ajouts:
        if nom not in existantes:
            conn.execute(f"ALTER TABLE rent_links ADD COLUMN {nom} {typ}")
            ajoutees.append(nom)

    # Reprise : idempotente, elle ne touche que les lignes encore sans origine.
    repris = conn.execute(
        """UPDATE rent_links
              SET origine   = 'manuel',
                  valide_at = COALESCE(valide_at, updated_at)
            WHERE origine IS NULL OR origine = ''"""
    ).rowcount

    conn.commit()
    print(
        f"[MySifa] migration rent_liens_origine : {len(ajoutees)} colonne(s) ajoutée(s) "
        f"({', '.join(ajoutees) or 'aucune'}), {repris} liaison(s) reprise(s) en manuel."
    )

"""
Postes clotures a leur fin prevue.

Le dessiccateur (DSI) n'a pas de saisie de production : aucun code 89 ne
vient clore ses dossiers, et le dechargement de stock qui suit la cloture ne
part donc jamais. Inventaire du 13/10/2026 : complexes en 333 consommes sur ce
poste et toujours en stock dans MySifa (+83 000 m sur le seul Thermique Pro
adhesif permanent).

Une machine cochee ici voit ses dossiers clos automatiquement des que leur fin
prevue au planning est passee, puis destockes depuis le theorique de l'OF. Le
balayage du destockage s'en charge (`cloturer_fins_prevues`), a partir de la
date de mise en service du destockage automatique : rien n'est rattrape.

Propriete du poste, cochee dans Parametres -> Machines comme
`sans_matiere_premiere` et `hors_production`. Le DSI est coche d'office : c'est
le cas connu au moment de la migration.
"""

NOM = "postes_cloture_fin_prevue"


def appliquer(conn):
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(machines)").fetchall()}
    if not cols:
        return  # table absente sur cette base (harnais de test) : rien a faire
    if "cloture_fin_prevue" not in cols:
        conn.execute(
            "ALTER TABLE machines ADD COLUMN cloture_fin_prevue INTEGER NOT NULL DEFAULT 0"
        )
    cur = conn.execute(
        "UPDATE machines SET cloture_fin_prevue = 1 "
        "WHERE UPPER(TRIM(COALESCE(code, ''))) = 'DSI' "
        "  AND COALESCE(cloture_fin_prevue, 0) = 0"
    )
    conn.commit()
    print(f"[MySifa] migration postes_cloture_fin_prevue : "
          f"{cur.rowcount} poste(s) clos a la fin prevue.")

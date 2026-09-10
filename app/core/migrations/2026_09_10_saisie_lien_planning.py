"""
Rattache chaque saisie de production à son créneau du planning.

Ajoute `production_data.planning_entry_id` (index) et le renseigne pour
l'existant, dans l'ordre chronologique : la règle « même créneau que la saisie
précédente du dossier, tant que rien ne l'a clos » s'appuie sur les
rattachements déjà faits. Détail des règles : app/services/lien_saisie_planning.

Pourquoi : voir la docstring du service. En bref, la référence texte ne suffit
plus à dire à quel passage appartient une saisie dès qu'un dossier a plusieurs
créneaux (reliquat, duplication, second créneau après annulation).

Rejouable : seules les saisies encore non rattachées sont traitées.
"""

NOM = "saisie_lien_planning"
DEPEND = ["saisie_fin_dossier"]


def appliquer(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "production_data" not in tables or "planning_entries" not in tables or "machines" not in tables:
        print("[MySifa] migration saisie_lien_planning : tables absentes, rien à faire.")
        return
    cols = {r[1] for r in conn.execute("PRAGMA table_info(production_data)").fetchall()}
    if "planning_entry_id" not in cols:
        conn.execute("ALTER TABLE production_data ADD COLUMN planning_entry_id INTEGER")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_production_data_planning_entry "
        "ON production_data(planning_entry_id)"
    )
    conn.commit()

    from app.services.lien_saisie_planning import resoudre

    rows = conn.execute(
        """SELECT * FROM production_data
            WHERE planning_entry_id IS NULL
              AND TRIM(COALESCE(no_dossier,'')) <> ''
              AND TRIM(COALESCE(machine,'')) <> ''
            ORDER BY date_operation, id"""
    ).fetchall()
    lies = 0
    for r in rows:
        pe_id = resoudre(conn, dict(r))
        if pe_id:
            conn.execute("UPDATE production_data SET planning_entry_id = ? WHERE id = ?", (pe_id, r["id"]))
            lies += 1
    conn.commit()
    print(f"[MySifa] migration saisie_lien_planning : {lies} saisie(s) rattachée(s) "
          f"sur {len(rows)} à traiter.")

"""
Dossier remis au planning après une annulation : même couleur, signal « à revoir ».

Deux colonnes sur `planning_entries` :

- `annulation_source_id` : le créneau du passage annulé dont celui-ci est la
  relance. Le planning colore un créneau d'après son id ; la relance prend
  celle de sa source, pour qu'on reconnaisse le même dossier d'un coup d'œil.
- `annulation_a_revoir` : 1 tant que la relance n'a pas été replacée. Le
  planning l'encadre en rouge, la fait clignoter et affiche « Ajout auto suite
  à annulation dossier ».

Le signal tombe dès que « À placer au planning » est décoché, par quelque
chemin que ce soit (fenêtre du dossier, glisser-déposer, changement de
machine) : c'est le déclencheur qui l'éteint, pas chaque route.

Reprise : un dossier annulé encore en attente et encore « à placer » reçoit
le signal, pour ne pas perdre le cadre rouge qu'il avait jusqu'ici.
"""

NOM = "planning_relance_apres_annulation"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(planning_entries)").fetchall()}
    if "annulation_source_id" not in cols:
        conn.execute("ALTER TABLE planning_entries ADD COLUMN annulation_source_id INTEGER")
    if "annulation_a_revoir" not in cols:
        conn.execute("ALTER TABLE planning_entries ADD COLUMN annulation_a_revoir INTEGER DEFAULT 0")

    conn.executescript("""
DROP TRIGGER IF EXISTS trg_pe_annulation_revue;
CREATE TRIGGER trg_pe_annulation_revue
AFTER UPDATE OF a_placer ON planning_entries
WHEN COALESCE(NEW.a_placer, 0) = 0 AND COALESCE(NEW.annulation_a_revoir, 0) = 1
BEGIN
    UPDATE planning_entries SET annulation_a_revoir = 0 WHERE id = NEW.id;
END;
""")

    n = 0
    if "annule_le" in cols and "a_placer" in cols:
        n = conn.execute(
            """UPDATE planning_entries SET annulation_a_revoir = 1
                WHERE trim(COALESCE(annule_le, '')) <> ''
                  AND statut = 'attente'
                  AND COALESCE(statut_reel, 'reellement_en_attente') = 'reellement_en_attente'
                  AND COALESCE(a_placer, 0) = 1
                  AND COALESCE(annulation_a_revoir, 0) = 0"""
        ).rowcount
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} dossier(s) annulé(s) signalé(s) à revoir.")

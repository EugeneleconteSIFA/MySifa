"""
Réaligner `planning_of_links` sur `planning_entries.of_import_id`.

Le constat (17/09/2026)
-----------------------
Le pont Access reliait un OF neuf à son dossier par un UPDATE direct de
`planning_entries.of_import_id`, sans toucher `planning_of_links`. Or le slot
du planning lit la colonne, et le panneau OF du dossier (l'œil « Voir l'OF
relié ») lit la table de liens. 102 dossiers divergeaient : 9931675+996
chiffrait sur l'OF « 9931675+996 » et ouvrait l'OF « 9931675 », sans
référence produit ni machine.

Le pont passe désormais par `_promote_of_link`. Cette migration répare
l'existant, dossier par dossier :

- aucun lien : on crée celui de la colonne, en position 0 ;
- des liens existent, dont un OF avec PDF, et la colonne pointe un OF SANS
  PDF : la colonne a tort — c'est exactement le cas que le garde-fou du pont
  devait empêcher (un aperçu réel remplacé par un rendu sur modèle). On
  réaligne la colonne sur le premier lien ;
- sinon : la colonne a raison (c'est le dernier OF rattaché par numéro
  exact), on la promeut en tête des liens, les autres restent accessibles.
"""

NOM = "realigner_liens_of_planning"


def _a_un_pdf(conn, of_id):
    r = conn.execute(
        "SELECT TRIM(COALESCE(pdf_filename,'')) != '' FROM of_imports WHERE id=?",
        (of_id,),
    ).fetchone()
    return bool(r and r[0])


def appliquer(conn):
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"planning_entries", "planning_of_links", "of_imports"} <= tables:
        return
    now = conn.execute("SELECT strftime('%Y-%m-%dT%H:%M:%S','now','localtime')").fetchone()[0]
    rows = conn.execute(
        """SELECT pe.id, pe.of_import_id FROM planning_entries pe
           JOIN of_imports o ON o.id = pe.of_import_id
           WHERE NOT EXISTS (SELECT 1 FROM planning_of_links pl
                              WHERE pl.planning_entry_id = pe.id
                                AND pl.of_import_id = pe.of_import_id)"""
    ).fetchall()
    crees = promus = realignes = 0
    for entry_id, of_id in rows:
        liens = [r[0] for r in conn.execute(
            "SELECT of_import_id FROM planning_of_links WHERE planning_entry_id=? "
            "ORDER BY position ASC, id ASC", (entry_id,)).fetchall()]
        if not liens:
            conn.execute(
                "INSERT INTO planning_of_links "
                "(planning_entry_id, of_import_id, position, created_by, created_at) "
                "VALUES (?, ?, 0, 'migration_realigner_liens', ?)",
                (entry_id, of_id, now))
            crees += 1
        elif not _a_un_pdf(conn, of_id) and any(_a_un_pdf(conn, l) for l in liens):
            conn.execute("UPDATE planning_entries SET of_import_id=? WHERE id=?",
                         (liens[0], entry_id))
            realignes += 1
        else:
            conn.execute(
                "UPDATE planning_of_links SET position = position + 1 "
                "WHERE planning_entry_id = ?", (entry_id,))
            conn.execute(
                "INSERT INTO planning_of_links "
                "(planning_entry_id, of_import_id, position, created_by, created_at) "
                "VALUES (?, ?, 0, 'migration_realigner_liens', ?)",
                (entry_id, of_id, now))
            promus += 1
    conn.commit()
    print(f"[MySifa] migration {NOM} : {crees} lien(s) créé(s), "
          f"{promus} OF promu(s) en tête, {realignes} dossier(s) réaligné(s) "
          f"sur leur OF avec PDF.")

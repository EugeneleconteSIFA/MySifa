"""
Rattacher un OF a son dossier dans les deux sens, et tenir la colonne
`planning_entries.of_import_id` et la table `planning_of_links` d'accord quel
que soit l'ecrivain.

Le constat (22/09/2026)
-----------------------
Le rattachement ne se faisait qu'a l'import de l'OF
(`_autolink_of_to_planning`, of_import.py) : l'OF cherche ses dossiers, jamais
l'inverse. Un dossier cree APRES son OF ne recupere donc rien — et cinq
endroits creent des dossiers (ajout au planning, split, second creneau
d'annulation de fin de production, import de planning, pont Access).

Cas d'origine : dossier 9932467-68-69-70-71. L'OF 1438 est importe le 02/09 et
rattache a l'entree 516 ; cette entree est supprimee, l'entree 535 la remplace
le 03/09 et n'est jamais reliee. Resultat en base : 92 dossiers portent un
`numero_of` dont l'OF existe, sans lien.

Ce que ca casse. Sans OF, `_metrage_dossier` (besoins_matieres.py) n'a ni
metrage ni quantite d'etiquettes : la Tracabilite et Besoins matieres affichent
« non chiffre » sur les six postes d'un dossier dont la fiche technique est
pourtant complete. Devant un auditeur, un besoin non chiffre ne se distingue
pas d'un poste qui ne consomme pas.

Deux fuites de plus, meme cause — le rattachement vit dans un seul chemin de
code :

- `_creer_second_creneau` (annulation de fin de production) recopie
  `of_import_id` sans creer la ligne de liens : le slot du planning voit l'OF,
  le panneau OF du dossier ne le voit pas ;
- la suppression d'un dossier laissait ses liens derriere elle — 27 lignes
  orphelines en base, qui ressortiraient sur un id reattribue.

Le rattachement descend donc dans des triggers. C'est le seul niveau que tous
les ecrivains traversent, pont Access et scripts de reprise compris : un
sixieme point de creation n'aura pas a y penser. Les triggers ne font que le
cas sans ambiguite — numero d'OF identique, un seul candidat retenu. Les
numeros approchants (« 9932163 Reliquat 2 ») restent l'affaire de
`_autolink_of_to_planning` et de la fenetre « Rattacher les documents » de
Besoins matieres, qui elle arbitre.
"""

NOM = "autolink_of_dossier"
DEPEND = ["realigner_liens_of_planning"]


# Le candidat retenu pour un `numero_of` : l'OF avec un PDF d'abord (c'est un
# apercu reel, pas un rendu sur modele — meme arbitrage que la migration
# `realigner_liens_of_planning`), le plus recent ensuite.
_CANDIDAT = """
    SELECT NEW.id, o.id, 0, 'autolink_dossier',
           strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')
      FROM of_imports o
     WHERE LOWER(TRIM(o.of_numero)) = LOWER(TRIM(NEW.numero_of))
     ORDER BY (TRIM(COALESCE(o.pdf_filename, '')) != '') DESC, o.id DESC
     LIMIT 1
"""

_INSERT = ("INSERT INTO planning_of_links "
           "(planning_entry_id, of_import_id, position, created_by, created_at)")

# `of_link_user_managed = 1` signe un arbitrage humain (detachement depuis
# Besoins matieres) : un trigger ne le defait pas.
_GARDE = ("NEW.of_import_id IS NULL\n"
          "     AND TRIM(COALESCE(NEW.numero_of, '')) != ''\n"
          "     AND COALESCE(NEW.of_link_user_managed, 0) = 0")

_TRIGGERS = f"""
DROP TRIGGER IF EXISTS trg_pe_of_lien_depuis_colonne;
CREATE TRIGGER trg_pe_of_lien_depuis_colonne
AFTER INSERT ON planning_entries
WHEN NEW.of_import_id IS NOT NULL
BEGIN
    {_INSERT}
    SELECT NEW.id, NEW.of_import_id, 0, 'copie_dossier',
           strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')
     WHERE EXISTS (SELECT 1 FROM of_imports WHERE id = NEW.of_import_id)
       AND NOT EXISTS (SELECT 1 FROM planning_of_links
                        WHERE planning_entry_id = NEW.id
                          AND of_import_id = NEW.of_import_id);
END;

DROP TRIGGER IF EXISTS trg_pe_autolink_of_ins;
CREATE TRIGGER trg_pe_autolink_of_ins
AFTER INSERT ON planning_entries
WHEN {_GARDE}
BEGIN
    {_INSERT}
    {_CANDIDAT};
END;

DROP TRIGGER IF EXISTS trg_pe_autolink_of_upd;
CREATE TRIGGER trg_pe_autolink_of_upd
AFTER UPDATE OF numero_of ON planning_entries
WHEN {_GARDE}
BEGIN
    {_INSERT}
    {_CANDIDAT};
END;

DROP TRIGGER IF EXISTS trg_pe_purge_of_links_del;
CREATE TRIGGER trg_pe_purge_of_links_del
AFTER DELETE ON planning_entries
BEGIN
    DELETE FROM planning_of_links WHERE planning_entry_id = OLD.id;
END;
"""


def _colonnes(conn, table):
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def appliquer(conn):
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"planning_entries", "planning_of_links", "of_imports"} <= tables:
        return
    cols = _colonnes(conn, "planning_entries")
    if not {"numero_of", "of_import_id", "of_link_user_managed"} <= cols:
        return

    now = conn.execute(
        "SELECT strftime('%Y-%m-%dT%H:%M:%S','now','localtime')").fetchone()[0]

    # 1. Menage. Un lien vers un dossier ou un OF disparu n'est pas une
    #    donnee, c'est un piege : il ressort au premier id reattribue.
    orphelins = conn.execute(
        "DELETE FROM planning_of_links "
        "WHERE planning_entry_id NOT IN (SELECT id FROM planning_entries)"
    ).rowcount
    of_morts = conn.execute(
        "DELETE FROM planning_of_links "
        "WHERE of_import_id NOT IN (SELECT id FROM of_imports)"
    ).rowcount
    # Meme raison cote colonne : elle pointe parfois un OF supprime depuis.
    # On la vide pour que le rattachement ci-dessous puisse en retrouver un bon.
    colonnes_mortes = conn.execute(
        "UPDATE planning_entries SET of_import_id = NULL "
        "WHERE of_import_id IS NOT NULL "
        "  AND of_import_id NOT IN (SELECT id FROM of_imports)"
    ).rowcount

    # 2. Colonne renseignee mais aucun lien : la copie de dossier
    #    (`_creer_second_creneau`) ecrit la premiere sans la seconde.
    #    `realigner_liens_of_planning` avait repris l'existant ; on reprend ce
    #    qui est apparu depuis, le trigger s'occupe de la suite.
    liens_crees = 0
    for entry_id, of_id in conn.execute(
        """SELECT pe.id, pe.of_import_id FROM planning_entries pe
           JOIN of_imports o ON o.id = pe.of_import_id
           WHERE NOT EXISTS (SELECT 1 FROM planning_of_links pl
                              WHERE pl.planning_entry_id = pe.id
                                AND pl.of_import_id = pe.of_import_id)"""
    ).fetchall():
        conn.execute(
            "UPDATE planning_of_links SET position = position + 1 "
            "WHERE planning_entry_id = ?", (entry_id,))
        conn.execute(
            _INSERT + " VALUES (?, ?, 0, 'migration_autolink_of', ?)",
            (entry_id, of_id, now))
        liens_crees += 1

    # 3. Le rattrapage : dossiers sans OF dont le numero designe un OF existant.
    rattaches = ambigus = 0
    for entry_id, numero in conn.execute(
        """SELECT id, numero_of FROM planning_entries
           WHERE of_import_id IS NULL
             AND TRIM(COALESCE(numero_of, '')) != ''
             AND COALESCE(of_link_user_managed, 0) = 0"""
    ).fetchall():
        candidats = conn.execute(
            """SELECT id FROM of_imports
               WHERE LOWER(TRIM(of_numero)) = LOWER(TRIM(?))
               ORDER BY (TRIM(COALESCE(pdf_filename, '')) != '') DESC, id DESC""",
            (numero,),
        ).fetchall()
        if not candidats:
            continue
        if len(candidats) > 1:
            # Deux OF sous le meme numero : c'est un arbitrage, pas un
            # rattachement. On laisse la fenetre « Rattacher les documents »
            # trancher plutot que de choisir a la place de l'atelier.
            ambigus += 1
            continue
        conn.execute(
            _INSERT + " VALUES (?, ?, 0, 'migration_autolink_of', ?)",
            (entry_id, candidats[0][0], now))
        rattaches += 1

    # 4. Les triggers, pour que rien de tout cela ne se reproduise.
    conn.executescript(_TRIGGERS)
    conn.commit()

    print(f"[MySifa] migration {NOM} : {rattaches} dossier(s) rattache(s) a leur OF, "
          f"{liens_crees} lien(s) recree(s) depuis la colonne, "
          f"{ambigus} dossier(s) laisse(s) a arbitrer, "
          f"{orphelins} lien(s) orphelin(s) et {of_morts} lien(s) vers un OF "
          f"supprime purges, {colonnes_mortes} colonne(s) remise(s) a NULL.")

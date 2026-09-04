"""
Créer un OF ou une fiche technique DANS MySifa, et non plus seulement les
importer d'Access ou d'un PDF.

Trois manques bloquaient cette création.

1. `of_imports` ne portait que ce que le parseur de PDF savait lire. Le papier
   de l'atelier contient davantage — particularités, cales et sachets, palettes,
   réglages plieuse, observations, colonnes Mag/Hauteur/Fournisseur du second
   outil. Un OF saisi dans MySifa qui ne saurait pas les écrire produirait un
   document plus pauvre que celui qu'il remplace, et l'atelier retournerait au
   papier.

2. Un OF ne pouvait pas pointer une commande RVGI. `rvgi_rattachements` sait
   déjà lier « un objet » à « une ou plusieurs pièces », mais `recalculer_etat`
   écrit l'état sur l'objet : il lui faut les trois colonnes d'accueil, les
   mêmes que `planning_entries` (`rvgi_etat`, `rvgi_maj_le`) plus la vitrine
   texte des numéros (`cmd_rvgi`, l'équivalent de `dos_rvgi`).

3. Une fiche technique ne pointait aucun article de l'ERP. La référence texte
   suffit à l'affichage mais pas au rapprochement : c'est `code1`/`code2` qui
   identifient un article dans RVGI, et ces colonnes y sont du TEXTE.

`source` distingue enfin l'origine d'un OF (`access`, `pdf`, `mysifa`) — la
colonne existait sur `fiches_techniques`, pas sur `of_imports`, et sans elle un
OF saisi ici est indiscernable d'un OF importé.
"""

NOM = "of_fiches_creation_mysifa"
DEPEND = ["rvgi_rattachements", "validation_of_et_fiches"]


_COLONNES_OF = [
    # Le papier atelier, au-delà de ce que le parseur PDF sait lire.
    ("particularites",          "TEXT"),
    ("cales_sachets",           "TEXT"),
    ("observations",            "TEXT"),
    ("ref_matiere_fournisseur", "TEXT"),
    ("outil_2_mag",             "TEXT"),
    ("outil_2_hauteur",         "REAL"),
    ("outil_2_fournisseur",     "TEXT"),
    ("palette_europe",          "INTEGER"),
    ("palette_perdues",         "INTEGER"),
    ("plieuse_pignon",          "TEXT"),
    ("nb_pouces",               "TEXT"),
    ("texte_bobinettes",        "TEXT"),
    # Origine et auteur.
    ("source",                  "TEXT"),
    ("cree_par",                "TEXT"),
    ("cree_le",                 "TEXT"),
    # Accueil du rattachement RVGI — mêmes noms que sur planning_entries.
    ("cmd_rvgi",                "TEXT"),
    ("rvgi_etat",               "TEXT"),
    ("rvgi_maj_le",             "TEXT"),
]

_COLONNES_FT = [
    # Article RVGI. code1/code2 sont du TEXTE côté miroir : les stocker en
    # entier ici casserait la jointure, comme cela s'est déjà produit.
    ("article_code1",   "TEXT"),
    ("article_code2",   "TEXT"),
    ("article_libelle", "TEXT"),
    ("cree_par",        "TEXT"),
    ("cree_le",         "TEXT"),
]


def _ajouter(conn, table, colonnes):
    presentes = {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    ajoutees = 0
    for nom, typ in colonnes:
        if nom in presentes:
            continue
        conn.execute('ALTER TABLE "%s" ADD COLUMN %s %s' % (table, nom, typ))
        ajoutees += 1
    return ajoutees


_TABLE_RATT = """CREATE TABLE rvgi_rattachements (
               id          INTEGER PRIMARY KEY AUTOINCREMENT,
               objet       TEXT    NOT NULL CHECK (objet IN ('dossier','depart','of')),
               objet_id    INTEGER NOT NULL,
               piece       TEXT    NOT NULL CHECK (piece IN ('commande','livraison')),
               numero      TEXT    NOT NULL,
               ligne       INTEGER,
               qte         REAL,
               etat        TEXT    NOT NULL DEFAULT 'confirme'
                           CHECK (etat IN ('confirme','a_verifier')),
               vu_qte      REAL,
               vu_article  TEXT,
               vu_client   TEXT,
               cree_le     TEXT    NOT NULL,
               cree_par    TEXT,
               confirme_le TEXT,
               note        TEXT,
               UNIQUE(objet, objet_id, piece, numero, ligne)
           )"""

_INDEX_RATT = (
    ("idx_rvgi_ratt_objet", "objet, objet_id"),
    ("idx_rvgi_ratt_piece", "piece, numero, ligne"),
    ("idx_rvgi_ratt_etat", "etat"),
)


def _ouvrir_rattachements_aux_of(conn) -> bool:
    """Autorise `objet = 'of'` dans rvgi_rattachements.

    La contrainte d'origine est un CHECK en dur (`objet IN ('dossier','depart')`).
    SQLite ne sait pas la modifier : il faut reconstruire la table. On ne le
    fait qu'une fois — un OF rattaché échouait sinon sur une IntegrityError,
    au moment précis où l'ADV valide sa saisie.
    """
    ligne = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='rvgi_rattachements'"
    ).fetchone()
    if ligne is None:
        return False           # la migration rvgi_rattachements créera la bonne
    if "'of'" in (ligne[0] or ""):
        return False           # déjà ouverte

    conn.execute("ALTER TABLE rvgi_rattachements RENAME TO _rvgi_ratt_avant_of")
    conn.execute(_TABLE_RATT)
    conn.execute(
        """INSERT INTO rvgi_rattachements
             (id, objet, objet_id, piece, numero, ligne, qte, etat,
              vu_qte, vu_article, vu_client, cree_le, cree_par, confirme_le, note)
           SELECT id, objet, objet_id, piece, numero, ligne, qte, etat,
                  vu_qte, vu_article, vu_client, cree_le, cree_par, confirme_le, note
             FROM _rvgi_ratt_avant_of"""
    )
    conn.execute("DROP TABLE _rvgi_ratt_avant_of")
    for idx, cols in _INDEX_RATT:
        conn.execute(
            "CREATE INDEX IF NOT EXISTS %s ON rvgi_rattachements(%s)" % (idx, cols)
        )
    return True


def appliquer(conn):
    n_of = _ajouter(conn, "of_imports", _COLONNES_OF)
    n_ft = _ajouter(conn, "fiches_techniques", _COLONNES_FT)

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_of_imports_source ON of_imports(source)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_of_imports_cmd_rvgi ON of_imports(cmd_rvgi)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_fiches_article ON fiches_techniques(article_code1, article_code2)"
    )

    # Reprise de l'existant : tout OF déjà en base vient d'ailleurs. On ne
    # devine pas mieux que « un PDF est là » vs « rien », ce qui suffit à ne
    # jamais confondre un OF saisi ici avec un OF venu d'Access.
    repris = conn.execute(
        """UPDATE of_imports
              SET source = CASE WHEN pdf_filename IS NOT NULL AND pdf_filename <> ''
                                THEN 'pdf' ELSE 'access' END
            WHERE source IS NULL OR source = ''"""
    ).rowcount

    rebati = _ouvrir_rattachements_aux_of(conn)

    conn.commit()
    print("[MySifa] migration of_fiches_creation_mysifa : "
          "%d colonne(s) sur of_imports, %d sur fiches_techniques, "
          "%d OF existant(s) datés de leur origine%s." % (
              n_of, n_ft, repris,
              ", table de rattachement rebâtie pour accueillir les OF" if rebati else ""))

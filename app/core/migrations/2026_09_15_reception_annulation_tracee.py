"""
Réception et bobines : on désactive, on n'efface pas.

Trois routes effaçaient jusqu'ici des lignes qui font preuve d'origine :
`DELETE FROM stock_receptions`, `DELETE FROM stock_reception_items` et
`DELETE FROM stock_bobines`. La migration `stock_bobines` du 09/09 dit pourtant
de `stock_reception_items` qu'elle est « un ÉVÉNEMENT, immuable — fait preuve
d'origine pour la chaîne FSC ». Supprimer une réception, c'est effacer l'origine
de bobines qui, elles, sont peut-être déjà montées en production.

Trois mécanismes, et le choix de chacun tient à une seule question : que se
passe-t-il si une requête de lecture oublie de filtrer ?

1. **`stock_receptions` reste en place, marquée.** `annulee_le`, `annulee_par`,
   `motif_annulation`. Et l'allégation est NEUTRALISÉE à l'annulation
   (`fsc_type_claim` passe à `non_fsc`, l'ancienne valeur étant conservée dans
   `fsc_claim_avant_annulation`). C'est ce qui rend l'oubli inoffensif : une
   vingtaine de requêtes, dans six fichiers, remontent d'un code-barres à sa
   réception pour en lire le claim. Les modifier toutes, c'est en manquer une —
   et celle qu'on manque fait revendiquer FSC une bobine dont la réception a été
   annulée. Neutraliser la source règle les vingt d'un coup.

2. **`stock_reception_items` : la ligne annulée CHANGE DE TABLE.**
   `stock_reception_items_annules` la garde telle quelle, avec qui l'a annulée
   et pourquoi. Rien n'est perdu, tout reste interrogeable, et aucune des
   requêtes qui résolvent un code-barres n'a besoin d'être touchée — la ligne a
   réellement quitté le journal des événements. Un drapeau laissé sur place
   aurait supposé que ces vingt requêtes le lisent toutes.

3. **`stock_bobines` : un nouvel ÉTAT.** `annulee` sort naturellement de tous
   les filtres `etat = 'stock'` déjà écrits — comptage de stock, cohérence,
   listes. Volontairement absent de `ETATS`, qui est la liste des états qu'un
   humain peut poser depuis l'écran : une annulation se trace, elle ne se
   choisit pas dans un menu. Les colonnes `annulee_*` gardent la trace.

Ce que la migration NE fait pas : rattraper les suppressions passées. Ce qui a
été effacé l'a été ; inventer des lignes pour boucher le trou donnerait à un
auditeur une histoire fausse plutôt qu'une histoire incomplète.

Rejouable : test de présence avant chaque ALTER, CREATE TABLE IF NOT EXISTS.
"""

NOM = "reception_annulation_tracee"
DEPEND = ["fsc_reception_verrou_portee_certificat"]


_COLONNES_RECEPTION = [
    ("annulee_le", "TEXT"),
    ("annulee_par", "TEXT"),
    ("motif_annulation", "TEXT"),
    # Ce que la réception revendiquait avant d'être annulée. Sans cette copie,
    # neutraliser le claim effacerait l'information qu'on cherche à conserver.
    ("fsc_claim_avant_annulation", "TEXT"),
]

_COLONNES_BOBINE = [
    ("annulee_le", "TEXT"),
    ("annulee_par", "TEXT"),
    ("motif_annulation", "TEXT"),
]


def _cols(conn, table: str) -> set:
    return {r[1] for r in conn.execute("PRAGMA table_info(%s)" % table).fetchall()}


def _tables(conn) -> set:
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def appliquer(conn):
    tables = _tables(conn)
    ajoutees = 0

    for table, colonnes in (("stock_receptions", _COLONNES_RECEPTION),
                            ("stock_bobines", _COLONNES_BOBINE)):
        if table not in tables:
            continue
        presentes = _cols(conn, table)
        for nom, typ in colonnes:
            if nom not in presentes:
                conn.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, nom, typ))
                ajoutees += 1

    # L'archive des bobines retirées d'une réception. Même forme que le journal
    # d'origine : on doit pouvoir la relire sans traduction, et la recoller si
    # une annulation était elle-même une erreur.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_reception_items_annules (
            id              INTEGER PRIMARY KEY,
            reception_id    INTEGER NOT NULL,
            code_barre      TEXT    NOT NULL,
            scanned_at      TEXT,
            matiere_id      INTEGER,
            laize_id        INTEGER,
            doublon_note    TEXT,
            impacte_stock   INTEGER,
            annule_le       TEXT    NOT NULL,
            annule_par      TEXT,
            motif           TEXT
        )
        """
    )
    for sql in (
        "CREATE INDEX IF NOT EXISTS idx_recp_items_annules_recep "
        "ON stock_reception_items_annules(reception_id)",
        "CREATE INDEX IF NOT EXISTS idx_recp_items_annules_code "
        "ON stock_reception_items_annules(code_barre)",
    ):
        conn.execute(sql)

    conn.commit()
    print("[MySifa] migration %s : %d colonne(s) ajoutee(s), "
          "archive des items de reception prete." % (NOM, ajoutees))

"""Rattacher un dossier de fabrication, ou un départ, à des pièces de RVGI.

Le problème
-----------
Un dossier de production porte aujourd'hui un `dos_rvgi` tapé à la main, et un
départ MyExpé un `no_bl` recopié. Rien ne vérifie que ces numéros existent, et
un champ texte ne sait pas dire « ce dossier couvre les lignes 1 à 3 de la
commande 9932128 et la moitié de la ligne 5 de la 9932131 ».

Or c'est le cas courant, pas le cas tordu : une production peut couvrir
plusieurs commandes, une seule, une ligne, plusieurs lignes, ou une partie de
ligne quand la quantité ne passe pas en un seul lancement. Et une expédition
peut porter plusieurs bons de livraison.

Ce que fait cette migration
---------------------------
Une table de liaison unique, `rvgi_rattachements`, pour les deux sens :

    dossier  → lignes de commande RVGI   (cde_ligne : numero + ligne)
    départ   → bons de livraison RVGI    (liv_ligne : numero + ligne)

Elle pointe l'**identifiant** de l'objet MySifa, jamais sa référence texte.
C'est la leçon du chantier Maintenance : le rattachement est structurel, le
libellé n'est qu'un affichage. Un dossier renommé garde ses rattachements.

`planning_entries.dos_rvgi` et `expe_departs.no_bl` sont conservés et tenus à
jour en dénormalisé — même choix assumé que `expe_departs.no_dossier`, pour ne
pas casser les requêtes qui les lisent.

Le miroir a jusqu'à douze heures de retard
------------------------------------------
Une commande saisie il y a dix minutes n'y est pas encore. Un rattachement
naît donc soit `confirme` (la pièce a été choisie dans une liste issue du
miroir), soit `a_verifier` (le numéro a été tapé à la main et le miroir ne le
connaît pas encore). Après chaque synchro, les `a_verifier` sont repassés : ce
qui est apparu devient `confirme`. Sans cette reprise, la porte de sortie
« je ne trouve pas ma commande » deviendrait la porte principale.
"""

from __future__ import annotations

import sqlite3

NOM = "rvgi_rattachements"
DEPEND = ["expe_depart_multi_dossiers"]

# États d'un dossier vis-à-vis de RVGI, portés par planning_entries.rvgi_etat.
#   lie          toutes les lignes rattachées sont confirmées et couvertes
#   partiel      rattaché, mais une ligne au moins n'est couverte qu'en partie
#   a_verifier   au moins un numéro saisi à la main, pas encore vu dans le miroir
#   a_rattacher  « je ne trouve pas ma commande » — attend un arbitrage humain
#   hors_commande  production sans commande (stock, essai, marché) — assumé
ETATS = ("lie", "partiel", "a_verifier", "a_rattacher", "hors_commande")


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}


def appliquer(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rvgi_rattachements (
               id          INTEGER PRIMARY KEY AUTOINCREMENT,

               -- Ce qu'on rattache, côté MySifa. `objet_id` est un id, jamais
               -- une référence texte : renommer un dossier ne doit rien casser.
               objet       TEXT    NOT NULL CHECK (objet IN ('dossier','depart')),
               objet_id    INTEGER NOT NULL,

               -- Ce à quoi on le rattache, côté RVGI. On stocke la clé
               -- métier (numéro + ligne), jamais l'`id` du miroir : le miroir
               -- est reconstruit à chaque synchro.
               piece       TEXT    NOT NULL CHECK (piece IN ('commande','livraison')),
               numero      TEXT    NOT NULL,
               ligne       INTEGER,          -- NULL = toute la pièce

               -- Quantité rattachée. NULL = toute la ligne. Sert à calculer le
               -- reste à produire et à fermer une ligne quand elle est couverte.
               qte         REAL,

               etat        TEXT    NOT NULL DEFAULT 'confirme'
                           CHECK (etat IN ('confirme','a_verifier')),

               -- Photo de la ligne RVGI au moment du rattachement : ce qui a
               -- été montré à celui qui a cliqué. Si RVGI change la quantité
               -- après coup, on doit pouvoir le voir au lieu de le subir.
               vu_qte      REAL,
               vu_article  TEXT,
               vu_client   TEXT,

               cree_le     TEXT    NOT NULL,
               cree_par    TEXT,
               confirme_le TEXT,             -- date de la synchro qui l'a vu

               note        TEXT,

               UNIQUE(objet, objet_id, piece, numero, ligne)
           )"""
    )
    for idx, cols in (
        ("idx_rvgi_ratt_objet", "objet, objet_id"),
        ("idx_rvgi_ratt_piece", "piece, numero, ligne"),
        ("idx_rvgi_ratt_etat", "etat"),
    ):
        conn.execute(
            "CREATE INDEX IF NOT EXISTS %s ON rvgi_rattachements(%s)" % (idx, cols)
        )

    # État de rattachement, porté par l'objet lui-même pour rester filtrable
    # sans jointure — c'est ce qui alimente la liste « à rattacher ».
    pe = _colonnes(conn, "planning_entries")
    if pe and "rvgi_etat" not in pe:
        conn.execute("ALTER TABLE planning_entries ADD COLUMN rvgi_etat TEXT")
    if pe and "rvgi_maj_le" not in pe:
        conn.execute("ALTER TABLE planning_entries ADD COLUMN rvgi_maj_le TEXT")

    ed = _colonnes(conn, "expe_departs")
    if ed and "rvgi_etat" not in ed:
        conn.execute("ALTER TABLE expe_departs ADD COLUMN rvgi_etat TEXT")
    if ed and "rvgi_maj_le" not in ed:
        conn.execute("ALTER TABLE expe_departs ADD COLUMN rvgi_maj_le TEXT")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pe_rvgi_etat ON planning_entries(rvgi_etat)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ed_rvgi_etat ON expe_departs(rvgi_etat)"
    )

    # ── Reprise de l'existant ────────────────────────────────────────────────
    # Les `dos_rvgi` et `no_bl` déjà saisis deviennent des rattachements
    # `a_verifier` : ils n'ont jamais été confrontés au miroir. La reprise après
    # synchro confirmera ceux qui existent et laissera les autres en évidence.
    # On ne devine RIEN : pas de ligne, pas de quantité, juste le numéro.
    repris_d = 0
    if pe and "dos_rvgi" in pe:
        repris_d = conn.execute(
            """INSERT OR IGNORE INTO rvgi_rattachements
                 (objet, objet_id, piece, numero, ligne, etat, cree_le, cree_par, note)
               SELECT 'dossier', id, 'commande',
                      TRIM(dos_rvgi), NULL, 'a_verifier',
                      COALESCE(created_at, datetime('now')),
                      'migration:rvgi_rattachements',
                      'Repris du champ texte dos_rvgi, jamais confronté au miroir.'
                 FROM planning_entries
                WHERE dos_rvgi IS NOT NULL AND TRIM(dos_rvgi) <> ''"""
        ).rowcount

    repris_b = 0
    if ed and "no_bl" in ed:
        repris_b = conn.execute(
            """INSERT OR IGNORE INTO rvgi_rattachements
                 (objet, objet_id, piece, numero, ligne, etat, cree_le, cree_par, note)
               SELECT 'depart', id, 'livraison',
                      TRIM(no_bl), NULL, 'a_verifier',
                      COALESCE(created_at, datetime('now')),
                      'migration:rvgi_rattachements',
                      'Repris du champ texte no_bl, jamais confronté au miroir.'
                 FROM expe_departs
                WHERE no_bl IS NOT NULL AND TRIM(no_bl) <> ''"""
        ).rowcount

    if pe:
        conn.execute(
            """UPDATE planning_entries
                  SET rvgi_etat = CASE
                        WHEN dos_rvgi IS NOT NULL AND TRIM(dos_rvgi) <> ''
                             THEN 'a_verifier' ELSE 'a_rattacher' END,
                      rvgi_maj_le = datetime('now')
                WHERE rvgi_etat IS NULL"""
        )
    if ed:
        conn.execute(
            """UPDATE expe_departs
                  SET rvgi_etat = CASE
                        WHEN no_bl IS NOT NULL AND TRIM(no_bl) <> ''
                             THEN 'a_verifier' ELSE 'a_rattacher' END,
                      rvgi_maj_le = datetime('now')
                WHERE rvgi_etat IS NULL"""
        )

    print(
        "[MySifa] migration rvgi_rattachements : table de liaison créée, "
        "%d dossier(s) et %d départ(s) repris depuis leur champ texte, en "
        "« à vérifier ». La prochaine synchro RVGI confirmera ceux qui existent."
        % (repris_d, repris_b)
    )

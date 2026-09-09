"""
La bobine devient un objet de stock.

Avant cette migration, le stock matiere de MySifa est un COMPTEUR : `mp_stock`
et `mp_stock_laize` tiennent une quantite par matiere x laize, et la bobine
`Y2606000506` n'existe nulle part. Le code-barres n'apparait que dans deux
JOURNAUX -- `stock_reception_items` (ce code a ete scanne a cette reception) et
`fab_matieres_utilisees` (ce code a ete scanne a cette machine). Aucun des deux
ne dit ce qu'il reste sur la bobine, ni si elle est encore la.

D'ou cette table. Elle ne remplace pas `stock_reception_items` et ne doit pas
la remplacer : les deux ne disent pas la meme chose.

    stock_reception_items   un EVENEMENT, immuable -- fait preuve d'origine
                            pour `origine_bobine.py` et pour la chaine FSC
    stock_bobines           un ETAT, qui change -- ce qui est en stock,
                            et ce qu'il en reste

Fusionner les deux ferait perdre la preuve le jour ou l'etat change. C'est
exactement ce qu'on demande a une tracabilite de ne jamais faire.

Pourquoi AUCUNE reprise des 25 lignes existantes
------------------------------------------------
Releve du 09/09/2026 sur la base de production : les 25 bobines de
`stock_reception_items` ont TOUTES `matiere_id` a NULL, et la derniere date du
29/06/2026. Les reprendre a l'etat « stock » creerait 25 bobines rattachees a
aucune matiere, qu'aucun compteur ne peut confronter a quoi que ce soit -- du
stock fantome, invisible et faux. Elles restent ou elles sont : le traceur les
lit deja, rien n'est perdu. La table demarre vide et se remplit par les
receptions a venir, comme la reception RVGI du 04/09.

Pourquoi `metrage_restant` accepte NULL
---------------------------------------
Une bobine dont on ne connait pas le metrage est un cas normal : ni packing
list, ni `metres_lineaires_par_bobine` renseigne sur la matiere. Mettre 0 la
ferait compter comme vide, et une somme silencieuse sortirait un stock reel
sous-estime sans que rien ne le dise. NULL oblige l'ecran a distinguer « il
reste 0 m » de « on ne sait pas », et le service rend toujours le nombre de
bobines sans metrage a cote de la somme.

Pourquoi `suivi_bobine` s'allume tout seul
------------------------------------------
Le drapeau dit quelles matieres sont desormais tenues a la bobine -- c'est lui
qui decide sur quelles references le controle de coherence
(nb de bobines en stock == `mp_stock_laize.quantite`) a un sens. Un drapeau
qu'il faut penser a cocher dans un ecran de parametres n'est jamais a jour :
celui-ci se pose a la premiere bobine creee sur la matiere. Il enregistre un
fait, il ne demande pas une intention.
"""

from __future__ import annotations

import sqlite3

NOM = "stock_bobines"


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def appliquer(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS stock_bobines (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            code_barre        TEXT    NOT NULL UNIQUE,
            matiere_id        INTEGER,
            laize_id          INTEGER,
            reception_id      INTEGER,
            lot_fournisseur   TEXT,
            metrage_initial   REAL,
            metrage_restant   REAL,
            metrage_origine   TEXT,
            etat              TEXT    NOT NULL DEFAULT 'stock',
            planning_entry_id INTEGER,
            no_dossier        TEXT,
            source            TEXT,
            note              TEXT,
            created_at        TEXT    NOT NULL,
            created_by_name   TEXT,
            consomme_at       TEXT,
            updated_at        TEXT
        );

        -- La requete de loin la plus frequente : « que reste-t-il en stock
        -- pour cette matiere dans cette laize ». L'etat est dans l'index
        -- parce qu'il filtre 90 % des lignes des le premier trimestre.
        CREATE INDEX IF NOT EXISTS idx_bob_stock
            ON stock_bobines(matiere_id, laize_id, etat);
        CREATE INDEX IF NOT EXISTS idx_bob_etat
            ON stock_bobines(etat);
        CREATE INDEX IF NOT EXISTS idx_bob_reception
            ON stock_bobines(reception_id);
        CREATE INDEX IF NOT EXISTS idx_bob_dossier
            ON stock_bobines(no_dossier);
        CREATE INDEX IF NOT EXISTS idx_bob_lot
            ON stock_bobines(lot_fournisseur);
        """
    )

    if "suivi_bobine" not in _colonnes(conn, "matieres_premieres"):
        conn.execute(
            "ALTER TABLE matieres_premieres "
            "ADD COLUMN suivi_bobine INTEGER NOT NULL DEFAULT 0"
        )
    conn.commit()

    n = conn.execute("SELECT COUNT(*) FROM stock_bobines").fetchone()[0]
    orphelines = conn.execute(
        "SELECT COUNT(*) FROM stock_reception_items WHERE matiere_id IS NULL"
    ).fetchone()[0]
    print(
        "[MySifa] migration stock_bobines : table en place, %d bobine(s) suivie(s). "
        "%d ligne(s) de reception sans matiere laissees a l'historique "
        "(aucune reprise retroactive)." % (n, orphelines)
    )

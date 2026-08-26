"""Rattacher une réception MyStock à la réception RVGI correspondante.

Pourquoi ces colonnes et pas d'autres
-------------------------------------
Une réception de matière se saisit aujourd'hui au code-barres, bobine par
bobine, et le seul endroit où l'on notait le bon de livraison du fournisseur
était le champ `note` — dont le texte d'aide disait littéralement
« ex: BL fournisseur ». Une information qu'on demande dans un placeholder est
une information qu'on ne pourra jamais retrouver.

On lui donne donc sa colonne, plus le lien vers la pièce RVGI qui la porte :

    rvgi_cde            le n° de commande fournisseur (`lif_ligne.numero`)
    rvgi_bl             le n° de BL du fournisseur (`lif_ligne.ref`)
    rvgi_qte_attendue   ce que RVGI dit avoir reçu, marchandise seule

`rvgi_qte_attendue` n'est pas une quantité de travail : c'est un point de
comparaison. RVGI ne connaît qu'un total, MyStock compte des bobines. Garder
les deux permet de dire « 12 bobines scannées, RVGI en annonçait 250 000 » —
et c'est cet écart-là qui vaut d'être vu, pas la valeur seule.

`pf_receptions` porte déjà `bon_livraison` : elle n'a besoin que du lien.
"""

from __future__ import annotations

import sqlite3

NOM = "reception_rvgi"


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def _ajouter(conn: sqlite3.Connection, table: str, colonnes: dict) -> int:
    presentes = _colonnes(conn, table)
    if not presentes:
        return 0
    n = 0
    for nom, decl in colonnes.items():
        if nom in presentes:
            continue
        conn.execute('ALTER TABLE "%s" ADD COLUMN %s %s' % (table, nom, decl))
        n += 1
    return n


def appliquer(conn: sqlite3.Connection) -> None:
    n = 0
    n += _ajouter(conn, "stock_receptions", {
        "rvgi_cde": "TEXT",
        "rvgi_bl": "TEXT",
        "rvgi_qte_attendue": "REAL",
    })
    n += _ajouter(conn, "pf_receptions", {
        "rvgi_cde": "TEXT",
    })

    for table, idx, col in (
        ("stock_receptions", "idx_stock_recep_rvgi", "rvgi_cde"),
        ("stock_receptions", "idx_stock_recep_bl", "rvgi_bl"),
        ("pf_receptions", "idx_pf_recep_rvgi", "rvgi_cde"),
    ):
        if _colonnes(conn, table):
            conn.execute("CREATE INDEX IF NOT EXISTS %s ON %s(%s)" % (idx, table, col))

    # Ce qui a été noté à la main jusqu'ici. Le champ `note` a servi de boîte
    # à tout : on en extrait ce qui ressemble sans ambiguïté à un n° de BL, et
    # on laisse la note intacte — on ne réécrit pas ce que quelqu'un a tapé.
    #
    # UNIQUEMENT la forme collée, « BL137434 ». « BL 137434 » avec un espace
    # est ambigu : le « BL » peut être une étiquette et le numéro « 137434 »,
    # ou faire partie du numéro. Les deux hypothèses existent dans les vraies
    # données de RVGI (`BL137434` mais aussi `AE0049887`, `292192`). Un numéro
    # reconstruit de travers ne retrouverait jamais sa réception : mieux vaut
    # une colonne vide, que quelqu'un remplira en reprenant la réception.
    repris = 0
    if "rvgi_bl" in _colonnes(conn, "stock_receptions"):
        import re
        colle = re.compile(r"\bBL[0-9][A-Za-z0-9\-_/]{2,19}\b", re.I)
        for r in conn.execute(
                "SELECT id, note FROM stock_receptions "
                "WHERE rvgi_bl IS NULL AND note IS NOT NULL AND TRIM(note) <> ''"
        ).fetchall():
            m = colle.search(str(r["note"]))
            if not m:
                continue
            conn.execute("UPDATE stock_receptions SET rvgi_bl = ? WHERE id = ?",
                         (m.group(0).upper(), r["id"]))
            repris += 1

    print(
        "[MySifa] migration reception_rvgi : %d colonnes ajoutées, %d n° de BL "
        "repris des notes existantes." % (n, repris)
    )

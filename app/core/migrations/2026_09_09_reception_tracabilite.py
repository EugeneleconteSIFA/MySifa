"""
Une ligne de réception dit désormais si elle a compté dans le stock.

Le problème, constaté le jour même de la mise en service
-------------------------------------------------------
L'import d'une packing list créait les bobines ET incrémentait le compteur.
Le 09/09/2026, l'import de la liste PZH260443 a fait passer la glassine 60 g
jaune de 394 à 442 bobines au compteur — sans qu'un mètre de matière de plus
soit arrivé dans l'allée.

C'est un double comptage, et il était structurel : le stock de MySifa est
alimenté par les réceptions RVGI, qui sont la vérité comptable de ce qui entre.
Une packing list, elle, arrive avant ou avec la marchandise et décrit les
MÊMES bobines. Les compter des deux côtés, c'est les compter deux fois.

Arbitrage d'Eugène : l'import depuis une liste est de la TRAÇABILITÉ. Il crée
les objets — un code-barres, une laize, un métrage, un lot fournisseur — et ne
touche pas au compteur.

Pourquoi une colonne, et pas simplement « ne plus rien écrire »
--------------------------------------------------------------
Parce que la suppression est le miroir de la réception. `_defalquer_bobines`
retire du stock ce que la réception y avait mis ; si l'import cesse d'ajouter
sans que la suppression cesse de retirer, supprimer un lot de traçabilité
creuse un trou dans un compteur où rien n'était jamais entré. Le drapeau porte
donc l'information là où elle est vraie : sur la ligne, une par bobine.

`DEFAULT 1` n'est pas un choix par défaut, c'est un constat : toutes les lignes
existantes ont bel et bien impacté le stock, y compris les 48 de PZH260443. La
migration ne réécrit donc aucun historique — elle nomme ce qui a eu lieu.

Ce qu'elle NE corrige pas
-------------------------
Les 48 bobines déjà entrées au compteur y restent. Les retirer d'office
supposerait que MySifa sache que la réception RVGI correspondante existe ou
existera, ce qu'il ne sait pas. Le bilan imprimé ci-dessous donne le compte
exact pour que la correction, si elle est voulue, soit faite en connaissance
de cause.
"""

from __future__ import annotations

import sqlite3

NOM = "reception_items_impacte_stock"


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def appliquer(conn: sqlite3.Connection) -> None:
    if "stock_reception_items" not in {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")
    }:
        print("[MySifa] migration reception_tracabilite : table absente, rien a faire.")
        return

    if "impacte_stock" not in _colonnes(conn, "stock_reception_items"):
        # DEFAULT 1 : tout ce qui existe a compte dans le stock. La colonne
        # nomme le passe, elle ne le reecrit pas.
        conn.execute(
            "ALTER TABLE stock_reception_items "
            "ADD COLUMN impacte_stock INTEGER NOT NULL DEFAULT 1"
        )
    conn.commit()

    # Le bilan est de l'information, pas de la migration : il ne doit jamais
    # faire echouer un demarrage sur une base dont le schema differe.
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM stock_reception_items").fetchone()[0]
    except sqlite3.Error:
        total = 0
    try:
        listes = conn.execute(
            "SELECT COUNT(*) FROM stock_reception_items "
            "WHERE doublon_note LIKE 'Packing list%'").fetchone()[0]
    except sqlite3.Error:
        listes = 0
    print(
        "[MySifa] migration reception_tracabilite : colonne en place. "
        "%d ligne(s) de reception, toutes marquees comme ayant compte dans le "
        "stock (dont %d venues d'une packing list, entrees avant la bascule). "
        "Les prochains imports de liste n'incrementeront plus le compteur."
        % (total, listes)
    )

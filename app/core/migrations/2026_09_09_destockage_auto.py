"""
Le déstockage de production se déclenche tout seul — et cesse d'attendre une
relecture que personne ne fait.

Constat du 09/09/2026 sur la base de production, et c'est lui qui décide de
cette migration :

    of_imports         938 lignes,   0 validée
    fiches_techniques  920 lignes,   0 validée
    planning_entries   232 dossiers marqués « déstocké », 0 mouvement de stock
    mp_mouvements      212 sorties,  0 rattachée à un dossier

Le verrou documentaire exigeait que l'OF ET la fiche technique aient été relus
et cochés avant tout mouvement. L'intention était juste : un stock faux ne se
voit qu'à l'inventaire suivant. Mais la case n'a jamais été cochée une seule
fois, donc le verrou bloquait 100 % des dossiers — et la modale de déstockage a
fini par être débranchée du planning, ce qui a supprimé la fonction entière.

Un verrou que personne ne peut satisfaire n'est pas un garde-fou.

Ce qui le remplace : un contrôle des DONNÉES. Le métrage est-il là ? Le nombre
de fronts boucle-t-il avec la géométrie de l'outil (`coherence_fiche`) ? Les
matières de la fiche pointent-elles des références MyStock ? Ce sont trois
questions qu'une machine sait poser à chaque dossier, donc qui seront posées.
`valide` reste en base et garde son sens — il ne commande simplement plus le
stock.

Les trois colonnes ajoutées
---------------------------
`destockage` accepte désormais une troisième valeur, `reserve` : le dossier a
été déstocké pour ce qui pouvait l'être, et une matière au moins ne l'a pas
été. Sans cet état, un dossier à moitié sorti ressemblerait à un dossier
propre — et l'écart dormirait jusqu'à l'inventaire.

`destockage_at` date le geste, `destockage_reserve` dit ce qui manque, en
clair, pour que la personne qui rouvre le dossier sache quoi corriger sans
relire un calcul.

Aucune reprise rétroactive
-------------------------
`destockage_auto_depuis` est vide à l'installation, exactement comme
`reception_rvgi_depuis` le 04/09. Tant que personne n'a fixé le jour de
bascule, l'automatisme ne prend RIEN — et il ne touchera jamais aux 232
dossiers déjà marqués, dont le stock a été tenu autrement pendant des mois.
Les rejouer réécrirait un historique que plus personne ne peut vérifier.
"""

from __future__ import annotations

import sqlite3

NOM = "destockage_auto_controle_donnees"

CLE_DEPUIS = "destockage_auto_depuis"


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def appliquer(conn: sqlite3.Connection) -> None:
    presentes = _colonnes(conn, "planning_entries")
    for nom, sql_type in (("destockage_at", "TEXT"),
                          ("destockage_reserve", "TEXT")):
        if nom not in presentes:
            conn.execute("ALTER TABLE planning_entries ADD COLUMN %s %s" % (nom, sql_type))

    conn.execute(
        """CREATE TABLE IF NOT EXISTS stock_config (
               cle        TEXT PRIMARY KEY NOT NULL,
               valeur     TEXT,
               updated_at TEXT
           )"""
    )
    # Vide, et pas une date : une valeur par défaut ferait déstocker
    # rétroactivement des mois de production au premier démarrage.
    conn.execute(
        "INSERT OR IGNORE INTO stock_config (cle, valeur) VALUES (?, '')",
        (CLE_DEPUIS,),
    )
    conn.commit()

    marques = conn.execute(
        "SELECT COUNT(*) FROM planning_entries WHERE destockage='done'"
    ).fetchone()[0]
    avec_mvt = conn.execute(
        "SELECT COUNT(DISTINCT planning_entry_id) FROM mp_mouvements "
        "WHERE planning_entry_id IS NOT NULL"
    ).fetchone()[0]
    print(
        "[MySifa] migration destockage_auto : contrôle des données en place. "
        "%d dossier(s) marqués « déstocké » dont %d avec un mouvement réel — "
        "aucun ne sera rejoué. L'automatisme ne prend rien tant que "
        "`%s` est vide (Paramètres)." % (marques, avec_mvt, CLE_DEPUIS)
    )

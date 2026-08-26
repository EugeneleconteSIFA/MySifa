"""Savoir quels postes rament, au lieu de le deviner.

Le problème
-----------
« MySifa est lent sur le PC de l'atelier » est un signalement invérifiable :
il ne dit ni de combien, ni depuis quand, ni si c'est le poste, le réseau ou
la page. Sans mesure, la seule réponse possible est de tout alléger pour tout
le monde — ce qui punit les postes qui vont bien.

Ce qu'on enregistre
-------------------
Un relevé par session et par poste : le nombre d'images par seconde réellement
obtenu pendant une seconde de mesure, le temps de rendu de la page, et les
caractéristiques du poste (cœurs, mémoire, définition d'écran). C'est le FPS
qui tranche : un poste qui affiche 12 images par seconde est lent, quel que
soit son âge affiché.

`poste` est un identifiant tiré au sort côté navigateur et gardé en
localStorage. Il ne dit rien de la personne — il permet seulement de recoller
les relevés d'une même machine dans le temps, et donc de distinguer « ce poste
a toujours ramé » de « ce poste s'est mis à ramer cette semaine ».

Pourquoi une table et pas un log
--------------------------------
Un écart de fluidité se juge sur une série, pas sur une photo. Et une fois la
série là, la question « faut-il remplacer ce poste ou alléger cette page ? »
se répond avec des chiffres : si le même poste est fluide sur MyStock et
saccadé sur le planning, c'est la page qu'il faut corriger.
"""

from __future__ import annotations

import sqlite3

NOM = "perf_postes"


def appliquer(conn: sqlite3.Connection) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS perf_releves (
               id           INTEGER PRIMARY KEY AUTOINCREMENT,
               cree_le      TEXT NOT NULL,
               email        TEXT,
               -- Identifiant de machine tiré au sort côté navigateur.
               poste        TEXT NOT NULL,
               -- 'eco' | 'normal' : ce que la sonde a décidé pour cette session.
               niveau       TEXT NOT NULL DEFAULT 'normal',
               -- 1 quand l'utilisateur a forcé le mode à la main : le relevé
               -- reste utile comme mesure, mais le niveau n'est plus un verdict.
               force_main   INTEGER NOT NULL DEFAULT 0,
               score        INTEGER NOT NULL DEFAULT 0,

               fps          REAL,
               fps_bas      REAL,
               blocage_ms   REAL,

               cores        INTEGER,
               memoire_go   REAL,
               dpr          REAL,
               ecran        TEXT,

               t_reponse_ms REAL,
               t_rendu_ms   REAL,
               t_charge_ms  REAL,

               page         TEXT,
               navigateur   TEXT
           )"""
    )
    for idx, cols in (
        ("idx_perf_poste", "perf_releves(poste, cree_le DESC)"),
        ("idx_perf_date", "perf_releves(cree_le DESC)"),
        ("idx_perf_niveau", "perf_releves(niveau, cree_le DESC)"),
    ):
        conn.execute("CREATE INDEX IF NOT EXISTS %s ON %s" % (idx, cols))

    print(
        "[MySifa] migration perf_postes : relevés de fluidité par poste prêts "
        "(FPS mesuré, temps de rendu, verdict eco/normal)."
    )

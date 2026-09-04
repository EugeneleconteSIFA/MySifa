"""Détection automatique du fournisseur d'une bobine au scan.

Ce que la base disait avant cette migration : sur 90 scans matière de la saisie
de production, zéro rattaché à une réception. Le fournisseur était tapé à la
main 57 fois, absent 33 fois — et il se contredisait (`R1001-26050458-440-*`
déclaré Frimpeks UK d'un côté, Likexin de l'autre).

`bobine_signatures` est la mémoire de ce que l'application a appris des codes
qu'on lui a déjà montrés : pour chaque forme de code (longueur + préfixe, ou
premier segment + nombre de segments), le COMPTE par fournisseur. Garder les
comptes plutôt qu'un verdict est ce qui rend la table honnête : une forme vue
sous deux noms devient ambiguë et cesse de proposer, au lieu d'imposer le
dernier nom écrit.

Les deux colonnes ajoutées à `fab_matieres_utilisees` répondent à une question
d'audit, pas de confort : « d'où vient ce fournisseur-là ? ». `liaison_mode`
disait déjà si l'origine était démontrée (réception) ou déclarée (manuel) ;
`origine_detection` dit par quel chemin elle a été trouvée, et
`origine_confiance` à quel titre. Sans elles, une origine devinée et une origine
saisie par un opérateur seraient indiscernables six mois plus tard.

La table est SEEDÉE en fin de migration depuis tout l'historique confirmé :
la détection est utile dès le premier scan qui suit le déploiement, pas au
bout de trois mois d'apprentissage.
"""

from __future__ import annotations

import sqlite3

NOM = "signature_bobine"


def _colonnes(conn: sqlite3.Connection, table: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA table_info("%s")' % table)}
    except sqlite3.Error:
        return set()


def appliquer(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS bobine_signatures (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            type         TEXT    NOT NULL,          -- 'num' | 'seg'
            valeur       TEXT    NOT NULL,          -- '11|602', 'G1101|4'
            specificite  INTEGER NOT NULL DEFAULT 0,
            observations TEXT    NOT NULL DEFAULT '{}',   -- {"Kanzan": 7, ...}
            total        INTEGER NOT NULL DEFAULT 0,
            premier_vu   TEXT,
            dernier_vu   TEXT,
            UNIQUE(type, valeur)
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_bobine_sign_lookup "
        "ON bobine_signatures(type, valeur)"
    )

    presentes = _colonnes(conn, "fab_matieres_utilisees")
    if presentes:
        if "origine_detection" not in presentes:
            # 'reception' | 'historique' | 'signature' | 'dossier' | 'saisie'
            conn.execute(
                "ALTER TABLE fab_matieres_utilisees ADD COLUMN origine_detection TEXT"
            )
        if "origine_confiance" not in presentes:
            # 'certain' | 'probable' | 'suggere' | 'aucune'
            conn.execute(
                "ALTER TABLE fab_matieres_utilisees ADD COLUMN origine_confiance TEXT"
            )
    conn.commit()

    # Seed : tout ce que l'application sait déjà des codes-barres devient
    # immédiatement exploitable. `reconstruire` vide la table avant de la
    # remplir, la migration reste donc rejouable sans doubler les compteurs.
    try:
        from app.services.origine_bobine import reconstruire
        bilan = reconstruire(conn)
        conn.commit()
        print(
            "[MySifa] migration signature_bobine : %d signature(s) apprises "
            "sur %d bobine(s) réceptionnées et %d scan(s) de production."
            % (bilan["signatures"], bilan["receptions"], bilan["production"])
        )
    except Exception as e:  # pragma: no cover - le seed ne doit jamais bloquer
        # Une table vide n'empêche rien : la détection repart du premier scan
        # confirmé. Bloquer le démarrage pour un apprentissage serait pire.
        print("[MySifa] migration signature_bobine : seed ignoré (%s)." % e)

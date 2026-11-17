"""
MyExpé : les tarifs transporteur s'organisent en grilles versionnées.

Jusqu'ici `expe_tarifs` était une liste plate de lignes, actives ou en
brouillon. Une grille importée ne laissait aucune trace de son ensemble : on
ne pouvait ni la retirer d'un geste, ni revenir à la précédente, et l'onglet
Tarifs chargeait les 42 000 lignes de Ceva pour les afficher une par une.

`expe_tarif_grilles` porte une grille : transporteur, type d'envoi, base de
calcul, date d'effet, fichier source, statut (brouillon, active, archivée).
Chaque ligne de `expe_tarifs` y est rattachée par `grille_id`. Quand une
grille est activée, les lignes actives qu'elle remplace passent à `actif=0`
avec `remplacee_par_grille_id` : archiver la grille plus tard les rétablit.

La recherche de tarif ne change pas : elle lit toujours `actif=1`.

Reprise : les lignes existantes sont regroupées par transporteur, type
d'envoi, base de calcul, fichier source et état. Chaque groupe devient une
grille « active » ou « brouillon ».
"""

NOM = "expe_tarif_grilles"


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS expe_tarif_grilles (
               id               INTEGER PRIMARY KEY AUTOINCREMENT,
               transporteur_id  INTEGER NOT NULL,
               libelle          TEXT,
               type_envoi       TEXT NOT NULL,
               base_calcul      TEXT NOT NULL,
               statut           TEXT NOT NULL DEFAULT 'brouillon',
               date_effet       TEXT,
               source_filename  TEXT,
               methode_lecture  TEXT,
               created_at       TEXT,
               created_by_email TEXT,
               activee_le       TEXT,
               activee_par      TEXT,
               archivee_le      TEXT,
               FOREIGN KEY (transporteur_id) REFERENCES expe_transporteurs(id)
           )"""
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_expe_tarif_grilles_trp
               ON expe_tarif_grilles(transporteur_id, statut)"""
    )
    cols = {r[1] for r in conn.execute('PRAGMA table_info("expe_tarifs")').fetchall()}
    if "grille_id" not in cols:
        conn.execute("ALTER TABLE expe_tarifs ADD COLUMN grille_id INTEGER")
    if "remplacee_par_grille_id" not in cols:
        conn.execute("ALTER TABLE expe_tarifs ADD COLUMN remplacee_par_grille_id INTEGER")
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_expe_tarifs_grille
               ON expe_tarifs(grille_id, zone_valeur, tranche_min)"""
    )
    conn.execute(
        """CREATE INDEX IF NOT EXISTS idx_expe_tarifs_remplacee
               ON expe_tarifs(remplacee_par_grille_id)"""
    )

    groupes = conn.execute(
        """SELECT transporteur_id, type_envoi, base_calcul,
                  COALESCE(source_filename, '') AS src,
                  CASE WHEN actif = 1 THEN 1 ELSE 0 END AS act,
                  MIN(valid_from) AS effet, MIN(created_at) AS cree,
                  MIN(created_by_email) AS par
             FROM expe_tarifs
            WHERE grille_id IS NULL
            GROUP BY transporteur_id, type_envoi, base_calcul, src, act"""
    ).fetchall()
    n_grilles = n_lignes = 0
    for g in groupes:
        trp, te, bc, src, act, effet, cree, par = (
            g[0], g[1], g[2], g[3], g[4], g[5], g[6], g[7]
        )
        cur = conn.execute(
            """INSERT INTO expe_tarif_grilles
                   (transporteur_id, libelle, type_envoi, base_calcul, statut,
                    date_effet, source_filename, methode_lecture,
                    created_at, created_by_email, activee_le)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                trp,
                "Reprise " + (src or "sans fichier"),
                te,
                bc,
                "active" if act else "brouillon",
                effet,
                src or None,
                "reprise",
                cree,
                par,
                cree if act else None,
            ),
        )
        gid = cur.lastrowid
        n_lignes += conn.execute(
            """UPDATE expe_tarifs SET grille_id = ?
                WHERE grille_id IS NULL AND transporteur_id = ?
                  AND type_envoi IS ? AND base_calcul IS ?
                  AND COALESCE(source_filename, '') = ?
                  AND (CASE WHEN actif = 1 THEN 1 ELSE 0 END) = ?""",
            (gid, trp, te, bc, src, act),
        ).rowcount or 0
        n_grilles += 1
    conn.commit()
    print(
        f"[MySifa] migration {NOM} : {n_grilles} grille(s) reprise(s), "
        f"{n_lignes} ligne(s) rattachée(s)."
    )

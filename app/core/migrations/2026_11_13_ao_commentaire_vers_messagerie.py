"""MyAO — le commentaire général d'une offre entre dans la messagerie.

Le commentaire saisi par un fournisseur sous son offre (« Same as AO-2026-019
right? ») n'était stocké que dans `ao_fournisseurs.commentaire_global` et
n'apparaissait nulle part côté SIFA. Depuis le 13/11/2026, le portail le copie
dans `ao_messages` à chaque dépôt. Cette reprise fait de même pour les
commentaires déjà déposés, en non lu, daté de la réponse. Un commentaire déjà
présent mot pour mot dans la conversation n'est pas recopié.
"""

NOM = "ao_commentaire_vers_messagerie"


def appliquer(conn):
    tables = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if not {"ao_fournisseurs", "ao_messages"} <= tables:
        return
    cols = {r[1] for r in conn.execute("PRAGMA table_info(ao_fournisseurs)").fetchall()}
    if "commentaire_global" not in cols:
        return
    rows = conn.execute(
        """SELECT id, nom_fournisseur, commentaire_global,
                  COALESCE(date_reponse, date_envoi,
                           strftime('%Y-%m-%dT%H:%M:%S', 'now', 'localtime')) AS d
           FROM ao_fournisseurs
           WHERE TRIM(COALESCE(commentaire_global, '')) != ''""").fetchall()
    n = 0
    for fid, nom, com, d in rows:
        com = com.strip()
        deja = conn.execute(
            """SELECT 1 FROM ao_messages
               WHERE ao_fournisseur_id=? AND expediteur='fournisseur'
                 AND TRIM(message)=? LIMIT 1""",
            (fid, com),
        ).fetchone()
        if deja:
            continue
        conn.execute(
            """INSERT INTO ao_messages
               (ao_fournisseur_id, expediteur, auteur_nom, message, date, lu)
               VALUES (?,'fournisseur',?,?,?,0)""",
            (fid, nom, com, d),
        )
        n += 1
    conn.commit()
    print(f"[MySifa] migration ao_commentaire_vers_messagerie : {n} commentaire(s) repris dans la messagerie.")

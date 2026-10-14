"""Nouvel ERP — cahiers des charges, fiche matière de RVGI, stock par laize.

Cahier des charges (réponse d'Eugène, 14/10/2026) : des notes attachées à un
tiers ou à un article, chacune pour une étape de la chaîne (devis, commande,
fabrication, livraison, facturation, achat, réception). Exemple : « livraison :
seulement des colis complets ». La pièce de l'étape les affiche.

Fiche matière RVGI : libellés techniques, adhésif, protecteur, film,
synthétique, épaisseur. Compte comptable par article (prime sur la famille).

Stock matières : RVGI le tient par laize (code 3). Le mouvement porte la laize
de la ligne de réception ou de la consommation.
"""

NOM = "gc_cahiers_matieres"
DEPEND = ["gc_socle", "gc_fiches_rvgi", "gc_conditionnement_achat"]


def _col(conn, table, col, decl):
    if col not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS gc_cahiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            objet TEXT NOT NULL,              -- tiers | article
            objet_id INTEGER NOT NULL,
            etape TEXT NOT NULL,
            texte TEXT NOT NULL,
            imprime INTEGER NOT NULL DEFAULT 0,
            rang INTEGER NOT NULL DEFAULT 0,
            cree_par TEXT, cree_le TEXT, modifie_le TEXT);
        CREATE INDEX IF NOT EXISTS idx_gc_cahiers_objet ON gc_cahiers(objet, objet_id);
        """
    )
    for col, decl in (("libelle_technique", "TEXT"), ("libelle_technique2", "TEXT"), ("adhesif", "TEXT"),
                      ("protecteur", "TEXT"), ("film", "INTEGER NOT NULL DEFAULT 0"),
                      ("synthetique", "INTEGER NOT NULL DEFAULT 0"), ("epaisseur_milli", "INTEGER"),
                      ("compte_vente", "TEXT"), ("compte_achat", "TEXT")):
        _col(conn, "gc_articles", col, decl)
    _col(conn, "gc_mouvements", "laize_dmm", "INTEGER")
    # Mouvements de réception déjà écrits : laize reprise de la ligne.
    n = conn.execute(
        """UPDATE gc_mouvements SET laize_dmm=(SELECT l.laize_dmm FROM gc_pieces_lignes l WHERE l.id=gc_mouvements.ligne_id)
           WHERE laize_dmm IS NULL AND ligne_id IS NOT NULL AND type='reception'""").rowcount
    if n:
        print(f"[MySifa] migration gc_cahiers_matieres : {n} mouvement(s) de réception avec laize.")
    conn.commit()

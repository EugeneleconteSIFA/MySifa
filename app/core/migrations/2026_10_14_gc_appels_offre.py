"""Nouvel ERP — appels d'offre fournisseurs (RVGI : « Appels d'offre »).

Une demande de prix est une pièce (`gc_pieces.type='aof'`) ; acceptée, elle
se transforme en commande fournisseur, ligne à ligne. Seule la numérotation
manque.
"""

NOM = "gc_appels_offre"
DEPEND = ["gc_socle", "gc_parite_rvgi"]


def appliquer(conn):
    conn.execute(
        "INSERT OR IGNORE INTO gc_sequences (code, libelle, format, reinit) VALUES ('aof', 'Appel d''offre', '{N}', 'jamais')"
    )
    conn.commit()

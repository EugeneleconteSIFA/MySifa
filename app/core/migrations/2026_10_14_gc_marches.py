"""Nouvel ERP — marchés (contrats cadres).

Un marché est une pièce (`gc_pieces.type='marche'`) : quantités et prix
convenus pour une période (`date_validite` = fin du marché). Chaque appel est
une commande dont les lignes pointent la ligne de marché (`ligne_amont_id`) ;
le reste à appeler s'en déduit. Seule la numérotation manque.
"""

NOM = "gc_marches"
DEPEND = ["gc_socle"]


def appliquer(conn):
    conn.execute(
        "INSERT OR IGNORE INTO gc_sequences (code, libelle, format) VALUES ('marche', 'Marché', 'MA{AA}{N:05}')"
    )
    conn.commit()

"""Nouvel ERP — ordres de fabrication.

Un OF est une pièce (`gc_pieces.type='of'`) lancée depuis une ligne de
commande ; ses déclarations de production et ses consommations sont des
mouvements de stock rattachés à l'OF. Seule la numérotation manque.
"""

NOM = "gc_production"
DEPEND = ["gc_socle"]


def appliquer(conn):
    conn.execute(
        "INSERT OR IGNORE INTO gc_sequences (code, libelle, format) VALUES ('of', 'Ordre de fabrication', 'OF{AA}{N:05}')"
    )
    conn.commit()

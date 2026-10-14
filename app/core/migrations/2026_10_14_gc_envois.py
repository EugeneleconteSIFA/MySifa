"""Nouvel ERP — historique des envois de pièces par e-mail.

Chaque envoi garde la pièce, les destinataires, l'objet, l'expéditeur et le
résultat : on doit pouvoir dire à un client quand et à qui sa facture est
partie, et ne pas renvoyer deux fois sans le savoir.
"""

NOM = "gc_envois"
DEPEND = ["gc_socle"]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS gc_envois (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            piece_id        INTEGER NOT NULL REFERENCES gc_pieces(id),
            envoye_le       TEXT NOT NULL,
            destinataires   TEXT NOT NULL,
            copie           TEXT NOT NULL DEFAULT '',
            objet           TEXT NOT NULL,
            fichier         TEXT NOT NULL,
            reussi          INTEGER NOT NULL,
            envoye_par      TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_gc_envois_piece ON gc_envois(piece_id);
        """
    )
    conn.commit()

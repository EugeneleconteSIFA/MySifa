"""Nouvel ERP — fiche fournisseur de RVGI (captures du 14/10/2026).

Spécificités : texte automatique, nombre d'exemplaires et expédition par
défaut (non / e-mail) pour l'appel d'offre et pour la commande ; traite ;
journal comptable. Interlocuteurs : destinataires automatiques des appels
d'offre et des commandes.

Les identifiants FTP de la fiche RVGI (utilisateur, mot de passe) ne sont pas
repris : un secret ne se stocke pas dans une fiche (CLAUDE.md, sécurité).
"""

NOM = "gc_fournisseurs_rvgi"
DEPEND = ["gc_socle", "gc_parite_rvgi"]


def _col(conn, table, col, decl):
    if col not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def appliquer(conn):
    for col, decl in (("texte_aof", "TEXT"), ("texte_cde", "TEXT"),
                      ("nb_ex_aof", "INTEGER NOT NULL DEFAULT 1"), ("nb_ex_cde", "INTEGER NOT NULL DEFAULT 1"),
                      ("envoi_auto_aof", "TEXT NOT NULL DEFAULT 'non'"), ("envoi_auto_cde", "TEXT NOT NULL DEFAULT 'email'"),
                      ("traite", "TEXT NOT NULL DEFAULT 'sans'"), ("journal", "TEXT")):
        _col(conn, "gc_tiers", col, decl)
    for col in ("envoi_aof", "envoi_cde"):
        _col(conn, "gc_tiers_contacts", col, "INTEGER NOT NULL DEFAULT 0")
    conn.commit()

"""Nouvel ERP — plan de comptes pour l'export comptable (FEC).

Les numéros de comptes et codes journaux sont des réglages, pas du code :
- `gc_compta_reglages` : comptes collectifs, banque, journaux (clé / valeur) ;
- comptes de TVA par taux (`gc_tva.compte_collecte`, `compte_deductible`) ;
- comptes de vente / d'achat par famille (`gc_familles.compte_vente`, `compte_achat`) ;
- compte auxiliaire par tiers (`gc_tiers.compte_auxiliaire`, vide = son code).
Valeurs de départ : plan comptable général, à ajuster dans Paramètres.
"""

NOM = "gc_comptes"
DEPEND = ["gc_socle"]


def _colonne(conn, table, col, decl):
    cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if col not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def appliquer(conn):
    conn.execute(
        """CREATE TABLE IF NOT EXISTS gc_compta_reglages (
               cle     TEXT PRIMARY KEY,
               libelle TEXT NOT NULL,
               valeur  TEXT NOT NULL DEFAULT '',
               rang    INTEGER NOT NULL DEFAULT 0
           )""")
    conn.executemany(
        "INSERT OR IGNORE INTO gc_compta_reglages (cle, libelle, valeur, rang) VALUES (?,?,?,?)",
        [
            ("compte_clients", "Compte collectif clients", "411000", 1),
            ("compte_fournisseurs", "Compte collectif fournisseurs", "401000", 2),
            ("compte_banque", "Compte de banque", "512000", 3),
            ("compte_vente_defaut", "Compte de vente par défaut", "706000", 4),
            ("compte_achat_defaut", "Compte d'achat par défaut", "601000", 5),
            ("journal_ventes", "Journal des ventes", "VT", 6),
            ("journal_achats", "Journal des achats", "AC", 7),
            ("journal_banque", "Journal de banque", "BQ", 8),
        ])
    _colonne(conn, "gc_tva", "compte_collecte", "TEXT NOT NULL DEFAULT ''")
    _colonne(conn, "gc_tva", "compte_deductible", "TEXT NOT NULL DEFAULT ''")
    _colonne(conn, "gc_familles", "compte_vente", "TEXT NOT NULL DEFAULT ''")
    _colonne(conn, "gc_familles", "compte_achat", "TEXT NOT NULL DEFAULT ''")
    _colonne(conn, "gc_tiers", "compte_auxiliaire", "TEXT NOT NULL DEFAULT ''")
    for code, col, ded in (("N", "445713", "445660"), ("I", "445712", "445660"), ("R", "445711", "445660"),
                           ("UE", "", ""), ("EX", "", "")):
        conn.execute("UPDATE gc_tva SET compte_collecte=?, compte_deductible=? WHERE code=? AND compte_collecte=''",
                     (col, ded, code))
    for code, v, a in (("ETQ", "701000", ""), ("SLV", "701000", ""), ("PAP", "", "601000"), ("FIL", "", "601000"),
                       ("ENC", "", "602000"), ("PREST", "706000", "604000")):
        conn.execute("UPDATE gc_familles SET compte_vente=?, compte_achat=? WHERE code=? AND compte_vente='' AND compte_achat=''",
                     (v, a, code))
    conn.commit()

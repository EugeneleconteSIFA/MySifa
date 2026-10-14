"""Nouvel ERP — « 20-Bases » de RVGI et regroupement de l'outillage.

Outillage (réponse d'Eugène, 14/10/2026) : RVGI range les outils en
découpes, cylindres et clichés ; MySifa en natures (`outil_types`).
Correspondance : découpe = plaque ; cylindre = magnétique, pelicut,
contre-partie ; cliché = cliché. Sérigraphie, porte-lames et dorures ne
servent pas. `outil_types.groupe` porte ce regroupement (réglable), et la
nature « pelicut » est ajoutée. Elle n'est reliée à aucun code opération : la
saisie atelier n'en est pas changée.

Bases de l'ERP : pays (avec appartenance à l'UE), devises, banques de la
société (compte comptable par banque), types de contacts, gammes de
produits, libellés automatiques (textes imprimés sur les pièces), familles
de clients et de fournisseurs.
"""

NOM = "gc_bases"
DEPEND = ["gc_socle", "gc_fiches_rvgi", "gc_reglements"]

PAYS = [("FR", "France", 1), ("DE", "Allemagne", 1), ("BE", "Belgique", 1), ("ES", "Espagne", 1), ("IT", "Italie", 1),
        ("NL", "Pays-Bas", 1), ("LU", "Luxembourg", 1), ("PT", "Portugal", 1), ("AT", "Autriche", 1), ("IE", "Irlande", 1),
        ("PL", "Pologne", 1), ("GB", "Royaume-Uni", 0), ("CH", "Suisse", 0), ("US", "États-Unis", 0)]
DEVISES = [("EUR", "Euro", "€"), ("USD", "Dollar américain", "$"), ("GBP", "Livre sterling", "£"), ("CHF", "Franc suisse", "CHF")]
TYPES_CONTACT = ["Achat", "Administratif", "Comptabilité", "Direction", "Qualité", "Logistique", "Production", "Marketing"]


def _col(conn, table, col, decl):
    if col not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def _tables(conn):
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def appliquer(conn):
    # ── Outillage ────────────────────────────────────────────────────
    if "outil_types" in _tables(conn):
        _col(conn, "outil_types", "groupe", "TEXT NOT NULL DEFAULT ''")
        conn.execute(
            """INSERT OR IGNORE INTO outil_types (cle, label, label_pluriel, ordre, actif, created_at)
               VALUES ('pelicut', 'Pelicut', 'Pelicuts', 35, 1, datetime('now','localtime'))""")
        for cle, groupe in (("plaque", "Découpes"), ("contre_partie", "Cylindres"), ("magnetique", "Cylindres"),
                            ("pelicut", "Cylindres"), ("cliche", "Clichés")):
            conn.execute("UPDATE outil_types SET groupe=? WHERE cle=? AND groupe=''", (groupe, cle))

    # ── Bases ────────────────────────────────────────────────────────
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS gc_pays (
            code TEXT PRIMARY KEY, libelle TEXT NOT NULL, ue INTEGER NOT NULL DEFAULT 0,
            actif INTEGER NOT NULL DEFAULT 1, rang INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS gc_devises (
            code TEXT PRIMARY KEY, libelle TEXT NOT NULL, symbole TEXT NOT NULL DEFAULT '',
            actif INTEGER NOT NULL DEFAULT 1, rang INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS gc_banques (
            code TEXT PRIMARY KEY, libelle TEXT NOT NULL, iban TEXT NOT NULL DEFAULT '', bic TEXT NOT NULL DEFAULT '',
            compte TEXT NOT NULL DEFAULT '', journal TEXT NOT NULL DEFAULT '',
            actif INTEGER NOT NULL DEFAULT 1, rang INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS gc_types_contact (
            code TEXT PRIMARY KEY, libelle TEXT NOT NULL, actif INTEGER NOT NULL DEFAULT 1, rang INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS gc_gammes (
            code TEXT PRIMARY KEY, libelle TEXT NOT NULL, actif INTEGER NOT NULL DEFAULT 1, rang INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS gc_textes (
            code TEXT PRIMARY KEY, libelle TEXT NOT NULL, texte TEXT NOT NULL DEFAULT '',
            actif INTEGER NOT NULL DEFAULT 1, rang INTEGER NOT NULL DEFAULT 0);
        """
    )
    for i, (code, lib, ue) in enumerate(PAYS, start=1):
        conn.execute("INSERT OR IGNORE INTO gc_pays (code, libelle, ue, rang) VALUES (?,?,?,?)", (code, lib, ue, i))
    for i, (code, lib, sym) in enumerate(DEVISES, start=1):
        conn.execute("INSERT OR IGNORE INTO gc_devises (code, libelle, symbole, rang) VALUES (?,?,?,?)", (code, lib, sym, i))
    for i, lib in enumerate(TYPES_CONTACT, start=1):
        code = lib.upper().replace("É", "E")[:4]
        conn.execute("INSERT OR IGNORE INTO gc_types_contact (code, libelle, rang) VALUES (?,?,?)", (code, lib, i))
    conn.execute("INSERT OR IGNORE INTO gc_textes (code, libelle, texte, rang) VALUES ('STD', 'Texte standard', '', 1)")

    for col, decl in (("famille", "TEXT"), ("devise", "TEXT NOT NULL DEFAULT 'EUR'"), ("texte_devis", "TEXT"),
                      ("texte_arc", "TEXT"), ("texte_bl", "TEXT"), ("texte_facture", "TEXT")):
        _col(conn, "gc_tiers", col, decl)
    _col(conn, "gc_reglements", "banque", "TEXT")
    conn.commit()

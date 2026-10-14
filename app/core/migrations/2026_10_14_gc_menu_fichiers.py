"""Nouvel ERP — fichiers comme dans RVGI (menu Fichiers, capture du 14/10/2026).

- Prospects : un tiers peut être prospect (devis possibles) avant d'être client.
- Types de matières : les familles de nature « matière » reprennent la liste
  de RVGI. Valeurs de départ, modifiables dans Paramètres › Familles.
"""

NOM = "gc_menu_fichiers"
DEPEND = ["gc_socle"]

FAMILLES_MATIERES = [
    ("CPX", "Complexes"), ("GLA", "Glassines"), ("VEL", "Vélins"), ("COU", "Couchés"), ("THE", "Thermiques"),
    ("SYN", "Synthétiques"), ("ADH", "Adhésifs"), ("ENC", "Encres"), ("CLI", "Clichés"), ("MAN", "Mandrins"),
    ("EMB", "Emballage"), ("DIV", "Divers"), ("BOI", "Boîtes"), ("CAR", "Cartons"), ("PAL", "Palettes"),
    ("PMA", "Pièces machines"),
]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gc_tiers)").fetchall()}
    if "est_prospect" not in cols:
        conn.execute("ALTER TABLE gc_tiers ADD COLUMN est_prospect INTEGER NOT NULL DEFAULT 0")
    for i, (code, lib) in enumerate(FAMILLES_MATIERES, start=1):
        conn.execute("INSERT OR IGNORE INTO gc_familles (code, libelle, nature, rang) VALUES (?, ?, 'mp', ?)",
                     (code, lib, 100 + i))
    # Les deux familles matière de départ (gc_socle) font doublon avec les types
    # RVGI : désactivées si aucun article ne les utilise. « ENC » est gardée.
    for code in ("PAP", "FIL"):
        if not conn.execute("SELECT 1 FROM gc_articles WHERE famille=? AND origine!='demo'", (code,)).fetchone():
            conn.execute("UPDATE gc_familles SET actif=0 WHERE code=?", (code,))
    conn.execute("UPDATE gc_familles SET libelle='Encres' WHERE code='ENC' AND libelle='Encres et vernis'")
    conn.commit()

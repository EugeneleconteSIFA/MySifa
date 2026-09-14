"""
MyQualité › FSC — registre des approvisionnements de chaîne de contrôle.

Ce que l'audit CoC demande (FSC-STD-40-004 V3-1) : pour chaque entrée de
matière d'origine forestière, le fournisseur et son certificat, l'allégation
portée par le BL ET par la facture, et la preuve que les deux concordent.
Aujourd'hui c'est un classeur Excel ; ici, c'est une table alimentée par RVGI.

Trois choix de structure, et leurs raisons.

1. **La ligne est FIGÉE à l'import.** Le fournisseur, la désignation et la
   quantité sont recopiés depuis le miroir RVGI au moment où la ligne entre au
   registre, jamais relus ensuite. Un article renommé dans l'ERP en novembre ne
   doit pas réécrire une réception de mars : l'auditeur lit ce qui était vrai le
   jour de la réception. `lif_id` porte l'unicité — une resynchro n'ajoute que
   du neuf.

2. **Le verdict du certificat est figé lui aussi**, comme sur `pf_receptions` et
   `stock_receptions` : `certificat_statut` est arrêté à la date du BL par
   `app/services/fsc_certificat.py`. Un renouvellement ultérieur ne réécrit pas
   l'histoire d'une livraison passée, une expiration ultérieure ne la condamne
   pas.

3. **Rien ne se supprime, tout se corrige et se trace.** `fsc_journal` garde
   l'avant et l'après de chaque champ modifié, avec qui et quand. Une saisie de
   registre modifiable sans trace est une faiblesse en audit.

`fsc_parametre` porte la date d'entrée dans la chaîne de contrôle : vide par
défaut, et c'est voulu — rien ne s'importe tant que personne ne l'a choisie.
"""

NOM = "fsc_registre_approvisionnements"
DEPEND = ["qualite_fsc_controles_lecture_certificats"]


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fsc_reception (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            -- Origine RVGI, figée à l'import
            lif_id                  INTEGER NOT NULL UNIQUE,
            cde_numero              INTEGER,
            cde_ligne               INTEGER,
            date_reception          TEXT    NOT NULL,
            date_saisie_rvgi        TEXT,
            num_bl                  TEXT,
            numfou                  INTEGER,
            fournisseur_rvgi        TEXT,
            fournisseur_id          INTEGER REFERENCES fournisseurs_fsc(id),
            code1                   TEXT,
            code2                   TEXT,
            code_matiere            TEXT,
            type_code               INTEGER,
            type_matiere            TEXT,
            origine_forestiere      INTEGER NOT NULL DEFAULT 1,
            designation             TEXT,
            libelle_matiere         TEXT,
            ref_fournisseur         TEXT,
            laize_mm                REAL,
            quantite_ml             REAL,
            quantite_m2             REAL,
            piece_facture_rvgi      INTEGER,
            ligne_facture_rvgi      INTEGER,
            reception_id            INTEGER,
            -- Saisie du contrôle à réception
            num_facture_fournisseur TEXT,
            allegation_bl           TEXT,
            allegation_facture      TEXT,
            pourcentage             REAL,
            code_certificat_present INTEGER,
            etiquette_posee         TEXT,
            observations            TEXT    NOT NULL DEFAULT '',
            -- Certificat du fournisseur, figé à la date du BL
            code_certificat_attendu TEXT,
            licence_attendue        TEXT,
            certificat_expiration   TEXT,
            certificat_statut       TEXT,
            -- Verdict
            eligible                TEXT    NOT NULL DEFAULT 'a_verifier',
            controle_par            TEXT,
            controle_le             TEXT,
            importe_le              TEXT    NOT NULL,
            importe_par             TEXT,
            modifie_le              TEXT
        )
        """
    )
    for sql in (
        "CREATE INDEX IF NOT EXISTS idx_fsc_rec_date ON fsc_reception(date_reception)",
        "CREATE INDEX IF NOT EXISTS idx_fsc_rec_four ON fsc_reception(fournisseur_id)",
        "CREATE INDEX IF NOT EXISTS idx_fsc_rec_elig ON fsc_reception(eligible)",
        "CREATE INDEX IF NOT EXISTS idx_fsc_rec_bl   ON fsc_reception(numfou, num_bl)",
    ):
        conn.execute(sql)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fsc_journal (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            table_cible      TEXT    NOT NULL,
            ligne_id         INTEGER NOT NULL,
            champ            TEXT    NOT NULL,
            ancienne_valeur  TEXT,
            nouvelle_valeur  TEXT,
            utilisateur      TEXT,
            horodatage       TEXT    NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_fsc_journal_ligne "
        "ON fsc_journal(table_cible, ligne_id, horodatage)"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fsc_parametre (
            cle         TEXT PRIMARY KEY,
            valeur      TEXT,
            modifie_le  TEXT,
            modifie_par TEXT
        )
        """
    )
    # Seed idempotent : la clé existe, sa valeur reste vide jusqu'à ce qu'un
    # humain choisisse le jour de bascule.
    conn.execute(
        "INSERT OR IGNORE INTO fsc_parametre (cle, valeur, modifie_le) VALUES (?, ?, ?)",
        ("registre_depuis", "", None),
    )
    conn.commit()
    print("[MySifa] migration %s : registre des approvisionnements FSC prêt." % NOM)

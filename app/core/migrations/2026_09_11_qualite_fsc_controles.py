"""
MyQualité — section FSC : contrôle des certificats fournisseurs sur la base FSC,
et lecture automatique des certificats déposés.

Deux besoins que le schéma ne couvrait pas.

1. LA PREUVE DU CONTRÔLE. L'auditeur CoC demande les « preuves de contrôle des
   certificats fournisseurs sur la base FSC ». `fournisseurs_fsc` porte une
   licence et une date d'expiration, mais rien ne dit qui les a vérifiées, quand,
   ni ce que la base publique affichait ce jour-là. `qualite_fsc_controles`
   garde une ligne par contrôle — jamais écrasée : un contrôle de mars reste
   opposable en octobre même si le certificat a été renouvelé entre-temps.
   Chaque contrôle fixe aussi les catégories (claims) que le fournisseur a le
   droit de livrer : c'est la seule source validée de ces catégories.

2. CE QUE DIT LE CERTIFICAT. Les certificats FSC déposés dans Ressources
   fournisseurs listent souvent, en annexe, la licence, la date d'expiration et
   les claims couverts. Les colonnes `fsc_*` de `qualite_fournisseur_certificats`
   gardent cette lecture (motifs ou IA) comme PROPOSITION : elle pré-remplit le
   contrôle, elle ne vaut jamais validation.

Rejouable : CREATE TABLE IF NOT EXISTS, test de présence avant chaque ALTER.
"""

NOM = "qualite_fsc_controles_lecture_certificats"


_COLONNES_CERTIFICAT = [
    # Quand la lecture a eu lieu, et comment : motifs | ia | aucune
    ("fsc_lecture_le", "TEXT"),
    ("fsc_lecture_methode", "TEXT"),
    ("fsc_lecture_modele", "TEXT"),
    # Ce qui a été lu. Rien n'est recopié ailleurs sans validation humaine.
    ("fsc_licence_lue", "TEXT"),
    ("fsc_certificat_lu", "TEXT"),
    ("fsc_expiration_lue", "TEXT"),
    # JSON : [{"code": "fsc_mix", "extrait": "...", "page": 2}]
    ("fsc_claims_lus", "TEXT"),
    # Ce qui empêche de conclure (« le certificat renvoie à la base FSC »…)
    ("fsc_lecture_note", "TEXT"),
]


def appliquer(conn):
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS qualite_fsc_controles (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            fournisseur_id         INTEGER NOT NULL REFERENCES fournisseurs_fsc(id) ON DELETE CASCADE,
            date_controle          TEXT    NOT NULL,
            statut_base            TEXT    NOT NULL,
            licence                TEXT,
            date_expiration_lue    TEXT,
            claims                 TEXT    NOT NULL DEFAULT '[]',
            source                 TEXT    NOT NULL DEFAULT 'base_fsc',
            certificat_id          INTEGER REFERENCES qualite_fournisseur_certificats(id) ON DELETE SET NULL,
            note                   TEXT    NOT NULL DEFAULT '',
            justificatif_filename  TEXT,
            justificatif_original  TEXT,
            justificatif_mime      TEXT,
            fiche_maj              INTEGER NOT NULL DEFAULT 0,
            ancienne_expiration    TEXT,
            created_at             TEXT    NOT NULL,
            created_by             INTEGER,
            created_by_nom         TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_qfsc_ctrl_four "
        "ON qualite_fsc_controles(fournisseur_id, date_controle)"
    )

    ajoutees = 0
    if "qualite_fournisseur_certificats" in tables:
        cols = {
            r[1] for r in conn.execute(
                "PRAGMA table_info(qualite_fournisseur_certificats)"
            ).fetchall()
        }
        for nom, typ in _COLONNES_CERTIFICAT:
            if nom not in cols:
                conn.execute(
                    f"ALTER TABLE qualite_fournisseur_certificats ADD COLUMN {nom} {typ}"
                )
                ajoutees += 1
    conn.commit()
    print(
        f"[MySifa] migration {NOM} : table qualite_fsc_controles prête, "
        f"{ajoutees} colonne(s) de lecture ajoutée(s) aux certificats."
    )

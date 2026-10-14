"""Nouvel ERP (erp.mysifa.com) — socle du modèle de gestion commerciale.

Préfixe `gc_` : distinct des tables `erp_*`, qui décrivent le miroir RVGI.
Feuille de route et principes : docs/erp/ROADMAP.md. Rappel des choix
structurants, à ne pas défaire sans décision :

- Montants en **centimes entiers**. Quantités en **millièmes entiers**
  (`*_milli`) : 1 étiquette = 1000, 2,5 kg = 2500. Taux en **points de base**
  (`*_bp`) : 20 % = 2000. Aucun REAL pour un montant, une quantité ou un taux.
- Un prix s'entend pour `base_prix` unités (1, 100, 1000 : l'étiquette se vend
  au mille). Montant de ligne = quantité × prix / base, arrondi au centime.
- Toutes les pièces, ventes comme achats, vivent dans `gc_pieces` ; leur type
  dit ce qu'elles sont. Une ligne connaît sa ligne amont (`ligne_amont_id`) :
  c'est de là que se déduisent reliquats, facturable et pièces liées. Pas de
  numéro recopié.
- Le stock est un journal (`gc_mouvements`), jamais un compteur.
- `origine` / `origine_ref` sur les tables métier : la reprise RVGI y posera
  ses identifiants sans collision.
"""

NOM = "gc_socle"


def appliquer(conn):
    conn.executescript(
        """
        -- ── Société (une ligne) ────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS gc_societe (
            id                  INTEGER PRIMARY KEY CHECK (id = 1),
            raison_sociale      TEXT NOT NULL DEFAULT '',
            forme_juridique     TEXT NOT NULL DEFAULT '',
            capital_cents       INTEGER,
            siret               TEXT NOT NULL DEFAULT '',
            rcs                 TEXT NOT NULL DEFAULT '',
            tva_intra           TEXT NOT NULL DEFAULT '',
            ape                 TEXT NOT NULL DEFAULT '',
            adresse1            TEXT NOT NULL DEFAULT '',
            adresse2            TEXT NOT NULL DEFAULT '',
            code_postal         TEXT NOT NULL DEFAULT '',
            ville               TEXT NOT NULL DEFAULT '',
            pays                TEXT NOT NULL DEFAULT 'FR',
            telephone           TEXT NOT NULL DEFAULT '',
            email               TEXT NOT NULL DEFAULT '',
            iban                TEXT NOT NULL DEFAULT '',
            bic                 TEXT NOT NULL DEFAULT '',
            penalites_retard    TEXT NOT NULL DEFAULT '',
            modifie_le          TEXT
        );

        -- ── Référentiels ───────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS gc_tva (
            code        TEXT PRIMARY KEY,
            libelle     TEXT NOT NULL,
            taux_bp     INTEGER NOT NULL,
            mention     TEXT NOT NULL DEFAULT '',     -- ex. autoliquidation, exonération
            actif       INTEGER NOT NULL DEFAULT 1,
            rang        INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS gc_unites (
            code        TEXT PRIMARY KEY,
            libelle     TEXT NOT NULL,
            decimales   INTEGER NOT NULL DEFAULT 0,  -- décimales saisissables (0 à 3)
            actif       INTEGER NOT NULL DEFAULT 1,
            rang        INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS gc_conditions_paiement (
            code            TEXT PRIMARY KEY,
            libelle         TEXT NOT NULL,
            jours           INTEGER NOT NULL DEFAULT 0,
            fin_de_mois     INTEGER NOT NULL DEFAULT 0,
            jour_du_mois    INTEGER NOT NULL DEFAULT 0,  -- 0 = aucun ; sinon le N du mois suivant l'échéance
            actif           INTEGER NOT NULL DEFAULT 1,
            rang            INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS gc_modes_paiement (
            code        TEXT PRIMARY KEY,
            libelle     TEXT NOT NULL,
            actif       INTEGER NOT NULL DEFAULT 1,
            rang        INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS gc_depots (
            code        TEXT PRIMARY KEY,
            libelle     TEXT NOT NULL,
            actif       INTEGER NOT NULL DEFAULT 1,
            rang        INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS gc_familles (
            code        TEXT PRIMARY KEY,
            libelle     TEXT NOT NULL,
            nature      TEXT NOT NULL DEFAULT 'pf',   -- pf | mp | service
            actif       INTEGER NOT NULL DEFAULT 1,
            rang        INTEGER NOT NULL DEFAULT 0
        );
        -- Numérotation : un compteur par type de pièce. Le numéro est pris dans
        -- la transaction qui valide la pièce — jamais de trou sur une facture.
        CREATE TABLE IF NOT EXISTS gc_sequences (
            code        TEXT PRIMARY KEY,             -- = type de pièce
            libelle     TEXT NOT NULL,
            format      TEXT NOT NULL,                -- ex. 'FA{AA}{N:05}'
            prochain    INTEGER NOT NULL DEFAULT 1,
            annuel      INTEGER NOT NULL DEFAULT 1,   -- compteur remis à 1 chaque année
            annee       INTEGER NOT NULL DEFAULT 0
        );

        -- ── Tiers ──────────────────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS gc_tiers (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            code                TEXT NOT NULL UNIQUE,
            est_client          INTEGER NOT NULL DEFAULT 0,
            est_fournisseur     INTEGER NOT NULL DEFAULT 0,
            raison_sociale      TEXT NOT NULL,
            siret               TEXT NOT NULL DEFAULT '',
            tva_intra           TEXT NOT NULL DEFAULT '',
            email               TEXT NOT NULL DEFAULT '',
            email_facturation   TEXT NOT NULL DEFAULT '',
            telephone           TEXT NOT NULL DEFAULT '',
            condition_paiement  TEXT REFERENCES gc_conditions_paiement(code),
            mode_paiement       TEXT REFERENCES gc_modes_paiement(code),
            tva_code            TEXT REFERENCES gc_tva(code),  -- régime : NULL = taux de l'article
            remise_bp           INTEGER NOT NULL DEFAULT 0,
            encours_max_cents   INTEGER,
            bloque              INTEGER NOT NULL DEFAULT 0,
            notes               TEXT NOT NULL DEFAULT '',
            actif               INTEGER NOT NULL DEFAULT 1,
            origine             TEXT NOT NULL DEFAULT 'erp',
            origine_ref         TEXT,
            cree_le             TEXT NOT NULL,
            modifie_le          TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_gc_tiers_client ON gc_tiers(est_client);
        CREATE INDEX IF NOT EXISTS idx_gc_tiers_fourn ON gc_tiers(est_fournisseur);

        CREATE TABLE IF NOT EXISTS gc_tiers_adresses (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tiers_id        INTEGER NOT NULL REFERENCES gc_tiers(id),
            type            TEXT NOT NULL,            -- facturation | livraison
            libelle         TEXT NOT NULL DEFAULT '',
            adresse1        TEXT NOT NULL DEFAULT '',
            adresse2        TEXT NOT NULL DEFAULT '',
            code_postal     TEXT NOT NULL DEFAULT '',
            ville           TEXT NOT NULL DEFAULT '',
            pays            TEXT NOT NULL DEFAULT 'FR',
            par_defaut      INTEGER NOT NULL DEFAULT 0,
            actif           INTEGER NOT NULL DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_gc_adr_tiers ON gc_tiers_adresses(tiers_id);

        CREATE TABLE IF NOT EXISTS gc_tiers_contacts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            tiers_id        INTEGER NOT NULL REFERENCES gc_tiers(id),
            nom             TEXT NOT NULL,
            fonction        TEXT NOT NULL DEFAULT '',
            email           TEXT NOT NULL DEFAULT '',
            telephone       TEXT NOT NULL DEFAULT '',
            actif           INTEGER NOT NULL DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_gc_ct_tiers ON gc_tiers_contacts(tiers_id);

        -- ── Articles et tarifs ─────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS gc_articles (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            code                TEXT NOT NULL UNIQUE,
            libelle             TEXT NOT NULL,
            libelle_client      TEXT NOT NULL DEFAULT '',
            nature              TEXT NOT NULL,        -- pf | mp | service
            famille             TEXT REFERENCES gc_familles(code),
            unite               TEXT NOT NULL REFERENCES gc_unites(code),  -- unité de stock et de vente
            base_prix           INTEGER NOT NULL DEFAULT 1,               -- prix pour N unités
            prix_vente_cents    INTEGER,
            prix_achat_cents    INTEGER,
            tva_code            TEXT REFERENCES gc_tva(code),
            gere_stock          INTEGER NOT NULL DEFAULT 1,
            fournisseur_id      INTEGER REFERENCES gc_tiers(id),
            client_id           INTEGER REFERENCES gc_tiers(id),         -- article propre à un client
            notes               TEXT NOT NULL DEFAULT '',
            actif               INTEGER NOT NULL DEFAULT 1,
            origine             TEXT NOT NULL DEFAULT 'erp',
            origine_ref         TEXT,
            cree_le             TEXT NOT NULL,
            modifie_le          TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_gc_art_nature ON gc_articles(nature);

        -- Prix négocié : par client (vente) ou fournisseur (achat), par palier.
        CREATE TABLE IF NOT EXISTS gc_tarifs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id      INTEGER NOT NULL REFERENCES gc_articles(id),
            tiers_id        INTEGER REFERENCES gc_tiers(id),   -- NULL = tarif général
            sens            TEXT NOT NULL,                     -- vente | achat
            qte_min_milli   INTEGER NOT NULL DEFAULT 0,
            prix_cents      INTEGER NOT NULL,                  -- pour base_prix unités de l'article
            debut           TEXT,
            fin             TEXT,
            actif           INTEGER NOT NULL DEFAULT 1
        );
        CREATE INDEX IF NOT EXISTS idx_gc_tarif_art ON gc_tarifs(article_id, sens);

        -- ── Pièces (ventes et achats) ──────────────────────────────────
        -- type : devis | commande | bl | facture | avoir
        --        | cde_fournisseur | reception | facture_fournisseur
        -- statut : brouillon | valide | partiel | solde | annule
        CREATE TABLE IF NOT EXISTS gc_pieces (
            id                      INTEGER PRIMARY KEY AUTOINCREMENT,
            type                    TEXT NOT NULL,
            numero                  TEXT,                 -- NULL tant que brouillon
            statut                  TEXT NOT NULL DEFAULT 'brouillon',
            tiers_id                INTEGER NOT NULL REFERENCES gc_tiers(id),
            date_piece              TEXT NOT NULL,
            date_livraison          TEXT,
            date_validite           TEXT,                 -- devis
            ref_tiers               TEXT NOT NULL DEFAULT '',   -- réf. commande client / n° facture fournisseur
            adresse_facturation_id  INTEGER REFERENCES gc_tiers_adresses(id),
            adresse_livraison_id    INTEGER REFERENCES gc_tiers_adresses(id),
            condition_paiement      TEXT REFERENCES gc_conditions_paiement(code),
            mode_paiement           TEXT REFERENCES gc_modes_paiement(code),
            depot                   TEXT REFERENCES gc_depots(code),
            remise_bp               INTEGER NOT NULL DEFAULT 0,
            total_ht_cents          INTEGER NOT NULL DEFAULT 0,
            total_tva_cents         INTEGER NOT NULL DEFAULT 0,
            total_ttc_cents         INTEGER NOT NULL DEFAULT 0,
            piece_annulee_id        INTEGER REFERENCES gc_pieces(id),   -- avoir → facture
            notes                   TEXT NOT NULL DEFAULT '',
            notes_internes          TEXT NOT NULL DEFAULT '',
            origine                 TEXT NOT NULL DEFAULT 'erp',
            origine_ref             TEXT,
            cree_par                TEXT,
            cree_le                 TEXT NOT NULL,
            modifie_le              TEXT NOT NULL,
            valide_par              TEXT,
            valide_le               TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS ux_gc_piece_numero ON gc_pieces(type, numero) WHERE numero IS NOT NULL;
        CREATE INDEX IF NOT EXISTS idx_gc_piece_tiers ON gc_pieces(tiers_id);
        CREATE INDEX IF NOT EXISTS idx_gc_piece_type ON gc_pieces(type, statut);

        CREATE TABLE IF NOT EXISTS gc_pieces_lignes (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            piece_id            INTEGER NOT NULL REFERENCES gc_pieces(id),
            rang                INTEGER NOT NULL,
            article_id          INTEGER REFERENCES gc_articles(id),  -- NULL = ligne de texte libre
            libelle             TEXT NOT NULL DEFAULT '',
            quantite_milli      INTEGER NOT NULL DEFAULT 0,
            unite               TEXT REFERENCES gc_unites(code),
            base_prix           INTEGER NOT NULL DEFAULT 1,
            prix_cents          INTEGER NOT NULL DEFAULT 0,          -- pour base_prix unités
            remise_bp           INTEGER NOT NULL DEFAULT 0,
            tva_code            TEXT REFERENCES gc_tva(code),
            taux_tva_bp         INTEGER NOT NULL DEFAULT 0,          -- figé à l'enregistrement
            montant_ht_cents    INTEGER NOT NULL DEFAULT 0,
            date_livraison      TEXT,
            ligne_amont_id      INTEGER REFERENCES gc_pieces_lignes(id),
            solde               INTEGER NOT NULL DEFAULT 0,          -- reliquat abandonné
            notes               TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_gc_ligne_piece ON gc_pieces_lignes(piece_id, rang);
        CREATE INDEX IF NOT EXISTS idx_gc_ligne_amont ON gc_pieces_lignes(ligne_amont_id);

        -- Échéances d'une facture (client ou fournisseur).
        CREATE TABLE IF NOT EXISTS gc_echeances (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            piece_id        INTEGER NOT NULL REFERENCES gc_pieces(id),
            date_echeance   TEXT NOT NULL,
            montant_cents   INTEGER NOT NULL,
            regle_cents     INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_gc_ech_piece ON gc_echeances(piece_id);

        -- ── Stock : journal de mouvements ──────────────────────────────
        CREATE TABLE IF NOT EXISTS gc_mouvements (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date_mvt        TEXT NOT NULL,
            article_id      INTEGER NOT NULL REFERENCES gc_articles(id),
            depot           TEXT NOT NULL REFERENCES gc_depots(code),
            quantite_milli  INTEGER NOT NULL,                     -- signée : + entrée, − sortie
            type            TEXT NOT NULL,                        -- reception | livraison | production | consommation | inventaire | ajustement | transfert
            lot             TEXT NOT NULL DEFAULT '',
            piece_id        INTEGER REFERENCES gc_pieces(id),
            ligne_id        INTEGER REFERENCES gc_pieces_lignes(id),
            valeur_cents    INTEGER,
            commentaire     TEXT NOT NULL DEFAULT '',
            cree_par        TEXT,
            cree_le         TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_gc_mvt_article ON gc_mouvements(article_id, depot);
        CREATE INDEX IF NOT EXISTS idx_gc_mvt_piece ON gc_mouvements(piece_id);
        """
    )

    # Référentiels de départ : ce sont des réglages par défaut, modifiables
    # dans Paramètres de l'ERP. Seeds idempotents.
    conn.execute("INSERT OR IGNORE INTO gc_societe (id) VALUES (1)")
    conn.executemany(
        "INSERT OR IGNORE INTO gc_tva (code, libelle, taux_bp, mention, rang) VALUES (?,?,?,?,?)",
        [
            ("N", "Normal 20 %", 2000, "", 1),
            ("I", "Intermédiaire 10 %", 1000, "", 2),
            ("R", "Réduit 5,5 %", 550, "", 3),
            ("UE", "Livraison intracommunautaire", 0,
             "Exonération de TVA, article 262 ter I du CGI", 4),
            ("EX", "Export hors UE", 0, "Exonération de TVA, article 262 I du CGI", 5),
        ],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO gc_unites (code, libelle, decimales, rang) VALUES (?,?,?,?)",
        [
            ("U", "Unité", 0, 1),
            ("ETQ", "Étiquette", 0, 2),
            ("ML", "Mètre linéaire", 2, 3),
            ("M2", "Mètre carré", 3, 4),
            ("KG", "Kilogramme", 3, 5),
            ("BOB", "Bobine", 0, 6),
            ("H", "Heure", 2, 7),
            ("FORF", "Forfait", 0, 8),
        ],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO gc_conditions_paiement (code, libelle, jours, fin_de_mois, jour_du_mois, rang) VALUES (?,?,?,?,?,?)",
        [
            ("COMPTANT", "Comptant", 0, 0, 0, 1),
            ("30J", "30 jours date de facture", 30, 0, 0, 2),
            ("30FM", "30 jours fin de mois", 30, 1, 0, 3),
            ("45FM", "45 jours fin de mois", 45, 1, 0, 4),
            ("60J", "60 jours date de facture", 60, 0, 0, 5),
        ],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO gc_modes_paiement (code, libelle, rang) VALUES (?,?,?)",
        [("VIR", "Virement", 1), ("LCR", "LCR", 2), ("CHQ", "Chèque", 3),
         ("PRLV", "Prélèvement", 4), ("CB", "Carte bancaire", 5)],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO gc_depots (code, libelle, rang) VALUES (?,?,?)",
        [("PRINC", "Dépôt principal", 1)],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO gc_familles (code, libelle, nature, rang) VALUES (?,?,?,?)",
        [
            ("ETQ", "Étiquettes adhésives", "pf", 1),
            ("SLV", "Manchons", "pf", 2),
            ("PAP", "Papiers adhésifs", "mp", 3),
            ("FIL", "Films adhésifs", "mp", 4),
            ("ENC", "Encres et vernis", "mp", 5),
            ("PREST", "Prestations", "service", 6),
        ],
    )
    conn.executemany(
        "INSERT OR IGNORE INTO gc_sequences (code, libelle, format) VALUES (?,?,?)",
        [
            ("devis", "Devis", "DE{AA}{N:05}"),
            ("commande", "Commande client", "CO{AA}{N:05}"),
            ("bl", "Bon de livraison", "BL{AA}{N:05}"),
            ("facture", "Facture", "FA{AA}{N:05}"),
            ("avoir", "Avoir", "AV{AA}{N:05}"),
            ("cde_fournisseur", "Commande fournisseur", "CF{AA}{N:05}"),
            ("reception", "Réception", "RE{AA}{N:05}"),
            ("facture_fournisseur", "Facture fournisseur", "FF{AA}{N:05}"),
        ],
    )
    conn.commit()

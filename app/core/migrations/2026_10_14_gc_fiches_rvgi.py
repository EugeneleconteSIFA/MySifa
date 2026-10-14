"""Nouvel ERP — fiches client et produit complétées d'après RVGI (captures du 14/10/2026).

Client : code court (« code AN »), groupe (client parent), état, fax, site,
RCS, EAN, NIF, ADV attitré, trois catégories, langue, désignation imprimée
(interne ou client), BAT à chaque commande, fiche de conformité, mode de
facturation (une facture par BL, groupée, manuelle), factor, en compte,
escompte, franco, marges de devis, n° chez le client, commission.
Interlocuteurs : service, GSM, et les documents reçus automatiquement
(devis, ARC, BL, facture, relance). Adresses : type principale, raison
sociale, téléphone, e-mail, SIRET propres. Banques.

Produit : code 3, couleur, poids, sous-famille, gamme, cliché, EAN, unités
d'achat et de conditionnement, taxe écologique, code douane, prix de stock,
stock mini / maxi, zone, article de remplacement, références client 2 et 3.

Pièce : situation d'édition (`imprime_le`, `envoye_le`) et passage en
comptabilité (`comptabilise_le`).
"""

NOM = "gc_fiches_rvgi"
DEPEND = ["gc_socle", "gc_parite_rvgi"]


def _col(conn, table, col, decl):
    if col not in {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")


def appliquer(conn):
    T = "TEXT NOT NULL DEFAULT ''"
    for col, decl in (
        ("nom_court", T), ("groupe_id", "INTEGER"), ("etat", "TEXT NOT NULL DEFAULT 'normal'"), ("fax", T),
        ("site_web", T), ("rcs", T), ("ean", T), ("nif", T), ("adv_id", "INTEGER"), ("categorie1", T),
        ("categorie2", T), ("categorie3", T), ("langue", "TEXT NOT NULL DEFAULT 'fr'"),
        ("designation_docs", "TEXT NOT NULL DEFAULT 'interne'"), ("bat_chaque_cde", "INTEGER NOT NULL DEFAULT 0"),
        ("fiche_conformite", "INTEGER NOT NULL DEFAULT 0"), ("facturation_auto", "TEXT NOT NULL DEFAULT 'par_bl'"),
        ("factor", "INTEGER NOT NULL DEFAULT 0"), ("en_compte", "INTEGER NOT NULL DEFAULT 1"),
        ("escompte_bp", "INTEGER NOT NULL DEFAULT 0"), ("franco_cents", "INTEGER"),
        ("marge_brute_bp", "INTEGER"), ("marge_nette_bp", "INTEGER"), ("notre_no_fournisseur", T),
        ("commission_bp", "INTEGER NOT NULL DEFAULT 0"),
    ):
        _col(conn, "gc_tiers", col, decl)
    for col, decl in (("raison_sociale", T), ("telephone", T), ("gsm", T), ("email", T), ("siret", T)):
        _col(conn, "gc_tiers_adresses", col, decl)
    for col, decl in (("service", T), ("civilite", T), ("gsm", T),
                      ("envoi_devis", "INTEGER NOT NULL DEFAULT 0"), ("envoi_arc", "INTEGER NOT NULL DEFAULT 0"),
                      ("envoi_bl", "INTEGER NOT NULL DEFAULT 0"), ("envoi_facture", "INTEGER NOT NULL DEFAULT 0"),
                      ("envoi_relance", "INTEGER NOT NULL DEFAULT 0")):
        _col(conn, "gc_tiers_contacts", col, decl)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS gc_tiers_banques (
               id       INTEGER PRIMARY KEY AUTOINCREMENT,
               tiers_id INTEGER NOT NULL REFERENCES gc_tiers(id),
               nom      TEXT NOT NULL,
               ville    TEXT NOT NULL DEFAULT '',
               pays     TEXT NOT NULL DEFAULT 'FR',
               iban     TEXT NOT NULL DEFAULT '',
               bic      TEXT NOT NULL DEFAULT '',
               actif    INTEGER NOT NULL DEFAULT 1
           )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gc_banque_tiers ON gc_tiers_banques(tiers_id)")
    for col, decl in (
        ("code3", T), ("couleur", T), ("poids_g", "INTEGER"), ("sous_famille", T), ("gamme", T), ("cliche", T),
        ("ean", T), ("unite_achat", T), ("unite_conditionnement", T), ("taxe_eco_cents", "INTEGER"),
        ("code_douane", T), ("prix_stock_cents", "INTEGER"), ("stock_mini_milli", "INTEGER"),
        ("stock_maxi_milli", "INTEGER"), ("zone", T), ("remplacement_id", "INTEGER"),
        ("ref_client2", T), ("ref_client3", T),
    ):
        _col(conn, "gc_articles", col, decl)
    for col in ("imprime_le", "envoye_le", "comptabilise_le"):
        _col(conn, "gc_pieces", col, "TEXT")
    conn.commit()

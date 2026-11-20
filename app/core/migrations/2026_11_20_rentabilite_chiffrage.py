"""
Rentabilité — postes en euros des devis, et paramètres du verdict.

`devis_chiffrage` : une ligne par devis, les postes de la feuille Prix que le
socle ne lisait pas (coût matière, outil, emballage, transport, coût de
production, prix de vente, marge brute, coût horaire, taux machine…). Sans
eux, aucune marge ne se compare. Table à part plutôt que colonnes de `devis` :
les trois chemins d'écriture d'un devis (écran, agent, reprise) n'ont pas à
changer leur INSERT, et un chiffrage se relit depuis le fichier conservé.

`rent_parametres` : seuils du verdict et largeur des fourchettes, éditables à
l'écran. Seedés depuis `config.py` (325 €/h et 40 % par défaut, arbitrage du
20/11/2026) ; une valeur déjà modifiée n'est jamais écrasée.
"""

NOM = "rentabilite_chiffrage_parametres"
DEPEND = ["devis_extraction_ia_indicateurs"]

COLONNES_REELLES = (
    "prix_m2_corrige", "prix_m2_base",
    "cout_matiere", "cout_encre", "cout_cliche", "cout_outil", "cout_emballage",
    "cout_production", "cout_conditionnement", "cout_manutention", "cout_transport",
    "prix_revient", "remise", "surmarge", "surmarge_taux", "prix_vente",
    "marge_brute", "cout_horaire", "taux_horaire", "temps_total_mn", "metrage_total_ml",
)


def appliquer(conn):
    cols = ",\n             ".join(f"{c} REAL" for c in COLONNES_REELLES)
    conn.execute(
        f"""CREATE TABLE IF NOT EXISTS devis_chiffrage (
             devis_id     INTEGER PRIMARY KEY,
             num_matiere  TEXT,
             {cols},
             sources_json TEXT,
             erreurs_json TEXT,
             lu_at        TEXT
           )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rent_parametres (
             cle         TEXT PRIMARY KEY,
             valeur      TEXT NOT NULL,
             modifie_le  TEXT,
             modifie_par TEXT
           )"""
    )
    import config
    seeds = {
        "seuil_mb_pct": config.RENT_SEUIL_MB_PCT,
        "seuil_cout_horaire": config.RENT_SEUIL_COUT_HORAIRE,
        "fourchette_duree_pct": config.RENT_FOURCHETTE_DUREE_PCT,
        "fourchette_frontiere_mn": config.RENT_FOURCHETTE_FRONTIERE_MN,
        "fourchette_metrage_pct": config.RENT_FOURCHETTE_METRAGE_PCT,
        "fourchette_matiere_pct": config.RENT_FOURCHETTE_MATIERE_PCT,
        "ecart_croisement_pct": config.RENT_ECART_CROISEMENT_PCT,
        "tolerance_controle_pct": config.RENT_TOLERANCE_CONTROLE_PCT,
    }
    for cle, valeur in seeds.items():
        conn.execute(
            "INSERT OR IGNORE INTO rent_parametres (cle, valeur) VALUES (?, ?)",
            (cle, str(valeur)),
        )
    conn.commit()

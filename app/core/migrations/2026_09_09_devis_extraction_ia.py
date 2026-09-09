"""
Rentabilité — traçabilité de la lecture d'un devis, et indicateurs hors socle.

Deux besoins que la table `devis` ne couvrait pas.

1. D'OÙ VIENT CE CHIFFRE. Un devis lu par un modèle doit pouvoir se rejouer :
   quelle méthode a produit la valeur (parser à motifs, IA, saisie manuelle),
   quel modèle, quelle cellule pour chaque champ, et qui a validé. Sans ça, un
   écart de rentabilité constaté en novembre sur un devis de juin n'est plus
   arbitrable.

2. LE RESTE DU DEVIS. Le socle comparable devis/réel tient en treize colonnes
   (vitesse, temps, métrages, quantité, gâche…). Un devis en porte beaucoup
   plus — nombre de fronts, poses, prix au mille, bobines théoriques, temps de
   conditionnement — et chaque commercial n'en remplit pas les mêmes. Les
   mettre en colonnes obligerait à une migration par indicateur découvert :
   ils vont donc dans une table clé/valeur, indexée par devis.

Rejouable : test de présence avant chaque ALTER, CREATE TABLE IF NOT EXISTS.
"""

NOM = "devis_extraction_ia_indicateurs"


_COLONNES_DEVIS = [
    # Le second poste de calage du devis. Il existait déjà dans les classeurs
    # mais nulle part en base : la comparaison opposait donc le calage relevé
    # en atelier — qui inclut les changements de couleur et de cliché — au seul
    # calage outil. Sur un devis à 150 mn d'outil et 450 mn d'impression,
    # l'écart affiché était faux d'un facteur 4.
    ("temps_calage_impression_mn", "REAL DEFAULT 0"),
    ("metrage_calage_impression_ml", "REAL DEFAULT 0"),
    # Comment la valeur a été obtenue : regex | ia | mixte | manuel
    ("extraction_methode", "TEXT"),
    # Le modèle appelé, quand il l'a été. Un changement de modèle explique un
    # changement de lecture : sans la trace, on cherche un bug qui n'existe pas.
    ("extraction_modele", "TEXT"),
    # JSON : {champ: {valeur, source, confiance, origine, commentaire}}
    ("extraction_json", "TEXT"),
    # JSON : les alertes de cohérence au moment de la validation.
    ("coherence_json", "TEXT"),
    # Le fichier d'origine, conservé pour pouvoir rouvrir la source.
    ("fichier_chemin", "TEXT"),
    ("fichier_mime", "TEXT"),
    # Qui a validé l'écran, et quand. L'IA propose, un humain tranche.
    ("valide_par", "TEXT"),
    ("valide_at", "TEXT"),
]


def appliquer(conn):
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "devis" not in tables:
        # La table naît des migrations historiques ; si elle n'est pas là,
        # rien à reprendre — la migration reste rejouable pour plus tard.
        print("[MySifa] migration devis_extraction_ia_indicateurs : table devis absente, rien à faire.")
        return

    cols = {r[1] for r in conn.execute("PRAGMA table_info(devis)").fetchall()}
    ajoutees = 0
    for nom, typ in _COLONNES_DEVIS:
        if nom not in cols:
            conn.execute(f"ALTER TABLE devis ADD COLUMN {nom} {typ}")
            ajoutees += 1

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS devis_indicateurs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            devis_id      INTEGER NOT NULL,
            libelle       TEXT    NOT NULL,
            valeur_nombre REAL,
            valeur_texte  TEXT,
            unite         TEXT,
            source        TEXT,
            confiance     TEXT,
            origine       TEXT,
            cree_at       TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_devis_indicateurs_devis "
        "ON devis_indicateurs(devis_id)"
    )
    # Un même libellé ne se pose qu'une fois par devis : réimporter le même
    # fichier corrige la valeur au lieu d'empiler des doublons.
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_devis_indicateurs_unique "
        "ON devis_indicateurs(devis_id, libelle)"
    )

    # Les devis déjà en base ont été saisis ou lus par le parser d'origine :
    # les marquer évite de les confondre avec une lecture IA validée.
    repris = conn.execute(
        "UPDATE devis SET extraction_methode='historique' "
        "WHERE extraction_methode IS NULL OR extraction_methode=''"
    ).rowcount

    conn.commit()
    print(
        f"[MySifa] migration devis_extraction_ia_indicateurs : "
        f"{ajoutees} colonne(s) ajoutée(s), {repris} devis marqué(s) « historique »."
    )

"""
MyQualité — section FSC : la portée produit du certificat, à côté des allégations.

Le schéma ne portait qu'une dimension : `qualite_fsc_controles.claims`, les
allégations de sortie (FSC Mix, Recycled, Controlled Wood…), affichées sous le
libellé trompeur « Catégories FSC ». Il manquait la question que l'auditeur CoC
pose en premier devant la liste des fournisseurs : *ce certificat couvre-t-il ce
que nous lui achetons ?*

Cette question se lit sur la PORTÉE du certificat — les codes produit de
FSC-STD-40-004a, P7.8 Adhesive labels, P2.4 Specialty paper… — et nulle part
ailleurs. Un fournisseur peut être parfaitement valide en FSC Mix et ne pas
avoir les étiquettes adhésives dans sa portée : le certificat est bon, il ne
couvre simplement pas ce qu'on lui achète.

Trois colonnes et une table :

1. `qualite_fsc_controles.portees` — la portée constatée sur la base FSC au
   moment du contrôle, au même titre que `claims`. Figée comme lui : un contrôle
   de septembre reste opposable en octobre.
2. `qualite_fournisseur_certificats.fsc_portees_lues` — ce que la lecture du
   certificat a cru voir. PROPOSITION, jamais validation, exactement comme les
   autres colonnes `fsc_*_lue`.
3. `fournisseurs_fsc.fsc_portees_achetees` — ce que SIFA achète à ce
   fournisseur, en codes de la norme. C'est l'autre moitié de la comparaison.
4. `fsc_portee_categorie` — la correspondance entre les catégories matière
   internes (complexe, frontal, glassine…) et les codes de la norme. Elle sert à
   amorcer la colonne ci-dessus, et elle vit en base parce qu'elle décrit ce que
   SIFA achète, pas ce que dit le standard.

Ce que la migration ne fait PAS : deviner la portée d'un certificat. Aucune
valeur n'est écrite dans `portees` ni dans `fsc_portees_lues` — elles se
remplissent au contrôle, dossier FSC en main. Une portée inventée serait pire
que pas de portée du tout : elle passerait pour vérifiée.

Rejouable : test de présence avant chaque ALTER, CREATE TABLE IF NOT EXISTS,
seeds en INSERT OR IGNORE, et l'amorçage ne touche que les fiches encore vides.
"""

import json

NOM = "fsc_portee_produit_certificats"
DEPEND = ["qualite_fsc_controles_lecture_certificats"]


# Correspondance de départ entre les catégories matière internes et la
# classification FSC. Volontairement prudente : on amorce avec le code le plus
# précis dont on soit sûr, et la fiche reste éditable. Mieux vaut une
# correspondance à compléter qu'une correspondance à défaire.
_CATEGORIES = [
    # (catégorie interne, codes de portée, ce que la catégorie recouvre)
    ("complexe",      ["P2.4.13"], "Complexe autoadhésif — papier adhésif"),
    ("frontal",       ["P2.4"],    "Papier frontal — papier de spécialité"),
    ("glassine",      ["P2.4"],    "Support siliconé — papier de spécialité"),
    ("sous_traitant", ["P7.8"],    "Étiquettes adhésives imprimées"),
]


def appliquer(conn):
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    def _cols(table):
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}

    ajoutees = 0

    # 1. La portée constatée au contrôle.
    if "qualite_fsc_controles" in tables and "portees" not in _cols("qualite_fsc_controles"):
        conn.execute(
            "ALTER TABLE qualite_fsc_controles ADD COLUMN portees TEXT NOT NULL DEFAULT '[]'"
        )
        ajoutees += 1

    # 2. La portée lue sur le certificat déposé — proposition.
    if ("qualite_fournisseur_certificats" in tables
            and "fsc_portees_lues" not in _cols("qualite_fournisseur_certificats")):
        conn.execute(
            "ALTER TABLE qualite_fournisseur_certificats ADD COLUMN fsc_portees_lues TEXT"
        )
        ajoutees += 1

    # 3. Ce que SIFA achète à ce fournisseur.
    if "fournisseurs_fsc" in tables and "fsc_portees_achetees" not in _cols("fournisseurs_fsc"):
        conn.execute("ALTER TABLE fournisseurs_fsc ADD COLUMN fsc_portees_achetees TEXT")
        ajoutees += 1

    # 4. La correspondance catégorie interne → portée de la norme.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS fsc_portee_categorie (
            categorie  TEXT PRIMARY KEY,
            portees    TEXT NOT NULL DEFAULT '[]',
            libelle    TEXT NOT NULL DEFAULT ''
        )
        """
    )
    for categorie, portees, libelle in _CATEGORIES:
        conn.execute(
            "INSERT OR IGNORE INTO fsc_portee_categorie (categorie, portees, libelle) VALUES (?,?,?)",
            (categorie, json.dumps(portees), libelle),
        )

    # Amorçage des fiches fournisseurs encore vides, depuis leurs catégories
    # matière. Une fiche déjà renseignée n'est jamais retouchée : la saisie
    # humaine prime sur la déduction, y compris au deuxième passage.
    amorcees = 0
    if "fournisseurs_fsc" in tables and "fsc_portees_achetees" in _cols("fournisseurs_fsc"):
        correspondance = {}
        for r in conn.execute("SELECT categorie, portees FROM fsc_portee_categorie").fetchall():
            try:
                codes = json.loads(r[1] or "[]")
            except (ValueError, TypeError):
                codes = []
            correspondance[r[0]] = [c for c in codes if isinstance(c, str)]

        for r in conn.execute(
            """SELECT id, categories FROM fournisseurs_fsc
                WHERE COALESCE(fsc_portees_achetees,'') = ''
                  AND COALESCE(categories,'') <> ''"""
        ).fetchall():
            try:
                internes = json.loads(r[1] or "[]")
            except (ValueError, TypeError):
                internes = []
            codes = []
            for cat in internes if isinstance(internes, list) else []:
                for code in correspondance.get(cat, []):
                    if code not in codes:
                        codes.append(code)
            if codes:
                conn.execute(
                    "UPDATE fournisseurs_fsc SET fsc_portees_achetees=? WHERE id=?",
                    (json.dumps(codes), r[0]),
                )
                amorcees += 1

    conn.commit()
    print(
        f"[MySifa] migration {NOM} : {ajoutees} colonne(s) ajoutée(s), "
        f"{len(_CATEGORIES)} correspondance(s) de catégorie, "
        f"{amorcees} fiche(s) fournisseur amorcée(s)."
    )

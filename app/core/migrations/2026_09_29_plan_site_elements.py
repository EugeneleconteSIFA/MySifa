"""
Plan du site (MyStock › Plan entrepôt, Paramètres › Emplacements).

Le plan était une grille d'allées déduite des codes d'emplacement : aucune
notion de bâtiment, de rack, de zone au sol. Cette table décrit le site
lui-même — une ligne par élément dessiné — et le rattache aux emplacements
par `prefixe` : un rack de préfixe « A » porte tous les codes A111, A112…,
une zone de préfixe « Z0 » porte le code Z0.

Types :
  contour  polygone des bâtiments (points)
  limite   trait pointillé entre deux bâtiments (points)
  entree   flèche de sens d'entrée (points : départ, arrivée)
  batiment zone cliquable d'un bâtiment (points) — migration plan_site_batiments
  titre    nom de bâtiment, texte seul
  rack     rack de rangement
  sol      matière première au sol
  zone     zone Z0 / Z1
  allee    couloir (allée F)
  machine  machine
  divers   rangement divers
  locaux   bureaux, locaux

Coordonnées en points, dans le repère du plan PDF d'origine (le rendu calcule
son cadre à partir du contenu, l'origine n'a donc pas d'importance).

Le seed reprend le plan du rez-de-chaussée de SIFA ; `cle` le rend
rejouable (INSERT OR IGNORE), un élément créé depuis Paramètres a une
`cle` NULL.
"""

import json

NOM = "plan_site_elements"


_SEED = [
    # cle, type, libelle, sous_titre, x, y, w, h, vertical, prefixe, points
    ("contour_site", "contour", "", "", 0, 0, 0, 0, 0, "",
     [(32, 72), (269, 72), (269, 217), (632, 209), (572, 540), (439, 540),
      (439, 393), (363, 393), (363, 306), (277, 306), (277, 357), (32, 357)]),
    ("limite_b1_e2", "limite", "", "", 0, 0, 0, 0, 0, "", [(271, 218), (277, 306)]),
    ("limite_e2_e3", "limite", "", "", 0, 0, 0, 0, 0, "", [(439, 409), (596, 409)]),

    ("titre_b1", "titre", "BÂTIMENT 1", "Atelier · bureaux", 80, 130, 135, 28, 0, "", None),
    ("titre_e2", "titre", "ENTREPÔT 2", "", 490, 285, 100, 16, 0, "", None),
    ("titre_e3", "titre", "ENTREPÔT 3", "Stock divers", 460, 445, 110, 28, 0, "", None),

    ("locaux_bureaux", "locaux", "Bureaux", "", 36, 76, 229, 54, 0, "", None),
    ("locaux_vestiaires", "locaux", "Bureaux · vestiaires · réfectoire", "", 88, 307, 185, 47, 0, "", None),
    ("locaux_compacteur", "locaux", "Compacteur", "", 42, 271, 40, 63, 0, "", None),
    ("locaux_bureau_log", "locaux", "Bureau logistique", "", 368, 221, 58, 16, 0, "", None),

    ("machine_cohesio", "machine", "Parc machines Cohésio", "", 37, 162, 188, 47, 0, "", None),
    ("machine_dsi", "machine", "DSI", "", 89, 250, 28, 37, 0, "", None),

    ("zone_z1", "zone", "Z1", "sortie de production", 148, 212, 78, 33, 0, "Z1", None),
    ("zone_z0", "zone", "Z0", "expédition", 291, 246, 127, 44, 0, "Z0", None),

    ("divers_outils", "divers", "Outils cylindres", "", 36, 211, 14, 54, 1, "", None),
    ("divers_mandrins", "divers", "Mandrins bagues", "", 51, 252, 33, 17, 0, "", None),
    ("divers_cartons_1", "divers", "Cartons", "", 251, 186, 17, 52, 1, "", None),
    ("divers_cartons_2", "divers", "Cartons", "", 216, 286, 40, 17, 0, "", None),
    ("divers_echantillons", "divers", "Échantillons", "", 431, 217, 13, 34, 1, "", None),
    ("divers_nc", "divers", "Non-conformités (MP + PF)", "", 443, 513, 126, 22, 0, "", None),

    ("rack_o", "rack", "Rack O", "", 273, 221, 90, 16, 0, "O", None),
    ("rack_a", "rack", "Rack A", "", 451, 253, 168, 14, 0, "A", None),
    ("rack_b", "rack", "Rack B", "", 451, 268, 165, 14, 0, "B", None),
    ("rack_c", "rack", "Rack C", "", 449, 303, 161, 11, 0, "C", None),
    ("rack_d", "rack", "Rack D", "", 449, 315, 159, 11, 0, "D", None),
    ("rack_e", "rack", "Rack E", "", 449, 341, 154, 11, 0, "E", None),
    ("rack_n", "rack", "Rack N", "", 365, 338, 10, 50, 1, "N", None),
    ("rack_m", "rack", "Rack M", "", 388, 375, 45, 13, 0, "M", None),

    ("sol_e2_haut", "sol", "Matière première · sol", "", 451, 219, 175, 13, 0, "", None),
    ("sol_e2_milieu", "sol", "Matière première · sol", "", 449, 354, 152, 20, 0, "", None),
    ("sol_e2_bas", "sol", "Matière première · sol", "", 469, 391, 126, 16, 0, "", None),
    ("sol_rack_n", "sol", "Matière première sol", "", 377, 338, 56, 33, 0, "", None),

    ("allee_f", "allee", "Allée F · couloir", "", 470, 377, 125, 12, 0, "F", None),

    ("entree_1", "entree", "", "", 0, 0, 0, 0, 0, "", [(447, 243), (463, 243)]),
    ("entree_2", "entree", "", "", 0, 0, 0, 0, 0, "", [(447, 292), (463, 292)]),
    ("entree_3", "entree", "", "", 0, 0, 0, 0, 0, "", [(447, 334), (463, 334)]),
    ("entree_4", "entree", "", "", 0, 0, 0, 0, 0, "", [(451, 383), (467, 383)]),
]


def appliquer(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS plan_site_elements (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            cle         TEXT UNIQUE,
            type        TEXT    NOT NULL,
            libelle     TEXT    NOT NULL DEFAULT '',
            sous_titre  TEXT    NOT NULL DEFAULT '',
            x           REAL    NOT NULL DEFAULT 0,
            y           REAL    NOT NULL DEFAULT 0,
            w           REAL    NOT NULL DEFAULT 0,
            h           REAL    NOT NULL DEFAULT 0,
            vertical    INTEGER NOT NULL DEFAULT 0,
            prefixe     TEXT    NOT NULL DEFAULT '',
            points      TEXT,
            ordre       INTEGER NOT NULL DEFAULT 0,
            updated_at  TEXT,
            updated_by  TEXT
        )
        """
    )
    n = 0
    for i, (cle, typ, lib, st, x, y, w, h, vert, pre, pts) in enumerate(_SEED):
        cur = conn.execute(
            """INSERT OR IGNORE INTO plan_site_elements
               (cle, type, libelle, sous_titre, x, y, w, h, vertical, prefixe, points, ordre)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (cle, typ, lib, st, x, y, w, h, vert, pre,
             json.dumps([list(p) for p in pts]) if pts else None, i * 10),
        )
        n += cur.rowcount
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} élément(s) de plan seedé(s).")

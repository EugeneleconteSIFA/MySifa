"""
Zones de bâtiment du plan du site.

Le plan de `plan_site_elements` n'avait qu'un contour d'un seul tenant : rien
ne disait où finit le bâtiment 1 et où commence l'entrepôt 2. Un élément
`batiment` est un polygone : en vue site, c'est la zone qu'on clique pour
entrer dans le bâtiment ; en vue bâtiment, il cadre le zoom et range les
éléments dont le centre tombe dedans.

Les trois polygones du seed découpent le contour d'origine le long des deux
limites déjà dessinées (pointillés entre bâtiments).
"""

import json

NOM = "plan_site_batiments"
DEPEND = ["plan_site_elements"]


_SEED = [
    ("batiment_1", "Bâtiment 1", "Atelier · bureaux",
     [(32, 72), (269, 72), (269, 217), (271, 218), (277, 306), (277, 357), (32, 357)]),
    ("batiment_e2", "Entrepôt 2", "Racks A à E, M, N, O · matière première",
     [(271, 218), (632, 209), (596, 409), (439, 409), (439, 393), (363, 393),
      (363, 306), (277, 306)]),
    ("batiment_e3", "Entrepôt 3", "Stock divers · non-conformités",
     [(439, 409), (596, 409), (572, 540), (439, 540)]),
]


def appliquer(conn):
    n = 0
    for i, (cle, lib, st, pts) in enumerate(_SEED):
        cur = conn.execute(
            """INSERT OR IGNORE INTO plan_site_elements
               (cle, type, libelle, sous_titre, points, ordre)
               VALUES (?, 'batiment', ?, ?, ?, ?)""",
            (cle, lib, st, json.dumps([list(p) for p in pts]), 1000 + i * 10),
        )
        n += cur.rowcount
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} bâtiment(s) ajouté(s) au plan.")

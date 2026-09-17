"""Référentiel des encres : gamme Pantone complète et noms de couleur courants.

Le premier seed (`encres_couleurs`) ne portait que 59 références. Le relevé
des fiches techniques du 17/09/2026 en compte 269 désignations distinctes,
dont une centaine de références Pantone absentes du seed : la zone du BAT
restait violette pour la plupart d'entre elles.

Cette migration ajoute :

- la gamme Pantone Solid Coated (C) et Uncoated (U), 3 172 références,
  depuis `donnees/pantone_couleurs.json` (paquet npm `pantone-table`,
  licence MIT, texte de licence dans le fichier) ;
- les noms de couleur saisis en clair à l'atelier (ROSE, CORAIL, BLEU CLAIR…),
  que les noms simples du code ne couvraient pas.

Toujours `INSERT OR IGNORE` sur la clé : une teinte déjà corrigée dans
Paramètres n'est jamais écrasée. Les teintes restent des approximations écran.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime

NOM = "encres_pantone_complet"
DEPEND = ["encres_couleurs"]

# Chemin resolu a l'execution : le test des migrations exec() le source sans
# __file__, seul le chargement doit en dependre.
def _fichier() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "donnees", "pantone_couleurs.json")

# Noms en clair relevés dans les fiches techniques (clé canonique, libellé, teinte).
NOMS = [
    ("ROSE", "Rose", "#F395C7"),
    ("ROSE CLAIR", "Rose clair", "#F8C8DC"),
    ("FUSHIA", "Fuchsia (orthographe atelier)", "#D6006F"),
    ("FUCHSIA", "Fuchsia", "#D6006F"),
    ("MAUVE", "Mauve", "#B38FC4"),
    ("VIOLET", "Violet", "#7A3E9D"),
    ("VIOLET PASTEL", "Violet pastel", "#C5B4E3"),
    ("CORAIL", "Corail", "#FF7F61"),
    ("SAUMON", "Saumon", "#FFA38B"),
    ("TURQUOISE", "Turquoise", "#00B2A9"),
    ("BLEU CLAIR", "Bleu clair", "#6CACE4"),
    ("BLEU FONCE", "Bleu foncé", "#002D72"),
    ("BLEU CANARD", "Bleu canard", "#00758F"),
    ("VERT CLAIR", "Vert clair", "#8EDD65"),
    ("VERT POMME", "Vert pomme", "#7CC242"),
    ("GRIS CLAIR", "Gris clair", "#C8C9C7"),
    ("GRIS MOYEN", "Gris moyen", "#97999B"),
    ("GRIS FONCE", "Gris foncé", "#54585A"),
    ("GRIS BLEUTE", "Gris bleuté", "#7C878E"),
    ("GRIS METALIQUE", "Gris métallique", "#8A8D8F"),
    ("OR", "Or", "#B9975B"),
    ("ARGENT", "Argent", "#A2AAAD"),
]


# Trois teintes du premier seed etaient fausses. On ne corrige que les lignes
# encore intactes (jamais modifiees dans Parametres).
CORRECTIONS = [
    ("135 C", "#FFC845", "#FFC658"),
    ("206 C", "#A50034", "#CE0037"),
    ("7424 C", "#E0457B", "#E24585"),
]


def _libelle(code: str) -> str:
    base, suf = code[:-2], code[-1]
    return "Pantone " + " ".join(m if m.isdigit() else m.capitalize() for m in base.split()) + " " + suf


def appliquer(conn: sqlite3.Connection) -> None:
    quand = datetime.now().isoformat(timespec="seconds")
    lignes = []
    try:
        with open(_fichier(), encoding="utf-8") as fh:
            for cle, code, hx in json.load(fh)["couleurs"]:
                lignes.append((code, cle, _libelle(code), hx))
    except (OSError, ValueError, KeyError, NameError) as exc:
        print(f"[MySifa] migration {NOM} : fichier Pantone illisible ({exc}).")
    for cle, libelle, hx in NOMS:
        lignes.append((cle, cle, libelle, hx))

    for cle, ancien, nouveau in CORRECTIONS:
        conn.execute(
            "UPDATE encres_couleurs SET hex=? WHERE cle=? AND upper(hex)=? AND updated_by IS NULL",
            (nouveau, cle, ancien),
        )

    n = 0
    for code, cle, libelle, hx in lignes:
        cur = conn.execute(
            "INSERT OR IGNORE INTO encres_couleurs"
            " (code, cle, libelle, hex, actif, created_at) VALUES (?,?,?,?,1,?)",
            (code, cle, libelle, hx, quand),
        )
        n += cur.rowcount or 0
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} couleur(s) d'encre ajoutée(s).")

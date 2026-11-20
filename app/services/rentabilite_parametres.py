"""
SIFA — Paramètres de la rentabilité : seuils du verdict, largeur des fourchettes.

Une seule porte de lecture et d'écriture. Les valeurs vivent dans
`rent_parametres` (modifiables à l'écran) ; `config.py` ne fournit que le
défaut, utilisé tant que la table n'existe pas ou qu'une clé y manque.
"""
from datetime import datetime

import config

# clé → (libellé, unité, défaut, minimum, maximum)
PARAMETRES = {
    "seuil_mb_pct":            ("Seuil de marge brute", "%", config.RENT_SEUIL_MB_PCT, 0, 100),
    "seuil_cout_horaire":      ("Seuil de coût horaire", "€/h", config.RENT_SEUIL_COUT_HORAIRE, 0, 10000),
    "fourchette_duree_pct":    ("Fourchette sur la durée totale", "%", config.RENT_FOURCHETTE_DUREE_PCT, 0, 50),
    "fourchette_frontiere_mn": ("Fourchette sur le passage calage → production", "mn", config.RENT_FOURCHETTE_FRONTIERE_MN, 0, 240),
    "fourchette_metrage_pct":  ("Fourchette sur le métrage compteur", "%", config.RENT_FOURCHETTE_METRAGE_PCT, 0, 50),
    "fourchette_matiere_pct":  ("Fourchette sur la matière déstockée", "%", config.RENT_FOURCHETTE_MATIERE_PCT, 0, 50),
    "ecart_croisement_pct":    ("Écart toléré compteur / MyStock", "%", config.RENT_ECART_CROISEMENT_PCT, 0, 50),
    "tolerance_controle_pct":  ("Tolérance du contrôle des devis", "%", config.RENT_TOLERANCE_CONTROLE_PCT, 0, 50),
}


def _table(conn) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='rent_parametres'"
    ).fetchone())


def lire(conn) -> dict:
    """`{clé: valeur float}` pour toutes les clés connues."""
    valeurs = {cle: float(p[2]) for cle, p in PARAMETRES.items()}
    if not _table(conn):
        return valeurs
    for row in conn.execute("SELECT cle, valeur FROM rent_parametres").fetchall():
        if row[0] in valeurs:
            try:
                valeurs[row[0]] = float(row[1])
            except (TypeError, ValueError):
                pass
    return valeurs


def decrire(conn) -> list[dict]:
    """Pour l'écran : libellé, unité, valeur, bornes, auteur de la dernière modif."""
    valeurs = lire(conn)
    auteurs = {}
    if _table(conn):
        auteurs = {r[0]: (r[1], r[2]) for r in conn.execute(
            "SELECT cle, modifie_le, modifie_par FROM rent_parametres").fetchall()}
    return [
        {"cle": cle, "libelle": p[0], "unite": p[1], "valeur": valeurs[cle],
         "defaut": float(p[2]), "min": p[3], "max": p[4],
         "modifie_le": (auteurs.get(cle) or (None, None))[0],
         "modifie_par": (auteurs.get(cle) or (None, None))[1]}
        for cle, p in PARAMETRES.items()
    ]


def ecrire(conn, cle: str, valeur, auteur: str) -> float:
    """Valide puis enregistre. Lève ValueError avec un message affichable."""
    if cle not in PARAMETRES:
        raise ValueError(f"Paramètre inconnu : {cle}.")
    libelle, unite, _d, mini, maxi = PARAMETRES[cle]
    try:
        v = float(str(valeur).replace(",", "."))
    except (TypeError, ValueError):
        raise ValueError(f"{libelle} : nombre attendu.")
    if not (mini <= v <= maxi):
        raise ValueError(f"{libelle} invalide — valeur entre {mini} et {maxi} {unite}.")
    conn.execute(
        """INSERT INTO rent_parametres (cle, valeur, modifie_le, modifie_par)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(cle) DO UPDATE SET valeur=excluded.valeur,
             modifie_le=excluded.modifie_le, modifie_par=excluded.modifie_par""",
        (cle, str(v), datetime.now().isoformat(timespec="seconds"), auteur),
    )
    return v

"""
Contrainte transport sur le planning de production.

Un dossier dont l'expedition est deja reservee ne peut plus etre repousse
librement : la production doit etre finie avant que le camion se presente.
Les trois valeurs qui pilotent la regle (heure limite le jour de
l'enlevement, seuil de palettes a partir duquel la regle s'applique, marge
de duree accordee) vivent en base pour rester reglables depuis Parametres,
jamais en dur dans le code.

Meme forme que arret_seuils_params : une table cle/valeur, seedee avec les
valeurs decidees avec SIFA le 02/09/2026.
"""

NOM = "transport_planning_params"

SEED_PARAMS = [
    # Interrupteur general. Mis a 0, le planning se comporte exactement
    # comme avant : ni camion, ni marge, ni refus.
    ("actif", "1"),
    # Heure limite le jour de l'enlevement (heures decimales : 11.5 = 11h30).
    ("heure_limite", "11"),
    # Nombre de palettes A PARTIR DUQUEL la regle s'applique (>=).
    ("seuil_palettes", "6"),
    # Marge de duree de production accordee au dossier contraint, en %.
    ("marge_pct", "20"),
]


def appliquer(conn):
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS transport_planning_params (
            cle    TEXT PRIMARY KEY NOT NULL,
            valeur TEXT NOT NULL
        );
        """
    )
    for cle, valeur in SEED_PARAMS:
        conn.execute(
            "INSERT OR IGNORE INTO transport_planning_params (cle, valeur) VALUES (?,?)",
            (cle, valeur),
        )
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM transport_planning_params").fetchone()[0]
    print(f"[MySifa] migration transport_planning : {n} parametre(s) en place.")

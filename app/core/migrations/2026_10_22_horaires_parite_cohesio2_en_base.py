"""
Inscrit en base les horaires semaine paire / impaire de la Cohésio 2.

Jusqu'ici, ces horaires n'existaient qu'en dur dans le code (planning.py,
planning_page.py, settings_page.py) : la colonne `machines.horaires_parity`
était vide, et la fenêtre « Réglages » affichait la table du code comme si
elle était enregistrée. Une semaine sans horaire saisi à la main retombait
donc sur 5h–13h / 13h–20h sans que personne ne l'ait choisi (S44, 22/10/2026).

Le code ne lit plus que la base. Pour ne rien changer à l'affichage le jour
du déploiement, on recopie ici la table du code, telle quelle, sur la seule
machine qui en dépendait. Les horaires se règlent ensuite dans Réglages.
Une machine dont `horaires_parity` est déjà renseigné n'est pas touchée.
"""
import json

NOM = "horaires_parite_cohesio2_en_base"

# Table recopiée du code retiré (_PARITY_DEFAULTS["C2"]).
_PARITE_C2 = {
    "pair": {"week": {"s": 5.0, "e": 13.0}, "fri": {"s": 6.0, "e": 13.0}},
    "impair": {"week": {"s": 13.0, "e": 20.0}, "fri": {"s": 14.0, "e": 20.0}},
}


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(machines)").fetchall()}
    if "horaires_parity" not in cols:
        return
    cur = conn.execute(
        """UPDATE machines SET horaires_parity=?
            WHERE (horaires_parity IS NULL OR TRIM(horaires_parity)='')
              AND (code='C2' OR nom='Cohésio 2')""",
        (json.dumps(_PARITE_C2),),
    )
    conn.commit()
    print(f"[MySifa] migration {NOM} : {cur.rowcount} machine(s) reprise(s).")

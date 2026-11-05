"""
Part de la vitesse conducteur que représente la vitesse du devis, machine par
machine.

Le devis chiffre une vitesse moyenne, plus basse que celle que le conducteur
règle : la vitesse théorique comparée au réel est `vitesse devis / part`.
`machines.rent_part_vitesse_devis` porte cette part (0,8 = le devis vaut 80 %
de la vitesse conducteur). NULL = la valeur par défaut de `config.py`
(`DEVIS_VITESSE_PART_CONDUCTEUR`). Le réglage se fait depuis MyProd >
Rentabilité > Pilotage, à côté du suivi des devis à lier.

Aucune valeur posée : rien ne change tant que personne n'a réglé une machine.
Rejouable.
"""

NOM = "machines_part_vitesse_devis"


def appliquer(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "machines" not in tables:
        print(f"[MySifa] migration {NOM} : table machines absente, rien à faire.")
        return
    cols = {r[1] for r in conn.execute("PRAGMA table_info(machines)").fetchall()}
    if "rent_part_vitesse_devis" not in cols:
        conn.execute("ALTER TABLE machines ADD COLUMN rent_part_vitesse_devis REAL")
    conn.commit()

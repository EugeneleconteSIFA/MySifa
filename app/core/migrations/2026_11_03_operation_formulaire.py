"""
Codes opération : formulaire ouvert au clic (`operation_codes.formulaire`).

Un code peut, au poste, ouvrir un formulaire propre avant que la saisie ne
parte. Premier cas : « Opération de maintenance », qui fait choisir
l'intervention, la machine, la date et un commentaire, puis enregistre
l'opération dans MyMaintenance en même temps que la saisie de production.

Même principe que `outil_type` : c'est cet attribut, et non le numéro du
code, qui décide du comportement. Valeurs admises : OPERATION_FORMULAIRES
de config.py ; il se règle dans Paramètres › Opérations.

Seed SIFA : le code 93 (« Opération de maintenance », créé le 03/11/2026).
"""

NOM = "operation_codes_formulaire"

_SEED = {"93": "maintenance"}


def appliquer(conn):
    cols = {r[1] for r in conn.execute('PRAGMA table_info("operation_codes")').fetchall()}
    if not cols:
        return  # référentiel encore en JSON : rien à étendre
    if "formulaire" not in cols:
        conn.execute("ALTER TABLE operation_codes ADD COLUMN formulaire TEXT")
    n = 0
    for code, formulaire in _SEED.items():
        cur = conn.execute(
            "UPDATE operation_codes SET formulaire = ? WHERE code = ? AND COALESCE(formulaire, '') = ''",
            (formulaire, code),
        )
        n += cur.rowcount or 0
    conn.commit()
    print(f"[MySifa] migration {NOM} : colonne prête, {n} code(s) relié(s) à un formulaire.")

"""
Codes opération : intervention MyMaintenance préchoisie
(`operation_codes.maint_code`).

Un code dont `formulaire` vaut « maintenance » ouvre au poste la fenêtre
d'opération de maintenance. Jusqu'ici le conducteur y choisissait
l'intervention dans la liste, ce qui convient au code générique « Opération
de maintenance ». Mais un changement de couteaux bande est TOUJOURS la même
intervention : `maint_code` la désigne (clé de `maintenance_codes`), la
fenêtre s'ouvre dessus, et le conducteur peut encore en changer. Il se règle
dans Paramètres › Opérations.

Seed SIFA (décision du 17/11/2026) : les changements de couteaux et de
contre-couteaux, en bande et en rive, sont reliés à MyMaintenance, chacun à
l'intervention de la pièce d'usure correspondante. Le lien n'est posé que si
le code opération n'a pas déjà de formulaire ni d'intervention, et si
l'intervention existe bien dans MyMaintenance.
"""

NOM = "operation_codes_intervention_maintenance"
DEPEND = ["operation_codes_formulaire", "codes_maintenance_archivage"]

# code opération -> code d'intervention MyMaintenance
_SEED = {"82": "91", "83": "92", "84": "93", "85": "94"}


def appliquer(conn):
    cols = {r[1] for r in conn.execute('PRAGMA table_info("operation_codes")').fetchall()}
    if not cols:
        return  # référentiel encore en JSON : rien à étendre
    if "maint_code" not in cols:
        conn.execute("ALTER TABLE operation_codes ADD COLUMN maint_code TEXT")
    if "formulaire" not in cols:
        # DEPEND garantit l'ordre ; on ne fait que se protéger d'une base
        # où la colonne aurait été retirée à la main.
        conn.commit()
        return
    existe_maint = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='maintenance_codes'"
    ).fetchone()
    n = 0
    for code, maint in (_SEED.items() if existe_maint else ()):
        if not conn.execute(
            "SELECT 1 FROM maintenance_codes WHERE code = ? AND archived_at IS NULL", (maint,)
        ).fetchone():
            continue
        cur = conn.execute(
            """UPDATE operation_codes
                  SET formulaire = 'maintenance', maint_code = ?
                WHERE code = ?
                  AND COALESCE(formulaire, '') = ''
                  AND COALESCE(maint_code, '') = ''""",
            (maint, code),
        )
        n += cur.rowcount or 0
    conn.commit()
    print(f"[MySifa] migration {NOM} : colonne prête, {n} code(s) relié(s) à une intervention.")

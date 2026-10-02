"""
Fusion des variantes fournisseur provisoires restées en double.

La migration `mp_variantes_fournisseur` crée une variante provisoire par
fournisseur ayant un prix (libellé = désignation de la matière, sans
référence). La reprise d'inventaire renomme ensuite la fiche AVANT de créer les
variantes : la provisoire n'était plus reconnue, et la page matière montrait
deux fois le même fournisseur — « Kanzan · Thermique Eco » à côté de
« Kanzan · Thermique Eco 70 g/m² KP460 BPA free » (v1, 03/10/2026).

Pour chaque matière : une variante provisoire qui a une sœur complète chez le
même fournisseur lui passe son statut principal s'il le porte, puis est
désactivée. Le fournisseur ne change pas, donc le prix en vigueur non plus.
"""

NOM = "mp_variantes_fusion_provisoires"
DEPEND = ["reprise_inventaire_mp_2026_10_01"]

_PROVISOIRE = """(v.rvgi_code1 IS NULL AND v.ref_fournisseur IS NULL
                  AND (v.note LIKE 'Reprise des prix fournisseur%'
                       OR v.note LIKE 'Créée depuis un prix%'
                       OR v.note LIKE 'Créée au choix%'))"""


def appliquer(conn):
    provisoires = conn.execute(
        f"""SELECT v.id, v.matiere_id, v.fournisseur_id, v.principal FROM mp_variantes v
             WHERE v.actif = 1 AND v.fournisseur_id IS NOT NULL AND {_PROVISOIRE}"""
    ).fetchall()
    fusionnees = 0
    for pid, mid, fid, principal in provisoires:
        soeur = conn.execute(
            f"""SELECT v.id FROM mp_variantes v
                 WHERE v.matiere_id = ? AND v.fournisseur_id = ? AND v.actif = 1 AND v.id <> ?
                   AND NOT {_PROVISOIRE}
                 ORDER BY (v.rvgi_code1 IS NULL), v.id LIMIT 1""",
            (mid, fid, pid),
        ).fetchone()
        if not soeur:
            continue
        if principal:
            conn.execute("UPDATE mp_variantes SET principal = 0 WHERE id = ?", (pid,))
            conn.execute("UPDATE mp_variantes SET principal = 1 WHERE id = ?", (soeur[0],))
        conn.execute(
            """UPDATE mp_variantes SET actif = 0, note = COALESCE(note,'') || ' Fusionnée dans la variante ' || ?
                WHERE id = ?""",
            (soeur[0], pid),
        )
        fusionnees += 1
    conn.commit()
    print(f"[MySifa] migration {NOM} : {fusionnees} variante(s) provisoire(s) fusionnée(s).")

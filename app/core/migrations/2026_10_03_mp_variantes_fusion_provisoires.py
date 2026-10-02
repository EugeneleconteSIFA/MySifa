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


def appliquer(conn):
    from app.services.mp_variantes import fusionner_provisoires

    fusionnees = fusionner_provisoires(conn)
    conn.commit()
    print(f"[MySifa] migration {NOM} : {fusionnees} variante(s) provisoire(s) fusionnée(s).")

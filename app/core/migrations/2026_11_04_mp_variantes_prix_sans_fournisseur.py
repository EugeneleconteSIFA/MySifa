"""
Reprise des prix d'articles « Fournisseur non identifié » restés sans effet.

Jusqu'au 4 novembre 2026, le prix saisi sur un article sans fournisseur (les
articles repris de l'inventaire du 01/10/2026) n'était enregistré que sur
l'article : `_pousse_prix` excluait le fournisseur vide. Coûts matières, la
grille « Prix d'achat par fournisseur » et la valorisation restaient donc à
« à compléter » alors que la fiche montrait un prix (PET 120 µm, PP 60 µm,
glassine jaune double siliconée).

Le code est corrigé ; cette migration repousse les prix déjà saisis, par le
même chemin qu'une saisie (`definir_prix_article`) : historique des prix et
miroir de valorisation compris.

Rejouable : un prix déjà arrivé dans Coûts matières n'est pas repris.
"""

NOM = "mp_variantes_prix_sans_fournisseur"
DEPEND = ["mp_variantes_prix_achat"]


def appliquer(conn):
    from app.services import mp_variantes

    rows = conn.execute(
        """SELECT v.id, v.prix_achat FROM mp_variantes v
            WHERE v.actif = 1 AND v.fournisseur_id IS NULL AND v.prix_achat > 0
              AND NOT EXISTS (
                SELECT 1 FROM mp_matiere_prix p
                 WHERE p.matiere_id = v.matiere_id AND p.fournisseur_id IS NULL
                   AND ABS(COALESCE(p.prix, 0) - v.prix_achat) < 1e-9)"""
    ).fetchall()
    n = 0
    for r in rows:
        try:
            res = mp_variantes.definir_prix_article(
                conn, int(r[0]), float(r[1]), confirmer=True,
                user_name="Reprise prix articles sans fournisseur",
            )
        except Exception as e:  # une matière sans déclinaison ne bloque pas le démarrage
            print(f"[MySifa] migration {NOM} : article {r[0]} ignoré ({e}).")
            continue
        if res.get("pousse"):
            n += 1
    conn.commit()
    print(f"[MySifa] migration {NOM} : {n} prix d'article repris dans Coûts matières.")

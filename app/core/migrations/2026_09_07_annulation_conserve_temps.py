"""
Rend leurs minutes aux saisies neutralisees par une annulation de dossier.

Jusqu'ici, annuler un dossier posait `est_annule=1` sur toutes les saisies du
cycle (01, calage, production, arrets, appro). Elles restaient visibles mais
sortaient de toutes les lectures dossier : rentabilite, memoire produit
(`produit_series`), point de production.

Le metrage, lui, ne sortait pas. La trace « 90 - Annulation dossier » porte le
compteur de debut et le compteur de fin du cycle annule, elle n'est pas
annulee, et son metrage entre donc normalement dans les chiffres. Idem pour les
entrees Z1 declarees pendant le cycle : elles vivent dans le stock, pas dans
`production_data`, et rien ne les annulait.

Resultat : un metrage complet rapporte a un temps ampute, donc une vitesse
fausse par le haut. Cas constate en production le 07/09/2026 sur le dossier
9932376-377 (Cohesio 2, TURRET HS) : 46 668 m rapportes aux 272 min du cycle
survivant au lieu des 571 min reellement passees, soit 171 m/min affiches
contre 82 reels — au-dessus de toutes les series passees de la reference.

A partir d'ici : le temps passe et la matiere engagee sont reels et comptent,
qu'un dossier ait ete livre ou non. Seule la livraison n'a pas eu lieu, et
c'est le planning qui le dit (statut + motif). `annule_le`, `annule_par` et
`annule_motif` sont conserves : ils tracent le cycle sans rien retirer aux
chiffres, et MyProd > Saisies s'en sert pour marquer les lignes concernees.

La colonne `est_annule` n'est pas supprimee : les lectures la filtrent encore
et une base restauree depuis une sauvegarde anterieure doit rester lisible.
Elle n'est simplement plus jamais posee (voir `annuler_dossier`).

Les series produit des dossiers concernes sont rematerialisees dans la foulee :
sans cela, `produit_series` garderait le couple metrage/temps incoherent
jusqu'a la prochaine cloture de la reference.
"""

NOM = "annulation_conserve_les_temps"


def appliquer(conn):
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "production_data" not in tables:
        return  # base de test sans la table : rien a reprendre

    cols = {r[1] for r in conn.execute(
        "PRAGMA table_info(production_data)").fetchall()}
    if "est_annule" not in cols:
        return  # colonne jamais creee : rien a reprendre

    dossiers = [
        str(r[0]).strip() for r in conn.execute(
            """SELECT DISTINCT no_dossier FROM production_data
                WHERE COALESCE(est_annule, 0) = 1
                  AND TRIM(COALESCE(no_dossier, '')) NOT IN ('', '0')"""
        ).fetchall()
    ]

    cur = conn.execute(
        "UPDATE production_data SET est_annule = 0 "
        "WHERE COALESCE(est_annule, 0) = 1"
    )
    reprises = cur.rowcount or 0
    conn.commit()

    # Rematerialisation des series : best effort. Une base sans memoire produit
    # (ou un import qui n'expose pas le service) ne doit pas faire echouer la
    # reprise des saisies, qui est le coeur de la migration.
    series = 0
    if dossiers and "produit_series" in tables:
        try:
            from app.services.produit_memoire import materialiser_serie
        except Exception:
            materialiser_serie = None
        if materialiser_serie is not None:
            for ref in dossiers:
                try:
                    if materialiser_serie(conn, ref, cloture_par=NOM):
                        series += 1
                except Exception:
                    continue
            conn.commit()

    print(f"[MySifa] migration {NOM} : {reprises} saisie(s) rendue(s) aux "
          f"statistiques, {series} serie(s) produit rematerialisee(s).")

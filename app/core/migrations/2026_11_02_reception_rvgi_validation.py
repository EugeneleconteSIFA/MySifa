"""Validation humaine des receptions RVGI entrees en stock.

La synchro fait entrer seule toute ligne de reception appariee : le stock reste
a jour, mais personne n'a relu ce qui est entre. Chaque ligne porte desormais
qui l'a validee et quand ; tant que ces deux champs sont vides, l'historique
l'affiche « A valider ».

Reprise : une ligne integree a la main l'a ete par quelqu'un qui l'avait sous
les yeux. Elle est reputee validee par son auteur, a l'heure de l'integration.
Seules les entrees de la synchro restent a valider.
"""

NOM = "reception_rvgi_validation"
DEPEND = ["reception_rvgi_socle"]

AUTEUR_SYNCHRO = "Synchro RVGI"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(erp_reception_integree)").fetchall()}
    if "valide_at" not in cols:
        conn.execute("ALTER TABLE erp_reception_integree ADD COLUMN valide_at TEXT")
    if "valide_par" not in cols:
        conn.execute("ALTER TABLE erp_reception_integree ADD COLUMN valide_par TEXT")
    n = conn.execute(
        "UPDATE erp_reception_integree SET valide_at = integre_at, valide_par = integre_par "
        "WHERE valide_at IS NULL AND COALESCE(integre_par, '') NOT IN ('', ?)",
        (AUTEUR_SYNCHRO,),
    ).rowcount
    conn.commit()
    print(f"[MySifa] migration reception_rvgi_validation : {n} ligne(s) integree(s) a la main reputee(s) validee(s).")

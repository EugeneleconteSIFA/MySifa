"""
FSC — verrouillage de l'allégation à la réception.

Trois manques, constatés le 15/09/2026 sur la base de production.

1. **La portée du certificat n'est nulle part dans le verdict.** `fsc_registre`
   vérifie que le certificat du fournisseur était valide à la date du BL, que le
   BL porte une allégation, que la facture porte la même, et que le code de
   certificat figure sur les documents. Il ne vérifie pas que cette allégation
   fait partie de celles que le certificat AUTORISE. Un fournisseur certifié
   FSC Mix qui facture du FSC 100 % ressort aujourd'hui « éligible ».
   `qualite_fsc_controles.claims` porte déjà cette portée — c'est la seule
   source validée de ces catégories — mais rien ne la lit.

   D'où `claims_autorises` sur la ligne de registre. FIGÉ à l'import, comme
   `certificat_statut` et pour la même raison : un contrôle fait en mars reste
   opposable en octobre, et un élargissement de portée en novembre ne doit pas
   rendre éligible rétroactivement une livraison de mars. `claims_controle_id`
   dit de quel contrôle la portée est tirée — c'est la pièce que l'auditeur
   demande quand il conteste une ligne.

   Portée inconnue (aucun contrôle enregistré pour ce fournisseur) = `a_verifier`,
   jamais `oui`. Au 15/09, AUCUN des 27 fournisseurs certifiés n'a de contrôle :
   toutes les lignes importées sortiront donc en « à vérifier » tant que les
   contrôles ne sont pas saisis. C'est le comportement voulu — une allégation
   sans portée contrôlée n'est pas démontrée.

2. **La réception physique ne connaît pas sa ligne de registre.**
   `fsc_reception.reception_id` n'est rempli qu'au moment de l'import, en lisant
   `erp_reception_integree`. Une réception intégrée dans MyStock APRÈS l'import
   de la ligne reste orpheline pour toujours. `stock_receptions.fsc_reception_id`
   porte le lien dans l'autre sens, écrit des deux côtés, et rend la chaîne
   RVGI → registre → réception → bobine → scan parcourable dans les deux sens.

3. **Rien ne distingue une allégation constatée d'une allégation saisie.**
   `fsc_source` le dit : `registre` (dérivée de la ligne de registre, la seule
   valeur admise après l'entrée dans la chaîne de contrôle) ou
   `saisie_historique` (tapée à la main avant, conservée telle quelle).

Les 14 réceptions existantes sont toutes en `non_fsc` et antérieures à l'entrée
dans la chaîne de contrôle : elles sont marquées `saisie_historique` et rien
d'autre ne les touche.

Rejouable : test de présence avant chaque ALTER, index IF NOT EXISTS, backfill
borné aux lignes dont la source est encore nulle.
"""

NOM = "fsc_reception_verrou_portee_certificat"
DEPEND = ["fsc_registre_approvisionnements"]


_COLONNES_REGISTRE = [
    # JSON : ["fsc_mix", "fsc_mix_credit"] — codes de FSC_CLAIMS_PORTEE.
    # NULL = portée jamais contrôlée, ce qui n'est pas la même chose que [].
    ("claims_autorises", "TEXT"),
    ("claims_controle_id", "INTEGER"),
    ("claims_controle_le", "TEXT"),
]

_COLONNES_RECEPTION = [
    ("fsc_reception_id", "INTEGER"),
    ("fsc_source", "TEXT"),
]


def _colonnes(conn, table: str) -> set:
    return {r[1] for r in conn.execute("PRAGMA table_info(%s)" % table).fetchall()}


def _tables(conn) -> set:
    return {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def appliquer(conn):
    tables = _tables(conn)
    ajoutees = 0

    if "fsc_reception" in tables:
        cols = _colonnes(conn, "fsc_reception")
        for nom, typ in _COLONNES_REGISTRE:
            if nom not in cols:
                conn.execute("ALTER TABLE fsc_reception ADD COLUMN %s %s" % (nom, typ))
                ajoutees += 1

    reprises = 0
    if "stock_receptions" in tables:
        cols = _colonnes(conn, "stock_receptions")
        for nom, typ in _COLONNES_RECEPTION:
            if nom not in cols:
                conn.execute("ALTER TABLE stock_receptions ADD COLUMN %s %s" % (nom, typ))
                ajoutees += 1
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_stock_rec_fsc_ligne "
            "ON stock_receptions(fsc_reception_id)"
        )
        # Tout ce qui existe déjà a été saisi à la main, avant la chaîne de
        # contrôle. On le dit, on ne le réécrit pas.
        reprises = conn.execute(
            "UPDATE stock_receptions SET fsc_source = 'saisie_historique' "
            "WHERE fsc_source IS NULL"
        ).rowcount

    conn.commit()
    print(
        "[MySifa] migration %s : %d colonne(s) ajoutee(s), "
        "%d reception(s) marquee(s) saisie_historique."
        % (NOM, ajoutees, reprises)
    )

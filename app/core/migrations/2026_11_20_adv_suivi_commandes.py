"""
ADV : suivi des lignes de commande et préparations.

Deux tables, clé métier `(numero, ligne)` de la ligne de commande RVGI — pas
l'id du miroir, reconstruit à chaque synchro (même règle que
`rvgi_rattachements`).

- `adv_prepas` : l'état de la préparation, saisi par la logistique dans
  l'onglet Prépa de /adv (à préparer, en cours, prête).
- `adv_forcages` : une étape de la chaîne (BAT, prod, stock, prépa, départ)
  que l'ADV a fixée à la main, quand les données ne disent pas la vérité
  (BAT validé par mail, stock hors MyStock…). Le calcul reste affiché à côté.
"""

NOM = "adv_suivi_commandes"


def appliquer(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS adv_prepas (
            numero   TEXT    NOT NULL,
            ligne    INTEGER NOT NULL,
            statut   TEXT    NOT NULL DEFAULT 'a_preparer',
            note     TEXT,
            maj_le   TEXT    NOT NULL,
            maj_par  TEXT,
            PRIMARY KEY (numero, ligne)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS adv_forcages (
            numero   TEXT    NOT NULL,
            ligne    INTEGER NOT NULL,
            etape    TEXT    NOT NULL,
            valeur   TEXT    NOT NULL,
            note     TEXT,
            maj_le   TEXT    NOT NULL,
            maj_par  TEXT,
            PRIMARY KEY (numero, ligne, etape)
        )
    """)
    conn.commit()

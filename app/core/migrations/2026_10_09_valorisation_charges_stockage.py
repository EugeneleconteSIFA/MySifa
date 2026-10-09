"""
Coûts directs de production et frais de stockage de la valorisation.

Valorisation PF = sous-total × 0,7835 (coûts directs seuls) × 1,02 (stockage).
Valorisation MP = sous-total d'achat × 1,02 (stockage).
`charge_production_pct` est un abattement : 0,7835 = 1 − 21,65 %.

Ne touche qu'une valeur restée à 0 : un réglage déjà saisi dans Coûts matières
n'est pas écrasé. Les deux valeurs restent éditables dans Paramètres.
"""

NOM = "valorisation_charges_stockage"


def appliquer(conn):
    for cle, val in (("charge_production_pct", 21.65), ("storage_fees_pct", 2.0)):
        conn.execute(
            "INSERT OR IGNORE INTO mc_setting (key, value_decimal) VALUES (?, 0)", (cle,)
        )
        conn.execute(
            "UPDATE mc_setting SET value_decimal = ? WHERE key = ? "
            "AND COALESCE(value_decimal, 0) = 0",
            (val, cle),
        )
    conn.commit()

"""
Méthodes de calcul du transport d'import.

Deux modes ne suffisaient pas. Selon le fournisseur, le transport se chiffre :

- AMOUNT     : un montant à l'unité d'achat (€/kg ou €/m²) ;
- PCT        : un pourcentage du prix d'achat ;
- CONTENEUR  : le coût d'un conteneur divisé par ce qu'il transporte ;
- FORFAIT    : un forfait de commande divisé par la quantité commandée.

Les deux derniers partagent la même arithmétique — un coût divisé par une
quantité — mais pas le même vocabulaire ni les mêmes ordres de grandeur. Les
distinguer évite de faire dire à un champ « coût conteneur » qu'il porte un
forfait de livraison.

D'où deux colonnes nouvelles, communes aux deux : le coût et la quantité.
"""

NOM = "mp_transport_methodes"
DEPEND = ["mc_taxe_pct_marge_grammage"]

_COLONNES = (
    # Coût total à répartir : prix du conteneur, ou forfait de la commande.
    ("transport_cout", "REAL NOT NULL DEFAULT 0"),
    # Quantité sur laquelle on le répartit, dans l'unité d'achat (kg ou m²).
    ("transport_quantite", "REAL NOT NULL DEFAULT 0"),
)

_TABLES = ("mc_material", "mp_matiere_declinaison")


def appliquer(conn):
    for table in _TABLES:
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if not cols:
            continue
        for nom, ddl in _COLONNES:
            if nom not in cols:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {nom} {ddl}")
    conn.commit()

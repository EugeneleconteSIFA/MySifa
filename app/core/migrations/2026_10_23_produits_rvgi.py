"""
Produits MyStock liés à leur article RVGI.

La base `produits` a été chargée une fois, le 14/04/2026, depuis un export de
l'ERP, et plus rien ne l'a enrichie depuis : une référence créée dans RVGI
après cette date (601/0168, par exemple) est commandée, produite, livrée, et
n'existe pas dans MyStock. `rvgi_produits.synchroniser()` la crée désormais à
chaque import du miroir.

Trois colonnes sur `produits` :

- `rvgi_article` : la référence de l'article dans RVGI, `code1/code2`
  (« 601/0168 », « TT/FR110X450_S2021 »). Posée sur les produits créés par la
  synchro ET sur les produits existants qu'elle a reconnus.
- `rvgi_cree_le` : renseignée seulement quand c'est la synchro qui a créé le
  produit. Distingue un produit saisi dans MyStock d'un produit venu de l'ERP.
- `rvgi_vu_le` : dernier import du miroir où l'article était encore présent.

Aucune reprise ici : la première synchro qui suit pose les liens.
"""

NOM = "produits_rvgi_article"


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(produits)").fetchall()}
    if not cols:
        return
    if "rvgi_article" not in cols:
        conn.execute("ALTER TABLE produits ADD COLUMN rvgi_article TEXT")
    if "rvgi_cree_le" not in cols:
        conn.execute("ALTER TABLE produits ADD COLUMN rvgi_cree_le TEXT")
    if "rvgi_vu_le" not in cols:
        conn.execute("ALTER TABLE produits ADD COLUMN rvgi_vu_le TEXT")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_produits_rvgi_article ON produits(rvgi_article)"
    )
    conn.commit()

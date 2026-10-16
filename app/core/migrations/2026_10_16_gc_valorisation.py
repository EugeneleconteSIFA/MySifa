"""Nouvel ERP — valorisation du stock (réponse d'Eugène, 16/10/2026 : « prix et
quantité à la date de la valorisation, et les paramètres complémentaires de
MyStock › Valorisation »).

- `gc_prix_stock_historique` : chaque changement du prix de stock d'un article,
  daté ; la valorisation à une date lit le dernier prix connu à cette date.
- `gc_articles.prix_stock_m2_cents` : matière en laize, prix au m² ; la valeur
  d'une quantité en mètres linéaires se calcule avec la laize du mouvement.
- Les paramètres complémentaires (charges de production, frais de stockage) ne
  sont PAS recopiés : l'ERP lit ceux de MyStock (`mc_setting`).
Le prix de stock déjà saisi sur une fiche devient la première entrée de
l'historique.
"""

NOM = "gc_valorisation"
DEPEND = ["gc_fiches_rvgi"]


def appliquer(conn):
    cols = {r[1] for r in conn.execute("PRAGMA table_info(gc_articles)").fetchall()}
    if "prix_stock_m2_cents" not in cols:
        conn.execute("ALTER TABLE gc_articles ADD COLUMN prix_stock_m2_cents INTEGER")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS gc_prix_stock_historique (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL,
            prix_cents INTEGER,              -- pour `base_prix` unités de l'article
            prix_m2_cents INTEGER,           -- matière en laize
            depuis TEXT NOT NULL,            -- AAAA-MM-JJ : valable à partir de ce jour
            cree_par TEXT, cree_le TEXT);
        CREATE INDEX IF NOT EXISTS idx_gc_prix_stock_hist ON gc_prix_stock_historique(article_id, depuis);
        """
    )
    n = conn.execute(
        """INSERT INTO gc_prix_stock_historique (article_id, prix_cents, prix_m2_cents, depuis, cree_par, cree_le)
           SELECT a.id, a.prix_stock_cents, a.prix_stock_m2_cents, substr(COALESCE(a.modifie_le, a.cree_le, '2000-01-01'),1,10),
                  'reprise', datetime('now','localtime')
           FROM gc_articles a
           WHERE (a.prix_stock_cents IS NOT NULL OR a.prix_stock_m2_cents IS NOT NULL)
             AND NOT EXISTS (SELECT 1 FROM gc_prix_stock_historique h WHERE h.article_id=a.id)""").rowcount
    if n:
        print(f"[MySifa] migration gc_valorisation : {n} prix de stock repris dans l'historique.")
    conn.commit()

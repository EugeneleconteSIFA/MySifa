"""Matières tenues à l'unité : ni palette, ni conditionnement fixe.

Cartons et mandrins se tiennent à la PALETTE, et `unites_par_palette` traduit
une quantité d'achat (cartons, tubes) dans cette unité. Deux familles n'ont pas
de palette qui veuille dire quelque chose :

- les bagues, achetées et comptées à l'unité (« Pal. XXX bagues » dans les
  libellés fournisseur : personne ne sait combien il y en a par palette) ;
- les cartons achetés au lot chez un fournisseur de détail, dont le lot change
  d'une commande à l'autre (lot de 20, de 25, de 50).

Sans conditionnement, la réception RVGI ne sait pas convertir et le déstockage
bloque. Une matière tenue à l'unité garde le même modèle que les autres, avec
une palette d'une unité : `unites_par_palette = 1`. Toutes les conversions
existantes (réception, déstockage, valorisation, stock réel) restent justes
sans rien changer, et seul l'affichage cesse de parler de palettes.

La bascule convertit le stock et son historique, comme l'a fait la bascule des
adhésifs au kilo : une quantité de palettes devient une quantité d'unités.
"""


def _cols(conn, table):
    return {r[1] for r in conn.execute("PRAGMA table_info(%s)" % table).fetchall()}


def _echelle(conn, matiere_id, f):
    """Multiplie stock, seuil et historique d'une matière par `f`."""
    st = _cols(conn, "mp_stock")
    champs = [c for c in ("quantite", "quantite_magasin", "quantite_production") if c in st]
    if champs:
        conn.execute(
            "UPDATE mp_stock SET %s WHERE matiere_id = ?"
            % ", ".join("%s = %s * ?" % (c, c) for c in champs),
            tuple([f] * len(champs)) + (matiere_id,))
    conn.execute(
        "UPDATE matieres_premieres SET seuil_alerte = COALESCE(seuil_alerte, 0) * ? WHERE id = ?",
        (f, matiere_id))
    mv = _cols(conn, "mp_mouvements")
    if mv:
        conn.execute(
            """UPDATE mp_mouvements
               SET quantite = COALESCE(quantite, 0) * ?,
                   quantite_avant = quantite_avant * ?,
                   quantite_apres = quantite_apres * ?
               WHERE matiere_id = ?""", (f, f, f, matiere_id))
    if _cols(conn, "inventaires_matieres"):
        conn.execute(
            """UPDATE inventaires_matieres
               SET quantite_avant = quantite_avant * ?,
                   quantite_comptee = quantite_comptee * ?,
                   ecart = ecart * ?
               WHERE matiere_id = ?""", (f, f, f, matiere_id))


def passer_a_l_unite(conn, matiere_id):
    """Bascule une matière à l'unité. Renvoie le facteur appliqué, ou None.

    Le facteur est le conditionnement en vigueur : 4 palettes de 125 bagues
    deviennent 500 bagues. Sans conditionnement, rien ne permet de convertir :
    un stock non nul est laissé tel quel (il était déjà inutilisable) et la
    fonction le signale en renvoyant None.
    """
    r = conn.execute(
        "SELECT unites_par_palette, COALESCE(stock_a_l_unite, 0) AS u "
        "FROM matieres_premieres WHERE id = ?", (matiere_id,)).fetchone()
    if not r or int(r[1] or 0):
        return 1.0
    try:
        f = float(r[0] or 0)
    except (TypeError, ValueError):
        f = 0.0
    if f > 0 and abs(f - 1.0) > 1e-9:
        _echelle(conn, matiere_id, f)
    conn.execute(
        "UPDATE matieres_premieres SET stock_a_l_unite = 1, unites_par_palette = 1 WHERE id = ?",
        (matiere_id,))
    return f if f > 0 else None


def repasser_a_la_palette(conn, matiere_id, unites_par_palette):
    """Retour à la palette : le stock en unités est divisé par le conditionnement."""
    f = float(unites_par_palette)
    if f <= 0:
        raise ValueError("conditionnement nul")
    r = conn.execute(
        "SELECT COALESCE(stock_a_l_unite, 0) FROM matieres_premieres WHERE id = ?",
        (matiere_id,)).fetchone()
    if r and int(r[0] or 0) and abs(f - 1.0) > 1e-9:
        _echelle(conn, matiere_id, 1.0 / f)
    conn.execute(
        "UPDATE matieres_premieres SET stock_a_l_unite = 0, unites_par_palette = ? WHERE id = ?",
        (f, matiere_id))

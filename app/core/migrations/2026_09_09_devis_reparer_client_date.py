"""
Répare les devis entrés avec une date sérielle Excel ou un client factice.

Deux défauts du premier import, corrigés depuis dans `devis_parser.py`, mais
qui restent gravés dans les lignes déjà en base — un correctif de lecture ne
revient pas en arrière sur ce qui est écrit.

1. LA DATE. Excel compte les dates en jours depuis le 30/12/1899. Quand la
   cellule n'est pas formatée en date — ce qui varie d'un classeur à l'autre —
   pandas rend le nombre brut, et « 46266 » se retrouvait tel quel dans
   `date_devis`. C'est le 1er septembre 2026.

2. LE CLIENT. Le modèle maison arrive prérempli « Mon client » et tous les
   commerciaux ne le remplacent pas. Pris pour un nom, ce texte regroupe des
   devis sans rapport sous un même client fantôme, sous lequel plus rien ne se
   retrouve. On le vide : un client inconnu s'affiche « (client non lu) », ce
   qui est vrai, plutôt qu'un nom qui ne l'est pas.

On ne rattrape PAS le client depuis le nom du fichier ici. La lecture le fait
déjà à l'import, avec la confiance dégradée et la provenance qui vont avec ;
le refaire en migration poserait la même valeur sans sa traçabilité, et
personne ne saurait plus, dans six mois, d'où elle sort.
"""

from datetime import datetime, timedelta

NOM = "devis_reparer_client_date"
DEPEND = ["devis_extraction_ia_indicateurs"]

_EPOQUE_EXCEL = datetime(1899, 12, 30)

# Mêmes valeurs que `devis_parser._CLIENTS_FACTICES`, en minuscules.
_CLIENTS_FACTICES = {
    "mon client", "nom du client", "client", "nom client", "xxx", "x",
    "à compléter", "a completer", "-", "?", "n/a", "na", "test", "exemple",
}


def _date_reparee(valeur):
    """Rend la date ISO si `valeur` est une série Excel plausible, sinon None."""
    txt = str(valeur or "").strip()
    if not txt:
        return None
    try:
        serie = float(txt.replace(",", "."))
    except ValueError:
        return None
    # 20 000-60 000 = 1954-2064. Hors de cette plage, ce n'est pas une date.
    if not (20000 <= serie <= 60000):
        return None
    return (_EPOQUE_EXCEL + timedelta(days=int(serie))).strftime("%Y-%m-%d")


def appliquer(conn):
    tables = {
        r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    if "devis" not in tables:
        print("[MySifa] migration devis_reparer_client_date : table devis absente.")
        return

    dates = 0
    for row in conn.execute("SELECT id, date_devis FROM devis").fetchall():
        reparee = _date_reparee(row[1])
        if reparee:
            conn.execute("UPDATE devis SET date_devis=? WHERE id=?", (reparee, row[0]))
            dates += 1

    clients = 0
    for row in conn.execute("SELECT id, client FROM devis").fetchall():
        brut = str(row[1] or "").strip().lower().rstrip(":").strip()
        if brut and brut in _CLIENTS_FACTICES:
            conn.execute("UPDATE devis SET client='' WHERE id=?", (row[0],))
            clients += 1

    conn.commit()
    print(
        f"[MySifa] migration devis_reparer_client_date : {dates} date(s) sérielle(s) "
        f"convertie(s), {clients} client(s) factice(s) vidé(s)."
    )

"""Allégation FSC d'un dossier, déduite des matières consommées.

Règle de l'affiche atelier (« Deux matières, deux allégations ? C'est la plus
basse qui l'emporte », septembre 2026) :

                 Mix Credit   Mix X %          Recycled         Non FSC
    Mix Credit   Mix Credit   Mix X %          Mix              NON FSC
    Mix X %      Mix X %      Mix (X le + bas) Mix (le + bas)   NON FSC
    Recycled     Mix          Mix (le + bas)   Recycled (+ bas) NON FSC

1. Une seule bobine non FSC → tout le dossier est non FSC.
2. Controlled Wood → non FSC : ce n'est pas une allégation.
3. Film, colle, encre → ne comptent pas : seul le bois décide
   (`gc_articles.fsc_bois = 0`).

FSC 100 % (absent de l'affiche) se combine comme la meilleure allégation :
avec une autre, c'est l'autre qui l'emporte.

Codes : ceux du module FSC de MySifa (`fsc_100`, `fsc_mix_credit`, `fsc_mix`,
`fsc_recycled`, `non_fsc`, `controlled_wood`). Une allégation est un couple
(code, pourcentage) ; le pourcentage ne vaut que pour `fsc_mix` et
`fsc_recycled`, et peut être inconnu (None).
"""
from __future__ import annotations

LIBELLES = {
    "fsc_100": "FSC 100%", "fsc_mix_credit": "FSC Mix Credit", "fsc_mix": "FSC Mix",
    "fsc_recycled": "FSC Recycled", "non_fsc": "Non FSC", "controlled_wood": "FSC Controlled Wood",
}
FSC = {"fsc_100", "fsc_mix_credit", "fsc_mix", "fsc_recycled"}


def _min_pct(a, b):
    vals = [x for x in (a, b) if x is not None]
    return min(vals) if vals else None


def combiner2(a: tuple, b: tuple) -> tuple:
    (ca, pa), (cb, pb) = a, b
    if ca in ("non_fsc", "controlled_wood") or cb in ("non_fsc", "controlled_wood"):
        return ("non_fsc", None)
    if ca == "fsc_100":
        return (cb, pb)
    if cb == "fsc_100":
        return (ca, pa)
    if ca == cb == "fsc_mix_credit":
        return ("fsc_mix_credit", None)
    if {ca, cb} == {"fsc_mix_credit", "fsc_mix"}:
        return ("fsc_mix", pa if ca == "fsc_mix" else pb)
    if {ca, cb} == {"fsc_mix_credit", "fsc_recycled"}:
        return ("fsc_mix", None)
    if ca == cb == "fsc_recycled":
        return ("fsc_recycled", _min_pct(pa, pb))
    # Mix X % avec Mix X % ou avec Recycled : Mix, le pourcentage le plus bas.
    return ("fsc_mix", _min_pct(pa, pb))


def combiner(allegations: list[tuple]) -> tuple | None:
    """Allégation d'un ensemble de matières. None si aucune matière bois."""
    res = None
    for a in allegations:
        if a is None or not a[0]:
            # matière bois sans allégation connue : on ne peut rien affirmer
            return ("non_fsc", None)
        res = a if res is None else combiner2(res, a)
    return res


def libelle(a: tuple | None) -> str:
    if not a:
        return ""
    code, pct = a
    txt = LIBELLES.get(code, code)
    if code in ("fsc_mix", "fsc_recycled") and pct is not None:
        txt += f" {pct}%"
    return txt


def allegation_of(conn, of_id: int) -> tuple | None:
    """Allégation d'un OF : combinaison des matières bois consommées."""
    rows = conn.execute(
        """SELECT DISTINCT a.fsc_allegation, a.fsc_pct FROM gc_mouvements m JOIN gc_articles a ON a.id=m.article_id
           WHERE m.piece_id=? AND m.type='consommation' AND COALESCE(a.fsc_bois,1)=1""", (of_id,)).fetchall()
    if not rows:
        return None
    return combiner([(r["fsc_allegation"] or "", r["fsc_pct"]) for r in rows])


def allegation_ligne(conn, ligne_id: int) -> tuple | None:
    """Allégation d'une ligne de vente : celle des OF lancés depuis la ligne de
    commande d'origine (en remontant BL → commande). None si inconnue."""
    lid = ligne_id
    for _ in range(4):   # facture → BL → commande
        r = conn.execute(
            """SELECT l.id, l.ligne_amont_id, p.type FROM gc_pieces_lignes l JOIN gc_pieces p ON p.id=l.piece_id
               WHERE l.id=?""", (lid,)).fetchone()
        if not r:
            return None
        if r["type"] in ("commande", "marche"):
            break
        if not r["ligne_amont_id"]:
            return None
        lid = r["ligne_amont_id"]
    ofs = [x["id"] for x in conn.execute(
        """SELECT DISTINCT p.id FROM gc_pieces_lignes lo JOIN gc_pieces p ON p.id=lo.piece_id
           WHERE lo.ligne_amont_id=? AND p.type='of' AND p.statut!='annule'""", (lid,)).fetchall()]
    alls = [allegation_of(conn, o) for o in ofs]
    alls = [a for a in alls if a is not None]
    return combiner(alls) if alls else None


def alertes(conn, piece_id: int) -> list[str]:
    """Lignes d'un article vendu « certifié FSC » dont l'allégation n'est pas FSC."""
    out = []
    for l in conn.execute(
        """SELECT l.id, a.code FROM gc_pieces_lignes l JOIN gc_articles a ON a.id=l.article_id
           WHERE l.piece_id=? AND COALESCE(a.fsc_requis,0)=1""", (piece_id,)).fetchall():
        a = allegation_ligne(conn, l["id"])
        if a is None:
            out.append(f"{l['code']} : vendu certifié FSC, allégation inconnue (aucune consommation tracée).")
        elif a[0] not in FSC:
            out.append(f"{l['code']} : vendu certifié FSC mais la matière consommée donne « {libelle(a)} ».")
    return out

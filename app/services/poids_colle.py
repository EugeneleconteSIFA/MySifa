"""Saisie prod › widget « Poids de colle » : ce que le dossier en cours dit.

Le calcul (classeur « application excel calcul de poids adhésif » de
l'atelier) se fait dans le navigateur :

    surface (mm²) = laize × hauteur − 4 × (r² − π r² / 4)   étiquette rectangle
                  = π × (Ø / 2)²                            étiquette ronde
    adhésif (g/m²) = (poids pesé − surface × n × (frontal [+ glassine]
                      + encre × couverture)) / (surface × n)

Ce module ne fournit que les entrées : le format du dossier (le dossier
d'abord, la fiche technique en repli), le rayon des coins, le papier, la
glassine et les anilox de la fiche, rapprochés du référentiel des épaisseurs
matière (`mp_metrage_epaisseurs`, colonne `grammage_gsm`).

Le rapprochement se fait sur le texte : `support_ref_id` existe, mais les
matières MyStock n'ont pas de grammage (`weight_gsm` vide partout au
2 novembre 2026). Une correspondance ambiguë (« THERMIQUE ECO » : Kanzan ou
Jujo ?) n'est pas tranchée : les candidats sont rendus, l'opérateur choisit.
"""
from __future__ import annotations

import re
import unicodedata

_RE_ROND = re.compile(r"\brond", re.I)


def _mots(texte) -> list:
    s = unicodedata.normalize("NFKD", str(texte or "")).encode("ascii", "ignore").decode().lower()
    return [m for m in re.split(r"[^a-z0-9]+", s) if m]


def _meme_mot(a: str, b: str) -> bool:
    """« therm » = « thermique », « pro » = « protege » : préfixe de 3 lettres
    au moins. Les nombres doivent être égaux (« 80 » n'est pas « 800 »)."""
    if a == b:
        return True
    if a.isdigit() or b.isdigit():
        return False
    court, long_ = sorted((a, b), key=len)
    return len(court) >= 3 and long_.startswith(court)


def _contenu(petit: list, grand: list) -> bool:
    return bool(petit) and all(any(_meme_mot(p, g) for g in grand) for p in petit)


def correspondance(texte, lignes: list, famille: str) -> dict:
    """{"choix": ligne | None, "candidats": [lignes]} pour un texte de fiche.

    Une ligne du référentiel dont tous les mots sont dans le texte de la fiche
    gagne (« Vélin » pour « VELIN ETIWELL »), la plus précise d'abord. À
    défaut, celles qui contiennent tous les mots de la fiche sont candidates
    (« THERMIQUE ECO » → Thermique Eco Kanzan, Thermique Eco Jujo) ; une seule
    suffit à choisir. Enfin, les plus proches sont proposées sans être choisies.
    """
    mf = _mots(texte)
    if not mf:
        return {"choix": None, "candidats": []}
    pool = [l for l in lignes if l.get("famille") == famille and l.get("grammage_gsm") is not None]
    pleins = [(len(_mots(l["libelle"])), l) for l in pool if _contenu(_mots(l["libelle"]), mf)]
    if pleins:
        top = max(n for n, _ in pleins)
        meilleurs = [l for n, l in pleins if n == top]
        if len({l["grammage_gsm"] for l in meilleurs}) == 1:
            return {"choix": meilleurs[0], "candidats": meilleurs}
        return {"choix": None, "candidats": meilleurs}
    partiels = [l for l in pool if _contenu(mf, _mots(l["libelle"]))]
    if partiels:
        return {"choix": partiels[0] if len(partiels) == 1 else None, "candidats": partiels}
    # Dernier recours, sans choisir : les lignes qui partagent le plus de mots
    # avec la fiche, deux au moins (« THERMIQUE ECO BPA » → les Thermique Eco).
    communs = [(sum(1 for m in mf if any(_meme_mot(m, x) for x in _mots(l["libelle"]))), l) for l in pool]
    top = max((n for n, _ in communs), default=0)
    return {"choix": None, "candidats": [l for n, l in communs if n == top] if top >= 2 else []}


def correspondance_anilox(texte, lignes: list):
    """« 400 L », « 400 lignes », « 400L » → la ligne anilox « 400L »."""
    m = re.search(r"\d+", str(texte or ""))
    if not m:
        return None
    for l in lignes:
        if l.get("famille") != "anilox" or l.get("grammage_gsm") is None:
            continue
        n = re.search(r"\d+", l["libelle"] or "")
        if n and n.group(0) == m.group(0):
            return l
    return None


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def contexte(conn, no_dossier: str, lignes: list) -> dict:
    """Entrées du calcul pour un dossier. Tout champ inconnu vaut None."""
    vide = {"no_dossier": no_dossier or None, "fiche": None, "format": None,
            "papier": None, "glassine": None, "anilox": []}
    ref = (no_dossier or "").strip()
    if not ref:
        return vide
    pe = conn.execute(
        """SELECT id, format_l, format_h FROM planning_entries
            WHERE TRIM(reference) = ? OR TRIM(COALESCE(numero_of, '')) = ?
            ORDER BY (statut = 'en_cours') DESC, id DESC LIMIT 1""",
        (ref, ref),
    ).fetchone()
    if not pe:
        return vide

    from app.routers.besoins_matieres import _SQL_PE_UN, _load_dossiers

    rows = _load_dossiers(conn, _SQL_PE_UN, (pe["id"],))
    ft_id = rows[0].get("ft_id") if rows else None
    ft = None
    if ft_id:
        ft = conn.execute(
            """SELECT id, reference, format, eti_laize, eti_longueur, eti_rayons,
                      support, glassine, tete1_anilox, tete2_anilox, tete3_anilox,
                      outil1_nb_front, mod_nb_front
                 FROM fiches_techniques WHERE id = ?""",
            (ft_id,),
        ).fetchone()
    ft = dict(ft) if ft else {}

    laize = _num(pe["format_l"]) or _num(ft.get("eti_laize"))
    hauteur = _num(pe["format_h"]) or _num(ft.get("eti_longueur"))
    ronde = bool(_RE_ROND.search(ft.get("format") or ""))
    fmt = None
    if laize or hauteur:
        fmt = {"forme": "ronde" if ronde else "rectangle", "laize": laize, "hauteur": hauteur,
               "rayon": float(ft["eti_rayons"]) if ft.get("eti_rayons") is not None else None,
               "diametre": laize if ronde else None, "texte": (ft.get("format") or "").strip() or None,
               "source": "dossier" if _num(pe["format_l"]) else "fiche"}

    def matiere(champ, famille):
        txt = (ft.get(champ) or "").strip()
        if not txt:
            return None
        c = correspondance(txt, lignes, famille)
        return {"texte": txt, "choix": c["choix"]["id"] if c["choix"] else None,
                "candidats": [l["id"] for l in c["candidats"]]}

    anilox = []
    for t in (1, 2, 3):
        txt = (ft.get(f"tete{t}_anilox") or "").strip()
        if txt:
            l = correspondance_anilox(txt, lignes)
            anilox.append({"tete": t, "texte": txt, "choix": l["id"] if l else None})

    return {
        "no_dossier": ref,
        "fiche": {"id": ft["id"], "reference": ft.get("reference"),
                  "nb_fronts": ft.get("outil1_nb_front") or ft.get("mod_nb_front")} if ft else None,
        "format": fmt,
        "papier": matiere("support", "frontal"),
        "glassine": matiere("glassine", "glassine"),
        "anilox": anilox,
    }

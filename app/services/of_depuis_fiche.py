"""
Compléter un OF sans PDF à partir de la fiche technique de son produit.

Un OF poussé par Access, ou saisi dans MySifa, n'a pas de document d'origine :
son aperçu est posé sur le modèle vierge (`of_pdf_generator`). Tout ce que
l'OF ne porte pas reste alors en blanc — or Access ne transmet ni l'outillage,
ni le conditionnement, et parfois même pas le produit. Constat du 17/09/2026 :
l'OF 9931675 s'imprimait avec « Réf : 9931675 » (le numéro d'OF à la place du
produit), sans machine, sans laize et sans aucun outil.

Ce que fait ce module, en LECTURE seule (rien n'est écrit en base)
-----------------------------------------------------------------
1. Retrouver le produit, dans cet ordre :
     a. la référence de l'OF, si elle contient une clé « XXX/NNNN » ;
     b. le dossier de planning relié à l'OF (`ref_produit`) ;
     c. les lignes de commande RVGI dont le numéro figure dans celui de l'OF
        — seulement si elles portent UN SEUL article. Deux articles dans un
        même OF, c'est un regroupement décidé par l'ADV : en prendre un au
        hasard serait pire que de laisser la case vide.
2. Choisir LA fiche de ce produit (`fiche_choix.choisir_fiche` : référence
   exacte, puis machine sans accent, puis laize).
3. Remplir les cases VIDES de l'OF depuis la fiche. Une valeur portée par
   l'OF n'est jamais remplacée — l'OF est le document de la production, la
   fiche le modèle du produit. Seule exception : la référence, qui est
   ramenée à la clé produit quand l'OF porte autre chose (son propre numéro,
   ou le libellé complet « 1220/0001 - COHESIO2 - Laize 570 »).

Le résultat porte `_fiche_id` et `_provenance_fiche` pour qui veut dire d'où
viennent les cases complétées.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.services.fiche_choix import choisir_fiche

_NUMERO_CDE_RE = re.compile(r"\b(99\d{5})\b")

# (colonne de l'OF, colonne de la fiche) — cases que la fiche complète quand
# l'OF les laisse vides. Ce sont des attributs du PRODUIT ; les quantités,
# dates et numéros de l'OF n'y figurent pas et ne doivent jamais y figurer.
CORRESPONDANCES = (
    ("machine",             "machine"),
    ("laize",               "laize_optimale"),
    ("matiere",             "support"),
    ("glassine",            "glassine"),
    ("adhesif_label",       "adhesif"),
    ("qte_au_mille",        "qte_au_mille"),
    ("outil_1_forme",       "outil1_forme"),
    ("outil_1_numero",      "outil1_numero_sifa"),
    ("outil_2_forme",       "outil2_forme"),
    ("outil_2_numero",      "outil2_numero_sifa"),
    ("mandrins_dia",        "mandrin_dia"),
    ("mandrin_longueur",    "mandrin_longueur"),
    ("conditionnement",     "conditionnement"),
    ("cartons_type",        "cartons"),
    ("cales_sachets",       "cales_sachets"),
    ("palette_type",        "palette_type"),
    ("particularites",      "particularite"),
)


def _vide(v: Any) -> bool:
    if v is None:
        return True
    if isinstance(v, str):
        return not v.strip()
    if isinstance(v, (int, float)):
        return v == 0
    return False


def _norm(texte: Any) -> Optional[str]:
    if not texte:
        return None
    try:
        from app.services.fiche_ref_parser import normalize_ref_produit
    except Exception:  # pragma: no cover
        return None
    return normalize_ref_produit(str(texte))


def _dossier_de_l_of(conn, of_id: Any) -> Optional[Dict[str, Any]]:
    """Le dossier de planning relié à l'OF — lien actif d'abord."""
    if not of_id:
        return None
    try:
        r = conn.execute(
            """SELECT pe.ref_produit, pe.laize, m.nom AS machine_nom
                 FROM planning_entries pe
                 LEFT JOIN machines m ON m.id = pe.machine_id
                WHERE pe.of_import_id = ?
                   OR pe.id IN (SELECT planning_entry_id FROM planning_of_links
                                 WHERE of_import_id = ?)
                ORDER BY CASE WHEN pe.of_import_id = ? THEN 0 ELSE 1 END, pe.id DESC
                LIMIT 1""",
            (of_id, of_id, of_id),
        ).fetchone()
    except Exception:
        return None
    return dict(r) if r else None


def article_rvgi_unique(numero_of: Any) -> Optional[str]:
    """« 1220/0001 » si les commandes citées par le numéro d'OF portent un
    seul article, sinon None. Le miroir peut être absent : jamais d'erreur."""
    numeros = sorted(set(_NUMERO_CDE_RE.findall(str(numero_of or ""))))
    if not numeros:
        return None
    try:
        from app.services import erp_mirror as miroir
        with miroir.get_erp_db() as c:
            tables = miroir.tables_presentes(c)
            if "cde_ligne" not in tables or "cde_entete" not in tables:
                return None
            # INNER JOIN obligatoire : une ligne dont l'entête est à la
            # corbeille reste dans le miroir sans lui (règle RVGI du 28/08).
            rows = c.execute(
                "SELECT DISTINCT TRIM(CAST(l.code1 AS TEXT)) AS c1, "
                "       TRIM(CAST(l.code2 AS TEXT)) AS c2 "
                "  FROM cde_ligne l "
                "  JOIN cde_entete e ON e.numero = l.numero AND e.corbeille = 0 "
                " WHERE l.corbeille = 0 "
                "   AND CAST(l.numero AS TEXT) IN (%s)" % ",".join("?" * len(numeros)),
                numeros,
            ).fetchall()
    except Exception:
        return None
    articles = {(r["c1"], r["c2"]) for r in rows if r["c1"] and r["c2"]}
    if len(articles) != 1:
        return None
    c1, c2 = next(iter(articles))
    return _norm("%s/%s" % (c1, c2))


def completer_of(conn, of_row: Dict[str, Any]) -> Dict[str, Any]:
    """Nouveau dict : l'OF complété depuis sa fiche technique. Lecture seule."""
    of = dict(of_row or {})
    ref_of = (of.get("reference") or "").strip()
    numero = (of.get("of_numero") or "").strip()
    machine = of.get("machine")
    laize = of.get("laize")

    provenance_produit = None
    norm = _norm(ref_of)
    if norm:
        provenance_produit = "OF"
    dossier = _dossier_de_l_of(conn, of.get("id"))
    if dossier:
        machine = machine or dossier.get("machine_nom")
        laize = laize or dossier.get("laize")
        if not norm:
            norm = _norm(dossier.get("ref_produit"))
            if norm:
                provenance_produit = "dossier de planning"
    if not norm:
        norm = article_rvgi_unique(numero)
        if norm:
            provenance_produit = "commande RVGI"

    if not norm:
        return of

    fiche = choisir_fiche(conn, norm, machine=machine, laize=laize,
                          reference=ref_of or None)

    # La référence imprimée est la clé produit. Un OF dont la « référence »
    # est son propre numéro, ou le libellé complet de la fiche, s'imprimait
    # tel quel dans la case Réf.
    of["reference"] = norm
    # Access envoie dans `format` la référence complète de la fiche
    # (t_of.format = fiches.reference) : ce n'est pas un format.
    if _norm(of.get("format")) or (of.get("format") or "").strip() == numero:
        of["format"] = None

    if not fiche:
        of["_provenance_fiche"] = provenance_produit
        return of

    remplis: List[str] = []
    if _vide(of.get("format")) and not _vide(fiche.get("format")):
        of["format"] = fiche["format"]
        remplis.append("format")
    for col_of, col_ft in CORRESPONDANCES:
        if col_of == "laize" and _vide(fiche.get(col_ft)):
            col_ft = "laize"
        val = fiche.get(col_ft)
        if _vide(of.get(col_of)) and not _vide(val):
            of[col_of] = val
            remplis.append(col_of)

    # « Permanent 2028Y - 19 » → « 2028 » dans la case orange, comme avant.
    if _vide(of.get("ref_adhesif")) and not _vide(fiche.get("adhesif")):
        m = re.search(r"\b(\d{3,5})\b", str(fiche["adhesif"]))
        if m:
            of["ref_adhesif"] = m.group(1)
            remplis.append("ref_adhesif")

    of["_fiche_id"] = fiche.get("id")
    of["_provenance_fiche"] = provenance_produit
    of["_champs_depuis_fiche"] = remplis
    return of

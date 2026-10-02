"""
Le stock d'une matière, fournisseur par fournisseur et laize par laize.

MySifa tient son stock par matière et par laize : une bobine au magasin ne dit
pas de quel fournisseur elle vient. RVGI, lui, le tient par ARTICLE (un
fournisseur × une référence) et par laize — c'est ce que ces lignes montrent,
à côté du total MySifa, jamais à sa place. Décision d'Eugène du 02/10/2026 :
la quantité d'une ligne fournisseur est le stock RVGI de ses articles.

Lecture seule des deux côtés. Les règles de lecture de RVGI sont celles de la
comparaison des stocks (`stock_compare`) : dernier `qte2` de chaque laize de
chaque article, types de variante (>= 100) écartés, article rejoint par
`erp_article_matiere`. Pour une bobine, `qte2` est en mètres linéaires ; pour
le reste, la quantité passe dans l'unité du magasin par `reception_rvgi.convertir`.
"""

from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from app.services import reception_rvgi as rr
from app.services import stock_compare as sc
from app.services.fournisseurs_fusion import par_numero_rvgi


def _variantes_par_article(conn) -> Dict[tuple, Dict[str, Any]]:
    """(code1, code2, type d'achat) -> variante active et son fournisseur."""
    out: Dict[tuple, Dict[str, Any]] = {}
    try:
        for r in conn.execute(
                """SELECT v.id, v.rvgi_code1, v.rvgi_code2, v.rvgi_type_code, v.fournisseur_id,
                          v.libelle_technique, v.ml_bobine
                     FROM mp_variantes v
                    WHERE v.actif = 1 AND v.rvgi_code1 IS NOT NULL"""):
            out[(str(r[1]), str(r[2]), int(r[3] or 0))] = {
                "variante_id": r[0], "fournisseur_id": r[4], "libelle": r[5], "ml_bobine": r[6]}
    except sqlite3.OperationalError:
        pass
    return out


def stock_par_fournisseur(conn: sqlite3.Connection, matiere_id: Optional[int] = None,
                          conn_erp=None) -> Dict[str, Any]:
    """Lignes (matière, fournisseur, article, laize) du stock RVGI.

    Renvoie {disponible, motif, lignes[]}. Sans miroir RVGI, `disponible` est
    faux et l'écran le dit : une liste vide se lirait « aucun stock ».
    """
    try:
        stock_rvgi, fiches = sc._stock_rvgi_matieres(conn_erp)
    except Exception as e:  # miroir absent, table manquante
        return {"disponible": False, "motif": str(e) or "Miroir RVGI indisponible.", "lignes": []}

    appar = rr._appariements(conn)
    variantes = _variantes_par_article(conn)
    sql = """SELECT id, reference, designation, categorie, sous_section,
                    metres_lineaires_par_bobine, unites_par_palette
               FROM matieres_premieres WHERE COALESCE(actif, 1) = 1"""
    params: tuple = ()
    if matiere_id is not None:
        sql += " AND id = ?"
        params = (int(matiere_id),)
    matieres = {int(r[0]): dict(zip(("id", "reference", "designation", "categorie", "sous_section",
                                     "metres_lineaires_par_bobine", "unites_par_palette"), r))
                for r in conn.execute(sql, params)}
    noms = {int(r[0]): r[1] for r in conn.execute("SELECT id, nom FROM fournisseurs_fsc")}

    lignes: List[Dict[str, Any]] = []
    for r in stock_rvgi:
        type_mat = int(r["type"] or 0)
        type_achat = type_mat + sc._DECALAGE_TYPE
        code1, code2 = str(r["code1"]), str(r["code2"])
        mid = appar.get((code1, code2, type_achat))
        if mid is None or mid not in matieres:
            continue
        q = float(r["qte2"] or 0)
        if not q:
            continue
        m = matieres[mid]
        unite = rr.UNITE_GESTION.get((m.get("categorie") or "").strip().lower(), "palette")
        v = variantes.get((code1, code2, type_achat)) or {}
        fid = v.get("fournisseur_id") or par_numero_rvgi(conn, code1)
        conv = rr.convertir(type_achat, abs(q), m,
                            (fiches.get((code1, code2, type_mat)) or {}).get("libt2"), v.get("ml_bobine"))
        quantite = conv.get("quantite")
        if quantite is not None and q < 0:
            quantite = -quantite
        lignes.append({
            "matiere_id": mid,
            "fournisseur_id": fid,
            "fournisseur": noms.get(int(fid)) if fid else None,
            "variante_id": v.get("variante_id"),
            "libelle": v.get("libelle") or (fiches.get((code1, code2, type_mat)) or {}).get("libc1"),
            "article": "%s/%s" % (code1, code2),
            "laize_mm": sc._laize(r["code3"]) if unite == "bobine" else None,
            # Une bobine : RVGI compte en mètres linéaires, c'est la grandeur
            # qu'on affiche. Le reste : l'unité du magasin.
            "metres": round(q, 1) if unite == "bobine" else None,
            "quantite": round(quantite, 3) if quantite is not None else None,
            "unite": unite,
            "maj_le": r["amjh"],
        })
    lignes.sort(key=lambda l: (l["matiere_id"], (l["fournisseur"] or "~").lower(), l["laize_mm"] or 0, l["article"]))
    return {"disponible": True, "motif": None, "lignes": lignes}

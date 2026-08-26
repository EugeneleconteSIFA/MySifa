"""Comparer le stock de MySifa à celui de RVGI.

Le principe, et il compte : **on ne recopie rien**. RVGI reste la référence
comptable, MySifa la référence physique, et c'est l'écart entre les deux qui
est l'indicateur. Aucune de ces deux bases n'est corrigée par l'autre ici.

Quatre statuts, et chacun veut dire quelque chose de différent :

    ok           les deux disent la même quantité
    ecart        les deux connaissent l'article et ne sont pas d'accord
    rvgi_seul    RVGI porte du stock, MySifa ne connaît pas la référence
    mysifa_seul  MySifa porte du stock, RVGI ne connaît pas la référence

Les deux derniers ne sont pas des erreurs de saisie mais des trous de
référentiel : c'est leur volume qui dit si la clé de rapprochement tient.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.services import erp_stock

# En dessous, deux quantités sont considérées égales. Les stocks RVGI sont des
# entiers d'étiquettes ; le flottant, lui, ne l'est pas toujours.
TOLERANCE = 0.001

PERIMETRES = ("pf", "matiere")


def _maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ── Le côté MySifa ───────────────────────────────────────────────────────────

def index_mysifa(conn: sqlite3.Connection, perimetre: str) -> Dict[str, Dict[str, Any]]:
    """{référence: {stock, designation, maj_le}} tel que MySifa le connaît."""
    if perimetre == "pf":
        return _index_pf(conn)
    if perimetre == "matiere":
        return _index_matiere(conn)
    raise ValueError("Périmètre inconnu : %r" % (perimetre,))


def _index_pf(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    """Produits finis : la somme des lots encore ouverts.

    Un lot à quantité nulle ou négative ne compte pas : il est consommé. C'est
    la même règle que l'écran de stock, pour que les deux montrent le même
    chiffre — un outil de contrôle qui ne dit pas la même chose que l'écran
    qu'il contrôle ne sert à rien.
    """
    rows = conn.execute(
        """SELECT p.reference, p.designation,
                  COALESCE(SUM(CASE WHEN l.quantite_restante > 0
                                    THEN l.quantite_restante END), 0) AS stock,
                  MAX(l.date_entree) AS maj_le
             FROM produits p
             LEFT JOIN lots_stock l ON l.produit_id = p.id
            GROUP BY p.id"""
    ).fetchall()
    out: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        ref = str(r["reference"] or "").strip()
        if not ref:
            continue
        out[ref] = {"stock": float(r["stock"] or 0),
                    "designation": r["designation"],
                    "maj_le": r["maj_le"]}
    return out


def _index_matiere(conn: sqlite3.Connection) -> Dict[str, Dict[str, Any]]:
    """Matières : le stock courant, catégorie par catégorie.

    Attention : MySifa nomme ses matières par référence fournisseur, RVGI par
    `code1/code2`. Les deux ne se rejoignent que si quelqu'un a saisi la même
    chaîne des deux côtés. C'est exactement ce que la comparaison mesure.
    """
    cols = {r[1] for r in conn.execute("PRAGMA table_info(matieres_premieres)")}
    if not cols:
        return {}
    a_stock = bool({r[1] for r in conn.execute("PRAGMA table_info(mp_stock)")})
    sql = """SELECT m.reference, m.designation, m.categorie,
                    %s AS stock, %s AS maj_le
               FROM matieres_premieres m
               %s
              WHERE COALESCE(m.actif, 1) = 1""" % (
        "COALESCE(s.quantite, 0)" if a_stock else "0",
        "s.updated_at" if a_stock else "NULL",
        "LEFT JOIN mp_stock s ON s.matiere_id = m.id" if a_stock else "",
    )
    out: Dict[str, Dict[str, Any]] = {}
    for r in conn.execute(sql):
        ref = str(r["reference"] or "").strip()
        if not ref:
            continue
        # Une même référence dans deux catégories est possible : on additionne
        # plutôt que d'en perdre une en silence.
        cur = out.setdefault(ref, {"stock": 0.0, "designation": r["designation"],
                                   "maj_le": r["maj_le"]})
        cur["stock"] += float(r["stock"] or 0)
    return out


# ── La comparaison ───────────────────────────────────────────────────────────

def comparer(conn: sqlite3.Connection, perimetre: str) -> Dict[str, Any]:
    """Confronte les deux bases et rend les lignes, sans rien enregistrer."""
    rvgi = erp_stock.index_stock(perimetre)
    mysifa = index_mysifa(conn, perimetre)

    lignes: List[Dict[str, Any]] = []
    for ref in sorted(set(rvgi) | set(mysifa)):
        r = rvgi.get(ref)
        m = mysifa.get(ref)
        s_r = r["stock_erp"] if r else None
        s_m = m["stock"] if m else None

        if r and m:
            ecart = s_m - s_r
            statut = "ok" if abs(ecart) < TOLERANCE else "ecart"
        elif r:
            ecart = None
            statut = "rvgi_seul"
        else:
            ecart = None
            statut = "mysifa_seul"

        # Une référence que ni l'un ni l'autre ne porte en stock n'apprend
        # rien : elle gonflerait la liste de milliers d'articles dormants.
        if statut in ("rvgi_seul", "mysifa_seul") and not (s_r or s_m):
            continue

        lignes.append({
            "reference": ref,
            "designation": (r and r.get("designation")) or (m and m.get("designation")),
            "stock_rvgi": s_r,
            "stock_mysifa": s_m,
            "ecart": ecart,
            "statut": statut,
            "rvgi_mvt_libelle": r and r.get("mvt_libelle"),
            "rvgi_mvt_date": r and r.get("mvt_date"),
            "rvgi_mvt_qte": r and r.get("mvt_qte"),
            "mysifa_maj_le": m and m.get("maj_le"),
        })

    return {"perimetre": perimetre, "lignes": lignes,
            "compte": _compter(lignes, rvgi, mysifa)}


def _compter(lignes: List[Dict[str, Any]], rvgi: Dict, mysifa: Dict) -> Dict[str, Any]:
    communs = len(set(rvgi) & set(mysifa))
    ecarts = [l for l in lignes if l["statut"] == "ecart"]
    return {
        "nb_rvgi": len(rvgi),
        "nb_mysifa": len(mysifa),
        "nb_communs": communs,
        "nb_ecarts": len(ecarts),
        "nb_rvgi_seul": sum(1 for l in lignes if l["statut"] == "rvgi_seul"),
        "nb_mysifa_seul": sum(1 for l in lignes if l["statut"] == "mysifa_seul"),
        "nb_negatifs": sum(1 for l in lignes
                           if (l["stock_rvgi"] or 0) < 0 or (l["stock_mysifa"] or 0) < 0),
        "ecart_absolu": sum(abs(l["ecart"]) for l in ecarts),
        # Le chiffre qui dit si la clé de rapprochement tient. Sur les
        # matières, il vaudra peut-être zéro — et il faudra le savoir avant
        # d'exploiter quoi que ce soit d'autre.
        "taux_correspondance": (round(100.0 * communs / len(rvgi), 1) if rvgi else 0.0),
    }


# ── L'instantané ─────────────────────────────────────────────────────────────

def enregistrer(conn: sqlite3.Connection, perimetre: str, utilisateur: str = "",
                origine: str = "manuel") -> Dict[str, Any]:
    """Compare et garde la trace. C'est l'historique qui fait l'outil."""
    if perimetre not in PERIMETRES:
        raise ValueError("Périmètre inconnu : %r" % (perimetre,))
    res = comparer(conn, perimetre)
    c = res["compte"]

    releve = None
    try:
        from app.services import erp_mirror as miroir
        releve = miroir.meta().get("releve_le")
    except Exception:
        pass

    cur = conn.execute(
        """INSERT INTO stock_compare_instantanes
             (perimetre, cree_le, cree_par, origine, miroir_releve_le,
              nb_rvgi, nb_mysifa, nb_communs, nb_ecarts, nb_rvgi_seul,
              nb_mysifa_seul, nb_negatifs, ecart_absolu)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (perimetre, _maintenant(), utilisateur or None, origine, releve,
         c["nb_rvgi"], c["nb_mysifa"], c["nb_communs"], c["nb_ecarts"],
         c["nb_rvgi_seul"], c["nb_mysifa_seul"], c["nb_negatifs"], c["ecart_absolu"]),
    )
    inst = cur.lastrowid
    conn.executemany(
        """INSERT INTO stock_compare_lignes
             (instantane_id, reference, designation, stock_rvgi, stock_mysifa,
              ecart, statut, rvgi_mvt_libelle, rvgi_mvt_date, rvgi_mvt_qte, mysifa_maj_le)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        [(inst, l["reference"], l["designation"], l["stock_rvgi"], l["stock_mysifa"],
          l["ecart"], l["statut"], l["rvgi_mvt_libelle"], l["rvgi_mvt_date"],
          l["rvgi_mvt_qte"], l["mysifa_maj_le"]) for l in res["lignes"]],
    )
    return {"instantane_id": inst, **c}


def instantanes(conn: sqlite3.Connection, perimetre: str, limite: int = 40) -> List[Dict[str, Any]]:
    return [dict(r) for r in conn.execute(
        """SELECT * FROM stock_compare_instantanes
            WHERE perimetre = ? ORDER BY cree_le DESC LIMIT ?""",
        (perimetre, int(limite)))]


def lignes(conn: sqlite3.Connection, instantane_id: int, statut: str = "",
           q: str = "", limite: int = 500) -> Dict[str, Any]:
    ou, params = ["instantane_id = ?"], [int(instantane_id)]
    if statut:
        ou.append("statut = ?")
        params.append(statut)
    if q:
        ou.append("(reference LIKE ? OR designation LIKE ?)")
        params += ["%" + q + "%"] * 2
    where = " WHERE " + " AND ".join(ou)
    total = conn.execute(
        "SELECT COUNT(*) FROM stock_compare_lignes" + where, params).fetchone()[0]
    rows = conn.execute(
        # Le plus gros écart d'abord : c'est celui qui coûte, et personne ne
        # descend au bout d'une liste de deux mille lignes.
        "SELECT * FROM stock_compare_lignes" + where +
        " ORDER BY CASE WHEN ecart IS NULL THEN 1 ELSE 0 END, ABS(COALESCE(ecart,0)) DESC,"
        " ABS(COALESCE(stock_rvgi, stock_mysifa, 0)) DESC LIMIT ?",
        params + [int(limite)]).fetchall()
    return {"total": total, "lignes": [dict(r) for r in rows],
            "tronque": total > len(rows)}


def suivi(conn: sqlite3.Connection, reference: str, perimetre: str,
          limite: int = 30) -> List[Dict[str, Any]]:
    """L'histoire d'un écart, instantané par instantané.

    C'est ce qui distingue un écart corrigé d'un écart masqué.
    """
    return [dict(r) for r in conn.execute(
        """SELECT i.cree_le, i.origine, l.stock_rvgi, l.stock_mysifa, l.ecart, l.statut
             FROM stock_compare_lignes l
             JOIN stock_compare_instantanes i ON i.id = l.instantane_id
            WHERE l.reference = ? AND i.perimetre = ?
            ORDER BY i.cree_le DESC LIMIT ?""",
        (reference, perimetre, int(limite)))]

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

Matières : la clé est l'appariement, par laize
----------------------------------------------
Les produits finis se rejoignent sur la référence « XXX/NNNN », la même des
deux côtés. Les matières non : MySifa les nomme par leur libellé commercial,
RVGI par article fournisseur (code1/code2/type), et une matière en a souvent
plusieurs. Les deux côtés se rejoignent donc par `erp_article_matiere`, la
table d'appariement des réceptions — celle qui fait entrer le stock —, et la
quantité RVGI est traduite dans l'unité du magasin par
`reception_rvgi.convertir`, le même code que l'entrée en stock.

Et RVGI tient le stock d'une matière PAR LAIZE : chaque mouvement de
`stm_hist` porte sa laize (`code3`) et le stock restant de cette laize
(`qte2`). Relevé du 02/10/2026 sur 1183/0004 : 574 523 m en 510, 429 694 en
530, 401 381 en 570. Le stock d'un article est la somme de ses laizes — le
dernier mouvement, toutes laizes confondues, ne donne que la laize qui a bougé
en dernier. La comparaison se fait donc par matière ET par laize, contre
`mp_stock_laize`.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.services import erp_stock
from app.services import reception_rvgi as rr

# En dessous, deux quantités sont considérées égales. Les stocks RVGI sont des
# entiers d'étiquettes ; le flottant, lui, ne l'est pas toujours.
TOLERANCE = 0.001

PERIMETRES = ("pf", "matiere")


def _maintenant() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ── Le côté MySifa ───────────────────────────────────────────────────────────

def index_mysifa(conn: sqlite3.Connection, perimetre: str) -> Dict[str, Dict[str, Any]]:
    """{référence: {stock, designation, maj_le}} tel que MySifa le connaît (produits finis).

    Les matières ne passent pas par une référence texte : voir `_comparer_matiere`.
    """
    if perimetre == "pf":
        return _index_pf(conn)
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


# ── La comparaison ───────────────────────────────────────────────────────────

def comparer(conn: sqlite3.Connection, perimetre: str) -> Dict[str, Any]:
    """Confronte les deux bases et rend les lignes, sans rien enregistrer."""
    if perimetre == "matiere":
        return _comparer_matiere(conn)
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


# ── Matières : par appariement et par laize ──────────────────────────────────

# Le stock restant de chaque laize de chaque article : le `qte2` de son dernier
# mouvement. Les types >= 100 sont les doublons de variante que RVGI écrit à
# chaque réception (cf. ecarts_mouvements_rvgi) : les compter doublerait tout.
_SQL_STOCK_RVGI = """
    SELECT h.code1, h.code2, h.type, h.code3, h.qte2, h.qte1, h.amjh, h.des1
      FROM stm_hist h
      JOIN (SELECT code1, code2, type, COALESCE(code3, '') AS c3,
                   MAX(amjh || '#' || printf('%012d', id)) AS mx
              FROM stm_hist WHERE type < 100
             GROUP BY code1, code2, type, COALESCE(code3, '')) d
        ON d.code1 IS h.code1 AND d.code2 IS h.code2 AND d.type = h.type
       AND d.c3 = COALESCE(h.code3, '')
       AND d.mx = h.amjh || '#' || printf('%012d', h.id)
"""

# stm_hist.type = type d'achat - 2 (même décalage que les mouvements).
_DECALAGE_TYPE = 2


def _laize(v) -> Optional[float]:
    try:
        f = float(str(v).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def _cle_laize(lz: Optional[float]) -> Optional[float]:
    return round(lz) if lz else None


def _lire_stock_rvgi(c) -> Tuple[List[Dict[str, Any]], Dict[Tuple[str, str, int], Dict[str, Any]]]:
    from app.services import erp_mirror as miroir
    presentes = miroir.tables_presentes(c)
    if "stm_hist" not in presentes:
        raise FileNotFoundError("La table « stm_hist » n'est pas dans le miroir : lancer la synchro RVGI.")
    lignes = [dict(r) for r in c.execute(_SQL_STOCK_RVGI)]
    fiches: Dict[Tuple[str, str, int], Dict[str, Any]] = {}
    if "mat_mat" in presentes:
        for r in c.execute("SELECT code1, code2, type, libc1, libt2 FROM mat_mat WHERE corbeille = 0"):
            fiches.setdefault((str(r["code1"]), str(r["code2"]), int(r["type"] or 0)),
                              {"libc1": r["libc1"], "libt2": r["libt2"]})
    return lignes, fiches


def _stock_rvgi_matieres(conn_erp=None):
    """Le stock RVGI par (article, laize), et la fiche de chaque article."""
    if conn_erp is not None:
        return _lire_stock_rvgi(conn_erp)
    from app.services import erp_mirror as miroir
    with miroir.get_erp_db() as c:
        return _lire_stock_rvgi(c)


def _comparer_matiere(conn: sqlite3.Connection, conn_erp=None) -> Dict[str, Any]:
    from app.services.ecarts_mouvements_rvgi import _tolerance

    stock_rvgi, fiches = _stock_rvgi_matieres(conn_erp)
    appar = rr._appariements(conn)
    ml_var = rr.ml_variantes(conn)
    matieres = {int(r["id"]): dict(r) for r in conn.execute(
        """SELECT id, reference, designation, categorie, sous_section,
                  metres_lineaires_par_bobine, unites_par_palette
             FROM matieres_premieres WHERE COALESCE(actif, 1) = 1""")}

    def unite(mid):
        return rr.UNITE_GESTION.get((matieres[mid].get("categorie") or "").strip().lower(), "palette")

    # (matiere_id, laize arrondie | None) -> agrégat
    cles: Dict[Tuple[int, Optional[float]], Dict[str, Any]] = {}

    def agregat(mid, lz):
        cle = (mid, _cle_laize(lz) if unite(mid) == "bobine" else None)
        if cle not in cles:
            cles[cle] = {"rvgi": None, "mysifa": None, "articles": set(), "non_convertibles": 0,
                         "mvt": None, "maj_le": None}
        return cles[cle]

    rvgi_seuls: Dict[str, Dict[str, Any]] = {}
    nb_articles_rvgi: set = set()
    for r in stock_rvgi:
        type_mat = int(r["type"] or 0)
        type_achat = type_mat + _DECALAGE_TYPE
        code1, code2 = str(r["code1"]), str(r["code2"])
        q = float(r["qte2"] or 0)
        mid = appar.get((code1, code2, type_achat))
        article = "%s/%s" % (code1, code2)
        lz = _laize(r["code3"])
        mvt = {"libelle": r["des1"] or None, "date": r["amjh"] or None,
               "qte": float(r["qte1"]) if r["qte1"] is not None else None}
        if mid is None or mid not in matieres:
            # Un article hors du périmètre des matières suivies (outillage,
            # consommables) n'est pas un trou de référentiel.
            if type_achat not in rr.PERIMETRE or not q:
                continue
            nb_articles_rvgi.add((code1, code2, type_achat))
            ref = article + (" · %g mm" % lz if lz else "")
            rvgi_seuls[ref] = {
                "designation": "%s (article RVGI non apparié)" % ((fiches.get((code1, code2, type_mat)) or {}).get("libc1") or article),
                "stock_rvgi": q, "mvt": mvt,
            }
            continue
        nb_articles_rvgi.add((code1, code2, type_achat))
        a = agregat(mid, lz)
        a["articles"].add(article)
        if a["mvt"] is None or (mvt["date"] or "") > (a["mvt"]["date"] or ""):
            a["mvt"] = mvt
        if not q:
            a["rvgi"] = a["rvgi"] or 0.0
            continue
        conv = rr.convertir(type_achat, abs(q), matieres[mid],
                            (fiches.get((code1, code2, type_mat)) or {}).get("libt2"),
                            ml_var.get((code1, code2, type_achat)))
        if conv.get("quantite") is None:
            a["non_convertibles"] += 1
            continue
        a["rvgi"] = (a["rvgi"] or 0.0) + (conv["quantite"] if q > 0 else -conv["quantite"])

    # MySifa : par laize pour les bobines, la fiche entière sinon.
    laizes = {int(r["id"]): float(r["valeur_mm"]) for r in conn.execute("SELECT id, valeur_mm FROM mp_laizes")}
    par_laize = set()
    for r in conn.execute("SELECT matiere_id, laize_id, quantite, updated_at FROM mp_stock_laize"):
        mid = int(r["matiere_id"])
        if mid not in matieres or unite(mid) != "bobine":
            continue
        par_laize.add(mid)
        a = agregat(mid, laizes.get(int(r["laize_id"] or 0)))
        a["mysifa"] = (a["mysifa"] or 0.0) + float(r["quantite"] or 0)
        a["maj_le"] = max(filter(None, [a["maj_le"], r["updated_at"]]), default=None)
    for r in conn.execute("SELECT matiere_id, quantite, updated_at FROM mp_stock"):
        mid = int(r["matiere_id"])
        if mid not in matieres or mid in par_laize:
            continue
        a = agregat(mid, None)
        a["mysifa"] = (a["mysifa"] or 0.0) + float(r["quantite"] or 0)
        a["maj_le"] = r["updated_at"]

    lignes: List[Dict[str, Any]] = []
    for (mid, lz), a in sorted(cles.items(), key=lambda kv: (matieres[kv[0][0]].get("reference") or "", kv[0][1] or 0)):
        m = matieres[mid]
        s_r, s_m = a["rvgi"], a["mysifa"]
        s_r = round(s_r, 3) if s_r is not None else None
        s_m = round(s_m, 3) if s_m is not None else None
        if not a["articles"]:
            statut = "mysifa_seul"
        elif s_m is None:
            statut = "rvgi_seul"
        else:
            statut = "ok" if abs((s_m or 0) - (s_r or 0)) <= _tolerance(unite(mid), s_r, s_m) else "ecart"
        if statut in ("rvgi_seul", "mysifa_seul") and not (s_r or s_m):
            continue
        if statut == "ok" and not (s_r or s_m):
            continue
        designation = m.get("designation") or m.get("reference")
        if a["articles"]:
            designation += " — RVGI " + ", ".join(sorted(a["articles"]))
        if a["non_convertibles"]:
            designation += " (%d laize(s) RVGI non convertible(s))" % a["non_convertibles"]
        lignes.append({
            "reference": (m.get("reference") or str(mid)) + (" · %g mm" % lz if lz else ""),
            "designation": designation,
            "stock_rvgi": s_r if a["articles"] else None,
            "stock_mysifa": s_m,
            "ecart": round((s_m or 0) - (s_r or 0), 3) if statut in ("ok", "ecart") else None,
            "statut": statut,
            "rvgi_mvt_libelle": a["mvt"] and a["mvt"]["libelle"],
            "rvgi_mvt_date": a["mvt"] and a["mvt"]["date"],
            "rvgi_mvt_qte": a["mvt"] and a["mvt"]["qte"],
            "mysifa_maj_le": a["maj_le"],
        })
    for ref, v in sorted(rvgi_seuls.items()):
        lignes.append({
            "reference": ref, "designation": v["designation"], "stock_rvgi": v["stock_rvgi"],
            "stock_mysifa": None, "ecart": None, "statut": "rvgi_seul",
            "rvgi_mvt_libelle": v["mvt"]["libelle"], "rvgi_mvt_date": v["mvt"]["date"],
            "rvgi_mvt_qte": v["mvt"]["qte"], "mysifa_maj_le": None,
        })

    communs = sum(1 for l in lignes if l["statut"] in ("ok", "ecart"))
    ecarts = [l for l in lignes if l["statut"] == "ecart"]
    nb_rvgi = communs + sum(1 for l in lignes if l["statut"] == "rvgi_seul")
    compte = {
        "nb_rvgi": nb_rvgi,
        "nb_mysifa": communs + sum(1 for l in lignes if l["statut"] == "mysifa_seul"),
        "nb_communs": communs,
        "nb_ecarts": len(ecarts),
        "nb_rvgi_seul": sum(1 for l in lignes if l["statut"] == "rvgi_seul"),
        "nb_mysifa_seul": sum(1 for l in lignes if l["statut"] == "mysifa_seul"),
        "nb_negatifs": sum(1 for l in lignes
                           if (l["stock_rvgi"] or 0) < 0 or (l["stock_mysifa"] or 0) < 0),
        "ecart_absolu": round(sum(abs(l["ecart"]) for l in ecarts), 3),
        # Part des lignes RVGI qui trouvent leur matière : c'est la couverture
        # des appariements, la clé de toute la comparaison.
        "taux_correspondance": round(100.0 * communs / nb_rvgi, 1) if nb_rvgi else 0.0,
        "articles_rvgi": len(nb_articles_rvgi),
    }
    return {"perimetre": "matiere", "lignes": lignes, "compte": compte}


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

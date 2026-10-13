"""Les encres, matières premières tenues dans RVGI.

MyStock ne mouvemente pas les encres : leur stock vit dans RVGI. Plutôt que de
le ressaisir, on crée une matière « encre » par article encre du miroir
(`mat_mat.type = 8`) et on y recopie la quantité RVGI — le `qte2` du dernier
mouvement, cf. `erp_stock`. Le prix d'achat RVGI (€/kg) est repris tant
qu'aucun prix n'a été saisi dans Coûts matières.

Le lien article ↔ matière passe par `erp_article_matiere`, dont `type_code` est
le type de la LIGNE D'ACHAT (`mat_mat.type + 2`, cf. erp_types) : 10 pour une
encre.
"""

import logging
from datetime import datetime

from app.services import erp_mirror as miroir
from app.services import erp_stock

logger = logging.getLogger(__name__)

CATEGORIE = "encre"
TYPE_ARTICLE = 8
TYPE_LIGNE_ACHAT = TYPE_ARTICLE + 2
# RVGI écrit 99 999 999 999,99 ou 999 999 999 999,99 sur un article dont il ne
# suit pas le stock : ce n'est pas une quantité, la reprendre ferait exploser la
# valorisation. Aucune encre ne se compte en milliards de kilos.
STOCK_NON_SUIVI = 1e10


def _prix_kg(pa, pafou1) -> float:
    """Prix d'achat RVGI au kilo : `pa`, ou à défaut le tarif de 1re tranche."""
    for v in (pa, pafou1):
        try:
            f = float(v or 0)
        except (TypeError, ValueError):
            continue
        if f > 0:
            return f
    return 0.0


def _articles_rvgi() -> list[dict]:
    with miroir.get_erp_db() as conn:
        if "mat_mat" not in miroir.tables_presentes(conn):
            return []
        rows = conn.execute(
            "SELECT code1, code2, libc1, pa, pafou1 FROM mat_mat WHERE corbeille = 0 AND type = ?",
            (TYPE_ARTICLE,),
        ).fetchall()
    return [
        {"code1": str(r["code1"]).strip(), "code2": str(r["code2"]).strip(),
         "libelle": (r["libc1"] or "").strip(),
         "prix": _prix_kg(r["pa"], r["pafou1"])}
        for r in rows if str(r["code1"] or "").strip()
    ]


def synchroniser(conn) -> dict:
    """Crée les matières encre manquantes et recopie leur stock RVGI.

    Idempotent. Ne lève pas : une synchro RVGI indisponible ne doit pas
    empêcher d'afficher la valorisation.
    """
    try:
        articles = _articles_rvgi()
        stocks = erp_stock.index_stock("matiere") if articles else {}
    except Exception:
        logger.exception("encres : lecture du miroir RVGI impossible")
        return {"ok": False, "creees": 0, "mises_a_jour": 0}

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    creees = maj = 0
    for a in articles:
        ref = erp_stock._reference(a["code1"], a["code2"])
        lien = conn.execute(
            """SELECT matiere_id FROM erp_article_matiere
                WHERE code1=? AND code2=? AND type_code=?""",
            (a["code1"], a["code2"], TYPE_LIGNE_ACHAT),
        ).fetchone()
        if lien:
            mid = int(lien[0])
        else:
            existante = conn.execute(
                "SELECT id FROM matieres_premieres WHERE categorie=? AND reference=?",
                (CATEGORIE, ref),
            ).fetchone()
            if existante:
                mid = int(existante[0])
            else:
                mid = int(conn.execute(
                    """INSERT INTO matieres_premieres (categorie, reference, designation, seuil_alerte)
                       VALUES (?,?,?,0)""",
                    (CATEGORIE, ref, a["libelle"] or ref),
                ).lastrowid)
                # Une déclinaison unique au kilo et sa ligne de prix vide, comme
                # une matière « autre ». `add_declinaison` refuse une catégorie
                # qui ne se décline pas : on les pose ici.
                did = int(conn.execute(
                    """INSERT INTO mp_matiere_declinaison
                       (matiere_id, laize_id, grammage_id, price_basis, applique_marge)
                       VALUES (?,NULL,NULL,'PER_KG',1)""",
                    (mid,),
                ).lastrowid)
                conn.execute(
                    """INSERT INTO mp_matiere_prix
                       (matiere_id, laize_id, grammage_id, declinaison_id, fournisseur_id,
                        prix, principal, updated_at)
                       VALUES (?,NULL,NULL,?,NULL,0,1,?)""",
                    (mid, did, now),
                )
                creees += 1
            conn.execute(
                """INSERT OR IGNORE INTO erp_article_matiere
                   (code1, code2, type_code, matiere_id, origine, created_at, created_by_name)
                   VALUES (?,?,?,?,'encre_rvgi',?,'Synchro RVGI')""",
                (a["code1"], a["code2"], TYPE_LIGNE_ACHAT, mid, now),
            )
        # Prix RVGI repris tant qu'aucun prix n'a été saisi : une saisie dans
        # Coûts matières (prix > 0) n'est jamais écrasée.
        if a["prix"] > 0:
            conn.execute(
                """UPDATE mp_matiere_prix SET prix=?, updated_at=?
                    WHERE matiere_id=? AND COALESCE(prix,0)=0""",
                (a["prix"], now, mid),
            )
            # Miroir MyStock du prix (lu par la valorisation et « Ajuster le
            # conditionnement ») : même règle, un prix saisi n'est pas écrasé.
            v = conn.execute(
                "SELECT prix_unitaire FROM mp_valorisation WHERE matiere_id=?", (mid,)
            ).fetchone()
            if v is None:
                conn.execute(
                    """INSERT INTO mp_valorisation (matiere_id, prix_unitaire, updated_at, updated_by_name)
                       VALUES (?,?,?,'Synchro RVGI')""",
                    (mid, a["prix"], now),
                )
            elif not float(v[0] or 0):
                conn.execute(
                    """UPDATE mp_valorisation SET prix_unitaire=?, updated_at=?, updated_by_name='Synchro RVGI'
                        WHERE matiere_id=?""",
                    (a["prix"], now, mid),
                )
        qte = float((stocks.get(ref) or {}).get("stock_erp") or 0)
        if abs(qte) >= STOCK_NON_SUIVI:
            qte = 0.0
        cur = conn.execute(
            """UPDATE mp_stock SET quantite=?, updated_at=?, updated_by_name='Synchro RVGI'
                WHERE matiere_id=? AND COALESCE(quantite,0)<>?""",
            (qte, now, mid, qte),
        )
        if cur.rowcount:
            maj += 1
        elif not conn.execute("SELECT 1 FROM mp_stock WHERE matiere_id=?", (mid,)).fetchone():
            conn.execute("INSERT INTO mp_stock (matiere_id, quantite) VALUES (?,?)", (mid, qte))
            maj += 1
    conn.commit()
    return {"ok": True, "creees": creees, "mises_a_jour": maj, "articles": len(articles)}

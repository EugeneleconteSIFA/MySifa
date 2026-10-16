"""Rapprochement d'une facture fournisseur avec ses réceptions et la commande.

Pour chaque ligne facturée : la quantité reçue (ligne de réception d'origine,
moins ce que d'autres factures en ont déjà repris) et le prix commandé (ligne
de commande fournisseur d'origine de la réception), ramené à la base de prix
de la ligne facturée. Les écarts se lisent en centimes ; aucun ne bloque la
validation (l'écran les affiche, la comptabilité tranche).
"""
from __future__ import annotations

from app.services.gc import calculs

ETATS = {"ok": "Conforme", "ecart_prix": "Écart de prix", "ecart_qte": "Écart de quantité",
         "ecart_prix_qte": "Écarts de prix et de quantité", "sans_reception": "Sans réception"}


def _ligne(conn, ligne_id):
    if not ligne_id:
        return None
    return conn.execute(
        """SELECT l.*, p.type AS piece_type, p.numero AS piece_numero FROM gc_pieces_lignes l
           JOIN gc_pieces p ON p.id=l.piece_id WHERE l.id=?""", (ligne_id,)).fetchone()


def _prix_ramene(prix_cents: int, base_source: int, base_cible: int) -> int:
    """Prix exprimé pour `base_source` unités, ramené à `base_cible` unités."""
    return calculs.div_arrondi(int(prix_cents) * max(1, int(base_cible or 1)), max(1, int(base_source or 1)))


def rapprochement(conn, piece_id: int) -> dict:
    p = conn.execute("SELECT id, type, statut FROM gc_pieces WHERE id=?", (piece_id,)).fetchone()
    if not p or p["type"] != "facture_fournisseur":
        return {"lignes": [], "ecart_total_cents": 0, "nb_ecarts": 0}
    out = []
    for l in conn.execute(
        """SELECT l.*, a.code AS article_code, a.unite AS article_unite FROM gc_pieces_lignes l
           JOIN gc_articles a ON a.id=l.article_id WHERE l.piece_id=? ORDER BY l.rang""", (piece_id,)).fetchall():
        rec = _ligne(conn, l["ligne_amont_id"])
        if rec is not None and rec["piece_type"] != "reception":
            rec = None
        cde = _ligne(conn, rec["ligne_amont_id"]) if rec is not None else None
        d = {"ligne_id": l["id"], "rang": l["rang"], "article_code": l["article_code"], "libelle": l["libelle"],
             "unite": l["unite"] or l["article_unite"], "base_prix": l["base_prix"],
             "qte_facturee_milli": int(l["quantite_milli"]), "prix_facture_cents": int(l["prix_cents"] or 0),
             "montant_facture_cents": int(l["montant_ht_cents"] or 0),
             "reception": rec["piece_numero"] if rec is not None else None,
             "commande": cde["piece_numero"] if cde is not None else None,
             "qte_recue_milli": None, "prix_commande_cents": None, "ecart_qte_milli": 0, "ecart_prix_cents": 0,
             "ecart_montant_cents": 0}
        if rec is None:
            d["etat"] = "sans_reception"
            out.append(d)
            continue
        autres = conn.execute(
            """SELECT COALESCE(SUM(lv.quantite_milli),0) q FROM gc_pieces_lignes lv JOIN gc_pieces pv ON pv.id=lv.piece_id
               WHERE lv.ligne_amont_id=? AND pv.type='facture_fournisseur' AND pv.statut!='annule' AND pv.id!=?""",
            (rec["id"], piece_id)).fetchone()["q"]
        d["qte_recue_milli"] = max(0, int(rec["quantite_milli"]) - int(autres))
        d["ecart_qte_milli"] = d["qte_facturee_milli"] - d["qte_recue_milli"]
        ref = cde if cde is not None else rec
        d["prix_commande_cents"] = _prix_ramene(ref["prix_cents"] or 0, ref["base_prix"], l["base_prix"])
        d["ecart_prix_cents"] = d["prix_facture_cents"] - d["prix_commande_cents"]
        attendu = calculs.montant_ligne(d["qte_recue_milli"], d["prix_commande_cents"], l["base_prix"], ref["remise_bp"] or 0)
        d["montant_attendu_cents"] = attendu
        d["ecart_montant_cents"] = d["montant_facture_cents"] - attendu
        prix_ko, qte_ko = d["ecart_prix_cents"] != 0, d["ecart_qte_milli"] != 0
        d["etat"] = "ecart_prix_qte" if prix_ko and qte_ko else "ecart_prix" if prix_ko else "ecart_qte" if qte_ko else "ok"
        out.append(d)
    ecarts = [d for d in out if d["etat"] != "ok"]
    return {"lignes": out, "ecart_total_cents": sum(d["ecart_montant_cents"] for d in out), "nb_ecarts": len(ecarts),
            "etats": ETATS}


def _q(m: int) -> str:
    return f"{m / 1000:,.3f}".rstrip("0").rstrip(".").replace(",", " ").replace(".", ",")


def _e(c: int) -> str:
    return f"{c / 100:,.2f}".replace(",", " ").replace(".", ",") + " €"


def alertes(conn, piece_id: int) -> list[str]:
    """Messages courts pour la validation d'une facture fournisseur."""
    out = []
    for d in rapprochement(conn, piece_id)["lignes"]:
        if d["etat"] == "sans_reception":
            out.append(f"Ligne {d['rang']} ({d['article_code']}) : facturée sans réception.")
            continue
        if d["ecart_qte_milli"]:
            out.append(f"Ligne {d['rang']} ({d['article_code']}) : facturé {_q(d['qte_facturee_milli'])}, "
                       f"reçu {_q(d['qte_recue_milli'])} {d['unite'] or ''}.".replace(" .", "."))
        if d["ecart_prix_cents"]:
            out.append(f"Ligne {d['rang']} ({d['article_code']}) : prix facturé {_e(d['prix_facture_cents'])}, "
                       f"commandé {_e(d['prix_commande_cents'])} (écart {_e(d['ecart_montant_cents'])} sur la ligne).")
    return out

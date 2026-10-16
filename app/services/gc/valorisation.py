"""Valorisation du stock de l'ERP à une date.

Règle (Eugène, 16/10/2026) : prix et quantité à la date de la valorisation, plus
les paramètres complémentaires de MyStock › Valorisation.

- Quantité à la date D : somme des mouvements jusqu'à D inclus, par article,
  dépôt et laize. Le journal est signé et daté : pas de reconstitution. Une
  quantité négative compte pour zéro (signalée).
- Prix à la date D, dans cet ordre :
  1. le dernier prix de stock de l'historique valable à D ;
  2. matière : le prix de la dernière réception jusqu'à D (valeur / quantité) ;
  3. le prix de la fiche : prix d'achat pour une matière, prix de vente pour
     un produit fini ;
  sinon la ligne est « sans prix » et vaut zéro.
  Matière en laize avec un prix au m² : valeur = mètres linéaires × laize × prix.
- Paramètres complémentaires, lus dans MyStock (`mc_setting`), jamais recopiés :
  charges de production (réduction appliquée aux produits finis) et frais de
  stockage (majoration du total). Comme MyStock, ils sont lus à leur valeur
  actuelle quelle que soit la date.
"""
from __future__ import annotations

from app.services.gc import calculs

PARAMETRES = {"charge_production_pct": "Charges de production (produits finis)",
              "storage_fees_pct": "Frais de stockage"}


def parametres(conn) -> dict:
    out = {k: 0.0 for k in PARAMETRES}
    try:
        for r in conn.execute(
                f"SELECT key, value_decimal FROM mc_setting WHERE key IN ({','.join('?' * len(PARAMETRES))})",
                tuple(PARAMETRES)).fetchall():
            out[r["key"]] = float(r["value_decimal"] or 0)
    except Exception:
        pass        # MyStock absent : pas de paramètre complémentaire
    return out


def historiser(conn, article_id: int, avant: dict | None, apres: dict, user: dict | None = None, jour: str | None = None):
    """Trace un changement du prix de stock (appelé à l'enregistrement de la fiche)."""
    from datetime import datetime
    a = avant or {}
    if (a.get("prix_stock_cents"), a.get("prix_stock_m2_cents")) == (apres.get("prix_stock_cents"), apres.get("prix_stock_m2_cents")):
        return
    now = datetime.now()
    conn.execute(
        """INSERT INTO gc_prix_stock_historique (article_id, prix_cents, prix_m2_cents, depuis, cree_par, cree_le)
           VALUES (?,?,?,?,?,?)""",
        (article_id, apres.get("prix_stock_cents"), apres.get("prix_stock_m2_cents"), jour or now.strftime("%Y-%m-%d"),
         str((user or {}).get("nom") or ""), now.strftime("%Y-%m-%dT%H:%M:%S")))


def valoriser(conn, date: str) -> dict:
    d = str(date)[:10]
    lignes = conn.execute(
        """SELECT a.id, a.code, a.libelle, a.nature, a.famille, a.unite, a.base_prix, a.prix_achat_cents, a.prix_vente_cents,
                  a.prix_stock_cents, a.prix_stock_m2_cents, m.depot, m.laize_dmm, SUM(m.quantite_milli) AS q
           FROM gc_mouvements m JOIN gc_articles a ON a.id=m.article_id
           WHERE substr(m.date_mvt,1,10) <= ? AND a.gere_stock=1
           GROUP BY a.id, m.depot, m.laize_dmm HAVING SUM(m.quantite_milli) != 0
           ORDER BY a.nature, a.famille, a.code, m.depot, m.laize_dmm""", (d,)).fetchall()
    items = []
    for r in lignes:
        x = dict(r)
        q = int(x.pop("q"))
        x["negatif"] = q < 0
        x["quantite_milli"] = max(0, q)
        base = max(1, int(x["base_prix"] or 1))
        h = conn.execute(
            """SELECT prix_cents, prix_m2_cents FROM gc_prix_stock_historique WHERE article_id=? AND depuis <= ?
               ORDER BY depuis DESC, id DESC LIMIT 1""", (x["id"], d)).fetchone()
        prix, prix_m2, source = None, None, None
        if h and (h["prix_cents"] is not None or h["prix_m2_cents"] is not None):
            prix, prix_m2, source = h["prix_cents"], h["prix_m2_cents"], "historique"
        elif x["prix_stock_cents"] is not None or x["prix_stock_m2_cents"] is not None:
            # Prix de la fiche sans historique antérieur à D : seulement s'il n'a
            # jamais changé depuis (sinon il serait dans l'historique).
            if not conn.execute("SELECT 1 FROM gc_prix_stock_historique WHERE article_id=?", (x["id"],)).fetchone():
                prix, prix_m2, source = x["prix_stock_cents"], x["prix_stock_m2_cents"], "fiche"
        if source is None and x["nature"] == "mp":
            rec = conn.execute(
                """SELECT valeur_cents, quantite_milli FROM gc_mouvements WHERE article_id=? AND type='reception'
                   AND substr(date_mvt,1,10) <= ? AND quantite_milli > 0 AND valeur_cents IS NOT NULL
                   ORDER BY date_mvt DESC, id DESC LIMIT 1""", (x["id"], d)).fetchone()
            if rec and rec["valeur_cents"]:
                # valeur d'une ligne de réception pour sa quantité → prix pour `base` unités
                prix = calculs.div_arrondi(int(rec["valeur_cents"]) * 1000 * base, int(rec["quantite_milli"]))
                source = "reception"
        if source is None:
            p = x["prix_achat_cents"] if x["nature"] == "mp" else x["prix_vente_cents"]
            if p is not None:
                prix, source = p, "fiche_achat" if x["nature"] == "mp" else "fiche_vente"
        if prix_m2 is not None and x["laize_dmm"] and (x["unite"] or "").upper() == "ML":
            # m² = ML × laize (dixièmes de mm → m : / 10 000)
            valeur = calculs.div_arrondi(x["quantite_milli"] * int(x["laize_dmm"]) * int(prix_m2), 1000 * 10000)
            x["prix_affiche"] = f"{prix_m2 / 100:.4f} €/m²".replace(".", ",")
        elif prix is not None:
            valeur = calculs.montant_ligne(x["quantite_milli"], int(prix), base)
        else:
            valeur, source = 0, "aucun"
        x.update(prix_cents=prix, prix_m2_cents=prix_m2, source_prix=source, valeur_cents=int(valeur))
        for k in ("prix_achat_cents", "prix_vente_cents", "prix_stock_cents", "prix_stock_m2_cents"):
            x.pop(k, None)
        items.append(x)

    P = parametres(conn)
    tot = lambda nat: sum(i["valeur_cents"] for i in items if i["nature"] == nat)
    mp, pf, autre = tot("mp"), tot("pf"), sum(i["valeur_cents"] for i in items if i["nature"] not in ("mp", "pf"))
    charge = int(round(pf * P["charge_production_pct"] / 100))
    pf_net = pf - charge
    sous_total = mp + pf_net + autre
    frais = int(round(sous_total * P["storage_fees_pct"] / 100))
    return {
        "date": d, "items": items, "parametres": P, "libelles_parametres": PARAMETRES,
        "totaux": {"mp_cents": mp, "pf_brut_cents": pf, "charge_production_cents": charge, "pf_net_cents": pf_net,
                   "autre_cents": autre, "frais_stockage_cents": frais, "total_cents": sous_total + frais},
        "sans_prix": sum(1 for i in items if i["source_prix"] == "aucun"),
        "negatifs": sum(1 for i in items if i["negatif"]),
    }

"""Lien ERP ↔ MyAO : une demande de prix MyAO devient une commande fournisseur.

MyAO garde la main sur la consultation (envoi, portail fournisseur,
comparaison, clôture). L'ERP lit ses tables en lecture seule et, pour une
demande clôturée, prépare une commande fournisseur en BROUILLON chez le
fournisseur retenu : quantité de la ligne (ou de la série choisie), prix de
sa réponse. La commande garde la référence de la demande (`origine='myao'`,
`origine_ref`) : une demande déjà transformée le dit.

Prix MyAO : `quotation` au mille ou à la bobine, en EUR ou USD. Au mille →
prix de l'article pour 1 000. À la bobine → le nombre d'étiquettes par bobine
n'est pas connu de l'ERP : le prix reste à saisir (la ligne le signale). USD →
converti en euros au taux de MyStock (`mc_setting.eur_usd_rate`), mentionné
dans les notes internes de la commande.
"""
from __future__ import annotations

from datetime import datetime

from app.services.gc import pieces
from app.services.gc.pieces import ErreurPiece


def _tables(conn) -> set[str]:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}


def disponible(conn) -> bool:
    return {"ao_demandes", "ao_lignes", "ao_fournisseurs", "ao_reponses"} <= _tables(conn)


def demandes(conn) -> list[dict]:
    if not disponible(conn):
        return []
    out = []
    for r in conn.execute(
        """SELECT d.id, d.reference, d.titre, d.statut, d.date_creation, d.date_limite, d.date_cloture,
                  d.fournisseur_retenu_id, f.nom_fournisseur AS fournisseur_retenu,
                  (SELECT COUNT(*) FROM ao_lignes l WHERE l.ao_id=d.id) AS nb_lignes,
                  (SELECT COUNT(*) FROM ao_fournisseurs x WHERE x.ao_id=d.id) AS nb_fournisseurs,
                  (SELECT COUNT(*) FROM ao_fournisseurs x WHERE x.ao_id=d.id AND x.statut='repondu') AS nb_reponses
           FROM ao_demandes d LEFT JOIN ao_fournisseurs f ON f.id=d.fournisseur_retenu_id
           WHERE d.deleted_at IS NULL ORDER BY d.date_creation DESC, d.id DESC""").fetchall():
        d = dict(r)
        cde = conn.execute(
            """SELECT id, numero, statut FROM gc_pieces WHERE origine='myao' AND origine_ref=? AND statut!='annule'
               ORDER BY id DESC LIMIT 1""", (d["reference"],)).fetchone()
        d["commande_id"] = cde["id"] if cde else None
        d["commande_numero"] = (cde["numero"] or "brouillon") if cde else None
        out.append(d)
    return out


def _taux_usd(conn) -> float:
    try:
        from app.services.ao_pricing import get_eur_usd_rate
        return float(get_eur_usd_rate(conn))
    except Exception:
        return 0.0


def _cle_produit(ligne) -> str | None:
    if ligne["produit_id"]:
        return f"produit:{ligne['produit_id']}"
    ref = (ligne["ref_produit"] or "").strip()
    return f"ref:{ref.upper()}" if ref else None


def _article_propose(conn, ligne, tiers_id: int | None) -> int | None:
    cle = _cle_produit(ligne)
    if cle:
        r = conn.execute("SELECT article_id FROM gc_correspondances_myao WHERE cle=?", (cle,)).fetchone()
        if r and conn.execute("SELECT 1 FROM gc_articles WHERE id=?", (r["article_id"],)).fetchone():
            return int(r["article_id"])
    ref = (ligne["ref_produit"] or "").strip()
    if ref:
        r = conn.execute(
            """SELECT id FROM gc_articles WHERE actif=1 AND (UPPER(code)=UPPER(?) OR UPPER(ref_client)=UPPER(?))
               ORDER BY (fournisseur_id=?) DESC, id LIMIT 1""", (ref, ref, tiers_id or 0)).fetchone()
        if r:
            return int(r["id"])
    return None


def _prix(reponse, taux: float) -> dict:
    """{prix_cents, base_prix, a_saisir, note} depuis une réponse MyAO."""
    if reponse is None:
        return {"prix_cents": None, "base_prix": None, "a_saisir": True, "note": "Pas de réponse du fournisseur retenu."}
    q = reponse["quotation"] if reponse["quotation"] is not None else reponse["prix_unitaire"]
    if q is None:
        return {"prix_cents": None, "base_prix": None, "a_saisir": True, "note": "Réponse sans prix."}
    unite = (reponse["unite_quotation"] or "mille").lower()
    devise = (reponse["devise"] or "EUR").upper()
    note = ""
    q = float(q)
    if devise == "USD":
        if taux <= 0:
            return {"prix_cents": None, "base_prix": None, "a_saisir": True, "note": "Prix en USD sans taux de change."}
        note = f"{q:.4f} USD au taux {taux:.4f}"
        q = q / taux
    if unite != "mille":
        return {"prix_cents": None, "base_prix": None, "a_saisir": True,
                "note": f"Prix à la bobine ({q:.4f} €) : nombre d'étiquettes par bobine inconnu de l'ERP, prix à saisir."}
    return {"prix_cents": int(round(q * 100)), "base_prix": 1000, "a_saisir": False, "note": note}


def detail(conn, ao_id: int) -> dict:
    if not disponible(conn):
        raise ErreurPiece("MyAO n'est pas installé sur cette base.")
    d = conn.execute("SELECT * FROM ao_demandes WHERE id=? AND deleted_at IS NULL", (ao_id,)).fetchone()
    if not d:
        raise ErreurPiece("Demande MyAO introuvable.")
    d = dict(d)
    fournisseurs = [dict(r) for r in conn.execute(
        "SELECT id, nom_fournisseur, email_contact, statut, fournisseur_id FROM ao_fournisseurs WHERE ao_id=? ORDER BY id",
        (ao_id,)).fetchall()]
    retenu = next((f for f in fournisseurs if f["id"] == d["fournisseur_retenu_id"]), None)
    tiers_id = None
    if retenu:
        if retenu["fournisseur_id"]:
            r = conn.execute("SELECT id FROM gc_tiers WHERE fournisseur_fsc_id=? AND est_fournisseur=1",
                             (retenu["fournisseur_id"],)).fetchone()
            tiers_id = r["id"] if r else None
        if tiers_id is None:
            r = conn.execute("SELECT id FROM gc_tiers WHERE est_fournisseur=1 AND UPPER(raison_sociale)=UPPER(?)",
                             ((retenu["nom_fournisseur"] or "").strip(),)).fetchone()
            tiers_id = r["id"] if r else None
    taux = _taux_usd(conn)
    lignes = []
    for l in conn.execute("SELECT * FROM ao_lignes WHERE ao_id=? ORDER BY position, id", (ao_id,)).fetchall():
        series = [dict(s) for s in conn.execute(
            "SELECT id, libelle, quantite FROM ao_lignes_series WHERE ligne_id=? ORDER BY position, id", (l["id"],)).fetchall()] \
            if "ao_lignes_series" in _tables(conn) else []
        options = []
        for s in (series or [None]):
            rep = None
            if retenu:
                rep = conn.execute(
                    """SELECT * FROM ao_reponses WHERE ao_fournisseur_id=? AND ligne_id=?
                       AND COALESCE(serie_id,0)=? LIMIT 1""", (retenu["id"], l["id"], s["id"] if s else 0)).fetchone()
                if rep is None and s is not None:
                    rep = conn.execute("SELECT * FROM ao_reponses WHERE ao_fournisseur_id=? AND ligne_id=? LIMIT 1",
                                       (retenu["id"], l["id"])).fetchone()
            qte = (s["quantite"] if s else None) or l["quantite"] or 0
            options.append(dict({"serie_id": s["id"] if s else None, "serie": s["libelle"] if s else "",
                                 "quantite_milli": int(round(float(qte) * 1000))}, **_prix(rep, taux)))
        lignes.append({"ligne_id": l["id"], "ref_produit": l["ref_produit"], "designation": l["designation"],
                       "unite": l["unite"], "options": options, "article_id": _article_propose(conn, l, tiers_id)})
    cde = conn.execute("SELECT id, numero FROM gc_pieces WHERE origine='myao' AND origine_ref=? AND statut!='annule' LIMIT 1",
                       (d["reference"],)).fetchone()
    return {"demande": {k: d[k] for k in ("id", "reference", "titre", "statut", "date_creation", "date_limite", "date_cloture")},
            "fournisseurs": fournisseurs, "retenu": retenu, "tiers_id": tiers_id, "lignes": lignes,
            "commande": dict(cde) if cde else None, "taux_usd": taux}


def vers_commande(conn, ao_id: int, data: dict, user: dict | None = None) -> int:
    """Commande fournisseur en brouillon depuis une demande clôturée.

    data = {tiers_id, lignes: [{ligne_id, serie_id?, article_id, quantite_milli?, prix_cents?}]} ;
    une ligne sans article est ignorée (pas commandée)."""
    D = detail(conn, ao_id)
    if D["demande"]["statut"] != "cloturee" or not D["retenu"]:
        raise ErreurPiece("La demande doit être clôturée dans MyAO, avec un fournisseur retenu.")
    if D["commande"]:
        raise ErreurPiece(f"Demande déjà transformée : commande fournisseur {D['commande']['numero'] or 'brouillon'}.")
    tiers_id = int(data.get("tiers_id") or D["tiers_id"] or 0)
    if not tiers_id:
        raise ErreurPiece("Choisir le fournisseur ERP qui correspond au fournisseur retenu.")
    par_ligne = {l["ligne_id"]: l for l in D["lignes"]}
    lignes, notes = [], []
    for i, x in enumerate(data.get("lignes") or [], start=1):
        L = par_ligne.get(int(x.get("ligne_id") or 0))
        if L is None:
            raise ErreurPiece(f"Ligne {i} : ligne MyAO inconnue.")
        if not x.get("article_id"):
            continue
        opt = next((o for o in L["options"] if (o["serie_id"] or None) == (x.get("serie_id") or None)), L["options"][0])
        prix_c = x.get("prix_cents") if x.get("prix_cents") not in (None, "") else opt["prix_cents"]
        if prix_c is None:
            raise ErreurPiece(f"Ligne {i} ({L['ref_produit'] or L['designation']}) : prix à saisir — {opt['note']}")
        q = int(x.get("quantite_milli") or opt["quantite_milli"])
        if q <= 0:
            raise ErreurPiece(f"Ligne {i} : quantité nulle.")
        lignes.append({"article_id": int(x["article_id"]), "quantite_milli": q, "prix_cents": int(prix_c),
                       "base_prix": int(x.get("base_prix") or opt["base_prix"] or 1000),
                       "notes": f"MyAO {D['demande']['reference']} · {L['ref_produit'] or ''} {L['designation'] or ''}".strip()})
        if opt["note"]:
            notes.append(f"{L['ref_produit'] or L['designation']} : {opt['note']}")
        cle = _cle_produit(conn.execute("SELECT * FROM ao_lignes WHERE id=?", (L["ligne_id"],)).fetchone())
        if cle:
            conn.execute("INSERT OR REPLACE INTO gc_correspondances_myao (cle, article_id, maj_le) VALUES (?,?,?)",
                         (cle, int(x["article_id"]), datetime.now().strftime("%Y-%m-%dT%H:%M:%S")))
    if not lignes:
        raise ErreurPiece("Aucune ligne à commander : associer au moins une ligne à un article.")
    pid = pieces.creer(conn, "cde_fournisseur", tiers_id, user, origine="myao")
    conn.execute("UPDATE gc_pieces SET origine_ref=?, notes_internes=? WHERE id=?",
                 (D["demande"]["reference"], "\n".join([f"Demande MyAO {D['demande']['reference']}"] + notes), pid))
    pieces.enregistrer(conn, pid, None, lignes)
    if D["retenu"]["fournisseur_id"]:
        conn.execute("UPDATE gc_tiers SET fournisseur_fsc_id=? WHERE id=? AND fournisseur_fsc_id IS NULL",
                     (D["retenu"]["fournisseur_id"], tiers_id))
    return pid

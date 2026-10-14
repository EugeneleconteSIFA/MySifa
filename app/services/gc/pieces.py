"""Cycle de vie des pièces : devis, commande, BL, facture, avoir, et leurs
équivalents achats.

Règles tenues ici, et nulle part ailleurs :

- Une pièce se modifie tant qu'elle est en **brouillon**. Valider lui donne
  son numéro, fige ses taux, passe ses mouvements de stock et ses échéances.
- Une pièce aval se **génère** depuis une ou plusieurs pièces amont validées
  (`transformer`) : chaque ligne garde `ligne_amont_id`. C'est ce lien, et lui
  seul, qui donne les reliquats et l'état des pièces amont.
- Une facture ou un avoir validé ne s'annule pas : on émet un avoir. Les autres
  pièces validées s'annulent tant qu'aucune pièce aval active n'en dépend ;
  leurs mouvements de stock sont contrepassés.
- La sortie de stock se fait au BL, l'entrée à la réception.

Les fonctions prennent une connexion ouverte et ne commitent pas : l'appelant
(router) commite une fois, ce qui rend chaque opération atomique — numéro de
facture compris.
"""
from __future__ import annotations

from datetime import date, datetime

from app.services.gc import calculs

TYPES = {
    "devis":               {"libelle": "Devis", "sens": "vente", "aval": ["commande"], "stock": 0, "legal": False},
    "commande":            {"libelle": "Commande", "sens": "vente", "aval": ["bl", "of"], "stock": 0, "legal": False},
    "bl":                  {"libelle": "Bon de livraison", "sens": "vente", "aval": ["facture"], "stock": -1, "legal": False},
    "facture":             {"libelle": "Facture", "sens": "vente", "aval": ["avoir"], "stock": 0, "legal": True},
    "avoir":               {"libelle": "Avoir", "sens": "vente", "aval": [], "stock": 0, "legal": True},
    "cde_fournisseur":     {"libelle": "Commande fournisseur", "sens": "achat", "aval": ["reception"], "stock": 0, "legal": False},
    "reception":           {"libelle": "Réception", "sens": "achat", "aval": ["facture_fournisseur"], "stock": 1, "legal": False},
    "facture_fournisseur": {"libelle": "Facture fournisseur", "sens": "achat", "aval": [], "stock": 0, "legal": False},
    # Ordre de fabrication : lancé depuis une ligne de commande, pour le client
    # de la commande. Ses mouvements (production +PF, consommation −MP) sont
    # saisis au fil de l'eau, pas à la validation.
    "of":                  {"libelle": "Ordre de fabrication", "sens": "vente", "aval": [], "stock": 0, "legal": False},
}

# Types aval qui font avancer l'état d'une pièce (partiel / soldé). Un avoir
# ne « solde » pas une facture : il la corrige.
AVANCEMENT = {
    "devis": ["commande"],
    "commande": ["bl"],
    "bl": ["facture"],
    "cde_fournisseur": ["reception"],
    "reception": ["facture_fournisseur"],
}

TYPES_AVEC_ECHEANCES = {"facture", "facture_fournisseur"}

CHAMPS_ENTETE = (
    "date_piece", "date_livraison", "date_validite", "ref_tiers",
    "adresse_facturation_id", "adresse_livraison_id", "condition_paiement",
    "mode_paiement", "depot", "remise_bp", "notes", "notes_internes",
)


class ErreurPiece(ValueError):
    """Refus métier : le message est affiché tel quel à l'utilisateur."""


def _maintenant() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _aujourdhui() -> str:
    return date.today().isoformat()


def _nom(user: dict | None) -> str:
    return str((user or {}).get("nom") or (user or {}).get("email") or "")


def _piece(conn, piece_id: int):
    p = conn.execute("SELECT * FROM gc_pieces WHERE id=?", (piece_id,)).fetchone()
    if not p:
        raise ErreurPiece("Pièce introuvable.")
    return p


# ── Résolution de prix et de TVA ──────────────────────────────────────

def taux_tva(conn, code: str | None) -> int:
    if not code:
        return 0
    r = conn.execute("SELECT taux_bp FROM gc_tva WHERE code=?", (code,)).fetchone()
    if not r:
        raise ErreurPiece(f"Code TVA inconnu : {code}.")
    return int(r["taux_bp"])


def tva_par_defaut(conn) -> str | None:
    r = conn.execute("SELECT code FROM gc_tva WHERE actif=1 ORDER BY rang, code LIMIT 1").fetchone()
    return r["code"] if r else None


def code_tva_ligne(conn, tiers, article) -> str | None:
    """Le régime du tiers (export, intracommunautaire) prime sur le taux de
    l'article ; à défaut, le premier taux actif."""
    if tiers is not None and tiers["tva_code"]:
        return tiers["tva_code"]
    if article is not None and article["tva_code"]:
        return article["tva_code"]
    return tva_par_defaut(conn)


def prix(conn, article_id: int, tiers_id: int | None, quantite_milli: int, sens: str, jour: str | None = None) -> dict:
    """Prix applicable : tarif du tiers, puis tarif général, au plus grand
    palier atteint et en cours de validité ; à défaut, le prix de la fiche."""
    a = conn.execute("SELECT * FROM gc_articles WHERE id=?", (article_id,)).fetchone()
    if not a:
        raise ErreurPiece("Article introuvable.")
    jour = jour or _aujourdhui()
    for tid in ([tiers_id] if tiers_id else []) + [None]:
        r = conn.execute(
            """SELECT prix_cents, qte_min_milli FROM gc_tarifs
               WHERE article_id=? AND sens=? AND actif=1
                 AND (tiers_id IS ? OR tiers_id=?)
                 AND qte_min_milli<=?
                 AND (debut IS NULL OR debut='' OR debut<=?)
                 AND (fin IS NULL OR fin='' OR fin>=?)
               ORDER BY qte_min_milli DESC LIMIT 1""",
            (article_id, sens, tid, tid, int(quantite_milli or 0), jour, jour),
        ).fetchone()
        if r:
            return {"prix_cents": int(r["prix_cents"]), "base_prix": int(a["base_prix"]),
                    "source": "tarif_tiers" if tid else "tarif_general"}
    p = a["prix_vente_cents"] if sens == "vente" else a["prix_achat_cents"]
    return {"prix_cents": int(p or 0), "base_prix": int(a["base_prix"]), "source": "fiche"}


# ── Quantités aval et état ────────────────────────────────────────────

def qte_aval(conn, ligne_id: int, types: list[str]) -> int:
    """Quantité déjà reprise par des pièces aval actives des types donnés."""
    if not types:
        return 0
    marques = ",".join("?" * len(types))
    r = conn.execute(
        f"""SELECT COALESCE(SUM(l.quantite_milli),0) q FROM gc_pieces_lignes l
            JOIN gc_pieces p ON p.id=l.piece_id
            WHERE l.ligne_amont_id=? AND p.statut!='annule' AND p.type IN ({marques})""",
        (ligne_id, *types),
    ).fetchone()
    return int(r["q"])


def qte_produite(conn, ligne_id: int) -> int:
    r = conn.execute(
        "SELECT COALESCE(SUM(quantite_milli),0) q FROM gc_mouvements WHERE ligne_id=? AND type='production'",
        (ligne_id,)).fetchone()
    return int(r["q"])


def _statut_of(conn, p) -> str:
    lignes = conn.execute(
        "SELECT id, quantite_milli, solde FROM gc_pieces_lignes WHERE piece_id=? AND article_id IS NOT NULL",
        (p["id"],)).fetchall()
    prod = [qte_produite(conn, l["id"]) for l in lignes]
    if lignes and all(q >= int(l["quantite_milli"]) or l["solde"] for q, l in zip(prod, lignes)):
        statut = "solde"
    else:
        statut = "partiel" if any(prod) else "valide"
    if statut != p["statut"]:
        conn.execute("UPDATE gc_pieces SET statut=?, modifie_le=? WHERE id=?", (statut, _maintenant(), p["id"]))
    return statut


def recalculer_statut(conn, piece_id: int) -> str:
    p = _piece(conn, piece_id)
    if p["statut"] in ("brouillon", "annule"):
        return p["statut"]
    if p["type"] == "of":
        return _statut_of(conn, p)
    if p["type"] not in AVANCEMENT:
        return p["statut"]
    types = AVANCEMENT[p["type"]]
    lignes = conn.execute(
        "SELECT id, quantite_milli, solde FROM gc_pieces_lignes WHERE piece_id=? AND article_id IS NOT NULL",
        (piece_id,),
    ).fetchall()
    touche = False
    complet = bool(lignes)
    for l in lignes:
        q = qte_aval(conn, l["id"], types)
        if q > 0:
            touche = True
        if q < int(l["quantite_milli"]) and not l["solde"]:
            complet = False
    statut = "solde" if (touche or any(l["solde"] for l in lignes)) and complet else ("partiel" if touche else "valide")
    if statut != p["statut"]:
        conn.execute("UPDATE gc_pieces SET statut=?, modifie_le=? WHERE id=?", (statut, _maintenant(), piece_id))
    return statut


def _pieces_amont(conn, piece_id: int) -> list[int]:
    return [r["id"] for r in conn.execute(
        """SELECT DISTINCT pa.id FROM gc_pieces_lignes l
           JOIN gc_pieces_lignes la ON la.id=l.ligne_amont_id
           JOIN gc_pieces pa ON pa.id=la.piece_id
           WHERE l.piece_id=?""", (piece_id,)).fetchall()]


def _pieces_aval(conn, piece_id: int, actives: bool = True) -> list[int]:
    filtre = "AND pv.statut!='annule'" if actives else ""
    return [r["id"] for r in conn.execute(
        f"""SELECT DISTINCT pv.id FROM gc_pieces_lignes l
            JOIN gc_pieces_lignes lv ON lv.ligne_amont_id=l.id
            JOIN gc_pieces pv ON pv.id=lv.piece_id
            WHERE l.piece_id=? {filtre}""", (piece_id,)).fetchall()]


# ── Lecture ───────────────────────────────────────────────────────────

def charger(conn, piece_id: int) -> dict:
    p = dict(_piece(conn, piece_id))
    t = conn.execute("SELECT id, code, raison_sociale, bloque FROM gc_tiers WHERE id=?", (p["tiers_id"],)).fetchone()
    p["tiers"] = dict(t) if t else None
    p["type_libelle"] = TYPES.get(p["type"], {}).get("libelle", p["type"])
    p["aval_possibles"] = TYPES.get(p["type"], {}).get("aval", [])
    av = AVANCEMENT.get(p["type"], [])
    lignes = []
    for l in conn.execute(
        """SELECT l.*, a.code AS article_code, a.libelle AS article_libelle, a.gere_stock
           FROM gc_pieces_lignes l LEFT JOIN gc_articles a ON a.id=l.article_id
           WHERE l.piece_id=? ORDER BY l.rang, l.id""", (piece_id,)).fetchall():
        d = dict(l)
        d["qte_aval_milli"] = qte_aval(conn, l["id"], av) if l["article_id"] else 0
        if p["type"] == "of" and l["article_id"]:
            d["qte_aval_milli"] = qte_produite(conn, l["id"])
        if l["ligne_amont_id"]:
            pa = conn.execute(
                """SELECT p.id, p.type, p.numero FROM gc_pieces_lignes la JOIN gc_pieces p ON p.id=la.piece_id
                   WHERE la.id=?""", (l["ligne_amont_id"],)).fetchone()
            d["amont"] = dict(pa) if pa else None
        lignes.append(d)
    p["lignes"] = lignes

    def resume(ids):
        if not ids:
            return []
        m = ",".join("?" * len(ids))
        return [dict(r) for r in conn.execute(
            f"SELECT id, type, numero, statut, date_piece, total_ht_cents FROM gc_pieces WHERE id IN ({m}) ORDER BY date_piece, id",
            ids).fetchall()]
    p["amont"] = resume(_pieces_amont(conn, piece_id))
    p["aval"] = resume(_pieces_aval(conn, piece_id, actives=False))
    p["echeances"] = [dict(r) for r in conn.execute(
        "SELECT * FROM gc_echeances WHERE piece_id=? ORDER BY date_echeance", (piece_id,)).fetchall()]
    p["mouvements"] = [dict(r) for r in conn.execute(
        """SELECT m.*, a.code AS article_code FROM gc_mouvements m JOIN gc_articles a ON a.id=m.article_id
           WHERE m.piece_id=? ORDER BY m.id""", (piece_id,)).fetchall()]
    p["totaux"] = calculs.totaux(lignes, p["remise_bp"])
    return p


def lister(conn, types: list[str]) -> list[dict]:
    m = ",".join("?" * len(types))
    return [dict(r) for r in conn.execute(
        f"""SELECT p.id, p.type, p.numero, p.statut, p.date_piece, p.date_livraison, p.ref_tiers,
                   p.total_ht_cents, p.total_ttc_cents, p.tiers_id, t.code AS tiers_code,
                   t.raison_sociale AS tiers_nom,
                   (SELECT COUNT(*) FROM gc_pieces_lignes l WHERE l.piece_id=p.id AND l.article_id IS NOT NULL) AS nb_lignes
            FROM gc_pieces p JOIN gc_tiers t ON t.id=p.tiers_id
            WHERE p.type IN ({m}) ORDER BY p.date_piece DESC, p.id DESC""", types).fetchall()]


# ── Écriture ──────────────────────────────────────────────────────────

def _verifier_tiers(conn, type_piece: str, tiers_id: int):
    t = conn.execute("SELECT * FROM gc_tiers WHERE id=?", (tiers_id,)).fetchone()
    if not t:
        raise ErreurPiece("Tiers introuvable.")
    sens = TYPES[type_piece]["sens"]
    if sens == "vente" and not t["est_client"]:
        raise ErreurPiece(f"{t['raison_sociale']} n'est pas déclaré client.")
    if sens == "achat" and not t["est_fournisseur"]:
        raise ErreurPiece(f"{t['raison_sociale']} n'est pas déclaré fournisseur.")
    return t


def _adresse_defaut(conn, tiers_id: int, type_adr: str):
    r = conn.execute(
        """SELECT id FROM gc_tiers_adresses WHERE tiers_id=? AND type=? AND actif=1
           ORDER BY par_defaut DESC, id LIMIT 1""", (tiers_id, type_adr)).fetchone()
    return r["id"] if r else None


def creer(conn, type_piece: str, tiers_id: int, user: dict | None = None, origine: str = "erp") -> int:
    if type_piece not in TYPES:
        raise ErreurPiece(f"Type de pièce inconnu : {type_piece}.")
    t = _verifier_tiers(conn, type_piece, tiers_id)
    depot = conn.execute("SELECT code FROM gc_depots WHERE actif=1 ORDER BY rang, code LIMIT 1").fetchone()
    now = _maintenant()
    cur = conn.execute(
        """INSERT INTO gc_pieces (type, statut, tiers_id, date_piece, adresse_facturation_id,
               adresse_livraison_id, condition_paiement, mode_paiement, depot, remise_bp,
               origine, cree_par, cree_le, modifie_le)
           VALUES (?, 'brouillon', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (type_piece, tiers_id, _aujourdhui(),
         _adresse_defaut(conn, tiers_id, "facturation"),
         _adresse_defaut(conn, tiers_id, "livraison"),
         t["condition_paiement"], t["mode_paiement"],
         depot["code"] if depot else None,
         int(t["remise_bp"] or 0) if TYPES[type_piece]["sens"] == "vente" else 0,
         origine, _nom(user), now, now),
    )
    return int(cur.lastrowid)


def _entier(v, nom: str, mini: int | None = None) -> int:
    try:
        n = int(v)
    except (TypeError, ValueError):
        raise ErreurPiece(f"{nom} invalide.") from None
    if mini is not None and n < mini:
        raise ErreurPiece(f"{nom} invalide — minimum {mini}.")
    return n


def enregistrer(conn, piece_id: int, entete: dict | None, lignes: list[dict] | None) -> None:
    """Met à jour l'en-tête et remplace les lignes d'un brouillon, puis
    recalcule les totaux. Les montants envoyés par le navigateur sont ignorés."""
    p = _piece(conn, piece_id)
    if p["statut"] != "brouillon":
        raise ErreurPiece("Pièce validée : elle ne se modifie plus.")
    t = conn.execute("SELECT * FROM gc_tiers WHERE id=?", (p["tiers_id"],)).fetchone()
    if entete:
        sets, vals = [], []
        for c in CHAMPS_ENTETE:
            if c in entete:
                v = entete[c]
                if c == "remise_bp":
                    v = _entier(v or 0, "Remise", 0)
                    if v > 10000:
                        raise ErreurPiece("Remise invalide — 100 % au plus.")
                elif c in ("adresse_facturation_id", "adresse_livraison_id"):
                    if v in ("", None):
                        v = None
                    else:
                        v = _entier(v, "Adresse")
                        ok = conn.execute("SELECT 1 FROM gc_tiers_adresses WHERE id=? AND tiers_id=?",
                                          (v, p["tiers_id"])).fetchone()
                        if not ok:
                            raise ErreurPiece("Adresse d'un autre tiers.")
                elif c in ("condition_paiement", "mode_paiement", "depot"):
                    v = v or None
                else:
                    v = "" if v is None and c in ("ref_tiers", "notes", "notes_internes") else v
                if c == "date_piece" and not v:
                    raise ErreurPiece("Date de pièce obligatoire.")
                sets.append(f"{c}=?")
                vals.append(v)
        if sets:
            conn.execute(f"UPDATE gc_pieces SET {', '.join(sets)} WHERE id=?", (*vals, piece_id))

    if lignes is not None:
        amont_ok = [k for k, v in TYPES.items() if p["type"] in v["aval"]]
        conn.execute("DELETE FROM gc_pieces_lignes WHERE piece_id=?", (piece_id,))
        for i, l in enumerate(lignes, start=1):
            art = None
            if l.get("article_id"):
                art = conn.execute("SELECT * FROM gc_articles WHERE id=?", (_entier(l["article_id"], "Article"),)).fetchone()
                if not art:
                    raise ErreurPiece(f"Ligne {i} : article introuvable.")
            libelle = str(l.get("libelle") or (art["libelle"] if art else "")).strip()
            if art is None:
                if not libelle:
                    continue  # ligne vide : ignorée
                conn.execute(
                    "INSERT INTO gc_pieces_lignes (piece_id, rang, libelle, notes) VALUES (?,?,?,?)",
                    (piece_id, i, libelle, str(l.get("notes") or "")))
                continue
            q = _entier(l.get("quantite_milli"), f"Ligne {i} : quantité", 1)
            prix_c = _entier(l.get("prix_cents") or 0, f"Ligne {i} : prix", 0)
            base = _entier(l.get("base_prix") or art["base_prix"] or 1, f"Ligne {i} : base de prix", 1)
            rem = _entier(l.get("remise_bp") or 0, f"Ligne {i} : remise", 0)
            if rem > 10000:
                raise ErreurPiece(f"Ligne {i} : remise invalide — 100 % au plus.")
            code_tva = l.get("tva_code") or code_tva_ligne(conn, t, art)
            amont = l.get("ligne_amont_id") or None
            if amont:
                la = conn.execute(
                    """SELECT la.article_id, pa.type, pa.tiers_id, pa.statut FROM gc_pieces_lignes la
                       JOIN gc_pieces pa ON pa.id=la.piece_id WHERE la.id=?""", (amont,)).fetchone()
                if (not la or la["type"] not in amont_ok or la["tiers_id"] != p["tiers_id"]
                        or la["statut"] in ("brouillon", "annule") or la["article_id"] != art["id"]):
                    raise ErreurPiece(f"Ligne {i} : lien vers la pièce d'origine invalide.")
            conn.execute(
                """INSERT INTO gc_pieces_lignes (piece_id, rang, article_id, libelle, quantite_milli, unite,
                       base_prix, prix_cents, remise_bp, tva_code, taux_tva_bp, montant_ht_cents,
                       date_livraison, ligne_amont_id, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (piece_id, i, art["id"], libelle, q, art["unite"], base, prix_c, rem, code_tva,
                 taux_tva(conn, code_tva), calculs.montant_ligne(q, prix_c, base, rem),
                 l.get("date_livraison") or None, amont, str(l.get("notes") or "")))
    _maj_totaux(conn, piece_id)


def _maj_totaux(conn, piece_id: int) -> None:
    p = _piece(conn, piece_id)
    lignes = conn.execute(
        "SELECT montant_ht_cents, taux_tva_bp FROM gc_pieces_lignes WHERE piece_id=? AND article_id IS NOT NULL",
        (piece_id,)).fetchall()
    tot = calculs.totaux([dict(l) for l in lignes], p["remise_bp"])
    conn.execute(
        "UPDATE gc_pieces SET total_ht_cents=?, total_tva_cents=?, total_ttc_cents=?, modifie_le=? WHERE id=?",
        (tot["ht"], tot["tva"], tot["ttc"], _maintenant(), piece_id))


def valider(conn, piece_id: int, user: dict | None = None) -> str:
    p = _piece(conn, piece_id)
    if p["statut"] != "brouillon":
        raise ErreurPiece("Pièce déjà validée.")
    t = _verifier_tiers(conn, p["type"], p["tiers_id"])
    # Un client bloqué ne reçoit plus de pièce commerciale ; l'avoir (qui lui
    # rend de l'argent) et l'OF (interne) restent possibles.
    if TYPES[p["type"]]["sens"] == "vente" and t["bloque"] and p["type"] not in ("avoir", "of"):
        raise ErreurPiece(f"{t['raison_sociale']} est bloqué : débloquer le client avant de valider.")
    lignes = conn.execute(
        """SELECT l.*, a.gere_stock FROM gc_pieces_lignes l JOIN gc_articles a ON a.id=l.article_id
           WHERE l.piece_id=? ORDER BY l.rang""", (piece_id,)).fetchall()
    if not lignes:
        raise ErreurPiece("Aucune ligne d'article : rien à valider.")
    if p["type"] == "avoir" and p["piece_annulee_id"]:
        _verifier_plafond_avoir(conn, piece_id)
    _maj_totaux(conn, piece_id)
    d = date.fromisoformat(p["date_piece"][:10])
    numero = calculs.prendre_numero(conn, p["type"], d)
    now = _maintenant()
    conn.execute(
        "UPDATE gc_pieces SET numero=?, statut='valide', valide_par=?, valide_le=?, modifie_le=? WHERE id=?",
        (numero, _nom(user), now, now, piece_id))

    sens_stock = TYPES[p["type"]]["stock"]
    if sens_stock:
        if not p["depot"]:
            raise ErreurPiece("Dépôt obligatoire pour un mouvement de stock.")
        for l in lignes:
            if l["gere_stock"]:
                conn.execute(
                    """INSERT INTO gc_mouvements (date_mvt, article_id, depot, quantite_milli, type, piece_id,
                           ligne_id, valeur_cents, cree_par, cree_le)
                       VALUES (?,?,?,?,?,?,?,?,?,?)""",
                    (p["date_piece"][:10], l["article_id"], p["depot"], sens_stock * int(l["quantite_milli"]),
                     "livraison" if sens_stock < 0 else "reception", piece_id, l["id"],
                     l["montant_ht_cents"], _nom(user), now))

    if p["type"] in TYPES_AVEC_ECHEANCES:
        _creer_echeances(conn, piece_id)

    for amont in _pieces_amont(conn, piece_id):
        recalculer_statut(conn, amont)
    recalculer_statut(conn, piece_id)
    return numero


def alertes_stock(conn, piece_id: int) -> list[str]:
    """Articles de la pièce dont le stock du dépôt est passé sous zéro.
    Ne bloque rien (question Q9 de la roadmap) : l'écran l'affiche."""
    out = []
    for r in conn.execute(
        """SELECT a.code, m.depot, a.unite,
                  (SELECT SUM(m2.quantite_milli) FROM gc_mouvements m2 WHERE m2.article_id=m.article_id AND m2.depot=m.depot) AS q
           FROM gc_mouvements m JOIN gc_articles a ON a.id=m.article_id
           WHERE m.piece_id=? GROUP BY m.article_id, m.depot""", (piece_id,)).fetchall():
        if r["q"] is not None and int(r["q"]) < 0:
            q = f"{int(r['q']) / 1000:,.3f}".rstrip("0").rstrip(".").replace(",", " ").replace(".", ",")
            out.append(f"{r['code']} : stock {q} {r['unite']} au dépôt {r['depot']}")
    return out


def dupliquer(conn, piece_id: int, user: dict | None = None) -> int:
    """Nouveau brouillon du même type et du même tiers, avec les mêmes lignes
    (sans lien amont : c'est une nouvelle pièce, pas une suite)."""
    p = _piece(conn, piece_id)
    if p["type"] == "avoir":
        raise ErreurPiece("Un avoir se crée depuis sa facture, pas par duplication.")
    nouvelle = creer(conn, p["type"], p["tiers_id"], user)
    lignes = [{"article_id": l["article_id"], "libelle": l["libelle"], "quantite_milli": l["quantite_milli"],
               "base_prix": l["base_prix"], "prix_cents": l["prix_cents"], "remise_bp": l["remise_bp"],
               "tva_code": l["tva_code"], "notes": l["notes"]}
              for l in conn.execute("SELECT * FROM gc_pieces_lignes WHERE piece_id=? ORDER BY rang", (piece_id,)).fetchall()]
    enregistrer(conn, nouvelle, {"ref_tiers": "", "remise_bp": p["remise_bp"], "notes": p["notes"],
                                 "adresse_livraison_id": p["adresse_livraison_id"]}, lignes)
    return nouvelle


def _of_ouvert(conn, of_id: int):
    p = _piece(conn, of_id)
    if p["type"] != "of":
        raise ErreurPiece("Ce n'est pas un ordre de fabrication.")
    if p["statut"] not in ("valide", "partiel", "solde"):
        raise ErreurPiece("Ordre de fabrication non lancé ou annulé.")
    if not p["depot"]:
        raise ErreurPiece("Dépôt obligatoire sur l'ordre de fabrication.")
    return p


def declarer_production(conn, of_id: int, quantite_milli: int, lot: str = "", jour: str | None = None,
                        user: dict | None = None) -> int:
    """Entrée en stock du produit fini fabriqué par l'OF."""
    p = _of_ouvert(conn, of_id)
    q = _entier(quantite_milli, "Quantité", 1)
    l = conn.execute(
        "SELECT id, article_id FROM gc_pieces_lignes WHERE piece_id=? AND article_id IS NOT NULL ORDER BY rang LIMIT 1",
        (of_id,)).fetchone()
    if not l:
        raise ErreurPiece("Aucun produit sur l'ordre de fabrication.")
    now = _maintenant()
    cur = conn.execute(
        """INSERT INTO gc_mouvements (date_mvt, article_id, depot, quantite_milli, type, lot, piece_id, ligne_id,
               commentaire, cree_par, cree_le) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (jour or now[:10], l["article_id"], p["depot"], q, "production", str(lot or ""), of_id, l["id"],
         "Production " + (p["numero"] or ""), _nom(user), now))
    _statut_of(conn, _piece(conn, of_id))
    return int(cur.lastrowid)


def declarer_consommation(conn, of_id: int, article_id: int, quantite_milli: int, lot: str = "",
                          jour: str | None = None, user: dict | None = None) -> int:
    """Sortie de stock d'une matière consommée par l'OF."""
    p = _of_ouvert(conn, of_id)
    q = _entier(quantite_milli, "Quantité", 1)
    a = conn.execute("SELECT id, nature, gere_stock FROM gc_articles WHERE id=?", (_entier(article_id, "Article"),)).fetchone()
    if not a or not a["gere_stock"]:
        raise ErreurPiece("Article introuvable ou non géré en stock.")
    if a["nature"] == "service":
        raise ErreurPiece("Une prestation ne se consomme pas.")
    now = _maintenant()
    cur = conn.execute(
        """INSERT INTO gc_mouvements (date_mvt, article_id, depot, quantite_milli, type, lot, piece_id,
               commentaire, cree_par, cree_le) VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (jour or now[:10], a["id"], p["depot"], -q, "consommation", str(lot or ""), of_id,
         "Consommation " + (p["numero"] or ""), _nom(user), now))
    return int(cur.lastrowid)


def _verifier_plafond_avoir(conn, avoir_id: int) -> None:
    """Un avoir ne rend pas plus que ce qui a été facturé, ligne à ligne."""
    for l in conn.execute(
        "SELECT ligne_amont_id, quantite_milli, rang FROM gc_pieces_lignes WHERE piece_id=? AND ligne_amont_id IS NOT NULL",
        (avoir_id,)).fetchall():
        fact = conn.execute("SELECT quantite_milli FROM gc_pieces_lignes WHERE id=?", (l["ligne_amont_id"],)).fetchone()
        deja = conn.execute(
            """SELECT COALESCE(SUM(lv.quantite_milli),0) q FROM gc_pieces_lignes lv JOIN gc_pieces pv ON pv.id=lv.piece_id
               WHERE lv.ligne_amont_id=? AND pv.type='avoir' AND pv.statut!='annule' AND pv.id!=?""",
            (l["ligne_amont_id"], avoir_id)).fetchone()["q"]
        if int(deja) + int(l["quantite_milli"]) > int(fact["quantite_milli"]):
            raise ErreurPiece(f"Ligne {l['rang']} : l'avoir dépasse la quantité facturée.")


def _creer_echeances(conn, piece_id: int) -> None:
    p = _piece(conn, piece_id)
    conn.execute("DELETE FROM gc_echeances WHERE piece_id=?", (piece_id,))
    c = None
    if p["condition_paiement"]:
        c = conn.execute("SELECT * FROM gc_conditions_paiement WHERE code=?", (p["condition_paiement"],)).fetchone()
    d = date.fromisoformat(p["date_piece"][:10])
    e = calculs.date_echeance(d, c["jours"], bool(c["fin_de_mois"]), c["jour_du_mois"]) if c else d
    conn.execute("INSERT INTO gc_echeances (piece_id, date_echeance, montant_cents) VALUES (?,?,?)",
                 (piece_id, e.isoformat(), p["total_ttc_cents"]))


def transformer(conn, sources: list[int], cible: str, user: dict | None = None) -> int:
    """Génère une pièce `cible` en brouillon depuis des pièces validées du même
    tiers, avec les quantités restant à reprendre."""
    if not sources:
        raise ErreurPiece("Aucune pièce d'origine.")
    ps = [_piece(conn, int(i)) for i in sources]
    types = {p["type"] for p in ps}
    tiers = {p["tiers_id"] for p in ps}
    if len(types) != 1 or len(tiers) != 1:
        raise ErreurPiece("Les pièces à regrouper doivent être du même type et du même tiers.")
    src_type = types.pop()
    if cible not in TYPES[src_type]["aval"]:
        raise ErreurPiece(f"Un(e) {TYPES[src_type]['libelle'].lower()} ne se transforme pas en {TYPES[cible]['libelle'].lower()}.")
    for p in ps:
        if p["statut"] in ("brouillon", "annule"):
            raise ErreurPiece(f"{p['numero'] or 'Brouillon'} : seule une pièce validée se transforme.")
    # Le reste se mesure contre les pièces du type demandé : une commande se
    # livre (BL) et se fabrique (OF) indépendamment.
    reprise = AVANCEMENT.get(src_type) if cible in AVANCEMENT.get(src_type, []) else [cible]
    lignes = []
    for p in ps:
        for l in conn.execute(
            "SELECT * FROM gc_pieces_lignes WHERE piece_id=? AND article_id IS NOT NULL ORDER BY rang", (p["id"],)
        ).fetchall():
            if l["solde"]:
                continue
            if cible == "of":
                a = conn.execute("SELECT nature, gere_stock FROM gc_articles WHERE id=?", (l["article_id"],)).fetchone()
                if not a or a["nature"] != "pf":
                    continue   # on ne fabrique que des produits finis
            reste = int(l["quantite_milli"]) - qte_aval(conn, l["id"], reprise)
            if reste <= 0:
                continue
            lignes.append({
                "article_id": l["article_id"], "libelle": l["libelle"], "quantite_milli": reste,
                "base_prix": l["base_prix"], "prix_cents": l["prix_cents"], "remise_bp": l["remise_bp"],
                "tva_code": l["tva_code"], "date_livraison": l["date_livraison"], "ligne_amont_id": l["id"],
            })
    if not lignes:
        raise ErreurPiece("Plus rien à reprendre : tout a déjà été repris.")
    nouvelle = creer(conn, cible, ps[0]["tiers_id"], user)
    src = ps[0]
    entete = {
        "ref_tiers": src["ref_tiers"],
        "adresse_facturation_id": src["adresse_facturation_id"],
        "adresse_livraison_id": src["adresse_livraison_id"],
        "condition_paiement": src["condition_paiement"],
        "mode_paiement": src["mode_paiement"],
        "depot": src["depot"],
        "remise_bp": src["remise_bp"],
    }
    if cible == "avoir":
        conn.execute("UPDATE gc_pieces SET piece_annulee_id=? WHERE id=?", (src["id"], nouvelle))
    enregistrer(conn, nouvelle, entete, lignes)
    return nouvelle


def supprimer(conn, piece_id: int) -> None:
    p = _piece(conn, piece_id)
    if p["statut"] != "brouillon":
        raise ErreurPiece("Seul un brouillon se supprime. Une pièce validée s'annule.")
    amont = _pieces_amont(conn, piece_id)
    conn.execute("DELETE FROM gc_pieces_lignes WHERE piece_id=?", (piece_id,))
    conn.execute("DELETE FROM gc_pieces WHERE id=?", (piece_id,))
    for a in amont:
        recalculer_statut(conn, a)


def annuler(conn, piece_id: int, user: dict | None = None) -> None:
    p = _piece(conn, piece_id)
    if p["statut"] in ("brouillon", "annule"):
        raise ErreurPiece("Rien à annuler : supprimer un brouillon, ou pièce déjà annulée.")
    if TYPES[p["type"]]["legal"]:
        raise ErreurPiece("Une facture ou un avoir validé ne s'annule pas : émettre un avoir.")
    if _pieces_aval(conn, piece_id, actives=True):
        raise ErreurPiece("Des pièces en dépendent : les annuler ou supprimer d'abord.")
    now = _maintenant()
    for m in conn.execute("SELECT * FROM gc_mouvements WHERE piece_id=?", (piece_id,)).fetchall():
        conn.execute(
            """INSERT INTO gc_mouvements (date_mvt, article_id, depot, quantite_milli, type, piece_id, ligne_id,
                   valeur_cents, commentaire, cree_par, cree_le)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (now[:10], m["article_id"], m["depot"], -int(m["quantite_milli"]), m["type"], piece_id, m["ligne_id"],
             -(m["valeur_cents"] or 0), "Contrepassation : annulation de " + (p["numero"] or ""), _nom(user), now))
    conn.execute("UPDATE gc_pieces SET statut='annule', modifie_le=? WHERE id=?", (now, piece_id))
    for a in _pieces_amont(conn, piece_id):
        recalculer_statut(conn, a)


def solder_ligne(conn, ligne_id: int, solde: bool) -> int:
    """Abandonne (ou rétablit) le reliquat d'une ligne de pièce validée."""
    l = conn.execute(
        "SELECT l.piece_id, p.statut FROM gc_pieces_lignes l JOIN gc_pieces p ON p.id=l.piece_id WHERE l.id=?",
        (ligne_id,)).fetchone()
    if not l:
        raise ErreurPiece("Ligne introuvable.")
    if l["statut"] in ("brouillon", "annule"):
        raise ErreurPiece("Seule une ligne de pièce validée se solde.")
    conn.execute("UPDATE gc_pieces_lignes SET solde=? WHERE id=?", (1 if solde else 0, ligne_id))
    recalculer_statut(conn, l["piece_id"])
    return int(l["piece_id"])

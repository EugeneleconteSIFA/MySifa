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

from datetime import date, datetime, timedelta

from app.services.gc import calculs

TYPES = {
    "devis":               {"libelle": "Devis", "sens": "vente", "aval": ["commande"], "stock": 0, "legal": False},
    # Marché : contrat cadre (quantité et prix pour une période) ; chaque
    # appel est une commande liée à la ligne de marché.
    "marche":              {"libelle": "Marché", "sens": "vente", "aval": ["commande"], "stock": 0, "legal": False},
    "commande":            {"libelle": "Commande", "sens": "vente", "aval": ["bl", "of"], "stock": 0, "legal": False},
    "bl":                  {"libelle": "Bon de livraison", "sens": "vente", "aval": ["facture"], "stock": -1, "legal": False},
    "facture":             {"libelle": "Facture", "sens": "vente", "aval": ["avoir"], "stock": 0, "legal": True},
    "avoir":               {"libelle": "Avoir", "sens": "vente", "aval": [], "stock": 0, "legal": True},
    "aof":                 {"libelle": "Appel d'offre", "sens": "achat", "aval": ["cde_fournisseur"], "stock": 0, "legal": False},
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
    "marche": ["commande"],
    "commande": ["bl"],
    "bl": ["facture"],
    "cde_fournisseur": ["reception"],
    "aof": ["cde_fournisseur"],
    "reception": ["facture_fournisseur"],
}

TYPES_AVEC_ECHEANCES = {"facture", "facture_fournisseur"}

CHAMPS_ENTETE = (
    "date_piece", "date_livraison", "date_validite", "ref_tiers",
    "adresse_facturation_id", "adresse_livraison_id", "condition_paiement",
    "mode_paiement", "depot", "remise_bp", "notes", "notes_internes",
    # relevés sur RVGI (migration gc_parite_rvgi)
    "contact_id", "transporteur_id", "jours_expedition", "date_expedition", "franco_cents",
    "escompte_bp", "acompte_cents", "representant_id", "commission_bp", "recepisse", "nb_colis",
    "nb_palettes", "poids_g", "emballage", "date_ouverture",
)
CHAMPS_ENTIERS = {"jours_expedition", "franco_cents", "escompte_bp", "acompte_cents", "commission_bp",
                  "nb_colis", "nb_palettes", "poids_g"}
CHAMPS_TEXTE = {"ref_tiers", "notes", "notes_internes", "recepisse", "emballage"}
ORIGINES = {"fabrication": "Fabrication", "stock": "Stock", "soustraitance": "Sous-traitance"}
LABORATOIRES = {"renouvellement": "Renouvellement", "creation": "Création", "modification": "Modification"}
# Une ligne en création ou en modification exige un BAT validé (module BAT de MySifa).
LABORATOIRES_AVEC_BAT = {"creation", "modification"}
TYPES_LIGNE = {"livrer_facturer": "À livrer et facturer", "livrer_sans_facture": "À livrer sans facture",
               "stocker": "À stocker"}
BAT_LIBELLES = {"a_faire": "À faire", "en_attente": "En attente", "valide": "Validé"}
REPORT_ENTETE = ("ref_tiers", "adresse_facturation_id", "adresse_livraison_id", "condition_paiement", "mode_paiement",
                 "depot", "remise_bp", "contact_id", "transporteur_id", "jours_expedition", "date_expedition",
                 "date_livraison", "franco_cents", "escompte_bp", "representant_id", "commission_bp")


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


def prix(conn, article_id: int, tiers_id: int | None, quantite_milli: int, sens: str, jour: str | None = None,
         laize_dmm: int | None = None, ml_par_bobine_milli: int | None = None) -> dict:
    """Prix applicable : tarif du tiers, puis tarif général, au plus grand
    palier atteint et en cours de validité ; à défaut, le prix de la fiche.

    À l'achat, le prix dépend du conditionnement (laize, longueur de bobine) :
    un conditionnement demandé ne retient que les tarifs de ce conditionnement
    (ou sans conditionnement précisé) ; le tarif retourné dit le sien."""
    a = conn.execute("SELECT * FROM gc_articles WHERE id=?", (article_id,)).fetchone()
    if not a:
        raise ErreurPiece("Article introuvable.")
    jour = jour or _aujourdhui()
    cond_sql, cond_args = "", []
    if laize_dmm:
        cond_sql += " AND (laize_dmm IS NULL OR laize_dmm=?)"
        cond_args.append(int(laize_dmm))
    if ml_par_bobine_milli:
        cond_sql += " AND (ml_par_bobine_milli IS NULL OR ml_par_bobine_milli=?)"
        cond_args.append(int(ml_par_bobine_milli))
    for tid in ([tiers_id] if tiers_id else []) + [None]:
        r = conn.execute(
            f"""SELECT prix_cents, qte_min_milli, laize_dmm, ml_par_bobine_milli, ref_fournisseur FROM gc_tarifs
               WHERE article_id=? AND sens=? AND actif=1
                 AND (tiers_id IS ? OR tiers_id=?)
                 AND qte_min_milli<=?
                 AND (debut IS NULL OR debut='' OR debut<=?)
                 AND (fin IS NULL OR fin='' OR fin>=?) {cond_sql}
               ORDER BY (laize_dmm IS NOT NULL) + (ml_par_bobine_milli IS NOT NULL) DESC, qte_min_milli DESC LIMIT 1""",
            (article_id, sens, tid, tid, int(quantite_milli or 0), jour, jour, *cond_args),
        ).fetchone()
        if r:
            return {"prix_cents": int(r["prix_cents"]), "base_prix": int(a["base_prix"]),
                    "source": "tarif_tiers" if tid else "tarif_general",
                    "laize_dmm": r["laize_dmm"] or laize_dmm or _t(a, "format_l_dmm"),
                    "ml_par_bobine_milli": r["ml_par_bobine_milli"] or ml_par_bobine_milli or _t(a, "ml_par_bobine_milli"),
                    "ref_fournisseur": r["ref_fournisseur"] or ""}
    p = a["prix_vente_cents"] if sens == "vente" else a["prix_achat_cents"]
    return {"prix_cents": int(p or 0), "base_prix": int(a["base_prix"]), "source": "fiche",
            "laize_dmm": laize_dmm or _t(a, "format_l_dmm"),
            "ml_par_bobine_milli": ml_par_bobine_milli or _t(a, "ml_par_bobine_milli"), "ref_fournisseur": ""}


def conditionnements(conn, article_id: int, tiers_id: int | None) -> list[dict]:
    """Conditionnements d'achat proposés pour un article chez un fournisseur."""
    return [dict(r) for r in conn.execute(
        """SELECT DISTINCT laize_dmm, ml_par_bobine_milli, ref_fournisseur FROM gc_tarifs
           WHERE article_id=? AND sens='achat' AND actif=1 AND (tiers_id IS NULL OR tiers_id=?)
             AND (laize_dmm IS NOT NULL OR ml_par_bobine_milli IS NOT NULL)
           ORDER BY laize_dmm, ml_par_bobine_milli""", (article_id, tiers_id)).fetchall()]


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


def qte_produite_pour(conn, ligne_cde_id: int) -> int:
    """Quantité produite par les OF actifs lancés depuis une ligne de commande."""
    r = conn.execute(
        """SELECT COALESCE(SUM(m.quantite_milli),0) q FROM gc_mouvements m
           JOIN gc_pieces_lignes lo ON lo.id=m.ligne_id JOIN gc_pieces po ON po.id=lo.piece_id
           WHERE lo.ligne_amont_id=? AND po.type='of' AND po.statut!='annule' AND m.type='production'""",
        (ligne_cde_id,)).fetchone()
    return int(r["q"])


def avancement_ligne(conn, piece_type: str, l) -> int:
    """Quantité « reprise » d'une ligne, selon son type :
    - ligne à stocker d'une commande : quantité produite par ses OF ;
    - ligne de BL livrée sans facture : entièrement « reprise » (rien à facturer) ;
    - sinon : quantité reprise par l'étape suivante."""
    tl = l["type_ligne"] if "type_ligne" in l.keys() else "livrer_facturer"
    if piece_type == "commande" and tl == "stocker":
        return qte_produite_pour(conn, l["id"])
    if piece_type == "bl" and tl == "livrer_sans_facture":
        return int(l["quantite_milli"])
    return qte_aval(conn, l["id"], AVANCEMENT.get(piece_type, []))


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
    lignes = conn.execute(
        "SELECT * FROM gc_pieces_lignes WHERE piece_id=? AND article_id IS NOT NULL",
        (piece_id,),
    ).fetchall()
    touche = False
    complet = bool(lignes)
    for l in lignes:
        q = avancement_ligne(conn, p["type"], l)
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
    p["totaux"] = calculs.totaux(lignes, p["remise_bp"], p.get("escompte_bp") or 0, p.get("acompte_cents") or 0)
    from app.services.gc import cahiers   # import local : cahiers dépend de ce module
    p["cahier"] = cahiers.pour_piece(conn, piece_id)
    p["etape"] = cahiers.ETAPE_DE_PIECE.get(p["type"])
    return p


def lister(conn, types: list[str]) -> list[dict]:
    m = ",".join("?" * len(types))
    return [dict(r) for r in conn.execute(
        f"""SELECT p.id, p.type, p.numero, p.statut, p.date_piece, p.date_livraison, p.ref_tiers, p.imprime_le, p.comptabilise_le,
                   p.envoye_le, p.remise_bp, p.escompte_bp, p.cree_par,
                   (SELECT libelle FROM gc_modes_paiement mp WHERE mp.code=p.mode_paiement) AS mode_libelle,
                   (SELECT nom FROM users u WHERE u.id=p.representant_id) AS representant,
                   (SELECT MIN(date_echeance) FROM gc_echeances e WHERE e.piece_id=p.id) AS date_echeance,
                   (SELECT COALESCE(SUM(montant_cents),0) FROM gc_echeances e WHERE e.piece_id=p.id) AS echeances_cents,
                   (SELECT COALESCE(SUM(regle_cents),0) FROM gc_echeances e WHERE e.piece_id=p.id) AS regle_cents,
                   p.total_ht_cents, p.total_ttc_cents, p.tiers_id, t.code AS tiers_code,
                   t.raison_sociale AS tiers_nom,
                   (SELECT COUNT(*) FROM gc_pieces_lignes l WHERE l.piece_id=p.id AND l.article_id IS NOT NULL) AS nb_lignes
            FROM gc_pieces p JOIN gc_tiers t ON t.id=p.tiers_id
            WHERE p.type IN ({m}) ORDER BY p.date_piece DESC, p.id DESC""", types).fetchall()]


def carnet(conn, types: list[str]) -> list[dict]:
    """Vue par ligne. `repris_milli` : quantité reprise par l'étape suivante
    (commandée pour un devis ou un marché, livrée pour une commande, facturée
    pour un BL). `situation_of` : état du dernier OF de la ligne."""
    m = ",".join("?" * len(types))
    out = []
    for l in conn.execute(
        f"""SELECT l.id AS ligne_id, l.rang, l.article_id, l.libelle, l.quantite_milli, l.unite, l.base_prix,
                   l.prix_cents, l.montant_ht_cents, l.date_livraison, l.date_expedition, l.origine_prod,
                   l.laboratoire, l.ref_client, l.solde, l.nb_livraisons, l.type_ligne, l.quantite_milli AS q_l,
                   p.id AS piece_id, p.type, p.numero, p.statut, p.date_piece, p.ref_tiers, p.date_validite,
                   p.date_ouverture, p.date_livraison AS piece_date_livraison, p.date_expedition AS piece_date_expedition,
                   t.id AS tiers_id, t.code AS tiers_code, t.raison_sociale AS tiers_nom,
                   a.code AS article_code, a.format_l_dmm, a.format_a_dmm, a.conditionnement,
                   a.code3, a.designation AS article_designation, a.famille, a.sous_famille,
                   l.prix_cents, l.laize_dmm, l.notes AS notes_ligne, l.ligne_amont_id, l.unite,
                   l.dates_confirmees, l.zone_rangement, l.zone_douane, l.remise_bp AS remise_ligne_bp,
                   p.cree_par AS operateur, p.valide_par, p.remise_bp AS remise_piece_bp, p.depot, p.notes AS notes_piece,
                   (SELECT nom FROM users u WHERE u.id=t.adv_id) AS adv,
                   ad.raison_sociale AS liv_raison_sociale, ad.adresse1 AS liv_adresse1, ad.adresse2 AS liv_adresse2,
                   ad.code_postal AS liv_cp, ad.ville AS liv_ville, ad.pays AS liv_pays,
                   pa.numero AS amont_numero, pa.type AS amont_type, la.rang AS amont_rang, pa.ref_tiers AS amont_ref_tiers,
                   la.quantite_milli AS amont_qte_milli, la.prix_cents AS amont_prix_cents, la.base_prix AS amont_base_prix,
                   (SELECT GROUP_CONCAT(DISTINCT pv.numero) FROM gc_pieces_lignes lv JOIN gc_pieces pv ON pv.id=lv.piece_id
                     WHERE lv.ligne_amont_id=l.id AND pv.statut!='annule' AND pv.numero IS NOT NULL) AS aval_numeros,
                   (SELECT COALESCE(SUM(quantite_milli),0) FROM gc_mouvements mv WHERE mv.article_id=l.article_id) AS stock_milli,
                   (SELECT nom FROM users u WHERE u.id=p.representant_id) AS representant,
                   (SELECT nom FROM expe_transporteurs x WHERE x.id=p.transporteur_id) AS transporteur
            FROM gc_pieces_lignes l JOIN gc_pieces p ON p.id=l.piece_id JOIN gc_tiers t ON t.id=p.tiers_id
            LEFT JOIN gc_articles a ON a.id=l.article_id
            LEFT JOIN gc_tiers_adresses ad ON ad.id=COALESCE(l.adresse_livraison_id, p.adresse_livraison_id)
            LEFT JOIN gc_pieces_lignes la ON la.id=l.ligne_amont_id
            LEFT JOIN gc_pieces pa ON pa.id=la.piece_id
            WHERE p.type IN ({m}) AND l.article_id IS NOT NULL
            ORDER BY COALESCE(l.date_expedition, p.date_expedition, l.date_livraison, p.date_livraison, p.date_piece), p.id, l.rang""",
            types).fetchall():
        d = dict(l)
        d["date_expedition"] = d["date_expedition"] or d.pop("piece_date_expedition")
        d["date_livraison"] = d["date_livraison"] or d.pop("piece_date_livraison")
        d.pop("piece_date_expedition", None)
        d.pop("piece_date_livraison", None)
        if d["type"] == "of":
            d["repris_milli"] = qte_produite(conn, d["ligne_id"])
        else:
            d["repris_milli"] = avancement_ligne(conn, d["type"], {"id": d["ligne_id"], "type_ligne": d["type_ligne"],
                                                                   "quantite_milli": d["quantite_milli"]})
        d["reste_milli"] = 0 if d["solde"] else max(0, int(d["quantite_milli"]) - d["repris_milli"])
        desig = [x for x in (d.pop("article_designation") or "").splitlines() if x.strip()]
        for i in range(3):
            d[f"designation{i + 2}"] = desig[i] if i < len(desig) else ""
        # Ligne d'origine (la commande d'un BL, le BL d'une facture) : son reste.
        d["amont_reste_milli"] = None
        if d["amont_numero"] is not None and d["amont_type"]:
            la = conn.execute("SELECT id, type_ligne, quantite_milli, solde FROM gc_pieces_lignes WHERE id=?",
                              (d["ligne_amont_id"],)).fetchone()
            if la:
                rep = avancement_ligne(conn, d["amont_type"], dict(la))
                d["amont_reste_milli"] = 0 if la["solde"] else max(0, int(la["quantite_milli"]) - rep)
        if d["statut"] in ("brouillon", "annule"):
            d["position"] = d["statut"]
        elif d["solde"] or d["reste_milli"] == 0:
            d["position"] = "solde"
        else:
            d["position"] = "partiel" if d["repris_milli"] else "valide"
        of = conn.execute(
            """SELECT p.statut FROM gc_pieces_lignes lo JOIN gc_pieces p ON p.id=lo.piece_id
               WHERE lo.ligne_amont_id=? AND p.type='of' AND p.statut!='annule' ORDER BY p.id DESC LIMIT 1""",
            (d["ligne_id"],)).fetchone()
        # Quantité à fabriquer : calculée, jamais saisie (C4 : un écart saisi
        # avec la quantité commandée était le plus souvent un bug). Reste à
        # livrer moins le stock disponible, moins ce que les OF ont déjà produit.
        if d["origine_prod"] == "fabrication" and d["type"] in ("commande", "marche") and d["reste_milli"] > 0:
            deja = qte_produite_pour(conn, d["ligne_id"])
            d["a_fabriquer_milli"] = max(0, d["reste_milli"] - max(0, int(d["stock_milli"] or 0)) - deja)
        else:
            d["a_fabriquer_milli"] = 0
        from app.services.gc import fsc as _fsc
        d["fsc"] = _fsc.libelle(_fsc.allegation_ligne(conn, d["ligne_id"])) if d["type"] in ("commande", "marche", "bl") else ""
        d["bat"] = ""
        if d["laboratoire"] in LABORATOIRES_AVEC_BAT and d["position"] not in ("solde", "annule"):
            d["bat"] = bat_article(conn, d["article_id"]) or "non_rattache"
        a_lancer = d["origine_prod"] == "fabrication" and d["type"] in ("commande", "marche") and d["reste_milli"] > 0
        d["situation_of"] = of["statut"] if of else ("a_ordonnancer" if a_lancer else "")
        out.append(d)
    return out


# ── Écriture ──────────────────────────────────────────────────────────

def _verifier_tiers(conn, type_piece: str, tiers_id: int):
    t = conn.execute("SELECT * FROM gc_tiers WHERE id=?", (tiers_id,)).fetchone()
    if not t:
        raise ErreurPiece("Tiers introuvable.")
    sens = TYPES[type_piece]["sens"]
    prospect = "est_prospect" in t.keys() and t["est_prospect"]
    if sens == "vente" and not t["est_client"]:
        # Un prospect reçoit des devis ; pour commander, il passe client sur sa fiche.
        if prospect and type_piece == "devis":
            return t
        if prospect:
            raise ErreurPiece(f"{t['raison_sociale']} est un prospect : le passer en client sur sa fiche avant de commander.")
        raise ErreurPiece(f"{t['raison_sociale']} n'est pas déclaré client.")
    if sens == "achat" and not t["est_fournisseur"]:
        raise ErreurPiece(f"{t['raison_sociale']} n'est pas déclaré fournisseur.")
    return t


def _adresse_defaut(conn, tiers_id: int, type_adr: str):
    """Adresse par défaut du type ; à défaut, l'adresse principale du tiers."""
    r = conn.execute(
        """SELECT id FROM gc_tiers_adresses WHERE tiers_id=? AND type IN (?, 'principale') AND actif=1
           ORDER BY type=? DESC, par_defaut DESC, id LIMIT 1""", (tiers_id, type_adr, type_adr)).fetchone()
    return r["id"] if r else None


def creer(conn, type_piece: str, tiers_id: int, user: dict | None = None, origine: str = "erp") -> int:
    if type_piece not in TYPES:
        raise ErreurPiece(f"Type de pièce inconnu : {type_piece}.")
    t = _verifier_tiers(conn, type_piece, tiers_id)
    depot = conn.execute("SELECT code FROM gc_depots WHERE actif=1 ORDER BY rang, code LIMIT 1").fetchone()
    now = _maintenant()
    notes = ""
    champ_texte = {"devis": "texte_devis", "commande": "texte_arc", "bl": "texte_bl", "facture": "texte_facture",
                   "aof": "texte_aof", "cde_fournisseur": "texte_cde"}.get(type_piece)
    if champ_texte and _t(t, champ_texte):
        tx = conn.execute("SELECT texte FROM gc_textes WHERE code=? AND actif=1", (t[champ_texte],)).fetchone()
        notes = tx["texte"] if tx else ""
    cur = conn.execute(
        """INSERT INTO gc_pieces (type, statut, tiers_id, date_piece, adresse_facturation_id,
               adresse_livraison_id, condition_paiement, mode_paiement, depot, remise_bp,
               transporteur_id, jours_expedition, representant_id, notes,
               origine, cree_par, cree_le, modifie_le)
           VALUES (?, 'brouillon', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (type_piece, tiers_id, _aujourdhui(),
         _adresse_defaut(conn, tiers_id, "facturation"),
         _adresse_defaut(conn, tiers_id, "livraison"),
         t["condition_paiement"], t["mode_paiement"],
         depot["code"] if depot else None,
         int(t["remise_bp"] or 0) if TYPES[type_piece]["sens"] == "vente" else 0,
         _t(t, "transporteur_id"), int(_t(t, "jours_expedition") or 0), _t(t, "representant_id"), notes,
         origine, _nom(user), now, now),
    )
    return int(cur.lastrowid)


def _t(row, cle):
    """Colonne facultative (ajoutée par une migration plus récente)."""
    return row[cle] if cle in row.keys() else None


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
                elif c in CHAMPS_ENTIERS:
                    v = None if v in ("", None) and c in ("franco_cents", "nb_colis", "nb_palettes", "poids_g") \
                        else _entier(v or 0, c, 0)
                    if c in ("escompte_bp", "commission_bp") and v and v > 10000:
                        raise ErreurPiece("Pourcentage invalide — 100 % au plus.")
                elif c == "contact_id":
                    v = None if v in ("", None) else _entier(v, "Contact")
                    if v and not conn.execute("SELECT 1 FROM gc_tiers_contacts WHERE id=? AND tiers_id=?",
                                              (v, p["tiers_id"])).fetchone():
                        raise ErreurPiece("Contact d'un autre tiers.")
                elif c == "transporteur_id":
                    v = None if v in ("", None) else _entier(v, "Transporteur")
                    if v and not conn.execute("SELECT 1 FROM expe_transporteurs WHERE id=?", (v,)).fetchone():
                        raise ErreurPiece("Transporteur inconnu.")
                elif c == "representant_id":
                    v = None if v in ("", None) else _entier(v, "Représentant")
                    if v and not conn.execute("SELECT 1 FROM users WHERE id=?", (v,)).fetchone():
                        raise ErreurPiece("Représentant inconnu.")
                elif c in ("date_livraison", "date_validite", "date_expedition", "date_ouverture"):
                    v = v or None
                else:
                    v = "" if v is None and c in CHAMPS_TEXTE else v
                if c == "date_piece" and not v:
                    raise ErreurPiece("Date de pièce obligatoire.")
                sets.append(f"{c}=?")
                vals.append(v)
        if sets:
            conn.execute(f"UPDATE gc_pieces SET {', '.join(sets)} WHERE id=?", (*vals, piece_id))
        # Date d'expédition absente : livraison − jours d'expédition (calendaires).
        q = conn.execute("SELECT date_livraison, date_expedition, jours_expedition FROM gc_pieces WHERE id=?",
                         (piece_id,)).fetchone()
        if q["date_livraison"] and not q["date_expedition"]:
            exp = date.fromisoformat(q["date_livraison"][:10]) - timedelta(days=int(q["jours_expedition"] or 0))
            conn.execute("UPDATE gc_pieces SET date_expedition=? WHERE id=?", (exp.isoformat(), piece_id))

    if lignes is not None:
        amont_ok = [k for k, v in TYPES.items() if p["type"] in v["aval"]]
        conn.execute("DELETE FROM gc_pieces_lignes WHERE piece_id=?", (piece_id,))
        for i, l in enumerate(lignes, start=1):
            art = None
            if l.get("article_id"):
                art = conn.execute("SELECT * FROM gc_articles WHERE id=?", (_entier(l["article_id"], "Article"),)).fetchone()
                if not art:
                    raise ErreurPiece(f"Ligne {i} : article introuvable.")
            if (art is not None and TYPES[p["type"]]["sens"] == "vente" and art["nature"] == "pf"
                    and art["client_id"] and art["client_id"] != p["tiers_id"]):
                raise ErreurPiece(f"Ligne {i} : {art['code']} est le produit d'un autre client.")
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
            origine_p = l.get("origine_prod")
            if origine_p is None:
                origine_p = _t(art, "origine_prod") or ("fabrication" if art["nature"] == "pf" else "")
            if origine_p and origine_p not in ORIGINES:
                raise ErreurPiece(f"Ligne {i} : origine inconnue.")
            labo = l.get("laboratoire")
            if labo is None:
                labo = "renouvellement" if art["nature"] == "pf" else ""
            if labo and labo not in LABORATOIRES:
                raise ErreurPiece(f"Ligne {i} : laboratoire inconnu.")
            adr_l = l.get("adresse_livraison_id") or None
            if adr_l and not conn.execute("SELECT 1 FROM gc_tiers_adresses WHERE id=? AND tiers_id=?",
                                          (adr_l, p["tiers_id"])).fetchone():
                raise ErreurPiece(f"Ligne {i} : adresse d'un autre tiers.")
            ref_c = l.get("ref_client")
            if ref_c is None:
                ref_c = _t(art, "ref_client") or ""
            type_l = l.get("type_ligne") or "livrer_facturer"
            if type_l not in TYPES_LIGNE:
                raise ErreurPiece(f"Ligne {i} : type de ligne inconnu.")
            conn.execute(
                """INSERT INTO gc_pieces_lignes (piece_id, rang, article_id, libelle, quantite_milli, unite,
                       base_prix, prix_cents, remise_bp, tva_code, taux_tva_bp, montant_ht_cents,
                       date_livraison, date_expedition, ligne_amont_id, notes, origine_prod, laboratoire,
                       ref_client, nb_livraisons, adresse_livraison_id, type_ligne, laize_dmm, ml_par_bobine_milli,
                       dates_confirmees, zone_rangement, zone_douane)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (piece_id, i, art["id"], libelle, q, art["unite"], base, prix_c, rem, code_tva,
                 taux_tva(conn, code_tva), calculs.montant_ligne(q, prix_c, base, rem),
                 l.get("date_livraison") or None, l.get("date_expedition") or None, amont,
                 str(l.get("notes") or ""), origine_p, labo, str(ref_c), _entier(l.get("nb_livraisons") or 1, "Livraisons", 1),
                 adr_l, type_l,
                 _entier(l["laize_dmm"], "Laize", 1) if l.get("laize_dmm") else _t(art, "format_l_dmm"),
                 _entier(l["ml_par_bobine_milli"], "Longueur de bobine", 1) if l.get("ml_par_bobine_milli")
                 else _t(art, "ml_par_bobine_milli"),
                 1 if l.get("dates_confirmees") in (True, 1, "1") else 0,
                 str(l.get("zone_rangement") or ""), str(l.get("zone_douane") or "")))
    _maj_totaux(conn, piece_id)


def _maj_totaux(conn, piece_id: int) -> None:
    p = _piece(conn, piece_id)
    lignes = conn.execute(
        "SELECT montant_ht_cents, taux_tva_bp FROM gc_pieces_lignes WHERE piece_id=? AND article_id IS NOT NULL",
        (piece_id,)).fetchall()
    tot = calculs.totaux([dict(l) for l in lignes], p["remise_bp"], _t(p, "escompte_bp") or 0)
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
                           ligne_id, valeur_cents, cree_par, cree_le, laize_dmm)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (p["date_piece"][:10], l["article_id"], p["depot"], sens_stock * int(l["quantite_milli"]),
                     "livraison" if sens_stock < 0 else "reception", piece_id, l["id"],
                     l["montant_ht_cents"], _nom(user), now,
                     (l["laize_dmm"] or None) if sens_stock > 0 and "laize_dmm" in l.keys() else None))

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


def bat_article(conn, article_id: int) -> str:
    """État du BAT lié à l'article : '' si aucun, sinon a_faire / en_attente / valide."""
    a = conn.execute("SELECT bat_id FROM gc_articles WHERE id=?", (article_id,)).fetchone()
    if not a or "bat_id" not in a.keys() or not a["bat_id"]:
        return ""
    try:
        b = conn.execute("SELECT statut FROM bat_entries WHERE id=?", (a["bat_id"],)).fetchone()
    except Exception:
        return ""
    return b["statut"] if b else ""


def alertes_bat(conn, piece_id: int) -> list[str]:
    """Lignes en création ou modification dont le BAT n'est pas validé.
    N'empêche rien : l'écran l'affiche (à durcir si Eugène le décide)."""
    out = []
    for l in conn.execute(
        """SELECT l.article_id, a.code, COALESCE(NULLIF(l.laboratoire,''), la.laboratoire) AS labo
           FROM gc_pieces_lignes l JOIN gc_articles a ON a.id=l.article_id
           LEFT JOIN gc_pieces_lignes la ON la.id=l.ligne_amont_id
           WHERE l.piece_id=?""", (piece_id,)).fetchall():
        if l["labo"] in LABORATOIRES_AVEC_BAT:
            etat = bat_article(conn, l["article_id"])
            if etat != "valide":
                out.append(f"{l['code']} : BAT {BAT_LIBELLES.get(etat, 'non rattaché').lower()} — la ligne est en "
                           f"{LABORATOIRES[l['labo']].lower()}.")
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
               "tva_code": l["tva_code"], "notes": l["notes"], "type_ligne": _t(l, "type_ligne"),
               "origine_prod": _t(l, "origine_prod"), "laboratoire": _t(l, "laboratoire"), "ref_client": _t(l, "ref_client")}
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
    for amont in _pieces_amont(conn, of_id):     # une ligne « à stocker » se solde à la production
        recalculer_statut(conn, amont)
    return int(cur.lastrowid)


def declarer_consommation(conn, of_id: int, article_id: int, quantite_milli: int, lot: str = "",
                          jour: str | None = None, user: dict | None = None, laize_dmm: int | None = None) -> int:
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
               commentaire, cree_par, cree_le, laize_dmm) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (jour or now[:10], a["id"], p["depot"], -q, "consommation", str(lot or ""), of_id,
         "Consommation " + (p["numero"] or ""), _nom(user), now,
         _entier(laize_dmm, "Laize", 1) if laize_dmm not in (None, "", 0) else None))
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
    net = int(p["total_ttc_cents"]) - int(_t(p, "acompte_cents") or 0)
    if net > 0:
        conn.execute("INSERT INTO gc_echeances (piece_id, date_echeance, montant_cents) VALUES (?,?,?)",
                     (piece_id, e.isoformat(), net))


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
        if p["type"] == "marche" and p["date_validite"] and p["date_validite"][:10] < _aujourdhui():
            raise ErreurPiece(f"Marché {p['numero']} échu le {p['date_validite'][8:10]}/{p['date_validite'][5:7]}/{p['date_validite'][:4]}.")
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
            tl = _t(l, "type_ligne") or "livrer_facturer"
            if cible == "of":
                a = conn.execute("SELECT nature, gere_stock FROM gc_articles WHERE id=?", (l["article_id"],)).fetchone()
                if not a or a["nature"] != "pf":
                    continue   # on ne fabrique que des produits finis
            if cible == "bl" and tl == "stocker":
                continue       # fabriquée pour le stock : ne se livre pas
            if cible == "of" and (_t(l, "origine_prod") or "fabrication") != "fabrication":
                continue       # servie depuis le stock ou sous-traitée : pas d'OF
            if cible in ("facture", "avoir") and tl == "livrer_sans_facture":
                continue       # livrée sans facture
            deja = qte_aval(conn, l["id"], reprise)
            if cible == "of":
                # Ce qui est déjà livré n'est plus à fabriquer.
                deja = max(deja, qte_aval(conn, l["id"], ["bl"]))
            reste = int(l["quantite_milli"]) - deja
            if reste <= 0:
                continue
            lignes.append({
                "article_id": l["article_id"], "libelle": l["libelle"], "quantite_milli": reste,
                "base_prix": l["base_prix"], "prix_cents": l["prix_cents"], "remise_bp": l["remise_bp"],
                "tva_code": l["tva_code"], "date_livraison": l["date_livraison"], "ligne_amont_id": l["id"],
                "date_expedition": _t(l, "date_expedition"), "origine_prod": _t(l, "origine_prod"),
                "laboratoire": _t(l, "laboratoire"), "ref_client": _t(l, "ref_client"),
                "adresse_livraison_id": _t(l, "adresse_livraison_id"), "type_ligne": _t(l, "type_ligne"),
                "laize_dmm": _t(l, "laize_dmm"), "ml_par_bobine_milli": _t(l, "ml_par_bobine_milli"),
                "dates_confirmees": _t(l, "dates_confirmees"),
            })
    if not lignes:
        raise ErreurPiece("Plus rien à reprendre : tout a déjà été repris.")
    nouvelle = creer(conn, cible, ps[0]["tiers_id"], user)
    src = ps[0]
    entete = {k: src[k] for k in REPORT_ENTETE if k in src.keys()}
    if cible in ("facture", "avoir", "facture_fournisseur"):
        entete.pop("date_livraison", None)
        entete.pop("date_expedition", None)
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

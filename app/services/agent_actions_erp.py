"""
Agent IA — actions et lectures du nouvel ERP (`/api/erp2`).

Même contrat que `agent_actions.py`, qui importe ce module et ajoute ces
entrées à son catalogue : l'agent propose, l'utilisateur confirme sur une
carte, et c'est l'API de l'ERP qui exécute avec ses droits, ses contrôles et
son journal. Rien n'est écrit ici.

Deux ajouts au format commun :
- `construire(valeurs) -> corps` : l'API de l'ERP attend des corps imbriqués
  (fiche + adresses + contacts, en-tête + lignes) ;
- `detailler(conn, valeurs) -> [[libellé, valeur]]` : la carte montre ce qui
  sera fait en clair (raison sociale, articles et quantités), et refuse un
  identifiant inexistant avant que l'utilisateur ne le voie.

Unités : l'agent parle en unités et en euros ; la conversion vers les
millièmes et les centimes de l'ERP se fait ici, jamais par le modèle.
"""

from __future__ import annotations

from typing import Any

from config import ROLES_ERP2

TYPES_PIECE = "devis,marche,commande,bl,facture,avoir,aof,cde_fournisseur,reception,facture_fournisseur,of"


def _erp(user: dict) -> bool:
    return user.get("role") in ROLES_ERP2


def _invalide(msg: str):
    from app.services.agent_actions import ActionInvalide
    return ActionInvalide(msg)


def _milli(v) -> int:
    return int(round(float(str(v).replace(",", ".")) * 1000))


def _cents(v) -> int:
    return int(round(float(str(v).replace(",", ".")) * 100))


def _qte(m: int) -> str:
    return f"{m / 1000:,.3f}".rstrip("0").rstrip(".").replace(",", " ").replace(".", ",")


# ── Corps des appels ─────────────────────────────────────────────────

_CHAMPS_TIERS = ("raison_sociale", "siret", "tva_intra", "email", "telephone", "condition_paiement", "mode_paiement",
                 "notes", "nom_court", "rcs")
_CHAMPS_ADRESSE = ("adresse1", "adresse2", "code_postal", "ville", "pays")


def _corps_tiers(v: dict) -> dict:
    role = v.get("role", "client")
    t = {k: v[k] for k in _CHAMPS_TIERS if k in v}
    if role:
        t.update(est_client=int(role == "client"), est_fournisseur=int(role == "fournisseur"),
                 est_prospect=int(role == "prospect"), actif=1)
    corps = {"tiers": t}
    if any(k in v for k in _CHAMPS_ADRESSE):
        corps["adresses"] = [dict({k: v[k] for k in _CHAMPS_ADRESSE if k in v}, type="principale", libelle="Siège",
                                  par_defaut=1, pays=v.get("pays", "FR"))]
    if v.get("contact_nom"):
        corps["contacts"] = [{"nom": v["contact_nom"], "email": v.get("contact_email", ""),
                              "telephone": v.get("contact_telephone", ""), "fonction": v.get("contact_fonction", "")}]
    return corps


def _corps_tiers_modif(v: dict) -> dict:
    v = dict(v)
    v.pop("tiers_id", None)
    c = _corps_tiers(dict(v, role=None))
    c["tiers"].pop("actif", None)
    return {"tiers": c["tiers"]}      # adresses et contacts inchangés


def _lignes(lignes: list) -> list[dict]:
    out = []
    for i, l in enumerate(lignes or [], start=1):
        if not isinstance(l, dict) or not l.get("article_id") or l.get("quantite") in (None, ""):
            raise _invalide(f"Ligne {i} : article_id et quantite obligatoires.")
        d = {"article_id": int(l["article_id"]), "quantite_milli": _milli(l["quantite"])}
        if l.get("prix") not in (None, ""):
            d["prix_cents"] = _cents(l["prix"])
        for k in ("date_livraison", "date_expedition", "ref_client", "libelle", "type_ligne"):
            if l.get(k):
                d[k] = l[k]
        if l.get("laize_mm"):
            d["laize_dmm"] = int(round(float(l["laize_mm"]) * 10))
        if l.get("remise_pct"):
            d["remise_bp"] = int(round(float(l["remise_pct"]) * 100))
        out.append(d)
    if not out:
        raise _invalide("Au moins une ligne.")
    return out


def _corps_piece(v: dict) -> dict:
    ent = {k: v[k] for k in ("ref_tiers", "date_livraison", "date_expedition", "notes", "date_piece") if k in v}
    return {"type": v["type"], "tiers_id": v["tiers_id"], "entete": ent, "lignes": _lignes(v.get("lignes"))}


def _corps_lignes(v: dict) -> dict:
    ent = {k: v[k] for k in ("ref_tiers", "date_livraison", "date_expedition", "notes") if k in v}
    return {"entete": ent or None, "lignes": _lignes(v.get("lignes"))}


def _corps_article(v: dict) -> dict:
    a = {k: v[k] for k in ("libelle", "nature", "client_id", "fournisseur_id", "famille", "unite", "ref_client",
                           "designation", "base_prix") if k in v}
    for k in ("prix_vente", "prix_achat"):
        if k in v:
            a[k + "_cents"] = _cents(v[k])
    for k in ("format_l_mm", "format_a_mm"):
        if k in v:
            a[k.replace("_mm", "_dmm")] = int(round(float(v[k]) * 10))
    a.setdefault("gere_stock", 0 if v.get("nature") == "service" else 1)
    a.setdefault("actif", 1)
    return {"article": a}


def _corps_reglement(v: dict) -> dict:
    c = {"tiers_id": v["tiers_id"], "sens": v.get("sens", "encaissement"), "date_reglement": v["date_reglement"],
         "montant_cents": _cents(v["montant"]), "mode_paiement": v.get("mode_paiement"),
         "reference": v.get("reference", ""), "banque": v.get("banque")}
    if v.get("affectations"):
        c["affectations"] = [{"echeance_id": int(a["echeance_id"]), "montant_cents": _cents(a["montant"])}
                             for a in v["affectations"]]
    return c


def _corps_mouvement(v: dict) -> dict:
    c = {"type": v["type"], "article_id": v["article_id"], "depot": v["depot"], "quantite_milli": _milli(v["quantite"]),
         "lot": v.get("lot", ""), "commentaire": v.get("commentaire", "")}
    if v.get("laize_mm"):
        c["laize_dmm"] = int(round(float(v["laize_mm"]) * 10))
    if v.get("depot_destination"):
        c["depot_destination"] = v["depot_destination"]
    return c


def _corps_myao(v: dict) -> dict:
    lignes = []
    for x in v.get("lignes") or []:
        d = {k: x[k] for k in ("ligne_id", "article_id", "serie_id") if x.get(k) is not None}
        if x.get("quantite") not in (None, ""):
            d["quantite_milli"] = _milli(x["quantite"])
        if x.get("prix") not in (None, ""):
            d["prix_cents"] = _cents(x["prix"])
            d["base_prix"] = 1000
        lignes.append(d)
    return {"tiers_id": v.get("tiers_id"), "lignes": lignes}


# ── Ce que la carte affiche ──────────────────────────────────────────

def _tiers(conn, tid) -> str:
    r = conn.execute("SELECT code, raison_sociale FROM gc_tiers WHERE id=?", (int(tid),)).fetchone()
    if not r:
        raise _invalide(f"Tiers {tid} introuvable — le chercher avec lire_ecran erp_tiers_liste ou erp_recherche.")
    return f"{r['raison_sociale']} ({r['code']})"


def _piece(conn, pid) -> str:
    r = conn.execute("SELECT type, numero, statut FROM gc_pieces WHERE id=?", (int(pid),)).fetchone()
    if not r:
        raise _invalide(f"Pièce {pid} introuvable.")
    return f"{r['type']} {r['numero'] or 'brouillon'} (#{pid})"


def _detail_lignes(conn, lignes) -> list[list[str]]:
    out = []
    for i, l in enumerate(lignes or [], start=1):
        a = conn.execute("SELECT code, libelle, unite FROM gc_articles WHERE id=?",
                         (int((l or {}).get("article_id") or 0),)).fetchone()
        if not a:
            raise _invalide(f"Ligne {i} : article {(l or {}).get('article_id')} introuvable — le chercher avec lire_ecran erp_articles.")
        txt = f"{a['code']} — {a['libelle']} : {_qte(_milli(l['quantite']))} {a['unite']}"
        if l.get("prix") not in (None, ""):
            txt += f" à {float(str(l['prix']).replace(',', '.')):.4f} €".replace(".", ",")
        if l.get("date_livraison"):
            txt += f", livraison {l['date_livraison']}"
        out.append([f"Ligne {i}", txt])
    return out


def _det_tiers(conn, v):
    return [["Tiers", _tiers(conn, v["tiers_id"])]] if v.get("tiers_id") else []


def _det_piece_creer(conn, v):
    return _det_tiers(conn, v) + _detail_lignes(conn, v.get("lignes"))


def _det_piece(conn, v):
    out = [["Pièce", _piece(conn, v["piece_id"])]]
    if v.get("lignes"):
        out += _detail_lignes(conn, v["lignes"])
    return out


def _det_transformer(conn, v):
    return [["Depuis", ", ".join(_piece(conn, s) for s in v["sources"])], ["Vers", v["cible"]]]


def _det_article(conn, v):
    out = []
    if v.get("article_id"):
        a = conn.execute("SELECT code, libelle FROM gc_articles WHERE id=?", (int(v["article_id"]),)).fetchone()
        if not a:
            raise _invalide(f"Article {v['article_id']} introuvable.")
        out.append(["Article", f"{a['code']} — {a['libelle']}"])
    for k in ("client_id", "fournisseur_id"):
        if v.get(k):
            out.append(["Client" if k == "client_id" else "Fournisseur", _tiers(conn, v[k])])
    return out


def _det_myao(conn, v):
    r = conn.execute("SELECT reference, titre, statut FROM ao_demandes WHERE id=?", (int(v["ao_id"]),)).fetchone()
    if not r:
        raise _invalide(f"Demande MyAO {v['ao_id']} introuvable.")
    out = [["Demande", f"{r['reference']} — {r['titre'] or ''}".strip(" —")]]
    if v.get("tiers_id"):
        out.append(["Fournisseur", _tiers(conn, v["tiers_id"])])
    n = 0
    for x in v.get("lignes") or []:
        if not x.get("article_id"):
            continue
        n += 1
        a = conn.execute("SELECT code, libelle FROM gc_articles WHERE id=?", (int(x["article_id"]),)).fetchone()
        if not a:
            raise _invalide(f"Article {x['article_id']} introuvable.")
        out.append([f"Ligne {n}", f"{a['code']} — {a['libelle']}"])
    return out


def _det_document(conn, v):
    r = conn.execute("SELECT nom_fichier, statut FROM gc_documents WHERE id=?", (int(v["doc_id"]),)).fetchone()
    if not r:
        raise _invalide(f"Document {v['doc_id']} introuvable.")
    if r["statut"] not in ("analyse",):
        raise _invalide("Document pas encore lu, ou déjà traité : le lire d'abord (erp_document_lire).")
    out = [["Document", r["nom_fichier"]], ["Pièce préparée", "réception" if v["cible"] == "reception" else "facture fournisseur"]]
    if v.get("commande_id"):
        out.append(["Commande", _piece(conn, v["commande_id"])])
    if v.get("tiers_id"):
        out.append(["Fournisseur", _tiers(conn, v["tiers_id"])])
    return out


# ── Catalogue ────────────────────────────────────────────────────────

_LIGNES_AIDE = ("liste d'objets {article_id*, quantite* (en unités de l'article), prix (€ HT pour la base de prix "
                "de l'article ; absent = tarif de l'ERP), date_livraison, date_expedition, ref_client, laize_mm, remise_pct, "
                "type_ligne (livrer_facturer|livrer_sans_facture|stocker)}")

ACTIONS: list[dict[str, Any]] = [
    {
        "cle": "erp_tiers_creer", "libelle": "ERP — nouveau tiers", "module": "erp2",
        "methode": "POST", "chemin": "/api/erp2/tiers", "lien": "/fichiers/clients", "autorise": _erp,
        "aide": "Crée un client, un prospect ou un fournisseur dans l'ERP, avec son adresse principale et un "
                "interlocuteur. Le code est attribué automatiquement. Vérifier d'abord qu'il n'existe pas (erp_recherche).",
        "params": {
            "role": ("enum:client,fournisseur,prospect", True, "Type de tiers", ""),
            "raison_sociale": ("str", True, "Raison sociale", ""),
            "siret": ("str", False, "SIRET", ""), "tva_intra": ("str", False, "N° TVA", ""), "rcs": ("str", False, "RCS", ""),
            "nom_court": ("str", False, "Code AN", ""),
            "email": ("str", False, "Email", ""), "telephone": ("str", False, "Téléphone", ""),
            "adresse1": ("str", False, "Adresse", ""), "adresse2": ("str", False, "Complément", ""),
            "code_postal": ("str", False, "Code postal", ""), "ville": ("str", False, "Ville", ""),
            "pays": ("str", False, "Pays", "code ISO, ex. FR"),
            "contact_nom": ("str", False, "Interlocuteur", ""), "contact_email": ("str", False, "Email interlocuteur", ""),
            "contact_telephone": ("str", False, "Téléphone interlocuteur", ""), "contact_fonction": ("str", False, "Fonction", ""),
            "condition_paiement": ("str", False, "Conditions de paiement", "code du référentiel ERP"),
            "mode_paiement": ("str", False, "Mode de paiement", "code du référentiel ERP"),
            "notes": ("str", False, "Notes", ""),
        },
        "construire": _corps_tiers,
    },
    {
        "cle": "erp_tiers_modifier", "libelle": "ERP — modification d'un tiers", "module": "erp2",
        "methode": "PUT", "chemin": "/api/erp2/tiers/{tiers_id}", "lien": "/fichiers/clients", "autorise": _erp,
        "aide": "Modifie les champs donnés de la fiche d'un tiers (les autres restent inchangés ; adresses et contacts aussi).",
        "params": {
            "tiers_id": ("int", True, "Tiers (gc_tiers.id)", ""),
            "raison_sociale": ("str", False, "Raison sociale", ""), "siret": ("str", False, "SIRET", ""),
            "tva_intra": ("str", False, "N° TVA", ""), "email": ("str", False, "Email", ""),
            "telephone": ("str", False, "Téléphone", ""), "condition_paiement": ("str", False, "Conditions de paiement", ""),
            "mode_paiement": ("str", False, "Mode de paiement", ""), "notes": ("str", False, "Notes", ""),
        },
        "construire": _corps_tiers_modif, "detailler": _det_tiers,
    },
    {
        "cle": "erp_piece_creer", "libelle": "ERP — nouvelle pièce (brouillon)", "module": "erp2",
        "methode": "POST", "chemin": "/api/erp2/pieces", "lien": "/", "autorise": _erp,
        "aide": "Crée une pièce en BROUILLON avec ses lignes : devis, commande client, commande fournisseur "
                "(cde_fournisseur), etc. Les prix absents viennent des tarifs de l'ERP. Pour enchaîner une étape "
                "(commande → BL → facture, commande fournisseur → réception), utiliser erp_transformer, pas cette action.",
        "params": {
            "type": (f"enum:{TYPES_PIECE}", True, "Type de pièce", ""),
            "tiers_id": ("int", True, "Tiers (gc_tiers.id)", ""),
            "lignes": ("objets", True, "Lignes", _LIGNES_AIDE),
            "ref_tiers": ("str", False, "Réf. du tiers", "n° de commande client, réf. fournisseur"),
            "date_livraison": ("date", False, "Livraison prévue", ""),
            "date_expedition": ("date", False, "Expédition prévue", ""),
            "notes": ("str", False, "Notes imprimées", ""),
        },
        "construire": _corps_piece, "detailler": _det_piece_creer,
    },
    {
        "cle": "erp_piece_modifier", "libelle": "ERP — modification d'un brouillon", "module": "erp2",
        "methode": "PUT", "chemin": "/api/erp2/pieces/{piece_id}", "lien": "/", "autorise": _erp,
        "aide": "Remplace les lignes d'une pièce en brouillon (toutes : relire la pièce et renvoyer la liste complète).",
        "params": {
            "piece_id": ("int", True, "Pièce (gc_pieces.id)", ""),
            "lignes": ("objets", True, "Lignes", _LIGNES_AIDE + " ; garder ligne_amont_id absent"),
            "ref_tiers": ("str", False, "Réf. du tiers", ""), "date_livraison": ("date", False, "Livraison prévue", ""),
            "notes": ("str", False, "Notes imprimées", ""),
        },
        "construire": _corps_lignes, "detailler": _det_piece,
    },
    {
        "cle": "erp_piece_valider", "libelle": "ERP — validation d'une pièce", "module": "erp2",
        "methode": "POST", "chemin": "/api/erp2/pieces/{piece_id}/valider", "lien": "/", "autorise": _erp,
        "aide": "Valide un brouillon : numéro définitif, mouvements de stock, échéances. Irréversible (seule l'annulation reste).",
        "params": {"piece_id": ("int", True, "Pièce (gc_pieces.id)", "")},
        "detailler": _det_piece,
    },
    {
        "cle": "erp_transformer", "libelle": "ERP — étape suivante", "module": "erp2",
        "methode": "POST", "chemin": "/api/erp2/pieces/transformer", "lien": "/", "autorise": _erp,
        "aide": "Crée la pièce suivante en brouillon depuis des pièces validées du même tiers, avec les quantités "
                "restant à reprendre : devis→commande, commande→bl ou of, bl→facture, facture→avoir, "
                "cde_fournisseur→reception, reception→facture_fournisseur, aof→cde_fournisseur.",
        "params": {"sources": ("ids", True, "Pièces d'origine (gc_pieces.id)", ""),
                   "cible": (f"enum:{TYPES_PIECE}", True, "Pièce à créer", "")},
        "detailler": _det_transformer,
    },
    {
        "cle": "erp_piece_annuler", "libelle": "ERP — annulation d'une pièce", "module": "erp2",
        "methode": "POST", "chemin": "/api/erp2/pieces/{piece_id}/annuler", "lien": "/", "autorise": _erp,
        "aide": "Annule une pièce validée (contre-mouvements de stock). Une facture s'annule par un avoir, pas ainsi.",
        "params": {"piece_id": ("int", True, "Pièce (gc_pieces.id)", "")},
        "detailler": _det_piece,
    },
    {
        "cle": "erp_article_creer", "libelle": "ERP — nouvel article", "module": "erp2",
        "methode": "POST", "chemin": "/api/erp2/articles", "lien": "/fichiers/articles", "autorise": _erp,
        "aide": "Crée un produit fini (nature pf : client_id obligatoire, code attribué « code client/rang »), "
                "une matière (mp) ou une prestation (service).",
        "params": {
            "nature": ("enum:pf,mp,service", True, "Nature", ""), "libelle": ("str", True, "Libellé", ""),
            "client_id": ("int", False, "Client (gc_tiers.id)", "obligatoire pour pf"),
            "fournisseur_id": ("int", False, "Fournisseur habituel (gc_tiers.id)", ""),
            "famille": ("str", False, "Famille", "code du référentiel"), "unite": ("str", False, "Unité", "ex. ETQ, ML, M2"),
            "base_prix": ("int", False, "Prix pour", "1000 = au mille"),
            "prix_vente": ("num", False, "Prix de vente HT (€)", ""), "prix_achat": ("num", False, "Prix d'achat HT (€)", ""),
            "format_l_mm": ("num", False, "Laize / format L (mm)", ""), "format_a_mm": ("num", False, "Avance (mm)", ""),
            "ref_client": ("str", False, "Réf. produit client", ""), "designation": ("str", False, "Désignation", "lignes suivantes"),
        },
        "construire": _corps_article, "detailler": _det_article,
    },
    {
        "cle": "erp_reglement", "libelle": "ERP — règlement", "module": "erp2",
        "methode": "POST", "chemin": "/api/erp2/reglements", "lien": "/compta/reglements", "autorise": _erp,
        "aide": "Enregistre un encaissement client ou un paiement fournisseur, affecté aux échéances données "
                "(lire erp_echeances pour leurs id).",
        "params": {
            "tiers_id": ("int", True, "Tiers (gc_tiers.id)", ""),
            "sens": ("enum:encaissement,decaissement", True, "Sens", ""),
            "date_reglement": ("date", True, "Date", ""), "montant": ("num", True, "Montant (€)", ""),
            "mode_paiement": ("str", False, "Mode", "code du référentiel"), "reference": ("str", False, "Référence", ""),
            "banque": ("str", False, "Banque", "code du référentiel"),
            "affectations": ("objets", False, "Affectations", "liste {echeance_id*, montant* (€)}"),
        },
        "construire": _corps_reglement, "detailler": _det_tiers,
    },
    {
        "cle": "erp_myao_commande", "libelle": "ERP — commande fournisseur depuis MyAO", "module": "erp2",
        "methode": "POST", "chemin": "/api/erp2/myao/{ao_id}/commande", "lien": "/achats/myao", "autorise": _erp,
        "aide": "Transforme une demande MyAO clôturée en commande fournisseur en brouillon chez le fournisseur retenu. "
                "Lire d'abord erp_myao_demande : lignes, séries, prix proposés, article ERP déjà associé. "
                "Une ligne sans article_id n'est pas commandée ; un prix à la bobine est à donner (prix au mille, €).",
        "params": {
            "ao_id": ("int", True, "Demande MyAO (ao_demandes.id)", ""),
            "tiers_id": ("int", False, "Fournisseur ERP (gc_tiers.id)", "absent = celui déjà associé"),
            "lignes": ("objets", True, "Lignes", "liste {ligne_id*, article_id, serie_id, quantite (unités), prix (€ HT au mille)}"),
        },
        "construire": lambda v: _corps_myao(v), "detailler": lambda conn, v: _det_myao(conn, v),
    },
    {
        "cle": "erp_document_lire", "libelle": "ERP — lecture d'un document fournisseur", "module": "erp2",
        "methode": "POST", "chemin": "/api/erp2/documents/{doc_id}/analyser", "lien": "/achats/documents", "autorise": _erp,
        "aide": "Fait lire par l'IA un document fournisseur déposé (statut « depose » ou « erreur »).",
        "params": {"doc_id": ("int", True, "Document (gc_documents.id)", "")},
    },
    {
        "cle": "erp_document_preparer", "libelle": "ERP — pièce préparée depuis un document fournisseur", "module": "erp2",
        "methode": "POST", "chemin": "/api/erp2/documents/{doc_id}/preparer", "lien": "/achats/documents", "autorise": _erp,
        "aide": "Depuis un document lu (erp_document) : prépare en BROUILLON la réception (BL) ou la facture fournisseur, "
                "aux quantités et prix du document, sur la commande rapprochée (ou commande_id). Signaler d'abord les "
                "écarts relevés par erp_document.",
        "params": {"doc_id": ("int", True, "Document (gc_documents.id)", ""),
                   "cible": ("enum:reception,facture_fournisseur", True, "Pièce à préparer", ""),
                   "commande_id": ("int", False, "Commande fournisseur (gc_pieces.id)", ""),
                   "tiers_id": ("int", False, "Fournisseur ERP (gc_tiers.id)", "si non reconnu")},
        "detailler": lambda conn, v: _det_document(conn, v),
    },
    {
        "cle": "erp_mouvement_stock", "libelle": "ERP — mouvement de stock", "module": "erp2",
        "methode": "POST", "chemin": "/api/erp2/mouvements", "lien": "/stocks/etat", "autorise": _erp,
        "aide": "Inventaire (quantité comptée), ajustement (+/−) ou transfert entre dépôts, hors pièce.",
        "params": {
            "type": ("enum:inventaire,ajustement,transfert", True, "Mouvement", ""),
            "article_id": ("int", True, "Article (gc_articles.id)", ""),
            "depot": ("str", True, "Dépôt", "code du référentiel"), "quantite": ("num", True, "Quantité", "en unités"),
            "depot_destination": ("str", False, "Vers le dépôt", "transfert"), "laize_mm": ("num", False, "Laize (mm)", ""),
            "lot": ("str", False, "Lot", ""), "commentaire": ("str", False, "Commentaire", ""),
        },
        "construire": _corps_mouvement, "detailler": _det_article,
    },
]

def consigne_page(page: dict | None) -> str:
    """Ajout au prompt quand l'utilisateur est dans le nouvel ERP."""
    url = str((page or {}).get("url") or "")
    if "erp." not in url and "/_erp" not in url:
        return ""
    return ("\nL'utilisateur est dans le NOUVEL ERP (erp.mysifa.com, tables gc_*), pas dans MyStock ni RVGI : "
            "pour ses tiers, articles, pièces, stock et règlements, lire avec lire_ecran erp_* et écrire avec "
            "les actions erp_*. Quantités en unités de l'article, prix en euros HT : la conversion est faite à "
            "l'exécution. Une pièce se crée en brouillon ; la valider est une action à part.")


# ── Lectures d'écran ERP ─────────────────────────────────────────────
LECTURES: list[dict[str, Any]] = [
    {"cle": "erp_recherche", "chemin": "/api/erp2/recherche",
     "aide": "ERP : recherche globale (tiers, articles, pièces) sur un fragment.", "params": {"q": ("str", True, "2 caractères au moins")}},
    {"cle": "erp_tiers_liste", "chemin": "/api/erp2/tiers",
     "aide": "ERP : clients, prospects ou fournisseurs (id, code, raison sociale, adresse, encours).",
     "params": {"role": ("str", False, "client | fournisseur | prospect")}},
    {"cle": "erp_tiers", "chemin": "/api/erp2/tiers/{tiers_id}",
     "aide": "ERP : fiche complète d'un tiers (adresses, interlocuteurs, pièces récentes, tarifs).",
     "params": {"tiers_id": ("int", True, "gc_tiers.id")}},
    {"cle": "erp_articles", "chemin": "/api/erp2/articles",
     "aide": "ERP : articles (id, code, libellé, client, unité, prix, stock).", "params": {"nature": ("str", False, "pf | mp | service")}},
    {"cle": "erp_article", "chemin": "/api/erp2/articles/{article_id}",
     "aide": "ERP : fiche article avec tarifs, stock et derniers mouvements.", "params": {"article_id": ("int", True, "gc_articles.id")}},
    {"cle": "erp_prix", "chemin": "/api/erp2/prix",
     "aide": "ERP : prix appliqué pour un article, un tiers et une quantité (millièmes).",
     "params": {"article_id": ("int", True, ""), "tiers_id": ("int", False, ""), "quantite_milli": ("int", False, "quantité × 1000"),
                "sens": ("str", False, "vente | achat")}},
    {"cle": "erp_pieces", "chemin": "/api/erp2/pieces",
     "aide": "ERP : liste des pièces d'un ou plusieurs types (id, numéro, tiers, dates, totaux, état).",
     "params": {"types": ("str", True, "ex. commande ou facture,avoir")}},
    {"cle": "erp_piece", "chemin": "/api/erp2/pieces/{piece_id}",
     "aide": "ERP : pièce complète (lignes, pièces liées, échéances, mouvements, cahier des charges).",
     "params": {"piece_id": ("int", True, "gc_pieces.id")}},
    {"cle": "erp_carnet", "chemin": "/api/erp2/carnet",
     "aide": "ERP : tableau de bord par ligne (dates, quantités reprises, reste, situation OF, BAT, pièce d'origine).",
     "params": {"types": ("str", True, "ex. commande, bl, cde_fournisseur")}},
    {"cle": "erp_rapprochement", "chemin": "/api/erp2/pieces/{piece_id}/rapprochement",
     "aide": "ERP : facture fournisseur rapprochée de ses réceptions et des prix commandés (écarts de quantité et de prix par ligne).",
     "params": {"piece_id": ("int", True, "gc_pieces.id d'une facture fournisseur")}},
    {"cle": "erp_myao_demandes", "chemin": "/api/erp2/myao",
     "aide": "ERP : demandes de prix MyAO (état, fournisseur retenu, commande ERP déjà créée ou non).", "params": {}},
    {"cle": "erp_myao_demande", "chemin": "/api/erp2/myao/{ao_id}",
     "aide": "ERP : une demande MyAO prête à commander (lignes, séries, prix du fournisseur retenu, article ERP proposé).",
     "params": {"ao_id": ("int", True, "ao_demandes.id")}},
    {"cle": "erp_documents", "chemin": "/api/erp2/documents",
     "aide": "ERP : documents fournisseurs déposés (BL, factures) : état de lecture, fournisseur, n°, commande citée, pièce créée.",
     "params": {"piece_id": ("int", False, "documents d'une pièce")}},
    {"cle": "erp_document", "chemin": "/api/erp2/documents/{doc_id}",
     "aide": "ERP : un document fournisseur lu par l'IA, rapproché de la commande : lignes du document, article commandé, "
             "reste à recevoir, prix commandé, écarts (quantité, unité, prix).",
     "params": {"doc_id": ("int", True, "gc_documents.id"), "commande_id": ("int", False, "forcer la commande à comparer")}},
    {"cle": "erp_valorisation", "chemin": "/api/erp2/valorisation",
     "aide": "ERP : stock valorisé à une date (quantité et prix à cette date, source du prix, charges de production et "
             "frais de stockage de MyStock, totaux matières / produits finis).",
     "params": {"date": ("str", False, "AAAA-MM-JJ, défaut aujourd'hui")}},
    {"cle": "erp_stock", "chemin": "/api/erp2/stock",
     "aide": "ERP : stock par article, dépôt et laize, avec mini / maxi.", "params": {}},
    {"cle": "erp_echeances", "chemin": "/api/erp2/echeances",
     "aide": "ERP : échéances (montant, réglé, reste) ; ouvertes=true pour celles à régler.",
     "params": {"tiers_id": ("int", False, ""), "ouvertes": ("str", False, "true")}},
    {"cle": "erp_stats", "chemin": "/api/erp2/stats",
     "aide": "ERP : chiffre d'affaires par client, article, représentant et mois.",
     "params": {"debut": ("str", True, "AAAA-MM-JJ"), "fin": ("str", True, "AAAA-MM-JJ")}},
    {"cle": "erp_referentiels", "chemin": "/api/erp2/meta",
     "aide": "ERP : référentiels (familles, unités, TVA, conditions et modes de paiement, dépôts, pays…) et types de pièces.",
     "params": {}},
]

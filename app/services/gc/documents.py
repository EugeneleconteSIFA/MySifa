"""Documents fournisseurs : dépôt, lecture par l'IA, rapprochement, préparation.

Le parcours :
1. un BL ou une facture fournisseur est déposé (PDF ou image) ;
2. l'IA le lit et rend ce qu'il contient, sans rien inventer (un champ absent
   reste vide) : fournisseur, numéro, date, n° de NOTRE commande, lignes ;
3. l'ERP retrouve le fournisseur, la commande et ses lignes, et compare
   quantités, unités et prix ;
4. sur confirmation, il prépare en BROUILLON la réception (BL) ou la facture
   fournisseur, aux quantités et prix du document. Rien n'est validé ici.

L'appel au modèle est injectable (`lecteur`) : les tests n'appellent pas l'API.
"""
from __future__ import annotations

import base64
import json
import os
import re
import uuid
from datetime import datetime

from config import ERP2_DOC_IA_MODELE, ERP2_DOC_MAX_OCTETS, UPLOADS_ROOT
from app.services.gc import calculs, pieces
from app.services.gc.pieces import ErreurPiece

MIMES = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}
DOSSIER = os.path.join(UPLOADS_ROOT, "erp", "documents")


def _maintenant() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


# ── Dépôt ──────────────────────────────────────────────────────────────

def deposer(conn, contenu: bytes, nom: str, piece_id: int | None = None, user: dict | None = None) -> int:
    ext = os.path.splitext(nom or "")[1].lower()
    if ext not in MIMES:
        raise ErreurPiece("Format refusé : PDF, PNG, JPG ou WEBP.")
    if not contenu:
        raise ErreurPiece("Fichier vide.")
    if len(contenu) > ERP2_DOC_MAX_OCTETS:
        raise ErreurPiece(f"Fichier trop lourd : {ERP2_DOC_MAX_OCTETS // (1024 * 1024)} Mo au plus.")
    if piece_id and not conn.execute("SELECT 1 FROM gc_pieces WHERE id=?", (piece_id,)).fetchone():
        raise ErreurPiece("Pièce introuvable.")
    sous = datetime.now().strftime("%Y-%m")
    os.makedirs(os.path.join(DOSSIER, sous), exist_ok=True)
    chemin = os.path.join(sous, uuid.uuid4().hex + ext)
    with open(os.path.join(DOSSIER, chemin), "wb") as f:
        f.write(contenu)
    tiers = None
    if piece_id:
        r = conn.execute("SELECT tiers_id FROM gc_pieces WHERE id=?", (piece_id,)).fetchone()
        tiers = r["tiers_id"] if r else None
    cur = conn.execute(
        """INSERT INTO gc_documents (piece_id, tiers_id, nom_fichier, chemin, mime, taille, cree_par, cree_le)
           VALUES (?,?,?,?,?,?,?,?)""",
        (piece_id or None, tiers, os.path.basename(nom)[:200], chemin, MIMES[ext], len(contenu),
         str((user or {}).get("nom") or ""), _maintenant()))
    return int(cur.lastrowid)


def fichier(conn, doc_id: int) -> tuple[str, str, str]:
    """(chemin absolu, nom, mime) — servi en pièce jointe, jamais exécuté."""
    d = _doc(conn, doc_id)
    p = os.path.normpath(os.path.join(DOSSIER, d["chemin"]))
    if not p.startswith(os.path.normpath(DOSSIER)) or not os.path.exists(p):
        raise ErreurPiece("Fichier introuvable.")
    return p, d["nom_fichier"], d["mime"]


def _doc(conn, doc_id: int):
    d = conn.execute("SELECT * FROM gc_documents WHERE id=?", (doc_id,)).fetchone()
    if not d:
        raise ErreurPiece("Document introuvable.")
    return d


def lister(conn, piece_id: int | None = None) -> list[dict]:
    filtre, args = ("WHERE d.piece_id=?", (piece_id,)) if piece_id else ("", ())
    out = []
    for r in conn.execute(
        f"""SELECT d.id, d.piece_id, d.tiers_id, d.nature, d.nom_fichier, d.taille, d.statut, d.erreur, d.cree_par, d.cree_le,
                   d.analyse_le, d.extraction, t.raison_sociale AS tiers_nom, p.type AS piece_type, p.numero AS piece_numero
            FROM gc_documents d LEFT JOIN gc_tiers t ON t.id=d.tiers_id LEFT JOIN gc_pieces p ON p.id=d.piece_id
            {filtre} ORDER BY d.id DESC LIMIT 500""", args).fetchall():
        x = dict(r)
        ex = json.loads(x.pop("extraction") or "{}")
        x["numero_document"] = ex.get("numero")
        x["date_document"] = ex.get("date")
        x["fournisseur_lu"] = (ex.get("fournisseur") or {}).get("nom")
        x["ref_commande_lue"] = ex.get("ref_commande")
        x["nb_lignes"] = len(ex.get("lignes") or [])
        out.append(x)
    return out


# ── Lecture par l'IA ───────────────────────────────────────────────────

_CONSIGNE = """Tu lis un document d'un FOURNISSEUR de SIFA (fabricant d'étiquettes) : bon de livraison ou facture.
Rends ce qui est écrit, rien d'autre. Un champ absent reste absent : jamais de valeur supposée, jamais de zéro inventé.
- nature : « bl » pour un bon de livraison / bordereau d'expédition, « facture » pour une facture ou un avoir, « autre » sinon.
- ref_commande : le numéro de commande de SIFA (« votre commande », « your order », « V/Cde », « PO »), pas celui du fournisseur.
- Lignes : une par article livré ou facturé, dans l'ordre du document. Quantité et prix tels qu'écrits, nombres décimaux
  avec un point. L'unité telle qu'écrite (m², ML, kg, bobines, pièces, mille…). La laize en mm si elle est indiquée.
- Les frais (port, emballage) sont des lignes comme les autres, avec leur libellé.
Appelle l'outil `document_fournisseur`."""

_OUTIL = {
    "name": "document_fournisseur",
    "description": "Contenu lu sur le document du fournisseur.",
    "input_schema": {
        "type": "object",
        "properties": {
            "nature": {"type": "string", "enum": ["bl", "facture", "autre"]},
            "fournisseur": {"type": "object", "properties": {
                "nom": {"type": "string"}, "siret": {"type": "string"}, "tva": {"type": "string"}}},
            "numero": {"type": "string", "description": "N° du BL ou de la facture chez le fournisseur"},
            "date": {"type": "string", "description": "AAAA-MM-JJ"},
            "ref_commande": {"type": "string", "description": "N° de commande de SIFA cité sur le document"},
            "lignes": {"type": "array", "items": {"type": "object", "properties": {
                "reference": {"type": "string", "description": "référence de l'article chez le fournisseur"},
                "designation": {"type": "string"},
                "quantite": {"type": "number"}, "unite": {"type": "string"},
                "prix_unitaire": {"type": "number", "description": "prix HT unitaire tel qu'écrit"},
                "base_prix": {"type": "number", "description": "quantité à laquelle s'applique le prix (1, 1000…) si précisé"},
                "montant_ht": {"type": "number"}, "laize_mm": {"type": "number"},
                "lot": {"type": "string"}}}},
            "total_ht": {"type": "number"}, "total_ttc": {"type": "number"},
            "devise": {"type": "string"},
            "commentaire": {"type": "string", "description": "ce qui est illisible ou douteux"},
        },
        "required": ["nature", "lignes"],
    },
}


def lecteur_claude(contenu: bytes, mime: str) -> tuple[dict, str]:
    """Appel réel au modèle. Rend (extraction, modèle). Lève ErreurPiece."""
    cle = os.getenv("ANTHROPIC_API_KEY", "")
    if not cle:
        raise ErreurPiece("Lecture IA indisponible : clé ANTHROPIC_API_KEY absente du serveur.")
    import anthropic
    bloc = ({"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                            "data": base64.standard_b64encode(contenu).decode()}}
            if mime == "application/pdf" else
            {"type": "image", "source": {"type": "base64", "media_type": mime,
                                         "data": base64.standard_b64encode(contenu).decode()}})
    try:
        r = anthropic.Anthropic(api_key=cle).messages.create(
            model=ERP2_DOC_IA_MODELE, max_tokens=8000, system=_CONSIGNE, tools=[_OUTIL],
            tool_choice={"type": "tool", "name": "document_fournisseur"},
            messages=[{"role": "user", "content": [bloc, {"type": "text", "text": "Lis ce document."}]}])
    except Exception as e:
        raise ErreurPiece(f"Lecture IA en échec : {e}") from None
    for b in r.content:
        if getattr(b, "type", "") == "tool_use":
            return (b.input if isinstance(b.input, dict) else json.loads(b.input)), ERP2_DOC_IA_MODELE
    raise ErreurPiece("Le modèle n'a rien rendu.")


def analyser(conn, doc_id: int, lecteur=None) -> dict:
    d = _doc(conn, doc_id)
    p, _nom, mime = fichier(conn, doc_id)
    with open(p, "rb") as f:
        contenu = f.read()
    try:
        ex, modele = (lecteur or lecteur_claude)(contenu, mime)
    except ErreurPiece as e:
        conn.execute("UPDATE gc_documents SET statut='erreur', erreur=? WHERE id=?", (str(e), doc_id))
        raise
    tiers = _trouver_tiers(conn, ex) or d["tiers_id"]
    conn.execute(
        """UPDATE gc_documents SET extraction=?, nature=?, tiers_id=?, statut='analyse', erreur=NULL, modele=?, analyse_le=?
           WHERE id=?""",
        (json.dumps(ex, ensure_ascii=False), ex.get("nature") or "autre", tiers, modele, _maintenant(), doc_id))
    return detail(conn, doc_id)


# ── Rapprochement ──────────────────────────────────────────────────────

def _norm(s) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(s or "").upper())


def _mots(s) -> set[str]:
    return {m for m in re.findall(r"[a-z0-9]+", str(s or "").lower()) if len(m) > 2}


def _trouver_tiers(conn, ex: dict) -> int | None:
    f = ex.get("fournisseur") or {}
    for col, v in (("siret", f.get("siret")), ("tva_intra", f.get("tva"))):
        if _norm(v):
            for r in conn.execute(f"SELECT id, {col} AS v FROM gc_tiers WHERE est_fournisseur=1 AND {col} IS NOT NULL").fetchall():
                if _norm(r["v"]) and (_norm(r["v"]) in _norm(v) or _norm(v) in _norm(r["v"])):
                    return int(r["id"])
    nom = _mots(f.get("nom"))
    meilleur, score = None, 0.0
    if nom:
        for r in conn.execute("SELECT id, raison_sociale, nom_court FROM gc_tiers WHERE est_fournisseur=1").fetchall():
            m = _mots(r["raison_sociale"]) | _mots(r["nom_court"])
            s = len(nom & m) / max(1, len(nom | m))
            if s > score:
                meilleur, score = int(r["id"]), s
    return meilleur if score >= 0.34 else None


def _commandes(conn, tiers_id: int | None, ex: dict) -> list[dict]:
    """Commandes fournisseur candidates : celle dont le numéro est cité, sinon
    les commandes ouvertes du fournisseur."""
    ref = _norm(ex.get("ref_commande"))
    out = []
    if ref:
        for r in conn.execute("SELECT id, numero, tiers_id, statut FROM gc_pieces WHERE type='cde_fournisseur' AND numero IS NOT NULL").fetchall():
            if _norm(r["numero"]) == ref or (len(ref) >= 4 and ref.endswith(_norm(r["numero"])) and len(_norm(r["numero"])) >= 4):
                out.append(dict(r))
    if not out and tiers_id:
        out = [dict(r) for r in conn.execute(
            """SELECT id, numero, tiers_id, statut FROM gc_pieces WHERE type='cde_fournisseur' AND tiers_id=?
               AND statut IN ('valide','partiel') ORDER BY date_piece DESC, id DESC""", (tiers_id,)).fetchall()]
    return out


def _lignes_commande(conn, cde_id: int, tiers_id: int) -> list[dict]:
    out = []
    for l in conn.execute(
        """SELECT l.*, a.code, a.libelle AS article_libelle, a.designation AS article_designation, a.unite AS article_unite
           FROM gc_pieces_lignes l JOIN gc_articles a ON a.id=l.article_id WHERE l.piece_id=? ORDER BY l.rang""",
            (cde_id,)).fetchall():
        d = dict(l)
        recu = pieces.qte_aval(conn, l["id"], ["reception"])
        d["reste_milli"] = 0 if l["solde"] else max(0, int(l["quantite_milli"]) - recu)
        d["refs"] = {_norm(l["code"]), _norm(l["ref_client"])} | {
            _norm(r["ref_fournisseur"]) for r in conn.execute(
                "SELECT ref_fournisseur FROM gc_tarifs WHERE article_id=? AND (tiers_id=? OR tiers_id IS NULL)",
                (l["article_id"], tiers_id)).fetchall()}
        d["refs"].discard("")
        d["mots"] = _mots(l["libelle"]) | _mots(l["article_libelle"]) | _mots(l["article_designation"])
        out.append(d)
    return out


def _unite(u) -> str:
    u = _norm(str(u or "").replace("²", "2"))
    return {"M2": "M2", "MC": "M2", "METRECARRE": "M2", "ML": "ML", "M": "ML", "METRE": "ML", "METRES": "ML",
            "KG": "KG", "ETQ": "ETQ", "ETIQUETTES": "ETQ", "U": "U", "UNITE": "U", "PCE": "U", "PIECES": "U"}.get(u, u)


def _apparier(lignes_doc: list[dict], lignes_cde: list[dict]) -> list[int | None]:
    """Index de la ligne de commande pour chaque ligne du document."""
    pris, out = set(), []
    for x in lignes_doc:
        ref = _norm(x.get("reference"))
        choix = None
        if ref:
            choix = next((i for i, c in enumerate(lignes_cde) if i not in pris and any(r and (r == ref or r in ref or ref in r) for r in c["refs"] if len(r) >= 3)), None)
        if choix is None:
            mots = _mots(x.get("designation")) | _mots(x.get("reference"))
            best, score = None, 0.0
            for i, c in enumerate(lignes_cde):
                if i in pris:
                    continue
                s = len(mots & c["mots"]) / max(1, len(mots | c["mots"]))
                if c.get("laize_dmm") and x.get("laize_mm") and abs(c["laize_dmm"] - round(float(x["laize_mm"]) * 10)) < 5:
                    s += 0.3
                if s > score:
                    best, score = i, s
            choix = best if score >= 0.2 else None
        out.append(choix)
        if choix is not None:
            pris.add(choix)
    # Même nombre de lignes et rien de reconnu : l'ordre du document.
    if all(c is None for c in out) and len(lignes_doc) == len(lignes_cde):
        out = list(range(len(lignes_doc)))
    return out


def rapprocher(conn, doc_id: int, commande_id: int | None = None) -> dict:
    d = _doc(conn, doc_id)
    ex = json.loads(d["extraction"] or "{}")
    if not ex:
        return {"commande": None, "candidates": [], "lignes": [], "alertes": ["Document pas encore lu."]}
    cands = _commandes(conn, d["tiers_id"], ex)
    cde = None
    if commande_id:
        cde = conn.execute("SELECT id, numero, tiers_id, statut FROM gc_pieces WHERE id=? AND type='cde_fournisseur'",
                           (commande_id,)).fetchone()
        cde = dict(cde) if cde else None
    lignes_doc = ex.get("lignes") or []
    best = None
    if cde is None and cands:
        # La commande qui reconnaît le plus de lignes du document.
        for c in cands:
            n = sum(1 for i in _apparier(lignes_doc, _lignes_commande(conn, c["id"], c["tiers_id"])) if i is not None)
            if best is None or n > best[0]:
                best = (n, c)
        cde = best[1]
    alertes, lignes = [], []
    if d["tiers_id"] is None:
        alertes.append("Fournisseur non reconnu : le choisir.")
    if cde is None:
        alertes.append("Aucune commande fournisseur ouverte ne correspond.")
    lc = _lignes_commande(conn, cde["id"], cde["tiers_id"]) if cde else []
    app = _apparier(lignes_doc, lc) if cde else [None] * len(lignes_doc)
    for k, (x, i) in enumerate(zip(lignes_doc, app), start=1):
        c = lc[i] if i is not None else None
        q_doc = x.get("quantite")
        ligne = {"rang_document": k, "reference": x.get("reference"), "designation": x.get("designation"),
                 "quantite_doc": q_doc, "unite_doc": x.get("unite"), "prix_doc": x.get("prix_unitaire"),
                 "base_prix_doc": x.get("base_prix"), "montant_doc": x.get("montant_ht"), "lot": x.get("lot"),
                 "ligne_commande_id": c["id"] if c else None, "article_id": c["article_id"] if c else None,
                 "article_code": c["code"] if c else None, "unite": c["unite"] if c else None,
                 "reste_commande_milli": c["reste_milli"] if c else None,
                 "prix_commande_cents": c["prix_cents"] if c else None, "base_prix": c["base_prix"] if c else None,
                 "ecarts": []}
        if c is None:
            ligne["ecarts"].append("ligne absente de la commande")
        else:
            if x.get("unite") and _unite(x["unite"]) != _unite(c["unite"]):
                ligne["ecarts"].append(f"unité {x['unite']} sur le document, {c['unite']} à la commande")
            if q_doc is not None:
                qm = int(round(float(q_doc) * 1000))
                if qm > c["reste_milli"]:
                    ligne["ecarts"].append("quantité au-delà du reste à recevoir")
            if x.get("prix_unitaire") is not None and c["prix_cents"] is not None:
                base_doc = int(x.get("base_prix") or c["base_prix"] or 1)
                prix_doc_c = calculs.div_arrondi(int(round(float(x["prix_unitaire"]) * 100)) * int(c["base_prix"] or 1), base_doc)
                ligne["prix_doc_cents"] = prix_doc_c
                if prix_doc_c != c["prix_cents"]:
                    ligne["ecarts"].append("prix différent de la commande")
        lignes.append(ligne)
    return {"commande": cde, "candidates": cands, "lignes": lignes, "alertes": alertes}


def detail(conn, doc_id: int, commande_id: int | None = None) -> dict:
    d = dict(_doc(conn, doc_id))
    d["extraction"] = json.loads(d["extraction"] or "{}") or None
    d.pop("chemin", None)
    t = conn.execute("SELECT id, code, raison_sociale FROM gc_tiers WHERE id=?", (d["tiers_id"],)).fetchone() if d["tiers_id"] else None
    d["tiers"] = dict(t) if t else None
    d["rapprochement"] = rapprocher(conn, doc_id, commande_id) if d["extraction"] else None
    return d


# ── Préparation des pièces ─────────────────────────────────────────────

def _entete(ex: dict) -> dict:
    ent = {"ref_tiers": str(ex.get("numero") or "")[:60]}
    if re.match(r"^\d{4}-\d{2}-\d{2}$", str(ex.get("date") or "")):
        ent["date_piece"] = ex["date"]
    return ent


def preparer(conn, doc_id: int, cible: str, commande_id: int | None = None, tiers_id: int | None = None,
             user: dict | None = None) -> int:
    """Réception (depuis la commande) ou facture fournisseur (depuis les
    réceptions de la commande), en brouillon, aux quantités / prix du document."""
    if cible not in ("reception", "facture_fournisseur"):
        raise ErreurPiece("Pièce à préparer : réception ou facture fournisseur.")
    if tiers_id:
        conn.execute("UPDATE gc_documents SET tiers_id=? WHERE id=?", (int(tiers_id), doc_id))
    D = detail(conn, doc_id, commande_id)
    R, ex = D["rapprochement"], D["extraction"] or {}
    if not R or not R["commande"]:
        raise ErreurPiece("Aucune commande fournisseur rapprochée : la choisir.")
    cde = R["commande"]
    par_ligne_cde = {l["ligne_commande_id"]: l for l in R["lignes"] if l["ligne_commande_id"]}
    if not par_ligne_cde:
        raise ErreurPiece("Aucune ligne du document ne correspond à la commande.")
    if cible == "reception":
        pid = pieces.transformer(conn, [cde["id"]], "reception", user)
        lignes = []
        for l in pieces.charger(conn, pid)["lignes"]:
            x = par_ligne_cde.get(l.get("ligne_amont_id"))
            if x is None:
                continue     # pas livré sur ce BL
            if x["quantite_doc"] is not None:
                l = dict(l, quantite_milli=int(round(float(x["quantite_doc"]) * 1000)))
            lignes.append(l)
        if not lignes:
            raise ErreurPiece("Aucune ligne à réceptionner.")
        pieces.enregistrer(conn, pid, _entete(ex), lignes)
    else:
        recs = [r["id"] for r in conn.execute(
            """SELECT DISTINCT p.id FROM gc_pieces p JOIN gc_pieces_lignes l ON l.piece_id=p.id
               JOIN gc_pieces_lignes lc ON lc.id=l.ligne_amont_id
               WHERE p.type='reception' AND p.statut IN ('valide','partiel') AND lc.piece_id=?""", (cde["id"],)).fetchall()]
        if not recs:
            raise ErreurPiece("Aucune réception validée à facturer pour cette commande.")
        pid = pieces.transformer(conn, recs, "facture_fournisseur", user)
        lignes = []
        for l in pieces.charger(conn, pid)["lignes"]:
            rec = conn.execute("SELECT ligne_amont_id FROM gc_pieces_lignes WHERE id=?", (l.get("ligne_amont_id"),)).fetchone()
            x = par_ligne_cde.get(rec["ligne_amont_id"] if rec else None)
            if x is None:
                continue     # pas facturé sur ce document
            if x["quantite_doc"] is not None:
                l = dict(l, quantite_milli=int(round(float(x["quantite_doc"]) * 1000)))
            if x.get("prix_doc_cents") is not None:
                l = dict(l, prix_cents=x["prix_doc_cents"])
            lignes.append(l)
        if not lignes:
            raise ErreurPiece("Aucune ligne de ce document ne se rapporte à une réception à facturer.")
        pieces.enregistrer(conn, pid, _entete(ex), lignes)
    conn.execute("UPDATE gc_documents SET piece_id=?, statut='traite' WHERE id=?", (pid, doc_id))
    return pid

"""Fichiers de base de l'ERP : référentiels, société, tiers, articles, tarifs.

Une adresse ou un contact retiré d'une fiche n'est pas supprimé mais
désactivé : une pièce peut y faire référence.
"""
from __future__ import annotations

from datetime import datetime

from app.services.gc.pieces import ErreurPiece as ErreurFichier  # même nature de refus

# Référentiels éditables dans Paramètres. `champs` : nom -> type (str, int, bool).
REFERENTIELS = {
    "tva": {"table": "gc_tva", "libelle": "Taux de TVA",
            "champs": {"libelle": str, "taux_bp": int, "mention": str, "compte_collecte": str,
                       "compte_deductible": str, "actif": bool, "rang": int}},
    "unites": {"table": "gc_unites", "libelle": "Unités",
               "champs": {"libelle": str, "decimales": int, "actif": bool, "rang": int}},
    "conditions_paiement": {"table": "gc_conditions_paiement", "libelle": "Conditions de paiement",
                            "champs": {"libelle": str, "jours": int, "fin_de_mois": bool, "jour_du_mois": int,
                                       "actif": bool, "rang": int}},
    "modes_paiement": {"table": "gc_modes_paiement", "libelle": "Modes de paiement",
                       "champs": {"libelle": str, "actif": bool, "rang": int}},
    "depots": {"table": "gc_depots", "libelle": "Dépôts",
               "champs": {"libelle": str, "actif": bool, "rang": int}},
    "familles": {"table": "gc_familles", "libelle": "Familles d'articles",
                 "champs": {"libelle": str, "nature": str, "compte_vente": str, "compte_achat": str,
                            "actif": bool, "rang": int}},
    "sequences": {"table": "gc_sequences", "libelle": "Numérotation",
                  "champs": {"libelle": str, "format": str, "prochain": int, "annuel": bool}},
}

CHAMPS_SOCIETE = ("raison_sociale", "forme_juridique", "capital_cents", "siret", "rcs", "tva_intra", "ape",
                  "adresse1", "adresse2", "code_postal", "ville", "pays", "telephone", "email", "iban", "bic",
                  "penalites_retard")

CHAMPS_TIERS = {"code": str, "est_client": bool, "est_fournisseur": bool, "raison_sociale": str, "siret": str,
                "tva_intra": str, "email": str, "email_facturation": str, "telephone": str,
                "condition_paiement": "ref", "mode_paiement": "ref", "tva_code": "ref", "remise_bp": int,
                "encours_max_cents": "int_null", "bloque": bool, "notes": str, "actif": bool,
                "compte_auxiliaire": str}

CHAMPS_ADRESSE = ("type", "libelle", "adresse1", "adresse2", "code_postal", "ville", "pays", "par_defaut")
CHAMPS_CONTACT = ("nom", "fonction", "email", "telephone")

CHAMPS_ARTICLE = {"code": str, "libelle": str, "libelle_client": str, "nature": str, "famille": "ref",
                  "unite": str, "base_prix": int, "prix_vente_cents": "int_null", "prix_achat_cents": "int_null",
                  "tva_code": "ref", "gere_stock": bool, "fournisseur_id": "int_null", "client_id": "int_null",
                  "notes": str, "actif": bool}

NATURES = {"pf": "Produit fini", "mp": "Matière première", "service": "Prestation"}


def _maintenant() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _conv(v, t, nom):
    if t is bool:
        return 1 if v in (True, 1, "1", "true", "on") else 0
    if t is int:
        try:
            return int(v or 0)
        except (TypeError, ValueError):
            raise ErreurFichier(f"{nom} : nombre entier attendu.") from None
    if t == "int_null":
        if v in (None, ""):
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            raise ErreurFichier(f"{nom} : nombre entier attendu.") from None
    if t == "ref":
        return v or None
    return str(v if v is not None else "").strip()


# ── Référentiels ──────────────────────────────────────────────────────

def lister_referentiel(conn, nom: str) -> list[dict]:
    r = REFERENTIELS.get(nom)
    if not r:
        raise ErreurFichier("Référentiel inconnu.")
    ordre = "code" if nom == "sequences" else "rang, code"
    return [dict(x) for x in conn.execute(f"SELECT * FROM {r['table']} ORDER BY {ordre}").fetchall()]


def enregistrer_referentiel(conn, nom: str, ligne: dict) -> None:
    r = REFERENTIELS.get(nom)
    if not r:
        raise ErreurFichier("Référentiel inconnu.")
    code = str(ligne.get("code") or "").strip()
    if not code:
        raise ErreurFichier("Code obligatoire.")
    vals = {c: _conv(ligne.get(c), t, c) for c, t in r["champs"].items() if c in ligne}
    if "libelle" in r["champs"] and not vals.get("libelle", "x"):
        raise ErreurFichier("Libellé obligatoire.")
    if nom == "sequences":
        if not conn.execute("SELECT 1 FROM gc_sequences WHERE code=?", (code,)).fetchone():
            raise ErreurFichier("Une séquence ne se crée pas : elle correspond à un type de pièce.")
        if "prochain" in vals and vals["prochain"] < 1:
            raise ErreurFichier("Prochain numéro : 1 au minimum.")
        if "format" in vals and "{N" not in vals["format"]:
            raise ErreurFichier("Le format doit contenir le compteur {N} (ex. FA{AA}{N:05}).")
    if nom == "familles" and vals.get("nature", "pf") not in NATURES:
        raise ErreurFichier("Nature invalide.")
    existe = conn.execute(f"SELECT 1 FROM {r['table']} WHERE code=?", (code,)).fetchone()
    if existe:
        if vals:
            conn.execute(f"UPDATE {r['table']} SET {', '.join(c + '=?' for c in vals)} WHERE code=?",
                         (*vals.values(), code))
    else:
        cols = ["code", *vals]
        conn.execute(f"INSERT INTO {r['table']} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                     (code, *vals.values()))


def lire_societe(conn) -> dict:
    r = conn.execute("SELECT * FROM gc_societe WHERE id=1").fetchone()
    return dict(r) if r else {}


def enregistrer_societe(conn, data: dict) -> None:
    vals = {}
    for c in CHAMPS_SOCIETE:
        if c in data:
            vals[c] = _conv(data[c], "int_null" if c == "capital_cents" else str, c)
    if vals:
        conn.execute(f"UPDATE gc_societe SET {', '.join(c + '=?' for c in vals)}, modifie_le=? WHERE id=1",
                     (*vals.values(), _maintenant()))


# ── Tiers ─────────────────────────────────────────────────────────────

def lister_tiers(conn, role: str | None = None) -> list[dict]:
    filtre = {"client": "WHERE t.est_client=1", "fournisseur": "WHERE t.est_fournisseur=1"}.get(role or "", "")
    return [dict(r) for r in conn.execute(
        f"""SELECT t.id, t.code, t.raison_sociale, t.est_client, t.est_fournisseur, t.email, t.telephone,
                   t.condition_paiement, t.bloque, t.actif,
                   (SELECT ville FROM gc_tiers_adresses a WHERE a.tiers_id=t.id AND a.actif=1
                     ORDER BY a.type='facturation' DESC, a.par_defaut DESC, a.id LIMIT 1) AS ville,
                   (SELECT COALESCE(SUM(e.montant_cents - e.regle_cents),0) FROM gc_echeances e
                     JOIN gc_pieces p ON p.id=e.piece_id WHERE p.tiers_id=t.id AND p.type='facture') AS encours_cents
            FROM gc_tiers t {filtre} ORDER BY t.raison_sociale""").fetchall()]


def charger_tiers(conn, tiers_id: int) -> dict:
    t = conn.execute("SELECT * FROM gc_tiers WHERE id=?", (tiers_id,)).fetchone()
    if not t:
        raise ErreurFichier("Tiers introuvable.")
    d = dict(t)
    d["adresses"] = [dict(r) for r in conn.execute(
        "SELECT * FROM gc_tiers_adresses WHERE tiers_id=? AND actif=1 ORDER BY type, par_defaut DESC, id",
        (tiers_id,)).fetchall()]
    d["contacts"] = [dict(r) for r in conn.execute(
        "SELECT * FROM gc_tiers_contacts WHERE tiers_id=? AND actif=1 ORDER BY id", (tiers_id,)).fetchall()]
    d["tarifs"] = [dict(r) for r in conn.execute(
        """SELECT g.*, a.code AS article_code, a.libelle AS article_libelle, a.base_prix, a.unite
           FROM gc_tarifs g JOIN gc_articles a ON a.id=g.article_id
           WHERE g.tiers_id=? AND g.actif=1 ORDER BY a.code, g.qte_min_milli""", (tiers_id,)).fetchall()]
    d["pieces"] = [dict(r) for r in conn.execute(
        """SELECT id, type, numero, statut, date_piece, total_ht_cents FROM gc_pieces
           WHERE tiers_id=? ORDER BY date_piece DESC, id DESC LIMIT 200""", (tiers_id,)).fetchall()]
    return d


def _code_suivant(conn, table: str, prefixe: str) -> str:
    n = 0
    for (c,) in conn.execute(f"SELECT code FROM {table} WHERE code LIKE ?", (prefixe + "%",)).fetchall():
        reste = c[len(prefixe):]
        if reste.isdigit():
            n = max(n, int(reste))
    return f"{prefixe}{n + 1:04d}"


def enregistrer_tiers(conn, tiers_id: int | None, data: dict, adresses: list | None = None,
                      contacts: list | None = None, origine: str = "erp") -> int:
    vals = {c: _conv(data.get(c), t, c) for c, t in CHAMPS_TIERS.items() if c in data}
    now = _maintenant()
    if tiers_id is None:
        if not vals.get("raison_sociale"):
            raise ErreurFichier("Raison sociale obligatoire.")
        if not vals.get("est_client") and not vals.get("est_fournisseur"):
            raise ErreurFichier("Cocher client, fournisseur, ou les deux.")
        if not vals.get("code"):
            vals["code"] = _code_suivant(conn, "gc_tiers", "C" if vals.get("est_client") else "F")
        if conn.execute("SELECT 1 FROM gc_tiers WHERE code=?", (vals["code"],)).fetchone():
            raise ErreurFichier(f"Le code {vals['code']} est déjà pris.")
        cols = [*vals, "origine", "cree_le", "modifie_le"]
        cur = conn.execute(f"INSERT INTO gc_tiers ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                           (*vals.values(), origine, now, now))
        tiers_id = int(cur.lastrowid)
    else:
        if not conn.execute("SELECT 1 FROM gc_tiers WHERE id=?", (tiers_id,)).fetchone():
            raise ErreurFichier("Tiers introuvable.")
        if "raison_sociale" in vals and not vals["raison_sociale"]:
            raise ErreurFichier("Raison sociale obligatoire.")
        if "code" in vals:
            if not vals["code"]:
                raise ErreurFichier("Code obligatoire.")
            if conn.execute("SELECT 1 FROM gc_tiers WHERE code=? AND id!=?", (vals["code"], tiers_id)).fetchone():
                raise ErreurFichier(f"Le code {vals['code']} est déjà pris.")
        if vals:
            conn.execute(f"UPDATE gc_tiers SET {', '.join(c + '=?' for c in vals)}, modifie_le=? WHERE id=?",
                         (*vals.values(), now, tiers_id))
    if adresses is not None:
        _synchroniser(conn, "gc_tiers_adresses", tiers_id, adresses, CHAMPS_ADRESSE,
                      obligatoire="adresse1", libelle="Adresse")
    if contacts is not None:
        _synchroniser(conn, "gc_tiers_contacts", tiers_id, contacts, CHAMPS_CONTACT,
                      obligatoire="nom", libelle="Contact")
    return tiers_id


def _synchroniser(conn, table, tiers_id, lignes, champs, obligatoire, libelle):
    """Met à jour les lignes connues, crée les nouvelles, désactive les absentes."""
    gardes = set()
    for l in lignes:
        vals = {c: (_conv(l.get(c), bool, c) if c == "par_defaut" else _conv(l.get(c), str, c))
                for c in champs if c in l}
        if not vals.get(obligatoire):
            continue
        if table == "gc_tiers_adresses" and vals.get("type") not in ("facturation", "livraison"):
            raise ErreurFichier("Type d'adresse : facturation ou livraison.")
        lid = l.get("id")
        if lid and conn.execute(f"SELECT 1 FROM {table} WHERE id=? AND tiers_id=?", (lid, tiers_id)).fetchone():
            conn.execute(f"UPDATE {table} SET {', '.join(c + '=?' for c in vals)}, actif=1 WHERE id=?",
                         (*vals.values(), lid))
            gardes.add(int(lid))
        else:
            cols = ["tiers_id", *vals]
            cur = conn.execute(f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                               (tiers_id, *vals.values()))
            gardes.add(int(cur.lastrowid))
    for (i,) in conn.execute(f"SELECT id FROM {table} WHERE tiers_id=? AND actif=1", (tiers_id,)).fetchall():
        if i not in gardes:
            conn.execute(f"UPDATE {table} SET actif=0 WHERE id=?", (i,))


# ── Articles ──────────────────────────────────────────────────────────

def stock_article(conn, article_id: int) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT depot, SUM(quantite_milli) AS quantite_milli FROM gc_mouvements
           WHERE article_id=? GROUP BY depot ORDER BY depot""", (article_id,)).fetchall()]


def lister_articles(conn, nature: str | None = None) -> list[dict]:
    filtre, args = ("WHERE a.nature=?", (nature,)) if nature else ("", ())
    return [dict(r) for r in conn.execute(
        f"""SELECT a.id, a.code, a.libelle, a.nature, a.famille, a.unite, a.base_prix,
                   a.prix_vente_cents, a.prix_achat_cents, a.gere_stock, a.actif,
                   (SELECT COALESCE(SUM(m.quantite_milli),0) FROM gc_mouvements m WHERE m.article_id=a.id) AS stock_milli
            FROM gc_articles a {filtre} ORDER BY a.code""", args).fetchall()]


def charger_article(conn, article_id: int) -> dict:
    a = conn.execute("SELECT * FROM gc_articles WHERE id=?", (article_id,)).fetchone()
    if not a:
        raise ErreurFichier("Article introuvable.")
    d = dict(a)
    d["tarifs"] = [dict(r) for r in conn.execute(
        """SELECT g.*, t.code AS tiers_code, t.raison_sociale AS tiers_nom FROM gc_tarifs g
           LEFT JOIN gc_tiers t ON t.id=g.tiers_id WHERE g.article_id=? AND g.actif=1
           ORDER BY g.sens DESC, t.raison_sociale, g.qte_min_milli""", (article_id,)).fetchall()]
    d["stock"] = stock_article(conn, article_id)
    d["mouvements"] = [dict(r) for r in conn.execute(
        """SELECT m.*, p.numero, p.type AS piece_type FROM gc_mouvements m LEFT JOIN gc_pieces p ON p.id=m.piece_id
           WHERE m.article_id=? ORDER BY m.date_mvt DESC, m.id DESC LIMIT 100""", (article_id,)).fetchall()]
    return d


def enregistrer_article(conn, article_id: int | None, data: dict, tarifs: list | None = None,
                        origine: str = "erp") -> int:
    vals = {c: _conv(data.get(c), t, c) for c, t in CHAMPS_ARTICLE.items() if c in data}
    if "nature" in vals and vals["nature"] not in NATURES:
        raise ErreurFichier("Nature invalide : produit fini, matière ou prestation.")
    if "unite" in vals and not conn.execute("SELECT 1 FROM gc_unites WHERE code=?", (vals["unite"],)).fetchone():
        raise ErreurFichier("Unité inconnue.")
    if "base_prix" in vals and vals["base_prix"] < 1:
        raise ErreurFichier("Base de prix : 1 au minimum.")
    now = _maintenant()
    if article_id is None:
        for c in ("libelle", "nature", "unite"):
            if not vals.get(c):
                raise ErreurFichier(f"{c.capitalize()} obligatoire.")
        if not vals.get("code"):
            vals["code"] = _code_suivant(conn, "gc_articles", {"pf": "PF", "mp": "MP", "service": "PR"}[vals["nature"]])
        if conn.execute("SELECT 1 FROM gc_articles WHERE code=?", (vals["code"],)).fetchone():
            raise ErreurFichier(f"Le code {vals['code']} est déjà pris.")
        cols = [*vals, "origine", "cree_le", "modifie_le"]
        cur = conn.execute(f"INSERT INTO gc_articles ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                           (*vals.values(), origine, now, now))
        article_id = int(cur.lastrowid)
    else:
        if not conn.execute("SELECT 1 FROM gc_articles WHERE id=?", (article_id,)).fetchone():
            raise ErreurFichier("Article introuvable.")
        if "code" in vals and conn.execute("SELECT 1 FROM gc_articles WHERE code=? AND id!=?",
                                           (vals["code"], article_id)).fetchone():
            raise ErreurFichier(f"Le code {vals['code']} est déjà pris.")
        if "libelle" in vals and not vals["libelle"]:
            raise ErreurFichier("Libellé obligatoire.")
        if vals:
            conn.execute(f"UPDATE gc_articles SET {', '.join(c + '=?' for c in vals)}, modifie_le=? WHERE id=?",
                         (*vals.values(), now, article_id))
    if tarifs is not None:
        conn.execute("DELETE FROM gc_tarifs WHERE article_id=?", (article_id,))
        for t in tarifs:
            if t.get("prix_cents") in (None, ""):
                continue
            sens = t.get("sens") or "vente"
            if sens not in ("vente", "achat"):
                raise ErreurFichier("Tarif : sens vente ou achat.")
            conn.execute(
                """INSERT INTO gc_tarifs (article_id, tiers_id, sens, qte_min_milli, prix_cents, debut, fin)
                   VALUES (?,?,?,?,?,?,?)""",
                (article_id, _conv(t.get("tiers_id"), "int_null", "Tiers"), sens,
                 _conv(t.get("qte_min_milli"), int, "Palier"), _conv(t.get("prix_cents"), int, "Prix"),
                 t.get("debut") or None, t.get("fin") or None))
    return article_id


def stock(conn) -> list[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT a.id, a.code, a.libelle, a.nature, a.unite, m.depot,
                  SUM(m.quantite_milli) AS quantite_milli, MAX(m.date_mvt) AS dernier_mvt
           FROM gc_mouvements m JOIN gc_articles a ON a.id=m.article_id
           GROUP BY a.id, m.depot ORDER BY a.code, m.depot""").fetchall()]


def mouvements(conn, article_id: int | None = None) -> list[dict]:
    filtre, args = ("WHERE m.article_id=?", (article_id,)) if article_id else ("", ())
    return [dict(r) for r in conn.execute(
        f"""SELECT m.id, m.date_mvt, m.depot, m.quantite_milli, m.type, m.lot, m.commentaire, m.piece_id,
                   a.id AS article_id, a.code AS article_code, a.libelle AS article_libelle, a.unite,
                   p.numero AS piece_numero, p.type AS piece_type
            FROM gc_mouvements m JOIN gc_articles a ON a.id=m.article_id
            LEFT JOIN gc_pieces p ON p.id=m.piece_id {filtre}
            ORDER BY m.date_mvt DESC, m.id DESC LIMIT 5000""", args).fetchall()]


def mouvement_manuel(conn, data: dict, user: dict | None = None) -> int:
    """Inventaire, ajustement ou transfert : les seules écritures de stock hors pièce.
    Un transfert écrit deux mouvements (sortie du dépôt, entrée dans l'autre)."""
    typ = data.get("type") or "ajustement"
    if typ not in ("inventaire", "ajustement", "transfert"):
        raise ErreurFichier("Type de mouvement manuel : inventaire, ajustement ou transfert.")
    art = conn.execute("SELECT id, gere_stock FROM gc_articles WHERE id=?",
                       (_conv(data.get("article_id"), int, "Article"),)).fetchone()
    if not art or not art["gere_stock"]:
        raise ErreurFichier("Article introuvable ou non géré en stock.")
    depot = data.get("depot")
    if not conn.execute("SELECT 1 FROM gc_depots WHERE code=?", (depot,)).fetchone():
        raise ErreurFichier("Dépôt inconnu.")
    q = _conv(data.get("quantite_milli"), int, "Quantité")
    if typ == "transfert":
        dest = data.get("depot_destination")
        if not conn.execute("SELECT 1 FROM gc_depots WHERE code=?", (dest,)).fetchone():
            raise ErreurFichier("Dépôt de destination inconnu.")
        if dest == depot:
            raise ErreurFichier("Dépôts de départ et d'arrivée identiques.")
        if q <= 0:
            raise ErreurFichier("Quantité à transférer : supérieure à zéro.")
        now = _maintenant()
        jour = data.get("date_mvt") or now[:10]
        lot = str(data.get("lot") or "")
        com = str(data.get("commentaire") or "") or f"Transfert {depot} → {dest}"
        nom = str((user or {}).get("nom") or "")
        cur = conn.execute(
            """INSERT INTO gc_mouvements (date_mvt, article_id, depot, quantite_milli, type, lot, commentaire, cree_par, cree_le)
               VALUES (?,?,?,?,?,?,?,?,?)""", (jour, art["id"], depot, -q, "transfert", lot, com, nom, now))
        conn.execute(
            """INSERT INTO gc_mouvements (date_mvt, article_id, depot, quantite_milli, type, lot, commentaire, cree_par, cree_le)
               VALUES (?,?,?,?,?,?,?,?,?)""", (jour, art["id"], dest, q, "transfert", lot, com, nom, now))
        return int(cur.lastrowid)
    if typ == "inventaire":
        # Quantité comptée : le mouvement est l'écart avec le stock théorique.
        th = conn.execute("SELECT COALESCE(SUM(quantite_milli),0) q FROM gc_mouvements WHERE article_id=? AND depot=?",
                          (art["id"], depot)).fetchone()["q"]
        q = q - int(th)
    if q == 0:
        raise ErreurFichier("Aucun écart : rien à enregistrer.")
    now = _maintenant()
    cur = conn.execute(
        """INSERT INTO gc_mouvements (date_mvt, article_id, depot, quantite_milli, type, lot, commentaire, cree_par, cree_le)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (data.get("date_mvt") or now[:10], art["id"], depot, q, typ, str(data.get("lot") or ""),
         str(data.get("commentaire") or ""), str((user or {}).get("nom") or ""), now))
    return int(cur.lastrowid)

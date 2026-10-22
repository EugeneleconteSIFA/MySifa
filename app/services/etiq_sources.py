"""
Étiquettes spécifiques — données MySifa liées aux champs variables.

Une variable de type « source » nomme un champ : « dossier.reference »,
« client.ville », « lot.lot_fournisseur »… À l'impression, l'opérateur choisit
un enregistrement (un dossier, un lot…) et toutes les variables liées se
remplissent. Choisir un dossier remplit aussi son OF, son produit (fiche
technique) et son client.

Lecture seule, sur les tables réelles :
  dossier   planning_entries (Dossiers au planning)
  of        of_imports (OF importés ou créés dans MySifa)
  produit   fiches_techniques, choisie par fiche_choix.choisir_fiche
  client    clients
  matiere   matieres_premieres (référentiel MyStock)
  lot       stock_bobines (bobines matière, lot fournisseur, réception)
  article   produits_finis (base d'articles) + sa fiche technique
  article_erp  articles vendus de RVGI (fic_art du miroir, lecture seule),
            servis par /articles/erp : jamais lus ici en base MySifa

Les colonnes absentes d'une base (ancienne instance) donnent une valeur vide,
jamais une erreur.
"""

from __future__ import annotations

from typing import Optional
from urllib.parse import quote

TYPES = {
    "dossier": "Dossier",
    "of": "OF",
    "produit": "Produit (fiche technique)",
    "client": "Client",
    "matiere": "Matière",
    "lot": "Lot / bobine",
    "article": "Article (produit fini)",
}
# Champs des articles RVGI : remplis depuis le miroir (route /articles/erp).
CHAMPS_ERP = [
    ("reference", "Référence article RVGI"), ("libelle", "Libellé"), ("matiere", "Matière, mandrin, enroulement"),
    ("conditionnement", "Conditionnement"), ("carton", "Carton"), ("ref_client", "Référence client"),
    ("format", "Format"), ("poids", "Poids net"),
]

# type → [(champ, libellé, colonne SQL)]
CHAMPS = {
    "dossier": [
        ("reference", "Référence dossier", "pe.reference"),
        ("client", "Client", "pe.client"),
        ("description", "Désignation", "pe.description"),
        ("ref_produit", "Référence produit", "pe.ref_produit"),
        ("numero_of", "N° d'OF", "pe.numero_of"),
        ("commande", "Commande RVGI", "pe.dos_rvgi"),
        ("laize", "Laize (mm)", "pe.laize"),
        ("format_l", "Format largeur (mm)", "pe.format_l"),
        ("format_h", "Format hauteur (mm)", "pe.format_h"),
        ("date_livraison", "Date de livraison", "pe.date_livraison"),
        ("etiquettes_par_carton", "Étiquettes par carton", "pe.etiquettes_par_carton"),
        ("machine", "Machine", "m.nom"),
    ],
    "of": [
        ("numero", "N° d'OF", "o.of_numero"),
        ("reference", "Référence", "o.reference"),
        ("machine", "Machine", "o.machine"),
        ("qte_etiquettes", "Quantité d'étiquettes", "o.qte_etiquettes"),
        ("qte_bobines", "Nombre de bobines", "o.qte_bobines"),
        ("metrage", "Métrage", "o.metrage"),
        ("conditionnement", "Conditionnement", "o.conditionnement"),
        ("delai_client", "Délai client", "o.delai_client"),
        ("date_creation", "Date de l'OF", "o.date_creation"),
        ("matiere", "Matière", "o.matiere"),
    ],
    "produit": [
        ("reference", "Référence produit", "ft.reference"),
        ("designation", "Désignation", "ft.designation"),
        ("client", "Client", "ft.client"),
        ("format", "Format", "ft.format"),
        ("laize", "Laize", "ft.laize"),
        ("matiere", "Matière", "ft.matiere"),
        ("adhesif", "Adhésif", "ft.adhesif"),
        ("conditionnement", "Conditionnement", "ft.conditionnement"),
        ("nb_etiq_bobin", "Étiquettes par bobine", "ft.nb_etiq_bobin"),
        ("mandrin_dia", "Diamètre mandrin", "ft.mandrin_dia"),
        ("enroulement", "Enroulement", "ft.enroulement"),
        ("lien_fiche", "Lien vers la fiche (QR)", None),
    ],
    "client": [
        ("code", "Code client", "c.code"),
        ("raison_sociale", "Raison sociale", "c.raison_sociale"),
        ("adresse1", "Adresse", "c.adresse1"),
        ("adresse2", "Complément d'adresse", "c.adresse2"),
        ("cp", "Code postal", "c.cp"),
        ("ville", "Ville", "c.ville"),
        ("pays", "Pays", "c.pays"),
        ("ean", "GLN / EAN", "c.ean"),
        ("telephone", "Téléphone", "c.telephone"),
    ],
    "matiere": [
        ("reference", "Référence matière", "mp.reference"),
        ("designation", "Désignation", "mp.designation"),
        ("categorie", "Catégorie", "mp.categorie"),
    ],
    "lot": [
        ("code_barre", "Code bobine", "b.code_barre"),
        ("lot_fournisseur", "Lot fournisseur", "b.lot_fournisseur"),
        ("lot_reception", "Lot de réception", "sr.lot_numero"),
        ("fournisseur", "Fournisseur", "sr.fournisseur"),
        ("metrage_restant", "Métrage restant", "b.metrage_restant"),
        ("metrage_initial", "Métrage initial", "b.metrage_initial"),
        ("laize_mm", "Laize (mm)", "lz.valeur_mm"),
        ("no_dossier", "Dossier", "b.no_dossier"),
        ("certificat_fsc", "Certificat FSC", "sr.certificat_fsc"),
        ("claim_fsc", "Claim FSC", "sr.fsc_type_claim"),
        ("date_entree", "Date d'entrée", "b.created_at"),
    ],
    "article": [
        ("reference", "Référence article", "pf.reference"),
        ("designation", "Désignation", "pf.designation"),
        ("unite", "Unité", "pf.unite"),
    ],
}

# Ce qu'un enregistrement d'un type remplit en plus de lui-même.
LIES = {"dossier": ("of", "produit", "client"), "of": ("produit",), "lot": ("matiere", "dossier"),
        "article": ("produit",)}

_FROM = {
    "dossier": "planning_entries pe LEFT JOIN machines m ON m.id = pe.machine_id",
    "of": "of_imports o",
    "produit": "fiches_techniques ft",
    "client": "clients c",
    "matiere": "matieres_premieres mp",
    "article": "produits_finis pf",
    "lot": ("stock_bobines b LEFT JOIN matieres_premieres mp ON mp.id = b.matiere_id"
            " LEFT JOIN mp_laizes lz ON lz.id = b.laize_id"
            " LEFT JOIN stock_receptions sr ON sr.id = b.reception_id"),
}
_ID = {"dossier": "pe.id", "of": "o.id", "produit": "ft.id", "client": "c.id", "matiere": "mp.id", "lot": "b.id",
       "article": "pf.id"}
# (libellé de la ligne, détail, colonnes cherchées)
_RECHERCHE = {
    "dossier": ("pe.reference", "pe.client || ' · ' || COALESCE(pe.description,'')",
                ("pe.reference", "pe.client", "pe.description", "pe.numero_of", "pe.ref_produit"), "pe.updated_at DESC"),
    "of": ("o.of_numero", "COALESCE(o.reference,'') || ' · ' || COALESCE(o.machine,'')",
           ("o.of_numero", "o.reference"), "o.id DESC"),
    "produit": ("ft.reference", "COALESCE(ft.designation,'') || ' · ' || COALESCE(ft.client,'')",
                ("ft.reference", "ft.designation", "ft.client"), "ft.id DESC"),
    "client": ("c.raison_sociale", "COALESCE(c.code,'') || ' · ' || COALESCE(c.ville,'')",
               ("c.raison_sociale", "c.code", "c.ville"), "c.raison_sociale COLLATE NOCASE"),
    "matiere": ("mp.reference", "COALESCE(mp.designation,'') || ' · ' || mp.categorie",
                ("mp.reference", "mp.designation"), "mp.reference COLLATE NOCASE"),
    "article": ("pf.reference", "COALESCE(pf.designation,'')", ("pf.reference", "pf.designation"),
                "pf.reference COLLATE NOCASE"),
    "lot": ("b.code_barre", "COALESCE(mp.reference,'') || ' · lot ' || COALESCE(b.lot_fournisseur,'')",
            ("b.code_barre", "b.lot_fournisseur", "b.no_dossier", "mp.reference"), "b.id DESC"),
}


def referentiel() -> dict:
    """Pour l'éditeur : types et champs liables, libellés compris."""
    out = {t: {"libelle": TYPES[t], "champs": [{"cle": f"{t}.{c}", "libelle": l} for c, l, _ in CHAMPS[t]]}
           for t in TYPES}
    out["article_erp"] = {"libelle": "Article RVGI (ERP)", "erp": True,
                          "champs": [{"cle": f"article_erp.{c}", "libelle": l} for c, l in CHAMPS_ERP]}
    return out


def article_erp_champs(r: dict) -> dict:
    """Ligne fic_art du miroir → {id, libelle, detail, champs}."""
    try:
        from app.routers.reconciliation import _erp_reference
        ref = _erp_reference(r.get("code1"), r.get("code2")) or ""
    except Exception:
        ref = f"{r.get('code1') or ''}/{r.get('code2') or ''}"
    fmt = " × ".join(_txt(x) for x in (r.get("ftl"), r.get("fth")) if x not in (None, "", 0))
    champs = {"article_erp.reference": ref, "article_erp.libelle": _txt(r.get("libc1")),
              "article_erp.matiere": _txt(r.get("libc2")), "article_erp.conditionnement": _txt(r.get("libc3")),
              "article_erp.carton": _txt(r.get("libc4")), "article_erp.ref_client": _txt(r.get("cltc2")),
              "article_erp.format": fmt, "article_erp.poids": _txt(r.get("pdsn"))}
    return {"id": ref, "libelle": ref, "detail": champs["article_erp.libelle"], "champs": champs}


def champ_connu(cle: str) -> bool:
    t, _, c = (cle or "").partition(".")
    if t == "article_erp":
        return any(x[0] == c for x in CHAMPS_ERP)
    return t in CHAMPS and any(x[0] == c for x in CHAMPS[t])


def _colonnes(conn, table: str) -> set:
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


_ALIAS_TABLE = {"pe": "planning_entries", "m": "machines", "o": "of_imports", "ft": "fiches_techniques",
                "c": "clients", "mp": "matieres_premieres", "b": "stock_bobines", "lz": "mp_laizes",
                "sr": "stock_receptions", "pf": "produits_finis"}


def _expr(conn, col: Optional[str], cache: dict) -> str:
    """Colonne SQL, ou NULL si elle n'existe pas dans cette base."""
    if not col:
        return "NULL"
    alias, _, nom = col.partition(".")
    table = _ALIAS_TABLE.get(alias)
    if table not in cache:
        cache[table] = _colonnes(conn, table)
    return col if nom in cache[table] else "NULL"


def _txt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def rechercher(conn, type_: str, q: str = "", limit: int = 20, dossier: str = "") -> list[dict]:
    if type_ not in TYPES:
        return []
    cache: dict = {}
    lib, detail, cols, ordre = _RECHERCHE[type_]
    where, params = [], []
    q = (q or "").strip()
    if q:
        exprs = [_expr(conn, c, cache) for c in cols]
        where.append("(" + " OR ".join(f"{e} LIKE ?" for e in exprs if e != "NULL") + ")")
        params += [f"%{q}%"] * sum(1 for e in exprs if e != "NULL")
    if type_ == "lot" and dossier:
        where.append("b.no_dossier = ?")
        params.append(dossier)
    if type_ == "matiere" and "actif" in _colonnes(conn, "matieres_premieres"):
        where.append("COALESCE(mp.actif,1) = 1")
    sql = (f"SELECT {_ID[type_]} AS id, {lib} AS libelle, {detail} AS detail FROM {_FROM[type_]}"
           + (" WHERE " + " AND ".join(where) if where else "") + f" ORDER BY {ordre} LIMIT ?")
    params.append(max(1, min(200, int(limit or 20))))
    try:
        rows = conn.execute(sql, params).fetchall()
    except Exception:
        return []
    return [{"id": r["id"], "libelle": _txt(r["libelle"]), "detail": _txt(r["detail"]).strip(" ·")} for r in rows]


def _ligne(conn, type_: str, where: str, params: tuple, cache: dict) -> Optional[dict]:
    sel = ", ".join(f"{_expr(conn, col, cache)} AS {c}" for c, _, col in CHAMPS[type_] if col)
    try:
        r = conn.execute(f"SELECT {_ID[type_]} AS _id, {sel} FROM {_FROM[type_]} WHERE {where} LIMIT 1",
                         params).fetchone()
    except Exception:
        return None
    return dict(r) if r else None


def _produit_pour(conn, ref, machine=None, laize=None, reference=None) -> Optional[int]:
    if not (ref or reference):
        return None
    try:
        from app.services.fiche_choix import choisir_fiche
        ft = choisir_fiche(conn, ref, machine, laize, reference, colonnes="id")
        return ft["id"] if ft else None
    except Exception:
        return None


def lire(conn, type_: str, id_, base_url: str = "") -> dict:
    """Champs à plat {"dossier.reference": "…", "client.ville": "…"} de
    l'enregistrement et de ceux qui lui sont liés. {} s'il est introuvable."""
    if type_ not in TYPES:
        return {}
    cache: dict = {}
    out: dict = {}
    vus = set()

    def poser(t, ligne):
        if not ligne or t in vus:
            return
        vus.add(t)
        for c, _, col in CHAMPS[t]:
            if col:
                out[f"{t}.{c}"] = _txt(ligne.get(c))
        if t == "produit":
            ref = ligne.get("reference") or ""
            out["produit.lien_fiche"] = (base_url.rstrip("/") + "/prod?produit=" + quote(str(ref), safe="")) if ref else ""

    ligne = _ligne(conn, type_, f"{_ID[type_]} = ?", (id_,), cache)
    if not ligne:
        return {}
    poser(type_, ligne)

    if type_ == "dossier":
        pe = conn.execute("SELECT * FROM planning_entries WHERE id = ?", (id_,)).fetchone()
        pe = dict(pe) if pe else {}
        of_id = pe.get("of_import_id")
        if not of_id and pe.get("numero_of"):
            r = conn.execute("SELECT id FROM of_imports WHERE of_numero = ? ORDER BY id DESC LIMIT 1",
                             (pe["numero_of"],)).fetchone()
            of_id = r["id"] if r else None
        if of_id:
            poser("of", _ligne(conn, "of", "o.id = ?", (of_id,), cache))
        fid = _produit_pour(conn, pe.get("ref_produit"), ligne.get("machine"), pe.get("laize"))
        if fid:
            poser("produit", _ligne(conn, "produit", "ft.id = ?", (fid,), cache))
        if pe.get("client"):
            poser("client", _ligne(conn, "client", "LOWER(TRIM(c.raison_sociale)) = LOWER(TRIM(?))",
                                   (pe["client"],), cache))
    elif type_ == "of":
        fid = _produit_pour(conn, ligne.get("reference"), ligne.get("machine"), None, ligne.get("reference"))
        if fid:
            poser("produit", _ligne(conn, "produit", "ft.id = ?", (fid,), cache))
    elif type_ == "article":
        fid = _produit_pour(conn, ligne.get("reference"), None, None, ligne.get("reference"))
        if fid:
            poser("produit", _ligne(conn, "produit", "ft.id = ?", (fid,), cache))
    elif type_ == "lot":
        b = conn.execute("SELECT matiere_id, no_dossier FROM stock_bobines WHERE id = ?", (id_,)).fetchone()
        if b and b["matiere_id"]:
            poser("matiere", _ligne(conn, "matiere", "mp.id = ?", (b["matiere_id"],), cache))
        if b and b["no_dossier"]:
            r = conn.execute("SELECT id FROM planning_entries WHERE reference = ? ORDER BY id DESC LIMIT 1",
                             (b["no_dossier"],)).fetchone()
            if r:
                poser("dossier", _ligne(conn, "dossier", "pe.id = ?", (r["id"],), cache))
    return out

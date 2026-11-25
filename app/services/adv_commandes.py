"""ADV — le carnet de commandes et sa chaîne de valeur.

Une ligne par ligne de commande RVGI à traiter, la même définition que le
carnet de l'ERP (`erp_tdb.adv`) : qtep > 0, position « en cours », référence
produit, entête présente. Le reste à livrer, lui, est `qte` moins les BL —
voir la note sur `qtep` dans `construire()`. Deux écrans ne donnent jamais deux chiffres pour le
même carnet, donc les prédicats sont importés, pas recopiés.

À côté de ce que dit RVGI, ce que MySifa sait de la ligne, étape par étape :

    BAT → Prod → Stock → Prépa → Départ prévu

Chaque étape vaut `oui`, `en_cours`, `non` ou `sans_objet` (et, pour le
stock seulement, `probable` — voir plus bas), et dit d'où elle
le tient (`detail`). L'ADV peut fixer une étape à la main (`adv_forcages`) :
la valeur forcée s'affiche, le calcul reste lisible à côté.

D'où vient chaque étape
-----------------------
- **BAT** : `bat_entries` par numéro d'article (`code1/code2`). Validé → oui,
  en attente → en cours. Sans BAT validé, une production lancée ou du stock
  de l'article valent BAT bon (oui). Sans BAT dans MySifa, un article déjà livré
  (`vte_ligne`) est une réimpression : sans objet. Le drapeau `bat` de RVGI
  n'apprend rien — il vaut 1 sur tout le carnet.
- **Prod** : les dossiers du planning qui couvrent la ligne (voir
  `_dossiers_de_ligne`). Tous terminés → oui, un en cours → en cours, sinon
  non. Une ligne servie sur stock ou en sous-traitance n'attend pas de prod.
- **Stock** : le stock MyStock de la référence (`lots_stock`), PAS celui de
  RVGI. Le stock d'une référence est partagé entre ses lignes : il est
  attribué par ordre de priorité (prépas engagées d'abord, puis date
  d'expédition), et les lots en FIFO — deux lignes ne revendiquent jamais
  les mêmes étiquettes.
  **Probable** : la logistique ne rentre pas toujours en stock une
  production qui part directement. Quand la Prod est faite et que les
  étiquettes saisies en fin de production (code 89, compte de MyProd)
  couvrent le reste à livrer (95 % suffisent, `ADV_STOCK_PROBABLE_COUVERTURE` :
  la gâche ne bloque pas), le stock est réputé là : la ligne se prépare.
  La production d'un dossier qui sert plusieurs lignes se partage entre
  elles dans l'ordre de priorité, comme le stock.
- **Prépa** : `adv_prepas`, saisie par la logistique dans l'onglet Prépa.
- **Départ prévu** : un départ MyExpé rattaché à la ligne, à l'un de ses
  dossiers, ou qui porte le numéro de commande dans son ARC.

Lecture seule sur les deux bases : la connexion du miroir attache MySifa en
`mode=ro`. Les écritures (prépa, forçage) passent par le router, sur
`get_db()`.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from config import ADV_ETAPES, ADV_PREPA_HORIZON_JOURS, ADV_PREPA_URGENCE_JOURS, ADV_STOCK_PROBABLE_COUVERTURE
from app.services import erp_mirror as miroir
from app.services import erp_tdb as tdb
from app.services.erp_stock import _reference
from app.services import machines_type as _mtype

_PARIS = ZoneInfo("Europe/Paris")
ETAPES = tuple(k for k, _ in ADV_ETAPES)
VALEURS = ("oui", "en_cours", "non", "sans_objet", "probable")
# Ce qui laisse la ligne avancer : rien à relancer sur cette étape.
FRANCHIES = ("oui", "sans_objet", "probable")
STATUTS_PREPA = ("a_preparer", "en_cours", "prete")

# Le numéro de commande RVGI dans un texte libre (référence de dossier, ARC
# d'un départ) : « 9932856 - L6 », « Rel 9932705 - L2 ».
_RE_COMMANDE = re.compile(r"(?<!\d)(99\d{5})(?!\d)")
# La ligne de commande : « - L6 », « L 2 ».
_RE_LIGNE = re.compile(r"(?<![A-Za-z0-9])L\s*(\d{1,3})(?!\d)")
# Une référence MyStock commence par « famille/numéro », parfois suivie d'un
# complément (« 1153/0005 - BOX DE 510 000 »).
_RE_REF = re.compile(r"^\s*(\d+)\s*/\s*(\d+)")


# ── Petits outils ────────────────────────────────────────────────────────────

def _jour(v: Any) -> Optional[str]:
    """« 2026-11-20 00:00:00 » → « 2026-11-20 » ; sentinelle → None."""
    s = miroir._propre_date(v)
    if not s:
        return None
    s = str(s)[:10]
    if not ("2000-01-01" < s < "2090-01-01"):
        return None
    return s


def _ref_norm(texte: Any) -> Optional[str]:
    m = _RE_REF.match(str(texte or ""))
    return _reference(m.group(1), m.group(2)) if m else None


def _f(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _lignes(conn, sql, params=()) -> List[Dict[str, Any]]:
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    except sqlite3.Error:
        return []


def _table(conn, nom: str) -> bool:
    try:
        return conn.execute(
            "SELECT 1 FROM mysifa.sqlite_master WHERE type='table' AND name=?",
            (nom,)).fetchone() is not None
    except sqlite3.Error:
        return False


def _colonnes(conn, nom: str) -> set:
    try:
        return {r[1] for r in conn.execute('PRAGMA mysifa.table_info("%s")' % nom)}
    except sqlite3.Error:
        return set()


def cle_ligne(numero: Any, ligne: Any) -> str:
    return "%s-%s" % (str(numero).strip(), int(ligne or 0))


# ── Le carnet RVGI ───────────────────────────────────────────────────────────

ADRESSE_LIVRAISON = ("lrs", "ladr1", "ladr2", "lcp", "lville", "lpays")


def destination(b: Dict[str, Any]) -> Dict[str, Any]:
    """L'adresse de livraison d'une ligne, et sa clé : deux lignes qui ont la
    même clé partent au même endroit (casse et espaces ignorés)."""
    v = {c: " ".join(str(b.get("liv_" + c) or "").split()) for c in ADRESSE_LIVRAISON}
    cle = "|".join(v[c].upper() for c in ADRESSE_LIVRAISON)
    return {"rs": v["lrs"], "adr1": v["ladr1"], "adr2": v["ladr2"], "cp": v["lcp"],
            "ville": v["lville"], "pays": v["lpays"], "cle": cle if cle.strip("|") else ""}


def _carnet_rvgi(conn, sch) -> List[Dict[str, Any]]:
    produit = tdb._ligne_produit("l")
    ouvert = ("l.qtep > 0 AND COALESCE(l.lpos, 0) = %d AND %s AND %s"
              % (tdb.POS_EN_COURS, produit, tdb._existe_piece(sch)))
    vref = "COALESCE(NULLIF(TRIM(l.vref),''), e.vref)" if sch.a("cde_ligne", "vref") else (
        "e.vref" if sch.a("cde_entete", "vref") else "''")
    amjc = "e.amjc" if sch.a("cde_entete", "amjc") else "NULL"
    # Adresse de livraison de la LIGNE (une commande peut partir à plusieurs
    # adresses) : ce qui part ensemble = même date, même adresse.
    adresse = ", ".join(
        ("l.%s AS liv_%s" % (c, c)) if sch.a("cde_ligne", c) else ("NULL AS liv_%s" % c)
        for c in ADRESSE_LIVRAISON)
    # Déjà livré : les lignes de BL qui reportent cette ligne de commande
    # (colonnes de report explicites, jamais le numéro seul), BL vivant.
    if sch.a("liv_ligne", "numcde", "lignecde", "qte"):
        livre = ("(SELECT COALESCE(SUM(b.qte), 0) FROM liv_ligne b WHERE b.numcde = l.numero"
                 " AND b.lignecde = l.ligne AND %s)" % tdb._existe_piece(sch, entete="liv_entete", alias="b"))
    else:
        livre = "0"
    return _lignes(conn, """
        SELECT l.id AS id, l.numero AS numero, l.ligne AS ligne, e.rs AS client,
               %s AS ref_client, %s AS creee_le,
               l.code1 AS code1, l.code2 AS code2, l.des1 AS designation,
               l.qte AS qte, l.qtep AS qtep, %s AS livre,
               l.amje AS amje, l.amjl AS amjl, l.orig AS origine, %s
          FROM cde_ligne l JOIN cde_entete e ON e.numero = l.numero
         WHERE %s
    """ % (vref, amjc, livre, adresse, ouvert))


def _deja_livres(conn, sch, refs: set) -> set:
    """Articles qui ont déjà été facturés : une réimpression n'a pas de BAT."""
    if not refs or not sch.a("vte_ligne", "code1", "code2"):
        return set()
    c1 = sorted({r.split("/")[0] for r in refs})
    out = set()
    for i in range(0, len(c1), 400):
        part = c1[i:i + 400]
        for r in _lignes(conn, "SELECT DISTINCT code1, code2 FROM vte_ligne WHERE code1 IN (%s)"
                         % ",".join("?" * len(part)), part):
            out.add(_reference(r["code1"], r["code2"]))
    return out & refs


# ── Ce que MySifa sait ───────────────────────────────────────────────────────

def _stock(conn) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, List[Dict[str, Any]]]]:
    """({réf: {unite, produits, designation}}, {réf: [lots FIFO]})."""
    produits: Dict[str, Dict[str, Any]] = {}
    lots: Dict[str, List[Dict[str, Any]]] = {}
    if not (_table(conn, "produits") and _table(conn, "lots_stock")):
        return produits, lots
    par_id = {}
    for r in _lignes(conn, "SELECT id, reference, designation, unite FROM mysifa.produits"):
        ref = _ref_norm(r["reference"])
        if not ref:
            continue
        # Une référence « exacte » prime sur une variante (« … - BOX DE 510 000 ») :
        # même article, mais pas forcément le même conditionnement.
        exacte = str(r["reference"] or "").strip() == ref
        par_id[r["id"]] = (ref, exacte)
        p = produits.setdefault(ref, {"unite": None, "produits": [], "designation": None})
        p["produits"].append({"id": r["id"], "reference": r["reference"], "unite": r["unite"],
                              "exacte": exacte})
        if exacte or not p["unite"]:
            p["unite"] = r["unite"]
            p["designation"] = r["designation"]
    for r in _lignes(conn, """
        SELECT id, produit_id, emplacement, quantite_restante, date_entree
          FROM mysifa.lots_stock WHERE quantite_restante > 0
      ORDER BY date_entree, id"""):
        ref, exacte = par_id.get(r["produit_id"], (None, False))
        if not ref:
            continue
        p = produits[ref]
        unite_lot = next((x["unite"] for x in p["produits"] if x["id"] == r["produit_id"]), None)
        # On ne mélange pas les unités : un lot en étiquettes ne sert pas une
        # ligne comptée en cartons.
        if unite_lot != p["unite"]:
            continue
        lots.setdefault(ref, []).append({
            "lot_id": r["id"], "produit_id": r["produit_id"],
            "emplacement": r["emplacement"], "quantite": _f(r["quantite_restante"]),
            "date_entree": (r["date_entree"] or "")[:10] or None,
        })
    return produits, lots


def _bats(conn) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    if not _table(conn, "bat_entries"):
        return out
    for r in _lignes(conn, """SELECT id, numero_article, statut, description, updated_at
                                FROM mysifa.bat_entries ORDER BY updated_at"""):
        ref = _ref_norm(r["numero_article"])
        if ref:
            out[ref] = r          # le plus récent l'emporte
    return out


def _dossiers(conn) -> List[Dict[str, Any]]:
    if not _table(conn, "planning_entries"):
        return []
    cols = _colonnes(conn, "planning_entries")
    of = "of_import_id" if "of_import_id" in cols else "NULL"
    pour_rep = "pe.pour_repiquage" if "pour_repiquage" in cols else "0"
    src_rep = "pe.repiquage_source_id" if "repiquage_source_id" in cols else "NULL"
    m_type = "m.type" if "type" in _colonnes(conn, "machines") else "NULL"
    epc = "pe.etiquettes_par_carton" if "etiquettes_par_carton" in cols else "NULL"
    rows = _lignes(conn, """
        SELECT pe.id, pe.reference, pe.numero_of, pe.ref_produit, pe.statut, pe.statut_reel,
               pe.planned_start, pe.planned_end, pe.machine_id, pe.client, %s AS of_import_id,
               %s AS pour_repiquage, %s AS repiquage_source_id,
               m.nom AS machine, %s AS machine_type, %s AS etiquettes_par_carton
          FROM mysifa.planning_entries pe
          LEFT JOIN mysifa.machines m ON m.id = pe.machine_id
    """ % (of, pour_rep, src_rep, m_type, epc))
    if not rows:
        # Sans la table des machines (base partielle), on se passe du nom.
        rows = _lignes(conn, """
            SELECT id, reference, numero_of, ref_produit, statut, statut_reel,
                   planned_start, planned_end, machine_id, client, %s AS of_import_id,
                   NULL AS machine
              FROM mysifa.planning_entries""" % of)
    # Fin réelle : la saisie « Fin de production » (code 89) du dossier.
    fins: Dict[int, str] = {}
    if _table(conn, "production_data"):
        for r in _lignes(conn, """
            SELECT planning_entry_id AS pe, MAX(date_operation) AS fin
              FROM mysifa.production_data
             WHERE operation_code = '89' AND COALESCE(est_annule, 0) = 0
               AND planning_entry_id IS NOT NULL
          GROUP BY planning_entry_id"""):
            fins[r["pe"]] = r["fin"]
    for r in rows:
        # Poste de repiquage : son type (machines.type), sinon son nom.
        r["repiquage"] = _mtype.est_repiquage({"type": r.get("machine_type"), "nom": r.get("machine")})
        texte = "%s %s" % (r.get("reference") or "", r.get("numero_of") or "")
        r["_numeros"] = set(_RE_COMMANDE.findall(texte))
        r["_lignes"] = {int(x) for x in _RE_LIGNE.findall(texte)}
        r["_ref"] = _ref_norm(r.get("ref_produit"))
        r["fin_reelle"] = fins.get(r["id"])
    return rows


def _etiquettes_produites(conn, refs: set) -> Dict[str, float]:
    """Étiquettes produites par dossier (`no_dossier`), au compte de MyProd.

    `build_dossier_production_stats` est le calcul de l'écran de référence
    (quantité saisie en fin de production, une par opérateur et par jour) :
    l'ADV ne recompte pas, un dossier n'a qu'un chiffre.
    """
    refs = sorted(r for r in refs if r)
    if not refs or not _table(conn, "production_data"):
        return {}
    from app.services.dossier_stats import build_dossier_production_stats
    ph = ",".join("?" * len(refs))
    rows = _lignes(conn, """
        SELECT * FROM mysifa.production_data
         WHERE no_dossier IN (%s) AND COALESCE(est_annule, 0) = 0""" % ph, refs)
    out = {}
    for ref in refs:
        try:
            q = build_dossier_production_stats(rows, ref)["quantites"]
            out[ref] = float(q.get("etiquettes") or 0)
        except Exception:
            out[ref] = 0.0
    return out


# L'unité de la ligne est celle de la référence MyStock ; sans référence, ce
# sont des étiquettes.
_UNITES_ETIQUETTE = (None, "", "0", "étiquette", "etiquette")


def _production_en_unite(etiq: float, unite: Optional[str], d: Dict[str, Any]) -> Optional[float]:
    """Les étiquettes produites, dans l'unité de la ligne — None si on ne sait
    pas convertir (un carton sans « étiquettes par carton » au planning, une
    bobine, une planche…)."""
    u = (unite or "").strip().lower()
    if u in _UNITES_ETIQUETTE:
        return etiq
    if u in ("carton", "cartons"):
        epc = _f(d.get("etiquettes_par_carton"))
        return etiq / epc if epc > 0 else None
    return None


def _jauge_prod(lignes: List[Dict[str, Any]], produites: Dict[str, float]) -> None:
    """Prod en cours : la part déjà produite, pour la jauge du nœud.

    Étiquettes de fin de prod saisies jusqu'ici sur les dossiers d'impression
    de la ligne, ramenées à son unité, sur le reste à livrer. Sans conversion
    possible (cartons sans « étiquettes par carton »…), pas de jauge.
    """
    for l in lignes:
        et = l["etapes"]["prod"]
        ds = l.get("_ds_impression") or []
        if et["valeur"] != "en_cours" or et.get("force") or not ds or l["reste"] <= 0:
            continue
        unite = l["stock"]["unite"]
        fait = 0.0
        for d in ds:
            q = _production_en_unite(produites.get(str(d.get("reference") or "").strip(), 0.0), unite, d)
            if q is None:
                fait = None
                break
            fait += q
        if not fait:
            continue
        et["jauge"] = _ratio(fait, l["reste"])
        et["detail"] += " · %s %s produites sur %s (%d %%)" % (
            _n(fait), _accord(unite, fait), _n(l["reste"]), int(min(fait / l["reste"], 1) * 100))


def _stock_probable(lignes: List[Dict[str, Any]], produites: Dict[str, float]) -> None:
    """Passe le stock en « probable » quand la production terminée couvre la ligne.

    Ne touche que les lignes dont la Prod est faite et dont le stock MyStock
    ne suffit pas. La production d'un dossier est partagée entre ses lignes
    dans l'ordre de priorité ; ce que MyStock leur a déjà attribué compte.
    """
    reste_dossier = dict(produites)
    for l in sorted(lignes, key=lambda x: x["priorite"]):
        et = l["etapes"]["stock"]
        ds = l.pop("_ds_impression", [])
        if (l["etapes"]["prod"]["valeur"] != "oui" or et["calcul"] == "oui"
                or et.get("force") or not ds or l["reste"] <= 0):
            continue
        besoin = l["reste"] - l["stock"]["alloue"]
        unite = l["stock"]["unite"]
        dispo = []
        for d in ds:
            ref = str(d.get("reference") or "").strip()
            q = _production_en_unite(reste_dossier.get(ref, 0.0), unite, d)
            if q is None:
                dispo = None
                break
            dispo.append((ref, d, q))
        total = sum(q for _, _, q in dispo) if dispo else 0.0
        # La gâche d'un tirage ne bloque pas : il suffit de couvrir 95 % du
        # reste (ADV_STOCK_PROBABLE_COUVERTURE).
        if not dispo or total < besoin * ADV_STOCK_PROBABLE_COUVERTURE:
            continue
        sortie = min(total, besoin)
        pris = sortie
        for ref, d, q in dispo:
            if pris <= 0:
                break
            prend = min(q, pris)
            pris -= prend
            par_unite = _production_en_unite(1.0, unite, d) or 1.0
            reste_dossier[ref] = max(reste_dossier.get(ref, 0.0) - prend / par_unite, 0.0)
        refs = ", ".join(ref for ref, _, _ in dispo)
        u = (" " + unite) if unite and unite.strip().lower() not in _UNITES_ETIQUETTE else " étiquettes"
        l["stock"]["sortie_prod"] = sortie
        l["stock"]["dossiers_prod"] = [ref for ref, _, _ in dispo]
        l["etapes"]["stock"] = _etape(
            "probable",
            "Production terminée (%s%s produites%s, dossier %s) mais pas entrée dans MyStock : "
            "à préparer en sortie de production" % (
                _n(total), u,
                (", %d %% du reste à livrer" % int(total * 100 // besoin)) if total < besoin else "",
                refs))
        l["a_fabriquer"] = 0.0


def _rattachements(conn) -> List[Dict[str, Any]]:
    if not _table(conn, "rvgi_rattachements"):
        return []
    return _lignes(conn, """
        SELECT objet, objet_id, numero, ligne FROM mysifa.rvgi_rattachements
         WHERE piece = 'commande'""")


def _departs(conn) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, set], Dict[str, set]]:
    """({id: départ}, {planning_entry_id: {départs}}, {n° commande: {départs}})."""
    par_id: Dict[int, Dict[str, Any]] = {}
    par_dossier: Dict[int, set] = {}
    par_numero: Dict[str, set] = {}
    if not _table(conn, "expe_departs"):
        return par_id, par_dossier, par_numero
    cols = _colonnes(conn, "expe_departs")
    parti = "parti_le" if "parti_le" in cols else "NULL"
    for r in _lignes(conn, """
        SELECT id, date_enlevement, date_livraison, transporteur, statut, arc, ref_sifa,
               no_bl, planning_entry_id, %s AS parti_le
          FROM mysifa.expe_departs
         WHERE date_enlevement >= ?""" % parti,
            ((aujourdhui_paris() - timedelta(days=120)).isoformat(),)):
        par_id[r["id"]] = r
        if r.get("planning_entry_id"):
            par_dossier.setdefault(r["planning_entry_id"], set()).add(r["id"])
        for n in _RE_COMMANDE.findall("%s %s" % (r.get("arc") or "", r.get("ref_sifa") or "")):
            par_numero.setdefault(n, set()).add(r["id"])
    if _table(conn, "expe_depart_dossiers"):
        for r in _lignes(conn, "SELECT depart_id, planning_entry_id FROM mysifa.expe_depart_dossiers"):
            if r["depart_id"] in par_id:
                par_dossier.setdefault(r["planning_entry_id"], set()).add(r["depart_id"])
    return par_id, par_dossier, par_numero


def _prepas(conn) -> Dict[str, Dict[str, Any]]:
    if not _table(conn, "adv_prepas"):
        return {}
    return {cle_ligne(r["numero"], r["ligne"]): r
            for r in _lignes(conn, "SELECT * FROM mysifa.adv_prepas")}


def _repiquages(conn) -> Dict[str, Dict[str, Any]]:
    """Statut du repiquage fixé à la main par l'ADV (à faire, en cours, terminé)."""
    if not _table(conn, "adv_repiquages"):
        return {}
    return {cle_ligne(r["numero"], r["ligne"]): r
            for r in _lignes(conn, "SELECT * FROM mysifa.adv_repiquages")}


def _priorites(conn) -> Dict[str, Dict[str, Any]]:
    """Rangs fixés à la main dans l'onglet Prépa (administration, direction)."""
    if not _table(conn, "adv_prepa_priorites"):
        return {}
    return {cle_ligne(r["numero"], r["ligne"]): r
            for r in _lignes(conn, "SELECT * FROM mysifa.adv_prepa_priorites")}


def _urgences(conn) -> Dict[str, Dict[str, Any]]:
    """Préparations marquées « urgente » à la main par l'ADV."""
    if not _table(conn, "adv_urgences"):
        return {}
    return {cle_ligne(r["numero"], r["ligne"]): r
            for r in _lignes(conn, "SELECT * FROM mysifa.adv_urgences")}


def _infos(conn) -> Dict[str, List[Dict[str, Any]]]:
    """Informations de suivi notées par l'ADV, la plus récente en tête."""
    if not _table(conn, "adv_infos"):
        return {}
    out: Dict[str, List[Dict[str, Any]]] = {}
    for r in _lignes(conn, """SELECT id, numero, ligne, texte, cree_le, cree_par
                                 FROM mysifa.adv_infos ORDER BY cree_le DESC, id DESC"""):
        out.setdefault(cle_ligne(r["numero"], r["ligne"]), []).append(
            {"id": r["id"], "texte": r["texte"], "cree_le": r["cree_le"], "cree_par": r["cree_par"]})
    return out


def _jours_prepa(conn) -> Dict[str, Dict[str, Any]]:
    """Jour de préparation fixé à la main par l'ADV dans le planning de prépa."""
    if not _table(conn, "adv_prepa_jours"):
        return {}
    return {cle_ligne(r["numero"], r["ligne"]): r
            for r in _lignes(conn, "SELECT * FROM mysifa.adv_prepa_jours")}


def _forcages(conn) -> Dict[str, Dict[str, Dict[str, Any]]]:
    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    if not _table(conn, "adv_forcages"):
        return out
    for r in _lignes(conn, "SELECT * FROM mysifa.adv_forcages"):
        out.setdefault(cle_ligne(r["numero"], r["ligne"]), {})[r["etape"]] = r
    return out


# ── Rapprochements ───────────────────────────────────────────────────────────

def _dossiers_de_ligne(l: Dict[str, Any], dossiers: List[Dict[str, Any]],
                       ratt_dossier: Dict[Tuple[str, Optional[int]], set],
                       par_id: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Les dossiers du planning qui produisent cette ligne.

    1. Le rattachement explicite (`rvgi_rattachements`, dossier ou OF) fait foi.
    2. À défaut, la référence du dossier porte le numéro de commande, et
       l'article du dossier est celui de la ligne — ou, sans article, son
       « - L<n> » désigne cette ligne (ou n'en désigne aucune).
    """
    num, lg, ref = str(l["numero"]), int(l["ligne"] or 0), l["article"]
    ids = set(ratt_dossier.get((num, lg), set())) | set(ratt_dossier.get((num, None), set()))
    if ids:
        return [par_id[i] for i in sorted(ids) if i in par_id]
    out = []
    for d in dossiers:
        if num not in d["_numeros"]:
            continue
        if d["_ref"]:
            if d["_ref"] != ref:
                continue
        elif d["_lignes"] and lg not in d["_lignes"]:
            continue
        out.append(d)
    return out


# ── Les étapes ───────────────────────────────────────────────────────────────

def _etape(valeur: str, detail: str, **extra) -> Dict[str, Any]:
    e = {"calcul": valeur, "valeur": valeur, "detail": detail, "force": False}
    e.update(extra)
    return e


def _etape_bat(l, bats, deja) -> Dict[str, Any]:
    b = bats.get(l["article"])
    if b:
        if b["statut"] == "valide":
            return _etape("oui", "BAT validé (MyBAT)", bat_id=b["id"])
        return _etape("en_cours", "BAT en attente de validation (MyBAT)", bat_id=b["id"])
    if l["article"] in deja:
        return _etape("sans_objet", "Réimpression : article déjà livré, aucun BAT ouvert")
    return _etape("non", "Aucun BAT dans MyBAT pour cet article")


def _bat_par_la_suite(bat, prod, stock) -> Dict[str, Any]:
    """Le BAT n'est pas toujours tracé dans MyBAT : une production lancée, ou
    du stock de l'article, dit qu'il a été bon. Décision d'Eugène (24/11/2026).
    """
    if bat["calcul"] not in ("non", "en_cours"):
        return bat
    raisons = []
    if prod["calcul"] in ("oui", "en_cours"):
        raisons.append("production lancée")
    if stock["calcul"] in ("oui", "en_cours"):
        raisons.append("article en stock")
    if not raisons:
        return bat
    avant = "BAT en attente dans MyBAT" if bat["calcul"] == "en_cours" else "Pas de BAT validé dans MyBAT"
    extra = {k: v for k, v in bat.items() if k == "bat_id"}
    return _etape("oui", "%s, mais %s : BAT réputé bon" % (avant, " et ".join(raisons)), **extra)


STATUTS_REPIQUAGE = ("a_faire", "en_cours", "termine")


def _repiquage_de_ligne(dossiers, manuel) -> Dict[str, Any]:
    """Le repiquage d'une ligne : requis ou non, et où il en est.

    Requis quand une production de la ligne est cochée « pour repiquage », ou
    qu'un dossier de repiquage la couvre. Le statut vient du dossier de
    repiquage (terminé, en cours, sinon à faire) ; l'ADV peut le fixer à la
    main — un repiquage sous-traité ou suivi hors planning existe aussi — et
    le fixer rend le repiquage requis.
    """
    reps = [d for d in dossiers if d.get("repiquage")]
    requis = bool(reps) or any(d.get("pour_repiquage") for d in dossiers)
    if reps and all(d.get("statut") == "termine" for d in reps):
        calcul = "termine"
    elif any(d.get("statut") == "en_cours" or d.get("statut_reel") == "reellement_en_saisie" for d in reps):
        calcul = "en_cours"
    else:
        calcul = "a_faire"
    m = (manuel or {}).get("statut")
    if m in STATUTS_REPIQUAGE:
        return {"requis": True, "statut": m, "calcul": calcul if requis else None, "manuel": True,
                "maj_par": manuel.get("maj_par"), "maj_le": manuel.get("maj_le"),
                "planifie": bool(reps)}
    return {"requis": requis, "statut": calcul if requis else None, "calcul": calcul if requis else None,
            "manuel": False, "maj_par": None, "maj_le": None, "planifie": bool(reps)}


def _etape_prod(l, dossiers, repiquage=None) -> Dict[str, Any]:
    """Prod = l'impression, puis le repiquage quand la ligne en demande un."""
    rep = repiquage or {}
    impression = _etape_impression(l, [d for d in dossiers if not d.get("repiquage")])
    if not rep.get("requis"):
        return impression
    # Une ligne servie sur stock peut être repiquée (étiquettes du stock
    # surimprimées) : « sans objet » côté impression compte alors comme fait.
    lib = {"a_faire": "repiquage à faire", "en_cours": "repiquage en cours",
           "termine": "repiquage terminé"}[rep["statut"]]
    if rep.get("manuel"):
        lib += " (fixé par l’ADV)"
    if impression["calcul"] in ("oui", "sans_objet"):
        if rep["statut"] == "termine":
            return _etape("oui", "Impression et repiquage terminés" + (" (repiquage fixé par l’ADV)" if rep.get("manuel") else ""))
        return _etape("en_cours", "Impression terminée · " + lib)
    return _etape(impression["calcul"], impression["detail"] + " · puis repiquage")


def _etape_impression(l, dossiers) -> Dict[str, Any]:
    if l["origine"] == tdb.ORIG_STOCK:
        return _etape("sans_objet", "Ligne servie sur stock")
    if l["origine"] == tdb.ORIG_SOUS_TRAITANCE:
        return _etape("sans_objet", "Sous-traitance")
    if not dossiers:
        # Rien à fabriquer : le stock MyStock attribué couvre la ligne.
        if l.get("a_fabriquer", 1) <= 0:
            return _etape("sans_objet", "Couvert par le stock MyStock, rien à fabriquer")
        return _etape("non", "Aucun dossier au planning")
    statuts = [d.get("statut") for d in dossiers]
    if all(s == "termine" for s in statuts):
        return _etape("oui", "Production terminée")
    if any(s == "en_cours" or d.get("statut_reel") == "reellement_en_saisie"
           for s, d in zip(statuts, dossiers)):
        return _etape("en_cours", "En production")
    return _etape("non", "Planifié, pas encore démarré")


def _accord(unite: Optional[str], q: float) -> str:
    """« étiquette » → « étiquettes » au-delà de 1 (bobine, carton…)."""
    u = (unite or "étiquette").strip() or "étiquette"
    if abs(q) < 2 or u[-1:].lower() in ("s", "x", "z"):
        return u
    return u + "s"


def _ratio(fait: float, total: float) -> Optional[float]:
    """Part faite, pour la jauge du nœud : entre 0 et 1, None si rien à mesurer."""
    if total <= 0:
        return None
    return round(max(0.0, min(fait / total, 1.0)), 3)


def _etape_stock(reste, alloue, total, unite) -> Dict[str, Any]:
    if reste > 0 and alloue >= reste:
        return _etape("oui", "Stock MyStock suffisant")
    if alloue > 0:
        return _etape("en_cours", "Stock partiel : %s %s sur %s (%d %%)" % (
            _n(alloue), _accord(unite, alloue), _n(reste), int(alloue * 100 // reste)),
            jauge=_ratio(alloue, reste))
    if total > 0:
        return _etape("non", "Stock MyStock déjà réservé par des lignes plus urgentes")
    return _etape("non", "Rien en stock dans MyStock")


def _etape_prepa(p) -> Dict[str, Any]:
    s = (p or {}).get("statut") or "a_preparer"
    if s == "prete":
        return _etape("oui", "Préparation prête")
    if s == "en_cours":
        return _etape("en_cours", "Préparation en cours")
    return _etape("non", "Pas encore préparée")


# Un départ parti il y a plus longtemps que ça ne « prévoit » plus rien : la
# ligne est toujours ouverte, c'est un envoi précédent (partiel, ou d'une autre
# ligne de la même commande).
JOURS_DEPART_RECENT = 7


def _etape_depart(deps, aujourdhui: str) -> Dict[str, Any]:
    """Un départ PRÉVU : à venir (ou du jour), ou parti il y a moins de 7 jours.

    Relevé le 23/11/2026 : une ligne encore ouverte affichait « Départ prévu :
    Oui » sur la foi d'un enlèvement du 29/10, rattaché par le numéro de
    commande — un envoi antérieur. Un départ passé reste listé dans la fiche,
    il ne valide plus l'étape.
    """
    if not deps:
        return _etape("non", "Aucun départ MyExpé")
    recent = (date.fromisoformat(aujourdhui) - timedelta(days=JOURS_DEPART_RECENT)).isoformat()
    partis = [d for d in deps if d.get("parti_le") and str(d["parti_le"])[:10] >= recent]
    if partis:
        return _etape("oui", "Parti le %s" % _fr(partis[-1]["parti_le"]))
    a_venir = [d for d in deps if not d.get("parti_le")
               and (d.get("date_enlevement") or "")[:10] >= aujourdhui]
    if not a_venir:
        dernier = max((d.get("date_enlevement") or "")[:10] for d in deps)
        return _etape("non", "Aucun départ à venir · dernier le %s" % _fr(dernier))
    valides = [d for d in a_venir if d.get("statut") == "valide"]
    d = (valides or a_venir)[0]
    txt = "Enlèvement prévu le %s" % _fr(d.get("date_enlevement"))
    return _etape("oui" if valides else "en_cours", txt if valides else txt + " (à valider)")


def _n(v: float) -> str:
    v = float(v or 0)
    s = ("%d" % v) if v == int(v) else ("%.2f" % v)
    if "." in s:
        ent, dec = s.split(".")
    else:
        ent, dec = s, ""
    neg = ent.startswith("-")
    ent = ent.lstrip("-")
    grp = []
    while len(ent) > 3:
        grp.insert(0, ent[-3:])
        ent = ent[:-3]
    grp.insert(0, ent)
    return ("-" if neg else "") + " ".join(grp) + (("," + dec) if dec else "")


def _fr(v: Any) -> str:
    s = str(v or "")[:10]
    if len(s) == 10 and s[4] == "-":
        return "%s/%s/%s" % (s[8:10], s[5:7], s[0:4])
    return s or "?"


def _appliquer_forcage(etape: Dict[str, Any], f: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not f or f.get("valeur") not in VALEURS:
        return etape
    etape["valeur"] = f["valeur"]
    etape["force"] = True
    etape["force_note"] = f.get("note")
    etape["force_par"] = f.get("maj_par")
    etape["force_le"] = f.get("maj_le")
    return etape


# ── Assemblage ───────────────────────────────────────────────────────────────

def _cle_priorite(l: Dict[str, Any]):
    """Prépas engagées d'abord (leurs étiquettes sont déjà mises de côté),
    puis l'ordre fixé à la main par l'ADV, puis les lignes marquées urgentes,
    puis la date d'expédition, la plus proche en tête ; sans date, à la fin."""
    engagee = 0 if (l.get("_prepa_statut") in ("en_cours", "prete")) else 1
    rang = l.get("priorite_manuelle")
    return (engagee, 0 if rang is not None else 1, rang or 0,
            0 if l.get("urgente_manuelle") else 1,
            l["expedition"] or "9999-12-31", str(l["numero"]), int(l["ligne"] or 0))


def construire(aujourdhui: Optional[date] = None) -> Dict[str, Any]:
    """Le carnet complet, une entrée par ligne, étapes calculées."""
    j = aujourdhui or aujourdhui_paris()
    sortie: Dict[str, Any] = {
        "present": miroir.miroir_present(),
        "aujourdhui": j.isoformat(),
        "etapes": [{"cle": k, "label": v} for k, v in ADV_ETAPES],
        "lignes": [],
        "indispo": [],
    }
    if not sortie["present"]:
        return sortie

    with miroir.get_erp_db(avec_mysifa=True) as conn:
        sch = tdb._Schema(conn)
        manque = sch.manque("cde_ligne", "qtep", "lpos", "amje", "numero", "ligne", "code1", "code2")
        if manque:
            sortie["indispo"].append("Carnet : " + manque)
            return sortie
        if not miroir.mysifa_attachee(conn):
            sortie["indispo"].append("Base MySifa illisible : étapes non calculées")
        brutes = _carnet_rvgi(conn, sch)
        for l in brutes:
            l["article"] = _reference(l["code1"], l["code2"])
        refs = {l["article"] for l in brutes}
        deja = _deja_livres(conn, sch, refs)
        produits, lots = _stock(conn)
        bats = _bats(conn)
        dossiers = _dossiers(conn)
        dossiers_par_id = {d["id"]: d for d in dossiers}
        par_of: Dict[int, List[int]] = {}
        for d in dossiers:
            if d.get("of_import_id"):
                par_of.setdefault(d["of_import_id"], []).append(d["id"])
        ratt_dossier: Dict[Tuple[str, Optional[int]], set] = {}
        ratt_depart: Dict[Tuple[str, Optional[int]], set] = {}
        for r in _rattachements(conn):
            cle = (str(r["numero"]).strip(), int(r["ligne"]) if r["ligne"] is not None else None)
            if r["objet"] == "dossier":
                ratt_dossier.setdefault(cle, set()).add(r["objet_id"])
            elif r["objet"] == "of":
                ratt_dossier.setdefault(cle, set()).update(par_of.get(r["objet_id"], []))
            elif r["objet"] == "depart":
                ratt_depart.setdefault(cle, set()).add(r["objet_id"])
        departs, deps_par_dossier, deps_par_numero = _departs(conn)
        prepas = _prepas(conn)
        priorites = _priorites(conn)
        urgences = _urgences(conn)
        infos = _infos(conn)
        jours_prepa = _jours_prepa(conn)
        repiquages_adv = _repiquages(conn)
        forcages = _forcages(conn)

    lignes: List[Dict[str, Any]] = []
    for b in brutes:
        cle = cle_ligne(b["numero"], b["ligne"])
        p = prepas.get(cle)
        pr = priorites.get(cle)
        ur = urgences.get(cle)
        jp = jours_prepa.get(cle)
        l = {
            "cle": cle,
            "numero": str(b["numero"]),
            "ligne": int(b["ligne"] or 0),
            "client": (b.get("client") or "").strip(),
            "ref_client": (b.get("ref_client") or "").strip() or None,
            "destination": destination(b),
            "creee_le": _jour(b.get("creee_le")),
            "article": b["article"],
            "designation": (b.get("designation") or "").strip(),
            "qte": _f(b.get("qte")),
            "livre": _f(b.get("livre")),
            # Le reste à livrer est la quantité commandée moins les BL. PAS
            # `qtep` : relevé le 20/11/2026, RVGI y cumule les commandes
            # ouvertes du même article et en retire SON stock (555 000 →
            # 960 000 → 1 365 000 sur des commandes de 202 500 / 405 000).
            # C'est le besoin de production vu par RVGI — exactement le stock
            # que l'ADV remplace par celui de MyStock. Gardé pour la fiche.
            "reste": max(_f(b.get("qte")) - _f(b.get("livre")), 0.0),
            "besoin_rvgi": _f(b.get("qtep")),
            "origine": int(b["origine"]) if str(b.get("origine") or "").isdigit() else None,
            "expedition": _jour(b.get("amje")),
            "livraison": _jour(b.get("amjl")),
            "_prepa_statut": (p or {}).get("statut"),
            "priorite_manuelle": int(pr["rang"]) if pr else None,
            "priorite_par": (pr or {}).get("maj_par"),
            "priorite_le": (pr or {}).get("maj_le"),
            "urgente_manuelle": bool(ur),
            "urgente_par": (ur or {}).get("maj_par"),
            "urgente_le": (ur or {}).get("maj_le"),
            "jour_manuel": (jp or {}).get("jour"),
            "jour_manuel_par": (jp or {}).get("maj_par"),
            "infos": infos.get(cle, []),
        }
        lignes.append(l)

    # Attribution du stock, ligne par ligne, dans l'ordre de priorité.
    restant = {ref: [dict(x) for x in ls] for ref, ls in lots.items()}
    total_ref = {ref: sum(x["quantite"] for x in ls) for ref, ls in lots.items()}
    for rang, l in enumerate(sorted(lignes, key=_cle_priorite), start=1):
        l["priorite"] = rang
        besoin = l["reste"]
        pris = []
        for lot in restant.get(l["article"], []):
            if besoin <= 0:
                break
            if lot["quantite"] <= 0:
                continue
            q = min(lot["quantite"], besoin)
            lot["quantite"] -= q
            besoin -= q
            pris.append({"emplacement": lot["emplacement"], "quantite": q,
                         "date_entree": lot["date_entree"], "lot_id": lot["lot_id"]})
        l["stock"] = {
            "total": total_ref.get(l["article"], 0.0),
            "alloue": l["reste"] - max(besoin, 0.0),
            "unite": (produits.get(l["article"]) or {}).get("unite"),
            "connu": l["article"] in produits,
            "emplacements": pris,
        }

    a_venir = j.isoformat()
    semaine = (j + timedelta(days=7)).isoformat()
    for l in lignes:
        ds = _dossiers_de_ligne(l, dossiers, ratt_dossier, dossiers_par_id)
        # Un dossier de repiquage relié (au planning) à l'une de ces productions
        # fait partie de la ligne, même sous une autre référence.
        ids_ds = {d["id"] for d in ds}
        ds = ds + [d for d in dossiers if d.get("repiquage_source_id") in ids_ds and d["id"] not in ids_ds]
        l["dossiers"] = [{
            "id": d["id"], "reference": d.get("reference"), "statut": d.get("statut"),
            "machine": d.get("machine"), "debut": d.get("planned_start"),
            "fin": d.get("fin_reelle") or d.get("planned_end"),
            "fin_reelle": bool(d.get("fin_reelle")),
            "repiquage": bool(d.get("repiquage")),
            "pour_repiquage": bool(d.get("pour_repiquage")),
        } for d in ds]
        l["repiquage"] = _repiquage_de_ligne(ds, repiquages_adv.get(l["cle"]))
        l["_ds_impression"] = [d for d in ds if not d.get("repiquage")]
        fins = [x["fin"] for x in l["dossiers"] if x["fin"]]
        l["fin_prod"] = (max(fins)[:16] if fins else None)
        l["fin_prod_reelle"] = bool(l["dossiers"]) and all(x["fin_reelle"] for x in l["dossiers"])

        ids_dep = set(ratt_depart.get((l["numero"], l["ligne"]), set())) \
            | set(ratt_depart.get((l["numero"], None), set())) \
            | set(deps_par_numero.get(l["numero"], set()))
        for d in ds:
            ids_dep |= deps_par_dossier.get(d["id"], set())
        deps = sorted((departs[i] for i in ids_dep if i in departs),
                      key=lambda d: (d.get("date_enlevement") or ""))
        l["departs"] = [{
            "id": d["id"], "date_enlevement": (d.get("date_enlevement") or "")[:10] or None,
            "transporteur": d.get("transporteur"), "statut": d.get("statut"),
            "parti_le": d.get("parti_le"), "no_bl": d.get("no_bl"),
        } for d in deps]

        p = prepas.get(l["cle"])
        l["prepa"] = {
            "statut": (p or {}).get("statut") or "a_preparer",
            "note": (p or {}).get("note"),
            "maj_le": (p or {}).get("maj_le"),
            "maj_par": (p or {}).get("maj_par"),
        }
        st = l["stock"]
        # Ce qu'il reste à produire une fois le stock MyStock attribué servi.
        l["a_fabriquer"] = max(l["reste"] - st["alloue"], 0.0)
        etapes = {
            "bat": _etape_bat(l, bats, deja),
            "prod": _etape_prod(l, ds, l["repiquage"]),
            "stock": _etape_stock(l["reste"], st["alloue"], st["total"], st["unite"]),
            "prepa": _etape_prepa(p),
            "depart": _etape_depart(deps, a_venir),
        }
        etapes["bat"] = _bat_par_la_suite(etapes["bat"], etapes["prod"], etapes["stock"])
        f = forcages.get(l["cle"], {})
        for k in ETAPES:
            _appliquer_forcage(etapes[k], f.get(k))
        l["etapes"] = etapes
        # La première étape qui n'est pas franchie : c'est elle qu'on relance.
        l["bloquante"] = next((k for k in ETAPES
                               if etapes[k]["valeur"] in ("non", "en_cours")), None)
        l["retard"] = bool(l["expedition"] and l["expedition"] < a_venir)
        l["semaine"] = bool(l["expedition"] and a_venir <= l["expedition"] < semaine)
        l.pop("_prepa_statut", None)

    # Stock « probable » : production finie, pas rentrée dans MyStock.
    # Et jauge de la Prod en cours : ce qui est déjà produit.
    candidats = {str(d.get("reference") or "").strip()
                 for l in lignes
                 if (l["etapes"]["prod"]["valeur"] == "oui" and l["etapes"]["stock"]["calcul"] != "oui")
                 or l["etapes"]["prod"]["valeur"] == "en_cours"
                 for d in l.get("_ds_impression", [])}
    produites = {}
    if candidats:
        try:
            with miroir.get_erp_db(avec_mysifa=True) as conn:
                produites = _etiquettes_produites(conn, candidats)
        except Exception:
            produites = {}
    _jauge_prod(lignes, produites)
    _stock_probable(lignes, produites)
    for l in lignes:
        l.pop("_ds_impression", None)
        l["bloquante"] = next((k for k in ETAPES
                               if l["etapes"][k]["valeur"] in ("non", "en_cours")), None)

    lignes.sort(key=lambda x: (x["expedition"] or "9999-12-31", x["numero"], x["ligne"]))
    sortie["lignes"] = lignes
    sortie["compteurs"] = compteurs(lignes)
    return sortie


def compteurs(lignes: List[Dict[str, Any]]) -> Dict[str, Any]:
    def _c(filtre):
        sel = [l for l in lignes if filtre(l)]
        return {"lignes": len(sel), "commandes": len({l["numero"] for l in sel})}
    out = {
        "carnet": _c(lambda l: True),
        "retard": _c(lambda l: l["retard"]),
        "semaine": _c(lambda l: l["semaine"]),
        "pretes": _c(lambda l: all(l["etapes"][k]["valeur"] in FRANCHIES
                                   for k in ("bat", "prod", "stock", "prepa"))),
    }
    out["etapes"] = {k: _c(lambda l, k=k: l["etapes"][k]["valeur"] in ("non", "en_cours"))
                     for k in ETAPES}
    return out


# ── L'onglet Prépa ───────────────────────────────────────────────────────────

# Dans l'ordre où la logistique les traite : ce qui est commencé d'abord.
GROUPES_PREPA = (
    ("en_cours", "En cours de préparation"),
    ("preparable", "À préparer — disponible"),
    ("partiel", "Stock partiel"),
    ("attente", "En attente de production"),
    ("pretes", "Prêtes, en attente de départ"),
)


def groupe_prepa(l: Dict[str, Any]) -> Optional[str]:
    """Où ranger la ligne dans l'onglet Prépa — None : elle n'y a pas sa place."""
    dep = l["etapes"]["depart"]
    if dep["calcul"] == "oui" and dep["detail"].startswith("Parti"):
        return None                       # déjà partie
    statut = l["prepa"]["statut"]
    if statut == "prete":
        return "pretes"
    if statut == "en_cours":
        return "en_cours"
    stock = l["etapes"]["stock"]["valeur"]
    if stock in FRANCHIES:
        return "preparable"
    if stock == "en_cours":
        return "partiel"
    return "attente"


def urgence(l: Dict[str, Any], groupe: Optional[str], aujourdhui: date) -> Optional[str]:
    """Pourquoi la préparation est urgente — None si elle ne l'est pas.

    Marquée par l'ADV, ou préparable (stock là, sortie de prod, ou déjà
    commencée) avec une expédition passée ou dans ADV_PREPA_URGENCE_JOURS.
    Une prépa prête ou partie n'est plus urgente.
    """
    if not groupe or groupe == "pretes":
        return None
    if l.get("urgente_manuelle"):
        return "Marquée urgente" + (" par " + l["urgente_par"] if l.get("urgente_par") else "")
    limite = (aujourdhui + timedelta(days=ADV_PREPA_URGENCE_JOURS)).isoformat()
    if groupe in ("preparable", "en_cours") and l.get("expedition") and l["expedition"] <= limite:
        j = aujourdhui.isoformat()
        quand = ("en retard" if l["expedition"] < j else
                 "aujourd'hui" if l["expedition"] == j else "le " + _fr(l["expedition"]))
        return "Expédition " + quand + ", de quoi la préparer"
    return None


def badges(aujourdhui: Optional[date] = None) -> Dict[str, Any]:
    """Les bulles rouges des tuiles du portail, d'un seul calcul du carnet.

    `urgentes` : préparations urgentes (logistique) ; `retard` et `semaine` :
    lignes à expédier en retard ou sous 7 jours (administration), les mêmes
    que les tuiles du carnet.
    """
    base = construire(aujourdhui)
    j = date.fromisoformat(base["aujourdhui"])
    c = base.get("compteurs") or compteurs(base["lignes"])
    urgentes = sum(1 for l in base["lignes"] if urgence(l, groupe_prepa(l), j))
    return {"present": base["present"], "urgentes": urgentes,
            "retard": c["retard"]["lignes"], "semaine": c["semaine"]["lignes"]}


def jour_ouvre_avant(j: date) -> date:
    """Le jour ouvré (lundi → vendredi) qui précède `j`."""
    j -= timedelta(days=1)
    while j.weekday() >= 5:
        j -= timedelta(days=1)
    return j


def jour_prepa(l: Dict[str, Any], aujourdhui: date) -> Tuple[Optional[str], str]:
    """Le jour où préparer la ligne, et d'où il vient.

    Fixé à la main par l'ADV (planning de prépa), sinon le jour ouvré qui
    précède le prochain enlèvement MyExpé, sinon celui qui précède
    l'expédition. Ce qui tombe avant aujourd'hui — retard, ou jour fixé
    dépassé — se fait aujourd'hui. Sans aucune date : None.
    """
    j = aujourdhui.isoformat()
    if l.get("jour_manuel"):
        return max(l["jour_manuel"], j), "manuel"
    enlev = sorted(d["date_enlevement"] for d in (l.get("departs") or [])
                   if d.get("date_enlevement") and not d.get("parti_le") and d["date_enlevement"] >= j)
    if enlev:
        base, source = enlev[0], "enlevement"
    elif l.get("expedition"):
        base, source = l["expedition"], "expedition"
    else:
        return None, "sans_date"
    return max(jour_ouvre_avant(date.fromisoformat(base)).isoformat(), j), source


def prepa(aujourdhui: Optional[date] = None, horizon: Optional[int] = None) -> Dict[str, Any]:
    """Les préparations à faire, dans l'ordre où les faire."""
    base = construire(aujourdhui)
    j = date.fromisoformat(base["aujourdhui"])
    h = ADV_PREPA_HORIZON_JOURS if horizon is None else max(1, min(int(horizon), 120))
    limite = (j + timedelta(days=h)).isoformat()
    lignes = []
    for l in base["lignes"]:
        g = groupe_prepa(l)
        if not g:
            continue
        # Ce qui est engagé, ou placé à la main par l'ADV, reste visible quelle
        # que soit la date ; le reste suit l'horizon.
        if (g not in ("en_cours", "pretes") and l["priorite_manuelle"] is None
                and not l["urgente_manuelle"] and not l.get("jour_manuel")
                and l["expedition"] and l["expedition"] > limite):
            continue
        l["groupe"] = g
        l["urgence"] = urgence(l, g, j)
        l["jour_prepa"], l["jour_source"] = jour_prepa(l, j)
        lignes.append(l)
    # L'ordre fixé par l'ADV d'abord, puis les lignes marquées urgentes, puis
    # la date d'expédition.
    lignes.sort(key=lambda l: (0 if l["priorite_manuelle"] is not None else 1,
                               l["priorite_manuelle"] or 0,
                               0 if l["urgente_manuelle"] else 1,
                               l["expedition"] or "9999-12-31", l["priorite"]))
    base["lignes"] = lignes
    base["horizon"] = h
    base["groupes"] = [{"cle": k, "label": v,
                        "lignes": sum(1 for l in lignes if l["groupe"] == k)}
                       for k, v in GROUPES_PREPA]
    base["compteurs"] = compteurs(lignes) if lignes else compteurs([])
    base["ordre_manuel"] = any(l["priorite_manuelle"] is not None for l in lignes)
    base["urgentes"] = sum(1 for l in lignes if l["urgence"])
    return base


HISTORIQUE_JOURS = (7, 30, 90)
MAX_HISTORIQUE = 500


def historique_prepa(jours: int = 30, aujourdhui: Optional[date] = None) -> Dict[str, Any]:
    """Les préparations déjà faites : passées « Prête » ces `jours` derniers jours.

    Une prépa prête quitte l'onglet Prépa dès que son départ est parti, ou que
    la ligne sort du carnet RVGI (livrée, soldée). L'historique la garde, avec
    ce qu'elle est devenue, pour qu'on puisse la retrouver et corriger son
    statut. `adv_prepas` ne garde que le dernier état d'une ligne : une prépa
    remise « à préparer » sort de l'historique et revient dans l'onglet.
    """
    base = construire(aujourdhui)
    jours = max(1, min(int(jours or 30), 366))
    j = date.fromisoformat(base["aujourdhui"])
    sortie: Dict[str, Any] = {"present": base["present"], "indispo": base["indispo"],
                              "aujourdhui": base["aujourdhui"], "jours": jours, "lignes": []}
    if not base["present"]:
        return sortie
    depuis = (j - timedelta(days=jours)).isoformat()
    carnet = {l["cle"]: l for l in base["lignes"]}
    with miroir.get_erp_db(avec_mysifa=True) as conn:
        if not _table(conn, "adv_prepas"):
            return sortie
        prepas = _lignes(conn, """
            SELECT numero, ligne, statut, maj_le, maj_par FROM mysifa.adv_prepas
             WHERE statut = 'prete' AND maj_le >= ?
          ORDER BY maj_le DESC LIMIT ?""", (depuis, MAX_HISTORIQUE))
        # Les lignes sorties du carnet : ce que le miroir en sait encore.
        hors = {}
        unites = {}
        for p in prepas:
            cle = cle_ligne(p["numero"], p["ligne"])
            if cle in carnet:
                continue
            try:
                num = int(str(p["numero"]).strip())
            except ValueError:
                continue
            r = _lignes(conn, """
                SELECT e.rs AS client, l.code1 AS code1, l.code2 AS code2,
                       l.des1 AS designation, l.qte AS qte, l.amje AS amje
                  FROM cde_ligne l LEFT JOIN cde_entete e ON e.numero = l.numero
                 WHERE l.numero = ? AND l.ligne = ? LIMIT 1""", (num, int(p["ligne"])))
            if r:
                r[0]["article"] = _reference(r[0]["code1"], r[0]["code2"])
                hors[cle] = r[0]
                unites[r[0]["article"]] = None
        if unites and _table(conn, "produits"):
            for r in _lignes(conn, "SELECT reference, unite FROM mysifa.produits"):
                ref = _ref_norm(r["reference"])
                if ref in unites and (unites[ref] is None or str(r["reference"]).strip() == ref):
                    unites[ref] = r["unite"]

    for p in prepas:
        cle = cle_ligne(p["numero"], p["ligne"])
        l = carnet.get(cle)
        if l:
            if groupe_prepa(l) == "pretes":
                dep = l["etapes"]["depart"]
                situation = ("attente_depart", "En attente de départ"
                             + (" · " + dep["detail"] if dep["calcul"] in ("oui", "en_cours") else ""))
            else:
                situation = ("parti", l["etapes"]["depart"]["detail"])
            info = {"client": l["client"], "article": l["article"], "designation": l["designation"],
                    "qte": l["qte"], "unite": l["stock"].get("unite"), "expedition": l["expedition"]}
        else:
            r = hors.get(cle) or {}
            situation = ("sortie", "Sortie du carnet RVGI (livrée ou soldée)")
            info = {"client": (r.get("client") or "").strip(), "article": r.get("article") or "",
                    "designation": (r.get("designation") or "").strip(), "qte": _f(r.get("qte")),
                    "unite": unites.get(r.get("article")), "expedition": _jour(r.get("amje"))}
        sortie["lignes"].append(dict(info, cle=cle, numero=str(p["numero"]), ligne=int(p["ligne"]),
                                     statut=p["statut"], prete_le=p["maj_le"], prete_par=p["maj_par"],
                                     situation=situation[0], situation_label=situation[1]))
    return sortie


def aujourdhui_paris() -> date:
    return datetime.now(_PARIS).date()


def maintenant() -> str:
    return datetime.now(_PARIS).strftime("%Y-%m-%dT%H:%M:%S")

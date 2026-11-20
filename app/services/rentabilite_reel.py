"""
SIFA — Le réel d'un dossier, rassemblé pour le moteur de rentabilité.

Un dossier se juge quand il est COMPLET : produit (89), matière déstockée,
facturé (arbitrage d'Eugène du 20/11/2026 — pas de temps réel, la rigueur
d'abord). Avant, la fiche se calcule quand même, marquée « provisoire », et
dit ce qui manque.

D'OÙ VIENT CHAQUE CHIFFRE

- Temps et métrage : `_reel_depuis_saisies` du router Rentabilité, qui appelle
  `dossier_stats` — le chiffre que lit MyProd. On ne recalcule rien ici.
- Matière et emballage : les mouvements MyStock du dossier (sorties moins
  retours ; une annulation est un mouvement inverse, elle se nette d'elle-même),
  valorisés comme la valorisation MyStock : une bobine vaut laize × mètres de la
  bobine × €/m², un adhésif se compte au kilo, mandrins et cartons à la palette.
  Prix en vigueur, pas prix historique à la date de sortie.
- Prix de vente : les lignes de facture RVGI dont `livno` porte le numéro de
  commande (99xxxxx) et l'article du créneau (`ref_produit`). Commande répartie
  sur plusieurs créneaux (L1, L2…) : la facture se partage au prorata des
  quantités produites.
- Transport : le prix retenu dans MyExpé quand le départ en a un ; sinon celui
  du devis, signalé « non mesuré ». Outil, encre, cliché : le devis.

Hors marché, l'excédent produit est de la gâche : sa matière et son temps
restent à la charge du dossier. Un marché facturé en plusieurs appels se juge
au prorata facturé (arbitrage du 20/11/2026), et reste « provisoire » tant que
des appels restent à facturer.
"""
import re
from typing import Optional

from app.services import devis_chiffrage, rentabilite_parametres
from app.services.devis_chiffrage import prix_m2_retenu
from app.services.rentabilite_calcul import (
    EntreesReelles, Fourchette, calcul_devis, calcul_reel, cascade_cout_horaire,
    cascade_marge, controler_devis, croiser_surfaces, redevise_laize, verdict,
)

RACINE_RE = re.compile(r"\b(99\d{5})\b")

# Postes du devis qui suivent la quantité quand on le ramène à un dossier.
_MONTANTS = ("prix_vente", "prix_revient", "surmarge", "remise", "marge_brute",
             "cout_matiere", "cout_encre", "cout_cliche", "cout_outil", "cout_emballage",
             "cout_production", "cout_conditionnement", "cout_manutention", "cout_transport")


def devis_ramene(valeurs: dict, k: float, calage_mn: float) -> dict:
    """Le devis ramené à la quantité d'un dossier (facteur k).

    Un même devis couvre souvent plusieurs lignes d'une commande (L1 à L5) :
    comparer UNE ligne au devis entier mettait 8,6 millions d'étiquettes
    devisées face à 1,7 million produites. Montants et métrage suivent la
    quantité ; le calage, lui, ne se divise pas. Approximation assumée : outil
    et transport suivent aussi, faute de savoir comment les répartir.
    """
    if k == 1.0:
        return dict(valeurs)
    v = dict(valeurs)
    for c in _MONTANTS:
        if v.get(c) is not None:
            v[c] = _f(v[c]) * k
    if v.get("metrage_total_ml") is not None:
        v["metrage_total_ml"] = _f(v["metrage_total_ml"]) * k
    if v.get("temps_total_mn") is not None:
        cal = min(_f(calage_mn), _f(v["temps_total_mn"]))
        v["temps_total_mn"] = cal + (_f(v["temps_total_mn"]) - cal) * k
    return v
MARCHE_RE = re.compile(r"march[ée]", re.IGNORECASE)

CATEGORIES_LAIZEES = ("frontal", "glassine", "complexe")
# La surface de référence se lit sur le support imprimé : frontal ou complexe.
CATEGORIES_SURFACE = ("frontal", "complexe")
CATEGORIES_MATIERE = ("frontal", "glassine", "complexe", "adhesif", "encre")
CATEGORIES_EMBALLAGE = ("mandrin", "carton", "palette")
CATEGORIES_A_LA_PALETTE = ("mandrin", "carton")


def _f(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _table(conn, nom: str) -> bool:
    return bool(conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nom,)
    ).fetchone())


# ══════════════════════════════════════════════════════════════════
# Dossier, devis, saisies
# ══════════════════════════════════════════════════════════════════

def dossiers_du_creneau(conn, entree) -> list[str]:
    """Les numéros de dossier dont les saisies appartiennent au créneau."""
    lies = [r[0] for r in conn.execute(
        "SELECT no_dossier FROM rent_prod_links WHERE planning_entry_id=? ORDER BY no_dossier",
        (entree["id"],),
    ).fetchall() if r[0]]
    if lies:
        return lies
    ref = str(entree["reference"] or "").strip()
    return [ref] if ref else []


# Une référence regroupe parfois plusieurs commandes, écrites en abrégé :
# « 9932574-75-77-78 », « 9932729/730/731 », « 9932756 +9932758 ». Chaque
# commande est facturée à part ; n'en lire qu'une donnait un prix de vente au
# quart du vrai (constaté le 20/11/2026 sur v1).
SUITE_RE = re.compile(r"(99\d{5})((?:\s*[-/]\s*\d{2,3}(?!\d))*)")


def racines_commande(entree, dossiers: list[str]) -> list[str]:
    """Tous les numéros de commande 99xxxxx portés par le créneau, abrégés compris."""
    vus: list[str] = []
    for txt in [entree["numero_of"], entree["reference"], *dossiers]:
        for m in SUITE_RE.finditer(str(txt or "")):
            base = m.group(1)
            if base not in vus:
                vus.append(base)
            for fin in re.findall(r"\d{2,3}", m.group(2) or ""):
                num = base[:len(base) - len(fin)] + fin
                if num not in vus:
                    vus.append(num)
    return vus


def racine_commande(entree, dossiers: list[str]) -> Optional[str]:
    r = racines_commande(entree, dossiers)
    return r[0] if r else None


def _article(ref_produit) -> tuple[Optional[str], Optional[str]]:
    """« 890/0112 » ou « 890-0112 » → (« 890 », « 0112 »)."""
    m = re.match(r"^\s*(\d+)\s*[/-]\s*(\d+)\s*$", str(ref_produit or ""))
    return (m.group(1), m.group(2)) if m else (None, None)


def _saisies(conn, dossiers: list[str]) -> dict:
    from app.routers.rentabilite import _reel_depuis_saisies
    return _reel_depuis_saisies(conn, dossiers)


def _fin_saisie(conn, dossiers: list[str]) -> bool:
    if not dossiers:
        return False
    ph = ",".join("?" * len(dossiers))
    return bool(conn.execute(
        f"""SELECT 1 FROM production_data
            WHERE no_dossier IN ({ph}) AND COALESCE(est_annule,0)=0
              AND (operation_code='89' OR COALESCE(fin_dossier,0)=1) LIMIT 1""",
        dossiers,
    ).fetchone())


# ══════════════════════════════════════════════════════════════════
# MyStock
# ══════════════════════════════════════════════════════════════════

def consommations_mystock(conn, entree_id: int, dossiers: list[str]) -> list[dict]:
    """Une ligne par matière × laize : quantité nette et valeur.

    Sorties moins entrées des mouvements du créneau ou de ses dossiers. Les
    annulations sont des mouvements inverses ; on prend aussi celles qui
    annulent une sortie du dossier sans en porter le numéro.
    """
    if not _table(conn, "mp_mouvements"):
        return []
    ph = ",".join("?" * len(dossiers)) if dossiers else "''"
    cible = f"(m.planning_entry_id = ? OR TRIM(COALESCE(m.no_dossier,'')) IN ({ph}))"
    rows = conn.execute(
        f"""SELECT m.matiere_id, m.laize_id,
                   SUM(CASE WHEN m.type_mouvement='sortie' THEN m.quantite
                            WHEN m.type_mouvement='entree' THEN -m.quantite ELSE 0 END) AS net,
                   mp.categorie, mp.reference, mp.designation,
                   COALESCE(mp.metres_lineaires_par_bobine,0) AS ml_bobine,
                   COALESCE(mp.prix_eur_m2,0) AS prix_m2,
                   COALESCE(mp.prix_par_laize,0) AS prix_par_laize,
                   mp.unites_par_palette,
                   COALESCE(v.prix_unitaire,0) AS prix_unitaire,
                   ml.prix_eur_m2 AS prix_m2_laize,
                   l.valeur_mm
              FROM mp_mouvements m
              JOIN matieres_premieres mp ON mp.id = m.matiere_id
              LEFT JOIN mp_valorisation v ON v.matiere_id = m.matiere_id
              LEFT JOIN mp_matiere_laizes ml ON ml.matiere_id = m.matiere_id AND ml.laize_id = m.laize_id
              LEFT JOIN mp_laizes l ON l.id = m.laize_id
             WHERE m.type_mouvement IN ('sortie','entree')
               AND ({cible}
                    OR m.annule_mouvement_id IN (
                        SELECT m2.id FROM mp_mouvements m2
                         WHERE m2.planning_entry_id = ? OR TRIM(COALESCE(m2.no_dossier,'')) IN ({ph})))
             GROUP BY m.matiere_id, m.laize_id""",
        [entree_id, *dossiers, entree_id, *dossiers],
    ).fetchall()

    lignes = []
    for r in rows:
        net = _f(r["net"])
        if abs(net) < 1e-9:
            continue
        cat = (r["categorie"] or "").lower()
        surface = None
        if cat in CATEGORIES_LAIZEES:
            laize = _f(r["valeur_mm"])
            prix = _f(r["prix_m2_laize"]) if (r["prix_par_laize"] and r["prix_m2_laize"] is not None) else _f(r["prix_m2"])
            surface = net * laize / 1000.0 * _f(r["ml_bobine"])
            valeur = surface * prix
            unite = "bobine"
        elif cat in CATEGORIES_A_LA_PALETTE:
            valeur = net * _f(r["prix_unitaire"]) * _f(r["unites_par_palette"])
            unite = "palette"
        else:
            valeur = net * _f(r["prix_unitaire"])
            unite = "kg" if cat == "adhesif" else "unité"
        lignes.append({
            "matiere_id": r["matiere_id"], "laize_mm": _f(r["valeur_mm"]) or None,
            "categorie": cat, "reference": r["reference"], "designation": r["designation"],
            "quantite": round(net, 6), "unite": unite,
            "surface_m2": round(surface, 2) if surface is not None else None,
            "valeur": round(valeur, 2),
            "sans_prix": valeur == 0,
        })
    return lignes


def _laize_et_surface(conso: list[dict]) -> tuple[Optional[float], Optional[float]]:
    """Laize réelle (pondérée par la surface) et surface du support."""
    supports = [c for c in conso if c["categorie"] in CATEGORIES_SURFACE and c["surface_m2"]]
    surface = sum(c["surface_m2"] for c in supports)
    if surface <= 0:
        return None, None
    laize = sum(c["laize_mm"] * c["surface_m2"] for c in supports if c["laize_mm"]) / surface
    return round(laize, 1), surface


# ══════════════════════════════════════════════════════════════════
# RVGI et MyExpé
# ══════════════════════════════════════════════════════════════════

def factures_rvgi(racines, ref_produit: Optional[str]) -> Optional[dict]:
    """Les lignes facturées de la commande. None si le miroir est absent.

    Filtrées sur l'article du créneau quand il est connu (`890/0112` →
    code1 = 890, code2 = 0112) : une commande peut porter plusieurs articles.
    `qte_ex` n'est sommée que sur les lignes facturées au mille (cuv = 11),
    les seules dont la quantité est en étiquettes.
    """
    if isinstance(racines, str):
        racines = [racines]
    racines = [r for r in (racines or []) if r]
    if not racines:
        return {"lignes": [], "montant": 0.0, "qte_ex": None, "par_article": False}
    from app.services import erp_mirror
    if not erp_mirror.miroir_present():
        return None
    code1, code2 = _article(ref_produit)
    with erp_mirror.get_erp_db() as erp:
        rows = erp.execute(
            f"""SELECT l.livno, l.numero, substr(e.amjf,1,10) AS date_facture, l.code1, l.code2,
                       l.des1, l.qte, l.pun, l.htn, l.cuv
                  FROM vte_ligne l
                  JOIN vte_entete e ON e.numero = l.numero AND e.corbeille = 0
                 WHERE l.corbeille = 0 AND l.livno IN ({",".join("?" * len(racines))})
                 ORDER BY e.amjf, l.ligne""",
            [int(r) for r in racines],
        ).fetchall()
    lignes = [dict(r) for r in rows]
    par_article = False
    if code1:
        article = [l for l in lignes if str(l["code1"]).strip() == code1
                   and str(l["code2"]).strip().lstrip("0") == code2.lstrip("0")]
        if article:
            lignes, par_article = article, True
    au_mille = [l for l in lignes if str(l.get("cuv") or "").strip() == "11"]
    return {
        "lignes": lignes,
        "montant": round(sum(_f(l["htn"]) for l in lignes), 2),
        "qte_ex": sum(_f(l["qte"]) for l in au_mille) if au_mille else None,
        # Facture isolée sur l'article du créneau : elle est déjà la sienne,
        # elle ne se partage pas avec les autres lignes de la commande.
        "par_article": par_article,
    }


def transport_myexpe(conn, entree_id: int, dossiers: list[str]) -> Optional[float]:
    """Prix retenu des départs du dossier, partagé entre les dossiers du départ.

    None quand aucun départ n'a de prix retenu : le transport n'est alors pas
    mesuré, et c'est le devis qui fait foi.
    """
    if not _table(conn, "expe_departs") or not _table(conn, "expe_devis_reponses"):
        return None
    ph = ",".join("?" * len(dossiers)) if dossiers else "''"
    rows = conn.execute(
        f"""SELECT d.id, r.prix,
                   (SELECT COUNT(*) FROM expe_depart_dossiers x WHERE x.depart_id = d.id) AS nb
              FROM expe_departs d
              JOIN expe_devis_reponses r ON r.id = d.source_devis_reponse_id
             WHERE r.prix > 0
               AND (d.planning_entry_id = ? OR TRIM(COALESCE(d.no_dossier,'')) IN ({ph})
                    OR d.id IN (SELECT depart_id FROM expe_depart_dossiers
                                 WHERE planning_entry_id = ? OR TRIM(COALESCE(no_dossier,'')) IN ({ph})))""",
        [entree_id, *dossiers, entree_id, *dossiers],
    ).fetchall()
    if not rows:
        return None
    return round(sum(_f(r["prix"]) / max(1, int(r["nb"] or 0)) for r in rows), 2)


def _part_de_commande(conn, entree, racine: Optional[str], qte_produite: float,
                      meme_article: bool = False) -> float:
    """Part de la facture qui revient à ce créneau quand la commande en a plusieurs.

    `meme_article` : la facture a été isolée sur l'article du créneau ; seuls
    les créneaux du MÊME article la partagent (L1 et L2 d'une même commande
    sont souvent deux articles, chacun sa ligne de facture)."""
    if not racine or qte_produite <= 0:
        return 1.0
    soeurs = conn.execute(
        """SELECT id, reference, numero_of, ref_produit FROM planning_entries
            WHERE id != ? AND (reference LIKE ? OR numero_of LIKE ?)
              AND COALESCE(statut,'') != 'annule'""",
        (entree["id"], f"%{racine}%", f"%{racine}%"),
    ).fetchall()
    if meme_article:
        art = _article(entree["ref_produit"])
        soeurs = [x for x in soeurs if _article(x["ref_produit"]) == art]
    if not soeurs:
        return 1.0
    # Un créneau scindé porte la même référence que son parent : mêmes
    # saisies, à ne compter qu'une fois.
    vus = {tuple(sorted(dossiers_du_creneau(conn, entree)))}
    total = qte_produite
    for s in soeurs:
        cle = tuple(sorted(dossiers_du_creneau(conn, s)))
        if not cle or cle in vus:
            continue
        vus.add(cle)
        total += _f(_saisies(conn, list(cle))["qte_etiquettes"])
    return qte_produite / total if total > 0 else 1.0


# ══════════════════════════════════════════════════════════════════
# Fiche
# ══════════════════════════════════════════════════════════════════

def fiche_rentabilite(conn, planning_entry_id: int, relire: bool = True) -> dict:
    """Tout ce que la fiche d'un dossier affiche. Lève LookupError si absent.

    `relire=False` : ne JAMAIS ouvrir le classeur d'un devis dont les montants
    n'ont pas été lus (le tableau de bord, qui juge des dizaines de dossiers
    d'un coup, les fait lire en arrière-plan à la place)."""
    entree = conn.execute(
        """SELECT e.*, m.nom AS machine_nom FROM planning_entries e
             LEFT JOIN machines m ON m.id = e.machine_id WHERE e.id=?""",
        (planning_entry_id,),
    ).fetchone()
    if not entree:
        raise LookupError("Créneau du planning introuvable.")
    lien = conn.execute(
        "SELECT devis_id FROM rent_links WHERE planning_entry_id=?", (planning_entry_id,)
    ).fetchone()
    devis = conn.execute("SELECT * FROM devis WHERE id=?", (lien["devis_id"],)).fetchone() \
        if lien and lien["devis_id"] else None

    tete = {
        "planning_entry_id": planning_entry_id,
        "reference": entree["reference"], "client": entree["client"],
        "machine": entree["machine_nom"], "statut": entree["statut"],
        "format": f"{_f(entree['format_l']):g} × {_f(entree['format_h']):g} mm"
                  if entree["format_l"] else "",
    }
    if not devis:
        return {**tete, "etat": "sans_devis", "message": "Aucun devis rattaché à ce dossier."}

    ch = devis_chiffrage.chiffrage_du_devis(conn, devis["id"])
    if ch is None and relire and devis_chiffrage.relire_depuis_fichier(conn, devis["id"]) is not None:
        conn.commit()
        ch = devis_chiffrage.chiffrage_du_devis(conn, devis["id"])
    tete["devis"] = {"id": devis["id"], "fichier": devis["filename"], "date": devis["date_devis"]}
    if ch is None or ch["valeurs"].get("prix_vente") is None:
        return {**tete, "etat": "sans_chiffrage", "devis_id": devis["id"],
                "message": "Les montants du devis ne sont pas lus — relire le devis depuis l'onglet Devis."}

    params = rentabilite_parametres.lire(conn)
    v = ch["valeurs"]
    laize_d = _f(devis["laize"]) or None
    calc_d = calcul_devis(v)
    alertes: list[dict] = []

    # ── Saisies ───────────────────────────────────────────────────
    dossiers = dossiers_du_creneau(conn, entree)
    s = _saisies(conn, dossiers)
    calage, prod = _f(s["temps_calage_mn"]), _f(s["temps_production_mn"])
    # La durée qui compte pour le coût horaire est l'OCCUPATION de la machine
    # (sessions 01 → 89) : un nettoyage du four à colle ou une pause dans le
    # dossier immobilisent la machine autant qu'un arrêt. Tout ce qui n'est ni
    # calage ni production est rangé avec les arrêts.
    duree = max(_f(s.get("duree_totale_mn")), calage + prod + _f(s["temps_arret_mn"])
                + _f(s.get("temps_nettoyage_mn")))
    arret = max(0.0, duree - calage - prod)
    metrage, qte_prod = _f(s["metrage_ml"]), _f(s["qte_etiquettes"])
    produit = (entree["statut"] == "termine") or _fin_saisie(conn, dossiers)

    # ── Matière ───────────────────────────────────────────────────
    conso = consommations_mystock(conn, planning_entry_id, dossiers)
    laize_r, surface_stock = _laize_et_surface(conso)
    matiere_eur = sum(c["valeur"] for c in conso if c["categorie"] in CATEGORIES_MATIERE)
    emballage_eur = sum(c["valeur"] for c in conso if c["categorie"] in CATEGORIES_EMBALLAGE)
    destocke = (str(entree["destockage"] or "") == "done") or bool(conso)
    if any(c["sans_prix"] for c in conso):
        alertes.append({"niveau": "avertissement",
                        "message": "Une matière déstockée n'a pas de prix dans MyStock : son coût compte pour zéro."})

    laize_ref = laize_r or laize_d or _f(entree["laize"]) or None
    surf_compteur = Fourchette.relative(metrage * laize_ref / 1000.0, params["fourchette_metrage_pct"]) \
        if (metrage > 0 and laize_ref) else None
    surf_stock = Fourchette.relative(surface_stock, params["fourchette_matiere_pct"]) if surface_stock else None
    surface, croisement, ecart = croiser_surfaces(surf_compteur, surf_stock, params["ecart_croisement_pct"])
    if croisement == "incoherent":
        alertes.append({"niveau": "avertissement",
                        "message": f"Compteur et MyStock s'écartent de {_pct(ecart)} sur la surface consommée : "
                                   "erreur de saisie probable. La fourchette retenue couvre les deux."})

    if surface_stock and matiere_eur > 0:
        prix_m2_r = matiere_eur / surface_stock
        source_matiere = "MyStock"
    else:
        prix_m2_r = prix_m2_retenu(v) or 0.0
        source_matiere = "estimé : compteur × prix du devis"
        if surface is not None:
            alertes.append({"niveau": "info",
                            "message": "Matière pas encore déstockée : coût estimé au métrage compteur et au prix du devis."})
    if surface is None:
        return {**tete, "etat": "sans_mesure", "dossiers": dossiers,
                "message": "Ni métrage compteur ni déstockage MyStock : rien à mesurer pour l'instant."}

    # ── Prix de vente ─────────────────────────────────────────────
    racines = racines_commande(entree, dossiers)
    racine = racines[0] if racines else None
    marche = bool(MARCHE_RE.search(str(entree["reference"] or "")))
    fact = factures_rvgi(racines, entree["ref_produit"])
    part = _part_de_commande(conn, entree, racine, qte_prod,
                             meme_article=bool(fact and fact.get("par_article")))
    qte_devis = _f(devis["qte_etiquettes"])
    facture = bool(fact and fact["montant"] > 0)
    prorata = 1.0
    if facture:
        pv = fact["montant"] * part
        source_pv = "facture RVGI" + (f" · {part * 100:.0f} % de la commande" if part < 0.999 else "")
        if marche and fact["qte_ex"] and qte_prod > 0:
            prorata = min(1.0, fact["qte_ex"] * part / qte_prod)
    else:
        base = min(qte_prod, qte_devis) if qte_devis else qte_prod
        pv = _f(v["prix_vente"]) / qte_devis * base if qte_devis else _f(v["prix_vente"])
        source_pv = "estimé : prix du devis × quantité produite"
        if fact is None:
            alertes.append({"niveau": "info", "message": "Miroir RVGI absent : prix de vente estimé depuis le devis."})

    # ── Devis ramené à la quantité du dossier ─────────────────────
    calage_d = _f(devis["temps_calage_mn"]) + _f(devis["temps_calage_impression_mn"])
    k = (qte_prod / qte_devis) if (qte_devis > 0 and qte_prod > 0) else 1.0
    if 0.9 <= k <= 1.1:
        k = 1.0
    vr = devis_ramene(v, k, calage_d)
    if k != 1.0:
        alertes.append({"niveau": "info",
                        "message": f"Devis chiffré pour {_milliers(qte_devis)} ex, dossier de "
                                   f"{_milliers(qte_prod)} ex : montants du devis ramenés à cette quantité."})

    # ── Postes annexes ────────────────────────────────────────────
    transport = transport_myexpe(conn, planning_entry_id, dossiers)
    annexes = {
        "outil": Fourchette.exacte(_f(v.get("cout_outil"))),
        "encre": Fourchette.exacte(_f(v.get("cout_encre"))),
        "cliche": Fourchette.exacte(_f(v.get("cout_cliche"))),
        "emballage": Fourchette.exacte(emballage_eur if emballage_eur > 0 else _f(v.get("cout_emballage"))),
        "transport": Fourchette.exacte(transport if transport is not None else _f(v.get("cout_transport"))),
    }

    entrees = EntreesReelles(
        prix_vente=pv, surface_m2=surface, prix_m2=prix_m2_r, couts_annexes=annexes,
        duree_mn=Fourchette.relative(duree, params["fourchette_duree_pct"]),
        calage_mn=calage, production_mn=prod, arret_mn=arret,
        frontiere_mn=params["fourchette_frontiere_mn"], prorata=prorata,
    )
    reel = calcul_reel(entrees) if duree > 0 else None
    if reel is None:
        alertes.append({"niveau": "avertissement", "message": "Aucun temps saisi : coût horaire non calculable."})
    seuils = {"mb_pct": params["seuil_mb_pct"], "cout_horaire": params["seuil_cout_horaire"]}
    vd = verdict(reel["mb_pct"] if reel else None, reel["cout_horaire"] if reel else None,
                 seuils["mb_pct"], seuils["cout_horaire"])
    vd_devis = verdict(
        {"bas": calc_d["mb_pct"], "probable": calc_d["mb_pct"], "haut": calc_d["mb_pct"]} if calc_d["mb_pct"] is not None else None,
        {"bas": calc_d["cout_horaire"], "probable": calc_d["cout_horaire"], "haut": calc_d["cout_horaire"]} if calc_d["cout_horaire"] is not None else None,
        seuils["mb_pct"], seuils["cout_horaire"])

    manque = [m for m, ok in (("production terminée", produit), ("matière déstockée", destocke),
                              ("facture", facture)) if not ok]
    provisoire = bool(manque) or prorata < 0.999
    if marche and prorata < 0.999:
        alertes.append({"niveau": "info",
                        "message": f"Marché facturé en plusieurs appels : {prorata * 100:.0f} % facturé, verdict provisoire."})
    if not marche and fact and fact["qte_ex"] and qte_prod > fact["qte_ex"] * part * 1.02:
        alertes.append({"niveau": "info",
                        "message": "Production supérieure à la quantité facturée : l'excédent est compté en gâche."})

    cascade_mb = cascade_marge(vr, laize_d or laize_ref, entrees, laize_ref) if reel else []
    cascade_eh = cascade_cout_horaire(vr, calage_d, entrees) if reel else []
    pv_redevise = redevise_laize(vr, laize_d, laize_r) if (laize_d and laize_r and abs(laize_r - laize_d) > 0.5) else None

    # Un résultat hors norme dit un rattachement faux, pas une rentabilité.
    import config
    hors_norme = []
    if reel and reel.get("mb_pct"):
        p = reel["mb_pct"]["probable"]
        if p < config.RENT_PLAUSIBLE_MB_MIN or p > config.RENT_PLAUSIBLE_MB_MAX:
            hors_norme.append(f"marge brute de {_pct(p)}")
    if reel and reel.get("cout_horaire") and reel["cout_horaire"]["probable"] > config.RENT_PLAUSIBLE_COUT_HORAIRE_MAX:
        hors_norme.append(f"coût horaire de {_milliers(reel['cout_horaire']['probable'])} €/h")
    if hors_norme:
        alertes.insert(0, {"niveau": "avertissement",
                           "message": "Résultat hors norme (" + ", ".join(hors_norme) + ") : vérifier la facture "
                                      "et la matière rattachées à ce dossier."})

    # Un dossier n'est COMPLET que si l'on est sûr de son résultat : aucun
    # avertissement (compteur et MyStock qui divergent, matière sans prix,
    # temps absent, résultat hors norme). Sinon il est « à vérifier » : listé,
    # jamais compté ni placé sur le nuage. Un provisoire reste provisoire,
    # il n'est de toute façon pas encore jugé.
    raisons = [a["message"] for a in alertes if a.get("niveau") == "avertissement"]
    if hors_norme:
        etat = "a_verifier"
    elif provisoire:
        etat = "provisoire"
    elif raisons:
        etat = "a_verifier"
    else:
        etat = "complet"

    lignes = [
        _ligne("Laize", laize_d, laize_r, "mm", "exacte", "bobines sorties MyStock" if laize_r else "non mesurée"),
        _ligne("Prix matière", prix_m2_retenu(v), prix_m2_r, "€/m²", "exact", source_matiere, 4),
        _ligne("Métrage", _f(vr.get("metrage_total_ml")), metrage, "ml",
               f"± {params['fourchette_metrage_pct']:g} %", "compteur machine"),
        _ligne("Surface consommée", (_f(vr.get("metrage_total_ml")) * laize_d / 1000.0) if laize_d else None,
               surface.probable, "m²", f"{surface.bas:,.0f} – {surface.haut:,.0f}".replace(",", " "),
               {"coherent": f"compteur et MyStock à {_pct(ecart)}", "incoherent": f"écart compteur / MyStock {_pct(ecart)}",
                "compteur_seul": "compteur seul", "mystock_seul": "MyStock seul"}.get(croisement, "")),
        _ligne("Coût matière", _f(vr.get("cout_matiere")), surface.probable * prix_m2_r, "€",
               f"{surface.bas * prix_m2_r:,.0f} – {surface.haut * prix_m2_r:,.0f}".replace(",", " "), source_matiere),
        _ligne("Durée totale", _f(vr.get("temps_total_mn")), duree, "mn",
               f"± {params['fourchette_duree_pct']:g} %", "saisies MyProd"),
        _ligne("dont calage", calage_d, calage, "mn", f"± {params['fourchette_frontiere_mn']:g} mn",
               "passage calage → production incertain"),
        _ligne("dont production", _f(vr.get("temps_total_mn")) - calage_d, prod, "mn",
               f"± {params['fourchette_frontiere_mn']:g} mn", "passage calage → production incertain"),
        _ligne("dont arrêts, nettoyage, autres", None, arret, "mn", "", "saisies MyProd"),
        _ligne("Quantité", qte_devis, qte_prod, "ex", "", "saisies MyProd"),
        _ligne("Prix de vente", _f(vr.get("prix_vente")), pv, "€", "exact", source_pv),
        _ligne("Emballage", _f(vr.get("cout_emballage")), annexes["emballage"].probable, "€", "exact",
               "sorties MyStock" if emballage_eur > 0 else "repris du devis · non mesuré"),
        _ligne("Transport", _f(vr.get("cout_transport")), annexes["transport"].probable, "€", "exact",
               "prix retenu MyExpé" if transport is not None else "repris du devis · non mesuré"),
        _ligne("Outil, encre, cliché", sum(_f(vr.get(c)) for c in ("cout_outil", "cout_encre", "cout_cliche")),
               sum(annexes[k].probable for k in ("outil", "encre", "cliche")), "€", "exact",
               "repris du devis · non mesuré"),
    ]

    return {
        **tete,
        "etat": etat,
        "hors_norme": hors_norme,
        "raisons": raisons,
        "ramene": round(k, 4),
        "manque": manque,
        "marche": marche,
        "dossiers": dossiers,
        "racine": racine,
        "racines": racines,
        "seuils": seuils,
        "devis_calcul": calc_d,
        "devis_verdict": vd_devis,
        "controle_devis_ok": _controle_ok(controler_devis(v, laize_d, params["tolerance_controle_pct"])),
        "reel": reel,
        "verdict": vd,
        "cascade_marge": cascade_mb,
        "cascade_cout_horaire": cascade_eh,
        "redevise": {"prix_vente": round(pv_redevise, 2),
                     "non_refacture": round(pv_redevise - _f(vr["prix_vente"]), 2)} if pv_redevise else None,
        "parametres": lignes,
        "consommations": conso,
        "factures": (fact or {}).get("lignes", []),
        "alertes": alertes,
    }


def _milliers(n) -> str:
    try:
        return f"{float(n):,.0f}".replace(",", " ")
    except (TypeError, ValueError):
        return str(n)


def _pct(v) -> str:
    """18.74 → « 18,7 % »."""
    return f"{float(v or 0):.1f}".replace(".", ",") + " %"


def _controle_ok(controles: list[dict]) -> Optional[bool]:
    return all(c["ok"] for c in controles) if controles else None


def _ligne(nom, devis, reel, unite, fourchette, source, decimales=0) -> dict:
    modifie = (devis is not None and reel is not None and devis != 0
               and abs(float(reel) - float(devis)) / abs(float(devis)) > 0.02
               and nom in ("Laize", "Prix matière", "Transport"))
    return {
        "parametre": nom, "unite": unite,
        "devis": round(float(devis), decimales) if devis is not None else None,
        "reel": round(float(reel), decimales) if reel is not None else None,
        "fourchette": fourchette, "source": source, "modifie": modifie,
    }


# ══════════════════════════════════════════════════════════════════
# Tableau de bord
# ══════════════════════════════════════════════════════════════════

PERIODES = ("ouvres7", "last30", "last90", "thisYear", "all")
PERIODE_DEFAUT = "ouvres7"
JOURS_OUVRES_RECENTS = 7


def jour_ouvre(d, machines, off, explicite, samedis) -> bool:
    """L'usine est ouverte ce jour-là si AU MOINS UNE machine tourne.

    Mêmes règles que le planning (`list_day_work`) et que la normalisation
    des besoins matières : dimanche fermé ; samedi ouvert seulement sur
    exception explicite ou `planning_config.samedi_travaille` ; lundi à
    vendredi ouverts sauf jour off (`planning_holidays`) ou exception à 0.
    """
    cle = d.isoformat()
    ex = explicite.get(cle, {})
    if d.weekday() == 6:
        return False
    if d.weekday() == 5:
        an, sem, _ = d.isocalendar()
        cfg = samedis.get(f"{an}-W{sem:02d}", set())
        return any(ex.get(m, 1 if m in cfg else 0) == 1 and m not in off.get(cle, ()) for m in machines)
    return any(ex.get(m, 1) == 1 and m not in off.get(cle, ()) for m in machines)


def debut_jours_ouvres(conn, n: int, aujourd_hui=None):
    """Premier jour de la fenêtre des `n` derniers jours ouvrés, aujourd'hui compris.

    Calendrier lu dans le planning (jours off, exceptions, samedis travaillés).
    Sur une base sans machine ni calendrier, les jours de semaine comptent.
    """
    from datetime import date, timedelta
    j = aujourd_hui or date.today()
    plancher = j - timedelta(days=n * 3 + 21)
    machines, off, explicite, samedis = [0], {}, {}, {}
    try:
        ids = [int(r[0]) for r in conn.execute("SELECT id FROM machines").fetchall()]
        if ids:
            machines = ids
        for r in conn.execute("SELECT machine_id, date FROM planning_holidays "
                              "WHERE COALESCE(is_off,1)=1 AND date BETWEEN ? AND ?",
                              (plancher.isoformat(), j.isoformat())).fetchall():
            off.setdefault(str(r[1])[:10], set()).add(int(r[0]))
        for r in conn.execute("SELECT machine_id, date, is_worked FROM planning_day_worked "
                              "WHERE date BETWEEN ? AND ?", (plancher.isoformat(), j.isoformat())).fetchall():
            explicite.setdefault(str(r[1])[:10], {})[int(r[0])] = int(r[2] or 0)
        for r in conn.execute("SELECT machine_id, semaine, samedi_travaille FROM planning_config").fetchall():
            if int(r[2] or 0) == 1:
                samedis.setdefault(str(r[1]), set()).add(int(r[0]))
    except Exception:
        pass
    d, vus = j, 0
    while d >= plancher:
        if jour_ouvre(d, machines, off, explicite, samedis):
            vus += 1
            if vus >= n:
                return d
        d -= timedelta(days=1)
    return plancher


def bornes_periode(periode: str, aujourd_hui=None, conn=None) -> tuple[Optional[str], Optional[str]]:
    """`(du, au)` en AAAA-MM-JJ ; `(None, None)` pour « tout »."""
    from datetime import date, timedelta
    j = aujourd_hui or date.today()
    if periode == "ouvres7":
        if conn is None:
            return (j - timedelta(days=9)).isoformat(), j.isoformat()
        return debut_jours_ouvres(conn, JOURS_OUVRES_RECENTS, j).isoformat(), j.isoformat()
    if periode == "last90":
        return (j - timedelta(days=89)).isoformat(), j.isoformat()
    if periode == "thisYear":
        return date(j.year, 1, 1).isoformat(), j.isoformat()
    if periode == "all":
        return None, None
    return (j - timedelta(days=29)).isoformat(), j.isoformat()


def resume_fiche(f: dict, date_fin: Optional[str] = None) -> dict:
    """Ce qu'une ligne du tableau de bord garde d'une fiche.

    `date_fin` (AAAA-MM-JJ) range le dossier dans la vue temporelle ; `heures`
    et `marge_brute` servent aux moyennes PONDÉRÉES d'une période (Σ MB ÷ Σ PV,
    Σ MB ÷ Σ heures) : une moyenne de pourcentages donnerait au dossier de
    2 000 € le même poids qu'à celui de 80 000 €.
    """
    reel = f.get("reel") or {}
    d = f.get("devis_calcul") or {}
    return {
        "planning_entry_id": f.get("planning_entry_id"),
        "date": (date_fin or "")[:10] or None,
        "heures": (reel.get("heures") or {}).get("probable"),
        "reference": f.get("reference"), "client": f.get("client"),
        "machine": f.get("machine"), "format": f.get("format"),
        "etat": f.get("etat"), "manque": f.get("manque") or [],
        "verdict": f.get("verdict") or {},
        "mb_pct": reel.get("mb_pct"), "cout_horaire": reel.get("cout_horaire"),
        "marge_brute": (reel.get("marge_brute") or {}).get("probable"),
        "prix_vente": reel.get("prix_vente"),
        "devis_mb_pct": d.get("mb_pct"), "devis_cout_horaire": d.get("cout_horaire"),
        "devis_prix_vente": d.get("prix_vente"),
        "modifies": [l["parametre"] for l in (f.get("parametres") or []) if l.get("modifie")],
        "cascade_marge": f.get("cascade_marge") or [],
        "cascade_cout_horaire": f.get("cascade_cout_horaire") or [],
        "alertes": len(f.get("alertes") or []),
        "hors_norme": f.get("hors_norme") or [],
        "raisons": f.get("raisons") or [],
    }


def _mediane(v: list[float]) -> Optional[float]:
    if not v:
        return None
    k = len(v) // 2
    return v[k] if len(v) % 2 else (v[k - 1] + v[k]) / 2


def _causes(lignes: list[dict], cle: str, en_points: bool) -> list[dict]:
    """Moyenne par cause des marches de cascade, sur les dossiers retenus.

    En points de marge pour la MB (marche ÷ PV devisé), en €/h pour le coût
    horaire. Un dossier sans une cause compte zéro pour elle : c'est une
    moyenne PAR DOSSIER, comparable d'une période à l'autre.
    """
    if not lignes:
        return []
    cumul: dict[str, float] = {}
    nature: dict[str, str] = {}
    for l in lignes:
        pv = _f(l.get("devis_prix_vente"))
        for e in l.get(cle) or []:
            if e.get("nature") == "total":
                continue
            v = _f(e.get("valeur"))
            if en_points:
                if not pv:
                    continue
                v = v / pv * 100.0
            cumul[e["cause"]] = cumul.get(e["cause"], 0.0) + v
            nature[e["cause"]] = e.get("nature")
    n = len(lignes)
    return sorted(({"cause": c, "nature": nature[c], "valeur": round(v / n, 2)}
                   for c, v in cumul.items()), key=lambda x: x["valeur"])


# ── Cache et lecture en arrière-plan ─────────────────────────────
# Juger un dossier, c'est relire ses saisies, ses mouvements MyStock et sa
# facture : quelques dizaines de millisecondes, mais multipliées par cent
# dossiers à chaque ouverture de l'onglet. Le résumé d'une fiche est gardé
# CACHE_SECONDES ; « Recalculer » (force) repart de zéro.
import threading
import time

CACHE_SECONDES = 600
_cache_fiches: dict[int, tuple[float, Optional[dict]]] = {}
_verrou_lecture = threading.Lock()
_lecture = {"en_cours": False, "restants": 0}


def vider_cache() -> None:
    _cache_fiches.clear()


def _relire_en_fond(devis_ids: list[int]) -> None:
    """Lit les montants des devis qui ne l'ont jamais été, sans bloquer l'écran.

    Un seul fil à la fois : un second appel pendant la lecture ne relance
    rien. Chaque devis est commité à part, et le cache est vidé à la fin pour
    que le tableau de bord suivant voie les nouveaux montants.
    """
    if not devis_ids or not _verrou_lecture.acquire(blocking=False):
        return
    _lecture.update(en_cours=True, restants=len(devis_ids))

    def travail():
        from database import get_db
        try:
            for i, did in enumerate(devis_ids):
                try:
                    with get_db() as c:
                        devis_chiffrage.relire_depuis_fichier(c, did)
                        c.commit()
                except Exception:
                    pass
                _lecture["restants"] = len(devis_ids) - i - 1
        finally:
            vider_cache()
            _lecture.update(en_cours=False, restants=0)
            _verrou_lecture.release()

    threading.Thread(target=travail, name="rentabilite-relecture-devis", daemon=True).start()


def tableau_de_bord(conn, periode: str = PERIODE_DEFAUT, machine: str = "", force: bool = False) -> dict:
    """Les dossiers terminés et rattachés à un devis validé, jugés un par un.

    Les compteurs, l'écart moyen et les causes ne portent que sur les dossiers
    COMPLETS (produits, déstockés, facturés) ; les autres sont listés « en
    attente » avec ce qui leur manque. Machines retirées du suivi des devis
    exclues, comme dans le Pilotage.
    """
    if periode not in PERIODES:
        periode = PERIODE_DEFAUT
    du, au = bornes_periode(periode, conn=conn)
    params = rentabilite_parametres.lire(conn)
    sql = """SELECT e.id, m.nom AS machine,
                    substr(COALESCE(e.planned_end, e.updated_at), 1, 10) AS date_fin
               FROM planning_entries e
               JOIN rent_links l ON l.planning_entry_id = e.id AND l.devis_id IS NOT NULL
               LEFT JOIN machines m ON m.id = e.machine_id
              WHERE e.statut = 'termine'
                AND NOT (COALESCE(l.origine, 'manuel') = 'auto' AND l.valide_at IS NULL)
                AND COALESCE(m.rent_suivi_devis, 1) != 0"""
    args: list = []
    if du:
        sql += " AND substr(COALESCE(e.planned_end, e.updated_at), 1, 10) BETWEEN ? AND ?"
        args += [du, au]
    lignes_sql = conn.execute(sql + " ORDER BY COALESCE(e.planned_end, e.updated_at) DESC", args).fetchall()
    machines = sorted({r["machine"] for r in lignes_sql if r["machine"]})

    if force:
        vider_cache()
    maintenant = time.time()
    lignes, erreurs, a_lire = [], 0, []
    for r in lignes_sql:
        if machine and r["machine"] != machine:
            continue
        eid = int(r["id"])
        en_cache = _cache_fiches.get(eid)
        if en_cache and maintenant - en_cache[0] < CACHE_SECONDES:
            resume = en_cache[1]
        else:
            try:
                f = fiche_rentabilite(conn, eid, relire=False)
            except Exception:
                erreurs += 1
                continue
            if f.get("etat") == "sans_chiffrage" and f.get("devis_id"):
                a_lire.append(int(f["devis_id"]))
            resume = None if f.get("etat") == "sans_devis" else resume_fiche(f, r["date_fin"])
            # Une fiche en attente de lecture ne se met pas en cache : elle
            # doit réapparaître dès que ses montants sont lus.
            if f.get("etat") != "sans_chiffrage":
                _cache_fiches[eid] = (maintenant, resume)
        if resume:
            lignes.append(resume)
    if a_lire:
        _relire_en_fond(sorted(set(a_lire)))

    complets = [l for l in lignes if l["etat"] == "complet" and l["mb_pct"] and l["cout_horaire"]]
    comptes = {"reussi": 0, "limite": 0, "sous_seuil": 0}
    for l in complets:
        g = (l["verdict"] or {}).get("global")
        if g in comptes:
            comptes[g] += 1
    ecarts = [l["mb_pct"]["probable"] - l["devis_mb_pct"] for l in complets if l["devis_mb_pct"] is not None]
    # Marge de la période PONDÉRÉE (Σ MB ÷ Σ PV) : le dossier de 80 000 € pèse
    # plus que celui de 2 000 €. Le devisé se pondère de la même façon.
    pv_tot = sum(_f(l.get("prix_vente")) for l in complets)
    mb_tot = sum(_f(l.get("marge_brute")) for l in complets)
    avec_devis = [l for l in complets if l["devis_mb_pct"] is not None and _f(l.get("devis_prix_vente")) > 0]
    pv_dv = sum(_f(l["devis_prix_vente"]) for l in avec_devis)
    mb_dv = sum(_f(l["devis_mb_pct"]) * _f(l["devis_prix_vente"]) / 100.0 for l in avec_devis)
    ehs_dv = sorted(_f(l["devis_cout_horaire"]) for l in complets if l.get("devis_cout_horaire") is not None)
    ehs = sorted(l["cout_horaire"]["probable"] for l in complets)
    mediane = None
    if ehs:
        k = len(ehs) // 2
        mediane = ehs[k] if len(ehs) % 2 else (ehs[k - 1] + ehs[k]) / 2
    return {
        "periode": periode, "du": du, "au": au, "machine": machine or None,
        "machines": machines,
        "seuils": {"mb_pct": params["seuil_mb_pct"], "cout_horaire": params["seuil_cout_horaire"]},
        "comptes": {**comptes, "complets": len(complets),
                    "attente": sum(1 for l in lignes if l["etat"] == "provisoire"),
                    "a_verifier": sum(1 for l in lignes if l["etat"] == "a_verifier"),
                    "non_calculables": sum(1 for l in lignes if l["etat"] not in
                                           ("complet", "provisoire", "a_verifier")),
                    "erreurs": erreurs},
        "ecart_mb_pts": round(sum(ecarts) / len(ecarts), 2) if ecarts else None,
        "cout_horaire_median": round(mediane, 1) if mediane is not None else None,
        "mb_pct_pondere": round(mb_tot / pv_tot * 100.0, 2) if pv_tot > 0 else None,
        "devis_mb_pct_pondere": round(mb_dv / pv_dv * 100.0, 2) if pv_dv > 0 else None,
        "devis_cout_horaire_median": round(_mediane(ehs_dv), 1) if ehs_dv else None,
        "causes_marge": _causes(complets, "cascade_marge", True),
        "causes_cout_horaire": _causes(complets, "cascade_cout_horaire", False),
        "dossiers": lignes,
        "lecture_devis": {"en_cours": _lecture["en_cours"] or bool(a_lire),
                          "restants": _lecture["restants"] or len(set(a_lire))},
    }

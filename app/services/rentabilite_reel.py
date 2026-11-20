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


def racine_commande(entree, dossiers: list[str]) -> Optional[str]:
    for txt in [entree["numero_of"], entree["reference"], *dossiers]:
        m = RACINE_RE.search(str(txt or ""))
        if m:
            return m.group(1)
    return None


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

def factures_rvgi(racine: Optional[str], ref_produit: Optional[str]) -> Optional[dict]:
    """Les lignes facturées de la commande. None si le miroir est absent.

    Filtrées sur l'article du créneau quand il est connu (`890/0112` →
    code1 = 890, code2 = 0112) : une commande peut porter plusieurs articles.
    `qte_ex` n'est sommée que sur les lignes facturées au mille (cuv = 11),
    les seules dont la quantité est en étiquettes.
    """
    if not racine:
        return {"lignes": [], "montant": 0.0, "qte_ex": None}
    from app.services import erp_mirror
    if not erp_mirror.miroir_present():
        return None
    code1 = code2 = None
    if ref_produit and "/" in str(ref_produit):
        code1, code2 = [s.strip() for s in str(ref_produit).split("/", 1)]
    with erp_mirror.get_erp_db() as erp:
        rows = erp.execute(
            """SELECT l.numero, substr(e.amjf,1,10) AS date_facture, l.code1, l.code2,
                      l.des1, l.qte, l.pun, l.htn, l.cuv
                 FROM vte_ligne l
                 JOIN vte_entete e ON e.numero = l.numero AND e.corbeille = 0
                WHERE l.corbeille = 0 AND l.livno = ?
                ORDER BY e.amjf, l.ligne""",
            (int(racine),),
        ).fetchall()
    lignes = [dict(r) for r in rows]
    if code1:
        article = [l for l in lignes if str(l["code1"]).strip() == code1
                   and str(l["code2"]).strip() == code2]
        if article:
            lignes = article
    au_mille = [l for l in lignes if str(l.get("cuv") or "").strip() == "11"]
    return {
        "lignes": lignes,
        "montant": round(sum(_f(l["htn"]) for l in lignes), 2),
        "qte_ex": sum(_f(l["qte"]) for l in au_mille) if au_mille else None,
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


def _part_de_commande(conn, entree, racine: Optional[str], qte_produite: float) -> float:
    """Part de la facture qui revient à ce créneau quand la commande en a plusieurs."""
    if not racine or qte_produite <= 0:
        return 1.0
    soeurs = conn.execute(
        """SELECT id, reference, numero_of FROM planning_entries
            WHERE id != ? AND (reference LIKE ? OR numero_of LIKE ?)
              AND COALESCE(statut,'') != 'annule'""",
        (entree["id"], f"%{racine}%", f"%{racine}%"),
    ).fetchall()
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

def fiche_rentabilite(conn, planning_entry_id: int) -> dict:
    """Tout ce que la fiche d'un dossier affiche. Lève LookupError si absent."""
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
    if ch is None and devis_chiffrage.relire_depuis_fichier(conn, devis["id"]) is not None:
        conn.commit()
        ch = devis_chiffrage.chiffrage_du_devis(conn, devis["id"])
    tete["devis"] = {"id": devis["id"], "fichier": devis["filename"], "date": devis["date_devis"]}
    if ch is None or ch["valeurs"].get("prix_vente") is None:
        return {**tete, "etat": "sans_chiffrage",
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
    racine = racine_commande(entree, dossiers)
    marche = bool(MARCHE_RE.search(str(entree["reference"] or "")))
    fact = factures_rvgi(racine, entree["ref_produit"])
    part = _part_de_commande(conn, entree, racine, qte_prod)
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

    calage_d = _f(devis["temps_calage_mn"]) + _f(devis["temps_calage_impression_mn"])
    cascade_mb = cascade_marge(v, laize_d or laize_ref, entrees, laize_ref) if reel else []
    cascade_eh = cascade_cout_horaire(v, calage_d, entrees) if reel else []
    pv_redevise = redevise_laize(v, laize_d, laize_r) if (laize_d and laize_r and abs(laize_r - laize_d) > 0.5) else None

    lignes = [
        _ligne("Laize", laize_d, laize_r, "mm", "exacte", "bobines sorties MyStock" if laize_r else "non mesurée"),
        _ligne("Prix matière", prix_m2_retenu(v), prix_m2_r, "€/m²", "exact", source_matiere, 4),
        _ligne("Métrage", _f(v.get("metrage_total_ml")), metrage, "ml",
               f"± {params['fourchette_metrage_pct']:g} %", "compteur machine"),
        _ligne("Surface consommée", (_f(v.get("metrage_total_ml")) * laize_d / 1000.0) if laize_d else None,
               surface.probable, "m²", f"{surface.bas:,.0f} – {surface.haut:,.0f}".replace(",", " "),
               {"coherent": f"compteur et MyStock à {_pct(ecart)}", "incoherent": f"écart compteur / MyStock {_pct(ecart)}",
                "compteur_seul": "compteur seul", "mystock_seul": "MyStock seul"}.get(croisement, "")),
        _ligne("Coût matière", _f(v.get("cout_matiere")), surface.probable * prix_m2_r, "€",
               f"{surface.bas * prix_m2_r:,.0f} – {surface.haut * prix_m2_r:,.0f}".replace(",", " "), source_matiere),
        _ligne("Durée totale", _f(v.get("temps_total_mn")), duree, "mn",
               f"± {params['fourchette_duree_pct']:g} %", "saisies MyProd"),
        _ligne("dont calage", calage_d, calage, "mn", f"± {params['fourchette_frontiere_mn']:g} mn",
               "passage calage → production incertain"),
        _ligne("dont production", _f(v.get("temps_total_mn")) - calage_d, prod, "mn",
               f"± {params['fourchette_frontiere_mn']:g} mn", "passage calage → production incertain"),
        _ligne("dont arrêts, nettoyage, autres", None, arret, "mn", "", "saisies MyProd"),
        _ligne("Quantité", qte_devis, qte_prod, "ex", "", "saisies MyProd"),
        _ligne("Prix de vente", _f(v.get("prix_vente")), pv, "€", "exact", source_pv),
        _ligne("Emballage", _f(v.get("cout_emballage")), annexes["emballage"].probable, "€", "exact",
               "sorties MyStock" if emballage_eur > 0 else "repris du devis · non mesuré"),
        _ligne("Transport", _f(v.get("cout_transport")), annexes["transport"].probable, "€", "exact",
               "prix retenu MyExpé" if transport is not None else "repris du devis · non mesuré"),
        _ligne("Outil, encre, cliché", sum(_f(v.get(k)) for k in ("cout_outil", "cout_encre", "cout_cliche")),
               sum(annexes[k].probable for k in ("outil", "encre", "cliche")), "€", "exact",
               "repris du devis · non mesuré"),
    ]

    return {
        **tete,
        "etat": "provisoire" if provisoire else "complet",
        "manque": manque,
        "marche": marche,
        "dossiers": dossiers,
        "racine": racine,
        "seuils": seuils,
        "devis_calcul": calc_d,
        "devis_verdict": vd_devis,
        "controle_devis_ok": _controle_ok(controler_devis(v, laize_d, params["tolerance_controle_pct"])),
        "reel": reel,
        "verdict": vd,
        "cascade_marge": cascade_mb,
        "cascade_cout_horaire": cascade_eh,
        "redevise": {"prix_vente": round(pv_redevise, 2),
                     "non_refacture": round(pv_redevise - _f(v["prix_vente"]), 2)} if pv_redevise else None,
        "parametres": lignes,
        "consommations": conso,
        "factures": (fact or {}).get("lignes", []),
        "alertes": alertes,
    }


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

PERIODES = ("last30", "last90", "thisYear", "all")


def bornes_periode(periode: str, aujourd_hui=None) -> tuple[Optional[str], Optional[str]]:
    """`(du, au)` en AAAA-MM-JJ ; `(None, None)` pour « tout »."""
    from datetime import date, timedelta
    j = aujourd_hui or date.today()
    if periode == "last90":
        return (j - timedelta(days=89)).isoformat(), j.isoformat()
    if periode == "thisYear":
        return date(j.year, 1, 1).isoformat(), j.isoformat()
    if periode == "all":
        return None, None
    return (j - timedelta(days=29)).isoformat(), j.isoformat()


def resume_fiche(f: dict) -> dict:
    """Ce qu'une ligne du tableau de bord garde d'une fiche."""
    reel = f.get("reel") or {}
    d = f.get("devis_calcul") or {}
    return {
        "planning_entry_id": f.get("planning_entry_id"),
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
    }


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


def tableau_de_bord(conn, periode: str = "last30", machine: str = "") -> dict:
    """Les dossiers terminés et rattachés à un devis validé, jugés un par un.

    Les compteurs, l'écart moyen et les causes ne portent que sur les dossiers
    COMPLETS (produits, déstockés, facturés) ; les autres sont listés « en
    attente » avec ce qui leur manque. Machines retirées du suivi des devis
    exclues, comme dans le Pilotage.
    """
    if periode not in PERIODES:
        periode = "last30"
    du, au = bornes_periode(periode)
    params = rentabilite_parametres.lire(conn)
    sql = """SELECT e.id, m.nom AS machine
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

    lignes, erreurs = [], 0
    for r in lignes_sql:
        if machine and r["machine"] != machine:
            continue
        try:
            f = fiche_rentabilite(conn, int(r["id"]))
        except Exception:
            erreurs += 1
            continue
        if f.get("etat") in ("sans_devis",):
            continue
        lignes.append(resume_fiche(f))

    complets = [l for l in lignes if l["etat"] == "complet" and l["mb_pct"] and l["cout_horaire"]]
    comptes = {"reussi": 0, "limite": 0, "sous_seuil": 0}
    for l in complets:
        g = (l["verdict"] or {}).get("global")
        if g in comptes:
            comptes[g] += 1
    ecarts = [l["mb_pct"]["probable"] - l["devis_mb_pct"] for l in complets if l["devis_mb_pct"] is not None]
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
                    "non_calculables": len(lignes) - len(complets)
                                       - sum(1 for l in lignes if l["etat"] == "provisoire"),
                    "erreurs": erreurs},
        "ecart_mb_pts": round(sum(ecarts) / len(ecarts), 2) if ecarts else None,
        "cout_horaire_median": round(mediane, 1) if mediane is not None else None,
        "causes_marge": _causes(complets, "cascade_marge", True),
        "causes_cout_horaire": _causes(complets, "cascade_cout_horaire", False),
        "dossiers": lignes,
    }

"""MyStock › Monitoring — flux des produits finis, rapprochés source par source.

Deux comparaisons, en lecture seule :

- **Production → stock** (`flux_production`) : ce que le planning annonce
  (dossier, référence produit, quantité de l'OF), ce que l'atelier a saisi
  (fins de production), ce que MyStock a reçu (entrées) et où la marchandise
  est allée ensuite (déplacements, stock restant du dossier).
- **Expédition** (`flux_expedition`) : ce que RVGI a livré (lignes de BL), ce
  que MyExpé a fait partir (départs), la date de livraison des dossiers, et ce
  que MyStock a sorti.

Une sortie de stock ne porte ni BL ni départ (`expe_depart_id` n'est rempli
par aucun écran à ce jour) : l'expédition se rapproche donc par RÉFÉRENCE sur
la période, pas ligne à ligne. Une entrée de production porte son dossier
(`mouvements_stock.no_dossier`) : la production se rapproche par DOSSIER.

Les déplacements s'écrivent en couple « sortie Déplacement vers X » + « entrée
Déplacement depuis Y » (`deplacer_lot_fifo`) : ils ne sont comptés ni comme
entrée de production, ni comme sortie d'expédition.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional

from config import MONITORING_RAPPROCHEMENT_JOURS, MONITORING_TOLERANCE_PCT
from datetime import datetime, timedelta

_RE_OF = re.compile(r"\b(99\d{5})\b")
_RE_CODE_ARTICLE = re.compile(r"^\d+$")

_NOTE_DEPLACEMENT_ENTREE = "Déplacement depuis%"
_NOTE_DEPLACEMENT_SORTIE = "Déplacement vers%"
_NOTE_ANNULATION = "Annulation%"


def _f(v: Any) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _tol() -> float:
    return max(0.0, MONITORING_TOLERANCE_PCT) / 100.0


def _proche(a: float, b: float) -> bool:
    """Deux quantités concordent à la tolérance près (relative à la plus grande)."""
    ref = max(abs(a), abs(b))
    return ref == 0 or abs(a - b) <= ref * _tol()


def _lots(seq: Iterable[Any], n: int = 500):
    seq = list(seq)
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def _place(n: int) -> str:
    return ",".join("?" * n)


# ─── Production → stock ─────────────────────────────────────────────────────

def _infos_dossiers(conn, refs: List[str]) -> Dict[str, dict]:
    """Ligne de planning de chaque dossier (par `reference`), OF compris."""
    out: Dict[str, dict] = {}
    for lot in _lots(refs):
        for r in conn.execute(
            f"""SELECT pe.id, pe.reference, pe.numero_of, pe.ref_produit,
                       pe.ref_produit_norm, pe.client, pe.statut, pe.date_livraison,
                       pe.planned_end, pe.planned_end_manual, m.nom AS machine,
                       (SELECT o.qte_etiquettes FROM of_imports o
                         WHERE o.id = pe.of_import_id) AS qte_of
                  FROM planning_entries pe
                  LEFT JOIN machines m ON m.id = pe.machine_id
                 WHERE TRIM(pe.reference) IN ({_place(len(lot))})
                 ORDER BY pe.id""",
            lot,
        ).fetchall():
            out.setdefault((r["reference"] or "").strip(), dict(r))
    return out


def _dossiers_par_of(conn, ofs: List[str]) -> Dict[str, str]:
    """Numéro d'OF / de commande (99xxxxx) → référence du dossier."""
    out: Dict[str, str] = {}
    for lot in _lots(ofs):
        for r in conn.execute(
            f"""SELECT TRIM(numero_of) AS of_, TRIM(reference) AS ref
                  FROM planning_entries
                 WHERE TRIM(numero_of) IN ({_place(len(lot))})
                 ORDER BY id""",
            lot,
        ).fetchall():
            out.setdefault(r["of_"], r["ref"])
    return out


def _dossier_anterieur(conn, ref: str, quand: str) -> Optional[str]:
    """Dernier dossier de la référence `ref` produit avant `quand`, dans la fenêtre
    `MONITORING_RAPPROCHEMENT_JOURS`. La date retenue est la dernière saisie de
    production, sinon la fin planifiée."""
    if not ref or not quand:
        return None
    try:
        borne = (datetime.fromisoformat(quand[:19]) - timedelta(days=MONITORING_RAPPROCHEMENT_JOURS)).isoformat()
    except ValueError:
        return None
    r = conn.execute(
        """SELECT ref, fin FROM (
             SELECT TRIM(pe.reference) AS ref,
                    COALESCE((SELECT MAX(pd.date_operation) FROM production_data pd
                               WHERE TRIM(pd.no_dossier) = TRIM(pe.reference)
                                 AND COALESCE(pd.est_annule, 0) = 0),
                             pe.planned_end) AS fin
               FROM planning_entries pe
              WHERE TRIM(COALESCE(pe.ref_produit_norm, '')) = ?)
            WHERE fin IS NOT NULL AND fin <= ? AND fin >= ?
            ORDER BY fin DESC LIMIT 1""",
        (ref, quand[:19], borne),
    ).fetchone()
    return r["ref"] if r else None


def flux_production(conn, du: str, au: str) -> dict:
    """Dossiers produits ou entrés en stock entre `du` et `au` (inclus, AAAA-MM-JJ)."""
    # 1. Dossiers saisis sur la période.
    dossiers: set = set()
    for r in conn.execute(
        """SELECT DISTINCT TRIM(no_dossier) AS d FROM production_data
            WHERE COALESCE(est_annule, 0) = 0
              AND TRIM(COALESCE(no_dossier, '')) <> ''
              AND substr(date_operation, 1, 10) BETWEEN ? AND ?""",
        (du, au),
    ).fetchall():
        dossiers.add(r["d"])

    # 2. Entrées de stock sur la période (hors déplacements).
    entrees_periode = [dict(r) for r in conn.execute(
        """SELECT m.id, m.created_at, m.emplacement, m.quantite, m.note,
                  TRIM(COALESCE(m.no_dossier, '')) AS no_dossier,
                  m.created_by_name, p.reference, p.designation, p.unite
             FROM mouvements_stock m JOIN produits p ON p.id = m.produit_id
            WHERE m.type_mouvement = 'entree'
              AND COALESCE(m.note, '') NOT LIKE ?
              AND substr(m.created_at, 1, 10) BETWEEN ? AND ?""",
        (_NOTE_DEPLACEMENT_ENTREE, du, au),
    ).fetchall()]

    # Une entrée sans dossier mais dont la note cite un OF (« Production |
    # 2026-10-15 | OF 9932641 ») se rattache au dossier de cet OF.
    ofs = {m.group(1) for e in entrees_periode if not e["no_dossier"]
           for m in [_RE_OF.search(e["note"] or "")] if m}
    par_of = _dossiers_par_of(conn, sorted(ofs)) if ofs else {}
    for e in entrees_periode:
        if not e["no_dossier"]:
            m = _RE_OF.search(e["note"] or "")
            if m and m.group(1) in par_of:
                e["no_dossier"] = par_of[m.group(1)]
                e["rattachement"] = "of"
        if e["no_dossier"]:
            dossiers.add(e["no_dossier"])

    liste = sorted(dossiers)
    infos = _infos_dossiers(conn, liste)

    # Une entrée sans dossier se rattache au dossier de même référence s'il
    # est le seul de la période — sinon elle reste une ligne à part.
    dossiers_par_ref: Dict[str, List[str]] = defaultdict(list)
    for d in liste:
        ref = ((infos.get(d) or {}).get("ref_produit_norm") or "").strip()
        if ref:
            dossiers_par_ref[ref].append(d)
    hors_dossier: List[dict] = []
    rattachees: Dict[str, List[dict]] = defaultdict(list)
    for e in entrees_periode:
        if e["no_dossier"]:
            continue
        cands = dossiers_par_ref.get((e["reference"] or "").strip()) or []
        if len(cands) == 1:
            e["rattachement"] = "reference"
            rattachees[cands[0]].append(e)
        else:
            hors_dossier.append(e)

    # Entrée tardive : le dossier a été produit AVANT la période (fin le 09,
    # mise en stock le 19). On cherche le dernier dossier de même référence
    # dont la production s'est terminée au plus tard N jours avant l'entrée.
    reste: List[dict] = []
    nouveaux: set = set()
    for e in hors_dossier:
        d = _dossier_anterieur(conn, (e["reference"] or "").strip(), e["created_at"] or "")
        if d:
            e["rattachement"] = "reference"
            rattachees[d].append(e)
            if d not in dossiers:
                nouveaux.add(d)
        else:
            reste.append(e)
    hors_dossier = reste
    if nouveaux:
        dossiers |= nouveaux
        liste = sorted(dossiers)
        infos.update(_infos_dossiers(conn, sorted(nouveaux)))

    saisies: Dict[str, dict] = {}
    entrees: Dict[str, List[dict]] = defaultdict(list)
    deplacements: Dict[str, List[dict]] = defaultdict(list)
    restants: Dict[str, List[dict]] = defaultdict(list)
    for lot in _lots(liste):
        ph = _place(len(lot))
        for r in conn.execute(
            f"""SELECT TRIM(no_dossier) AS d,
                       SUM(CASE WHEN operation_code = '89' THEN COALESCE(quantite_traitee, 0) END) AS somme,
                       MAX(CASE WHEN operation_code = '89' THEN COALESCE(quantite_traitee, 0) END) AS maxi,
                       MAX(CASE WHEN operation_code = '89' THEN COALESCE(fin_dossier, 0) END) AS cloture,
                       MIN(date_operation) AS debut, MAX(date_operation) AS fin,
                       GROUP_CONCAT(DISTINCT machine) AS machines,
                       COUNT(*) AS nb
                  FROM production_data
                 WHERE COALESCE(est_annule, 0) = 0 AND TRIM(no_dossier) IN ({ph})
                 GROUP BY TRIM(no_dossier)""",
            lot,
        ).fetchall():
            saisies[r["d"]] = dict(r)
        # Entrées du dossier, toutes dates : un dossier saisi le 14 peut entrer en stock le 21.
        for r in conn.execute(
            f"""SELECT m.id, m.created_at, m.emplacement, m.quantite, m.note,
                       TRIM(m.no_dossier) AS no_dossier, m.created_by_name,
                       p.reference, p.designation, p.unite
                  FROM mouvements_stock m JOIN produits p ON p.id = m.produit_id
                 WHERE m.type_mouvement = 'entree'
                   AND COALESCE(m.note, '') NOT LIKE ?
                   AND TRIM(m.no_dossier) IN ({ph})""",
            [_NOTE_DEPLACEMENT_ENTREE, *lot],
        ).fetchall():
            entrees[r["no_dossier"]].append(dict(r))
        for r in conn.execute(
            f"""SELECT m.created_at, m.emplacement, m.quantite, m.note,
                       TRIM(m.no_dossier) AS no_dossier
                  FROM mouvements_stock m
                 WHERE m.type_mouvement = 'entree'
                   AND COALESCE(m.note, '') LIKE ?
                   AND TRIM(m.no_dossier) IN ({ph})
                 ORDER BY m.created_at""",
            [_NOTE_DEPLACEMENT_ENTREE, *lot],
        ).fetchall():
            deplacements[r["no_dossier"]].append(dict(r))
        for r in conn.execute(
            f"""SELECT TRIM(no_dossier) AS d, emplacement, SUM(quantite_restante) AS q
                  FROM lots_stock
                 WHERE quantite_restante > 0 AND TRIM(no_dossier) IN ({ph})
                 GROUP BY TRIM(no_dossier), emplacement""",
            lot,
        ).fetchall():
            restants[r["d"]].append({"emplacement": r["emplacement"], "quantite": _f(r["q"])})
    # Les entrées sans dossier rattachées par la note (OF) sont déjà dans
    # `entrees` si elles portaient le dossier ; sinon on les ajoute ici.
    for e in entrees_periode:
        if e.get("rattachement") == "of":
            entrees[e["no_dossier"]].append(e)
    for d, lst in rattachees.items():
        entrees[d].extend(lst)

    lignes: List[dict] = []
    for d in liste:
        pe = infos.get(d) or {}
        s = saisies.get(d) or {}
        ents = sorted(entrees.get(d) or [], key=lambda x: x["created_at"] or "")
        deps = deplacements.get(d) or []
        rest = restants.get(d) or []
        q_somme, q_maxi = _f(s.get("somme")), _f(s.get("maxi"))
        q_entree = sum(_f(e["quantite"]) for e in ents)
        refs_stock = sorted({(e["reference"] or "").strip() for e in ents if e.get("reference")})
        ref_plan = (pe.get("ref_produit_norm") or "").strip()
        ref = ref_plan or (refs_stock[0] if refs_stock else "")
        premiere = ents[0] if ents else None
        cloture = bool(s.get("cloture"))

        if q_maxi <= 0 and q_entree <= 0:
            statut = "en_cours"
        elif q_maxi <= 0:
            statut = "sans_saisie"
        elif q_entree <= 0:
            statut = "non_entre" if cloture else "en_cours"
        elif q_entree >= q_maxi * (1 - _tol()) and q_entree <= q_somme * (1 + _tol()):
            # Selon le poste, la fin de production porte le cycle ou le cumul
            # du dossier (cf. coherence.ctrl_prod_quantites) : l'entrée est
            # juste si elle tombe entre le plus grand relevé et leur somme.
            statut = "ok"
        else:
            statut = "ecart"
        if statut == "ok" and ref_plan and refs_stock and ref_plan not in refs_stock:
            statut = "ref_diff"

        # Écart affiché : contre le cumul quand l'entrée le dépasse, contre le
        # plus grand relevé sinon — l'écart le plus petit, donc le plus honnête.
        if q_maxi > 0 and q_entree > 0:
            ecart = q_entree - (q_somme if q_entree > q_somme else q_maxi if q_entree < q_maxi else q_entree)
        elif q_maxi > 0 or q_entree > 0:
            ecart = q_entree - q_maxi
        else:
            ecart = None

        lignes.append({
            "cle": "d:" + d,
            "no_dossier": d,
            "planning_entry_id": pe.get("id"),
            "numero_of": pe.get("numero_of"),
            "reference": ref,
            "ref_planning": ref_plan or None,
            "refs_stock": refs_stock,
            "designation": (premiere or {}).get("designation") or pe.get("ref_produit"),
            "unite": (premiere or {}).get("unite"),
            "client": pe.get("client"),
            "machine": pe.get("machine") or s.get("machines"),
            "statut_planning": pe.get("statut"),
            "fin_prevue": pe.get("planned_end_manual") or pe.get("planned_end"),
            "qte_of": _f(pe.get("qte_of")) or None,
            "qte_produite": q_somme or None,
            "qte_produite_max": q_maxi or None,
            "cloture": cloture,
            "derniere_saisie": s.get("fin"),
            "qte_entree": q_entree or None,
            "nb_entrees": len(ents),
            "derniere_entree": ents[-1]["created_at"] if ents else None,
            "emplacements_entree": sorted({e["emplacement"] for e in ents if e.get("emplacement")}),
            "rattachement": sorted({e["rattachement"] for e in ents if e.get("rattachement")}),
            "nb_deplacements": len(deps),
            "qte_deplacee": sum(_f(x["quantite"]) for x in deps) or None,
            "dernier_deplacement": deps[-1]["created_at"] if deps else None,
            "derniere_destination": deps[-1]["emplacement"] if deps else None,
            "stock_restant": sum(x["quantite"] for x in rest) or None,
            "emplacements_restants": sorted(x["emplacement"] for x in rest),
            "ecart": ecart,
            "statut": statut,
        })

    # Entrées hors dossier, regroupées par référence.
    par_ref: Dict[str, List[dict]] = defaultdict(list)
    for e in hors_dossier:
        par_ref[(e["reference"] or "").strip()].append(e)
    for ref, ents in sorted(par_ref.items()):
        ents.sort(key=lambda x: x["created_at"] or "")
        lignes.append({
            "cle": "r:" + ref,
            "no_dossier": None,
            "reference": ref,
            "refs_stock": [ref],
            "designation": ents[0].get("designation"),
            "unite": ents[0].get("unite"),
            "client": None, "machine": None, "statut_planning": None,
            "qte_of": None, "qte_produite": None, "qte_produite_max": None,
            "cloture": False, "derniere_saisie": None,
            "qte_entree": sum(_f(e["quantite"]) for e in ents) or None,
            "nb_entrees": len(ents),
            "derniere_entree": ents[-1]["created_at"],
            "emplacements_entree": sorted({e["emplacement"] for e in ents if e.get("emplacement")}),
            "rattachement": [],
            "nb_deplacements": 0, "qte_deplacee": None,
            "dernier_deplacement": None, "derniere_destination": None,
            "stock_restant": None, "emplacements_restants": [],
            "ecart": None,
            "statut": "hors_dossier",
        })
    return {"du": du, "au": au, "tolerance_pct": MONITORING_TOLERANCE_PCT, "lignes": lignes}


# ─── Expédition ─────────────────────────────────────────────────────────────

def _bl_rvgi(erp, du: str, au: str) -> List[dict]:
    from app.routers.reconciliation import _erp_reference

    out = []
    for r in erp.execute(
        """SELECT l.numero AS bl, substr(e.amje, 1, 10) AS jour, e.lrs AS client,
                  l.numcde, l.qte, c.code1, c.code2
             FROM liv_ligne l
             JOIN liv_entete e ON e.numero = l.numero AND e.corbeille = 0
             JOIN cde_ligne c ON c.numero = l.numcde AND c.ligne = l.lignecde AND c.corbeille = 0
            WHERE l.corbeille = 0 AND substr(e.amje, 1, 10) BETWEEN ? AND ?""",
        (du, au),
    ).fetchall():
        # Frais de port & co. (« FR / FRAIS_DE_PORT ») : pas un article.
        if not _RE_CODE_ARTICLE.match(str(r["code1"] or "").strip()):
            continue
        ref = _erp_reference(r["code1"], r["code2"])
        if not ref:
            continue
        out.append({"bl": str(r["bl"]), "jour": r["jour"], "client": r["client"],
                    "numcde": str(r["numcde"] or "").strip(), "qte": _f(r["qte"]), "reference": ref})
    return out


def flux_expedition(conn, erp, du: str, au: str) -> dict:
    """Références livrées, parties ou sorties de stock entre `du` et `au`.

    `erp` peut être `None` (miroir absent) : la page garde alors le côté
    MySifa et le dit.
    """
    from app.services.coherence import numeros_bl

    bls = _bl_rvgi(erp, du, au) if erp is not None else []

    sorties = [dict(r) for r in conn.execute(
        """SELECT m.created_at, m.emplacement, m.quantite, m.note, m.created_by_name,
                  TRIM(COALESCE(m.no_dossier, '')) AS no_dossier, p.reference
             FROM mouvements_stock m JOIN produits p ON p.id = m.produit_id
            WHERE m.type_mouvement = 'sortie'
              AND COALESCE(m.note, '') NOT LIKE ?
              AND COALESCE(m.note, '') NOT LIKE ?
              AND substr(m.created_at, 1, 10) BETWEEN ? AND ?""",
        (_NOTE_DEPLACEMENT_SORTIE, _NOTE_ANNULATION, du, au),
    ).fetchall()]

    # Dossiers : ceux des commandes livrées, et ceux à livrer sur la période.
    a_livrer = [dict(r) for r in conn.execute(
        """SELECT pe.id, TRIM(pe.reference) AS reference, TRIM(pe.numero_of) AS numero_of,
                  pe.ref_produit_norm, pe.client, pe.statut, pe.date_livraison
             FROM planning_entries pe
            WHERE substr(COALESCE(pe.date_livraison, ''), 1, 10) BETWEEN ? AND ?""",
        (du, au),
    ).fetchall()]
    ofs = sorted({b["numcde"] for b in bls if b["numcde"]})
    par_of: Dict[str, dict] = {}
    for lot in _lots(ofs):
        for r in conn.execute(
            f"""SELECT pe.id, TRIM(pe.reference) AS reference, TRIM(pe.numero_of) AS numero_of,
                       pe.ref_produit_norm, pe.client, pe.statut, pe.date_livraison
                  FROM planning_entries pe
                 WHERE TRIM(pe.numero_of) IN ({_place(len(lot))})
                 ORDER BY pe.id""",
            lot,
        ).fetchall():
            par_of.setdefault(r["numero_of"], dict(r))

    departs = [dict(r) for r in conn.execute(
        """SELECT d.id, substr(d.date_enlevement, 1, 10) AS jour, d.statut, d.client,
                  d.no_bl, d.transporteur, d.date_livraison,
                  COALESCE(NULLIF(TRIM(COALESCE(d.no_dossier, '')), ''),
                           TRIM(COALESCE(pe.reference, ''))) AS no_dossier,
                  pe.ref_produit_norm
             FROM expe_departs d
             LEFT JOIN planning_entries pe ON pe.id = d.planning_entry_id
            WHERE substr(COALESCE(d.date_enlevement, ''), 1, 10) BETWEEN ? AND ?""",
        (du, au),
    ).fetchall()]

    lignes: Dict[str, dict] = {}

    def ligne(ref: str) -> dict:
        if ref not in lignes:
            lignes[ref] = {"reference": ref, "bls": [], "dossiers": {}, "departs": {},
                           "sorties": [], "clients": set()}
        return lignes[ref]

    def poser_dossier(L: dict, pe: dict):
        if pe and pe.get("reference"):
            L["dossiers"].setdefault(pe["reference"], {
                "no_dossier": pe["reference"], "planning_entry_id": pe["id"],
                "date_livraison": (pe.get("date_livraison") or "")[:10] or None,
                "statut": pe.get("statut"),
            })

    bl_vers_ref: Dict[str, set] = defaultdict(set)
    for b in bls:
        L = ligne(b["reference"])
        L["bls"].append(b)
        if b["client"]:
            L["clients"].add(b["client"])
        bl_vers_ref[b["bl"]].add(b["reference"])
        poser_dossier(L, par_of.get(b["numcde"]))
    for pe in a_livrer:
        ref = (pe.get("ref_produit_norm") or "").strip()
        if ref:
            L = ligne(ref)
            poser_dossier(L, pe)
            if pe.get("client"):
                L["clients"].add(pe["client"])
    dossier_vers_ref: Dict[str, set] = defaultdict(set)
    for ref, L in lignes.items():
        for d in L["dossiers"]:
            dossier_vers_ref[d].add(ref)
    for d in departs:
        refs = set()
        for n in numeros_bl(d["no_bl"]):
            refs |= bl_vers_ref.get(n, set())
        if not refs and d["no_dossier"]:
            refs |= dossier_vers_ref.get(d["no_dossier"], set())
        if not refs and (d.get("ref_produit_norm") or "").strip():
            refs.add(d["ref_produit_norm"].strip())
        for ref in refs:
            ligne(ref)["departs"].setdefault(d["id"], {
                "id": d["id"], "jour": d["jour"], "statut": d["statut"],
                "no_bl": d["no_bl"], "transporteur": d["transporteur"],
                "no_dossier": d["no_dossier"] or None,
            })
    for s in sorties:
        ref = (s["reference"] or "").strip()
        if ref:
            ligne(ref)["sorties"].append(s)

    # Désignation, unité et stock actuel côté MyStock.
    produits: Dict[str, dict] = {}
    for lot in _lots(sorted(lignes)):
        for r in conn.execute(
            f"""SELECT p.reference, p.designation, p.unite,
                       COALESCE((SELECT SUM(se.quantite) FROM stock_emplacements se
                                  WHERE se.produit_id = p.id), 0) AS stock
                  FROM produits p WHERE p.reference IN ({_place(len(lot))})""",
            lot,
        ).fetchall():
            produits[r["reference"]] = dict(r)

    out = []
    for ref, L in sorted(lignes.items()):
        p = produits.get(ref) or {}
        q_bl = sum(b["qte"] for b in L["bls"])
        q_sortie = sum(_f(s["quantite"]) for s in L["sorties"])
        deps = sorted(L["departs"].values(), key=lambda x: x["jour"] or "")
        doss = sorted(L["dossiers"].values(), key=lambda x: x["date_livraison"] or "")
        if q_bl > 0 and q_sortie > 0:
            statut = "ok" if _proche(q_bl, q_sortie) else "ecart"
        elif q_bl > 0:
            statut = "bl_sans_sortie"
        elif q_sortie > 0:
            statut = "sortie_sans_bl" if erp is not None else "sortie"
        elif any(d["statut"] != "valide" for d in deps):
            statut = "depart_prevu"
        else:
            statut = "a_expedier"
        sorties_tri = sorted(L["sorties"], key=lambda x: x["created_at"] or "")
        out.append({
            "cle": ref,
            "reference": ref,
            "designation": p.get("designation"),
            "unite": p.get("unite"),
            "clients": sorted(L["clients"]),
            "dossiers": doss,
            "date_livraison": doss[0]["date_livraison"] if doss else None,
            "bls": sorted({b["bl"] for b in L["bls"]}),
            "date_bl": max((b["jour"] for b in L["bls"]), default=None),
            "qte_bl": q_bl or None,
            "departs": deps,
            "date_depart": deps[-1]["jour"] if deps else None,
            "nb_sorties": len(sorties_tri),
            "qte_sortie": q_sortie or None,
            "derniere_sortie": sorties_tri[-1]["created_at"] if sorties_tri else None,
            "emplacements_sortie": sorted({s["emplacement"] for s in sorties_tri if s.get("emplacement")}),
            "stock_actuel": _f(p.get("stock")) if p else None,
            "ecart": (q_sortie - q_bl) if (q_bl > 0 or q_sortie > 0) and erp is not None else None,
            "statut": statut,
        })
    return {"du": du, "au": au, "tolerance_pct": MONITORING_TOLERANCE_PCT,
            "miroir": erp is not None, "lignes": out}

"""MySifa — Contrôleurs de cohérence.

Toutes les 30 minutes, des règles écrites en code (aucun appel à l'IA) croisent
la production, le planning, MyExpé, MyStock, les OF, les fiches techniques et
le miroir RVGI. Ce qu'elles trouvent va dans `coherence_ecarts`, une file de
travail que l'agent IA lit (`mysifa_ecarts`) et que la pastille compte.

Principes
---------
- Un contrôleur ne corrige rien. Il constate, avec les chiffres qui le prouvent.
- Un écart retrouvé reste ouvert ; un écart que le passage suivant ne retrouve
  plus passe « résolu » de lui-même. Seules les règles qui ont tourné sans
  erreur résolvent : un contrôleur en panne ne vide pas la file.
- Les chiffres de prod viennent des mêmes sources que les écrans
  (`rapport_dossier` via `mcp_metier.anomalies`, `fiche_choix`,
  `coherence_fiche`) : jamais une seconde définition de ce qui est anormal.
- Les seuils et l'activation de chaque règle se règlent dans
  Paramètres › Cohérence (`coherence_reglages`).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional
from zoneinfo import ZoneInfo

_PARIS = ZoneInfo("Europe/Paris")

FAMILLES = {
    "prod": "Production et planning",
    "flux": "Livraison, départ et stock",
    "documents": "OF et fiches techniques",
}
GRAVITES = ("haute", "moyenne", "basse")
STATUTS = ("ouvert", "explique", "resolu")


@dataclass(frozen=True)
class Regle:
    code: str
    famille: str
    titre: str
    description: str
    gravite: str
    lien: str
    actif_defaut: bool = True


REGLES: Dict[str, Regle] = {r.code: r for r in (
    Regle("prod.en_cours_sans_saisie", "prod", "Dossier en cours sans saisie",
          "Dossier « en cours » au planning sans aucune saisie depuis plus de N heures.",
          "moyenne", "/planning"),
    Regle("prod.retard_prevu", "prod", "Fin prévue après la date de livraison",
          "Dossier pas encore terminé dont la fin planifiée dépasse la date de livraison.",
          "haute", "/planning"),
    Regle("prod.quantite_vs_of", "prod", "Quantité produite loin de l'OF",
          "Dossier clôturé dont les étiquettes saisies s'écartent de la quantité de l'OF "
          "au-delà de la tolérance.",
          "moyenne", "/prod#retour"),
    Regle("prod.quantite_non_saisie", "prod", "Quantité produite non saisie",
          "Dossier clôturé dont aucune fin de production ne porte de quantité d'étiquettes.",
          "moyenne", "/prod#retour"),
    Regle("prod.info_prod_absente", "prod", "Clôture sans info prod",
          "Dossier clôturé sans note de clôture.", "basse", "/prod#retour"),
    Regle("prod.seuils_sans_explication", "prod", "Arrêt sans explication",
          "Seuil d'arrêt franchi sans explication saisie.", "basse", "/prod#retour"),
    Regle("prod.saisie_ouverte", "prod", "Saisie restée ouverte",
          "Saisie restée ouverte d'un jour à l'autre : le temps du dossier est faux.",
          "moyenne", "/prod#retour"),
    Regle("flux.bl_sans_depart", "flux", "BL RVGI sans départ MyExpé",
          "Bon de livraison émis dans RVGI qu'aucun départ MyExpé ne porte.",
          "moyenne", "/expe#suivi_departs"),
    Regle("flux.depart_sans_bl", "flux", "Départ validé sans BL",
          "Départ validé dont la date d'enlèvement est passée, sans numéro de BL.",
          "moyenne", "/expe#suivi_departs"),
    Regle("flux.bl_inconnu", "flux", "BL du départ absent de RVGI",
          "Numéro de BL saisi sur un départ et introuvable dans le miroir RVGI.",
          "haute", "/expe#suivi_departs"),
    Regle("flux.expedie_sans_sortie", "flux", "Expédié sans sortie de stock",
          "Article livré sur un BL RVGI, encore en stock dans MyStock, sans sortie "
          "de stock autour de la date du BL : le stock MySifa est probablement surévalué.",
          "haute", "/stock"),
    Regle("flux.date_enlevement", "flux", "Date d'enlèvement aberrante",
          "Départ dont la date d'enlèvement est très loin dans le futur ou dans le passé.",
          "basse", "/expe#suivi_departs"),
    Regle("documents.of_fiche", "documents", "OF différent de la fiche technique",
          "Dossier à produire dont l'OF ne dit pas la même chose que sa fiche technique "
          "(laize, quantité au mille, matières, mandrin, carton).",
          "haute", "/planning"),
    Regle("documents.of_planning", "documents", "OF différent du planning",
          "Machine ou laize de l'OF différente de celle du dossier au planning.",
          "moyenne", "/planning"),
    Regle("documents.fiche_incoherente", "documents", "Fiche technique incohérente",
          "La fiche ne boucle pas : largeur d'étiquette × nombre de poses ne tient pas dans la laize.",
          "haute", "/planning"),
)}

# cle -> (défaut, libellé, unité)
SEUILS: Dict[str, tuple] = {
    "fenetre_jours": (14, "Période examinée", "jours"),
    "tolerance_quantite_pct": (10, "Tolérance quantité produite / OF", "%"),
    "en_cours_sans_saisie_h": (24, "Dossier en cours sans saisie depuis", "heures"),
    "sortie_stock_jours": (3, "Délai admis entre BL et sortie de stock", "jours"),
    "enlevement_max_jours": (180, "Date d'enlèvement au-delà de", "jours"),
}


# ─── Réglages ────────────────────────────────────────────────────────────────

def charger_reglages(conn) -> Dict[str, Any]:
    brut: Dict[str, str] = {}
    try:
        for r in conn.execute("SELECT cle, valeur FROM coherence_reglages").fetchall():
            brut[r["cle"]] = r["valeur"]
    except Exception:
        pass
    seuils = {}
    for cle, (defaut, _l, _u) in SEUILS.items():
        try:
            seuils[cle] = float(brut[cle]) if cle in brut else float(defaut)
        except (TypeError, ValueError):
            seuils[cle] = float(defaut)
    actives = {code: (brut.get("regle." + code, "1" if r.actif_defaut else "0") == "1")
               for code, r in REGLES.items()}
    return {"seuils": seuils, "regles": actives}


def enregistrer_reglages(conn, valeurs: Dict[str, Any]) -> Dict[str, Any]:
    for cle, val in (valeurs.get("seuils") or {}).items():
        if cle not in SEUILS:
            continue
        try:
            n = float(val)
        except (TypeError, ValueError):
            raise ValueError(f"Valeur invalide pour « {SEUILS[cle][1]} ».")
        if n <= 0 or n > 10000:
            raise ValueError(f"« {SEUILS[cle][1]} » : valeur entre 0 et 10 000.")
        conn.execute("INSERT INTO coherence_reglages (cle, valeur) VALUES (?,?) "
                     "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur", (cle, str(n)))
    for code, actif in (valeurs.get("regles") or {}).items():
        if code not in REGLES:
            continue
        conn.execute("INSERT INTO coherence_reglages (cle, valeur) VALUES (?,?) "
                     "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
                     ("regle." + code, "1" if actif in (True, 1, "1", "true") else "0"))
    conn.commit()
    return charger_reglages(conn)


# ─── Outils ──────────────────────────────────────────────────────────────────

def maintenant() -> datetime:
    return datetime.now(_PARIS).replace(tzinfo=None)


def _iso(d: datetime) -> str:
    return d.strftime("%Y-%m-%dT%H:%M:%S")


def _jour_fr(iso: Optional[str]) -> str:
    s = str(iso or "")[:10]
    if len(s) < 10:
        return "—"
    return f"{s[8:10]}/{s[5:7]}/{s[:4]}"


def _nombre_fr(v: Any) -> str:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "—"
    if n == int(n):
        return f"{int(n):,}".replace(",", " ")
    return f"{n:,.2f}".replace(",", " ").replace(".", ",")


def _ecart(regle: str, objet_type: str, objet_ref: str, titre: str, detail: str,
           donnees: Optional[dict] = None, cle: Optional[str] = None) -> Dict[str, Any]:
    return {
        "regle": regle, "objet_type": objet_type, "objet_ref": str(objet_ref),
        "titre": titre, "detail": detail, "donnees": donnees or {},
        "cle": f"{regle}:{cle or objet_ref}",
    }


def _tables(conn) -> set:
    return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _colonnes(conn, table: str) -> set:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


_RE_BL = re.compile(r"\d{4,9}")


def numeros_bl(texte: Any) -> List[str]:
    """Les numéros de BL écrits dans `expe_departs.no_bl` (« 9939094 », « BL 9939085 / 9939086 »)."""
    return _RE_BL.findall(str(texte or ""))


# ─── Production et planning ─────────────────────────────────────────────────

def ctrl_prod_en_cours_sans_saisie(conn, s, **_) -> List[dict]:
    limite = _iso(maintenant() - timedelta(hours=s["en_cours_sans_saisie_h"]))
    rows = conn.execute(
        """SELECT pe.id, pe.reference, pe.client, m.nom AS machine,
                  (SELECT MAX(pd.date_operation) FROM production_data pd
                    WHERE (pd.planning_entry_id = pe.id OR pd.no_dossier = pe.reference)
                      AND COALESCE(pd.est_annule, 0) = 0) AS derniere
             FROM planning_entries pe
             LEFT JOIN machines m ON m.id = pe.machine_id
            WHERE pe.statut = 'en_cours'"""
    ).fetchall()
    out = []
    for r in rows:
        if r["derniere"] and str(r["derniere"]) >= limite:
            continue
        quand = (f"dernière saisie le {_jour_fr(r['derniere'])} à {str(r['derniere'])[11:16]}"
                 if r["derniere"] else "aucune saisie")
        out.append(_ecart(
            "prod.en_cours_sans_saisie", "dossier", r["reference"],
            f"{r['reference']} · {r['machine'] or '—'}",
            f"En cours au planning, {quand}.",
            {"planning_entry_id": r["id"], "client": r["client"], "machine": r["machine"],
             "derniere_saisie": r["derniere"]}))
    return out


def ctrl_prod_retard_prevu(conn, s, **_) -> List[dict]:
    rows = conn.execute(
        """SELECT pe.id, pe.reference, pe.client, pe.statut, pe.planned_end, pe.date_livraison,
                  m.nom AS machine
             FROM planning_entries pe
             LEFT JOIN machines m ON m.id = pe.machine_id
            WHERE pe.statut IN ('attente', 'en_cours')
              AND COALESCE(pe.date_livraison, '') <> ''
              AND COALESCE(pe.planned_end, '') <> ''
              AND substr(pe.planned_end, 1, 10) > substr(pe.date_livraison, 1, 10)"""
    ).fetchall()
    out = []
    for r in rows:
        retard = (datetime.fromisoformat(str(r["planned_end"])[:10])
                  - datetime.fromisoformat(str(r["date_livraison"])[:10])).days
        out.append(_ecart(
            "prod.retard_prevu", "dossier", r["reference"],
            f"{r['reference']} · {r['client'] or '—'}",
            f"Fin prévue le {_jour_fr(r['planned_end'])} pour une livraison le "
            f"{_jour_fr(r['date_livraison'])} : {retard} jour(s) de retard sur {r['machine'] or '—'}.",
            {"planning_entry_id": r["id"], "machine": r["machine"], "retard_jours": retard,
             "fin_prevue": r["planned_end"], "date_livraison": r["date_livraison"]}))
    return out


def ctrl_prod_quantites(conn, s, depuis: str, **_) -> List[dict]:
    """Quantité saisie en fin de production contre `of_imports.qte_etiquettes`.

    Selon le poste, la quantité d'une fin de production est celle du cycle ou
    le cumul du dossier. On ne tranche pas : on signale un excédent seulement si
    la plus grande valeur saisie dépasse déjà l'OF, et un manque seulement si
    leur somme reste en dessous. Un dossier n'est jugé qu'une fois clôturé.
    """
    tol = s["tolerance_quantite_pct"] / 100.0
    rows = conn.execute(
        """SELECT pd.no_dossier,
                  SUM(COALESCE(pd.quantite_traitee, 0)) AS somme,
                  MAX(COALESCE(pd.quantite_traitee, 0)) AS maxi,
                  MAX(pd.planning_entry_id) AS pe_id,
                  MAX(pd.date_operation) AS fin,
                  MAX(COALESCE(pd.fin_dossier, 0)) AS cloture
             FROM production_data pd
            WHERE pd.operation_code = '89' AND COALESCE(pd.est_annule, 0) = 0
              AND pd.date_operation >= ?
            GROUP BY pd.no_dossier""",
        (depuis,),
    ).fetchall()
    out = []
    for r in rows:
        if not r["cloture"] or not r["pe_id"]:
            continue
        of = conn.execute(
            """SELECT o.of_numero, o.qte_etiquettes, m.nom AS machine
                 FROM planning_entries pe
                 JOIN of_imports o ON o.id = pe.of_import_id
                 LEFT JOIN machines m ON m.id = pe.machine_id
                WHERE pe.id = ?""", (r["pe_id"],)).fetchone()
        dos = r["no_dossier"]
        somme, maxi = float(r["somme"] or 0), float(r["maxi"] or 0)
        if maxi <= 0:
            out.append(_ecart(
                "prod.quantite_non_saisie", "dossier", dos, f"{dos} · {(of['machine'] if of else None) or '—'}",
                f"Clôturé le {_jour_fr(r['fin'])} sans quantité d'étiquettes sur les fins de production.",
                {"fin": r["fin"]}))
            continue
        if not of or not of["qte_etiquettes"]:
            continue
        cible = float(of["qte_etiquettes"])
        if maxi > cible * (1 + tol):
            ecart_pct, constat, vu = (maxi - cible) / cible * 100, "au-dessus", maxi
        elif somme < cible * (1 - tol):
            ecart_pct, constat, vu = (somme - cible) / cible * 100, "en dessous", somme
        else:
            continue
        out.append(_ecart(
            "prod.quantite_vs_of", "dossier", dos, f"{dos} · {of['machine'] or '—'}",
            f"{_nombre_fr(vu)} étiquettes saisies pour {_nombre_fr(cible)} à l'OF {of['of_numero'] or ''} : "
            f"{ecart_pct:+.0f} %, {constat} de la tolérance de {s['tolerance_quantite_pct']:.0f} %.",
            {"saisi_somme": somme, "saisi_max": maxi, "of": of["of_numero"],
             "qte_of": cible, "ecart_pct": round(ecart_pct, 1), "fin": r["fin"]}))
    return out


def ctrl_prod_vigilance(conn, s, depuis: str, aujourdhui: str, **_) -> List[dict]:
    """Les trous des dossiers clôturés, tels que l'écran Retour de prod les liste."""
    from app.services import mcp_metier
    res = mcp_metier.anomalies(depuis[:10], aujourdhui, None, 200)
    out = []
    for p in res.get("points") or []:
        code = "prod." + str(p.get("cle") or "")
        if code not in REGLES:
            continue
        out.append(_ecart(
            code, "dossier", p["dossier"], f"{p['dossier']} · {p.get('machine') or '—'}",
            f"{p.get('constat') or ''} Clôturé le {_jour_fr(p.get('date_fin'))}.".strip(),
            {"client": p.get("client"), "machine": p.get("machine"), "date_fin": p.get("date_fin")}))
    return out


# ─── Livraison RVGI → départ MyExpé → sortie MyStock ────────────────────────

def _bl_rvgi(erp, depuis: str, jusqua: str) -> List[dict]:
    return [dict(r) for r in erp.execute(
        """SELECT e.numero, substr(e.amje, 1, 10) AS jour, e.lrs AS client
             FROM liv_entete e
            WHERE e.corbeille = 0 AND substr(e.amje, 1, 10) BETWEEN ? AND ?""",
        (depuis[:10], jusqua[:10])).fetchall()]


def _departs(conn, depuis: str) -> List[dict]:
    return [dict(r) for r in conn.execute(
        """SELECT id, statut, substr(date_enlevement, 1, 10) AS jour, no_bl, ref_sifa,
                  no_dossier, arc
             FROM expe_departs
            WHERE substr(date_enlevement, 1, 10) >= ?""", (depuis[:10],)).fetchall()]


def ctrl_flux_bl_departs(conn, s, depuis: str, aujourdhui: str, erp=None, releve: str = "", **_) -> List[dict]:
    if erp is None:
        return []
    # Un départ peut porter un BL émis quelques jours avant son enlèvement :
    # on lit les départs sur une fenêtre élargie pour ne pas crier trop tôt.
    departs = _departs(conn, (datetime.fromisoformat(depuis[:10]) - timedelta(days=30)).date().isoformat())
    portes = {n for d in departs for n in numeros_bl(d["no_bl"])}
    out = []
    # Un BL du jour n'a peut-être pas encore son départ : on le juge le lendemain.
    hier = (datetime.fromisoformat(aujourdhui) - timedelta(days=1)).date().isoformat()
    for bl in _bl_rvgi(erp, depuis, hier):
        if str(bl["numero"]) in portes:
            continue
        out.append(_ecart(
            "flux.bl_sans_depart", "bl", bl["numero"], f"BL {bl['numero']} · {bl['client'] or '—'}",
            f"BL émis dans RVGI le {_jour_fr(bl['jour'])}, porté par aucun départ MyExpé.",
            {"date_bl": bl["jour"], "client": bl["client"]}))

    a_verifier: Dict[str, dict] = {}
    for d in departs:
        if d["jour"] < depuis[:10] or d["jour"] > aujourdhui:
            continue
        nums = numeros_bl(d["no_bl"])
        if d["statut"] == "valide" and not nums:
            out.append(_ecart(
                "flux.depart_sans_bl", "depart", d["id"], f"Départ du {_jour_fr(d['jour'])} · {d['ref_sifa'] or '—'}",
                "Départ validé sans numéro de BL.",
                {"depart_id": d["id"], "ref_sifa": d["ref_sifa"], "no_dossier": d["no_dossier"]}))
        # Le miroir doit avoir été relevé après l'enlèvement pour qu'un absent soit un vrai absent.
        if releve and releve[:10] > d["jour"]:
            for n in nums:
                a_verifier[n] = d
    if a_verifier:
        connus = set()
        nums = list(a_verifier)
        for i in range(0, len(nums), 500):
            lot = nums[i:i + 500]
            connus |= {str(r[0]) for r in erp.execute(
                "SELECT numero FROM liv_entete WHERE corbeille = 0 AND numero IN (%s)"
                % ",".join("?" * len(lot)), [int(x) for x in lot]).fetchall()}
        for n, d in a_verifier.items():
            if n in connus:
                continue
            out.append(_ecart(
                "flux.bl_inconnu", "depart", d["id"], f"BL {n} · départ du {_jour_fr(d['jour'])}",
                f"Le départ porte le BL {n}, introuvable dans RVGI (miroir relevé le {_jour_fr(releve)}).",
                {"depart_id": d["id"], "no_bl": n, "ref_sifa": d["ref_sifa"]}, cle=f"{d['id']}:{n}"))
    return out


def ctrl_flux_sortie_stock(conn, s, depuis: str, aujourdhui: str, erp=None, **_) -> List[dict]:
    if erp is None:
        return []
    from app.routers.reconciliation import _erp_reference

    jours = int(s["sortie_stock_jours"])
    hier = (datetime.fromisoformat(aujourdhui) - timedelta(days=1)).date().isoformat()
    lignes = erp.execute(
        """SELECT l.numero, substr(e.amje, 1, 10) AS jour, e.lrs AS client, l.qte,
                  c.code1, c.code2
             FROM liv_ligne l
             JOIN liv_entete e ON e.numero = l.numero AND e.corbeille = 0
             JOIN cde_ligne c ON c.numero = l.numcde AND c.ligne = l.lignecde AND c.corbeille = 0
            WHERE l.corbeille = 0 AND substr(e.amje, 1, 10) BETWEEN ? AND ?""",
        (depuis[:10], hier)).fetchall()
    out = []
    for l in lignes:
        ref = _erp_reference(l["code1"], l["code2"])
        if not ref:
            continue
        p = conn.execute(
            """SELECT p.id, COALESCE((SELECT SUM(quantite) FROM stock_emplacements se
                                       WHERE se.produit_id = p.id), 0) AS stock
                 FROM produits p WHERE p.reference = ?""", (ref,)).fetchone()
        if not p or float(p["stock"] or 0) <= 0:
            continue
        borne = (datetime.fromisoformat(l["jour"]) - timedelta(days=jours)).date().isoformat()
        sortie = conn.execute(
            """SELECT 1 FROM mouvements_stock
                WHERE produit_id = ? AND type_mouvement = 'sortie'
                  AND substr(created_at, 1, 10) >= ? LIMIT 1""", (p["id"], borne)).fetchone()
        if sortie:
            continue
        out.append(_ecart(
            "flux.expedie_sans_sortie", "article", ref, f"{ref} · BL {l['numero']}",
            f"Livré le {_jour_fr(l['jour'])} ({_nombre_fr(l['qte'])} sur le BL, {l['client'] or '—'}), "
            f"aucune sortie de stock depuis le {_jour_fr(borne)} ; MyStock en compte encore "
            f"{_nombre_fr(p['stock'])}.",
            {"no_bl": l["numero"], "date_bl": l["jour"], "qte_bl": l["qte"],
             "stock_mysifa": p["stock"], "produit_id": p["id"]}, cle=f"{ref}:{l['numero']}"))
    return out


def ctrl_flux_date_enlevement(conn, s, aujourdhui: str, **_) -> List[dict]:
    loin = (datetime.fromisoformat(aujourdhui) + timedelta(days=int(s["enlevement_max_jours"]))).date().isoformat()
    rows = conn.execute(
        """SELECT id, substr(date_enlevement, 1, 10) AS jour, ref_sifa, no_bl, statut
             FROM expe_departs
            WHERE COALESCE(date_enlevement, '') <> ''
              AND (substr(date_enlevement, 1, 10) > ? OR substr(date_enlevement, 1, 10) < '2020-01-01')""",
        (loin,)).fetchall()
    return [_ecart(
        "flux.date_enlevement", "depart", r["id"], f"Départ {r['ref_sifa'] or r['id']} · BL {r['no_bl'] or '—'}",
        f"Date d'enlèvement au {_jour_fr(r['jour'])} : probable faute de frappe.",
        {"depart_id": r["id"], "date_enlevement": r["jour"], "statut": r["statut"]}) for r in rows]


# ─── OF, fiches techniques, planning ────────────────────────────────────────

_CHAMPS_OF_FICHE = (
    # (libellé, colonne OF, colonne fiche, nature)
    ("Laize", "laize", "laize", "mm"),
    ("Quantité au mille", "qte_au_mille", "qte_au_mille", "qam"),
    ("Support", "matiere_ref_id", "support_ref_id", "matiere"),
    ("Adhésif", "adhesif_ref_id", "adhesif_ref_id", "matiere"),
    ("Glassine", "glassine_ref_id", "glassine_ref_id", "matiere"),
    ("Mandrin", "mandrin_ref_id", "mandrin_ref_id", "matiere"),
    ("Carton", "carton_ref_id", "carton_ref_id", "matiere"),
)


def _designation(conn, mid: Any) -> str:
    r = conn.execute("SELECT designation FROM matieres_premieres WHERE id = ?", (mid,)).fetchone()
    return (r["designation"] if r and r["designation"] else f"#{mid}")


def ctrl_documents(conn, s, actives: Dict[str, bool], **_) -> List[dict]:
    from app.services.coherence_fiche import controler
    from app.services.fiche_choix import choisir_fiche

    rows = conn.execute(
        """SELECT pe.id AS pe_id, pe.reference AS dossier, pe.ref_produit, pe.laize AS pe_laize,
                  m.nom AS machine,
                  o.of_numero, o.reference AS of_reference, o.machine AS of_machine, o.laize,
                  o.qte_au_mille, o.matiere_ref_id, o.adhesif_ref_id, o.glassine_ref_id,
                  o.mandrin_ref_id, o.carton_ref_id
             FROM planning_entries pe
             JOIN of_imports o ON o.id = pe.of_import_id
             LEFT JOIN machines m ON m.id = pe.machine_id
            WHERE pe.statut IN ('attente', 'en_cours')"""
    ).fetchall()
    out = []
    for r in rows:
        r = dict(r)
        dos, pe_id = r["dossier"], r["pe_id"]
        titre = f"{dos} · {r['machine'] or '—'}"

        if actives.get("documents.of_planning"):
            diffs = _comparer_of_planning(r)
            if diffs:
                out.append(_ecart("documents.of_planning", "dossier", dos, titre,
                                  " ; ".join(diffs) + ".", {"planning_entry_id": pe_id, "of": r["of_numero"]}))

        ft = choisir_fiche(conn, r.get("ref_produit") or r.get("of_reference"),
                           machine=r.get("machine"), laize=r.get("laize"), reference=r.get("of_reference"))
        if not ft:
            continue

        if actives.get("documents.of_fiche"):
            diffs = []
            for libelle, c_of, c_ft, nature in _CHAMPS_OF_FICHE:
                v_of, v_ft = r.get(c_of), ft.get(c_ft)
                if v_of in (None, "") or v_ft in (None, ""):
                    continue
                if nature == "mm":
                    if abs(float(v_of) - float(v_ft)) <= 0.5:
                        continue
                    diffs.append(f"{libelle} {_nombre_fr(v_of)} sur l'OF, {_nombre_fr(v_ft)} sur la fiche")
                elif nature == "qam":
                    if float(v_ft) and abs(float(v_of) - float(v_ft)) / float(v_ft) <= 0.01:
                        continue
                    diffs.append(f"{libelle} {_nombre_fr(round(float(v_of), 2))} sur l'OF, "
                                 f"{_nombre_fr(round(float(v_ft), 2))} sur la fiche")
                else:
                    if int(v_of) == int(v_ft):
                        continue
                    diffs.append(f"{libelle} « {_designation(conn, v_of)} » sur l'OF, "
                                 f"« {_designation(conn, v_ft)} » sur la fiche")
            if diffs:
                out.append(_ecart(
                    "documents.of_fiche", "dossier", dos, titre,
                    f"OF {r['of_numero'] or ''} contre fiche {ft.get('reference') or ft.get('id')} : "
                    + " ; ".join(diffs) + ".",
                    {"planning_entry_id": pe_id, "of": r["of_numero"], "fiche_id": ft.get("id"),
                     "champs": len(diffs)}))

        if actives.get("documents.fiche_incoherente"):
            try:
                v = controler(ft, r.get("laize"))
            except Exception:
                v = {"verdict": "indeterminable"}
            if v.get("verdict") == "incoherent":
                out.append(_ecart(
                    "documents.fiche_incoherente", "fiche", ft.get("id"),
                    f"Fiche {ft.get('reference') or ft.get('id')} · {dos}",
                    str(v.get("message") or "La fiche ne boucle pas géométriquement."),
                    {"fiche_id": ft.get("id"), "planning_entry_id": pe_id,
                     "facteur_erreur": v.get("facteur_erreur")}, cle=f"{ft.get('id')}"))
    return out


def _comparer_of_planning(r: dict) -> List[str]:
    from app.services.fiche_choix import cle_machine

    diffs = []
    m_pl, m_of = cle_machine(r.get("machine")), cle_machine(r.get("of_machine"))
    if m_pl and m_of and m_pl != m_of:
        diffs.append(f"OF prévu sur {r.get('of_machine')}, dossier planifié sur {r.get('machine')}")
    l_pl, l_of = r.get("pe_laize"), r.get("laize")
    if l_pl and l_of and abs(float(l_pl) - float(l_of)) > 0.5:
        diffs.append(f"laize {_nombre_fr(l_of)} sur l'OF, {_nombre_fr(l_pl)} au planning")
    return diffs


# ─── Orchestration ───────────────────────────────────────────────────────────

# Contrôleur -> règles qu'il produit. Un contrôleur dont aucune règle n'est
# active ne tourne pas ; un contrôleur en erreur ne résout aucune de ses règles.
CONTROLEURS: List[tuple] = [
    (ctrl_prod_en_cours_sans_saisie, ("prod.en_cours_sans_saisie",), False),
    (ctrl_prod_retard_prevu, ("prod.retard_prevu",), False),
    (ctrl_prod_quantites, ("prod.quantite_vs_of", "prod.quantite_non_saisie"), False),
    (ctrl_prod_vigilance, ("prod.info_prod_absente", "prod.seuils_sans_explication",
                           "prod.saisie_ouverte"), False),
    (ctrl_flux_bl_departs, ("flux.bl_sans_depart", "flux.depart_sans_bl", "flux.bl_inconnu"), True),
    (ctrl_flux_sortie_stock, ("flux.expedie_sans_sortie",), True),
    (ctrl_flux_date_enlevement, ("flux.date_enlevement",), False),
    (ctrl_documents, ("documents.of_fiche", "documents.of_planning", "documents.fiche_incoherente"), False),
]


def executer(conn, erp=None, releve: str = "") -> Dict[str, Any]:
    """Fait tourner les contrôleurs et met la file à jour. Rend un bilan."""
    reg = charger_reglages(conn)
    s, actives = reg["seuils"], reg["regles"]
    now = maintenant()
    aujourdhui = now.date().isoformat()
    depuis = _iso(now - timedelta(days=int(s["fenetre_jours"])))
    trouves: List[dict] = []
    reussies: set = set()
    erreurs: Dict[str, str] = {}
    for fn, codes, besoin_erp in CONTROLEURS:
        codes_actifs = [c for c in codes if actives.get(c)]
        if not codes_actifs:
            continue
        if besoin_erp and erp is None:
            continue
        try:
            res = fn(conn, s, depuis=depuis, aujourdhui=aujourdhui, erp=erp,
                     releve=releve, actives=actives)
        except Exception as e:  # un contrôleur en panne n'arrête pas les autres
            erreurs[fn.__name__] = str(e)[:300]
            continue
        trouves.extend(e for e in res if e["regle"] in codes_actifs)
        reussies.update(codes_actifs)
    # Une règle désactivée ne tourne plus : ses écarts encore ouverts passent résolus.
    reussies.update(c for c, a in actives.items() if not a)
    bilan = synchroniser(conn, trouves, reussies, _iso(now))
    bilan["erreurs"] = erreurs
    return bilan


def synchroniser(conn, trouves: List[dict], reussies: set, horodatage: str) -> Dict[str, int]:
    vus = set()
    nouveaux = 0
    for e in trouves:
        if e["cle"] in vus:
            continue
        vus.add(e["cle"])
        regle = REGLES[e["regle"]]
        existe = conn.execute("SELECT id, statut FROM coherence_ecarts WHERE cle = ?", (e["cle"],)).fetchone()
        donnees = json.dumps(e["donnees"], ensure_ascii=False, default=str)
        if existe:
            statut = "ouvert" if existe["statut"] == "resolu" else existe["statut"]
            conn.execute(
                """UPDATE coherence_ecarts SET titre=?, detail=?, donnees_json=?, gravite=?,
                          derniere_vue=?, statut=?, resolu_le=CASE WHEN ?='ouvert' AND statut='resolu'
                          THEN NULL ELSE resolu_le END
                    WHERE id=?""",
                (e["titre"], e["detail"], donnees, regle.gravite, horodatage, statut, statut, existe["id"]))
            if existe["statut"] == "resolu":
                nouveaux += 1
        else:
            conn.execute(
                """INSERT INTO coherence_ecarts (cle, regle, famille, objet_type, objet_ref, titre, detail,
                          donnees_json, gravite, statut, premiere_vue, derniere_vue)
                   VALUES (?,?,?,?,?,?,?,?,?,'ouvert',?,?)""",
                (e["cle"], e["regle"], regle.famille, e["objet_type"], e["objet_ref"], e["titre"],
                 e["detail"], donnees, regle.gravite, horodatage, horodatage))
            nouveaux += 1
    resolus = 0
    if reussies:
        marques = ",".join("?" * len(reussies))
        for r in conn.execute(
                f"SELECT id, cle FROM coherence_ecarts WHERE statut <> 'resolu' AND regle IN ({marques})",
                list(reussies)).fetchall():
            if r["cle"] not in vus:
                conn.execute("UPDATE coherence_ecarts SET statut='resolu', resolu_le=? WHERE id=?",
                             (horodatage, r["id"]))
                resolus += 1
    conn.commit()
    ouverts = conn.execute("SELECT COUNT(*) FROM coherence_ecarts WHERE statut='ouvert'").fetchone()[0]
    return {"trouves": len(vus), "nouveaux": nouveaux, "resolus": resolus, "ouverts": int(ouverts)}


def tour(get_db) -> Dict[str, Any]:
    """Appelé par la boucle de `main.py`."""
    from app.services import erp_mirror

    with get_db() as conn:
        if "coherence_ecarts" not in _tables(conn):
            return {"ouverts": 0, "erreurs": {"tour": "table absente"}}
        if erp_mirror.miroir_present():
            releve = erp_mirror.meta().get("releve_le") or erp_mirror.meta().get("importe_le") or ""
            with erp_mirror.get_erp_db() as erp:
                return executer(conn, erp, str(releve))
        return executer(conn, None, "")


# ─── Lecture (écran, agent, pastille) ────────────────────────────────────────

def lister(conn, famille: Optional[str] = None, statut: str = "ouvert", regle: Optional[str] = None,
           objet: Optional[str] = None, limite: int = 200) -> Dict[str, Any]:
    cond, params = [], []
    if statut and statut != "tous":
        cond.append("statut = ?")
        params.append(statut)
    if famille:
        cond.append("famille = ?")
        params.append(famille)
    if regle:
        cond.append("regle = ?")
        params.append(regle)
    if objet:
        cond.append("(objet_ref LIKE ? OR titre LIKE ?)")
        params += [f"%{objet}%", f"%{objet}%"]
    where = ("WHERE " + " AND ".join(cond)) if cond else ""
    rows = conn.execute(
        f"""SELECT id, regle, famille, objet_type, objet_ref, titre, detail, donnees_json, gravite,
                   statut, premiere_vue, derniere_vue, resolu_le, explication, explique_par, explique_le
              FROM coherence_ecarts {where}
             ORDER BY CASE gravite WHEN 'haute' THEN 0 WHEN 'moyenne' THEN 1 ELSE 2 END,
                      premiere_vue DESC
             LIMIT ?""", params + [max(1, min(int(limite or 200), 1000))]).fetchall()
    ecarts = []
    for r in rows:
        d = dict(r)
        try:
            d["donnees"] = json.loads(d.pop("donnees_json") or "{}")
        except Exception:
            d["donnees"] = {}
        rg = REGLES.get(d["regle"])
        d["regle_titre"] = rg.titre if rg else d["regle"]
        d["lien"] = rg.lien if rg else ""
        ecarts.append(d)
    par_regle = {r["regle"]: r["n"] for r in conn.execute(
        "SELECT regle, COUNT(*) AS n FROM coherence_ecarts WHERE statut='ouvert' GROUP BY regle")}
    dernier = conn.execute("SELECT MAX(derniere_vue) FROM coherence_ecarts").fetchone()[0]
    return {"ecarts": ecarts, "ouverts_par_regle": par_regle, "dernier_passage": dernier}


def expliquer(conn, ecart_id: int, explication: str, qui: str) -> dict:
    txt = (explication or "").strip()
    if not txt:
        raise ValueError("Explication vide — dire pourquoi cet écart est normal.")
    r = conn.execute("SELECT id FROM coherence_ecarts WHERE id = ?", (ecart_id,)).fetchone()
    if not r:
        raise LookupError("Écart introuvable.")
    conn.execute(
        """UPDATE coherence_ecarts SET statut='explique', explication=?, explique_par=?, explique_le=?
            WHERE id=?""", (txt[:1000], qui, _iso(maintenant()), ecart_id))
    conn.commit()
    return dict(conn.execute("SELECT * FROM coherence_ecarts WHERE id = ?", (ecart_id,)).fetchone())


def rouvrir(conn, ecart_id: int) -> None:
    conn.execute("""UPDATE coherence_ecarts SET statut='ouvert', explication=NULL, explique_par=NULL,
                           explique_le=NULL WHERE id=? AND statut='explique'""", (ecart_id,))
    conn.commit()


def compter_ouverts(conn, famille: Optional[str] = None) -> tuple:
    """(nombre, signature) pour la pastille."""
    if "coherence_ecarts" not in _tables(conn):
        return 0, None
    q = "SELECT COUNT(*) AS n, MAX(id) AS m FROM coherence_ecarts WHERE statut='ouvert'"
    params: list = []
    if famille:
        q += " AND famille = ?"
        params.append(famille)
    r = conn.execute(q, params).fetchone()
    n = int(r["n"] or 0)
    return n, (str(r["m"]) if n else None)

"""Calage déclaré à la clôture d'un dossier.

Le dossier de prod papier porte trois heures notées à la main : début de
calage, fin de calage, fin de prod. À la clôture, l'écran les propose
pré-remplies depuis les saisies et l'opérateur les recopie.

Ce qu'on fait des heures déclarées
----------------------------------
Les saisies sont corrigées en place, pas doublées d'un second jeu d'heures.
Le temps de calage est calculé par trois chemins (`timings`,
`rapport_dossier`, la mémoire produit) : leur faire lire une surcouche les
ferait diverger à la première évolution. Une saisie déplacée, au contraire,
est lue pareil par tous.

- Début de calage : la première saisie de la catégorie calage du dossier est
  déplacée. Si l'heure déclarée précède le « 01 Début de production » qui la
  précède immédiatement, le 01 suit — le papier dit que le dossier a démarré
  plus tôt.
- Fin de calage : la première saisie de production qui suit le calage est
  déplacée. Si l'opérateur n'a jamais cliqué « Production », un 03 est
  inséré, à condition que l'heure tombe dans le calage resté ouvert.
- Fin de prod : c'est l'heure de la saisie de clôture elle-même.

Une heure qui enjamberait une autre saisie n'est PAS appliquée : réordonner
les saisies d'un opérateur à sa place serait pire que de laisser l'écart. La
déclaration reste dans `dossier_calages_declares`, avec le motif, et Retour
de prod la montre.

Les heures d'origine sont dans la même table : l'écart entre mesuré et
déclaré se lit toujours.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from statistics import median
from typing import Any, Dict, List, Optional

from config import (
    CODE_ANNUL_DOS, CODE_DEBUT_DOS, CODE_FIN_DOS, CODE_PRODUCTION, CALAGE_ALERTE_FACTEUR,
    classify_operation,
)
from database import parse_datetime

logger = logging.getLogger(__name__)

CAT_CALAGE = "calage"
CAT_PRODUCTION = "production"
FMT = "%Y-%m-%dT%H:%M:%S"


def _cat(r) -> str:
    return str(r["operation_category"] or "").strip().lower()


def _code(r) -> str:
    return str(r["operation_code"] or "").strip()


def _dt(v) -> Optional[datetime]:
    if isinstance(v, datetime):
        return v
    return parse_datetime(v) if v else None


def _iso(d: Optional[datetime]) -> Optional[str]:
    return d.strftime(FMT) if d else None


def _hm(v) -> str:
    d = _dt(v)
    return d.strftime("%d/%m %H:%M") if d else "?"


def _meme_dossier(r, no_dossier: str) -> bool:
    return str(r["no_dossier"] or "").strip() == str(no_dossier or "").strip()


def _saisies_machine(conn, machine: str, depuis: str) -> List[Any]:
    return conn.execute(
        """SELECT id, operateur, date_operation, operation, operation_code,
                  operation_category, no_dossier, client, designation, fin_dossier
             FROM production_data
            WHERE COALESCE(est_annule, 0) = 0
              AND trim(machine) = trim(?)
              AND date_operation >= ?
            ORDER BY date_operation ASC, id ASC""",
        (machine, depuis),
    ).fetchall()


def _debut_perimetre(conn, no_dossier: str, machine: str, avant_id: Optional[int]) -> Optional[str]:
    """Première saisie du dossier sur la machine depuis sa dernière clôture.

    Un dossier rouvert après une clôture repart de zéro : le papier du
    nouveau passage ne parle pas du calage de l'ancien.
    """
    params: list = [no_dossier, machine, CODE_FIN_DOS]
    filtre_id = ""
    if avant_id:
        filtre_id = " AND id <> ?"
        params.append(avant_id)
    derniere_cloture = conn.execute(
        f"""SELECT MAX(date_operation) FROM production_data
             WHERE trim(no_dossier) = trim(?) AND trim(machine) = trim(?)
               AND operation_code = ? AND COALESCE(fin_dossier, 0) = 1
               AND COALESCE(est_annule, 0) = 0{filtre_id}""",
        params,
    ).fetchone()[0]
    row = conn.execute(
        """SELECT MIN(date_operation) FROM production_data
            WHERE trim(no_dossier) = trim(?) AND trim(machine) = trim(?)
              AND COALESCE(est_annule, 0) = 0
              AND date_operation > COALESCE(?, '')""",
        (no_dossier, machine, derniere_cloture),
    ).fetchone()
    return row[0] if row else None


def _analyser(conn, no_dossier: str, machine: str, maintenant: datetime,
              cloture_id: Optional[int] = None) -> Dict[str, Any]:
    """Lit les saisies et en déduit les trois bornes mesurées.

    `cloture_id` est la clôture en cours, déjà insérée à l'heure de fin de prod
    retenue. Elle est écartée : elle ne borne ni le périmètre, ni les
    déplacements (`heure_fin_prod` a vérifié qu'elle suit la fin de calage), ni
    le calage mesuré — placée avant un « Production » cliqué en retard, elle
    raccourcirait la dernière plage de calage et bloquerait sa correction."""
    depuis = _debut_perimetre(conn, no_dossier, machine, cloture_id)
    vide = {"rows": [], "debut": None, "fin": None, "calage_min": 0.0, "depuis": depuis}
    if not depuis:
        return vide
    rows = [r for r in _saisies_machine(conn, machine, depuis) if r["id"] != cloture_id]
    i_debut = next((i for i, r in enumerate(rows)
                    if _meme_dossier(r, no_dossier) and _cat(r) == CAT_CALAGE), None)
    i_fin = None
    if i_debut is not None:
        i_fin = next((i for i in range(i_debut + 1, len(rows))
                      if _meme_dossier(rows[i], no_dossier) and _cat(rows[i]) == CAT_PRODUCTION),
                     None)

    # Calage mesuré : chaque saisie de calage du dossier dure jusqu'à la
    # saisie suivante de la machine, la dernière jusqu'à maintenant.
    calage = 0.0
    for i, r in enumerate(rows):
        if not (_meme_dossier(r, no_dossier) and _cat(r) == CAT_CALAGE):
            continue
        a = _dt(r["date_operation"])
        b = _dt(rows[i + 1]["date_operation"]) if i + 1 < len(rows) else maintenant
        if a and b and b > a:
            calage += (b - a).total_seconds() / 60.0

    return {"rows": rows, "debut": i_debut, "fin": i_fin,
            "calage_min": round(calage, 1), "depuis": depuis}


def mediane_calage_machine(conn, machine: str) -> Optional[float]:
    """Repère pour signaler un calage aberrant : médiane des 60 dernières
    séries clôturées de la machine. Les calages à zéro (non saisis) ou de plus
    de 8 h (oubli de clic) n'en font pas partie."""
    try:
        rows = conn.execute(
            """SELECT temps_calage_min FROM produit_series
                WHERE trim(machine) = trim(?) AND temps_calage_min > 1
                  AND temps_calage_min <= 480
                ORDER BY date_fin DESC LIMIT 60""",
            (machine,),
        ).fetchall()
    except Exception:
        return None
    vals = [float(r[0]) for r in rows if r[0] is not None]
    return round(median(vals), 1) if len(vals) >= 5 else None


def proposer(conn, no_dossier: str, machine: str, maintenant: datetime) -> Dict[str, Any]:
    """Les trois heures à pré-remplir à la clôture, et de quoi juger."""
    a = _analyser(conn, no_dossier, machine, maintenant)
    rows = a["rows"]
    debut = rows[a["debut"]]["date_operation"] if a["debut"] is not None else None
    fin = rows[a["fin"]]["date_operation"] if a["fin"] is not None else None
    jours = sorted({str(r["date_operation"])[:10] for r in rows if _meme_dossier(r, no_dossier)}
                   | {maintenant.strftime("%Y-%m-%d")})
    mediane = mediane_calage_machine(conn, machine)
    # Compteurs pour les métrages de l'écran : celui d'avant le calage (le 01,
    # ou la fin du dossier précédent) et celui relevé en fin de calage. Le
    # compteur de fin de prod, l'opérateur vient de le saisir à l'écran 1.
    depart = None
    borne = debut or next((r["date_operation"] for r in rows
                           if _meme_dossier(r, no_dossier) and _code(r) == CODE_DEBUT_DOS), None)
    if borne:
        params = (CODE_DEBUT_DOS, CODE_FIN_DOS, CODE_ANNUL_DOS)
        ligne = conn.execute(
            f"""SELECT {_SQL_COMPTEUR} AS ctr FROM production_data
                 WHERE trim(machine) = trim(?) AND COALESCE(est_annule, 0) = 0
                   AND date_operation <= ? AND ({_SQL_COMPTEUR}) IS NOT NULL
                 ORDER BY date_operation DESC, id DESC LIMIT 1""",
            params + (machine, borne) + params,
        ).fetchone()
        depart = float(ligne["ctr"]) if ligne and ligne["ctr"] is not None else None
    ctr_fin_calage = None
    if a["fin"] is not None:
        r = conn.execute("SELECT metrage_compteur FROM production_data WHERE id=?",
                         (rows[a["fin"]]["id"],)).fetchone()
        ctr_fin_calage = float(r[0]) if r and r[0] is not None else None
    return {
        "compteur_debut": depart,
        "compteur_fin_calage": ctr_fin_calage,
        "debut_calage": debut,
        "fin_calage": fin,
        "fin_prod": _iso(maintenant),
        "calage_mesure_min": a["calage_min"],
        "mediane_machine_min": mediane,
        "seuil_alerte_min": round(mediane * CALAGE_ALERTE_FACTEUR, 1) if mediane else None,
        "jours": jours,
        "derniere_saisie": rows[-1]["date_operation"] if rows else None,
    }


def lire_declaration(body_calage: Any) -> Optional[Dict[str, datetime]]:
    """Valide les trois heures envoyées par l'écran. Rend None si l'écran
    n'en a pas envoyé ; lève ValueError avec un message affichable sinon."""
    if not isinstance(body_calage, dict):
        return None
    out = {}
    for cle, libelle in (("debut_calage", "Début de calage"),
                         ("fin_calage", "Fin de calage"),
                         ("fin_prod", "Fin de prod")):
        d = _dt(body_calage.get(cle))
        if d is None:
            raise ValueError(f"{libelle} manquant — recopiez l'heure du dossier de prod.")
        out[cle] = d.replace(second=0, microsecond=0)
    if out["debut_calage"] > out["fin_calage"]:
        raise ValueError("La fin de calage ne peut pas précéder le début de calage.")
    if not out["fin_calage"] <= out["fin_prod"]:
        raise ValueError("La fin de prod ne peut pas précéder la fin de calage.")
    return out


def heure_fin_prod(conn, no_dossier: str, machine: str, declare: Dict[str, datetime],
                   maintenant: datetime):
    """Heure à donner à la saisie de clôture. Rend (heure_iso, motif) : le
    motif est renseigné quand la déclaration n'a pas pu être retenue.

    La clôture doit suivre la dernière saisie de la machine. Quand cette
    dernière saisie est le « Production » cliqué en retard, qui va prendre
    l'heure de fin de calage déclarée, c'est à sa place corrigée qu'on compare
    — sinon un oubli de clic empêcherait de corriger l'autre."""
    P = declare["fin_prod"]
    if P > maintenant:
        return None, "Fin de prod déclarée dans le futur — heure du clic conservée."
    a = _analyser(conn, no_dossier, machine, maintenant)
    rows = a["rows"]
    if not rows:
        return _iso(P), None
    derniere = rows[-1]
    borne = _dt(derniere["date_operation"])
    if a["fin"] == len(rows) - 1 and _place_libre(rows, a["fin"], declare["fin_calage"]):
        borne = declare["fin_calage"]
    # Les heures déclarées sont à la minute, les saisies à la seconde : une
    # fin de prod notée 16:10 n'est pas « avant » une saisie de 16:10:35. La
    # clôture se place alors juste après elle.
    if borne and P < borne and P.replace(second=0) == borne.replace(second=0, microsecond=0):
        return _iso(borne.replace(microsecond=0) + timedelta(seconds=1)), None
    if borne and P < borne:
        return None, (f"Fin de prod {_hm(P)} antérieure à la saisie "
                      f"« {derniere['operation']} » de {_hm(derniere['date_operation'])}.")
    return _iso(P), None


def _deplacer(conn, saisie_id: int, quand: datetime, auteur: str, note: str, maintenant: datetime):
    conn.execute(
        """UPDATE production_data
              SET date_operation = ?, modifie_par = ?, modifie_le = ?, modifie_note = ?
            WHERE id = ?""",
        (_iso(quand), auteur, _iso(maintenant), note, saisie_id),
    )


def _meme_minute(iso, quand: datetime) -> bool:
    """La saisie tombe-t-elle dans la minute déclarée ?"""
    return str(iso or "")[:16] == _iso(quand)[:16]


def _place_libre(rows, i, quand: datetime) -> bool:
    """La saisie d'indice i peut-elle prendre l'heure `quand` sans dépasser
    ses voisines ?"""
    avant = _dt(rows[i - 1]["date_operation"]) if i > 0 else None
    apres = _dt(rows[i + 1]["date_operation"]) if i + 1 < len(rows) else None
    return (avant is None or avant < quand) and (apres is None or quand < apres)


def appliquer(conn, *, no_dossier: str, machine: str, declare: Dict[str, datetime],
              saisie_cloture_id: int, fin_prod_mesure: str,
              fin_prod_motif: Optional[str], auteur: str, maintenant: datetime,
              signalement: Optional[str] = None) -> Dict[str, Any]:
    """Corrige les saisies d'après les heures déclarées et enregistre la
    déclaration. La saisie de clôture est déjà insérée, à son heure retenue.
    Ne commite pas : c'est à l'appelant."""
    a = _analyser(conn, no_dossier, machine, maintenant, cloture_id=saisie_cloture_id)
    rows = [dict(r) for r in a["rows"]]
    i_debut, i_fin = a["debut"], a["fin"]
    debut_mesure = rows[i_debut]["date_operation"] if i_debut is not None else None
    fin_mesure = rows[i_fin]["date_operation"] if i_fin is not None else None
    motifs: List[str] = []
    note = "Heure corrigée à la clôture d'après le dossier de prod"

    # ── Début de calage ─────────────────────────────────────────────────────
    D = declare["debut_calage"]
    debut_ok = False
    if i_debut is None:
        motifs.append("Aucune saisie de calage sur le dossier : début non appliqué.")
    elif _meme_minute(rows[i_debut]["date_operation"], D):
        # Les heures déclarées sont à la minute : une saisie faite dans cette
        # minute est déjà à la bonne heure, ses secondes ne sont pas un écart.
        debut_ok = True
    elif _place_libre(rows, i_debut, D):
        _deplacer(conn, rows[i_debut]["id"], D, auteur, note, maintenant)
        rows[i_debut]["date_operation"] = _iso(D)
        debut_ok = True
    elif (i_debut > 0 and _code(rows[i_debut - 1]) == CODE_DEBUT_DOS
          and _meme_dossier(rows[i_debut - 1], no_dossier)
          and D < _dt(rows[i_debut - 1]["date_operation"])
          and (i_debut < 2 or _dt(rows[i_debut - 2]["date_operation"]) < D)
          and (i_debut + 1 >= len(rows) or D < _dt(rows[i_debut + 1]["date_operation"]))):
        # Calage commencé avant le clic « Début de production » : le 01 suit.
        for k in (i_debut - 1, i_debut):
            _deplacer(conn, rows[k]["id"], D, auteur, note, maintenant)
            rows[k]["date_operation"] = _iso(D)
        debut_ok = True
    else:
        motifs.append(f"Début de calage {_hm(D)} : enjamberait une autre saisie, non appliqué.")

    # ── Fin de calage ───────────────────────────────────────────────────────
    F = declare["fin_calage"]
    fin_ok = False
    if i_fin is not None:
        if _meme_minute(rows[i_fin]["date_operation"], F):
            fin_ok = True
        elif _place_libre(rows, i_fin, F):
            _deplacer(conn, rows[i_fin]["id"], F, auteur, note, maintenant)
            rows[i_fin]["date_operation"] = _iso(F)
            fin_ok = True
        else:
            motifs.append(f"Fin de calage {_hm(F)} : enjamberait une autre saisie, non appliquée.")
    elif i_debut is not None:
        # Jamais de clic « Production » : on insère le 03, s'il tombe dans un
        # calage du dossier resté ouvert.
        avant = [i for i, r in enumerate(rows) if _dt(r["date_operation"]) < F]
        k = avant[-1] if avant else None
        suivante = rows[k + 1] if k is not None and k + 1 < len(rows) else None
        if (k is not None and k >= i_debut and _cat(rows[k]) == CAT_CALAGE
                and _meme_dossier(rows[k], no_dossier)
                and (suivante is None or F < _dt(suivante["date_operation"]))):
            ref = rows[k]
            cl = classify_operation(CODE_PRODUCTION)
            op_str = f"{CODE_PRODUCTION} - {cl.get('label') or 'Production'}"
            cur = conn.execute(
                """INSERT INTO production_data
                   (operateur, date_operation, operation, operation_code,
                    operation_severity, operation_category, machine, no_dossier,
                    client, designation, quantite_a_traiter, quantite_traitee,
                    service, commentaire, data, est_manuel,
                    modifie_par, modifie_le, modifie_note)
                   VALUES (?,?,?,?,?,?,?,?,?,?,0,0,'fabrication',NULL,?,1,?,?,?)""",
                (ref["operateur"], _iso(F), op_str, CODE_PRODUCTION,
                 cl.get("severity") or "info", cl.get("category") or CAT_PRODUCTION,
                 machine, no_dossier, ref["client"], ref["designation"],
                 json.dumps({"operateur": ref["operateur"], "date_operation": _iso(F),
                             "operation": op_str, "no_dossier": no_dossier,
                             "machine": machine}),
                 auteur, _iso(maintenant),
                 "Fin de calage déclarée à la clôture — saisie Production manquante"),
            )
            try:
                from app.services.lien_saisie_planning import rattacher
                rattacher(conn, cur.lastrowid)
            except Exception:
                logger.exception("[calage] 03 inséré non rattaché au planning")
            fin_ok = True
        else:
            motifs.append(f"Fin de calage {_hm(F)} : hors du calage ouvert, non appliquée.")
    else:
        motifs.append("Aucune saisie de calage sur le dossier : fin non appliquée.")

    if fin_prod_motif:
        motifs.append(fin_prod_motif)

    conn.execute(
        """INSERT INTO dossier_calages_declares
           (no_dossier, machine, saisie_cloture_id,
            debut_calage_declare, fin_calage_declare, fin_prod_declare,
            debut_calage_mesure, fin_calage_mesure, fin_prod_mesure, calage_mesure_min,
            debut_applique, fin_calage_applique, fin_prod_applique,
            motifs_non_appliques, declare_par, declare_le)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (no_dossier, machine, saisie_cloture_id,
         _iso(D), _iso(F), _iso(declare["fin_prod"]),
         debut_mesure, fin_mesure, fin_prod_mesure, a["calage_min"],
         1 if debut_ok else 0, 1 if fin_ok else 0, 0 if fin_prod_motif else 1,
         json.dumps(motifs, ensure_ascii=False) if motifs else None,
         auteur, _iso(maintenant)),
    )
    # Signalement d'un chiffrage incohérent : écrit à part, la colonne vient
    # d'une migration plus récente que la table.
    signalement = (signalement or "").strip()[:1000]
    if signalement:
        try:
            conn.execute(
                "UPDATE dossier_calages_declares SET signalement=? WHERE id=last_insert_rowid()",
                (signalement,))
        except Exception:
            logger.exception("[calage] signalement non enregistré")
    return {"debut_applique": debut_ok, "fin_calage_applique": fin_ok,
            "fin_prod_applique": not fin_prod_motif, "motifs": motifs}


# ─── Lecture : ce que le calage a vraiment coûté ─────────────────────────────

def _table_existe(conn, nom: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nom,)
    ).fetchone() is not None


def declaration(conn, no_dossier: str) -> Optional[Dict[str, Any]]:
    """La dernière déclaration de calage du dossier, avec l'écart au mesuré."""
    if not _table_existe(conn, "dossier_calages_declares"):
        return None
    r = conn.execute(
        """SELECT * FROM dossier_calages_declares
            WHERE trim(no_dossier) = trim(?) ORDER BY declare_le DESC, id DESC LIMIT 1""",
        (no_dossier,),
    ).fetchone()
    if not r:
        return None

    def minutes(a, b):
        da, db = _dt(a), _dt(b)
        return round((db - da).total_seconds() / 60.0, 1) if da and db and db > da else None

    declare = minutes(r["debut_calage_declare"], r["fin_calage_declare"])
    mesure = r["calage_mesure_min"]
    try:
        motifs = json.loads(r["motifs_non_appliques"]) if r["motifs_non_appliques"] else []
    except (TypeError, ValueError):
        motifs = []
    return {
        "debut_calage": r["debut_calage_declare"],
        "fin_calage": r["fin_calage_declare"],
        "fin_prod": r["fin_prod_declare"],
        "minutes_declarees": declare,
        "minutes_mesurees": mesure,
        "ecart_min": (round(declare - mesure, 1)
                      if declare is not None and mesure is not None else None),
        "applique": bool(r["debut_applique"] and r["fin_calage_applique"] and r["fin_prod_applique"]),
        "motifs_non_appliques": motifs,
        "signalement": (r["signalement"] if "signalement" in r.keys() else None) or None,
        "declare_par": r["declare_par"],
        "declare_le": r["declare_le"],
    }


# Le compteur porté par une saisie, selon ce qu'elle relève : le début de
# dossier, sa fin (ou son annulation), ou un relevé intermédiaire.
_SQL_COMPTEUR = """CASE
    WHEN operation_code = ? THEN COALESCE(metrage_total_debut, metrage_prevu)
    WHEN operation_code IN (?, ?) THEN COALESCE(metrage_total_fin, metrage_reel)
    ELSE metrage_compteur END"""


def gache_calage(conn, no_dossier: str) -> Dict[str, Any]:
    """Mètres passés au calage, mesurés au compteur.

    Pour chaque « Production » du dossier qui ferme un calage et porte un
    relevé : compteur à ce moment − dernier compteur relevé avant le début de
    la plage de calage (le 01, ou la fin du dossier précédent). Un relevé
    manquant laisse la plage hors du total, jamais estimée.
    """
    params_cpt = (CODE_DEBUT_DOS, CODE_FIN_DOS, CODE_ANNUL_DOS)
    prods = conn.execute(
        """SELECT id, machine, date_operation, metrage_compteur FROM production_data
            WHERE trim(no_dossier) = trim(?) AND operation_category = ?
              AND COALESCE(est_annule, 0) = 0
            ORDER BY date_operation, id""",
        (no_dossier, CAT_PRODUCTION),
    ).fetchall()
    plages: List[Dict[str, Any]] = []
    sans_releve = 0
    for p in prods:
        # Remonter la plage de calage qui précède ce « Production ».
        avant = conn.execute(
            """SELECT date_operation, operation_category FROM production_data
                WHERE trim(machine) = trim(?) AND COALESCE(est_annule, 0) = 0
                  AND (date_operation < ? OR (date_operation = ? AND id < ?))
                ORDER BY date_operation DESC, id DESC LIMIT 50""",
            (p["machine"], p["date_operation"], p["date_operation"], p["id"]),
        ).fetchall()
        debut_plage = None
        for r in avant:
            if _cat(r) != CAT_CALAGE:
                break
            debut_plage = r["date_operation"]
        if debut_plage is None:
            continue  # ce « Production » ne ferme pas un calage
        if p["metrage_compteur"] is None:
            sans_releve += 1
            continue
        depart = conn.execute(
            f"""SELECT {_SQL_COMPTEUR} AS ctr FROM production_data
                 WHERE trim(machine) = trim(?) AND COALESCE(est_annule, 0) = 0
                   AND date_operation <= ? AND ({_SQL_COMPTEUR}) IS NOT NULL
                 ORDER BY date_operation DESC, id DESC LIMIT 1""",
            params_cpt + (p["machine"], debut_plage) + params_cpt,
        ).fetchone()
        if not depart or depart["ctr"] is None:
            sans_releve += 1
            continue
        metres = float(p["metrage_compteur"]) - float(depart["ctr"])
        if metres < 0:
            sans_releve += 1
            continue
        plages.append({"debut": debut_plage, "fin": p["date_operation"],
                       "compteur_debut": float(depart["ctr"]),
                       "compteur_fin": float(p["metrage_compteur"]),
                       "metres": round(metres, 1)})
    return {
        "metres": round(sum(x["metres"] for x in plages), 1) if plages else None,
        "plages": plages,
        "plages_sans_releve": sans_releve,
    }


def prevu_devis(conn, no_dossier: str) -> Optional[Dict[str, Any]]:
    """Le calage chiffré par le devis rattaché au dossier (Rentabilité).

    Le devis sépare calage outil et calage impression ; MyProd les range tous
    deux dans la catégorie calage. On compare donc à la SOMME des deux postes,
    en temps comme en métrage — la règle de `rentabilite._calage_theorique`.
    Le recalage par palier ne touche pas au calage : il ne dépend pas de la
    quantité."""
    if not (_table_existe(conn, "rent_prod_links") and _table_existe(conn, "rent_links")
            and _table_existe(conn, "devis")):
        return None
    d = conn.execute(
        """SELECT d.* FROM rent_prod_links p
             JOIN rent_links l ON l.planning_entry_id = p.planning_entry_id
             JOIN devis d ON d.id = l.devis_id
            WHERE trim(p.no_dossier) = trim(?)
            ORDER BY p.planning_entry_id DESC LIMIT 1""",
        (no_dossier,),
    ).fetchone()
    if not d:
        return None
    cols = set(d.keys())

    def v(nom):
        return float(d[nom] or 0) if nom in cols else 0.0

    return {
        "devis_id": d["id"],
        "minutes": round(v("temps_calage_mn") + v("temps_calage_impression_mn"), 1),
        "metres": round(v("metrage_calage_ml") + v("metrage_calage_impression_ml"), 1),
    }


def bilan(conn, no_dossier: str, minutes_calage: float) -> Dict[str, Any]:
    """Calage et gâche du dossier : déclaré, mesuré, prévu.

    `minutes_calage` est le temps de la catégorie calage tel que le compte-rendu
    le calcule : après correction à la clôture, c'est la plage déclarée plus
    les changements faits en cours de production."""
    def pct(reel, prevu):
        return round((reel - prevu) / prevu * 100.0, 1) if reel is not None and prevu else None

    g = gache_calage(conn, no_dossier)
    dv = prevu_devis(conn, no_dossier)
    return {
        "minutes": round(minutes_calage, 1) if minutes_calage else None,
        "declaration": declaration(conn, no_dossier),
        "gache": g,
        "devis": dv,
        "ecart_devis_minutes_pct": pct(minutes_calage or None, dv and dv["minutes"]),
        "ecart_devis_metres_pct": pct(g["metres"], dv and dv["metres"]),
    }


# ─── Correction depuis MyProd › Erreurs & Qualité ────────────────────────────

def lire_declaration_id(conn, declaration_id: int) -> Optional[Dict[str, Any]]:
    r = conn.execute("SELECT * FROM dossier_calages_declares WHERE id=?", (declaration_id,)).fetchone()
    return dict(r) if r else None


def marquer_traite(conn, declaration_id: int, auteur: str, maintenant: datetime) -> None:
    """La déclaration sort de la file des écarts (validée ou corrigée). Ne commite pas."""
    conn.execute(
        "UPDATE dossier_calages_declares SET traite_le=?, traite_par=? WHERE id=?",
        (_iso(maintenant), auteur, declaration_id))


def forcer_heures(conn, declaration_id: int, declare: Dict[str, datetime], auteur: str,
                  maintenant: datetime, simuler: bool = False) -> Dict[str, Any]:
    """Reporte les trois heures sur les saisies, sans la garde qui refuse
    d'enjamber une autre saisie.

    À la clôture, une heure qui enjambait une saisie n'était pas appliquée :
    l'opérateur n'avait personne à qui demander. Ici c'est un responsable qui
    décide, après avoir vu l'aperçu (`simuler=True`) : les saisies bornes
    prennent les heures déclarées, et celles qu'elles enjambent changent de
    côté (un changement de plaque noté après la fin de calage devient un
    changement en cours de production). Rien n'est supprimé.

    Rend {"changements": [...], "inseree": bool}. Ne commite pas."""
    decl = lire_declaration_id(conn, declaration_id)
    if not decl:
        raise LookupError("Déclaration introuvable.")
    no_dossier, machine = decl["no_dossier"], decl["machine"]
    cloture_id = decl.get("saisie_cloture_id")
    a = _analyser(conn, no_dossier, machine, maintenant, cloture_id=cloture_id)
    rows = [dict(r) for r in a["rows"]]
    i_debut, i_fin = a["debut"], a["fin"]
    D, F, P = declare["debut_calage"], declare["fin_calage"], declare["fin_prod"]
    note = "Heures du dossier de prod reportées depuis Erreurs & Qualité"
    changements: List[Dict[str, Any]] = []

    def changer(r, quand):
        if str(r["date_operation"])[:16] == _iso(quand)[:16]:
            return
        changements.append({"saisie_id": r["id"], "operation": r["operation"],
                            "avant": r["date_operation"], "apres": _iso(quand)})
        if not simuler:
            _deplacer(conn, r["id"], quand, auteur, note, maintenant)

    if i_debut is None:
        raise ValueError("Aucune saisie de calage sur ce dossier : rien à déplacer.")
    changer(rows[i_debut], D)
    # Le 01 du dossier ne peut pas suivre le début du calage.
    for r in rows[:i_debut]:
        if _meme_dossier(r, no_dossier) and _code(r) == CODE_DEBUT_DOS and _dt(r["date_operation"]) > D:
            changer(r, D)

    inseree = False
    if i_fin is not None:
        changer(rows[i_fin], F)
    else:
        inseree = True
        changements.append({"saisie_id": None, "operation": f"{CODE_PRODUCTION} - Production (ajoutée)",
                            "avant": None, "apres": _iso(F)})
        if not simuler:
            ref = rows[i_debut]
            cl = classify_operation(CODE_PRODUCTION)
            op_str = f"{CODE_PRODUCTION} - {cl.get('label') or 'Production'}"
            conn.execute(
                """INSERT INTO production_data
                   (operateur, date_operation, operation, operation_code,
                    operation_severity, operation_category, machine, no_dossier,
                    client, designation, quantite_a_traiter, quantite_traitee,
                    service, data, est_manuel, modifie_par, modifie_le, modifie_note)
                   VALUES (?,?,?,?,?,?,?,?,?,?,0,0,'fabrication',?,1,?,?,?)""",
                (ref["operateur"], _iso(F), op_str, CODE_PRODUCTION,
                 cl.get("severity") or "info", cl.get("category") or CAT_PRODUCTION,
                 machine, no_dossier, ref["client"], ref["designation"],
                 json.dumps({"date_operation": _iso(F), "operation": op_str,
                             "no_dossier": no_dossier, "machine": machine}),
                 auteur, _iso(maintenant), note))

    if cloture_id:
        r = conn.execute("SELECT id, operation, date_operation FROM production_data WHERE id=?",
                         (cloture_id,)).fetchone()
        if r:
            changer(dict(r), P)

    if not simuler:
        conn.execute(
            """UPDATE dossier_calages_declares
                  SET debut_calage_declare=?, fin_calage_declare=?, fin_prod_declare=?,
                      debut_applique=1, fin_calage_applique=1, fin_prod_applique=1,
                      motifs_non_appliques=NULL
                WHERE id=?""",
            (_iso(D), _iso(F), _iso(P), declaration_id))
        marquer_traite(conn, declaration_id, auteur, maintenant)
    return {"changements": changements, "inseree": inseree}

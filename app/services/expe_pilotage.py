"""
MyExpé — pilotage amont des expéditions.

Ce que cet écran répond, dans l'ordre où la question se pose : pour ce qui va
sortir de production dans les prochains jours, le transport est-il commandé,
est-ce parti, le bon de livraison est-il fait ?

Aujourd'hui la réponse n'existe nulle part avant le dernier moment : un départ
MyExpé n'est saisi qu'une fois le BL édité, donc on attend la fin de production
pour réserver un camion. Ce module construit la vue qui manque, en croisant
trois sources et une seule fois :

  - le planning MySifa      → ce qui va sortir, et quand la prod finit ;
  - le carnet RVGI          → la date d'expédition demandée et l'adresse de
                              livraison de la commande (`cde_ligne.amje`,
                              `lrs/lcp/lville`), plus les BL déjà édités
                              (`liv_entete` via `liv_ligne.numcde`) ;
  - `expe_departs`          → les jalons déjà posés.

Trois partis pris.

**Une ligne = un envoi, pas un dossier.** On commande un camion pour un client
à une adresse à une date, pas pour un dossier de production. Trois dossiers qui
partent ensemble chez le même client comptent leurs palettes ensemble — sinon
le nombre de palettes de la ligne ne veut rien dire, et c'est précisément le
chiffre dont les transporteurs ont besoin.

**Le nombre de palettes est estimé, jamais inventé.** Il vient de
`palettes_estimation` (le même calcul que le camion du planning). Quand une
fiche technique est incomplète, l'estimation est marquée partielle et la raison
est affichée — une case vide sans explication envoie chercher dans trois
écrans.

**Le BL ne se recopie pas.** Il se lit dans RVGI et dans `no_bl`. Une donnée
qui a déjà une source ne devient pas une case à cocher de plus.

Le miroir RVGI peut être absent (instance neuve, synchro en retard) : dans ce
cas le tableau s'affiche quand même, sans les colonnes qui en dépendent, et le
dit — `rvgi.present` vaut False.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from app.services import palettes_estimation

_log = logging.getLogger(__name__)

TABLE_PARAMS = "expe_pilotage_params"

# Numéro de commande RVGI, tel que `_OF_RACINE_RE` le reconnaît partout
# ailleurs dans MySifa. Une référence de dossier en porte parfois plusieurs
# ("9932327+29+30" n'en donne qu'un ; "9932376-377" non plus) : on prend tous
# ceux qui ont la forme complète, on ne reconstitue pas les abrégés.
_RE_CDE_RVGI = re.compile(r"\b(99\d{5})\b")

DEFAUTS: Dict[str, Any] = {
    # Fenêtre du tableau, en jours à venir.
    "horizon_jours": 21.0,
    # Préavis de réservation : à J-N avant la date d'expédition visée, la ligne
    # passe en « à commander ». Deux valeurs, parce que réserver une messagerie
    # et affréter un camion complet ne se décident pas au même moment.
    "preavis_messagerie_jours": 2.0,
    "preavis_affretement_jours": 5.0,
    # Au-delà de ce nombre de palettes, l'envoi est traité en affrètement.
    "seuil_affretement_palettes": 6.0,
}

BORNES = {
    "horizon_jours": (1.0, 120.0),
    "preavis_messagerie_jours": (0.0, 30.0),
    "preavis_affretement_jours": (0.0, 60.0),
    "seuil_affretement_palettes": (1.0, 99.0),
}


# ─── Paramètres ──────────────────────────────────────────────────────────────

def _table_existe(conn, nom: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nom,)
    ).fetchone()
    return row is not None


def charger_params(conn) -> Dict[str, float]:
    """Réglages du pilotage. Toujours complet : les défauts comblent les trous."""
    vals: Dict[str, Any] = dict(DEFAUTS)
    if _table_existe(conn, TABLE_PARAMS):
        try:
            for r in conn.execute(f"SELECT cle, valeur FROM {TABLE_PARAMS}").fetchall():
                vals[r["cle"]] = r["valeur"]
        except Exception:
            pass
    out: Dict[str, float] = {}
    for cle in DEFAUTS:
        try:
            v = float(vals.get(cle))
        except (TypeError, ValueError):
            v = float(DEFAUTS[cle])
        lo, hi = BORNES[cle]
        out[cle] = min(max(v, lo), hi)
    return out


def enregistrer_params(conn, valeurs: Dict[str, Any]) -> Dict[str, float]:
    """Écrit les réglages fournis (les autres ne bougent pas) et relit le tout."""
    conn.execute(
        f"CREATE TABLE IF NOT EXISTS {TABLE_PARAMS} "
        "(cle TEXT PRIMARY KEY NOT NULL, valeur TEXT NOT NULL)"
    )
    for cle in DEFAUTS:
        if cle not in valeurs or valeurs[cle] is None or valeurs[cle] == "":
            continue
        try:
            v = float(str(valeurs[cle]).replace(",", "."))
        except (TypeError, ValueError):
            raise ValueError(f"Valeur invalide pour {cle}.")
        lo, hi = BORNES[cle]
        if v < lo or v > hi:
            raise ValueError(
                f"Valeur hors bornes pour {cle} (attendu entre {lo:g} et {hi:g})."
            )
        conn.execute(
            f"INSERT INTO {TABLE_PARAMS} (cle, valeur) VALUES (?,?) "
            "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
            (cle, f"{v:g}"),
        )
    conn.commit()
    return charger_params(conn)


# ─── Petits utilitaires ──────────────────────────────────────────────────────

def _norm(s: Any) -> str:
    t = unicodedata.normalize("NFD", str(s or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def _jour(v: Any) -> Optional[str]:
    """Les dates RVGI portent une heure ; MySifa stocke tantôt l'un tantôt
    l'autre. On tronque à 10 caractères et on refuse ce qui n'a pas la forme."""
    s = str(v or "").strip()[:10]
    if re.match(r"^\d{4}-\d{2}-\d{2}$", s):
        return s
    return None


def _d(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    try:
        return date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except (ValueError, TypeError):
        return None


def _cdes_rvgi(*textes: Any) -> List[str]:
    """Numéros de commande RVGI trouvés dans une référence de dossier."""
    out: List[str] = []
    for t in textes:
        for m in _RE_CDE_RVGI.findall(str(t or "")):
            if m not in out:
                out.append(m)
    return out


def _dept(cp: Any) -> str:
    s = re.sub(r"\s+", "", str(cp or "")).upper()
    m = re.search(r"(\d{5})", s)
    if not m:
        return ""
    cp5 = m.group(1)
    return cp5[:3] if cp5.startswith("97") else cp5[:2]


# ─── Source 1 : ce qui va sortir de production ───────────────────────────────

# Dossiers du planning enrichis de l'OF et de la fiche technique. Le
# rapprochement de fiche reprend le motif éprouvé de `dossiers-disponibles`
# (MyExpé) : deux tables dérivées plutôt qu'une sous-requête corrélée, parce
# que SQLite n'autorise pas un ON à référencer l'alias de la jointure voisine,
# et parce que le MIN(id) par clé garantit une fiche unique — donc jamais un
# dossier dupliqué par ses variantes de fiche.
#   ftm = la fiche de la machine du dossier (prioritaire)
#   fta = n'importe quelle fiche de ce produit (repli)
_SQL_DOSSIERS = """
    SELECT pe.id, pe.reference, pe.client, pe.description, pe.ref_produit,
           pe.numero_of, pe.statut, pe.statut_reel, pe.date_livraison,
           COALESCE(pe.date_livraison_imposee, 0) AS date_livraison_imposee,
           pe.planned_end, pe.departement_livraison,
           COALESCE(pe.prise_rdv, 0) AS prise_rdv,
           COALESCE(pe.fsc_requis, 0) AS fsc_requis,
           COALESCE(pe.fsc_type_requis, '') AS fsc_type_requis,
           m.nom AS machine_nom,
           oi.qte_bobines    AS _of_qte_bobines,
           oi.qte_etiquettes AS _of_qte_etiquettes,
           COALESCE(ftm.nb_bobines_carton, fta.nb_bobines_carton)
             AS _ft_nb_bobines_carton,
           COALESCE(ftm.palette_nb_cartons_sol, fta.palette_nb_cartons_sol)
             AS _ft_palette_nb_cartons_sol,
           COALESCE(ftm.palette_nb_cartons_hauteur, fta.palette_nb_cartons_hauteur)
             AS _ft_palette_nb_cartons_hauteur,
           COALESCE(ftm.palette_type, fta.palette_type) AS _ft_palette_type,
           COALESCE(ftm.cartons, fta.cartons)           AS _ft_cartons,
           (SELECT d.id FROM expe_departs d
             WHERE d.id IN (
                     SELECT dd.depart_id FROM expe_depart_dossiers dd
                      WHERE dd.planning_entry_id = pe.id
                     UNION
                     SELECT d2.id FROM expe_departs d2
                      WHERE d2.planning_entry_id = pe.id)
             ORDER BY CASE d.statut WHEN 'prevu' THEN 0
                                    WHEN 'en_attente' THEN 1
                                    ELSE 2 END, d.id DESC
             LIMIT 1) AS depart_id
      FROM planning_entries pe
      JOIN machines m ON m.id = pe.machine_id
      LEFT JOIN of_imports oi ON oi.id = pe.of_import_id
      LEFT JOIN (
          SELECT MIN(id) AS id,
                 COALESCE(NULLIF(TRIM(ref_produit_norm), ''),
                          LOWER(TRIM(COALESCE(reference, '')))) AS k,
                 LOWER(TRIM(COALESCE(machine, ''))) AS mk
            FROM fiches_techniques
           GROUP BY k, mk
      ) km ON km.k = COALESCE(NULLIF(TRIM(pe.ref_produit_norm), ''),
                              LOWER(TRIM(COALESCE(pe.ref_produit, ''))))
          AND km.mk = LOWER(TRIM(COALESCE(m.nom, '')))
          AND km.mk != ''
          AND COALESCE(pe.ref_produit, '') != ''
      LEFT JOIN fiches_techniques ftm ON ftm.id = km.id
      LEFT JOIN (
          SELECT MIN(id) AS id,
                 COALESCE(NULLIF(TRIM(ref_produit_norm), ''),
                          LOWER(TRIM(COALESCE(reference, '')))) AS k
            FROM fiches_techniques
           GROUP BY k
      ) ka ON ka.k = COALESCE(NULLIF(TRIM(pe.ref_produit_norm), ''),
                              LOWER(TRIM(COALESCE(pe.ref_produit, ''))))
          AND COALESCE(pe.ref_produit, '') != ''
      LEFT JOIN fiches_techniques fta ON fta.id = ka.id
     WHERE COALESCE(pe.annule_count, 0) = 0
       AND (pe.statut IN ('attente', 'en_cours')
            OR (pe.statut = 'termine' AND pe.updated_at >= ?))
     ORDER BY pe.position ASC, pe.id ASC
"""


def _dossiers_a_expedier(conn, depuis_termine: str) -> List[dict]:
    try:
        rows = conn.execute(_SQL_DOSSIERS, (depuis_termine,)).fetchall()
    except Exception:
        _log.exception("pilotage expé : lecture des dossiers impossible")
        return []
    return [dict(r) for r in rows]


def _departs_par_id(conn, ids: List[int]) -> Dict[int, dict]:
    if not ids:
        return {}
    trous = ",".join("?" for _ in ids)
    rows = conn.execute(
        "SELECT id, statut, transporteur, transporteur_id, no_cde_transport, no_bl,"
        "       nb_palette, nb_palette_estime, poids_total_kg, date_enlevement,"
        "       date_enlevement_source, transport_commande_le, parti_le,"
        "       code_postal_destination, client, arc, cle_envoi, origine"
        f"  FROM expe_departs WHERE id IN ({trous})",
        ids,
    ).fetchall()
    return {int(r["id"]): dict(r) for r in rows}


# ─── Source 2 : le carnet RVGI ───────────────────────────────────────────────

# `cde_ligne.amje` est la date d'EXPÉDITION demandée, `amjl` la date de
# livraison ; c'est bien la première qui pilote la réservation du transport.
# Le filtre `corbeille = 0` porte des deux côtés de la jointure, et l'entête
# est jointe en INNER : l'export RVGI filtre table par table, donc une commande
# mise à la corbeille laisse ses lignes orphelines dans le miroir.
_SQL_RVGI_CDE = """
    SELECT l.numero,
           MIN(substr(l.amje, 1, 10)) AS amje,
           MIN(substr(l.amjl, 1, 10)) AS amjl,
           MAX(l.lrs)    AS lrs,
           MAX(l.lcp)    AS lcp,
           MAX(l.lville) AS lville,
           MAX(l.lpays)  AS lpays,
           MAX(e.rs)     AS client,
           SUM(CASE WHEN COALESCE(l.lpos, 0) = 0 THEN 1 ELSE 0 END) AS lignes_ouvertes
      FROM cde_ligne l
      JOIN cde_entete e ON e.numero = l.numero AND e.corbeille = 0
     WHERE l.corbeille = 0 AND l.numero IN (%s)
     GROUP BY l.numero
"""

_SQL_RVGI_BL = """
    SELECT DISTINCT ll.numcde AS numero,
           le.numero AS bl,
           substr(le.amje, 1, 10) AS date_bl,
           le.pal, le.pds, le.col
      FROM liv_ligne ll
      JOIN liv_entete le ON le.numero = ll.numero AND le.corbeille = 0
     WHERE ll.corbeille = 0 AND ll.numcde IN (%s)
"""


def infos_rvgi(numeros: List[str]) -> Dict[str, dict]:
    """Ce que RVGI sait de ces commandes : date d'expédition, adresse, BL.

    Renvoie un dictionnaire vide quand le miroir est absent — le tableau
    s'affiche alors sans ces colonnes plutôt que de tomber. Le miroir est
    ouvert en `mode=ro` par `erp_mirror`, aucune écriture n'est possible.
    """
    if not numeros:
        return {}
    try:
        from app.services import erp_mirror
    except Exception:
        return {}
    if not erp_mirror.miroir_present():
        return {}

    nums = [int(n) for n in numeros if str(n).isdigit()]
    if not nums:
        return {}
    out: Dict[str, dict] = {}
    try:
        with erp_mirror.get_erp_db() as conn:
            conn.row_factory = __import__("sqlite3").Row
            presentes = erp_mirror.tables_presentes(conn)
            if {"cde_ligne", "cde_entete"} <= presentes:
                trous = ",".join("?" for _ in nums)
                for r in conn.execute(_SQL_RVGI_CDE % trous, nums).fetchall():
                    out[str(r["numero"])] = {
                        "amje": _jour(r["amje"]),
                        "amjl": _jour(r["amjl"]),
                        "lrs": (r["lrs"] or "").strip(),
                        "lcp": (r["lcp"] or "").strip(),
                        "lville": (r["lville"] or "").strip(),
                        "lpays": (r["lpays"] or "").strip(),
                        "client": (r["client"] or "").strip(),
                        "lignes_ouvertes": int(r["lignes_ouvertes"] or 0),
                        "bls": [],
                    }
            if {"liv_ligne", "liv_entete"} <= presentes:
                trous = ",".join("?" for _ in nums)
                for r in conn.execute(_SQL_RVGI_BL % trous, nums).fetchall():
                    cle = str(r["numero"])
                    fiche = out.setdefault(cle, {"amje": None, "amjl": None, "lrs": "",
                                                 "lcp": "", "lville": "", "lpays": "",
                                                 "client": "", "lignes_ouvertes": 0,
                                                 "bls": []})
                    fiche["bls"].append({
                        "numero": str(r["bl"]),
                        "date": _jour(r["date_bl"]),
                        "pal": r["pal"],
                        "pds": r["pds"],
                        "col": r["col"],
                    })
    except Exception:
        _log.exception("pilotage expé : lecture du miroir RVGI impossible")
        return {}
    return out


# ─── Assemblage : un envoi = client + destination + date ─────────────────────

def _cle_envoi(client: str, cp: str, date_cible: Optional[str]) -> str:
    """Clé stable d'un envoi. Stable, parce qu'elle sert à retrouver le départ
    prévisionnel d'un rafraîchissement à l'autre : si elle bougeait, chaque
    passage créerait un doublon."""
    return "|".join([_norm(client)[:60], _dept(cp) or _norm(cp)[:10],
                     date_cible or "sans-date"])


def _etat_dossier(pe: dict) -> str:
    st = (pe.get("statut") or "").strip().lower()
    reel = (pe.get("statut_reel") or "").strip().lower()
    if st == "termine" and reel == "reellement_termine":
        return "termine"
    if st == "termine":
        return "saisie_en_cours"
    if st == "en_cours":
        return "en_cours"
    return "attente"


def construire_tableau(conn, aujourdhui: Optional[date] = None) -> dict:
    """Le tableau de bord expédition, prêt à sérialiser.

    Une passe sur le planning, une sur RVGI, une sur les départs. Rien n'est
    écrit : cette fonction ne fait que lire et croiser.
    """
    from app.services.date_livraison import parse_date_livraison

    today = aujourdhui or date.today()
    p = charger_params(conn)
    horizon = int(p["horizon_jours"])
    seuil_aff = float(p["seuil_affretement_palettes"])

    # Un dossier terminé il y a longtemps et jamais expédié n'est pas un envoi
    # à piloter, c'est de l'historique : on borne sur la fin de production.
    depuis = (today - timedelta(days=max(horizon, 30))).isoformat()
    dossiers = _dossiers_a_expedier(conn, depuis)

    departs = _departs_par_id(
        conn, [int(d["depart_id"]) for d in dossiers if d.get("depart_id")]
    )

    # Un seul aller-retour vers le miroir pour toutes les commandes citées.
    tous_cdes: List[str] = []
    for d in dossiers:
        for n in _cdes_rvgi(d.get("numero_of"), d.get("reference")):
            if n not in tous_cdes:
                tous_cdes.append(n)
    rvgi = infos_rvgi(tous_cdes)
    rvgi_present = bool(rvgi) or not tous_cdes

    groupes: Dict[str, dict] = {}

    for d in dossiers:
        dep = departs.get(int(d["depart_id"])) if d.get("depart_id") else None
        # Un départ déjà historisé clôt le sujet : le dossier est parti.
        if dep and (dep.get("statut") or "") == "valide":
            continue

        cdes = _cdes_rvgi(d.get("numero_of"), d.get("reference"))
        infos = [rvgi[n] for n in cdes if n in rvgi]

        # Date d'expédition visée, par ordre de fiabilité décroissante.
        date_cible, source = None, None
        amjes = sorted(i["amje"] for i in infos if i.get("amje"))
        if amjes:
            date_cible, source = amjes[0], "rvgi"
        if not date_cible:
            dl = parse_date_livraison(d.get("date_livraison"), reference=today)
            if dl:
                date_cible, source = dl.isoformat(), "planning"
        if not date_cible:
            pe_fin = _jour(d.get("planned_end"))
            if pe_fin:
                date_cible, source = pe_fin, "fin_prod"

        cp = ""
        ville = ""
        destinataire = ""
        for i in infos:
            if i.get("lcp"):
                cp, ville, destinataire = i["lcp"], i.get("lville", ""), i.get("lrs", "")
                break
        if not cp and dep and dep.get("code_postal_destination"):
            cp = str(dep["code_postal_destination"])
        if not cp:
            cp = str(d.get("departement_livraison") or "")

        client = (d.get("client") or "").strip() or (
            infos[0].get("client", "") if infos else "")

        cle = _cle_envoi(client, cp, date_cible)
        g = groupes.get(cle)
        if g is None:
            g = groupes[cle] = {
                "cle_envoi": cle,
                "client": client,
                "destinataire": destinataire,
                "code_postal": cp,
                "ville": ville,
                "departement": _dept(cp),
                "date_cible": date_cible,
                "date_cible_source": source,
                "dossiers": [],
                "commandes_rvgi": [],
                "bls": [],
                "depart_ids": [],
            }
        if destinataire and not g["destinataire"]:
            g["destinataire"] = destinataire
        if ville and not g["ville"]:
            g["ville"] = ville

        est = palettes_estimation.nb_palettes(d)
        g["dossiers"].append({
            "id": d["id"],
            "reference": d.get("reference"),
            "numero_of": d.get("numero_of"),
            "ref_produit": d.get("ref_produit"),
            "machine": d.get("machine_nom"),
            "etat": _etat_dossier(d),
            "planned_end": d.get("planned_end"),
            "date_livraison": d.get("date_livraison"),
            "date_livraison_imposee": bool(d.get("date_livraison_imposee")),
            "fsc_requis": bool(d.get("fsc_requis")),
            "prise_rdv": bool(d.get("prise_rdv")),
            "nb_palette_estime": est,
            "manques": palettes_estimation.manques(d),
        })
        for n in cdes:
            if n not in g["commandes_rvgi"]:
                g["commandes_rvgi"].append(n)
        for i in infos:
            for bl in i.get("bls", []):
                if bl["numero"] not in [b["numero"] for b in g["bls"]]:
                    g["bls"].append(bl)
        if d.get("depart_id") and int(d["depart_id"]) not in g["depart_ids"]:
            g["depart_ids"].append(int(d["depart_id"]))

    envois = [_finaliser(g, departs, today, p, seuil_aff) for g in groupes.values()]

    # Horizon : on borne ce qui est LOIN, jamais ce qui est en retard ni ce qui
    # n'a pas de date. Un envoi sans date est un trou à combler, le masquer
    # reviendrait à le perdre.
    borne = (today + timedelta(days=horizon)).isoformat()
    envois = [e for e in envois
              if not e["date_cible"]
              or e["date_cible"] <= borne
              or e["alerte"] in ("retard", "urgent", "a_commander")]

    # Tri : ce qui brûle d'abord. Les envois sans date en fin, jamais masqués —
    # une date manquante est un problème, pas une raison de disparaître.
    ordre = {"retard": 0, "urgent": 1, "a_commander": 2, "a_venir": 3,
             "commande": 4, "parti": 5}
    envois.sort(key=lambda e: (ordre.get(e["alerte"], 9),
                               e["date_cible"] or "9999-12-31"))

    return {
        "envois": envois,
        "params": p,
        "rvgi": {"present": rvgi_present, "commandes_lues": len(rvgi)},
        "horizon_jusquau": (today + timedelta(days=horizon)).isoformat(),
        "resume": _resume(envois),
        "genere_le": datetime.now().isoformat(timespec="seconds"),
    }


def _finaliser(g: dict, departs: Dict[int, dict], today: date,
               p: Dict[str, float], seuil_aff: float) -> dict:
    """Palettes, jalons et niveau d'alerte d'un envoi constitué."""
    ests = [d["nb_palette_estime"] for d in g["dossiers"]]
    connus = [e for e in ests if e is not None]
    g["nb_palette_estime"] = sum(connus) if connus else None
    g["nb_palette_estime_partiel"] = bool(connus) and len(connus) < len(ests)
    g["manques"] = sorted({m for d in g["dossiers"] for m in d["manques"]})

    dep = None
    for did in g["depart_ids"]:
        cand = departs.get(did)
        if cand and (dep is None or (cand.get("statut") == "prevu")):
            dep = cand
    g["depart"] = dep

    # Le nombre de palettes qui fait foi : la saisie d'abord, puis ce que RVGI
    # a compté sur le BL, puis l'estimation. C'est l'ordre de fiabilité réelle.
    pal_bl = None
    for bl in g["bls"]:
        try:
            v = float(bl.get("pal") or 0)
        except (TypeError, ValueError):
            v = 0.0
        if v > 0:
            pal_bl = (pal_bl or 0) + v
    saisi = dep.get("nb_palette") if dep else None
    g["nb_palette"] = saisi if saisi else (pal_bl if pal_bl else g["nb_palette_estime"])
    g["nb_palette_source"] = ("saisi" if saisi else
                              "bl" if pal_bl else
                              "estime" if g["nb_palette_estime"] is not None else None)

    pal = g["nb_palette"] or 0
    g["type_envoi"] = "affretement" if pal >= seuil_aff else "messagerie"
    preavis = int(p["preavis_affretement_jours"] if g["type_envoi"] == "affretement"
                  else p["preavis_messagerie_jours"])
    g["preavis_jours"] = preavis

    dc = _d(g["date_cible"])
    g["jours_restants"] = (dc - today).days if dc else None
    g["a_commander_le"] = (dc - timedelta(days=preavis)).isoformat() if dc else None

    # Production : le tableau doit dire si l'envoi est physiquement possible.
    fins = [_jour(d["planned_end"]) for d in g["dossiers"] if d.get("planned_end")]
    g["prod_fin_prevue"] = max(fins) if fins else None
    g["prod_prete"] = all(d["etat"] == "termine" for d in g["dossiers"])
    g["prod_apres_expedition"] = bool(
        dc and g["prod_fin_prevue"] and _d(g["prod_fin_prevue"]) and
        _d(g["prod_fin_prevue"]) > dc
    )

    transport_le = (dep or {}).get("transport_commande_le")
    transport_ref = (dep or {}).get("no_cde_transport")
    parti_le = (dep or {}).get("parti_le")
    if dep and (dep.get("statut") or "") == "valide" and not parti_le:
        parti_le = dep.get("date_enlevement")
    numeros_bl = [b["numero"] for b in g["bls"]]
    if dep and (dep.get("no_bl") or "").strip():
        for n in re.split(r"[^0-9]+", dep["no_bl"]):
            if n and n not in numeros_bl:
                numeros_bl.append(n)

    g["jalons"] = {
        "transport": {
            "fait": bool(transport_le or (transport_ref or "").strip()),
            "le": transport_le,
            "reference": transport_ref,
            "transporteur": (dep or {}).get("transporteur"),
            "date_enlevement": (dep or {}).get("date_enlevement"),
            "date_confirmee": ((dep or {}).get("date_enlevement_source") == "confirmee"),
        },
        "bl": {"fait": bool(numeros_bl), "numeros": numeros_bl},
        "parti": {"fait": bool(parti_le), "le": parti_le},
    }

    g["alerte"] = _alerte(g, today)
    g.pop("depart_ids", None)
    return g


def _alerte(g: dict, today: date) -> str:
    """Un envoi, un mot. L'ordre des tests est l'ordre de gravité."""
    if g["jalons"]["parti"]["fait"]:
        return "parti"
    dc = _d(g["date_cible"])
    if g["jalons"]["transport"]["fait"]:
        # Transport commandé mais la date d'expédition est passée : ce n'est
        # plus une réservation à faire, c'est un enlèvement à vérifier.
        return "retard" if (dc and dc < today) else "commande"
    if not dc:
        return "a_commander"
    if dc < today:
        return "retard"
    ac = _d(g["a_commander_le"])
    if ac and today >= ac:
        return "urgent" if (dc - today).days <= 1 else "a_commander"
    return "a_venir"


def _resume(envois: List[dict]) -> dict:
    def n(pred):
        return sum(1 for e in envois if pred(e))
    return {
        "total": len(envois),
        "retard": n(lambda e: e["alerte"] == "retard"),
        "urgent": n(lambda e: e["alerte"] == "urgent"),
        "a_commander": n(lambda e: e["alerte"] in ("a_commander", "urgent")),
        "transport_commande": n(lambda e: e["jalons"]["transport"]["fait"]),
        "bl_manquant": n(lambda e: not e["jalons"]["bl"]["fait"]),
        "partis": n(lambda e: e["alerte"] == "parti"),
        "palettes_a_reserver": sum(
            (e["nb_palette"] or 0) for e in envois
            if e["alerte"] in ("a_commander", "urgent", "retard")
        ),
        "sans_estimation": n(lambda e: e["nb_palette"] is None),
    }

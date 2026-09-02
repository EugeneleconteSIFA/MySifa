"""
Contrainte transport sur le planning de production.

La regle, decidee avec SIFA le 02/09/2026.

Un dossier est « sous contrainte transport » quand il est rattache a au moins
un depart MyExpe dont la date d'enlevement est a venir et qui porte au moins
`seuil_palettes` palettes. Sur un tel dossier :

- la production doit etre terminee avant la date d'enlevement a `heure_limite` ;
- la duree du dossier est majoree de `marge_pct` % pour assurer une marge de
  production ; cette marge occupe reellement le creneau, elle repousse donc les
  dossiers suivants ;
- un camion apparait sur le creneau du planning.

En dessous du seuil de palettes, rien ne s'applique : ni camion, ni marge, ni
refus. C'est un choix explicite — la regle n'existe que pour les expeditions
volumineuses, les petits envois se replacent sans consequence.

Deux points de mecanique qui expliquent le code.

1. **La marge ne s'ecrit jamais dans `duree_heures`.** La duree d'un dossier est
   une donnee metier, comparee au reel des saisies operateur ; y injecter un
   tampon de securite fausserait l'ecart prevu/reel pour toujours et ne serait
   pas reversible si le transport change. La marge est donc recalculee a chaque
   lecture, a partir des departs du moment.

2. **Le nombre de palettes vient d'abord de MyExpe.** `expe_departs.nb_palette`
   est la quantite reellement commandee au transporteur. Elle est souvent vide
   (tous les departs DSV, par exemple) : on retombe alors sur le nombre de
   palettes que le planning calcule deja depuis la fiche technique. Sans l'un ni
   l'autre, le depart ne declenche rien — on ne devine pas.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional

TABLE_PARAMS = "transport_planning_params"

DEFAUTS: Dict[str, Any] = {
    "actif": 1,
    "heure_limite": 11.0,
    "seuil_palettes": 6.0,
    "marge_pct": 20.0,
}

# Bornes de saisie cote Parametres. Une heure limite hors de la journee ou une
# marge de 400 % ne sont pas des reglages, ce sont des fautes de frappe.
BORNES = {
    "heure_limite": (0.0, 23.99),
    "seuil_palettes": (1.0, 99.0),
    "marge_pct": (0.0, 100.0),
}

# Tolerance de comparaison des fins de production, en heures (1 minute).
# Deux simulations successives ne retombent pas a la seconde pres : sans
# tolerance, tout geste serait vu comme une aggravation.
TOLERANCE_H = 1.0 / 60.0


# ─── Parametres ──────────────────────────────────────────────────────────────

def _table_existe(conn, nom: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (nom,)
    ).fetchone()
    return row is not None


def charger_params(conn) -> Dict[str, Any]:
    """Parametres de la regle. Toujours complet : les defauts comblent les trous."""
    vals: Dict[str, Any] = dict(DEFAUTS)
    if _table_existe(conn, TABLE_PARAMS):
        try:
            for r in conn.execute(f"SELECT cle, valeur FROM {TABLE_PARAMS}").fetchall():
                vals[r["cle"]] = r["valeur"]
        except Exception:
            pass
    out: Dict[str, Any] = {}
    out["actif"] = str(vals.get("actif", 1)).strip() not in ("0", "", "false", "False")
    for cle in ("heure_limite", "seuil_palettes", "marge_pct"):
        try:
            v = float(vals.get(cle))
        except (TypeError, ValueError):
            v = float(DEFAUTS[cle])
        lo, hi = BORNES[cle]
        out[cle] = min(max(v, lo), hi)
    return out


def enregistrer_params(conn, valeurs: Dict[str, Any]) -> Dict[str, Any]:
    """Ecrit les parametres fournis (les autres ne bougent pas) et relit le tout."""
    if not _table_existe(conn, TABLE_PARAMS):
        conn.execute(
            f"CREATE TABLE IF NOT EXISTS {TABLE_PARAMS} "
            "(cle TEXT PRIMARY KEY NOT NULL, valeur TEXT NOT NULL)"
        )
    for cle in ("actif", "heure_limite", "seuil_palettes", "marge_pct"):
        if cle not in valeurs or valeurs[cle] is None:
            continue
        if cle == "actif":
            brut = valeurs[cle]
            txt = "1" if (brut is True or str(brut).strip() in ("1", "true", "True")) else "0"
        else:
            try:
                v = float(valeurs[cle])
            except (TypeError, ValueError):
                raise ValueError(f"Valeur invalide pour {cle}.")
            lo, hi = BORNES[cle]
            if v < lo or v > hi:
                raise ValueError(
                    f"Valeur hors bornes pour {cle} (attendu entre {lo:g} et {hi:g})."
                )
            txt = f"{v:g}"
        conn.execute(
            f"INSERT INTO {TABLE_PARAMS} (cle, valeur) VALUES (?,?) "
            "ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur",
            (cle, txt),
        )
    conn.commit()
    return charger_params(conn)


# ─── Departs rattaches aux dossiers ──────────────────────────────────────────

def _parse_date_enlevement(val: Any) -> Optional[date]:
    """`date_enlevement` est un TEXT 'YYYY-MM-DD'. Tout le reste vaut None."""
    s = str(val or "").strip()[:10]
    if len(s) != 10:
        return None
    try:
        return date(int(s[0:4]), int(s[5:7]), int(s[8:10]))
    except (ValueError, TypeError):
        return None


def departs_par_dossier(
    conn, entry_ids: Iterable[int], *, aujourdhui: Optional[date] = None
) -> Dict[int, List[dict]]:
    """Departs A VENIR rattaches a chaque dossier, du plus proche au plus lointain.

    Le rattachement fait foi dans `expe_depart_dossiers` (multi-dossiers depuis
    le 06/08/2026) ; `expe_departs.planning_entry_id` n'en est que le miroir du
    premier dossier. On lit quand meme les deux : un depart cree hors du chemin
    normal aurait le miroir sans la ligne de liaison, et disparaitrait sinon.
    """
    ids = [int(i) for i in entry_ids if i is not None]
    out: Dict[int, List[dict]] = {i: [] for i in ids}
    if not ids or not _table_existe(conn, "expe_departs"):
        return out
    ref = aujourdhui or date.today()
    marques = ",".join("?" * len(ids))
    sql = f"""
        SELECT entry_id, id AS depart_id, date_enlevement, transporteur,
               transporteur_id, nb_palette, statut, client, no_cde_transport
        FROM (
            SELECT dd.planning_entry_id AS entry_id, d.*
              FROM expe_depart_dossiers dd
              JOIN expe_departs d ON d.id = dd.depart_id
             WHERE dd.planning_entry_id IN ({marques})
            UNION
            SELECT d.planning_entry_id AS entry_id, d.*
              FROM expe_departs d
             WHERE d.planning_entry_id IN ({marques})
        )
        WHERE date_enlevement IS NOT NULL AND TRIM(date_enlevement) != ''
    """
    params = ids + ids
    try:
        rows = conn.execute(sql, params).fetchall()
    except Exception:
        return out
    for r in rows:
        d = _parse_date_enlevement(r["date_enlevement"])
        if d is None or d < ref:
            continue
        eid = int(r["entry_id"])
        if eid not in out:
            continue
        out[eid].append(
            {
                "depart_id": int(r["depart_id"]),
                "date_enlevement": d.isoformat(),
                "_date": d,
                "transporteur": (r["transporteur"] or "").strip(),
                "transporteur_id": r["transporteur_id"],
                "nb_palette": r["nb_palette"],
                "statut": (r["statut"] or "").strip(),
                "client": (r["client"] or "").strip(),
                "no_cde_transport": (r["no_cde_transport"] or "").strip(),
            }
        )
    for eid in out:
        out[eid].sort(key=lambda x: (x["_date"], x["depart_id"]))
    return out


# ─── Regle ───────────────────────────────────────────────────────────────────

def _palettes_du_depart(dep: dict, palettes_dossier: Optional[float]) -> Optional[float]:
    brut = dep.get("nb_palette")
    if brut is not None and str(brut).strip() != "":
        try:
            v = float(brut)
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    if palettes_dossier is None:
        return None
    try:
        v = float(palettes_dossier)
    except (TypeError, ValueError):
        return None
    return v if v > 0 else None


def limite_pour(date_enlevement: str, heure_limite: float) -> Optional[datetime]:
    """Instant avant lequel la production doit etre finie."""
    d = _parse_date_enlevement(date_enlevement)
    if d is None:
        return None
    return datetime(d.year, d.month, d.day) + timedelta(hours=float(heure_limite))


def contraintes_pour(
    conn,
    entries: List[dict],
    palettes_dossier: Optional[Dict[int, Any]] = None,
    *,
    params: Optional[Dict[str, Any]] = None,
    aujourdhui: Optional[date] = None,
) -> Dict[int, dict]:
    """Contrainte transport de chaque dossier, indexee par id de dossier.

    `entries` : dossiers du planning (dicts portant au moins `id` et `statut`).
    `palettes_dossier` : repli {id: nb_palettes calcule} quand MyExpe ne dit rien.

    Un dossier termine est deja produit : plus rien a contraindre, donc pas de
    camion non plus. Les dossiers sans depart qualifiant sont absents du retour.
    """
    p = params or charger_params(conn)
    if not p["actif"] or not entries:
        return {}
    pal_map = {int(k): v for k, v in (palettes_dossier or {}).items()}
    ids = [
        int(e["id"])
        for e in entries
        if e.get("id") is not None and (e.get("statut") or "attente") != "termine"
    ]
    if not ids:
        return {}
    departs = departs_par_dossier(conn, ids, aujourdhui=aujourdhui)
    seuil = float(p["seuil_palettes"])
    out: Dict[int, dict] = {}
    for eid in ids:
        qualifiants = []
        for dep in departs.get(eid, []):
            pal = _palettes_du_depart(dep, pal_map.get(eid))
            if pal is None or pal < seuil:
                continue
            source = "expe" if (dep.get("nb_palette") not in (None, "")) else "dossier"
            qualifiants.append({**dep, "palettes": pal, "source_palettes": source})
        if not qualifiants:
            continue
        # Le depart le plus proche impose la limite ; les autres restent listes
        # pour l'infobulle (un dossier part parfois en deux camions).
        premier = qualifiants[0]
        lim = limite_pour(premier["date_enlevement"], p["heure_limite"])
        if lim is None:
            continue
        out[eid] = {
            "entry_id": eid,
            "depart_id": premier["depart_id"],
            "transporteur": premier["transporteur"],
            "date_enlevement": premier["date_enlevement"],
            "palettes": premier["palettes"],
            "source_palettes": premier["source_palettes"],
            "statut_depart": premier["statut"],
            "limite": lim,
            "limite_iso": lim.strftime("%Y-%m-%dT%H:%M:%S"),
            "heure_limite": p["heure_limite"],
            "marge_pct": float(p["marge_pct"]),
            "departs": [
                {
                    "depart_id": d["depart_id"],
                    "date_enlevement": d["date_enlevement"],
                    "transporteur": d["transporteur"],
                    "palettes": d["palettes"],
                    "source_palettes": d["source_palettes"],
                }
                for d in qualifiants
            ],
        }
    return out


def duree_effective(duree_h: Any, contrainte: Optional[dict]) -> float:
    """Duree occupee sur la machine : duree du dossier + marge transport."""
    try:
        d = float(duree_h or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if not contrainte:
        return d
    try:
        pct = float(contrainte.get("marge_pct") or 0.0)
    except (TypeError, ValueError):
        pct = 0.0
    return d * (1.0 + pct / 100.0)


def marge_heures(duree_h: Any, contrainte: Optional[dict]) -> float:
    try:
        d = float(duree_h or 0.0)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, duree_effective(d, contrainte) - d)


# ─── Verdict et message ──────────────────────────────────────────────────────

def _fmt_jour_heure(dt: Optional[datetime]) -> str:
    """« 02/09/2026 à 11h » — l'heure ronde perd ses minutes, comme partout ailleurs."""
    if not dt:
        return "date inconnue"
    h = dt.strftime("%Hh%M")
    if h.endswith("h00"):
        h = h[:-2]
    return dt.strftime("%d/%m/%Y") + " à " + h


def tension(contrainte: Optional[dict], fin: Optional[datetime]) -> str:
    """Etat d'un dossier contraint : 'ok', 'juste' ou 'depasse'.

    « juste » = il reste moins d'une journee ouvree de battement avant le
    camion. Ce n'est pas une alerte, c'est le seuil a partir duquel un
    planificateur veut regarder de plus pres avant de bouger quoi que ce soit.
    """
    if not contrainte or not fin:
        return "ok"
    lim = contrainte.get("limite")
    if not isinstance(lim, datetime):
        return "ok"
    reste_h = (lim - fin).total_seconds() / 3600.0
    if reste_h < 0:
        return "depasse"
    if reste_h < 8.0:
        return "juste"
    return "ok"


fmt_jour_heure = _fmt_jour_heure


def message_refus(entry: dict, contrainte: dict, fin: Optional[datetime]) -> str:
    """Message factuel et actionnable, au ton MySifa : ce qui est refusé, pourquoi,
    et les deux dates qui permettent de décider quoi faire ensuite."""
    ref = str(entry.get("numero_of") or entry.get("reference") or "?").strip()
    transp = (contrainte.get("transporteur") or "").strip() or "transporteur non précisé"
    pal = contrainte.get("palettes")
    pal_txt = f"{pal:g} palettes" if pal is not None else "palettes non précisées"
    return (
        f"Déplacement refusé — le dossier {ref} doit être terminé avant le "
        f"{_fmt_jour_heure(contrainte.get('limite'))} "
        f"(transport {transp}, {pal_txt}). "
        f"Fin calculée : {_fmt_jour_heure(fin)}."
    )


def violations(
    entries: List[dict],
    contraintes: Dict[int, dict],
    fins_avant: Dict[int, Optional[datetime]],
    fins_apres: Dict[int, Optional[datetime]],
) -> List[dict]:
    """Dossiers que le geste ferait rater, ou rater davantage.

    Un dossier deja en retard sur son enlevement n'est pas bloque tant que le
    geste ne l'aggrave pas : la regle est arrivee apres des annees de planning,
    et bloquer l'existant rendrait l'ecran inutilisable des la mise en service.
    """
    out: List[dict] = []
    par_id = {int(e["id"]): e for e in entries if e.get("id") is not None}
    for eid, c in contraintes.items():
        lim = c.get("limite")
        apres = fins_apres.get(eid)
        if not isinstance(lim, datetime) or apres is None:
            continue
        if apres <= lim:
            continue
        avant = fins_avant.get(eid)
        if avant is not None and avant > lim:
            # Deja en retard avant le geste : refus seulement si on l'aggrave.
            if (apres - avant).total_seconds() / 3600.0 <= TOLERANCE_H:
                continue
        e = par_id.get(eid) or {"id": eid}
        out.append(
            {
                "entry_id": eid,
                "reference": str(e.get("numero_of") or e.get("reference") or "").strip(),
                "depart_id": c.get("depart_id"),
                "transporteur": c.get("transporteur"),
                "date_enlevement": c.get("date_enlevement"),
                "palettes": c.get("palettes"),
                "limite_iso": c.get("limite_iso"),
                "fin_iso": apres.strftime("%Y-%m-%dT%H:%M:%S"),
                "message": message_refus(e, c, apres),
            }
        )
    out.sort(key=lambda v: v["limite_iso"])
    return out

"""
Photographier le carnet, pour pouvoir un jour le prévoir.

Le raisonnement complet est dans la migration `carnet_snapshots`. En deux
lignes : `planning_entries` ne garde que les quatre derniers mois, donc la
part du carnet déjà visible k mois à l'avance — p(k), le cœur du modèle de
prévision — ne peut pas se reconstituer après coup. Elle ne peut que
s'accumuler à partir d'aujourd'hui.

Ce module écrit donc une photo par jour et ne lit jamais l'avenir. Il ne
prédit rien : il fabrique la matière première d'un modèle qui viendra quand
il y aura de quoi le calibrer.

Deux principes de conception, tous deux dictés par le fait qu'on ne saura
qu'en novembre si la capture était correcte :

1. **On stocke le besoin CALCULÉ, pas les dossiers.** C'est la grandeur qu'on
   cherchera à prédire, et elle survit à la suppression du dossier qui l'a
   produite.
2. **On compte séparément ce qu'on n'a pas su chiffrer.** Un carnet dont les
   OF n'ont pas de métrage ressemble trait pour trait à un carnet vide. Sans
   `nb_incalculables`, on calibrerait un modèle sur une pénurie de données en
   croyant calibrer sur une pénurie de commandes.

La capture est best-effort et idempotente : la relancer dans la journée ne
duplique rien, et son échec ne doit jamais empêcher l'affichage des besoins.
"""
from datetime import date, datetime
from typing import Optional

from app.services.date_livraison import parse_date_livraison


def _mois_livraison(pe: dict) -> Optional[str]:
    """Mois visé par un dossier, 'AAAA-MM'.

    `date_livraison` d'abord — c'est l'engagement client, donc l'axe sur lequel
    on veut prévoir. `planned_end` en repli : un dossier planifié sans date de
    livraison lisible pèse quand même sur le mois où il sera produit.
    """
    for champ in ("date_livraison", "planned_end", "planned_start"):
        d = parse_date_livraison(pe.get(champ))
        if d:
            return f"{d.year:04d}-{d.month:02d}"
    return None


def capturer(conn, jour: Optional[date] = None, force: bool = False) -> dict:
    """Écrit la photo du jour. Ne committe pas : l'appelant maîtrise sa transaction.

    Retourne {"jour", "lignes", "dossiers", "deja_fait"}.
    """
    jour = jour or date.today()
    cle = jour.isoformat()

    deja = conn.execute(
        "SELECT COUNT(*) c FROM carnet_snapshots WHERE snapshot_le=?", (cle,)
    ).fetchone()["c"]
    if deja and not force:
        return {"jour": cle, "lignes": 0, "dossiers": 0, "deja_fait": True}
    if deja:
        conn.execute("DELETE FROM carnet_snapshots WHERE snapshot_le=?", (cle,))

    # Import local : ce service est appelé DEPUIS le router besoins_matieres.
    # Au niveau module, l'import serait circulaire. Même parti pris que
    # besoins_matieres avec of_import._promote_of_link.
    from app.routers.besoins_matieres import (
        _load_dossiers, _load_mapping, _compute_besoins_dossier,
    )
    from app.routers.stock import stock_config_float

    dossiers = _load_dossiers(conn)
    mapping = _load_mapping(conn)
    perte = stock_config_float(conn, "mandrin_perte_coupe_pct")

    # (mois, matiere_id, kind) → agrégat
    cumul: dict = {}
    vus: dict = {}   # mêmes clés → set d'ids de dossiers, pour ne pas les compter deux fois
    for pe in dossiers:
        mois = _mois_livraison(pe)
        if not mois:
            continue  # aucune date exploitable : le dossier n'a pas de mois à peser
        for b in _compute_besoins_dossier(pe, mapping, perte):
            cle_ligne = (mois, b.get("matiere_id"), b.get("kind"))
            agg = cumul.setdefault(cle_ligne, {"q": 0.0, "unite": b.get("unite"), "inc": 0})
            vus.setdefault(cle_ligne, set()).add(pe["id"])
            q = b.get("quantite")
            if q is None:
                agg["inc"] += 1
            else:
                agg["q"] += float(q)
            if not agg["unite"]:
                agg["unite"] = b.get("unite")

    for (mois, mid, kind), agg in cumul.items():
        conn.execute(
            """INSERT INTO carnet_snapshots
               (snapshot_le, mois_livraison, matiere_id, kind, unite,
                quantite, nb_dossiers, nb_incalculables)
               VALUES (?,?,?,?,?,?,?,?)""",
            (cle, mois, mid, kind, agg["unite"], round(agg["q"], 3),
             len(vus[(mois, mid, kind)]), agg["inc"]),
        )

    return {"jour": cle, "lignes": len(cumul), "dossiers": len(dossiers),
            "deja_fait": False}


def capturer_si_besoin(conn) -> None:
    """Photo du jour si elle n'a pas encore été prise. Silencieux, best-effort.

    Branché sur la consultation des besoins matières : l'écran est ouvert tous
    les jours ouvrés par l'administration, ce qui suffit à alimenter la série
    sans dépendre d'un cron à installer sur le VPS. Un jour chômé sans photo
    n'est pas un problème — la calibration raisonne en mois d'avance, pas en
    jours consécutifs.

    Toute erreur est avalée : rien de ce qui sert à une prévision d'automne ne
    justifie de faire échouer l'affichage des besoins d'aujourd'hui.
    """
    try:
        res = capturer(conn)
        if not res["deja_fait"]:
            conn.commit()
    except Exception:
        pass


def couverture(conn) -> dict:
    """Où en est l'accumulation — pour savoir quand le modèle sera calibrable."""
    try:
        r = conn.execute(
            """SELECT COUNT(DISTINCT snapshot_le) AS jours,
                      MIN(snapshot_le) AS depuis, MAX(snapshot_le) AS jusqu_a,
                      COUNT(*) AS lignes
               FROM carnet_snapshots"""
        ).fetchone()
    except Exception:
        return {"jours": 0, "depuis": None, "jusqu_a": None, "lignes": 0,
                "horizons_calibrables": []}
    jours, depuis, jusqu_a = r["jours"] or 0, r["depuis"], r["jusqu_a"]

    # Un horizon M+k n'est calibrable que si l'on possède des photos prises au
    # moins k mois avant des mois de livraison désormais révolus.
    mois_couverts = 0
    if depuis and jusqu_a:
        d0, d1 = datetime.fromisoformat(depuis).date(), datetime.fromisoformat(jusqu_a).date()
        mois_couverts = (d1.year - d0.year) * 12 + (d1.month - d0.month)
    return {
        "jours": jours,
        "depuis": depuis,
        "jusqu_a": jusqu_a,
        "lignes": r["lignes"] or 0,
        "mois_couverts": mois_couverts,
        "horizons_calibrables": list(range(1, mois_couverts + 1)),
    }

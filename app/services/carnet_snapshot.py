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
3. **On photographie TOUS les statuts, pas seulement le reste à produire.**
   p(k) est un rapport dont le dénominateur est le volume FINAL du mois M. Si
   la photo se limite aux dossiers actifs, ce volume final n'est jamais
   enregistré : les dossiers passent en « terminé » à mesure que M approche et
   la série retombe à zéro le mois venu. D'où `quantite` (tout ce qui vise ce
   mois) à côté de `quantite_active` (ce qui reste à produire).

La capture est best-effort et idempotente : la relancer dans la journée ne
duplique rien, et son échec ne doit jamais empêcher l'affichage des besoins.
"""
import logging
from datetime import date, datetime
from typing import Optional

from app.services.date_livraison import parse_date_livraison

logger = logging.getLogger(__name__)


# Deux axes de temps possibles, et ils ne répondent pas à la même question.
#
#   livraison  — quand le client attend sa commande. C'est l'engagement, et
#                l'axe sur lequel on veut PRÉVOIR l'activité.
#   production — quand le dossier passe en machine, donc quand la matière doit
#                être EN STOCK. C'est l'axe sur lequel on ACHÈTE.
#
# L'écart entre les deux vaut un à deux mois : la matière sort du stock avant
# la production, qui précède la livraison. Confronté au relevé de
# consommations d'Access (avril-août 2026), l'axe livraison décalait les
# courbes d'autant — les volumes étaient bons à 15 % près sur cinq mois, mais
# répartis sur les mauvais mois pour qui doit passer commande.
_AXES = {
    "livraison":  ("date_livraison", "planned_end", "planned_start"),
    "production": ("planned_start", "planned_end", "date_livraison"),
}


def _mois_livraison(pe: dict, axe: str = "livraison") -> Optional[str]:
    """Mois visé par un dossier, 'AAAA-MM', selon l'axe demandé.

    L'ordre des champs est un ordre de REPLI, pas une préférence : un dossier
    sans date sur l'axe choisi pèse quand même sur le mois qu'on peut lui
    connaître, plutôt que de disparaître de l'écran.
    """
    for champ in _AXES.get(axe) or _AXES["livraison"]:
        d = parse_date_livraison(pe.get(champ))
        if d:
            return f"{d.year:04d}-{d.month:02d}"
    return None


def laize_mm(besoin: dict):
    """Laize d'un besoin, en millimètres entiers — `None` si la matière n'est pas laizée.

    Arrondie à l'entier volontairement : 76 et 76.0 désignent la même bobine, et
    deux clés pour une seule laize scinderaient la courbe en deux moitiés qui ne
    veulent rien dire.
    """
    v = besoin.get("laize_mm")
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return int(round(v)) if v > 0 else None


def agreger(conn, axe: str = "livraison") -> tuple:
    """Besoin par (mois de livraison, matière, nature), sur tout le planning.

    Cœur commun à la photo quotidienne et à la vue Tendance : les deux posent
    exactement la même question, l'une pour l'écrire, l'autre pour l'afficher.
    Les faire diverger garantirait qu'un jour l'écran et la série de
    calibration ne racontent plus la même chose.

    Retourne (cumul, vus, vus_actifs, dossiers) où `cumul` est indexé par
    (mois, matiere_id, kind) et porte { q, q_actif, unite, inc, laizes }.

    `laizes` éclate le même total par laize (en mm, `None` pour ce qui n'est
    pas laizé) : une bobine ne se commande ni ne se stocke hors de sa laize,
    et un besoin de frontal agrégé toutes laizes confondues est juste en
    mètres mais inutilisable pour passer commande. Le total de la clé reste
    la somme de ses laizes — la photo quotidienne continue de n'écrire que
    lui, et ne voit pas la différence.
    """
    # Import local : ce service est appelé DEPUIS le router besoins_matieres.
    # Au niveau module, l'import serait circulaire. Même parti pris que
    # besoins_matieres avec of_import._promote_of_link.
    from app.routers.besoins_matieres import (
        _SQL_PE, _load_dossiers, _load_mapping, _compute_besoins_dossier,
    )
    from app.routers.stock import stock_config_float

    # `_SQL_PE` restreint aux dossiers en attente ou en cours — le périmètre de
    # l'écran Besoins matières, qui répond à « que reste-t-il à approvisionner ».
    # On a besoin de l'autre question : « combien ce mois aura-t-il pesé au
    # total ». On retire donc le filtre de statut, et on distingue les deux
    # grandeurs à la sortie.
    sql_tous = _SQL_PE.replace("WHERE pe.statut IN ('attente', 'en_cours')", "")
    dossiers = _load_dossiers(conn, sql_tous)
    mapping = _load_mapping(conn)
    perte = stock_config_float(conn, "mandrin_perte_coupe_pct")

    cumul: dict = {}
    vus: dict = {}         # (mois, mat, kind) → ids, pour ne pas compter deux fois
    vus_actifs: dict = {}  # idem, restreint aux dossiers encore à produire
    for pe in dossiers:
        mois = _mois_livraison(pe, axe)
        if not mois:
            continue  # aucune date exploitable : le dossier n'a pas de mois à peser
        actif = (pe.get("statut") or "") in ("attente", "en_cours")
        for b in _compute_besoins_dossier(pe, mapping, perte):
            cle = (mois, b.get("matiere_id"), b.get("kind"))
            agg = cumul.setdefault(
                cle, {"q": 0.0, "q_actif": 0.0, "unite": b.get("unite"), "inc": 0,
                      "ref": b.get("matiere_ref"), "designation": b.get("matiere_designation"),
                      "source_value": b.get("source_value"), "laizes": {}})
            vus.setdefault(cle, set()).add(pe["id"])
            if actif:
                vus_actifs.setdefault(cle, set()).add(pe["id"])
            sub = agg.setdefault("laizes", {}).setdefault(
                laize_mm(b), {"q": 0.0, "q_actif": 0.0, "inc": 0, "ids": set()})
            sub["ids"].add(pe["id"])
            q = b.get("quantite")
            if q is None:
                agg["inc"] += 1
                sub["inc"] += 1
            else:
                agg["q"] += float(q)
                sub["q"] += float(q)
                if actif:
                    agg["q_actif"] += float(q)
                    sub["q_actif"] += float(q)
            if not agg["unite"]:
                agg["unite"] = b.get("unite")
    return cumul, vus, vus_actifs, dossiers


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

    cumul, vus, vus_actifs, dossiers = agreger(conn)

    for (mois, mid, kind), agg in cumul.items():
        k = (mois, mid, kind)
        conn.execute(
            """INSERT INTO carnet_snapshots
               (snapshot_le, mois_livraison, matiere_id, kind, unite,
                quantite, quantite_active, nb_dossiers, nb_dossiers_actifs,
                nb_incalculables)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (cle, mois, mid, kind, agg["unite"],
             round(agg["q"], 3), round(agg["q_actif"], 3),
             len(vus[k]), len(vus_actifs.get(k, ())), agg["inc"]),
        )

    if dossiers and not cumul:
        # Des dossiers au planning, mais rien à photographier : aucun n'a de
        # date exploitable, ou aucun besoin n'est calculable. Ce n'est pas une
        # capture réussie, c'est une capture vide — et elle se lira plus tard
        # comme un carnet vide si personne ne le dit maintenant.
        logger.warning("[carnet] %s dossier(s) au planning mais aucune ligne "
                       "photographiée — dates de livraison ou besoins "
                       "incalculables ?", len(dossiers))
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
    justifie de faire échouer l'affichage des besoins d'aujourd'hui. Elle est
    en revanche TRACÉE. Une capture qui échoue en silence ne se découvre qu'en
    novembre, devant une table vide et trois mois irrécupérables — le coût
    d'une ligne de log est sans commune mesure.
    """
    try:
        res = capturer(conn)
        if not res["deja_fait"]:
            conn.commit()
            logger.info("[carnet] photo du %s : %s ligne(s), %s dossier(s).",
                        res["jour"], res["lignes"], res["dossiers"])
    except Exception:
        logger.exception("[carnet] photo du jour impossible — la série de "
                         "calibration aura un trou aujourd'hui.")


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

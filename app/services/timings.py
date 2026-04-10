from datetime import datetime
from collections import defaultdict
from database import parse_datetime
from config import CODE_CALAGE, CODE_PRODUCTION, CODE_REPRISE, CODE_DEBUT_DOS, CODE_FIN_DOS

# ─── Calcul temps par dossier ─────────────────────────────────────
def compute_dossier_times(rows):
    """
    Pour chaque dossier (no_dossier + operateur + jour), calcule :
    - temps_calage   : durée cumulée du code 02
    - temps_prod     : durée cumulée des codes 03 + 88 (reprise)
    - temps_total    : de Début dossier (01) à Fin dossier (89), hors calage
    - temps_total_avec_calage : de 01 à 89 calage compris
    La durée d'une opération = écart jusqu'à l'opération suivante du même opérateur/jour.
    """
    # Grouper par opérateur + jour, trier
    by_op_day = defaultdict(list)
    for r in rows:
        op = r["operateur"] or "?"
        dt = parse_datetime(r["date_operation"])
        day_key = dt.date().isoformat() if dt else (r["date_operation"] or "")[:10]
        by_op_day[(op, day_key)].append((dt, r))

    # dossier_times[dos_key] = dict accumulateur
    dossier_times = defaultdict(lambda: {
        "temps_calage_min": 0.0,
        "temps_prod_min": 0.0,
        "temps_arret_min": 0.0,
        "temps_total_min": None,
        "temps_total_calage_min": None,
        "debut_ts": None,
        "fin_ts": None,
        "no_dossier": None,
        "operateur": None,
        "jour": None,
        "machine": None,
        "client": None,
        "designation": None,
        "quantite_a_traiter": 0,
        "quantite_traitee": 0,
    })

    for (operateur, jour), items in by_op_day.items():
        items_sorted = sorted(items, key=lambda x: x[0] if x[0] else datetime.min)
        # Pré-calculer le prochain dt non-None pour éviter la recherche O(n)
        # à chaque i (sinon on tombe sur O(n^2) dans un groupe).
        next_dt_after = [None] * len(items_sorted)
        next_dt = None
        for idx in range(len(items_sorted) - 1, -1, -1):
            next_dt_after[idx] = next_dt
            if items_sorted[idx][0] is not None:
                next_dt = items_sorted[idx][0]

        for i, (dt, r) in enumerate(items_sorted):
            code  = r.get("operation_code", "")
            dos   = r.get("no_dossier", "") or ""
            if not dos or dos in ("0",):
                continue

            dos_key = (operateur, jour, dos)
            acc = dossier_times[dos_key]
            acc["no_dossier"]        = dos
            acc["operateur"]         = operateur
            acc["jour"]              = jour
            acc["machine"]           = r.get("machine", "") or acc["machine"]
            acc["client"]            = r.get("client", "") or acc["client"]
            acc["designation"]       = r.get("designation", "") or acc["designation"]

            if r.get("quantite_a_traiter", 0):
                acc["quantite_a_traiter"] = r["quantite_a_traiter"]
            if r.get("quantite_traitee", 0):
                acc["quantite_traitee"] = r["quantite_traitee"]

            # Bornes du dossier
            if code == CODE_DEBUT_DOS and dt:
                if acc["debut_ts"] is None or dt < acc["debut_ts"]:
                    acc["debut_ts"] = dt
            if code == CODE_FIN_DOS and dt:
                if acc["fin_ts"] is None or dt > acc["fin_ts"]:
                    acc["fin_ts"] = dt

            # Durée de cette opération = écart avec la suivante du même opérateur/jour
            if dt is None:
                continue
            next_dt = next_dt_after[i]
            if next_dt is None:
                continue
            delta_min = (next_dt - dt).total_seconds() / 60.0
            if delta_min < 0 or delta_min > 480:   # ignorer écarts > 8h (pause, fin de journée)
                continue

            if code == CODE_CALAGE:
                acc["temps_calage_min"] += delta_min
            elif code in (CODE_PRODUCTION, CODE_REPRISE):
                acc["temps_prod_min"] += delta_min
            else:
                # Pour la vitesse : inclure les arrêts machine (catégorie 'arret') dans le temps "prod effectif"
                # (les autres catégories : technique/nettoyage/etc ne sont pas ajoutées ici).
                if str(r.get("operation_category") or "") == "arret":
                    acc["temps_arret_min"] += delta_min

    # Calculer temps totaux à partir des bornes 01→89
    results = []
    for dos_key, acc in dossier_times.items():
        if acc["debut_ts"] and acc["fin_ts"] and acc["fin_ts"] > acc["debut_ts"]:
            total_avec_calage = (acc["fin_ts"] - acc["debut_ts"]).total_seconds() / 60.0
            acc["temps_total_calage_min"] = round(total_avec_calage, 1)
            acc["temps_total_min"]        = round(max(0, total_avec_calage - acc["temps_calage_min"]), 1)
        acc["temps_calage_min"] = round(acc["temps_calage_min"], 1)
        acc["temps_prod_min"]   = round(acc["temps_prod_min"],   1)
        acc["temps_arret_min"]  = round(acc["temps_arret_min"],  1)
        results.append(acc)

    return results
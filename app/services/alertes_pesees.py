"""Historique des pesées par front (saisie prod, MyProd).

Les pesées d'étiquettes se saisissent dans une alerte de maintenance : une
question « valeur » à mesures multiples (`points_libres`), une mesure par
front. Jusqu'ici elles ne se relisaient qu'une validation à la fois, noyées
dans la liste des saisies. Ce module les rend en tableau : quand, qui, quel
dossier, et la valeur de chaque front, à côté des autres mesures de la même
validation (grammage de colle, release…).

Aucune question n'est nommée ici : une alerte entre dans l'historique dès
qu'elle a une question valeur à mesures multiples, et toutes ses questions
valeur deviennent des colonnes. Les validations retenues sont celles de
l'onglet Analyse (`alertes_statistiques._trier`) : ni fermeture automatique,
ni esquive, ni ancien formulaire.

Les validations sont regroupées par dossier : les fronts d'un même dossier
pèsent la même étiquette, c'est donc à l'intérieur du dossier qu'une valeur
se compare. Une mesure loin de la médiane du dossier, ou un front loin des
autres fronts de la même pesée, est signalé « à vérifier »
(`PESEES_ECART_DOSSIER`, `PESEES_ECART_FRONTS` de config.py).
"""
from __future__ import annotations

from config import PESEES_ECART_DOSSIER, PESEES_ECART_FRONTS
from app.services.alertes_questionnaire import items_de_params
from app.services.alertes_statistiques import _lignes, _nombre, _resume, _trier, _valeurs


def _questions_valeur(items: list) -> list:
    out = []
    for i, it in enumerate(items):
        if it.get("type") != "value":
            continue
        out.append({
            "index": i,
            "id": it.get("id") or "",
            "label": it.get("label") or f"Question {i + 1}",
            "unit": it.get("unit") or "",
            "multiple": bool(it.get("points_libres")),
            "libelle_point": it.get("libelle_point") or "Mesure",
            "min": _nombre(it.get("min")), "max": _nombre(it.get("max")),
        })
    return out


def _mediane(vals: list):
    v = sorted(vals)
    n = len(v)
    if not n:
        return None
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def _loin(v: float, ref, seuil: float) -> bool:
    return bool(ref) and abs(v - ref) / abs(ref) > seuil


def par_dossier(lignes: list, qs: list) -> list:
    """Regroupe les lignes (plus récentes d'abord) par dossier et marque les
    mesures à vérifier : `ligne["aberrants"] = {index question: [positions]}`.
    Ordre des dossiers : le plus récemment pesé d'abord."""
    groupes, ordre = {}, []
    for l in lignes:
        cle = l["no_dossier"] or ""
        if cle not in groupes:
            groupes[cle] = {"no_dossier": cle, "machines": [], "lignes": [], "medianes": {}, "nb_aberrants": 0}
            ordre.append(cle)
        g = groupes[cle]
        g["lignes"].append(l)
        if l["machine"] and l["machine"] not in g["machines"]:
            g["machines"].append(l["machine"])
    for cle in ordre:
        g = groupes[cle]
        for l in g["lignes"]:
            l["aberrants"] = {}
        for q in qs:
            k = str(q["index"])
            tout = [n for l in g["lignes"] for n in l["valeurs"].get(k, [])]
            med = _mediane(tout) if len(tout) >= 4 else None
            if tout:
                g["medianes"][k] = _mediane(tout)
            for l in g["lignes"]:
                nums = l["valeurs"].get(k, [])
                med_v = _mediane(nums) if q["multiple"] and len(nums) >= 3 else None
                pos = [i for i, n in enumerate(nums)
                       if _loin(n, med, PESEES_ECART_DOSSIER) or _loin(n, med_v, PESEES_ECART_FRONTS)]
                if pos:
                    l["aberrants"][k] = pos
                    g["nb_aberrants"] += len(pos)
    return [groupes[c] for c in ordre]


def alertes_avec_pesees(conn) -> list:
    """[(id, nom, items, questions valeur)] des alertes à mesures multiples."""
    out = []
    for al in conn.execute("SELECT id, nom, params FROM maintenance_alerts ORDER BY nom").fetchall():
        items = items_de_params(al["params"])
        qs = _questions_valeur(items)
        if any(q["multiple"] for q in qs):
            out.append((al["id"], al["nom"] or "", items, qs))
    return out


def historique(conn, machine=None, no_dossier=None, du=None, au=None, limite: int = 300) -> dict:
    """Validations les plus récentes d'abord, `limite` par alerte."""
    dossier = (no_dossier or "").strip()
    alertes, machines = [], set()
    for aid, nom, items, qs in alertes_avec_pesees(conn):
        rows = _lignes(conn, aid, du, au, machine, None)
        retenues, _ = _trier(rows, items, None, None)
        if dossier:
            retenues = [l for l in retenues if l["no_dossier"] == dossier]
        lignes, par_front = [], {}
        for l in reversed(retenues):
            machines.add(l["machine"])
            valeurs, vide = {}, True
            for q in qs:
                nums = [n for n in (_nombre(x) for x in _valeurs(l["responses"].get(str(q["index"])))) if n is not None]
                valeurs[str(q["index"])] = nums
                if nums:
                    vide = False
                if q["multiple"]:
                    for i, n in enumerate(nums):
                        par_front.setdefault((q["index"], i), []).append(n)
            if vide:
                continue
            lignes.append({"id": l["id"], "ack_at": l["ack_at"], "machine": l["machine"],
                           "operateur": l["operateur"], "no_dossier": l["no_dossier"],
                           "valeurs": valeurs, "nc": l["nc"]})
            if len(lignes) >= limite:
                break
        for q in qs:
            if q["multiple"]:
                q["par_front"] = [{"position": i + 1, **_resume(v)}
                                  for (qi, i), v in sorted(par_front.items()) if qi == q["index"]]
        alertes.append({"id": aid, "nom": nom, "questions": qs, "lignes": lignes,
                        "dossiers": par_dossier(lignes, qs),
                        "nb_fronts": max((len(v) for l in lignes for k, v in l["valeurs"].items()
                                          if any(q["multiple"] and str(q["index"]) == k for q in qs)),
                                         default=0)})
    return {"alertes": alertes, "machines": sorted(m for m in machines if m)}

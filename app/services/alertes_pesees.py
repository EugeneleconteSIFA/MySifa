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
"""
from __future__ import annotations

from app.services.alertes_questionnaire import items_de_params
from app.services.alertes_statistiques import _lignes, _nombre, _resume, _trier, _valeurs


def _questions_valeur(items: list) -> list:
    out = []
    for i, it in enumerate(items):
        if it.get("type") != "value":
            continue
        out.append({
            "index": i,
            "label": it.get("label") or f"Question {i + 1}",
            "unit": it.get("unit") or "",
            "multiple": bool(it.get("points_libres")),
            "libelle_point": it.get("libelle_point") or "Mesure",
            "min": _nombre(it.get("min")), "max": _nombre(it.get("max")),
        })
    return out


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
                        "nb_fronts": max((len(v) for l in lignes for k, v in l["valeurs"].items()
                                          if any(q["multiple"] and str(q["index"]) == k for q in qs)),
                                         default=0)})
    return {"alertes": alertes, "machines": sorted(m for m in machines if m)}

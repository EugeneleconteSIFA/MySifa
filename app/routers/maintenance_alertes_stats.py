"""Maintenance › alertes — onglet Analyse de l'historique des saisies.

GET /api/maintenance/alertes/stats : statistiques des réponses, avec les
filtres de l'historique. `format=csv` rend les validations retenues, une
colonne par question.

Mêmes droits que la lecture de l'historique (`/api/maintenance/alert-acks`) :
tout utilisateur connecté. Calcul : app/services/alertes_statistiques.py.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import date

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from app.core.database import get_db
from app.services.alertes_statistiques import PERIODES, bornes_periode, statistiques, texte_reponse
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/api/maintenance/alertes", tags=["maintenance_alertes_stats"])


def _date(s):
    if not s:
        return None
    try:
        return date.fromisoformat(str(s)[:10])
    except ValueError:
        raise HTTPException(400, "Date invalide — format AAAA-MM-JJ.")


@router.get("/stats")
def alertes_stats(request: Request):
    get_current_user(request)
    q = request.query_params
    ids = []
    for v in q.getlist("alerte"):
        try:
            ids.append(int(v))
        except ValueError:
            raise HTTPException(400, "Alerte invalide.")
    periode = q.get("periode") or ""
    if periode in PERIODES:
        du, au = bornes_periode(periode)
    else:
        du, au = _date(q.get("du")), _date(q.get("au"))
    if du and au and du > au:
        du, au = au, du
    conformite = q.get("conformite") if q.get("conformite") in ("nc", "ok") else None
    try:
        points = json.loads(q.get("points") or "{}")
    except ValueError:
        points = {}
    if not isinstance(points, dict) or len(ids) != 1:
        points = {}  # les filtres par question n'ont de sens que pour une alerte
    with get_db() as conn:
        if not ids:
            ids = [r["id"] for r in conn.execute(
                """SELECT al.id FROM maintenance_alerts al
                    WHERE EXISTS (SELECT 1 FROM maintenance_alert_acks a WHERE a.alert_id = al.id)
                    ORDER BY al.nom""").fetchall()]
        res = statistiques(conn, ids, du=du, au=au, machine=q.get("machine") or None,
                           operateur=q.get("operateur") or None, conformite=conformite, points=points)

    if q.get("format") == "csv":
        return _csv(res)
    for a in res["alertes"]:
        a.pop("_lignes", None)
        a.pop("_items", None)
    return res


def _csv(res: dict) -> Response:
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    for n, a in enumerate(res["alertes"]):
        items = a["_items"]
        if n:
            w.writerow([])
        w.writerow(["Alerte", a["nom"]])
        w.writerow(["Date", "Machine", "Opérateur", "Dossier", "Produit", "Non conforme"]
                   + [(it.get("label") or f"Question {i + 1}") + (f" ({it['unit']})" if it.get("unit") else "")
                      for i, it in enumerate(items)]
                   + ["Commentaire"])
        for l in a["_lignes"]:
            w.writerow([l["ack_at"].replace("T", " ")[:16], l["machine"], l["operateur"], l["no_dossier"],
                        l.get("produit", ""), "oui" if l["nc"] else ""]
                       + [texte_reponse(it, l["responses"], i) for i, it in enumerate(items)]
                       + [l["comment"]])
    periode = "-".join(x for x in (res["du"], res["au"]) if x) or "tout"
    return Response(
        content="﻿" + buf.getvalue(),  # BOM : Excel lit l'UTF-8 et les accents
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="alertes-{periode}.csv"'},
    )

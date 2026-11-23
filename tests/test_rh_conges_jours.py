"""
Planning RH : les dates d'un congé font foi, et une absence justifiée peut
retirer une part de jours du solde CP.

Lancer : python3 tests/test_rh_conges_jours.py

Ce test verrouille :
1. Sans nombre de jours, le congé compte les jours ouvrés de ses dates,
   fériés retirés (Noël 2026) ; un ajustement par demi-journée est gardé.
2. Une période sans jour ouvré est refusée.
3. Changer les dates d'un congé recalcule ses jours, sauf ajustement envoyé.
4. Absence justifiée (événement familial) : `jours_cp` s'ajoute aux CP posés,
   le reste ne touche pas au solde ; plus de jours CP que d'absence est
   refusé ; un motif CP ignore `jours_cp`.
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_rh_conges_jours_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  (shim d'abord, voir CLAUDE.md)
from database import get_db  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from app.routers import planning_rh  # noqa: E402

_now = datetime.now().isoformat(timespec="seconds")
with get_db() as _c:
    U = _c.execute("INSERT INTO users (email,nom,password_hash,role,actif,created_at) "
                   "VALUES ('jours@local','Employé Jours','x','fabrication',1,?)", (_now,)).lastrowid
    _c.commit()

EDITEUR = {"id": 1, "nom": "Resp", "email": "resp@local", "role": "direction"}
planning_rh._require_conge_edit = lambda request: dict(EDITEUR)
planning_rh._require_view = lambda request, scope="atelier": dict(EDITEUR)
planning_rh.log_action = lambda **k: None


class Req:
    def __init__(self, body=None):
        self._b = body or {}
        self.client = None

    async def json(self):
        return json.loads(json.dumps(self._b))


ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(62) + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


def appel(f, *a):
    try:
        r = f(*a)
        if asyncio.iscoroutine(r):
            r = asyncio.run(r)
        return 200, r
    except HTTPException as e:
        return e.status_code, e.detail


def poses_cp():
    s = planning_rh.get_soldes(Req(), annee=2026, scope="rh")["soldes"]
    return next(x for x in s if x["user_id"] == U)["poses_cp"]


# 1. Jours tirés des dates.
st, c1 = appel(planning_rh.create_conge, Req({"user_id": U, "date_debut": "2026-12-21",
                                              "date_fin": "2026-12-27", "type_conge": "CP"}))
check("CP 21 → 27/12 : 4 jours ouvrés (Noël retiré)", c1.get("nb_jours") if st == 200 else st, 4.0)
check("motif CP : jours_cp sans objet (NULL)", c1.get("jours_cp", "absent"), None)
st, c2 = appel(planning_rh.create_conge, Req({"user_id": U, "date_debut": "2026-12-01",
                                              "date_fin": "2026-12-01", "nb_jours": 0.5, "type_conge": "CP"}))
check("demi-journée ajustée gardée", c2.get("nb_jours") if st == 200 else st, 0.5)
st, _ = appel(planning_rh.create_conge, Req({"user_id": U, "date_debut": "2026-12-05",
                                             "date_fin": "2026-12-06", "type_conge": "CP"}))
check("week-end seul refusé (400)", st, 400)
check("soldes : 4,5 CP posés", poses_cp(), 4.5)

# 3. Modification des dates.
st, m = appel(planning_rh.update_conge, c1["id"], Req({"date_debut": "2026-12-21", "date_fin": "2026-12-23"}))
check("dates raccourcies → 3 jours recalculés", m.get("nb_jours") if st == 200 else st, 3.0)
st, m = appel(planning_rh.update_conge, c1["id"], Req({"date_fin": "2026-12-24", "nb_jours": 3.5}))
check("ajustement envoyé avec les dates gardé", m.get("nb_jours") if st == 200 else st, 3.5)

# 4. Absence justifiée avec part CP.
st, ev = appel(planning_rh.create_conge, Req({"user_id": U, "date_debut": "2026-11-02", "date_fin": "2026-11-09",
                                              "type_conge": "evenement_familial", "jours_cp": 2}))
check("événement familial : 6 jours d'absence", ev.get("nb_jours") if st == 200 else st, 6.0)
check("… dont 2 décomptés des CP", ev.get("jours_cp"), 2.0)
check("soldes : CP posés = 3,5 + 0,5 + 2", poses_cp(), 6.0)
st, _ = appel(planning_rh.create_conge, Req({"user_id": U, "date_debut": "2026-10-05", "date_fin": "2026-10-06",
                                             "type_conge": "formation", "jours_cp": 3}))
check("plus de jours CP que d'absence refusé (400)", st, 400)
st, fo = appel(planning_rh.create_conge, Req({"user_id": U, "date_debut": "2026-10-05", "date_fin": "2026-10-06",
                                              "type_conge": "formation"}))
check("formation sans part CP : 0 par défaut", fo.get("jours_cp") if st == 200 else st, 0.0)
check("soldes : la formation ne touche pas aux CP", poses_cp(), 6.0)
st, m = appel(planning_rh.update_conge, ev["id"], Req({"type_conge": "CP"}))
check("passé en CP : jours_cp effacé, 6 jours CP", (m.get("jours_cp"), poses_cp()), (None, 10.0))

print()
print("ÉCHECS : " + ", ".join(ECHECS) if ECHECS else "Tous les contrôles passent.")
sys.exit(1 if ECHECS else 0)

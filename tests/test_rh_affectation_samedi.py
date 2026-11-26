"""
Planning RH : un employé affecté du lundi au vendredi sur un poste peut être
ajouté le samedi sur un autre poste.

Lancer : python3 tests/test_rh_affectation_samedi.py

Ce test verrouille :
1. Lundi–vendredi pris, samedi demandé explicitement (jours=32) : accepté.
2. Lundi–vendredi pris, sans jours demandés : toujours refusé (409).
3. Lundi–vendredi pris, jours demandés déjà occupés : refusé (409).
4. Lundi–samedi pris : plus rien ne s'ajoute, même le samedi.
5. CP le lundi et affecté du mardi au vendredi : le samedi passe sans
   confirmation (le congé ne le touche pas) ; un jour du congé demande
   toujours confirmation.
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_rh_samedi_test_")
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
                   "VALUES ('samedi@local','Employé Samedi','x','fabrication',1,?)", (_now,)).lastrowid
    V = _c.execute("INSERT INTO users (email,nom,password_hash,role,actif,created_at) "
                   "VALUES ('samedi2@local','Employé Six Jours','x','fabrication',1,?)", (_now,)).lastrowid
    W = _c.execute("INSERT INTO users (email,nom,password_hash,role,actif,created_at) "
                   "VALUES ('samedi3@local','Employé CP Lundi','x','fabrication',1,?)", (_now,)).lastrowid
    _c.execute("INSERT INTO rh_conges (user_id,date_debut,date_fin,nb_jours,type_conge,statut) "
               "VALUES (?,'2026-11-23','2026-11-23',1,'CP','valide')", (W,))
    _c.commit()

EDITEUR = {"id": 1, "nom": "Resp", "email": "resp@local", "role": "direction"}
planning_rh._require_atelier_edit = lambda request: dict(EDITEUR)
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


def poser(corps):
    try:
        r = asyncio.run(planning_rh.create_planning(Req(corps)))
    except HTTPException as e:
        return e.status_code, e.detail
    if hasattr(r, "status_code") and not isinstance(r, dict):
        return r.status_code, json.loads(r.body)
    return 200, r


SEM = "2026-W48"
st, _ = poser({"user_id": U, "semaine": SEM, "poste": "conducteur", "creneau": "aprem"})
check("lundi–vendredi posé sur l'après-midi", st, 200)

st, _ = poser({"user_id": U, "semaine": SEM, "poste": "conducteur", "creneau": "matin"})
check("sans jours demandés : refusé", st, 409)

st, _ = poser({"user_id": U, "semaine": SEM, "poste": "conducteur", "creneau": "matin", "jours": 4})
check("mercredi demandé, déjà pris : refusé", st, 409)

st, d = poser({"user_id": U, "semaine": SEM, "poste": "conducteur", "creneau": "matin", "jours": 32})
check("samedi seul demandé : accepté", st, 200)
check("… affectation enregistrée sur le samedi seul", (d or {}).get("jours"), 32)

st, _ = poser({"user_id": V, "semaine": SEM, "poste": "conducteur", "creneau": "aprem", "jours": 63})
check("lundi–samedi posé", st, 200)
st, _ = poser({"user_id": V, "semaine": SEM, "poste": "conducteur", "creneau": "matin", "jours": 32})
check("lundi–samedi pris : samedi refusé", st, 409)

st, _ = poser({"user_id": W, "semaine": SEM, "poste": "tournant", "creneau": "journee", "jours": 30})
check("CP lundi : mardi–vendredi posé", st, 200)
st, d = poser({"user_id": W, "semaine": SEM, "poste": "conducteur", "creneau": "matin", "jours": 32})
check("CP lundi : samedi accepté sans confirmation", (st, (d or {}).get("jours")), (200, 32))
st, d = poser({"user_id": W, "semaine": SEM, "poste": "aide", "creneau": "aprem", "jours": 1})
check("CP lundi : lundi demandé, confirmation demandée", (st, (d or {}).get("conflict_type")), (409, "conge"))

print()
if ECHECS:
    print(f"{len(ECHECS)} échec(s)")
    sys.exit(1)
print("Tout est bon.")

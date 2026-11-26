"""
Planning RH : fermetures collectives.

Lancer : python3 tests/test_rh_fermetures.py

Ce test verrouille :
1. L'aperçu compte les jours ouvrés (fériés retirés) : 28/12 → 31/12/2026 = 4.
2. Créer une fermeture pose un congé validé, du motif par défaut, à chaque
   employé actif coché ; un employé décoché est retiré ; un employé déjà
   absent sur la période ne reçoit pas un second congé.
3. Le motif d'un employé se change seul (sans solde) ; changer le motif par
   défaut ne l'écrase pas, mais suit pour les autres.
4. Les soldes décomptent selon le motif : 4 CP pour les uns, 0 pour celui en
   sans solde.
5. Supprimer un congé de fermeture retire l'employé : réappliquer ne le
   rajoute pas. Un employé arrivé après est rattrapé par « appliquer ».
6. Supprimer la fermeture retire tous ses congés.
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_rh_fermetures_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  (shim d'abord, voir CLAUDE.md)
from database import get_db  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from app.routers import planning_rh, planning_rh_fermetures as fm  # noqa: E402

_now = datetime.now().isoformat(timespec="seconds")
with get_db() as _c:
    # Base neuve : seuls nos comptes doivent compter.
    _c.execute("UPDATE users SET actif = 0")

    def _compte(email, nom, role):
        return _c.execute("INSERT INTO users (email,nom,password_hash,role,actif,created_at) VALUES (?,?,?,?,1,?)",
                          (email, nom, "x", role, _now)).lastrowid
    U_A = _compte("a.ferm@local", "Alice Fermeture", "fabrication")
    U_B = _compte("b.ferm@local", "Bruno Fermeture", "comptabilite")
    U_C = _compte("c.ferm@local", "Carla Fermeture", "logistique")
    U_D = _compte("d.ferm@local", "Interimaire Fermeture", "fabrication")
    U_RESP = _compte("resp.ferm@local", "Responsable Fermeture", "direction")
    # Carla est déjà en congé du 21 au 31/12.
    _c.execute("INSERT INTO rh_conges (user_id,date_debut,date_fin,nb_jours,type_conge,statut,created_at) "
               "VALUES (?, '2026-12-21', '2026-12-31', 8, 'CP', 'valide', ?)", (U_C, _now))
    _c.commit()

EDITEUR = {"id": U_RESP, "nom": "Responsable", "email": "resp.ferm@local", "role": "direction"}
fm._require_hr_edit = lambda request: dict(EDITEUR)
fm._require_hr_view = lambda request: dict(EDITEUR)
planning_rh._require_view = lambda request, scope="atelier": dict(EDITEUR)
planning_rh._require_conge_edit = lambda request: dict(EDITEUR)
fm.log_action = lambda **k: None
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


def etats(det):
    return {e["user_id"]: e["etat"] for e in det["employes"]}


def solde_cp(uid):
    s = {x["user_id"]: x for x in planning_rh.get_soldes(Req(), annee=2026, scope="rh")["soldes"]}
    return s[uid]["poses_cp"]


# 1. Aperçu.
st, ap = appel(fm.apercu_fermeture, Req(), "2026-12-28", "2026-12-31")
check("aperçu : 28 → 31/12/2026 = 4 jours ouvrés", ap["nb_jours"], 4.0)
st, ap2 = appel(fm.apercu_fermeture, Req(), "2026-12-21", "2026-12-27")
check("aperçu : Noël (25/12) retiré → 4 jours", ap2["nb_jours"], 4.0)
check("aperçu : Carla déjà absente", etats(ap)[U_C], "deja_absent")
st, _ = appel(fm.apercu_fermeture, Req(), "2026-12-31", "2026-12-28")
check("aperçu : fin avant début refusée (400)", st, 400)

# 2. Création.
st, det = appel(fm.creer_fermeture, Req({"libelle": "Fermeture annuelle", "date_debut": "2026-12-28",
                                         "date_fin": "2026-12-31", "type_conge": "CP", "exclus": [U_D]}))
check("fermeture créée", st, 200)
check("bilan : 3 congés posés (A, B, responsable)", det["bilan"]["ajoutes"], 3)
check("jours par défaut = jours ouvrés", det["nb_jours"], 4.0)
e = etats(det)
check("intérimaire décoché → retiré", e[U_D], "exclu")
check("Carla déjà absente → pas de second congé", e[U_C], "deja_absent")
FID = det["id"]
with get_db() as c:
    row = dict(c.execute("SELECT * FROM rh_conges WHERE fermeture_id=? AND user_id=?", (FID, U_A)).fetchone())
check("congé posé : CP, validé, 4 j, libellé en note",
      (row["type_conge"], row["statut"], row["nb_jours"], row["note"]), ("CP", "valide", 4.0, "Fermeture annuelle"))
st, _ = appel(fm.creer_fermeture, Req({"libelle": "X", "date_debut": "2026-12-28",
                                       "date_fin": "2026-12-31", "type_conge": "inexistant"}))
check("motif inconnu refusé (400)", st, 400)

# 3. Ajustement individuel puis changement du motif par défaut.
st, det = appel(fm.ajuster_employe, FID, U_B, Req({"type_conge": "sans_solde"}))
check("Bruno passe en sans solde", {x["user_id"]: x["type_conge"] for x in det["employes"]}[U_B], "sans_solde")
check("soldes : Alice 4 CP", solde_cp(U_A), 4.0)
check("soldes : Bruno 0 CP (sans solde)", solde_cp(U_B), 0.0)
st, det = appel(fm.modifier_fermeture, FID, Req({"type_conge": "RTT", "date_fin": "2026-12-30", "nb_jours": 3}))
types = {x["user_id"]: x["type_conge"] for x in det["employes"]}
check("motif par défaut reporté sur Alice", types[U_A], "RTT")
check("ajustement de Bruno conservé", types[U_B], "sans_solde")
with get_db() as c:
    dates = {r["date_fin"] for r in c.execute("SELECT date_fin FROM rh_conges WHERE fermeture_id=?", (FID,))}
check("nouvelle date de fin sur tous les congés", dates, {"2026-12-30"})
appel(fm.modifier_fermeture, FID, Req({"type_conge": "CP", "date_fin": "2026-12-31", "nb_jours": 4}))

# 5. Retrait par suppression du congé, puis rattrapage d'un nouvel arrivant.
with get_db() as c:
    cid = c.execute("SELECT id FROM rh_conges WHERE fermeture_id=? AND user_id=?", (FID, U_A)).fetchone()[0]
appel(planning_rh.delete_conge, cid, Req())
with get_db() as c:
    U_E = c.execute("INSERT INTO users (email,nom,password_hash,role,actif,created_at) "
                    "VALUES ('e.ferm@local','Emma Fermeture','x','expedition',1,?)", (_now,)).lastrowid
    c.commit()
st, det = appel(fm.appliquer_fermeture, FID, Req())
e = etats(det)
check("congé supprimé à la main → employé retiré", e[U_A], "exclu")
check("appliquer : seule la nouvelle arrivée reçoit le congé", det["bilan"]["ajoutes"], 1)
check("nouvelle arrivée couverte", e[U_E], "couvert")
st, det = appel(fm.ajuster_employe, FID, U_A, Req({"inclus": True}))
check("réintégration : congé reposé", etats(det)[U_A], "couvert")
st, _ = appel(fm.ajuster_employe, FID, U_C, Req({"inclus": True}))
check("réintégrer quelqu'un déjà absent refusé (409)", st, 409)

# 6. Suppression.
st, r = appel(fm.supprimer_fermeture, FID, Req())
check("suppression : congés de la fermeture retirés", r["conges_supprimes"], 4)
with get_db() as c:
    reste = c.execute("SELECT COUNT(*) FROM rh_conges WHERE user_id=?", (U_C,)).fetchone()[0]
check("le congé personnel de Carla reste", reste, 1)

print()
print("ÉCHECS : " + ", ".join(ECHECS) if ECHECS else "Tous les contrôles passent.")
sys.exit(1 if ECHECS else 0)

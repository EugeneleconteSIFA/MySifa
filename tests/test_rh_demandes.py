"""
Planning RH : demandes des employés et motifs d'absence.

Lancer : python3 tests/test_rh_demandes.py

Ce test verrouille :
1. Les motifs d'absence sont seedés ; un motif non demandable (maladie) est
   refusé à un employé (400).
2. Un employé dépose une absence : jours ouvrés comptés par défaut, demande en
   attente, chevauchement du même type refusé (409).
3. Aménagement d'horaire : heures au format HH:MM et motif obligatoires.
4. Valider une absence crée le congé (type = code du motif, statut valide) ;
   un conflit avec le planning postes demande confirmation (409) puis passe
   avec `force`.
5. Refuser exige un motif ; une demande traitée ne s'annule plus (409) ;
   seul l'auteur annule la sienne (403 sinon).
6. Les soldes imputent un motif selon son décompte (RTT, formation hors CP).
"""

import asyncio
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_rh_demandes_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  (shim d'abord, voir CLAUDE.md)
from database import get_db  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from app.routers import planning_rh, planning_rh_demandes as dm  # noqa: E402

_now = datetime.now().isoformat(timespec="seconds")
with get_db() as _c:
    def _compte(email, nom, role):
        return _c.execute("INSERT INTO users (email,nom,password_hash,role,actif,created_at) VALUES (?,?,?,?,1,?)",
                          (email, nom, "x", role, _now)).lastrowid
    U_OP = _compte("op.demandes@local", "Opérateur Demandes", "fabrication")
    U_OP2 = _compte("op2.demandes@local", "Second Demandes", "fabrication")
    U_RESP = _compte("resp.demandes@local", "Responsable Demandes", "direction")
    _c.commit()

COURANT = {}


def en_tant_que(uid, role):
    COURANT.clear()
    COURANT.update({"id": uid, "nom": f"user{uid}", "email": f"u{uid}@local", "role": role})


dm.get_current_user = lambda request: dict(COURANT)
dm._require_conge_edit = lambda request: dict(COURANT)
planning_rh._require_view = lambda request, scope="atelier": dict(COURANT)
dm.log_action = lambda **k: None
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


# 1. Motifs.
en_tant_que(U_OP, "fabrication")
codes = {m["code"]: m for m in dm.list_motifs(Req())["motifs"]}
check("motifs seedés (CP, RTT, formation, maladie)", {"CP", "RTT", "formation", "maladie"} <= set(codes))
st, _ = appel(dm.create_demande, Req({"nature": "absence", "motif_code": "maladie",
                                       "date_debut": "2026-12-01", "date_fin": "2026-12-01"}))
check("maladie non demandable par l'employé (400)", st, 400)

# 2. Absence : lundi 07/12 → vendredi 11/12 = 5 jours ouvrés.
st, d_cp = appel(dm.create_demande, Req({"nature": "absence", "motif_code": "CP",
                                         "date_debut": "2026-12-07", "date_fin": "2026-12-13"}))
check("absence déposée", st, 200)
check("jours ouvrés comptés par défaut", d_cp["nb_jours"], 5.0)
check("demande en attente", d_cp["statut"], "en_attente")
st, _ = appel(dm.create_demande, Req({"nature": "absence", "motif_code": "RTT",
                                       "date_debut": "2026-12-09", "date_fin": "2026-12-09"}))
check("chevauchement du même type refusé (409)", st, 409)
st, _ = appel(dm.create_demande, Req({"nature": "absence", "motif_code": "CP", "nb_jours": 9,
                                       "date_debut": "2026-12-14", "date_fin": "2026-12-15"}))
check("plus de jours que la période refusé (400)", st, 400)

# 3. Horaire.
st, _ = appel(dm.create_demande, Req({"nature": "horaire", "date_debut": "2026-12-01",
                                       "heure_debut": "8h", "heure_fin": "16:00", "commentaire": "école"}))
check("horaire mal formé refusé (400)", st, 400)
st, _ = appel(dm.create_demande, Req({"nature": "horaire", "date_debut": "2026-12-01",
                                       "heure_debut": "08:00", "heure_fin": "16:00"}))
check("horaire sans motif refusé (400)", st, 400)
st, d_h = appel(dm.create_demande, Req({"nature": "horaire", "date_debut": "2026-12-01", "date_fin": "2026-12-04",
                                         "heure_debut": "08:00", "heure_fin": "16:00", "commentaire": "école"}))
check("aménagement d'horaire déposé", st, 200)
st, d_f = appel(dm.create_demande, Req({"nature": "absence", "motif_code": "formation",
                                         "date_debut": "2026-12-16", "date_fin": "2026-12-17"}))
check("formation demandable", st, 200)

# 5. Seul l'auteur annule.
en_tant_que(U_OP2, "fabrication")
st, _ = appel(dm.annuler_demande, d_h["id"], Req())
check("annulation par un autre employé refusée (403)", st, 403)

# 4. Validation avec conflit planning (semaine 2026-W50 = 07/12).
with get_db() as c:
    c.execute("INSERT INTO rh_planning_postes (user_id, semaine, poste, creneau) VALUES (?, '2026-W50', 'conducteur', 'matin')",
              (U_OP,))
    c.commit()
en_tant_que(U_RESP, "direction")
st, det = appel(dm.decider_demande, d_cp["id"], Req({"decision": "valider"}))
check("conflit planning : confirmation demandée (409)", st, 409)
check("conflit planning : semaine renvoyée", isinstance(det, dict) and det.get("semaines"), ["2026-W50"])
st, d_ok = appel(dm.decider_demande, d_cp["id"], Req({"decision": "valider", "force": True}))
check("validation forcée", d_ok["statut"] if st == 200 else st, "validee")
with get_db() as c:
    cg = c.execute("SELECT * FROM rh_conges WHERE id = ?", (d_ok["conge_id"],)).fetchone()
check("congé créé avec le code du motif", (cg["type_conge"], cg["statut"], cg["nb_jours"]), ("CP", "valide", 5.0))
st, _ = appel(dm.decider_demande, d_cp["id"], Req({"decision": "refuser", "note": "x"}))
check("demande déjà traitée (409)", st, 409)

st, _ = appel(dm.decider_demande, d_h["id"], Req({"decision": "refuser"}))
check("refus sans motif refusé (400)", st, 400)
st, d_r = appel(dm.decider_demande, d_h["id"], Req({"decision": "refuser", "note": "Équipe incomplète"}))
check("refus avec motif", (d_r["statut"], d_r["decision_note"]), ("refusee", "Équipe incomplète"))
appel(dm.decider_demande, d_f["id"], Req({"decision": "valider"}))

en_tant_que(U_OP, "fabrication")
st, _ = appel(dm.annuler_demande, d_r["id"], Req())
check("demande traitée non annulable (409)", st, 409)
mes = dm.mes_demandes(Req())["demandes"]
check("mes demandes : 3 demandes", len(mes), 3)

# 6. Soldes.
en_tant_que(U_RESP, "direction")
sol = {s["user_id"]: s for s in planning_rh.get_soldes(Req(), annee=2026)["soldes"]}
s_op = sol.get(U_OP, {})
check("CP imputés au solde CP", s_op.get("poses_cp"), 5.0)
check("formation hors CP, comptée par motif", (s_op.get("poses_par_motif") or {}).get("formation"), 2.0)

# Motif créé : code dérivé du libellé.
st, m = appel(dm.create_motif, Req({"libelle": "Visite médicale", "decompte": "aucun"}))
check("motif créé, code dérivé du libellé", m.get("code") if st == 200 else st, "visite_medicale")

print()
print("ÉCHECS : " + ", ".join(ECHECS) if ECHECS else "Tous les contrôles passent.")
sys.exit(1 if ECHECS else 0)

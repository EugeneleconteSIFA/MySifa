"""
MyRH : intitulés de poste (catalogue, postes d'un employé, formations
exigées pour un poste).

Lancer : python3 tests/test_rh_outil_postes.py

Ce test verrouille :
1. Un poste appartient à un service connu ; même intitulé deux fois dans un
   service refusé (409), accepté dans un autre service.
2. Exiger une formation pour un poste l'attribue aux employés qui l'occupent,
   et seulement à eux (pas à tout le service).
3. Un employé peut occuper plusieurs postes ; en ajouter un lui attribue les
   formations de ce poste, en retirer un ne lui retire rien.
4. Suivre un compte avec des postes lui attribue tout de suite leurs formations.
5. Supprimer un poste laisse les formations déjà attribuées.
"""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_rh_postes_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  (shim d'abord, voir CLAUDE.md)
from database import get_db  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from app.routers import rh_outil, rh_outil_postes  # noqa: E402

AUTEUR = {"id": 1, "nom": "Auteur Test", "email": "auteur.test@local", "role": "superadmin"}
for mod in (rh_outil, rh_outil_postes):
    mod._require = lambda request: AUTEUR
    mod.log_action = lambda **k: None

_now = datetime.now().isoformat(timespec="seconds")
with get_db() as _c:
    def _compte(email, nom, role):
        return _c.execute("INSERT INTO users (email,nom,password_hash,role,actif,created_at) VALUES (?,?,?,?,1,?)",
                          (email, nom, "x", role, _now)).lastrowid
    U_ANNE = _compte("anne.postes@local", "Anne Postes", "fabrication")
    U_BOB = _compte("bob.postes@local", "Bob Postes", "fabrication")
    U_CLAIRE = _compte("claire.postes@local", "Claire Postes", "fabrication")
    def _formation(lib):
        return _c.execute("INSERT INTO rh_outil_formations (libelle, cree_le) VALUES (?,?)", (lib, _now)).lastrowid
    F_COND = _formation("Conduite test postes")
    F_REPIQ = _formation("Repiquage test postes")
    _c.commit()

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(62) + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


def statut(f):
    try:
        f()
    except HTTPException as e:
        return e.status_code
    return 200


def a_formation(user_id, formation_id):
    with get_db() as c:
        return c.execute(
            """SELECT 1 FROM rh_outil_membre_formations a JOIN rh_outil_membres m ON m.id = a.membre_id
                WHERE m.user_id=? AND a.formation_id=?""", (user_id, formation_id)).fetchone() is not None


def membre_id(user_id):
    with get_db() as c:
        return c.execute("SELECT id FROM rh_outil_membres WHERE user_id=?", (user_id,)).fetchone()["id"]


# 1. Catalogue.
P_COND = rh_outil_postes.add_poste(rh_outil_postes.PosteIn(libelle="Conducteur", service="fabrication"), None)["id"]
P_REPIQ = rh_outil_postes.add_poste(rh_outil_postes.PosteIn(libelle="Repiqueur", service="fabrication"), None)["id"]
check("doublon dans le même service refusé (409)", statut(lambda: rh_outil_postes.add_poste(
    rh_outil_postes.PosteIn(libelle="conducteur", service="fabrication"), None)), 409)
check("même intitulé dans un autre service accepté", statut(lambda: rh_outil_postes.add_poste(
    rh_outil_postes.PosteIn(libelle="Conducteur", service="logistique"), None)), 200)
check("service inconnu refusé (400)", statut(lambda: rh_outil_postes.add_poste(
    rh_outil_postes.PosteIn(libelle="X", service="nimporte"), None)), 400)

# 4. Anne suivie comme conductrice, Bob sans poste (même service).
rh_outil.add_membre(rh_outil.MembreIn(user_id=U_ANNE, postes=[P_COND]), None)
rh_outil.add_membre(rh_outil.MembreIn(user_id=U_BOB), None)

# 2. Formation exigée pour le poste Conducteur.
r = rh_outil.set_exige("formations", F_COND, rh_outil.ExigeIn(postes=[P_COND]), None)
check("exigée pour un poste : attribuée à son titulaire", a_formation(U_ANNE, F_COND))
check("pas au reste du service", a_formation(U_BOB, F_COND), False)
check("attribution comptée", r["attribues"], 1)
cat = {e["id"]: e for e in rh_outil.list_catalogue("formations", None)["elements"]}
check("catalogue : postes exigés renvoyés", cat[F_COND]["postes"], [P_COND])
check("poste inconnu refusé dans « exigé pour » (400)", statut(lambda: rh_outil.set_exige(
    "formations", F_COND, rh_outil.ExigeIn(postes=[999999]), None)), 400)

# 4 bis. Suivre un compte avec un poste déjà exigé : formation tout de suite.
rh_outil.add_membre(rh_outil.MembreIn(user_id=U_CLAIRE, postes=[P_COND]), None)
check("suivi avec un poste : ses formations attribuées", a_formation(U_CLAIRE, F_COND))

# 3. Plusieurs postes.
rh_outil.set_exige("formations", F_REPIQ, rh_outil.ExigeIn(postes=[P_REPIQ]), None)
r = rh_outil_postes.set_postes_membre(membre_id(U_BOB), rh_outil_postes.PostesMembreIn(postes=[P_COND, P_REPIQ]), None)
check("deux postes : formations des deux attribuées", (a_formation(U_BOB, F_COND), a_formation(U_BOB, F_REPIQ)), (True, True))
check("deux postes : nombre attribué", r["attribues"], 2)
rh_outil_postes.set_postes_membre(membre_id(U_BOB), rh_outil_postes.PostesMembreIn(postes=[P_REPIQ]), None)
check("poste retiré : la formation reste", a_formation(U_BOB, F_COND))
membres = {m["user_id"]: m for m in rh_outil.list_membres(None)["membres"]}
check("liste des employés : postes renvoyés", [p["id"] for p in membres[U_BOB]["postes"]], [P_REPIQ])

# 5. Suppression d'un poste.
rh_outil_postes.delete_poste(P_COND, None)
check("poste supprimé : formation gardée", a_formation(U_ANNE, F_COND))
membres = {m["user_id"]: m for m in rh_outil.list_membres(None)["membres"]}
check("poste supprimé : retiré de l'employé", membres[U_ANNE]["postes"], [])
cat = {e["id"]: e for e in rh_outil.list_catalogue("formations", None)["elements"]}
check("poste supprimé : retiré des exigences", cat[F_COND]["postes"], [])

if ECHECS:
    print(f"\n{len(ECHECS)} échec(s)")
    sys.exit(1)
print("\nTout est vert.")

"""
MyRH : suivre un compte MySifa existant (POST /api/rh-outil/membres).

Lancer : python3 tests/test_rh_outil_suivi.py

Ce test verrouille :
1. Suivre un compte existant ne crée aucun compte (pas de doublon).
2. Le contrat fourni est écrit dans la fiche Paie AVANT les attributions :
   les documents exigés pour ce contrat arrivent tout de suite.
3. Sans contrat fourni, la fiche Paie existante n'est pas touchée.
4. Un compte déjà suivi est refusé (409), un contrat inconnu aussi (400).
5. La liste des comptes (GET /employes) porte le contrat de la fiche Paie
   et signale les comptes déjà suivis.
"""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Base isolée AVANT tout import projet (tests lancés en parallèle en CI).
_tmp = tempfile.mkdtemp(prefix="mysifa_rh_suivi_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  (shim d'abord, voir CLAUDE.md)
from database import get_db  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from app.routers import rh_outil  # noqa: E402

AUTEUR = {"id": 1, "nom": "Auteur Test", "email": "auteur.test@local", "role": "superadmin"}
rh_outil._require = lambda request: AUTEUR
rh_outil.log_action = lambda **k: None

_now = datetime.now().isoformat(timespec="seconds")
with get_db() as _c:
    def _compte(email, nom, role):
        return _c.execute("INSERT INTO users (email,nom,password_hash,role,actif,created_at) VALUES (?,?,?,?,1,?)",
                          (email, nom, "x", role, _now)).lastrowid
    U_ANNE = _compte("anne.test@local", "Anne Test", "fabrication")
    U_BOB = _compte("bob.test@local", "Bob Test", "logistique")
    # Bob a déjà une fiche Paie remplie par la comptabilité.
    _c.execute("INSERT INTO paie_employes (user_id, contrat_type, date_debut, date_fin, updated_at, updated_by) "
               "VALUES (?,?,?,?,?,?)", (U_BOB, "CDI", "2024-01-15", None, _now, "compta@local"))
    DOC = _c.execute("INSERT INTO rh_outil_documents (libelle, cree_le) VALUES ('Attestation test CDD', ?)", (_now,)).lastrowid
    _c.execute("INSERT INTO rh_outil_document_contrats (document_id, contrat) VALUES (?, 'CDD')", (DOC,))
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


def nb_comptes():
    with get_db() as c:
        return c.execute("SELECT COUNT(*) FROM users").fetchone()[0]


avant = nb_comptes()

# 1-2. Anne, sans fiche Paie : suivie avec un CDD, le document exigé arrive.
r = rh_outil.add_membre(rh_outil.MembreIn(user_id=U_ANNE, date_arrivee="2026-11-02",
                                          contrat_type="CDD", contrat_fin="2027-05-01"), None)
check("suivi d'un compte existant : succès", r["success"])
check("aucun compte créé", nb_comptes(), avant)
with get_db() as c:
    pe = c.execute("SELECT contrat_type, date_debut, date_fin FROM paie_employes WHERE user_id=?", (U_ANNE,)).fetchone()
    m = c.execute("SELECT id, date_arrivee FROM rh_outil_membres WHERE user_id=?", (U_ANNE,)).fetchone()
    doc = c.execute("SELECT 1 FROM rh_outil_membre_documents WHERE membre_id=? AND document_id=?", (m["id"], DOC)).fetchone()
check("contrat écrit dans la fiche Paie", (pe["contrat_type"], pe["date_debut"], pe["date_fin"]),
      ("CDD", "2026-11-02", "2027-05-01"))
check("date d'arrivée enregistrée", m["date_arrivee"], "2026-11-02")
check("document exigé pour le contrat attribué", doc is not None)
check("attributions comptées dans la réponse", r["attribues"] >= 1)

# 3. Bob, sans contrat fourni : sa fiche Paie reste telle quelle.
rh_outil.add_membre(rh_outil.MembreIn(user_id=U_BOB), None)
with get_db() as c:
    pe = c.execute("SELECT contrat_type, date_debut, updated_by FROM paie_employes WHERE user_id=?", (U_BOB,)).fetchone()
check("fiche Paie existante non touchée", (pe["contrat_type"], pe["date_debut"], pe["updated_by"]),
      ("CDI", "2024-01-15", "compta@local"))

# 4. Refus.
check("compte déjà suivi refusé (409)", statut(lambda: rh_outil.add_membre(rh_outil.MembreIn(user_id=U_ANNE), None)), 409)
check("compte inconnu refusé (404)", statut(lambda: rh_outil.add_membre(rh_outil.MembreIn(user_id=999999), None)), 404)
check("contrat inconnu refusé (400)", statut(lambda: rh_outil.add_membre(
    rh_outil.MembreIn(user_id=U_BOB, contrat_type="Pigiste"), None)), 400)

# 5. Liste des comptes.
emp = {e["user_id"]: e for e in rh_outil.list_employes(None)["employes"]}
check("liste : compte suivi signalé", emp[U_ANNE]["deja_ajoute"])
check("liste : contrat de la fiche Paie", emp[U_BOB]["contrat_type"], "CDI")
check("liste : libellé du service", bool(emp[U_BOB]["service_label"]))

if ECHECS:
    print(f"\n{len(ECHECS)} échec(s)")
    sys.exit(1)
print("\nTout est vert.")

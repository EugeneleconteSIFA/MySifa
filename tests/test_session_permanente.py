"""
Sessions sans déconnexion pour direction, administration et superadmin.

Lancer : python3 tests/test_session_permanente.py

Ce test verrouille :
1. Un rôle admin reçoit une session longue au login (base et cookie), les
   autres rôles gardent SESSION_HOURS.
2. /api/auth/me prolonge une session admin déjà ouverte (y compris une
   ancienne session de 6 h) et repose le cookie ; il ne touche pas une
   session opérateur.
3. La prolongation n'écrit qu'une fois par jour.
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _base_temporaire  # noqa: E402,F401  base jetable, avant tout le reste
import database  # noqa: E402,F401
from database import get_db  # noqa: E402
from config import COOKIE_NAME, SESSION_HOURS, SESSION_HOURS_PERMANENTE  # noqa: E402
from services.auth_service import create_session, hash_password, prolonger_session  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(62) + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


def ajouter(email, role):
    with get_db() as c:
        c.execute("INSERT INTO users (email,nom,password_hash,role,actif,created_at) VALUES (?,?,?,?,1,?)",
                  (email, email, hash_password("motdepasse-test"), role, datetime.now().isoformat()))
        c.commit()
        return c.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()["id"]


def heures_restantes(token):
    with get_db() as c:
        exp = c.execute("SELECT expires_at FROM sessions WHERE token=?", (token,)).fetchone()["expires_at"]
    return (datetime.fromisoformat(exp) - datetime.now()).total_seconds() / 3600


def max_age(reponse):
    for v in reponse.headers.get_list("set-cookie"):
        if v.startswith(COOKIE_NAME + "="):
            for part in v.split(";"):
                if part.strip().lower().startswith("max-age="):
                    return int(part.split("=")[1])
    return None


admin_id = ajouter("direction.test@local", "direction")
ajouter("operateur.test@local", "fabrication")

cl = TestClient(main.app)
r = cl.post("/api/auth/login", json={"email": "direction.test@local", "password": "motdepasse-test"})
check("login direction : cookie longue durée", max_age(r), SESSION_HOURS_PERMANENTE * 3600)
check("login direction : session longue en base",
      heures_restantes(cl.cookies.get(COOKIE_NAME)) > SESSION_HOURS_PERMANENTE - 1)

cl_op = TestClient(main.app)
r = cl_op.post("/api/auth/login", json={"email": "operateur.test@local", "password": "motdepasse-test"})
check("login fabrication : cookie 6 h", max_age(r), SESSION_HOURS * 3600)
tok_op = cl_op.cookies.get(COOKIE_NAME)
check("login fabrication : session 6 h en base", heures_restantes(tok_op) <= SESSION_HOURS)
r = cl_op.get("/api/auth/me")
check("me fabrication : cookie non reposé", max_age(r), None)
check("me fabrication : session inchangée", heures_restantes(tok_op) <= SESSION_HOURS)

# Ancienne session de 6 h ouverte avant le changement : prolongée à la visite.
ancien = create_session(admin_id)
check("ancienne session admin : 6 h au départ", heures_restantes(ancien) <= SESSION_HOURS)
cl_ancien = TestClient(main.app)
cl_ancien.cookies.set(COOKIE_NAME, ancien)
r = cl_ancien.get("/api/auth/me")
check("me direction : utilisateur renvoyé", (r.json() or {}).get("role"), "direction")
check("me direction : cookie reposé longue durée", max_age(r), SESSION_HOURS_PERMANENTE * 3600)
check("me direction : session prolongée en base",
      heures_restantes(ancien) > SESSION_HOURS_PERMANENTE - 1)

check("deuxième visite le même jour : pas d'écriture", prolonger_session(ancien, "direction"), False)
with get_db() as c:
    c.execute("UPDATE sessions SET expires_at=? WHERE token=?",
              ((datetime.now() + timedelta(hours=SESSION_HOURS_PERMANENTE - 30)).isoformat(), ancien))
    c.commit()
check("visite le lendemain : prolongée", prolonger_session(ancien, "direction"), True)
with get_db() as c:
    c.execute("UPDATE sessions SET expires_at=? WHERE token=?",
              ((datetime.now() - timedelta(minutes=1)).isoformat(), ancien))
    c.commit()
check("session déjà expirée : pas ressuscitée", prolonger_session(ancien, "direction"), False)

if ECHECS:
    print(f"\n{len(ECHECS)} échec(s)")
    sys.exit(1)
print("\nTout est vert.")

"""
Agent IA du widget : catalogue d'actions, boucle, confirmation.

Lancer : python3 tests/test_agent_ia.py

Ce test verrouille :
1. Une action proposée est validée AVANT d'atteindre l'utilisateur :
   paramètre inconnu, valeur hors liste, identifiant inexistant → refus.
2. Les actions offertes dépendent du rôle (pas de dossier au planning pour
   l'expédition, pas de mouvement de stock pour le commercial).
3. La boucle : une lecture puis une proposition, sans rien écrire en base
   métier ; la carte revient au widget.
4. La confirmation rejoue l'écran existant avec la session de l'utilisateur
   (ici la création d'un post-it), une seule fois même sur double clic.
Le modèle est remplacé par un faux client : aucun appel réseau.
"""

import os
import sys
import tempfile
import types
from datetime import datetime
from pathlib import Path

# Base isolée AVANT tout import projet : la CI lance les tests en parallèle,
# deux tests qui migrent la même base se marchent dessus (colonne en double).
_tmp = tempfile.mkdtemp(prefix="mysifa_agent_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  (shim d'abord, voir CLAUDE.md)
from database import get_db  # noqa: E402
from app.services import agent_actions as aa  # noqa: E402
from app.services import agent_ia  # noqa: E402

# Jeu de données minimal : un super admin pour la session, une machine.
with get_db() as _c:
    _now = datetime.now().isoformat(timespec="seconds")
    _c.execute("INSERT INTO users (email,nom,password_hash,role,actif,created_at) VALUES (?,?,?,?,1,?)",
               ("agent.test@local", "Agent Test", "x", "superadmin", _now))
    _c.execute("INSERT INTO machines (nom,code,actif,created_at) VALUES ('Machine test','MTEST',1,?)", (_now,))
    _c.commit()

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(62) + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


def refuse(label, f):
    try:
        f()
        check(label, "accepté", "refusé")
    except aa.ActionInvalide:
        check(label, True)


sup = {"id": 0, "email": "test@local", "role": "superadmin", "nom": "Test"}
expe = {"id": 0, "email": "x@local", "role": "expedition", "nom": "X"}
com = {"id": 0, "email": "c@local", "role": "commercial", "nom": "C"}

# ── 1. Validation ────────────────────────────────────────────────────────────
p = aa.preparer(sup, "postit_creer", {"type": "today", "title": "Appeler le transporteur"})
check("post-it : chemin", (p["methode"], p["chemin"]), ("POST", "/api/postits"))
check("post-it : corps", p["corps"], {"type": "today", "title": "Appeler le transporteur"})
refuse("paramètre inconnu refusé", lambda: aa.preparer(sup, "postit_creer", {"type": "today", "title": "x", "z": 1}))
refuse("valeur hors liste refusée", lambda: aa.preparer(sup, "postit_creer", {"type": "demain", "title": "x"}))
refuse("obligatoire manquant refusé", lambda: aa.preparer(sup, "postit_creer", {"type": "today"}))
refuse("action inconnue refusée", lambda: aa.preparer(sup, "drop_table", {}))
refuse("identifiant inexistant refusé", lambda: aa.preparer(sup, "prix_produit_fini",
                                                             {"produit_id": 99999999, "prix_unitaire_ht": 1}))
refuse("date mal formée refusée", lambda: aa.preparer(sup, "tache_creer", {"titre": "x", "echeance": "28/10"}))
refuse("prix sans montant refusé", lambda: aa.preparer(sup, "prix_matiere", {"matiere_id": 1}))
with get_db() as c:
    mid = c.execute("SELECT id FROM machines ORDER BY id LIMIT 1").fetchone()
if mid:
    p = aa.preparer(sup, "planning_ajouter", {"machine_id": mid[0], "reference": "TEST-1", "duree_heures": "6,5"})
    check("planning : id dans le chemin", p["chemin"], f"/api/planning/machines/{mid[0]}/entries")
    check("planning : nombre à virgule converti", p["corps"]["duree_heures"], 6.5)
    check("planning : machine nommée sur la carte", p["details"][0][0], "Machine")

# ── 2. Rôles ─────────────────────────────────────────────────────────────────
cles = lambda u: {a["cle"] for a in aa.catalogue_pour(u)}  # noqa: E731
check("expédition : pas de dossier au planning", "planning_ajouter" in cles(expe), False)
check("commercial : pas de mouvement de stock", "stock_mouvement_pf" in cles(com), False)
check("superadmin : tout le catalogue", len(cles(sup)), len(aa.CATALOGUE))
check("description listée pour l'agent", "postit_creer" in aa.description_catalogue(aa.catalogue_pour(sup)))

# ── 3. Boucle avec un faux modèle ────────────────────────────────────────────
class _B:
    def __init__(self, **kw):
        self.__dict__.update(kw)


tours = [
    types.SimpleNamespace(stop_reason="tool_use", content=[
        _B(type="tool_use", id="t1", name="mysifa_bases", input={})]),
    types.SimpleNamespace(stop_reason="tool_use", content=[
        _B(type="tool_use", id="t2", name="proposer_action",
           input={"action": "postit_creer", "parametres": {"type": "today", "title": "Test agent"},
                  "resume": "Créer un post-it « Test agent »."})]),
    types.SimpleNamespace(stop_reason="end_turn", content=[_B(type="text", text="Post-it prêt, à confirmer.")]),
]
appels = []
agent_ia._client = lambda: types.SimpleNamespace(messages=types.SimpleNamespace(
    create=lambda **kw: (appels.append(kw), tours[len(appels) - 1])[1]))
with get_db() as conn:
    res = agent_ia.converser(conn, sup, [{"role": "user", "content": "Note : rappeler X"}], {"url": "/stock"})
check("boucle : outils appelés", res["outils"], ["mysifa_bases", "proposer_action"])
check("boucle : une carte", len(res["actions"]), 1)
check("boucle : réponse texte", res["reponse"], "Post-it prêt, à confirmer.")
check("boucle : modèle par défaut", appels[0]["model"], agent_ia.choisir_modele(None)["id"])
check("boucle : outils lecture + action", "proposer_action" in [o["name"] for o in appels[0]["tools"]])
jeton = res["actions"][0]["jeton"]

# ── 4. Confirmation par l'API ────────────────────────────────────────────────
from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402
from app.services.auth_service import create_session  # noqa: E402

with get_db() as c:
    u = c.execute("SELECT id,email FROM users WHERE role='superadmin' AND COALESCE(actif,1)=1 ORDER BY id LIMIT 1").fetchone()
if u:
    tok = create_session(u["id"])
    with get_db() as c:   # l'action appartient à l'utilisateur de la session
        c.execute("UPDATE ai_actions SET user_email=? WHERE jeton=?", (u["email"], jeton))
        c.commit()
    cl = TestClient(main.app)
    cl.cookies.set("sifa_token", tok)
    r = cl.post(f"/api/ai/actions/{jeton}/confirmer")
    check("confirmer : exécuté", (r.status_code, r.json().get("ok")), (200, True))
    r2 = cl.post(f"/api/ai/actions/{jeton}/confirmer")
    check("double clic : refusé", r2.status_code, 409)
    check("config : widget actif pour superadmin", cl.get("/api/ai/config").json()["actif"], True)
    conf = cl.get("/api/ai/config").json()
    check("config : annonce pour un admin", bool(conf.get("annonce") and conf["annonce"].get("texte")), True)
    msgs = [{"role": "user", "content": "Stock en A141 ?"}, {"role": "assistant", "content": "Vide."}]
    cid = cl.post("/api/ai/conversations", json={"messages": msgs}).json()["id"]
    liste = cl.get("/api/ai/conversations").json()
    check("conversation : listée avec son titre", (liste[0]["id"], liste[0]["titre"]), (cid, "Stock en A141 ?"))
    msgs.append({"role": "user", "content": "Et B121 ?"})
    cl.put(f"/api/ai/conversations/{cid}", json={"messages": msgs})
    check("conversation : rouverte à jour", len(cl.get(f"/api/ai/conversations/{cid}").json()["messages"]), 3)
    with get_db() as c:
        c.execute("INSERT INTO users (email,nom,password_hash,role,actif,created_at) VALUES "
                  "('autre@local','Autre','x','direction',1,'2026-01-01')")
        c.commit()
        autre = c.execute("SELECT id FROM users WHERE email='autre@local'").fetchone()[0]
    cl2 = TestClient(main.app)
    cl2.cookies.set("sifa_token", create_session(autre))
    check("conversation : invisible pour un autre", cl2.get(f"/api/ai/conversations/{cid}").status_code, 404)
    check("conversation : liste d'un autre vide", cl2.get("/api/ai/conversations").json(), [])
    check("conversation : supprimée", cl.delete(f"/api/ai/conversations/{cid}").json().get("ok"), True)
    ctx = {"app": main.app, "cookies": {"sifa_token": tok}}
    lu = agent_ia.lire_ecran(ctx, {"ecran": "stock_emplacement", "parametres": {"emplacement": "A141"}})
    check("lire_ecran : l'écran MyStock répond", '"erreur"' in lu, False)
    lu = agent_ia.lire_ecran(ctx, {"ecran": "stock_emplacement", "parametres": {"x": 1}})
    check("lire_ecran : paramètre inconnu refusé", "inconnu" in lu, True)
    check("lire_ecran : sans contexte, refus propre", "erreur" in agent_ia.lire_ecran(None, {"ecran": "reunions"}), True)
    with get_db() as c:
        n = c.execute("SELECT COUNT(*) FROM postits WHERE title='Test agent' AND user_id=?", (u["id"],)).fetchone()[0]
        check("post-it réellement créé par l'écran", n, 1)
        c.execute("DELETE FROM postits WHERE title='Test agent' AND user_id=?", (u["id"],))
        c.execute("DELETE FROM ai_actions WHERE jeton=?", (jeton,))
        c.execute("DELETE FROM sessions WHERE token=?", (tok,))
        c.commit()

print()
if ECHECS:
    print(f"{len(ECHECS)} échec(s)")
    sys.exit(1)
print("Tout est vert.")

"""
Journal des actions : ce qui entre, ce qui n'entre pas, et ce qui ne double pas.

Le journal ne couvrait que 7 routers sur 65. Il est desormais alimente par un
middleware qui journalise toute ecriture aboutie, en s'effacant devant les
appels explicites des routers. Trois choses doivent rester vraies, sinon le
journal redevient soit troue, soit illisible :

- toute route d'ecriture de MySifa tombe dans un module NOMME (jamais "autre"),
  sans quoi le filtre par module ne sert a rien ;
- un endpoint qui appelle deja `log_action` n'ecrit pas une seconde ligne
  generique par-dessus la sienne, plus precise ;
- ce qui ne doit jamais etre recopie (mots de passe, cles, contenu des
  discussions, du coffre et de la paie) ne l'est pas.

Le premier cas se joue sur la taxonomie seule, sans FastAPI : il balaie les
decorateurs des routers du depot. Les suivants montent une mini-application
si FastAPI est installe, et sont sautes sinon (la CI ne l'installe pas).

Lancer : python3 tests/test_audit_journal.py
"""

import importlib.util
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
FAIL: list[str] = []


def verifier(libelle, obtenu, attendu):
    if obtenu == attendu:
        print(f"  ok   {libelle}")
    else:
        print(f"  KO   {libelle} : obtenu {obtenu!r}, attendu {attendu!r}")
        FAIL.append(libelle)


def _charger(nom, chemin):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tx = _charger("audit_taxonomy", RACINE / "app" / "core" / "audit_taxonomy.py")


# ─── 1. Aucune route d'ecriture ne tombe dans "autre" ────────────────
def _routes_ecriture():
    """Les (methode, chemin) de tous les endpoints d'ecriture du depot."""
    prefixes = {}
    dossier = RACINE / "app" / "routers"
    for f in sorted(dossier.glob("*.py")):
        if f.name.startswith("_"):
            continue
        src = f.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"APIRouter\(([^)]*)\)", src, re.S)
        pre = ""
        if m:
            mm = re.search(r'prefix\s*=\s*["\']([^"\']*)["\']', m.group(1))
            if mm:
                pre = mm.group(1)
        prefixes[f.name] = pre
    # Prefixes poses au moment du include_router, dans main.py.
    main_src = (RACINE / "main.py").read_text(encoding="utf-8", errors="replace")
    for fichier, variable in (("matiere_prix.py", "router_matiere_prix"),
                              ("expe_departs.py", "expe_departs_router"),
                              ("expe_pilotage.py", "expe_pilotage_router")):
        m = re.search(
            rf'include_router\({variable},\s*prefix="([^"]*)"', main_src
        )
        if m:
            prefixes[fichier] = m.group(1) + prefixes.get(fichier, "")

    pat = re.compile(
        r'@router\.(post|put|patch|delete)\(\s*[fr]?["\']([^"\']+)["\']', re.I
    )
    for fichier, pre in prefixes.items():
        src = (dossier / fichier).read_text(encoding="utf-8", errors="replace")
        for m in pat.finditer(src):
            yield fichier, m.group(1).upper(), pre + m.group(2)


def test_toutes_les_routes_ont_un_module():
    orphelines = [
        f"{fichier} {meth} {chemin}"
        for fichier, meth, chemin in _routes_ecriture()
        if not tx.is_skipped(chemin) and tx.resolve_module(chemin) == "autre"
    ]
    verifier("aucune route d'ecriture sans module", orphelines, [])


def test_libelles_complets():
    """Un module ou une action sans libelle s'afficherait en brut a l'ecran."""
    modules = {
        tx.resolve_module(c)
        for _, _, c in _routes_ecriture()
        if not tx.is_skipped(c)
    }
    actions = {
        tx.resolve_action(m, c)
        for _, m, c in _routes_ecriture()
        if not tx.is_skipped(c)
    }
    verifier("tous les modules ont un libelle", sorted(modules - set(tx.MODULE_LABELS)), [])
    verifier("toutes les actions ont un libelle", sorted(actions - set(tx.ACTION_LABELS)), [])


def test_verbe_deduit_du_chemin():
    verifier("cloture", tx.resolve_action("POST", "/api/ao/12/cloturer"), "CLOSE")
    verifier("validation", tx.resolve_action("PUT", "/api/qualite/documents/3/valider"), "VALIDATE")
    verifier("saisie atelier", tx.resolve_action("POST", "/api/stock/mouvement"), "SAISIE")
    verifier("import", tx.resolve_action("POST", "/api/matiere/import-excel"), "IMPORT")
    # Un DELETE reste une suppression : sinon effacer un commentaire passerait
    # pour en ecrire un.
    verifier(
        "DELETE non requalifie",
        tx.resolve_action("DELETE", "/api/taches/12/commentaires/9"),
        "DELETE",
    )
    # Le dernier segment parlant l'emporte sur le premier.
    verifier(
        "le segment final gagne",
        tx.resolve_action("POST", "/api/qualite/documents/3/valider"),
        "VALIDATE",
    )


def test_module_prefixe_le_plus_precis():
    verifier("besoins matieres", tx.resolve_module("/api/stock/besoins-matieres/x"), "besoins")
    verifier("stock general", tx.resolve_module("/api/stock/mouvement"), "stock")
    verifier("GED", tx.resolve_module("/api/qualite/ged/documents"), "qualite_ged")
    verifier("qualite", tx.resolve_module("/api/qualite/nc/4"), "qualite")


def test_redaction():
    charge = {"nom": "Eugene", "password": "hunter2", "cle_api": "sk-1",
              "imbrique": {"token": "abc", "qte": 3}}
    net = tx.redact(charge)
    verifier("mot de passe masque", net["password"], "***")
    verifier("cle masquee", net["cle_api"], "***")
    verifier("jeton imbrique masque", net["imbrique"]["token"], "***")
    verifier("donnee anodine conservee", net["imbrique"]["qte"], 3)


# ─── 2. La couverture voit les routes, quelle que soit la version ───
def test_parcours_des_routes():
    """`routes_ecriture` doit voir a travers `include_router`.

    Selon la version de FastAPI, l'inclusion aplatit les routes dans
    `app.routes` (<= 0.115, celle de production) ou pose un routeur paresseux
    qui les garde ailleurs (>= 0.140). Un parcours qui ne connaitrait qu'une
    forme afficherait « 4 routes couvertes » sur l'autre — un ecran de
    couverture qui ment.
    """
    try:
        from fastapi import APIRouter, FastAPI
    except Exception:
        print("  --   parcours des routes : FastAPI absent, cas saute")
        return

    tx.MODULE_LABELS.setdefault("taches", "Tâches")
    interne = APIRouter()

    @interne.post("/api/taches")
    def creer():
        return {}

    @interne.delete("/api/taches/{tid}")
    def supprimer(tid: int):
        return {}

    @interne.get("/api/taches")
    def lister():
        return {}

    prefixe = APIRouter(prefix="/api/expe")

    @prefixe.post("/departs")
    def creer_depart():
        return {}

    application = FastAPI()
    application.include_router(interne)
    application.include_router(prefixe)

    vues = sorted(tx.routes_ecriture(application))
    verifier(
        "routes d'ecriture vues a travers include_router",
        vues,
        [("DELETE", "/api/taches/{tid}"), ("POST", "/api/expe/departs"),
         ("POST", "/api/taches")],
    )


# ─── 3. Le middleware, si FastAPI est disponible ────────────────────
def test_middleware():
    try:
        from fastapi import FastAPI, HTTPException, Request
        from fastapi.testclient import TestClient
    except Exception:
        print("  --   middleware : FastAPI absent, cas sautes")
        return

    sys.path.insert(0, str(RACINE))
    import app.services.audit_service as audit
    import app.core.audit_middleware as mw

    lignes: list[dict] = []

    def faux_log(**kw):
        audit._marquer_appel()
        lignes.append(kw)

    audit.log_action = faux_log
    mw.log_action = faux_log
    mw._utilisateur = lambda scope: {"id": 7, "nom": "Eugene", "role": "superadmin"}

    application = FastAPI()
    application.add_middleware(mw.AuditMiddleware)

    @application.post("/api/reunions/{rid}/actions")
    def creer_action(rid: int):
        return {"ok": True}

    @application.post("/api/expe/departs")
    def creer_depart(request: Request):
        audit.log_action(user={"id": 7, "nom": "Eugene"}, action="CREATE",
                         module="expe", objet="Depart 42", request=request)
        return {"ok": True}

    @application.post("/api/settings/utilisateurs")
    def creer_utilisateur():
        raise HTTPException(status_code=403, detail="refus")

    @application.post("/api/auth/login")
    def login():
        raise HTTPException(status_code=401, detail="ko")

    @application.post("/api/perf/releve")
    def releve():
        return {"ok": True}

    c = TestClient(application, raise_server_exceptions=False)
    c.post("/api/reunions/8/actions", json={"quoi": "relancer"})
    c.post("/api/expe/departs", json={"x": 1})
    c.post("/api/settings/utilisateurs", json={"email": "a@b.c"})
    c.post("/api/auth/login", json={"email": "a@b.c", "password": "x"})
    c.post("/api/perf/releve", json={"ms": 12})

    verifier("nombre de lignes", len(lignes), 3)
    verifier("module deduit", lignes[0]["module"], "reunions")
    verifier("objet lisible", lignes[0]["objet"], "Creer action · rid=8")
    verifier("pas de doublon sur appel explicite", lignes[1]["objet"], "Depart 42")
    verifier("refus journalise", lignes[2]["action"], "DENIED")
    verifier("session expiree ignoree",
             [l for l in lignes if l["module"] == "auth"], [])
    verifier("bruit technique ignore",
             [l for l in lignes if l["module"] == "profil"], [])


if __name__ == "__main__":
    print("Journal des actions\n" + "=" * 62)
    test_toutes_les_routes_ont_un_module()
    test_libelles_complets()
    test_verbe_deduit_du_chemin()
    test_module_prefixe_le_plus_precis()
    test_redaction()
    test_parcours_des_routes()
    test_middleware()
    print("\n" + "=" * 62)
    if FAIL:
        print(f"{len(FAIL)} echec(s) :")
        for f in FAIL:
            print("  -", f)
        sys.exit(1)
    print("Tous les cas passent.")

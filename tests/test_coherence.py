"""
Contrôleurs de cohérence (app/services/coherence.py).

Lancer : python3 tests/test_coherence.py

Ce test verrouille :
1. Chaque règle trouve son cas sur un jeu de données construit pour elle :
   dossier en cours sans saisie, fin prévue après la livraison, quantité loin
   de l'OF, OF contre fiche, OF contre planning, BL sans départ, départ sans
   BL, BL inconnu de RVGI, article livré sans sortie de stock, date aberrante.
2. Un second passage ne crée aucun doublon ; un écart corrigé passe résolu de
   lui-même ; une règle désactivée vide sa part de la file.
3. Un écart expliqué sort de la pastille sans disparaître.
4. L'agent lit la file (mysifa_ecarts) et peut proposer de l'expliquer.
5. L'API Paramètres répond et refuse un rôle non autorisé.
"""

import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

_tmp = tempfile.mkdtemp(prefix="mysifa_coherence_test_")
os.environ["DB_PATH"] = os.path.join(_tmp, "test.db")
os.environ["ERP_MIRROR_DB"] = os.path.join(_tmp, "erp_mirror.db")

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  (shim d'abord, voir CLAUDE.md)
from database import get_db  # noqa: E402
from app.services import coherence  # noqa: E402

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(64) + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


def inserer(conn, table, **valeurs):
    """INSERT qui complète les colonnes NOT NULL sans défaut : le test ne
    dépend pas du détail d'un schéma qui évolue."""
    for r in conn.execute(f"PRAGMA table_info({table})").fetchall():
        nom, typ, notnull, defaut, pk = r[1], (r[2] or "").upper(), r[3], r[4], r[5]
        if pk or nom in valeurs or not notnull or defaut is not None:
            continue
        valeurs[nom] = 0 if ("INT" in typ or "REAL" in typ) else "x"
    cols = ",".join(valeurs)
    cur = conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({','.join('?' * len(valeurs))})",
                       list(valeurs.values()))
    return cur.lastrowid


now = coherence.maintenant()
J = lambda n: (now + timedelta(days=n)).strftime("%Y-%m-%d")  # noqa: E731
T = lambda n: (now + timedelta(days=n)).strftime("%Y-%m-%dT%H:%M:%S")  # noqa: E731

# ── Jeu de données MySifa ────────────────────────────────────────────────────
with get_db() as c:
    m1 = inserer(c, "machines", nom="Machine A test", code="MAT", actif=1)
    m2 = inserer(c, "machines", nom="Machine B test", code="MBT", actif=1)
    support_ok = inserer(c, "matieres_premieres", reference="SUP-1", designation="Vélin 80 g")
    support_ko = inserer(c, "matieres_premieres", reference="SUP-2", designation="Couché 90 g")

    def pe(ref, statut, **kw):
        return inserer(c, "planning_entries", machine_id=kw.pop("machine_id", m1), position=1, reference=ref,
                       duree_heures=4.0, statut=statut, created_at=T(-5), updated_at=T(-1), **kw)

    pe_sans_saisie = pe("D-SANS-SAISIE", "en_cours")
    pe_retard = pe("D-RETARD", "attente", planned_end=T(10), date_livraison=J(2))
    of_qte = inserer(c, "of_imports", of_numero="OF-QTE", reference="D-QTE", qte_etiquettes=1000, valide=0)
    pe_qte = pe("D-QTE", "termine", of_import_id=of_qte)
    inserer(c, "production_data", no_dossier="D-QTE", operation_code="89", quantite_traitee=700,
            fin_dossier=1, planning_entry_id=pe_qte, date_operation=T(-1), machine="Machine A test")
    of_doc = inserer(c, "of_imports", of_numero="OF-DOC", reference="77/0001", machine="Machine B test",
                     laize=330, qte_au_mille=10.0, matiere_ref_id=support_ko, valide=0)
    pe_doc = pe("D-DOC", "attente", of_import_id=of_doc, ref_produit="77/0001", laize=440)
    inserer(c, "fiches_techniques", reference="77/0001", ref_produit_norm="77/0001", machine="Machine A test",
            laize=330, qte_au_mille=12.0, support_ref_id=support_ok)

    # Départs : un BL porté, un validé sans BL, un BL inconnu de RVGI, une date aberrante.
    inserer(c, "expe_departs", statut="valide", date_enlevement=J(-1), no_bl="BL 9001", ref_sifa="12/0003")
    dep_sans_bl = inserer(c, "expe_departs", statut="valide", date_enlevement=J(-1), no_bl="", ref_sifa="12/0004")
    dep_inconnu = inserer(c, "expe_departs", statut="valide", date_enlevement=J(-3), no_bl="9999", ref_sifa="12/0005")
    dep_2036 = inserer(c, "expe_departs", statut="valide", date_enlevement="2036-02-11", no_bl="9001", ref_sifa="12/0006")

    # Produit en stock, livré sur le BL 9002, sans sortie.
    prod = inserer(c, "produits", reference="12/0003", designation="Étiquette test")
    inserer(c, "stock_emplacements", produit_id=prod, emplacement="A111", quantite=50, updated_at=T(-10))
    c.commit()

# ── Miroir RVGI ──────────────────────────────────────────────────────────────
erp = sqlite3.connect(os.environ["ERP_MIRROR_DB"])
erp.executescript("""
    CREATE TABLE liv_entete (numero INTEGER, corbeille INTEGER, amje TEXT, lrs TEXT);
    CREATE TABLE liv_ligne (numero INTEGER, corbeille INTEGER, numcde INTEGER, lignecde INTEGER, qte REAL, amje TEXT);
    CREATE TABLE cde_ligne (numero INTEGER, ligne INTEGER, corbeille INTEGER, code1 TEXT, code2 TEXT);
    CREATE TABLE erp_meta (nom TEXT, lignes INTEGER, colonnes INTEGER, importe_le TEXT, releve_le TEXT);
""")
erp.execute("INSERT INTO liv_entete VALUES (9001, 0, ?, 'Client A')", (T(-1)[:10] + " 09:00",))
erp.execute("INSERT INTO liv_entete VALUES (9002, 0, ?, 'Client B')", (T(-1)[:10] + " 10:00",))
erp.execute("INSERT INTO liv_entete VALUES (9003, 1, ?, 'Corbeille')", (T(-1)[:10] + " 10:00",))
erp.execute("INSERT INTO liv_ligne VALUES (9002, 0, 9930001, 1, 24, ?)", (T(-1)[:10],))
erp.execute("INSERT INTO cde_ligne VALUES (9930001, 1, 0, '12', '0003')")
erp.execute("INSERT INTO erp_meta VALUES ('liv_entete', 3, 4, ?, ?)", (T(0), T(0)))
erp.commit()
erp.close()

# ── 1. Chaque règle trouve son cas ───────────────────────────────────────────
bilan = coherence.tour(get_db)
check("premier passage sans contrôleur en erreur", bilan.get("erreurs"), {})
with get_db() as c:
    ouverts = coherence.lister(c, limite=500)["ecarts"]
par = {}
for e in ouverts:
    par.setdefault(e["regle"], []).append(e)


def trouve(regle, objet):
    return any(e["objet_ref"] == str(objet) for e in par.get(regle, []))


check("en cours sans saisie", trouve("prod.en_cours_sans_saisie", "D-SANS-SAISIE"))
check("fin prévue après la livraison", trouve("prod.retard_prevu", "D-RETARD"))
check("quantité produite loin de l'OF (-30 %)", trouve("prod.quantite_vs_of", "D-QTE"))
q = next(e for e in par["prod.quantite_vs_of"] if e["objet_ref"] == "D-QTE")
check("  … le détail donne les chiffres", "700" in q["detail"] and "1 000" in q["detail"])
check("OF contre fiche", trouve("documents.of_fiche", "D-DOC"))
d = next(e for e in par["documents.of_fiche"] if e["objet_ref"] == "D-DOC")
check("  … nomme les matières, pas des identifiants", "Couché 90 g" in d["detail"] and "Vélin 80 g" in d["detail"])
check("  … la quantité au mille", "Quantité au mille" in d["detail"])
check("  … la fiche de la bonne machine (laize égale, non signalée)", "Laize" in d["detail"], False)
check("OF contre planning (machine et laize)", trouve("documents.of_planning", "D-DOC"))
p_ = next(e for e in par["documents.of_planning"] if e["objet_ref"] == "D-DOC")
check("  … machine et laize citées", "Machine B test" in p_["detail"] and "440" in p_["detail"])
check("BL sans départ", trouve("flux.bl_sans_depart", 9002))
check("BL porté par un départ : pas d'écart", trouve("flux.bl_sans_depart", 9001), False)
check("BL à la corbeille ignoré", trouve("flux.bl_sans_depart", 9003), False)
check("départ validé sans BL", trouve("flux.depart_sans_bl", dep_sans_bl))
check("BL du départ inconnu de RVGI", trouve("flux.bl_inconnu", dep_inconnu))
check("article livré sans sortie de stock", trouve("flux.expedie_sans_sortie", "12/0003"))
check("date d'enlèvement aberrante", trouve("flux.date_enlevement", dep_2036))

# ── 2. Pas de doublon, résolution automatique, règle désactivée ──────────────
nb = len(ouverts)
b2 = coherence.tour(get_db)
check("second passage : aucun nouveau", b2["nouveaux"], 0)
check("second passage : même nombre d'ouverts", b2["ouverts"], nb)
with get_db() as c:
    inserer(c, "production_data", no_dossier="D-SANS-SAISIE", operation_code="01",
            planning_entry_id=pe_sans_saisie, date_operation=T(0), machine="Machine A test")
    inserer(c, "mouvements_stock", produit_id=prod, emplacement="A111", type_mouvement="sortie",
            quantite=24, created_at=T(0))
    c.commit()
b3 = coherence.tour(get_db)
check("saisie ajoutée : écart résolu", b3["resolus"], 2)
with get_db() as c:
    st = c.execute("SELECT statut FROM coherence_ecarts WHERE regle='prod.en_cours_sans_saisie'").fetchone()[0]
    check("  … statut resolu", st, "resolu")
    coherence.enregistrer_reglages(c, {"regles": {"flux.date_enlevement": False}})
coherence.tour(get_db)
with get_db() as c:
    st = c.execute("SELECT statut FROM coherence_ecarts WHERE regle='flux.date_enlevement'").fetchone()[0]
    check("règle désactivée : ses écarts sortent de la file", st, "resolu")
    try:
        coherence.enregistrer_reglages(c, {"seuils": {"tolerance_quantite_pct": -5}})
        check("seuil négatif refusé", "accepté", "refusé")
    except ValueError:
        check("seuil négatif refusé", True)

# ── 3. Écart expliqué ────────────────────────────────────────────────────────
with get_db() as c:
    avant, _ = coherence.compter_ouverts(c)
    eid = c.execute("SELECT id FROM coherence_ecarts WHERE regle='prod.retard_prevu'").fetchone()[0]
    coherence.expliquer(c, eid, "Livraison décalée avec le client.", "Test")
    apres, _ = coherence.compter_ouverts(c)
    check("expliqué : la pastille baisse d'un", avant - apres, 1)
coherence.tour(get_db)
with get_db() as c:
    st = c.execute("SELECT statut FROM coherence_ecarts WHERE id=?", (eid,)).fetchone()[0]
    check("expliqué : reste expliqué au passage suivant", st, "explique")

# ── 4. L'agent ───────────────────────────────────────────────────────────────
from app.services import mcp_metier, agent_actions as aa  # noqa: E402
lu = mcp_metier.ecarts("flux")
check("mysifa_ecarts : ne rend que la famille demandée", {e["famille"] for e in lu["ecarts"]}, {"flux"})
sup = {"id": 0, "email": "t@local", "role": "superadmin", "nom": "T"}
p = aa.preparer(sup, "coherence_expliquer", {"ecart_id": eid, "explication": "Décalage client."})
check("action expliquer : chemin", p["chemin"], f"/api/settings/coherence/{eid}/expliquer")
try:
    aa.preparer({"id": 0, "role": "expedition"}, "coherence_expliquer", {"ecart_id": eid, "explication": "x"})
    check("action expliquer refusée à l'expédition", "accepté", "refusé")
except aa.ActionInvalide:
    check("action expliquer refusée à l'expédition", True)
try:
    aa.preparer(sup, "coherence_expliquer", {"ecart_id": 999999, "explication": "x"})
    check("action expliquer : écart inexistant refusé", "accepté", "refusé")
except aa.ActionInvalide:
    check("action expliquer : écart inexistant refusé", True)

# ── 5. API Paramètres ────────────────────────────────────────────────────────
from fastapi.testclient import TestClient  # noqa: E402
import main  # noqa: E402
from app.services.auth_service import create_session  # noqa: E402

with get_db() as c:
    uid_dir = inserer(c, "users", email="dir@local", nom="Direction Test", password_hash="x",
                      role="direction", actif=1, created_at=T(0))
    uid_exp = inserer(c, "users", email="exp@local", nom="Expé Test", password_hash="x",
                      role="expedition", actif=1, created_at=T(0))
    c.commit()
cl = TestClient(main.app)
cl.cookies.set("sifa_token", create_session(uid_dir))
r = cl.get("/api/settings/coherence?statut=tous")
check("API : liste", r.status_code, 200)
check("API : compte par famille", isinstance(r.json().get("ouverts_par_famille"), dict))
check("API : réglages", cl.get("/api/settings/coherence/reglages").status_code, 200)
check("API : relancer", cl.post("/api/settings/coherence/relancer").status_code, 200)
check("API : explication vide refusée",
      cl.post(f"/api/settings/coherence/{eid}/expliquer", json={"explication": " "}).status_code, 400)
cl2 = TestClient(main.app)
cl2.cookies.set("sifa_token", create_session(uid_exp))
check("API : refusée à l'expédition", cl2.get("/api/settings/coherence").status_code, 403)

print()
if ECHECS:
    print(f"{len(ECHECS)} échec(s)")
    sys.exit(1)
print("Tout est vert.")

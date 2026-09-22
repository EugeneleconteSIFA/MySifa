"""
Déstockage à la clôture, et fermeture des mouvements MP à la main.

Ce que ce test protège, dans l'ordre où ça casse :

1. **La clôture déstocke, mais jamais rétroactivement.** Sans date de mise en
   service, `destocker_a_la_cloture` ne fait rien ; avant cette date non plus.
   C'est la même précaution que le balayage : 232 dossiers portaient déjà un
   marquage « déstocké » sans qu'aucun mouvement n'ait été écrit, et les
   rejouer réécrirait un historique que plus personne ne peut vérifier.
2. **Un dossier déjà sorti du stock n'est pas resorti.** La double sortie est
   silencieuse et ne se voit qu'à l'inventaire suivant.
3. **Le mouvement porte le nom de l'automatisme.** L'opérateur qui tape le
   code 89 n'a rien décidé ; lire son nom dans « déstocké par » enverrait la
   collègue lui demander des comptes sur une sortie qu'il n'a pas faite.
4. **Entrée et sortie MP à la main sont fermées** à tout le monde sauf
   superadmin, direction et administration technique — pendant que
   l'ajustement et l'inventaire, eux, restent ouverts. Fermer la correction
   en même temps que la saisie rendrait tout écart d'automatisme définitif.
5. **La consommation d'atelier reste ouverte.** La sortie d'une tête
   d'impression au repiquage est une consommation constatée au poste, pas un
   mouvement décidé : elle se reconnaît sur des attributs du référentiel.
6. **Les deux clôtures appellent le déstockage sans jamais faire échouer la
   saisie** — code 89 dans MyProd, clôture forcée depuis le planning.

Le code testé est extrait des routers par découpage de source : les modules
entiers tireraient fastapi et toute la base pour quelques fonctions pures.
"""
import re
import sqlite3
import sys
import unicodedata
from datetime import datetime, timedelta

sys.path.insert(0, ".")

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


def vrai(libelle, condition, detail=""):
    global ko
    if not condition:
        ko += 1
    print(f"  {'OK ' if condition else 'KO '} {libelle}")
    if not condition and detail:
        print(f"       {detail}")


# ── Extraction : le garde-fou des mouvements MP ───────────────────────
src_stock = open("app/routers/stock.py", encoding="utf-8").read()
bloc_roles = src_stock[src_stock.index("_STOCK_MP_MOUVEMENT_ROLES = "):
                       src_stock.index("_STOCK_VALORISATION_USD_ROLES = ")]
bloc_conso = src_stock[src_stock.index("def _mp_est_consommable_atelier("):
                       src_stock.index("_MP_TYPES_MVT = ")]
ns = {"unicodedata": unicodedata}
exec(compile(bloc_roles + "\n" + bloc_conso, "stock_bloc", "exec"), ns)
ROLES_MVT = ns["_STOCK_MP_MOUVEMENT_ROLES"]
est_consommable = ns["_mp_est_consommable_atelier"]

# ── Extraction : le déstockage à la clôture ───────────────────────────
src_bm = open("app/routers/besoins_matieres.py", encoding="utf-8").read()
bloc_cfg = src_bm[src_bm.index("CLE_DESTOCKAGE_DEPUIS = "):
                  src_bm.index("def _motif_reserve(")]
bloc_clot = src_bm[src_bm.index("def destocker_a_la_cloture("):
                   src_bm.index('@router.post("/api/stock/destockage/{planning_id}/auto")')]
appels = []


def _destockage_auto_un(conn, pe_id, user):          # doublure
    appels.append((pe_id, dict(user or {})))
    return {"planning_id": pe_id, "etat": "done", "mouvements": 3}


ns2 = {"sqlite3": sqlite3, "datetime": datetime,
       "_destockage_auto_un": _destockage_auto_un}
exec(compile(bloc_cfg + "\n" + bloc_clot, "besoins_bloc", "exec"), ns2)
destocker_a_la_cloture = ns2["destocker_a_la_cloture"]

AUJOURDHUI = datetime.now().strftime("%Y-%m-%d")
DEMAIN = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


def base(depuis, etat="todo"):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE stock_config (cle TEXT PRIMARY KEY, valeur TEXT)")
    conn.execute("CREATE TABLE planning_entries (id INTEGER PRIMARY KEY, destockage TEXT)")
    if depuis is not None:
        conn.execute("INSERT INTO stock_config VALUES ('destockage_auto_depuis', ?)", (depuis,))
    conn.execute("INSERT INTO planning_entries VALUES (7, ?)", (etat,))
    return conn


print("\n1. La clôture ne déstocke pas rétroactivement")
appels.clear()
check("automatisme jamais mis en service : ne fait rien",
      destocker_a_la_cloture(base(None), 7, {"id": 4}), None)
check("clé présente mais vide : ne fait rien",
      destocker_a_la_cloture(base(""), 7, {"id": 4}), None)
check("mise en service dans le futur : ne fait rien",
      destocker_a_la_cloture(base(DEMAIN), 7, {"id": 4}), None)
check("aucun appel au déstockage", appels, [])

print("\n2. Un dossier déjà sorti du stock n'est pas resorti")
appels.clear()
for etat in ("done", "reserve"):
    check(f"dossier « {etat} » laissé tranquille",
          destocker_a_la_cloture(base(AUJOURDHUI, etat), 7, {"id": 4}), None)
check("dossier inconnu ignoré",
      destocker_a_la_cloture(base(AUJOURDHUI), 99, {"id": 4}), None)
check("aucun appel au déstockage", appels, [])

print("\n3. Le mouvement porte le nom de l'automatisme")
appels.clear()
res = destocker_a_la_cloture(base(AUJOURDHUI), 7, {"id": 4, "nom": "Kevin",
                                                   "email": "kevin@sifa.pro"})
check("le dossier est déstocké", (res or {}).get("etat"), "done")
check("un seul appel", len(appels), 1)
if appels:
    pe_id, user = appels[0]
    check("sur le bon dossier", pe_id, 7)
    check("nom affiché = l'automatisme", user.get("nom"), "Déstockage automatique")
    check("identifiant de l'opérateur conservé", user.get("id"), 4)
    vrai("le nom de l'opérateur ne fuit pas", "Kevin" not in str(user),
         f"user transmis : {user!r}")
appels.clear()
check("sans utilisateur, ça passe quand même",
      (destocker_a_la_cloture(base(AUJOURDHUI), 7) or {}).get("etat"), "done")

print("\n4. Entrée et sortie MP à la main : fermées, correction ouverte")
check("rôles autorisés", sorted(ROLES_MVT),
      ["administration_technique", "direction", "superadmin"])
for role in ("administration", "administration_ventes", "fabrication",
             "logistique", "expedition", "comptabilite", "commercial"):
    vrai(f"« {role} » ne peut plus saisir d'entrée ni de sortie",
         role not in ROLES_MVT)
garde = re.search(r'if type_mvt in \("entree", "sortie"\) and not '
                  r'_mp_est_consommable_atelier\(mp\):\s*\n\s*if user\.get\("role"\) '
                  r"not in _STOCK_MP_MOUVEMENT_ROLES:\s*\n\s*raise HTTPException\(\s*\n\s*403,",
                  src_stock)
vrai("le garde-fou est bien posé dans /api/stock/matieres/mouvement", garde is not None)
vrai("il ne porte que sur entree et sortie",
     "ajustement" not in (garde.group(0) if garde else "ajustement"))
inv = src_stock[src_stock.index('@router.post("/api/stock/matieres/{matiere_id}/inventaire")'):]
inv = inv[:inv.index("\n@router.")]
vrai("l'inventaire reste ouvert (require_stock_write)",
     "require_stock_write(request)" in inv and "_STOCK_MP_MOUVEMENT_ROLES" not in inv)
vrai("la réception magasin reste ouverte (require_stock)",
     "_STOCK_MP_MOUVEMENT_ROLES" not in src_stock[
         src_stock.index('@router.post("/api/stock/receptions")'):
         src_stock.index('@router.patch("/api/stock/receptions/{reception_id}")')])

print("\n5. La consommation d'atelier reste ouverte")
check("tête d'impression du repiquage",
      est_consommable({"categorie": "autre", "sous_section": "Têtes d'impression"}), True)
check("accents et casse indifférents",
      est_consommable({"categorie": "AUTRE", "sous_section": "TETE IMPRESSION"}), True)
check("print head",
      est_consommable({"categorie": "autre", "sous_section": "print head"}), True)
check("autre chose en catégorie « autre » : non",
      est_consommable({"categorie": "autre", "sous_section": "Colle"}), False)
check("sous-section vide : non",
      est_consommable({"categorie": "autre", "sous_section": None}), False)
check("une bobine n'est jamais un consommable d'atelier",
      est_consommable({"categorie": "frontal", "sous_section": "tete"}), False)
check("colonne absente : non",
      est_consommable({"categorie": "autre"}), False)
_c = sqlite3.connect(":memory:")
_c.row_factory = sqlite3.Row
check("fonctionne sur une ligne sqlite3.Row",
      est_consommable(_c.execute(
          "SELECT 'autre' AS categorie, 'Têtes impression' AS sous_section").fetchone()),
      True)
check("ligne sqlite3.Row sans la colonne : refusée sans casser",
      est_consommable(_c.execute("SELECT 'autre' AS categorie").fetchone()), False)

print("\n6. Les deux clôtures appellent le déstockage sans risquer la saisie")
for fichier, motif in (("app/routers/fabrication.py", "code 89"),
                       ("app/routers/planning.py", "clôture forcée")):
    src = open(fichier, encoding="utf-8").read()
    i = src.find("destocker_a_la_cloture(")
    vrai(f"{motif} : le déstockage est appelé", i > 0)
    if i > 0:
        autour = src[max(0, i - 900):i + 900]
        vrai(f"{motif} : appel protégé par un try/except", "try:" in autour
             and "except Exception" in autour, autour[-500:])
        vrai(f"{motif} : la transaction est commitée", "conn.commit()" in autour)

print("\n%s" % ("Tout est vert." if not ko else f"{ko} contrôle(s) en échec."))
sys.exit(1 if ko else 0)

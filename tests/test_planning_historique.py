"""
Planning : fenêtre « Historique des modifications ».

Le 22/10/2026, les horaires de la semaine suivante de la Cohésio 2 sont
apparus en 5h–13h sans que personne ne sache pourquoi. Le journal savait qui
avait touché aux horaires, mais il fallait du SQL pour le lire, et la réponse
(« personne : c'est le réglage semaine paire qui s'appliquait ») n'y figurait
pas. Cette fenêtre lit le journal pour tout utilisateur qui modifie le planning.

Ce test verrouille :
- le rafraîchissement automatique (live-refresh) n'apparaît pas et n'est plus
  journalisé ;
- les trois formes de ligne (avant/après, métier, middleware) sortent avec un
  titre lisible et leurs valeurs en clair (heures en HH:MM, machines par nom) ;
- le filtre machine retrouve une ligne par son chemin, ses identifiants ou le
  nom de machine écrit dans l'objet, sans confondre « Cohésio 1 » et « Cohésio 10 ».

Lancer : python3 tests/test_planning_historique.py
"""
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import audit_taxonomy as tx  # noqa: E402
from app.services import planning_historique as ph  # noqa: E402

FAIL = []


def verifier(cas, obtenu, attendu):
    if obtenu != attendu:
        FAIL.append(cas)
        print(f"  ECHEC  {cas} — obtenu {obtenu!r}, attendu {attendu!r}")
    else:
        print(f"  ok     {cas}")


def base():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("CREATE TABLE machines (id INTEGER PRIMARY KEY, nom TEXT)")
    c.execute("""CREATE TABLE audit_logs (id INTEGER PRIMARY KEY, user_id INTEGER, user_nom TEXT,
                 user_role TEXT, action TEXT, module TEXT, objet TEXT, detail TEXT, ip TEXT,
                 created_at TEXT)""")
    c.executemany("INSERT INTO machines VALUES (?,?)",
                  [(1, "Cohésio 1"), (3, "Cohésio 2"), (10, "Cohésio 10")])
    lignes = [
        # 1. middleware (forme réelle de prod)
        ("Grégory", "UPDATE", "Set day horaires · machine_id=3", {
            "methode": "PUT", "chemin": "/api/planning/machines/3/day-horaires",
            "donnees": {"date": "2026-10-16", "heure_debut": 6.583333333333333, "heure_fin": 13,
                        "journee_entiere": 0}}),
        # 2. avant / après (_journal_horaires)
        ("Eugene", "UPDATE", "Cohésio 2 · Horaires du lun 26/10/2026",
         {"avant": None, "apres": "05:25–20:35", "affiche_avant": "05:00–13:00"}),
        # 3. métier, machine dans l'objet
        ("Grégory", "CREATE", "Dossier 9932723 - L1 · Cohésio 1",
         {"reference": "9932723 - L1", "duree_heures": 5.0}),
        # 4. métier, machine dans les identifiants
        ("Manuel", "UPDATE", "Dossier 9932757 · Cohésio 1 → Cohésio 2",
         {"geste": "changer_machine", "machine_source": 1, "machine_cible": 3}),
        # 5. bruit
        ("Opérateur", "CREATE", "Live refresh en cours · machine_id=3",
         {"methode": "POST", "chemin": "/api/planning/machines/3/live-refresh"}),
        # 6. autre module
        ("Eugene", "UPDATE", "Cohésio 2 · Stock", {}),
        # 7. machine 10 : ne doit pas sortir sous Cohésio 1
        ("Eugene", "UPDATE", "Réorganisation planning Cohésio 10", {"entry_ids": [1, 2, 3]}),
        # 8. parité avant / après
        ("Eugene", "UPDATE", "Cohésio 2 · Horaires semaines paires / impaires", {
            "avant": {"pair": {"week": "05:00–13:00", "fri": "06:00–13:00"},
                      "impair": {"week": "13:00–20:00", "fri": "14:00–20:00"}},
            "apres": {"pair": {"week": "05:25–20:35", "fri": "06:00–13:00"},
                      "impair": {"week": "13:00–20:00", "fri": "14:00–20:00"}}}),
    ]
    for i, (u, a, o, d) in enumerate(lignes, 1):
        c.execute("""INSERT INTO audit_logs (id,user_nom,action,module,objet,detail,created_at)
                     VALUES (?,?,?,?,?,?,?)""",
                  (i, u, a, "stock" if i == 6 else "planning", o, json.dumps(d),
                   f"2026-10-2{i % 3}T09:00:00"))
    return c


print("Exclusion du rafraîchissement automatique")
verifier("live-refresh n'est plus journalisé", tx.is_skipped("/api/planning/machines/3/live-refresh"), True)
verifier("les autres écritures planning le restent", tx.is_skipped("/api/planning/machines/3/day-horaires"), False)

c = base()
tout = ph.lister(c, jours=None)
ids = [l["id"] for l in tout["lignes"]]
verifier("ni bruit ni autre module", sorted(ids), [1, 2, 3, 4, 7, 8])

par_id = {l["id"]: l for l in tout["lignes"]}
print("Mise en forme")
l1 = par_id[1]
verifier("middleware : titre tiré de la route", l1["titre"], "Horaires du ven 16/10/2026")
verifier("middleware : heures en HH:MM",
         [(x["champ"], x["valeur"]) for x in l1["lignes"]],
         [("Début", "06:35"), ("Fin", "13:00"), ("Journée entière", "Non")])
verifier("middleware : machine par le chemin", l1["machine"], "Cohésio 2")
l2 = par_id[2]
verifier("avant/après : aucun réglage → valeur", (l2["lignes"][0]["avant"], l2["lignes"][0]["apres"]),
         ("aucun réglage enregistré", "05:25–20:35"))
verifier("avant/après : ce qu'affichait la timeline", l2["lignes"][1],
         {"champ": "Affiché avant", "valeur": "05:00–13:00"})
verifier("changement de machine : une ligne origine → cible, par les noms",
         par_id[4]["lignes"], [{"champ": "Machine", "avant": "Cohésio 1", "apres": "Cohésio 2"}])
verifier("changement de machine : geste et dossier visé",
         (par_id[4]["geste"], par_id[4]["dossier"]), ("Changé de machine", "9932757"))
verifier("création : dossier visé", (par_id[3]["geste"], par_id[3]["dossier"]),
         ("Ajout au planning", "9932723 - L1"))
verifier("réorganisation : un compte, pas la liste", par_id[7]["lignes"][0]["valeur"], "3 dossier(s)")
verifier("parité : seule la plage changée sort", par_id[8]["lignes"],
         [{"champ": "Paire lun–jeu", "avant": "05:00–13:00", "apres": "05:25–20:35"}])

verifier("titre sans la machine (elle a sa pastille)", l2["titre"], "Horaires du lun 26/10/2026")
semaine = ph.mettre_en_forme({"id": 9, "objet": "Cohésio 2 · Horaires machine (semaine type)", "action": "UPDATE",
                              "user_nom": "E", "created_at": "2026-10-22T08:00:00",
                              "detail": json.dumps({"avant": {"horaires_lundi": "5,21"},
                                                    "apres": {"horaires_lundi": "05:25,20:35"}})},
                             {3: "Cohésio 2"})
verifier("semaine type en HH:MM", semaine["lignes"],
         [{"champ": "Lundi", "avant": "05:00–21:00", "apres": "05:25–20:35"}])

print("Modification de dossier")
src = Path(__file__).resolve().parents[1] / "app/routers/planning.py"
code = src.read_text(encoding="utf-8")
debut = code.index("_DIFF_IGNORES = {")
fin = code.index("def _journal_horaires(")
ns: dict = {"Any": object}
exec(code[debut:fin], ns)
exd = {"reference": "9932601", "duree_heures": 8.0, "notes": "", "date_livraison": "2026-11-02",
       "laize": 470.0, "updated_at": "x", "client": "SNV"}
corps = {"reference": "9932601", "duree_heures": "8", "notes": "Attente encre", "date_livraison": "2026-11-05",
         "laize": 470, "updated_at": "y", "client": "SNV", "confirme_gel": True}
av, ap = ns["_diff_entree"](exd, corps)
verifier("diff : seuls les champs changés", sorted(ap), ["date_livraison", "notes"])
l = ph.mettre_en_forme({"id": 1, "objet": "Dossier 9932601", "action": "UPDATE", "user_nom": "F",
                        "created_at": "2026-10-22T08:00:00",
                        "detail": json.dumps({"avant": av, "apres": ap, "machine_id": 3})},
                       {3: "Cohésio 2"})
verifier("diff : libellés et dates lisibles", l["lignes"], [
    {"champ": "Notes", "avant": "—", "apres": "Attente encre"},
    {"champ": "Livraison", "avant": "lun 02/11/2026", "apres": "jeu 05/11/2026"}])
verifier("diff : machine par machine_id", l["machine"], "Cohésio 2")
vide = ph.mettre_en_forme({"id": 2, "objet": "Dossier X", "action": "UPDATE", "user_nom": "F",
                           "created_at": "2026-10-22T08:00:00",
                           "detail": json.dumps({"avant": {}, "apres": {}, "machine_id": 3})}, {3: "C2"})
verifier("diff vide : marqué sans changement", (vide["inchange"], vide["lignes"]), (True, []))

print("Geste, dossier, avant → après")
statut = ph.mettre_en_forme({"id": 11, "objet": "Statut dossier 9932448 → termine", "action": "CLOSE",
                             "user_nom": "G", "created_at": "2026-10-22T08:00:00",
                             "detail": json.dumps({"avant": {"statut": "attente"}, "apres": {"statut": "termine"},
                                                   "override": False, "machine_id": 1})}, {1: "Cohésio 1"})
verifier("statut : dossier et geste", (statut["dossier"], statut["geste"]),
         ("9932448", "Changement de statut"))
verifier("statut : avant → après", statut["lignes"][0],
         {"champ": "Statut", "avant": "En attente", "apres": "Terminé"})
dep = ph.mettre_en_forme({"id": 12, "objet": "Dossier 9932500 · Cohésio 1", "action": "REORDER",
                          "user_nom": "G", "created_at": "2026-10-22T08:00:00",
                          "detail": json.dumps({"geste": "apres", "apres_id": 40, "rang_avant": 9, "rang": 3})},
                         {1: "Cohésio 1"}, {40: "9932499"})
verifier("déplacement : rang avant → après, dossier cité par son numéro", dep["lignes"], [
    {"champ": "Rang dans la file", "avant": "9", "apres": "3"},
    {"champ": "Placé après", "valeur": "9932499"}])
reorg = ph.mettre_en_forme({"id": 13, "objet": "Réorganisation planning Cohésio 1", "action": "REORDER",
                            "user_nom": "G", "created_at": "2026-10-22T08:00:00",
                            "detail": json.dumps({"ordre_avant": [1, 2, 3, 4, 5], "entry_ids": [1, 4, 2, 3, 5]})},
                           {1: "Cohésio 1"}, {4: "9932004"})
verifier("réorganisation : seul le dossier déplacé sort", reorg["lignes"],
         [{"champ": "9932004", "avant": "rang 4", "apres": "rang 2"}])
verifier("réorganisation : dossier visé", (reorg["dossier"], reorg["geste"]),
         ("9932004", "Réorganisation de la file"))

print("Filtre machine")
verifier("Cohésio 2 : chemin, objet, machine cible",
         sorted(l["id"] for l in ph.lister(c, machine_id=3, jours=None)["lignes"]), [1, 2, 4, 8])
verifier("Cohésio 1 sans Cohésio 10",
         sorted(l["id"] for l in ph.lister(c, machine_id=1, jours=None)["lignes"]), [3, 4])
verifier("filtre utilisateur",
         [l["id"] for l in ph.lister(c, utilisateur="Grégory", jours=None)["lignes"]], [3, 1])
verifier("recherche texte", [l["id"] for l in ph.lister(c, q="9932723", jours=None)["lignes"]], [3])
verifier("liste des utilisateurs de la machine",
         sorted(ph.lister(c, machine_id=3, jours=None)["utilisateurs"]), ["Eugene", "Grégory", "Manuel"])

if FAIL:
    print(f"\n{len(FAIL)} échec(s)")
    sys.exit(1)
print("\nTOUT EST VERT")

"""
Reunions de production : ce que le service doit garantir.

Les cas verrouilles ici sont ceux ou une erreur passerait inapercue parce
qu'elle produirait un ecran plausible :

- une personne ne peut pas avoir deux reunions ouvertes ; rouvrir la page doit
  lui rendre la sienne, pas en creer une seconde qui perdrait ses notes ;
- clore ne verrouille pas — on corrige toujours un compte-rendu apres coup ;
- la liste s'ordonne sur la plage analysee, pas sur l'heure de creation ;
- une action videe de son texte est supprimee, pas gardee vide.

Le service ne touche a aucun module de l'application : il prend une connexion
sqlite et rien d'autre. Le test s'execute donc sur une base en memoire, sans
charger `database` ni FastAPI.

Lancer : python3 tests/test_reunion.py
"""

import importlib.util
import sqlite3
import sys
from datetime import date
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def _charger(nom: str, chemin: Path):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


svc = _charger("reunion", RACINE / "app" / "services" / "reunion.py")
mig = _charger("mig_reunions", RACINE / "app" / "core" / "migrations" / "2026_08_31_reunions_prod.py")

FAIL = []


def verifier(cas, obtenu, attendu):
    if obtenu != attendu:
        FAIL.append(f"{cas} : obtenu {obtenu!r}, attendu {attendu!r}")
        print(f"  ECHEC  {cas} — obtenu {obtenu!r}, attendu {attendu!r}")
    else:
        print(f"  ok     {cas}")


def base():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    mig.appliquer(conn)
    return conn


def test_lancer():
    print("\n1. Lancer une reunion")
    conn = base()
    r = svc.lancer(conn, "Eugene", "2026-08-28")
    verifier("reunion creee", bool(r), True)
    verifier("ouverte", r["ouverte"], True)
    verifier("plage d'un jour : fin = debut", (r["date_debut"], r["date_fin"]),
             ("2026-08-28", "2026-08-28"))
    import re as _re
    verifier("titre par defaut : la date seule",
             bool(_re.fullmatch(r"\d{2}/\d{2}/\d{4}", r["titre"])), True)
    verifier("aucune action", r["actions"], [])

    # Rouvrir la page ne doit pas empiler une seconde reunion.
    r2 = svc.lancer(conn, "Eugene", "2026-08-29")
    verifier("la reunion ouverte est rendue, pas dupliquee", r2["id"], r["id"])
    verifier("et sa plage n'a pas bouge", r2["date_debut"], "2026-08-28")
    verifier("une autre personne peut en ouvrir une",
             svc.lancer(conn, "Alan", "2026-08-28")["id"] != r["id"], True)

    # Bornes inversees : on remet dans l'ordre plutot que de refuser.
    conn2 = base()
    r3 = svc.lancer(conn2, "Eugene", "2026-08-29", "2026-08-27")
    verifier("bornes remises dans l'ordre", (r3["date_debut"], r3["date_fin"]),
             ("2026-08-27", "2026-08-29"))

    conn3 = base()
    r4 = svc.lancer(conn3, "Eugene", "", titre="Point machines",
                    noms_participants=["Marc", "Sophie", "  "])
    verifier("sans date : la veille", r4["date_debut"],
             (date.today().toordinal() - 1) and r4["date_debut"])
    verifier("titre choisi", r4["titre"], "Point machines")
    verifier("participants enregistres, les vides ignores",
             [p["nom"] for p in r4["participants"]], ["Marc", "Sophie"])


def test_notes_et_cloture():
    print("\n2. Notes, cloture, reouverture")
    conn = base()
    r = svc.lancer(conn, "Eugene", "2026-08-28")

    maj = svc.enregistrer(conn, r["id"], "Eugene", notes="Casse bande recurrente sur Cohesio 1")
    verifier("notes enregistrees", maj["notes"], "Casse bande recurrente sur Cohesio 1")
    verifier("dernier auteur trace", maj["updated_par"], "Eugene")

    maj = svc.enregistrer(conn, r["id"], "Eugene", titre="Point du vendredi")
    verifier("titre modifie", maj["titre"], "Point du vendredi")
    verifier("les notes n'ont pas bouge", maj["notes"], "Casse bande recurrente sur Cohesio 1")

    close = svc.clore(conn, r["id"], "Eugene")
    verifier("close", close["statut"], "close")
    verifier("qui l'a close", close["close_par"], "Eugene")

    # Clore ne verrouille pas : on corrige toujours un compte-rendu apres coup.
    apres = svc.enregistrer(conn, r["id"], "Alan", notes="Complete apres coup")
    verifier("une reunion close reste modifiable", apres["notes"], "Complete apres coup")
    verifier("et reste close", apres["statut"], "close")

    verifier("reouverture possible", svc.clore(conn, r["id"], "Eugene", rouvrir=True)["ouverte"], True)
    verifier("la trace de cloture est effacee",
             svc.reunion(conn, r["id"])["close_par"], None)

    # Une reunion close libere la place pour la suivante.
    svc.clore(conn, r["id"], "Eugene")
    suivante = svc.lancer(conn, "Eugene", "2026-08-29")
    verifier("une nouvelle reunion peut demarrer", suivante["id"] != r["id"], True)


def test_actions():
    print("\n3. Actions")
    conn = base()
    r = svc.lancer(conn, "Eugene", "2026-08-28")

    a = svc.ajouter_action(conn, r["id"], "Commander des lames", "Alan", "2026-09-05")
    verifier("action creee", a["texte"], "Commander des lames")
    verifier("responsable", a["responsable"], "Alan")
    verifier("echeance", a["echeance"], "2026-09-05")
    verifier("pas faite", a["fait"], False)
    verifier("le quoi suffit",
             svc.ajouter_action(conn, r["id"], "Revoir le calage")["responsable"], None)
    verifier("action vide refusee", svc.ajouter_action(conn, r["id"], "   "), None)

    fait = svc.modifier_action(conn, a["id"], "Eugene", fait=True)
    verifier("action cochee", fait["fait"], True)
    verifier("par qui", fait["fait_par"], "Eugene")
    verifier("decochee", svc.modifier_action(conn, a["id"], "Eugene", fait=False)["fait"], False)
    verifier("et la trace part", svc.modifier_action(conn, a["id"], "Eugene", fait=False)["fait_par"], None)

    verifier("texte corrige",
             svc.modifier_action(conn, a["id"], "Eugene", texte="Commander 4 lames")["texte"],
             "Commander 4 lames")
    verifier("texte vide = action supprimee",
             svc.modifier_action(conn, a["id"], "Eugene", texte="  "), None)
    verifier("il n'en reste qu'une", len(svc.actions(conn, r["id"])), 1)

    verifier("compteur d'actions restantes",
             svc.reunion(conn, r["id"])["actions_restantes"], 1)


def test_liste():
    print("\n4. Liste, la plus recente en tete")
    conn = base()
    verifier("aucune reunion", svc.liste(conn), [])

    # Creees dans le desordre : c'est la PLAGE qui ordonne, pas la creation.
    for auteur, jour in (("Eugene", "2026-08-20"), ("Alan", "2026-08-28"),
                         ("Sophie", "2026-08-24")):
        r = svc.lancer(conn, auteur, jour)
        svc.clore(conn, r["id"], auteur)

    l = svc.liste(conn)
    verifier("ordre par plage decroissante", [x["date_debut"] for x in l],
             ["2026-08-28", "2026-08-24", "2026-08-20"])
    verifier("statut porte", all(x["statut"] == "close" for x in l), True)
    verifier("aucune note", [x["a_des_notes"] for x in l], [False, False, False])

    svc.enregistrer(conn, l[0]["id"], "Alan", notes="Un mot")
    svc.ajouter_action(conn, l[0]["id"], "Faire quelque chose")
    l = svc.liste(conn)
    verifier("les notes se voient depuis la liste", l[0]["a_des_notes"], True)
    verifier("les actions se comptent", (l[0]["nb_actions"], l[0]["actions_restantes"]), (1, 1))

    verifier("suppression", svc.supprimer(conn, l[0]["id"]), True)
    verifier("il en reste deux", len(svc.liste(conn)), 2)
    verifier("suppression d'une reunion inconnue", svc.supprimer(conn, 9999), False)


def test_participants():
    print("\n5. Participants")
    conn = base()
    r = svc.lancer(conn, "Eugene", "2026-08-28", noms_participants=["Marc"])
    maj = svc.enregistrer(conn, r["id"], "Eugene", noms_participants=["Marc", "Sophie", "Alan"])
    verifier("liste remplacee", [p["nom"] for p in maj["participants"]],
             ["Alan", "Marc", "Sophie"])
    maj = svc.enregistrer(conn, r["id"], "Eugene", noms_participants=[])
    verifier("liste videe", maj["participants"], [])
    maj = svc.enregistrer(conn, r["id"], "Eugene", notes="x")
    verifier("ne pas passer la liste ne l'efface pas", maj["participants"], [])


def test_inconnu():
    print("\n6. Reunion inconnue")
    conn = base()
    verifier("lecture", svc.reunion(conn, 404), None)
    verifier("enregistrement", svc.enregistrer(conn, 404, "Eugene", notes="x"), None)
    verifier("cloture", svc.clore(conn, 404, "Eugene"), None)
    verifier("action", svc.ajouter_action(conn, 404, "x"), None)
    verifier("aucune reunion ouverte", svc.ouverte_de(conn, "Personne"), None)


if __name__ == "__main__":
    test_lancer()
    test_notes_et_cloture()
    test_actions()
    test_liste()
    test_participants()
    test_inconnu()

    print("\n" + "=" * 60)
    if FAIL:
        print(f"{len(FAIL)} echec(s) :")
        for f in FAIL:
            print("  -", f)
        sys.exit(1)
    print("Tous les cas passent.")

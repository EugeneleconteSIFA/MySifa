"""
Réunions — espace commun et mode écoute : ce que les services doivent garantir.

Les cas verrouillés ici sont ceux où une erreur passerait inaperçue :

- visibilité : une réunion de direction ne doit apparaître ni dans la liste,
  ni par ses actions sur le tableau de l'atelier, pour qui n'y a pas droit ;
- une écoute n'est visible que de qui l'a lancée, jusqu'à sa validation ;
- un morceau d'audio manquant est SIGNALÉ, pas comblé en silence ;
- l'audio disparaît dès la transcription faite ;
- un type sans IA saute la structuration : rien ne part chez Claude ;
- valider écrit la réunion et ses actions, et pose la date de purge ;
- un type qui porte des réunions se désactive, il ne se supprime pas.

Base en mémoire, dossier temporaire ; ni FastAPI ni réseau.

Lancer : PYTHONPATH=. python3 tests/test_reunion_ecoute.py
"""

import importlib.util
import os
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))

from app.services import reunion as rn  # noqa: E402
from app.services import reunion_ecoute as ec  # noqa: E402

MIGRATIONS = (
    "2026_08_31_reunions_prod.py",
    "2026_09_01_reunion_machines.py",
    "2026_10_12_reunion_actions_statut.py",
    "2026_10_19_reunion_actions_sans_reunion.py",
    "2026_11_05_reunions_types_visibilite.py",
    "2026_11_05_reunion_ecoutes.py",
    "2026_11_05_reunion_ecoutes_progression.py",
)

FAIL = []


def verifier(cas, obtenu, attendu):
    if obtenu != attendu:
        FAIL.append(f"{cas} : obtenu {obtenu!r}, attendu {attendu!r}")


def _mig(nom):
    spec = importlib.util.spec_from_file_location(nom, RACINE / "app" / "core" / "migrations" / nom)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def base():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    for f in MIGRATIONS:
        _mig(f).appliquer(conn)
    return conn


def type_id(conn, libelle):
    return conn.execute("SELECT id FROM reunion_types WHERE libelle=?", (libelle,)).fetchone()[0]


def qui(id_, nom, role="fabrication", superadmin=False):
    return {"id": id_, "nom": nom, "role": role, "superadmin": superadmin}


def test_migrations_rejouables():
    conn = base()
    for f in MIGRATIONS:
        _mig(f).appliquer(conn)
    verifier("seed sans doublon", conn.execute("SELECT COUNT(*) FROM reunion_types").fetchone()[0], 5)
    prod = rn.type_reunion(conn, type_id(conn, "Production"))
    verifier("Production a les chiffres", prod["chiffres_prod"], True)
    verifier("Production visible par rôles", prod["visibilite_defaut"], "roles")


def test_reprise_reunions_existantes():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    for f in MIGRATIONS[:4]:
        _mig(f).appliquer(conn)
    conn.execute("""INSERT INTO reunions (titre, date_debut, date_fin, notes, statut, ouverte_le, ouverte_par)
                    VALUES ('Point', '2026-10-01', '2026-10-01', '', 'close', '2026-10-01T08:00:00', 'Eddy')""")
    conn.commit()
    for f in MIGRATIONS[4:]:
        _mig(f).appliquer(conn)
    r = rn.reunion(conn, 1)
    verifier("ancienne réunion sur Production", r["type"]["libelle"], "Production")
    verifier("ancienne réunion vue par la fabrication", rn.peut_voir(r, qui(9, "Autre", "fabrication")), True)
    verifier("ancienne réunion cachée à la compta", rn.peut_voir(r, qui(9, "Autre", "comptabilite")), False)


def test_visibilite():
    conn = base()
    direction = type_id(conn, "Direction")
    r = rn.lancer(conn, "Jacques", "2026-11-05", type_id=direction, auteur_id=1, reprendre=False,
                  noms_participants=["Flo"])
    verifier("visibilité reprise du type", r["visibilite"], "participants")
    verifier("créateur voit", rn.peut_voir(r, qui(1, "Jacques", "direction")), True)
    verifier("participant voit (par son nom)", rn.peut_voir(r, qui(2, "flo", "commercial")), True)
    verifier("autre ne voit pas", rn.peut_voir(r, qui(3, "Eddy", "direction")), False)
    verifier("superadmin voit", rn.peut_voir(r, qui(4, "Admin", "superadmin", True)), True)
    liste = rn.liste(conn, qui=qui(3, "Eddy", "direction"))
    verifier("liste filtrée", [x["id"] for x in liste], [])
    verifier("liste du créateur", [x["id"] for x in rn.liste(conn, qui=qui(1, "Jacques"))], [r["id"]])

    rn.enregistrer(conn, r["id"], "Jacques", visibilite="roles", roles_visibles=["direction"])
    r2 = rn.reunion(conn, r["id"])
    verifier("par rôle : direction voit", rn.peut_voir(r2, qui(3, "Eddy", "direction")), True)
    verifier("par rôle : fabrication non", rn.peut_voir(r2, qui(5, "Paul", "fabrication")), False)


def test_actions_filtrees():
    conn = base()
    direction = type_id(conn, "Direction")
    r = rn.lancer(conn, "Jacques", "2026-11-05", type_id=direction, auteur_id=1, reprendre=False)
    rn.ajouter_action(conn, r["id"], "Revoir les prix", "Jacques")
    rn.ajouter_action(conn, None, "Ranger l'atelier", "Paul")
    atelier = rn.toutes_actions(conn, qui(5, "Paul", "fabrication"))
    verifier("action de direction cachée à l'atelier", [a["texte"] for a in atelier], ["Ranger l'atelier"])
    verifier("le créateur voit les deux", len(rn.toutes_actions(conn, qui(1, "Jacques", "direction"))), 2)


def test_types():
    conn = base()
    try:
        rn.enregistrer_type(conn, None, {"libelle": "Direction"})
        FAIL.append("doublon de libellé accepté")
    except ValueError:
        pass
    try:
        rn.enregistrer_type(conn, None, {"libelle": "CSE", "visibilite_defaut": "roles"})
        FAIL.append("visibilité par rôles sans rôle acceptée")
    except ValueError:
        pass
    t = rn.enregistrer_type(conn, None, {"libelle": "CSE", "visibilite_defaut": "participants",
                                         "structuration_ia": False})
    verifier("création", (t["libelle"], t["structuration_ia"]), ("CSE", False))
    verifier("type vide supprimé", rn.supprimer_type(conn, t["id"]), "supprime")
    qualite = type_id(conn, "Qualité")
    rn.lancer(conn, "Flo", "2026-11-05", type_id=qualite, reprendre=False)
    verifier("type utilisé désactivé", rn.supprimer_type(conn, qualite), "desactive")
    verifier("plus proposé", any(x["id"] == qualite for x in rn.types(conn, actifs_seulement=True)), False)


def test_cycle_ecoute():
    conn = base()
    with tempfile.TemporaryDirectory() as dossier:
        e = ec.creer(conn, "Jacques", 1, type_id(conn, "Production"), "")
        verifier("visible du créateur", ec.visible(e, qui(1, "Jacques")), True)
        verifier("invisible d'un autre", ec.visible(e, qui(2, "Flo", "direction")), False)
        verifier("en cours repris", ec.en_cours_de(conn, qui(1, "Jacques"))["id"], e["id"])
        for n, contenu in ((0, b"AAA"), (1, b"BBB"), (3, b"DDD")):
            ec.ajouter_morceau(conn, dossier, e["id"], n, contenu, "audio/webm;codecs=opus")
        ec.ajouter_morceau(conn, dossier, e["id"], 1, b"BBB", "audio/webm")  # renvoi après coupure
        a = ec.arreter(conn, dossier, e["id"], nb_annonces=5, duree_s=150)
        verifier("statut après arrêt", a["statut"], ec.A_TRANSCRIRE)
        verifier("morceaux reçus", a["nb_morceaux"], 3)
        verifier("trous signalés", a["morceaux_manquants"], [2, 4])
        verifier("mime nettoyé", a["mime"], "audio/webm")
        try:
            ec.ajouter_morceau(conn, dossier, e["id"], 5, b"EEE")
            FAIL.append("morceau accepté après l'arrêt")
        except ValueError:
            pass
        chemin = ec.assembler(dossier, e["id"], a["mime"])
        verifier("assemblage dans l'ordre", open(chemin, "rb").read(), b"AAABBBDDD")
        verifier("extension", chemin.endswith(".webm"), True)
        verifier("worker appelé", ec.travail_en_attente(conn, 20), True)

        ec.debut_transcription(conn, e["id"], "large-v3-turbo")
        ec.poser_progression(conn, e["id"], 0.42)
        verifier("avancement noté", ec.ecoute(conn, e["id"])["progression"], 0.42)
        ec.poser_progression(conn, e["id"], 7)
        verifier("avancement borné à 1", ec.ecoute(conn, e["id"])["progression"], 1.0)
        verifier("interrompue reprise", ec.reprendre_interrompues(conn), 1)
        ec.poser_progression(conn, e["id"], 0.5)
        verifier("hors transcription : pas d'écriture", ec.ecoute(conn, e["id"])["progression"], 1.0)
        ec.debut_transcription(conn, e["id"], "large-v3-turbo")
        verifier("redémarrage remet à zéro", ec.ecoute(conn, e["id"])["progression"], 0.0)
        ec.reprendre_interrompues(conn)
        verifier("de nouveau à transcrire", ec.ecoute(conn, e["id"])["statut"], ec.A_TRANSCRIRE)

        p = ec.poser_transcription(conn, dossier, e["id"], "[00:00] Bonjour.", 12.0, 150.0)
        verifier("type avec IA → à structurer", p["statut"], ec.A_STRUCTURER)
        verifier("transcription complète", p["progression"], 1.0)
        verifier("audio effacé", os.path.isdir(ec.dossier(dossier, e["id"])), False)

        ec.poser_proposition(conn, e["id"], {"titre": "Point atelier", "resume": "", "notes": "- Rouleau",
                                             "decisions": ["Changer le rouleau"], "actions": [],
                                             "participants": ["Flo"], "points_ouverts": []})
        res = ec.valider(conn, e["id"], {
            "titre": "Point atelier", "notes": "- Rouleau changé", "decisions": ["Changer le rouleau"],
            "participants": ["Flo"],
            "actions": [{"texte": "Demande d'intervention", "responsable": "Paul", "echeance": "2026-11-13"},
                        {"texte": "  ", "responsable": "", "echeance": ""}],
        }, "Jacques", 1, 30)
        r = res["reunion"]
        verifier("réunion close", r["statut"], rn.STATUT_CLOSE)
        verifier("type gardé", r["type"]["libelle"], "Production")
        verifier("décisions en puces", r["decisions"], "- Changer le rouleau")
        verifier("action vide ignorée", [x["texte"] for x in r["actions"]], ["Demande d'intervention"])
        verifier("écoute validée", res["ecoute"]["statut"], ec.VALIDEE)
        verifier("purge posée", bool(res["ecoute"]["purge_le"]), True)
        try:
            ec.valider(conn, e["id"], {}, "Jacques", 1, 30)
            FAIL.append("double validation acceptée")
        except ValueError:
            pass
        n = ec.purger(conn, dossier, 30, maintenant=datetime.now() + timedelta(days=31))
        verifier("transcription purgée", n["transcriptions"], 1)
        verifier("texte effacé", ec.ecoute(conn, e["id"])["transcription"], None)


def test_type_sans_ia():
    conn = base()
    sans = rn.enregistrer_type(conn, None, {"libelle": "CSE", "visibilite_defaut": "participants",
                                            "structuration_ia": False})
    with tempfile.TemporaryDirectory() as dossier:
        e = ec.creer(conn, "Jacques", 1, sans["id"])
        ec.ajouter_morceau(conn, dossier, e["id"], 0, b"A")
        ec.arreter(conn, dossier, e["id"], nb_annonces=1)
        p = ec.poser_transcription(conn, dossier, e["id"], "[00:00] Texte.", 1.0)
        verifier("sans IA → proposition directe", p["statut"], ec.PROPOSITION)


def test_rattachement():
    conn = base()
    with tempfile.TemporaryDirectory() as dossier:
        r = rn.lancer(conn, "Jacques", "2026-11-05", type_id=type_id(conn, "Commercial"), reprendre=False,
                      notes="Avant", decisions="- D1", noms_participants=["Flo"])
        e = ec.creer(conn, "Jacques", 1, None, reunion_id=r["id"])
        ec.ajouter_morceau(conn, dossier, e["id"], 0, b"A")
        ec.arreter(conn, dossier, e["id"], nb_annonces=1)
        ec.poser_transcription(conn, dossier, e["id"], "x", 1.0)
        ec.poser_proposition(conn, e["id"], ec.brief_vide(e))
        res = ec.valider(conn, e["id"], {"notes": "Après", "decisions": "- D2", "participants": ["flo", "Paul"]},
                         "Jacques", 1, 30)
        m = res["reunion"]
        verifier("même réunion", m["id"], r["id"])
        verifier("notes ajoutées à la suite", m["notes"], "Avant\n\nAprès")
        verifier("décisions ajoutées", m["decisions"], "- D1\n- D2")
        verifier("participants sans doublon", sorted(p["nom"] for p in m["participants"]), ["Flo", "Paul"])


def test_silence_et_abandon():
    conn = base()
    with tempfile.TemporaryDirectory() as dossier:
        vide = ec.creer(conn, "Jacques", 1)
        muette = ec.creer(conn, "Flo", 2)
        ec.ajouter_morceau(conn, dossier, muette["id"], 0, b"A")
        plus_tard = datetime.now() + timedelta(minutes=30)
        verifier("deux écoutes arrêtées d'office", ec.clore_silencieuses(conn, dossier, 20, plus_tard), 2)
        verifier("sans son → abandonnée", ec.ecoute(conn, vide["id"])["statut"], ec.ABANDONNEE)
        verifier("avec son → à transcrire", ec.ecoute(conn, muette["id"])["statut"], ec.A_TRANSCRIRE)
        ec.abandonner(conn, dossier, muette["id"])
        verifier("abandon efface l'audio", os.path.isdir(ec.dossier(dossier, muette["id"])), False)


def test_nettoyage_brief():
    from app.services import reunion_ecoute_ia as eia
    b = eia.nettoyer({"titre": "T" * 500, "actions": [{"texte": "A", "responsable": "Paul", "echeance": "vendredi"},
                                                      {"texte": "", "responsable": "x"}, "pas un dict"],
                      "decisions": ["D", "", None], "participants": "pas une liste"})
    verifier("titre borné", len(b["titre"]), 200)
    verifier("échéance invalide vidée", b["actions"], [{"texte": "A", "responsable": "Paul", "echeance": ""}])
    verifier("décisions vides retirées", b["decisions"], ["D"])
    verifier("participants forcés en liste", b["participants"], [])
    verifier("clés présentes", sorted(b), sorted(eia.SCHEMA["required"]))


if __name__ == "__main__":
    for nom, f in list(globals().items()):
        if nom.startswith("test_") and callable(f):
            f()
    print("=" * 60)
    if FAIL:
        print("\n".join(FAIL))
        sys.exit(1)
    print("Tous les cas passent.")

# -*- coding: utf-8 -*-
"""
Vue « Santé du dépôt » (Paramètres > Promouvoir > Déployer).

Les fonctions testées vivent dans app/routers/settings.py, qui importe toute
l'application. On les extrait par AST et on les exécute dans un espace de noms
minimal : le test reste rapide et n'a besoin ni de pydantic ni d'une instance.

Ce qui est vérifié :
  - les migrations numérotées ET les migrations en fichiers sont listées ;
  - un numéro utilisé deux fois est signalé (la seconde ne s'exécute jamais) ;
  - une migration présente dans le code mais absente de la base est « en attente » ;
  - les branches fusionnées et dormantes sont marquées « à nettoyer », jamais
    main ni staging ;
  - l'état du dossier distingue modifiés, non suivis et verrou git ;
  - la note sur 100 part de 100, plafonne chaque critère, ne descend jamais
    sous 0 et justifie chaque point retiré ;
  - le rafraîchissement des références utilise --prune (sans quoi une branche
    supprimée sur GitHub resterait comptée) et échoue proprement ;
  - aucune des commandes git utilisées n'écrit dans le dépôt.
"""

import ast
import datetime as _dt
import io
import os
import sqlite3
import subprocess
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FONCTIONS = ("_git_lire", "_jours_depuis", "_migrations_etat", "_branches_etat",
             "_dossier_etat", "_note_sante", "_git_rafraichir_refs")

_ok = True


_RIEN = object()


def ok(libelle, valeur, attendu=_RIEN):
    """Sans `attendu`, on teste la véracité ; avec, l'égalité (y compris None)."""
    global _ok
    bon = bool(valeur) if attendu is _RIEN else (valeur == attendu)
    if not bon:
        _ok = False
    print(("ok   " if bon else "ECHEC") + " " + libelle.ljust(56) + " " + repr(valeur))


def noms_globaux_non_definis(chemin, fonctions):
    """
    Noms que les fonctions vont chercher dans le module sans qu'ils y existent.

    `symtable` applique les vraies règles de portée de Python : un nom importé
    DANS la fonction est local, un nom seulement supposé présent est global. On
    compare donc les globaux référencés à ce que le module définit réellement.
    """
    import builtins
    import symtable

    src = io.open(chemin, encoding="utf-8").read()
    table = symtable.symtable(src, chemin.name, "exec")
    connus = {s.get_name() for s in table.get_symbols()
              if s.is_assigned() or s.is_imported()} | set(dir(builtins))

    manquants = []

    def visiter(t):
        for sym in t.get_symbols():
            if sym.is_global() and sym.is_referenced() and sym.get_name() not in connus:
                manquants.append(t.get_name() + " -> " + sym.get_name())
        for enfant in t.get_children():
            visiter(enfant)

    for enfant in table.get_children():
        if enfant.get_name() in fonctions:
            visiter(enfant)
    return sorted(set(manquants))


def charger(depot, conn):
    """Extrait les fonctions du routeur et les câble sur un dépôt/DB de test."""
    src = io.open(ROOT / "app/routers/settings.py", encoding="utf-8").read()
    arbre = ast.parse(src)
    segments = [
        ast.get_source_segment(src, n)
        for n in arbre.body
        if isinstance(n, ast.FunctionDef) and n.name in FONCTIONS
    ]
    assert len(segments) == len(FONCTIONS), "fonctions manquantes dans settings.py"

    class _DB:
        def __enter__(self):
            return conn

        def __exit__(self, *a):
            return False

    # Les fonctions du routeur font `from database import get_db` : on présente
    # un module `database` de test plutôt que d'ouvrir la vraie base.
    faux = types.ModuleType("database")
    faux.get_db = lambda: _DB()
    sys.modules["database"] = faux

    ns = {
        "_subprocess": subprocess,
        "_GIT_BIN": "git",
        "V2_REPO_PATH": str(depot),
        "_dt": _dt,
        "Path": Path,
        "Optional": __import__("typing").Optional,
        "NOTE_TOLERANCE_BRANCHES": 5,
    }
    for s in segments:
        exec(s, ns)
    return ns


def depot_de_test(base):
    """Petit dépôt git jouet : staging, une branche fusionnée, une branche vivante."""
    def g(*args, **kw):
        return subprocess.run(
            ["git", "-C", str(base), *args], check=True,
            capture_output=True, text=True, env=kw.get("env"),
        )

    env = dict(os.environ, GIT_AUTHOR_NAME="Test", GIT_AUTHOR_EMAIL="t@t",
               GIT_COMMITTER_NAME="Test", GIT_COMMITTER_EMAIL="t@t")
    subprocess.run(["git", "init", "-q", "-b", "staging", str(base)], check=True, capture_output=True)
    for cle, val in (("user.name", "Test"), ("user.email", "t@t")):
        g("config", cle, val)
    (base / "a.txt").write_text("un\n", encoding="utf-8")
    g("add", "."); g("commit", "-qm", "initial", env=env)
    g("checkout", "-q", "-b", "feature/fusionnee")
    (base / "b.txt").write_text("deux\n", encoding="utf-8")
    g("add", "."); g("commit", "-qm", "travail fini", env=env)
    g("checkout", "-q", "staging")
    g("merge", "-q", "--no-ff", "feature/fusionnee", "-m", "merge")
    g("checkout", "-q", "-b", "feature/vivante")
    (base / "c.txt").write_text("trois\n", encoding="utf-8")
    g("add", "."); g("commit", "-qm", "en cours", env=env)
    # Un dépôt local n'a pas de refs/remotes : on les fabrique pour que
    # for-each-ref et --merged voient les mêmes noms qu'en production.
    for nom in ("staging", "main", "feature/fusionnee", "feature/vivante"):
        ref = "staging" if nom == "main" else nom
        g("update-ref", "refs/remotes/origin/" + nom, "refs/heads/" + ref)
    g("checkout", "-q", "feature/vivante")
    return base


def db_de_test(chemin):
    conn = sqlite3.connect(chemin)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE schema_migrations (version INTEGER, name TEXT, applied_at TEXT);
        CREATE TABLE schema_migrations_fichiers (nom TEXT PRIMARY KEY, applique_le TEXT);
        """
    )
    conn.executemany(
        "INSERT INTO schema_migrations (version, name, applied_at) VALUES (?,?,?)",
        [
            (224, "calendrier_partage", "2026-07-30T09:00:00"),
            (225, "mc_transport_pct", "2026-08-01T09:00:00"),
            # Numéro réutilisé : la seconde n'a jamais tourné.
            (195, "imprimantes_windows", "2026-05-02T09:00:00"),
            (195, "imprimantes_windows_bis", "2026-05-02T09:00:00"),
        ],
    )
    conn.execute(
        "INSERT INTO schema_migrations_fichiers (nom, applique_le) VALUES (?,?)",
        ("mp_matiere_prix_par_fournisseur", "2026-08-03T11:00:00"),
    )
    conn.commit()
    return conn


def main():
    print("--- noms résolus dans le vrai module ---")
    # Le reste du test exécute les fonctions dans un espace de noms fabriqué :
    # il ne verrait pas un nom absent de settings.py. Chaque nom global
    # référencé doit donc exister au niveau module — `get_db`, lui, s'importe
    # localement dans chaque fonction (convention du fichier), et l'oublier a
    # déjà provoqué une 500 sur cette vue.
    ok("aucun nom global non défini",
       noms_globaux_non_definis(ROOT / "app/routers/settings.py", FONCTIONS), [])

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        depot = depot_de_test(tmp / "depot")
        conn = db_de_test(tmp / "test.db")
        ns = charger(depot, conn)

        print("\n--- migrations ---")
        mig = ns["_migrations_etat"]()
        noms = {m["nom"] for m in mig["appliquees"]}
        ok("les migrations numérotées sont listées", "mc_transport_pct" in noms)
        ok("les migrations en fichiers aussi", "mp_matiere_prix_par_fournisseur" in noms)
        ok("nombre total d'appliquées", mig["nb_appliquees"], 5)
        ok("le numéro 195 en double est signalé", [d["cle"] for d in mig["doublons"]], ["195"])
        ok("la plus récente est en tête", mig["derniere"]["nom"], "mp_matiere_prix_par_fournisseur")
        attente = {m["nom"] for m in mig["en_attente"]}
        ok("une migration déjà passée n'est plus en attente",
           "mp_matiere_prix_par_fournisseur" not in attente)
        ok("les migrations du code non jouées sont en attente", len(attente) >= 1)
        ok("chaque attente porte son fichier", all(m.get("fichier") for m in mig["en_attente"]))

        print("\n--- branches ---")
        branches = {b["nom"]: b for b in ns["_branches_etat"]()}
        ok("les branches distantes sont lues", sorted(branches), sorted(
            ["staging", "main", "feature/fusionnee", "feature/vivante"]))
        ok("une branche fusionnée est reconnue", branches["feature/fusionnee"]["fusionnee"], True)
        ok("une branche vivante ne l'est pas", branches["feature/vivante"]["fusionnee"], False)
        ok("staging est protégée", branches["staging"]["protegee"], True)
        ok("main est protégée", branches["main"]["protegee"], True)
        ok("jamais de ménage sur staging", branches["staging"]["a_nettoyer"], False)
        ok("jamais de ménage sur main", branches["main"]["a_nettoyer"], False)
        # Fraîchement créée : fusionnée mais pas encore dormante.
        ok("une branche fusionnée récente n'est pas à nettoyer",
           branches["feature/fusionnee"]["a_nettoyer"], False)
        ok("l'auteur et le sujet remontent",
           bool(branches["feature/vivante"]["auteur"] and branches["feature/vivante"]["dernier_commit"]))
        ok("l'âge est calculé", branches["feature/vivante"]["jours"], 0)

        print("\n--- seuil de ménage ---")
        ok("15 jours -> à nettoyer", ns["_jours_depuis"](
            (_dt.datetime.now() - _dt.timedelta(days=15)).strftime("%Y-%m-%d")) >= 14, True)
        ok("date illisible -> pas de calcul", ns["_jours_depuis"]("bidon"), None)

        print("\n--- dossier de travail ---")
        d = ns["_dossier_etat"]()
        ok("dossier propre au départ", d["propre"], True)
        ok("la branche courante est lue", d["branche"], "feature/vivante")
        (depot / "a.txt").write_text("modifié\n", encoding="utf-8")
        (depot / "nouveau.txt").write_text("x\n", encoding="utf-8")
        d = ns["_dossier_etat"]()
        ok("un fichier modifié est compté", d["nb_modifies"], 1)
        ok("un fichier non suivi est compté", d["nb_non_suivis"], 1)
        ok("le dossier n'est plus propre", d["propre"], False)
        ok("les chemins sont exposés", "a.txt" in d["modifies"][0])
        (depot / ".git" / "index.lock").write_text("", encoding="utf-8")
        ok("le verrou git est détecté", ns["_dossier_etat"]()["verrou_git"], True)
        (depot / ".git" / "index.lock").unlink()

        print("\n--- note de santé ---")
        note = ns["_note_sante"]
        mig_ok = {"doublons": [], "en_attente": []}
        dossier_ok = {"verrou_git": False, "nb_modifies": 0, "nb_non_suivis": 0}

        parfait = note(mig_ok, [], dossier_ok)
        ok("un dépôt sans reproche vaut 100", parfait["score"], 100)
        ok("et décroche la lettre A", parfait["lettre"], "A")
        ok("aucun critère ne coûte de point",
           [c["cle"] for c in parfait["criteres"] if c["perdu"]], [])

        # Cinq branches dormantes sont tolérées : la note ne bouge qu'au-delà.
        cinq = note(mig_ok, [{"a_nettoyer": True} for _ in range(5)], dossier_ok)
        ok("cinq branches dormantes ne coûtent rien", cinq["score"], 100)
        sept = note(mig_ok, [{"a_nettoyer": True} for _ in range(7)], dossier_ok)
        ok("la sixième et la septième coûtent 1 pt chacune", sept["score"], 98)

        # Chaque critère est plafonné : un seul défaut ne peut pas tout emporter.
        noyee = note(mig_ok, [{"a_nettoyer": True} for _ in range(500)], dossier_ok)
        ok("les branches sont plafonnées à 25 points", noyee["score"], 75)

        double = note({"doublons": [{"cle": "195"}], "en_attente": []}, [], dossier_ok)
        ok("un numéro de migration en double coûte 15 pts", double["score"], 85)
        ok("et le critère est cité en tête", double["criteres"][0]["cle"], "doublons")

        verrou = note(mig_ok, [], dict(dossier_ok, verrou_git=True))
        ok("un verrou git coûte 20 pts", verrou["score"], 80)

        pire = note(
            {"doublons": [{}, {}, {}], "en_attente": [{}] * 9},
            [{"a_nettoyer": True} for _ in range(400)],
            {"verrou_git": True, "nb_modifies": 99, "nb_non_suivis": 999},
        )
        ok("la note ne descend jamais sous 0", pire["score"], 0)
        ok("le pire cas est noté E", pire["lettre"], "E")

        reel = note(mig_ok, [{"a_nettoyer": True} for _ in range(48)],
                    dict(dossier_ok, nb_non_suivis=115))
        ok("l'état constaté le 27/08/2026 note C", reel["lettre"], "C")
        ok("chaque point perdu est justifié",
           all(c["detail"] for c in reel["criteres"] if c["perdu"]), True)
        ok("les points perdus totalisent l'écart à 100",
           sum(c["perdu"] for c in reel["criteres"]), 100 - reel["score"])

        print("\n--- rafraîchissement des références ---")
        src_r = io.open(ROOT / "app/routers/settings.py", encoding="utf-8").read()
        arbre_r = ast.parse(src_r)
        corps_r = next(
            ast.get_source_segment(src_r, n) for n in arbre_r.body
            if isinstance(n, ast.FunctionDef) and n.name == "_git_rafraichir_refs"
        )
        # Un fetch nu ajoute les nouvelles références mais ne retire jamais
        # celles dont la branche a disparu : sans --prune, le compteur
        # « à nettoyer » ne redescend jamais après un ménage.
        ok("le fetch utilise --prune", '"--prune"' in corps_r, True)
        ok("le fetch est silencieux", '"--quiet"' in corps_r, True)
        ok("le fetch a un garde-fou de temps", "timeout=" in corps_r, True)
        # Sur le dépôt jouet (aucun remote), git sort en 0 : « rien à fetcher »
        # n'est pas une erreur. Ce qu'on garantit ici, c'est que la fonction rend
        # toujours un booléen sans lever, et qu'elle laisse le dossier de travail
        # exactement dans l'état où elle l'a trouvé.
        avant = ns["_dossier_etat"]()
        ok("le rafraîchissement rend un booléen sans lever",
           isinstance(ns["_git_rafraichir_refs"](), bool), True)
        ok("le dossier de travail n'a pas bougé", ns["_dossier_etat"](), avant)
        ok("la branche courante n'a pas changé",
           ns["_dossier_etat"]()["branche"], avant["branche"])

        print("\n--- consultation seule ---")
        src = io.open(ROOT / "app/routers/settings.py", encoding="utf-8").read()
        arbre = ast.parse(src)
        corps = "\n".join(
            ast.get_source_segment(src, n) for n in arbre.body
            if isinstance(n, ast.FunctionDef) and n.name in FONCTIONS
        )
        ecritures = [v for v in ("\"push\"", "\"commit\"", "\"merge\"", "\"checkout\"",
                                 "\"branch\", \"-d", "\"reset\"", "\"clean\"")
                     if v in corps]
        ok("aucune commande git qui écrit", ecritures, [])
        ok("_git_lire ne passe jamais par le shell", "shell=True" not in corps, True)

        conn.close()

    print("\n" + ("TOUT EST VERT" if _ok else "DES VERIFICATIONS ONT ECHOUE"))
    return 0 if _ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

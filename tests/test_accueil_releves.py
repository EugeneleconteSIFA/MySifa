# -*- coding: utf-8 -*-
"""Relevés quotidiens des indicateurs d'accueil (app/services/accueil_releves.py).

Ce que ce test protège :

1. **Aucun bloc oublié.** Chaque bloc du registre est dans exactement une
   des trois tables : relevé (RELEVEURS), reconstituable (RECONSTITUABLES) ou
   écarté avec sa raison (NON_RELEVES). Un bloc sur un objet qui est relevé a
   son énumération d'objets (OBJETS). Un bloc ajouté au registre oblige à
   trancher.
2. **Un relevé rend les clés du registre.** Chaque relevé est exécuté contre
   une base neuve (migrations jouées dans un fichier temporaire) sous
   l'utilisateur système : il ne doit pas lever, et ses clés doivent être des
   valeurs numériques déclarées du bloc — sinon la future courbe lirait une
   clé que l'indicateur ne connaît pas.
3. **Le tour écrit la ligne du jour, une seule fois.** Deux passages le même
   jour réécrivent la ligne au lieu d'en ajouter une.
3bis. **La valeur du jour est figée à 18 h** (RELEVES_HEURE_FIGEE) : elle
   suit l'état courant avant, le premier passage à partir de 18 h l'arrête,
   et minimum et maximum couvrent toute la journée.
4. **L'utilisateur système ne sort pas de son bloc.** Hors de
   `en_tant_que_systeme()`, une requête sans cookie reste refusée.

Lancer : python3 tests/test_accueil_releves.py (partie 2-4 : FastAPI requis).
"""
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
os.chdir(RACINE)
sys.path.insert(0, str(RACINE))

echecs = []


def verifier(cond, msg):
    if not cond:
        echecs.append(msg)


def fin():
    if echecs:
        print("ÉCHEC test_accueil_releves :")
        for e in echecs:
            print("  -", e)
        sys.exit(1)


# ── 1. Couverture, sans FastAPI ─────────────────────────────────────────
_spec = importlib.util.spec_from_file_location("blocs_registre", RACINE / "app/services/blocs_registre.py")
reg = importlib.util.module_from_spec(_spec)
sys.modules["blocs_registre"] = reg
_spec.loader.exec_module(reg)

import ast
_src = (RACINE / "app/services/accueil_releves.py").read_text(encoding="utf-8")
_arbre = ast.parse(_src)
noms = {}
for n in _arbre.body:
    if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ("RELEVEURS", "NON_RELEVES", "RECONSTITUABLES", "OBJETS"):
        noms[n.targets[0].id] = {k.value for k in n.value.keys}
releves, ecartes = noms.get("RELEVEURS", set()), noms.get("NON_RELEVES", set())
reconst, objets = noms.get("RECONSTITUABLES", set()), noms.get("OBJETS", set())
for nom in reg.BLOCS:
    n_ = (nom in releves) + (nom in ecartes) + (nom in reconst)
    verifier(n_ == 1, f"{nom} : dans {n_} table(s) — l'ajouter à une seule de RELEVEURS, RECONSTITUABLES, NON_RELEVES")
    if nom in releves and reg.BLOCS[nom].objet:
        verifier(nom in objets, f"{nom} : relevé sur un objet sans énumération dans OBJETS")
for nom in releves | ecartes | reconst | objets:
    verifier(nom in reg.BLOCS, f"{nom} : cité dans accueil_releves.py mais absent du registre")
fin()

try:
    import fastapi  # noqa: F401
except ImportError:
    print(f"test_accueil_releves : OK partiel ({len(releves)} relevés, {len(reconst)} reconstituables, {len(ecartes)} écartés) — FastAPI absent, exécution non testée")
    sys.exit(0)

# ── 2-4. Exécution contre une base neuve ────────────────────────────────
_dossier = tempfile.mkdtemp(prefix="releves_")
os.environ["DB_PATH"] = os.path.join(_dossier, "test.db")
os.environ.setdefault("ERP_MIRROR_DB", os.path.join(_dossier, "absent_erp.db"))
import database  # noqa: E402  — d'abord, toujours (CLAUDE.md)
from database import get_db  # noqa: E402
from app.services import accueil_releves as ar  # noqa: E402
from app.services.auth_service import en_tant_que_systeme, get_current_user  # noqa: E402

with en_tant_que_systeme():
    for nom, fn in ar.RELEVEURS.items():
        b = reg.BLOCS[nom]
        numeriques = {c for c, _ in b.valeurs if c not in b.textes}
        objet = "1" if b.objet else ""
        try:
            v = fn(objet, {})
        except FileNotFoundError:
            continue   # miroir ERP absent : le tour le journalise et passe
        except Exception as e:
            verifier(False, f"{nom} : le relevé lève {type(e).__name__} : {e}")
            continue
        if v is None:
            verifier(bool(b.objet), f"{nom} : None sans objet suivi")
            continue
        inconnues = set(v) - numeriques
        verifier(not inconnues, f"{nom} : clés hors registre {sorted(inconnues)}")

with en_tant_que_systeme():
    for nom, enumerer in ar.OBJETS.items():
        try:
            objets_ = enumerer()
            verifier(isinstance(objets_, list) and all(isinstance(o, str) for o in objets_),
                     f"{nom} : l'énumération des objets doit rendre une liste de textes")
        except Exception as e:
            verifier(False, f"{nom} : l'énumération des objets lève {type(e).__name__} : {e}")

n1 = ar.tour(get_db)
n2 = ar.tour(get_db)

# ── 3bis. Une journée : 10 h, 17 h 40, 18 h 05, 22 h ────────────────────
from datetime import datetime  # noqa: E402
_vraie = ar.RELEVEURS["bat.statuts"]
_suite = iter([3, 9, 5, 1])
ar.RELEVEURS["bat.statuts"] = lambda objet, f: {"a-faire": next(_suite)}
for h, m in ((10, 0), (17, 40), (18, 5), (22, 0)):
    ar.tour(get_db, maintenant=datetime(2030, 1, 15, h, m))
ar.RELEVEURS["bat.statuts"] = _vraie
with get_db() as conn:
    r = conn.execute("SELECT valeurs, minimums, maximums, maj_le, vu_le FROM accueil_releves"
                     " WHERE bloc='bat.statuts' AND jour='2030-01-15'").fetchone()
import json as _j  # noqa: E402
verifier(r is not None, "journée simulée : aucune ligne écrite")
if r is not None:
    verifier(_j.loads(r["valeurs"]) == {"a-faire": 5}, f"valeur figée à 18 h : attendu 5 (passage de 18:05), obtenu {r['valeurs']}")
    verifier(_j.loads(r["minimums"]) == {"a-faire": 1} and _j.loads(r["maximums"]) == {"a-faire": 9},
             f"min/max de la journée : attendu 1 et 9, obtenu {r['minimums']} {r['maximums']}")
    verifier(r["maj_le"] == "2030-01-15T18:05:00" and r["vu_le"] == "2030-01-15T22:00:00",
             f"heures : valeur à {r['maj_le']}, dernier passage à {r['vu_le']}")

# Passage après 18 h sur une journée sans ligne (serveur redémarré à 19 h) : la valeur est prise.
f = ar.fusionner(None, {"x": 4}, "2030-01-16T19:00:00", "2030-01-16")
verifier(f["valeurs"] == {"x": 4}, "premier passage après 18 h : la valeur doit être prise")
with get_db() as conn:
    lignes = conn.execute("SELECT COUNT(*) FROM accueil_releves WHERE jour < '2030-01-01'").fetchone()[0]
verifier(n1 > 0 and n1 == n2, f"tour : {n1} puis {n2} relevés écrits")
verifier(lignes == n1, f"tour rejoué le même jour : {lignes} lignes pour {n1} relevés")

refuse = False
try:
    get_current_user(ar._requete())
except Exception:
    refuse = True
verifier(refuse, "hors de en_tant_que_systeme, une requête sans cookie est acceptée")

fin()
print(f"test_accueil_releves : OK ({len(ar.RELEVEURS)} relevés, {len(ar.RECONSTITUABLES)} reconstituables, {len(ar.NON_RELEVES)} écartés, {n1} écrits par tour)")

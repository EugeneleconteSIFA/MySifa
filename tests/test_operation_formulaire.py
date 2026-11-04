"""
Codes opération : attribut `formulaire` (fenêtre ouverte au poste avant la
saisie — « maintenance » pour l'opération de maintenance).

- migration `operation_codes_formulaire` rejouable, seed du code 93 ;
- le référentiel servi au poste porte l'attribut ;
- Paramètres n'accepte que les valeurs de OPERATION_FORMULAIRES.

Lancer : python3 tests/test_operation_formulaire.py
"""
import importlib.util
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402,F401  — d'abord, toujours (CLAUDE.md)
from app.services import operations_config as oc  # noqa: E402

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(60) + ("" if ok else f"{got!r}   attendu {expected!r}"))
    if not ok:
        FAIL.append(label)


conn = sqlite3.connect(":memory:")
conn.row_factory = sqlite3.Row
conn.execute("""CREATE TABLE operation_codes (code TEXT PRIMARY KEY, severity TEXT, label TEXT, category TEXT,
                required INTEGER DEFAULT 0, updated_at TEXT, outil_type TEXT)""")
conn.executemany("INSERT INTO operation_codes (code, severity, label, category) VALUES (?,?,?,?)",
                 [("64", "info", "Intervention technique", "technique"),
                  ("93", "info", "Opération de maintenance", "nettoyage")])

check("avant migration : attribut absent → None", oc.load_operations_dict(conn)["93"]["formulaire"], None)

spec = importlib.util.spec_from_file_location("m", RACINE / "app/core/migrations/2026_11_03_operation_formulaire.py")
mig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig)
mig.appliquer(conn)
conn.execute("UPDATE operation_codes SET formulaire = NULL WHERE code = '93'")
conn.execute("UPDATE operation_codes SET formulaire = 'maintenance' WHERE code = '64'")
mig.appliquer(conn)  # rejouée : le seed revient sur le 93, le réglage du 64 reste

ops = oc.load_operations_dict(conn)
check("seed : 93 ouvre le formulaire maintenance", ops["93"]["formulaire"], "maintenance")
check("réglage fait dans Paramètres conservé", ops["64"]["formulaire"], "maintenance")
check("liste Paramètres porte l'attribut",
      {o["code"]: o["formulaire"] for o in oc.list_operation_codes(conn)}, {"64": "maintenance", "93": "maintenance"})

base = {"code": "93", "label": "Opération de maintenance", "severity": "info", "category": "nettoyage"}
check("payload : formulaire admis", oc.validate_operation_payload({**base, "formulaire": "maintenance"})["formulaire"], "maintenance")
check("payload : vide → None", oc.validate_operation_payload({**base, "formulaire": ""})["formulaire"], None)
try:
    oc.validate_operation_payload({**base, "formulaire": "inconnu"})
    check("payload : formulaire inconnu refusé", False, True)
except ValueError:
    check("payload : formulaire inconnu refusé", True, True)

print("\n" + ("TOUT EST VERT" if not FAIL else f"{len(FAIL)} ÉCHEC(S)"))
sys.exit(1 if FAIL else 0)

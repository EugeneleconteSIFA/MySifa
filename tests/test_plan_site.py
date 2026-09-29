"""Plan du site : rattachement des codes d'emplacement et validation des éléments.

    python3 tests/test_plan_site.py
"""
import os
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services import plan_site  # noqa: E402
import importlib.util  # noqa: E402

_mig = os.path.join(os.path.dirname(__file__), "..", "app", "core", "migrations",
                    "2026_09_29_plan_site_elements.py")
spec = importlib.util.spec_from_file_location("mig_plan_site", _mig)
mig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig)

_mig_bat = os.path.join(os.path.dirname(__file__), "..", "app", "core", "migrations",
                        "2026_09_29_plan_site_batiments.py")
spec_bat = importlib.util.spec_from_file_location("mig_plan_site_bat", _mig_bat)
mig_bat = importlib.util.module_from_spec(spec_bat)
spec_bat.loader.exec_module(mig_bat)


def test_code_appartient():
    assert plan_site.code_appartient("A111", "A")
    assert plan_site.code_appartient("a432", "A")
    assert plan_site.code_appartient("Z0", "Z0")
    assert not plan_site.code_appartient("Z1", "Z0")
    assert not plan_site.code_appartient("AB12", "A")   # un préfixe ne capte pas un autre rack
    assert not plan_site.code_appartient("A111", "")
    assert not plan_site.code_appartient("Z", "Z0")


def test_nettoyer():
    d = plan_site.nettoyer({"type": "rack", "libelle": " Rack A ", "prefixe": "a",
                            "x": "10", "y": 5, "w": 80, "h": 12})
    assert d["libelle"] == "Rack A" and d["prefixe"] == "A" and d["points"] is None
    for mauvais in (
        {"type": "inconnu", "w": 10, "h": 10},
        {"type": "rack", "w": 1, "h": 10},
        {"type": "rack", "w": 10, "h": 10, "prefixe": "A-1"},
        {"type": "contour", "points": [[0, 0], [1, 1]]},
        {"type": "limite", "points": [[0, "x"]]},
    ):
        try:
            plan_site.nettoyer(mauvais)
        except ValueError:
            continue
        raise AssertionError(f"accepté à tort : {mauvais}")
    d = plan_site.nettoyer({"type": "limite", "points": [[0, 0], [10.26, 3]]})
    assert d["points"] == "[[0.0, 0.0], [10.3, 3.0]]"


def test_migration_rejouable():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    mig.appliquer(conn)
    n1 = conn.execute("SELECT COUNT(*) FROM plan_site_elements").fetchone()[0]
    mig.appliquer(conn)
    n2 = conn.execute("SELECT COUNT(*) FROM plan_site_elements").fetchone()[0]
    assert n1 == n2 == len(mig._SEED)
    els = plan_site.lister(conn)
    contour = [e for e in els if e["type"] == "contour"][0]
    assert len(contour["points"]) >= 3
    prefixes = {e["prefixe"] for e in els if e["prefixe"]}
    assert {"A", "B", "C", "D", "E", "M", "N", "O", "Z0", "Z1", "F"} <= prefixes


def test_batiments():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    mig.appliquer(conn)
    mig_bat.appliquer(conn)
    mig_bat.appliquer(conn)
    bats = [e for e in plan_site.lister(conn) if e["type"] == "batiment"]
    assert [b["libelle"] for b in bats] == ["Bâtiment 1", "Entrepôt 2", "Entrepôt 3"]
    assert all(len(b["points"]) >= 3 for b in bats)
    try:
        plan_site.nettoyer({"type": "batiment", "points": [[0, 0], [5, 5]]})
    except ValueError:
        pass
    else:
        raise AssertionError("bâtiment à deux points accepté")
    d = plan_site.nettoyer({"type": "batiment", "libelle": "Entrepôt 4",
                            "points": [[0, 0], [10, 0], [10, 10]]})
    assert d["libelle"] == "Entrepôt 4"


if __name__ == "__main__":
    test_code_appartient()
    test_nettoyer()
    test_migration_rejouable()
    test_batiments()
    print("Tous les cas passent.")

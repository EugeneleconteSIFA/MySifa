"""Garde-fou des références produit MyStock : python3 tests/test_reference_produit.py"""
import sys; sys.path.insert(0, '.')
from app.services.reference_produit import canoniser_reference_produit as c

CAS = {
    "10770035": "1077/0035",
    "1077/0035": "1077/0035",
    "1077 0035": "1077/0035",
    " 1077  /  0035 ": "1077/0035",
    "1077-0035": "1077/0035",
    "1077.0035": "1077/0035",
    "1077_0035": "1077/0035",
    "1077/35": "1077/0035",
    "6900041": "690/0041",
    "690 0041": "690/0041",
    "690/0041": "690/0041",
    # hors format : inchangé, en majuscules
    "123123": "123123",
    "123456789": "123456789",
    "fr055x300_s2020": "FR055X300_S2020",
    "BROSSE PLUS3": "BROSSE PLUS3",
    "1077/0035 - COHESIO 1": "1077/0035 - COHESIO 1",
    "": "",
    None: "",
}
ko = [(k, c(k), v) for k, v in CAS.items() if c(k) != v]
for k, got, want in ko:
    print(f"KO {k!r} -> {got!r}, attendu {want!r}")
print("OK" if not ko else f"{len(ko)} échec(s)")
sys.exit(1 if ko else 0)

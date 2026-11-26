"""Numéros d'OF abrégés d'Access : « 9932913, 914, 915 et 916 ».

Constat du 26/11/2026 : 387 OF de la prod portent plusieurs commandes dans
leur numéro, souvent abrégées. Seul le premier numéro complet était reconnu :
le dossier 9932914 ne retrouvait pas son OF « 9932913, 914, 915 et 916 ».
Les cas viennent tous de numéros réels de la prod.

Lancement : `python3 tests/test_of_numeros_abreges.py`
"""
import _base_temporaire  # noqa: F401  — base jetable, avant config/database/app.*
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database  # noqa: E402,F401
from app.routers.of_import import _of_tokens, _of_token_present  # noqa: E402

CAS = [
    ("9932913, 914, 915 et 916", ["9932913", "9932914", "9932915", "9932916"]),
    ("9932929-935-936", ["9932929", "9932935", "9932936"]),
    ("9930349+50+51+52 - L1", ["9930349", "9930350", "9930351", "9930352"]),
    ("9931848 - 849 - 851 - 852 - L2", ["9931848", "9931849", "9931851", "9931852"]),
    ("9931387, 89,91, 92 et 93", ["9931387", "9931389", "9931391", "9931392", "9931393"]),
    ("9930804, 805, 806 & 807.", ["9930804", "9930805", "9930806", "9930807"]),
    ("9931056/57/58/59 - 1183/0030", ["9931056", "9931057", "9931058", "9931059"]),
    ("9931532 /34 / 35 / 36 - L1", ["9931532", "9931534", "9931535", "9931536"]),
    ("9931685/86/87+745/46/47/49/50", ["9931685", "9931686", "9931687", "9931745",
                                       "9931746", "9931747", "9931749", "9931750"]),
    ("9931439,40,41&42/1", ["9931439", "9931440", "9931441", "9931442"]),
    ("9932449+ 652+ 653", ["9932449", "9932652", "9932653"]),
    ("OF 9931775-777-778-779-780-781-783", ["9931775", "9931777", "9931778", "9931779",
                                           "9931780", "9931781", "9931783"]),
    # Ce qui ne doit PAS s'étendre
    ("9930724 - 2e cadence", ["9930724"]),
    ("9931049 - 07/01", ["9931049"]),
    ("9930274/6+stock", ["9930274"]),
    ("9931044 - L2/3/4", ["9931044"]),
    ("9931996 LIGNE 2-3-4", ["9931996"]),
    ("9932325 - marché 752", ["9932325"]),
    ("9931004+9931005 1/2", ["9931004", "9931005"]),
    ("9932755 + stock", ["9932755"]),
]


def main() -> int:
    ko = 0
    for texte, attendu in CAS:
        obtenu = _of_tokens(texte)
        ok = obtenu == attendu
        ko += not ok
        print("%s  %-40s %s" % ("OK" if ok else "KO", texte, obtenu if not ok else ""))
    # Le dossier 9932914 retrouve l'OF abrégé, pas 9932917.
    for t, attendu in (("9932914", True), ("9932917", False)):
        ok = _of_token_present(t, "9932913, 914, 915 et 916") is attendu
        ko += not ok
        print("%s  %s dans « 9932913, 914, 915 et 916 » : %s" % ("OK" if ok else "KO", t, attendu))
    print()
    print("ECHECS : %d" % ko if ko else "Tout est vert.")
    return 1 if ko else 0


if __name__ == "__main__":
    sys.exit(main())

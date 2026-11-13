"""
Libellés des mesures en nombre libre : pesée par front.

Le premier front est le « Front opérateur », le dernier le « Front pignon »,
ceux du milieu gardent leur numéro. La même règle est écrite en JS
(`_libellePoint` de mysifa_alert_runtime.js, `libellePoint` des écrans de
MyMaintenance) : ce test fige celle du serveur.
"""
import sys

sys.path.insert(0, ".")
from app.services.mesures_libres import libelle, libelle_libre  # noqa: E402

ko = 0


def check(nom, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    ko += 0 if ok else 1
    print(("ok   " if ok else "KO   ") + nom + ("" if ok else f" : {obtenu!r} ≠ {attendu!r}"))


front = {"points_libres": True, "libelle_point": "Front"}
check("premier front", libelle(front, 0, 4), "Front opérateur")
check("front du milieu", libelle(front, 1, 4), "Front 2")
check("avant-dernier", libelle(front, 2, 4), "Front 3")
check("dernier front", libelle(front, 3, 4), "Front pignon")
check("deux fronts", [libelle(front, k, 2) for k in range(2)], ["Front opérateur", "Front pignon"])
check("un seul front", libelle(front, 0, 1), "Front opérateur")
check("série inconnue : pas de pignon", libelle(front, 3), "Front 4")
check("casse indifférente", libelle_libre("front", 2, 3), "front pignon")
check("autre libellé inchangé", libelle({"points_libres": True, "libelle_point": "Mesure"}, 0, 3), "Mesure 1")
check("points fixes inchangés", libelle({"points": ["Début", "Fin"]}, 1, 2), "Fin")

if ko:
    print(f"\n{ko} échec(s).")
    sys.exit(1)
print("\nTous les cas passent.")

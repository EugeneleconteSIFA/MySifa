"""
Déstockage : le conditionnement suit le métrage réel, comme la colle.

Décision du 19/10/2026 (Solde marché 772) : mandrins, cartons et palettes se
calculent sur le prévu de l'OF ramené au prorata du métrage réel / théorique.
Le nombre d'étiquettes saisi n'est pas fiable (1 885 800 étiquettes pour 43 %
du métrage), le compteur métrage l'est.

    python3 tests/test_destockage_prorata_reel.py
"""
import sys

sys.path.insert(0, ".")
import database  # noqa: F401 — d'abord, toujours (cf. CLAUDE.md)
from app.routers.besoins_matieres import _compute_besoins_dossier

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(("  OK  " if ok else "  KO  ") + libelle)
    if not ok:
        print("       attendu : %r\n       obtenu  : %r" % (attendu, obtenu))


ratio = 49627 / 116494.56
pe = {
    "of_metrage": 49627,
    "of_nb_mandrins": 1092 * ratio,
    "of_nb_cartons": 546 * ratio,
    "ft_mandrin_dia": "76",
    "ft_cartons": "385x385",
    "ft_palette_type": "Perdue",
    "ft_palette_nb_cartons_sol": 4,
    "ft_palette_nb_cartons_hauteur": 10,
    "prorata_reel": {"ratio": ratio, "mandrins": 1092, "cartons": 546},
}
lignes = {b["kind"]: b for b in _compute_besoins_dossier(pe, {}, 10.0)}

print("1. Quantités au prorata du métrage réel")
check("mandrins = 1092 x 42,6 %", round(lignes["mandrin"]["quantite"]), 465)
check("cartons = 546 x 42,6 %", round(lignes["carton"]["quantite"]), 233)
check("palettes suivent les cartons", round(lignes["palette"]["quantite"], 1), 5.8)

print("2. La formule dit d'où vient le chiffre")
# _n sépare les milliers par une espace fine insécable.
check("mandrins : prévu x prorata",
      "1 092 mandrins prévus × 42,6 % du métrage" in lignes["mandrin"]["formule"], True)
check("cartons : prévu x prorata",
      "546 cartons prévus × 42,6 % du métrage" in lignes["carton"]["formule"], True)

print("3. Sans prorata, l'OF reste la source")
sans = dict(pe, of_nb_mandrins=1092, of_nb_cartons=546)
sans.pop("prorata_reel")
l2 = {b["kind"]: b for b in _compute_besoins_dossier(sans, {}, 10.0)}
check("mandrins de l'OF", l2["mandrin"]["formule"].endswith("(chiffrés sur l'OF)"), True)

print("\n%s" % ("Tout est bon." if not ko else "%d échec(s)." % ko))
sys.exit(1 if ko else 0)

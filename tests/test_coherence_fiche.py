"""
Nombre de fronts : la bonne source, et le contrôle géométrique.

Les fiches utilisées ici sont réelles, relevées en production le 7 août 2026.
Elles documentent le défaut que ce module corrige : `mod_nb_front` vaut 1 sur
878 fiches sur 909, alors que `outil1_nb_front` est confirmé par la géométrie
sur 868 d'entre elles.

L'enjeu n'est pas cosmétique. Le nombre de fronts est au dénominateur du
métrage : le prendre à 1 quand il vaut 18 multiplie le besoin en frontal par
18, et c'est ce qui a produit un dossier à 55 823 km de frontal.
"""
import sys

sys.path.insert(0, ".")
from app.services.coherence_fiche import (            # noqa: E402
    alerte_courte, controler, laize_utile, nb_fronts, nb_fronts_geometrique,
)

ko = 0


def check(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}")
    if not ok:
        print(f"       attendu : {attendu!r}\n       obtenu  : {obtenu!r}")


# Relevés réels : (id, mod_nb_front, outil1_nb_front, mod_laize, laize, géométrie)
REELLES = [
    (1,   1, 9,  49.0,  470.0, 9),
    (3,   1, 6,  72.9,  470.0, 6),
    (4,   1, 17, 18.9,  333.0, 17),
    (6,   1, 5,  112.0, 570.0, 5),
    (8,   1, 3,  139.0, 440.0, 3),
    (10,  1, 8,  57.5,  470.0, 8),
    (15,  1, 15, 32.0,  500.0, 15),
    (146, 1, None, 23.0, 430.0, 18),
]

print("\n1. La géométrie retrouve le nombre de poses de l'outil")
for fid, mod, outil, ml, lz, geo in REELLES:
    ft = {"mod_nb_front": mod, "outil1_nb_front": outil,
          "mod_laize": ml, "laize_optimale": lz}
    check(f"fiche {fid:4} : {lz:g} ÷ {ml:g} → {nb_fronts_geometrique(ft)} front(s)",
          nb_fronts_geometrique(ft), geo)

print("\n2. C'est l'outil qui fait foi, pas le module")
for fid, mod, outil, ml, lz, geo in REELLES:
    ft = {"mod_nb_front": mod, "outil1_nb_front": outil,
          "mod_laize": ml, "laize_optimale": lz}
    res = nb_fronts(ft)
    attendu_source = "outil" if outil else "geometrie"
    attendu_valeur = float(outil) if outil else float(geo)
    check(f"fiche {fid:4} : {res['valeur']:g} front(s) via « {res['source']} »",
          (res["valeur"], res["source"]), (attendu_valeur, attendu_source))

print("\n3. L'ampleur de l'erreur évitée")
# Fiche 4 : 17 fronts réels, 1 déclaré dans mod_nb_front.
ft4 = {"mod_nb_front": 1, "outil1_nb_front": 17, "mod_laize": 18.9, "laize_optimale": 333.0}
qte, mod_long = 4_200_000, 152.4
avant = qte / 1 * mod_long / 1000.0
apres = qte / nb_fronts(ft4)["valeur"] * mod_long / 1000.0
check(f"ancien calcul : {avant:,.0f} m", round(avant), 640080)
check(f"nouveau calcul : {apres:,.0f} m", round(apres), 37652)
check("facteur d'erreur supprimé", round(avant / apres), 17)

print("\n4. Le contrôle nomme les fiches à corriger")
ft_ok = {"mod_nb_front": 1, "outil1_nb_front": 9, "mod_laize": 49.0, "laize_optimale": 470.0}
check("outil cohérent → coherent", controler(ft_ok)["verdict"], "coherent")
check("aucune alerte sur une fiche saine", alerte_courte(controler(ft_ok)), None)

ft_ko = {"mod_nb_front": 1, "outil1_nb_front": 1, "mod_laize": 18.9, "laize_optimale": 333.0}
r = controler(ft_ko)
check("outil à 1 mais 17 attendus → incoherent", r["verdict"], "incoherent")
check("le facteur d'erreur est chiffré", r["facteur_erreur"], 17.0)
check("le message dit le sens de l'erreur", "surestimé" in r["message"], True)
check("l'alerte courte est exploitable en une ligne",
      alerte_courte(r), "Fiche à vérifier : 1 front(s), 17 attendu(s) par la laize — besoin ×17.")

print("\n5. Cas limites")
check("sans mod_laize → indéterminable",
      controler({"outil1_nb_front": 4, "laize_optimale": 470})["verdict"], "indeterminable")
check("sans laize → indéterminable",
      controler({"outil1_nb_front": 4, "mod_laize": 100})["verdict"], "indeterminable")
check("module plus large que la bobine → incohérent",
      controler({"outil1_nb_front": 1, "mod_laize": 600, "laize_optimale": 470})["verdict"],
      "incoherent")
check("aucun front renseigné → incohérent, avec la valeur attendue",
      controler({"mod_laize": 47.0, "laize_optimale": 470.0})["nb_front_geometrique"], 10)
check("rien du tout → pas de valeur", nb_fronts({})["valeur"], None)

print("\n6. La laize de l'OF prime sur celle de la fiche")
ft = {"outil1_nb_front": 8, "mod_laize": 57.5, "laize_optimale": 470.0}
check("sans OF : la fiche fait foi", laize_utile(ft), 470.0)
check("avec OF : c'est la bobine montée", laize_utile(ft, 333.0), 333.0)
check("et le contrôle suit", controler(ft, 333.0)["nb_front_geometrique"], 5)
check("eti_laize n'est jamais prise pour la bobine",
      laize_utile({"eti_laize": 148.0}), None)

print("\n7. Une étiquette très large peut légitimement n'avoir qu'un front")
ft1 = {"mod_nb_front": 1, "mod_laize": 430.0, "laize_optimale": 470.0}
check("1 front déclaré, 1 attendu → coherent", controler(ft1)["verdict"], "coherent")
check("et la valeur retenue reste 1", nb_fronts(ft1)["valeur"], 1.0)

print()
if ko:
    print(f"ÉCHEC — {ko} vérification(s) en erreur.")
    sys.exit(1)
print("Tous les cas passent.")

"""
Accord OF / fiche technique, et le plus récent qui fait foi (18/11/2026).

Cas réels relevés en production :
- dossier 9932921, 1341/0012 : OF du 18/11 en 110 x 150, PP 95µ, Cohésio 1 ;
  fiche du 11/09 dupliquée de 1341/0008 — 100 x 99,6, Vélin H400, DSI ;
- dossier 9932763, 382/0074 : planifié et OF sur DSI, seule fiche Cohésio 1 ;
- 122/0023 : trois fiches Cohésio 1, la plus ancienne sortait à égalité.

Lancer : python3 tests/test_of_fiche_accord.py
"""
import sys

sys.path.insert(0, ".")

import database  # noqa: F401  — shim d'abord (cf. CLAUDE.md)
from app.services import of_fiche_accord as acc
from app.services.fiche_choix import meilleure_fiche
from app.services.fiche_pdf import generate_fiche_pdf

ko = 0


def verifier(libelle, obtenu, attendu):
    global ko
    ok = obtenu == attendu
    ko += 0 if ok else 1
    print(("  OK  " if ok else "  KO  ") + libelle + ("" if ok else f" — obtenu {obtenu!r}, attendu {attendu!r}"))


def champs(v):
    return [e["champ"] for e in v["ecarts"]]


OF_1341 = {"id": 1648, "of_numero": "9932921", "machine": "COHESIO 1", "format": "110 x 150 mm",
           "matiere": "PP 95µ BLANC MAT", "laize": 470.0, "qte_au_mille": 38.1,
           "date_creation": "18/11/2026", "date_import": "2026-11-18T09:40:59"}
FT_1341 = {"id": 924, "reference": "1341/0012", "machine": "DSI", "format": "100 x 99,6 mm",
           "eti_laize": 100.0, "eti_longueur": 99.6, "support": "VELIN H400", "laize": None,
           "laize_optimale": 333.0, "qte_au_mille": 33.86666488647461, "date_modif": "2026-09-11",
           "date_import": "2026-09-11T12:00:05", "outil1_numero_sifa": "1398"}

print("1341/0012 — fiche d'un autre produit")
v = acc.verdict(OF_1341, FT_1341)
verifier("machine, format, matière et quantité au mille en écart", champs(v),
         ["machine", "format", "matiere", "qte_au_mille"])
verifier("reconnue comme un autre produit", v["autre_produit"], True)
verifier("l'OF, plus récent, fait foi", v["source"], "of")
verifier("le message le dit", "plus récent que la fiche" in v["message"], True)
aff = acc.fiche_affichee(FT_1341, OF_1341, v)
verifier("support affiché = celui de l'OF", aff["support"], "PP 95µ BLANC MAT")
verifier("machine affichée = celle de l'OF", aff["machine"], "COHESIO 1")
verifier("format étiquette repris de l'OF", (aff["eti_laize"], aff["eti_longueur"]), (110.0, 150.0))
verifier("outillage de la fiche laissé tel quel", aff["outil1_numero_sifa"], "1398")
verifier("la fiche d'origine n'est pas modifiée", FT_1341["support"], "VELIN H400")

print("Fiche plus récente que l'OF")
ft_recente = dict(FT_1341, date_modif="2026-11-19")
v = acc.verdict(OF_1341, ft_recente)
verifier("la fiche fait foi", v["source"], "fiche")
verifier("rien n'est substitué", acc.fiche_affichee(ft_recente, OF_1341, v)["_substitutions"], [])
verifier("une correction manuelle récente compte comme une modification",
         acc.verdict(OF_1341, FT_1341, "2026-11-19T08:00:00")["source"], "fiche")
verifier("à date égale, l'OF", acc.verdict(OF_1341, dict(FT_1341, date_modif="2026-11-18"))["source"], "of")

print("382/0074 — fiche d'une autre machine")
v = acc.verdict(
    {"of_numero": "9932763", "machine": "DSI", "format": "99 x 35 mm", "matiere": "Thermique Eco H400",
     "laize": 333.0, "qte_au_mille": 12.7, "date_creation": "20/10/2026"},
    {"id": 580, "machine": "COHESIO 1", "format": "99 x 35 mm", "eti_laize": 99, "eti_longueur": 35,
     "support": "THERMIQUE ECO", "qte_au_mille": 9.525, "date_modif": "2025-12-23"})
verifier("machine en écart, matière identique", champs(v), ["machine", "qte_au_mille"])
verifier("un seul champ d'identité : pas « autre produit »", v["autre_produit"], False)

print("Pas de fausse alerte")
ok_of = {"machine": "COHESIO 1", "format": "40 x 40 mm", "matiere": "Couché", "qte_au_mille": 3.88}
ok_ft = {"machine": "COHESIO 1", "format": "Rond de 40 mm", "eti_laize": 40, "eti_longueur": 40,
         "support": "Couché", "qte_au_mille": 3.884000062942505}
verifier("« Rond de 40 mm » = 40 x 40", acc.comparer(ok_of, ok_ft), [])
verifier("format tourné", acc.comparer({"format": "150 x 110 mm"}, {"format": "110 x 150 mm"}), [])
verifier("102x152 contre 101,6 x 152,4", acc.comparer({"format": "102x152"}, {"format": "101,6 x 152,4 mm"}), [])
verifier("« COHESIO » générique vaut pour Cohésio 2",
         acc.comparer({"machine": "Cohésio 2"}, {"machine": "COHESIO"}), [])
verifier("« COHESIO2 » = « COHESIO 2 »", acc.comparer({"machine": "COHESIO 2"}, {"machine": "COHESIO2"}), [])
verifier("libellé ambigu (PP + thermique) : pas de conclusion",
         acc.comparer({"matiere": "PP100 Blanc thermique"}, {"support": "VELIN"}), [])
verifier("champ vide d'un côté : pas comparé", acc.comparer({"machine": None, "format": None}, FT_1341), [])
verifier("libellé d'OF sans format (« 1077/0058 - COHESIO1 »)",
         acc.comparer({"format": "1077/0058 - COHESIO1"}, {"format": "Rond de 70 mm"}), [])
verifier("ids de matière identiques, textes différents",
         acc.comparer({"matiere": "PP 95", "matiere_ref_id": 30}, {"support": "VELIN", "support_ref_id": 30}), [])

print("Familles de matière")
for texte, fam in (("VELIN ETI MATT", "velin"), ("Matt Coated inkjet paper", "couche"),
                   ("Couché mat 125µ spécial jet d'encre", "couche"), ("PP synthétique", "pp"),
                   ("Therm. Eco. Permanent", "thermique"), ("PET BLANC ENLEVABLE", "pet")):
    verifier(f"{texte} → {fam}", acc.famille_matiere(texte), fam)

print("Choix de la fiche : à rang égal, la plus récente")
fts = [
    {"id": 223, "reference": "122/0023 - COHESIO1 - Laize 510", "machine": "COHESIO 1",
     "laize_optimale": 510, "date_modif": "2025-06-11"},
    {"id": 884, "reference": "122/0023 - COHESIO2 - Laize 530", "machine": "COHESIO 1",
     "laize_optimale": 530, "date_modif": "2026-07-01"},
    {"id": 497, "reference": "122/0023 - COHESIO1 - Laize 440", "machine": "COHESIO 1",
     "laize_optimale": 440, "date_modif": "2025-11-19"},
]
verifier("machine seule : la plus récente (884)", meilleure_fiche(fts, "Cohésio 1")["id"], 884)
verifier("machine + laize l'emporte sur la récence (497)", meilleure_fiche(fts, "Cohésio 1", 440)["id"], 497)
verifier("sans date : la plus grande id",
         meilleure_fiche([{"id": 3, "machine": "DSI"}, {"id": 9, "machine": "DSI"}], "DSI")["id"], 9)

print("PDF")
v = acc.verdict(OF_1341, FT_1341)
pdf = generate_fiche_pdf(acc.fiche_affichee(FT_1341, OF_1341, v), avertissement=v["message"])
verifier("PDF généré avec bandeau", pdf[:4] == b"%PDF" and len(pdf) > 1000, True)
verifier("PDF sans écart inchangé", generate_fiche_pdf(FT_1341)[:4], b"%PDF")

print()
print("Tous les cas passent." if not ko else f"{ko} échec(s).")
sys.exit(1 if ko else 0)

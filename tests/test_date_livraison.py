"""
Lecture des dates de livraison saisies à la main.

Les trois formats testés ici sont ceux réellement présents en base le
7 août 2026 (295 dossiers, 33 illisibles avant ce correctif) :

    2026-04-07          262 dossiers
    07/04/2026           quelques-uns
    A livrer le 03/04    la majorité des 33

Le reste des cas couvre ce que la saisie manuelle produira tôt ou tard.
"""
import sys
from datetime import date

sys.path.insert(0, ".")
from app.services.date_livraison import parse_date_livraison, est_lisible  # noqa: E402

REF = date(2026, 8, 7)
ko = 0

CAS = [
    # (saisie, attendu, libellé)
    ("2026-04-07",            date(2026, 4, 7),  "ISO — format applicatif"),
    ("2026-04-07T09:30:00",   date(2026, 4, 7),  "ISO avec heure"),
    ("2026-4-7",              date(2026, 4, 7),  "ISO sans zéro de tête"),
    ("07/04/2026",            date(2026, 4, 7),  "français JJ/MM/AAAA — vu en base"),
    ("7/4/2026",              date(2026, 4, 7),  "français sans zéros"),
    ("07/04/26",             date(2026, 4, 7),  "année sur 2 chiffres"),
    ("07-04-2026",            date(2026, 4, 7),  "séparateur tiret"),
    ("07.04.2026",            date(2026, 4, 7),  "séparateur point"),
    ("A livrer le 03/04",     date(2026, 4, 3),  "phrase sans année — vu en base"),
    ("A livrer le 10/04",     date(2026, 4, 10), "phrase sans année — vu en base"),
    ("livraison prévue 15/09", date(2026, 9, 15), "autre phrase — le préfixe n'est pas listé"),
    ("  12/12/2026  ",        date(2026, 12, 12), "espaces autour"),
    ("",                      None,              "vide"),
    (None,                    None,              "NULL"),
    ("A livrer",              None,              "phrase sans chiffres"),
    ("dès que possible",      None,              "texte libre sans date"),
    ("30/02/2026",            None,              "date impossible — pas de repli silencieux"),
    ("32/01/2026",            None,              "jour hors bornes"),
]

print("\n1. Formats réellement saisis")
for brut, attendu, libelle in CAS:
    obtenu = parse_date_livraison(brut, reference=REF)
    ok = obtenu == attendu
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle:44} {str(brut)[:22]:24} → {obtenu}")
    if not ok:
        print(f"       attendu : {attendu}")

print("\n2. Convention française : JJ/MM, jamais MM/JJ")
d = parse_date_livraison("03/04/2026", reference=REF)
ok = d == date(2026, 4, 3)
ko += 0 if ok else 1
print(f"  {'OK ' if ok else 'KO '} 03/04/2026 est le 3 avril, pas le 4 mars → {d}")

print("\n3. Année devinée : on prend la plus proche de la référence")
essais = [
    (date(2026, 12, 28), "03/01",  date(2027, 1, 3),  "fin décembre → janvier PROCHAIN"),
    (date(2026, 1, 5),   "28/12",  date(2025, 12, 28), "début janvier → décembre DERNIER"),
    (date(2026, 8, 7),   "10/04",  date(2026, 4, 10),  "milieu d'année → même année"),
]
for ref, brut, attendu, libelle in essais:
    obtenu = parse_date_livraison(brut, reference=ref)
    ok = obtenu == attendu
    ko += 0 if ok else 1
    print(f"  {'OK ' if ok else 'KO '} {libelle:38} (réf {ref}) {brut} → {obtenu}")
    if not ok:
        print(f"       attendu : {attendu}")

print("\n4. est_lisible sépare bien les deux populations")
for brut, attendu in [("2026-04-07", True), ("A livrer le 03/04", True),
                      ("07/04/2026", True), ("dès que possible", False), ("", False)]:
    obtenu = est_lisible(brut)
    ok = obtenu == attendu
    ko += 0 if ok else 1
    print(f"  {'OK ' if ok else 'KO '} {str(brut)[:24]:26} → {obtenu}")

print()
if ko:
    print(f"ÉCHEC — {ko} cas en erreur.")
    sys.exit(1)
print("Tous les cas passent.")

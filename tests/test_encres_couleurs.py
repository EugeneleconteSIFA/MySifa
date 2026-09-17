"""
Couleurs d'encre : rapprochement des désignations et teinte du BAT.

Les désignations viennent telles quelles des fiches techniques (relevé du
17/09/2026) : le test verrouille qu'elles retombent sur la même clé, et que le
BAT prend la teinte du référentiel avant les noms simples.

Le service ne touche qu'à sqlite : base en mémoire, sans FastAPI.

Lancer : python3 tests/test_encres_couleurs.py
"""

import importlib.util
import sqlite3
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))


def _charger(nom: str, chemin: Path):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


svc = _charger("encres_couleurs", RACINE / "app" / "services" / "encres_couleurs.py")
mig = _charger("mig_encres", RACINE / "app" / "core" / "migrations" / "2026_09_17_encres_couleurs.py")

FAIL = []


def verifier(cas, obtenu, attendu):
    if obtenu != attendu:
        FAIL.append(cas)
        print(f"  ECHEC  {cas} — obtenu {obtenu!r}, attendu {attendu!r}")
    else:
        print(f"  ok     {cas}")


def base():
    conn = sqlite3.connect(":memory:")
    mig.appliquer(conn)
    return conn


def test_seed():
    conn = base()
    mig.appliquer(conn)  # rejouable
    n = conn.execute("SELECT COUNT(*) FROM encres_couleurs").fetchone()[0]
    verifier("seed rejouable sans doublon", n, len(mig.SEED))
    verifier("chaque code du seed est deja sous sa forme canonique",
             [c for c, _, _ in mig.SEED if svc.cle(c) != c], [])


def test_cles():
    for saisie in ("P.485 C", "P 485C", "485 C", "P. 485 C", "P.485 C ROUGE", "P-485C"):
        verifier(f"cle({saisie!r})", svc.cle(saisie), "485 C")
    verifier("sans suffixe → C par defaut", svc.cle("P485"), "485 C")
    verifier("zero de tete sur 4 chiffres", svc.cle("P.0631 C"), "631 C")
    verifier("zero de tete garde sur 3 chiffres", svc.cle("RED 032"), "032 C")
    verifier("nom avec prefixe", svc.cle("P. BLACK C"), "BLACK C")
    verifier("nom libre", svc.cle("bleu clair"), "BLEU CLAIR")
    verifier("PURPLE n'est pas un prefixe P", svc.cle("PURPLE U"), "PURPLE U")


def test_resolution():
    E = svc.charger(base())
    cas = {
        "P.485 C": "#DA291C",
        "JAUNE P 135U": "#FFC845",   # U absent → teinte C
        "P.BLACKU": "#2D2926",       # suffixe colle
        "P. BLACK": "#2D2926",
        "BLEU P.647 U": "#236192",
        "P. 072U": "#10069F",
        "Process Blue": "#0085CA",
        "#fd0": "#FFDD00",
        "ROUGE": None,               # nom simple : pas dans le referentiel
        "": None,
    }
    for d, attendu in cas.items():
        verifier(f"resoudre({d!r})", svc.resoudre(d, E), attendu)


def test_inactive_ignoree():
    conn = base()
    conn.execute("UPDATE encres_couleurs SET actif=0 WHERE cle='485 C'")
    verifier("encre inactive ignoree", svc.resoudre("P485", svc.charger(conn)), None)


def test_bat():
    bat = _charger("bat_etiquette", RACINE / "app" / "services" / "bat_etiquette.py")
    E = svc.charger(base())
    verifier("BAT : referentiel avant nom simple",
             bat._guess_hex("P.286 C BLEU", E), "#0033A0")
    verifier("BAT : nom simple si referentiel muet",
             bat._guess_hex("ROUGE", E), bat._BASIC_INKS["rouge"])
    verifier("BAT : sans referentiel, comportement d'avant",
             bat._guess_hex("P.286 C BLEU"), bat._BASIC_INKS["bleu"])
    verifier("BAT : pantone de tete puis nom de couleur",
             bat._guess_hex("P 999 C", E, fallback="jaune"), bat._BASIC_INKS["jaune"])
    fiche = {"impressions": True, "etiquette": {"laize": 100, "longueur": 150},
             "impressions_detail": {"recto": 1, "recto_details": [{"couleur": "P.485 C"}]}}
    spec = bat.build_bat_spec({}, fiche, encres=E)
    verifier("BAT : spec porte la teinte", spec["couleurs"][0]["hex"], "#DA291C")
    verifier("BAT : zone teintee a la couleur de l'encre",
             bat._print_palette(spec)["fill"], "#DA291C")


if __name__ == "__main__":
    for t in (test_seed, test_cles, test_resolution, test_inactive_ignoree, test_bat):
        print(t.__name__)
        t()
    if FAIL:
        print(f"\n{len(FAIL)} echec(s)")
        sys.exit(1)
    print("\nTout est vert.")

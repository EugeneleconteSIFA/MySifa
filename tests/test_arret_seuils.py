"""
Seuils d'arret : ce qui declenche, ce qui ne declenche pas, et ce qui dispense.

La regle n'a d'interet que si elle reste silencieuse sur la routine. Ces cas
verrouillent les trois choses qui la rendent tenable a l'atelier :

- la 3e casse bande ne demande rien, la 4e oui ;
- un arret deja commente franchit le seuil sans rien exiger de plus ;
- un meme arret ne franchit qu'un seul seuil, et les compteurs repartent.

Le service ne touche a aucun module de l'application : il prend une connexion
sqlite et rien d'autre. Le test s'execute donc sur une base en memoire, sans
charger `database` ni FastAPI.

Lancer : python3 tests/test_arret_seuils.py
"""

import importlib.util
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]


def _charger(nom: str, chemin: Path):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


svc = _charger("arret_seuils", RACINE / "app" / "services" / "arret_seuils.py")
mig = _charger("mig_seuils", RACINE / "app" / "core" / "migrations" / "2026_08_27_arret_seuils.py")

FAIL = []
T0 = datetime(2026, 6, 11, 8, 0, 0)


def verifier(cas: str, obtenu, attendu):
    if obtenu != attendu:
        FAIL.append(f"{cas} : obtenu {obtenu!r}, attendu {attendu!r}")
        print(f"  ECHEC  {cas} — obtenu {obtenu!r}, attendu {attendu!r}")
    else:
        print(f"  ok     {cas}")


def base():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE production_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operateur TEXT, date_operation TEXT, operation TEXT,
            operation_code TEXT, operation_category TEXT,
            machine TEXT, no_dossier TEXT, commentaire TEXT,
            est_annule INTEGER DEFAULT 0);
        CREATE TABLE users (id INTEGER PRIMARY KEY, nom TEXT, operateur_lie TEXT);
        """
    )
    mig.appliquer(conn)
    return conn


def saisir(conn, minute, code, categorie="arret", operation=None, commentaire=None,
           dossier="D1", machine="Cohesio 1", operateur="Alan"):
    """Ecrit une saisie et rejoue les deux evaluations, comme le fait l'endpoint."""
    dt = (T0 + timedelta(minutes=minute)).strftime("%Y-%m-%dT%H:%M:%S")
    cur = conn.execute(
        """INSERT INTO production_data
           (operateur, date_operation, operation, operation_code, operation_category,
            machine, no_dossier, commentaire)
           VALUES (?,?,?,?,?,?,?,?)""",
        (operateur, dt, operation or f"{code} - Operation", code, categorie,
         machine, dossier, commentaire),
    )
    sid = cur.lastrowid
    precedent = svc.cloturer_precedent(conn, sid)
    courant = svc.evaluer_saisie(conn, sid)
    return sid, [e for e in (precedent, courant) if e]


def prod(conn, minute, **kw):
    """Une reprise de production : ferme l'arret precedent, n'en ouvre aucun."""
    return saisir(conn, minute, "88", categorie="production",
                  operation="88 - Reprise production", **kw)


# ─── 1. Repetition : la 3e ne demande rien, la 4e oui ────────────────────────
def test_repetition():
    print("\n1. Repetition — seuil a 4 sur la casse bande (code 53)")
    conn = base()
    declenches = []
    for i in range(3):
        _, ev = saisir(conn, i * 20, "53", operation="53 - Casse bande")
        declenches += ev
        prod(conn, i * 20 + 5)
    verifier("trois casses bande ne declenchent rien", len(declenches), 0)

    _, ev = saisir(conn, 100, "53", operation="53 - Casse bande")
    verifier("la 4e declenche", len(ev), 1)
    verifier("regle = repetition", ev[0]["regle"] if ev else None, "repetition")
    verifier("compteur = 4", ev[0]["compteur"] if ev else None, 4)
    verifier("explication exigee", ev[0]["explication_exigee"] if ev else None, True)
    return conn


# ─── 2. Remise a zero apres franchissement ───────────────────────────────────
def test_remise_a_zero():
    print("\n2. Remise a zero — apres un franchissement, le compteur repart")
    conn = test_repetition_silencieuse()
    prod(conn, 105)
    declenches = []
    for i in range(3):
        _, ev = saisir(conn, 110 + i * 20, "53", operation="53 - Casse bande")
        declenches += ev
        prod(conn, 115 + i * 20)
    verifier("les 3 suivantes ne redeclenchent pas", len(declenches), 0)
    _, ev = saisir(conn, 200, "53", operation="53 - Casse bande")
    verifier("la 4e d'apres declenche a nouveau", len(ev), 1)


def test_repetition_silencieuse():
    conn = base()
    for i in range(3):
        saisir(conn, i * 20, "53", operation="53 - Casse bande")
        prod(conn, i * 20 + 5)
    saisir(conn, 100, "53", operation="53 - Casse bande")
    return conn


# ─── 3. Regle permanente ─────────────────────────────────────────────────────
def test_permanent():
    print("\n3. Permanent — intervention technique et approvisionnement")
    conn = base()
    _, ev = saisir(conn, 0, "64", categorie="technique",
                   operation="64 - Intervention technique")
    verifier("64 declenche des la 1re fois", len(ev), 1)
    verifier("regle = permanent", ev[0]["regle"] if ev else None, "permanent")

    _, ev = saisir(conn, 10, "56", categorie="appro",
                   operation="56 - Approvisionnement mandrins")
    verifier("la categorie appro declenche aussi", len(ev), 1)

    _, ev = saisir(conn, 20, "51", operation="51 - Casse Echenillage")
    verifier("un arret ordinaire ne declenche pas", len(ev), 0)


# ─── 4. Dispense par commentaire ─────────────────────────────────────────────
def test_dispense():
    print("\n4. Dispense — un arret deja commente n'exige rien de plus")
    conn = base()
    _, ev = saisir(conn, 0, "64", categorie="technique",
                   operation="64 - Intervention technique",
                   commentaire="fuite d'air fondoir")
    verifier("le seuil est bien franchi", len(ev), 1)
    verifier("mais aucune explication n'est exigee",
             ev[0]["explication_exigee"] if ev else None, False)
    ligne = conn.execute("SELECT * FROM arret_seuils_franchis ORDER BY id DESC LIMIT 1").fetchone()
    verifier("le commentaire est repris comme explication",
             ligne["explication_texte"], "fuite d'air fondoir")


# ─── 5. Duree d'un seul arret, connue a la reprise ───────────────────────────
def test_duree_unitaire():
    print("\n5. Arret long — la duree n'est connue qu'a la reprise")
    conn = base()
    _, ev = saisir(conn, 0, "51", operation="51 - Casse Echenillage")
    verifier("rien au moment ou l'arret est code", len(ev), 0)
    _, ev = prod(conn, 75)
    verifier("la reprise 1 h 15 plus tard declenche", len(ev), 1)
    verifier("regle = duree_unitaire", ev[0]["regle"] if ev else None, "duree_unitaire")
    verifier("la demande porte sur l'arret, pas sur la reprise",
             ev[0]["operation_code"] if ev else None, "51")


# ─── 6. Duree cumulee ────────────────────────────────────────────────────────
def test_duree_cumul():
    print("\n6. Duree cumulee — trois arrets de 35 min sur la meme production")
    conn = base()
    declenches = []
    t = 0
    for _ in range(3):
        _, ev = saisir(conn, t, "51", operation="51 - Casse Echenillage")
        declenches += ev
        _, ev = prod(conn, t + 35)
        declenches += ev
        t += 40
    regles = [e["regle"] for e in declenches]
    verifier("un seul franchissement", len(declenches), 1)
    verifier("par la duree cumulee", regles[0] if regles else None, "duree_cumul")


# ─── 7. Un arret ne franchit qu'un seul seuil ────────────────────────────────
def test_un_seul_seuil():
    print("\n7. Un arret, un seuil — la repetition prend le pas, pas de doublon")
    conn = base()
    for i in range(3):
        saisir(conn, i * 20, "53", operation="53 - Casse bande")
        prod(conn, i * 20 + 5)
    _, ev = saisir(conn, 100, "53", operation="53 - Casse bande")
    sid = ev[0]["saisie_id"]
    _, ev2 = prod(conn, 190)   # l'arret a dure 1 h 30
    verifier("la reprise ne recompte pas le meme arret", len(ev2), 0)
    n = conn.execute(
        "SELECT COUNT(*) c FROM arret_seuils_franchis WHERE saisie_id=?", (sid,)
    ).fetchone()["c"]
    verifier("une seule ligne pour cette saisie", n, 1)


# ─── 8. L'explication eteint la demande ──────────────────────────────────────
def test_explication():
    print("\n8. Explication — le commentaire ecrit apres coup eteint la demande")
    conn = base()
    _, ev = saisir(conn, 0, "64", categorie="technique",
                   operation="64 - Intervention technique")
    sid = ev[0]["saisie_id"]
    verifier("demande ouverte", ev[0]["explication_exigee"], True)
    maj = svc.enregistrer_explication(conn, sid, "changement de la broche")
    verifier("une ligne mise a jour", maj, 1)
    reste = conn.execute(
        "SELECT COUNT(*) c FROM arret_seuils_franchis WHERE explication_exigee=1"
    ).fetchone()["c"]
    verifier("plus aucune demande en attente", reste, 0)


# ─── 9. Une regle de machine bat la regle generale ───────────────────────────
def test_regle_machine():
    print("\n9. Specificite — une regle attachee a une machine bat la regle generale")
    conn = base()
    conn.execute(
        """INSERT INTO arret_seuils
           (cible_type, cible, machine, mode, repetitions, actif, created_at)
           VALUES ('code','53','Cohesio 2','repetition',2,1,'2026-06-01')"""
    )
    regles = svc.charger_regles(conn)
    r1 = svc.regle_pour(regles, "53", "arret", "Cohesio 1")
    r2 = svc.regle_pour(regles, "53", "arret", "Cohesio 2")
    verifier("Cohesio 1 garde le seuil general", r1["repetitions"], 4)
    verifier("Cohesio 2 prend son seuil propre", r2["repetitions"], 2)
    r3 = svc.regle_pour(regles, "99", "arret", "Cohesio 1")
    verifier("un code inconnu tombe sur la regle par defaut", r3["cible_type"], "defaut")


# ─── 10. Rien en dehors des categories surveillees ───────────────────────────
def test_hors_perimetre():
    print("\n10. Perimetre — la production et le calage ne sont pas surveilles")
    conn = base()
    declenches = []
    for code, cat in (("03", "production"), ("02", "calage"), ("63", "pause"),
                      ("86", "personnel")):
        for _ in range(6):
            _, ev = saisir(conn, len(declenches) * 3, code, categorie=cat)
            declenches += ev
    verifier("aucun franchissement hors perimetre", len(declenches), 0)


if __name__ == "__main__":
    print("Seuils d'arret\n" + "=" * 62)
    test_repetition()
    test_remise_a_zero()
    test_permanent()
    test_dispense()
    test_duree_unitaire()
    test_duree_cumul()
    test_un_seul_seuil()
    test_explication()
    test_regle_machine()
    test_hors_perimetre()
    print("\n" + "=" * 62)
    if FAIL:
        print(f"{len(FAIL)} echec(s) :")
        for f in FAIL:
            print("  -", f)
        sys.exit(1)
    print("Tous les cas passent.")

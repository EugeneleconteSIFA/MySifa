"""
Note de confiance transporteur : ce que le calcul doit garantir.

Les cas verrouilles ici sont ceux ou une erreur produirait un ecran plausible
— une lettre s'affiche, elle a l'air juste, et elle est fausse :

- tout le monde part de NOTE_DEPART (5/10, soit C), et cette note de depart
  pese comme un avis : le premier avis deplace la note de moitie, il ne la fait
  pas basculer d'un bout a l'autre de l'echelle ;
- la note de depart ne compte jamais comme un avis (nb_avis reste a 0) ;
- une thematique lourde pese davantage qu'une thematique legere ;
- un avis ancien pese moins qu'un avis recent ;
- l'ajustement manuel s'AJOUTE a la moyenne, il ne l'ecrase pas — sinon le
  mecanisme d'avis devient decoratif ;
- l'ajustement est borne ;
- les seuils de lettre ne bougent pas, et 5/10 tombe bien dans la bande C ;
- la recommandation par zone n'ecarte pas un transporteur jamais utilise ;
- la zone de classement est la REGION : deux departs sur deux departements
  d'une meme region comptent ensemble ;
- l'experience sur la zone est le nombre de transports PONDERE par leur
  recence — dix transports de 2023 ne valent pas dix transports du trimestre ;
- a experience egale, la note departage ; a note egale, l'experience departe.

Le service ne touche qu'au referentiel des regions (`expe_regions`, stdlib
seule) : il prend une connexion sqlite et rien d'autre. Le test s'execute donc sur une base en memoire, sans
charger `database` ni FastAPI.

Lancer : python3 tests/test_expe_notes.py
"""

import importlib.util
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))


def _charger(nom: str, chemin: Path):
    spec = importlib.util.spec_from_file_location(nom, chemin)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


svc = _charger("expe_notes", RACINE / "app" / "services" / "expe_notes.py")
reg = _charger("expe_regions", RACINE / "app" / "services" / "expe_regions.py")
mig = _charger(
    "mig_notes",
    RACINE / "app" / "core" / "migrations" / "2026_08_31_expe_notes_transporteurs.py",
)

FAIL = []


def verifier(cas, obtenu, attendu):
    if obtenu != attendu:
        FAIL.append(f"{cas} : obtenu {obtenu!r}, attendu {attendu!r}")
        print(f"  ECHEC  {cas} — obtenu {obtenu!r}, attendu {attendu!r}")
    else:
        print(f"  ok     {cas}")


def base():
    """Base minimale : les tables que la migration attend, puis la migration."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """CREATE TABLE expe_transporteurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT, couleur TEXT, actif INTEGER DEFAULT 1,
            zone_france INTEGER DEFAULT 1, zone_messagerie INTEGER DEFAULT 1,
            zone_affretement INTEGER DEFAULT 1)"""
    )
    conn.execute(
        """CREATE TABLE expe_departs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transporteur_id INTEGER, transporteur TEXT,
            code_postal_destination TEXT, date_enlevement TEXT)"""
    )
    conn.execute(
        """CREATE TABLE expe_tarifs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, transporteur_id INTEGER,
            zone_type TEXT, zone_valeur TEXT, actif INTEGER DEFAULT 1)"""
    )
    conn.execute("CREATE TABLE clients (id INTEGER PRIMARY KEY, cp TEXT, ville TEXT)")
    mig.appliquer(conn)
    return conn


def ajouter_transporteur(conn, nom, couleur=""):
    return conn.execute(
        "INSERT INTO expe_transporteurs (nom, couleur, actif) VALUES (?,?,1)",
        (nom, couleur),
    ).lastrowid


def them(conn, code):
    return conn.execute(
        "SELECT id FROM expe_avis_thematiques WHERE code=?", (code,)
    ).fetchone()["id"]


def avis(conn, trp, note, code="ponctualite", jours=0, sens="alerte"):
    quand = (datetime.now() - timedelta(days=jours)).strftime("%Y-%m-%dT%H:%M:%S")
    conn.execute(
        """INSERT INTO expe_transporteur_avis
           (transporteur_id, type, sens, note, thematique_id, created_at)
           VALUES (?, 'avis', ?, ?, ?, ?)""",
        (trp, sens, note, them(conn, code), quand),
    )


def ajustement(conn, trp, valeur):
    conn.execute(
        """INSERT INTO expe_transporteur_avis
           (transporteur_id, type, sens, ajustement, commentaire, created_at)
           VALUES (?, 'ajustement', 'appreciation', ?, 'motif', ?)""",
        (trp, valeur, datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
    )


def test_seuils():
    print("\n1. Seuils de lettre")
    for valeur, attendu in (
        (10.0, "A"), (8.5, "A"), (8.49, "B"), (7.0, "B"), (6.99, "C"),
        (5.0, "C"), (4.5, "C"), (4.49, "D"), (3.0, "D"), (2.99, "E"),
        (1.5, "E"), (1.49, "F"), (0.0, "F"),
    ):
        verifier(f"{valeur} -> {attendu}", svc.lettre_pour(valeur), attendu)
    verifier("pas de note -> pas de lettre", svc.lettre_pour(None), None)
    # La note de depart doit tomber dans la bande neutre, avec de la marge des
    # deux cotes : sinon tout le monde demarre a « A surveiller ».
    verifier("la note de depart est un C", svc.lettre_pour(svc.NOTE_DEPART), "C")


def test_sans_avis():
    print("\n2. Aucun avis : note de depart")
    conn = base()
    trp = ajouter_transporteur(conn, "Coupe")
    note = svc.calculer_note(conn, trp)
    verifier("valeur", note["valeur"], svc.NOTE_DEPART)
    verifier("lettre", note["lettre"], "C")
    verifier("par_defaut", note["par_defaut"], True)
    verifier("nb_avis", note["nb_avis"], 0)
    verifier("pas marquee provisoire", note["provisoire"], False)


def test_poids_thematique():
    print("\n3. Une thematique lourde pese davantage")
    conn = base()
    a = ajouter_transporteur(conn, "A")
    b = ajouter_transporteur(conn, "B")
    # Meme couple de notes, mais le 2 tombe sur une thematique de poids 2.0
    # (colis perdu) pour A et de poids 1.0 (ponctualite) pour B.
    avis(conn, a, 2, code="perte_colis")
    avis(conn, a, 10, code="ponctualite", sens="appreciation")
    avis(conn, b, 2, code="ponctualite")
    avis(conn, b, 10, code="ponctualite", sens="appreciation")
    na = svc.calculer_note(conn, a)["valeur"]
    nb = svc.calculer_note(conn, b)["valeur"]
    verifier("A (mauvais avis lourd) sous B", na < nb, True)
    # La note de depart entre dans la moyenne avec le poids d'un avis.
    verifier("B", nb, round((2 * 1 + 10 * 1 + svc.NOTE_DEPART) / 3, 2))
    verifier("A tire vers le bas", na, round((2 * 2 + 10 * 1 + svc.NOTE_DEPART) / 4, 2))
    verifier("les avis ne comptent pas la note de depart", svc.calculer_note(conn, a)["nb_avis"], 2)


def test_anciennete():
    print("\n4. Un avis ancien pese moins")
    conn = base()
    a = ajouter_transporteur(conn, "A")
    b = ajouter_transporteur(conn, "B")
    avis(conn, a, 2, jours=1000)  # poids 0.25
    avis(conn, a, 10, jours=0, sens="appreciation")
    avis(conn, b, 2, jours=0)
    avis(conn, b, 10, jours=0, sens="appreciation")
    verifier("poids d'un avis recent", svc.poids_anciennete(datetime.now()), 1.0)
    verifier(
        "poids d'un avis de 3 ans",
        svc.poids_anciennete(datetime.now() - timedelta(days=1000)),
        0.25,
    )
    verifier(
        "l'ancien incident pese moins",
        svc.calculer_note(conn, a)["valeur"] > svc.calculer_note(conn, b)["valeur"],
        True,
    )


def test_ajustement():
    print("\n5. Ajustement manuel : il s'ajoute, il n'ecrase pas")
    conn = base()
    trp = ajouter_transporteur(conn, "A")
    avis(conn, trp, 6)
    moyenne_1 = round((6 + svc.NOTE_DEPART) / 2, 2)
    verifier("moyenne seule", svc.calculer_note(conn, trp)["valeur"], moyenne_1)
    ajustement(conn, trp, 1.5)
    note = svc.calculer_note(conn, trp)
    verifier("moyenne brute inchangee", note["moyenne_brute"], moyenne_1)
    verifier("note ajustee", note["valeur"], round(moyenne_1 + 1.5, 2))
    verifier("ajustement expose", note["ajustement"], 1.5)
    # Un nouvel avis continue de faire bouger la note malgre l'ajustement.
    avis(conn, trp, 2)
    verifier(
        "un avis apres ajustement compte",
        svc.calculer_note(conn, trp)["valeur"],
        round((6 + 2 + svc.NOTE_DEPART) / 3 + 1.5, 2),
    )
    # Bornage.
    ajustement(conn, trp, 5)
    verifier(
        "ajustement borne",
        svc.calculer_note(conn, trp)["ajustement"],
        svc.AJUSTEMENT_MAX,
    )


def test_ajustement_seul():
    print("\n6. Un ajustement seul deplace la note de depart")
    conn = base()
    trp = ajouter_transporteur(conn, "A")
    ajustement(conn, trp, 3)
    note = svc.calculer_note(conn, trp)
    verifier("valeur", note["valeur"], svc.NOTE_DEPART + 3)
    verifier("toujours aucun avis", note["nb_avis"], 0)
    verifier("toujours une note de depart", note["par_defaut"], True)


def test_provisoire_et_cache():
    print("\n7. Note provisoire et mise en cache")
    conn = base()
    trp = ajouter_transporteur(conn, "A")
    verifier("0 avis = pas provisoire, mais par defaut",
             svc.calculer_note(conn, trp)["provisoire"], False)
    avis(conn, trp, 9, sens="appreciation")
    verifier("1 avis = provisoire", svc.calculer_note(conn, trp)["provisoire"], True)
    avis(conn, trp, 9, sens="appreciation")
    avis(conn, trp, 9, sens="appreciation")
    note = svc.calculer_note(conn, trp)
    verifier("3 avis = fiable", note["provisoire"], False)
    verifier("plus une note de depart", note["par_defaut"], False)
    svc.recalculer_note(conn, trp)
    ligne = conn.execute(
        "SELECT note_valeur, note_lettre, note_nb_avis FROM expe_transporteurs WHERE id=?",
        (trp,),
    ).fetchone()
    attendu = round((9 * 3 + svc.NOTE_DEPART) / 4, 2)
    verifier("cache valeur", ligne["note_valeur"], attendu)
    verifier("cache lettre", ligne["note_lettre"], svc.lettre_pour(attendu))
    verifier("cache nb", ligne["note_nb_avis"], 3)


def test_departements():
    print("\n8. Departement deduit du code postal, puis region")
    for cp, attendu in (
        ("59100", "59"), ("75011", "75"), ("20190", "2A"), ("20200", "2B"),
        ("97400", "974"), ("", ""),
    ):
        verifier(f"{cp or '(vide)'} -> {attendu or '(vide)'}", svc._norm_dept(cp), attendu)
    for dept, attendu in (
        ("59", "HDF"), ("75", "IDF"), ("2A", "COR"), ("974", "REU"), ("ZZ", ""),
    ):
        verifier(
            f"region de {dept} -> {attendu or '(vide)'}",
            reg.region_du_departement(dept),
            attendu,
        )
    couverts = sorted(d for _, depts in reg.REGIONS.values() for d in depts)
    verifier("aucun departement en double", len(couverts), len(set(couverts)))
    verifier("101 departements couverts", len(couverts), 101)


def test_recommandation():
    print("\n9. Recommandation par region")
    conn = base()
    bien = ajouter_transporteur(conn, "Bien note")
    habitue = ajouter_transporteur(conn, "Habitue mal note")
    jamais = ajouter_transporteur(conn, "Jamais utilise")
    for _ in range(3):
        avis(conn, bien, 10, sens="appreciation")
        avis(conn, habitue, 2)
    hier = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    # Deux departements DIFFERENTS de la meme region : c'est la region qui
    # regroupe l'historique, pas le departement.
    conn.execute(
        "INSERT INTO expe_departs (transporteur_id, code_postal_destination, date_enlevement)"
        " VALUES (?,?,?)",
        (bien, "75011", hier),
    )
    for _ in range(8):
        conn.execute(
            "INSERT INTO expe_departs (transporteur_id, code_postal_destination, date_enlevement)"
            " VALUES (?,?,?)",
            (habitue, "77100", hier),
        )
    svc.recalculer_toutes(conn)

    classement = svc.recommander_transporteurs(conn, "IDF")
    noms = [r["transporteur"] for r in classement]
    verifier("les trois sont classes", len(classement), 3)
    verifier(
        "les departs des deux departements comptent sur la meme region",
        sum(r["nb_expeditions"] for r in classement),
        9,
    )
    # Arbitrage assume : a 50/50, huit transports recents pesent plus qu'un
    # ecart de note. Le transporteur habituel passe donc devant.
    verifier("le volume recent l'emporte a 50/50", noms[0], "Habitue mal note")
    verifier(
        "le transporteur jamais utilise reste present",
        "Jamais utilise" in noms,
        True,
    )
    verifier(
        "et il est signale comme tel",
        [r["jamais_utilise"] for r in classement if r["transporteur"] == "Jamais utilise"][0],
        True,
    )
    verifier(
        "il porte la note de depart, pas un trou",
        [r["note_lettre"] for r in classement if r["transporteur"] == "Jamais utilise"][0],
        "C",
    )
    verifier("rangs numerotes", [r["rang"] for r in classement], [1, 2, 3])
    verifier("aucune recommandation hors region connue", svc.recommander_transporteurs(conn, "ZZZ"), [])

    carte = svc.carte_zones(conn)
    verifier("la carte ne colorie que les regions livrees", sorted(carte.keys()), ["IDF"])
    verifier("et y met le mieux classe", carte["IDF"]["transporteur"], "Habitue mal note")
    verifier("avec le total des expeditions", carte["IDF"]["nb_expeditions"], 9)
    verifier("et le nom de la region", carte["IDF"]["region_nom"], "Île-de-France")


def test_note_departage():
    print("\n10. A experience egale, la note departage")
    conn = base()
    bien = ajouter_transporteur(conn, "Bien note")
    mal = ajouter_transporteur(conn, "Mal note")
    for _ in range(3):
        avis(conn, bien, 10, sens="appreciation")
        avis(conn, mal, 2)
    hier = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    for trp in (bien, mal):
        for _ in range(4):
            conn.execute(
                "INSERT INTO expe_departs (transporteur_id, code_postal_destination,"
                " date_enlevement) VALUES (?,?,?)",
                (trp, "59000", hier),
            )
    svc.recalculer_toutes(conn)
    classement = svc.recommander_transporteurs(conn, "HDF")
    verifier("meme volume : la note decide", classement[0]["transporteur"], "Bien note")


def test_recence_des_transports():
    print("\n11. L'experience est ponderee par la recence")
    conn = base()
    ancien = ajouter_transporteur(conn, "Beaucoup mais vieux")
    recent = ajouter_transporteur(conn, "Moins mais recent")

    def depart(trp, jours):
        quand = (datetime.now() - timedelta(days=jours)).strftime("%Y-%m-%d")
        conn.execute(
            "INSERT INTO expe_departs (transporteur_id, code_postal_destination,"
            " date_enlevement) VALUES (?,?,?)",
            (trp, "33000", quand),
        )

    for _ in range(10):
        depart(ancien, 1100)   # plus de 24 mois -> 0,1 chacun, soit 1,0
    for _ in range(4):
        depart(recent, 10)     # moins de 3 mois -> 1,0 chacun, soit 4,0
    svc.recalculer_toutes(conn)

    classement = svc.recommander_transporteurs(conn, "NAQ")
    par_nom = {r["transporteur"]: r for r in classement}
    verifier("dix vieux transports pesent 1", par_nom["Beaucoup mais vieux"]["experience"], 1.0)
    verifier("quatre recents pesent 4", par_nom["Moins mais recent"]["experience"], 4.0)
    verifier(
        "le recent passe devant malgre moins de transports",
        classement[0]["transporteur"],
        "Moins mais recent",
    )
    verifier(
        "le compte brut reste affiche tel quel",
        par_nom["Beaucoup mais vieux"]["nb_expeditions"],
        10,
    )
    verifier(
        "les paliers de recence",
        [
            svc.poids_recence_transport(
                (datetime.now() - timedelta(days=j)).strftime("%Y-%m-%d"),
                datetime.now(),
            )
            for j in (10, 120, 200, 400, 900)
        ],
        [1.0, 0.75, 0.5, 0.25, 0.1],
    )


def test_resolution_ville():
    print("\n12. Ville, code postal et region")
    conn = base()
    conn.execute("INSERT INTO clients (cp, ville) VALUES ('69003','LYON')")
    conn.execute("INSERT INTO clients (cp, ville) VALUES ('59000','LILLE')")
    verifier(
        "ville connue",
        svc.resoudre_destination(conn, ville="lyon")["departement"],
        "69",
    )
    verifier(
        "et sa region",
        svc.resoudre_destination(conn, ville="lyon")["region"],
        "ARA",
    )
    verifier(
        "accents et casse",
        svc.resoudre_destination(conn, ville="Lille")["cp"],
        "59000",
    )
    verifier(
        "code postal tape dans le champ ville",
        svc.resoudre_destination(conn, ville="75011")["region"],
        "IDF",
    )
    verifier(
        "ville inconnue",
        svc.resoudre_destination(conn, ville="Zzz")["region"],
        "",
    )
    verifier(
        "suggestions",
        [s["ville"] for s in svc.chercher_villes(conn, "li")],
        ["LILLE"],
    )
    verifier(
        "les suggestions portent la region",
        [s["region"] for s in svc.chercher_villes(conn, "li")],
        ["HDF"],
    )


if __name__ == "__main__":
    test_seuils()
    test_sans_avis()
    test_poids_thematique()
    test_anciennete()
    test_ajustement()
    test_ajustement_seul()
    test_provisoire_et_cache()
    test_departements()
    test_recommandation()
    test_note_departage()
    test_recence_des_transports()
    test_resolution_ville()

    print("\n" + "=" * 60)
    if FAIL:
        print(f"{len(FAIL)} echec(s) :")
        for f in FAIL:
            print("  -", f)
        sys.exit(1)
    print("Tous les cas passent.")

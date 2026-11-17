"""
MyExpé — grilles tarifaires versionnées et lecture des fichiers de tarifs.

Ce que ce test verrouille :

- la migration rattache les tarifs existants à des grilles « reprises »,
  actives ou brouillon selon leur état, et se rejoue sans rien dupliquer ;
- activer une grille remplace les prix actifs des mêmes zones et tranches,
  et seulement eux : l'international d'une grille France reste actif ;
- archiver la grille rétablit exactement les prix qu'elle avait remplacés ;
- une grille archivée volontairement ne revient pas quand on archive la
  grille qui l'avait remplacée en partie ;
- la recherche de tarif (actif = 1) ne voit qu'une ligne par case ;
- le tableau d'une grille brouillon porte le prix actif qu'elle remplace ;
- le lecteur générique lit les en-têtes de tranches usuels, un PDF dont les
  prix d'une ligne sont fusionnés dans une seule cellule, un CSV au schéma
  MySifa et un Excel quelconque, sans appel à Claude.

Lancer : python3 tests/test_expe_grilles.py
"""

import _base_temporaire  # noqa: F401  — base jetable, avant tout le reste
import io

import database  # noqa: E402,F401  — toujours avant tout app.*
from database import get_db  # noqa: E402
from app.services import expe_grilles as G  # noqa: E402
from app.services import expe_tarif_lecture as L  # noqa: E402

ECHECS = []


def check(label, obtenu, attendu=True):
    ok = obtenu == attendu
    print(("ok   " if ok else "KO   ") + label.ljust(64)
          + ("" if ok else f"{obtenu!r}   attendu {attendu!r}"))
    if not ok:
        ECHECS.append(label)


def ligne(zone, tmin, tmax, prix, base="poids", unite="forfait", zt="departement"):
    return {"type_envoi": "messagerie", "base_calcul": base, "zone_type": zt,
            "zone_valeur": zone, "tranche_min": tmin, "tranche_max": tmax,
            "prix": prix, "unite": unite}


def actifs(conn, trp):
    return sorted(
        (r["base_calcul"], r["zone_valeur"], r["tranche_min"], r["prix"])
        for r in conn.execute(
            "SELECT * FROM expe_tarifs WHERE transporteur_id=? AND actif=1", (trp,)
        )
    )


with get_db() as conn:
    trp = conn.execute("INSERT INTO expe_transporteurs (nom, created_at, updated_at) VALUES ('Test grilles', '2026-11-17', '2026-11-17')").lastrowid
    autre = conn.execute("INSERT INTO expe_transporteurs (nom, created_at, updated_at) VALUES ('Autre', '2026-11-17', '2026-11-17')").lastrowid

    # ─── Reprise des tarifs existants ────────────────────────────────
    for z, p, act in (("01", 19.07, 1), ("59", 19.41, 1), ("Italie 00", 30.0, 1), ("62", 9.0, 0)):
        conn.execute(
            """INSERT INTO expe_tarifs (transporteur_id, type_envoi, base_calcul, zone_type,
                   zone_valeur, tranche_min, tranche_max, prix, unite, actif, source_filename)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (trp, "messagerie", "poids", "departement", z, 1, 10, p, "forfait", act, "ancien.xlsx"),
        )
    import importlib
    mig = importlib.import_module("app.core.migrations.2026_11_17_expe_tarif_grilles")
    mig.appliquer(conn)
    mig.appliquer(conn)
    gs = G.lister(conn, trp)
    check("reprise : une grille active, une brouillon", sorted(g["statut"] for g in gs), ["active", "brouillon"])
    check("reprise : rejouée sans doublon", len(gs), 2)
    check("reprise : toutes les lignes rattachées",
          conn.execute("SELECT COUNT(*) FROM expe_tarifs WHERE grille_id IS NULL").fetchone()[0], 0)
    ancienne = next(g for g in gs if g["statut"] == "active")
    conn.execute("DELETE FROM expe_tarifs WHERE grille_id = ?",
                 (next(g["id"] for g in gs if g["statut"] == "brouillon"),))
    conn.execute("DELETE FROM expe_tarif_grilles WHERE statut = 'brouillon'")

    # ─── Import d'une grille France ──────────────────────────────────
    ids = G.creer_brouillons(
        conn, trp,
        [ligne("01", 1, 10, 20.21), ligne("59", 1, 10, 20.57), ligne("75", 1, 10, 25.0),
         ligne("01", 1, 1, 100.0, base="palette"), ligne("01", 1, 10, 20.21)],
        source_filename="tarif 2027.pdf", methode="pdf_tableau", email="t@x", date_effet="2026-12-01",
    )
    check("import : une grille par base de calcul", len(ids), 2)
    poids = next(i for i in ids if conn.execute(
        "SELECT base_calcul FROM expe_tarif_grilles WHERE id=?", (i,)).fetchone()[0] == "poids")
    palette = next(i for i in ids if i != poids)
    check("import : doublon de cellule fusionné",
          conn.execute("SELECT COUNT(*) FROM expe_tarifs WHERE grille_id=?", (poids,)).fetchone()[0], 3)
    check("import : rien d'actif avant validation", actifs(conn, trp), [
        ("poids", "01", 1.0, 19.07), ("poids", "59", 1.0, 19.41), ("poids", "Italie 00", 1.0, 30.0)])

    comp = G.comparaison(conn, poids)
    check("comparaison : deux prix comparés", comp["cellules_comparees"], 2)
    check("comparaison : écart moyen ≈ +6 %", round(comp["ecart_moyen_pct"]), 6)
    check("comparaison : une zone nouvelle (75)", comp["zones_nouvelles"], 1)

    m = G.matrice(conn, trp, poids)
    z01 = next(z for z in m["zones"] if z["zone_valeur"] == "01")
    check("matrice : prix et prix actif remplacé", (z01["prix"], z01["ancien"]), ([20.21], [19.07]))
    check("matrice : recherche par département", [z["zone_valeur"] for z in G.matrice(conn, trp, poids, "59")["zones"]], ["59"])
    check("matrice : libellé de tranche", m["tranches"][0]["libelle"], "1 – 10 kg")

    # ─── Activation ──────────────────────────────────────────────────
    res = G.activer(conn, trp, poids, "t@x")
    check("activation : 3 activés, 2 remplacés", (res["activees"], res["remplacees"]), (3, 2))
    check("activation : international intact, nouveaux prix en place", actifs(conn, trp), [
        ("poids", "01", 1.0, 20.21), ("poids", "59", 1.0, 20.57), ("poids", "75", 1.0, 25.0),
        ("poids", "Italie 00", 1.0, 30.0)])
    check("activation : l'ancienne grille reste active (international)",
          conn.execute("SELECT statut FROM expe_tarif_grilles WHERE id=?", (ancienne["id"],)).fetchone()[0], "active")
    check("activation : une seule ligne active par case",
          conn.execute("""SELECT MAX(n) FROM (SELECT COUNT(*) n FROM expe_tarifs WHERE actif=1
                            GROUP BY transporteur_id, base_calcul, zone_valeur, tranche_min)""").fetchone()[0], 1)
    check("activation : brouillon palette toujours inactif",
          conn.execute("SELECT COUNT(*) FROM expe_tarifs WHERE grille_id=? AND actif=1", (palette,)).fetchone()[0], 0)
    try:
        G.activer(conn, trp, poids, "t@x")
        check("activation : refusée deux fois", False)
    except G.GrilleErreur:
        check("activation : refusée deux fois", True)

    # ─── Archivage = retour arrière ──────────────────────────────────
    res = G.archiver(conn, trp, poids)
    check("archivage : 3 retirés, 2 rétablis", (res["retirees"], res["retablies"]), (3, 2))
    check("archivage : retour exact aux anciens prix", actifs(conn, trp), [
        ("poids", "01", 1.0, 19.07), ("poids", "59", 1.0, 19.41), ("poids", "Italie 00", 1.0, 30.0)])

    # Réactivation, puis l'ancienne est archivée volontairement : elle ne
    # doit pas revenir quand on archive ensuite la plus récente.
    G.activer(conn, trp, poids, "t@x")
    G.archiver(conn, trp, ancienne["id"])
    check("ancienne archivée : seul le récent reste", actifs(conn, trp), [
        ("poids", "01", 1.0, 20.21), ("poids", "59", 1.0, 20.57), ("poids", "75", 1.0, 25.0)])
    G.archiver(conn, trp, poids)
    check("archiver le récent ne ressuscite pas l'ancienne", actifs(conn, trp), [])

    # ─── Suppression ─────────────────────────────────────────────────
    try:
        G.activer(conn, trp, poids, "t@x")
        G.supprimer(conn, trp, poids)
        check("suppression d'une grille active refusée", False)
    except G.GrilleErreur:
        check("suppression d'une grille active refusée", True)
    n = G.supprimer(conn, trp, palette)
    check("suppression d'un brouillon et de ses lignes", n, 1)
    check("autre transporteur intact", G.lister(conn, autre), [])
    try:
        G.matrice(conn, autre, poids)
        check("grille d'un autre transporteur inaccessible", False)
    except G.GrilleErreur:
        check("grille d'un autre transporteur inaccessible", True)
    conn.rollback()


# ─── Lecture des fichiers ────────────────────────────────────────────

def tr(txt):
    t = L.lire_tranche(txt)
    return None if t is None else (t["min"], t["max"], t["base"])


check("tranche « De 1 à\\n10 kg »", tr("De 1 à\n10 kg"), (1.0, 10.0, "poids"))
check("tranche « 101 - 200 »", tr("101 - 200"), (101.0, 200.0, None))
check("tranche « 1 PAL »", tr("1 PAL"), (1, 1, "palette"))
check("tranche « + de 2000 kg »", tr("+ de 2000 kg"), (2001.0, None, "poids"))
check("tranche « 1 à 2 t » en kg", tr("1 à 2 t"), (1000.0, 2000.0, "poids"))
check("pas de tranche dans une date", tr("01.12.2026"), None)
check("pas de tranche dans « Département »", tr("Département"), None)

check("zone « France 01 »", L.lire_zone("France 01"), ("departement", "01"))
check("zone « (59) NORD »", L.lire_zone("(59) NORD"), ("departement", "59"))
check("zone « 2A »", L.lire_zone("2A"), ("departement", "2A"))
check("zone code postal", L.lire_zone("59200"), ("code_postal", "59200"))
check("zone pays", L.lire_zone("Italie 00"), ("pays", "Italie 00"))
check("ligne « Minimum » ignorée", L.lire_zone("Minimum de perception"), None)

# Tableau PDF façon CEVA : prix d'une ligne fusionnés dans la 1re cellule.
table = [
    [None, None, "TARIF CLIENT", None, None],
    [None, None, "FORFAIT (en EUROS HT)", None, "PRIX AU 100KG (en EUROS HT)"],
    ["Pays", "Département", "De 1 à\n10 kg", "De 11 à\n100 kg", "De 101 à\n200 kg"],
    ["France", "01", "20,21 21,47 39,5", None, None],
    ["France", "59", "20,57 19,98 20,19", None, None],
    ["France", "62", "1 2", None, None],
]
lg, av = L.lignes_depuis_tableau(table)
check("tableau PDF : 2 zones × 3 tranches", len(lg), 6)
check("tableau PDF : unité forfait puis au 100 kg",
      [l["unite"] for l in lg if l["zone_valeur"] == "01"], ["forfait", "forfait", "au_100kg"])
check("tableau PDF : ligne incomplète signalée", len(av), 1)

csv_mysifa = ("type_envoi,base_calcul,zone_type,zone_valeur,tranche_min,tranche_max,prix,unite\n"
              "messagerie,poids,departement,01,1,10,20.21,forfait\n").encode()
r = L.lire(csv_mysifa, "grille.csv", ia=False)
check("CSV MySifa lu tel quel", (r["methode"], len(r["lignes"])), ("csv", 1))

import openpyxl  # noqa: E402

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Grille"
ws.append(["Tarif applicable au 01/01/2027"])
ws.append(["Département", "1 palette", "2 palettes", "3 palettes"])
ws.append(["(59) NORD", 51, 77, 102])
ws.append(["(62) PAS-DE-CALAIS", 56, 83, 110])
buf = io.BytesIO()
wb.save(buf)
r = L.lire(buf.getvalue(), "transporteur.xlsx", ia=False)
check("Excel quelconque : lecteur générique", r["methode"], "excel_tableau")
check("Excel quelconque : 6 prix à la palette",
      sorted((l["zone_valeur"], l["tranche_min"], l["prix"]) for l in r["lignes"])[:3],
      [("59", 1.0, 51.0), ("59", 2.0, 77.0), ("59", 3.0, 102.0)])
check("Excel quelconque : date d'effet", r["date_effet"], "2027-01-01")

try:
    L.lire(b"%PDF-1.4 vide", "vide.pdf", ia=False)
    check("PDF sans grille : erreur lisible", False)
except L.LectureErreur:
    check("PDF sans grille : erreur lisible", True)
try:
    L.lire(b"x", "tarif.docx", ia=False)
    check("format refusé", False)
except L.LectureErreur as e:
    check("format refusé", "non pris en charge" in str(e))

compact = {"grilles": [{"type_envoi": "messagerie", "base_calcul": "poids",
                        "tranches": [{"min": 1, "max": 10, "unite": "forfait"}, {"min": 11, "max": 20, "unite": "forfait"}],
                        "zones": [{"zone_type": "departement", "zone": "1", "prix": [20.0, None]},
                                  {"zone_type": "departement", "zone": "59", "prix": [1.0]}]}]}
lg = L.deplier_grilles_ia(compact)
check("réponse IA compacte dépliée (zone normalisée, case vide, ligne bancale)",
      [(l["zone_valeur"], l["tranche_min"]) for l in lg], [("01", 1)])

print()
if ECHECS:
    print(f"{len(ECHECS)} echec(s)")
    raise SystemExit(1)
print("tout passe")

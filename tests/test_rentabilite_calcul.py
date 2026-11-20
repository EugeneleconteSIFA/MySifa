"""
Moteur de rentabilité et chiffrage des devis.

Ce que ce test garde :

1. Le moteur reproduit le classeur. Les postes ci-dessous sont ceux lus dans
   quatre vrais devis (80×40, 149×55, 148×210 Rotoflex, 45×130) : marge brute,
   coût horaire, prix de revient, PV et coût matière recalculés doivent
   retomber sur les cellules du classeur.
2. Le temps n'entre pas dans la marge brute — seulement dans le coût horaire.
3. Une fourchette se propage en pire cas, et le verdict ne tombe que quand
   toute la fourchette est du même côté du seuil.
4. Les cascades tombent exactement sur le réel.
5. Le prorata d'un marché ne change ni le MB % ni le coût horaire.
6. Les paramètres se lisent, se valident et s'écrivent ; le chiffrage fait
   l'aller-retour en base.

Lancer : python3 tests/test_rentabilite_calcul.py
"""

import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)

db = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["DB_PATH"] = db
import config; config.DB_PATH = db                      # noqa: E402,E702
import database                                          # noqa: E402,F401
import app.core.database as dbmod                        # noqa: E402
dbmod.DB_PATH = db
with contextlib.redirect_stdout(io.StringIO()):
    dbmod.init_db()

from database import get_db                              # noqa: E402
from app.services import devis_chiffrage, rentabilite_parametres  # noqa: E402
from app.services.rentabilite_calcul import (            # noqa: E402
    EntreesReelles, Fourchette, LIMITE, REUSSI, SOUS_SEUIL,
    calcul_devis, calcul_reel, cascade_cout_horaire, cascade_marge,
    controler_devis, croiser_surfaces, redevise_laize, sensibilite, verdict,
)

FAIL = []


def check(nom, cond, detail=""):
    if cond:
        print(f"  ok  {nom}")
    else:
        print(f"  KO  {nom} {detail}")
        FAIL.append(nom)


def proche(a, b, tol=0.01):
    return a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(b))


# Postes lus par `lire_chiffrage` dans les classeurs fournis le 20/11/2026.
DEVIS = {
    "80x40 bicolor": (510, dict(
        prix_m2_corrige=0.931, prix_m2_base=0.35, cout_matiere=47052.3985, cout_encre=0,
        cout_cliche=0, cout_outil=69.0, cout_emballage=921.3213, cout_production=8946.72,
        cout_conditionnement=0, cout_manutention=0, cout_transport=450.0,
        prix_revient=57439.4398, remise=0, surmarge=23550.1703, surmarge_taux=0.41,
        prix_vente=80989.6101, marge_brute=32496.8903, cout_horaire=1307.6167,
        taux_horaire=360.0, temps_total_mn=1491.12, metrage_total_ml=99097.32)),
    "149x55 protégé": (470, dict(
        prix_m2_corrige=0.27607, prix_m2_base=0.35, cout_matiere=15669.1634, cout_encre=0,
        cout_cliche=0, cout_outil=67.9363, cout_emballage=249.4131, cout_production=10715.2299,
        cout_conditionnement=0, cout_manutention=0, cout_transport=540.0,
        prix_revient=27241.7427, remise=0, surmarge=1607.2628, surmarge_taux=0.059,
        prix_vente=28849.0055, marge_brute=12322.4927, cout_horaire=413.9993,
        taux_horaire=360.0, temps_total_mn=1785.8716, metrage_total_ml=120761.5662)),
    "148x210 Rotoflex": (306, dict(
        prix_m2_corrige=0.416, prix_m2_base=0.275, cout_matiere=21669.7572, cout_encre=0,
        cout_cliche=0, cout_outil=132.1429, cout_emballage=555.3093, cout_production=7816.4583,
        cout_conditionnement=0, cout_manutention=0, cout_transport=712.0,
        prix_revient=30885.6676, remise=0, surmarge=23442.2217, surmarge_taux=0.759,
        prix_vente=54327.8894, marge_brute=31258.6801, cout_horaire=679.8444,
        taux_horaire=170.0, temps_total_mn=2758.75, metrage_total_ml=170231.25)),
    "45x130 Hermes": (500, dict(
        prix_m2_corrige=1.285, prix_m2_base=0.275, cout_matiere=13249.0, cout_encre=0,
        cout_cliche=0, cout_outil=33.2014, cout_emballage=562.4517, cout_production=2540.4908,
        cout_conditionnement=0, cout_manutention=0, cout_transport=9000.0,
        prix_revient=25385.1439, remise=0, surmarge=14215.6806, surmarge_taux=0.56,
        prix_vente=39600.8245, marge_brute=16756.1713, cout_horaire=2374.4317,
        taux_horaire=360.0, temps_total_mn=423.4151, metrage_total_ml=20621.0117)),
}

print("1. Le moteur reproduit le classeur")
for nom, (laize, v) in DEVIS.items():
    controles = controler_devis(v, laize, tolerance_pct=0.5)
    faux = [c for c in controles if not c["ok"]]
    check(f"{nom} : {len(controles)} contrôles justes", len(controles) >= 5 and not faux,
          str(faux))
    calc = calcul_devis(v)
    check(f"{nom} : MB % du classeur", proche(calc["mb_pct"], v["marge_brute"] / v["prix_vente"] * 100))

print("2. Le temps n'entre pas dans la marge brute")
v = dict(DEVIS["80x40 bicolor"][1])
mb_avant = calcul_devis(v)["marge_brute"]
v["temps_total_mn"] *= 1.5
check("MB inchangée quand le temps augmente", proche(calcul_devis(v)["marge_brute"], mb_avant))
check("coût horaire baisse d'un tiers", proche(calcul_devis(v)["cout_horaire"], 1307.6167 / 1.5))

print("3. Contrôle : un poste mal lu est signalé")
v = dict(DEVIS["149x55 protégé"][1])
v["marge_brute"] = 9999.0
faux = [c["controle"] for c in controler_devis(v, 470, 1.0) if not c["ok"]]
check("marge brute fausse détectée", any("Marge brute" in f for f in faux), str(faux))
check("contrôle omis si une entrée manque",
      not any("matière" in c["controle"] for c in controler_devis(DEVIS["149x55 protégé"][1], None, 1.0)))

print("4. Fourchettes")
a, b = Fourchette(9, 10, 11), Fourchette(1, 2, 3)
d = a - b
check("soustraire élargit", (d.bas, d.probable, d.haut) == (6, 8, 10))
q = Fourchette(100, 120, 140).divise_par(Fourchette(10, 12, 20))
check("division en pire cas", (round(q.bas, 2), q.probable, q.haut) == (5.0, 10.0, 14.0))
check("relative ±1 %", Fourchette.relative(200, 1).dict() == {"bas": 198, "probable": 200, "haut": 202})

print("5. Croisement compteur / MyStock")
f, statut, ecart = croiser_surfaces(Fourchette.relative(63189, 1), Fourchette.relative(62800, 1), 2)
check("cohérent : recouvrement plus étroit que chaque mesure",
      statut == "coherent" and f.largeur() < Fourchette.relative(63189, 1).largeur(), statut)
f, statut, ecart = croiser_surfaces(Fourchette.relative(63189, 1), Fourchette.relative(58000, 1), 2)
check("incohérent au-delà de 2 % : union", statut == "incoherent" and f.bas < 58000 and f.haut > 63189)
f, statut, _ = croiser_surfaces(None, Fourchette.relative(50000, 1), 2)
check("une seule source", statut == "mystock_seul" and f.probable == 50000)

print("6. Exemple de la proposition : 149×55 produit en laize 510")
devis = DEVIS["149x55 protégé"][1]
reel = EntreesReelles(
    prix_vente=28849.0,
    surface_m2=Fourchette.relative(123900 * 0.510, 1),
    prix_m2=0.2795,
    couts_annexes={"outil": Fourchette.exacte(68), "emballage": Fourchette.exacte(268),
                   "transport": Fourchette.exacte(612)},
    duree_mn=Fourchette.relative(205 + 1960 + 110, 3),
    calage_mn=205, production_mn=1960, arret_mn=110, frontiere_mn=20,
)
r = calcul_reel(reel)
check("MB probable 10 240 €", proche(r["marge_brute"]["probable"], 10240, 0.001), r["marge_brute"])
check("MB % entre 34,9 et 36,1", proche(r["mb_pct"]["bas"], 34.9, 0.003) and proche(r["mb_pct"]["haut"], 36.1, 0.003), r["mb_pct"])
check("coût horaire entre 258 et 283", proche(r["cout_horaire"]["bas"], 258, 0.005) and proche(r["cout_horaire"]["haut"], 283, 0.005), r["cout_horaire"])
vd = verdict(r["mb_pct"], r["cout_horaire"], 40, 325)
check("sous les deux seuils", vd == {"global": SOUS_SEUIL, "marge": SOUS_SEUIL, "cout_horaire": SOUS_SEUIL}, vd)
check("re-devisé en laize 510 : 30 261 €", proche(redevise_laize(devis, 470, 510), 30261, 0.0005))

print("7. Verdict sur fourchette")
check("à cheval = limite", verdict({"bas": 38, "probable": 40, "haut": 42}, {"bas": 500, "probable": 600, "haut": 700}, 40, 325)["global"] == LIMITE)
check("tout au-dessus = réussi", verdict({"bas": 41, "probable": 42, "haut": 43}, {"bas": 400, "probable": 450, "haut": 500}, 40, 325)["global"] == REUSSI)
check("un seul indicateur sous le seuil suffit", verdict({"bas": 45, "probable": 46, "haut": 47}, {"bas": 200, "probable": 250, "haut": 300}, 40, 325)["global"] == SOUS_SEUIL)

print("8. Cascades")
cm = cascade_marge(devis, 470, reel, 510)
somme = sum(e["valeur"] for e in cm if e["nature"] != "total")
check("cascade marge : départ = MB devisée", proche(cm[0]["valeur"], 12322.49, 0.0001))
check("cascade marge : arrivée = MB réelle", proche(cm[-1]["valeur"], r["marge_brute"]["probable"], 0.0001))
check("cascade marge : les marches s'additionnent", proche(cm[0]["valeur"] + somme, cm[-1]["valeur"], 0.0005), cm)
check("cascade marge : la laize coûte 1 334 €", any(e["cause"] == "Laize" and proche(e["valeur"], -1334, 0.002) for e in cm), cm)
ce = cascade_cout_horaire(devis, 150, reel)
somme = sum(e["valeur"] for e in ce if e["nature"] != "total")
check("cascade €/h : arrivée = coût horaire réel", proche(ce[-1]["valeur"], r["cout_horaire"]["probable"], 0.002), ce)
check("cascade €/h : les marches s'additionnent", proche(ce[0]["valeur"] + somme, ce[-1]["valeur"], 0.002), ce)
cal = next(e for e in ce if e["cause"] == "Calage")
check("calage porte une fourchette (frontière ± 20 mn)", cal["fourchette"][0] < cal["valeur"] <= cal["fourchette"][1] or cal["fourchette"][0] <= cal["valeur"] < cal["fourchette"][1], cal)

print("9. Prorata d'un marché")
reel_tiers = EntreesReelles(
    prix_vente=28849.0 / 3, surface_m2=reel.surface_m2, prix_m2=reel.prix_m2,
    couts_annexes=reel.couts_annexes, duree_mn=reel.duree_mn,
    calage_mn=205, production_mn=1960, arret_mn=110, prorata=1 / 3,
)
r3 = calcul_reel(reel_tiers)
check("MB % identique au tiers facturé", proche(r3["mb_pct"]["probable"], r["mb_pct"]["probable"], 0.0001))
check("coût horaire identique", proche(r3["cout_horaire"]["probable"], r["cout_horaire"]["probable"], 0.0001))
check("MB en euros = un tiers", proche(r3["marge_brute"]["probable"], r["marge_brute"]["probable"] / 3, 0.0001))
check("MB pleine échelle = MB totale", proche(r3["marge_brute_pleine"]["probable"], r["marge_brute"]["probable"], 0.0001))

print("9 bis. Sensibilité du devis 80×40 (avant production)")
socle_80 = {"laize": 510, "gache": 0.05, "vitesse_theorique": 70,
            "metrage_production_ml": 93878.4, "temps_production_mn": 1341.12}
sens = {l["cle"]: l for l in sensibilite(DEVIS["80x40 bicolor"][1], socle_80, 40, 325)}
check("laize 530 : MB 37,8 %, sous le seuil", proche(sens["laize"]["mb_pct"], 37.85, 0.002) and sens["laize"]["sous_seuil_mb"], sens["laize"])
check("prix matière +5 % : 37,2 %", proche(sens["prix"]["mb_pct"], 37.22, 0.002), sens["prix"])
check("gâche 8 % : 38,5 %", proche(sens["gache"]["mb_pct"], 38.47, 0.002), sens["gache"])
check("vitesse 60 : MB inchangée, 1 137 €/h", proche(sens["vitesse"]["mb_pct"], 40.12, 0.001)
      and proche(sens["vitesse"]["cout_horaire"], 1137, 0.003), sens["vitesse"])
check("libellé lisible", sens["laize"]["detail"] == "530 au lieu de 510 mm", sens["laize"]["detail"])

print("10. Paramètres et chiffrage en base")
with get_db() as conn:
    p = rentabilite_parametres.lire(conn)
    check("325 €/h par défaut", p["seuil_cout_horaire"] == 325.0, p)
    check("40 % par défaut", p["seuil_mb_pct"] == 40.0)
    rentabilite_parametres.ecrire(conn, "seuil_cout_horaire", "340,5", "test@sifa")
    conn.commit()
    check("écriture avec virgule", rentabilite_parametres.lire(conn)["seuil_cout_horaire"] == 340.5)
    try:
        rentabilite_parametres.ecrire(conn, "seuil_mb_pct", 140, "test@sifa")
        check("hors bornes refusé", False)
    except ValueError as e:
        check("hors bornes refusé, message actionnable", "entre 0 et 100" in str(e), str(e))
    conn.execute("INSERT INTO devis (id, filename, imported_at) VALUES (1, 'x.xlsx', '2026-11-20')")
    lecture = {"valeurs": {**{c: None for c in devis_chiffrage.CHAMPS_CHIFFRAGE},
                           **DEVIS["80x40 bicolor"][1], "num_matiere": "274"},
               "sources": {"cout_matiere": "Prix!J4"}, "erreurs": []}
    check("chiffrage enregistré", devis_chiffrage.enregistrer(conn, 1, lecture))
    conn.commit()
    ch = devis_chiffrage.chiffrage_du_devis(conn, 1)
    check("aller-retour : prix de vente", proche(ch["valeurs"]["prix_vente"], 80989.6101, 1e-6))
    check("aller-retour : source conservée", ch["sources"].get("cout_matiere") == "Prix!J4")
    check("aller-retour : n° matière en texte", ch["valeurs"]["num_matiere"] == "274")

print("11. Classeur → fichier conservé → routes")
import openpyxl                                          # noqa: E402
from unittest.mock import patch                          # noqa: E402
from fastapi import FastAPI                              # noqa: E402
from fastapi.testclient import TestClient                # noqa: E402

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Prix"
# Libellés et valeurs aux places du modèle 80×40 (valeurs en cache seulement).
cellules = {
    "I4": "COUT MATIERE + Frais annexe Fournisseur", "J4": 47052.3985,
    "I5": "COUT ENCRE", "J5": 0, "I6": "COUT CLICHE inclus", "J6": 0,
    "I7": "COUT OUTIL inclus", "J7": 69, "I8": "COUT EMBALLAGE + MANDRIN", "J8": 921.3213,
    "I9": "COUT Production", "J9": 8946.72, "I10": "COUT CONDITIONNEMENT", "J10": 0,
    "I11": "COUT MANUTENTION", "J11": 0, "L11": "surmarge s/ dossier", "L12": 0.41,
    "I12": "COUT TRANSPORT", "J12": 450, "I13": "Prix normal de vente", "J13": 57439.4398,
    "I15": "Remise", "J15": 0, "I16": "Surmarge", "J16": 23550.1703,
    "A17": "MATIERE N°", "B17": 274, "I17": "Budget", "J17": 80989.6101,
    "I18": "Marge brute réelle", "J18": 32496.8903, "L18": "Cout Horaire", "L19": 1307.6167,
    "A19": "PRIX AU M2", "B19": 0.35, "A20": "Prix au M² mise à jour",
    "D20": "Prix corrigé", "E20": 0.931,
    "I31": "S/TOTAL", "J31": 1491.12, "L31": 99097.32,
    "A44": "COUT KDO/HEURE", "B44": 360,
}
for c, v in cellules.items():
    ws[c] = v
dossier = tempfile.mkdtemp()
chemin = os.path.join(dossier, "80x40 test.xlsx")
wb.save(chemin)

lecture = devis_chiffrage.lire_chiffrage(open(chemin, "rb").read(), chemin)
check("classeur généré : 22 postes lus",
      sum(1 for v in lecture["valeurs"].values() if v is not None) == 22, lecture)
check("« Prix au M² mise à jour » n'est pas pris pour le prix au m²",
      lecture["valeurs"]["prix_m2_base"] == 0.35)
check("taux machine lu en B44", lecture["sources"].get("taux_horaire") == "Prix!B44")

with get_db() as conn:
    conn.execute("INSERT INTO devis (id, filename, laize, imported_at, fichier_chemin) "
                 "VALUES (2, '80x40 test.xlsx', 510, '2026-11-20', ?)", (chemin,))
    conn.commit()

from app.routers.rentabilite import router as rent_router  # noqa: E402
appli = FastAPI()
appli.include_router(rent_router)
cli = TestClient(appli, raise_server_exceptions=True)
USER = {"id": 1, "nom": "Test", "email": "test@sifa", "role": "direction"}
with patch("app.routers.rentabilite.get_current_user", return_value=dict(USER)):
    rep = cli.get("/api/rentabilite/devis/2/chiffrage").json()
    check("route chiffrage : lu depuis le fichier conservé",
          rep.get("chiffrage") and proche(rep["chiffrage"]["prix_vente"], 80989.61, 1e-6), rep)
    check("route chiffrage : contrôle juste", rep.get("controle_ok") is True, rep.get("controles"))
    check("route chiffrage : seuil courant (340,5)", rep["seuils"]["cout_horaire"] == 340.5)
    check("route chiffrage : sensibilité sans gâche ni vitesse inventées",
          [l["cle"] for l in rep.get("sensibilite") or []] == ["laize", "prix"], rep.get("sensibilite"))
    with get_db() as conn:
        conn.execute("INSERT INTO devis_indicateurs (devis_id, libelle, valeur_nombre, source) "
                     "VALUES (2, 'Laize mini', 511, 'Prix!B11')")
        conn.commit()
    rep = cli.get("/api/rentabilite/devis/2/chiffrage").json()
    check("alerte : laize de production sous la laize mini",
          any("laize mini 511" in a["message"] for a in rep.get("alertes") or []), rep.get("alertes"))
    rep = cli.post("/api/rentabilite/devis/2/chiffrage/relire")
    check("route relire : 200", rep.status_code == 200, rep.text)
    rep = cli.put("/api/rentabilite/parametres", json={"seuil_cout_horaire": 325})
    check("route paramètres : écriture", rep.status_code == 200
          and any(p["cle"] == "seuil_cout_horaire" and p["valeur"] == 325 for p in rep.json()["parametres"]))
    rep = cli.put("/api/rentabilite/parametres", json={"seuil_mb_pct": "abc"})
    check("route paramètres : 400 sur valeur invalide", rep.status_code == 400, rep.text)
    rep = cli.get("/api/rentabilite/devis/999/chiffrage")
    check("route chiffrage : 404 sur devis inconnu", rep.status_code == 404)
with patch("app.routers.rentabilite.get_current_user", return_value={**USER, "role": "fabrication"}):
    check("route paramètres : réservée", cli.get("/api/rentabilite/parametres").status_code == 403)

print("12. Quantité de fichier multiple exacte de celle des calculs")
from app.services.devis_extraction import multiple_exact      # noqa: E402
check("4 320 000 = 2 × 2 160 000", multiple_exact(4320000, 2160000))
check("3 × aussi", multiple_exact(300000, 900000))
check("1,5 × non", not multiple_exact(3000000, 2000000))
check("égal non (pas un multiple ≥ 2)", not multiple_exact(1000, 1000))
coh = json.dumps([{"niveau": "avertissement", "champs": ["qte_etiquettes"],
                   "court": "Fichier : 4 320 000 ex · calculs : 2 160 000 ex",
                   "message": "Le nom du fichier annonce 4 320 000 ex, qui est bien un palier du devis."},
                  {"niveau": "info", "champs": ["qte_etiquettes"], "message": "La quantité des calculs ne figure dans aucun palier."}],
                 ensure_ascii=False)
with get_db() as conn:
    conn.execute(
        """INSERT INTO devis (id, filename, laize, qte_etiquettes, imported_at, a_verifier, note, coherence_json,
               fichier_chemin) VALUES (3, '100x148 mm thermique qté 4.320.000 19-11-2026.xlsx', 530, 2160000,
               '2026-11-20', 1, 'Fichier : 4 320 000 ex · calculs : 2 160 000 ex · non lu : Vitesse devisée', ?, ?)""",
        (coh, chemin))
    conn.commit()
with patch("app.routers.rentabilite.get_current_user", return_value=dict(USER)):
    rep = cli.get("/api/rentabilite/devis/3/chiffrage").json()
msgs = [x["message"] for x in rep.get("alertes") or []]
check("Schisler : aucune alerte de quantité", not any("4 320 000" in m or "calculs" in m for m in msgs), msgs)
check("les autres raisons de la note restent, une fois", msgs.count("Non lu : Vitesse devisée") == 1, msgs)
import importlib                                          # noqa: E402
mig = importlib.import_module("app.core.migrations.2026_11_20_devis_quantite_multiple")
with get_db() as conn:
    with contextlib.redirect_stdout(io.StringIO()):
        mig.appliquer(conn)
    r = conn.execute("SELECT a_verifier, note, coherence_json FROM devis WHERE id=3").fetchone()
check("migration : note réduite à l'autre raison", r["note"] == "non lu : Vitesse devisée" and r["a_verifier"] == 1, dict(r))
check("migration : alerte de quantité retirée", "4 320 000" not in r["coherence_json"], r["coherence_json"])

import shutil                                            # noqa: E402
shutil.rmtree(dossier, ignore_errors=True)
os.unlink(db)
print()
if FAIL:
    print(f"{len(FAIL)} échec(s) : {FAIL}")
    sys.exit(1)
print("Tous les tests passent.")

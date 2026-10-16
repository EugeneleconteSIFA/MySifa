"""
Rattachement automatique devis ↔ planning.

Ce que ce test garde :
- papier et colle, lus dans le nom du fichier du devis et dans l'OF, départagent
  deux devis au même format ;
- un papier contraire (vélin contre thermique) empêche la proposition ;
- deux versions d'un même devis ne bloquent plus le rattachement : la plus
  récente antérieure à la production l'emporte ;
- deux devis différents également plausibles : aucune proposition ;
- un couple rejeté n'est jamais reproposé, même après relance du moteur ;
- une liaison décidée par quelqu'un n'est jamais touchée.

Lancer : python3 tests/test_devis_rapprochement.py
"""

import contextlib
import io
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
from app.services.devis_rapprochement import (           # noqa: E402
    caracteristiques_devis, caracteristiques_entree, evaluer, meilleur_devis,
    signature_produit, vocabulaire,
)

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(64) + f"{got}"
          + ("" if ok else f"   (attendu {expected})"))
    if not ok:
        FAIL.append(label)


MATIERES = ["THERMIQUE ECO", "THERMIQUE ECO", "THERMIQUE PRO", "THERMIQUE PRO",
            "VELIN ETIWELL", "VELIN H400", "Couché", "Couché Perm", "PP 95µ BLANC MAT",
            "PP100 MAT"]
ADHESIFS = ["Permanent 2028Y - 19", "Permanent", "Enlevable 1408 -22", "Enlevable",
            "Congélation 1340 - 22", "Congélation 2030-30"]
VOC = vocabulaire(MATIERES, ADHESIFS)

print("\n1. Vocabulaire tiré des OF")
check("familles", sorted(VOC["familles"]), ["couche", "pp", "thermique", "velin"])
check("types de colle", sorted(VOC["colles"]), ["congelation", "enlevable", "permanent"])

print("\n2. Lecture du nom de fichier")
cd = caracteristiques_devis(
    {"filename": "50x60 mm thermique pro permanent M76 B5000 3.705.000 12-10-2026.xlsx"}, VOC)
check("famille", cd["famille"], "thermique")
check("qualificatif", cd["qualificatif"], "pro")
check("colle", cd["colles"], ["permanent"])
cd = caracteristiques_devis(
    {"filename": "75x52 mm Thermique protégé congélation 22g M76 qté 12.000.000.xlsx"}, VOC)
check("« protégé » reconnu comme qualificatif", cd["qualificatif"], "protege")
check("congélation", cd["colles"], ["congelation"])
ce = caracteristiques_entree({"matiere": "VELIN Enlevable R400", "adhesif": None}, VOC)
check("colle lue dans la matière quand l'adhésif manque", ce["colle"], "enlevable")
check("signature sans date ni quantité",
      signature_produit("100x149mm thermique éco 1408 B1200 M76 3.600.000 05-10-2026.xlsx")
      == signature_produit("100x149mm thermique éco 1408 B1200 M76 2.900.000 06-10-2026.xlsx"),
      True)

ENTREE = {"id": 1, "client": "GRAND FRAIS", "format_l": 50, "format_h": 60, "laize": 470,
          "planned_start": "2026-10-20", "matiere": "THERMIQUE PRO",
          "adhesif": "Permanent 2028Y - 19"}


def devis(i, fichier, **k):
    d = {"id": i, "filename": fichier, "client": "Grand Frais", "format_h": 60,
         "format_v": 50, "laize": 470, "date_devis": "2026-10-12"}
    d.update(k)
    return d


print("\n3. Papier et colle départagent deux devis au même format")
bon = devis(10, "50x60 mm thermique pro permanent M76 B5000 3.705.000 12-10-2026.xlsx")
mauvais = devis(11, "50x60 mm thermique eco enlevable M76 B5000 3.705.000 12-10-2026.xlsx")
p = meilleur_devis([bon, mauvais], ENTREE, VOC)
check("le devis au bon papier et à la bonne colle", p and p["devis_id"], 10)
check("motif cite papier et colle",
      bool(p and "papier thermique pro" in p["motif"] and "colle permanent" in p["motif"]), True)

print("\n3 bis. Validation automatique")
check("format, laize, client et matière identiques : validé d'office",
      bool(p and p.get("identique")), True)
autre_client = devis(14, "50x60 mm thermique pro permanent 12-10-2026.xlsx", client="Bricorama")
p2 = meilleur_devis([autre_client], ENTREE, VOC)
check("client différent : proposé mais pas validé", (bool(p2), bool(p2 and p2.get("identique"))),
      (True, False))
sans_qualif = devis(15, "50x60 mm thermique permanent 12-10-2026.xlsx")
p3 = meilleur_devis([sans_qualif], ENTREE, VOC)
check("matière incomplète (thermique sans « pro ») : pas validé",
      bool(p3 and p3.get("identique")), False)

print("\n4. Papier contraire")
velin = devis(12, "50x60 velin permanent 12-10-2026.xlsx")
check("vélin contre thermique : pas de proposition", meilleur_devis([velin], ENTREE, VOC), None)
check("score inférieur au même devis sans papier lisible",
      evaluer(velin, ENTREE, VOC)["score"]
      < evaluer(devis(13, "50x60 12-10-2026.xlsx"), ENTREE, VOC)["score"], True)

print("\n5. Versions successives d'un même devis")
v1 = devis(20, "50x60 mm thermique pro permanent M76 B5000 3.000.000 05-10-2026.xlsx",
           date_devis="2026-10-05")
v2 = devis(21, "50x60 mm thermique pro permanent M76 B5000 3.705.000 12-10-2026.xlsx",
           date_devis="2026-10-12")
v3 = devis(22, "50x60 mm thermique pro permanent M76 B5000 3.705.000 25-10-2026.xlsx",
           date_devis="2026-10-25")
p = meilleur_devis([v1, v2, v3], ENTREE, VOC)
check("la plus récente avant la production", p and p["devis_id"], 21)

print("\n6. Deux produits différents également plausibles")
a = devis(30, "50x60 mm thermique pro permanent tabac 12-10-2026.xlsx")
b = devis(31, "50x60 mm thermique pro permanent fromage 12-10-2026.xlsx")
check("aucune proposition", meilleur_devis([a, b], ENTREE, VOC), None)

print("\n7. Moteur sur la base : rejets et décisions humaines")
from app.routers.rentabilite import rapprocher           # noqa: E402

with get_db() as conn:
    mid = conn.execute("INSERT INTO machines (nom, code, actif) VALUES ('M test','MT',1)").lastrowid
    for m, adh in [("THERMIQUE PRO", "Enlevable 1408 -22")] * 2 + [("THERMIQUE PRO", "Permanent 2028Y - 19")] * 3:
        conn.execute("INSERT INTO of_imports (matiere, adhesif_label) VALUES (?,?)", (m, adh))
    of_id = conn.execute("SELECT MAX(id) FROM of_imports").fetchone()[0]
    e1 = conn.execute(
        "INSERT INTO planning_entries (machine_id, position, reference, client, format_l, format_h, "
        "laize, planned_start, of_import_id) VALUES (?,?,'R1',?,?,?,?,?,?)",
        (mid, 1, "GRAND FRAIS", 50, 60, 470, "2026-10-20", of_id)).lastrowid
    e2 = conn.execute(
        "INSERT INTO planning_entries (machine_id, position, reference, client, format_l, format_h, "
        "laize, planned_start, of_import_id) VALUES (?,?,'R2',?,?,?,?,?,?)",
        (mid, 2, "GRAND FRAIS", 50, 60, 470, "2026-10-21", of_id)).lastrowid
    ids = []
    for f, dt in [("50x60 mm thermique pro permanent 12-10-2026.xlsx", "2026-10-12"),
                  ("50x60 mm thermique pro enlevable 01-09-2026.xlsx", "2026-09-01")]:
        ids.append(conn.execute(
            "INSERT INTO devis (filename, client, date_devis, format_h, format_v, laize, "
            "imported_at) VALUES (?,?,?,?,?,?,?)",
            (f, "Grand Frais", dt, 60, 50, 470, "2026-10-12")).lastrowid)
    conn.commit()

    r = rapprocher(conn)
    liens = {x["planning_entry_id"]: dict(x) for x in conn.execute("SELECT * FROM rent_links")}
    check("les deux dossiers rattachés au même devis (refabrication)",
          [liens.get(e1, {}).get("devis_id"), liens.get(e2, {}).get("devis_id")], [ids[0], ids[0]])
    check("identiques : validés d'office par le moteur",
          (liens[e1]["origine"], liens[e1]["valide_par"], bool(liens[e1]["valide_at"])),
          ("auto", "auto:identique", True))
    check("compteur de validations", r["validees"], 2)

    # Rejet sur e1, comme le fait DELETE /links/{id}
    conn.execute("INSERT INTO rent_rejets (planning_entry_id, devis_id) VALUES (?,?)", (e1, ids[0]))
    conn.execute("DELETE FROM rent_links WHERE planning_entry_id=?", (e1,))
    # e2 relu par quelqu'un
    conn.execute("UPDATE rent_links SET valide_at='2026-10-15', valide_par='eugene' "
                 "WHERE planning_entry_id=?", (e2,))
    conn.commit()
    rapprocher(conn)
    liens = {x["planning_entry_id"]: dict(x) for x in conn.execute("SELECT * FROM rent_links")}
    check("devis rejeté jamais reproposé", liens.get(e1, {}).get("devis_id") != ids[0], True)
    check("liaison confirmée intacte", liens[e2]["valide_at"], "2026-10-15")

print("\n8. Notification « Devis à traiter » (superadmin)")
from app.services import notifications as notif          # noqa: E402

with get_db() as conn:
    futur = conn.execute(
        "INSERT INTO devis (filename, client, date_devis, format_h, format_v, laize, imported_at) "
        "VALUES ('x.xlsx','Futur','2099-01-01',10,10,100,'2026-10-16')").lastrowid
    conn.commit()
    d = notif.devis_a_traiter(conn)
    check("devis rattaché : ni sans dossier ni futur", ids[0] in d["sans_dossier"], False)
    check("devis jamais rattaché : sans dossier", ids[1] in d["sans_dossier"], True)
    check("devis daté de 2099 : date future", futur in d["date_future"], True)
    n, sig = notif._compter_devis_a_traiter(conn)
    check("compte = sans dossier ET date future", n,
          len(set(d["sans_dossier"]) & set(d["date_future"])))
    check("le devis de 2099 sans dossier est compté, l'ancien sans dossier non", n, 1)
    regle = notif.regles(conn).get("prod.devis_a_traiter") or {}
    check("règle seedée active pour le superadmin", (regle.get("actif"), regle.get("roles")),
          (True, ["superadmin"]))

print()
if FAIL:
    print(f"ÉCHEC — {len(FAIL)} contrôle(s) en défaut")
    sys.exit(1)
print("TOUT EST VERT")

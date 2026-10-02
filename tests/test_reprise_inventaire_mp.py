"""
Reprise d'un inventaire physique dans MyStock (`app/services/reprise_inventaire_mp.py`).

Jeu synthétique, aucune donnée SIFA. Ce que le test verrouille :
- quantité appliquée = compté à la date d'inventaire + mouvements enregistrés
  depuis ; un mouvement antérieur n'est pas recompté ;
- non-conformités hors stock disponible, portées par leur emplacement ;
- laize connue mais non trouvée remise à zéro ;
- fiche reprise renommée, ancienne désignation gardée au mapping ;
- fiche doublon ramenée à zéro puis désactivée ;
- chaque ligne tracée (mouvement + inventaire) ;
- variantes créées et principal posé ;
- la migration SIFA s'ignore sur une base qui n'a pas ses fiches.

Lancer : python3 tests/test_reprise_inventaire_mp.py
"""

import importlib
import json
import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)
os.environ["DB_PATH"] = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["ERP_MIRROR_DB"] = os.environ["DB_PATH"] + ".absent"
import database  # noqa: F401,E402  — le shim d'abord
from database import get_db  # noqa: E402
from app.services import reprise_inventaire_mp as rep  # noqa: E402

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(62) + f"{got!r}"
          + ("" if ok else f"   attendu {expected!r}"))
    if not ok:
        FAIL.append(label)


with get_db() as c:
    mig = importlib.import_module("app.core.migrations.2026_10_02_reprise_inventaire_mp")
    sifa = json.load(open(mig._fichier(), encoding="utf-8"))
    check("migration SIFA ignorée sur une base sans ses fiches", mig._base_sifa(c, sifa), False)

    fa = c.execute("INSERT INTO fournisseurs_fsc (nom) VALUES ('Fournisseur A')").lastrowid
    fb = c.execute("INSERT INTO fournisseurs_fsc (nom) VALUES ('Fournisseur B')").lastrowid

    def fiche(ref, des, cat="frontal"):
        mid = c.execute(
            """INSERT INTO matieres_premieres (categorie, reference, designation, actif, is_europe, prix_par_laize,
                                               suivi_bobine, metres_lineaires_par_bobine)
               VALUES (?,?,?,1,0,0,0,10000)""", (cat, ref, des)).lastrowid
        c.execute("INSERT INTO mp_stock (matiere_id, quantite) VALUES (?, 0)", (mid,))
        return mid

    def laize(mm):
        r = c.execute("SELECT id FROM mp_laizes WHERE ABS(valeur_mm-?)<=0.5", (mm,)).fetchone()
        return r[0] if r else c.execute(
            "INSERT INTO mp_laizes (valeur_mm,label,ordre,actif,created_at) VALUES (?,?,0,1,'x')", (mm, "%g mm" % mm)).lastrowid

    m1 = fiche("TEST-ECO", "thermique eco")
    m2 = fiche("TEST-DOUBLON", "Thermique Eco fournisseur B")
    l1, l2 = laize(471.0), laize(531.0)
    for mid, lid, q in ((m1, l1, 30), (m1, l2, 12), (m2, l1, 5)):
        c.execute("INSERT INTO mp_matiere_laizes (matiere_id, laize_id) VALUES (?,?)", (mid, lid))
        c.execute("INSERT INTO mp_stock_laize (matiere_id, laize_id, quantite) VALUES (?,?,?)", (mid, lid, q))
    c.execute("UPDATE mp_stock SET quantite=42 WHERE matiere_id=?", (m1,))
    c.execute("UPDATE mp_stock SET quantite=5 WHERE matiere_id=?", (m2,))
    # sortie de 2 bobines APRÈS l'inventaire, entrée de 4 AVANT (déjà dans le compté)
    c.execute("""INSERT INTO mp_mouvements (matiere_id, type_mouvement, quantite, quantite_avant, quantite_apres,
                                            created_at, laize_id) VALUES (?,'sortie',2,30,28,'2026-10-02T08:00:00',?)""",
              (m1, l1))
    c.execute("""INSERT INTO mp_mouvements (matiere_id, type_mouvement, quantite, quantite_avant, quantite_apres,
                                            created_at, laize_id) VALUES (?,'entree',4,26,30,'2026-09-30T08:00:00',?)""",
              (m1, l1))

    data = {
        "date_inventaire": "2026-10-01",
        "fiches": [
            {"cle": str(m1), "id": m1, "action": "Reprendre", "categorie": "frontal", "sous_section": "Thermiques",
             "designation": "Thermique Eco 70 g/m²", "designation_avant": "thermique eco", "ml_std": 12000,
             "unites_par_palette": None},
            {"cle": "N:neuve", "id": None, "action": "Créer", "categorie": "glassine", "sous_section": None,
             "designation": "Glassine test 45 g/m²", "designation_avant": None, "ml_std": 18000,
             "unites_par_palette": None},
            {"cle": str(m2), "id": m2, "action": "Désactiver", "categorie": "frontal", "sous_section": "Thermiques",
             "designation": "Thermique Eco fournisseur B", "designation_avant": "Thermique Eco fournisseur B",
             "ml_std": None, "unites_par_palette": None},
        ],
        "variantes": [
            {"cle": str(m1), "fournisseur_id": fa, "libelle_technique": "Thermique Eco 70 g R1101", "ref_fournisseur": "R1101",
             "rvgi_code1": "7777", "rvgi_code2": "0004", "rvgi_type_code": 7, "ml_bobine": 12000, "principal": False},
            {"cle": str(m1), "fournisseur_id": fb, "libelle_technique": "Thermique Eco 70 g Termax", "ref_fournisseur": None,
             "rvgi_code1": None, "rvgi_code2": None, "rvgi_type_code": None, "ml_bobine": 10000, "principal": True},
            {"cle": "N:neuve", "fournisseur_id": fa, "libelle_technique": "Glassine 45 g Label 45", "ref_fournisseur": None,
             "rvgi_code1": None, "rvgi_code2": None, "rvgi_type_code": None, "ml_bobine": 18000, "principal": True},
        ],
        "stock": [
            {"cle": str(m1), "laize_mm": 471.0, "emplacement": "A14", "zone": "magasin", "quantite": 20.0},
            {"cle": str(m1), "laize_mm": 471.0, "emplacement": "DROITE 3", "zone": "magasin", "quantite": 5.5},
            {"cle": str(m1), "laize_mm": 471.0, "emplacement": "ATELIER", "zone": "production", "quantite": 0.5},
            {"cle": str(m1), "laize_mm": 471.0, "emplacement": "NC KL", "zone": "non_conforme", "quantite": 1.0},
            {"cle": "N:neuve", "laize_mm": 471.2, "emplacement": "E205", "zone": "magasin", "quantite": 3.0},
        ],
    }
    r = rep.appliquer(c, data)

    def q(mid, lid=None):
        if lid is None:
            return c.execute("SELECT quantite FROM mp_stock WHERE matiere_id=?", (mid,)).fetchone()[0]
        return c.execute("SELECT quantite FROM mp_stock_laize WHERE matiere_id=? AND laize_id=?", (mid, lid)).fetchone()[0]

    check("471 : compté 26 (20+5,5+0,5) - sortie du 02/10 = 24", q(m1, l1), 24.0)
    check("531 : laize non trouvée remise à zéro", q(m1, l2), 0.0)
    check("stock fiche = somme des laizes", q(m1), 24.0)
    check("zones : magasin / production du comptage",
          tuple(c.execute("SELECT quantite_magasin, quantite_production FROM mp_stock_laize WHERE matiere_id=? AND laize_id=?",
                          (m1, l1)).fetchone()), (25.5, 0.5))
    check("non-conformité : emplacement NC KL, hors stock",
          c.execute("SELECT quantite FROM mp_emplacements WHERE matiere_id=? AND emplacement='NC KL'", (m1,)).fetchone()[0], 1.0)
    check("emplacement terrain DROITE 3 repris",
          c.execute("SELECT quantite FROM mp_emplacements WHERE matiere_id=? AND emplacement='DROITE 3'", (m1,)).fetchone()[0], 5.5)
    check("fiche renommée au libellé commercial",
          c.execute("SELECT designation FROM matieres_premieres WHERE id=?", (m1,)).fetchone()[0], "Thermique Eco 70 g/m²")
    check("ancienne désignation gardée au mapping",
          c.execute("SELECT matiere_id FROM mp_fiche_mapping WHERE source_value='thermique eco'").fetchone()[0], m1)
    check("doublon : stock à zéro et désactivé",
          tuple(c.execute("SELECT m.actif, s.quantite FROM matieres_premieres m JOIN mp_stock s ON s.matiere_id=m.id WHERE m.id=?",
                          (m2,)).fetchone()), (0, 0.0))
    neuve = c.execute("SELECT id FROM matieres_premieres WHERE reference='Glassine test 45 g/m²'").fetchone()[0]
    check("fiche créée, laize 471,2 rapprochée de 471", q(neuve, l1), 3.0)
    check("chaque ligne tracée : mouvements = inventaires",
          c.execute("SELECT COUNT(*) FROM mp_mouvements WHERE note LIKE ?", (rep.MARQUE + "%",)).fetchone()[0],
          c.execute("SELECT COUNT(*) FROM inventaires_matieres WHERE operateur_nom=?", (rep.AUTEUR,)).fetchone()[0])
    check("principal posé sur la variante choisie",
          c.execute("SELECT fournisseur_id FROM mp_variantes WHERE matiere_id=? AND principal=1 AND actif=1", (m1,)).fetchone()[0], fb)
    check("article RVGI apparié à la fiche",
          c.execute("SELECT matiere_id FROM erp_article_matiere WHERE code1='7777'").fetchone()[0], m1)
    check("rapport sans erreur", r.get("erreurs", []), [])

    # État de v1 au 03/10 : une variante provisoire (prix) restée à côté de la
    # variante complète du même fournisseur, et portant le principal.
    c.execute("UPDATE mp_variantes SET principal=0 WHERE matiere_id=?", (m1,))
    prov = c.execute(
        """INSERT INTO mp_variantes (matiere_id, fournisseur_id, libelle_technique, principal, actif, note)
           VALUES (?, ?, 'thermique eco', 1, 1, 'Reprise des prix fournisseur : libellé technique à compléter.')""",
        (m1, fa)).lastrowid
    fusion = importlib.import_module("app.core.migrations.2026_10_03_mp_variantes_fusion_provisoires")
    fusion.appliquer(c)
    check("fusion : la provisoire est désactivée",
          c.execute("SELECT actif FROM mp_variantes WHERE id=?", (prov,)).fetchone()[0], 0)
    check("fusion : le principal passe à la variante complète du même fournisseur",
          tuple(c.execute("SELECT fournisseur_id, rvgi_code1 FROM mp_variantes WHERE matiere_id=? AND principal=1 AND actif=1",
                          (m1,)).fetchone()), (fa, "7777"))
    c.rollback()

print()
if FAIL:
    print("ÉCHEC : %d contrôle(s) en erreur" % len(FAIL))
    sys.exit(1)
print("Reprise d'inventaire : tout est vert.")

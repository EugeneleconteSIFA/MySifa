"""
Fusion de deux fiches fournisseur (`app/services/fournisseurs_fusion.py`).

Jeu synthétique. Ce que le test verrouille :
- la fiche gardée reprend le lien RVGI du doublon quand elle n'en a pas, et le
  doublon est supprimé ;
- prix, tarifs, réceptions, certificats, variantes passent sur la fiche gardée ;
  sur une clé unique déjà occupée, la fiche gardée gagne et garde le principal ;
- les noms recopiés en texte (réceptions, MyProd) suivent ;
- variante provisoire + variante complète du même fournisseur → une seule ;
- deux fiches toutes deux liées à RVGI : le doublon reste, désactivé, avec son
  numéro (sinon l'import le recréerait), et ce numéro résout vers la fiche
  gardée ;
- une réception RVGI intégrée porte la fiche fournisseur, pas seulement la
  raison sociale ;
- la migration SIFA s'ignore sur une base qui n'a pas ses fiches.

Lancer : python3 tests/test_fournisseurs_fusion.py
"""

import importlib
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
from app.services import fournisseurs_fusion as fus  # noqa: E402
from app.services import mp_variantes as mv  # noqa: E402
from app.services import mystock_prix as mp  # noqa: E402
from app.services import reception_rvgi as rr  # noqa: E402

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(66) + f"{got!r}"
          + ("" if ok else f"   attendu {expected!r}"))
    if not ok:
        FAIL.append(label)


with get_db() as c:
    M = c.execute("INSERT INTO fournisseurs_fsc (nom) VALUES ('Fournisseur Manuel')").lastrowid
    R = c.execute("""INSERT INTO fournisseurs_fsc (nom, rvgi_numero, rvgi_etat, rvgi_rs, siret, ville)
                     VALUES ('FOURNISSEUR RVGI LTD', 1183, 'lie', 'SHENZHEN LIKEXIN', '123', 'SHENZHEN')""").lastrowid
    mid = c.execute(
        """INSERT INTO matieres_premieres (categorie, reference, designation, actif, is_europe, prix_par_laize,
                                           suivi_bobine, sous_section)
           VALUES ('frontal', 'TEST', 'Thermique Eco 70 g/m²', 1, 0, 0, 0, 'Thermiques')""").lastrowid
    c.execute("INSERT INTO mp_stock (matiere_id, quantite) VALUES (?, 0)", (mid,))
    lz = []
    for v in (471.0, 511.0):
        lid = c.execute("INSERT INTO mp_laizes (valeur_mm, label, ordre, actif, created_at) VALUES (?, ?, 0, 1, 'x')",
                        (v, "%d mm" % v)).lastrowid
        c.execute("INSERT INTO mp_matiere_laizes (matiere_id, laize_id) VALUES (?, ?)", (mid, lid))
        lz.append(lid)
    d470 = mp.add_declinaison(c, matiere_id=mid, laize_id=lz[0])["declinaison_id"]
    d510 = mp.add_declinaison(c, matiere_id=mid, laize_id=lz[1])["declinaison_id"]

    # Prix : la fiche manuelle porte le principal, le doublon un prix concurrent
    # sur 470 et le seul prix de 510.
    mp.set_prix(c, declinaison_id=d470, fournisseur_id=M, prix=1.0)
    mp.set_prix(c, declinaison_id=d470, fournisseur_id=R, prix=1.3)
    mp.set_prix(c, declinaison_id=d510, fournisseur_id=R, prix=1.1)
    # L'article RVGI rattaché au doublon (son numéro est le code1).
    vr = mv.creer(c, mid, {"libelle_technique": "Thermique Eco 70 g KP460", "ref_rvgi": "1183/0004",
                           "rvgi_type_code": 7}, "test")
    check("avant fusion : l'article RVGI va chez le doublon",
          c.execute("SELECT fournisseur_id FROM mp_variantes WHERE id=?", (vr,)).fetchone()[0], R)

    for fid in (M, R):
        c.execute("INSERT INTO mc_tarif_fournisseur (fournisseur_id, matiere_id, price_basis, updated_at) "
                  "VALUES (?, ?, 'm2', 'x')", (fid, mid))
    c.execute("""INSERT INTO qualite_fournisseur_certificats
                 (fournisseur_id, filename, original_name, titre, commentaire, uploaded_at)
                 VALUES (?, 'f.pdf', 'FSC.pdf', 'FSC', '', 'x')""", (R,))
    rec = c.execute("INSERT INTO stock_receptions (created_at, fournisseur, fournisseur_id, nb_bobines) "
                    "VALUES ('x', 'FOURNISSEUR RVGI LTD', ?, 0)", (R,)).lastrowid

    r = fus.fusionner(c, R, M, auteur="test")

    check("doublon supprimé (son lien RVGI est passé à la fiche gardée)", c.execute(
        "SELECT COUNT(*) FROM fournisseurs_fsc WHERE id=?", (R,)).fetchone()[0], 0)
    check("lien RVGI transporté sur la fiche gardée", tuple(c.execute(
        "SELECT rvgi_numero, rvgi_etat, rvgi_rs FROM fournisseurs_fsc WHERE id=?", (M,)).fetchone()),
        (1183, "lie", "SHENZHEN LIKEXIN"))
    check("champs vides complétés (ville)", c.execute(
        "SELECT ville FROM fournisseurs_fsc WHERE id=?", (M,)).fetchone()[0], "SHENZHEN")
    check("variantes jumelles fondues par la fusion elle-même", r["variantes_fusionnees"], 1)
    check("numéro RVGI 1183 → fiche gardée", fus.par_numero_rvgi(c, "1183"), M)
    check("470 : une seule ligne de prix, la fiche gardée, principale", [tuple(x) for x in c.execute(
        "SELECT fournisseur_id, principal, prix FROM mp_matiere_prix WHERE declinaison_id=? AND fournisseur_id IS NOT NULL", (d470,))], [(M, 1, 1.0)])
    check("510 : le prix du doublon passe à la fiche gardée", c.execute(
        "SELECT fournisseur_id FROM mp_matiere_prix WHERE declinaison_id=? AND principal=1", (d510,)).fetchone()[0], M)
    check("tarif : clé unique, la fiche gardée gagne", c.execute(
        "SELECT COUNT(*) FROM mc_tarif_fournisseur WHERE matiere_id=?", (mid,)).fetchone()[0], 1)
    check("certificat déplacé", c.execute(
        "SELECT fournisseur_id FROM qualite_fournisseur_certificats").fetchone()[0], M)
    check("réception : id et nom suivent", tuple(c.execute(
        "SELECT fournisseur_id, fournisseur FROM stock_receptions WHERE id=?", (rec,)).fetchone()), (M, "Fournisseur Manuel"))

    actives = [tuple(x) for x in c.execute(
        "SELECT fournisseur_id, rvgi_code1, principal FROM mp_variantes WHERE matiere_id=? AND actif=1", (mid,))]
    check("page matière : un seul fournisseur, la variante complète principale", actives, [(M, "1183", 1)])

    refus = None
    try:
        fus.fusionner(c, R, M)
    except LookupError:
        refus = "refusé"
    check("refaire la fusion est refusé", refus, "refusé")

    # Deux fiches toutes deux liées à RVGI.
    B1 = c.execute("INSERT INTO fournisseurs_fsc (nom, rvgi_numero, rvgi_etat) VALUES ('Palettes A', 1190, 'lie')").lastrowid
    B2 = c.execute("INSERT INTO fournisseurs_fsc (nom, rvgi_numero, rvgi_etat) VALUES ('PALETTES A (X)', 1195, 'lie')").lastrowid
    r2 = fus.fusionner(c, B2, B1)
    check("double RVGI : le doublon reste, désactivé, avec son numéro", tuple(c.execute(
        "SELECT actif, fusionne_dans, rvgi_numero FROM fournisseurs_fsc WHERE id=?", (B2,)).fetchone()),
        (0, B1, 1195))
    check("double RVGI : signalé dans le rapport", r2["source_conservee"], True)
    check("double RVGI : ce numéro résout vers la fiche gardée", fus.par_numero_rvgi(c, 1195), B1)
    check("double RVGI : la fiche gardée garde le sien", fus.par_numero_rvgi(c, 1190), B1)

    # Réception RVGI intégrée : fiche fournisseur par le numéro.
    ligne = {"lif_id": 999001, "integrable": True, "matiere_id": mid, "quantite": 2.0, "type_code": 7,
             "regime": "attente", "laize_mm": 471.0, "numfou": 1183, "numero": 1, "ligne": 1,
             "fournisseur": "FOURNISSEUR RVGI LTD"}
    res = rr.integrer(c, ligne, {"nom": "t"}, lambda *a, **k: {"mouvement_id": None})
    check("réception RVGI : fiche fournisseur et nom MySifa", tuple(c.execute(
        "SELECT fournisseur_id, fournisseur FROM stock_receptions WHERE id=?", (res["reception_id"],)).fetchone()),
        (M, "Fournisseur Manuel"))

    mig = importlib.import_module("app.core.migrations.2026_10_03_fournisseurs_fusion_doublons")
    n_avant = c.execute("SELECT COUNT(*) FROM fournisseurs_fsc WHERE fusionne_dans IS NOT NULL").fetchone()[0]
    mig.appliquer(c)
    check("migration SIFA ignorée sur une base sans ses fiches", c.execute(
        "SELECT COUNT(*) FROM fournisseurs_fsc WHERE fusionne_dans IS NOT NULL").fetchone()[0], n_avant)
    c.rollback()

print()
if FAIL:
    print("ÉCHEC : %d contrôle(s) en erreur" % len(FAIL))
    sys.exit(1)
print("Fusion fournisseurs : tout est vert.")

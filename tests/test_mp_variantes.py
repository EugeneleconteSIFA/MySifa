"""
Variantes fournisseur d'une matière : un seul fournisseur principal, partagé
avec Coûts matières.

Ce que le test verrouille :
- un prix saisi dans Coûts matières fait apparaître son fournisseur sur la page ;
- choisir le principal sur la page fait suivre le prix en vigueur, et dit les
  laizes où ce fournisseur n'a pas de prix ;
- choisir le principal dans Coûts matières fait suivre la page ;
- saisir un prix sur une laize que le principal ne livre pas ne fait PAS
  basculer la matière ;
- une variante provisoire se complète au lieu d'être doublée ;
- les refus : principal désactivé, fournisseur du principal changé, article
  RVGI déjà rattaché, libellé vide.

Lancer : python3 tests/test_mp_variantes.py
"""

import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))
os.chdir(RACINE)

# Base jetable : le shim `database` initialise le schéma au chargement.
os.environ["DB_PATH"] = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["ERP_MIRROR_DB"] = os.environ["DB_PATH"] + ".absent"
import database  # noqa: F401,E402  — le shim doit être chargé avant tout app.*
from database import get_db  # noqa: E402
from app.services import mp_variantes as mv  # noqa: E402
from app.services import mystock_prix as mp  # noqa: E402
from app.services import reception_rvgi as rr  # noqa: E402

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(64) + f"{got!r}"
          + ("" if ok else f"   attendu {expected!r}"))
    if not ok:
        FAIL.append(label)


def refus(label, fn):
    try:
        fn()
    except ValueError:
        check(label, "refusé", "refusé")
        return
    check(label, "accepté", "refusé")


def principaux_prix(c, mid):
    return {r["declinaison_id"]: r["fournisseur_id"] for r in c.execute(
        "SELECT declinaison_id, fournisseur_id FROM mp_matiere_prix WHERE matiere_id=? AND principal=1", (mid,))}


def fournisseur_principal(c, mid):
    r = c.execute("SELECT fournisseur_id FROM mp_variantes WHERE matiere_id=? AND principal=1 AND actif=1",
                  (mid,)).fetchone()
    return r["fournisseur_id"] if r else None


with get_db() as c:
    A = c.execute("INSERT INTO fournisseurs_fsc (nom, rvgi_numero) VALUES ('Fournisseur A', 1183)").lastrowid
    B = c.execute("INSERT INTO fournisseurs_fsc (nom) VALUES ('Fournisseur B')").lastrowid
    mid = c.execute(
        """INSERT INTO matieres_premieres (categorie, reference, designation, actif, is_europe, prix_par_laize,
                                           suivi_bobine, sous_section)
           VALUES ('frontal', 'TEST', 'Thermique Eco 70 g/m²', 1, 0, 0, 0, 'Thermiques')""").lastrowid
    c.execute("INSERT INTO mp_stock (matiere_id, quantite) VALUES (?, 0)", (mid,))
    laizes = []
    for v in (471.0, 511.0):
        lid = c.execute("INSERT INTO mp_laizes (valeur_mm, label, ordre, actif, created_at) VALUES (?, ?, 0, 1, 'x')",
                        (v, "%d mm" % v)).lastrowid
        c.execute("INSERT INTO mp_matiere_laizes (matiere_id, laize_id) VALUES (?, ?)", (mid, lid))
        laizes.append(lid)
    d470 = mp.add_declinaison(c, matiere_id=mid, laize_id=laizes[0])["declinaison_id"]
    d510 = mp.add_declinaison(c, matiere_id=mid, laize_id=laizes[1])["declinaison_id"]

    # Prix : A sur les deux laizes, B sur la première seulement.
    mp.set_prix(c, declinaison_id=d470, fournisseur_id=A, prix=1.0)
    mp.set_prix(c, declinaison_id=d470, fournisseur_id=B, prix=0.9)
    mp.set_prix(c, declinaison_id=d510, fournisseur_id=A, prix=1.1)
    fous = sorted(v["fournisseur_id"] for v in mv.lister(c, mid)["variantes"])
    check("un prix fait apparaître son fournisseur sur la page", fous, sorted([A, B]))
    check("principal de la page = principal des prix (A)", fournisseur_principal(c, mid), A)

    # Compléter la variante provisoire de B plutôt que la doubler.
    vb = mv.creer(c, mid, {"fournisseur_id": B, "libelle_technique": "Termax TFS 70 g", "ref_rvgi": "9999/0001",
                           "rvgi_type_code": 7, "ml_bobine": "10 000"}, "test")
    n_b = c.execute("SELECT COUNT(*) FROM mp_variantes WHERE matiere_id=? AND fournisseur_id=? AND actif=1",
                    (mid, B)).fetchone()[0]
    check("variante provisoire complétée, pas doublée", n_b, 1)
    check("longueur de bobine lue avec séparateur", c.execute(
        "SELECT ml_bobine FROM mp_variantes WHERE id=?", (vb,)).fetchone()[0], 10000.0)
    check("article RVGI apparié et pointé vers la variante", c.execute(
        "SELECT matiere_id, variante_id FROM erp_article_matiere WHERE code1='9999'").fetchone()[:], (mid, vb))

    # Page -> Coûts matières.
    res = mv.definir_principal(c, vb, user_name="test")
    check("page : B principal", fournisseur_principal(c, mid), B)
    check("page : prix en vigueur 470 chez B", principaux_prix(c, mid)[d470], B)
    check("page : 510 sans prix chez B reste chez A", principaux_prix(c, mid)[d510], A)
    check("page : la laize sans prix est signalée", res["declinaisons_sans_prix"], ["511 mm"])
    check("écart signalé sur la fiche", [e["etat"] for e in mv.lister(c, mid)["ecarts_prix"]], ["sans_prix"])

    # Saisir un prix sur la 510 (principal A) ne fait pas basculer la matière.
    mp.set_prix(c, declinaison_id=d510, fournisseur_id=A, prix=1.2)
    check("saisie de prix : le principal de la page ne bouge pas", fournisseur_principal(c, mid), B)

    # Coûts matières -> page.
    mp.set_principal(c, declinaison_id=d470, fournisseur_id=A, user_name="test")
    check("Coûts matières : choix explicite de A, la page suit", fournisseur_principal(c, mid), A)

    # Refus.
    va = c.execute("SELECT id FROM mp_variantes WHERE matiere_id=? AND fournisseur_id=? AND actif=1",
                   (mid, A)).fetchone()[0]
    refus("désactiver le fournisseur principal", lambda: mv.desactiver(c, va, "t"))
    refus("changer le fournisseur du principal", lambda: mv.modifier(c, va, {"fournisseur_id": B}, "t"))
    refus("article RVGI déjà rattaché", lambda: mv.creer(
        c, mid, {"libelle_technique": "x", "ref_rvgi": "9999/0001", "rvgi_type_code": 7}, "t"))
    refus("libellé technique vide", lambda: mv.creer(c, mid, {"libelle_technique": "  "}, "t"))
    refus("référence RVGI mal formée", lambda: mv.creer(c, mid, {"libelle_technique": "x", "ref_rvgi": "9999"}, "t"))

    # Appariement RVGI : le code1 désigne le fournisseur.
    rr.apparier(c, "1183", "0004", 7, mid, auteur="t")
    check("appariement : variante du fournisseur au numéro RVGI", c.execute(
        "SELECT fournisseur_id FROM mp_variantes WHERE rvgi_code1='1183' AND actif=1").fetchone()[0], A)

    # Désactiver une variante non principale libère son article RVGI.
    mv.desactiver(c, vb, "t")
    check("désactivation : l'article RVGI ne pointe plus la variante", c.execute(
        "SELECT variante_id FROM erp_article_matiere WHERE code1='9999'").fetchone()[0], None)
    c.rollback()

print()
if FAIL:
    print("ÉCHEC : %d contrôle(s) en erreur" % len(FAIL))
    sys.exit(1)
print("Variantes fournisseur : tout est vert.")

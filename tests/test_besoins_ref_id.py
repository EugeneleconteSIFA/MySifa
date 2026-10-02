"""
Besoins matières et déstockage : la référence MyStock d'abord, le texte ensuite.

La fiche technique et l'OF portent l'id de la matière choisie dans MyStock
(`support_ref_id`, `matiere_ref_id`…). Ce que le test verrouille :
- une ligne dont la fiche porte une référence se résout sur elle, même quand
  le texte ne correspond à rien (renommage, faute de frappe) ;
- la référence gagne sur une correspondance texte qui désigne une autre matière ;
- sans référence, le texte (mp_fiche_mapping) sert comme avant ;
- une référence vers une matière désactivée retombe sur le texte ;
- l'OF qui remplace le texte de la fiche remplace aussi sa référence.

Lancer : python3 tests/test_besoins_ref_id.py
"""

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
from app.routers import besoins_matieres as bm  # noqa: E402

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(64) + f"{got!r}"
          + ("" if ok else f"   attendu {expected!r}"))
    if not ok:
        FAIL.append(label)


def support(pe, mapping):
    lignes = [b for b in bm._compute_besoins_dossier(pe, mapping) if b["kind"] == "support"]
    return lignes[0]["matiere_id"] if lignes else "aucune ligne"


with get_db() as c:
    def matiere(des, actif=1):
        return c.execute(
            """INSERT INTO matieres_premieres (categorie, reference, designation, actif, is_europe,
                                               prix_par_laize, suivi_bobine, metres_lineaires_par_bobine)
               VALUES ('frontal', ?, ?, ?, 0, 0, 0, 10000)""", (des.upper()[:20], des, actif)).lastrowid

    A = matiere("Test Thermique Pro 70 g/m²")
    B = matiere("Test Velin 80 g/m²")
    X = matiere("Test Ancienne fiche", actif=0)
    c.execute("INSERT INTO mp_fiche_mapping (kind, source_value, matiere_id) VALUES ('support', 'velin test', ?)", (B,))
    mapping = bm._load_mapping(c)

    base = {"of_metrage": 1000.0, "qte_etiquettes": 1000, "of_laize": 100.0}
    check("référence de la fiche, texte inconnu → la référence",
          support({**base, "ft_support": "thermique pro (ancien libellé)", "ft_support_ref_id": A}, mapping), A)
    check("la référence gagne sur une correspondance texte",
          support({**base, "ft_support": "velin test", "ft_support_ref_id": A}, mapping), A)
    check("sans référence, le texte sert comme avant",
          support({**base, "ft_support": "velin test", "ft_support_ref_id": None}, mapping), B)
    check("référence vers une matière désactivée → repli sur le texte",
          support({**base, "ft_support": "velin test", "ft_support_ref_id": X}, mapping), B)
    check("ni référence ni correspondance : ligne non associée",
          support({**base, "ft_support": "inconnu", "ft_support_ref_id": None}, mapping), None)

    pe = {**base, "ft_support": "velin test", "ft_support_ref_id": B,
          "of_matiere": "Test Thermique Pro 70 g/m²", "of_support_ref_id": A}
    bm._matieres_depuis_of(pe)
    check("archive : l'OF prime, sa référence avec son texte", support(pe, mapping), A)

    pe = {**base, "ft_support": "Thermique sans référence", "of_matiere": "velin test",
          "of_support_ref_id": None, "ft_support_ref_id": A}
    bm._matieres_depuis_of(pe)
    check("archive : texte de l'OF sans référence → plus la référence de la fiche", support(pe, mapping), B)
    c.rollback()

print()
if FAIL:
    print("ÉCHEC : %d contrôle(s) en erreur" % len(FAIL))
    sys.exit(1)
print("Besoins par référence : tout est vert.")

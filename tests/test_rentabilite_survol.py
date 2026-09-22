"""
Vue Rentabilite > Dossiers : ce que le bloc et son survol ont besoin de savoir.

Le bloc affiche desormais la quantite et le format, et le survol quatre
sections. Ces valeurs ne vivent pas toutes dans `planning_entries` : la
quantite d'etiquettes, la matiere et le conditionnement sont sur l'OF. Ce test
verifie que la jointure les ramene, et qu'elle reste une LEFT — un dossier
pose au planning avant son OF doit rester visible, c'est meme celui-la qu'on
cherche dans cet ecran.

Lancer : python3 tests/test_rentabilite_survol.py
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

FAIL = []


def check(label, got, expected):
    ok = got == expected
    print(("ok   " if ok else "KO   ") + label.ljust(58) + f"{got}"
          + ("" if ok else f"   attendu {expected}"))
    if not ok:
        FAIL.append(label)


# ── La requete de l'ecran, lue dans le routeur ────────────────────────
# Lue en texte et non importee : le routeur tire FastAPI, qui n'est pas
# toujours installe sur le poste du developpeur. Un test qui ne tourne que sur
# la CI ne protege pas au moment ou l'on casse la requete.
ROUTEUR = (RACINE / "app" / "routers" / "rentabilite.py").read_text(encoding="utf-8")
_debut = ROUTEUR.index("def list_planning_entries")
_fin = ROUTEUR.index("@router.get", _debut)
FONCTION = ROUTEUR[_debut:_fin]
# Le docstring parle lui aussi de SELECT : on part de l'appel, pas du texte.
_exec = FONCTION.index("conn.execute(")
sql = FONCTION[FONCTION.index("SELECT", _exec):
               FONCTION.index("e.position ASC", _exec) + len("e.position ASC")]

print("\n1. La requete de l'ecran")

check("l'OF est joint", "LEFT JOIN of_imports" in sql, True)
check("en LEFT, pas en INNER", "JOIN of_imports" in sql and "LEFT JOIN of_imports" in sql, True)
for colonne in ("of_qte_etiquettes", "of_format", "of_matiere",
                "of_conditionnement", "of_nb_cartons", "of_laize"):
    check(f"expose {colonne}", colonne in sql, True)

print("\n2. Elle tourne, et ramene l'OF quand il existe")

with dbmod.get_db() as conn:
    # Le referentiel machines est seede par les migrations : en creer une
    # doublonnerait un code. On prend celle qui est la.
    mid = conn.execute(
        "SELECT id FROM machines WHERE actif=1 ORDER BY id LIMIT 1"
    ).fetchone()[0]
    ofid = conn.execute(
        """INSERT INTO of_imports (of_numero, qte_etiquettes, format, matiere,
                                   conditionnement, nb_cartons, valide)
           VALUES ('OF-1', 400000, '100 x 130 mm', 'THERMIQUE ECO BPA',
                   'Paquet de 1 000 plis', 100, 1)"""
    ).lastrowid
    commun = ("machine_id, position, reference, client, duree_heures, statut, "
              "created_at, updated_at")
    conn.execute(
        f"INSERT INTO planning_entries ({commun}, of_import_id, format_l, format_h) "
        "VALUES (?,1,'9932617','JULES',4.5,'attente','2026-09-22','2026-09-22',?,100,130)",
        (mid, ofid))
    conn.execute(
        f"INSERT INTO planning_entries ({commun}, format_l, format_h) "
        "VALUES (?,2,'9932610','SODEBO',3.0,'attente','2026-09-22','2026-09-22',149,55)",
        (mid,))
    conn.commit()
    lignes = [dict(r) for r in conn.execute(sql).fetchall()]

par_ref = {l["reference"]: l for l in lignes}
check("les deux dossiers sont la", len(lignes), 2)
check("quantite reprise de l'OF", par_ref["9932617"]["of_qte_etiquettes"], 400000)
check("matiere reprise de l'OF", par_ref["9932617"]["of_matiere"], "THERMIQUE ECO BPA")
check("format de l'OF", par_ref["9932617"]["of_format"], "100 x 130 mm")
check("le dossier SANS OF reste visible", "9932610" in par_ref, True)
check("… et ses colonnes d'OF sont vides, pas a zero",
      par_ref["9932610"]["of_qte_etiquettes"], None)
check("… son format planning est intact", par_ref["9932610"]["format_l"], 149.0)
check("la laize du planning n'est pas ecrasee par celle de l'OF",
      "laize" in par_ref["9932617"] and "of_laize" in par_ref["9932617"], True)

print("\n3. Ce que l'ecran fait de ces valeurs")

js = (RACINE / "static" / "mysifa_prod_core.js").read_text(encoding="utf-8")
check("le bloc porte une troisieme ligne", "rent-tl-bloc-meta" in js, True)
check("le survol n'est plus un title natif",
      "title:(head.client" not in js, True)
check("le panneau de survol existe", "rentTipMontrer" in js, True)
check("l'ecart de quantite alerte au-dela de 10 %",
      "Math.abs(pc) > 10" in js, True)
check("les liaisons transportent les chiffres du devis",
      "devis: l.devis||null" in js, True)

print("")
if FAIL:
    print("ECHECS : " + ", ".join(FAIL))
    sys.exit(1)
print("TOUT EST VERT")

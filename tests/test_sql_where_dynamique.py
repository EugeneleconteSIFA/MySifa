# -*- coding: utf-8 -*-
"""
Garde-fou : aucune valeur utilisateur ne doit entrer dans une clause SQL.

Plusieurs routers construisent leur clause morceau par morceau, puis
l'interpolent :

    wc = " AND ".join(where)
    conn.execute(f"SELECT ... WHERE {wc}", params)

C'est sain TANT QUE chaque morceau est une chaine ecrite dans le code, avec des
`?` pour les valeurs. Le jour ou quelqu'un ecrit
`where.append(f"machine = '{m}'")`, c'est une injection SQL — et rien ne le
signale, la ligne ressemble aux autres.

Ce test lit le code (AST, aucune execution) et refuse ce cas.

Il PROUVE tout seul le motif majoritaire — `for col in ("a","b"): sets.append(f"{col}=?")`
— en verifiant que la variable de boucle vient d'une collection litterale. Les
rares sites qui echappent a cette preuve sont listes dans SITES_REVUS, avec la
raison ET une verification automatique de cette raison : un modele Pydantic
whiteliste par declaration doit refuser les champs supplementaires, sinon le
test tombe.

Lancer : python3 tests/test_sql_where_dynamique.py
"""

import ast
import os
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
os.chdir(RACINE)

LISTES_SQL = {"where", "ws", "conds", "clauses", "filtres", "sets", "fields", "champs"}

MOTIF_PLACEHOLDER = re.compile(
    r"""^\s*(
        ['"][,\s]*['"]\.join\(\s*['"]\?['"]\s*\*\s*len\(.+\)\s*\)
      | ['"][,\s]*['"]\.join\(\s*\[?\s*['"]\?['"].*\)
      | placeholders? | qmarks | marks | trous
    )\s*$""",
    re.VERBOSE,
)

# Sites que la preuve statique ne couvre pas. Chacun a ete relu le 27/08/2026.
# `modele` déclenche la verification automatique de la raison invoquee.
SITES_REVUS = {
    ("app/routers/taches.py", "update_tache"): {
        "raison": "les cles viennent de TachePatch.model_dump()",
        "modele": "TachePatch",
    },
    ("app/routers/pricing.py", "patch_supplier"): {
        "raison": "les cles viennent de McSupplierUpdate.model_dump()",
        "modele": "McSupplierUpdate",
    },
    ("app/routers/pricing.py", "patch_material"): {
        "raison": "les cles viennent de McMaterialUpdate.model_dump()",
        "modele": "McMaterialUpdate",
    },
    ("app/routers/pricing.py", "patch_product"): {
        "raison": "les cles viennent de McProductUpdate.model_dump()",
        "modele": "McProductUpdate",
    },
    ("app/routers/expe_departs.py", "list_palettes_europe"): {
        "raison": "search_sql vient de _historique_search_clause() : colonnes issues de "
                  "_HIST_SEARCH_COLS (constante module), valeurs en `?`",
        "constante": ("app/routers/expe_departs.py", "_HIST_SEARCH_COLS"),
    },
}

FAIL = []


def check(label, ok):
    print(("ok   " if ok else "KO   ") + label)
    if not ok:
        FAIL.append(label)


def _litteral_de_chaines(noeud):
    return (isinstance(noeud, (ast.List, ast.Tuple, ast.Set))
            and bool(noeud.elts)
            and all(isinstance(e, ast.Constant) and isinstance(e.value, str)
                    for e in noeud.elts))


def variables_de_boucle_litterale(arbre):
    """Noms de variables dont la valeur ne peut etre qu'une chaine ecrite dans
    le code : `for k in ("a","b")`, ou `for k in cols` avec `cols = ["a","b"]`."""
    litteraux = set()
    for n in ast.walk(arbre):
        if isinstance(n, ast.Assign) and _litteral_de_chaines(n.value):
            for c in n.targets:
                if isinstance(c, ast.Name):
                    litteraux.add(c.id)
        elif isinstance(n, ast.AnnAssign) and n.value is not None and _litteral_de_chaines(n.value):
            if isinstance(n.target, ast.Name):
                litteraux.add(n.target.id)

    sures = set()
    for n in ast.walk(arbre):
        if not isinstance(n, ast.For):
            continue
        it = n.iter
        ok = _litteral_de_chaines(it) or (isinstance(it, ast.Name) and it.id in litteraux)
        if ok and isinstance(n.target, ast.Name):
            sures.add(n.target.id)
    return sures


def analyser(chemin):
    src = chemin.read_text(encoding="utf-8")
    arbre = ast.parse(src, str(chemin))
    sures = variables_de_boucle_litterale(arbre)
    restants = []

    for noeud in ast.walk(arbre):
        if not isinstance(noeud, ast.Call):
            continue
        fonc = noeud.func
        if not (isinstance(fonc, ast.Attribute) and fonc.attr == "append"):
            continue
        cible = fonc.value
        if not (isinstance(cible, ast.Name) and cible.id in LISTES_SQL):
            continue
        if not noeud.args:
            continue
        arg = noeud.args[0]

        # `ws` est aussi le nom usuel d'une feuille openpyxl : `ws.append([...])`
        # ajoute une ligne de tableur, pas un morceau de SQL.
        if isinstance(arg, (ast.List, ast.Dict, ast.Tuple)):
            continue
        if isinstance(arg, ast.BinOp):
            # Une ligne de tableur assemblee (`["TOTAL"] + [""] * n`) est
            # inoffensive ; une CONCATENATION DE CHAINES dans une clause SQL ne
            # l'est pas — c'est meme la forme historique de l'injection. On ne
            # laisse donc passer que le cas ou une liste est en jeu.
            operandes = (arg.left, arg.right)
            if any(isinstance(o, (ast.List, ast.Tuple)) for o in operandes):
                continue
            # `"pe." + c` ou `c` boucle sur une collection litterale : c'est le
            # meme motif prouve que `f"{col}=?"`, ecrit avec un `+`.
            noms = [o.id for o in operandes if isinstance(o, ast.Name)]
            consts = [o for o in operandes
                      if isinstance(o, ast.Constant) and isinstance(o.value, str)]
            if consts and noms and all(n in sures for n in noms):
                continue
            restants.append((noeud.lineno, " ".join((ast.get_source_segment(src, noeud) or "").split())))
            continue
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            continue
        if isinstance(arg, ast.IfExp) and all(
                isinstance(b, ast.Constant) and isinstance(b.value, str)
                for b in (arg.body, arg.orelse)):
            continue
        if isinstance(arg, ast.Name):
            continue
        if not isinstance(arg, ast.JoinedStr):
            restants.append((noeud.lineno, (ast.get_source_segment(src, noeud) or "").strip()))
            continue

        morceaux = [v for v in arg.values if isinstance(v, ast.FormattedValue)]
        sources = [ast.get_source_segment(src, m.value) or "" for m in morceaux]
        if all(MOTIF_PLACEHOLDER.match(s) for s in sources):
            continue                                   # ne fabrique que des `?`
        if all(s in sures for s in sources):
            continue                                   # PROUVE : boucle litterale
        restants.append((noeud.lineno, " ".join((ast.get_source_segment(src, noeud) or "").split())))

    return restants


def modele_refuse_les_extras(nom_modele):
    """Le modele Pydantic est cherche dans tout app/ : les schemas ne vivent pas
    forcement dans le router qui les utilise. Si plusieurs definitions portent
    le meme nom, TOUTES doivent refuser les extras — on ne sait pas laquelle est
    importee, et la plus permissive fait la securite."""
    trouves = []
    for chemin in sorted(Path("app").rglob("*.py")):
        if "__pycache__" in str(chemin):
            continue
        try:
            arbre = ast.parse(chemin.read_text(encoding="utf-8"), str(chemin))
        except SyntaxError:
            continue
        for n in ast.walk(arbre):
            if isinstance(n, ast.ClassDef) and n.name == nom_modele:
                corps = ast.get_source_segment(chemin.read_text(encoding="utf-8"), n) or ""
                champs = [a.target.id for a in n.body if isinstance(a, ast.AnnAssign)]
                permissif = 'extra="allow"' in corps or "extra='allow'" in corps
                trouves.append((str(chemin), len(champs), permissif))
    if not trouves:
        return False, "introuvable dans app/"
    permissifs = [t for t in trouves if t[2]]
    if permissifs:
        return False, "extra='allow' dans %s : n'importe quelle cle passe" % permissifs[0][0]
    sans_champ = [t for t in trouves if t[1] == 0]
    if sans_champ:
        return False, "aucun champ declare dans %s" % sans_champ[0][0]
    return True, "%d definition(s), %d champs, extras refuses" % (
        len(trouves), trouves[0][1])


def fonction_englobante(arbre, ligne):
    cands = [n for n in ast.walk(arbre)
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
             and n.lineno <= ligne <= (n.end_lineno or n.lineno)]
    if not cands:
        return "?"
    return min(cands, key=lambda n: (n.end_lineno or n.lineno) - n.lineno).name


CIBLES = [c for c in sorted(Path("app/routers").glob("*.py")) if c.exists()]
CIBLES.append(Path("app/services/prod_machine_filter.py"))

print("--- 1. morceaux de clause SQL ---")
non_prouves, hors_liste = [], []
for f in CIBLES:
    if not f.exists():
        continue
    arbre = ast.parse(f.read_text(encoding="utf-8"), str(f))
    for ligne, code in analyser(f):
        fonc = fonction_englobante(arbre, ligne)
        cle = (str(f), fonc)
        if cle in SITES_REVUS:
            non_prouves.append((cle, ligne))
        else:
            hors_liste.append("%s:%d  (%s)  %s" % (f, ligne, fonc, code[:90]))

check("aucun morceau de clause hors preuve ou hors liste revue (%d fichiers)" % len(CIBLES),
      not hors_liste)
for s_ in hors_liste:
    print("     " + s_)
    print("       -> soit la valeur vient de l'exterieur (injection : corriger),")
    print("          soit elle est bornee (ajouter la fonction a SITES_REVUS).")

print("\n--- 2. les raisons invoquees tiennent-elles encore ? ---")
vus = set()
for (fichier, fonc), ligne in sorted(non_prouves):
    if (fichier, fonc) in vus:
        continue
    vus.add((fichier, fonc))
    info = SITES_REVUS[(fichier, fonc)]
    court = fichier.split("/")[-1]
    if "modele" in info:
        ok, detail = modele_refuse_les_extras(info["modele"])
        check("%-22s %-22s %s -> %s" % (court, fonc, info["modele"], detail), ok)
    elif "constante" in info:
        fc, nom = info["constante"]
        arbre_c = ast.parse(Path(fc).read_text(encoding="utf-8"))
        trouve = any(isinstance(n, (ast.Assign, ast.AnnAssign))
                     and n.value is not None and _litteral_de_chaines(n.value)
                     and nom in ast.dump(n)
                     for n in arbre_c.body)
        check("%-22s %-22s %s est une constante litterale" % (court, fonc, nom), trouve)
    else:
        print("ok   %-22s %-22s %s" % (court, fonc, info["raison"]))

print("\n--- 3. requetes interpolees : les parametres suivent ---")
manquants = []
for f in CIBLES:
    if not f.exists():
        continue
    src = f.read_text(encoding="utf-8")
    for noeud in ast.walk(ast.parse(src, str(f))):
        if not (isinstance(noeud, ast.Call) and isinstance(noeud.func, ast.Attribute)
                and noeud.func.attr in ("execute", "executemany")):
            continue
        if not noeud.args or not isinstance(noeud.args[0], ast.JoinedStr):
            continue
        texte = "".join(v.value for v in noeud.args[0].values if isinstance(v, ast.Constant))
        if "?" in texte and len(noeud.args) < 2:
            manquants.append("%s:%d" % (f, noeud.lineno))
check("toute requete a placeholders passe ses parametres", not manquants)
for s in manquants:
    print("     " + s)

print("\n--- 4. le filtre machine reste en placeholders ---")
src_filtre = Path("app/services/prod_machine_filter.py").read_text(encoding="utf-8")
check("append_machine_filter n'ecrit que des `?`",
      "'?' * len(values)" in src_filtre and "params.extend(values)" in src_filtre)

print("\n--- 5. le garde-fou attrape-t-il vraiment une injection ? ---")
# Un test de securite qui ne se verifie pas lui-meme finit par ne rien verifier :
# une refonte de `analyser()` peut le rendre aveugle sans qu'aucune ligne ne
# rougisse. On lui soumet donc du code volontairement fautif.
import tempfile

PIEGES = {
    "valeur interpolee en clair":
        'where = []\nm = input()\nwhere.append(f"machine = \'{m}\'")\n',
    "valeur concatenee":
        'where = []\nm = input()\nwhere.append("machine = " + m)\n',
    "colonne venant d\'un dict libre":
        'sets = []\nbody = {}\nfor k, v in body.items():\n    sets.append(f"{k}=?")\n',
}
SAINS = {
    "chaine litterale": 'where = []\nwhere.append("machine = ?")\n',
    "boucle sur un tuple litteral":
        'sets = []\nbody = {}\nfor col in ("a", "b"):\n    if col in body:\n        sets.append(f"{col}=?")\n',
    "placeholders generes":
        'where = []\nvalues = [1, 2]\nwhere.append(f"id IN ({\',\'.join(\'?\' * len(values))})")\n',
}

def _analyser_source(code):
    tmp = tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8")
    tmp.write(code); tmp.close()
    try:
        return analyser(Path(tmp.name))
    finally:
        os.unlink(tmp.name)

for nom, code in sorted(PIEGES.items()):
    check("piege detecte : %s" % nom, bool(_analyser_source(code)))
for nom, code in sorted(SAINS.items()):
    check("faux positif evite : %s" % nom, not _analyser_source(code))

print("\n--- 6. la liste blanche ne rouille pas ---")
utilises = {cle for cle, _ in non_prouves}
orphelins = sorted(set(SITES_REVUS) - utilises)
check("aucune entree de SITES_REVUS devenue inutile", not orphelins)
for fichier, fonc in orphelins:
    print("     %s :: %s — le code a change, retirer cette entree" % (fichier, fonc))

print()
print("ECHECS : " + ", ".join(FAIL) if FAIL else "TOUT EST VERT")
sys.exit(1 if FAIL else 0)

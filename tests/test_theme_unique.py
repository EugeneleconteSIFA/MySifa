# -*- coding: utf-8 -*-
"""
Garde-fou : les tokens du theme vivent a UN seul endroit.

Avant le 27/08/2026, le bloc `:root{...}` / `body.light{...}` etait recopie dans
21 pages de `app/web/`. Chaque nouvelle page repartait d'une variante de la
precedente, et les variantes divergeaient : `--accent-bg` existait en 0.08,
0.10 et 0.12 selon la page, `--c1` en deux teintes. Personne ne pouvait dire
quelle etait la bonne valeur.

Les tokens par defaut vivent maintenant dans `static/mysifa_theme.css`, charge
par ces pages AVANT leur `<style>` inline. Chaque page ne redeclare que ses
ecarts reels.

Ce test verifie deux choses :

1. `static/mysifa_theme.css` et `app/web/components/theme.py` disent la meme
   chose. Deux fichiers portent la valeur — le CSS pour le navigateur, le
   Python pour les pages qui n'utilisent pas le lien — donc il faut une
   verification, pas une promesse.

2. La table de tokens RESOLUE de chaque page (defauts + ses ecarts) est restee
   identique a ce qu'elle etait avant la bascule. C'est la preuve qu'aucun
   ecran n'a change d'apparence : le snapshot `tests/theme_resolu.json` a ete
   fige a partir des blocs d'origine.

Lancer : python3 tests/test_theme_unique.py
"""

import json
import os
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
os.chdir(RACINE)
sys.path.insert(0, str(RACINE))

from app.web.components.theme import TOKENS_CSS

FAIL = []


def check(label, ok):
    print(("ok   " if ok else "KO   ") + label)
    if not ok:
        FAIL.append(label)


def norm(v):
    """`.12` et `0.12` sont la meme valeur CSS ; `#FFF` et `#fff` aussi."""
    v = " ".join(v.split()).lower().rstrip(";")
    v = re.sub(r"(?<![\d.])\.(\d)", r"0.\1", v)
    v = re.sub(r"\s*,\s*", ",", v)
    if re.fullmatch(r"#[0-9a-f]{3}", v):
        v = "#" + "".join(c * 2 for c in v[1:])
    return v


def variables(bloc):
    return {m.group(1).strip(): norm(m.group(2))
            for m in re.finditer(r"--([a-z0-9-]+)\s*:\s*([^;}\n]+)", bloc or "", re.I)}


def bloc_de(src, sel):
    for motif in (sel + "{", sel + " {"):
        i = src.find(motif)
        if i >= 0:
            j = src.index("{", i)
            k = src.find("}", j)
            if k > 0:
                return src[j + 1:k]
    return None


CANON_ROOT = variables(TOKENS_CSS.split("body.light")[0])
CANON_LIGHT = variables(TOKENS_CSS.split("body.light")[1])

print("--- 1. le CSS partage et theme.py disent la meme chose ---")
css = Path("static/mysifa_theme.css").read_text(encoding="utf-8")
tete = css.split("/* ── Palette")[0]
check("static/mysifa_theme.css porte le bloc de tokens", ":root{" in tete)
css_root = variables(bloc_de(tete, ":root"))
css_light = variables(bloc_de(tete, "body.light"))
check("meme :root que theme.py (%d variables)" % len(CANON_ROOT), css_root == CANON_ROOT)
check("meme body.light que theme.py (%d variables)" % len(CANON_LIGHT), css_light == CANON_LIGHT)
if css_root != CANON_ROOT:
    for k in sorted(set(css_root) | set(CANON_ROOT)):
        if css_root.get(k) != CANON_ROOT.get(k):
            print("       --%s : css=%s  theme.py=%s" % (k, css_root.get(k), CANON_ROOT.get(k)))

print("\n--- 2. aucun ecran n'a change d'apparence ---")
snapshot = json.loads(Path("tests/theme_resolu.json").read_text(encoding="utf-8"))
check("snapshot present (%d pages)" % len(snapshot), bool(snapshot))

ecarts = []
for nom, attendu in sorted(snapshot.items()):
    f = Path("app/web") / nom
    if not f.exists():
        ecarts.append("%s : fichier disparu" % nom)
        continue
    src = f.read_text(encoding="utf-8", errors="replace")
    resolu_r = dict(CANON_ROOT); resolu_r.update(variables(bloc_de(src, ":root")))
    resolu_l = dict(CANON_LIGHT); resolu_l.update(variables(bloc_de(src, "body.light")))
    for cle, obtenu, att in (("root", resolu_r, attendu["root"]),
                             ("light", resolu_l, attendu["light"])):
        if obtenu != att:
            diff = [k for k in set(obtenu) | set(att) if obtenu.get(k) != att.get(k)]
            ecarts.append("%s [%s] : %s" % (
                nom, cle, ", ".join("--%s %s->%s" % (k, att.get(k), obtenu.get(k))
                                    for k in sorted(diff)[:3])))

check("les %d pages resolvent exactement comme avant la bascule" % len(snapshot), not ecarts)
for e in ecarts:
    print("     " + e)
    print("       -> soit le changement est voulu (mettre a jour theme_resolu.json),")
    print("          soit une page a repris une valeur en dur (la retirer).")

print("\n--- 3. les pages ne redeclarent plus le bloc complet ---")
gros = []
for nom in snapshot:
    src = (Path("app/web") / nom).read_text(encoding="utf-8", errors="replace")
    r = variables(bloc_de(src, ":root"))
    # Une page qui redeclare la quasi-totalite du canonique a recopie le bloc.
    communes = len(set(r) & set(CANON_ROOT))
    if communes >= len(CANON_ROOT) - 2:
        gros.append("%s : %d variables du canonique redeclarees" % (nom, communes))
check("aucune page n'a recopie le bloc complet", not gros)
for g in gros:
    print("     " + g)

print()
print("ECHECS : " + ", ".join(FAIL) if FAIL else "TOUT EST VERT")
sys.exit(1 if FAIL else 0)

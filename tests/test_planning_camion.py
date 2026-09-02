"""
Le camion du planning : sa syntaxe, et ce qu'il rend vraiment.

Deux angles, parce que ni l'un ni l'autre ne suffit.

1. Le JS des pages est ecrit DANS des chaines Python. La CI passe `node --check`
   sur `static/**.js` et `app/**.js` — pas sur ces chaines-la. Une parenthese
   oubliee dans `planning_page.py` part donc en production sans que rien ne
   bronche, et casse la page entiere : un seul script, une seule erreur de
   parsing, plus aucune fonction definie. Ce test ferme ce trou pour les trois
   pages touchees par la contrainte transport.

2. `node --check` ne dit rien de ce que le code PRODUIT. On execute donc pour
   de vrai les fonctions du camion, avec les memes donnees que l'API renvoie :
   pas de camion sans transport, la bonne couleur selon la tension, le
   transporteur echappe, et le clic qui pointe le bon depart.

Lancer : python3 tests/test_planning_camion.py
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
PAGES = [
    RACINE / "app" / "web" / "planning_page.py",
    RACINE / "app" / "web" / "expe_assets.py",
    RACINE / "app" / "web" / "settings_page.py",
]

FAIL = []


def verifier(cas, obtenu, attendu):
    if obtenu != attendu:
        FAIL.append(f"{cas} : obtenu {obtenu!r}, attendu {attendu!r}")
        print(f"  ECHEC  {cas} — obtenu {obtenu!r}, attendu {attendu!r}")
    else:
        print(f"  ok     {cas}")


def vrai(cas, cond):
    verifier(cas, bool(cond), True)


def _node(source: str):
    """Execute un script node et renvoie (code, sortie)."""
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write(source)
        chemin = f.name
    r = subprocess.run(["node", chemin], capture_output=True, text=True)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def _check(source: str):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False,
                                     encoding="utf-8") as f:
        f.write(source)
        chemin = f.name
    r = subprocess.run(["node", "--check", chemin], capture_output=True, text=True)
    return r.returncode == 0, r.stderr.strip()


def _blocs_js(fichier: Path):
    src = fichier.read_text(encoding="utf-8")
    out = []
    for i, b in enumerate(re.findall(r"<script>(.*?)</script>", src, re.S)):
        out.append((f"<script> #{i}", b))
    for nom, b in re.findall(r'^([A-Z_0-9]*JS[A-Z_0-9]*)\s*=\s*r?"""(.*?)"""',
                             src, re.S | re.M):
        out.append((nom, b))
    return [(n, b) for n, b in out if len(b.strip()) >= 30]


# ── 1. Le JS embarque doit parser ─────────────────────────────────────────
print("\n1. Le JS ecrit dans les chaines Python doit parser")

for page in PAGES:
    blocs = _blocs_js(page)
    vrai(f"{page.name} : au moins un bloc JS trouve", len(blocs) > 0)
    for nom, bloc in blocs:
        ok, err = _check(bloc)
        if not ok:
            print("    ", err.split("\n")[1] if "\n" in err else err)
        vrai(f"{page.name} · {nom} : syntaxe valide", ok)


# ── 2. Ce que le camion rend vraiment ─────────────────────────────────────
print("\n2. Rendu du camion")

src = (RACINE / "app" / "web" / "planning_page.py").read_text(encoding="utf-8")
debut = src.index("// ── Transport réservé")
fin = src.index("function fscBadgeHtml(e){", debut)
bloc_camion = src[debut:fin]

PRELUDE = """
function escAttr(s){return String(s??"").replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;");}
"""


def rendre(slot):
    code = PRELUDE + bloc_camion + "\nconsole.log(transportBadgeHtml(" + json.dumps(slot) + "));"
    rc, sortie = _node(code)
    if rc != 0:
        FAIL.append("execution du rendu : " + sortie)
        print("  ECHEC  execution du rendu —", sortie.strip()[:200])
        return ""
    return sortie.strip()


TRANSPORT = {
    "depart_id": 2848,
    "transporteur": "MEHEZ",
    "date_enlevement": "2026-09-10",
    "palettes": 11.0,
    "source_palettes": "expe",
    "limite": "2026-09-10T11:00:00",
    "heure_limite": 11.0,
    "marge_pct": 20.0,
    "marge_heures": 2.0,
    "tension": "ok",
    "departs": [],
}

verifier("aucun transport : rien n'est rendu", rendre({"transport": None}), "")
verifier("champ absent : rien n'est rendu", rendre({}), "")

html = rendre({"transport": TRANSPORT})
vrai("un camion est rendu", "slot-camion" in html)
vrai("l'icone est un SVG inline", "<svg" in html and "</svg>" in html)
vrai("marge confortable : vert", "var(--success)" in html)
vrai("le transporteur est dans l'infobulle", "MEHEZ" in html)
vrai("la date d'enlevement est lisible en francais", "10/09/2026" in html)
vrai("l'heure limite est annoncee", "avant 11h" in html)
vrai("les palettes sont annoncees", "11" in html)
vrai("le clic pointe le bon depart", "ouvrirDepartExpe(2848)" in html)
vrai("le clic ne declenche pas le creneau", "event.stopPropagation()" in html)
vrai("aucun emoji", all(ord(c) < 0x2190 for c in html))

juste = rendre({"transport": {**TRANSPORT, "tension": "juste"}})
vrai("battement court : ambre", "var(--warn)" in juste)
depasse = rendre({"transport": {**TRANSPORT, "tension": "depasse"}})
vrai("fin apres l'enlevement : rouge", "var(--danger)" in depasse)

vrai("aucune couleur codee en dur",
     not re.search(r"#[0-9a-fA-F]{3,6}", html + juste + depasse))

sale = rendre({"transport": {**TRANSPORT,
                             "transporteur": 'TRANS "X" <script>alert(1)</script>'}})
vrai("le nom de transporteur est echappe", "<script>" not in sale)
vrai("les guillemets sont echappes", "&quot;" in sale)

sans_id = rendre({"transport": {**TRANSPORT, "depart_id": None}})
vrai("depart sans id : camion affiche", "slot-camion" in sans_id)
vrai("depart sans id : pas de clic mort", "ouvrirDepartExpe" not in sans_id)

print()
if FAIL:
    print(f"ECHEC : {len(FAIL)} cas")
    for f in FAIL:
        print("  -", f)
    sys.exit(1)
print("Camion du planning : tous les cas passent.")

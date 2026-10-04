# -*- coding: utf-8 -*-
"""Registre des blocs capturables en widget d'accueil.

Ce que ce test protège :

1. **Un widget ne casse pas en silence.** Chaque bloc du registre doit exister
   dans le code (un data-bloc qui le porte). Un bloc retiré d'une page sans
   alias laisserait les widgets des utilisateurs sur un bloc fantôme.
2. **Un nom de bloc n'est porté que par un seul fichier.** Deux pages qui
   déclarent le même nom : le widget ne saurait pas laquelle charger.
3. **Un data-bloc du code est déclaré au registre.** Sinon il est invisible à
   la capture — le plus souvent une faute de frappe.
4. **La validation serveur tient ses promesses** : 4 valeurs au maximum, URL
   interne uniquement, clés et alertes contrôlées.
5. **Un bloc déplacé garde ses widgets** : l'URL suit l'emplacement actuel et
   conserve les filtres capturés.

Lancer : python3 tests/test_blocs_registre.py
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
os.chdir(RACINE)
sys.path.insert(0, str(RACINE))

# Module pur : aucun import de base ni de FastAPI.
import importlib.util

_spec = importlib.util.spec_from_file_location("blocs_registre", RACINE / "app/services/blocs_registre.py")
reg = importlib.util.module_from_spec(_spec)
sys.modules["blocs_registre"] = reg
_spec.loader.exec_module(reg)

# data-bloc="x" (HTML), 'data-bloc':'x' (h()/el()), "data-bloc": "x" — jamais
# data-bloc-valeur-… ni data-bloc-objet (le caractère suivant est un guillemet,
# un « = » ou un « : »).
MOTIF = re.compile(r"""['"]?data-bloc['"]?\s*[:=]\s*['"]([a-z0-9][a-z0-9.\-]*)['"]""")
# Le moteur et sa documentation citent des exemples de noms : hors périmètre.
EXCLUS = {"static/mysifa_blocs.js", "static/mysifa_accueil.js"}

echecs = []


def verifier(cond, msg):
    if not cond:
        echecs.append(msg)


def _fichiers():
    for f in list(Path("app/web").rglob("*.py")) + list(Path("static").rglob("*.js")):
        rel = f.as_posix()
        if rel in EXCLUS or "/__pycache__/" in rel:
            continue
        try:
            yield rel, f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue


TEXTES = dict(_fichiers())


def noms_dans_le_code() -> dict[str, set[str]]:
    """Noms posés directement en data-bloc (le cas courant)."""
    trouves: dict[str, set[str]] = {}
    for rel, texte in TEXTES.items():
        for m in MOTIF.finditer(texte):
            trouves.setdefault(m.group(1), set()).add(rel)
    return trouves


def fichiers_citant(nom: str) -> set[str]:
    """Fichiers où le nom apparaît en chaîne littérale. Un bloc peut recevoir
    son nom selon le cas (`bloc = cle === 'a' ? 'x.y.a' : 'x.y.b'`) : le
    registre est alors cité sans être collé à « data-bloc »."""
    motif = re.compile(r"""['"]""" + re.escape(nom) + r"""['"]""")
    return {rel for rel, texte in TEXTES.items() if motif.search(texte)}


# ── 1-3. Registre ↔ code ────────────────────────────────────────────────
for e in reg.erreurs_registre():
    verifier(False, "registre : " + e)

code = noms_dans_le_code()
for nom in reg.BLOCS:
    cites = fichiers_citant(nom)
    verifier(cites, f"{nom} : déclaré au registre mais absent du code "
                    "(bloc retiré ? poser son nom en alias du bloc qui le remplace)")
    verifier(len(cites) <= 1, f"{nom} : porté par plusieurs fichiers {sorted(cites)}")
for nom, fichiers in code.items():
    verifier(reg.resoudre(nom) is not None,
             f"{nom} : data-bloc présent dans {sorted(fichiers)} mais absent du registre")
    verifier(nom not in reg._index_alias(),
             f"{nom} : le code utilise un ancien nom (alias) — utiliser le nom actuel")

# ── 4. Validation ───────────────────────────────────────────────────────
NOM_TEST = "test.onglet.bloc"
reg.BLOCS[NOM_TEST] = reg.Bloc(
    appli="test", libelle="Bloc de test", url="/test?tab=a#vue", type="liste",
    valeurs=(("lignes", "Lignes"), ("a", "A"), ("b", "B"), ("c", "C"), ("d", "D")),
    alias=("test.ancien.bloc",),
)


def creer(**k):
    base = {"bloc": NOM_TEST, "url_capture": "/test?tab=a#vue", "nom": "Mon widget",
            "valeurs": [{"cle": "lignes"}], "affichage": "bloc", "hauteur": "m"}
    base.update(k)
    return reg.valider_widget(base, creation=True)


def refuse(msg, **k):
    try:
        creer(**k)
    except ValueError:
        return
    verifier(False, "devrait être refusé : " + msg)


ok = creer()
verifier(ok["bloc"] == NOM_TEST and ok["valeurs"] == [{"cle": "lignes", "alerte": None}], "création simple")
verifier(creer(bloc="test.ancien.bloc")["bloc"] == NOM_TEST, "un alias est résolu vers le nom actuel")

cinq = [{"cle": c} for c in ("lignes", "a", "b", "c", "d")]
refuse("5 valeurs", valeurs=cinq)
verifier(len(creer(valeurs=cinq[:4])["valeurs"]) == 4, "4 valeurs acceptées")
refuse("clé inconnue", valeurs=[{"cle": "inconnue"}])
refuse("clé en double", valeurs=[{"cle": "a"}, {"cle": "a"}])
refuse("bloc inconnu", bloc="nexiste.pas.du-tout")
refuse("url absolue", url_capture="https://exemple.com/stock")
refuse("url protocole relatif", url_capture="//exemple.com/stock")
refuse("url relative", url_capture="stock?tab=a")
refuse("nom vide", nom="   ")
refuse("nom trop long", nom="x" * 81)
refuse("hauteur", hauteur="xl")
refuse("affichage", affichage="graphique")
refuse("aucune valeur cochée", valeurs=[])
verifier(creer(affichage=None)["affichage"] == "valeurs", "affichage « valeurs » par défaut")
refuse("opérateur d'alerte", valeurs=[{"cle": "a", "alerte": {"op": ">=", "seuil": "3"}}])
refuse("seuil non numérique", valeurs=[{"cle": "a", "alerte": {"op": ">", "seuil": "beaucoup"}}])
refuse("seuil vide", valeurs=[{"cle": "a", "alerte": {"op": "<", "seuil": ""}}])
etat = creer(valeurs=[{"cle": "a", "alerte": {"op": "=", "seuil": "Arrêt"}}])
verifier(etat["valeurs"][0]["alerte"] == {"op": "=", "seuil": "Arrêt"}, "alerte sur un état acceptée")
verifier(creer(valeurs=[{"cle": "a", "alerte": {"op": ">", "seuil": "12,5"}}])["valeurs"][0]["alerte"]["seuil"] == "12,5",
         "seuil décimal à virgule accepté")

# ── 5. Bloc déplacé ─────────────────────────────────────────────────────
verifier(reg.url_widget(NOM_TEST, "/test?tab=a&client=7#vue") == "/test?tab=a&client=7#vue",
         "même emplacement : URL capturée conservée")
reg.BLOCS[NOM_TEST] = reg.Bloc(
    appli="test", libelle="Bloc de test", url="/autre?tab=b#ailleurs", type="liste",
    alias=("test.ancien.bloc",),
)
deplace = reg.url_widget("test.ancien.bloc", "/test?tab=a&client=7#vue")
verifier(deplace == "/autre?tab=b&client=7#ailleurs",
         f"bloc déplacé : nouvel emplacement + filtres capturés (obtenu {deplace!r})")
verifier(reg.url_widget("nexiste.pas.du-tout", "/x") is None, "bloc disparu : pas d'URL")
del reg.BLOCS[NOM_TEST]

if echecs:
    print("ÉCHEC test_blocs_registre :")
    for e in echecs:
        print("  -", e)
    sys.exit(1)
print(f"test_blocs_registre : OK ({len(reg.BLOCS)} blocs au registre, {len(code)} noms dans le code)")

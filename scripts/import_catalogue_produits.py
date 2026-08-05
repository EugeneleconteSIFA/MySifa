# -*- coding: utf-8 -*-
"""
Import du catalogue « Table Matières » dans les produits MyStock de Coûts matières.

Chaque ligne du catalogue est un produit fini : un frontal, un adhésif et une
glassine. Le script les crée dans `mp_produit` et rattache les DÉCLINAISONS
MyStock correspondantes, de sorte que le coût de revient se calcule tout seul.

Le catalogue est figé dans ce fichier : le script tourne sur le VPS sans Excel
ni dépendance à installer.

──────────────────────────────────────────────────────────────────────────────
Trois étapes, dans cet ordre
──────────────────────────────────────────────────────────────────────────────

  1.  python3 scripts/import_catalogue_produits.py --inventaire

      Liste les matières MyStock et propose une correspondance pour chaque
      frontal, chaque famille d'adhésif et la glassine. Rien n'est écrit.
      Recopiez le bloc CORRESPONDANCES affiché dans ce fichier, et corrigez
      ce que la proposition a raté.

  2.  python3 scripts/import_catalogue_produits.py --simulation

      Rejoue tout l'import sans rien enregistrer : produits qui seraient créés,
      déclinaisons qui seraient ajoutées, et ce qui bloque.

  3.  python3 scripts/import_catalogue_produits.py --appliquer

      Écrit. Relançable : un produit déjà présent est mis à jour, pas dupliqué.

Options : --db /chemin/production.db pour viser une autre base.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

# ─────────────────────────────────────────────────────────────────────────────
# Correspondances — à compléter avec la sortie de --inventaire
# ─────────────────────────────────────────────────────────────────────────────
# Laissez vide pour que le script propose lui-même une correspondance par le
# nom. Une entrée renseignée fait autorité : c'est le moyen de corriger un
# rapprochement douteux sans toucher au reste.
#
#   "nom du catalogue": "référence MyStock"

FRONTAUX = {
    "Couché Brillant 80g": "80gsm Coated Paper",
    "Synthé. 95µm 71g": "PP blanc mat 95µm",
    "Thermique Eco 70g": "70g Eco Thermal",
    "Thermique Eco Bicolore 74g": "Thermique Bicolore",
    # Le stock ne connaît que du 105 gsm — c'est le plus proche du 108 g
    # commercial, et il n'y a pas d'autre thermique pro épais.
    "Thermique Pro 108g": "TOP Thermal 105gsm",
    "Thermique Pro 70g": "70gsm TOP Thermal",
    "Velin 62g": "62gsm Vellum",
    "Velin 68g": "68gsm Vellum",
    # Aucun vélin fluo en 90 g au stock : c'est le couché 90 fluo qui part.
    "Velin Jaune Fluo 90g": "couché 90gsm fluo jaune",
}

# « toujours le même enlevable, toujours le même congélation » : une seule
# matière MyStock par famille, le grammage fait la déclinaison.
ADHESIFS = {
    "Enlevable": "1408",        # enlevable fort (MELTAVIS)
    "Permanent": "2028Y",       # permanent (JAOUR)
    "Congélation": "2030",      # congélation (JAOUR)
    "Permanent Pneu": "2288M",  # pneu (JAOUR)
}

# Une seule glassine pour tout le catalogue.
GLASSINE = "60gsm glassine jaune siliconné"

# ─────────────────────────────────────────────────────────────────────────────
# Catalogue
# ─────────────────────────────────────────────────────────────────────────────
# (code, désignation, frontal, famille d'adhésif, grammage de colle en g/m²)
CATALOGUE = [
    ('886-0001', 'Thermique Pro 70g · Enlevable 22g, Jaune 60g standard', 'Thermique Pro 70g', 'Enlevable', 22),
    ('886-0002', 'Thermique Pro 70g · Permanent 19g, Jaune 60g Standard', 'Thermique Pro 70g', 'Permanent', 19),
    ('886-0003', 'Thermique Pro 70g · Permanent 22g, Jaune 60g Standard', 'Thermique Pro 70g', 'Permanent', 22),
    ('886-0004', 'Thermique Pro 70g · Permanent 25g, Jaune 60g Standard', 'Thermique Pro 70g', 'Permanent', 25),
    ('886-0005', 'Thermique Pro 70g · Permanent 17g, Jaune 60g Standard', 'Thermique Pro 70g', 'Permanent', 17),
    ('886-0006', 'Thermique Pro 70g · Congélation 22g, Jaune 60g Standard', 'Thermique Pro 70g', 'Congélation', 22),
    ('886-0007', 'Thermique Pro 70g · Congélation 30g, Jaune 60g Standard', 'Thermique Pro 70g', 'Congélation', 30),
    ('886-0019', 'Thermique Eco 70g · Enlevable 19g, Jaune 60g standard', 'Thermique Eco 70g', 'Enlevable', 19),
    ('886-0020', 'Thermique Eco 70g · Enlevable 22g, Jaune 60g standard', 'Thermique Eco 70g', 'Enlevable', 22),
    ('886-0021', 'Thermique Eco 70g · Permanent 19g, Jaune 60g Standard', 'Thermique Eco 70g', 'Permanent', 19),
    ('886-0022', 'Thermique Eco 70g · Permanent 22g, Jaune 60g Standard', 'Thermique Eco 70g', 'Permanent', 22),
    ('886-0023', 'Thermique Eco 70g · Permanent 25g, Jaune 60g Standard', 'Thermique Eco 70g', 'Permanent', 25),
    ('886-0024', 'Thermique Eco 70g · Congélation 22g, Jaune 60g Standard', 'Thermique Eco 70g', 'Congélation', 22),
    ('886-0025', 'Thermique Eco 70g · Congélation 28g, Jaune 60g Standard', 'Thermique Eco 70g', 'Congélation', 28),
    ('886-0033', 'Thermique Eco Bicolore 74g · Enlevable 22g, Jaune 60g Standard', 'Thermique Eco Bicolore 74g', 'Enlevable', 22),
    ('886-0034', 'Thermique Eco Bicolore 74g · Permanent 19g, Jaune 60g Standard', 'Thermique Eco Bicolore 74g', 'Permanent', 19),
    ('886-0035', 'Thermique Pro 108g · Permanent 19g, Jaune 60g Standard', 'Thermique Pro 108g', 'Permanent', 19),
    ('886-0036', 'Thermique Pro 70g · Permanent Pneu 55g, Jaune 60g', 'Thermique Pro 70g', 'Permanent Pneu', 55),
    ('886-0037', 'Thermique Pro 108g · Permanent Pneu 55g, Jaune 60g', 'Thermique Pro 108g', 'Permanent Pneu', 55),
    ('886-0100', 'Couché Brillant 80g · Enlevable 19g, Jaune 60g standard', 'Couché Brillant 80g', 'Enlevable', 19),
    ('886-0101', 'Couché Brillant 80g · Enlevable 22g, Jaune 60g standard', 'Couché Brillant 80g', 'Enlevable', 22),
    ('886-0102', 'Couché Brillant 80g · Enlevable 17g, Jaune 60g standard', 'Couché Brillant 80g', 'Enlevable', 17),
    ('886-0103', 'Couché Brillant 80g · Permanent 17g, Jaune 60g standard', 'Couché Brillant 80g', 'Permanent', 17),
    ('886-0104', 'Couché Brillant 80g · Permanent 19g, Jaune 60g standard', 'Couché Brillant 80g', 'Permanent', 19),
    ('886-0105', 'Couché Brillant 80g · Congélation 22g, Jaune 60g standard', 'Couché Brillant 80g', 'Congélation', 22),
    ('886-0200', 'Synthé. 95µm 71g · Permanent 19g, Jaune 60g standard', 'Synthé. 95µm 71g', 'Permanent', 19),
    ('886-0201', 'Synthé. 95µm 71g · Permanent 22g, Jaune 60g standard', 'Synthé. 95µm 71g', 'Permanent', 22),
    ('886-0202', 'Synthé. 95µm 71g · Permanent 25g, Jaune 60g standard', 'Synthé. 95µm 71g', 'Permanent', 25),
    ('886-0203', 'Synthé. 95µm 71g · Permanent 30g, Jaune 60g standard', 'Synthé. 95µm 71g', 'Permanent', 30),
    ('886-0204', 'Synthé. 95µm 71g · Permanent 40g, Jaune 60g standard', 'Synthé. 95µm 71g', 'Permanent', 40),
    ('886-0300', 'Velin 62g · Enlevable 19g, Jaune 60g Standard', 'Velin 62g', 'Enlevable', 19),
    ('886-0301', 'Velin 62g · Enlevable 22g, Jaune 60g Standard', 'Velin 62g', 'Enlevable', 22),
    ('886-0302', 'Velin 62g · Permanent 19g, Jaune 60g Standard', 'Velin 62g', 'Permanent', 19),
    ('886-0303', 'Velin 62g · Congélation 22g, Jaune 60g Standard', 'Velin 62g', 'Congélation', 22),
    ('886-0305', 'Velin 68g · Enlevable 19g, Jaune 60g Standard', 'Velin 68g', 'Enlevable', 19),
    ('886-0306', 'Velin 68g · Enlevable 22g, Jaune 60g Standard', 'Velin 68g', 'Enlevable', 22),
    ('886-0307', 'Velin 68g · Permanent 19g, Jaune 60g Standard', 'Velin 68g', 'Permanent', 19),
    ('886-0308', 'Velin 68g · Congélation 22g, Jaune 60g Standard', 'Velin 68g', 'Congélation', 22),
    ('886-0312', 'Velin Jaune Fluo 90g · Enlevable 22g, Jaune 60g Standard', 'Velin Jaune Fluo 90g', 'Enlevable', 22),
    ('886-0313', 'Velin Jaune Fluo 90g · Permanent 19g, Jaune 60g Standard', 'Velin Jaune Fluo 90g', 'Permanent', 19),
    ('886-0314', 'Velin Jaune Fluo 90g · Enlevable 19g, Jaune 60g Standard', 'Velin Jaune Fluo 90g', 'Enlevable', 19),
    ('886-0315', 'Velin 62g · Congélation 30g, Jaune 60g Standard', 'Velin 62g', 'Congélation', 30),
]

CATEGORIES = {"frontal": "frontal", "adhesif": "adhesif", "glassine": "glassine"}


# ─────────────────────────────────────────────────────────────────────────────
# Rapprochement par le nom
# ─────────────────────────────────────────────────────────────────────────────


def _sans_accents(txt: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", txt or "")
        if unicodedata.category(c) != "Mn"
    )


_PETITS = {"de", "du", "la", "le", "les", "et", "en", "g", "gr", "gsm", "um", "micron", "microns"}

# Les références MyStock sont en anglais technique, le catalogue en français
# commercial : « 62gsm Vellum » et « Velin 62g » désignent la même chose. Sans
# ce petit lexique, la proposition automatique passe à côté de l'essentiel.
_LEXIQUE = {
    "vellum": "velin",
    "coated": "couche",
    "paper": "papier",
    "thermal": "thermique",
    "top": "pro",
    "yellow": "jaune",
    "white": "blanc",
    "matt": "mat",
    "freezer": "congelation",
    "removable": "enlevable",
    "permanent": "permanent",
    "tyre": "pneu",
    "tire": "pneu",
    "pp": "synthe",
    "synthetique": "synthe",
    "bicolore": "bicolore",
}


def _mots(txt: str) -> set[str]:
    """
    Mots signifiants d'un libellé, accents et ponctuation retirés.

    Les chiffres sont détachés des lettres : « 95µm » et « 95 microns » doivent
    donner le même « 95 », sinon un grammage collé à son unité ne se rapproche
    jamais de sa version espacée.
    """
    t = _sans_accents(str(txt or "")).lower().replace("µ", "u")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    t = re.sub(r"(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])", " ", t)
    return {
        _LEXIQUE.get(m, m) for m in t.split() if m and m not in _PETITS
    }


def _correspond(a: str, b: str) -> bool:
    """
    Deux mots désignent-ils la même chose ?

    « synthe » et « synthetique » oui — les abréviations sont courantes dans les
    libellés commerciaux. « 62 » et « 628 » non : sur un nombre, seule l'égalité
    compte, sinon on confondrait deux grammages voisins.
    """
    if a == b:
        return True
    if a.isdigit() or b.isdigit():
        return False
    court, long_ = (a, b) if len(a) <= len(b) else (b, a)
    return len(court) >= 4 and long_.startswith(court)


def _score(cible: str, candidat: str) -> float:
    """Part des mots de la cible retrouvés dans le candidat, 0 à 1."""
    a, b = _mots(cible), _mots(candidat)
    if not a:
        return 0.0
    commun = sum(1 for x in a if any(_correspond(x, y) for y in b))
    # Un candidat très bavard qui contient tout par hasard ne doit pas gagner.
    return commun / len(a) * (1 - 0.02 * max(0, len(b) - len(a)))


def proposer(cible: str, matieres: list[sqlite3.Row]) -> tuple[str, float]:
    meilleur, note = "", 0.0
    for m in matieres:
        s = max(_score(cible, m["reference"]), _score(cible, m["designation"]))
        if s > note:
            meilleur, note = m["reference"], s
    return meilleur, note


# ─────────────────────────────────────────────────────────────────────────────
# Lecture de la base
# ─────────────────────────────────────────────────────────────────────────────


# Le chemin par défaut vient de config.py. Sur le serveur, l'instance de test
# tourne sur la base de la production via une variable d'environnement : lancé à
# la main, le script ne la voit pas et tombe sur un fichier vide.
_AIDE_BASE = """
Le chemin par défaut vient de config.py (DB_PATH). Si l'application tourne avec
une autre base — c'est le cas quand une instance de test partage celle de la
production — passez-la explicitement :

    python3 scripts/import_catalogue_produits.py --inventaire --db /chemin/production.db

Pour retrouver le chemin utilisé par l'application en service :

    tr '\\0' '\\n' < /proc/$(pgrep -f uvicorn | head -1)/environ | grep DB_PATH
"""

TABLES_REQUISES = (
    "matieres_premieres",
    "mp_matiere_declinaison",
    "mp_matiere_prix",
    "mp_produit",
)


def tables_manquantes(conn) -> list[str]:
    """Vérifie que la base est bien celle de l'application, avant tout travail."""
    presentes = {
        r["name"]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    return [t for t in TABLES_REQUISES if t not in presentes]


def matieres_par_categorie(conn, categorie: str) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT id, reference, designation FROM matieres_premieres
            WHERE LOWER(categorie)=? AND actif=1
            ORDER BY reference COLLATE NOCASE""",
        (categorie,),
    ).fetchall()


def matiere_par_reference(conn, reference: str) -> sqlite3.Row | None:
    return conn.execute(
        "SELECT id, reference, designation, categorie FROM matieres_premieres "
        "WHERE reference=? COLLATE NOCASE",
        (reference,),
    ).fetchone()


def declinaison_la_moins_chere(conn, matiere_id: int) -> int | None:
    """
    Déclinaison retenue pour un frontal : celle qui coûte le moins au m².

    Le catalogue ne dit pas la laize, et le prix au m² varie peu de l'une à
    l'autre : partir de la moins chère donne une base de devis prudente.
    """
    rows = conn.execute(
        """SELECT d.id, COALESCE(p.prix, 0) AS prix
             FROM mp_matiere_declinaison d
             LEFT JOIN mp_matiere_prix p
                    ON p.declinaison_id = d.id AND p.principal = 1
            WHERE d.matiere_id = ?
            ORDER BY CASE WHEN COALESCE(p.prix,0) > 0 THEN 0 ELSE 1 END,
                     COALESCE(p.prix, 0), d.id""",
        (matiere_id,),
    ).fetchall()
    return int(rows[0]["id"]) if rows else None


def declinaison_par_grammage(conn, matiere_id: int, gsm: float) -> int | None:
    row = conn.execute(
        """SELECT d.id FROM mp_matiere_declinaison d
             JOIN mp_grammages g ON g.id = d.grammage_id
            WHERE d.matiere_id = ? AND ABS(g.valeur_gsm - ?) < 0.001""",
        (matiere_id, float(gsm)),
    ).fetchone()
    return int(row["id"]) if row else None


# ─────────────────────────────────────────────────────────────────────────────
# Étape 1 — inventaire
# ─────────────────────────────────────────────────────────────────────────────


def inventaire(conn) -> int:
    for cat in ("frontal", "adhesif", "glassine"):
        mats = matieres_par_categorie(conn, cat)
        print(f"\n=== {cat.upper()} — {len(mats)} matière(s) active(s) ===")
        for m in mats:
            decls = conn.execute(
                """SELECT COUNT(*) AS n FROM mp_matiere_declinaison WHERE matiere_id=?""",
                (m["id"],),
            ).fetchone()["n"]
            print(f"  {m['reference']:<18} {(m['designation'] or '')[:58]:<58} {decls} décl.")

    frontaux = matieres_par_categorie(conn, "frontal")
    adhesifs = matieres_par_categorie(conn, "adhesif")
    glassines = matieres_par_categorie(conn, "glassine")

    print("\n\n" + "=" * 78)
    print("Bloc CORRESPONDANCES proposé — à recopier en tête de ce fichier")
    print("Vérifiez chaque ligne : « ? » signale un rapprochement peu sûr.")
    print("=" * 78)

    print("\nFRONTAUX = {")
    for nom in sorted({c[2] for c in CATALOGUE}):
        ref, note = proposer(nom, frontaux)
        marque = "" if note >= 0.75 else "   # ? à vérifier"
        print(f'    {nom!r}: {ref!r},{marque}')
    print("}")

    print("\nADHESIFS = {")
    for fam in sorted({c[3] for c in CATALOGUE}):
        ref, note = proposer(fam, adhesifs)
        marque = "" if note >= 0.75 else "   # ? à vérifier"
        print(f'    {fam!r}: {ref!r},{marque}')
    print("}")

    ref, note = proposer("Jaune 60g", glassines)
    print(f'\nGLASSINE = {ref!r}' + ("" if note >= 0.6 else "   # ? à vérifier"))
    print()
    return 0


# ─────────────────────────────────────────────────────────────────────────────
# Étapes 2 et 3 — simulation et import
# ─────────────────────────────────────────────────────────────────────────────


def resoudre_correspondances(conn) -> tuple[dict, list[str]]:
    """Traduit les noms du catalogue en identifiants MyStock."""
    erreurs: list[str] = []
    res = {"frontal": {}, "adhesif": {}, "glassine": None}

    frontaux = matieres_par_categorie(conn, "frontal")
    for nom in sorted({c[2] for c in CATALOGUE}):
        ref = FRONTAUX.get(nom) or proposer(nom, frontaux)[0]
        m = matiere_par_reference(conn, ref) if ref else None
        if not m:
            erreurs.append(f"frontal sans correspondance : « {nom} » (réf. essayée : {ref or '—'})")
            continue
        res["frontal"][nom] = m

    adhesifs = matieres_par_categorie(conn, "adhesif")
    for fam in sorted({c[3] for c in CATALOGUE}):
        ref = ADHESIFS.get(fam) or proposer(fam, adhesifs)[0]
        m = matiere_par_reference(conn, ref) if ref else None
        if not m:
            erreurs.append(f"adhésif sans correspondance : « {fam} » (réf. essayée : {ref or '—'})")
            continue
        res["adhesif"][fam] = m

    glassines = matieres_par_categorie(conn, "glassine")
    ref = GLASSINE or proposer("Jaune 60g", glassines)[0]
    m = matiere_par_reference(conn, ref) if ref else None
    if not m:
        erreurs.append(f"glassine sans correspondance (réf. essayée : {ref or '—'})")
    else:
        res["glassine"] = m
    return res, erreurs


def executer(conn, *, appliquer: bool) -> int:
    from app.services import mystock_prix, mystock_produits

    corr, erreurs = resoudre_correspondances(conn)
    for e in erreurs:
        print("  BLOQUANT :", e)
    if erreurs:
        print("\nComplétez le bloc CORRESPONDANCES en tête du fichier "
              "(voir --inventaire), puis relancez.")
        return 1

    print("Correspondances retenues")
    for nom, m in sorted(corr["frontal"].items()):
        print(f"  frontal   {nom:<28} -> {m['reference']}")
    for fam, m in sorted(corr["adhesif"].items()):
        print(f"  adhésif   {fam:<28} -> {m['reference']}")
    print(f"  glassine  {'(toutes lignes)':<28} -> {corr['glassine']['reference']}")

    # La déclinaison d'un frontal ne dépend pas du produit : on la résout une
    # fois par matière plutôt que 42 fois.
    decl_frontal: dict[str, int] = {}
    for nom, m in corr["frontal"].items():
        d = declinaison_la_moins_chere(conn, int(m["id"]))
        if d is None:
            print(f"  BLOQUANT : le frontal {m['reference']} n'a aucune déclinaison")
            return 1
        decl_frontal[nom] = d

    decl_glassine = declinaison_la_moins_chere(conn, int(corr["glassine"]["id"]))
    if decl_glassine is None:
        print(f"  BLOQUANT : la glassine {corr['glassine']['reference']} n'a aucune déclinaison")
        return 1

    crees = maj = ignores = decl_creees = 0
    print("\nProduits")
    for code, designation, front, fam, gsm in CATALOGUE:
        mat_adh = corr["adhesif"][fam]
        d_adh = declinaison_par_grammage(conn, int(mat_adh["id"]), gsm)
        if d_adh is None:
            # Le grammage de colle n'existe pas encore chez cet adhésif : on le
            # décline (sans prix — il reste à paramétrer dans Coûts matières).
            r = mystock_prix.add_declinaison(
                conn, matiere_id=int(mat_adh["id"]), valeur_gsm=gsm
            )
            if not r.get("ok"):
                print(f"  IGNORÉ  {code} : {mat_adh['reference']} en {gsm:g} g/m² — {r.get('reason')}")
                ignores += 1
                continue
            d_adh = r["declinaison_id"]
            decl_creees += 1
            print(f"  + déclinaison {mat_adh['reference']} en {gsm:g} g/m² (prix à renseigner)")

        composants = [
            {"declinaison_id": decl_frontal[front], "role": "FRONTAL"},
            {"declinaison_id": d_adh, "role": "ADHESIF"},
            {"declinaison_id": decl_glassine, "role": "GLASSINE"},
        ]
        existant = conn.execute(
            "SELECT id FROM mp_produit WHERE code=? COLLATE NOCASE", (code,)
        ).fetchone()
        if existant:
            r = mystock_produits.modifier_produit(
                conn, int(existant["id"]),
                patch={"designation": designation, "composants": composants},
                user_name="import catalogue",
            )
            etat = "maj    "
            maj += 1
        else:
            r = mystock_produits.creer_produit(
                conn, code=code, designation=designation,
                composants=composants, user_name="import catalogue",
            )
            etat = "créé   "
            crees += 1
        if not r.get("ok"):
            print(f"  IGNORÉ  {code} : {r.get('reason')}")
            ignores += 1
            crees -= 1 if etat.startswith("créé") else 0
            maj -= 1 if etat.startswith("maj") else 0
            continue
        print(f"  {etat} {code}  {designation[:64]}")

    print(f"\n{crees} créé(s), {maj} mis à jour, {ignores} ignoré(s), "
          f"{decl_creees} déclinaison(s) ajoutée(s).")
    if appliquer:
        conn.commit()
        print("Enregistré.")
    else:
        conn.rollback()
        print("SIMULATION — rien n'a été enregistré. Relancez avec --appliquer.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--inventaire", action="store_true",
                   help="liste les matières MyStock et propose les correspondances")
    g.add_argument("--simulation", action="store_true",
                   help="rejoue l'import sans rien enregistrer")
    g.add_argument("--appliquer", action="store_true", help="enregistre")
    ap.add_argument("--db", default=None, help="chemin de la base (défaut : config)")
    args = ap.parse_args()

    chemin = args.db
    if not chemin:
        from config import DB_PATH
        chemin = DB_PATH
    print(f"Base : {chemin}\n")
    if not Path(chemin).exists():
        print("Cette base n'existe pas.\n" + _AIDE_BASE)
        return 2
    conn = sqlite3.connect(chemin)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    manquantes = tables_manquantes(conn)
    if manquantes:
        conn.close()
        print("Cette base ne contient pas " + ", ".join(manquantes) + ".")
        print("Ce n'est pas la base de l'application.\n" + _AIDE_BASE)
        return 2
    try:
        if args.inventaire:
            return inventaire(conn)
        return executer(conn, appliquer=args.appliquer)
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

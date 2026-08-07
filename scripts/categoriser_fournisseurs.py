#!/usr/bin/env python3
"""
Propose une catégorie aux fiches fournisseurs qui n'en ont pas.

Pourquoi
--------
Les catégories pilotent les « favoris » de la recherche fournisseur : sur
l'écran de réception d'un adhésif, les fournisseurs d'adhésif remontent en
tête. Une fiche sans catégorie reste trouvable — elle ne remonte simplement
jamais. Après un import de 200 lignes d'export ERP, qui ne dit rien des
catégories, la fonctionnalité existe sans se voir.

Deux sources, dans cet ordre
----------------------------
1. **Les liens réels déjà en base.** Un fournisseur rattaché à un adhésif
   dans `mp_matiere_prix`, `matiere_laize_fournisseurs` ou
   `mc_tarif_fournisseur` EST un fournisseur d'adhésif : ce n'est pas une
   supposition, c'est une donnée que quelqu'un a saisie. Priorité absolue.

2. **Le nom, à défaut.** « BURBAN PALETTES » vend des palettes, « Cartonnages
   du Nord » du carton. C'est une heuristique, et elle est marquée comme telle
   dans le rapport.

Ce que le script ne fait PAS
---------------------------
- Il ne retire jamais une catégorie déjà posée : il ajoute.
- Il ne force pas une catégorie sur tout le monde. Une fiche qu'aucune règle
  ne reconnaît reste sans catégorie. Une catégorie fausse est PIRE que pas de
  catégorie : elle fait remonter le mauvais fournisseur en tête de liste sur
  l'écran de réception, à l'endroit exact où l'on veut aller vite.
- Il ne devine pas le transporteur : « FRANCE EXPRESS » ou « AFFRETOO » ne
  sont pas des fournisseurs de matière. Le référentiel n'a pas de catégorie
  « transport » ; ils tombent donc dans « autre », qui est honnête.

Usage
-----
    python3 scripts/categoriser_fournisseurs.py                 # simulation
    python3 scripts/categoriser_fournisseurs.py --appliquer
    python3 scripts/categoriser_fournisseurs.py --csv props.csv # pour relire
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))


def norm(s) -> str:
    s = unicodedata.normalize("NFKD", str(s or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", s)).strip()


# ── Règles de nom ────────────────────────────────────────────────────────
# Ordre important : la première règle qui matche gagne pour cette catégorie,
# mais toutes les catégories sont évaluées (un fournisseur peut être à la fois
# « frontal » et « negoce »).
#
# Les motifs sont cherchés dans le nom NORMALISÉ (sans accent, minuscule,
# ponctuation en espaces), donc « ADEZIF » et « adézif » se valent.
REGLES = {
    "palette": ("palette", "burban"),
    "carton": ("carton", "cartonnage", "kartonnage", "ondul", "vpk", "embaltec",
               "toutembal", "packaging", "pack discount", "sd pack", "allpack",
               "lgp packaging", "green packing", "package material"),
    "mandrin": ("mandril", "corex", "papierhulsen", "abzac", "tube", "gipako",
                "rsw gmbh"),
    "adhesif": ("adhesif", "adhesive", "adezif", "hotmelt", "bostik", "henkel",
                "paramelt", "meltavis", "tixo", "adley", "self adhesive",
                "brenntag", "sengken"),
    "frontal": ("papier", "paper", "papel", "thermal", "arjobex", "arconvert",
                "torraspapel", "mondi", "inapa", "antalis", "kanzan",
                "mitsubishi", "ricoh", "flexcon", "ester industries",
                "codewel", "crown van gelber", "rkw", "skyflex", "spandex"),
    "glassine": ("release", "glassine", "silicone", "siliconee"),
    "complexe": ("complexe", "laminat"),
    "sous_traitant": ("etiquette", "etiquettes", "label", "labels", "imprimerie",
                      "imprimeur", "etiflex", "eticzen", "etikservices",
                      "printing", "graphique", "graphics", "flexo"),
    "negoce": ("distribution", "distr", "diffusion", "negoce", "grossiste"),
    "autre": ("adecco", "amazon", "xerox", "absoft", "access it", "softage",
              "erp associes", "jarltech", "barcodis", "checkpoint", "affretoo",
              "france express", "sedis logistics", "recuperation", "consult",
              "computer", "actebis", "raja", "jpg", "autour du bureau",
              "toddchrono", "scopus", "analytics", "generique", "spoolex",
              "kocher", "wink", "rotometal", "rotometrics", "daetwyler",
              "vetaphone", "spandex group", "miller graphics", "diatecx"),
}

# Un nom qui matche « autre » ET une catégorie matière : la catégorie matière
# gagne, « autre » ne sert que de dernier recours. Sans cette règle, « Miller
# Graphics » (outillage) et « QRT Graphique » (sous-traitance d'impression)
# tomberaient tous les deux dans le même panier.
PRIORITE_BASSE = {"autre", "negoce"}


def categories_depuis_nom(nom: str) -> list[str]:
    n = norm(nom)
    trouvees = []
    for code, motifs in REGLES.items():
        if any(m in n for m in motifs):
            trouvees.append(code)
    fortes = [c for c in trouvees if c not in PRIORITE_BASSE]
    return fortes if fortes else trouvees


# ── Déduction depuis les liens réels ─────────────────────────────────────

def colonnes(conn, table) -> set[str]:
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except sqlite3.Error:
        return set()


def categories_depuis_base(conn, codes_connus: set[str]) -> dict[int, set[str]]:
    """{fournisseur_id: {codes}} d'après les matières réellement rattachées.

    Trois chemins, tous facultatifs : une base où le module Coûts matières n'a
    jamais servi n'a aucun de ces liens, et le script doit s'en accommoder sans
    rien inventer.
    """
    sortie: dict[int, set[str]] = defaultdict(set)

    def ajouter(fid, brut):
        c = norm(brut).replace(" ", "_")
        if c in codes_connus:
            sortie[int(fid)].add(c)

    # matieres_premieres.categorie, via les trois tables de liaison MyStock.
    if "categorie" in colonnes(conn, "matieres_premieres"):
        for table, col_mat in (("mp_matiere_prix", "matiere_id"),
                               ("matiere_laize_fournisseurs", "matiere_id"),
                               ("mc_tarif_fournisseur", "matiere_id")):
            cols = colonnes(conn, table)
            if "fournisseur_id" not in cols or col_mat not in cols:
                continue
            try:
                for r in conn.execute(
                    f"""SELECT t.fournisseur_id AS fid, m.categorie AS cat
                          FROM {table} t
                          JOIN matieres_premieres m ON m.id = t.{col_mat}
                         WHERE t.fournisseur_id IS NOT NULL
                           AND m.categorie IS NOT NULL AND m.categorie <> ''"""
                ).fetchall():
                    ajouter(r["fid"], r["cat"])
            except sqlite3.Error:
                continue

    # mc_material.category_id → mc_category (ancien module Coûts matières).
    if {"fournisseur_fsc_id", "category_id"} <= colonnes(conn, "mc_material") \
            and colonnes(conn, "mc_category"):
        col_lib = "code" if "code" in colonnes(conn, "mc_category") else "label"
        try:
            for r in conn.execute(
                f"""SELECT mm.fournisseur_fsc_id AS fid, mc.{col_lib} AS cat
                      FROM mc_material mm
                      JOIN mc_category mc ON mc.id = mm.category_id
                     WHERE mm.fournisseur_fsc_id IS NOT NULL"""
            ).fetchall():
                ajouter(r["fid"], r["cat"])
        except sqlite3.Error:
            pass

    return sortie


# ── Programme ────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=None, help="Base SQLite (défaut : DB_PATH de config.py)")
    ap.add_argument("--appliquer", action="store_true", help="Écrit en base")
    ap.add_argument("--csv", default=None, metavar="CHEMIN",
                    help="Écrit les propositions en CSV pour relecture, puis s'arrête")
    args = ap.parse_args()

    chemin = args.db
    if not chemin:
        from config import DB_PATH
        chemin = DB_PATH
    if not Path(chemin).exists():
        raise SystemExit(f"Base introuvable : {chemin}")

    from config import FOURNISSEUR_CATEGORIES_CODES as CODES
    conn = sqlite3.connect(chemin)
    conn.row_factory = sqlite3.Row

    fiches = conn.execute(
        "SELECT id, nom, categories FROM fournisseurs_fsc ORDER BY nom COLLATE NOCASE"
    ).fetchall()
    depuis_base = categories_depuis_base(conn, CODES)

    plans, deja, sans = [], [], []
    for f in fiches:
        try:
            actuelles = json.loads(f["categories"]) if f["categories"] else []
            actuelles = actuelles if isinstance(actuelles, list) else []
        except (ValueError, TypeError):
            actuelles = []
        if actuelles:
            deja.append(f)
            continue
        sures = sorted(depuis_base.get(int(f["id"]), set()))
        devinees = [] if sures else categories_depuis_nom(f["nom"])
        proposees = sures or devinees
        if not proposees:
            sans.append(f)
            continue
        plans.append({
            "id": int(f["id"]), "nom": f["nom"], "cats": proposees,
            "source": "base" if sures else "nom",
        })

    print(f"Annuaire : {len(fiches)} fiche(s)")
    print(f"  {len(deja):>4} ont déjà une catégorie — non touchées")
    print(f"  {len(plans):>4} recevraient une proposition")
    print(f"  {len(sans):>4} qu'aucune règle ne reconnaît — laissées vides")
    par_source = Counter(p["source"] for p in plans)
    if par_source:
        print("       dont " + ", ".join(
            f"{n} déduite(s) des liens en base" if s == "base" else f"{n} devinée(s) du nom"
            for s, n in par_source.most_common()))

    par_cat = Counter(c for p in plans for c in p["cats"])
    if par_cat:
        print("\nRépartition proposée")
        print("─" * 40)
        for code, n in par_cat.most_common():
            print(f"  {code:<16} {n:>4}")

    if args.csv:
        lignes = ["# Catégories proposées — relisez, corrigez, puis :",
                  "#   python3 scripts/categoriser_fournisseurs.py --appliquer",
                  "# (ce CSV est un rapport de relecture, le script relit la base)",
                  "#",
                  "# id;nom;categories;source"]
        for p in plans:
            lignes.append(f"{p['id']};{p['nom']};{','.join(p['cats'])};{p['source']}")
        lignes.append("#")
        lignes.append(f"# {len(sans)} fiche(s) sans proposition :")
        for f in sans:
            lignes.append(f"# {f['id']};{f['nom']};;")
        Path(args.csv).write_text("\n".join(lignes) + "\n", encoding="utf-8")
        print(f"\nÉcrit dans {args.csv} — rien n'a été modifié en base.")
        return 0

    print("\nDétail (40 premières)")
    print("─" * 60)
    for p in plans[:40]:
        marque = "base" if p["source"] == "base" else "  ?  "
        print(f"  [{marque}] {p['nom'][:38]:<40} {', '.join(p['cats'])}")
    if len(plans) > 40:
        print(f"  … {len(plans) - 40} autre(s). Utilisez --csv pour la liste complète.")

    if sans:
        print(f"\nSans proposition ({len(sans)}) — à faire à la main dans Paramètres")
        print("─" * 60)
        for f in sans[:40]:
            print(f"  {f['nom']}")
        if len(sans) > 40:
            print(f"  … {len(sans) - 40} autre(s).")

    if not args.appliquer:
        print("\nSimulation : rien n'a été écrit. --appliquer pour valider.")
        return 0

    now = datetime.now().isoformat(timespec="seconds")
    n = 0
    for p in plans:
        conn.execute(
            "UPDATE fournisseurs_fsc SET categories=?, sous_traitant=?, updated_at=? WHERE id=?",
            (json.dumps(p["cats"], ensure_ascii=False),
             1 if "sous_traitant" in p["cats"] else 0, now, p["id"]),
        )
        n += 1
    conn.commit()
    print(f"\nAppliqué : {n} fiche(s) catégorisée(s).")
    print("  Les propositions marquées « ? » viennent du nom, pas d'une donnée :")
    print("  relisez-les dans Paramètres → Fournisseurs, colonne Catégories.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

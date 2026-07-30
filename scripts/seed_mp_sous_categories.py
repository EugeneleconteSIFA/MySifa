#!/usr/bin/env python3
"""Remplit matieres_premieres.sous_categorie / sous_categorie_en depuis la
taxonomie validee par Eugene (relecture du 30/07/2026).

Le francais s'affiche dans MyStock, l'anglais part dans la reference produit
envoyee aux fournisseurs. Les deux sont stockes car la correspondance n'est pas
bijective : « Velin » et « Velin Fluo » se rejoignent tous deux sur « Vellum ».

Idempotent et non destructif : n'ecrit que sur les lignes dont la sous_categorie
francaise est encore vide. Une valeur saisie a la main n'est jamais ecrasee.
Rejouable autant de fois que necessaire.

    python3 scripts/seed_mp_sous_categories.py            # apercu, n'ecrit rien
    python3 scripts/seed_mp_sous_categories.py --apply    # ecrit
    python3 scripts/seed_mp_sous_categories.py --apply --force   # ecrase aussi l'existant

Le rattachement se fait sur (categorie, reference), compare sans accents ni
casse : LOWER() de SQLite ne replie pas les accents et les references d'ici en
sont pleines.

A jouer APRES un premier demarrage de l'application, qui cree les colonnes.
"""

import argparse
import os
import sqlite3
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# TAXONOMIE : (categorie, libelle francais, libelle anglais, [references])
# Source de verite du seed — modifiable directement ici.
TAXONOMIE = [
    ('Adhésif', 'Congelation', 'Deep-Freeze', [
        '2030',
    ]),
    ('Adhésif', 'Enlevable', 'Removable', [
        '1408',
        '2355',
    ]),
    ('Adhésif', 'Permanent', 'Permanent', [
        '1225',
        '2028Y',
    ]),
    ('Adhésif', 'Special Pneu', 'Tyre', [
        '2288M',
    ]),
    ('Autre', "Tête d'impression", 'Printer head', [
        'ASYB BX420',
        'EX4T1',
    ]),
    ('Carton', 'Carton F&C', 'Carton F&C', [
        '305 x 210 x 80 F&C',
        '305 x 215 x 150 F&C',
        '315 x 235 x 80 F&C',
    ]),
    ('Carton', 'Carton standard', 'Carton standard', [
        '200 x 200 x 57 mm',
        '275 x 255 x 300 mm',
        '305 x 215 x 80 mm',
        '320 x 130 x 190 mm',
        '350 x 320 x 111 mm',
        '385 x 320 x 79 mm',
        '385 X 385 X 105 mm',
        '385 x 385 x 111 mm',
        '385 x 385 x 120 mm',
        '385 x 385 x 135 mm',
        '385 x 385 x 152 mm',
        '385 x 385 x 170 mm',
        '385 x 385 x 180 mm',
        '385 x 385 x 208 mm',
        '385 x 385 x 260 mm',
        '385 x 385 x 311 mm',
        '385 x 385 x 54 mm',
        '385 x 385 x 83 mm',
        '385 x 385 x 90 mm',
    ]),
    ('Carton', 'Grand Box', 'Grand Box', [
        '1180 x 780 x 1070 mm',
    ]),
    ('Carton', 'Intercalaire', 'Intercalaire', [
        'Intercalaire Grand Box/Palette',
    ]),
    ('complexe', 'Complexe', 'Complexe', [
        'Couché adhésif enlevable',
        'Couché adhésif permanent',
        'Couché adhésif permanent acrylique',
        'Couché Pharma adhésif permanent acrylique',
        'PET argenté adhésif permanent',
        'PET blanc adhésif permanent',
        'PP blanc 90µm adhésif pneu',
        'PP blanc thermique 95µ adhésif permanent acrylique',
        'PP transparent permanent acrylique',
        'Thermique Eco adhésif congélation',
        'Thermique Eco adhésif enlevable',
        'Thermique Eco adhésif permanent',
        'Thermique Pro adhésif permanent',
        'Thermique pro adhésif permanent acrylique',
        'Velin adhésif enlevable',
        'Velin adhésif permanent',
        'Velin adhésif permanent P1000',
    ]),
    ('Frontal', 'Couche', 'Coated', [
        '80gsm Coated Paper',
        'couché 70gsm satiné',
        'couché 90gsm fluo jaune',
    ]),
    ('Frontal', 'Synthetique', 'Synthetic', [
        'PP blanc mat 120µm',
        'PP blanc mat 200µm',
        'PP blanc mat 95µm',
    ]),
    ('Frontal', 'Thermique Bicolore', 'Thermal Bicolor', [
        'Thermique Bicolore',
    ]),
    ('Frontal', 'Thermique Eco', 'Thermal Eco', [
        '70g Eco Thermal',
        'Eco Thermal 70gsm Torraspapel',
    ]),
    ('Frontal', 'Thermique Pro', 'Thermal Top', [
        '70gsm TOP Thermal',
        '95gsm TOP Thermal',
        'TOP Thermal 105gsm',
    ]),
    ('Frontal', 'Velin', 'Vellum', [
        '62gsm Vellum',
        '68gsm Vellum',
    ]),
    ('Frontal', 'Velin Fluo', 'Vellum', [
        '70gsm Vellum fluo jaune',
    ]),
    ('Glassine', 'Glassine', 'Glassine', [
        '60gsm glassine jaune siliconné',
        '60gsm ITASA',
        '60gsm KAM20',
        '60gsm KAS2',
    ]),
    ('Mandrin', 'Core 25', 'Core 25', [
        'Ø 25 mm',
    ]),
    ('Mandrin', 'Core 40', 'Core 40', [
        'Ø 40 mm',
    ]),
    ('Mandrin', 'Core 76', 'Core 76', [
        'Ø 76 mm',
        'Ø 76 mm épaisseur 7 mm',
    ]),
    ('Palette', 'Pallet Europe', 'Pallet Europe', [
        'Europe',
    ]),
    ('Palette', 'Pallet Perdue', 'Pallet Perdue', [
        'Perdue',
    ]),
]


def cle(valeur: object) -> str:
    """Cle de comparaison : sans accents, sans casse, sans espaces de bord."""
    texte = unicodedata.normalize("NFD", str(valeur or "").strip().casefold())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def db_path() -> str:
    if os.environ.get("DB_PATH"):
        return os.environ["DB_PATH"]
    try:
        from config import DB_PATH  # noqa: PLC0415

        return str(DB_PATH)
    except Exception:
        for candidat in (ROOT / "app" / "data" / "production.db",
                         ROOT / "data" / "production.db"):
            if candidat.is_file():
                return str(candidat)
    raise SystemExit("Base introuvable : renseigne DB_PATH.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="ecrit en base")
    ap.add_argument("--force", action="store_true",
                    help="ecrase aussi les sous-categories deja renseignees")
    args = ap.parse_args()

    chemin = db_path()
    print(f"Base : {chemin}")
    conn = sqlite3.connect(chemin)
    conn.row_factory = sqlite3.Row

    colonnes = {r["name"] for r in conn.execute("PRAGMA table_info(matieres_premieres)")}
    manquantes = {"sous_categorie", "sous_categorie_en"} - colonnes
    if manquantes:
        raise SystemExit(
            f"Colonne(s) absente(s) : {', '.join(sorted(manquantes))}. "
            "Demarre l'application une fois pour jouer les migrations, puis relance."
        )

    par_cle: dict[tuple[str, str], list[sqlite3.Row]] = {}
    for row in conn.execute(
        "SELECT id, categorie, reference, sous_categorie, sous_categorie_en"
        "  FROM matieres_premieres"
    ):
        par_cle.setdefault((cle(row["categorie"]), cle(row["reference"])), []).append(row)

    a_ecrire: list[tuple[str, int, str, str, str]] = []
    deja: list[str] = []
    absents: list[str] = []

    for categorie, fr, en, refs in TAXONOMIE:
        for ref in refs:
            lignes = par_cle.get((cle(categorie), cle(ref)))
            if not lignes:
                absents.append(f"{categorie} | {ref}")
                continue
            for ligne in lignes:
                actuelle = (ligne["sous_categorie"] or "").strip()
                actuelle_en = (ligne["sous_categorie_en"] or "").strip()
                if actuelle and not args.force:
                    if cle(actuelle) != cle(fr):
                        deja.append(
                            f"{categorie} | {ref} : garde {actuelle!r} "
                            f"(la taxonomie propose {fr!r})"
                        )
                    elif not actuelle_en:
                        # Meme famille, traduction manquante : on la complete,
                        # ce n'est pas ecraser une decision mais en finir une.
                        a_ecrire.append((categorie, int(ligne["id"]), ref, actuelle, en))
                    continue
                if cle(actuelle) == cle(fr) and cle(actuelle_en) == cle(en):
                    continue
                a_ecrire.append((categorie, int(ligne["id"]), ref, fr, en))

    print(f"\n{len(a_ecrire)} ligne(s) a mettre a jour")
    for categorie, _id, ref, fr, en in a_ecrire:
        suffixe = fr if cle(fr) == cle(en) else f"{fr} / {en}"
        print(f"  {categorie:10} | {ref[:40]:40} -> {suffixe}")

    if deja:
        print(f"\n{len(deja)} ligne(s) laissee(s) en place (valeur manuelle differente) :")
        for d in deja:
            print(f"  {d}")
        print("  Utilise --force pour les ecraser.")

    if absents:
        print(f"\n{len(absents)} reference(s) de la taxonomie introuvable(s) en base :")
        for a in absents:
            print(f"  {a}")
        print("  Reference renommee ou desactivee depuis l'export. Sans effet sur le reste.")

    if not args.apply:
        print("\nApercu uniquement — relance avec --apply pour ecrire.")
        conn.close()
        return 0

    for _categorie, ligne_id, _ref, fr, en in a_ecrire:
        conn.execute(
            "UPDATE matieres_premieres SET sous_categorie=?, sous_categorie_en=? WHERE id=?",
            (fr, en, ligne_id),
        )
    conn.commit()
    print(f"\n{len(a_ecrire)} ligne(s) ecrite(s).")

    restantes = conn.execute(
        "SELECT categorie, reference FROM matieres_premieres"
        "  WHERE actif=1 AND TRIM(COALESCE(sous_categorie,'')) = ''"
        "  ORDER BY categorie, reference"
    ).fetchall()
    if restantes:
        print(f"\n{len(restantes)} matiere(s) active(s) encore sans sous-categorie :")
        for r in restantes:
            print(f"  {r['categorie']:10} | {r['reference']}")
        print("  A completer dans MyStock ; en attendant, MyAO deduit le libelle "
              "de la description.")
    else:
        print("\nToutes les matieres actives ont une sous-categorie.")

    sans_en = conn.execute(
        "SELECT categorie, reference, sous_categorie FROM matieres_premieres"
        "  WHERE actif=1 AND TRIM(COALESCE(sous_categorie,'')) <> ''"
        "    AND TRIM(COALESCE(sous_categorie_en,'')) = ''"
        "  ORDER BY categorie, reference"
    ).fetchall()
    if sans_en:
        print(f"\n{len(sans_en)} matiere(s) sans traduction anglaise "
              "(la reference produit reprendra le libelle francais) :")
        for r in sans_en:
            print(f"  {r['categorie']:10} | {r['reference']} ({r['sous_categorie']})")

    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

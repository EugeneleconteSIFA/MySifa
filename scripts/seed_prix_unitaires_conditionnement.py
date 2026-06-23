#!/usr/bin/env python3
"""Seed des prix unitaires + conditionnement (unites_par_palette) pour les
catégories cartons, adhésifs et mandrins de MyStock.

Avant : prix_unitaire = prix à la palette (€/palette).
Après : prix_unitaire = prix à l'unité d'achat (€/carton, €/tube, €/kg)
        + unites_par_palette = nombre d'unités d'achat par palette.
        Valorisation = stock_palettes × unites_par_palette × prix_unitaire.

Idempotent : on n'écrit que si la valeur diffère. Toute écriture est tracée
dans mp_valorisation_historique avec une note explicite.

Matching :
- Cartons   : normalisation (mm strippé, x lowercase, F&C insensible casse)
- Adhésifs  : code numérique (1225, 1408, 2028Y, 2030, 2288M, 2355)
- Mandrins  : diamètre + nb tubes/palette (résout le doublon de l'Excel)

Source des prix : « Prix Cartons mysifa (2).xlsx » (saisie 2026-06-23).

Usage :
    python3 scripts/seed_prix_unitaires_conditionnement.py            # dry-run
    python3 scripts/seed_prix_unitaires_conditionnement.py --commit   # écrit
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Permet d'importer config.py depuis la racine
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import DB_PATH  # noqa: E402


NOTE_HIST = (
    "Conversion prix palette → prix unitaire d'achat + conditionnement "
    "(seed 2026-06-23)"
)

# ─────────────────────────────────────────────────────────────────────────
# Données source (Excel)
# ─────────────────────────────────────────────────────────────────────────

# (référence_normalisee, unites_par_palette, prix_unitaire_eur)
CARTONS: list[tuple[str, float, float]] = [
    ("1180x780x1070",     100, 9.938),
    ("275x255x300",       260, 0.81),
    ("305x210x80f&c",     400, 0.599),
    ("305x215x150f&c",    400, 0.99),
    ("315x235x80f&c",     400, 0.877),
    ("320x130x190",       260, 0.486),
    ("350x320x111",       260, 0.606),
    ("385x385x105",       260, 0.503),
    ("385x320x79",        260, 0.456),
    ("385x385x120",       260, 0.579),
    ("385x385x135",       260, 0.779),
    ("385x385x152",       260, 0.575),
    ("385x385x170",       260, 0.625),
    ("385x385x180",       260, 0.897),
    ("385x385x208",       260, 0.523),
    ("385x385x260",       260, 0.809),
    ("385x385x311",       260, 0.99),
    ("385x385x54",        260, 0.704),
    ("385x385x83",        260, 0.6),
    ("385x385x90",        260, 1.094),
]

# Adhésifs : clé = code numérique (référence en base = "1225", "2028Y", etc.)
ADHESIFS: list[tuple[str, float, float]] = [
    ("1225",  1200, 3.20),
    ("1408",  1200, 4.20),
    ("2028Y", 1200, 2.36),
    ("2030",  1200, 2.97),
    ("2288M", 1200, 2.91),
    ("2355",  400,  5.89),
]

# Mandrins : match par diamètre + qté/palette
# Format : (diametre_mm, epaisseur_mm, unites_par_palette, prix_unitaire)
# L'Excel a un doublon "mandrin 76 epaisseur 7" : 338 = en fait ép.4, 231 = ép.7
MANDRINS: list[tuple[int, float, float, float]] = [
    (25, 2.5, 1505, 0.3856),
    (40, 4.0,  990, 0.7106),
    (76, 4.0,  338, 1.1495),   # libellé Excel "epaisseur 7" est erroné (cf. user)
    (76, 7.0,  231, 2.31),
]


# ─────────────────────────────────────────────────────────────────────────
# Normalisation des références
# ─────────────────────────────────────────────────────────────────────────

def normalize_carton(ref: str) -> str:
    """385 X 385 X 105 mm → 385x385x105 ; 305 x 210 x 80 F&C → 305x210x80f&c."""
    s = (ref or "").strip().lower()
    s = re.sub(r"\bmm\b", "", s)
    s = s.replace(" ", "")
    return s


# Diamètre extrait via regex sur référence ou désignation
_MANDRIN_DIA_RE = re.compile(r"(?:[Øo])\s*(\d+)\s*mm", re.IGNORECASE)
_MANDRIN_DIA_RE_SIMPLE = re.compile(r"\b(\d+)\b")


def extract_mandrin_dia(reference: str, designation: str) -> int | None:
    """Tente d'extraire le diamètre. Référence ressemble à 'Ø 25 mm' / 'Ø 76 mm épaisseur 7 mm'."""
    src = (reference or "") + " " + (designation or "")
    m = _MANDRIN_DIA_RE.search(src)
    if m:
        return int(m.group(1))
    # fallback : premier nombre de la référence seule
    m = _MANDRIN_DIA_RE_SIMPLE.search(reference or "")
    if m:
        return int(m.group(1))
    return None


# Palette de XXX → nb tubes
_MANDRIN_PAL_RE = re.compile(r"palette\s+de\s+(\d+)", re.IGNORECASE)


def extract_mandrin_palette(designation: str) -> int | None:
    m = _MANDRIN_PAL_RE.search(designation or "")
    if m:
        return int(m.group(1))
    return None


# ─────────────────────────────────────────────────────────────────────────
# Logique seed
# ─────────────────────────────────────────────────────────────────────────

def fetch_mp(conn: sqlite3.Connection, categorie: str) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT mp.id, mp.reference, mp.designation,
               COALESCE(mp.unites_par_palette, 0) AS upp,
               COALESCE(v.prix_unitaire, 0) AS prix
        FROM matieres_premieres mp
        LEFT JOIN mp_valorisation v ON v.matiere_id = mp.id
        WHERE mp.actif = 1 AND mp.categorie = ?
        ORDER BY mp.reference
        """,
        (categorie,),
    ).fetchall()


def match_cartons(rows: list[sqlite3.Row]) -> tuple[list[tuple], list[str], list[str]]:
    """Retourne (matched, missing_in_excel, missing_in_db).

    matched : liste de (matiere_id, ref_db, upp_target, prix_target, upp_actuel, prix_actuel)
    """
    excel = {normalize_carton(k): (u, p) for k, u, p in CARTONS}
    db_by_norm = {normalize_carton(r["reference"]): r for r in rows}
    matched = []
    for nk, (u, p) in excel.items():
        r = db_by_norm.get(nk)
        if r:
            matched.append((r["id"], r["reference"], u, p, r["upp"], r["prix"]))
    missing_in_db = [k for k in excel if k not in db_by_norm]
    missing_in_excel = [r["reference"] for k, r in db_by_norm.items() if k not in excel]
    return matched, missing_in_excel, missing_in_db


def match_adhesifs(rows: list[sqlite3.Row]) -> tuple[list[tuple], list[str], list[str]]:
    excel = {k.upper(): (u, p) for k, u, p in ADHESIFS}
    db_by_ref = {(r["reference"] or "").strip().upper(): r for r in rows}
    matched = []
    for k, (u, p) in excel.items():
        r = db_by_ref.get(k)
        if r:
            matched.append((r["id"], r["reference"], u, p, r["upp"], r["prix"]))
    missing_in_db = [k for k in excel if k not in db_by_ref]
    missing_in_excel = [r["reference"] for k, r in db_by_ref.items() if k not in excel]
    return matched, missing_in_excel, missing_in_db


def match_mandrins(rows: list[sqlite3.Row]) -> tuple[list[tuple], list[str], list[str]]:
    """Match par (diamètre, qté/palette). La qté/palette se lit dans la désignation."""
    db_idx: dict[tuple[int, int], sqlite3.Row] = {}
    for r in rows:
        dia = extract_mandrin_dia(r["reference"], r["designation"])
        pal = extract_mandrin_palette(r["designation"])
        if dia is not None and pal is not None:
            db_idx[(dia, pal)] = r
    matched = []
    missing_in_db = []
    for dia, ep, u, p in MANDRINS:
        r = db_idx.get((dia, int(u)))
        if r:
            matched.append((r["id"], r["reference"], u, p, r["upp"], r["prix"]))
        else:
            missing_in_db.append(f"Ø {dia} mm (palette {int(u)})")
    matched_ids = {m[0] for m in matched}
    missing_in_excel = [r["reference"] for r in rows if r["id"] not in matched_ids]
    return matched, missing_in_excel, missing_in_db


# ─────────────────────────────────────────────────────────────────────────
# Application
# ─────────────────────────────────────────────────────────────────────────

def apply_seed(conn: sqlite3.Connection, matched: list[tuple], commit: bool, dry: bool) -> int:
    """Applique le seed. Retourne le nombre de matières effectivement modifiées."""
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    changed = 0
    for matiere_id, ref_db, upp_target, prix_target, upp_actuel, prix_actuel in matched:
        upp_actuel = float(upp_actuel or 0)
        prix_actuel = float(prix_actuel or 0)
        delta_upp = abs(upp_actuel - upp_target) > 1e-9
        delta_prix = abs(prix_actuel - prix_target) > 1e-9
        if not delta_upp and not delta_prix:
            continue
        changed += 1
        # Affichage
        action = "DRY" if dry else "WRITE"
        print(
            f"  [{action}] #{matiere_id:>4} {ref_db:<35} "
            f"upp: {upp_actuel:>8.2f} → {upp_target:>8.2f}  "
            f"prix: {prix_actuel:>10.4f} → {prix_target:>10.4f}"
        )
        if dry:
            continue
        # 1) unites_par_palette
        if delta_upp:
            conn.execute(
                "UPDATE matieres_premieres SET unites_par_palette=?, "
                "updated_at=strftime('%Y-%m-%dT%H:%M:%S','now','localtime') "
                "WHERE id=?",
                (upp_target, matiere_id),
            )
        # 2) prix_unitaire + historique
        if delta_prix:
            existing = conn.execute(
                "SELECT 1 FROM mp_valorisation WHERE matiere_id=?",
                (matiere_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE mp_valorisation SET prix_unitaire=?, updated_at=?, "
                    "updated_by_name=? WHERE matiere_id=?",
                    (prix_target, now, "seed-script", matiere_id),
                )
            else:
                conn.execute(
                    "INSERT INTO mp_valorisation "
                    "(matiere_id, prix_unitaire, updated_at, updated_by_name) "
                    "VALUES (?,?,?,?)",
                    (matiere_id, prix_target, now, "seed-script"),
                )
            conn.execute(
                "INSERT INTO mp_valorisation_historique "
                "(matiere_id, prix_avant, prix_apres, note, created_at, created_by_name) "
                "VALUES (?,?,?,?,?,?)",
                (matiere_id, prix_actuel, prix_target, NOTE_HIST, now, "seed-script"),
            )
    if commit and not dry:
        conn.commit()
    return changed


def summary(label: str, matched, missing_in_excel, missing_in_db) -> None:
    print(f"\n── {label} : {len(matched)} matches ─────────────────────────────")
    if missing_in_db:
        print(f"  ⚠  {len(missing_in_db)} ref Excel SANS match en base : {missing_in_db}")
    if missing_in_excel:
        print(f"  ⚠  {len(missing_in_excel)} ref base SANS prix Excel : {missing_in_excel}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", action="store_true",
                        help="Écrit en base. Sans ce flag : dry-run uniquement.")
    args = parser.parse_args()
    dry = not args.commit

    print(f"DB : {DB_PATH}")
    print(f"Mode : {'DRY-RUN' if dry else 'COMMIT'}")
    print()

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row

        # ── Cartons ────────────────────────────────────────────────────────
        rows = fetch_mp(conn, "carton")
        matched, miss_excel, miss_db = match_cartons(rows)
        summary("CARTONS", matched, miss_excel, miss_db)
        ch_c = apply_seed(conn, matched, args.commit, dry)

        # ── Adhésifs ───────────────────────────────────────────────────────
        rows = fetch_mp(conn, "adhesif")
        matched, miss_excel, miss_db = match_adhesifs(rows)
        summary("ADHÉSIFS", matched, miss_excel, miss_db)
        ch_a = apply_seed(conn, matched, args.commit, dry)

        # ── Mandrins ───────────────────────────────────────────────────────
        rows = fetch_mp(conn, "mandrin")
        matched, miss_excel, miss_db = match_mandrins(rows)
        summary("MANDRINS", matched, miss_excel, miss_db)
        ch_m = apply_seed(conn, matched, args.commit, dry)

    print()
    print(f"── Total : {ch_c} cartons · {ch_a} adhésifs · {ch_m} mandrins à modifier ──")
    if dry:
        print("Dry-run terminé. Relance avec --commit pour appliquer.")
    else:
        print("Seed appliqué.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

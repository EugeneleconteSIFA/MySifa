"""
MyExpé — lecture d'une grille tarifaire transporteur, quel que soit son format.

Un fichier déposé (PDF, Excel, CSV) devient une liste de lignes au schéma de
`expe_tarifs` (type d'envoi, base, zone, tranche, prix, unité). Ces lignes
partent ensuite en grilles brouillon (`expe_grilles.creer_brouillons`) : rien
n'est actif avant validation à l'écran.

Ordre des lecteurs, du plus sûr au plus coûteux :

1. **CSV au schéma MySifa** : colonnes `type_envoi`, `zone_valeur`, `prix`…
   lues telles quelles.
2. **Mises en page Excel connues** (Compte 100346, CEVA, TRANSBENELUX) : les
   parseurs historiques, réglés sur les fichiers réels.
3. **Lecteur générique de tableau** : sur chaque feuille Excel, chaque
   tableau de PDF (pdfplumber) ou un CSV quelconque, il cherche une ligne
   d'en-têtes de tranches (« De 1 à 10 kg », « 101 - 200 », « 1 PAL »,
   « + de 2000 ») et une colonne de zones (département, code postal, pays).
4. **Claude**, en dernier recours, si rien n'a été reconnu. Il ne recopie
   pas chaque ligne : il rend la grille en tableau compact (tranches une
   fois, puis les prix de chaque zone), ce qui tient une grille de 2 000
   cases en quelques milliers de tokens au lieu de la tronquer.

Aucune lecture n'est garantie : l'écran montre la grille en tableau et
l'écart avec la grille active avant toute activation. C'est ce contrôle qui
attrape une colonne décalée, pas le lecteur.
"""
from __future__ import annotations

import base64
import csv
import io
import json
import os
import re
from typing import Any, Optional

from app.services import ia_usage
from config import TARIF_TRANSPORT_IA_MODELE

EXTENSIONS = (".pdf", ".xlsx", ".xlsm", ".xls", ".csv")
_MAX_PAGES_PDF = 80
_MAX_TEXTE_IA = 400_000


class LectureErreur(Exception):
    """Message destiné à l'utilisateur."""


# ─── Parseurs Excel historiques (déplacés depuis app/routers/expe_departs.py) ──

def _tarif_float(v, default=None):
    """Convertit une valeur de cellule en float, None si impossible."""
    import math as _math

    try:
        f = float(str(v).strip().replace(",", "."))
        return None if _math.isnan(f) else f
    except Exception:
        return default


def _tarif_dept_from_label(label):
    """
    Extrait le code département depuis des formats variés :
      '(59) NORD'  →  '59'
      '59 - NORD'  →  '59'
      'FR59'       →  '59'
      '02'         →  '02'
    """
    s = str(label or "").strip()
    m = re.search(r"\((\w{1,3})\)", s)
    if m:
        code = m.group(1)
        return code.upper() if code.upper() in ("2A", "2B") else code.zfill(2)
    m = re.match(r"^FR(\w{2,3})$", s.upper())
    if m:
        code = m.group(1)
        return code.upper() if code.upper() in ("2A", "2B") else code.lstrip("0").zfill(2)
    m = re.match(r"^(\d{2,3})\s*[-–]?\s*", s)
    if m:
        code = m.group(1)
        return code.zfill(2) if len(code) <= 3 else None
    return None


def _tarif_unite_norm(v):
    s = str(v or "").strip().upper()
    if "100" in s:
        return "au_100kg"
    if "KG" in s and "100" not in s:
        return "au_kg"
    return "forfait"


def _tarif_find_header_row(ws, keywords, max_scan=40):
    """Retourne le numéro de la première ligne contenant un keyword (insensible à la casse)."""
    keywords_up = [k.upper() for k in keywords]
    for r in range(1, max_scan + 1):
        for c in range(1, min(ws.max_column + 1, 20)):
            val = str(ws.cell(row=r, column=c).value or "").upper()
            if any(k in val for k in keywords_up):
                return r
    return None


def _detect_tarif_format(wb):
    """
    Détecte le format de la grille tarifaire en examinant noms de feuilles + cellules clés.
    Retourne : 'compte100346' | 'ceva' | 'transbenelux' | 'generique'
    """
    sheet_names = " | ".join(ws.title.upper() for ws in wb.worksheets)

    if any(k in sheet_names for k in ("MESSAGERIE", "SMARTPAL", "SMART PAL", "CONDITIONS COMMERCIALES")):
        return "ceva"

    if any(k in sheet_names for k in ("BENELUX", "TRANSBENELUX", "SIFA VERS FRANCE")):
        return "transbenelux"

    for ws in wb.worksheets:
        a8 = str(ws["A8"].value or "").upper()
        if "POIDS" in a8 or "PALETTE" in a8:
            return "compte100346"

    return "generique"


def _parse_compte100346(wb, source_filename):
    """
    Format SIFA 010126 - P U (Compte 100346) :
    - Feuille avec A8 = "POIDS" ou "PALETTE"
    - Ligne 10 : bornes basses (DE)
    - Ligne 11 : bornes hautes (A)
    - Ligne 12 : unité (Forfait / Prx/100Kg)
    - Données à partir de la ligne 13
    - Col A : "(XX) NOM DÉPARTEMENT"
    """
    rows = []
    for ws in wb.worksheets:
        a8 = str(ws["A8"].value or "").upper()
        if "POIDS" in a8:
            base_calcul, type_envoi = "poids", "messagerie"
        elif "PALETTE" in a8:
            base_calcul, type_envoi = "palette", "messagerie"
        else:
            continue

        cols = []
        for c in range(3, ws.max_column + 1):
            tmax = _tarif_float(ws.cell(row=11, column=c).value)
            if tmax is None:
                continue
            tmin = _tarif_float(ws.cell(row=10, column=c).value, default=0)
            unite = _tarif_unite_norm(ws.cell(row=12, column=c).value)
            cols.append((c, tmin, tmax, unite))

        for r in range(13, ws.max_row + 1):
            dept = _tarif_dept_from_label(ws.cell(row=r, column=1).value)
            if not dept:
                continue
            for c, tmin, tmax, unite in cols:
                price = _tarif_float(ws.cell(row=r, column=c).value)
                if price is None:
                    continue
                rows.append(
                    {
                        "type_envoi": type_envoi,
                        "base_calcul": base_calcul,
                        "zone_type": "departement",
                        "zone_valeur": dept,
                        "tranche_min": tmin,
                        "tranche_max": int(tmax) if base_calcul == "palette" else tmax,
                        "prix": round(price, 4),
                        "unite": unite,
                        "mini_perception": None,
                        "source_filename": source_filename,
                    }
                )

    return rows, []


def _parse_ceva_messagerie(ws, source_filename):
    rows = []
    header_row = _tarif_find_header_row(
        ws, ["DÉPARTEMENT", "DEPARTEMENT", "ZONE", "CODE POSTAL", "CP"]
    )
    if header_row is None:
        return rows

    cols = []
    for c in range(2, ws.max_column + 1):
        val = str(ws.cell(row=header_row, column=c).value or "").strip()
        if not val:
            continue
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*[-àaÀ]\s*(\d+(?:[.,]\d+)?)", val)
        if m:
            tmin = _tarif_float(m.group(1), 0)
            tmax = _tarif_float(m.group(2))
            unite = "forfait" if (tmax is not None and tmax <= 100) else "au_100kg"
            cols.append((c, tmin, tmax, unite))

    for r in range(header_row + 1, ws.max_row + 1):
        zone_lbl = str(ws.cell(row=r, column=1).value or "").strip()
        if not zone_lbl:
            continue
        dept = _tarif_dept_from_label(zone_lbl)
        cp_m = re.match(r"^(\d{5})\b", zone_lbl)
        if dept:
            zone_type, zone_valeur = "departement", dept
        elif cp_m:
            zone_type, zone_valeur = "code_postal", cp_m.group(1)
        else:
            continue
        for c, tmin, tmax, unite in cols:
            if tmin is None:
                continue
            price = _tarif_float(ws.cell(row=r, column=c).value)
            if price is None:
                continue
            rows.append(
                {
                    "type_envoi": "messagerie",
                    "base_calcul": "poids",
                    "zone_type": zone_type,
                    "zone_valeur": zone_valeur,
                    "tranche_min": tmin,
                    "tranche_max": tmax,
                    "prix": round(price, 4),
                    "unite": unite,
                    "mini_perception": None,
                    "source_filename": source_filename,
                }
            )
    return rows


def _parse_ceva_palettes(ws, source_filename):
    rows = []
    header_row = _tarif_find_header_row(ws, ["DÉPARTEMENT", "DEPARTEMENT", "ZONE", "PALETTE", "PAL"])
    if header_row is None:
        return rows
    cols = []
    for c in range(2, ws.max_column + 1):
        val = str(ws.cell(row=header_row, column=c).value or "").strip()
        m = re.match(r"^(\d+)\s*(?:palette|pal\.?)?$", val, re.IGNORECASE)
        if m:
            nb = int(m.group(1))
            if 1 <= nb <= 20:
                cols.append((c, nb))
    if not cols:
        cols = [(c, i) for i, c in enumerate(range(2, min(ws.max_column + 1, 7)), start=1)]
    for r in range(header_row + 1, ws.max_row + 1):
        dept = _tarif_dept_from_label(ws.cell(row=r, column=1).value)
        if not dept:
            continue
        for c, nb in cols:
            price = _tarif_float(ws.cell(row=r, column=c).value)
            if price is None:
                continue
            rows.append(
                {
                    "type_envoi": "messagerie",
                    "base_calcul": "palette",
                    "zone_type": "departement",
                    "zone_valeur": dept,
                    "tranche_min": nb,
                    "tranche_max": nb,
                    "prix": round(price, 4),
                    "unite": "forfait",
                    "mini_perception": None,
                    "source_filename": source_filename,
                }
            )
    return rows


def _parse_ceva_frais(ws):
    frais = []
    patterns = [
        (r"gasoil|carburant|fuel", "Gasoil", "pct_transport", 1),
        (r"sûreté|surete|sécurité|securite", "Taxe sûreté/sécurité", "forfait_expedition", 1),
        (r"prise.{0,10}rdv|rendez.{0,5}vous", "Prise de RDV", "forfait_expedition", 0),
        (r"hayon|tail.?lift", "Hayon", "par_palette", 0),
        (r"ville.{0,15}excentr", "Ville excentrée", "forfait_expedition", 0),
        (r"co2|contribution", "CO2", "forfait_expedition", 1),
        (r"centre.{0,10}urbain|urban", "Centres urbains", "forfait_expedition", 0),
    ]
    seen = set()
    for r in range(1, ws.max_row + 1):
        for c in range(1, min(ws.max_column + 1, 10)):
            cell = str(ws.cell(row=r, column=c).value or "").strip()
            if not cell:
                continue
            for pattern, libelle, mode, defaut in patterns:
                if libelle in seen:
                    continue
                if re.search(pattern, cell, re.IGNORECASE):
                    for cc in range(c + 1, min(c + 6, ws.max_column + 1)):
                        val = _tarif_float(ws.cell(row=r, column=cc).value)
                        if val is not None and val > 0:
                            frais.append(
                                {
                                    "libelle": libelle,
                                    "mode": mode,
                                    "valeur": val,
                                    "mini": None,
                                    "applique_defaut": defaut,
                                }
                            )
                            seen.add(libelle)
                            break
                    break
    return frais


def _parse_ceva(wb, source_filename):
    rows = []
    frais = []
    for ws in wb.worksheets:
        t = ws.title.upper().replace(" ", "")
        if "MESSAGERIE" in t or ("TARIF" in t and "GN" in t):
            rows += _parse_ceva_messagerie(ws, source_filename)
        elif "PALETTE" in t or "SMARTPAL" in t or "SMART" in t:
            rows += _parse_ceva_palettes(ws, source_filename)
        elif "CONDITION" in t or "COMMERCIALE" in t or "ANNEXE" in t:
            frais += _parse_ceva_frais(ws)
    return rows, frais


def _parse_transbenelux(wb, source_filename):
    rows = []
    for ws in wb.worksheets:
        header_row = _tarif_find_header_row(ws, ["PALETTE", "PAL", "FRANCE", "DÉPARTEMENT"])
        if header_row is None:
            continue
        cols = []
        for c in range(2, ws.max_column + 1):
            val = str(ws.cell(row=header_row, column=c).value or "").strip()
            m = re.fullmatch(r"(\d{1,2})", val)
            if m:
                nb = int(m.group(1))
                if 1 <= nb <= 20:
                    cols.append((c, nb))
        if not cols:
            continue
        for r in range(header_row + 1, ws.max_row + 1):
            dept = _tarif_dept_from_label(ws.cell(row=r, column=1).value)
            if not dept:
                continue
            for c, nb in cols:
                raw = str(ws.cell(row=r, column=c).value or "").strip().upper()
                if raw in ("", "FO", "PU", "PP", "-", "NC", "N/A"):
                    continue
                price = _tarif_float(raw)
                if price is None or price <= 0:
                    continue
                rows.append(
                    {
                        "type_envoi": "affretement" if nb > 6 else "messagerie",
                        "base_calcul": "palette",
                        "zone_type": "departement",
                        "zone_valeur": dept,
                        "tranche_min": nb,
                        "tranche_max": nb,
                        "prix": round(price, 4),
                        "unite": "forfait",
                        "mini_perception": None,
                        "source_filename": source_filename,
                    }
                )
    return rows, []




# ─── Lecteur générique de tableau ────────────────────────────────────

_N = r"\d+(?:[.,]\d+)?"


def _norm(txt: Any) -> str:
    s = str(txt if txt is not None else "").replace("\xa0", " ").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s.replace("kgs", "kg")


def _base_unite(tok: str) -> Optional[str]:
    tok = (tok or "").lower()
    if tok.startswith("pal") or tok == "pl":
        return "palette"
    if tok in ("m", "ml", "mpl", "mp"):
        return "metre_plancher"
    if tok in ("kg", "t"):
        return "poids"
    return None


def lire_tranche(txt: Any) -> Optional[dict]:
    """Interprète un en-tête de colonne comme une tranche, ou None.

    Rend {min, max, base} ; min ou max peuvent manquer (« jusqu'à 10 »,
    « + de 2000 ») et sont complétés plus tard par les colonnes voisines.
    """
    s = _norm(txt)
    if not s or len(s) > 40 or re.search(r"\d{2}[./]\d{2}[./]\d{2,4}", s):
        return None
    m = re.fullmatch(r"(\d{1,2})\s*(pal(?:ette)?s?\.?|pl)", s)
    if m:
        n = int(m.group(1))
        return {"min": n, "max": n, "base": "palette"}
    m = re.search(
        rf"(?:de\s*)?({_N})\s*(kg|t|ml|mpl|m|pal\w*)?\s*(?:à|a|-|–|/|au)\s*({_N})\s*(kg|t|ml|mpl|m|pal\w*)?",
        s,
    )
    if m:
        a, b = float(m.group(1).replace(",", ".")), float(m.group(3).replace(",", "."))
        unite = m.group(4) or m.group(2) or ""
        if unite == "t":
            a, b = a * 1000, b * 1000
        if b < a:
            return None
        return {"min": a, "max": b, "base": _base_unite(unite)}
    m = re.search(rf"(?:\+\s*de|plus\s*de|>\s*=?|au[- ]?del[aà]\s*de|sup[ée]rieur\s*[àa])\s*({_N})\s*(kg|t|ml|m|pal\w*)?", s) \
        or re.fullmatch(rf"({_N})\s*(kg|t|ml|m|pal\w*)?\s*(?:et\s*\+|et\s*plus|\+)", s)
    if m:
        a = float(m.group(1).replace(",", "."))
        return {"min": a + 1 if a.is_integer() else a, "max": None, "base": _base_unite(m.group(2) or "")}
    m = re.search(rf"(?:jusqu'?\s*[àa]|<\s*=?|max\.?|moins\s*de)\s*({_N})\s*(kg|t|ml|m|pal\w*)?", s)
    if m:
        return {"min": None, "max": float(m.group(1).replace(",", ".")), "base": _base_unite(m.group(2) or "")}
    return None


_PAYS_FRANCE = {"france", "fr", "fra", "metropole", "métropole"}


def lire_zone(txt: str) -> Optional[tuple[str, str]]:
    """(zone_type, zone_valeur) depuis le libellé de zone d'une ligne, ou None."""
    s = re.sub(r"\s+", " ", str(txt or "").replace("\xa0", " ")).strip()
    if not s or re.search(r"mini|total|minimum|tarif|zone\b|d[ée]partement", s, re.I):
        return None
    m = re.fullmatch(r"(?:fr\s*-?\s*)?(\d{5})", s, re.I)
    if m:
        return ("code_postal", m.group(1))
    m = re.match(r"^([A-Za-zÀ-ÿ' -]+?)\s+(\S.*)$", s)
    if m and not re.fullmatch(r"\(?\d", m.group(1)[:2]):
        pays, reste = m.group(1).strip(), m.group(2).strip()
        if pays.lower() in _PAYS_FRANCE:
            d = _tarif_dept_from_label(reste)
            if d:
                return ("departement", d)
            m5 = re.fullmatch(r"\d{5}", reste)
            return ("code_postal", reste) if m5 else None
        if re.fullmatch(r"(?:FR)?\d{2,3}|2[AB]", pays, re.I):
            pass
        else:
            return ("pays", f"{pays} {reste}")
    if re.fullmatch(r"2[AB]", s, re.I):
        return ("departement", s.upper())
    d = _tarif_dept_from_label(s)
    if d and (len(d) == 2 or d.startswith("97")):
        return ("departement", d)
    return None


def _nombres(txt: Any) -> list[Optional[float]]:
    """Les prix d'une cellule : un ou plusieurs nombres (cellules fusionnées d'un PDF)."""
    if txt is None:
        return []
    if isinstance(txt, (int, float)):
        return [float(txt)]
    out: list[Optional[float]] = []
    for tok in str(txt).replace("\xa0", " ").replace("€", " ").split():
        if tok in ("-", "–", "nc", "NC", "/", "x", "X"):
            out.append(None)
            continue
        try:
            out.append(float(tok.replace(",", ".")))
        except ValueError:
            return []
    return out


def _unite_libelle(txt: str) -> Optional[str]:
    s = _norm(txt)
    if not s:
        return None
    if "100" in s and "kg" in s or "/100" in s or "cent" in s:
        return "au_100kg"
    if "forfait" in s:
        return "forfait"
    if "/kg" in s or "au kg" in s or "par kg" in s:
        return "au_kg"
    return None


def lignes_depuis_tableau(table: list[list[Any]], contexte: str = "") -> tuple[list[dict], list[str]]:
    """Lit un tableau (lignes × cellules) et rend des lignes tarifaires.

    Un tableau peut porter plusieurs blocs d'en-têtes (une page PDF qui
    enchaîne deux grilles) : chaque ligne d'en-têtes ouvre un nouveau bloc.
    """
    lignes: list[dict] = []
    avert: list[str] = []
    ctx = _norm(contexte)
    rows = [list(r) for r in table if r]
    i = 0
    while i < len(rows):
        cands = [(j, t) for j, c in enumerate(rows[i]) if (t := lire_tranche(c))]
        if len(cands) < 2:
            i += 1
            continue
        cols = [j for j, _ in cands]
        tranches = [dict(t) for _, t in cands]
        # Bornes manquantes : déduites des voisines.
        for k, t in enumerate(tranches):
            if t["min"] is None:
                prev = tranches[k - 1]["max"] if k else None
                t["min"] = (prev + 1 if prev is not None and float(prev).is_integer() else prev) if prev is not None else 0.0
        bases = {t["base"] for t in tranches if t["base"]}
        base = bases.pop() if len(bases) == 1 else None
        if base is None:
            petits = all(t["max"] is not None and t["max"] == t["min"] and t["max"] <= 33 for t in tranches)
            base = "palette" if petits and ("pal" in ctx or "palette" in _norm(" ".join(map(str, rows[i])))) else "poids"
        # Unité par colonne : ligne de libellés juste au-dessus ou au-dessous,
        # cellules fusionnées propagées vers la droite.
        unites: dict[int, str] = {}
        for k in (i - 2, i - 1, i + 1):
            if 0 <= k < len(rows) and k != i:
                courant = None
                for j, c in enumerate(rows[k]):
                    u = _unite_libelle(c) if c not in (None, "") else None
                    courant = u or (courant if c in (None, "") else None)
                    if courant and j in cols:
                        unites.setdefault(j, courant)
        cent_kg = bool(re.search(r"100\s*kg|/\s*100|cent kilo", ctx))
        for j, t in zip(cols, tranches):
            if base != "poids":
                t["unite"] = "forfait"
            elif j in unites:
                t["unite"] = unites[j]
            elif cent_kg:
                t["unite"] = "forfait" if (t["max"] is not None and t["max"] <= 100) else "au_100kg"
            else:
                t["unite"] = "forfait"

        premier = cols[0]
        i += 1
        lus = sautes = 0
        while i < len(rows):
            r = rows[i]
            if len([1 for c in r if lire_tranche(c)]) >= 2:
                break  # nouveau bloc d'en-têtes
            zone = lire_zone(" ".join(str(c) for c in r[:premier] if c not in (None, "")))
            i += 1
            if not zone:
                continue
            cellules = r[premier:]
            fusion = any(len(_nombres(c)) > 1 for c in cellules)
            if fusion:
                prix = [p for c in cellules for p in _nombres(c)]
            else:
                prix = []
                for j in cols:
                    n = _nombres(r[j]) if j < len(r) else []
                    prix.append(n[0] if n else None)
            if len(prix) != len(tranches):
                sautes += 1
                continue
            for t, p in zip(tranches, prix):
                if p is None:
                    continue
                lignes.append({
                    "type_envoi": "messagerie",
                    "base_calcul": base,
                    "zone_type": zone[0],
                    "zone_valeur": zone[1],
                    "tranche_min": t["min"],
                    "tranche_max": t["max"],
                    "prix": p,
                    "unite": t["unite"],
                })
            lus += 1
        if sautes:
            avert.append(f"{sautes} ligne(s) de zone ignorée(s) : nombre de prix différent du nombre de tranches.")
    return lignes, avert


def date_effet_du_texte(texte: str) -> Optional[str]:
    m = re.search(
        r"(?:applicable|vigueur|effet|valable)\D{0,25}?(\d{1,2})[./-](\d{1,2})[./-](\d{4})",
        texte or "", re.I,
    )
    if not m:
        return None
    j, mo, a = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if 1 <= j <= 31 and 1 <= mo <= 12:
        return f"{a:04d}-{mo:02d}-{j:02d}"
    return None


# ─── Lecteurs par format ─────────────────────────────────────────────

_COLS_CSV = {"type_envoi", "base_calcul", "zone_type", "zone_valeur", "tranche_min", "prix", "unite"}


def _lire_csv(contenu: bytes) -> tuple[list[dict], list[str], str]:
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            texte = contenu.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    premiere = texte.splitlines()[0] if texte else ""
    delim = ";" if premiere.count(";") > premiere.count(",") else ("\t" if "\t" in premiere else ",")
    rows = list(csv.reader(io.StringIO(texte), delimiter=delim))
    if rows and _COLS_CSV.issubset({c.strip() for c in rows[0]}):
        entetes = [c.strip() for c in rows[0]]
        return [dict(zip(entetes, r)) for r in rows[1:] if any(r)], [], "csv"
    lignes, avert = lignes_depuis_tableau(rows, texte[:5000])
    return lignes, avert, "csv_tableau"


def _lire_excel(contenu: bytes, nom: str) -> tuple[list[dict], list[dict], list[str], str, str]:
    try:
        import openpyxl
    except ImportError:
        raise LectureErreur("openpyxl absent du serveur : lecture Excel impossible.")
    if nom.lower().endswith(".xls"):
        raise LectureErreur("Ancien format .xls : l'enregistrer en .xlsx puis recommencer.")
    try:
        wb = openpyxl.load_workbook(io.BytesIO(contenu), data_only=True, read_only=False)
    except Exception:
        raise LectureErreur("Fichier Excel illisible.")
    texte = []
    tables = []
    for ws in wb.worksheets:
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        tables.append((ws.title, rows))
        texte.append(f"=== Feuille : {ws.title} ===")
        texte.extend("\t".join("" if c is None else str(c) for c in r) for r in rows if any(c is not None for c in r))
    texte_complet = "\n".join(texte)

    fmt = _detect_tarif_format(wb)
    if fmt == "compte100346":
        lignes, frais = _parse_compte100346(wb, nom)
    elif fmt == "ceva":
        lignes, frais = _parse_ceva(wb, nom)
    elif fmt == "transbenelux":
        lignes, frais = _parse_transbenelux(wb, nom)
    else:
        lignes, frais = [], []
    if lignes:
        return lignes, frais, [], f"excel_{fmt}", texte_complet
    avert: list[str] = []
    for titre, rows in tables:
        lg, av = lignes_depuis_tableau(rows, titre + "\n" + texte_complet[:5000])
        lignes += lg
        avert += [f"{titre} : {a}" for a in av]
    return lignes, [], avert, "excel_tableau", texte_complet


def _lire_pdf(contenu: bytes) -> tuple[list[dict], list[str], str]:
    try:
        import pdfplumber
    except ImportError:
        raise LectureErreur("pdfplumber absent du serveur : lecture PDF impossible.")
    lignes: list[dict] = []
    avert: list[str] = []
    textes = []
    try:
        with pdfplumber.open(io.BytesIO(contenu)) as pdf:
            pages = pdf.pages[:_MAX_PAGES_PDF]
            for p in pages:
                textes.append(p.extract_text() or "")
            contexte = "\n".join(textes)
            for n, p in enumerate(pages, start=1):
                tables = p.extract_tables() or []
                trouve = False
                for t in tables:
                    lg, av = lignes_depuis_tableau(t, contexte)
                    if lg:
                        trouve = True
                    lignes += lg
                    avert += [f"page {n} : {a}" for a in av]
                if not trouve:
                    # Tableau sans filets : colonnes séparées par des blancs.
                    brut = p.extract_text(layout=True) or ""
                    rows = [re.split(r"\s{2,}", ligne.strip()) for ligne in brut.splitlines() if ligne.strip()]
                    lg, av = lignes_depuis_tableau(rows, contexte)
                    lignes += lg
                    avert += [f"page {n} : {a}" for a in av]
    except LectureErreur:
        raise
    except Exception:
        raise LectureErreur("PDF illisible (protégé ou endommagé).")
    return lignes, avert, "\n".join(textes)


# ─── Repli Claude ────────────────────────────────────────────────────

_SCHEMA_IA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["grilles", "frais", "date_effet"],
    "properties": {
        "date_effet": {"type": ["string", "null"]},
        "grilles": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["type_envoi", "base_calcul", "tranches", "zones"],
                "properties": {
                    "type_envoi": {"type": "string", "enum": ["messagerie", "ramasse", "affretement", "express_intl"]},
                    "base_calcul": {"type": "string", "enum": ["poids", "palette", "metre_plancher"]},
                    "tranches": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["min", "max", "unite"],
                            "properties": {
                                "min": {"type": "number"},
                                "max": {"type": ["number", "null"]},
                                "unite": {"type": "string", "enum": ["forfait", "au_100kg", "au_kg"]},
                            },
                        },
                    },
                    "zones": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["zone_type", "zone", "prix"],
                            "properties": {
                                "zone_type": {"type": "string", "enum": ["departement", "code_postal", "pays"]},
                                "zone": {"type": "string"},
                                "prix": {"type": "array", "items": {"type": ["number", "null"]}},
                            },
                        },
                    },
                },
            },
        },
        "frais": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["libelle", "mode", "valeur", "mini"],
                "properties": {
                    "libelle": {"type": "string"},
                    "mode": {"type": "string", "enum": ["pct_transport", "forfait_expedition", "par_palette"]},
                    "valeur": {"type": "number"},
                    "mini": {"type": ["number", "null"]},
                },
            },
        },
    },
}

_CONSIGNE_IA = """Ce document est une grille tarifaire de transporteur (messagerie, palettes, affrètement).
Rends-la en tableaux compacts, sans recopier chaque case sous forme de ligne :

- une entrée dans `grilles` par tableau de prix (par exemple une grille au poids et une grille à la palette) ;
- `tranches` : les colonnes de prix dans l'ordre, une fois chacune. Bornes en kg pour le poids, en nombre
  de palettes pour la palette, en mètres pour le mètre plancher. « De 1 à 10 kg » donne min 1, max 10.
  Une dernière tranche ouverte (« + de 2000 ») a max null. `unite` vaut « forfait » pour un prix par envoi,
  « au_100kg » pour un prix aux 100 kg, « au_kg » pour un prix au kilo ;
- `zones` : une entrée par ligne du tableau. `prix` suit exactement l'ordre de `tranches` (null pour une case
  vide, « NC » ou « - »). Département français : `zone_type` « departement », `zone` sur deux caractères
  (« 01 », « 2A », « 59 ») ou trois pour l'outre-mer (« 971 »). Code postal : « code_postal ». Autre pays :
  « pays », avec le nom du pays suivi de son code de zone tel qu'écrit (« Italie 00 ») ;
- `frais` : les frais annexes chiffrés (gazole, sûreté, prise de rendez-vous, hayon…) ;
- `date_effet` : la date d'entrée en vigueur au format AAAA-MM-JJ, ou null.

Ne rends que les prix réellement écrits dans le document. N'invente aucune zone ni aucune tranche."""


def _client_ia():
    cle = os.getenv("ANTHROPIC_API_KEY", "")
    if not cle:
        raise LectureErreur("Format non reconnu, et l'assistant IA est indisponible (clé ANTHROPIC_API_KEY absente).")
    import anthropic

    return anthropic.Anthropic(api_key=cle)


def _lire_ia(contenu: bytes, nom: str, texte: str) -> tuple[list[dict], list[dict], Optional[str]]:
    """Fait lire le fichier par Claude et rend les lignes dépliées."""
    client = _client_ia()
    if nom.lower().endswith(".pdf"):
        bloc = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                               "data": base64.standard_b64encode(contenu).decode()}}
    else:
        if not texte.strip():
            raise LectureErreur("Fichier vide.")
        if len(texte) > _MAX_TEXTE_IA:
            raise LectureErreur("Fichier trop volumineux pour l'assistant — le découper par onglet.")
        bloc = {"type": "text", "text": "Contenu du fichier (une ligne par rangée, cellules séparées par des tabulations) :\n\n" + texte}
    try:
        with client.messages.stream(
            model=TARIF_TRANSPORT_IA_MODELE,
            max_tokens=64000,
            messages=[{"role": "user", "content": [bloc, {"type": "text", "text": _CONSIGNE_IA}]}],
            extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
            extra_body={
                "output_config": {"effort": "medium", "format": {"type": "json_schema", "schema": _SCHEMA_IA}},
                "fallbacks": "default",
            },
        ) as flux:
            reponse = flux.get_final_message()
    except LectureErreur:
        raise
    except Exception as e:
        raise LectureErreur(f"Lecture par l'assistant en échec : {e}")
    ia_usage.noter(reponse, "tarif_transport")
    ia_usage.preciser(modele_demande=TARIF_TRANSPORT_IA_MODELE, fichiers=1)
    raison = getattr(reponse, "stop_reason", "")
    if raison == "refusal":
        raise LectureErreur("L'assistant a refusé de lire ce document.")
    if raison == "max_tokens":
        raise LectureErreur("Grille trop longue pour une lecture en un passage — la découper (France / international).")
    brut = "".join(getattr(b, "text", "") for b in reponse.content if getattr(b, "type", "") == "text")
    try:
        data = json.loads(brut)
    except ValueError:
        raise LectureErreur("Réponse illisible de l'assistant — recommencer.")
    return deplier_grilles_ia(data), list(data.get("frais") or []), data.get("date_effet")


def deplier_grilles_ia(data: dict) -> list[dict]:
    """Tableaux compacts rendus par Claude → lignes au schéma `expe_tarifs`."""
    lignes = []
    for g in data.get("grilles") or []:
        tranches = g.get("tranches") or []
        for z in g.get("zones") or []:
            prix = z.get("prix") or []
            if len(prix) != len(tranches):
                continue
            zt = z.get("zone_type") or "departement"
            zv = str(z.get("zone") or "").strip()
            if zt == "departement":
                if zv.isdigit() and len(zv) == 1:
                    zv = zv.zfill(2)
                d = _tarif_dept_from_label(zv) if not re.fullmatch(r"2[AB]", zv, re.I) else zv.upper()
                if not d:
                    continue
                zv = d
            for t, p in zip(tranches, prix):
                if p is None:
                    continue
                lignes.append({
                    "type_envoi": g.get("type_envoi"),
                    "base_calcul": g.get("base_calcul"),
                    "zone_type": zt,
                    "zone_valeur": zv,
                    "tranche_min": t.get("min"),
                    "tranche_max": t.get("max"),
                    "prix": p,
                    "unite": t.get("unite"),
                })
    return lignes


# ─── Point d'entrée ──────────────────────────────────────────────────


def lire(contenu: bytes, nom: str, ia: bool = True) -> dict:
    """Lit un fichier de tarifs. Rend lignes, frais, méthode, avertissements, date d'effet.

    `ia=False` interdit le repli Claude (tests, ou lecture sans clé).
    """
    nom = os.path.basename(nom or "tarif")
    ext = os.path.splitext(nom)[1].lower()
    if ext not in EXTENSIONS:
        raise LectureErreur(f"Format {ext or 'inconnu'} non pris en charge — PDF, Excel (.xlsx) ou CSV.")
    if not contenu:
        raise LectureErreur("Fichier vide.")
    frais: list[dict] = []
    texte = ""
    if ext == ".csv":
        lignes, avert, methode = _lire_csv(contenu)
        texte = contenu[:200_000].decode("utf-8", "ignore")
    elif ext == ".pdf":
        lignes, avert, texte = _lire_pdf(contenu)
        methode = "pdf_tableau"
    else:
        lignes, frais, avert, methode, texte = _lire_excel(contenu, nom)
    date_effet = date_effet_du_texte(texte)

    if not lignes and ia:
        lignes, frais, d_ia = _lire_ia(contenu, nom, texte)
        methode = "ia"
        date_effet = date_effet or d_ia
        avert = []
    if not lignes:
        raise LectureErreur("Aucune grille de prix reconnue dans ce fichier.")
    return {"lignes": lignes, "frais": frais, "methode": methode,
            "avertissements": avert[:20], "date_effet": date_effet}

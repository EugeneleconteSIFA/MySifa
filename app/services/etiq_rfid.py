"""
MyTools › Étiquettes — encodage RFID (EPC Gen2) imprimé avec l'étiquette.

EPC tirés des données GS1 de l'étiquette (GS1 EPC Tag Data Standard) :
  SGTIN-96   GTIN-14 (AI 01) + numéro de série numérique (AI 21)
  SSCC-96    SSCC (AI 00)
La longueur du préfixe entreprise GS1 (6 à 12 chiffres) fixe la partition ;
elle vient de l'élément RFID du modèle, sinon de la longueur de
ETIQ_GS1_PREFIXE (config.py) passée par l'appelant.

ZPL : ^RS8 (Gen2) puis ^RFW,H,,,A^FD<hex>^FS (écriture de l'EPC, bits PC
ajustés par l'imprimante). Une imprimante sans module RFID ignore ou refuse
ces commandes : seul un profil marqué « RFID » les reçoit.

Module pur, testé par tests/test_etiq_zpl.py (exemple officiel du TDS).
"""

from __future__ import annotations

import re
from typing import Optional

# Partition : longueur du préfixe → (n° de partition, bits préfixe, bits référence)
_PART_SGTIN = {12: (0, 40, 4), 11: (1, 37, 7), 10: (2, 34, 10), 9: (3, 30, 14), 8: (4, 27, 17), 7: (5, 24, 20),
               6: (6, 20, 24)}
_PART_SSCC = {12: (0, 40, 18), 11: (1, 37, 21), 10: (2, 34, 24), 9: (3, 30, 28), 8: (4, 27, 31), 7: (5, 24, 34),
              6: (6, 20, 38)}
_AI_RE = re.compile(r"\((\d{2,4})\)([^(]*)")


class EpcInvalide(ValueError):
    """Message factuel, affiché tel quel."""


def _bits(valeur: int, n: int) -> str:
    if valeur < 0 or valeur >= (1 << n):
        raise EpcInvalide("Valeur hors capacité du champ EPC.")
    return format(valeur, f"0{n}b")


def _hex(bits: str) -> str:
    return format(int(bits, 2), "024X")


def sgtin96(gtin14: str, serie, longueur_prefixe: int, filtre: int = 1) -> str:
    g = re.sub(r"\D", "", gtin14 or "")
    if len(g) != 14:
        raise EpcInvalide("SGTIN-96 : GTIN de 14 chiffres attendu.")
    if longueur_prefixe not in _PART_SGTIN:
        raise EpcInvalide("Préfixe GS1 : 6 à 12 chiffres.")
    s = str(serie or "").strip()
    if not s.isdigit() or (len(s) > 1 and s.startswith("0")):
        raise EpcInvalide("SGTIN-96 : numéro de série numérique sans zéro de tête attendu.")
    p, bp, br = _PART_SGTIN[longueur_prefixe]
    prefixe = int(g[1:1 + longueur_prefixe])
    ref = int(g[0] + g[1 + longueur_prefixe:13])
    bits = "00110000" + _bits(filtre, 3) + _bits(p, 3) + _bits(prefixe, bp) + _bits(ref, br) + _bits(int(s), 38)
    return _hex(bits)


def sscc96(sscc18: str, longueur_prefixe: int, filtre: int = 2) -> str:
    s = re.sub(r"\D", "", sscc18 or "")
    if len(s) != 18:
        raise EpcInvalide("SSCC-96 : SSCC de 18 chiffres attendu.")
    if longueur_prefixe not in _PART_SSCC:
        raise EpcInvalide("Préfixe GS1 : 6 à 12 chiffres.")
    p, bp, br = _PART_SSCC[longueur_prefixe]
    prefixe = int(s[1:1 + longueur_prefixe])
    ref = int(s[0] + s[1 + longueur_prefixe:17])
    bits = "00110001" + _bits(filtre, 3) + _bits(p, 3) + _bits(prefixe, bp) + _bits(ref, br) + "0" * 24
    return _hex(bits)


def epc_depuis_gs1(donnee: str, longueur_prefixe: int) -> Optional[str]:
    """EPC d'une donnée GS1 « (00)… » ou « (01)…(21)… », None sinon."""
    ais = dict(_AI_RE.findall(re.sub(r"\s+", "", donnee or "")))
    if "00" in ais:
        return sscc96(ais["00"], longueur_prefixe)
    if "01" in ais and "21" in ais:
        return sgtin96(ais["01"], ais["21"], longueur_prefixe)
    return None


def epc_element(e: dict, valeur: str, longueur_prefixe_defaut: int) -> str:
    """EPC (hexadécimal) d'un élément « rfid » du modèle.
    schema : sscc96 | sgtin96 | gs1 (déduit des AI) | hex (EPC donné tel quel)."""
    schema = (e.get("schema") or "gs1").lower()
    lp = int(e.get("longueur_prefixe") or longueur_prefixe_defaut or 0)
    v = (valeur or "").strip()
    if schema == "hex":
        h = re.sub(r"[^0-9A-Fa-f]", "", v).upper()
        if not h or len(h) % 4:
            raise EpcInvalide("EPC hexadécimal : multiple de 4 caractères attendu.")
        return h
    if schema == "sscc96":
        return sscc96(v, lp)
    if schema == "sgtin96":
        ais = dict(_AI_RE.findall(v))
        if ais:
            return sgtin96(ais.get("01", ""), ais.get("21", ""), lp)
        gtin, _, serie = v.partition(" ")
        return sgtin96(gtin, serie, lp)
    epc = epc_depuis_gs1(v, lp)
    if not epc:
        raise EpcInvalide("RFID : donnée GS1 sans SSCC (00) ni GTIN + série (01)(21).")
    return epc


def zpl_rfid(epc_hex: str) -> str:
    return f"^RS8^RFW,H,,,A^FD{epc_hex}^FS"

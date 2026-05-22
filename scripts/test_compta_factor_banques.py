#!/usr/bin/env python3
"""Test mapping code vendeur Factor → compte CAF (compta_banques)."""
import os
import sys
import sqlite3
import tempfile
from contextlib import contextmanager
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from app.routers import compta as compta_mod


@contextmanager
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    now = datetime.now().isoformat()
    conn.execute(
        """CREATE TABLE compta_banques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_vendeur TEXT NOT NULL UNIQUE,
            numero_compte TEXT NOT NULL,
            libelle TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE compta_comptes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            libelle_condense TEXT NOT NULL,
            libelle_key TEXT NOT NULL UNIQUE,
            numero_compte TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE compta_acheteurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_vendeur TEXT,
            identifiant TEXT NOT NULL,
            raison_sociale TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(code_vendeur, identifiant)
        )"""
    )
    for code, num in (("100", "512330000000"), ("98", "519320000000")):
        conn.execute(
            "INSERT INTO compta_banques (code_vendeur, numero_compte, libelle, created_at, updated_at) VALUES (?,?,?,?,?)",
            (code, num, f"Factor {code}", now, now),
        )
    conn.commit()

    @contextmanager
    def _get_db():
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    orig = compta_mod.get_db
    compta_mod.get_db = _get_db
    try:
        yield conn
    finally:
        compta_mod.get_db = orig
        conn.close()
        os.unlink(path)


def _factor_table(code_vendeur: str, libelle: str = "Achat de Factures"):
    return [
        [
            "Code vendeur",
            "Date comptable de l'écriture",
            "Libellé condensé",
            "Montant du débit",
            "Montant du crédit",
            "Données de l'acheteur concerné par l'opération",
            "Complément sur l'acheteur concerné par l'opération",
        ],
        [code_vendeur, "2025-01-15", libelle, 100, 0, "", ""],
    ]


def test_vendeur_100_and_98():
    with temp_db():
        r100 = compta_mod._transform_factor_table(_factor_table("100"))
        r98 = compta_mod._transform_factor_table(_factor_table("98"))
        caf100 = [x for x in r100["rows"] if x.get("debit") == 0 and x.get("credit") == 100]
        caf98 = [x for x in r98["rows"] if x.get("debit") == 0 and x.get("credit") == 100]
        assert caf100 and caf100[0]["compte"] == "512330000000", caf100
        assert caf98 and caf98[0]["compte"] == "519320000000", caf98
        assert not r100["missing"]["banques"], r100["missing"]["banques"]
        assert not r98["missing"]["banques"], r98["missing"]["banques"]


def test_vendeur_float_normalization():
    with temp_db():
        r = compta_mod._transform_factor_table(_factor_table("98.0"))
        caf = [x for x in r["rows"] if x.get("credit") == 100 and x.get("debit") == 0]
        assert caf and caf[0]["compte"] == "519320000000"


def test_unknown_vendeur_flags_missing():
    with temp_db():
        r = compta_mod._transform_factor_table(_factor_table("77"))
        caf = [x for x in r["rows"] if x.get("credit") == 100 and x.get("debit") == 0]
        assert caf and caf[0].get("problem") == "banque_manquante", caf
        assert r["missing"]["banques"], r["missing"]


def test_norm_code_vendeur():
    assert compta_mod._norm_code_vendeur("100.0") == "100"
    assert compta_mod._norm_code_vendeur(" 98 ") == "98"


if __name__ == "__main__":
    test_norm_code_vendeur()
    test_vendeur_100_and_98()
    test_vendeur_float_normalization()
    test_unknown_vendeur_flags_missing()
    print("OK — tous les tests compta banques passent.")

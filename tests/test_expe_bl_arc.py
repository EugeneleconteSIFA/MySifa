"""MyExpé — badge « lié / lié auto / non lié » du BL × ARC au suivi des départs.

Verrouille la lecture des champs saisis à la main et le classement :
un rattachement fait dans le sélecteur RVGI l'emporte ; à défaut, le BL et
l'ARC doivent se recouper dans le miroir pour être « lié auto » ; sinon la
raison est dite.
"""
import sys

sys.path.insert(0, ".")

import database  # noqa: F401  (shim d'abord, cf. CLAUDE.md)
from app.services import expe_bl_arc as b


def test_numeros():
    assert b.numeros("9939126") == ["9939126"]
    assert b.numeros("9932610+611+612+613") == ["9932610", "9932611", "9932612", "9932613"]
    # Un nombre court hors d'une vitrine compacte n'est pas un numéro de pièce.
    assert b.numeros("9932344 (marché 751)") == ["9932344"]
    assert b.numeros("BL 9939126, 9939127") == ["9939126", "9939127"]
    assert b.numeros(None) == [] and b.numeros("—") == []


def test_classement():
    miroir = {"9939126": {"9932699"}, "9939125": {"9932600"}}
    assert b.evaluer({"rvgi_etat": "lie", "no_bl": ""}, miroir)["etat"] == b.LIE
    assert b.evaluer({"no_bl": "9939126", "arc": "9932699"}, miroir)["etat"] == b.LIE_AUTO
    r = b.evaluer({"no_bl": "9939125", "arc": "9932656"}, miroir)
    assert r["etat"] == b.NON_LIE and "9932600" in r["detail"]
    assert b.evaluer({"no_bl": "", "arc": "9932656"}, miroir)["detail"] == "Pas de n° de BL"
    assert b.evaluer({"no_bl": "9939126", "arc": ""}, miroir)["detail"] == "Pas d'ARC"
    assert "inconnu" in b.evaluer({"no_bl": "9999999", "arc": "9932699"}, miroir)["detail"]
    assert "indisponible" in b.evaluer({"no_bl": "9939126", "arc": "9932699"}, None)["detail"]
    # Plusieurs commandes dans l'ARC : un BL qui en livre une suffit.
    assert b.evaluer({"no_bl": "9939126", "arc": "9932698+699"}, miroir)["etat"] == b.LIE_AUTO


if __name__ == "__main__":
    test_numeros()
    test_classement()
    print("ok")

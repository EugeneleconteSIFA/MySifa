# -*- coding: utf-8 -*-
"""Déclaration UE de conformité — section « Contact alimentaire ».

Absente par défaut, ajoutée seulement si cochée, et refusée à la génération
tant qu'un passage « [à compléter » reste dans le texte (l'aperçu l'accepte).
"""
import sys
sys.path.insert(0, ".")
import database  # noqa: F401  (shim d'abord, cf. CLAUDE.md)

import pytest
from app.services import sifa_doc_pdf as d

BASE = dict(client_nom="Client test",
            fournisseurs=[{"nom": "Fournisseur", "pays_origine": "France"}],
            ref="TEST-1", date_emission_iso="2026-11-25")
SOUS = ("sec_ca_1", "sec_ca_2", "sec_ca_3", "sec_ca_4")


def test_absente_par_defaut():
    assert d.build_declaration_ue_pdf(**BASE)[:4] == b"%PDF"


def test_refusee_tant_qu_il_reste_a_completer():
    with pytest.raises(d.SectionsIncompletes) as e:
        d.build_declaration_ue_pdf(**BASE, sections_overrides={"sec_ca": {"include": True}})
    assert "5.3 Conditions d'utilisation" in str(e.value)


def test_apercu_accepte_les_passages_a_completer():
    pdf = d.build_declaration_ue_pdf(**BASE, brouillon=True,
                                     sections_overrides={"sec_ca": {"include": True}})
    assert pdf[:4] == b"%PDF"


def test_complete_generee():
    ov = {"sec_ca": {"include": True}}
    ov.update({k: {"custom_body": "Texte renseigné."} for k in SOUS})
    assert d.build_declaration_ue_pdf(**BASE, sections_overrides=ov)[:4] == b"%PDF"


def test_textes_par_defaut_des_autres_sections_sans_marque():
    for s in d.SECTIONS_META:
        if s["id"].startswith("sec_ca"):
            continue
        assert d.MARQUE_A_COMPLETER not in (s.get("default_body") or ""), s["id"]

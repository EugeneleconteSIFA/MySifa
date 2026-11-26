# -*- coding: utf-8 -*-
"""Déclaration UE de conformité — section « Contact alimentaire ».

Absente par défaut, ajoutée seulement si cochée, et refusée à la génération
tant qu'un passage « [à compléter » reste dans le texte (l'aperçu l'accepte).

Script autonome, comme les autres tests du dépôt : la CI les lance avec
`python tests/<nom>.py` et n'installe pas pytest (le 26/11/2026, la première
version, écrite pour pytest, plantait sur GitHub dès `import pytest`).
"""
import sys
sys.path.insert(0, ".")
import database  # noqa: F401,E402  (shim d'abord, cf. CLAUDE.md)

from app.services import sifa_doc_pdf as d  # noqa: E402

BASE = dict(client_nom="Client test",
            fournisseurs=[{"nom": "Fournisseur", "pays_origine": "France"}],
            ref="TEST-1", date_emission_iso="2026-11-25")
SOUS = ("sec_ca_1", "sec_ca_2", "sec_ca_3", "sec_ca_4")

ko = 0


def check(libelle, ok, detail=""):
    global ko
    if not ok:
        ko += 1
    print(f"  {'OK ' if ok else 'KO '} {libelle}" + (f" — {detail}" if detail and not ok else ""))


print("\nContact alimentaire")
check("absente par défaut : le PDF se génère", d.build_declaration_ue_pdf(**BASE)[:4] == b"%PDF")

try:
    d.build_declaration_ue_pdf(**BASE, sections_overrides={"sec_ca": {"include": True}})
    refus = None
except d.SectionsIncompletes as e:
    refus = e
check("refusée tant qu'il reste « à compléter »", refus is not None)
check("le refus nomme la sous-section", refus is not None and "5.3 Conditions d'utilisation" in str(refus), str(refus))

pdf = d.build_declaration_ue_pdf(**BASE, brouillon=True, sections_overrides={"sec_ca": {"include": True}})
check("l'aperçu accepte les passages à compléter", pdf[:4] == b"%PDF")

ov = {"sec_ca": {"include": True}}
ov.update({k: {"custom_body": "Texte renseigné."} for k in SOUS})
check("complète : générée", d.build_declaration_ue_pdf(**BASE, sections_overrides=ov)[:4] == b"%PDF")

marquees = [s["id"] for s in d.SECTIONS_META
            if not s["id"].startswith("sec_ca") and d.MARQUE_A_COMPLETER in (s.get("default_body") or "")]
check("les autres sections n'ont pas de passage à compléter par défaut", not marquees, ", ".join(marquees))

print()
if ko:
    print(f"test_sifa_doc_contact_alimentaire : {ko} échec(s)")
    sys.exit(1)
print("test_sifa_doc_contact_alimentaire : OK")

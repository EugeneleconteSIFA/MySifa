# -*- coding: utf-8 -*-
"""MyQualité › FSC : import d'un lot de contrôles.

Ce que ce test protège, et pourquoi chaque point a coûté cher :

1. La LECTURE d'un FSC Certification Record. Trois pièges, tous rencontrés sur
   les dossiers réels du 16/09/2026 :
   - les polices embarquées déclarent des largeurs fausses ; au réglage par
     défaut l'extraction rend « LicenseCode: » et plus rien n'est lisible ;
   - les blocs produit courts s'avalent l'un l'autre si on lit par fenêtre de
     taille fixe — « P7.8 Adhesive labels » disparaissait chez Avery Dennison ;
   - le pied de page se glisse dans le dernier champ d'un bloc.
2. La PORTÉE et les ALLÉGATIONS sont l'union de tous les blocs, dans l'ordre du
   référentiel, et « FSC Mix Credit » ne compte jamais aussi pour « FSC Mix ».
3. Le RAPPROCHEMENT retrouve une fiche dont le code de certificat est faux —
   cas Itasa, qui portait ceux de la filiale mexicaine. C'est la raison d'être
   de l'écran : une fiche fausse ne se répare pas par le code qu'elle porte.
4. Le CSV d'accompagnement ne corrige jamais une valeur lue.
5. La COUVERTURE de portée est hiérarchique : P7.8 est couvert par P7.

Lancer : python3 tests/test_fsc_import_controles.py
"""

from __future__ import annotations

import io
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from app.services.fsc_import_controles import (  # noqa: E402
    couvre_portee,
    ecarts,
    lire_csv,
    lire_record,
    rapprocher,
)

ECHECS: list[str] = []


def verifie(condition, libelle: str) -> None:
    if condition:
        print("  ok    %s" % libelle)
    else:
        print("  ECHEC %s" % libelle)
        ECHECS.append(libelle)


def egal(obtenu, attendu, libelle: str) -> None:
    verifie(obtenu == attendu, "%s (obtenu %r, attendu %r)" % (libelle, obtenu, attendu))


# ── Un dossier de démonstration, calqué sur la mise en page réelle ─────────
# Les blocs produit sont volontairement courts et collés : c'est la forme qui
# faisait disparaître le bloc du milieu.

PAGES = [
    [
        "FSC CERTIFICATION RECORD",
        "",
        "License Code: FSC-C004451",
        "Certificate Code: CU-COC-807907",
        "Old certificate code:",
        "Primary Certificate Holder",
        "Company Name: Avery Dennison Netherland Investment",
        "II BV",
        "Local Name:",
        "Address: Willem Einthovenstraat 11-2342 BH",
        "NETHERLANDS-",
        "Website",
        "Certification status: Valid",
        "Date of first issue: Aug 20, 2007",
        "Last status update: Aug 10, 2022",
        "Expiry date: Aug 09, 2027",
        "Certified Forest Area: N/A",
        "Standards assessed: FSC-STD-40-003 V2-1;FSC-STD-40-004 V3-1",
        "Due diligence system for No",
        "FSC controlled wood:",
        "FSC Certification File - FSC-C004451 Page 1 about 3",
    ],
    [
        "FSC CERTIFICATION RECORD",
        "",
        "Products,Species,and product category details",
        "PRODUCT CATEGORY:",
        "P2 Paper",
        "TRADE NAME:",
        "PRIMARY ACTIVITY:",
        "Printing and related service",
        "SECONDARY ACTIVITY:",
        "MAIN OUTPUT CATEGORY:",
        "FSC Mix",
        "TREE SPECIES:",
        "PRODUCT CATEGORY:",
        "P7.8 Adhesive labels",
        "TRADE NAME:",
        "PRIMARY ACTIVITY:",
        "Secondary Processor",
        "SECONDARY ACTIVITY:",
        "MAIN OUTPUT CATEGORY:",
        "FSC Mix Credit;FSC Recycled",
        "TREE SPECIES:",
        "Not Applicable",
        "FSC Certification File - FSC-C004451 Page 2 about 3",
    ],
    [
        "FSC CERTIFICATION RECORD",
        "",
        "PRODUCT CATEGORY:",
        "P10 Other pulp and paper products n.e.c.",
        "TRADE NAME:",
        "PRIMARY ACTIVITY:",
        "Primary Processor",
        "SECONDARY ACTIVITY:",
        "MAIN OUTPUT CATEGORY:",
        "FSC Mix",
        "TREE SPECIES:",
        "* IMPORTANT NOTICE",
        "Certification information and data are managed by the Certification Body.",
        "FSC Certification File - FSC-C004451 Page 3 about 3",
    ],
]


def dossier_pdf(pages: list[list[str]]) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    tampon = io.BytesIO()
    c = canvas.Canvas(tampon, pagesize=A4)
    for lignes in pages:
        y = 800
        c.setFont("Helvetica", 9)
        for ligne in lignes:
            c.drawString(50, y, ligne)
            y -= 14
        c.showPage()
    c.save()
    return tampon.getvalue()


print("\n--- 1. lecture d'un FSC Certification Record ---")
lu = lire_record(dossier_pdf(PAGES))
verifie(lu.get("ok"), "le dossier est reconnu")
egal(lu.get("licence"), "FSC-C004451", "licence")
egal(lu.get("certificat"), "CU-COC-807907", "code de certificat")
egal(lu.get("ancien_certificat"), None, "ancien code absent, pas inventé")
egal(lu.get("statut_base"), "valide", "statut")
egal(lu.get("date_expiration_lue"), "2027-08-09", "expiration")
egal(lu.get("date_premiere_emission"), "2007-08-20", "première émission")
egal(lu.get("titulaire"), "Avery Dennison Netherland Investment II BV",
     "raison sociale recollée sur deux lignes")
verifie("NETHERLANDS" in (lu.get("adresse") or ""), "adresse recollée")
verifie("Page 2 about 3" not in (lu.get("titulaire") or ""), "le pied de page n'entre pas dans un champ")

print("\n--- 2. portée et allégations ---")
egal(lu.get("portees"), ["P2", "P7.8", "P10"],
     "les trois blocs produit sont lus, y compris celui du milieu")
egal(lu.get("claims"), ["fsc_mix", "fsc_mix_credit", "fsc_recycled"],
     "allégations dans l'ordre du référentiel")
verifie("fsc_controlled_wood" not in lu.get("claims", []),
        "« FSC controlled wood: » du champ DDS n'est pas une allégation")

print("\n--- 3. refus de ce qui n'est pas un dossier FSC ---")
autre = lire_record(dossier_pdf([["Facture 26090002", "Client Calabas Industrie"]]))
verifie(not autre.get("ok"), "un PDF quelconque est refusé")
verifie("Certification Record" in (autre.get("erreur") or ""), "le refus dit pourquoi")

print("\n--- 4. CSV d'accompagnement ---")
CSV = (
    "date_controle;statut_base;fournisseur;licence;certificat;date_expiration_lue;"
    "titulaire_du_certificat;justificatif_filename;liste_fournisseurs_fsc;motif\n"
    "2026-09-16;Valide;Avery Dennison;FSC-C004451;CU-COC-807907;2027-08-09;"
    "Avery Dennison Netherland Investment II BV;x.pdf;Oui;\n"
    "2026-09-16;Valide;Imprimerie Feys;FSC-C017070;SGSCH-COC-004366;2028-03-09;"
    "Drukkerij Feys NV;y.pdf;Non;\"Portee P7.6;P8.4 hors etiquettes\"\n"
)
meta = lire_csv(CSV.encode("utf-8-sig"))
egal(sorted(meta), ["CU-COC-807907", "SGSCH-COC-004366"], "deux lignes indexées par certificat")
egal(meta["CU-COC-807907"]["dans_liste"], True, "Avery reste dans la liste")
egal(meta["SGSCH-COC-004366"]["dans_liste"], False, "Feys en sort")
verifie("etiquettes" in (meta["SGSCH-COC-004366"]["motif"] or ""), "le motif est conservé")

print("\n--- 5. rapprochement avec les fiches ---")
FICHES = [
    {"id": 1, "nom": "Avery", "licence": "FSC-C004451", "certificat": "CU-COC-807907",
     "fsc_date_expiration": "2027-08-09"},
    {"id": 11, "nom": "Itasa", "licence": "FSC-C160893", "certificat": "AEN-COC-000369",
     "fsc_date_expiration": "2028-12-31"},
    {"id": 24, "nom": "Xinzhu", "licence": "FSC-C177953", "certificat": None,
     "fsc_date_expiration": "2027-05-05"},
]
fiche, methode = rapprocher(FICHES, lu, "Avery Dennison")
egal((fiche or {}).get("id"), 1, "rapproché par code de certificat")
egal(methode, "certificat", "méthode annoncée")

xinzhu = {"certificat": "SGSHK-COC-331526", "licence": "FSC-C177953",
          "titulaire": "GUANGZHOU XINZHU ADHESIVE STICKER MATERIALS CO., LTD."}
fiche, methode = rapprocher(FICHES, xinzhu, "Guangzhou Xinzhu")
egal((fiche or {}).get("id"), 24, "fiche sans code de certificat rattrapée par la licence")
egal(methode, "licence", "méthode annoncée")

itasa = {"certificat": "AEN-COC-000252", "licence": "FSC-C145439",
         "date_expiration_lue": "2029-04-03",
         "titulaire": "INDUSTRIAS DE TRANSFORMACION DE ANDOAIN, S.A. (ITASA)"}
fiche, methode = rapprocher(FICHES, itasa, "Itasa")
egal((fiche or {}).get("id"), 11, "fiche dont les DEUX codes sont faux rattrapée par le nom")
egal(methode, "nom", "méthode annoncée")

inconnu = {"certificat": "XX-COC-999999", "licence": "FSC-C999999", "titulaire": "Société inconnue"}
fiche, methode = rapprocher(FICHES, inconnu, None)
egal(fiche, None, "aucun rapprochement forcé")
egal(methode, "aucun", "méthode annoncée")

print("\n--- 6. écarts avec la fiche ---")
diff = ecarts(FICHES[1], itasa)
egal(sorted(e["champ"] for e in diff),
     ["certificat", "fsc_date_expiration", "licence"], "les trois écarts Itasa sont vus")
egal([e for e in diff if e["champ"] == "certificat"][0]["avant"], "AEN-COC-000369", "valeur en base")
egal(ecarts(FICHES[0], lu), [], "aucune fiche juste n'est signalée en écart")
egal(ecarts(None, lu), [], "pas de fiche, pas d'écart")

print("\n--- 7. couverture de portée ---")
verifie(couvre_portee(["P7.8"], "P7.8"), "P7.8 couvre P7.8")
verifie(couvre_portee(["P7"], "P7.8"), "P7 couvre P7.8")
verifie(not couvre_portee(["P7.8"], "P7"), "P7.8 ne couvre pas tout P7")
verifie(couvre_portee(["P2.4"], "P2.4.5"), "P2.4 couvre P2.4.5")
verifie(not couvre_portee(["P7.6", "P8.4"], "P7.8"), "la portée de Feys ne couvre pas P7.8")
verifie(not couvre_portee([], "P7.8"), "portée vide ne couvre rien")

print("\n%s" % ("ECHECS : %d" % len(ECHECS) if ECHECS else "Tout est vert."))
sys.exit(1 if ECHECS else 0)

# -*- coding: utf-8 -*-
"""MyQualité › FSC : lecture des certificats, choix du document, dossier PDF.

Ce que ce test protège :

1. La LECTURE ne fabrique pas de catégorie. « FSC Controlled Wood » cité dans le
   titre d'une norme n'est pas un claim ; « FSC Mix Credit » n'est pas lu deux
   fois en « FSC Mix » ; une licence écrite « FSC® C007179 » est reconnue.
2. Le CHOIX du certificat ne présente jamais une pièce annexe (auto-déclaration
   RBUE, « Statement on FSC Directive ») comme le certificat, et retrouve un
   certificat rangé sous une autre branche du groupe par sa licence — sans
   l'attribuer à la branche qui l'héberge.
3. Le DOSSIER PDF sort même quand un fichier manque ou qu'un certificat est une
   photo : page de garde, un signet par fournisseur présent.
4. La MIGRATION est rejouable.

Lancer : python3 tests/test_fsc_fournisseurs.py
"""

from __future__ import annotations

import importlib.util
import io
import os
import sqlite3
import sys
import tempfile
from datetime import date

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from app.services.fsc_dossier import (  # noqa: E402
    choisir_document,
    construire_dossier_pdf,
    rang_document,
    statut_expiration,
)
from app.services.fsc_lecture_certificat import lire_motifs  # noqa: E402

ECHECS: list[str] = []


def verifie(condition, libelle: str) -> None:
    if condition:
        print("  ok   %s" % libelle)
    else:
        print("  ECHEC %s" % libelle)
        ECHECS.append(libelle)


def egal(obtenu, attendu, libelle: str) -> None:
    verifie(obtenu == attendu, "%s (obtenu %r, attendu %r)" % (libelle, obtenu, attendu))


# ── 1. Lecture ─────────────────────────────────────────────────────────────
print("\n--- 1. lecture d'un certificat ---")
lu = lire_motifs([(1, "\n".join([
    "Certificate code: CU-COC-807907",
    "FSC® C004451",
    "This certificate is valid until: 9 August 2027",
    "Product group P5.1  Output FSC claims: FSC Mix Credit, FSC Recycled Credit",
    "FSC-STD-40-005 Requirements for Sourcing FSC Controlled Wood",
]))])
egal(lu["licence"], "FSC-C004451", "licence écrite avec ®")
egal(lu["certificat"], "CU-COC-807907", "code certificat")
egal(lu["expiration"], "2027-08-09", "date « valid until » en toutes lettres")
egal([c["code"] for c in lu["claims"]], ["fsc_mix_credit", "fsc_recycled_credit"],
     "Credit reconnu sans doublon court, CW d'un titre de norme ignoré")

lu = lire_motifs([(2, "Expiry date: 11/02/2028\nFSC Mix 70% · FSC 100% · Claim: FSC Controlled Wood")])
egal([c["code"] for c in lu["claims"]], ["fsc_100", "fsc_mix", "fsc_controlled_wood"],
     "Mix x %, 100 % et Controlled Wood en claim")
egal(lu["expiration"], "2028-02-11", "date JJ/MM/AAAA")
egal(lu["claims"][0]["page"], 2, "page de l'extrait")

lu = lire_motifs([(1, "The list of products can be verified at info.fsc.org\nFSC-C004657")])
egal(lu["claims"], [], "certificat qui renvoie à la base : aucune catégorie inventée")


# ── 2. Choix du document ──────────────────────────────────────────────────
print("\n--- 2. choix du certificat présenté ---")
JOUR = date(2026, 9, 11)


def doc(id_, four, nom, titre="", exp=None, **kw):
    return {"id": id_, "fournisseur_id": four, "original_name": nom, "titre": titre,
            "date_expiration": exp, "uploaded_at": "2026-07-15T10:00:00", **kw}


docs = [
    doc(25, 7, "FrimpeksItaly_FSC-C164660.pdf", "FSC", "2031-02-24"),
    doc(83, 7, "Timestamped_FSC-C129558.pdf", "FSC", "2031-03-29"),
    doc(55, 7, "Frimpeks.pdf", "Auto déclaration relative à l'obtention des informations exigées par le RBUE", "2028-12-31"),
    doc(12, 1, "2025_Avery.pdf", "FSC", "2027-08-09"),
    doc(53, 1, "Avery Statement on FSC Directive.pdf", "Statement on FSC Directive", "2028-12-31"),
    doc(57, 11, "Itasa.pdf", "", "2028-12-31"),
    doc(60, 22, "Torraspapel - Lecta.pdf", "Auto déclaration relative à l'obtention des informations exigées par le RBUE", "2028-12-31"),
]
italy = {"id": 7, "licence": "FSC-C164660"}
turkey = {"id": 8, "licence": "FSC-C129558"}
uk = {"id": 6, "licence": "FSC-C160714"}
egal(choisir_document(italy, docs, JOUR)["id"], 25, "Frimpeks Italy garde son propre certificat")
egal(choisir_document(turkey, docs, JOUR)["id"], 83, "Frimpeks Turkey retrouve le sien, rangé sous Italy")
egal(choisir_document(uk, docs, JOUR), None, "Frimpeks UK ne reçoit pas le certificat d'une autre branche")
egal(choisir_document({"id": 1, "licence": "FSC-C004451"}, docs, JOUR)["id"], 12,
     "le certificat passe devant le « statement » à l'expiration plus lointaine")
egal(choisir_document({"id": 22, "licence": "FSC-C011032"}, docs, JOUR), None,
     "une auto-déclaration RBUE n'est jamais présentée comme certificat")
egal(choisir_document({"id": 11, "licence": "FSC-C160893"}, docs, JOUR)["id"], 57,
     "document simplement tagué : retenu tant qu'il n'est pas lu")
itasa_lu = dict(docs[5], fsc_lecture_methode="motifs", fsc_licence_lue=None)
egal(rang_document(itasa_lu, "FSC-C160893"), 0, "lu sans licence : un document tagué n'est plus un certificat")
itasa_echec = dict(docs[5], fsc_lecture_methode="aucune", fsc_licence_lue=None)
egal(rang_document(itasa_echec, "FSC-C160893"), 1, "une lecture impossible ne condamne pas le document")

egal(statut_expiration("2026-06-18", 60, JOUR)["statut"], "expire", "expiré")
egal(statut_expiration("2026-10-01", 60, JOUR)["statut"], "a_renouveler", "à renouveler sous 60 j")
egal(statut_expiration(None, 60, JOUR)["statut"], "sans_date", "sans date n'est pas valide")


# ── 3. Dossier PDF ─────────────────────────────────────────────────────────
print("\n--- 3. dossier PDF fusionné ---")
from pypdf import PdfReader  # noqa: E402
from reportlab.pdfgen import canvas  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    c = canvas.Canvas(os.path.join(tmp, "a.pdf"))
    for i in range(2):
        c.drawString(40, 800, "Certificat page %d" % (i + 1))
        c.showPage()
    c.save()
    try:
        from PIL import Image
        Image.new("RGB", (600, 800), "white").save(os.path.join(tmp, "b.jpg"))
        image_ok = True
    except Exception:
        image_ok = False
    lignes = [
        {"id": 1, "nom": "Avery", "licence": "FSC-C004451", "certificat": "CU-COC-807907",
         "expiration": "2027-08-09", "claims_labels": ["FSC Mix Credit"], "dernier_controle": None,
         "document": {"filename": "a.pdf", "original_name": "a.pdf", "mime_type": "application/pdf"}},
        {"id": 2, "nom": "Suzhou", "licence": "FSC-C140235", "certificat": None,
         "expiration": "2028-03-18", "claims_labels": [], "dernier_controle": None,
         "document": {"filename": "b.jpg", "original_name": "b.jpg", "mime_type": "image/jpeg"} if image_ok else None},
        {"id": 3, "nom": "Mitsubishi", "licence": "FSC-C014541", "certificat": None,
         "expiration": "2026-06-18", "claims_labels": [], "dernier_controle": None,
         "document": {"filename": "absent.pdf", "original_name": "absent.pdf", "mime_type": "application/pdf"}},
        {"id": 4, "nom": "YCDLabel", "licence": None, "certificat": None, "expiration": None,
         "claims_labels": [], "dernier_controle": None, "document": None},
    ]
    pdf = construire_dossier_pdf(lignes, tmp, "Fournisseurs certifiés FSC", "test")
    lecteur = PdfReader(io.BytesIO(pdf))
    attendu_pages = 1 + 2 + (1 if image_ok else 0)
    egal(len(lecteur.pages), attendu_pages, "garde + certificat PDF + photo, fichier absent ignoré")
    titres = [o.title for o in lecteur.outline]
    verifie(titres[0] == "Liste des fournisseurs certifiés" and "Avery · FSC-C004451" in titres,
            "signets : page de garde puis un par fournisseur")
    verifie(not any("Mitsubishi" in t for t in titres), "pas de signet pour un fichier absent")
    egal(lignes[2].get("note_dossier"), "Fichier absent du serveur", "le fichier absent est signalé sur la garde")


# ── 4. Migration ───────────────────────────────────────────────────────────
print("\n--- 4. migration rejouable ---")
chemin = os.path.join(RACINE, "app", "core", "migrations", "2026_09_11_qualite_fsc_controles.py")
spec = importlib.util.spec_from_file_location("mig_fsc", chemin)
mig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mig)
conn = sqlite3.connect(":memory:")
conn.execute("CREATE TABLE fournisseurs_fsc (id INTEGER PRIMARY KEY, nom TEXT)")
conn.execute("CREATE TABLE qualite_fournisseur_certificats (id INTEGER PRIMARY KEY, fournisseur_id INTEGER, filename TEXT)")
mig.appliquer(conn)
mig.appliquer(conn)
cols = {r[1] for r in conn.execute("PRAGMA table_info(qualite_fournisseur_certificats)")}
verifie({"fsc_licence_lue", "fsc_claims_lus", "fsc_lecture_methode"} <= cols, "colonnes de lecture ajoutées une fois")
verifie(conn.execute("SELECT name FROM sqlite_master WHERE name='qualite_fsc_controles'").fetchone() is not None,
        "table des contrôles créée")


print()
if ECHECS:
    print("%d échec(s)" % len(ECHECS))
    sys.exit(1)
print("Tout est vert.")

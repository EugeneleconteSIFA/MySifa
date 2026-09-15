# -*- coding: utf-8 -*-
"""Le verrou FSC de la réception : l'allégation se constate, elle ne se saisit plus.

Ce que ce test protège.

1. **Le verrou s'arme avec la date d'entrée dans la chaîne de contrôle**, pas
   avec une option. Tant qu'elle n'est pas renseignée, rien ne change — ce qui
   laisse le temps de saisir les contrôles fournisseurs. Une réception
   antérieure à cette date garde son allégation saisie : la chaîne de contrôle
   ne réécrit pas ce qui la précède.
2. **Sous le verrou, une réception ne porte que ce que le registre démontre.**
   Pas de ligne de registre, ligne à vérifier, écart BL/facture, allégation hors
   de la portée du certificat : dans tous les cas `non_fsc`.
3. **Un refus dit toujours quoi corriger.** Un « Non FSC » sans motif
   n'appellerait aucun geste au magasin, et apprendrait à ignorer l'écran.
4. **Une réception n'est jamais refusée.** Les bobines sont physiquement là ;
   les écarter de la traçabilité serait le pire des deux maux.
5. **Le lien registre ↔ réception se pose dans les deux sens**, et n'écrase
   jamais un rattachement existant.

Lancer : python3 tests/test_fsc_reception_verrou.py
"""

from __future__ import annotations

import importlib.util
import os
import sqlite3
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from app.services import fsc_registre as R  # noqa: E402

ECHECS: list[str] = []


def verifie(condition, libelle: str) -> None:
    if condition:
        print("  ok   %s" % libelle)
    else:
        print("  ECHEC %s" % libelle)
        ECHECS.append(libelle)


def egal(obtenu, attendu, libelle: str) -> None:
    verifie(obtenu == attendu, "%s (obtenu %r, attendu %r)" % (libelle, obtenu, attendu))


SCHEMA = """
CREATE TABLE fournisseurs_fsc (
    id INTEGER PRIMARY KEY, nom TEXT NOT NULL, licence TEXT, certificat TEXT,
    has_fsc INTEGER NOT NULL DEFAULT 1, actif INTEGER NOT NULL DEFAULT 1,
    fsc_date_expiration TEXT, rvgi_numero INTEGER, rvgi_rs TEXT, rvgi_lie_le TEXT,
    updated_at TEXT);
CREATE TABLE qualite_fsc_controles (
    id INTEGER PRIMARY KEY, fournisseur_id INTEGER NOT NULL, date_controle TEXT NOT NULL,
    statut_base TEXT NOT NULL, licence TEXT, date_expiration_lue TEXT,
    claims TEXT NOT NULL DEFAULT '[]', source TEXT NOT NULL DEFAULT 'base_fsc',
    certificat_id INTEGER, note TEXT NOT NULL DEFAULT '', justificatif_filename TEXT,
    justificatif_original TEXT, justificatif_mime TEXT,
    fiche_maj INTEGER NOT NULL DEFAULT 0, ancienne_expiration TEXT,
    created_at TEXT NOT NULL, created_by INTEGER, created_by_nom TEXT);
CREATE TABLE stock_receptions (
    id INTEGER PRIMARY KEY, created_at TEXT NOT NULL, fournisseur TEXT,
    fournisseur_id INTEGER, certificat_fsc TEXT, fsc_type_claim TEXT,
    lot_numero TEXT, nb_bobines INTEGER, rvgi_bl TEXT, rvgi_lif_id INTEGER);
"""

MIGRATIONS = ("2026_09_14_fsc_registre_appro.py", "2026_09_15_fsc_reception_verrou.py")


def base():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    c.executemany(
        "INSERT INTO fournisseurs_fsc (id,nom,licence,certificat,fsc_date_expiration,rvgi_numero) "
        "VALUES (?,?,?,?,?,?)",
        [(1, "Likexin", "FSC-C128270", "ESTS-COC-242264", "2030-02-10", 101),
         (2, "Kanzan", "FSC-C007179", "TUVDC-COC-100605", "2030-01-01", 102)],
    )
    c.executemany(
        "INSERT INTO qualite_fsc_controles "
        "(fournisseur_id, date_controle, statut_base, claims, created_at) VALUES (?,?,?,?,?)",
        [(1, "2026-09-20", "valide", '["fsc_mix_credit"]', "2026-09-20T09:00:00"),
         (2, "2026-09-20", "valide", '["fsc_mix_credit"]', "2026-09-20T09:00:00")],
    )
    for fichier in MIGRATIONS:
        spec = importlib.util.spec_from_file_location(
            "mig_" + fichier[:-3], os.path.join(RACINE, "app", "core", "migrations", fichier))
        mig = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mig)
        mig.appliquer(c)
    return c


def ligne_registre(conn, lif_id, fournisseur_id, num_bl, date_reception,
                   allegation=None, code=None, claims='["fsc_mix_credit"]'):
    """Une ligne de registre déjà contrôlée, telle que l'import + la saisie la laissent."""
    ligne = {
        "lif_id": lif_id, "date_reception": date_reception, "num_bl": num_bl,
        "fournisseur_id": fournisseur_id, "certificat_statut": "valide",
        "code_certificat_attendu": "ESTS-COC-242264",
        "claims_autorises": claims,
        "allegation_bl": allegation, "allegation_facture": allegation,
        "code_certificat_present": code, "importe_le": "2026-10-01T08:00:00",
        "origine_forestiere": 1, "observations": "",
    }
    ligne["eligible"] = R.evaluer_eligibilite(ligne)
    cols = list(ligne)
    conn.execute("INSERT INTO fsc_reception (%s) VALUES (%s)"
                 % (", ".join(cols), ", ".join("?" * len(cols))),
                 [ligne[c] for c in cols])
    conn.commit()
    return conn.execute("SELECT id FROM fsc_reception WHERE lif_id=?", (lif_id,)).fetchone()["id"]


# ── 1. L'armement du verrou ────────────────────────────────────────────────
print("\n--- 1. quand le verrou s'applique ---")
conn = base()
egal(R.claim_pour_reception(conn, date_reception="2026-10-05", num_bl="BL1")["verrou"], False,
     "sans date d'entrée, le verrou dort")
R.definir_date_entree(conn, "2026-10-01", "test")
egal(R.claim_pour_reception(conn, date_reception="2026-09-20", num_bl="BL1")["verrou"], False,
     "une réception antérieure à l'entrée garde son allégation saisie")
egal(R.claim_pour_reception(conn, date_reception="2026-10-01", num_bl="BL1")["verrou"], True,
     "le jour même de l'entrée, le verrou s'applique")


# ── 2. Ce que le registre démontre, et ce qu'il ne démontre pas ───────────
print("\n--- 2. l'allégation retenue ---")
v = R.claim_pour_reception(conn, date_reception="2026-10-05", num_bl="BL-INCONNU", fournisseur_id=1)
egal(v["claim"], "non_fsc", "aucune ligne de registre : pas d'allégation")
verifie("bon de livraison" in (v["motif"] or ""), "et le motif dit quoi vérifier")

ligne_registre(conn, 501, 1, "BL-COMPLET", "2026-10-02", "fsc_mix_credit", 1)
v = R.claim_pour_reception(conn, date_reception="2026-10-05", num_bl="BL-COMPLET", fournisseur_id=1)
egal(v["claim"], "fsc_mix_credit", "ligne éligible : la réception hérite de son allégation")
egal(v["motif"], None, "rien à corriger, donc pas de motif")
egal(v["certificat"], "ESTS-COC-242264", "le code de certificat vient du registre, pas d'une saisie")
egal(R.claim_pour_reception(conn, date_reception="2026-10-05", lif_id=501)["claim"], "fsc_mix_credit",
     "la ligne de livraison RVGI est une clé exacte, sans passer par le BL")

ligne_registre(conn, 502, 1, "BL-EN-COURS", "2026-10-02", "fsc_mix_credit", None)
v = R.claim_pour_reception(conn, date_reception="2026-10-05", num_bl="BL-EN-COURS", fournisseur_id=1)
egal(v["claim"], "non_fsc", "contrôle de registre inachevé : pas d'allégation")
verifie("contrôle" in (v["motif"] or ""), "et le motif le dit")

ligne_registre(conn, 503, 1, "BL-AUCUNE", "2026-10-02", "aucune", 1)
egal(R.claim_pour_reception(conn, date_reception="2026-10-05", num_bl="BL-AUCUNE",
                            fournisseur_id=1)["claim"], "non_fsc",
     "un BL sans allégation reste sans allégation")

# Kanzan : le cas réel — FSC Mix sur un bon, rien sur le suivant.
ligne_registre(conn, 504, 2, "KZ-001", "2026-10-02", "fsc_mix_credit", 1)
ligne_registre(conn, 505, 2, "KZ-002", "2026-10-03", "aucune", 1)
egal(R.claim_pour_reception(conn, date_reception="2026-10-05", num_bl="KZ-001",
                            fournisseur_id=2)["claim"], "fsc_mix_credit",
     "Kanzan, premier bon : FSC Mix Crédit")
egal(R.claim_pour_reception(conn, date_reception="2026-10-05", num_bl="KZ-002",
                            fournisseur_id=2)["claim"], "non_fsc",
     "Kanzan, bon suivant : non FSC — c'est l'allégation du BL qui s'hérite, pas le certificat")

# Hors portée du certificat : Likexin n'est validé qu'en FSC Mix Crédit.
ligne_registre(conn, 506, 1, "BL-HORS-PORTEE", "2026-10-02", "fsc_100", 1)
v = R.claim_pour_reception(conn, date_reception="2026-10-05", num_bl="BL-HORS-PORTEE", fournisseur_id=1)
egal(v["claim"], "non_fsc", "FSC 100 % hors de la portée validée : refusé")
verifie("pas éligible" in (v["motif"] or ""), "et signalé comme un écart, pas comme un doute")

# Deux lignes du même bon qui ne disent pas la même chose.
ligne_registre(conn, 507, 1, "BL-MELANGE", "2026-10-02", "fsc_mix_credit", 1)
ligne_registre(conn, 508, 1, "BL-MELANGE", "2026-10-02", "aucune", 1)
v = R.claim_pour_reception(conn, date_reception="2026-10-05", num_bl="BL-MELANGE", fournisseur_id=1)
egal(v["claim"], "non_fsc", "deux lignes divergentes sur un même BL : aucune allégation")
verifie("même allégation" in (v["motif"] or ""), "et le motif nomme la divergence")


# ── 3. Le lien vers la réception physique ─────────────────────────────────
print("\n--- 3. lien registre ↔ réception ---")
conn.execute("INSERT INTO stock_receptions (id, created_at, fournisseur_id, rvgi_bl) "
             "VALUES (77, '2026-10-05T09:00:00', 1, 'BL-COMPLET')")
conn.commit()
v = R.claim_pour_reception(conn, date_reception="2026-10-05", num_bl="BL-COMPLET", fournisseur_id=1)
egal(R.lier_reception(conn, 77, v["lignes"], "Fatiha"), 1, "la ligne de registre apprend sa réception")
egal(conn.execute("SELECT reception_id FROM fsc_reception WHERE lif_id=501").fetchone()[0], 77,
     "le lien est écrit côté registre")
verifie(any(e["champ"] == "reception_id" for e in R.journal(conn, v["lignes"][0])),
        "et journalisé")
egal(R.lier_reception(conn, 88, v["lignes"], "Fatiha"), 0,
     "un rattachement existant ne s'écrase pas en silence")


print()
if ECHECS:
    print("%d échec(s)" % len(ECHECS))
    sys.exit(1)
print("Tout est vert.")

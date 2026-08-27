#!/usr/bin/env python3
"""
Fusion et détection de doublons de fournisseurs.

Ce que ce test protège
----------------------
La fusion réassigne les références portées par une quinzaine de tables, dont
certaines imposent l'unicité du couple (fournisseur, autre chose). Trois façons
de se tromper, toutes silencieuses à l'écran :

1. Oublier une table  → des lignes pointent vers un id supprimé. L'écran qui
   les lit affiche une liste vide, sans erreur.
2. Écraser une ligne de la cible par celle de la source sur une table à index
   unique → le tarif que l'utilisateur voit change sans qu'il l'ait demandé.
3. Perdre l'historique stocké par NOM (réceptions déjà parties en production)
   → rupture de traçabilité, ce qu'un audit de chaîne de contrôle cherche.

Lancement : python3 tests/test_fournisseurs_merge.py
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
if str(RACINE) not in sys.path:
    sys.path.insert(0, str(RACINE))

import database  # noqa: E402  (le chemin de base est posé par le test)
from app.routers import settings as S  # noqa: E402


# ═══════════════════════════════════════════════════════════════════
#  Schéma minimal — uniquement les tables que la fusion doit toucher
# ═══════════════════════════════════════════════════════════════════

SCHEMA = """
CREATE TABLE fournisseurs_fsc (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nom TEXT NOT NULL UNIQUE,
  licence TEXT, certificat TEXT,
  traca_photo_url TEXT, traca_explication TEXT, traca_exemple_code TEXT,
  has_fsc INTEGER NOT NULL DEFAULT 1,
  groupe TEXT, branche TEXT,
  adresse TEXT, code_postal TEXT, ville TEXT, pays TEXT DEFAULT 'FR',
  langue_default TEXT DEFAULT 'fr', tags TEXT, notes TEXT,
  actif INTEGER NOT NULL DEFAULT 1, updated_at TEXT,
  pays_origine TEXT, sous_traitant INTEGER NOT NULL DEFAULT 0,
  categories TEXT, siret TEXT, tva_intracom TEXT, fsc_date_expiration TEXT,
  price_currency TEXT NOT NULL DEFAULT 'EUR',
  telephone TEXT, email TEXT, fax TEXT,
  mode_reglement TEXT, mode_livraison TEXT, delai_expedition_jours INTEGER,
  regime_tva TEXT, rcs TEXT
);

-- Référence simple : rien n'empêche deux lignes sur le même fournisseur.
CREATE TABLE fournisseur_contacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fournisseur_id INTEGER NOT NULL REFERENCES fournisseurs_fsc(id) ON DELETE CASCADE,
  nom TEXT NOT NULL, actif INTEGER NOT NULL DEFAULT 1
);

-- Index unique sur (fournisseur, matiere) : c'est le cas piège.
CREATE TABLE mc_tarif_fournisseur (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fournisseur_id INTEGER NOT NULL,
  matiere_id INTEGER NOT NULL,
  transport_cout REAL NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX idx_mctf_unique ON mc_tarif_fournisseur(fournisseur_id, matiere_id);

-- Clé primaire composite portant le fournisseur.
CREATE TABLE matiere_laize_fournisseurs (
  matiere_id INTEGER NOT NULL, laize_id INTEGER NOT NULL,
  fournisseur_id INTEGER NOT NULL,
  PRIMARY KEY (matiere_id, laize_id, fournisseur_id)
);

-- Historique par NOM, doublé d'un id récent.
CREATE TABLE stock_receptions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT, created_by_name TEXT, nb_bobines INTEGER,
  certificat_fsc TEXT, note TEXT,
  fournisseur TEXT, fournisseur_id INTEGER
);
CREATE TABLE stock_reception_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  reception_id INTEGER, code_barre TEXT
);

-- Ancien annuaire : colonne nommée autrement.
CREATE TABLE mc_supplier (
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT,
  fournisseur_fsc_id INTEGER
);

-- Liste d'ids en JSON.
CREATE TABLE ao_declarations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fournisseurs_ids TEXT
);
"""


def base_neuve() -> str:
    fd, chemin = tempfile.mkstemp(suffix=".db", prefix="mysifa_test_")
    os.close(fd)
    os.remove(chemin)
    conn = sqlite3.connect(chemin)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()
    database.CHEMIN = chemin
    return chemin


def peupler(chemin: str) -> tuple[int, int]:
    conn = sqlite3.connect(chemin)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # SOURCE : la fiche qui disparaît. Elle porte des infos que la cible n'a
    # pas — elles doivent être récupérées, pas perdues avec elle.
    c.execute(
        """INSERT INTO fournisseurs_fsc
             (nom, has_fsc, licence, ville, siret, telephone, categories, notes)
           VALUES ('2DM', 1, 'FSC-C111111', 'LILLE', '12345678901234',
                   '03 20 56 25 22', ?, 'Note source')""",
        (json.dumps(["adhesif"]),),
    )
    src = c.lastrowid

    # CIBLE : elle survit. Ses valeurs déjà remplies ne doivent PAS bouger.
    c.execute(
        """INSERT INTO fournisseurs_fsc (nom, has_fsc, ville, email, categories)
           VALUES ('2 D M S.A.S.', 0, 'TOURCOING', 'contact@2dm.fr', ?)""",
        (json.dumps(["frontal"]),),
    )
    tgt = c.lastrowid

    # Un troisième, qui ne doit rien voir de la fusion.
    c.execute("INSERT INTO fournisseurs_fsc (nom, has_fsc) VALUES ('AVERY', 1)")
    autre = c.lastrowid

    c.executemany("INSERT INTO fournisseur_contacts (fournisseur_id, nom) VALUES (?,?)",
                  [(src, "Paul"), (src, "Marie"), (tgt, "Jean"), (autre, "Luc")])

    # Matière 10 : les DEUX ont un tarif → collision d'index unique. Celui de
    # la cible doit survivre (transport 9.0), celui de la source disparaître.
    # Matière 20 : seule la source en a un → il doit être déplacé.
    c.executemany(
        "INSERT INTO mc_tarif_fournisseur (fournisseur_id, matiere_id, transport_cout) VALUES (?,?,?)",
        [(src, 10, 5.0), (tgt, 10, 9.0), (src, 20, 7.0)],
    )

    # Idem sur une clé primaire composite.
    c.executemany(
        "INSERT INTO matiere_laize_fournisseurs (matiere_id, laize_id, fournisseur_id) VALUES (?,?,?)",
        [(1, 100, src), (1, 100, tgt), (2, 200, src)],
    )

    # Réceptions : une ancienne (nom seul), une récente (id).
    c.execute("INSERT INTO stock_receptions (created_at, fournisseur, nb_bobines) "
              "VALUES ('2025-01-10T08:00:00', '2DM', 3)")
    c.execute("INSERT INTO stock_receptions (created_at, fournisseur, fournisseur_id, nb_bobines) "
              "VALUES ('2026-08-01T08:00:00', '2DM', ?, 5)", (src,))
    c.execute("INSERT INTO stock_receptions (created_at, fournisseur, fournisseur_id, nb_bobines) "
              "VALUES ('2026-08-02T08:00:00', '2 D M S.A.S.', ?, 2)", (tgt,))

    c.execute("INSERT INTO mc_supplier (name, fournisseur_fsc_id) VALUES ('2DM', ?)", (src,))

    # JSON : la source ET la cible sont dans la même liste → après réécriture,
    # la cible ne doit y figurer qu'une fois.
    c.executemany("INSERT INTO ao_declarations (fournisseurs_ids) VALUES (?)",
                  [(json.dumps([src, autre]),), (json.dumps([src, tgt]),),
                   (json.dumps([autre]),)])

    conn.commit()
    conn.close()
    return src, tgt


# ═══════════════════════════════════════════════════════════════════

ECHECS: list[str] = []


def verifie(condition, message):
    if condition:
        print(f"  ok   {message}")
    else:
        print(f"  ECHEC {message}")
        ECHECS.append(message)


def q(chemin, sql, params=()):
    conn = sqlite3.connect(chemin)
    conn.row_factory = sqlite3.Row
    r = conn.execute(sql, params).fetchall()
    conn.close()
    return r


def test_fusion():
    print("\nFusion d'un doublon")
    print("─" * 60)
    chemin = base_neuve()
    src, tgt = peupler(chemin)

    res = S.merge_fournisseurs(src, tgt, _requete())

    verifie(res.get("success") is True, "la fusion répond success")
    verifie(not q(chemin, "SELECT 1 FROM fournisseurs_fsc WHERE id=?", (src,)),
            "la fiche source est supprimée")
    verifie(bool(q(chemin, "SELECT 1 FROM fournisseurs_fsc WHERE id=?", (tgt,))),
            "la fiche cible existe toujours")

    # 1. Références simples : tout est déplacé.
    n = q(chemin, "SELECT COUNT(*) n FROM fournisseur_contacts WHERE fournisseur_id=?",
          (tgt,))[0]["n"]
    verifie(n == 3, f"les 3 contacts (2 source + 1 cible) sont sur la cible — vu {n}")
    verifie(not q(chemin, "SELECT 1 FROM fournisseur_contacts WHERE fournisseur_id=?", (src,)),
            "aucun contact ne pointe plus vers la source")

    # 2. Index unique : la ligne de la CIBLE gagne, celle de la source part.
    tarifs = {r["matiere_id"]: r["transport_cout"]
              for r in q(chemin, "SELECT matiere_id, transport_cout FROM "
                                 "mc_tarif_fournisseur WHERE fournisseur_id=?", (tgt,))}
    verifie(tarifs.get(10) == 9.0,
            f"sur collision, le tarif de la cible est conservé (9.0) — vu {tarifs.get(10)}")
    verifie(tarifs.get(20) == 7.0,
            f"le tarif que seule la source portait est récupéré (7.0) — vu {tarifs.get(20)}")
    verifie(not q(chemin, "SELECT 1 FROM mc_tarif_fournisseur WHERE fournisseur_id=?", (src,)),
            "aucun tarif orphelin ne subsiste")

    # 3. Clé primaire composite : même règle.
    laizes = {(r["matiere_id"], r["laize_id"]) for r in
              q(chemin, "SELECT matiere_id, laize_id FROM matiere_laize_fournisseurs "
                        "WHERE fournisseur_id=?", (tgt,))}
    verifie(laizes == {(1, 100), (2, 200)},
            f"les liens matière×laize sont dédoublonnés — vu {sorted(laizes)}")
    verifie(not q(chemin, "SELECT 1 FROM matiere_laize_fournisseurs WHERE fournisseur_id=?",
                  (src,)),
            "aucun lien matière×laize orphelin")

    # 4. Historique par nom : renommé, jamais supprimé.
    noms = [r["fournisseur"] for r in
            q(chemin, "SELECT fournisseur FROM stock_receptions ORDER BY id")]
    verifie(noms == ["2 D M S.A.S."] * 3,
            f"les 3 réceptions portent le nom de la cible — vu {noms}")
    verifie(q(chemin, "SELECT COUNT(*) n FROM stock_receptions")[0]["n"] == 3,
            "aucune réception perdue")

    # 5. Colonne nommée autrement.
    verifie(q(chemin, "SELECT fournisseur_fsc_id f FROM mc_supplier")[0]["f"] == tgt,
            "mc_supplier.fournisseur_fsc_id suit la cible")

    # 6. JSON : réécrit et dédoublonné.
    listes = [json.loads(r["fournisseurs_ids"]) for r in
              q(chemin, "SELECT fournisseurs_ids FROM ao_declarations ORDER BY id")]
    verifie(src not in [x for l in listes for x in l],
            f"l'id source ne figure dans aucune liste JSON — vu {listes}")
    verifie(listes[1].count(tgt) == 1,
            f"la cible n'apparaît qu'une fois après dédoublonnage — vu {listes[1]}")
    verifie(res.get("json_rewrites") == 2,
            f"2 réécritures JSON rapportées — vu {res.get('json_rewrites')}")

    # 7. Récupération : ce que la cible n'avait pas, sans écraser ce qu'elle avait.
    f = q(chemin, "SELECT * FROM fournisseurs_fsc WHERE id=?", (tgt,))[0]
    verifie(f["ville"] == "TOURCOING", f"la ville de la cible n'a pas bougé — vu {f['ville']}")
    verifie(f["email"] == "contact@2dm.fr", "l'e-mail de la cible n'a pas bougé")
    verifie(f["licence"] == "FSC-C111111",
            f"la licence, vide sur la cible, est récupérée — vu {f['licence']}")
    verifie(f["siret"] == "12345678901234", "le SIRET est récupéré")
    verifie(f["telephone"] == "03 20 56 25 22", "le téléphone est récupéré")
    verifie(f["has_fsc"] == 1, "has_fsc passe à 1 : la source était certifiée")
    cats = json.loads(f["categories"])
    verifie(sorted(cats) == ["adhesif", "frontal"],
            f"les catégories sont l'union des deux — vu {cats}")

    # 8. Le tiers n'a rien vu.
    autre = q(chemin, "SELECT * FROM fournisseurs_fsc WHERE nom='AVERY'")[0]
    verifie(autre["has_fsc"] == 1 and autre["categories"] is None,
            "le fournisseur non concerné est intact")
    verifie(q(chemin, "SELECT COUNT(*) n FROM fournisseur_contacts "
                      "WHERE fournisseur_id=?", (autre["id"],))[0]["n"] == 1,
            "ses contacts sont intacts")

    os.remove(chemin)


def test_fusion_refuse_soi_meme():
    print("\nGarde-fous de la fusion")
    print("─" * 60)
    chemin = base_neuve()
    src, tgt = peupler(chemin)
    from fastapi import HTTPException

    for a, b, quoi in ((src, src, "source = cible"),
                       (src, 99999, "cible inexistante"),
                       (99999, tgt, "source inexistante")):
        try:
            S.merge_fournisseurs(a, b, _requete())
            verifie(False, f"{quoi} est refusé")
        except HTTPException as e:
            verifie(e.status_code in (400, 404), f"{quoi} est refusé ({e.status_code})")

    verifie(q(chemin, "SELECT COUNT(*) n FROM fournisseurs_fsc")[0]["n"] == 3,
            "aucune fiche supprimée par un appel refusé")
    os.remove(chemin)


def test_doublons():
    print("\nDétection de doublons")
    print("─" * 60)
    chemin = base_neuve()
    conn = sqlite3.connect(chemin)
    conn.executemany(
        "INSERT INTO fournisseurs_fsc (nom, siret, tva_intracom, has_fsc) VALUES (?,?,?,?)",
        [
            ("2DM", None, None, 1),
            ("2 D M S.A.S.", None, None, 0),          # nom tassé identique
            ("Fedrigoni Italy", "99988877766655", None, 1),
            ("FEDRIGONI ITALIA SPA", "99988877766655", None, 1),  # même SIRET
            ("Coquelle", None, "FR12345678901", 1),
            ("COQUELLE SA", None, "FR12345678901", 1),  # même TVA + nom normalisé
            ("Avery", None, None, 1),                  # seul de son espèce
        ],
    )
    conn.commit()
    conn.close()

    r = S.fournisseurs_doublons(_requete())
    groups = r["groups"]
    print(f"  {len(groups)} groupe(s) : "
          + " | ".join(f"{g['reason']}×{g['count']}" for g in groups))

    verifie(len(groups) == 3, f"3 groupes détectés — vu {len(groups)}")
    verifie(groups[0]["reason"] == "siret",
            f"le SIRET passe en premier — vu {groups[0]['reason']}")

    tous = [f["nom"] for g in groups for f in g["fournisseurs"]]
    verifie("Avery" not in tous, "le fournisseur unique n'est pas signalé")
    verifie(len(tous) == len(set(tous)),
            f"aucune fiche listée deux fois — vu {tous}")
    verifie({"2DM", "2 D M S.A.S."} <= set(tous),
            "le doublon que seul le nom tassé rapproche est trouvé")
    os.remove(chemin)


def test_validateurs():
    print("\nValidation des champs d'achat")
    print("─" * 60)
    from fastapi import HTTPException

    verifie(S._parse_siret("382 095 206 00035") == "38209520600035",
            "un SIRET espacé est nettoyé")
    verifie(S._parse_siret(None) is None, "un SIRET vide reste vide")
    for mauvais in ("123", "12345678901", "abcd"):
        try:
            S._parse_siret(mauvais)
            verifie(False, f"SIRET « {mauvais} » refusé")
        except HTTPException:
            verifie(True, f"SIRET « {mauvais} » refusé")

    verifie(S._parse_tva_intracom("FR81 511 760 092") == "FR81511760092",
            "un numéro de TVA espacé est nettoyé")
    try:
        S._parse_tva_intracom("81511760092")
        verifie(False, "TVA sans code pays refusée")
    except HTTPException:
        verifie(True, "TVA sans code pays refusée")

    verifie(S._parse_email_fournisseur(" Devis@Fournisseur.COM ") == "devis@fournisseur.com",
            "un e-mail est mis en minuscules et détouré")
    try:
        S._parse_email_fournisseur("pas-un-email")
        verifie(False, "e-mail invalide refusé")
    except HTTPException:
        verifie(True, "e-mail invalide refusé")

    verifie(S._parse_code_referentiel("virement", {"virement", "comptant"}, "Mode") == "virement",
            "un code du référentiel passe")
    try:
        S._parse_code_referentiel("chèque en bois", {"virement"}, "Mode")
        verifie(False, "code hors référentiel refusé")
    except HTTPException:
        verifie(True, "code hors référentiel refusé")

    verifie(S._parse_delai_expedition("3") == 3, "un délai numérique est lu")
    verifie(S._parse_delai_expedition("") is None, "un délai vide reste vide")
    try:
        S._parse_delai_expedition("900")
        verifie(False, "délai hors bornes refusé")
    except HTTPException:
        verifie(True, "délai hors bornes refusé")

    verifie(S._parse_devise_achat("usd") == "USD", "une devise est mise en majuscules")
    verifie(S._parse_devise_achat("", "EUR") == "EUR", "une devise vide retombe sur le défaut")


def test_norm_noms():
    print("\nNormalisation des noms (doit coller à l'import et à la migration)")
    print("─" * 60)
    verifie(S._four_norm_nom("JAOUR S.A.") == S._four_norm_nom("Jaour"),
            "la forme juridique est ignorée")
    verifie(S._four_norm_nom("Étiq-Plus") == S._four_norm_nom("ETIQ PLUS"),
            "accents et ponctuation sont ignorés")
    verifie(S._four_squash("2 D M S.A.S.") == "2dm",
            f"« 2 D M S.A.S. » se tasse en « 2dm » — vu {S._four_squash('2 D M S.A.S.')}")
    verifie(S._four_squash("2DM") == "2dm", "« 2DM » se tasse en « 2dm »")
    verifie(S._four_squash("Avery Dennison") != S._four_squash("Avery"),
            "deux noms réellement différents ne se confondent pas")


class _Faux:
    """Fausse requête. `get_current_user` lit le cookie de session : sans
    l'attribut, le test tombe sur un AttributeError sans rapport avec ce
    qu'il vérifie. Reste à lui donner une vraie session — voir
    tests/CI_QUARANTAINE.txt."""
    client = None
    headers: dict = {}
    cookies: dict = {}


def _requete():
    return _Faux()


def main() -> int:
    test_validateurs()
    test_norm_noms()
    test_doublons()
    test_fusion()
    test_fusion_refuse_soi_meme()
    print("\n" + "═" * 60)
    if ECHECS:
        print(f"{len(ECHECS)} ECHEC(S) :")
        for e in ECHECS:
            print(f"  - {e}")
        return 1
    print("Tous les contrôles passent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fusion des doublons de l'annuaire fournisseurs : fiche d'usage ⇄ tiers ERP.

Pourquoi
--------
L'annuaire porte deux populations superposées. D'un côté une trentaine de
fiches historiques au nom d'usage court — « Avery », « Kanzan », « Sato » —
qui portent la licence FSC, la traçabilité et les rattachements matières. De
l'autre, les ~200 tiers repris de l'export RVGI, qui portent l'adresse, le
SIRET et le lien ERP. « Avery » et « AVERY DENNISON MATERIALS SALES FRANCE
SAS » sont le même fournisseur, saisi à deux endroits, et l'écran de réception
propose les deux.

Le sens de la fusion, et pourquoi il compte
-------------------------------------------
La fiche qui SURVIT est la fiche d'usage : c'est son nom que les écrans
affichent, que la traçabilité FSC porte, et que l'historique de réception a
déjà écrit. Elle récupère de la fiche absorbée tout ce qu'elle n'a pas —
adresse, SIRET, téléphone — ET le lien ERP (`rvgi_numero`), sans quoi elle
repasserait en « manuel » : la synchro RVGI ne l'alimenterait plus et
« importer les manquants » recréerait une fiche pour le tiers laissé libre.
Le doublon reviendrait au prochain import.

`--sens erp` fait l'inverse (le tiers ERP survit, avec sa raison sociale
complète). Le choix se fait une fois pour toutes : ne pas mélanger les deux
sens sur un même lot.

Ce que ce script ne fait pas
---------------------------
- Il ne devine aucun couple. La liste est écrite ligne à ligne, avec les deux
  noms attendus ; une fiche renommée entre-temps fait sauter SA ligne, elle ne
  fait pas fusionner autre chose.
- Il ne tranche pas les quatre cas qui demandent un arbitrage humain (Suzhou,
  Torraspapel, BURBAN, UPM) : ils sont affichés par `--inventaire`, jamais
  fusionnés.
- Il ne fusionne pas deux fiches toutes deux liées à un tiers ERP actif sans
  `--forcer` : là, le doublon est côté ERP et se règle dans RVGI d'abord.

Il passe par `fusionner_fournisseurs()` — le même code que le bouton de
l'interface — pour qu'une table ajoutée demain soit reprise ici sans y penser.

Trois étapes, dans cet ordre

  1.  python3 scripts/fusion_fournisseurs_doublons.py --inventaire
      L'état de chaque couple aujourd'hui : ce qui existe, ce qui est déjà
      fait, ce qui coince, et les cas laissés de côté.

  2.  python3 scripts/fusion_fournisseurs_doublons.py
      Simulation : ce qui serait déplacé, table par table. N'écrit rien.

  3.  python3 scripts/fusion_fournisseurs_doublons.py --appliquer
      Écrit, après une copie de sauvegarde de la base. Relançable : un couple
      déjà fusionné est ignoré.

Après `--appliquer`, lancer la synchro RVGI (Paramètres → Fournisseurs → RVGI,
« Appliquer ») : elle réaligne pays, devise et langue des fiches survivantes
sur le tiers, champs que la fusion ne recopie pas.

Options : --db /chemin/production.db, --sens court|erp, --couple N (une seule
ligne du plan), --forcer.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
from datetime import datetime

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)


# ═══════════════════════════════════════════════════════════════════════
#  Le plan — établi le 08/09/2026 sur l'export des 223 fiches, croisé avec
#  fic_fou. Chaque ligne a été vérifiée sur l'adresse ET le code ERP, pas
#  seulement sur la ressemblance des noms.
# ═══════════════════════════════════════════════════════════════════════

PLAN = [
    # (id fiche d'usage, nom attendu, id tiers ERP, nom attendu, remarque)
    (1,  "Avery",            39,  "AVERY DENNISON MATERIALS SALES FRANCE SAS", ""),
    (4,  "Burgo / Mosaico",  104, "MOSAICO",
     "la fiche d'usage porte 2 tarifs matière"),
    (3,  "Feys",             127, "IMPRIMERIE FEYS", ""),
    (6,  "Frimpeks UK",      122, "FRIMPEKS LTD", ""),
    (7,  "Frimpeks Italy",   192, "FRIMPEKS ITALIA SRL", ""),
    (9,  "Grand Ouest",      106, "GRAND OUEST ETIQUETTES", ""),
    (12, "Kanzan",           50,  "KANZAN SPEZIALPAPIERE",
     "4 réceptions sont enregistrées au nom « Kanzan » — elles suivent"),
    (13, "Lefrancq",         213, "LEFRANCQ IMPRIMEUR", ""),
    (15, "Mitsubishi",       207, "Mitsubishi HiTec Paper Europe GmbH", ""),
    (17, "Ricoh",            78,  "RICOH Industrie France SAS",
     "la fiche d'usage PROPOSE le tiers 814, doublon inactif de 1065 (même "
     "site, Wettolsheim) : le lien proposé est retiré avant la fusion"),
    (18, "Sato",             117, "SATO FRANCE", ""),
    (19, "Shine",            177, "GUANGZHOU SHINE LABEL MATERIALS CO.LTD", ""),
    (29, "Siegwerk",         58,  "SIEGWERK France SAS", ""),
    (31, "Bostik",           69,  "BOSTIK SA (BOSTIK)",
     "la fiche d'usage porte 1 fournisseur coût matière et 2 matières"),
    (30, "Fedrigoni Manter", 51,  "ARCONVERT S.A",
     "le tiers 629 porte le code ERP MANTER et l'adresse de Manipulados del "
     "Ter à Sant Gregori : c'est Manter, pas Arconvert — la fiche Fedrigoni "
     "(id 2, branche Arconvert) reste seule, sans tiers ERP"),
]

# Vus, écartés, et pourquoi. Affichés par --inventaire pour que personne ne
# refasse l'analyse en croyant à un oubli.
A_TRANCHER = [
    ("Suzhou (20) ⇄ SUZHOU PIAOZHIHUA (160)",
     "« Suzhou » est un nom de ville et le tiers est à Taicang. La fiche 20 "
     "porte un contact : une question suffit à trancher."),
    ("Torrespapel (22) ⇄ TORRASPAPEL FRANCE (63) / ESPAGNE (220)",
     "Deux tiers ERP réels. La licence FSC-C011032 va sur celui qui facture "
     "les bobines ; l'autre reste, avec groupe = Torraspapel."),
    ("BURBAN Palettes (195) ⇄ BURBAN PALETTES (199)",
     "Vrai doublon, mais né côté ERP : deux tiers ACTIFS (1190 et 1195), même "
     "code, SIRET d'établissements différents. Fusionner ici libère un tiers "
     "vivant, que le prochain import recréera. À corbeiller dans RVGI d'abord."),
    ("UPM (23) ⇄ UPM RAFLATAC (172)",
     "NE PAS fusionner : 1151 = UPM Tampere (FI), 1166 = Raflatac Pompey (FR), "
     "deux entités. Confirmer le lien de la 23 et poser groupe = UPM."),
]


def _chemin_defaut() -> str:
    try:
        from config import DB_PATH  # type: ignore
        return DB_PATH
    except Exception:
        return os.path.join(RACINE, "data", "production.db")


def _ouvrir(chemin: str) -> sqlite3.Connection:
    conn = sqlite3.connect(chemin)
    conn.row_factory = sqlite3.Row
    # `fusionner_fournisseurs` ouvre sa transaction avec un BEGIN explicite :
    # sans autocommit, sqlite3 en aurait déjà ouvert une et le BEGIN échouerait.
    conn.isolation_level = None
    return conn


def _fiche(conn, fid: int):
    return conn.execute("SELECT * FROM fournisseurs_fsc WHERE id=?", (fid,)).fetchone()


def _lien(f) -> str:
    """Lien ERP d'une fiche, en une ligne lisible."""
    if f is None or "rvgi_numero" not in f.keys():
        return "—"
    if not f["rvgi_numero"]:
        return "manuel"
    return "%s %s" % (f["rvgi_etat"] or "?", f["rvgi_numero"])


def _ce_qui_bouge(conn, source_id: int) -> dict:
    """Lignes rattachées à la fiche absorbée, table par table.

    Même introspection que la fusion : ce qui est compté ici est exactement ce
    qui sera déplacé.
    """
    from app.routers.settings import _four_refs_fournisseur
    refs_id, refs_nom, _refs_json = _four_refs_fournisseur(conn)
    src = _fiche(conn, source_id)
    detail = {}
    for table, col, _u in refs_id:
        n = conn.execute(
            "SELECT COUNT(*) FROM %s WHERE %s=?" % (table, col), (source_id,)
        ).fetchone()[0]
        if n:
            detail["%s.%s" % (table, col)] = n
    if src is not None:
        for table, col in refs_nom:
            n = conn.execute(
                "SELECT COUNT(*) FROM %s WHERE %s=?" % (table, col), (src["nom"],)
            ).fetchone()[0]
            if n:
                detail["%s.%s (renommé)" % (table, col)] = n
    return detail


# ═══════════════════════════════════════════════════════════════════════
#  Un couple
# ═══════════════════════════════════════════════════════════════════════

class Refus(Exception):
    """Le couple n'est pas dans l'état attendu : on le saute, on ne devine pas."""


def _preparer(conn, ligne, sens: str, forcer: bool):
    """Résout un couple du plan et rend (source, cible) ou lève Refus."""
    id_court, nom_court, id_erp, nom_erp, _note = ligne
    f_court, f_erp = _fiche(conn, id_court), _fiche(conn, id_erp)

    if f_court is None and f_erp is None:
        raise Refus("les deux fiches ont disparu — plan périmé")
    if f_court is None or f_erp is None:
        raise Refus("déjà fusionné (il ne reste qu'une fiche)")
    if f_court["nom"] != nom_court:
        raise Refus("la fiche %s s'appelle « %s » et non « %s »"
                    % (id_court, f_court["nom"], nom_court))
    if f_erp["nom"] != nom_erp:
        raise Refus("la fiche %s s'appelle « %s » et non « %s »"
                    % (id_erp, f_erp["nom"], nom_erp))

    a_lien = "rvgi_numero" in f_court.keys()
    if (a_lien and not forcer
            and f_court["rvgi_etat"] == "lie" and f_erp["rvgi_etat"] == "lie"):
        raise Refus("les deux fiches sont liées à un tiers ERP actif (%s et %s) — "
                    "le doublon est côté RVGI, à régler là-bas (ou --forcer)"
                    % (f_court["rvgi_numero"], f_erp["rvgi_numero"]))

    if sens == "erp":
        return f_court, f_erp          # la fiche d'usage est absorbée
    return f_erp, f_court              # défaut : le tiers ERP est absorbé


def _detacher_proposition(conn, cible, source, ecrire: bool) -> str:
    """Retire de la cible un lien ERP seulement PROPOSÉ, quand la source en
    porte un confirmé.

    Cas Ricoh : la fiche d'usage propose le tiers 814 — un doublon inactif —
    pendant que le tiers repris porte le 1065, confirmé. Sans ce détachement,
    la survivante garderait la proposition et le 1065, libéré, reviendrait au
    prochain import. La fusion, elle, ne tranche jamais entre deux liens : ce
    n'est pas une reprise de champ vide, c'est un arbitrage.
    """
    if "rvgi_numero" not in cible.keys():
        return ""
    if not (cible["rvgi_numero"] and cible["rvgi_etat"] == "a_confirmer"
            and source["rvgi_numero"] and source["rvgi_etat"] == "lie"):
        return ""
    if ecrire:
        conn.execute(
            "UPDATE fournisseurs_fsc SET rvgi_numero=NULL, rvgi_code=NULL, "
            "rvgi_etat='manuel', rvgi_motif=NULL, rvgi_score=NULL, "
            "updated_at=? WHERE id=?",
            (datetime.now().isoformat(), cible["id"]))
        conn.commit()
    return ("lien proposé %s retiré de la cible au profit du lien confirmé %s"
            % (cible["rvgi_numero"], source["rvgi_numero"]))


# ═══════════════════════════════════════════════════════════════════════
#  Les trois modes
# ═══════════════════════════════════════════════════════════════════════

def inventaire(conn, sens: str, lignes) -> None:
    print("\nÉtat des couples")
    print("─" * 78)
    for i, ligne in enumerate(lignes, 1):
        id_court, nom_court, id_erp, nom_erp, note = ligne
        f_court, f_erp = _fiche(conn, id_court), _fiche(conn, id_erp)
        print("%2d. %-28s %-8s ⇄ %-42s %s"
              % (i, nom_court if f_court else "(%s absente)" % id_court,
                 _lien(f_court),
                 (nom_erp if f_erp else "(%s absente)" % id_erp)[:42],
                 _lien(f_erp)))
        if note:
            print("      %s" % note)
    print("\nLaissés de côté — arbitrage humain")
    print("─" * 78)
    for titre, pourquoi in A_TRANCHER:
        print("  %s" % titre)
        print("      %s" % pourquoi)


def executer(conn, sens: str, lignes, ecrire: bool, forcer: bool) -> int:
    faits = 0
    from app.routers.settings import fusionner_fournisseurs

    for i, ligne in enumerate(lignes, 1):
        try:
            source, cible = _preparer(conn, ligne, sens, forcer)
        except Refus as r:
            print("%2d. — %s" % (i, r))
            continue

        bouge = _ce_qui_bouge(conn, source["id"])
        print("%2d. %s (%s) → %s (%s)"
              % (i, source["nom"], source["id"], cible["nom"], cible["id"]))
        detache = _detacher_proposition(conn, cible, source, ecrire)
        if detache:
            print("      %s" % detache)
        if bouge:
            for quoi, n in sorted(bouge.items()):
                print("      %-52s %3d" % (quoi, n))
        else:
            print("      rien de rattaché à déplacer")

        if not ecrire:
            continue
        try:
            res = fusionner_fournisseurs(conn, source["id"], cible["id"])
        except Exception as e:                       # noqa: BLE001
            print("      ÉCHEC — %s : %s" % (type(e).__name__, e))
            print("      (transaction annulée, la base est intacte ; les "
                  "couples suivants sont tout de même tentés)")
            continue
        recup = res["champs_recuperes"]
        print("      fusionné. Champs récupérés : %s"
              % (", ".join(recup) if recup else "aucun"))
        faits += 1
    return faits


def sauvegarder(chemin: str) -> str:
    """Copie de la base AVANT écriture. Via l'API backup de SQLite : un simple
    `cp` laisserait le WAL de côté et rendrait une copie en retard."""
    dest = "%s.avant_fusion_%s.bak" % (chemin, datetime.now().strftime("%Y%m%d_%H%M%S"))
    src = sqlite3.connect(chemin)
    dst = sqlite3.connect(dest)
    with dst:
        src.backup(dst)
    dst.close()
    src.close()
    return dest


def main() -> int:
    ap = argparse.ArgumentParser(description="Fusion des doublons fournisseurs")
    ap.add_argument("--db", default=_chemin_defaut())
    ap.add_argument("--inventaire", action="store_true",
                    help="l'état des couples, sans rien simuler")
    ap.add_argument("--appliquer", action="store_true",
                    help="écrit (défaut : simulation)")
    ap.add_argument("--sens", choices=("court", "erp"), default="court",
                    help="quelle fiche survit : la fiche d'usage (défaut) ou "
                         "le tiers ERP")
    ap.add_argument("--couple", type=int, default=None,
                    help="ne traiter que la ligne N du plan")
    ap.add_argument("--forcer", action="store_true",
                    help="fusionner même si les deux fiches sont liées à un "
                         "tiers ERP actif")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print("Base introuvable : %s" % args.db)
        return 2

    lignes = PLAN
    if args.couple is not None:
        if not 1 <= args.couple <= len(PLAN):
            print("--couple attend un numéro entre 1 et %d" % len(PLAN))
            return 2
        lignes = [PLAN[args.couple - 1]]

    print("Base   : %s" % args.db)
    print("Sens   : la fiche %s survit"
          % ("d'usage (nom court)" if args.sens == "court" else "reprise de l'ERP"))
    print("Mode   : %s" % ("INVENTAIRE" if args.inventaire else
                           "ÉCRITURE" if args.appliquer else "simulation"))

    conn = _ouvrir(args.db)
    try:
        if args.inventaire:
            inventaire(conn, args.sens, lignes)
            return 0

        if args.appliquer:
            conn.close()
            copie = sauvegarder(args.db)
            print("Copie  : %s\n" % copie)
            conn = _ouvrir(args.db)
        else:
            print("")

        faits = executer(conn, args.sens, lignes, args.appliquer, args.forcer)
        print("\n" + "─" * 78)
        if args.appliquer:
            print("%d fusion(s) effectuée(s)." % faits)
            print("Lancer maintenant la synchro RVGI (Paramètres → Fournisseurs "
                  "→ RVGI, « Appliquer ») : elle réaligne pays, devise et langue "
                  "des fiches survivantes.")
        else:
            print("Simulation terminée — rien n'a été écrit. "
                  "Relancer avec --appliquer.")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())

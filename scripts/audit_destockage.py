#!/usr/bin/env python3
"""Audit du déstockage de production — est-ce que ça marche vraiment ?

Le mécanisme de déstockage de fin de dossier est écrit, testé et correct :
`/api/stock/destockage/{planning_id}` calcule ce qui doit sortir à partir de
l'OF et de la fiche technique, refuse de bouger sans documents relus, fait
primer le réel sur le théorique et sait se contre-passer.

Ce script ne vérifie pas ce code. Il vérifie qu'il TOURNE — ce qui est une tout
autre question, et la seule qui se voie à l'inventaire.

Lecture seule. Aucune écriture, aucune correction : ce script constate.

    python3 scripts/audit_destockage.py --db data/production.db
"""

from __future__ import annotations

import argparse
import sqlite3
import sys

CHAMPS_FICHE = [
    ("support", "support_ref_id", "support"),
    ("glassine", "glassine_ref_id", "glassine"),
    ("adhesif", "adhesif_ref_id", "adhesif"),
    ("mandrin_dia", "mandrin_ref_id", "mandrin"),
    ("cartons", "carton_ref_id", "carton"),
    ("palette_type", "palette_ref_id", "palette"),
]


def titre(t: str) -> None:
    print("\n" + t)
    print("─" * len(t))


def un(conn, sql, args=()):
    r = conn.execute(sql, args).fetchone()
    return r[0] if r else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="data/production.db")
    a = ap.parse_args()

    conn = sqlite3.connect("file:%s?mode=ro" % a.db, uri=True)
    conn.row_factory = sqlite3.Row

    alertes = []

    # ── 1. Le bouton du planning écrit-il quelque chose ? ────────────────────
    titre("1. Le bouton « Déstocker » du planning")
    done = un(conn, "SELECT COUNT(*) FROM planning_entries WHERE destockage='done'")
    avec_mvt = un(conn, "SELECT COUNT(DISTINCT planning_entry_id) FROM mp_mouvements "
                        "WHERE planning_entry_id IS NOT NULL")
    print("  dossiers marqués « déstocké »          : %d" % done)
    print("  dossiers avec un mouvement de stock    : %d" % avec_mvt)
    if done and not avec_mvt:
        alertes.append(
            "Le marquage « déstocké » ne déclenche AUCUN mouvement de stock. "
            "%d dossiers portent le drapeau, zéro n'a sorti un gramme de matière. "
            "La modale de déstockage a été débranchée du planning "
            "(app/web/planning_page.py, `toggleDestockage`) : le bouton ne fait "
            "plus que colorer un point sur la timeline. Les endpoints, eux, "
            "fonctionnent toujours." % done)
    elif done and avec_mvt < done * 0.8:
        alertes.append("Seuls %d des %d dossiers marqués déstockés ont un mouvement."
                       % (avec_mvt, done))

    # ── 2. D'où viennent les sorties de stock, alors ? ───────────────────────
    titre("2. Les sorties de stock existantes")
    for r in conn.execute(
        """SELECT type_mouvement AS t, COUNT(*) AS n,
                  SUM(CASE WHEN planning_entry_id IS NOT NULL THEN 1 ELSE 0 END) AS lie,
                  MAX(created_at) AS dernier
             FROM mp_mouvements GROUP BY type_mouvement ORDER BY t"""
    ).fetchall():
        print("  %-11s %5d mouvement(s) · %d rattaché(s) à un dossier · dernier %s"
              % (r["t"], r["n"], r["lie"], (r["dernier"] or "")[:10]))
    sorties = un(conn, "SELECT COUNT(*) FROM mp_mouvements WHERE type_mouvement='sortie'")
    sorties_liees = un(conn, "SELECT COUNT(*) FROM mp_mouvements "
                             "WHERE type_mouvement='sortie' AND planning_entry_id IS NOT NULL")
    if sorties and not sorties_liees:
        alertes.append(
            "Les %d sorties de matière sont toutes saisies à la main, sans "
            "rattachement à un dossier. Une consommation sans dossier ne se "
            "compare à aucun besoin : ni écart, ni surconsommation, ni "
            "rentabilité matière." % sorties)

    # ── 3. Dossiers terminés jamais déstockés ────────────────────────────────
    titre("3. Dossiers terminés et non déstockés")
    n = un(conn, "SELECT COUNT(*) FROM planning_entries "
                 "WHERE statut='termine' AND COALESCE(destockage,'todo')='todo'")
    print("  %d dossier(s) terminé(s) sans marquage de déstockage" % n)
    for r in conn.execute(
        """SELECT reference, numero_of, client FROM planning_entries
            WHERE statut='termine' AND COALESCE(destockage,'todo')='todo'
            ORDER BY id DESC LIMIT 8"""
    ).fetchall():
        print("    · %-14s %-12s %s" % (r["reference"] or "", r["numero_of"] or "",
                                        (r["client"] or "")[:34]))

    # ── 4. Couverture des correspondances fiche → matière ────────────────────
    #
    # Le point aveugle connu : une valeur de fiche qu'aucune référence MyStock
    # ne recouvre sort un besoin NUL, en silence. Le dossier se déstocke,
    # l'écran ne dit rien, et l'écart apparaît à l'inventaire des semaines plus
    # tard sans que rien ne le relie à sa cause.
    titre("4. Correspondances fiche technique → matière MyStock")
    mapping = {(r["kind"], (r["source_value"] or "").strip().lower())
               for r in conn.execute(
                   "SELECT kind, source_value FROM mp_fiche_mapping").fetchall()}
    print("  %d correspondance(s) enregistrée(s) dans mp_fiche_mapping" % len(mapping))

    total_trous = 0
    for colonne, ref_col, kind in CHAMPS_FICHE:
        trous: dict = {}
        for r in conn.execute(
            """SELECT ft.%s AS v, COUNT(DISTINCT pe.id) AS n
                 FROM planning_entries pe
                 JOIN of_imports oi        ON oi.id = pe.of_import_id
                 JOIN fiches_techniques ft ON ft.reference = oi.reference
                WHERE IFNULL(ft.%s,'') <> '' AND ft.%s IS NULL
                GROUP BY ft.%s""" % (colonne, colonne, ref_col, colonne)
        ).fetchall():
            v = (r["v"] or "").strip()
            if not v or (kind, v.lower()) in mapping:
                continue
            trous[v] = r["n"]
        if trous:
            total_trous += len(trous)
            print("  %s — %d valeur(s) sans référence MyStock :" % (kind, len(trous)))
            for v, nb in sorted(trous.items(), key=lambda x: -x[1])[:6]:
                print("    · %-38s %d dossier(s)" % (v[:38], nb))
    if total_trous:
        alertes.append(
            "%d valeur(s) de fiche technique ne pointent aucune référence "
            "MyStock, ni par mp_fiche_mapping ni par *_ref_id. Ces lignes "
            "sortent un besoin nul sans le dire." % total_trous)
    else:
        print("  Aucun trou sur les dossiers du planning actuel.")

    # ── 5. Le verrou documentaire ────────────────────────────────────────────
    titre("5. Verrou documentaire (OF et fiche relus)")
    try:
        bloques = un(conn, """
            SELECT COUNT(*) FROM planning_entries pe
              LEFT JOIN of_imports oi        ON oi.id = pe.of_import_id
              LEFT JOIN fiches_techniques ft ON ft.reference = oi.reference
             WHERE pe.statut='termine'
               AND COALESCE(pe.destockage,'todo')='todo'
               AND (COALESCE(oi.valide,0)=0 OR COALESCE(ft.valide,0)=0)""")
        print("  %d dossier(s) terminé(s) que le verrou empêcherait de déstocker" % bloques)
        if bloques and n:
            print("    soit %d %% des dossiers terminés non déstockés."
                  % round(100.0 * bloques / n))
    except sqlite3.Error as e:
        print("  (contrôle impossible : %s)" % e)

    # ── 6. Stocks négatifs ───────────────────────────────────────────────────
    titre("6. Stocks négatifs")
    neg = [dict(r) for r in conn.execute(
        """SELECT mp.reference, sl.laize_id, sl.quantite
             FROM mp_stock_laize sl JOIN matieres_premieres mp ON mp.id=sl.matiere_id
            WHERE sl.quantite < 0
            UNION ALL
           SELECT mp.reference, NULL, s.quantite
             FROM mp_stock s JOIN matieres_premieres mp ON mp.id=s.matiere_id
            WHERE s.quantite < 0""").fetchall()]
    if neg:
        alertes.append("%d ligne(s) de stock négative(s)." % len(neg))
        for r in neg[:10]:
            print("    · %-16s laize %-6s %g" % (r["reference"], r["laize_id"] or "—",
                                                 r["quantite"]))
    else:
        print("  Aucune.")

    # ── Verdict ──────────────────────────────────────────────────────────────
    titre("Ce qu'il faut retenir")
    if not alertes:
        print("  Rien à signaler : le déstockage tourne et laisse des traces.")
    else:
        for i, m in enumerate(alertes, 1):
            print("  %d. %s" % (i, m))
    conn.close()
    return 1 if alertes else 0


if __name__ == "__main__":
    sys.exit(main())

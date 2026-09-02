#!/usr/bin/env python3
"""
Rejeu de la contrainte transport sur les donnees reelles, sans rien ecrire.

A lancer AVANT de mettre la regle en service, et apres tout changement de
seuil : le script dit exactement quels dossiers seraient contraints, lesquels
sont deja en retard sur leur enlevement, et combien d'heures de marge la regle
ajouterait a chaque machine.

Il ne touche jamais la base visee. Le module `app.core.database` joue ses
migrations au chargement : travailler directement sur `production.db`
reviendrait a la migrer pour une simulation. Le script en fait donc une COPIE
et raisonne dessus.

Usage :
    python3 scripts/simuler_contrainte_transport.py
    python3 scripts/simuler_contrainte_transport.py --base /chemin/vers/production.db
    python3 scripts/simuler_contrainte_transport.py --historique
"""

import argparse
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RACINE))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", help="Base a simuler (defaut : DB_PATH de config.py)")
    ap.add_argument("--historique", action="store_true",
                    help="Ajoute le bilan sur tout l'historique des rattachements")
    args = ap.parse_args()

    import config
    source = Path(args.base or config.DB_PATH)
    if not source.exists():
        print(f"Base introuvable : {source}")
        return 1

    tmp = Path(tempfile.mkdtemp(prefix="simu_transport_")) / "copie.db"
    shutil.copy2(source, tmp)
    os.environ["DB_PATH"] = str(tmp)

    import database  # noqa: F401  — toujours avant tout app.* (cf. CLAUDE.md)
    from database import get_db
    from app.routers import planning as P
    from app.services import transport_planning as tp

    print(f"Base simulee : {source}")
    print(f"Copie de travail : {tmp}\n")

    with get_db() as conn:
        params = tp.charger_params(conn)
        print("Reglages en vigueur")
        print(f"  regle active        : {'oui' if params['actif'] else 'non'}")
        print(f"  heure limite        : {params['heure_limite']:g} h")
        print(f"  seuil de palettes   : {params['seuil_palettes']:g}")
        print(f"  marge de production : {params['marge_pct']:g} %\n")

        machines = conn.execute(
            "SELECT id, nom FROM machines WHERE COALESCE(actif,1)=1 ORDER BY id"
        ).fetchall()

        total_contraints = 0
        total_depasses = 0
        total_marge = 0.0

        for m in machines:
            mid = int(m["id"])
            entries, contraintes, fins = P._transport_etat(conn, mid)
            if not contraintes:
                print(f"{m['nom']} : aucun dossier contraint "
                      f"({len(entries)} dossier(s) au planning)")
                continue
            marge_machine = sum(
                tp.marge_heures(e.get("duree_heures"), contraintes.get(int(e["id"])))
                for e in entries if e.get("id") is not None
            )
            total_marge += marge_machine
            print(f"{m['nom']} : {len(contraintes)} dossier(s) contraint(s), "
                  f"+{marge_machine:.1f} h de marge sur la file")
            for eid, c in sorted(contraintes.items(),
                                 key=lambda kv: kv[1]["date_enlevement"]):
                e = next((x for x in entries if int(x["id"]) == eid), {})
                ref = str(e.get("numero_of") or e.get("reference") or eid).strip()
                fin = fins.get(eid)
                etat = tp.tension(c, fin)
                total_contraints += 1
                if etat == "depasse":
                    total_depasses += 1
                fin_txt = tp.fmt_jour_heure(fin) if fin else "fin inconnue"
                print(f"    [{etat.upper():7}] {ref:32.32} "
                      f"{c['transporteur'] or '?':12.12} "
                      f"{c['palettes']:g} pal  "
                      f"limite {tp.fmt_jour_heure(c['limite'])}  "
                      f"fin {fin_txt}")

        print(f"\nTotal : {total_contraints} dossier(s) contraint(s), "
              f"dont {total_depasses} deja au-dela de la limite. "
              f"Marge cumulee : {total_marge:.1f} h.")
        if total_depasses:
            print("Les dossiers marques DEPASSE ne seront pas bloques : la regle "
                  "refuse seulement les gestes qui AGGRAVENT leur situation.")

        if args.historique:
            print("\nBilan sur tout l'historique des rattachements")
            lignes = conn.execute(
                """
                WITH liens AS (
                  SELECT dd.planning_entry_id AS eid, d.id AS did,
                         d.date_enlevement, d.nb_palette, d.created_at
                    FROM expe_depart_dossiers dd
                    JOIN expe_departs d ON d.id = dd.depart_id
                  UNION
                  SELECT d.planning_entry_id, d.id, d.date_enlevement,
                         d.nb_palette, d.created_at
                    FROM expe_departs d WHERE d.planning_entry_id IS NOT NULL
                )
                SELECT COUNT(*) AS liens,
                       SUM(CASE WHEN l.nb_palette >= ? THEN 1 ELSE 0 END) AS qualifiants,
                       SUM(CASE WHEN l.nb_palette IS NULL THEN 1 ELSE 0 END) AS sans_palette,
                       SUM(CASE WHEN l.nb_palette >= ?
                                 AND pe.planned_end > l.date_enlevement || 'T'
                                     || substr('0' || CAST(? AS INT), -2) || ':00:00'
                                THEN 1 ELSE 0 END) AS auraient_depasse
                  FROM liens l JOIN planning_entries pe ON pe.id = l.eid
                """,
                (params["seuil_palettes"], params["seuil_palettes"],
                 int(params["heure_limite"])),
            ).fetchone()
            def _n(cle):
                # SUM() sur un ensemble vide renvoie NULL, pas 0 : sans ça le
                # bilan afficherait « None » sur une base sans rattachement.
                return int(lignes[cle] or 0)
            print(f"  rattachements dossier <-> depart : {_n('liens')}")
            print(f"  dont au moins {params['seuil_palettes']:g} palettes : {_n('qualifiants')}")
            print(f"  dont palettes non renseignees    : {_n('sans_palette')}")
            print(f"  qui auraient depasse la limite   : {_n('auraient_depasse')}")

    print(f"\nAucune ecriture sur {source}. La copie peut etre supprimee : {tmp.parent}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Synchronisation Access → MySifa : table t_of
--------------------------------------------
Ce script lit les OFs créés après DATE_DEPUIS dans la base Access et les
pousse vers MySifa via l'API bridge.

Un OF déjà présent dans MySifa (même numero_of) n'est jamais écrasé. Avec
ENRICHIR_EXISTANTS = True, ses colonnes restées vides sont simplement
complétées — utile pour rattraper les OF poussés avant l'ajout du métrage.

Ce que le script récupère, et d'où
-----------------------------------
Le métrage est STOCKÉ dans Access : t_of.theorique_metrage_necessaire. Il n'y
a rien à recalculer. (Vérifié sur l'OF 9931861 : 7124,0398 en base pour 7124
imprimé sur le papier.)

La quantité d'adhésif, elle, est calculée. La formule vient de la vue Access
[adhesif_necessaire_sans_date_prev], reprise ici telle quelle :

    kg = Adhesif.grammage × theorique_metrage_necessaire × matlaizestandard / 1e6

Vérifié sur l'OF 9931861 : 19 g/m² × 7124,04 m × 470 mm / 1e6 = 63,618 kg,
pour 63,6 kg imprimé.

ATTENTION — la laize utilisée est matlaizestandard, PAS matlaize. Sur ce même
OF, matlaize vaut 453 et donnerait 61,3 kg, ce qui est faux. Le libellé
« Laize optionnelle » porté par t_of.choix_laize_matiere est un intitulé de
formulaire, pas le choix d'une laize alternative.

Toutes les matières n'ont pas de grammage : quand matadhesif vaut simplement
« Permanent », sans référence, la jointure sur Adhesif ne donne rien et les
champs adhésif restent vides. C'est le comportement attendu — sur ces OF, les
cases adhésif du papier sont vides elles aussi. Environ 30 % des OF sont dans
ce cas.

Dépendances :
    pip install pyodbc requests

Configuration :
    ACCESS_DB_PATH ci-dessous, et la clé API dans la variable
    d'environnement MYSIFA_API_KEY (jamais en clair dans le fichier).

Usage :
    python scripts/access_sync_of.py
    python scripts/access_sync_of.py --depuis 2025-09-01 --dry-run
    python scripts/access_sync_of.py --depuis 2025-09-01

`--depuis` sert aux rattrapages. La borne porte sur la date de CRÉATION de
l'OF : viser les livraisons de novembre en partant du 1er novembre ne ramène
rien, puisque ces OF ont été créés en septembre ou en octobre.

`--dry-run` n'écrit rien et dit seulement ce qu'Access contient — à faire
avant tout rattrapage de masse, qui écrit en production.
"""

import argparse
import os
import re
import pyodbc
import requests
from datetime import datetime

# ── Configuration ────────────────────────────────────────────────────
ACCESS_DB_PATH  = r"\\IDEFIX\sifa_pub\Fiches techniques Access\of.mdb"
MYSIFA_BASE_URL = "https://mysifa.com"
# Clé API : setx MYSIFA_API_KEY "msk_..." puis rouvrir le terminal.
MYSIFA_API_KEY  = os.environ.get("MYSIFA_API_KEY", "")

# Date de départ PAR DÉFAUT du passage quotidien. `--depuis` la surcharge pour
# un rattrapage ponctuel : la borne porte sur la date de CRÉATION de l'OF, pas
# sur sa livraison. Un OF livré en novembre a été créé en septembre ou octobre,
# donc un rattrapage qui vise les livraisons de novembre doit remonter plus
# haut que novembre, sans quoi il ne verra rien.
DATE_DEPUIS        = "2025-11-01"   # OFs créés strictement après cette date
ENRICHIR_EXISTANTS = True           # compléter les colonnes vides des OF déjà importés
RAFRAICHIR_ACCESS  = True           # propager aussi les valeurs CHANGÉES dans Access
                                    # (sans effet sur un OF ayant un PDF ou une saisie manuelle)

HEADERS = {
    "X-Api-Key":    MYSIFA_API_KEY,
    "Content-Type": "application/json",
}

# ── Connexion Access ─────────────────────────────────────────────────
CONN_STR = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    f"DBQ={ACCESS_DB_PATH};"
)

# t_fiches_techniques et Adhesif vivent toutes deux dans of.mdb : la première
# est une table liée vers sifa_fiches_techniques.mdb, la seconde est locale.
# La jointure se fait donc en une seule requête, sans seconde connexion.
SQL_OF = """
    SELECT t_of.numero_of                     AS numero_of,
           t_of.date_creation                 AS date_creation,
           t_of.date_delai                    AS date_delai,
           t_of.format                        AS format,
           t_of.theorique_quantite            AS qte,
           t_of.theorique_quantite_bobines    AS bobines,
           t_of.theorique_metrage_necessaire  AS metrage,
           t_of.theorique_mandrins            AS mandrins,
           t_of.theorique_cartons             AS cartons,
           t_of.theorique_tubes               AS tubes,
           f.matsupport                       AS matiere,
           f.matglassine                      AS glassine,
           f.matlaizestandard                 AS laize,
           f.matquantite                      AS qte_mille,
           f.matquantite_type                 AS qte_mille_type,
           f.matadhesif                       AS adhesif_label,
           f.machine                          AS machine,
           a.reference                        AS adhesif_ref,
           a.grammage                         AS adhesif_grammage
    FROM   (t_of LEFT JOIN t_fiches_techniques AS f
                 ON t_of.format = f.reference)
           LEFT JOIN Adhesif AS a
                 ON f.matadhesif = a.type
    WHERE  t_of.date_creation > ?
    ORDER  BY t_of.date_creation ASC
"""


def get_access_of(depuis=None):
    """Lit les OFs de t_of créés après `depuis`, fiche technique jointe."""
    conn = pyodbc.connect(CONN_STR)
    cur  = conn.cursor()
    cur.execute(SQL_OF, (depuis or DATE_DEPUIS,))
    rows = cur.fetchall()
    conn.close()
    return rows


# ── Conversions ──────────────────────────────────────────────────────

def to_float(val):
    """Convertit une valeur Access en float. Tolère « 470mm », « 10,794 », « 1 234 »."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    txt = re.sub(r"[^0-9,.\-]", "", str(val)).replace(",", ".")
    if txt in ("", "-", "."):
        return None
    try:
        return float(txt)
    except ValueError:
        return None


def to_int(val):
    f = to_float(val)
    return int(round(f)) if f is not None else None


def to_str(val):
    if val is None:
        return None
    return str(val).strip() or None


def format_date(val):
    """Convertit une date Access (datetime ou string) en 'YYYY-MM-DD'."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    brut = str(val).strip()[:10]
    for fmt in ("%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(brut, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return brut


def qte_adhesif_kg(grammage, metrage, laize_mm):
    """Formule de la vue Access [adhesif_necessaire_sans_date_prev].

    grammage en g/m², metrage en m, laize en mm → kg.
    Retourne None dès qu'un ingrédient manque : mieux vaut une case vide
    qu'un tonnage faux dans les besoins matières.
    """
    if grammage is None or metrage is None or laize_mm is None:
        return None
    return round(grammage * metrage * laize_mm / 1_000_000, 3)


# ── Envoi ────────────────────────────────────────────────────────────

def push_of(row) -> dict:
    """Envoie un OF vers MySifa. Retourne la réponse JSON."""
    metrage  = to_float(row.metrage)
    laize    = to_float(row.laize)
    grammage = to_float(row.adhesif_grammage)

    # matquantite ne vaut « quantité au mille » que si matquantite_type le dit.
    # Sur un autre type (au cent, à l'unité…), l'envoyer tel quel fausserait
    # tout calcul en aval.
    qte_mille = None
    if (row.qte_mille_type or "").strip().lower().startswith("au mille"):
        qte_mille = to_float(row.qte_mille)

    payload = {
        "numero_of":        str(row.numero_of).strip(),
        "date_creation":    format_date(row.date_creation),
        "delai_client":     format_date(row.date_delai),
        "format":           to_str(row.format),
        "reference":        to_str(row.format),   # t_of.format = fiches.reference
        "machine":          to_str(row.machine),
        "matiere":          to_str(row.matiere),
        "glassine":         to_str(row.glassine),
        "laize":            laize,
        "qte_etiquettes":   to_float(row.qte),
        "qte_bobines":      to_float(row.bobines),
        "metrage":          metrage,
        "qte_au_mille":     qte_mille,
        "adhesif_label":    to_str(row.adhesif_label),
        "ref_adhesif":      to_str(row.adhesif_ref),
        "qte_adhesif_g":    grammage,
        "qte_adhesif_kg":   qte_adhesif_kg(grammage, metrage, laize),
        "nb_mandrins":      to_int(row.mandrins),
        "nb_cartons":       to_int(row.cartons),
        "nb_tubes":         to_int(row.tubes),
        "enrich_if_exists":     ENRICHIR_EXISTANTS,
        "refresh_access_fields": RAFRAICHIR_ACCESS,
    }
    resp = requests.post(
        f"{MYSIFA_BASE_URL}/api/bridge/of",
        json=payload,
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def essai_a_blanc(rows, depuis):
    """Ce qu'Access a vraiment à donner, sans rien pousser.

    Un rattrapage sur plusieurs centaines d'OF écrit en production. Avant de
    le lancer, la seule question qui compte est : les colonnes qu'on vient
    chercher sont-elles renseignées côté Access ? Si `format` et `metrage` y
    sont vides, la synchro ne réparera rien et le problème est en amont.
    """
    n = len(rows)
    compte = {
        "format (→ référence produit, et donc fiche technique)":
            sum(1 for r in rows if str(r.format or "").strip()),
        "matiere (matsupport)":
            sum(1 for r in rows if str(r.matiere or "").strip()),
        "glassine (matglassine)":
            sum(1 for r in rows if str(r.glassine or "").strip()),
        "adhesif (matadhesif)":
            sum(1 for r in rows if str(r.adhesif_label or "").strip()),
        "metrage (theorique_metrage_necessaire)":
            sum(1 for r in rows if to_float(r.metrage)),
        "laize (matlaizestandard)":
            sum(1 for r in rows if to_float(r.laize)),
    }
    print(f"ESSAI À BLANC — rien n'est poussé vers {MYSIFA_BASE_URL}.\n")
    print(f"{n} OF(s) créés après le {depuis} dans Access.\n")
    print("  colonne Access                                          renseignée")
    print("  ─────────────────────────────────────────────────────────────────")
    for libelle, c in compte.items():
        pct = f"{(100.0 * c / n):5.1f}%" if n else "    —"
        print(f"  {libelle:52} {c:5} {pct}")

    exemples = [r for r in rows if not str(r.format or "").strip()][:5]
    if exemples:
        print(f"\n  {sum(1 for r in rows if not str(r.format or '').strip())} OF sans "
              "`format` : ceux-là ne trouveront jamais de fiche technique.")
        for r in exemples:
            print(f"    {str(r.numero_of).strip():28} "
                  f"créé le {format_date(r.date_creation)}")

    print("\n  Si `format` et `metrage` sont bien remplis ci-dessus, relancer sans")
    print("  --dry-run rapatriera tout. S'ils sont vides, la synchro n'y peut rien :")
    print("  la donnée manque dans Access, et c'est là qu'il faut la chercher.")


def main():
    ap = argparse.ArgumentParser(
        description="Synchronisation Access → MySifa (table t_of).")
    ap.add_argument("--depuis", default=DATE_DEPUIS, metavar="AAAA-MM-JJ",
                    help="OF créés strictement après cette date "
                         f"(défaut : {DATE_DEPUIS}). Pour un rattrapage, viser "
                         "plusieurs mois avant les livraisons manquantes.")
    ap.add_argument("--dry-run", action="store_true",
                    help="N'écrit rien : dit seulement ce qu'Access contient.")
    args = ap.parse_args()

    if not MYSIFA_API_KEY and not args.dry_run:
        print("Clé API absente. Définir la variable d'environnement MYSIFA_API_KEY :")
        print('  setx MYSIFA_API_KEY "msk_..."   puis rouvrir le terminal.')
        return

    print(f"Connexion à Access : {ACCESS_DB_PATH}")
    rows = get_access_of(args.depuis)

    if args.dry_run:
        essai_a_blanc(rows, args.depuis)
        return

    print(f"{len(rows)} OF(s) trouvé(s) après le {args.depuis}.\n")

    inserted = enriched = skipped = errors = 0
    conflits = devalides = 0
    sans_metrage = sans_adhesif = 0

    for row in rows:
        numero = str(row.numero_of).strip()
        if to_float(row.metrage) is None:
            sans_metrage += 1
        if to_float(row.adhesif_grammage) is None:
            sans_adhesif += 1
        try:
            result = push_of(row)
            if result.get("inserted"):
                print(f"  [OK]       OF {numero} → importé (id MySifa : {result['id']})")
                inserted += 1
            elif result.get("reason") == "refreshed":
                champs = ", ".join(sorted(set((result.get("refreshed_fields") or [])
                                              + (result.get("enriched_fields") or []))))
                print(f"  [MAJ]      OF {numero} → {champs}")
                enriched += 1
            elif result.get("reason") == "enriched":
                champs = ", ".join(result.get("enriched_fields") or [])
                print(f"  [COMPLÉTÉ] OF {numero} → {champs}")
                enriched += 1
            elif result.get("reason") == "conflit_saisie_manuelle":
                # Access propose une valeur différente sur un champ qu'un humain
                # a saisi dans MySifa. On ne l'écrase pas, mais le silence
                # d'avant était pire : personne ne savait que les deux bases
                # divergeaient. Le détail est aussi consultable dans MyStock.
                for c in result.get("conflits") or []:
                    print(f"  [CONFLIT]  OF {numero} → {c.get('libelle', c.get('champ'))} : "
                          f"MySifa {c.get('actuel')!r} ≠ Access {c.get('propose')!r} "
                          f"(saisie manuelle conservée)")
                conflits += 1
            else:
                print(f"  [IGNORÉ]   OF {numero} → déjà complet (id : {result['id']})")
                skipped += 1
            if result.get("validation_retiree"):
                print(f"             ↳ {result.get('motif_validation')} "
                      f"L'OF est à revalider dans MyStock avant tout déstockage.")
                devalides += 1
        except requests.HTTPError as e:
            print(f"  [ERREUR]   OF {numero} → HTTP {e.response.status_code} : {e.response.text[:120]}")
            errors += 1
        except Exception as e:
            print(f"  [ERREUR]   OF {numero} → {e}")
            errors += 1

    print(f"\nRésultat — Importés : {inserted}  |  Complétés : {enriched}"
          f"  |  Inchangés : {skipped}  |  Conflits : {conflits}"
          f"  |  Validations retirées : {devalides}  |  Erreurs : {errors}")
    print(f"Sans métrage en base : {sans_metrage}  |  "
          f"Sans grammage adhésif : {sans_adhesif} "
          f"(normal quand matadhesif = « Permanent » sans référence)")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompu.")

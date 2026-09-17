"""
Synchronisation Access → MySifa : fiches techniques
----------------------------------------------------
Lit TOUTES les fiches de sifa_fiches_techniques.mdb et pousse vers MySifa
(upsert par référence) celles dont le CONTENU a changé depuis le dernier
passage.

Pourquoi plus de filtre sur `modif` (17/09/2026)
-----------------------------------------------
La fiche 1341/0012 est restée dans MySifa en « VELIN H400 » alors qu'Access
dit « PP synthétique ». Elle avait été créée le 11/09 en dupliquant la
1341/0008, poussée telle quelle au passage de 12h00, puis corrigée dans
l'après-midi (matière, format, outil). Le passage suivant ne l'a jamais
revue : il filtrait sur `modif > date du dernier passage`, or `modif` est une
DATE sans heure et le fichier de dernier passage contenait déjà
« 2026-09-11 ». Toute correction faite le jour même d'un passage — et toute
modification qui ne met pas `modif` à jour — était perdue pour de bon.

Le script compare désormais une empreinte du contenu de chaque fiche à celle
du dernier envoi réussi (`SYNC_STATE_FILE`). Lire ~900 lignes d'Access prend
une seconde ; seules les fiches réellement modifiées partent vers MySifa.
Au premier passage (fichier d'empreintes absent), toutes les fiches sont
envoyées : celles qui n'ont pas changé répondent « identique » et ne
bougent pas, les autres sont rattrapées.

Usage :
    python scripts/access_sync_fiches.py
    python scripts/access_sync_fiches.py --tout        renvoyer toutes les fiches
    python scripts/access_sync_fiches.py --ref 1341/0012

Dépendances :
    pip install pyodbc requests

Configuration :
    ACCESS_DB_PATH et TABLE_NAME ci-dessous, et la clé API dans la variable
    d'environnement MYSIFA_API_KEY (jamais en clair dans le fichier).
"""
import argparse
import hashlib
import json
import os
import pyodbc
import requests
from datetime import datetime

# ── Configuration ────────────────────────────────────────────────────
ACCESS_DB_PATH  = r"\\IDEFIX\sifa_pub\Fiches techniques Access\sifa_fiches_techniques.mdb"
LAST_RUN_FILE   = r"\\IDEFIX\sifa_pub\Fiches techniques Access\last_sync_fiches.txt"
# Empreinte du contenu de chaque fiche au dernier envoi réussi.
SYNC_STATE_FILE = r"\\IDEFIX\sifa_pub\Fiches techniques Access\sync_fiches_empreintes.json"
TABLE_NAME      = "fiches_techniques"
MYSIFA_BASE_URL = "https://mysifa.com"
# Clé API : setx MYSIFA_API_KEY "msk_..." puis rouvrir le terminal.
MYSIFA_API_KEY  = os.environ.get("MYSIFA_API_KEY", "")

HEADERS = {
    "X-Api-Key":    MYSIFA_API_KEY,
    "Content-Type": "application/json",
}

CONN_STR = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    f"DBQ={ACCESS_DB_PATH};"
)

# ── Helpers date ─────────────────────────────────────────────────────

def save_date_depuis():
    """Trace humaine du dernier passage. Plus lue par le script."""
    with open(LAST_RUN_FILE, "w") as f:
        f.write(datetime.now().strftime("%Y-%m-%d %H:%M"))


def lire_empreintes() -> dict:
    try:
        with open(SYNC_STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def ecrire_empreintes(empreintes: dict) -> None:
    tmp = SYNC_STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(empreintes, f, ensure_ascii=False, indent=0, sort_keys=True)
    os.replace(tmp, SYNC_STATE_FILE)


def cle_ref(ref: str) -> str:
    return " ".join(str(ref or "").split()).lower()


def empreinte(payload: dict) -> str:
    brut = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha1(brut.encode("utf-8")).hexdigest()

def fmt_date(val) -> str | None:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    try:
        return datetime.strptime(str(val).strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return str(val).strip()[:10]

def s(val) -> str | None:
    """String ou None."""
    if val is None:
        return None
    v = str(val).strip()
    return v if v else None

def f(val) -> float | None:
    try:
        return float(val) if val is not None else None
    except (ValueError, TypeError):
        return None

def i(val) -> int | None:
    try:
        return int(val) if val is not None else None
    except (ValueError, TypeError):
        return None


# ── Lecture Access ────────────────────────────────────────────────────

def get_access_fiches() -> list:
    """Toutes les fiches. Pas de filtre sur `modif` : voir l'en-tête."""
    conn = pyodbc.connect(CONN_STR)
    cur  = conn.cursor()
    cur.execute(
        f"""
        SELECT [reference], [date_creation], [modif],
               [format],
               [etilaize], [etilong], [etirayon], [etiperfo],
               [modlaize], [modlong], [nbfront],
               [lateral_ext], [horizontal], [lateral_int],
               [outil], [outilnumerosifa], [laizecoupant], [machine],
               [outil_epaisseur], [nbdents], [outilnbfront], [outilnbavance],
               [outil2], [outilnumerosifa2], [outil_epaisseur2],
               [nbdents2], [outilnbfront2], [outilnbavance2],
               [outil3], [outilnumerosifa3], [outil_epaisseur3],
               [nbdents3], [outilnbfront3], [outilnbavance3],
               [matsupport], [matglassine], [matlaizestandard], [matlaize],
               [protect_epaisseur], [matadhesif], [matquantite],
               [nbcouleurs], [recto], [verso],
               [pant1], [anilox1], [composition1],
               [pant2], [anilox2], [composition2],
               [pant3], [anilox3], [composition3],
               [remarques],
               [mandrin_diametre], [mandrin_longueur], [enroulement],
               [nbetiquette], [diametreext], [poids],
               [miseboite], [cales_sachets], [dimensions_carton],
               [nb_au_sol], [nb_etag], [bob_carton],
               [palettisation_type], [palettisation_nb_sol],
               [palettisation_nb_hauteur], [palettisation_hauteur_max],
               [particularites]
        FROM   [{TABLE_NAME}]
        ORDER  BY [modif] ASC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


# ── Mapping Access → payload API ─────────────────────────────────────

def build_payload(row) -> dict:
    return {
        "reference":              s(row.reference),
        "date_modif":             fmt_date(row.modif),
        "format":                 s(row.format),
        # Étiquette
        "eti_laize":              f(row.etilaize),
        "eti_longueur":           f(row.etilong),
        "eti_rayons":             f(row.etirayon),
        "eti_perforations":       s(row.etiperfo),
        # Module
        "mod_laize":              f(row.modlaize),
        "mod_longueur":           f(row.modlong),
        "mod_nb_front":           i(row.nbfront),
        # Échenillage
        "lateral_ext":            f(row.lateral_ext),
        "horizontal":             f(row.horizontal),
        "lateral_int":            f(row.lateral_int),
        # Outil 1
        "outil1_forme":           s(row.outil),
        "outil1_numero_sifa":     s(row.outilnumerosifa),
        "outil1_laize":           f(row.laizecoupant),
        "machine":                s(row.machine),
        "outil1_epaisseur":       f(row.outil_epaisseur),
        "outil1_nb_dents":        i(row.nbdents),
        "outil1_nb_front":        i(row.outilnbfront),
        "outil1_nb_avance":       i(row.outilnbavance),
        # Outil 2
        "outil2_forme":           s(row.outil2),
        "outil2_numero_sifa":     s(row.outilnumerosifa2),
        "outil2_epaisseur":       f(row.outil_epaisseur2),
        "outil2_nb_dents":        i(row.nbdents2),
        "outil2_nb_front":        i(row.outilnbfront2),
        "outil2_nb_avance":       i(row.outilnbavance2),
        # Outil 3
        "outil3_forme":           s(row.outil3),
        "outil3_numero_sifa":     s(row.outilnumerosifa3),
        "outil3_epaisseur":       f(row.outil_epaisseur3),
        "outil3_nb_dents":        i(row.nbdents3),
        "outil3_nb_front":        i(row.outilnbfront3),
        "outil3_nb_avance":       i(row.outilnbavance3),
        # Matière
        "support":                s(row.matsupport),
        "glassine":               s(row.matglassine),
        "laize_optimale":         f(row.matlaizestandard),
        "laize_optionnelle":      f(row.matlaize),
        "epaisseur":              f(row.protect_epaisseur),
        "adhesif":                s(row.matadhesif),
        "qte_au_mille":           f(row.matquantite),
        # Impression
        "nb_couleurs":            i(row.nbcouleurs),
        "recto":                  i(row.recto),
        "verso":                  i(row.verso),
        "tete1_pantone":          s(row.pant1),
        "tete1_anilox":           s(row.anilox1),
        "tete1_composition":      s(row.composition1),
        "tete2_pantone":          s(row.pant2),
        "tete2_anilox":           s(row.anilox2),
        "tete2_composition":      s(row.composition2),
        "tete3_pantone":          s(row.pant3),
        "tete3_anilox":           s(row.anilox3),
        "tete3_composition":      s(row.composition3),
        "remarque":               s(row.remarques),
        # Conditionnement
        "mandrin_dia":            s(row.mandrin_diametre),
        "mandrin_longueur":       f(row.mandrin_longueur),
        "enroulement":            s(row.enroulement),
        "nb_etiq_bobin":          i(row.nbetiquette),
        "dia_ext":                f(row.diametreext),
        "poids":                  f(row.poids),
        "conditionnement":        s(row.miseboite),
        "cales_sachets":          s(row.cales_sachets),
        "cartons":                s(row.dimensions_carton),
        "nb_au_sol":              i(row.nb_au_sol),
        "nb_etage":               i(row.nb_etag),
        "nb_bobines_carton":      i(row.bob_carton),
        # Palettisation
        "palette_type":               s(row.palettisation_type),
        "palette_nb_cartons_sol":     i(row.palettisation_nb_sol),
        "palette_nb_cartons_hauteur": i(row.palettisation_nb_hauteur),
        "palette_hauteur_max":        f(row.palettisation_hauteur_max),
        "particularite":              s(row.particularites),
    }


# ── Push vers MySifa ──────────────────────────────────────────────────

def push_fiche(payload: dict) -> dict:
    resp = requests.post(
        f"{MYSIFA_BASE_URL}/api/bridge/fiche-technique",
        json=payload,
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


# ── Main ─────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Synchronisation Access → MySifa (fiches techniques).")
    ap.add_argument("--tout", action="store_true",
                    help="Renvoyer toutes les fiches, même celles dont l'empreinte n'a pas changé.")
    ap.add_argument("--ref", metavar="REFERENCE",
                    help="Ne traiter que les fiches dont la référence contient ce texte.")
    args = ap.parse_args()

    if not MYSIFA_API_KEY:
        print("Clé API absente. Définir la variable d'environnement MYSIFA_API_KEY :")
        print('  setx MYSIFA_API_KEY "msk_..."   puis rouvrir le terminal.')
        return
    empreintes = lire_empreintes()
    print(f"Connexion à Access : {ACCESS_DB_PATH}")
    print(f"Table             : {TABLE_NAME}")
    if not empreintes:
        print("Aucune empreinte enregistrée : toutes les fiches seront envoyées.")

    rows = get_access_fiches()
    print(f"{len(rows)} fiche(s) lue(s) dans Access.\n")

    created = updated = errors = conflits = devalides = identiques = 0
    a_envoyer = 0

    for row in rows:
        ref = s(row.reference) or "???"
        try:
            payload = build_payload(row)
            if not payload.get("reference"):
                continue
            if args.ref and args.ref.lower() not in payload["reference"].lower():
                continue
            cle = cle_ref(payload["reference"])
            emp = empreinte(payload)
            if not args.tout and empreintes.get(cle) == emp:
                continue
            a_envoyer += 1
            result = push_fiche(payload)
            action = result.get("action", "?")
            fid    = result.get("id", "?")
            if action == "created":
                print(f"  [CRÉÉ]    {ref} → id MySifa : {fid}")
                created += 1
            elif action == "unchanged":
                identiques += 1
            else:
                champs = ", ".join(result.get("fields") or [])
                print(f"  [MIS À JOUR] {ref} → {champs or 'aucun champ'} (id : {fid})")
                updated += 1
            # Une valeur saisie à la main dans MySifa n'est plus écrasée. Le
            # conflit est signalé ici et consultable dans MyStock : c'est un
            # désaccord entre deux bases, pas un non-événement.
            for c in result.get("conflits") or []:
                print(f"  [CONFLIT] {ref} → {c.get('libelle', c.get('champ'))} : "
                      f"MySifa {c.get('actuel')!r} ≠ Access {c.get('propose')!r} "
                      f"(saisie manuelle conservée)")
                conflits += 1
            if result.get("validation_retiree"):
                print(f"            ↳ {result.get('motif_validation')} "
                      f"Fiche à revalider dans MyStock avant tout déstockage.")
                devalides += 1
            # L'empreinte n'est retenue qu'après un envoi réussi : une erreur
            # réseau fait simplement repartir la fiche au passage suivant.
            empreintes[cle] = emp
        except requests.HTTPError as e:
            print(f"  [ERREUR]  {ref} → HTTP {e.response.status_code} : {e.response.text[:120]}")
            errors += 1
        except Exception as e:
            print(f"  [ERREUR]  {ref} → {e}")
            errors += 1

    print(f"\nRésultat — Envoyées : {a_envoyer}  |  Créées : {created}  |  "
          f"Mises à jour : {updated}  |  Déjà identiques : {identiques}  |  "
          f"Conflits : {conflits}  |  Validations retirées : {devalides}  |  "
          f"Erreurs : {errors}")

    ecrire_empreintes(empreintes)
    save_date_depuis()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompu.")

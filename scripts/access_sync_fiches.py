"""
Synchronisation Access → MySifa : fiches techniques
----------------------------------------------------
Lit les fiches modifiées après le dernier sync depuis sifa_fiches_techniques.mdb
et les pousse vers MySifa via l'API bridge (upsert par référence).

Dépendances :
    pip install pyodbc requests

Configuration :
    Adapter ACCESS_DB_PATH, TABLE_NAME et MYSIFA_API_KEY ci-dessous.
"""
import pyodbc
import requests
from datetime import datetime

# ── Configuration ────────────────────────────────────────────────────
ACCESS_DB_PATH  = r"\\IDEFIX\sifa_pub\Fiches techniques Access\sifa_fiches_techniques.mdb"
LAST_RUN_FILE   = r"\\IDEFIX\sifa_pub\Fiches techniques Access\last_sync_fiches.txt"
TABLE_NAME      = "fiches_techniques"
MYSIFA_BASE_URL = "https://mysifa.com"
MYSIFA_API_KEY  = "msk_b5ffcec1a8d91e7f46a6bcfe305360f704d6da503f37d5e9fadd31421f47e83d"
DATE_FALLBACK   = "2025-01-01"     # première sync : fiches depuis 2025

HEADERS = {
    "X-Api-Key":    MYSIFA_API_KEY,
    "Content-Type": "application/json",
}

CONN_STR = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    f"DBQ={ACCESS_DB_PATH};"
)

# ── Helpers date ─────────────────────────────────────────────────────

def get_date_depuis() -> str:
    try:
        with open(LAST_RUN_FILE) as f:
            return f.read().strip()
    except FileNotFoundError:
        return DATE_FALLBACK

def save_date_depuis():
    with open(LAST_RUN_FILE, "w") as f:
        f.write(datetime.now().strftime("%Y-%m-%d"))

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

def get_access_fiches(date_depuis: str) -> list:
    conn = pyodbc.connect(CONN_STR)
    cur  = conn.cursor()
    # Filtre sur `modif` (date de dernière modification)
    # Si ta table n'a pas de champ modif, remplace par date_creation
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
        WHERE  [modif] > ?
        ORDER  BY [modif] ASC
        """,
        (date_depuis,)
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
    date_depuis = get_date_depuis()
    print(f"Connexion à Access : {ACCESS_DB_PATH}")
    print(f"Table             : {TABLE_NAME}")
    print(f"Fiches depuis le  : {date_depuis}\n")

    rows = get_access_fiches(date_depuis)
    print(f"{len(rows)} fiche(s) trouvée(s).\n")

    created = 0
    updated = 0
    errors  = 0

    for row in rows:
        ref = s(row.reference) or "???"
        try:
            payload = build_payload(row)
            if not payload.get("reference"):
                print(f"  [IGNORÉ]  fiche sans référence — ignorée")
                continue
            result = push_fiche(payload)
            action = result.get("action", "?")
            fid    = result.get("id", "?")
            if action == "created":
                print(f"  [CRÉÉ]    {ref} → id MySifa : {fid}")
                created += 1
            else:
                print(f"  [MIS À JOUR] {ref} → id MySifa : {fid}")
                updated += 1
        except requests.HTTPError as e:
            print(f"  [ERREUR]  {ref} → HTTP {e.response.status_code} : {e.response.text[:120]}")
            errors += 1
        except Exception as e:
            print(f"  [ERREUR]  {ref} → {e}")
            errors += 1

    print(f"\nRésultat — Créées : {created}  |  Mises à jour : {updated}  |  Erreurs : {errors}")

    if created + updated > 0:
        save_date_depuis()
        print(f"Date de dernier sync mise à jour : {datetime.now().strftime('%Y-%m-%d')}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompu.")

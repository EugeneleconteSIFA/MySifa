"""
Synchronisation Access → MySifa : table t_of
--------------------------------------------
Ce script lit les OFs créés après le 01/11/2025 dans la base Access
et les pousse vers MySifa via l'API bridge.

Un OF déjà présent dans MySifa (même numero_of) est ignoré — pas d'écrasement.

Dépendances :
    pip install pyodbc requests

Configuration :
    Renseigner ACCESS_DB_PATH et MYSIFA_API_KEY ci-dessous.
    MYSIFA_BASE_URL : URL du VPS sans slash final.
"""

import pyodbc
import requests
from datetime import datetime

# ── Configuration ────────────────────────────────────────────────────
ACCESS_DB_PATH  = r"\\IDEFIX\sifa_pub\Fiches techniques Access\of.mdb"
MYSIFA_BASE_URL = "https://mysifa.com"
MYSIFA_API_KEY  = "msk_REMPLACER_PAR_NOUVELLE_CLE"    # ← générer dans /settings > Clés API

DATE_DEPUIS     = "2025-11-01"   # OFs créés strictement après cette date

HEADERS = {
    "X-Api-Key":    MYSIFA_API_KEY,
    "Content-Type": "application/json",
}

# ── Connexion Access ─────────────────────────────────────────────────
CONN_STR = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    f"DBQ={ACCESS_DB_PATH};"
)


def get_access_of():
    """Lit les OFs de t_of créés après DATE_DEPUIS."""
    conn = pyodbc.connect(CONN_STR)
    cur  = conn.cursor()
    cur.execute(
        """
        SELECT [id_of],
               [numero_of],
               [date_creation],
               [format],
               [theorique_quantite],
               [theorique_quantite_bobines]
        FROM   [t_of]
        WHERE  [date_creation] > ?
        ORDER  BY [date_creation] ASC
        """,
        (DATE_DEPUIS,)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def format_date(val) -> str | None:
    """Convertit une date Access (datetime ou string) en 'YYYY-MM-DD'."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.strftime("%Y-%m-%d")
    try:
        # Access stocke parfois en string "DD/MM/YYYY"
        return datetime.strptime(str(val).strip(), "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        return str(val).strip()[:10]  # tronquer si déjà ISO


def push_of(row) -> dict:
    """Envoie un OF vers MySifa. Retourne la réponse JSON."""
    payload = {
        "numero_of":      str(row.numero_of).strip(),
        "date_creation":  format_date(row.date_creation),
        "format":         str(row.format).strip() if row.format else None,
        "qte_etiquettes": float(row.theorique_quantite)        if row.theorique_quantite        is not None else None,
        "qte_bobines":    float(row.theorique_quantite_bobines) if row.theorique_quantite_bobines is not None else None,
    }
    resp = requests.post(
        f"{MYSIFA_BASE_URL}/api/bridge/of",
        json=payload,
        headers=HEADERS,
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    print(f"Connexion à Access : {ACCESS_DB_PATH}")
    rows = get_access_of()
    print(f"{len(rows)} OF(s) trouvé(s) après le {DATE_DEPUIS}.\n")

    inserted = 0
    skipped  = 0
    errors   = 0

    for row in rows:
        numero = str(row.numero_of).strip()
        try:
            result = push_of(row)
            if result.get("inserted"):
                print(f"  [OK]     OF {numero} → importé (id MySifa : {result['id']})")
                inserted += 1
            else:
                print(f"  [IGNORÉ] OF {numero} → déjà dans MySifa (id : {result['id']})")
                skipped += 1
        except requests.HTTPError as e:
            print(f"  [ERREUR] OF {numero} → HTTP {e.response.status_code} : {e.response.text[:120]}")
            errors += 1
        except Exception as e:
            print(f"  [ERREUR] OF {numero} → {e}")
            errors += 1

    print(f"\nRésultat — Importés : {inserted}  |  Ignorés (déjà présents) : {skipped}  |  Erreurs : {errors}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompu.")

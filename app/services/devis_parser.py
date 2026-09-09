"""
SIFA — Parser de devis Excel (chemin rapide, sans IA).

Ce module lit les classeurs dont la disposition est celle du modèle maison :
une feuille « Calculs » et une feuille « Prix », des libellés reconnaissables,
la valeur immédiatement à droite du libellé. Il est gratuit et instantané, et
il couvre la majorité des devis.

Il ne couvre PAS les classeurs des commerciaux qui devisent autrement. Quand
un champ clé ressort vide, l'appelant (`app/services/devis_extraction.py`)
bascule sur l'extraction IA. Ce parser n'a donc pas à deviner : il rend ce
qu'il reconnaît, et il DIT d'où il l'a tiré (`sources`), pour que l'écran de
validation puisse afficher « Calculs!I2 » à côté de la valeur.

Deux pièges corrigés ici, qui rendaient tout import silencieusement vide :

1. `pd.ExcelFile(file_bytes)` lève `Expected file path name or file-like
   object, got <class 'bytes'>`. L'exception était avalée par le `try` et
   remontait comme un simple avertissement : chaque devis importé arrivait
   avec des zéros partout, sans que rien ne signale l'échec.
2. Un même tampon ne se relit pas trois fois sans `seek(0)`. Le classeur est
   donc ouvert UNE fois et les feuilles utiles sont mises en cache.

`.xls` : lu par python-calamine, pas par xlrd (absent des dépendances).
"""
import io
import re
from typing import Any, Optional

import pandas as pd

try:  # openpyxl est une dépendance dure, mais on ne casse pas l'import pour ça
    from openpyxl.utils import get_column_letter
except Exception:  # pragma: no cover
    def get_column_letter(idx: int) -> str:
        return str(idx)


# Champs sans lesquels une comparaison devis/réel n'a aucun sens. Si l'un
# d'eux manque, l'appelant déclenche l'IA. Volontairement court : la vitesse,
# les deux temps, les deux métrages et la quantité — le reste est du confort.
CHAMPS_CLES = (
    "vitesse_theorique",
    "temps_production_mn",
    "metrage_production_ml",
    "qte_etiquettes",
    "temps_calage_mn",
)

CHAMPS_NUMERIQUES = (
    "format_h", "format_v", "laize", "nb_couleurs",
    "temps_calage_mn", "metrage_calage_ml",
    "temps_production_mn", "metrage_production_ml",
    "vitesse_theorique", "qte_etiquettes", "gache",
)


def gabarit_devis(filename: str = "") -> dict:
    """Le dictionnaire de sortie, tous champs à vide. Une seule définition."""
    return {
        "filename":              filename,
        "client":               None,
        "date_devis":           None,
        "format_h":             None,
        "format_v":             None,
        "laize":                None,
        "nb_couleurs":          0,
        "temps_calage_mn":      0.0,
        "metrage_calage_ml":    0.0,
        "temps_production_mn":  0.0,
        "metrage_production_ml": 0.0,
        "vitesse_theorique":    0.0,
        "qte_etiquettes":       0.0,
        "gache":                0.0,
        "parse_errors":         [],
    }


def champ_vide(valeur: Any) -> bool:
    """Un champ « non trouvé » : None, chaîne vide, ou zéro numérique."""
    if valeur is None:
        return True
    if isinstance(valeur, str):
        return not valeur.strip()
    try:
        return float(valeur) == 0.0
    except (TypeError, ValueError):
        return False


def champs_cles_manquants(donnees: dict) -> list[str]:
    return [c for c in CHAMPS_CLES if champ_vide(donnees.get(c))]


def _coord(sheet: str, row_idx: int, col_idx: int) -> str:
    """« Calculs!I2 » — la référence telle qu'un humain la retrouve dans Excel."""
    return f"{sheet}!{get_column_letter(col_idx + 1)}{row_idx + 1}"


def _find_value(df, label_pattern, col_offset=1, sheet_name=""):
    """Cherche un libellé par regex et retourne la valeur voisine.

    Retourne `(valeur, coordonnée)` — la coordonnée est celle de la VALEUR,
    pas du libellé : c'est la cellule que l'utilisateur ira vérifier.
    """
    for row_idx in range(len(df)):
        for col_idx in range(len(df.columns)):
            cell = df.iloc[row_idx, col_idx]
            if pd.isna(cell):
                continue
            if re.search(label_pattern, str(cell), re.IGNORECASE):
                target_col = col_idx + col_offset
                if target_col < len(df.columns):
                    val = df.iloc[row_idx, target_col]
                    if not pd.isna(val):
                        return val, _coord(sheet_name, row_idx, target_col)
                # Certains classeurs posent la valeur SOUS le libellé.
                if row_idx + 1 < len(df):
                    val = df.iloc[row_idx + 1, col_idx]
                    if not pd.isna(val):
                        return val, _coord(sheet_name, row_idx + 1, col_idx)
    return None, None


def _safe_float(val, default=0.0):
    try:
        return float(val) if val is not None and not pd.isna(val) else default
    except (ValueError, TypeError):
        return default


def _moteur(filename: str) -> str:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "xlsx"
    # xlrd n'est pas installé : les .xls passent par calamine, qui lit les deux
    # formats. openpyxl reste le moteur des .xlsx (meilleur support des
    # formules mises en cache).
    return "calamine" if ext == "xls" else "openpyxl"


def charger_feuilles(file_bytes: bytes, filename: str) -> tuple[dict, list[str]]:
    """Ouvre le classeur UNE fois et rend `{nom_feuille: DataFrame}`.

    Le tampon est rembobiné entre chaque feuille : sans ça, la deuxième
    lecture rend un DataFrame vide sans lever d'erreur.
    """
    erreurs: list[str] = []
    moteur = _moteur(filename)
    try:
        buf = io.BytesIO(file_bytes)
        xl = pd.ExcelFile(buf, engine=moteur)
        noms = list(xl.sheet_names)
    except Exception as e:
        return {}, [f"Impossible d'ouvrir le fichier : {e}"]

    feuilles: dict[str, Any] = {}
    for nom in noms:
        try:
            buf.seek(0)
            feuilles[nom] = pd.read_excel(buf, sheet_name=nom, header=None,
                                          engine=moteur)
        except Exception as e:
            erreurs.append(f"Feuille « {nom} » illisible : {e}")
    return feuilles, erreurs


def parse_devis(file_bytes: bytes, filename: str) -> dict:
    """Parse un devis Excel au format maison.

    Rend le gabarit complet, plus `sources` : `{champ: "Feuille!Cellule"}`
    pour chaque champ effectivement trouvé.
    """
    result = gabarit_devis(filename)
    result["sources"] = {}

    if isinstance(file_bytes, (io.BytesIO, io.BufferedReader)):
        file_bytes = file_bytes.read()

    feuilles, erreurs = charger_feuilles(file_bytes, filename)
    result["parse_errors"].extend(erreurs)
    if not feuilles:
        return result

    def poser(champ: str, valeur, coord, transform=None):
        if valeur is None:
            return
        result[champ] = transform(valeur) if transform else valeur
        if coord:
            result["sources"][champ] = coord

    def chercher(df, nom, motif, offset=1):
        return _find_value(df, motif, col_offset=offset, sheet_name=nom)

    # ── Feuille Prix ──────────────────────────────────────────────
    nom_prix = next((s for s in feuilles if "prix" in s.lower()), None)
    df_prix = feuilles.get(nom_prix) if nom_prix else None
    if df_prix is not None:
        try:
            v, c = chercher(df_prix, nom_prix, r"nom.du.client|client")
            if v is not None:
                poser("client", str(v).strip(), c)

            v, c = chercher(df_prix, nom_prix, r"^date\s*:")
            if v is not None:
                d = v.strftime("%Y-%m-%d") if hasattr(v, "strftime") else str(v)[:10]
                poser("date_devis", d, c)

            v, c = chercher(df_prix, nom_prix, r"format.hauteur|dim.h")
            poser("format_h", v, c, _safe_float)

            v, c = chercher(df_prix, nom_prix, r"format.laize|format.v\b|dim.v")
            poser("format_v", v, c, _safe_float)

            v, c = chercher(df_prix, nom_prix, r"laize.production|laize.prod")
            poser("laize", v, c, _safe_float)

            # Le nombre de couleurs vaut 1,5 quand un poste tourne en demi-teinte :
            # `int()` le ramenait à 1 et faussait le calage devisé. On garde le réel.
            v, c = chercher(df_prix, nom_prix, r"nbre.couleurs|nb.couleurs|nombre.couleurs")
            poser("nb_couleurs", v, c, _safe_float)

            # La gâche vit sur la feuille Prix dans le modèle maison, pas sur
            # Calculs — la chercher uniquement sur Calculs la rendait toujours nulle.
            v, c = chercher(df_prix, nom_prix, r"^\s*g[aâ]che\s*$")
            poser("gache", v, c, _safe_float)
        except Exception as e:
            result["parse_errors"].append(f"Erreur feuille Prix : {e}")

    # ── Feuille Calculs ───────────────────────────────────────────
    nom_calc = next((s for s in feuilles if "calcul" in s.lower()), None)
    df_calc = feuilles.get(nom_calc) if nom_calc else None
    if df_calc is not None:
        try:
            v, c = chercher(df_calc, nom_calc, r"temps.calage.outil|temps.calage$")
            if v is None:
                v, c = chercher(df_calc, nom_calc, r"calage.outil")
            poser("temps_calage_mn", v, c, _safe_float)

            v, c = chercher(df_calc, nom_calc, r"metrage.calage|métrage.calage")
            poser("metrage_calage_ml", v, c, _safe_float)

            v, c = chercher(df_calc, nom_calc, r"qte.d.etiquettes|quantit..*tiquet|qte.etiquet")
            poser("qte_etiquettes", v, c, _safe_float)

            v, c = chercher(df_calc, nom_calc, r"temps.production|tps.production")
            poser("temps_production_mn", v, c, _safe_float)

            v, c = chercher(df_calc, nom_calc, r"metrage.lin|métrage.lin|metrage.utilise.*ml|metrage.production")
            if v is None:
                v, c = chercher(df_calc, nom_calc, r"metrage.utilise")
            poser("metrage_production_ml", v, c, _safe_float)

            v, c = chercher(df_calc, nom_calc, r"vitesse.prd|vitesse.prod|vitesse.moy")
            poser("vitesse_theorique", v, c, _safe_float)

            if champ_vide(result["gache"]):
                v, c = chercher(df_calc, nom_calc, r"g.che$|gache$|gâche$")
                if v is None:
                    v, c = chercher(df_calc, nom_calc, r"g.che|gache|gâche")
                poser("gache", v, c, _safe_float)
        except Exception as e:
            result["parse_errors"].append(f"Erreur feuille Calculs : {e}")
    else:
        result["parse_errors"].append("Feuille « Calculs » introuvable")

    return result

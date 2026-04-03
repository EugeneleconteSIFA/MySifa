"""
SIFA — Parser de devis Excel
Extrait les données de production des feuilles Calculs et Prix.
Compatible .xlsx et .xls
"""
import re
import pandas as pd
from typing import Optional


def _find_value(df, label_pattern, col_offset=1, search_cols=None):
    """
    Cherche une valeur dans un DataFrame en cherchant un label par regex.
    Retourne la valeur dans la colonne col_offset à droite du label trouvé.
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
                        return val
                # Chercher dans la ligne suivante
                if row_idx + 1 < len(df):
                    val = df.iloc[row_idx + 1, col_idx]
                    if not pd.isna(val):
                        return val
    return None


def _safe_float(val, default=0.0):
    try:
        return float(val) if val is not None and not pd.isna(val) else default
    except (ValueError, TypeError):
        return default


def parse_devis(file_bytes: bytes, filename: str) -> dict:
    """
    Parse un fichier devis Excel (.xlsx ou .xls).
    Retourne un dict avec toutes les données extraites.
    """
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else "xlsx"
    engine = "xlrd" if ext == "xls" else "openpyxl"

    result = {
        "filename":             filename,
        "client":               None,
        "date_devis":           None,
        "format_h":             None,
        "format_v":             None,
        "laize":                None,
        "nb_couleurs":          0,
        "temps_calage_mn":      0.0,
        "metrage_calage_ml":    0.0,
        "temps_production_mn":  0.0,
        "metrage_production_ml":0.0,
        "vitesse_theorique":    0.0,
        "qte_etiquettes":       0.0,
        "gache":                0.0,
        "parse_errors":         [],
    }

    try:
        xl = pd.ExcelFile(file_bytes, engine=engine)
    except Exception as e:
        result["parse_errors"].append(f"Impossible d'ouvrir le fichier : {e}")
        return result

    sheets = xl.sheet_names

    # ── Feuille Prix ──────────────────────────────────────────────
    prix_names = [s for s in sheets if "prix" in s.lower()]
    if prix_names:
        try:
            df_prix = pd.read_excel(file_bytes, sheet_name=prix_names[0],
                                    header=None, engine=engine)

            # Client
            client_val = _find_value(df_prix, r"nom.du.client|client", col_offset=1)
            if client_val:
                result["client"] = str(client_val).strip()

            # Date
            date_val = _find_value(df_prix, r"^date\s*:", col_offset=1)
            if date_val:
                if hasattr(date_val, 'strftime'):
                    result["date_devis"] = date_val.strftime("%Y-%m-%d")
                else:
                    result["date_devis"] = str(date_val)[:10]

            # Format H x V
            format_h = _find_value(df_prix, r"format.hauteur|dim.h", col_offset=1)
            format_v = _find_value(df_prix, r"format.v|dim.v", col_offset=1)
            if format_h is None:
                # Chercher la valeur numérique après "FORMAT HAUTEUR"
                for _, row in df_prix.iterrows():
                    vals = [v for v in row if not pd.isna(v) and str(v).strip()]
                    for i, v in enumerate(vals):
                        if re.search(r'format.hauteur', str(v), re.IGNORECASE):
                            if i + 1 < len(vals):
                                format_h = vals[i + 1]
            result["format_h"] = _safe_float(format_h)
            result["format_v"] = _safe_float(format_v)

            # Laize production
            laize = _find_value(df_prix, r"laize.production|laize.prod", col_offset=1)
            result["laize"] = _safe_float(laize)

            # Nombre de couleurs
            nb_coul = _find_value(df_prix, r"nbre.couleurs|nb.couleurs|nombre.couleurs", col_offset=1)
            result["nb_couleurs"] = int(_safe_float(nb_coul))

        except Exception as e:
            result["parse_errors"].append(f"Erreur feuille Prix : {e}")

    # ── Feuille Calculs ───────────────────────────────────────────
    calc_names = [s for s in sheets if "calcul" in s.lower()]
    if calc_names:
        try:
            df_calc = pd.read_excel(file_bytes, sheet_name=calc_names[0],
                                    header=None, engine=engine)

            # Temps calage outil (mn)
            tps_calage = _find_value(df_calc, r"temps.calage.outil|temps.calage$", col_offset=1)
            if tps_calage is None:
                tps_calage = _find_value(df_calc, r"calage.outil", col_offset=1)
            result["temps_calage_mn"] = _safe_float(tps_calage)

            # Métrage calage (ml)
            met_calage = _find_value(df_calc, r"metrage.calage|métrage.calage", col_offset=1)
            result["metrage_calage_ml"] = _safe_float(met_calage)

            # Quantité étiquettes
            qte = _find_value(df_calc, r"qte.d.etiquettes|quantit..*tiquet|qte.etiquet", col_offset=1)
            result["qte_etiquettes"] = _safe_float(qte)

            # Temps production (mn)
            tps_prod = _find_value(df_calc, r"temps.production|tps.production", col_offset=1)
            result["temps_production_mn"] = _safe_float(tps_prod)

            # Métrage linéaire production (ml)
            met_prod = _find_value(df_calc, r"metrage.lin|métrage.lin|metrage.utilise.*ml|metrage.production", col_offset=1)
            if met_prod is None:
                met_prod = _find_value(df_calc, r"metrage.utilise", col_offset=1)
            result["metrage_production_ml"] = _safe_float(met_prod)

            # Vitesse production (m/mn)
            vitesse = _find_value(df_calc, r"vitesse.prd|vitesse.prod|vitesse.moy", col_offset=1)
            result["vitesse_theorique"] = _safe_float(vitesse)

            # Gâche (%)
            gache = _find_value(df_calc, r"g.che$|gache$|gâche$", col_offset=1)
            if gache is None:
                gache = _find_value(df_calc, r"g.che|gache|gâche", col_offset=1)
            result["gache"] = _safe_float(gache)

        except Exception as e:
            result["parse_errors"].append(f"Erreur feuille Calculs : {e}")
    else:
        result["parse_errors"].append("Feuille 'Calculs' introuvable")

    return result


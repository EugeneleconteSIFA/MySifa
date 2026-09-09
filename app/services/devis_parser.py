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
    "temps_calage_impression_mn", "metrage_calage_impression_ml",
    "temps_production_mn", "metrage_production_ml",
    "vitesse_theorique", "qte_etiquettes", "gache",
)


# Indicateurs hors socle que le modèle maison porte à des libellés stables.
# Les lire ici évite un appel au modèle pour des chiffres qu'un motif trouve.
# Format : (feuille, motif, libellé affiché, unité, décalage de colonne).
# Le décalage vaut 3 quand le classeur pose le temps en J et le métrage en L
# sur la ligne d'un même libellé (bloc « CALCUL Temps et métrage »).
INDICATEURS_MAISON = (
    ("prix", r"nombre\s+front", "Nombre de fronts", "", 1),
    ("prix", r"nbre\s+total\s+poses", "Nombre total de poses", "", 1),
    ("prix", r"pas\s+developpe|pas\s+développé", "Pas développé", "mm", 1),
    ("prix", r"laize\s+mini", "Laize mini", "mm", 1),
    ("prix", r"nb\s+etiquettes?\s+au\s+rouleau", "Étiquettes par rouleau", "ex", 1),
    ("prix", r"^prix\s+au\s+mille\s*:", "Prix au mille", "€", 1),
    ("prix", r"^s/?\s*total$", "Temps total devisé", "mn", 1),
    ("prix", r"^s/?\s*total$", "Métrage total devisé", "ml", 3),
    ("prix", r"^conditionnement$", "Temps de conditionnement", "mn", 1),
    ("prix", r"^g[aâ]che\s*$", "Métrage de gâche", "ml", 3),
    ("calculs", r"nbre\s+bobine\s+theo", "Bobines théoriques", "", 1),
    ("calculs", r"nombre\s+outil", "Nombre d'outils", "", 1),
    ("calculs", r"metrage\s+outil", "Métrage outil", "ml", 1),
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
        # Second poste de calage, distinct dans le devis mais NON distinct dans
        # la saisie atelier : les changements de couleur (op. 12) et de cliché
        # (op. 75) tombent dans la catégorie « calage » de MyProd comme le
        # calage outil. Le devis doit donc être comparé sur la somme des deux.
        "temps_calage_impression_mn":   0.0,
        "metrage_calage_impression_ml": 0.0,
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


def _valeur_a_gauche(df, sheet_name: str, label_pattern: str):
    """Première cellule numérique à GAUCHE d'un libellé, sur sa ligne.

    Repli de position, à n'utiliser qu'après l'échec d'une recherche par
    libellé : il suppose une disposition, il ne lit pas une intention. Toute
    valeur qui en sort doit sortir en confiance dégradée.
    """
    for row_idx in range(len(df)):
        for col_idx in range(len(df.columns)):
            cell = df.iloc[row_idx, col_idx]
            if pd.isna(cell):
                continue
            if not re.search(label_pattern, str(cell), re.IGNORECASE):
                continue
            for gauche in range(col_idx - 1, -1, -1):
                val = df.iloc[row_idx, gauche]
                if pd.isna(val):
                    continue
                try:
                    float(val)
                except (TypeError, ValueError):
                    return None, None  # un texte à gauche : on n'insiste pas
                return val, _coord(sheet_name, row_idx, gauche)
            return None, None
    return None, None


def paliers_quantite(df, sheet_name: str) -> list[dict]:
    """Le bloc « Descriptif de la cde » : les quantités chiffrées et leur prix.

    Pourquoi ce bloc compte. Un devis ne chiffre pas UNE quantité, il en
    chiffre plusieurs — le client demande le prix à 984 000, à 1 135 000 et à
    2 111 900, le commercial les met en regard. Les feuilles Calculs et Prix,
    elles, ne calculent le temps et le métrage QUE pour une seule de ces
    quantités, et rien dans le classeur ne dit laquelle a été commandée.

    Sur le devis « RONDS », les calculs portent sur 14 400 000 exemplaires
    alors que le nom du fichier annonce 29 000 000 : comparer la production
    réelle d'une commande de 29 millions à un devis calculé pour 14,4 millions
    double l'écart sans qu'aucun chiffre soit faux. On relève donc les paliers,
    et l'écran de validation pose la question au lieu de trancher tout seul.
    """
    ligne_entete = None
    col_qte = col_prix = None
    for row_idx in range(len(df)):
        cols_qte = []
        cols_prix = []
        for col_idx in range(len(df.columns)):
            cell = df.iloc[row_idx, col_idx]
            if pd.isna(cell):
                continue
            txt = str(cell).strip().lower()
            if re.match(r"^quantit", txt):
                cols_qte.append(col_idx)
            elif re.search(r"prix.*(ht.*)?mille", txt):
                cols_prix.append(col_idx)
        if cols_qte and cols_prix:
            ligne_entete, col_qte, col_prix = row_idx, cols_qte[0], cols_prix[0]
            break
    if ligne_entete is None:
        return []

    paliers: list[dict] = []
    vides = 0
    for row_idx in range(ligne_entete + 1, min(ligne_entete + 10, len(df))):
        qte = df.iloc[row_idx, col_qte] if col_qte < len(df.columns) else None
        try:
            qte = float(qte) if not pd.isna(qte) else None
        except (TypeError, ValueError):
            qte = None
        if qte is None or qte <= 0:
            vides += 1
            if vides >= 2:
                break
            continue
        vides = 0
        prix = None
        source_prix = ""
        if col_prix < len(df.columns):
            try:
                v = df.iloc[row_idx, col_prix]
                if not pd.isna(v):
                    prix = float(v)
                    # La coordonnée du PRIX, pas celle de la quantité : chaque
                    # valeur cite la cellule qui la contient, sans quoi la
                    # provenance affichée à l'écran est fausse.
                    source_prix = _coord(sheet_name, row_idx, col_prix)
            except (TypeError, ValueError):
                prix = None
                source_prix = ""
        note = ""
        if col_prix + 1 < len(df.columns):
            v = df.iloc[row_idx, col_prix + 1]
            if not pd.isna(v) and not isinstance(v, (int, float)):
                note = str(v).strip()
        paliers.append({
            "quantite": qte,
            "prix_mille": prix,
            "note": note,
            "source": _coord(sheet_name, row_idx, col_qte),
            "source_prix": source_prix,
        })
    return paliers


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
    # Confiance dégradée pour les valeurs obtenues par repli de position.
    result["confiances"] = {}

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

            # « FORMAT               LAIZE : » — le classeur maison aligne le
            # libellé à la colonne avec des espaces. Un motif à un caractère
            # (`format.laize`) ne les traverse pas et laissait la laize vide.
            v, c = chercher(df_prix, nom_prix, r"format[\s.:]*laize|dim[\s.:]*v\b")
            poser("format_v", v, c, _safe_float)

            # Repli géométrique. Sur deux des trois devis de référence, le
            # libellé « FORMAT LAIZE » a disparu de la feuille : il ne reste
            # que la valeur, seule dans sa cellule à gauche de « FORMAT
            # HAUTEUR », sur la même ligne. On la prend — mais en confiance
            # « moyenne », parce que c'est une déduction de position et non un
            # libellé lu : l'écran de validation doit le signaler.
            if champ_vide(result["format_v"]):
                v, c = _valeur_a_gauche(df_prix, nom_prix, r"format.hauteur")
                if v is not None:
                    poser("format_v", v, c, _safe_float)
                    result["confiances"]["format_v"] = "moyenne"

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

            # Calage impression. Le bloc « CALCUL Temps et métrage » de la
            # feuille Prix porte le temps en colonne J et le métrage en L sur
            # la même ligne — d'où les décalages 1 et 3. On le prend là plutôt
            # que sur Calculs, où le métrage s'appelle « METRAGE UTILISE », un
            # libellé qui apparaît trois fois pour trois choses différentes.
            v, c = chercher(df_prix, nom_prix, r"^calage\s+impression$")
            poser("temps_calage_impression_mn", v, c, _safe_float)
            v, c = chercher(df_prix, nom_prix, r"^calage\s+impression$", offset=3)
            poser("metrage_calage_impression_ml", v, c, _safe_float)
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

            # Repli si la feuille Prix n'a pas donné le calage impression.
            if champ_vide(result["temps_calage_impression_mn"]):
                v, c = chercher(df_calc, nom_calc, r"tps.calage.impression|temps.calage.impression")
                poser("temps_calage_impression_mn", v, c, _safe_float)

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

    # ── Indicateurs hors socle ────────────────────────────────────
    # « Tous les autres indicateurs du devis » : sur le modèle maison ils se
    # lisent au motif, sans appel au modèle. Un libellé absent est sauté —
    # le classeur d'un autre commercial n'en portera qu'une partie.
    try:
        result["indicateurs"] = _indicateurs_maison(
            {"prix": (nom_prix, df_prix), "calculs": (nom_calc, df_calc)}
        )
    except Exception as e:
        result["indicateurs"] = []
        result["parse_errors"].append(f"Indicateurs annexes : {e}")

    # Les quantités chiffrées par le commercial, qui ne sont pas forcément
    # celle sur laquelle les temps ont été calculés.
    try:
        result["paliers"] = paliers_quantite(df_prix, nom_prix) if df_prix is not None else []
    except Exception as e:
        result["paliers"] = []
        result["parse_errors"].append(f"Paliers de quantité : {e}")

    return result


def _indicateurs_maison(feuilles_par_role: dict) -> list[dict]:
    """Relève les indicateurs à libellé stable des feuilles Prix et Calculs."""
    trouves: list[dict] = []
    vus: set[str] = set()
    for role, motif, libelle, unite, offset in INDICATEURS_MAISON:
        nom, df = feuilles_par_role.get(role, (None, None))
        if df is None:
            continue
        valeur, coord = _find_value(df, motif, col_offset=offset, sheet_name=nom)
        if valeur is None or coord is None:
            continue
        try:
            nombre = float(valeur)
        except (TypeError, ValueError):
            continue
        if libelle in vus:
            continue
        vus.add(libelle)
        trouves.append({
            "libelle": libelle,
            "valeur_nombre": nombre,
            "valeur_texte": "",
            "unite": unite,
            "source": coord,
            "confiance": "haute",
            "origine": "regex",
        })
    return trouves

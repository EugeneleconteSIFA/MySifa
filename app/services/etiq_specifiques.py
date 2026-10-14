"""
MyPrint — étiquettes spécifiques : mise en page, variables, séries, rendu ZPL.

Une étiquette est décrite par un JSON, jamais par du ZPL :

    {
      "elements":  [ {id, type, x, y, ...}, ... ],   positions en mm, origine
                                                     en haut à gauche
      "variables": [ {nom, libelle, type, ...}, ... ]
    }

Le format (largeur_mm, hauteur_mm, dpi) vit dans les colonnes du modèle.
L'éditeur à la main et l'assistant IA modifient ce même JSON, puis
`rendre_zpl()` en tire le ZPL envoyé à l'imprimante. Le ZPL n'est donc
jamais une source : il se régénère à chaque impression.

Variables, référencées dans un élément par {{nom}} :

  fixe       valeur écrite une fois dans l'étiquette
  saisie     demandée à l'impression (lot, quantité, référence client…)
  compteur   numéro qui avance d'une étiquette à l'autre, et d'une impression
             à la suivante (compteur conservé en base, par étiquette)
  sscc       SSCC GS1 de 18 chiffres : extension + préfixe GS1 + série +
             clé de contrôle. Le compteur est partagé par toutes les
             étiquettes qui utilisent le même préfixe : un SSCC ne sort
             jamais deux fois.
  date       date du jour (format strftime, décalage en jours)
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Optional

# ─── Référentiel figé ────────────────────────────────────────────────────

TYPES_ELEMENT = ("texte", "code_barre", "cadre", "ligne")
SYMBOLOGIES = {
    "code128": "Code 128",
    "gs1_128": "GS1-128",
    "ean13": "EAN-13",
    "datamatrix": "DataMatrix",
    "qrcode": "QR code",
}
TYPES_VARIABLE = {
    "fixe": "Valeur fixe",
    "saisie": "Saisie à l'impression",
    "compteur": "Compteur",
    "sscc": "SSCC (GS1)",
    "date": "Date du jour",
}
ROTATIONS = {0: "N", 90: "R", 180: "I", 270: "B"}
ALIGNEMENTS = {"gauche": "L", "centre": "C", "droite": "R"}
DPI_ADMIS = (203, 300, 600)

QUANTITE_MAX = 5000
FORMAT_MAX_MM = 400

_NOM_VAR_RE = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


class EtiquetteInvalide(ValueError):
    """Message factuel, affiché tel quel à l'utilisateur."""


# ─── Normalisation ──────────────────────────────────────────────────────

def _num(v, defaut: float, mini: float, maxi: float) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return defaut
    if f != f:  # NaN
        return defaut
    return round(max(mini, min(maxi, f)), 2)


def _ent(v, defaut: int, mini: int, maxi: int) -> int:
    try:
        i = int(float(v))
    except (TypeError, ValueError):
        return defaut
    return max(mini, min(maxi, i))


def _txt(v, maxi: int = 500) -> str:
    return ("" if v is None else str(v))[:maxi]


def normaliser_layout(layout: Any) -> dict:
    """Rend un layout propre : champs bornés, types connus, ids uniques.

    Tolérant sur la forme (ce qui vient de l'IA passe par ici), strict sur le
    fond : un élément de type inconnu est écarté, une variable au nom invalide
    lève une erreur, parce qu'elle casserait les {{…}} qui la référencent.
    """
    if isinstance(layout, str):
        try:
            layout = json.loads(layout or "{}")
        except Exception:
            raise EtiquetteInvalide("Mise en page illisible (JSON invalide).")
    if not isinstance(layout, dict):
        layout = {}

    variables = []
    noms = set()
    for v in layout.get("variables") or []:
        if not isinstance(v, dict):
            continue
        nom = _txt(v.get("nom"), 40).strip().lower()
        if not _NOM_VAR_RE.match(nom):
            raise EtiquetteInvalide(
                f"Nom de variable invalide « {nom or '(vide)'} » — minuscules, chiffres et _ uniquement, "
                "commençant par une lettre.")
        if nom in noms:
            raise EtiquetteInvalide(f"Variable « {nom} » déclarée deux fois.")
        noms.add(nom)
        typ = v.get("type") if v.get("type") in TYPES_VARIABLE else "saisie"
        var = {"nom": nom, "libelle": _txt(v.get("libelle") or nom, 80), "type": typ}
        if typ in ("fixe", "saisie"):
            var["valeur"] = _txt(v.get("valeur"), 500)
            if typ == "saisie":
                var["obligatoire"] = bool(v.get("obligatoire", True))
        elif typ == "compteur":
            var["debut"] = _ent(v.get("debut"), 1, 0, 10**15)
            var["pas"] = _ent(v.get("pas"), 1, 1, 10**6)
            var["longueur"] = _ent(v.get("longueur"), 0, 0, 20)
            var["prefixe"] = _txt(v.get("prefixe"), 30)
            var["suffixe"] = _txt(v.get("suffixe"), 30)
        elif typ == "sscc":
            ext = re.sub(r"\D", "", _txt(v.get("extension"), 1)) or "0"
            pre = re.sub(r"\D", "", _txt(v.get("prefixe_gs1"), 12))
            var["extension"] = ext[:1]
            var["prefixe_gs1"] = pre
        elif typ == "date":
            fmt = _txt(v.get("format") or "%d/%m/%Y", 40)
            if "%" not in fmt:
                fmt = "%d/%m/%Y"
            var["format"] = fmt
            var["decalage_jours"] = _ent(v.get("decalage_jours"), 0, -3650, 3650)
        variables.append(var)

    elements = []
    ids = set()
    for i, e in enumerate(layout.get("elements") or []):
        if not isinstance(e, dict) or e.get("type") not in TYPES_ELEMENT:
            continue
        eid = _txt(e.get("id"), 20).strip() or f"e{i + 1}"
        while eid in ids:
            eid = f"{eid}_"
        ids.add(eid)
        typ = e["type"]
        el = {
            "id": eid,
            "type": typ,
            "nom": _txt(e.get("nom"), 60),
            "x": _num(e.get("x"), 5, 0, FORMAT_MAX_MM),
            "y": _num(e.get("y"), 5, 0, FORMAT_MAX_MM),
        }
        if typ == "texte":
            el["valeur"] = _txt(e.get("valeur"), 1000)
            el["taille"] = _num(e.get("taille"), 3.5, 1, 100)
            el["gras"] = bool(e.get("gras"))
            el["largeur"] = _num(e.get("largeur"), 0, 0, FORMAT_MAX_MM)
            el["lignes"] = _ent(e.get("lignes"), 1, 1, 20)
            el["align"] = e.get("align") if e.get("align") in ALIGNEMENTS else "gauche"
            el["rotation"] = _ent(e.get("rotation"), 0, 0, 270) if _ent(e.get("rotation"), 0, 0, 270) in ROTATIONS else 0
            el["inverse"] = bool(e.get("inverse"))
        elif typ == "code_barre":
            sym = e.get("symbologie") if e.get("symbologie") in SYMBOLOGIES else "code128"
            el["symbologie"] = sym
            el["valeur"] = _txt(e.get("valeur"), 500)
            el["hauteur"] = _num(e.get("hauteur"), 15, 2, 200)
            el["module"] = _num(e.get("module"), 0.375 if sym in ("code128", "gs1_128", "ean13") else 0.5, 0.1, 5)
            el["lisible"] = bool(e.get("lisible", True))
            el["rotation"] = _ent(e.get("rotation"), 0, 0, 270) if _ent(e.get("rotation"), 0, 0, 270) in ROTATIONS else 0
        elif typ == "cadre":
            el["largeur"] = _num(e.get("largeur"), 50, 0.1, FORMAT_MAX_MM)
            el["hauteur"] = _num(e.get("hauteur"), 20, 0.1, FORMAT_MAX_MM)
            el["epaisseur"] = _num(e.get("epaisseur"), 0.5, 0.1, 50)
            el["arrondi"] = _ent(e.get("arrondi"), 0, 0, 8)
            el["plein"] = bool(e.get("plein"))
        elif typ == "ligne":
            el["orientation"] = "v" if e.get("orientation") == "v" else "h"
            el["longueur"] = _num(e.get("longueur"), 50, 0.1, FORMAT_MAX_MM)
            el["epaisseur"] = _num(e.get("epaisseur"), 0.5, 0.1, 50)
        elements.append(el)

    return {"elements": elements, "variables": variables}


def normaliser_format(largeur_mm, hauteur_mm, dpi) -> tuple[float, float, int]:
    l = _num(largeur_mm, 100, 10, FORMAT_MAX_MM)
    h = _num(hauteur_mm, 150, 5, FORMAT_MAX_MM)
    d = _ent(dpi, 203, 150, 600)
    if d not in DPI_ADMIS:
        d = min(DPI_ADMIS, key=lambda x: abs(x - d))
    return l, h, d


def variables_referencees(layout: dict) -> set:
    noms = set()
    for e in layout.get("elements", []):
        for m in _PLACEHOLDER_RE.finditer(str(e.get("valeur") or "")):
            noms.add(m.group(1).lower())
    return noms


def controles(layout: dict) -> list[str]:
    """Avertissements non bloquants affichés dans l'éditeur."""
    out = []
    declarees = {v["nom"] for v in layout.get("variables", [])}
    for nom in sorted(variables_referencees(layout) - declarees):
        out.append(f"{{{{{nom}}}}} est utilisé mais aucune variable « {nom} » n'est déclarée.")
    for v in layout.get("variables", []):
        if v["type"] == "sscc" and not (7 <= len(v.get("prefixe_gs1", "")) <= 10):
            out.append(f"Variable « {v['nom']} » : le préfixe GS1 doit compter 7 à 10 chiffres.")
    return out


# ─── SSCC / GS1 ─────────────────────────────────────────────────────────

def cle_gs1(chiffres: str) -> str:
    """Clé de contrôle GS1 (modulo 10) d'une chaîne de chiffres sans sa clé."""
    total = 0
    for i, c in enumerate(reversed(chiffres)):
        total += int(c) * (3 if i % 2 == 0 else 1)
    return str((10 - total % 10) % 10)


def sscc(extension: str, prefixe_gs1: str, serie: int) -> str:
    longueur_serie = 16 - len(prefixe_gs1)
    if not (7 <= len(prefixe_gs1) <= 10):
        raise EtiquetteInvalide("Préfixe GS1 invalide — 7 à 10 chiffres.")
    if serie < 0 or serie >= 10 ** longueur_serie:
        raise EtiquetteInvalide(
            f"Série SSCC épuisée pour le préfixe {prefixe_gs1} ({longueur_serie} chiffres de série).")
    base = f"{extension}{prefixe_gs1}{serie:0{longueur_serie}d}"
    return base + cle_gs1(base)


def cle_compteur(modele_id: int, var: dict) -> str:
    if var["type"] == "sscc":
        return f"sscc:{var['extension']}{var['prefixe_gs1']}"
    return f"modele:{modele_id}:{var['nom']}"


def _format_compteur(var: dict, n: int) -> str:
    corps = str(n).zfill(var.get("longueur") or 0)
    return f"{var.get('prefixe', '')}{corps}{var.get('suffixe', '')}"


# ─── Séries ─────────────────────────────────────────────────────────────

def _dernier(conn, cle: str) -> Optional[int]:
    if conn is None:
        return None
    row = conn.execute("SELECT dernier FROM etiq_compteurs WHERE cle=?", (cle,)).fetchone()
    return None if row is None else int(row["dernier"])


def plan_serie(conn, modele_id: int, layout: dict, quantite: int,
               departs: Optional[dict] = None) -> dict:
    """Calcule, sans rien écrire, les numéros que prendrait une impression.

    Rend {nom_variable: {"cle", "premier", "pas"}} pour chaque compteur et
    SSCC. Un départ demandé à la main ne peut pas revenir en arrière sur un
    SSCC : ce serait réémettre un numéro déjà sorti.
    """
    departs = departs or {}
    plan = {}
    for var in layout.get("variables", []):
        if var["type"] not in ("compteur", "sscc"):
            continue
        cle = cle_compteur(modele_id, var)
        dernier = _dernier(conn, cle)
        pas = var.get("pas", 1) if var["type"] == "compteur" else 1
        if var["type"] == "compteur":
            suivant = var["debut"] if dernier is None else dernier + pas
        else:
            suivant = 1 if dernier is None else dernier + 1
        demande = departs.get(var["nom"])
        if demande not in (None, ""):
            try:
                demande = int(str(demande).strip())
            except ValueError:
                raise EtiquetteInvalide(f"Départ de « {var['libelle']} » invalide — nombre entier attendu.")
            if var["type"] == "sscc" and dernier is not None and demande <= dernier:
                raise EtiquetteInvalide(
                    f"Départ SSCC {demande} refusé : la série {dernier} est déjà sortie. "
                    f"Premier numéro libre : {dernier + 1}.")
            suivant = demande
        if var["type"] == "sscc":
            sscc(var["extension"], var["prefixe_gs1"], suivant + quantite - 1)  # lève si épuisé
        plan[var["nom"]] = {"cle": cle, "premier": suivant, "pas": pas, "type": var["type"]}
    return plan


def reserver_serie(conn, plan: dict, quantite: int, email: str) -> None:
    """Écrit les nouveaux « derniers » dans la transaction ouverte.

    L'UPDATE pose le verrou d'écriture SQLite avant le contrôle : deux
    impressions simultanées sur le même SSCC se sérialisent, et la seconde
    voit que la plage a bougé.
    """
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    for nom, p in plan.items():
        dernier = p["premier"] + (quantite - 1) * p["pas"]
        conn.execute(
            "INSERT INTO etiq_compteurs (cle,dernier,updated_at,updated_by) VALUES (?,?,?,?) "
            "ON CONFLICT(cle) DO UPDATE SET dernier=MAX(dernier, excluded.dernier), "
            "updated_at=excluded.updated_at, updated_by=excluded.updated_by",
            (p["cle"], dernier, now, email),
        )


def valeurs_etiquette(layout: dict, plan: dict, index: int, saisies: dict,
                      maintenant: Optional[datetime] = None) -> dict:
    """Valeurs de toutes les variables pour la n-ième étiquette (index 0)."""
    maintenant = maintenant or datetime.now()
    out = {}
    for var in layout.get("variables", []):
        typ = var["type"]
        if typ == "fixe":
            out[var["nom"]] = var.get("valeur", "")
        elif typ == "saisie":
            val = saisies.get(var["nom"])
            out[var["nom"]] = var.get("valeur", "") if val is None else str(val)
        elif typ == "date":
            d = maintenant + timedelta(days=var.get("decalage_jours", 0))
            out[var["nom"]] = d.strftime(var.get("format") or "%d/%m/%Y")
        elif typ in ("compteur", "sscc"):
            p = plan.get(var["nom"]) or {"premier": var.get("debut", 1), "pas": 1}
            n = p["premier"] + index * p["pas"]
            if typ == "compteur":
                out[var["nom"]] = _format_compteur(var, n)
            else:
                out[var["nom"]] = sscc(var["extension"], var["prefixe_gs1"], n)
    return out


def controler_saisies(layout: dict, saisies: dict) -> None:
    manquantes = [v["libelle"] for v in layout.get("variables", [])
                  if v["type"] == "saisie" and v.get("obligatoire", True)
                  and not str(saisies.get(v["nom"], v.get("valeur", "")) or "").strip()]
    if manquantes:
        raise EtiquetteInvalide("À renseigner avant impression : " + ", ".join(manquantes) + ".")


# ─── Rendu ZPL ──────────────────────────────────────────────────────────

def _dots(mm: float, dpi: int) -> int:
    return max(0, int(round(mm * dpi / 25.4)))


def _fh(s: str) -> str:
    """Échappement ZPL via ^FH_ : _ ^ ~ deviennent leur code hexadécimal."""
    return (str(s).replace("_", "_5F").replace("^", "_5E").replace("~", "_7E")
            .replace("\r", "").replace("\n", "_0A"))


def substituer(texte: str, valeurs: dict) -> str:
    return _PLACEHOLDER_RE.sub(lambda m: str(valeurs.get(m.group(1).lower(), "")), texte or "")


def _donnees_code(sym: str, valeur: str) -> str:
    if sym == "ean13":
        chiffres = re.sub(r"\D", "", valeur)
        return chiffres[:12]  # l'imprimante calcule la 13e (clé)
    if sym == "gs1_128":
        # Mode D du ^BC : les AI s'écrivent entre parenthèses, FNC1 est posé
        # par l'imprimante. On retire les espaces de mise en forme.
        return re.sub(r"\s+", "", valeur)
    return valeur


def _zpl_element(e: dict, valeurs: dict, dpi: int) -> str:
    x, y = _dots(e["x"], dpi), _dots(e["y"], dpi)
    typ = e["type"]
    if typ == "texte":
        h = max(10, _dots(e["taille"], dpi))
        w = int(h * (1.0 if e.get("gras") else 0.85))
        rot = ROTATIONS.get(e.get("rotation", 0), "N")
        out = f"^FO{x},{y}^A0{rot},{h},{w}"
        if e.get("largeur"):
            out += f"^FB{_dots(e['largeur'], dpi)},{e.get('lignes', 1)},0,{ALIGNEMENTS[e.get('align', 'gauche')]},0"
        if e.get("inverse"):
            out += "^FR"
        return out + f"^FH_^FD{_fh(substituer(e['valeur'], valeurs))}^FS"
    if typ == "code_barre":
        sym = e["symbologie"]
        rot = ROTATIONS.get(e.get("rotation", 0), "N")
        h = max(10, _dots(e["hauteur"], dpi))
        mod = max(1, _dots(e["module"], dpi))
        lisible = "Y" if e.get("lisible", True) else "N"
        data = _fh(_donnees_code(sym, substituer(e["valeur"], valeurs)))
        if sym == "code128":
            return f"^FO{x},{y}^BY{mod},3,{h}^BC{rot},{h},{lisible},N,N^FH_^FD{data}^FS"
        if sym == "gs1_128":
            return f"^FO{x},{y}^BY{mod},3,{h}^BC{rot},{h},{lisible},N,N,D^FH_^FD{data}^FS"
        if sym == "ean13":
            return f"^FO{x},{y}^BY{mod},3,{h}^BE{rot},{h},{lisible},N^FD{data}^FS"
        if sym == "datamatrix":
            return f"^FO{x},{y}^BX{rot},{mod},200^FH_^FD{data}^FS"
        if sym == "qrcode":
            return f"^FO{x},{y}^BQN,2,{min(10, mod)}^FH_^FDQA,{data}^FS"
    if typ == "cadre":
        t = max(1, _dots(e["epaisseur"], dpi))
        w, h = max(t, _dots(e["largeur"], dpi)), max(t, _dots(e["hauteur"], dpi))
        if e.get("plein"):
            t = min(w, h)
        return f"^FO{x},{y}^GB{w},{h},{t},B,{e.get('arrondi', 0)}^FS"
    if typ == "ligne":
        t = max(1, _dots(e["epaisseur"], dpi))
        l = max(1, _dots(e["longueur"], dpi))
        return f"^FO{x},{y}^GB{l},{t},{t}^FS" if e["orientation"] == "h" else f"^FO{x},{y}^GB{t},{l},{t}^FS"
    return ""


def rendre_zpl(layout: dict, largeur_mm: float, hauteur_mm: float, dpi: int,
               valeurs: dict, exemplaires: int = 1) -> str:
    """Une étiquette ^XA…^XZ. `exemplaires` copies identiques (^PQ)."""
    lignes = [
        "^XA", "^CI28",
        f"^PW{_dots(largeur_mm, dpi)}", f"^LL{_dots(hauteur_mm, dpi)}", "^LH0,0",
    ]
    for e in layout.get("elements", []):
        z = _zpl_element(e, valeurs, dpi)
        if z:
            lignes.append(z)
    lignes.append(f"^PQ{max(1, int(exemplaires))}")
    lignes.append("^XZ")
    return "\n".join(lignes) + "\n"


def rendre_serie(layout: dict, largeur_mm: float, hauteur_mm: float, dpi: int,
                 plan: dict, quantite: int, saisies: dict, exemplaires: int = 1) -> tuple[str, list]:
    """ZPL de toute la série + liste des valeurs de chaque étiquette."""
    morceaux, toutes = [], []
    maintenant = datetime.now()
    for i in range(quantite):
        vals = valeurs_etiquette(layout, plan, i, saisies, maintenant)
        toutes.append(vals)
        morceaux.append(rendre_zpl(layout, largeur_mm, hauteur_mm, dpi, vals, exemplaires))
    return "".join(morceaux), toutes

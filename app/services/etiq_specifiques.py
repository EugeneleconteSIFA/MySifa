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
  date       date calculée : base (jour d'impression ou autre variable, ex.
             date de fabrication) + N mois + N jours, format au choix
             (JJ/MM/AAAA, semaine ISO, lot daté AAJJJ…) — etiq_formules.py
  formule    expression sûre sur les autres variables (concaténation,
             majuscules, calculs, SI…) — etiq_formules.py
  source     donnée MySifa (dossier, OF, produit, client, matière, lot) :
             `champ` = « dossier.reference », « client.ville »… Remplie à
             l'impression comme une saisie, depuis l'enregistrement choisi
             (etiq_sources.py), modifiable avant d'imprimer.

Objets communs à tous les éléments :
  calque           id d'un calque de `layout.calques` (fond figé, données…)
  verrou           objet figé : seul un rôle de ETIQ_ROLES_CONCEPTION le modifie
  condition        expression : l'objet n'est imprimé que si elle est vraie
  masquer_si_vide  texte / code dont la valeur est vide → objet non imprimé

Le format complet (unités, champs par type) est décrit en tête de
static/mysifa_etiq_editeur.js : c'est le contrat lu par l'impression.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Any, Optional

# ─── Référentiel figé ────────────────────────────────────────────────────

TYPES_ELEMENT = ("texte", "code_barre", "cadre", "ligne", "picto", "ellipse", "image")
SYMBOLOGIES = {
    "code128": "Code 128 (auto)",
    "gs1_128": "GS1-128",
    "ean13": "EAN-13",
    "datamatrix": "DataMatrix",
    "gs1_datamatrix": "GS1 DataMatrix",
    "qrcode": "QR code",
    "pdf417": "PDF417",
    "ean8": "EAN-8",
    "upca": "UPC-A",
    "code39": "Code 39",
    "itf14": "ITF-14",
}
SYMBOLOGIES_2D = ("datamatrix", "gs1_datamatrix", "qrcode")
TYPES_VARIABLE = {
    "fixe": "Valeur fixe",
    "saisie": "Saisie à l'impression",
    "source": "Donnée MySifa",
    "compteur": "Compteur",
    "sscc": "SSCC (GS1)",
    "date": "Date calculée",
    "formule": "Formule",
}
CALQUES_DEFAUT = (
    {"id": "fond", "nom": "Fond figé (logo, mentions)", "verrou": True},
    {"id": "donnees", "nom": "Données", "verrou": False},
)
_CHAMP_SOURCE_RE = re.compile(r"^[a-z]+\.[a-z0-9_]+$")
_CALQUE_RE = re.compile(r"^[a-z][a-z0-9_]{0,19}$")
_LANGUE_RE = re.compile(r"^[a-z]{2}(-[a-z]{2})?$")
FORMES = ("rectangle", "arrondi", "ronde", "ovale", "libre")
_CHEMIN_RE = re.compile(r"^[MmLlHhVvCcSsQqTtAaZz0-9 ,.\-eE]*$")
CONTROLES_SAISIE = ("texte", "entier", "nombre", "date", "motif")
IMAGE_MAX_CARACTERES = 800_000   # data URL d'un logo, ~600 Ko


def _couleur(c) -> Optional[dict]:
    """Couleur d'un objet (sortie PDF couleur, aperçu). Les imprimantes
    thermiques impriment en noir : la couleur y est ignorée."""
    if not isinstance(c, dict) or c.get("mode") not in ("cmjn", "ton_direct"):
        return None
    out = {"mode": c["mode"]}
    for k in ("c", "m", "j", "n"):
        out[k] = _num(c.get(k), 0, 0, 100)
    out["nom"] = _txt(c.get("nom"), 40)
    hexa = _txt(c.get("hex"), 7)
    out["hex"] = hexa if re.fullmatch(r"#[0-9a-fA-F]{6}", hexa or "") else ""
    return out


def _forme(f) -> dict:
    f = f if isinstance(f, dict) else {}
    t = f.get("type") if f.get("type") in FORMES else "rectangle"
    out = {"type": t, "rayon_mm": _num(f.get("rayon_mm"), 3, 0, 100)}
    chemin = _txt(f.get("chemin"), 4000).strip()
    out["chemin"] = chemin if (t == "libre" and _CHEMIN_RE.match(chemin)) else ""
    return out


def _planche(p) -> dict:
    p = p if isinstance(p, dict) else {}
    return {
        "type": "a4" if p.get("type") == "a4" else "rouleau",
        "poses": _ent(p.get("poses"), 1, 1, 12),
        "rangees": _ent(p.get("rangees"), 0, 0, 40),          # 0 = autant qu'il en tient (A4)
        "marge_gauche_mm": _num(p.get("marge_gauche_mm"), 0 if p.get("type") != "a4" else 5, 0, 100),
        "marge_haut_mm": _num(p.get("marge_haut_mm"), 0 if p.get("type") != "a4" else 5, 0, 100),
        "espace_h_mm": _num(p.get("espace_h_mm"), 2 if p.get("type") == "a4" else 3, 0, 100),
        "espace_v_mm": _num(p.get("espace_v_mm"), 2, 0, 100),
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
        return float(defaut)
    if f != f:  # NaN
        return float(defaut)
    return float(round(max(mini, min(maxi, f)), 2))


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
        if typ in ("fixe", "saisie", "source"):
            var["valeur"] = _txt(v.get("valeur"), 500)
            if typ == "saisie":
                var["obligatoire"] = bool(v.get("obligatoire", True))
                c = v.get("controle") if isinstance(v.get("controle"), dict) else {}
                ct = c.get("type") if c.get("type") in CONTROLES_SAISIE else "texte"
                var["controle"] = {"type": ct, "motif": _txt(c.get("motif"), 120) if ct == "motif" else "",
                                   "min": c.get("min") if isinstance(c.get("min"), (int, float)) else None,
                                   "max": c.get("max") if isinstance(c.get("max"), (int, float)) else None,
                                   "longueur_max": _ent(c.get("longueur_max"), 0, 0, 500)}
                var["choix"] = [_txt(x, 120) for x in (v.get("choix") or []) if str(x).strip()][:60]
                var["pesee"] = bool(v.get("pesee"))
                var["balance_id"] = _ent(v.get("balance_id"), 0, 0, 10**9) or None
            if typ == "source":
                champ = _txt(v.get("champ"), 60).strip().lower()
                var["champ"] = champ if _CHAMP_SOURCE_RE.match(champ) else ""
                var["obligatoire"] = bool(v.get("obligatoire", False))
        elif typ == "formule":
            var["expression"] = _txt(v.get("expression"), 1000)
        elif typ == "compteur":
            var["debut"] = _ent(v.get("debut"), 1, 0, 10**15)
            var["pas"] = _ent(v.get("pas"), 1, 1, 10**6)
            var["longueur"] = _ent(v.get("longueur"), 0, 0, 20)
            var["prefixe"] = _txt(v.get("prefixe"), 30)
            var["suffixe"] = _txt(v.get("suffixe"), 30)
            # Reprise au dernier numéro mémorisé en base (défaut) ou départ
            # à `debut` à chaque impression.
            var["reprise"] = bool(v.get("reprise", True))
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
            base = _txt(v.get("base") or "impression", 40).strip().lower()
            var["base"] = base if (base == "impression" or _NOM_VAR_RE.match(base)) else "impression"
            var["decalage_jours"] = _ent(v.get("decalage_jours"), 0, -3650, 3650)
            var["decalage_mois"] = _ent(v.get("decalage_mois"), 0, -600, 600)
        variables.append(var)

    calques = []
    for c in layout.get("calques") or []:
        if not isinstance(c, dict):
            continue
        cid = _txt(c.get("id"), 20).strip().lower()
        if not _CALQUE_RE.match(cid) or any(x["id"] == cid for x in calques):
            continue
        calques.append({"id": cid, "nom": _txt(c.get("nom") or cid, 60), "verrou": bool(c.get("verrou"))})
        if len(calques) >= 8:
            break
    for d in CALQUES_DEFAUT:
        if not any(x["id"] == d["id"] for x in calques):
            calques.append(dict(d))
    ids_calques = {c["id"] for c in calques}

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
            "calque": e.get("calque") if e.get("calque") in ids_calques else "donnees",
            "verrou": bool(e.get("verrou")),
            "condition": _txt(e.get("condition"), 500).strip(),
            "masquer_si_vide": bool(e.get("masquer_si_vide")),
        }
        coul = _couleur(e.get("couleur"))
        if coul:
            el["couleur"] = coul
        if typ == "texte":
            el["valeur"] = _txt(e.get("valeur"), 1000)
            el["taille"] = _num(e.get("taille"), 3.5, 1, 100)
            el["gras"] = bool(e.get("gras"))
            el["largeur"] = _num(e.get("largeur"), 0, 0, FORMAT_MAX_MM)
            el["lignes"] = _ent(e.get("lignes"), 1, 1, 20)
            el["align"] = e.get("align") if e.get("align") in ALIGNEMENTS else "gauche"
            el["rotation"] = _ent(e.get("rotation"), 0, 0, 270) if _ent(e.get("rotation"), 0, 0, 270) in ROTATIONS else 0
            el["inverse"] = bool(e.get("inverse"))
            el["ajuster"] = bool(e.get("ajuster"))
            el["miroir"] = bool(e.get("miroir"))
            el["police"] = _txt(e.get("police"), 40)
            arc = e.get("arc") if isinstance(e.get("arc"), dict) else None
            if arc and _num(arc.get("rayon_mm"), 0, 0, 500) > 0:
                el["arc"] = {"rayon_mm": _num(arc.get("rayon_mm"), 20, 2, 500),
                             "sens": "bas" if arc.get("sens") == "bas" else "haut"}
            tr = e.get("traductions") if isinstance(e.get("traductions"), dict) else {}
            el["traductions"] = {k: _txt(v, 1000) for k, v in list(tr.items())[:12]
                                 if isinstance(k, str) and _LANGUE_RE.match(k) and v}
        elif typ == "code_barre":
            sym = e.get("symbologie") if e.get("symbologie") in SYMBOLOGIES else "code128"
            el["symbologie"] = sym
            el["valeur"] = _txt(e.get("valeur"), 500)
            el["hauteur"] = _num(e.get("hauteur"), 15, 2, 200)
            el["module"] = _num(e.get("module"), 0.375 if sym in ("code128", "gs1_128", "ean13") else 0.5, 0.1, 5)
            if sym == "pdf417":
                el["colonnes"] = _ent(e.get("colonnes"), 0, 0, 30)   # 0 = automatique
                el["securite"] = _ent(e.get("securite"), 5, 0, 8)
            if sym == "qrcode":
                el["correction"] = e.get("correction") if e.get("correction") in ("L", "M", "Q", "H") else "M"
            el["lisible"] = bool(e.get("lisible", True))
            el["rotation"] = _ent(e.get("rotation"), 0, 0, 270) if _ent(e.get("rotation"), 0, 0, 270) in ROTATIONS else 0
        elif typ == "cadre":
            el["largeur"] = _num(e.get("largeur"), 50, 0.1, FORMAT_MAX_MM)
            el["hauteur"] = _num(e.get("hauteur"), 20, 0.1, FORMAT_MAX_MM)
            el["epaisseur"] = _num(e.get("epaisseur"), 0.5, 0.1, 50)
            el["arrondi"] = _ent(e.get("arrondi"), 0, 0, 8)
            el["plein"] = bool(e.get("plein"))
        elif typ == "ellipse":
            el["largeur"] = _num(e.get("largeur"), 20, 0.5, FORMAT_MAX_MM)
            el["hauteur"] = _num(e.get("hauteur"), 20, 0.5, FORMAT_MAX_MM)
            el["epaisseur"] = _num(e.get("epaisseur"), 0.5, 0.1, 50)
            el["plein"] = bool(e.get("plein"))
        elif typ == "image":
            src = _txt(e.get("src"), IMAGE_MAX_CARACTERES)
            if not re.match(r"^data:image/(png|jpeg|gif|webp);base64,[A-Za-z0-9+/=]+$", src or ""):
                continue
            el["src"] = src
            el["largeur"] = _num(e.get("largeur"), 20, 1, FORMAT_MAX_MM)
            el["hauteur"] = _num(e.get("hauteur"), 20, 1, FORMAT_MAX_MM)
            el["seuil"] = _ent(e.get("seuil"), 128, 0, 255)
            el["tramage"] = "diffusion" if e.get("tramage") == "diffusion" else "seuil"
            el["inverse"] = bool(e.get("inverse"))
        elif typ == "ligne":
            el["orientation"] = "v" if e.get("orientation") == "v" else "h"
            el["longueur"] = _num(e.get("longueur"), 50, 0.1, FORMAT_MAX_MM)
            el["epaisseur"] = _num(e.get("epaisseur"), 0.5, 0.1, 50)
        elif typ == "picto":
            from app.services.etiq_pictos import PICTOS
            nom_p = e.get("picto") if e.get("picto") in PICTOS else None
            if not nom_p:
                continue
            el["picto"] = nom_p
            el["largeur"] = _num(e.get("largeur"), 15, 2, FORMAT_MAX_MM)
            el["hauteur"] = _num(e.get("hauteur"), 15, 2, FORMAT_MAX_MM)
            el["legende"] = _txt(e.get("legende"), 200)
            el["taille_legende"] = _num(e.get("taille_legende"), 2.2, 1, 20)
            el["rotation"] = _ent(e.get("rotation"), 0, 0, 270) if _ent(e.get("rotation"), 0, 0, 270) in ROTATIONS else 0
        elements.append(el)

    langues = [l for l in (layout.get("langues") or []) if isinstance(l, str) and _LANGUE_RE.match(l)][:12]
    out = {"elements": elements, "variables": variables, "calques": calques,
           "forme": _forme(layout.get("forme")), "planche": _planche(layout.get("planche")),
           "langues": langues or ["fr"]}
    out["langue_defaut"] = layout.get("langue_defaut") if layout.get("langue_defaut") in out["langues"] else out["langues"][0]
    guides = []
    for g in (layout.get("guides") or [])[:40]:
        if isinstance(g, dict) and g.get("o") in ("h", "v"):
            guides.append({"o": g["o"], "pos": _num(g.get("pos"), 0, 0, FORMAT_MAX_MM)})
    out["guides"] = guides
    return out


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
    from app.services.etiq_formules import evaluer
    exemple = {v["nom"]: (v.get("valeur") or "1") for v in layout.get("variables", [])}
    for v in layout.get("variables", []):
        if v["type"] == "sscc" and not (7 <= len(v.get("prefixe_gs1", "")) <= 10):
            out.append(f"Variable « {v['nom']} » : le préfixe GS1 doit compter 7 à 10 chiffres.")
        if v["type"] == "formule":
            r = evaluer(v.get("expression", ""), exemple)
            if r["erreur"]:
                out.append(f"Formule « {v['nom']} » : {r['erreur']}")
        if v["type"] == "source" and not v.get("champ"):
            out.append(f"Variable « {v['nom']} » : choisir la donnée MySifa à lire.")
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
            suivant = var["debut"] if (dernier is None or not var.get("reprise", True)) else dernier + pas
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
    from app.services.etiq_formules import calculer_date, evaluer
    maintenant = maintenant or datetime.now()
    out = {}
    for k, v in valeurs_systeme().items():
        out.setdefault(k, v)
    langue = str((saisies or {}).get("_langue") or layout.get("langue_defaut") or "")
    if langue in (layout.get("langues") or []):
        out["_langue"] = langue
    variables = layout.get("variables", [])
    for var in variables:
        typ = var["type"]
        if typ == "fixe":
            out[var["nom"]] = var.get("valeur", "")
        elif typ in ("saisie", "source"):
            val = saisies.get(var["nom"])
            out[var["nom"]] = var.get("valeur", "") if val is None else str(val)
        elif typ in ("compteur", "sscc"):
            p = plan.get(var["nom"]) or {"premier": var.get("debut", 1), "pas": 1}
            n = p["premier"] + index * p["pas"]
            if typ == "compteur":
                out[var["nom"]] = _format_compteur(var, n)
            else:
                out[var["nom"]] = sscc(var["extension"], var["prefixe_gs1"], n)
    # Dates puis formules : elles lisent les autres variables. Deux passes,
    # pour qu'une formule puisse lire une formule déclarée après elle.
    for _passe in range(2):
        for var in variables:
            if var["type"] == "date":
                out[var["nom"]] = calculer_date(var, out, maintenant)
            elif var["type"] == "formule":
                out[var["nom"]] = evaluer(var.get("expression", ""), out)["valeur"]
    return out


def valeurs_systeme() -> dict:
    """Variables fournies par MySifa sans déclaration : {{fsc_licence}},
    {{gs1_prefixe}}. Une variable déclarée du même nom l'emporte."""
    try:
        from config import ETIQ_GS1_PREFIXE, FSC_LICENCE_SIFA
    except Exception:
        return {}
    return {"fsc_licence": FSC_LICENCE_SIFA or "", "gs1_prefixe": ETIQ_GS1_PREFIXE or ""}


def element_visible(e: dict, valeurs: dict) -> bool:
    """Condition d'affichage et « masquer si vide » d'un objet."""
    from app.services.etiq_formules import condition_vraie
    if e.get("condition") and not condition_vraie(e["condition"], valeurs):
        return False
    if e.get("masquer_si_vide") and e.get("type") in ("texte", "code_barre"):
        # Vide = toutes les variables qu'il cite sont vides (« Lot {{lot}} »
        # disparaît sans lot), ou son texte entier s'il n'en cite aucune.
        noms = [m.group(1).lower() for m in _PLACEHOLDER_RE.finditer(e.get("valeur") or "")]
        if noms:
            if not any(str(valeurs.get(n, "")).strip() for n in noms):
                return False
        elif not substituer(texte_element(e, valeurs.get("_langue", "")), valeurs).strip():
            return False
    return True


def elements_visibles(layout: dict, valeurs: dict) -> list:
    return [e for e in layout.get("elements", []) if element_visible(e, valeurs)]


def controler_saisies(layout: dict, saisies: dict) -> None:
    manquantes = [v["libelle"] for v in layout.get("variables", [])
                  if v["type"] in ("saisie", "source") and v.get("obligatoire", v["type"] == "saisie")
                  and not str(saisies.get(v["nom"], v.get("valeur", "")) or "").strip()]
    if manquantes:
        raise EtiquetteInvalide("À renseigner avant impression : " + ", ".join(manquantes) + ".")
    for v in layout.get("variables", []):
        if v["type"] != "saisie":
            continue
        msg = controle_saisie(v, str(saisies.get(v["nom"], v.get("valeur", "")) or ""))
        if msg:
            raise EtiquetteInvalide(msg)


def controle_saisie(v: dict, val: str) -> str:
    """Message d'erreur d'une saisie opérateur, ou "" (miroir du formulaire
    d'impression, static/mysifa_etiq_donnees.js)."""
    val = (val or "").strip()
    if not val:
        return ""
    lib = v.get("libelle") or v["nom"]
    c = v.get("controle") or {}
    if v.get("choix") and val not in v["choix"]:
        return f"{lib} : valeur hors de la liste."
    if c.get("longueur_max") and len(val) > c["longueur_max"]:
        return f"{lib} : {c['longueur_max']} caractères au plus."
    t = c.get("type") or "texte"
    if t in ("entier", "nombre"):
        motif = r"^-?\d+$" if t == "entier" else r"^-?\d+([.,]\d+)?$"
        if not re.match(motif, val.replace(" ", "")):
            return f"{lib} : {'nombre entier' if t == 'entier' else 'nombre'} attendu."
        n = float(val.replace(" ", "").replace(",", "."))
        if c.get("min") is not None and n < c["min"]:
            return f"{lib} : {c['min']:g} au moins."
        if c.get("max") is not None and n > c["max"]:
            return f"{lib} : {c['max']:g} au plus."
    elif t == "date":
        from app.services.etiq_formules import lire_date
        if lire_date(val) is None:
            return f"{lib} : date JJ/MM/AAAA attendue."
    elif t == "motif" and c.get("motif"):
        try:
            if not re.fullmatch(c["motif"], val):
                return f"{lib} : format attendu {c['motif']}."
        except re.error:
            return ""
    return ""


def texte_element(e: dict, langue: str = "") -> str:
    """Texte d'un objet dans la langue demandée (variante par langue), sinon
    le texte de base."""
    if langue and e.get("traductions", {}).get(langue):
        return e["traductions"][langue]
    return e.get("valeur", "")


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
        texte = substituer(texte_element(e, valeurs.get("_langue", "")), valeurs)
        if e.get("arc") or e.get("miroir"):
            from app.services.etiq_pictos import gfa_texte
            g = gfa_texte(e, texte, dpi)
            return f"^FO{x},{y}{g}^FS" if g else ""
        taille = taille_ajustee(e, texte) if e.get("ajuster") else e["taille"]
        h = max(10, _dots(taille, dpi))
        w = int(h * (1.0 if e.get("gras") else 0.85))
        rot = ROTATIONS.get(e.get("rotation", 0), "N")
        out = f"^FO{x},{y}^A0{rot},{h},{w}"
        if e.get("largeur"):
            out += f"^FB{_dots(e['largeur'], dpi)},{e.get('lignes', 1)},0,{ALIGNEMENTS[e.get('align', 'gauche')]},0"
        if e.get("inverse"):
            out += "^FR"
        return out + f"^FH_^FD{_fh(texte)}^FS"
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
        if sym == "gs1_datamatrix":
            # FNC1 en tête puis après chaque AI de longueur variable, par la
            # séquence d'échappement « _1 » du ^BX (7e paramètre). Pas de ^FH :
            # le « _ » y servirait aussi d'échappement hexadécimal.
            from app.services.etiq_gs1 import AI, decouper
            brut = substituer(e["valeur"], valeurs)
            groupes = decouper(brut)
            morceaux = []
            for i, (ai, d) in enumerate(groupes):
                morceaux.append(ai + re.sub(r"[\^~_]", "", d))
                if i < len(groupes) - 1 and AI.get(ai, (0, None))[1] is None:
                    morceaux.append("_1")
            donnees = "_1" + "".join(morceaux) if groupes else re.sub(r"[\^~_]", "", brut)
            return f"^FO{x},{y}^BX{rot},{mod},200,,,,_^FD{donnees}^FS"
        if sym == "qrcode":
            return f"^FO{x},{y}^BQN,2,{min(10, mod)}^FH_^FDQA,{data}^FS"
        if sym == "ean8":
            return f"^FO{x},{y}^BY{mod},3,{h}^B8{rot},{h},{lisible},N^FD{re.sub(r'[^0-9]', '', data)[:7]}^FS"
        if sym == "upca":
            return f"^FO{x},{y}^BY{mod},3,{h}^BU{rot},{h},{lisible},N,Y^FD{re.sub(r'[^0-9]', '', data)[:11]}^FS"
        if sym == "code39":
            return f"^FO{x},{y}^BY{mod},3,{h}^B3{rot},N,{h},{lisible},N^FD{data.upper()}^FS"
        if sym == "itf14":
            return f"^FO{x},{y}^BY{mod},3,{h}^B2{rot},{h},{lisible},N,Y^FD{re.sub(r'[^0-9]', '', data)[:13]}^FS"
        if sym == "pdf417":
            cols = e.get("colonnes") or ""
            return f"^FO{x},{y}^BY{mod}^B7{rot},{max(2, mod * 3)},5,{cols},,N^FH_^FD{data}^FS"
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
    if typ == "ellipse":
        t = max(1, _dots(e["epaisseur"], dpi))
        w, h = max(t, _dots(e["largeur"], dpi)), max(t, _dots(e["hauteur"], dpi))
        return f"^FO{x},{y}^GE{w},{h},{min(w, h) if e.get('plein') else t},B^FS"
    if typ == "image":
        from app.services.etiq_pictos import gfa_image_src
        g = gfa_image_src(e["src"], max(8, _dots(e["largeur"], dpi)), max(8, _dots(e["hauteur"], dpi)),
                          e.get("seuil", 128), e.get("inverse", False))
        return f"^FO{x},{y}{g}^FS" if g else ""
    if typ == "picto":
        from app.services.etiq_pictos import zpl_gfa
        w, h = max(8, _dots(e["largeur"], dpi)), max(8, _dots(e["hauteur"], dpi))
        legende = substituer(e.get("legende", ""), valeurs).strip()
        hl = max(10, _dots(e.get("taille_legende", 2.2), dpi)) if legende else 0
        out = f"^FO{x},{y}{zpl_gfa(e['picto'], w, max(8, h - (hl + 2 if legende else 0)))}^FS"
        if legende:
            out += (f"^FO{x},{y + h - hl}^A0N,{hl},{int(hl * 0.85)}^FB{w},1,0,C,0"
                    f"^FH_^FD{_fh(legende)}^FS")
        return out
    return ""


def rendre_zpl(layout: dict, largeur_mm: float, hauteur_mm: float, dpi: int,
               valeurs: dict, exemplaires: int = 1) -> str:
    """Une étiquette ^XA…^XZ. `exemplaires` copies identiques (^PQ)."""
    lignes = [
        "^XA", "^CI28",
        f"^PW{_dots(largeur_mm, dpi)}", f"^LL{_dots(hauteur_mm, dpi)}", "^LH0,0",
    ]
    for e in elements_visibles(layout, valeurs):
        z = _zpl_element(e, valeurs, dpi)
        if z:
            lignes.append(z)
    lignes.append(f"^PQ{max(1, int(exemplaires))}")
    lignes.append("^XZ")
    return "\n".join(lignes) + "\n"


def taille_ajustee(e: dict, texte: str) -> float:
    """Hauteur de caractère réduite pour que le texte tienne dans son bloc
    (largeur × lignes). Police 0 des Zebra : ~0,55 × la hauteur par caractère."""
    larg = e.get("largeur") or 0
    if not larg or not texte:
        return e["taille"]
    place = larg * max(1, e.get("lignes", 1))
    besoin = len(texte) * e["taille"] * 0.55
    if besoin <= place:
        return e["taille"]
    return max(1.0, round(e["taille"] * place / besoin, 2))


def rendre_lot(layout: dict, largeur_mm: float, hauteur_mm: float, dpi: int,
               valeurs: list, exemplaires: int = 1) -> str:
    """ZPL d'une liste d'étiquettes. Un rouleau multi-poses (planche
    « rouleau », poses > 1) pose les étiquettes côte à côte : une ^XA par
    rangée, chaque pose décalée par ^LH."""
    pl = layout.get("planche") or {}
    poses = pl.get("poses", 1) if pl.get("type", "rouleau") == "rouleau" else 1
    if poses <= 1:
        return "".join(rendre_zpl(layout, largeur_mm, hauteur_mm, dpi, v, exemplaires) for v in valeurs)
    pas = largeur_mm + pl.get("espace_h_mm", 3)
    largeur_totale = pl.get("marge_gauche_mm", 0) + poses * largeur_mm + (poses - 1) * pl.get("espace_h_mm", 3)
    out = []
    for i in range(0, len(valeurs), poses):
        lignes = ["^XA", "^CI28", f"^PW{_dots(largeur_totale, dpi)}", f"^LL{_dots(hauteur_mm, dpi)}"]
        for k, vals in enumerate(valeurs[i:i + poses]):
            lignes.append(f"^LH{_dots(pl.get('marge_gauche_mm', 0) + k * pas, dpi)},0")
            for e in elements_visibles(layout, vals):
                z = _zpl_element(e, vals, dpi)
                if z:
                    lignes.append(z)
        lignes += [f"^PQ{max(1, int(exemplaires))}", "^XZ"]
        out.append("\n".join(lignes) + "\n")
    return "".join(out)


def rendre_serie(layout: dict, largeur_mm: float, hauteur_mm: float, dpi: int,
                 plan: dict, quantite: int, saisies: dict, exemplaires: int = 1) -> tuple[str, list]:
    """ZPL de toute la série + liste des valeurs de chaque étiquette."""
    maintenant = datetime.now()
    toutes = [valeurs_etiquette(layout, plan, i, saisies, maintenant) for i in range(quantite)]
    return rendre_lot(layout, largeur_mm, hauteur_mm, dpi, toutes, exemplaires), toutes

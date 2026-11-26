"""
SIFA — Ce que le dossier fabrique et ce que le devis chiffrait, côte à côte.

Cinq caractéristiques, lues des deux côtés pour pouvoir les comparer :
format, quantité, étiquettes par rouleau, matière, colle (demande du
24/11/2026 : « sur le dossier et sur le devis rattaché, pour mieux les
comparer »).

D'où vient chaque valeur :

| | Dossier | Devis |
|---|---|---|
| Format | OF (`format`), sinon le planning | classeur (`format_v × format_h`) |
| Quantité | OF (`qte_etiquettes`) | classeur (`Prix!B13`) |
| Étiquettes par rouleau | OF : « Bobine de 650 étiquettes », sinon quantité ÷ bobines | classeur (`Prix!E12`), sinon « B3500 » du nom de fichier |
| Matière | OF (`matiere`) | nom du fichier (le « Matière n° » du classeur pointe un fichier externe, figé) |
| Colle | OF (`adhesif_label`, sinon `ref_adhesif`) | nom du fichier (types et codes 4 chiffres) |

Les écarts suivent les règles du rapprochement automatique
(`devis_rapprochement`) : format sans tenir compte du sens, familles de
papier, codes de colle. Un côté inconnu n'est jamais un écart.
"""
import re
from typing import Optional

from app.services.devis_rapprochement import (
    _cotes, _proches, caracteristiques_devis, caracteristiques_entree,
)

# « Bobine de 4.000 étiquettes », « Bobines de 650 ex »
_RE_EX_BOBINE = re.compile(r"bobines?\s+de\s+([\d\s.  ]+)\s*(?:[ée]tiquettes|ex)", re.IGNORECASE)
# « … M76 B3500 … » dans le nom d'un devis : B = étiquettes par bobine.
_RE_EX_FICHIER = re.compile(r"(?<![a-z0-9])b\s?(\d{2,6})(?![\d])", re.IGNORECASE)

# Au-delà, la quantité produite n'est plus celle chiffrée (hors multiple exact).
ECART_QUANTITE = 0.10


def _n(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f > 0 else None


def _entier(txt) -> Optional[float]:
    chiffres = re.sub(r"[^\d]", "", str(txt or ""))
    return float(chiffres) if chiffres else None


def ex_par_rouleau_of(conditionnement, qte, bobines) -> Optional[float]:
    m = _RE_EX_BOBINE.search(str(conditionnement or ""))
    if m:
        v = _entier(m.group(1))
        if v:
            return v
    q, b = _n(qte), _n(bobines)
    return round(q / b) if (q and b) else None


def ex_par_rouleau_devis(valeur_classeur, filename) -> Optional[float]:
    v = _n(valeur_classeur)
    if v:
        return v
    m = _RE_EX_FICHIER.search(str(filename or ""))
    return float(m.group(1)) if m else None


def _fmt(a, b) -> str:
    a, b = _n(a), _n(b)
    return f"{a:g} × {b:g} mm" if (a and b) else ""


def _multiple(a: float, b: float) -> bool:
    grand, petit = max(a, b), min(a, b)
    k = round(grand / petit)
    return k >= 2 and abs(grand - k * petit) <= 0.001 * grand


def comparer(entree: dict, devis: dict, ex_rouleau_classeur, voc: dict) -> dict:
    """Les cinq lignes « Dossier / Devis ».

    `entree` : planning_entries + OF (`of_format`, `of_qte_etiquettes`,
    `of_qte_bobines`, `of_conditionnement`, `matiere`, `adhesif_label`,
    `ref_adhesif`). `devis` : ligne de `devis` (format_h, format_v,
    qte_etiquettes, filename)."""
    ce = caracteristiques_entree(
        {"matiere": entree.get("matiere"),
         "adhesif": entree.get("adhesif_label") or entree.get("ref_adhesif")}, voc)
    cd = caracteristiques_devis(devis, voc)
    lignes = []

    # Format
    fe = str(entree.get("of_format") or "").strip() or _fmt(entree.get("format_l"), entree.get("format_h"))
    fd = _fmt(devis.get("format_v"), devis.get("format_h"))
    ke, kd = _cotes(entree.get("format_l"), entree.get("format_h")), _cotes(devis.get("format_v"), devis.get("format_h"))
    ecart_f = len(ke) == 2 and len(kd) == 2 and not (_proches(ke[0], kd[0]) and _proches(ke[1], kd[1]))
    lignes.append({"cle": "format", "libelle": "Format", "dossier": fe, "devis": fd, "ecart": ecart_f})

    # Quantité
    qe, qd = _n(entree.get("of_qte_etiquettes")), _n(devis.get("qte_etiquettes"))
    ecart_q = bool(qe and qd and abs(qe - qd) / qd > ECART_QUANTITE and not _multiple(qe, qd))
    lignes.append({"cle": "quantite", "libelle": "Quantité", "unite": "ex",
                   "dossier": qe, "devis": qd, "ecart": ecart_q,
                   "note": "multiple exact" if (qe and qd and qe != qd and _multiple(qe, qd)) else ""})

    # Étiquettes par rouleau
    re_ = ex_par_rouleau_of(entree.get("of_conditionnement"), entree.get("of_qte_etiquettes"),
                            entree.get("of_qte_bobines"))
    rd = ex_par_rouleau_devis(ex_rouleau_classeur, devis.get("filename"))
    lignes.append({"cle": "ex_rouleau", "libelle": "Étiquettes par rouleau", "unite": "ex",
                   "dossier": re_, "devis": rd, "ecart": bool(re_ and rd and abs(re_ - rd) > 0.5)})

    # Matière : le texte de l'OF tel quel ; côté devis, la famille lue dans
    # le nom du fichier. L'écart ne se juge que sur deux familles connues.
    # Écrite comme l'OF l'écrit (« THERMIQUE PRO ») : le vocabulaire, lui,
    # est normalisé en minuscules sans accents.
    mat_d = " ".join(x for x in (cd["famille"], cd["qualificatif"]) if x).upper()
    ecart_m = bool(ce["famille"] and cd["famille"] and (
        ce["famille"] != cd["famille"] or (
            ce["qualificatif"] and cd["qualificatif"]
            and not ce["qualificatif"][:4] == cd["qualificatif"][:4])))
    lignes.append({"cle": "matiere", "libelle": "Matière",
                   "dossier": str(entree.get("matiere") or "").strip(), "devis": mat_d, "ecart": ecart_m})

    # Colle : libellé de l'OF, sinon sa référence ; codes à 4 chiffres et
    # types (permanent, enlevable…) comparés quand les deux côtés en ont.
    colle_e = str(entree.get("adhesif_label") or "").strip()
    if not colle_e and entree.get("ref_adhesif"):
        colle_e = f"réf. {str(entree['ref_adhesif']).strip()}"
    morceaux_d = [c.capitalize() for c in cd["colles"]] + [f"réf. {c}" for c in sorted(cd["codes_colle"])]
    colle_d = " · ".join(morceaux_d)
    ecart_c = False
    if ce["codes_colle"] and cd["codes_colle"]:
        ecart_c = not (ce["codes_colle"] & cd["codes_colle"])
    elif ce["colle"] and cd["colles"]:
        ecart_c = ce["colle"] not in cd["colles"]
    lignes.append({"cle": "colle", "libelle": "Colle", "dossier": colle_e, "devis": colle_d, "ecart": ecart_c})

    return {"lignes": lignes, "ecarts": sum(1 for l in lignes if l["ecart"]),
            "devis_fichier": devis.get("filename")}
